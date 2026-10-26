"""R116/R118 Ansible preflight and trust-staging tests; no real controller."""
import base64
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ansible_preflight import (
    AnsiblePreflightError, analyze_playbook, run_check_mode, connection_fingerprints,
)
from winrm_readonly import private_temporary_directory, _sddl_is_private

PLAYBOOK = """- name: Read-only diagnostic
  hosts: servers
  gather_facts: false
  tasks:
    - name: Verify SSH transport
      ansible.builtin.ping: {}
    - name: Collect minimal facts
      ansible.builtin.setup:
        gather_subset: [min]
    - name: Read service list
      ansible.builtin.service_facts: {}
"""
INVENTORY = """[servers]
server1.example.test
server2.example.test
"""
KNOWN_HOSTS = (
    "server1.example.test ssh-ed25519 "
    + base64.b64encode(b"R116 synthetic host public key bytes!!").decode("ascii")
    + "\n"
)
KEY_BYTES = b"R116_PRIVATE_KEY_SENTINEL_not_a_real_key\n"


class StuckProcess:
    def __init__(self, args, **kwargs):
        self.args = list(args)
        self.kwargs = kwargs
        self.pid = 999999

    def wait(self, timeout=None):
        raise subprocess.TimeoutExpired("ansible-playbook", timeout)

    def poll(self):
        return None

    def terminate(self):
        pass

    def kill(self):
        pass


class FakeProcess:
    next_codes = []

    def __init__(self, args, **kwargs):
        self.args = list(args)
        self.kwargs = kwargs
        self.pid = 999999
        self._code = self.next_codes.pop(0) if self.next_codes else 0
        self._terminated = False

    def wait(self, timeout=None):
        if self._terminated:
            return -15
        return self._code

    def poll(self):
        return -15 if self._terminated else self._code

    def terminate(self):
        self._terminated = True

    def kill(self):
        self._terminated = True


