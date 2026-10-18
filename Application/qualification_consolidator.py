"""Consolidate explicit QA results, without claiming unexecuted scenarios passed."""
import argparse,json,sys
from pathlib import Path
ALLOWED={'passed','failed','timeout','launcher_error','not_executed','blocked'}
def consolidate(reports):
    if not isinstance(reports,dict) or not reports: raise ValueError('reports required')
    output={};counts={s:0 for s in sorted(ALLOWED)}
    for name,report in reports.items():
        if not isinstance(name,str) or not name or not isinstance(report,dict):raise ValueError('invalid report')
        status=report.get('status','not_executed')
        if status not in ALLOWED:raise ValueError('unknown status')
        output[name]={'status':status,'schema':str(report.get('schema',''))[:120]}
        counts[status]+=1
    overall='failed' if counts['failed'] or counts['timeout'] or counts['launcher_error'] else ('incomplete' if counts['not_executed'] or counts['blocked'] else 'passed')
    return {'schema':'openremote.qa-summary.v1','overall':overall,'counts':counts,'reports':output,'note':'Offline results do not qualify live Windows GUI, DPI, or network protocols.'}
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('reports',type=Path,nargs='+');args=p.parse_args(argv)
    source={}
    for path in args.reports:
        with path.open(encoding='utf8') as stream: source[path.name]=json.load(stream)
    result=consolidate(source)
    with args.output.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2,ensure_ascii=False);stream.write('\n')
    return 0 if result['overall']=='passed' else 1
if __name__=='__main__':sys.exit(main())
