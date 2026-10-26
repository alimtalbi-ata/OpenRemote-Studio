"""R120 tests for the bounded, local-only Ansible CLI qualification harness.

Unit tests use a stub process. The real CLI test is explicitly opted in by the
Linux CI job after installing ansible-core; it only targets generated localhost.
Author: Abdelhalim Talbi.
"""
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from ansible_local_qualification import qualify_local_cli


class AnsibleLocalQualificationR120Tests(unittest.TestCase):
    def test_missing_cli_is_explicit_and_does_not_spawn(self):
        with patch("ansible_local_qualification.subprocess.run") as run:
            result = qualify_local_cli(executable_lookup=lambda _name: None)
        self.assertEqual(result["state"], "unavailable")
        self.assertEqual(result["code"], "ansible_cli_not_installed")
        self.assertFalse(result["remote_target_used"])
        self.assertFalse(result["output_retained"])
        run.assert_not_called()

    def test_invalid_timeout_is_rejected_before_cli_discovery(self):
        lookup_calls = []
        for value in (True, 0, 4, 31, 20.5, "20"):
            with self.subTest(timeout=value):
                result = qualify_local_cli(
                    timeout_seconds=value,
                    executable_lookup=lambda name: lookup_calls.append(name) or "/fake/ansible-playbook",
                )
                self.assertEqual(result["state"], "rejected")
                self.assertEqual(result["code"], "ansible_timeout_invalid")
        self.assertEqual(lookup_calls, [])

    def test_success_uses_generated_localhost_files_and_discards_output(self):
        calls = []

        def fake_run(args, **kwargs):
            calls.append((list(args), kwargs))
            cwd = Path(kwargs["cwd"])
            self.assertEqual((cwd / "localhost.ini").read_text("ascii"),
                             "localhost ansible_connection=local\n")
            playbook = (cwd / "local-qualification.yml").read_text("utf-8")
            self.assertIn("hosts: localhost", playbook)
            self.assertIn("connection: local", playbook)
            self.assertIn("ansible.builtin.debug", playbook)
            self.assertNotIn("shell:", playbook)
            self.assertNotIn("command:", playbook)
            self.assertTrue((cwd / "ansible.cfg").is_file())
            return subprocess.CompletedProcess(args, 0, stdout="SECRET_OUTPUT_SENTINEL", stderr="SECRET_ERROR_SENTINEL")

        poisoned = {
            "ANSIBLE_CONFIG": "/untrusted/ansible.cfg",
            "ANSIBLE_CALLBACK_PLUGINS": "/untrusted/callbacks",
            "ANSIBLE_INVENTORY": "/untrusted/inventory",
            "SSH_AUTH_SOCK": "/tmp/agent.sock",
            "SSH_AGENT_PID": "1234",
            "PYTHONPATH": "/untrusted/pythonpath",
        }
        with patch.dict(os.environ, poisoned, clear=False):
            with patch("ansible_local_qualification.subprocess.run", side_effect=fake_run):
                result = qualify_local_cli(executable_lookup=lambda _name: "/trusted/bin/ansible-playbook")

        self.assertEqual(result["state"], "qualified")
        self.assertEqual(result["stages"], {"syntax_check": "passed", "localhost_check": "passed"})
        self.assertFalse(result["remote_target_used"])
        self.assertFalse(result["output_retained"])
        self.assertNotIn("SECRET_OUTPUT_SENTINEL", repr(result))
        self.assertNotIn("SECRET_ERROR_SENTINEL", repr(result))
        self.assertEqual(len(calls), 2)
        syntax_args, syntax_kwargs = calls[0]
        check_args, check_kwargs = calls[1]
        self.assertIn("--syntax-check", syntax_args)
        self.assertIn("--check", check_args)
        self.assertIn("--diff", check_args)
        self.assertIn("--connection", check_args)
        self.assertEqual(check_args[check_args.index("--connection") + 1], "local")
        self.assertEqual(check_args[check_args.index("--limit") + 1], "localhost")
        self.assertFalse(any(flag in check_args for flag in ("--become", "--private-key", "--ssh-common-args", "--ssh-extra-args")))
        self.assertIn("--limit", syntax_args)
        self.assertIn("localhost", syntax_args)
        self.assertIn("localhost", check_args)
        for args, kwargs in calls:
            self.assertFalse(kwargs["shell"])
            self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
            self.assertIs(kwargs["stdout"], subprocess.DEVNULL)
            self.assertIs(kwargs["stderr"], subprocess.DEVNULL)
            self.assertTrue(kwargs["close_fds"])
            self.assertGreater(kwargs["timeout"], 0)
            env = kwargs["env"]
            for untrusted in ("ANSIBLE_CALLBACK_PLUGINS", "ANSIBLE_INVENTORY", "SSH_AUTH_SOCK", "SSH_AGENT_PID", "PYTHONPATH"):
                self.assertNotIn(untrusted, env)
            self.assertEqual(env["ANSIBLE_CONFIG"], str(Path(kwargs["cwd"]) / "ansible.cfg"))

    def test_syntax_failure_stops_before_local_check(self):
        with patch("ansible_local_qualification.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 4)) as run:
            result = qualify_local_cli(executable_lookup=lambda _name: "/trusted/bin/ansible-playbook")
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["code"], "ansible_cli_syntax_check_failed")
        self.assertEqual(result["stage"], "syntax_check")
        self.assertEqual(result["exit_code"], 4)
        self.assertEqual(run.call_count, 1)

    def test_local_check_failure_is_generic_and_has_no_output(self):
        with patch("ansible_local_qualification.subprocess.run", side_effect=[
            subprocess.CompletedProcess([], 0),
            subprocess.CompletedProcess([], 2, stdout="sensitive", stderr="details"),
        ]) as run:
            result = qualify_local_cli(executable_lookup=lambda _name: "/trusted/bin/ansible-playbook")
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["code"], "ansible_cli_local_check_failed")
        self.assertEqual(result["stage"], "localhost_check")
        self.assertEqual(result["exit_code"], 2)
        self.assertNotIn("sensitive", repr(result))
        self.assertNotIn("details", repr(result))
        self.assertEqual(run.call_count, 2)

    def test_timeout_and_unavailable_process_are_generic(self):
        with patch("ansible_local_qualification.subprocess.run", side_effect=subprocess.TimeoutExpired("ansible-playbook", 2)) as run:
            result = qualify_local_cli(timeout_seconds=5, executable_lookup=lambda _name: "/trusted/bin/ansible-playbook")
        self.assertEqual(result["state"], "timeout")
        self.assertEqual(result["code"], "ansible_cli_timeout")
        self.assertEqual(result["stage"], "syntax_check")
        self.assertNotIn("stdout", result)
        self.assertEqual(run.call_count, 1)
        with patch("ansible_local_qualification.subprocess.run", side_effect=OSError("sensitive path")):
            unavailable = qualify_local_cli(executable_lookup=lambda _name: "/trusted/bin/ansible-playbook")
        self.assertEqual(unavailable["state"], "unavailable")
        self.assertEqual(unavailable["code"], "ansible_cli_unavailable")
        self.assertNotIn("sensitive path", repr(unavailable))

    def test_real_ansible_cli_only_when_ci_explicitly_requests_it(self):
        if os.environ.get("ORS_R120_RUN_REAL_CLI") != "1":
            self.skipTest("real CLI is enabled only in the isolated Linux CI gate")
        if shutil.which("ansible-playbook") is None:
            self.fail("CI opted into real Ansible qualification but ansible-playbook is missing")
        result = qualify_local_cli(timeout_seconds=25)
        self.assertEqual(result["state"], "qualified", result)
        self.assertFalse(result["remote_target_used"])
        self.assertFalse(result["output_retained"])


if __name__ == "__main__":
    unittest.main()
