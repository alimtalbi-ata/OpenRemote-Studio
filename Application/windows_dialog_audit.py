"""Isolated dialog geometry checks. Author: Abdelhalim Talbi."""
import argparse,json,os,subprocess,sys
from pathlib import Path
SCHEMA='openremote.dialog-audit.v1'
CHILD=r"""
import json,os,tempfile
from PySide6.QtWidgets import QApplication,QDialogButtonBox
from layout_geometry import inspect_rectangles
with tempfile.TemporaryDirectory() as tmp:
 os.environ['APPDATA']=tmp
 import qt_app
 app=QApplication([])
 # Construct dialogs without invoking any connection or authentication.
 dialogs={'connection':qt_app.Editor(None),'jump_chain':qt_app.JumpChainDialog(None)}
 checks={};metrics={}
 for name,dialog in dialogs.items():
  dialog.show();app.processEvents()
  size=(dialog.width(),dialog.height())
  screen=dialog.screen().availableGeometry()
  bounds=(0,0,screen.width(),screen.height())
  geometry=inspect_rectangles({'dialog':(0,0,*size)},bounds)
  buttons=dialog.findChildren(QDialogButtonBox)
  checks[name]={'visible':dialog.isVisible(),'within_screen':geometry['checks']['dialog'],'has_action_buttons':bool(buttons),'positive_size':all(x>0 for x in size)}
  metrics[name]={'width':size[0],'height':size[1]}
  dialog.close();app.processEvents()
 print('DIALOG_AUDIT_JSON='+json.dumps({'checks':checks,'metrics':metrics},sort_keys=True))
"""
EXPECTED=('connection','jump_chain')
def validate_payload(value):
 if not isinstance(value,dict):return None
 checks=value.get('checks')
 if not isinstance(checks,dict) or set(checks)!=set(EXPECTED):return None
 keys={'visible','within_screen','has_action_buttons','positive_size'}
 if any(not isinstance(row,dict) or set(row)!=keys or any(type(v) is not bool for v in row.values()) for row in checks.values()):return None
 return checks
def run_audit(*,timeout=30,python=None,env=None):
 if type(timeout) is not int or not 1<=timeout<=120:raise ValueError('timeout must be 1..120 seconds')
 child_env=dict(os.environ if env is None else env);child_env.setdefault('QT_QPA_PLATFORM','offscreen')
 try:
  proc=subprocess.run([python or sys.executable,'-c',CHILD],cwd=str(Path(__file__).resolve().parent),env=child_env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout,check=False)
 except subprocess.TimeoutExpired:return {'schema':SCHEMA,'status':'timeout','checks':{},'network_tests_executed':False}
 except OSError:return {'schema':SCHEMA,'status':'launcher_error','checks':{},'network_tests_executed':False}
 checks=None
 if proc.returncode==0:
  for line in proc.stdout.splitlines():
   if line.startswith('DIALOG_AUDIT_JSON='):
    try:checks=validate_payload(json.loads(line.split('=',1)[1]))
    except (ValueError,TypeError):pass
 return {'schema':SCHEMA,'status':'passed' if checks and all(all(row.values()) for row in checks.values()) else 'failed','checks':checks or {},'exit_code':proc.returncode,'network_tests_executed':False,'note':'Offscreen dialog geometry only; no real Windows DPI or accessibility qualification.'}
def main(argv=None):
 parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);parser.add_argument('--timeout',type=int,default=30)
 args=parser.parse_args(argv);report=run_audit(timeout=args.timeout)
 with args.output.open('x',encoding='utf8') as f:json.dump(report,f,indent=2,ensure_ascii=False);f.write('\n')
 return 0 if report['status']=='passed' else 1
if __name__=='__main__':sys.exit(main())
