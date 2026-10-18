"""Redacted per-hop SSH diagnostic presentation. Author: Abdelhalim Talbi."""
STATES={'starting':('EN COURS','#2b70b5'),'ok':('RÉUSSI','#167a45'),'failed':('ÉCHEC','#b33030')}
def stage_rows(events, status=None):
    if not isinstance(events,(list,tuple)) or len(events)>24:raise ValueError('Événements invalides')
    rows=[]
    for event in events:
        if not isinstance(event,dict):raise ValueError('Événement invalide')
        step=event.get('step','')
        state=event.get('state','')
        if state not in STATES or not isinstance(step,str) or not (step=='Serveur cible' or step=='Bastion principal' or (step.startswith('Bastion ') and step[8:].isdigit())):
            raise ValueError('Étape SSH invalide')
        label,color=STATES[state]
        duration=event.get('duration_ms')
        if duration is not None and (type(duration) is not int or not 0<=duration<=3600000):raise ValueError('Durée SSH invalide')
        rows.append({'step':step,'state':state,'label':label,'color':color,'duration_ms':duration})
    if status=='cancelled':
        rows.append({'step':'Diagnostic','state':'cancelled','label':'ANNULÉ','color':'#8b671e'})
    return rows


def compact_stage_rows(events,status=None):
    """Collapse stage transitions into one safe display row per hop."""
    validated=stage_rows(events,status)
    latest={}
    for row in validated:
        key=row['step']
        if key not in latest:
            latest[key]=dict(row)
        else:
            previous=latest[key]
            if previous['state'] in ('ok','failed') and row['state']=='starting':
                continue  # Ignore delayed start events after a terminal state.
            latest[key]=dict(row)
    return list(latest.values())
