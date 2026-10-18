"""Reusable Qt connection inspector dock. Author: Abdelhalim Talbi."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget,QWidget,QVBoxLayout,QLabel,QPushButton
from inspector_action_layout import inspector_action_groups

def create_inspector_panel(parent, handlers):
    """Build a dock; handlers are existing main-window callbacks, not executed here."""
    dock=QDockWidget('Connexion sélectionnée',parent)
    dock.setObjectName('connection-inspector')
    dock.setAllowedAreas(Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
    panel=QWidget();layout=QVBoxLayout(panel)
    details=QLabel()
    details.setTextFormat(Qt.PlainText)
    details.setWordWrap(True)
    layout.addWidget(details)
    buttons=[]
    for section,actions in inspector_action_groups():
        heading=QLabel(section)
        heading.setObjectName('inspectorSectionHeading')
        layout.addWidget(heading)
        for title,method,description in actions:
            if method not in handlers or not callable(handlers[method]):
                raise ValueError('Missing inspector action handler: '+method)
            button=QPushButton(title)
            button.setToolTip(description)
            button.setAccessibleName(title+' · '+section)
            button.clicked.connect(handlers[method])
            button.setEnabled(False)
            layout.addWidget(button)
            buttons.append(button)
    layout.addStretch(1)
    dock.setWidget(panel)
    dock.setFeatures(QDockWidget.DockWidgetClosable|QDockWidget.DockWidgetMovable|QDockWidget.DockWidgetFloatable)
    return dock,details,buttons
