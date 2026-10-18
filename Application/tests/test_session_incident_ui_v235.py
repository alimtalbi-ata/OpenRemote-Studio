from pathlib import Path

def test_guidance_selection_present():
    s=(Path(__file__).parents[1]/'qt_app.py').read_text()
    assert 'def _focus_incident_guidance(self):' in s
    assert 'itemSelectionChanged.connect(self._focus_incident_guidance)' in s

def test_no_automatic_connection_in_selection_handler():
    s=(Path(__file__).parents[1]/'qt_app.py').read_text()
    fragment=s.split('def _focus_incident_guidance(self):',1)[1].split('def navigate_session_incident',1)[0]
    assert 'self.connect(' not in fragment
    assert 'reconnect(' not in fragment
