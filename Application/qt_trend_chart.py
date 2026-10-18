"""Qt stacked histogram for local incident observations only.
Author: Abdelhalim Talbi.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget
from trend_chart_data import chart_data, stacked_heights

class LocalTrendChart(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self._data=None
        self.setMinimumHeight(140)
        self.setAccessibleName('Histogramme des échecs locaux par période')
        self.setToolTip('Bleu : TCP ; orange : SSH ; gris : client. Observations locales uniquement.')

    def set_report(self,report):
        self._data=chart_data(report)
        self.update()

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing,False)
        painter.fillRect(self.rect(),self.palette().base())
        data=self._data
        if not data: return
        margin=12
        width=max(1,self.width()-2*margin)
        height=max(1,self.height()-2*margin)
        painter.setPen(self.palette().mid().color())
        painter.drawLine(margin,margin+height,margin+width,margin+height)
        palette=(QColor('#3b82f6'),QColor('#f59e0b'),QColor('#64748b'))
        n=len(data['series'])
        for i,point in enumerate(data['series']):
            x0=margin+i*width//n
            x1=margin+(i+1)*width//n
            bar_width=max(1,x1-x0-1)
            y=margin+height
            for color,part_height in zip(palette,stacked_heights(point,data['maximum'],height)):
                if part_height:
                    y-=part_height
                    painter.fillRect(x0,y,bar_width,part_height,color)
        painter.end()
