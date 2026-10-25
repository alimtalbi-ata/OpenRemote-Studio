"""R94: opt-in Windows Server inventory preview over verified HTTPS WinRM.

No network on construction; no background polling; no secret persistence/export.
All responses are normalized by winrm_readonly before reaching Qt.
Author: Abdelhalim Talbi.
"""
from threading import Event

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel,
                               QLineEdit, QCheckBox, QPushButton, QTreeWidget,
                               QTreeWidgetItem, QInputDialog)

from winrm_readonly import WinRMReadOnly, WinRMError
from winrm_services_readonly import WinRMServicesReadOnly, _STATES, _MODES
from winrm_service_totals import validated_display_total, ServiceTotalError
from winrm_service_drift import compare_service_snapshots, ServiceDriftError
from winrm_credential_ref import validate_winrm_credential_ref, resolve_winrm_credential


class _Signals(QObject):
    finished = Signal(int, object)


class _InventoryJob(QRunnable):
    def __init__(self, generation, origin, username, password, client_factory,
                 operation='inventory', credential_ref=None, credential_resolver=None):
        super().__init__()
        self.generation = generation
        self._origin = origin
        self._username = username
        self._password = password
        self._factory = client_factory
        self._operation = operation
        self._credential_ref = credential_ref
        self._credential_resolver = credential_resolver
        self._cancelled = Event()
        self.signals = _Signals()

    def cancel(self):
        self._cancelled.set()

    def run(self):
        result = {'state': 'cancelled'}
        try:
            if not self._cancelled.is_set():
                if self._credential_ref is not None:
                    # Resolve inside the worker, never on the UI thread.
                    self._password = resolve_winrm_credential(
                        self._credential_ref, resolver=self._credential_resolver)
                if self._cancelled.is_set():
                    raise WinRMError('winrm_cancelled')
                client = self._factory(self._origin, self._username,
                                       credential_provider=lambda: self._password)
                # Operation is selected internally from a fixed allowlist.
                method = client.services if self._operation == 'services' else client.inventory
                result = method(online=True, cancelled=self._cancelled.is_set)
        except WinRMError as exc:
            # Custom clients may forge a WinRMError with secret text. Never
            # place untrusted exception text in a Qt signal payload.
            allowed = frozenset((
                'winrm_invalid_response', 'winrm_remote_query_failed',
                'winrm_transport_unavailable', 'winrm_dependency_missing',
                'winrm_cancelled', 'winrm_credentials_unavailable',
                'winrm_credentials_required',
            ))
            code = str(exc)
            result = {'state': 'error', 'code': (code if code in allowed
                                                 else 'winrm_transport_unavailable')}
        except Exception:
            # Never propagate a provider exception: it may contain a password.
            result = {'state': 'error', 'code': 'winrm_transport_unavailable'}
        finally:
            self._password = None
            self._credential_ref = None
            self._credential_resolver = None
            self._username = None
            self._origin = None
        if self._cancelled.is_set():
            result = {'state': 'cancelled'}
        self.signals.finished.emit(self.generation, result)


