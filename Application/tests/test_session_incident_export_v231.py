import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from session_incident_center import incident_export

def test_export_no_secrets():
    x=incident_export([{'connection_id':'c1','protocol':'SSH','password':'secret','pid':123,'diagnostic':{'severity':'error','summary':'Connexion impossible','token':'secret'}}])
    assert x['count']==1 and 'secret' not in repr(x) and 'pid' not in repr(x)
    assert x['incidents'][0]['can_reconnect'] is False

def test_export_invalid():
    import pytest
    with pytest.raises(TypeError):incident_export(None)
