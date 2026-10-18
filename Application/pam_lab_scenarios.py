"""Deterministic PAM laboratory test cases; no network and no credentials.
Author: Abdelhalim Talbi.
"""
from pam_simulator import SimulatedPamBroker

def run_scenarios():
    now=[1000.0]
    broker=SimulatedPamBroker(lambda:now[0],ttl_seconds=5)
    p,r,t='operator','generic:Demo/Account','lab-host'
    results=[]
    def expect_deny(name,action):
        try:action()
        except PermissionError:results.append({'scenario':name,'result':'PASS'})
        else:results.append({'scenario':name,'result':'FAIL'})
    expect_deny('approval_required',lambda:broker.authorize(p,r,t))
    grant=broker.authorize(p,r,t,approved=True)
    expect_deny('target_mismatch',lambda:broker.open_session(grant.grant_id,p,r,'other-host'))
    expect_deny('grant_consumed_on_mismatch',lambda:broker.open_session(grant.grant_id,p,r,t))
    grant=broker.authorize(p,r,t,approved=True)
    now[0]+=5
    expect_deny('expiry',lambda:broker.open_session(grant.grant_id,p,r,t))
    grant=broker.authorize(p,r,t,approved=True)
    outcome=broker.open_session(grant.grant_id,p,r,t)
    results.append({'scenario':'simulated_success','result':'PASS' if outcome['simulated'] and not outcome['real_session'] else 'FAIL'})
    expect_deny('single_use',lambda:broker.open_session(grant.grant_id,p,r,t))
    return {'results':results,'audit':list(broker.audit()),'passed':all(x['result']=='PASS' for x in results)}
