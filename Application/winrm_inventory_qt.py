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


class _Signals(QObject):
    finished = Signal(int, object)


class _InventoryJob(QRunnable):
    def __init__(self, generation, origin, username, password, client_factory):
        super().__init__()
        self.generation = generation
        self._origin = origin
        self._username = username
        self._password = password
        self._factory = client_factory
        self._cancelled = Event()
        self.signals = _Signals()

    def cancel(self):
        self._cancelled.set()

    def run(self):
        result = {'state': 'cancelled'}
        try:
            if not self._cancelled.is_set():
                client = self._factory(self._origin, self._username,
                                       credential_provider=lambda: self._password)
                result = client.inventory(online=True, cancelled=self._cancelled.is_set)
        except WinRMError as exc:
            # WinRMError contains only fixed, sanitized error codes.
            result = {'state': 'error', 'code': str(exc)}
        except Exception:
            # Never propagate a provider exception: it may contain a password.
            result = {'state': 'error', 'code': 'winrm_transport_unavailable'}
        finally:
            self._password = None
            self._username = None
            self._origin = None
        if self._cancelled.is_set():
            result = {'state': 'cancelled'}
        self.signals.finished.emit(self.generation, result)


class WinRMInventoryPanel(QWidget):
    """Operator-initiated read-only inventory; secrets live only in a worker.

    credential_provider is optional for future vault-by-reference integration.
    Without it, a password is requested once through a masked Qt prompt.
    The UI never stores, logs, renders or exports the returned secret.
    """
    def __init__(self, parent=None, *, client_factory=WinRMReadOnly,
                 credential_provider=None, thread_pool=None):
        super().__init__(parent)
        self.setObjectName('winrmInventoryPanel')
        self._client_factory = client_factory
        self._credential_provider = credential_provider
        self._pool = thread_pool or QThreadPool.globalInstance()
        self._generation = 0
        self._pending = None
        self._closed = False
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Windows Server — inventaire OS et disques en lecture seule'))
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
        self.consent = QCheckBox('Autoriser une requête WinRM HTTPS explicite')
        self.consent.setObjectName('winrmOnlineConsent')
        layout.addWidget(self.consent)
        self.refresh_button = QPushButton('Lire l’inventaire')
        self.refresh_button.setObjectName('winrmInventoryRefresh')
        self.refresh_button.clicked.connect(self.refresh)
        layout.addWidget(self.refresh_button)
        self.status = QLabel('Hors ligne — aucune connexion WinRM ouverte.')
        self.status.setObjectName('winrmInventoryStatus')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.table = QTreeWidget()
        self.table.setObjectName('winrmInventoryRows')
        self.table.setHeaderLabels(['Propriété', 'Valeur'])
        layout.addWidget(self.table)
        layout.addWidget(QLabel('Aucune commande libre, aucune modification distante, '
                                'aucun mot de passe enregistré. Le certificat HTTPS est vérifié.'))
        self.origin.textChanged.connect(self._invalidate)
        self.username.textChanged.connect(self._invalidate)
        self.consent.toggled.connect(self._invalidate)

    def _invalidate(self, *_):
        self._generation += 1
        if self._pending is not None:
            self._pending.cancel()
        self._pending = None
        self.table.clear()
        self.refresh_button.setEnabled(not self._closed)
        self.status.setText('Hors ligne — consentement et paramètres à confirmer.')

    def refresh(self):
        if self._closed or self._pending is not None:
            return
        self.table.clear()
        if not self.consent.isChecked():
            self.status.setText('Hors ligne — autorisation explicite requise.')
            return
        # Validate BEFORE asking for a password, and without opening a socket.
        try:
            self._client_factory(self.origin.text(), self.username.text(),
                                 credential_provider=lambda: '')
        except WinRMError as exc:
            self.status.setText('Configuration refusée : ' + str(exc))
            return
        except Exception:
            self.status.setText('Configuration WinRM indisponible.')
            return
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
                               self.username.text(), password, self._client_factory)
        password = None
        self._pending = worker
        worker.signals.finished.connect(self._finished)
        self.refresh_button.setEnabled(False)
        self.status.setText('Lecture WinRM en cours…')
        self._pool.start(worker)

    def _finished(self, generation, result):
        if self._closed or generation != self._generation or not self.consent.isChecked():
            return
        self._pending = None
        self.refresh_button.setEnabled(True)
        if not isinstance(result, dict) or result.get('state') != 'ok':
            code = result.get('code', 'winrm_transport_unavailable') if isinstance(result, dict) else 'winrm_invalid_response'
            # Never show untrusted exception strings from custom client adapters.
            allowed = {'winrm_invalid_response', 'winrm_remote_query_failed',
                       'winrm_transport_unavailable', 'winrm_dependency_missing',
                       'winrm_cancelled', 'winrm_credentials_unavailable',
                       'winrm_credentials_required'}
            self.status.setText('Lecture refusée : ' + (code if code in allowed else 'winrm_transport_unavailable'))
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

    def hideEvent(self, event):
        self._invalidate()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._closed = True
        self._invalidate()
        super().closeEvent(event)
