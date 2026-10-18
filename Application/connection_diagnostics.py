"""Local-only, sanitized access readiness report. Author: Abdelhalim Talbi."""
import json
from datetime import datetime, timezone
from urllib.parse import urlsplit
from launch_plan import build_launch_plan

def safe_target(connection):
    target=connection.get('host','')
    if connection.get('protocol')=='WEB':
        from core import validate
        checked=validate(connection)
        url=checked['host'] if '://' in checked['host'] else 'https://'+checked['host']
        parts=urlsplit(url)
        if parts.query or parts.fragment:
            # Reports must never persist web query tokens.
            return parts.hostname or '[URL masquée]'
        return parts.hostname or '[URL masquée]'
    return target

def report(connection,route=None,which=None,platform=None):
    plan=build_launch_plan(connection,route,which=which,platform=platform)
    return {'schema':'openremote.access.v1','timestamp_utc':datetime.now(timezone.utc).isoformat(),
            'connection_name':connection.get('name',''),
            'protocol':connection['protocol'],'target':safe_target(connection),
            'route_mode':(route or {}).get('mode','direct'),
            'pam_required':bool((route or {}).get('vault_ref')),
            'local_ready':bool(plan['ready']),
            'issues':plan['issues'],'warnings':plan['warnings'],
            'note':'Précontrôle local uniquement : ni réseau, ni identité, ni coffre vérifiés.'}

def json_report(connection,route=None,which=None,platform=None):
    return json.dumps(report(connection,route,which,platform),ensure_ascii=False,indent=2)
