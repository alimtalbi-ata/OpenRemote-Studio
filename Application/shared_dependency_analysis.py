"""Conservative offline grouping of locally observed failures by shared access hop.
No remote outage inference, no hostnames or PAM references in output.
Author: Abdelhalim Talbi.
"""
from collections import defaultdict
from gateways import validate_route

def compare_dependencies(connections, routes, dashboard):
    if not isinstance(connections,(list,tuple)) or not isinstance(routes,dict) or not isinstance(dashboard,dict):
        raise ValueError('invalid inputs')
    if len(connections)>10000 or len(routes)>10000 or not isinstance(dashboard.get('rows'),list):
        raise ValueError('invalid comparison size')
    observations={r['id']:r for r in dashboard['rows'] if isinstance(r,dict) and isinstance(r.get('id'),str)}
    groups=defaultdict(list)
    skipped=0
    for connection in connections:
        if not isinstance(connection,dict) or not isinstance(connection.get('id'),str):continue
        identity=connection['id']
        if identity not in observations:continue
        try:
            route=validate_route(routes.get(identity,{}))
        except ValueError:
            skipped+=1
            continue
        mode=route['mode']
        if mode=='ssh_jump':
            # Full chain identity: do not conflate different routes that merely share a name.
            key=('ssh_jump',route['jump_host'].casefold(),route['jump_port'],route['jump_chain'].casefold())
            category='Bastion SSH / chaîne de rebonds'
        elif mode in ('rd_gateway','rds_collection'):
            key=('rd_gateway',route['gateway_host'].casefold(),route['gateway_port'])
            category='Passerelle RDP'
        else:continue
        row=observations[identity]
        failures=row.get('local_errors_30m',0)
        if type(failures) is not int or failures<0:continue
        groups[key].append((identity,failures))
    output=[]
    for key,members in groups.items():
        if len(members)<2:continue
        affected=[identity for identity,count in members if count>0]
        output.append({'dependency_type':'Bastion SSH / chaîne de rebonds' if key[0]=='ssh_jump' else 'Passerelle RDP',
                       'connections':len(members),'affected_connections':len(affected),
                       'local_errors_30m':sum(count for _,count in members),
                       'connection_ids':sorted(identity for identity,_ in members),
                       'shared_remote_cause_confirmed':False})
    output.sort(key=lambda g:(-g['affected_connections'],-g['local_errors_30m'],g['dependency_type'],g['connection_ids']))
    return {'schema':'openremote.shared_dependency.v1','scope':'local_only','remote_cause_confirmed':False,
            'skipped_invalid_routes':skipped,'groups':output}
