"""Explicit, asynchronous, read-only NetBox comparison tab for Qt.

Author: Abdelhalim Talbi. No background polling, no writes, no token display.
"""
import os
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QCheckBox, QComboBox, QTreeWidget, QTreeWidgetItem)
from netbox_readonly import NetBoxError, NetBoxReadOnly
from netbox_preview import NetBoxPreviewError, compare_inventory
from netbox_preview_filter import NetBoxFilterError, filter_preview


class _Signals(QObject):
    finished = Signal(object)


class _Fetch(QRunnable):
    def __init__(self, origin, token, connections, client_factory):
        super().__init__()
        self.origin, self.token = origin, token
        self.connections = connections
        self.client_factory = client_factory
        self.signals = _Signals()

    def run(self):
        try:
            snapshot = self.client_factory(self.origin, self.token).devices(online=True)
            result = compare_inventory(snapshot, self.connections)
        except (NetBoxError, NetBoxPreviewError) as exc:
            result = {'state': 'error', 'code': str(exc)}
        except Exception:
            # A raw network/transport exception may include credentials.
            result = {'state': 'error', 'code': 'netbox_network_unavailable'}
        finally:
            self.token = ''
        self.signals.finished.emit(result)


class NetBoxPreviewPanel(QWidget):
    """Safe operator-initiated preview. No import/export or automatic sync."""
    def __init__(self, connections, parent=None, *, client_factory=NetBoxReadOnly):
        super().__init__(parent)
        self.setObjectName('netboxPreviewPanel')
        self._connections = [{'host': item.get('host'), 'protocol': item.get('protocol')}
                             for item in connections if isinstance(item, dict)]
        self._client_factory = client_factory
        self._pending = None
        self._preview = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('NetBox IPAM/DCIM — prévisualisation sans modification des connexions'))
        form = QHBoxLayout(); layout.addLayout(form)
        self.origin = QLineEdit()
        self.origin.setObjectName('netboxOrigin')
        self.origin.setPlaceholderText('https://netbox.example.internal (origine HTTPS uniquement)')
        form.addWidget(self.origin)
        self.online = QCheckBox('Autoriser une lecture réseau explicite (GET)')
        self.online.setObjectName('netboxOnlineConsent')
        layout.addWidget(self.online)
        self.refresh_button = QPushButton('Comparer maintenant')
        self.refresh_button.setObjectName('netboxPreviewRefresh')
        self.refresh_button.clicked.connect(self.refresh)
        layout.addWidget(self.refresh_button)
        self.status = QLabel('Hors ligne — aucune requête envoyée.')
        self.status.setObjectName('netboxPreviewStatus')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        filters = QHBoxLayout()
        layout.addLayout(filters)
        self.status_filter = QComboBox()
        self.status_filter.setObjectName('netboxStatusFilter')
        for label, code in (('Tous les états', 'all'), ('Correspondants', 'matched'),
                            ('Absents localement', 'missing_local'), ('Ambigus', 'ambiguous'),
                            ('Locaux seuls', 'local_only')):
            self.status_filter.addItem(label, code)
        filters.addWidget(self.status_filter)
        self.search_filter = QLineEdit()
        self.search_filter.setObjectName('netboxSearchFilter')
        self.search_filter.setMaxLength(120)
        self.search_filter.setPlaceholderText('Rechercher un équipement ou hôte local (filtre local)')
        filters.addWidget(self.search_filter)
        self.status_filter.currentIndexChanged.connect(lambda *_: self._apply_filter())
        self.search_filter.textChanged.connect(lambda *_: self._apply_filter())
        self.table = QTreeWidget()
        self.table.setObjectName('netboxPreviewRows')
        self.table.setHeaderLabels(['État', 'Équipement NetBox', 'Hôte local'])
        layout.addWidget(self.table)
        layout.addWidget(QLabel('Lecture seule. Les correspondances ambiguës exigent une revue humaine. '
                                'Aucun secret, import, modification, tunnel ou session déclenchés.'))

    def refresh(self):
        if self._pending is not None:
            return
        self.table.clear()
        self._preview = None
        if not self.online.isChecked():
            self._render(compare_inventory({'state': 'offline'}, self._connections))
            return
        self.refresh_button.setEnabled(False)
        self.status.setText('Chargement NetBox (lecture seule)…')
        self._pending = _Fetch(self.origin.text(), os.environ.get('OPENREMOTE_NETBOX_TOKEN', ''),
                               list(self._connections), self._client_factory)
        self._pending.signals.finished.connect(self._render)
        QThreadPool.globalInstance().start(self._pending)

    def _render(self, result):
        self._pending = None
        self.refresh_button.setEnabled(True)
        self.table.clear()
        self._preview = None
        if result['state'] == 'offline':
            self.status.setText('Hors ligne — aucune requête envoyée.')
        elif result['state'] == 'error':
            self.status.setText('Échec explicite : ' + result['code'])
        else:
            self._preview = result
            self._apply_filter()

    def _apply_filter(self):
        # Filtering a cached snapshot never performs another HTTPS GET.
        if self._preview is None:
            return
        try:
            filtered = filter_preview(self._preview,
                                      status=self.status_filter.currentData(),
                                      search=self.search_filter.text())
        except NetBoxFilterError as exc:
            self.table.clear()
            self.status.setText('Filtre refusé : ' + str(exc))
            return
        self.table.clear()
        for row in filtered['rows']:
            QTreeWidgetItem(self.table, [row['status'], row['device'], row['local_host']])
        counts = self._preview['counts']
        self.status.setText(
            'Lecture seule · correspondances : {matched} · absents localement : '
            '{missing_local} · ambigus : {ambiguous} · locaux seuls : {local_only}'.format(**counts)
            + ' · visibles : {}/{}'.format(filtered['visible'], filtered['total']))
        self.table.resizeColumnToContents(0)
