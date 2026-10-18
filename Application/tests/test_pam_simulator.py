import unittest
from pam_simulator import SimulatedPamBroker
class PamSimulationTests(unittest.TestCase):
 def setUp(self):
  self.now=[1000.0]
  self.broker=SimulatedPamBroker(lambda:self.now[0],ttl_seconds=30)
  self.args=('admin','cyberark:Safe/Account','server01')
 def test_explicit_approval(self):
  with self.assertRaises(PermissionError):self.broker.authorize(*self.args)
 def test_simulated_session_not_real(self):
  grant=self.broker.authorize(*self.args,approved=True)
  result=self.broker.open_session(grant.grant_id,*self.args)
  self.assertTrue(result['simulated']);self.assertFalse(result['real_session'])
 def test_replay_denied(self):
  grant=self.broker.authorize(*self.args,approved=True)
  self.broker.open_session(grant.grant_id,*self.args)
  with self.assertRaises(PermissionError):self.broker.open_session(grant.grant_id,*self.args)
 def test_expired(self):
  grant=self.broker.authorize(*self.args,approved=True)
  self.now[0]+=30
  with self.assertRaises(PermissionError):self.broker.open_session(grant.grant_id,*self.args)
 def test_context_mismatch_consumes_grant(self):
  grant=self.broker.authorize(*self.args,approved=True)
  with self.assertRaises(PermissionError):self.broker.open_session(grant.grant_id,'other',*self.args[1:])
  with self.assertRaises(PermissionError):self.broker.open_session(grant.grant_id,*self.args)
 def test_bad_reference(self):
  with self.assertRaises(PermissionError):self.broker.authorize('admin','invalid','server',approved=True)
 def test_audit_is_copy(self):
  self.broker.authorize(*self.args,approved=True)
  events=self.broker.audit()
  self.assertEqual(events[0]['decision'],'ALLOW_SIMULATION')
  events[0]['decision']='TAMPERED'
  self.assertEqual(self.broker.audit()[0]['decision'],'ALLOW_SIMULATION')
 def test_bad_ttl(self):
  with self.assertRaises(ValueError):SimulatedPamBroker(lambda:0,0)
