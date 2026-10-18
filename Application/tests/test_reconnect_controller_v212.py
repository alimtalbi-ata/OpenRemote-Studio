import unittest
from session_reconnect_controller import resolve_reconnect_target

class Registry:
    def __init__(self,rows,fail=False):self.rows=rows;self.fail=fail
    def snapshot(self):
        if self.fail:raise OSError('unavailable')
        return self.rows

class ReconnectControllerTests(unittest.TestCase):
    def setUp(self):
        self.row={'connection_id':'a','pid':101,'status':'exited'}
        self.catalog=[{'id':'a','name':'Server'}]
    def test_success(self):
        self.assertEqual(resolve_reconnect_target(Registry([self.row]),self.catalog,'a',101),(self.catalog[0],None))
    def test_deleted_connection(self):
        self.assertEqual(resolve_reconnect_target(Registry([self.row]),[],'a',101)[1],'missing_or_ambiguous_connection')
    def test_duplicate_connection(self):
        self.assertEqual(resolve_reconnect_target(Registry([self.row]),self.catalog*2,'a',101)[1],'missing_or_ambiguous_connection')
    def test_running_sibling(self):
        rows=[self.row,{'connection_id':'a','pid':102,'status':'running'}]
        self.assertEqual(resolve_reconnect_target(Registry(rows),self.catalog,'a',101)[1],'session_unavailable')
    def test_unknown_sibling(self):
        rows=[self.row,{'connection_id':'a','pid':102,'status':'unknown'}]
        self.assertEqual(resolve_reconnect_target(Registry(rows),self.catalog,'a',101)[1],'session_unavailable')
    def test_stale_process(self):
        self.assertEqual(resolve_reconnect_target(Registry([]),self.catalog,'a',101)[1],'session_unavailable')
    def test_snapshot_failure(self):
        self.assertEqual(resolve_reconnect_target(Registry([],True),self.catalog,'a',101)[1],'snapshot_unavailable')
    def test_invalid_catalog(self):
        self.assertEqual(resolve_reconnect_target(Registry([self.row]),None,'a',101)[1],'invalid_catalog')
    def test_invalid_identity(self):
        self.assertEqual(resolve_reconnect_target(Registry([self.row]),self.catalog,'',101)[1],'invalid_connection')
    def test_duplicate_pid(self):
        self.assertEqual(resolve_reconnect_target(Registry([self.row,self.row]),self.catalog,'a',101)[1],'session_unavailable')

if __name__=='__main__':unittest.main()
