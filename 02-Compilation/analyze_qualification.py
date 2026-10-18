#!/usr/bin/env python3
"""Analyze real V31.x Windows qualification JSON; never infer success from missing steps."""
import argparse, json, sys
from pathlib import Path

def analyze(payload):
    if not isinstance(payload, dict): raise ValueError('report must be a JSON object')
    steps=payload.get('steps')
    if not isinstance(steps,list) or not steps: raise ValueError('missing or empty steps: no qualification evidence')
    names=set(); failures=[]
    for index, step in enumerate(steps):
        if not isinstance(step,dict): raise ValueError(f'invalid step {index}')
        name=step.get('name'); status=step.get('status')
        if not isinstance(name,str) or not name.strip() or name in names: raise ValueError('invalid or duplicate step name')
        names.add(name)
        if status not in ('PASS','FAIL'): raise ValueError(f'invalid status for {name}')
        if status=='FAIL': failures.append({'name':name,'error':str(step.get('error') or 'No error detail')})
    reported=payload.get('failed')
    if not isinstance(reported,int) or isinstance(reported,bool) or reported!=len(failures):
        raise ValueError('failed count does not match step records; report may be incomplete')
    passed=payload.get('passed')
    if not isinstance(passed,int) or isinstance(passed,bool) or passed!=len(steps)-len(failures):
        raise ValueError('passed count does not match step records')
    declared=payload.get('qualificationStatus')
    if declared is not None and declared not in ('PASS','FAIL','PARTIAL'):
        raise ValueError('invalid qualificationStatus')
    skipped=payload.get('skipped',[])
    if not isinstance(skipped,list) or any(not isinstance(s,str) or not s.strip() for s in skipped):
        raise ValueError('invalid skipped steps')
    if len(skipped)!=len(set(skipped)):
        raise ValueError('duplicate skipped steps')
    computed='FAIL' if failures else ('PARTIAL' if skipped else 'PASS')
    if declared is not None and declared!=computed:
        raise ValueError('qualificationStatus contradicts step records')
    version=payload.get('version')
    if version is not None and (not isinstance(version,str) or not version.strip()):
        raise ValueError('invalid version')
    return {'version':version,'status':computed, 'passed':passed,'failed':len(failures),'skipped':skipped,'failures':failures}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--require-complete',action='store_true',help='fail when qualification is PARTIAL')
    args=parser.parse_args(argv)
    try:
        result=analyze(json.loads(args.report.read_text(encoding='utf-8-sig')))
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        print(json.dumps({'status':'INVALID','error':str(exc)},ensure_ascii=False));return 2
    print(json.dumps(result,ensure_ascii=False,indent=2));return 1 if result['failed'] or (args.require_complete and result['status'] != 'PASS') else 0
if __name__=='__main__':sys.exit(main())
