"""Declarative primary navigation; no network or credential side effects.
Author: Abdelhalim Talbi.
"""
PRIMARY_VIEWS = (
    ("Connexions", "show_home", "Ctrl+1"),
    ("Sessions", "show_session_overview", "Ctrl+2"),
    ("Diagnostics", "show_local_readiness", "Ctrl+3"),
    ("Transferts", "show_transfer_history", "Menu Outils"),
)

def primary_views():
    return PRIMARY_VIEWS

def resolve_view(label):
    for name, handler, shortcut in PRIMARY_VIEWS:
        if name == label:
            return handler
    raise ValueError("Unknown workspace view")
