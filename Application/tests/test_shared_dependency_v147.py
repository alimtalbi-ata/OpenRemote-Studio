import unittest
from shared_dependency_analysis import compare_dependencies

class SharedDependencyTests(unittest.TestCase):
    def setUp(self):
        self.connections=[{'id':'a'},{'id':'b'},{'id':'c'}]
        self.routes={'a':{'mode':'ssh_jump','jump_host':'jump.example'},'b':{'mode':'ssh_jump','jump_host':'JUMP.EXAMPLE'},'c':{'mode':'direct'}}
        self.report={'rows':[{'id':'a','local_errors_30m':3},{'id':'b','local_errors_30m':1},{'id':'c','local_errors_30m':8}]}
    def test_shared_jump(self):
        result=compare_dependencies(self.connections,self.routes,self.report)
        self.assertEqual((len(result['groups']),result['groups'][0]['affected_connections'],result['groups'][0]['local_errors_30m']),(1,2,4))
    def test_no_host_exposure(self):
        self.assertNotIn('jump.example',str(compare_dependencies(self.connections,self.routes,self.report)))
    def test_no_cause_claim(self):
        result=compare_dependencies(self.connections,self.routes,self.report)
        self.assertFalse(result['remote_cause_confirmed']);self.assertFalse(result['groups'][0]['shared_remote_cause_confirmed'])
    def test_single_route_ignored(self):
        self.assertEqual(compare_dependencies(self.connections[:1],self.routes,self.report)['groups'],[])
    def test_different_jump(self):
        self.routes['b']['jump_host']='other.example'
        self.assertEqual(compare_dependencies(self.connections,self.routes,self.report)['groups'],[])
    def test_rdp_gateway(self):
        self.routes={'a':{'mode':'rd_gateway','gateway_host':'rd.example'},'b':{'mode':'rds_collection','gateway_host':'rd.example','collection':'Team'}}
        self.assertEqual(compare_dependencies(self.connections,self.routes,self.report)['groups'][0]['dependency_type'],'Passerelle RDP')
    def test_invalid_route_skipped(self):
        self.routes['a']={'mode':'ssh_jump','jump_host':'bad host'}
        self.assertEqual(compare_dependencies(self.connections,self.routes,self.report)['skipped_invalid_routes'],1)
    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):compare_dependencies(None,{},self.report)
    def test_no_error_members(self):
        self.report['rows'][0]['local_errors_30m']=0
        self.assertEqual(compare_dependencies(self.connections,self.routes,self.report)['groups'][0]['affected_connections'],1)
    def test_empty(self):
        self.assertEqual(compare_dependencies([],{},self.report)['groups'],[])
