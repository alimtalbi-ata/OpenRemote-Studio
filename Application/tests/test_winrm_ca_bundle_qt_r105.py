"""R105 Qt CA consent and worker binding; no remote server."""
import unittest
from pathlib import Path
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from winrm_inventory_qt import WinRMInventoryPanel
except ImportError: QApplication=None
CA=Path(__file__).parent/'fixtures'/'r105-public-test-ca.pem'
def wait_until(app,predicate):
    for _ in range(300):
        app.processEvents()
        if predicate():return True
        QTest.qWait(10)
    return False
@unittest.skipIf(QApplication is None,'PySide6 unavailable: Windows Qt CI required')
class CABundleQtR105(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def panel(self,calls,factory):
        p=WinRMInventoryPanel(client_factory=factory,
             credential_provider=lambda:calls.append('password') or 'TEST_ONLY_PASSWORD')
        p.origin.setText('https://win.example.test');p.username.setText('readonly')
        return p
    def test_change_revokes_consent(self):
        calls=[];p=self.panel(calls,lambda *a,**kw:calls.append('network'))
        try:
            p.consent.setChecked(True);p.ca_bundle.setText(str(CA.resolve()))
            self.assertFalse(p.consent.isChecked());p.refresh();self.assertEqual(calls,[])
        finally:p.close()
    def test_invalid_ca_before_secret(self):
        calls=[];p=self.panel(calls,lambda *a,**kw:calls.append('network'))
        try:
            p.ca_bundle.setText('/missing/test-ca.pem');p.consent.setChecked(True);p.refresh()
            self.assertEqual(calls,[]);self.assertIn('winrm_invalid_ca_bundle',p.status.text())
        finally:p.close()
    def test_valid_ca_worker_and_no_rendered_secret(self):
        calls=[]
        class Fake:
            def __init__(self,origin,username,credential_provider,*,ca_bundle):
                calls.append(('ca',ca_bundle));self.provider=credential_provider
            def inventory(self,*,online,cancelled):
                calls.append(('auth',self.provider()))
                return {'state':'ok','read_only':True,'os':{
                    'caption':'Windows','version':'10','build':'1','computer':'LAB'},'disks':[]}
        p=self.panel(calls,Fake)
        try:
            p.ca_bundle.setText(str(CA.resolve()));p.consent.setChecked(True);p.refresh()
            self.assertTrue(wait_until(self.app,lambda:p.refresh_button.isEnabled()))
            self.assertIn(('ca',str(CA.resolve())),calls)
            self.assertEqual(p.table.topLevelItemCount(),4)
            self.assertNotIn('TEST_ONLY_PASSWORD',p.status.text())
        finally:p.close()
if __name__=='__main__':unittest.main()
