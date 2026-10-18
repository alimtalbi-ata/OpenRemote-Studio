"""Conservative local event correlation, never infers remote authentication success.
Author: Abdelhalim Talbi.
"""
from datetime import datetime, timezone, timedelta

def _date(value):
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (TypeError,ValueError,AttributeError,OverflowError):
        return None

def correlate(events, window_minutes=30, threshold=3, now=None):
    """Count recent observed local errors; ignore unknowns and invalid timestamps."""
    if type(window_minutes) is not int or not 1<=window_minutes<=1440:raise ValueError('fenêtre invalide')
    if type(threshold) is not int or not 2<=threshold<=100:raise ValueError('seuil invalide')
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError('now doit être UTC aware')
    cutoff=now.astimezone(timezone.utc)-timedelta(minutes=window_minutes)
    errors=[]
    for event in events:
        if not isinstance(event,dict) or event.get('state') not in ('error','failed'):continue
        at=_date(event.get('at'))
        if at is not None and cutoff<=at<=now:errors.append(event)
    count=len(errors)
    return {'count':count,'recurrent':count>=threshold,'window_minutes':window_minutes,
            'level':'attention' if count>=threshold else 'normal',
            'advice':('Examiner la chronologie et les diagnostics de chemin avant une nouvelle tentative.'
                      if count>=threshold else 'Aucune répétition d’échecs locaux au seuil défini.')}

def overview(connections,sessions,probes,now=None):
    from connection_timeline import timeline
    result=[]
    for conn in connections:
        identity=conn.get('id')
        if not isinstance(identity,str) or not identity:continue
        events=timeline(sessions,probes,identity,limit=500)
        item=correlate(events,now=now)
        if item['recurrent']:result.append({'id':identity,'name':conn.get('name') or identity,'count':item['count']})
    return sorted(result,key=lambda x:(-x['count'],x['name']))
