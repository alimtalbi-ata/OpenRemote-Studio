"""R119 OpenSSH known_hosts hashed-name and IP-literal validation tests.

The integration test uses the local OpenSSH ssh-keygen utility only; it never
contacts a remote host or uses an operator/production key.
Author: Abdelhalim Talbi.
"""
import base64
import hashlib
import hmac
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from ansible_preflight import AnsiblePreflightError, _validate_known_hosts

PLACEHOLDER_KEY = base64.b64encode(b"R119 synthetic host public key bytes").decode("ascii")
SALT = b"R119-fixed-salt-0123"  # exactly 20 bytes


def _hashed_host(host: str, salt: bytes = SALT) -> str:
    digest = hmac.new(salt, host.encode("utf-8"), hashlib.sha1).digest()
    return "|1|{}|{}".format(
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def _validate_host_field(host_field: str) -> None:
    line = f"{host_field} ssh-ed25519 {PLACEHOLDER_KEY}\n"
    _validate_known_hosts(line.encode("utf-8"))


class KnownHostsR119Tests(unittest.TestCase):
    def test_accepts_plain_hostname_ipv4_and_existing_ca_marker(self):
        _validate_host_field("server.example.test")
        _validate_host_field("192.0.2.10")
        _validate_known_hosts(
            f"@cert-authority server.example.test ssh-ed25519 {PLACEHOLDER_KEY}\n".encode()
        )

    def test_rejects_invalid_key_type_and_unknown_marker(self):
        for line in (
            f"server.example.test unsupported/keytype {PLACEHOLDER_KEY}\\n",
            f"@unknown server.example.test ssh-ed25519 {PLACEHOLDER_KEY}\\n",
        ):
            with self.subTest(line=line):
                with self.assertRaises(AnsiblePreflightError):
                    _validate_known_hosts(line.encode("utf-8"))

    def test_accepts_canonical_openssh_hashed_host_and_mixed_host_list(self):
        hashed = _hashed_host("server.example.test")
        _validate_host_field(hashed)
        _validate_host_field(f"server.example.test,{hashed}")

    def test_accepts_ipv6_and_bracketed_host_port_forms(self):
        for host in (
            "2001:db8::1",
            "[2001:db8::1]:2222",
            "[server.example.test]:22",
            "[192.0.2.10]:65535",
        ):
            with self.subTest(host=host):
                _validate_host_field(host)

    def test_rejects_unknown_hash_version_bad_base64_and_wrong_digest_sizes(self):
        good_salt = base64.b64encode(SALT).decode("ascii")
        good_digest = base64.b64encode(b"d" * 20).decode("ascii")
        bad_entries = (
            "|2|" + good_salt + "|" + good_digest,
            "|1|not*base64|" + good_digest,
            "|1|" + base64.b64encode(b"s" * 19).decode("ascii") + "|" + good_digest,
            "|1|" + good_salt + "|" + base64.b64encode(b"d" * 19).decode("ascii"),
            "|1||" + good_digest,
            "|1|" + good_salt + "|",
        )
        for host in bad_entries:
            with self.subTest(host=host):
                with self.assertRaises(AnsiblePreflightError) as error:
                    _validate_host_field(host)
                self.assertEqual(str(error.exception), "ansible_known_hosts_invalid")

    def test_rejects_malformed_ipv6_and_out_of_range_ports(self):
        bad_hosts = (
            "[2001:db8::zz]:22",
            "[2001:db8::1]:0",
            "[2001:db8::1]:65536",
            "[server.example.test]:00000",
            "server.example.test:2222",
            "2001:db8::1%eth0",
        )
        for host in bad_hosts:
            with self.subTest(host=host):
                with self.assertRaises(AnsiblePreflightError):
                    _validate_host_field(host)

    def test_rejects_empty_or_ambiguous_comma_separated_fields(self):
        for host in (
            "server.example.test,",
            ",server.example.test",
            "server.example.test,,192.0.2.1",
        ):
            with self.subTest(host=host):
                with self.assertRaises(AnsiblePreflightError):
                    _validate_host_field(host)

    @unittest.skipUnless(shutil.which("ssh-keygen"), "OpenSSH ssh-keygen is not installed")
    def test_real_ssh_keygen_hash_output_is_accepted(self):
        ssh_keygen = shutil.which("ssh-keygen")
        self.assertIsNotNone(ssh_keygen)
        with tempfile.TemporaryDirectory(prefix="ors-r119-") as temp:
            root = Path(temp)
            key_path = root / "fixture-key"
            known_hosts = root / "known_hosts"
            subprocess.run(
                [ssh_keygen, "-q", "-t", "ed25519", "-N", "", "-f", str(key_path)],
                check=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=15,
            )
            public_fields = Path(str(key_path) + ".pub").read_text(encoding="utf-8").split()
            self.assertEqual(public_fields[0], "ssh-ed25519")
            known_hosts.write_text(
                f"server.example.test {public_fields[0]} {public_fields[1]}\n",
                encoding="ascii",
            )
            subprocess.run(
                [ssh_keygen, "-H", "-f", str(known_hosts)],
                check=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=15,
            )
            hashed_line = next(
                line for line in known_hosts.read_text(encoding="utf-8").splitlines()
                if line and not line.startswith("#")
            )
            self.assertTrue(hashed_line.split()[0].startswith("|1|"))
            _validate_known_hosts(known_hosts.read_bytes())


if __name__ == "__main__":
    unittest.main()
