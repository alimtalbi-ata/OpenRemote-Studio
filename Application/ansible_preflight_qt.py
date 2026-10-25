"""R116 Qt UI: offline Ansible preflight with explicit, constrained check-mode run.

No output from the Ansible child process is captured or displayed. Author:
Abdelhalim Talbi.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QFileDialog, QTreeWidget, QTreeWidgetItem,
)

from ansible_preflight import (AnsiblePreflightError, analyze_playbook, run_check_mode, connection_fingerprints)


class _Signals(QObject):
    finished = Signal(int, str, object)


class _Task(QRunnable):
    def __init__(self, generation, mode, operation, kwargs):
        super().__init__()
        self.generation = generation
        self.mode = mode
        self.operation = operation
        self.kwargs = dict(kwargs)
        self.signals = _Signals()
        from threading import Event
        self._cancelled = Event()

    def cancel(self):
        self._cancelled.set()
        self.kwargs["cancelled"] = self._cancelled.is_set

    def run(self):
        if self._cancelled.is_set():
            self.signals.finished.emit(self.generation, self.mode, {
                "state": "cancelled", "read_only": True, "output_retained": False,
            })
            return
        try:
            if self.mode == "check":
                self.kwargs["cancelled"] = self._cancelled.is_set
            result = self.operation(**self.kwargs)
            if self._cancelled.is_set():
                result = {"state": "cancelled", "read_only": True, "output_retained": False}
        except AnsiblePreflightError as exc:
            result = {"state": "error", "code": str(exc),
                      "read_only": True, "output_retained": False}
        except Exception:
            result = {"state": "error", "code": "ansible_operation_unavailable",
                      "read_only": True, "output_retained": False}
        finally:
            # Do not retain credentials or child output in a worker after completion.
            self.kwargs.clear()
            self.operation = lambda **_kwargs: {}
        self.signals.finished.emit(self.generation, self.mode, result)


class AnsiblePreflightPanel(QWidget):
    """Offline static preview and user-confirmed public-key SSH check mode."""
    def __init__(self, parent=None, *, analyzer=analyze_playbook, runner=run_check_mode,
                 executable_lookup=None, pool=None):
        super().__init__(parent)
        self.setObjectName("ansiblePreflightPanel")
        self._analyzer = analyzer or analyze_playbook
        self._runner = runner or run_check_mode
        self._which = executable_lookup or shutil.which
        self._pool = pool or QThreadPool.globalInstance()
        self._pending = None
        self._generation = 0
        self._analysis = None
        self._connection_fingerprints = None
        self._closed = False
        self._last_mode = ""

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Ansible — prévalidation statique hors ligne. Aucun playbook n'est exécuté à l'analyse."
        ))
        layout.addWidget(QLabel(
            "Le check mode distant reste indicatif (pas un sandbox). Seuls sept modules "
            "builtin en lecture seule sont acceptés ; les commandes, rôles et plugins sont refusés."
        ))

        self.playbook_path = QLineEdit()
        self.playbook_path.setObjectName("ansiblePlaybookPath")
        self.playbook_path.setPlaceholderText("Playbook statique .yml/.yaml")
        layout.addLayout(self._path_row("Playbook", self.playbook_path, self._browse_playbook))

        self.inventory_path = QLineEdit()
        self.inventory_path.setObjectName("ansibleInventoryPath")
        self.inventory_path.setPlaceholderText("Inventaire statique .ini (groupes, hôtes uniquement)")
        layout.addLayout(self._path_row("Inventaire", self.inventory_path, self._browse_inventory))

        self.known_hosts_path = QLineEdit()
        self.known_hosts_path.setObjectName("ansibleKnownHostsPath")
        self.known_hosts_path.setPlaceholderText("known_hosts explicitement approuvé (requis pour exécuter)")
        layout.addLayout(self._path_row("Clés hôtes", self.known_hosts_path, self._browse_known_hosts))

        self.private_key_path = QLineEdit()
        self.private_key_path.setObjectName("ansiblePrivateKeyPath")
        self.private_key_path.setPlaceholderText("Fichier de clé privée SSH (jamais affiché/lu dans l'UI)")
        layout.addLayout(self._path_row("Clé SSH", self.private_key_path, self._browse_key))

        self.username = QLineEdit()
        self.username.setObjectName("ansibleRemoteUsername")
        self.username.setPlaceholderText("Utilisateur distant (facultatif)")
        user_row = QHBoxLayout()
        user_row.addWidget(QLabel("Utilisateur SSH"))
        user_row.addWidget(self.username, 1)
        layout.addLayout(user_row)

        self.consent = QCheckBox(
            "J'autorise une connexion SSH limitée avec clé hôte épinglée "
            "et --check --diff (des fichiers temporaires distants peuvent exister)."
        )
        self.consent.setObjectName("ansibleCheckModeConsent")
        self.consent.setChecked(False)
        layout.addWidget(self.consent)

        controls = QHBoxLayout()
        layout.addLayout(controls)
        self.analyze_button = QPushButton("Analyser hors ligne")
        self.analyze_button.setObjectName("ansibleAnalyzeOffline")
        self.analyze_button.clicked.connect(self.analyze)
        controls.addWidget(self.analyze_button)

        self.run_button = QPushButton("Exécuter le check mode")
        self.run_button.setObjectName("ansibleRunCheckMode")
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(self.run_check)
        controls.addWidget(self.run_button)

        self.cancel_button = QPushButton("Annuler")
        self.cancel_button.setObjectName("ansibleCancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_current)
        controls.addWidget(self.cancel_button)

        self.status = QLabel("Hors ligne — aucune connexion et aucun processus Ansible démarré.")
        self.status.setObjectName("ansiblePreflightStatus")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.summary = QTreeWidget()
        self.summary.setObjectName("ansiblePreflightSummary")
        self.summary.setHeaderLabels(["Module builtin autorisé", "Tâches"])
        self.summary.setRootIsDecorated(False)
        self.summary.setAlternatingRowColors(True)
        layout.addWidget(self.summary, 1)

        for field in (self.playbook_path, self.inventory_path, self.known_hosts_path,
                      self.private_key_path, self.username):
            field.textChanged.connect(self._inputs_changed)
        self.consent.toggled.connect(self._consent_changed)
        self._refresh_gate()

    def _path_row(self, label, field, callback):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(field, 1)
        button = QPushButton("Parcourir…")
        button.clicked.connect(callback)
        row.addWidget(button)
        return row

    def _browse_playbook(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir un playbook", "",
                                               "Playbooks YAML (*.yml *.yaml)")
        if path:
            self.playbook_path.setText(path)

    def _browse_inventory(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir un inventaire", "",
                                               "Inventaires INI (*.ini)")
        if path:
            self.inventory_path.setText(path)

    def _browse_known_hosts(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir known_hosts", "", "Tous les fichiers (*)")
        if path:
            self.known_hosts_path.setText(path)

    def _browse_key(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir une clé SSH privée", "",
                                               "Tous les fichiers (*)")
        if path:
            self.private_key_path.setText(path)

    def _consent_changed(self, checked):
        if not checked:
            self._connection_fingerprints = None
            self._refresh_gate()
            return
        # Consent is tied to the exact trust anchors and private-key bytes in use;
        # their contents are never displayed or retained in the UI.
        try:
            self._connection_fingerprints = connection_fingerprints(
                self.known_hosts_path.text().strip(),
                self.private_key_path.text().strip(),
            )
        except AnsiblePreflightError as exc:
            self._connection_fingerprints = None
            self.consent.blockSignals(True)
            self.consent.setChecked(False)
            self.consent.blockSignals(False)
            self.status.setText(f"Consentement refusé — {str(exc)}.")
        except Exception:
            self._connection_fingerprints = None
            self.consent.blockSignals(True)
            self.consent.setChecked(False)
            self.consent.blockSignals(False)
            self.status.setText("Consentement refusé — fichiers SSH indisponibles.")
        else:
            self.status.setText(
                "Consentement lié aux fichiers sélectionnés — known_hosts SHA-256 "
                f"{self._connection_fingerprints['known_hosts_sha256'][:12]}… / "
                f"clé SHA-256 {self._connection_fingerprints['private_key_sha256'][:12]}…. "
                "Les fichiers seront revérifiés avant l'appel réseau."
            )
        self._refresh_gate()

    def _refresh_gate(self, *_):
        pending = self._pending is not None
        self.analyze_button.setEnabled(not pending and bool(self.playbook_path.text().strip())
                                       and bool(self.inventory_path.text().strip()))
        try:
            executable_available = bool(self._which("ansible-playbook"))
        except Exception:
            executable_available = False
        can_run = (
            not pending and isinstance(self._analysis, dict) and self._analysis.get("state") == "ok"
            and executable_available and self.consent.isChecked()
            and bool(self.known_hosts_path.text().strip())
            and bool(self.private_key_path.text().strip())
            and isinstance(self._connection_fingerprints, dict)
        )
        self.run_button.setEnabled(bool(can_run))
        self.cancel_button.setEnabled(pending)

    def _inputs_changed(self, *_):
        if self._closed:
            return
        self._generation += 1
        if self._pending is not None:
            self._pending.cancel()
        self._analysis = None
        self._connection_fingerprints = None
        self.summary.clear()
        self.consent.blockSignals(True)
        self.consent.setChecked(False)
        self.consent.blockSignals(False)
        if self._pending is None:
            self.status.setText("Entrées modifiées — consentement révoqué, nouvelle analyse requise.")
        else:
            self.status.setText("Annulation demandée — attente de l'arrêt de la tâche précédente.")
        self._refresh_gate()

    def _launch(self, mode, operation, kwargs):
        if self._closed or self._pending is not None:
            return
        self._generation += 1
        task = _Task(self._generation, mode, operation, kwargs)
        task.signals.finished.connect(self._finish)
        self._pending = task
        self._last_mode = mode
        self.status.setText("Analyse locale en cours…" if mode == "analyze"
                            else "Check mode SSH en cours — aucune sortie brute conservée.")
        self._refresh_gate()
        self._pool.start(task)

    def analyze(self):
        if self._pending is not None:
            return
        playbook = self.playbook_path.text().strip()
        inventory = self.inventory_path.text().strip()
        if not playbook or not inventory:
            self.status.setText("Sélectionnez un playbook et un inventaire statique.")
            return
        self._analysis = None
        self.summary.clear()
        self._launch("analyze", self._analyzer, {
            "playbook_path": playbook, "inventory_path": inventory,
        })

    def run_check(self):
        if not self.run_button.isEnabled() or not isinstance(self._analysis, dict):
            self.status.setText("Analyse réussie, CLI, known_hosts, clé SSH et consentement requis.")
            return
        # Bind approval to the exact byte fingerprints reviewed during the offline
        # analysis. The runner rechecks these before creating snapshots or sockets.
        self._launch("check", self._runner, {
            "playbook_path": self.playbook_path.text().strip(),
            "inventory_path": self.inventory_path.text().strip(),
            "known_hosts_path": self.known_hosts_path.text().strip(),
            "private_key_path": self.private_key_path.text().strip(),
            "username": self.username.text().strip(),
            "consent": True,
            "timeout_seconds": 60,
            "expected_playbook_sha256": self._analysis["playbook_sha256"],
            "expected_inventory_sha256": self._analysis["inventory_sha256"],
            "expected_known_hosts_sha256": self._connection_fingerprints["known_hosts_sha256"],
            "expected_private_key_sha256": self._connection_fingerprints["private_key_sha256"],
            "executable_lookup": self._which,
        })

    def cancel_current(self):
        if self._pending is None:
            return
        self._generation += 1
        self._pending.cancel()
        self._analysis = None
        self._connection_fingerprints = None
        self.summary.clear()
        self.consent.blockSignals(True)
        self.consent.setChecked(False)
        self.consent.blockSignals(False)
        self.status.setText("Annulation demandée — aucun résultat en attente ne sera affiché.")
        self._refresh_gate()

    def _finish(self, generation, mode, result):
        self._pending = None
        if self._closed or generation != self._generation:
            self._refresh_gate()
            return
        state = result.get("state") if isinstance(result, dict) else "error"
        if mode == "analyze" and state == "ok":
            self._analysis = result
            self.status.setText(
                f"Prévalidation réussie — {result['host_count']} hôte(s), "
                f"{result['play_count']} play(s), {result['task_count']} tâche(s). "
                f"SHA-256 playbook {result['playbook_sha256'][:12]}… / "
                f"inventaire {result['inventory_sha256'][:12]}… — hors ligne."
            )
            for module, count in result["module_counts"].items():
                QTreeWidgetItem(self.summary, [module, str(count)])
        elif mode == "analyze":
            code = result.get("code", "ansible_preflight_failed") if isinstance(result, dict) else "ansible_preflight_failed"
            self.status.setText(f"Prévalidation refusée — {code}. Aucune connexion réseau effectuée.")
            self._analysis = None
        else:
            state_labels = {
                "check_succeeded": "Check mode terminé (succès du contrôleur, sans sortie conservée).",
                "check_failed": "Check mode refusé ou en échec ; détail distant non conservé.",
                "timeout": "Délai maximal atteint ; processus arrêté.",
                "cancelled": "Check mode annulé ; sortie distante non conservée.",
                "unavailable": "Contrôleur Ansible ou transport indisponible.",
                "error": "Check mode non exécuté ; contrôle de sécurité en échec.",
            }
            self.status.setText(state_labels.get(state, "Check mode non qualifié."))
            self.consent.blockSignals(True)
            self.consent.setChecked(False)
            self.consent.blockSignals(False)
            self._connection_fingerprints = None
        self._refresh_gate()

    def closeEvent(self, event):
        self._closed = True
        self._generation += 1
        if self._pending is not None:
            self._pending.cancel()
        self._analysis = None
        self._connection_fingerprints = None
        super().closeEvent(event)
