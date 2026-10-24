"""R82: native Qt local SSH tunnel panel, opt-in and fail-closed.
No credentials, hostnames or key paths enter status messages or exports.
Author: Abdelhalim Talbi.
"""
import time
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QCheckBox, QFileDialog)

from ssh_transport import SSHSettings
from ssh_consent_guard import SSHConsentGuard
from tunnel_controller import TunnelController


class SSHTunnelPanel(QWidget):
    def __init__(self, profile=None, parent=None, controller_factory=TunnelController):
        super().__init__(parent)
        profile = profile if profile and profile.get('protocol') in ('SSH', 'SFTP') else {}
        self._controller_factory = controller_factory
        self._controller = controller_factory()
        self._consent_guard = SSHConsentGuard()
        self._closing_panel = False
        self._close_callbacks = []
        self._close_requested_at = None
        self.setObjectName('sshTunnelPanel')
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Tunnel local 127.0.0.1 uniquement · hors ligne par défaut.'))
        form = QFormLayout(); layout.addLayout(form)
        self.host = QLineEdit(str(profile.get('host') or ''))
        self.user = QLineEdit(str(profile.get('user') or ''))
        self.ssh_port = QLineEdit(str(profile.get('port') or 22))
        self.local_port = QLineEdit('8080')
        self.keepalive_seconds = QLineEdit('0')
        self.keepalive_seconds.setObjectName('sshKeepaliveSeconds')
        self.keepalive_seconds.setPlaceholderText('0 = désactivé ; 15–60 s conseillé sur réseau instable')
        self.target_host = QLineEdit('127.0.0.1')
        self.target_port = QLineEdit('80')
        self.key_file = QLineEdit()
        self.key_file.setPlaceholderText('Clé privée locale (jamais exportée)')
        self.known_hosts = QLineEdit()
        self.known_hosts.setPlaceholderText('Facultatif : known_hosts explicite')
        for label, widget in [('Hôte SSH',self.host), ('Utilisateur SSH',self.user),
            ('Port SSH',self.ssh_port), ('Keepalive SSH (secondes, 0–300)',self.keepalive_seconds),
            ('Port local (127.0.0.1)',self.local_port),
            ('Destination vue du serveur SSH',self.target_host),
            ('Port distant',self.target_port), ('Clé privée',self.key_file),
            ('Fichier known_hosts',self.known_hosts)]:
            form.addRow(label,widget)
        for field, title in [(self.key_file,'Choisir une clé'),
                             (self.known_hosts,'Choisir known_hosts')]:
            button=QPushButton(title)
            button.clicked.connect(lambda _=False, f=field: self._choose(f))
            form.addRow('',button)
        self.consent = QCheckBox('Autoriser explicitement cette connexion SSH et ce tunnel local')
        layout.addWidget(self.consent)
        # Consent is bound to the exact form revision, never just a checked box.
        # Store no endpoint, username, private-key path or other secret in the guard.
        self.consent.toggled.connect(self._consent_toggled)
        for field in (self.host, self.user, self.ssh_port, self.keepalive_seconds,
                      self.local_port, self.target_host, self.target_port,
                      self.key_file, self.known_hosts):
            field.textChanged.connect(self._configuration_changed)
        actions=QHBoxLayout();layout.addLayout(actions)
        self.start_button=QPushButton('Démarrer le tunnel');actions.addWidget(self.start_button)
        self.stop_button=QPushButton('Révoquer et fermer');actions.addWidget(self.stop_button)
        self.retry_button=QPushButton('Nouvelle tentative');actions.addWidget(self.retry_button)
        self.retry_button.setObjectName('sshTunnelRetryButton')
        self.retry_button.setEnabled(False)
        self.retry_button.clicked.connect(self.prepare_retry)
        self.start_button.clicked.connect(self.start_tunnel)
        self.stop_button.clicked.connect(self.request_close)
        self.stop_button.setEnabled(False)
        self.status=QLabel('Hors ligne · aucune connexion ouverte')
        self.status.setObjectName('sshTunnelStatus')
        layout.addWidget(self.status)
        layout.addWidget(QLabel('Clé d’hôte inconnue ou modifiée : refus strict. '
                                'Authentification par clé privée uniquement; aucun agent SSH automatique.'))
        layout.addStretch(1)
        self._timer=QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._refresh)

    def _revoke_live_tunnel(self):
        """A revoked approval cannot leave a connecting/active tunnel running.

        Qt can change disabled/read-only widgets programmatically. The network
        controller, not the checkbox's enabled state, determines revocation.
        """
        if self._controller.poll().phase in ('connecting', 'active'):
            self.request_close()

    def _consent_toggled(self, checked):
        if checked:
            self._consent_guard.approve()
        else:
            self._consent_guard.revoke()
            self._revoke_live_tunnel()

    def _configuration_changed(self, *_):
        # Any edit, including changing back, revokes consent even if the
        # checkbox was already unchecked by a separate programmatic action.
        self._consent_guard.configuration_changed()
        if self.consent.isChecked():
            self.consent.setChecked(False)  # toggled signal closes a live tunnel
        else:
            self._revoke_live_tunnel()

    def _choose(self, field):
        path, _ = QFileDialog.getOpenFileName(self, 'Choisir un fichier local')
        if path:
            field.setText(path)

    def start_tunnel(self):
        if not self.consent.isChecked() or not self._consent_guard.approved:
            self.status.setText('Hors ligne : autorisation explicite requise')
            return
        try:
            settings=SSHSettings(self.host.text(), self.user.text(),
                                 int(self.ssh_port.text()), timeout=12,
                                 known_hosts=self.known_hosts.text() or None)
            self._controller.start(settings, key_filename=self.key_file.text(),
                                   local_port=int(self.local_port.text()),
                                   target_host=self.target_host.text(),
                                   target_port=int(self.target_port.text()),
                                   keepalive_seconds=int(self.keepalive_seconds.text()))
        except (ValueError, RuntimeError):
            self.status.setText('Configuration refusée : vérifier les paramètres SSH et les ports')
            return
        for field in (self.host,self.user,self.ssh_port,self.keepalive_seconds,self.local_port,
                      self.target_host,self.target_port,self.key_file,self.known_hosts):
            field.setReadOnly(True)
        self.consent.setEnabled(False)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.retry_button.setEnabled(False)
        self._timer.start()
        self._refresh()

    def request_close(self, callback=None):
        if callable(callback):
            self._closing_panel = True
            self._close_callbacks.append(callback)
        if self._close_requested_at is None:
            self._close_requested_at=time.monotonic()
        self._controller.stop()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.retry_button.setEnabled(False)
        self._timer.start()
        self._refresh()
        return self.is_shutdown_complete()

    def prepare_retry(self):
        """Explicit manual reset only after cleanup; never reconnect implicitly.

        The controller is intentionally one-shot. Reusing it after a failed
        connection would bypass its lifecycle guard, so replace it only after
        its resources are confirmed released and require fresh consent.
        """
        if (self._closing_panel or self._close_callbacks
                or not self.is_shutdown_complete()):
            return False
        if self._controller.poll().phase not in ('closed', 'failed', 'disconnected'):
            return False
        self._timer.stop()
        self._controller = self._controller_factory()
        self._close_requested_at = None
        for field in (self.host, self.user, self.ssh_port, self.keepalive_seconds,
                      self.local_port, self.target_host, self.target_port,
                      self.key_file, self.known_hosts):
            field.setReadOnly(False)
        self.consent.setChecked(False)
        self.consent.setEnabled(True)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.retry_button.setEnabled(False)
        self.status.setText('Hors ligne : nouvelle autorisation explicite requise')
        return True

    def is_shutdown_complete(self):
        return self._controller.is_shutdown_complete()

    def _refresh(self):
        snapshot=self._controller.poll()
        descriptions={
            'idle':'Hors ligne', 'connecting':'Connexion SSH en cours…',
            'active':f'Tunnel actif · {snapshot.active_connections} connexion(s) · '
                     f'{snapshot.pending_channel_opens} négociation(s)',
            'closing':'Fermeture SSH en cours…',
            'cleanup':'Nettoyage des ressources SSH…',
            'draining':'Drainage des canaux SSH…',
            'closed':'Tunnel fermé et ressources libérées',
            'failed':'Échec SSH (détails sensibles masqués) · ressources libérées',
            'disconnected':'Connexion SSH interrompue · ressources libérées',
        }
        label=descriptions.get(snapshot.phase,'État SSH indisponible')
        if snapshot.phase == 'failed':
            # Fixed messages only; never expose Paramiko exception strings,
            # endpoint names, key paths or credential details.
            label = {
                'host_key': 'Clé d’hôte SSH refusée · vérifier known_hosts hors bande',
                'authentication': 'Authentification SSH refusée · vérifier la clé privée',
            }.get(snapshot.failure_code, label)
        if (self._close_requested_at is not None and not self.is_shutdown_complete()
                and time.monotonic()-self._close_requested_at >= 12):
            label='Arrêt SSH non confirmé · nettoyage toujours en cours…'
        terminal = snapshot.phase in ('closed', 'failed', 'disconnected')
        # A terminal-looking phase alone must not release the parent tab.
        # The controller owns the listener and in-flight SSH channels.
        drained = self.is_shutdown_complete() if terminal else False
        if terminal and not drained:
            label = 'Nettoyage des ressources SSH…'
        self.status.setText(label)
        if terminal and drained:
            self.stop_button.setEnabled(False)
            self.retry_button.setEnabled(not self._closing_panel)
            self._timer.stop()
            callbacks, self._close_callbacks = self._close_callbacks, []
            for callback in callbacks:
                QTimer.singleShot(0, callback)
        elif terminal:
            self.stop_button.setEnabled(False)
            self.retry_button.setEnabled(False)
            # Keep polling until shutdown is confirmed; callbacks remain queued.
            if not self._timer.isActive():
                self._timer.start()
