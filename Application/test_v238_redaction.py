import unittest
from session_incident_center import incident_export
class TestV238Export(unittest.TestCase):
 def test_bearer(self):
  x=incident_export([{'diagnostic':{'summary':'Authorization: Bearer abc123'}}])
  self.assertNotIn('abc123',str(x))
 def test_url_password(self):
  x=incident_export([{'diagnostic':{'summary':'ssh://alice:supersecret@host'}}])
  self.assertNotIn('supersecret',str(x))
 def test_readonly(self):
  x=incident_export([{'diagnostic':{'summary':'failed'}}])
  self.assertFalse(x['incidents'][0]['can_reconnect'])
if __name__=='__main__':unittest.main()
