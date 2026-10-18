"""Opt-in isolated Qt geometry audit; author Abdelhalim Talbi. No network connections."""
import argparse,json,os,subprocess,sys
from pathlib import Path
SCHEMA="openremote.windows-layout-audit.v1"
CHILD=r"""
import json,os,tempfile
from PySide6.QtWidgets import QApplication,QWidget,QPushButton,QLineEdit,QTabWidget
with tempfile.TemporaryDirectory() as tmp:
 os.environ['APPDATA']=tmp
 import qt_app
 app=QApplication([])
 w=qt_app.Main();w.show();app.processEvents()
 checks={}
 checks['main_visible']=w.isVisible()
 checks['main_positive_geometry']=w.width()>0 and w.height()>0
 checks['search_visible']=w.search.isVisible()
 checks['search_nonzero_size']=w.search.width()>0 and w.search.height()>0
 checks['tabs_visible']=w.tabs.isVisible()
 checks['tabs_nonzero_size']=w.tabs.width()>0 and w.tabs.height()>0
 checks['main_within_screen']=w.width()<=app.primaryScreen().availableGeometry().width() and w.height()<=app.primaryScreen().availableGeometry().height()
 print('LAYOUT_AUDIT_JSON='+json.dumps({'checks':checks,'screen':[app.primaryScreen().availableGeometry().width(),app.primaryScreen().availableGeometry().height()],'window':[w.width(),w.height()],'dpr':w.devicePixelRatioF()},sort_keys=True))
 w.close();app.processEvents()
"""
def run_audit(*,timeout=30,python=None,env=None):
 if type(timeout) is not int or not 1<=timeout<=120:raise ValueError('timeout must be 1..120 seconds')
 child_env=dict(os.environ if env is None else env)
 child_env.setdefault('QT_QPA_PLATFORM','offscreen')
 try:
  result=subprocess.run([python or sys.executable,'-c',CHILD],cwd=str(Path(__file__).resolve().parent),env=child_env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout,check=False)
 except subprocess.TimeoutExpired:
  return {'schema':SCHEMA,'status':'timeout','checks':{},'network_tests_executed':False}
 except OSError:
  return {'schema':SCHEMA,'status':'launcher_error','checks':{},'network_tests_executed':False}
 details={}
 if result.returncode==0:
  for line in result.stdout.splitlines():
   if line.startswith('LAYOUT_AUDIT_JSON='):
    try:
     data=json.loads(line.split('=',1)[1]);checks=data.get('checks')
     if isinstance(checks,dict) and len(checks)==7 and all(type(v) is bool for v in checks.values()):details=data
    except (ValueError,TypeError,AttributeError):pass
 checks=details.get('checks',{})
 return {'schema':SCHEMA,'status':'passed' if checks and all(checks.values()) else 'failed','checks':checks,'geometry':{'screen':details.get('screen'),'window':details.get('window'),'device_pixel_ratio':details.get('dpr')} if details else {},'exit_code':result.returncode,'network_tests_executed':False,'note':'Offscreen geometry checks only. Not a real Windows DPI or screenshot qualification.'}
def main(argv=None):
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--timeout',type=int,default=30)
 args=parser.parse_args(argv);report=run_audit(timeout=args.timeout)
 with args.output.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2,ensure_ascii=False);f.write('\n')
 return 0 if report['status']=='passed' else 1
if __name__=='__main__':sys.exit(main())
