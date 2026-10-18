"""Unified accessible Qt visual theme; author Abdelhalim Talbi."""
MAIN_STYLESHEET = """
QMainWindow, QWidget { background-color: #111b2a; color: #edf3fa; font-family: 'Segoe UI'; font-size: 13px; }
QMenuBar, QMenu, QStatusBar { background-color: #17283b; color: #edf3fa; }
QMenu::item:selected { background-color: #285779; }
QTreeWidget, QListWidget, QTableWidget, QTextEdit, QPlainTextEdit, QLineEdit, QComboBox {
 background-color: #192a3d; color: #f2f7ff; border: 1px solid #496079; border-radius: 5px;
 selection-background-color: #326b9b; selection-color: white; padding: 5px; }
QTreeWidget::item, QListWidget::item { min-height: 25px; }
QTreeWidget::item:selected, QListWidget::item:selected { background-color: #326b9b; }
QPushButton { background-color: #234b6c; color: #ffffff; border: 1px solid #537d9c; border-radius: 6px; padding: 8px 12px; min-height: 21px; }
QPushButton:hover { background-color: #326a93; }
QPushButton:pressed { background-color: #153a5a; }
QPushButton:disabled { background-color: #283543; color: #9caebf; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus { border: 2px solid #8bc5fa; }
QTabWidget::pane { border: 1px solid #415873; background: #142235; }
QTabBar::tab { background: #213a54; color: #e8f2ff; padding: 10px 14px; border: 1px solid #3c5571; }
QTabBar::tab:selected { background: #326b9b; color: #ffffff; }
QDockWidget::title { background: #1d354d; padding: 9px; }
QHeaderView::section { background: #203b56; color: white; padding: 8px; border: 1px solid #47647e; }
QToolTip { background: #eff6ff; color: #142235; border: 1px solid #4b7ea4; padding: 6px; }
"""
