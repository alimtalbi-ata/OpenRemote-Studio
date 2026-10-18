"""Isolated Qt keyboard/accessibility structural smoke; Abdelhalim Talbi."""
import argparse,json,os,subprocess,sys
from pathlib import Path
SCHEMA="openremote.accessibility-smoke.v1"
CHILD=r"""
import json,os,tempfile
with tempfile.TemporaryDirectory() as tmp:
 os.environ['APPDATA']=tmp
 from PySide6.QtWidgets import QApplication,QLineEdit,QShortcut
 from PySide6.QtCore import Qt
 from PySide6.QtGui import QKeySequence
 from PySide6.QtTest import QTest
 import qt_app
 app=QApplication([])
 window=qt_app.Main();window.show();app.processEvents()
 checks={}
 checks['window_title']=bool(window.windowTitle().strip())
 checks['search_visible']=window.search.isVisible()
 checks['search_keyboard_focusable']=bool(window.search.focusPolicy() & Qt.FocusPolicy.TabFocus)
 window.search.clearFocus();window.tabs.setFocus();app.processEvents()
 QTest.keyClick(window,Qt.Key.Key_F,Qt.KeyboardModifier.ControlModifier);app.processEvents()
 checks['ctrl_f_search_focus']=window.search.hasFocus()
 checks['tab_widget_keyboard_focusable']=bool(window.tabs.focusPolicy() & Qt.FocusPolicy.TabFocus)
 shortcuts=[s.key().toString() for s in window.findChildren(QShortcut)]
 checks['shortcuts_present']=bool(shortcuts)
 checks['home_available']=window.tabs.count()>0 and window.tabs.tabText(0)=='Accueil'
 checks['main_visible']=window.isVisible()
 window.close();app.processEvents()
 print('ACCESS_SMOKE_JSON='+json.dumps(checks,sort_keys=True))
"""
def run_smoke(*,timeout=30,python=None,env=None):
 if type(timeout) is not int or not 1<=timeout<=120:raise ValueError('timeout must be 1..120 seconds')
 child_env=dict(os.environ if env is None else env)
 child_env.setdefault('QT_QPA_PLATFORM','offscreen')
 try:
  result=subprocess.run([python or sys.executable,'-c',CHILD],cwd=str(Path(__file__).resolve().parent),env=child_env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout,check=False)
 except subprocess.TimeoutExpired:
  return {'schema':SCHEMA,'status':'timeout','checks':{},'network_tests_executed':False}
 except OSError:
  return {'schema':SCHEMA,'status':'launcher_error','checks':{},'network_tests_executed':False}
 checks={}
 if result.returncode==0:
  for line in result.stdout.splitlines():
   if line.startswith('ACCESS_SMOKE_JSON='):
    try:
     value=json.loads(line.split('=',1)[1])
     if isinstance(value,dict) and value and all(type(v) is bool for v in value.values()):checks=value
    except (ValueError,TypeError):pass
 return {'schema':SCHEMA,'status':'passed' if checks and all(checks.values()) else 'failed','checks':checks,'exit_code':result.returncode,'network_tests_executed':False,'note':'Offscreen keyboard/structure checks only; no DPI measurement, screenshots or live network tests.'}
def main(argv=None):
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--timeout',type=int,default=30)
 args=parser.parse_args(argv);report=run_smoke(timeout=args.timeout)
 with args.output.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2,ensure_ascii=False);stream.write('\n')
 return 0 if report['status']=='passed' else 1
if __name__=='__main__':sys.exit(main())
