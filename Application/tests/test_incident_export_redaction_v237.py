import unittest
from session_incident_center import incident_export

class TestIncidentExportRedaction(unittest.TestCase):
    def test_redacts_sensitive_fields(self):
        item={'connection_id':'server','protocol':'SSH','diagnostic':{'severity':'error','summary':'password=hunter2 token:abc123 authorization=Bearer'}}
        out=incident_export([item]); summary=out['incidents'][0]['summary']
        for secret in ('hunter2','abc123','Bearer'): self.assertNotIn(secret,summary)
        self.assertIn('[REDACTED]',summary)
    def test_drops_control_characters(self):
        item={'connection_id':'x\nInjected','diagnostic':{'summary':'oops\x00broken'}}
        out=incident_export([item]); self.assertNotIn('\n',out['incidents'][0]['connection_id'])
        self.assertNotIn('\x00',out['incidents'][0]['summary'])
    def test_does_not_export_extra_keys(self):
        item={'password':'danger','process_args':'--password danger','diagnostic':{'summary':'failed'}}
        self.assertNotIn('danger',str(incident_export([item])))
