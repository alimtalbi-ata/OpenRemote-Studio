"""Privacy-aware filtering of locally observed connection rows. Author: Abdelhalim Talbi."""
STATUSES = ('ALL', 'attention', 'observed', 'not_tested')
ALLOWED = ('ALL','SSH','RDP','VNC','SFTP','WEB','TELNET','LOCAL','OTHER')
def filtered_rows(report, names, protocol='ALL', query='', status='ALL'):
    if not isinstance(report,dict) or not isinstance(report.get('rows'),list) or not isinstance(names,dict):
        raise ValueError('invalid dashboard data')
    if protocol not in ALLOWED or status not in STATUSES or not isinstance(query,str) or len(query)>200:
        raise ValueError('invalid filter')
    term=query.casefold().strip()
    result=[]
    for item in report['rows']:
        if not isinstance(item,dict) or not isinstance(item.get('id'),str):continue
        proto=item.get('protocol','OTHER')
        if protocol!='ALL' and proto!=protocol:continue
        if status!='ALL' and item.get('status')!=status:continue
        name=str(names.get(item['id'],'Connexion'))
        if term and term not in name.casefold() and term not in str(proto).casefold():continue
        result.append(item)
    return result


def diagnostic_hint(row):
    """Advisory only; never infer remote health from local observations."""
    if not isinstance(row,dict):
        raise ValueError('invalid row')
    status=row.get('status')
    if status=='attention':
        return 'Échecs locaux répétés : consulter la chronologie puis lancer un précontrôle explicite.'
    if status=='observed':
        return 'Observations locales disponibles : consulter la chronologie. État distant non vérifié.'
    if status=='not_tested':
        return 'Aucune observation locale : lancer un précontrôle explicite si nécessaire.'
    return 'Statut inconnu : vérifier les journaux locaux avant toute conclusion.'
