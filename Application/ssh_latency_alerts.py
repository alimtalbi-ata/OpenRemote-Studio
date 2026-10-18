"""Bounded, opt-in local SSH latency degradation detection. Author: Abdelhalim Talbi."""
import math

STEPS=('Bastion principal','Bastion 2','Bastion 3','Bastion 4','Serveur cible')

def evaluate(series, *, threshold_ms=500, ratio=1.5, baseline_size=5):
    """Compare latest sample to preceding median; no host identities, no network calls."""
    if type(threshold_ms) not in (int,float) or not math.isfinite(threshold_ms) or threshold_ms<=0:
        raise ValueError('Seuil invalide')
    if type(ratio) not in (int,float) or not math.isfinite(ratio) or ratio<=1:
        raise ValueError('Ratio invalide')
    if type(baseline_size) is not int or not 2<=baseline_size<=50:
        raise ValueError('Fenêtre invalide')
    if not isinstance(series,list) or len(series)>200:raise ValueError('Série invalide')
    values=[]
    for row in series:
        if not isinstance(row,dict):raise ValueError('Mesure invalide')
        v=row.get('duration_ms')
        if type(v) not in (int,float) or not math.isfinite(v) or v<0:raise ValueError('Durée invalide')
        values.append(v)
    if not values:return {'state':'insufficient','latest_ms':None,'baseline_ms':None,'absolute_exceeded':False,'relative_exceeded':False}
    latest=values[-1]
    baseline=sorted(values[max(0,len(values)-baseline_size-1):-1])
    median=(baseline[(len(baseline)-1)//2]+baseline[len(baseline)//2])/2 if baseline else None
    absolute=latest>threshold_ms
    relative=median is not None and len(baseline)>=2 and latest>median*ratio
    return {'state':'degraded' if absolute or relative else ('normal' if len(baseline)>=2 else 'insufficient'),
            'latest_ms':latest,'baseline_ms':median,'absolute_exceeded':absolute,'relative_exceeded':relative}

def evaluate_dashboard(statistics, *, threshold_ms=500, ratio=1.5):
    if not isinstance(statistics,dict) or not isinstance(statistics.get('series'),dict):raise ValueError('Statistiques invalides')
    return {step:evaluate(statistics['series'].get(step,[]),threshold_ms=threshold_ms,ratio=ratio) for step in STEPS}
