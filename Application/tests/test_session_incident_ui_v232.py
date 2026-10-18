from pathlib import Path

def test_incident_ui_wiring():
    src=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
    for key in ('sessionIncidentCenter','sessionIncidentSearch','navigate_session_incident','refresh_session_incidents','incident_index(rows'):
        assert key in src

def test_navigation_revalidates():
    src=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
    section=src.split('def navigate_session_incident(',1)[1].split('def refresh_guidance_panel(',1)[0]
    assert 'selected_session(self.external_sessions.snapshot(),identity,pid)' in section
    assert 'reconnect_overview_session(' not in section
