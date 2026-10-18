"""Local incident time-series and period comparison. No remote-health inference.
Author: Abdelhalim Talbi.
"""
from collections import Counter
from datetime import datetime, timezone, timedelta
from connection_timeline import timeline

CATEGORIES=('tcp_local','ssh_jump','session_exit')

def build_trends(sessions, probes, connection_id, *, now=None, minutes=60, bucket_minutes=15, limit=500):
    if not isinstance(connection_id,str) or not connection_id: raise ValueError('invalid connection id')
    if type(minutes) is not int or minutes not in (30,60,120,240,480,1440): raise ValueError('invalid window')
    if type(bucket_minutes) is not int or bucket_minutes not in (5,15,30,60) or minutes%bucket_minutes: raise ValueError('invalid bucket')
    if type(limit) is not int or not 1<=limit<=500: raise ValueError('invalid limit')
    now=datetime.now(timezone.utc) if now is None else now
    if not isinstance(now,datetime) or now.tzinfo is None: raise ValueError('timezone-aware now required')
    now=now.astimezone(timezone.utc)
    start=now-timedelta(minutes=minutes)
    counts=Counter(); earlier=0; later=0
    for event in timeline(sessions,probes,connection_id,limit=limit,kind='error'):
        try: at=datetime.fromisoformat(event['at'].replace('Z','+00:00')).astimezone(timezone.utc)
        except (ValueError,TypeError,KeyError,AttributeError): continue
        if not start<=at<=now: continue
        category=('session_exit' if event.get('kind')=='session' else event.get('detail'))
        if category not in CATEGORIES: continue
        index=min((minutes-1)//bucket_minutes,int((at-start).total_seconds()//(bucket_minutes*60)))
        counts[(index,category)]+=1
        if at<start+timedelta(minutes=minutes/2): earlier+=1
        else: later+=1
    buckets=[]
    for i in range(minutes//bucket_minutes):
        at=start+timedelta(minutes=i*bucket_minutes)
        by_kind={kind:counts[(i,kind)] for kind in CATEGORIES}
        buckets.append({'start_utc':at.isoformat(),'counts':by_kind,'total':sum(by_kind.values())})
    return {'schema':'openremote.incident_trends.v1','scope':'local_only','remote_cause_confirmed':False,
            'window_minutes':minutes,'bucket_minutes':bucket_minutes,'total_errors':earlier+later,
            'earlier_half':earlier,'later_half':later,'delta':later-earlier,'buckets':buckets}
