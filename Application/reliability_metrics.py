"""Observed local-client reliability metrics; never infer remote service uptime.
Author: Abdelhalim Talbi.
"""

def enrich_statistics(rows):
    """Compute rates only over observed exits; preserve unknown outcomes."""
    result=[]
    for row in rows:
        r=dict(row)
        observed=r['observed']; attempts=r['attempts']
        r['observation_rate']=round(100*observed/attempts,1) if attempts else None
        r['local_zero_exit_rate']=round(100*r['success']/observed,1) if observed else None
        r['risk']='Échecs observés' if r['failed'] else ('Données insuffisantes' if not observed else 'Aucun échec observé')
        result.append(r)
    return result

def filter_statistics(rows,query='',only_failures=False):
    q=query.strip().casefold()
    return [r for r in rows if (not only_failures or r['failed']>0) and
            (not q or q in (str(r['name'])+' '+str(r['protocol'])).casefold())]
