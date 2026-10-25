"""R109: opt-in, asynchronous Zabbix problem triage panel.

No token is read until online consent is enabled and the HTTPS origin validates.
The panel never acknowledges/updates problems and never starts sessions itself.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
import unicodedata
from threading import Event

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QComboBox, QTreeWidget, QTreeWidgetItem,
)

from zabbix_readonly import ZabbixError, ZabbixReadOnly


class _Signals(QObject):
    finished = Signal(int, object)


def _visible(value, maximum=160):
    """Make plain UI labels from local profile text without reading credentials."""
    if not isinstance(value, str):
        return ""
    result = []
    for char in value:
        category = unicodedata.category(char)
        if category not in ("Cc", "Cf", "Cs", "Zl", "Zp") and not (
            0xFDD0 <= ord(char) <= 0xFDEF or (ord(char) & 0xFFFE) == 0xFFFE
        ):
            result.append(char)
    return "".join(result).strip()[:maximum]


def _host_key(value):
    value = _visible(value, 255).strip().rstrip(".")
    if not value or any(char in value for char in "/@?#\\"):
        return ""
    return value.casefold()


def _format_clock(timestamp):
    try:
        return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except (OverflowError, OSError, ValueError):
        return "Heure inconnue"


def _local_candidates(problem, connections):
    remote_keys = set()
    for host in problem.get("hosts", []):
        if isinstance(host, dict):
            for field in ("host", "name"):
                key = _host_key(host.get(field, ""))
                if key:
                    remote_keys.add(key)
    candidates = []
    for item in connections:
        if not isinstance(item, dict):
            continue
        if _host_key(item.get("host", "")) not in remote_keys:
            continue
        name = _visible(item.get("name", "Connexion locale"), 96) or "Connexion locale"
        protocol = _visible(item.get("protocol", ""), 16)
        candidates.append((name, protocol))
    return list(dict.fromkeys(candidates))[:12]


class _Fetch(QRunnable):
    """One bounded request sequence; a cancelled in-flight read remains timeout-bounded."""
    def __init__(self, generation, origin, connections, limit, client_factory,
                 token_provider, timeout=5):
        super().__init__()
        self.generation = generation
        self.origin = origin
        self.connections = connections
        self.limit = limit
        self.client_factory = client_factory
        self.token_provider = token_provider
        self.timeout = timeout
        self.signals = _Signals()
        self._cancelled = Event()

    def cancel(self):
        self._cancelled.set()

    def run(self):
        token = ""
        result = {"state": "cancelled", "problems": []}
        try:
            if self._cancelled.is_set():
                raise ZabbixError("zabbix_request_cancelled")
            # Constructor validates the HTTPS origin before credentials are read.
            client = self.client_factory(self.origin, timeout=self.timeout, max_problems=self.limit)
            if self._cancelled.is_set():
                raise ZabbixError("zabbix_request_cancelled")
            token = self.token_provider()
            if self._cancelled.is_set():
                raise ZabbixError("zabbix_request_cancelled")
            snapshot = client.problems(online=True, token=token, limit=self.limit,
                                      cancelled=self._cancelled.is_set)
            if self._cancelled.is_set():
                raise ZabbixError("zabbix_request_cancelled")
            if not isinstance(snapshot, dict) or snapshot.get("state") != "ok" or snapshot.get("read_only") is not True:
                raise ZabbixError("zabbix_invalid_response")
            raw_problems = snapshot.get("problems")
            if not isinstance(raw_problems, list) or len(raw_problems) > self.limit:
                raise ZabbixError("zabbix_invalid_response")
            rows = []
            for item in raw_problems:
                if not isinstance(item, dict):
                    raise ZabbixError("zabbix_invalid_response")
                severity = item.get("severity")
                if type(severity) is not int or not 0 <= severity <= 5:
                    raise ZabbixError("zabbix_invalid_response")
                name = _visible(item.get("name", ""), 512)
                label = _visible(item.get("severity_label", ""), 32)
                if not name or not label:
                    raise ZabbixError("zabbix_invalid_response")
                hosts = item.get("hosts", [])
                if not isinstance(hosts, list) or len(hosts) > 32:
                    raise ZabbixError("zabbix_invalid_response")
                safe_hosts = []
                for host in hosts:
                    if not isinstance(host, dict):
                        raise ZabbixError("zabbix_invalid_response")
                    safe_hosts.append({"host": _visible(host.get("host", ""), 255),
                                       "name": _visible(host.get("name", ""), 255)})
                safe_item = {
                    "event_id": _visible(item.get("event_id", ""), 32),
                    "name": name, "severity": severity, "severity_label": label,
                    "last_change": item.get("last_change"),
                    "acknowledged": item.get("acknowledged") is True,
                    "hosts": safe_hosts,
                    "trigger_description": _visible(item.get("trigger_description", ""), 512),
                }
                if type(safe_item["last_change"]) is not int or not 0 <= safe_item["last_change"] <= 4_102_444_800:
                    raise ZabbixError("zabbix_invalid_response")
                safe_item["local_candidates"] = _local_candidates(safe_item, self.connections)
                rows.append(safe_item)
            result = {"state": "ok", "read_only": True, "problems": rows,
                      "limit": snapshot.get("limit", self.limit),
                      "may_be_truncated": snapshot.get("may_be_truncated") is True}
        except ZabbixError as exc:
            result = {"state": "cancelled" if str(exc) == "zabbix_request_cancelled" else "error",
                      "read_only": True, "code": str(exc), "problems": []}
        except Exception:
            result = {"state": "error", "read_only": True,
                      "code": "zabbix_unavailable", "problems": []}
        finally:
            token = ""
            self.token_provider = lambda: ""
            self.connections = []
        if self._cancelled.is_set():
            result = {"state": "cancelled", "read_only": True, "problems": []}
        self.signals.finished.emit(self.generation, result)


class ZabbixAlertsPanel(QWidget):
    """Read-only active-problem triage, offline by default, with no write actions."""
    def __init__(self, connections, parent=None, *, client_factory=ZabbixReadOnly,
                 token_provider=None, pool=None):
        super().__init__(parent)
        self.setObjectName("zabbixAlertsPanel")
        self._connections = [
            {key: item.get(key) for key in ("name", "protocol", "host")}
            for item in connections if isinstance(item, dict)
        ]
        self._client_factory = client_factory
        self._token_provider = token_provider or (lambda: os.environ.get("OPENREMOTE_ZABBIX_TOKEN", ""))
        self._pool = pool or QThreadPool.globalInstance()
        self._pending = None
        self._generation = 0
        self._closed = False
        self._problems = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Zabbix — alertes actives et rapprochement local, lecture seule"))
        form = QHBoxLayout()
        layout.addLayout(form)
        self.origin = QLineEdit()
        self.origin.setObjectName("zabbixOrigin")
        self.origin.setPlaceholderText("https://zabbix.example.internal/zabbix (HTTPS uniquement)")
        form.addWidget(self.origin, 1)
        self.limit = QComboBox()
        self.limit.setObjectName("zabbixProblemLimit")
        for count in (10, 25, 50, 100):
            self.limit.addItem(str(count), count)
        self.limit.setCurrentIndex(2)
        form.addWidget(QLabel("Maximum"))
        form.addWidget(self.limit)
        self.consent = QCheckBox("Autoriser les lectures API HTTPS (problem.get / trigger.get)")
        self.consent.setObjectName("zabbixOnlineConsent")
        layout.addWidget(self.consent)
        controls = QHBoxLayout()
        layout.addLayout(controls)
        self.refresh_button = QPushButton("Actualiser les alertes")
        self.refresh_button.setObjectName("zabbixRefresh")
        self.refresh_button.clicked.connect(self.refresh)
        controls.addWidget(self.refresh_button)
        self.cancel_button = QPushButton("Annuler")
        self.cancel_button.setObjectName("zabbixCancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_request)
        controls.addWidget(self.cancel_button)
        self.status = QLabel("Hors ligne — aucune requête envoyée, aucun jeton lu.")
        self.status.setObjectName("zabbixStatus")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        filters = QHBoxLayout()
        layout.addLayout(filters)
        self.severity_filter = QComboBox()
        self.severity_filter.setObjectName("zabbixSeverityFilter")
        self.severity_filter.addItem("Toutes les sévérités", -1)
        for severity, label in enumerate(("Non classée", "Information", "Avertissement", "Moyenne", "Haute", "Désastre")):
            self.severity_filter.addItem(label, severity)
        filters.addWidget(self.severity_filter)
        self.search_filter = QLineEdit()
        self.search_filter.setObjectName("zabbixLocalSearch")
        self.search_filter.setMaxLength(120)
        self.search_filter.setClearButtonEnabled(True)
        self.search_filter.setPlaceholderText("Filtrer localement : problème, hôte ou profil local")
        filters.addWidget(self.search_filter, 1)
        self.table = QTreeWidget()
        self.table.setObjectName("zabbixProblemRows")
        self.table.setHeaderLabels(["Sévérité", "État", "Dernier changement (UTC)",
                                    "Hôte(s)", "Problème", "Profil(s) local(aux) candidat(s)"])
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)
        layout.addWidget(QLabel("Aucun acquittement, modification Zabbix ou ouverture de session n'est déclenchée. "
                                "Les correspondances locales sont indicatives et exigent une action opérateur séparée."))

        self.origin.textChanged.connect(self._origin_changed)
        self.consent.toggled.connect(self._invalidate)
        self.limit.currentIndexChanged.connect(self._invalidate)
        self.severity_filter.currentIndexChanged.connect(self._apply_filter)
        self.search_filter.textChanged.connect(self._apply_filter)

    def _origin_changed(self, *_):
        """A network approval is scoped to the exact origin the operator reviewed."""
        if self.consent.isChecked():
            # Toggling consent invokes _invalidate synchronously: cancel pending
            # work, clear old data and fence off any result from the previous origin.
            self.consent.setChecked(False)
            self.status.setText(
                "Origine HTTPS modifiée — consentement révoqué ; vérifier la cible puis autoriser de nouveau."
            )
            return
        self._invalidate()

    def _invalidate(self, *_):
        self._generation += 1
        if self._pending is not None:
            self._pending.cancel()
        self._pending = None
        self._problems = []
        self.table.clear()
        self.cancel_button.setEnabled(False)
        self.refresh_button.setEnabled(not self._closed)
        if not self.consent.isChecked():
            self.status.setText("Hors ligne — aucune nouvelle requête autorisée, aucun jeton lu.")
        else:
            self.status.setText("Paramètres modifiés — relancer explicitement la lecture.")

    def refresh(self):
        if self._closed or self._pending is not None:
            return
        self.table.clear()
        self._problems = []
        if not self.consent.isChecked():
            self.status.setText("Hors ligne — aucune requête envoyée, aucun jeton lu.")
            return
        self._generation += 1
        generation = self._generation
        self.refresh_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.setText("Lecture Zabbix en cours (GET JSON-RPC autorisés uniquement)…")
        worker = _Fetch(generation, self.origin.text(), list(self._connections),
                        self.limit.currentData(), self._client_factory,
                        self._token_provider, timeout=5)
        worker.signals.finished.connect(self._render_result)
        self._pending = worker
        self._pool.start(worker)

    def cancel_request(self):
        if self._pending is None:
            return
        self._pending.cancel()
        self.cancel_button.setEnabled(False)
        self.status.setText("Annulation demandée — une lecture HTTPS en cours reste bornée par le timeout.")

    def _render_result(self, generation, result):
        if generation != self._generation or self._closed or not self.consent.isChecked():
            return
        self._pending = None
        self.refresh_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self._render(result)

    def _render(self, result):
        self.table.clear()
        self._problems = []
        if result.get("state") == "offline":
            self.status.setText("Hors ligne — aucune requête envoyée, aucun jeton lu.")
            return
        if result.get("state") == "cancelled":
            self.status.setText("Lecture annulée — aucune donnée affichée.")
            return
        if result.get("state") == "error":
            self.status.setText("Échec explicite : " + _visible(result.get("code", "zabbix_unavailable"), 80))
            return
        problems = result.get("problems")
        if result.get("state") != "ok" or result.get("read_only") is not True or not isinstance(problems, list):
            self.status.setText("Échec explicite : zabbix_invalid_response")
            return
        self._problems = problems
        self._apply_filter()
        if not problems:
            self.status.setText("Aucune alerte active retournée par Zabbix.")
        elif result.get("may_be_truncated"):
            self.status.setText(f"Lecture seule · {len(problems)} alertes affichées · limite atteinte, résultat potentiellement tronqué.")
        else:
            self.status.setText(f"Lecture seule · {len(problems)} alertes actives retournées · aucune écriture effectuée.")

    def _apply_filter(self, *_):
        if not hasattr(self, "table"):
            return
        self.table.clear()
        severity = self.severity_filter.currentData()
        query = self.search_filter.text().strip().casefold()
        visible = 0
        severity_colors = {3: QColor("#8a5a00"), 4: QColor("#b3261e"), 5: QColor("#780000")}
        for problem in self._problems:
            if severity != -1 and problem["severity"] != severity:
                continue
            hosts = ", ".join(host.get("name") or host.get("host", "") for host in problem["hosts"])
            candidates = "; ".join(f"{name} [{protocol}]" if protocol else name
                                     for name, protocol in problem["local_candidates"])
            searchable = " ".join((problem["name"], hosts, candidates,
                                   problem["severity_label"])).casefold()
            if query and query not in searchable:
                continue
            row = QTreeWidgetItem([
                problem["severity_label"], "Acquittée" if problem["acknowledged"] else "À traiter",
                _format_clock(problem["last_change"]), hosts or "—", problem["name"], candidates or "—",
            ])
            row.setData(0, 32, problem["severity"])
            if problem["severity"] in severity_colors:
                row.setForeground(0, severity_colors[problem["severity"]])
            row.setToolTip(4, problem.get("trigger_description", ""))
            self.table.addTopLevelItem(row)
            visible += 1
        self.table.resizeColumnToContents(0)
        if self._problems:
            self.status.setText(f"Lecture seule · {len(self._problems)} alertes · {visible} visibles · filtres locaux sans nouvelle requête.")

    def hideEvent(self, event):
        if self._pending is not None:
            self._invalidate()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._closed = True
        self._invalidate()
        super().closeEvent(event)
