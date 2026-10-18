"""Bounded SSH latency correlation and recurrence, without host identities.
Author: Abdelhalim Talbi.
"""
import math
from ssh_latency_alerts import STEPS, evaluate


def correlate(statistics, *, threshold_ms=500, ratio=1.5, recurrence=3, window=5):
    """Return descriptive signals, not proof of shared root cause.

    Series must be chronological. No server identifiers are accepted or emitted.
    """
    if not isinstance(statistics, dict) or not isinstance(statistics.get('series'),dict):
        raise ValueError('Statistiques invalides')
    if type(window) is not int or not 3<=window<=20 or type(recurrence) is not int or not 2<=recurrence<=window:
        raise ValueError('Fenêtre de récurrence invalide')
    result={}; degraded=[]; recurrent=[]
    for step in STEPS:
        series=statistics['series'].get(step,[])
        if not isinstance(series,list) or len(series)>200:
            raise ValueError('Série invalide')
        # Validate every sample, even when the series is shorter than the window.
        for row in series:
            if not isinstance(row,dict) or type(row.get('recorded_at')) is not int or row['recorded_at']<0:
                raise ValueError('Horodatage invalide')
        if any(a['recorded_at']>b['recorded_at'] for a,b in zip(series,series[1:])):
            raise ValueError('Ordre chronologique invalide')
        current=evaluate(series,threshold_ms=threshold_ms,ratio=ratio)
        recent=series[-window:]
        # Recurrence is based on the absolute threshold, which avoids shifting baselines.
        count=sum(row['duration_ms']>threshold_ms for row in recent)
        is_recurrent=len(recent)>=recurrence and count>=recurrence
        if current['state']=='degraded':degraded.append(step)
        if is_recurrent:recurrent.append(step)
        result[step]={'state':current['state'],'latest_ms':current['latest_ms'],
                      'exceedances':count,'samples':len(recent),'recurrent':is_recurrent}
    return {'steps':result,'degraded_steps':degraded,'recurrent_steps':recurrent,
            'multi_step_degradation':len(degraded)>=2,
            'interpretation':'Corrélation indicative uniquement : parcours anonymisés potentiellement différents.'}
