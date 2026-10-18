"""Bounded, Qt-independent visualization data for local connection failures.
Author: Abdelhalim Talbi.
"""
KINDS = ('tcp_local', 'ssh_jump', 'session_exit')

def chart_data(report):
    if not isinstance(report, dict) or report.get('schema') != 'openremote.incident_trends.v1' or report.get('scope') != 'local_only' or report.get('remote_cause_confirmed') is not False:
        raise ValueError('invalid local trend report')
    buckets = report.get('buckets')
    if not isinstance(buckets, list) or not 1 <= len(buckets) <= 288:
        raise ValueError('invalid buckets')
    points=[]
    for bucket in buckets:
        if not isinstance(bucket,dict) or not isinstance(bucket.get('counts'),dict):
            raise ValueError('invalid bucket')
        counts=[]
        for kind in KINDS:
            value=bucket['counts'].get(kind)
            if type(value) is not int or not 0 <= value <= 1000000:
                raise ValueError('invalid count')
            counts.append(value)
        if type(bucket.get('total')) is not int or bucket['total'] != sum(counts):
            raise ValueError('inconsistent total')
        points.append(tuple(counts))
    maximum=max(1,max(sum(point) for point in points))
    return {'series':points,'maximum':maximum,'total':sum(sum(p) for p in points),'categories':KINDS}

def stacked_heights(point, maximum, height):
    if type(height) is not int or height < 1 or type(maximum) is not int or maximum < 1:
        raise ValueError('invalid dimensions')
    if len(point)!=3 or any(type(n) is not int or n<0 for n in point) or sum(point)>maximum:
        raise ValueError('invalid point')
    # cumulative rounding prevents overdraw or gaps caused by independent rounding
    edges=[0];cumulative=0
    for count in point:
        cumulative+=count
        edges.append(round(cumulative*height/maximum))
    return tuple(edges[i+1]-edges[i] for i in range(3))
