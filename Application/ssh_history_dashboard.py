"""Qt SSH diagnostic history dashboard. Author: Abdelhalim Talbi."""
import time
from ssh_latency_alerts import evaluate_dashboard
from ssh_latency_correlation import correlate
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QTableWidget,QTableWidgetItem,QWidget,QPushButton,QSpinBox

STEPS=('Bastion principal','Bastion 2','Bastion 3','Bastion 4','Serveur cible')

class LatencyPlot(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.values=[];self.setMinimumHeight(170)
    def set_series(self,series):
        self.values=[float(x['duration_ms']) for x in series if x.get('duration_ms') is not None];self.update()
    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(),QColor('#17212e'))
        painter.setPen(QColor('#b9c8d7'))
        if not self.values:
            painter.drawText(self.rect(),Qt.AlignCenter,'Aucune mesure disponible');return
        left,top,right,bottom=48,18,self.width()-16,self.height()-32
        if right<=left or bottom<=top:return
        peak=max(max(self.values),1)
        painter.drawText(4,top+10,f'{peak:g} ms');painter.drawText(4,bottom,'0')
        painter.setPen(QPen(QColor('#52c8ee'),2))
        points=[]
        for i,v in enumerate(self.values):
            x=left+(right-left)*(i/max(len(self.values)-1,1))
            y=bottom-(bottom-top)*v/peak
            points.append((round(x),round(y)))
        for a,b in zip(points,points[1:]):painter.drawLine(*a,*b)
        for x,y in points:painter.drawEllipse(x-2,y-2,4,4)

class HistoryDashboard(QDialog):
    def __init__(self,history,parent=None,route_id=None):
        super().__init__(parent);self.history=history;self.route_id=route_id
        self.setWindowTitle('Historique SSH — tableau de bord anonymisé');self.resize(840,600)
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('Historique du parcours pseudonymisé sélectionné.' if route_id else 'Mesures locales anonymisées : parcours mélangés (sélectionnez un parcours pour les isoler).'))
        filters=QHBoxLayout();layout.addLayout(filters)
        self.period=QComboBox();self.period.addItems(['7 jours','30 jours','90 jours','Tout']);filters.addWidget(self.period)
        self.status=QComboBox()
        for label,value in [('Tous les états',None),('Réussi','authenticated'),('Échec','failed'),('Annulé','cancelled')]:self.status.addItem(label,value)
        filters.addWidget(self.status)
        self.step=QComboBox();self.step.addItems(STEPS);filters.addWidget(self.step)
        refresh=QPushButton('Actualiser');filters.addWidget(refresh)
        limits=QHBoxLayout();layout.addLayout(limits)
        limits.addWidget(QLabel('Seuil de latence (ms) :'))
        self.latency_limit=QSpinBox();self.latency_limit.setRange(1,60000);self.latency_limit.setValue(500);limits.addWidget(self.latency_limit)
        limits.addWidget(QLabel('Ratio de dégradation (%) :'))
        self.ratio_limit=QSpinBox();self.ratio_limit.setRange(110,500);self.ratio_limit.setValue(150);limits.addWidget(self.ratio_limit)
        self.latency_limit.valueChanged.connect(self.refresh)
        self.ratio_limit.valueChanged.connect(self.refresh)
        self.summary=QLabel();layout.addWidget(self.summary)
        self.alert_summary=QLabel();layout.addWidget(self.alert_summary)
        self.correlation_summary=QLabel();self.correlation_summary.setWordWrap(True);layout.addWidget(self.correlation_summary)
        self.plot=LatencyPlot();layout.addWidget(self.plot)
        self.table=QTableWidget(0,7);self.table.setHorizontalHeaderLabels(['Étape','Passages','Échecs','Taux échec (%)','Moyenne (ms)','Médiane (ms)','P95 (ms)']);layout.addWidget(self.table)
        self.period.currentIndexChanged.connect(self.refresh)
        self.status.currentIndexChanged.connect(self.refresh)
        self.step.currentIndexChanged.connect(self.refresh)
        refresh.clicked.connect(self.refresh)
        self.refresh()
    def refresh(self,*_):
        days=(7,30,90,None)[self.period.currentIndex()]
        since=int(time.time())-days*86400 if days is not None else None
        try:data=self.history.statistics(since=since,status=self.status.currentData(),route_id=self.route_id)
        except Exception:
            self.summary.setText('Historique indisponible (base absente, verrouillée ou corrompue).')
            self.table.setRowCount(0);self.plot.set_series([]);self.alert_summary.setText('');self.correlation_summary.setText('');return
        self.summary.setText(f"{data['count']} diagnostics affichés (maximum 200) — historique non chiffré")
        self.plot.set_series(data['series'][self.step.currentText()])
        alerts=evaluate_dashboard(data,threshold_ms=self.latency_limit.value(),ratio=self.ratio_limit.value()/100)
        degraded=[name for name,item in alerts.items() if item['state']=='degraded']
        self.alert_summary.setText('Dégradation détectée : '+', '.join(degraded) if degraded else 'Aucune dégradation détectée sur les dernières mesures disponibles')
        self.alert_summary.setStyleSheet('color: #e88b76;' if degraded else '')
        signals=correlate(data,threshold_ms=self.latency_limit.value(),ratio=self.ratio_limit.value()/100)
        details=[]
        if signals['multi_step_degradation']:details.append('Plusieurs étapes dégradées simultanément dans les dernières mesures disponibles')
        if signals['recurrent_steps']:details.append('Dépassements récurrents : '+', '.join(signals['recurrent_steps']))
        self.correlation_summary.setText((' | '.join(details) if details else 'Aucune récurrence détectée')+(' — Corrélation limitée au parcours sélectionné.' if self.route_id else ' — Corrélation indicative : parcours non identifiés.'))
        self.table.setRowCount(len(data['steps']))
        for i,row in enumerate(data['steps']):
            for j,value in enumerate((row['step'],row['runs'],row['failures'],row['failure_rate_pct'],row['average_ms'],row['median_ms'],row['p95_ms'])):
                self.table.setItem(i,j,QTableWidgetItem('—' if value is None else str(value)))
        self.table.resizeColumnsToContents()