class AnsiblePreflightR116Tests(unittest.TestCase):
    def setUp(self):
        # Windows CI fixtures inherit a DACL created by the same verified
        # user+SYSTEM-only directory policy required by the production runner.
        self._temp_context = private_temporary_directory()
        temporary, self._fixture_user_sid = self._temp_context.__enter__()
        self.root = Path(temporary)
        self.playbook = self.root / "safe.yml"
        self.inventory = self.root / "hosts.ini"
        self.known_hosts = self.root / "known_hosts"
        self.key = self.root / "id_key"
        self.write_inputs()

    def tearDown(self):
        self._temp_context.__exit__(None, None, None)

    def write_inputs(self, playbook=PLAYBOOK, inventory=INVENTORY):
        self.playbook.write_text(playbook, encoding="utf-8")
        self.inventory.write_text(inventory, encoding="utf-8")
        self.known_hosts.write_text(KNOWN_HOSTS, encoding="utf-8")
        self.key.write_bytes(KEY_BYTES)
        if os.name != "nt":
            os.chmod(self.key, 0o600)

    def approved_hashes(self):
        """Return the four exact input digests the operator reviewed."""
        report = analyze_playbook(self.playbook, self.inventory)
        trust = connection_fingerprints(self.known_hosts, self.key)
        return {
            "expected_playbook_sha256": report["playbook_sha256"],
            "expected_inventory_sha256": report["inventory_sha256"],
            "expected_known_hosts_sha256": trust["known_hosts_sha256"],
            "expected_private_key_sha256": trust["private_key_sha256"],
        }

    def test_valid_preflight_is_offline_bounded_and_does_not_return_task_text(self):
        result = analyze_playbook(self.playbook, self.inventory)
        self.assertEqual(result["state"], "ok")
        self.assertTrue(result["read_only"])
        self.assertFalse(result["remote_execution"])
        self.assertFalse(result["output_retained"])
        self.assertEqual(result["host_count"], 2)
        self.assertEqual(result["task_count"], 3)
        self.assertEqual(result["play_count"], 1)
        self.assertEqual(result["module_counts"]["ansible.builtin.ping"], 1)
        self.assertNotIn("tasks", result)
        self.assertNotIn("password", repr(result).lower())
        self.assertEqual(len(result["playbook_sha256"]), 64)
        self.assertEqual(len(result["inventory_sha256"]), 64)

    def test_command_shell_role_and_other_modules_are_rejected(self):
        unsafe = PLAYBOOK.replace(
            "ansible.builtin.ping: {}", "ansible.builtin.command: {cmd: id}"
        )
        self.write_inputs(unsafe)
        with self.assertRaisesRegex(AnsiblePreflightError, "ansible_module_not_allowlisted"):
            analyze_playbook(self.playbook, self.inventory)

    def test_dynamic_hosts_patterns_and_implicit_facts_are_rejected(self):
        for replacement, expected in (
            ("hosts: servers", "hosts: 'all:!server1'"),
            ("gather_facts: false", "gather_facts: true"),
        ):
            self.write_inputs(PLAYBOOK.replace(replacement, expected))
            with self.subTest(expected=expected), self.assertRaises(AnsiblePreflightError):
                analyze_playbook(self.playbook, self.inventory)

    def test_duplicate_yaml_keys_fail_closed(self):
        self.write_inputs(PLAYBOOK.replace("hosts: servers", "hosts: servers\n  hosts: all"))
        with self.assertRaisesRegex(AnsiblePreflightError, "ansible_yaml_duplicate_key"):
            analyze_playbook(self.playbook, self.inventory)

    def test_unknown_group_is_rejected(self):
        self.write_inputs(PLAYBOOK.replace("hosts: servers", "hosts: other"))
        with self.assertRaisesRegex(AnsiblePreflightError, "ansible_target_group_not_in_inventory"):
            analyze_playbook(self.playbook, self.inventory)

    def test_jinja_aliases_and_explicit_yaml_tags_are_rejected(self):
        self.write_inputs(PLAYBOOK.replace("Verify SSH transport", "\"{{ lookup('env','X') }}\""))
        with self.assertRaisesRegex(AnsiblePreflightError, "ansible_dynamic_expression_rejected"):
            analyze_playbook(self.playbook, self.inventory)
        self.write_inputs(PLAYBOOK.replace("gather_facts: false", "gather_facts: !!str false"))
        with self.assertRaisesRegex(AnsiblePreflightError, "ansible_yaml_anchor_alias_or_tag_rejected"):
            analyze_playbook(self.playbook, self.inventory)
        self.write_inputs(PLAYBOOK.replace("gather_facts: false", "gather_facts: &facts false"))
        with self.assertRaisesRegex(AnsiblePreflightError, "ansible_yaml_anchor_alias_or_tag_rejected"):
            analyze_playbook(self.playbook, self.inventory)

    def test_inventory_variables_inline_comments_and_dynamic_groups_are_rejected(self):
        for inventory in (
            "[servers:vars]\nansible_user=admin\n",
            "[servers]\nserver1.example.test ansible_user=admin\n",
            "[servers]\nserver1.example.test # comment\n",
        ):
            self.write_inputs(inventory=inventory)
            with self.subTest(inventory=inventory), self.assertRaises(AnsiblePreflightError):
                analyze_playbook(self.playbook, self.inventory)

    def test_setup_must_be_minimal_and_stat_must_not_follow_or_hash(self):
        self.write_inputs(PLAYBOOK.replace("gather_subset: [min]", "gather_subset: [all]"))
        with self.assertRaisesRegex(AnsiblePreflightError, "ansible_setup_requires_minimal_subset"):
            analyze_playbook(self.playbook, self.inventory)
        unsafe = PLAYBOOK.replace(
            "ansible.builtin.service_facts: {}",
            "ansible.builtin.stat:\n        path: /etc/shadow\n        follow: true\n        get_checksum: false",
        )
        self.write_inputs(unsafe)
        with self.assertRaisesRegex(AnsiblePreflightError, "ansible_stat_requires_no_follow_no_checksum"):
            analyze_playbook(self.playbook, self.inventory)

    def test_oversized_input_is_rejected(self):
        self.playbook.write_bytes(b"#" + b"x" * (1024 * 1024))
        with self.assertRaisesRegex(AnsiblePreflightError, "ansible_input_too_large"):
            analyze_playbook(self.playbook, self.inventory)

    def test_symlink_input_is_rejected_when_platform_allows_symlink_creation(self):
        link = self.root / "linked.yml"
        try:
            link.symlink_to(self.playbook)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation is not permitted in this runner")
        with self.assertRaisesRegex(AnsiblePreflightError, "ansible_symlink_input_rejected"):
            analyze_playbook(link, self.inventory)

    def test_selected_host_trust_and_key_fingerprints_never_return_file_bytes(self):
        fingerprints = connection_fingerprints(self.known_hosts, self.key)
        self.assertEqual(set(fingerprints), {"known_hosts_sha256", "private_key_sha256"})
        self.assertEqual(len(fingerprints["known_hosts_sha256"]), 64)
        self.assertEqual(len(fingerprints["private_key_sha256"]), 64)
        self.assertNotIn("R116_PRIVATE_KEY_SENTINEL", repr(fingerprints))
        self.assertNotIn(KEY_BYTES.decode("utf-8").strip(), repr(fingerprints))

    def test_changed_known_hosts_or_private_key_requires_reapproval_before_spawn(self):
        for changed_file in ("known_hosts", "private_key"):
            with self.subTest(changed_file=changed_file):
                self.write_inputs()
                fingerprints = connection_fingerprints(self.known_hosts, self.key)
                if changed_file == "known_hosts":
                    self.known_hosts.write_text(
                        "server1.example.test ssh-ed25519 "
                        + base64.b64encode(b"DIFFERENT approved fixture key material").decode("ascii")
                        + "\n", encoding="utf-8",
                    )
                else:
                    self.key.write_bytes(b"R116 different key bytes")
                    if os.name != "nt":
                        os.chmod(self.key, 0o600)
                report = analyze_playbook(self.playbook, self.inventory)
                with patch("ansible_preflight.subprocess.Popen") as popen:
                    with self.assertRaisesRegex(AnsiblePreflightError, "ansible_connection_input_changed_reapprove"):
                        run_check_mode(
                            self.playbook, self.inventory, self.known_hosts, self.key,
                            consent=True,
                            expected_playbook_sha256=report["playbook_sha256"],
                            expected_inventory_sha256=report["inventory_sha256"],
                            expected_known_hosts_sha256=fingerprints["known_hosts_sha256"],
                            expected_private_key_sha256=fingerprints["private_key_sha256"],
                            executable_lookup=lambda _name: "/fake/ansible-playbook",
                        )
                popen.assert_not_called()

    def test_runner_requires_all_four_canonical_approval_fingerprints(self):
        approved = self.approved_hashes()
        cases = []
        for missing in approved:
            incomplete = dict(approved)
            del incomplete[missing]
            cases.append((f"missing:{missing}", incomplete))
        for name, bad_value in (
            ("uppercase", "A" * 64),
            ("short", "a" * 63),
            ("non_hex", "g" * 64),
        ):
            malformed = dict(approved)
            malformed["expected_private_key_sha256"] = bad_value
            cases.append((name, malformed))

        for name, kwargs in cases:
            with self.subTest(case=name):
                with patch("ansible_preflight.subprocess.Popen") as popen:
                    with patch("ansible_preflight._private_runner_directory") as staging:
                        with self.assertRaisesRegex(
                            AnsiblePreflightError, "ansible_approval_fingerprints_required"
                        ):
                            run_check_mode(
                                self.playbook, self.inventory, self.known_hosts, self.key,
                                consent=True, executable_lookup=lambda _name: "/fake/ansible-playbook",
                                **kwargs,
                            )
                popen.assert_not_called()
                staging.assert_not_called()

    def test_consent_is_required_before_cli_discovery_or_process_creation(self):
        lookup_calls = []
        with patch("ansible_preflight.subprocess.Popen") as popen:
            with self.assertRaisesRegex(AnsiblePreflightError, "ansible_explicit_consent_required"):
                run_check_mode(
                    self.playbook, self.inventory, self.known_hosts, self.key,
                    consent=False, executable_lookup=lambda name: lookup_calls.append(name) or "/fake/ansible-playbook",
                )
        self.assertEqual(lookup_calls, [])
        popen.assert_not_called()

    def test_missing_ansible_cli_is_explicit_and_never_spawns(self):
        with patch("ansible_preflight.subprocess.Popen") as popen:
            result = run_check_mode(
                self.playbook, self.inventory, self.known_hosts, self.key,
                consent=True, executable_lookup=lambda _name: None,
            )
        self.assertEqual(result["state"], "unavailable")
        self.assertEqual(result["code"], "ansible_cli_not_installed")
        self.assertFalse(result["output_retained"])
        popen.assert_not_called()

    def test_runner_uses_syntax_check_then_check_diff_with_pinned_host_keys(self):
        captured = []
        def fake_popen(args, **kwargs):
            captured.append((list(args), kwargs, Path(kwargs["env"]["ANSIBLE_CONFIG"]).read_text("utf-8")))
            return FakeProcess(args, **kwargs)
        FakeProcess.next_codes = [0, 0]
        approval = self.approved_hashes()
        with patch("ansible_preflight.subprocess.Popen", side_effect=fake_popen):
            result = run_check_mode(
                self.playbook, self.inventory, self.known_hosts, self.key,
                consent=True, timeout_seconds=30, username="ops_readonly",
                **approval,
                executable_lookup=lambda _name: "/fake/ansible-playbook",
            )
        self.assertEqual(result["state"], "check_succeeded")
        self.assertEqual(result["stage"], "check")
        self.assertEqual(len(captured), 2)
        self.assertIn("--syntax-check", captured[0][0])
        self.assertIn("--check", captured[1][0])
        self.assertIn("--diff", captured[1][0])
        self.assertIn("--user", captured[1][0])
        for args, kwargs, cfg in captured:
            self.assertFalse(kwargs["shell"])
            self.assertIs(kwargs["stdout"], __import__("subprocess").DEVNULL)
            self.assertIs(kwargs["stderr"], __import__("subprocess").DEVNULL)
            self.assertIs(kwargs["stdin"], __import__("subprocess").DEVNULL)
            self.assertNotIn("R116_PRIVATE_KEY_SENTINEL", " ".join(args))
            self.assertIn("StrictHostKeyChecking=yes", cfg)
            self.assertIn("PasswordAuthentication=no", cfg)
            self.assertIn("ProxyCommand=none", cfg)
            self.assertIn("UserKnownHostsFile=", cfg)
            self.assertIn("GlobalKnownHostsFile=", cfg)
            self.assertIn("ForwardAgent=no", cfg)
            self.assertIn("IdentitiesOnly=yes", cfg)
            self.assertIn("IdentityAgent=none", cfg)
            self.assertNotIn("SSH_AUTH_SOCK", kwargs["env"])
            self.assertNotIn("SSH_AGENT_PID", kwargs["env"])
            self.assertNotIn("ANSIBLE_CALLBACK_PLUGINS", kwargs["env"])
            self.assertNotIn("PYTHONPATH", kwargs["env"])
        self.assertNotIn("stdout", result)
        self.assertNotIn("stderr", result)
        self.assertFalse(result["output_retained"])

    def test_changed_bytes_between_review_and_execution_require_reanalysis(self):
        approval = self.approved_hashes()
        self.playbook.write_text(PLAYBOOK.replace("Read-only diagnostic", "Different playbook"), encoding="utf-8")
        with patch("ansible_preflight.subprocess.Popen") as popen:
            with self.assertRaisesRegex(AnsiblePreflightError, "ansible_preflight_changed_reanalyze"):
                run_check_mode(
                    self.playbook, self.inventory, self.known_hosts, self.key,
                    consent=True, **approval,
                    executable_lookup=lambda _name: "/fake/ansible-playbook",
                )
        popen.assert_not_called()

    def test_invalid_known_hosts_and_permissive_posix_private_key_are_rejected(self):
        self.known_hosts.write_text("not a host-key line\n", encoding="utf-8")
        with self.assertRaisesRegex(AnsiblePreflightError, "ansible_known_hosts_invalid"):
            run_check_mode(self.playbook, self.inventory, self.known_hosts, self.key,
                           consent=True, executable_lookup=lambda _name: "/fake/ansible-playbook")
        self.known_hosts.write_text(KNOWN_HOSTS, encoding="utf-8")
        if os.name != "nt":
            os.chmod(self.key, 0o644)
            with self.assertRaisesRegex(AnsiblePreflightError, "ansible_private_key_permissions_too_open"):
                run_check_mode(self.playbook, self.inventory, self.known_hosts, self.key,
                               consent=True, executable_lookup=lambda _name: "/fake/ansible-playbook")

    def test_nonzero_exit_is_neutral_and_never_returns_child_output(self):
        calls = []
        def fake_popen(args, **kwargs):
            calls.append(list(args))
            return FakeProcess(args, **kwargs)
        FakeProcess.next_codes = [0, 4]
        with patch("ansible_preflight.subprocess.Popen", side_effect=fake_popen):
            result = run_check_mode(
                self.playbook, self.inventory, self.known_hosts, self.key,
                consent=True, **self.approved_hashes(),
                executable_lookup=lambda _name: "/fake/ansible-playbook",
            )
        self.assertEqual(result["state"], "check_failed")
        self.assertEqual(result["exit_code"], 4)
        self.assertNotIn("stderr", result)
        self.assertNotIn("stdout", result)

    def test_global_deadline_stops_a_stalled_check_process_without_collecting_output(self):
        def fake_popen(args, **kwargs):
            self.assertIs(kwargs["stdout"], subprocess.DEVNULL)
            self.assertIs(kwargs["stderr"], subprocess.DEVNULL)
            return StuckProcess(args, **kwargs)
        with patch("ansible_preflight.subprocess.Popen", side_effect=fake_popen):
            with patch("ansible_preflight.time.monotonic", side_effect=[0.0, 0.0, 0.0, 11.0]):
                with patch("ansible_preflight._stop_process") as stop:
                    result = run_check_mode(
                        self.playbook, self.inventory, self.known_hosts, self.key,
                        consent=True, timeout_seconds=10, **self.approved_hashes(),
                        executable_lookup=lambda _name: "/fake/ansible-playbook",
                    )
        self.assertEqual(result["state"], "timeout")
        self.assertEqual(result["stage"], "syntax")
        self.assertIsNone(result["exit_code"])
        self.assertNotIn("stdout", result)
        self.assertNotIn("stderr", result)
        stop.assert_called_once()

    def test_cancellation_after_process_start_stops_the_active_child(self):
        states = {"calls": 0}
        def cancelled():
            states["calls"] += 1
            return states["calls"] >= 4
        with patch("ansible_preflight.subprocess.Popen", side_effect=lambda args, **kwargs: StuckProcess(args, **kwargs)):
            with patch("ansible_preflight._stop_process") as stop:
                result = run_check_mode(
                    self.playbook, self.inventory, self.known_hosts, self.key,
                    consent=True, cancelled=cancelled, **self.approved_hashes(),
                    executable_lookup=lambda _name: "/fake/ansible-playbook",
                )
        self.assertEqual(result["state"], "cancelled")
        self.assertEqual(result["stage"], "syntax")
        stop.assert_called_once()

    def test_cancel_before_process_start_returns_cancelled(self):
        calls = []
        with patch("ansible_preflight.subprocess.Popen") as popen:
            result = run_check_mode(
                self.playbook, self.inventory, self.known_hosts, self.key,
                consent=True, cancelled=lambda: True,
                executable_lookup=lambda name: calls.append(name) or "/fake/ansible-playbook",
            )
        self.assertEqual(result["state"], "cancelled")
        self.assertEqual(calls, [])
        popen.assert_not_called()

    def test_windows_acl_policy_accepts_only_private_explicit_or_inherited_file_dacl(self):
        user_sid = "S-1-5-21-101-202-303-1001"
        inherited = f"D:(A;ID;FA;;;{user_sid})(A;ID;FA;;;SY)"
        inherited_nested = f"D:(A;OICIID;FA;;;{user_sid})(A;OICIID;FA;;;SY)"
        explicit_protected = f"D:P(A;;FA;;;{user_sid})(A;;FA;;;SY)"
        explicit_protected_propagating = f"D:P(A;OICI;FA;;;{user_sid})(A;OICI;FA;;;SY)"
        explicit_unprotected = f"D:(A;;FA;;;{user_sid})(A;;FA;;;SY)"
        everyone_added = f"D:P(A;;FA;;;{user_sid})(A;;FA;;;SY)(A;;FA;;;WD)"
        self.assertTrue(_sddl_is_private(inherited, user_sid, directory=False))
        self.assertTrue(_sddl_is_private(inherited_nested, user_sid, directory=False))
        self.assertFalse(_sddl_is_private(explicit_protected, user_sid, directory=False))
        self.assertTrue(_sddl_is_private(
            explicit_protected, user_sid, directory=False, allow_explicit_file=True
        ))
        self.assertTrue(_sddl_is_private(
            explicit_protected_propagating, user_sid, directory=False,
            allow_explicit_file=True,
        ))
        self.assertFalse(_sddl_is_private(
            explicit_unprotected, user_sid, directory=False, allow_explicit_file=True
        ))
        self.assertFalse(_sddl_is_private(
            everyone_added, user_sid, directory=False, allow_explicit_file=True
        ))

    @unittest.skipUnless(os.name == "nt", "native DACL inspection requires Windows")
    def test_windows_acl_inspection_failure_blocks_before_private_key_read(self):
        with patch("winrm_readonly.private_file_acl_is_safe", return_value=False):
            with patch("ansible_preflight._read_regular") as reader:
                with self.assertRaisesRegex(
                    AnsiblePreflightError, "ansible_private_key_acl_unverified"
                ):
                    connection_fingerprints(self.known_hosts, self.key)
        reader.assert_not_called()


    def test_ssh_trust_and_config_files_stay_in_verified_root_and_are_rechecked(self):
        import ansible_preflight

        protected_names = [
            "playbook.yml", "inventory.ini", "known_hosts", "id_key",
            "empty_known_hosts", "empty_config", "ansible.cfg",
        ]
        acl_checked = []
        observed_configs = []
        diagnostics = []
        original_acl_check = ansible_preflight._require_staged_file_acl

        def check(condition, label):
            if not condition:
                diagnostics.append(label)

        def record_acl_check(path, user_sid):
            acl_checked.append(Path(path).name)
            return original_acl_check(path, user_sid)

        def fake_popen(args, **kwargs):
            try:
                config_path = Path(kwargs["env"]["ANSIBLE_CONFIG"])
                root = config_path.parent
                cfg = config_path.read_text(encoding="utf-8")
                check(config_path.name == "ansible.cfg", "ansible_config_not_at_root")
                for name in protected_names:
                    candidate = root / name
                    check(candidate.parent == root, "control_file_not_direct_child:" + name)
                    check(candidate.is_file(), "control_file_missing:" + name)
                check(
                    (root / "known_hosts").read_bytes() == self.known_hosts.read_bytes(),
                    "known_hosts_snapshot_changed",
                )
                check((root / "empty_known_hosts").read_bytes() == b"", "global_known_hosts_not_empty")
                check((root / "empty_config").read_bytes() == b"", "ssh_config_not_empty")
                check((root / "known_hosts").as_posix() in cfg, "selected_known_hosts_path_missing")
                check((root / "empty_known_hosts").as_posix() in cfg, "global_known_hosts_path_missing")
                check((root / "empty_config").as_posix() in cfg, "ssh_config_path_missing")
                check((root / "id_key").as_posix() in cfg, "selected_identity_path_missing")
                check(".ssh/known_hosts" not in cfg, "nested_known_hosts_reference")
                check("IdentitiesOnly=yes" in cfg, "identities_only_missing")
                check("IdentityAgent=none" in cfg, "identity_agent_not_disabled")
                observed_configs.append(cfg)
            except Exception as exc:
                # _run_one deliberately normalizes Popen exceptions; retain only
                # the exception class here so the test itself remains diagnostic
                # without echoing a local path, key, or process command.
                diagnostics.append("fake_popen_inspection_exception:" + type(exc).__name__)
            return FakeProcess(args, **kwargs)

        FakeProcess.next_codes = [0, 0]
        with patch("ansible_preflight.subprocess.Popen", side_effect=fake_popen):
            with patch("ansible_preflight._require_staged_file_acl", side_effect=record_acl_check):
                result = run_check_mode(
                    self.playbook, self.inventory, self.known_hosts, self.key,
                    consent=True, timeout_seconds=30, **self.approved_hashes(),
                    executable_lookup=lambda _name: "/fake/ansible-playbook",
                )

        self.assertEqual(diagnostics, [])
        self.assertEqual(result["state"], "check_succeeded")
        self.assertEqual(len(observed_configs), 2)
        self.assertEqual(acl_checked, protected_names * 3)
        for cfg in observed_configs:
            self.assertIn("StrictHostKeyChecking=yes", cfg)
            self.assertIn("PasswordAuthentication=no", cfg)
            self.assertIn("ProxyCommand=none", cfg)
            self.assertIn("ControlMaster=no", cfg)
        self.assertFalse(result["output_retained"])
        self.assertNotIn("stdout", result)
        self.assertNotIn("stderr", result)


    def test_runner_refuses_to_spawn_when_staged_known_hosts_acl_is_unverified(self):
        import ansible_preflight

        checked = []
        original_acl_check = ansible_preflight._require_staged_file_acl

        def reject_selected_host_trust(path, user_sid):
            name = Path(path).name
            checked.append(name)
            if name == "known_hosts":
                raise AnsiblePreflightError("ansible_staging_acl_unverified")
            return original_acl_check(path, user_sid)

        with patch("ansible_preflight.subprocess.Popen") as popen:
            with patch(
                "ansible_preflight._require_staged_file_acl",
                side_effect=reject_selected_host_trust,
            ):
                with self.assertRaisesRegex(
                    AnsiblePreflightError, "ansible_staging_acl_unverified"
                ):
                    run_check_mode(
                        self.playbook, self.inventory, self.known_hosts, self.key,
                        consent=True, timeout_seconds=30, **self.approved_hashes(),
                        executable_lookup=lambda _name: "/fake/ansible-playbook",
                    )

        self.assertEqual(checked, ["playbook.yml", "inventory.ini", "known_hosts"])
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
