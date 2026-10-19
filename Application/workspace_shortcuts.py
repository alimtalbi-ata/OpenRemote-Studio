"""Primary keyboard shortcuts for the Windows workspace. No side effects.
Author: Abdelhalim Talbi.
"""
SHORTCUTS = (
    ("Ctrl+F", "focus_connection_search"),
    ("Ctrl+L", "focus_connection_search"),
    ("Ctrl+Shift+F", "clear_and_focus_connection_search"),
    ("Ctrl+E", "toggle_favorites_filter"),
    ("Ctrl+Return", "connect"),
    ("Ctrl+W", "close_current_tab"),
    ("Ctrl+Tab", "next_tab"),
    ("Ctrl+Shift+Tab", "previous_tab"),
    ("Ctrl+1", "show_home"),
    ("Ctrl+2", "show_session_overview"),
    ("Ctrl+3", "show_local_readiness"),
    ("Ctrl+4", "show_transfer_history"),
    ("Ctrl+Shift+S", "show_session_overview"),
    ("F1", "show_quick_guide"),
)

def workspace_shortcuts():
    return SHORTCUTS

def validate_shortcuts(shortcuts=SHORTCUTS):
    keys = [key.casefold() for key, _ in shortcuts]
    return len(keys) == len(set(keys)) and all(key and method.isidentifier() for key, method in shortcuts)
