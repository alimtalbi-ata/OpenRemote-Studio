"""R114 Qt panel for explicit, asynchronous, read-only Grafana discovery.

Offline by default. Consent is revoked on target/query edits, tab hide, close, or
explicit cancellation. Results are local projections; links are rebuilt from
the validated origin and UID. Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import os
import re
import unicodedata
from threading import Event

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QTreeWidget, QTreeWidgetItem,
)

from grafana_readonly import GrafanaError, GrafanaReadOnly, dashboard_link, MAX_DASHBOARDS

_CONTROL_CATEGORIES = frozenset(("Cc", "Cf", "Cs", "Zl", "Zp"))


def _visible(value, maximum):
    if not isinstance(value, str):
        return ""
    result = []
    for char in value:
        codepoint = ord(char)
        if (unicodedata.category(char) not in _CONTROL_CATEGORIES
                and not (0xFDD0 <= codepoint <= 0xFDEF)
                and (codepoint & 0xFFFE) != 0xFFFE):
            result.append(char)
    return "".join(result).strip()[:maximum]


class _Signals(QObject):
    finished = Signal(int, object)


class _Fetch(QRunnable):
    """One user-triggered GET. A late worker cannot publish after cancellation."""
    def __init__(self, generation, origin, query, token_provider, client_factory, timeout=5):
        super().__init__()
        self.generation = generation
        self.origin = origin
        self.query = query
        self.token_provider = token_provider
        self.client_factory = client_factory
        self.timeout = timeout
        self.signals = _Signals()
        self._cancelled = Event()

    def cancel(self):
        self._cancelled.set()

    def run(self):
        result = {"state": "cancelled", "read_only": True, "dashboards": []}
        token = ""
        client = None
        try:
            if self._cancelled.is_set():
                raise GrafanaError("grafana_request_cancelled")
            # Validate the target before reading a credential from the provider.
            client = self.client_factory(self.origin, timeout=self.timeout,
                                         max_dashboards=MAX_DASHBOARDS)
            if self._cancelled.is_set():
                raise GrafanaError("grafana_request_cancelled")
            token = self.token_provider()
            if self._cancelled.is_set():
                raise GrafanaError("grafana_request_cancelled")
            snapshot = client.dashboards(
                online=True, token=token, query=self.query,
                cancelled=self._cancelled.is_set,
            )
            if self._cancelled.is_set():
                raise GrafanaError("grafana_request_cancelled")
            if (not isinstance(snapshot, dict) or snapshot.get("state") != "ok"
                    or snapshot.get("read_only") is not True
                    or not isinstance(snapshot.get("dashboards"), list)):
                raise GrafanaError("grafana_invalid_response")
            result = snapshot
        except GrafanaError as exc:
            code = str(exc)
            if not re.fullmatch(r"grafana_[a-z_]+", code):
                code = "grafana_unavailable"
            result = {"state": "cancelled" if code == "grafana_request_cancelled" else "error",
                      "read_only": True, "code": code, "dashboards": []}
        except Exception:
            # External transports can embed tokens or headers in exception text.
            result = {"state": "error", "read_only": True,
                      "code": "grafana_unavailable", "dashboards": []}
        finally:
            token = ""
            self.token_provider = lambda: ""
            self.query = ""
            if client is not None and hasattr(client, "clear_sensitive_state"):
                try:
                    client.clear_sensitive_state()
                except Exception:
                    pass
        if self._cancelled.is_set():
            result = {"state": "cancelled", "read_only": True, "dashboards": []}
        self.signals.finished.emit(self.generation, result)


class GrafanaDashboardsPanel(QWidget):
    """Manual dashboard discovery with credential and stale-result fencing."""
    def __init__(self, parent=None, *, client_factory=GrafanaReadOnly,
                 token_provider=None, pool=None, url_opener=None):
        super().__init__(parent)
        self.setObjectName("grafanaDashboardsPanel")
        self._client_factory = client_factory
        self._token_provider = token_provider or (
            lambda: os.environ.get("OPENREMOTE_GRAFANA_TOKEN", "")
        )
        self._pool = pool or QThreadPool.globalInstance()
        self._url_opener = url_opener or QDesktopServices.openUrl
        self._pending = None
        self._generation = 0
        self._closed = False

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Grafana — découverte de tableaux de bord, lecture seule. "
            "Aucun dashboard n'est modifié."
        ))
        form = QHBoxLayout()
        layout.addLayout(form)
        self.origin = QLineEdit()
        self.origin.setObjectName("grafanaOrigin")
        self.origin.setPlaceholderText(
            "https://grafana.example.internal (origine HTTPS uniquement)"
        )
        form.addWidget(self.origin, 2)
        self.query = QLineEdit()
        self.query.setObjectName("grafanaDashboardSearch")
        self.query.setMaxLength(120)
        self.query.setPlaceholderText("Rechercher un tableau de bord (facultatif)")
        form.addWidget(self.query, 1)

        self.consent = QCheckBox("Autoriser une lecture API HTTPS (GET /api/search)")
        self.consent.setObjectName("grafanaOnlineConsent")
        layout.addWidget(self.consent)
        controls = QHBoxLayout()
        layout.addLayout(controls)
        self.refresh_button = QPushButton("Charger les tableaux de bord")
        self.refresh_button.setObjectName("grafanaRefresh")
        self.refresh_button.clicked.connect(self.refresh)
        controls.addWidget(self.refresh_button)
        self.cancel_button = QPushButton("Annuler")
        self.cancel_button.setObjectName("grafanaCancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_request)
        controls.addWidget(self.cancel_button)
        self.open_button = QPushButton("Ouvrir le tableau sélectionné")
        self.open_button.setObjectName("grafanaOpenDashboard")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_selected)
        controls.addWidget(self.open_button)

        self.status = QLabel("Hors ligne — aucune requête envoyée, aucun jeton lu.")
        self.status.setObjectName("grafanaStatus")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.table = QTreeWidget()
        self.table.setObjectName("grafanaDashboardRows")
        self.table.setHeaderLabels(["Tableau de bord", "Dossier", "Tags"])
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.itemDoubleClicked.connect(lambda *_: self.open_selected())
        layout.addWidget(self.table)
        layout.addWidget(QLabel(
            "Lecture seule : seule la liste des dashboards est lue. "
            "Le jeton reste dans l'en-tête Bearer, jamais dans l'URL ou l'export. "
            "L'ouverture d'un lien est toujours déclenchée par l'opérateur."
        ))
        self.origin.textChanged.connect(self._configuration_changed)
        self.query.textChanged.connect(self._configuration_changed)
        self.consent.toggled.connect(self._invalidate)

    def _selection_changed(self):
        self.open_button.setEnabled(
            not self._closed and self.consent.isChecked()
            and self.table.currentItem() is not None
        )

    def _invalidate(self, *_):
        self._generation += 1
        if self._pending is not None:
            self._pending.cancel()
        self._pending = None
        self.table.clear()
        self.refresh_button.setEnabled(not self._closed)
        self.cancel_button.setEnabled(False)
        self.open_button.setEnabled(False)
        if self.consent.isChecked() and not self._closed:
            self.status.setText("Consentement actif — lancer une lecture explicitement.")
        else:
            self.status.setText("Hors ligne — aucune requête autorisée, aucune donnée conservée.")

    def _configuration_changed(self, *_):
        was_consented = self.consent.isChecked()
        if was_consented:
            self.consent.blockSignals(True)
            self.consent.setChecked(False)
            self.consent.blockSignals(False)
        self._invalidate()
        if was_consented:
            self.status.setText(
                "Cible ou recherche modifiée — consentement révoqué, données effacées."
            )

    def _revoke(self, message):
        self.consent.blockSignals(True)
        self.consent.setChecked(False)
        self.consent.blockSignals(False)
        self._invalidate()
        self.status.setText(message)

    def refresh(self):
        if self._closed or self._pending is not None:
            return
        self.table.clear()
        self.open_button.setEnabled(False)
        if not self.consent.isChecked():
            self.status.setText("Hors ligne — autoriser explicitement la lecture API pour continuer.")
            return
        self._generation += 1
        generation = self._generation
        self.refresh_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.setText("Chargement des dashboards Grafana (lecture seule)…")
        self._pending = _Fetch(
            generation, self.origin.text(), self.query.text(),
            self._token_provider, self._client_factory,
        )
        self._pending.signals.finished.connect(self._render_result)
        self._pool.start(self._pending)

    def cancel_request(self):
        if self._pending is None:
            return
        self._generation += 1
        self._pending.cancel()
        self._pending = None
        self.table.clear()
        self.open_button.setEnabled(False)
        self.refresh_button.setEnabled(not self._closed)
        self.cancel_button.setEnabled(False)
        self.status.setText("Requête annulée — résultat supprimé, aucune nouvelle requête lancée.")

    def _render_result(self, generation, result):
        if (generation != self._generation or self._closed
                or not self.consent.isChecked()):
            return
        self._pending = None
        self.refresh_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self._render(result)

    def _render(self, result):
        self.table.clear()
        self.open_button.setEnabled(False)
        if not isinstance(result, dict) or result.get("read_only") is not True:
            self.status.setText("Échec explicite : grafana_invalid_response")
            return
        state = result.get("state")
        if state == "cancelled":
            self.status.setText("Requête annulée — aucune donnée affichée.")
            return
        if state == "error":
            code = result.get("code", "")
            if not isinstance(code, str) or not re.fullmatch(r"grafana_[a-z_]+", code):
                code = "grafana_unavailable"
            self.status.setText("Échec explicite : " + code)
            return
        if state != "ok":
            self.status.setText("Échec explicite : grafana_invalid_response")
            return
        rows = result.get("dashboards")
        if not isinstance(rows, list) or len(rows) > MAX_DASHBOARDS:
            self.status.setText("Échec explicite : grafana_invalid_response")
            return
        seen = set()
        safe_rows = []
        try:
            for row in rows:
                if not isinstance(row, dict):
                    raise GrafanaError("grafana_invalid_dashboard")
                uid = row.get("uid")
                title = _visible(row.get("title"), 200)
                folder = _visible(row.get("folder", ""), 120)
                tags = row.get("tags", [])
                if (not isinstance(uid, str) or not isinstance(tags, list)
                        or len(tags) > 20 or not title or uid in seen):
                    raise GrafanaError("grafana_invalid_dashboard")
                # Never trust an injected/server-supplied URL: rebuild from origin + UID.
                link = dashboard_link(self.origin.text(), uid, title)
                safe_tags = []
                for tag in tags:
                    value = _visible(tag, 80)
                    if not isinstance(tag, str) or not value:
                        raise GrafanaError("grafana_invalid_dashboard")
                    if value not in safe_tags:
                        safe_tags.append(value)
                seen.add(uid)
                safe_rows.append((uid, title, folder, safe_tags, link))
        except GrafanaError:
            self.status.setText("Échec explicite : grafana_invalid_dashboard")
            return
        for uid, title, folder, tags, link in safe_rows:
            item = QTreeWidgetItem([title, folder, ", ".join(tags)])
            item.setData(0, Qt.UserRole, uid)
            item.setToolTip(0, link)
            self.table.addTopLevelItem(item)
        self.table.resizeColumnToContents(0)
        self.status.setText(
            "Lecture seule · {} dashboard(s) listé(s). "
            "La recherche locale n'émet aucune requête supplémentaire.".format(len(safe_rows))
        )

    def open_selected(self):
        item = self.table.currentItem()
        if self._closed or item is None or not self.consent.isChecked():
            return
        try:
            # Rebuild once more at click time so a stale/arbitrary URL cannot be opened.
            link = dashboard_link(self.origin.text(), item.data(0, Qt.UserRole), item.text(0))
        except GrafanaError:
            self.status.setText("Ouverture refusée : grafana_invalid_dashboard")
            return
        if QUrl(link).scheme() != "https":
            self.status.setText("Ouverture refusée : grafana_invalid_https_origin")
            return
        try:
            self._url_opener(QUrl(link))
        except Exception:
            self.status.setText("Ouverture impossible : grafana_link_open_failed")

    def hideEvent(self, event):
        if not self._closed:
            self._revoke("Panneau masqué — consentement révoqué et données effacées.")
        super().hideEvent(event)

    def closeEvent(self, event):
        self._closed = True
        self._revoke("Panneau fermé — consentement révoqué et données effacées.")
        self.refresh_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.open_button.setEnabled(False)
        super().closeEvent(event)
