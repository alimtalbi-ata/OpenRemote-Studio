import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from session_incident_center import incident_index,incident_counts,format_incident_index

def sample():
    return [{'connection_id':'a','name':'Serveur A','protocol':'ssh','status':'exited','exit_code':255},
            {'connection_id':'b','name':'Serveur B','protocol':'rdp','status':'unknown','exit_code':None},
            {'connection_id':'c','name':'Serveur C','protocol':'ssh','status':'running','exit_code':None}]

def test_filter_and_counts():
    cards=incident_index(sample());assert len(cards)==2
    assert incident_counts(cards)=={'total':2,'errors':1,'uncertain':1}

def test_search_and_navigation_guard():
    cards=incident_index(sample(),query='serveur a');assert len(cards)==1
    assert cards[0]['requires_revalidation'] and not cards[0]['can_reconnect']

def test_missing_identity_ignored():
    assert incident_index([{'status':'exited','exit_code':1}])==[]

def test_no_sensitive_remote_diagnosis():
    text=format_incident_index(incident_index(sample()))
    assert 'Serveur A' in text and 'Serveur B' in text

def test_success_excluded():
    assert incident_index([{'connection_id':'x','status':'exited','exit_code':0}])==[]
