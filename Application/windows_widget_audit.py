"""Isolated real-widget geometry checks; author Abdelhalim Talbi. No remote sessions."""
import argparse,json,os,subprocess,sys
from pathlib import Path
SCHEMA='openremote.widget-audit.v1'
CHILD=r"""
import json,os,tempfile
from PySide6.QtWidgets import QApplication
from layout_geometry import inspect_rectangles
with tempfile.TemporaryDirectory() as tmp:
 os.environ['APPDATA']=tmp
 import qt_app
 app=QApplication([])
 window=qt_app.Main();window.show();app.processEvents()
 def rect(widget):
  point=widget.mapTo(window,widget.rect().topLeft())
  return (point.x(),point.y(),widget.width(),widget.height())
 bounds=(0,0,window.width(),window.height())
 widgets={'search':window.search,'tabs':window.tabs,'tree':window.tree,'menu':window.menuBar()}
 visible={name:widget.isVisible() for name,widget in widgets.items()}
 geometry=inspect_rectangles({name:rect(widget) for name,widget in widgets.items()},bounds)
 checks={name:visible[name] and geometry['checks'][name] for name in widgets}
 print('WIDGET_AUDIT_JSON='+json.dumps({'checks':checks,'clipped':geometry['clipped'],'window':[window.width(),window.height()],'dpr':window.devicePixelRatioF()},sort_keys=True))
 window.close();app.processEvents()
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
   if line.startswith('WIDGET_AUDIT_JSON='):
    try:
     value=json.loads(line.split('=',1)[1]);checks=value.get('checks')
     if isinstance(checks,dict) and set(checks)=={'search','tabs','tree','menu'} and all(type(v) is bool for v in checks.values()):details=value
    except (ValueError,TypeError,AttributeError):pass
 checks=details.get('checks',{})
 return {'schema':SCHEMA,'status':'passed' if checks and all(checks.values()) else 'failed','checks':checks,'clipped':details.get('clipped',[]),'window':details.get('window'),'device_pixel_ratio':details.get('dpr'),'exit_code':result.returncode,'network_tests_executed':False,'note':'Offscreen widget geometry only; Windows DPI and real user interactions not qualified.'}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--timeout',type=int,default=30)
 args=p.parse_args(argv);report=run_audit(timeout=args.timeout)
 with args.output.open('x',encoding='utf8') as f:json.dump(report,f,indent=2,ensure_ascii=False);f.write('\n')
 return 0 if report['status']=='passed' else 1
if __name__=='__main__':sys.exit(main())