class WinRMInventoryPanel(QWidget):
    """Operator-initiated read-only inventory; secrets live only in a worker.

    A wincred: target is resolved inside the worker after explicit consent.
    Without a reference, a password is requested once through a masked Qt prompt.
    The UI never stores, logs, renders or exports the returned secret.
    """
    def __init__(self, parent=None, *, client_factory=None,
                 credential_provider=None, credential_resolver=None,
                 thread_pool=None, mode='inventory'):
        if mode not in ('inventory', 'services'):
            raise ValueError('unsupported WinRM operation')
        super().__init__(parent)
        self.setObjectName('winrmInventoryPanel')
        self._mode = mode
        self._services = []
        self._last_successful_services = None
        self._service_change_labels = {}
        self._client_factory = client_factory or (WinRMServicesReadOnly if mode == 'services' else WinRMReadOnly)
        self._credential_provider = credential_provider
        self._credential_resolver = credential_resolver
        self._pool = thread_pool or QThreadPool.globalInstance()
        self._generation = 0
        self._pending = None
        self._closed = False
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Windows Server — services en lecture seule' if mode == 'services'
                                else 'Windows Server — inventaire OS et disques en lecture seule'))
        form = QFormLayout()
        layout.addLayout(form)
        self.origin = QLineEdit()
        self.origin.setObjectName('winrmOrigin')
        self.origin.setMaxLength(300)
        self.origin.setPlaceholderText('https://windows.example.internal:5986')
        form.addRow('Origine WinRM HTTPS', self.origin)
        self.username = QLineEdit()
        self.username.setObjectName('winrmUsername')
        self.username.setMaxLength(256)
        form.addRow('Compte de lecture', self.username)
        self.credential_ref = QLineEdit()
        self.credential_ref.setObjectName('winrmCredentialReference')
        self.credential_ref.setMaxLength(136)
        self.credential_ref.setPlaceholderText('wincred:OpenRemote/WinRM/serveur (facultatif)')
        form.addRow('Référence Credential Manager', self.credential_ref)
        self.consent = QCheckBox('Autoriser une requête WinRM HTTPS explicite')
        self.consent.setObjectName('winrmOnlineConsent')
        layout.addWidget(self.consent)
        self.refresh_button = QPushButton('Lire les services' if mode == 'services'
                                          else 'Lire l’inventaire')
        self.refresh_button.setObjectName('winrmInventoryRefresh')
        self.refresh_button.clicked.connect(self.refresh)
        layout.addWidget(self.refresh_button)
        self.status = QLabel('Hors ligne — aucune connexion WinRM ouverte.')
        self.status.setObjectName('winrmInventoryStatus')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.table = QTreeWidget()
        self.table.setObjectName('winrmInventoryRows')
        self.table.setHeaderLabels(['Service', 'Libellé', 'État', 'Démarrage', 'Évolution'] if mode == 'services'
                                   else ['Propriété', 'Valeur'])
        if mode == 'services':
            self.service_filter = QLineEdit()
            self.service_filter.setObjectName('winrmServicesFilter')
            self.service_filter.setMaxLength(128)
            self.service_filter.setPlaceholderText('Filtrer localement : nom, état, démarrage…')
            layout.addWidget(self.service_filter)
            self.service_filter.textChanged.connect(self._filter_services)
            self.filter_status = QLabel('Aucun service chargé.')
            self.filter_status.setObjectName('winrmServicesFilterStatus')
            layout.addWidget(self.filter_status)
            self.drift_status = QLabel('Aucune comparaison locale disponible.')
            self.drift_status.setObjectName('winrmServicesDriftStatus')
            self.drift_status.setWordWrap(True)
            layout.addWidget(self.drift_status)
        layout.addWidget(self.table)
        layout.addWidget(QLabel('Aucune commande libre, aucune modification distante, '
                                'aucun mot de passe enregistré. Le certificat HTTPS est vérifié.'))
        self.origin.textChanged.connect(self._invalidate)
        self.username.textChanged.connect(self._invalidate)
        self.credential_ref.textChanged.connect(self._invalidate)
        self.consent.toggled.connect(self._invalidate)

    def _invalidate(self, *_):
        # Consent is bound to the exact endpoint, account and credential ref.
        # A changed field always requires a new operator authorization.
        if (self.sender() in (self.origin, self.username, self.credential_ref)
                and self.consent.isChecked()):
            self.consent.setChecked(False)
            return
        self._generation += 1
        self._services = []
        self._last_successful_services = None
        self._service_change_labels = {}
        if self._mode == 'services':
            self.drift_status.setText('Comparaison effacée — paramètres ou consentement modifiés.')
            self.filter_status.setText('Aucun service chargé.')
        if self._pending is not None:
            self._pending.cancel()
        # Do not permit a second request while an invalidated network call is
        # still draining: cancellation cannot interrupt an in-flight WinRM POST.
        self.table.clear()
        self.refresh_button.setEnabled(not self._closed and self._pending is None)
        self.status.setText('Hors ligne — consentement et paramètres à confirmer.')

    def refresh(self):
        if self._closed or self._pending is not None:
            return
        self._services = []
        self._service_change_labels = {}
        if self._mode == 'services':
            self.filter_status.setText('Aucun service chargé.')
            self.drift_status.setText('Lecture en cours — dernière référence locale conservée.')
        self.table.clear()
        if not self.consent.isChecked():
            self.status.setText('Hors ligne — autorisation explicite requise.')
            return
        # Validate BEFORE asking for a password, and without opening a socket.
        try:
            # Validate with the production parser, not a replaceable test/provider
            # factory: a custom constructor may have side effects or open sockets.
            WinRMReadOnly(self.origin.text(), self.username.text(),
                          credential_provider=lambda: '')
        except WinRMError as exc:
            self.status.setText('Configuration refusée : ' + str(exc))
            return
        except Exception:
            self.status.setText('Configuration WinRM indisponible.')
            return
        reference = self.credential_ref.text()
        if reference:
            try:
                validate_winrm_credential_ref(reference)
            except WinRMError:
                self.status.setText('Référence Credential Manager invalide.')
                return
            password = None  # Never resolve WinCred from the Qt event thread.
        else:
            try:
                if self._credential_provider is not None:
                    password = self._credential_provider()
                else:
                    password, accepted = QInputDialog.getText(
                        self, 'WinRM — authentification temporaire',
                        'Mot de passe (non enregistré) :', QLineEdit.Password)
                    if not accepted:
                        self.status.setText('Hors ligne — authentification annulée.')
                        return
            except Exception:
                self.status.setText('Identifiants indisponibles.')
                return
            if not isinstance(password, str) or not password or '\x00' in password:
                self.status.setText('Identifiants indisponibles.')
                return
        self._generation += 1
        worker = _InventoryJob(self._generation, self.origin.text(),
                               self.username.text(), password, self._client_factory,
                               operation=self._mode, credential_ref=reference or None,
                               credential_resolver=self._credential_resolver)
        password = None
        self._pending = worker
        worker.signals.finished.connect(self._finished)
        self.refresh_button.setEnabled(False)
        self.status.setText('Lecture WinRM en cours…')
        self._pool.start(worker)

    def _finished(self, generation, result):
        # Exactly one worker may be outstanding. Even an invalidated response
        # releases the concurrency gate, but never updates visible inventory.
        self._pending = None
        self.refresh_button.setEnabled(not self._closed)
        if self._closed or generation != self._generation or not self.consent.isChecked():
            return
        if not isinstance(result, dict) or result.get('state') != 'ok':
            code = result.get('code', 'winrm_transport_unavailable') if isinstance(result, dict) else 'winrm_invalid_response'
            # Never show untrusted exception strings from custom client adapters.
            allowed = {'winrm_invalid_response', 'winrm_remote_query_failed',
                       'winrm_transport_unavailable', 'winrm_dependency_missing',
                       'winrm_cancelled', 'winrm_credentials_unavailable',
                       'winrm_credentials_required'}
            self.status.setText('Lecture refusée : ' + (code if isinstance(code, str) and code in allowed else 'winrm_transport_unavailable'))
            return
        if self._mode == 'services':
            try:
                items = result['services']
                if (result.get('read_only') is not True or result.get('limit') != 128
                        or type(result.get('may_be_truncated')) is not bool
                        or not isinstance(items, list) or len(items) > 128):
                    raise ValueError('invalid services')
                total_count = validated_display_total(
                    result.get('total_count'), items, result['may_be_truncated'])
                rows = []
                seen = set()
                for item in items:
                    if not isinstance(item, dict):
                        raise ValueError('invalid service')
                    row = tuple(item[key] for key in ('name', 'display_name', 'state', 'start_mode'))
                    if (any(not isinstance(v, str) or len(v) > 256
                            or any(ord(ch) < 32 or ord(ch) == 127 for ch in v) for v in row)
                            or not row[0] or row[2] not in _STATES or row[3] not in _MODES
                            or row[0].casefold() in seen):
                        raise ValueError('invalid service fields')
                    seen.add(row[0].casefold())
                    rows.append(row)
            except (KeyError, TypeError, ValueError, ServiceTotalError):
                self.status.setText('Réponse WinRM invalide.')
                return
            # Compare only successful readings under unchanged consent and endpoint.
            # Never infer missing services from truncated snapshots.
            snapshot = [dict(zip(('name', 'display_name', 'state', 'start_mode'), row))
                        for row in rows]
            self._service_change_labels = {}
            if self._last_successful_services is None:
                self.drift_status.setText('Première lecture : référence locale enregistrée.')
            else:
                try:
                    previous, previous_truncated = self._last_successful_services
                    drift = compare_service_snapshots(
                        previous, snapshot,
                        previous_truncated=previous_truncated,
                        current_truncated=result['may_be_truncated'])
                except ServiceDriftError:
                    self.status.setText('Comparaison WinRM invalide.')
                    return
                for change in drift['transitions']:
                    pieces = []
                    if change['before_state'] != change['after_state']:
                        pieces.append(change['before_state'] + ' → ' + change['after_state'])
                    if change['before_mode'] != change['after_mode']:
                        pieces.append(change['before_mode'] + ' → ' + change['after_mode'])
                    self._service_change_labels[change['name'].casefold()] = '; '.join(pieces)
                for name in drift['added']:
                    self._service_change_labels[name.casefold()] = 'Nouveau'
                summary = (f"Comparaison locale : {len(drift['transitions'])} transition(s), "
                           f"{len(drift['added'])} ajout(s), {len(drift['removed'])} disparition(s).")
                if not drift['membership_complete']:
                    summary += ' Inventaire tronqué : ajouts et disparitions non évalués.'
                self.drift_status.setText(summary)
            self._last_successful_services = (snapshot, result['may_be_truncated'])
            self._services = rows
            self._filter_services()
            if total_count is None:
                warning = ' — résultat potentiellement tronqué (128 max).' if result['may_be_truncated'] else '.'
                self.status.setText('Services en lecture seule — ' + str(len(rows)) + ' reçus' + warning)
            else:
                warning = ' — résultat tronqué (128 max).' if result['may_be_truncated'] else '.'
                self.status.setText('Services en lecture seule — ' + str(len(rows)) +
                                    '/' + str(total_count) + ' reçus' + warning)
            return
        try:
            os_info = result['os']
            rows = [('Système', os_info['caption']), ('Version', os_info['version']),
                    ('Build', os_info['build']), ('Machine', os_info['computer'])]
            for disk in result['disks']:
                rows.append(('Volume ' + disk['drive'],
                             str(disk['free_bytes']) + ' libres / ' + str(disk['size_bytes']) + ' octets'))
            if len(rows) > 132 or any(not isinstance(a, str) or not isinstance(b, str) for a, b in rows):
                raise ValueError('invalid inventory')
        except (KeyError, TypeError, ValueError):
            self.status.setText('Réponse WinRM invalide.')
            return
        self.table.clear()
        for key, value in rows:
            self.table.addTopLevelItem(QTreeWidgetItem([key, value]))
        self.status.setText('Inventaire en lecture seule — ' + str(len(result['disks'])) + ' volume(s).')

    def _filter_services(self, *_):
        if self._mode != 'services':
            return
        # No network, credential access or worker creation during filtering.
        needle = self.service_filter.text().strip().casefold()
        self.table.clear()
        shown = 0
        for row in self._services:
            if needle and needle not in ' '.join(row).casefold():
                continue
            self.table.addTopLevelItem(QTreeWidgetItem(
                list(row) + [self._service_change_labels.get(row[0].casefold(), '—')]))
            shown += 1
        self.filter_status.setText(f'{shown}/{len(self._services)} services affichés — filtre local.')

    def hideEvent(self, event):
        self._invalidate()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._closed = True
        self._invalidate()
        super().closeEvent(event)


class WinRMServicesPanel(WinRMInventoryPanel):
    """R96 services viewer: same offline, consent and cancellation gate as OS inventory."""

    def __init__(self, parent=None, *, client_factory=WinRMServicesReadOnly,
                 credential_provider=None, credential_resolver=None, thread_pool=None):
        super().__init__(parent, client_factory=client_factory,
                         credential_provider=credential_provider,
                         credential_resolver=credential_resolver,
                         thread_pool=thread_pool, mode='services')
