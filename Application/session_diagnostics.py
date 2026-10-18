"""Non-invasive, local-only session failure diagnostics. Author: Abdelhalim Talbi."""
from collections import defaultdict

HINTS={
    'SSH': 'Vérifier DNS, port 22, accès réseau, clés SSH, known_hosts et règles de bastion.',
    'SFTP': 'Vérifier la négociation SSH, les droits sur le chemin distant et les quotas.',
    'RDP': 'Vérifier DNS, port 3389, RD Gateway, droits RDS et journaux Windows.',
    'VNC': 'Vérifier le serveur VNC, son port, son pare-feu et sa configuration TLS.',
}
def analyze_sessions(rows,minimum_failures=2):
    if not isinstance(minimum_failures,int) or minimum_failures<2:
        raise ValueError('Seuil de répétition invalide')
    grouped=defaultdict(list)
    for row in rows:
        if not isinstance(row,dict):continue
        identity=row.get('connection_id')
        if not isinstance(identity,str) or not identity:continue
        grouped[identity].append(row)
    result=[]
    for identity,events in grouped.items():
        failures=[r for r in events if r.get('status')=='exited' and type(r.get('exit_code')) is int and r['exit_code']!=0]
        successes=sum(r.get('status')=='exited' and r.get('exit_code')==0 for r in events)
        active=sum(r.get('status')=='running' for r in events)
        protocol=str(events[-1].get('protocol','')).upper()
        result.append({'connection_id':identity,'name':str(events[-1].get('name','')),
                       'protocol':protocol,'attempts':len(events),'failures':len(failures),
                       'successes':successes,'active_processes':active,
                       'repeated_failure':len(failures)>=minimum_failures,
                       'last_exit_code':failures[-1]['exit_code'] if failures else None,
                       'hint':HINTS.get(protocol,'Examiner les journaux du client externe et la connectivité.') if failures else ''})
    return sorted(result,key=lambda r:(-int(r['repeated_failure']),-r['failures'],r['name'].casefold()))

def summarize_diagnostics(rows):
    data=analyze_sessions(rows)
    return {'connections':len(data),'repeated_failures':sum(x['repeated_failure'] for x in data),
            'failed_attempts':sum(x['failures'] for x in data),'items':data}


def format_session_diagnostic(report):
    """Render a safe, copyable summary from local process exit metadata only."""
    lines = [f"Connexions suivies : {report['connections']}",
             f"Tentatives en erreur : {report['failed_attempts']}",
             f"Connexions avec erreurs répétées : {report['repeated_failures']}", '']
    for item in report['items']:
        if not item['failures']:
            continue
        label = 'ÉCHECS RÉPÉTÉS' if item['repeated_failure'] else 'Échec isolé'
        lines.extend([f"{item['name']} ({item['protocol']}) — {label}",
                      f"Échecs : {item['failures']} / {item['attempts']} lancement(s) · dernier code : {item['last_exit_code']}",
                      item['hint'], ''])
    if not report['failed_attempts']:
        lines.append('Aucun processus terminé en erreur dans le suivi local.')
    return '\n'.join(lines)


# V22.7: deterministic guidance derived only from local process metadata.
# Never claim a network or authentication root cause from an exit code alone.
GUIDANCE_V227 = {
    'SSH': ('Verifier la resolution DNS et le port SSH.', 'Examiner la cle, known_hosts et les politiques du bastion.'),
    'SFTP': ('Verifier le transport SSH.', 'Verifier les droits et quotas du chemin distant.'),
    'RDP': ('Verifier la connectivite au port RDP ou a la passerelle.', 'Consulter les journaux RDS et les droits utilisateur.'),
    'VNC': ('Verifier le service VNC et son port.', 'Verifier les parametres TLS et pare-feu.'),
}

def explain_session_failure(row):
    """Explain a locally observed failure; never infer the remote root cause."""
    if not isinstance(row, dict):
        raise TypeError('Une session doit etre un dictionnaire')
    status = row.get('status')
    code = row.get('exit_code')
    protocol = str(row.get('protocol') or '').upper()
    if status == 'running':
        return {'code':'SESSION_RUNNING','severity':'info','summary':'Processus local actif',
                'probable_causes':[], 'actions':[], 'safe_to_retry':False}
    if status == 'unknown':
        return {'code':'SESSION_UNVERIFIED','severity':'warning','summary':'Etat du processus non confirme',
                'probable_causes':['Identite du processus indisponible ou ambigue'],
                'actions':['Actualiser les sessions et verifier l identite avant toute action'], 'safe_to_retry':False}
    if status == 'exited' and type(code) is int and code == 0:
        return {'code':'SESSION_EXIT_OK','severity':'info','summary':'Processus termine sans erreur signalee',
                'probable_causes':[], 'actions':[], 'safe_to_retry':False}
    if status != 'exited' or type(code) is not int:
        return {'code':'SESSION_INCOMPLETE','severity':'warning','summary':'Diagnostic incomplet',
                'probable_causes':['Code de sortie indisponible'],
                'actions':['Actualiser les sessions et consulter les journaux du client'], 'safe_to_retry':False}
    actions=list(GUIDANCE_V227.get(protocol,('Consulter les journaux du client externe.',)))
    return {'code':'LOCAL_PROCESS_EXIT_NONZERO','severity':'error',
            'summary':f'Le client {protocol or "externe"} a quitte avec le code {code}',
            'probable_causes':['Cause distante indeterminee : le code de sortie seul ne suffit pas'],
            'actions':actions, 'safe_to_retry':False}

def format_guided_diagnostic(row):
    report=explain_session_failure(row)
    return '\n'.join([f"{report['code']} - {report['summary']}",
       'Causes possibles : '+('; '.join(report['probable_causes']) or 'Aucune erreur confirmee'),
       'Verifications : '+('; '.join(report['actions']) or 'Aucune')])
