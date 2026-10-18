
import unittest
from diagnostics import command_args,safe_host
class DiagnosticTests(unittest.TestCase):
    def test_ping_windows(self):
        self.assertEqual(command_args("ping","server.example",True),["ping","-n","4","server.example"])
    def test_ping_linux(self):
        self.assertEqual(command_args("ping","192.0.2.1",False),["ping","-c","4","192.0.2.1"])
    def test_traceroute(self):
        self.assertEqual(command_args("traceroute","host",True)[0],"tracert")
    def test_ipv6(self):
        self.assertEqual(safe_host("[2001:db8::1]"),"2001:db8::1")
    def test_reject_option_injection(self):
        for host in ["-Ieth0","host\n--bad","x y","x;whoami","host/evil"]:
            with self.subTest(host=host):
                with self.assertRaises(ValueError):safe_host(host)
    def test_reject_unknown_diagnostic(self):
        with self.assertRaises(ValueError):command_args("shell","host")
