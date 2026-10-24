"""R82: native Qt local SSH tunnel panel, opt-in and fail-closed.
No credentials, hostnames or key paths enter status messages or exports.
Author: Abdelhalim Talbi.
"""
import time
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QCheckBox, QFileDialog)

from ssh_transport import SSHSettings
from tunnel_controller import TunnelController


class SSHTunnelPanel(QWidget):
    def __init__(self, profile=None, parent=None, controller_factory=TunnelController):
        super().__init__(parent)
        profile = profile if profile and profile.get('protocol') in ('SSH', 'SFTP') else {}
        self._controller = controller_factory()
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
        actions=QHBoxLayout();layout.addLayout(actions)
        self.start_button=QPushButton('Démarrer le tunnel');actions.addWidget(self.start_button)
        self.stop_button=QPushButton('Révoquer et fermer');actions.addWidget(self.stop_button)
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

    def _choose(self, field):
        path, _ = QFileDialog.getOpenFileName(self, 'Choisir un fichier local')
        if path:
            field.setText(path)

    def start_tunnel(self):
        if not self.consent.isChecked():
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
        self._timer.start()
        self._refresh()

    def request_close(self, callback=None):
        if callable(callback):
            self._close_callbacks.append(callback)
        if self._close_requested_at is None:
            self._close_requested_at=time.monotonic()
        self._controller.stop()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self._timer.start()
        self._refresh()
        return self.is_shutdown_complete()

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
        if (self._close_requested_at is not None and not self.is_shutdown_complete()
                and time.monotonic()-self._close_requested_at >= 12):
            label='Arrêt SSH non confirmé · nettoyage toujours en cours…'
        self.status.setText(label)
        if snapshot.phase in ('closed','failed','disconnected'):
            self.stop_button.setEnabled(False)
            self._timer.stop()
            callbacks, self._close_callbacks=self._close_callbacks, []
            for callback in callbacks:
                QTimer.singleShot(0,callback)
