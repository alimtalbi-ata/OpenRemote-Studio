"""Safe per-hop SSH diagnostics without hostnames, credentials or exception bodies.
Author: Abdelhalim Talbi.
"""

STAGES = ('bastion_connect', 'bastion_transport', 'bastion_tunnel',
          'target_connect', 'target_transport', 'target_pty') + tuple(
              f'bastion_{i}_{stage}' for i in range(2,5) for stage in ('tunnel','connect','transport'))


def hop_status(stage, outcome):
    if stage not in STAGES:
        raise ValueError('Etape SSH inconnue')
    if outcome not in ('starting', 'ok', 'failed'):
        raise ValueError('Etat SSH inconnu')
    return f'SSH/{stage}: {outcome}'


def route_stages(route):
    mode = (route or {}).get('mode', '')
    if mode in ('', 'direct'):
        return STAGES[3:]
    if mode == 'ssh_jump':
        from gateways import parse_jump_chain
        extra=parse_jump_chain((route or {}).get('jump_chain',''))
        return STAGES[:3] + tuple(
            f'bastion_{i}_{stage}' for i in range(2,len(extra)+2)
            for stage in ('tunnel','connect','transport')) + STAGES[3:]
    raise ValueError('Route SSH non prise en charge')
