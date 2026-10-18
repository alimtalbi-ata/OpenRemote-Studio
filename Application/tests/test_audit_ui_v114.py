import unittest
from pathlib import Path
from ssh_import_audit import filter_rows,summary,export_signed,verify_signed
class AuditUiV114Tests(unittest.TestCase):
    def test_gui_has_audit_entry(self):
        text=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
        self.assertIn('def show_import_audit(self):',text)
        self.assertIn('self.ssh_audit_view.clicked.connect(self.show_import_audit)',text)
    def test_gui_has_filters(self):
        text=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
        self.assertIn('conflicts.toggled.connect(refresh)',text)
        self.assertIn('search.textChanged.connect(refresh)',text)
    def test_gui_has_signed_export_verify(self):
        text=(Path(__file__).resolve().parents[1]/'qt_app.py').read_text()
        self.assertIn('export.clicked.connect(save_signed)',text)
        self.assertIn('verify.clicked.connect(check_signed)',text)
    def test_signed_roundtrip(self):
        rows=[dict(imported_at=10,total=3,inserted=2,duplicates=1,conflicts=1)]
        self.assertEqual(verify_signed(export_signed(rows,b'x'*32),b'x'*32),rows)
    def test_filtered_summary(self):
        rows=[dict(imported_at=10,total=3,inserted=2,duplicates=1,conflicts=1),dict(imported_at=20,total=1,inserted=1,duplicates=0,conflicts=0)]
        self.assertEqual(summary(filter_rows(rows,conflicts_only=True))['operations'],1)
if __name__=='__main__':unittest.main()
