"""R116: static Ansible preflight and strictly allowlisted SSH check-mode runner.

The analyzer is offline. Remote execution is always opt-in, uses a pinned known_hosts
file, public-key authentication only, a minimal builtin-module allowlist, bounded
runtime, and discards all child output. No playbook stdout/stderr is captured.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import base64
import ipaddress
import os
import re
import shlex
import shutil
import signal
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable

try:
    import yaml
except ImportError:  # Optional capability; offline application remains available.
    yaml = None

MAX_PLAYBOOK_BYTES = 1024 * 1024
MAX_INVENTORY_BYTES = 256 * 1024
MAX_KNOWN_HOSTS_BYTES = 1024 * 1024
MAX_PRIVATE_KEY_BYTES = 1024 * 1024
MAX_PLAYS = 20
MAX_TASKS = 256
MAX_HOSTS = 100
MAX_TIMEOUT_SECONDS = 120
_MODULES = frozenset({
    "ansible.builtin.debug",
    "ansible.builtin.ping",
    "ansible.builtin.setup",
    "ansible.builtin.stat",
    "ansible.builtin.service_facts",
    "ansible.builtin.package_facts",
    "ansible.builtin.getent",
})
_GROUP = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
_DNS_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_USERNAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,63}$")
_MODULE_NAME = re.compile(r"^ansible\.builtin\.[a-z_]+$")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_TEMPLATE = re.compile(r"({{|}}|{%|%}|{#|#}|lookup\s*\(|query\s*\()", re.I)


class AnsiblePreflightError(ValueError):
    """Stable public error code; never contains file or transport details."""


def _fail(code: str) -> None:
    raise AnsiblePreflightError(code)


def _optional_yaml():
    if yaml is None:
        _fail("ansible_yaml_dependency_unavailable")
    return yaml


def _read_regular(path_value, limit: int, expected_suffixes=()):
    if not isinstance(path_value, (str, os.PathLike)):
        _fail("ansible_invalid_path")
    raw_path = os.fspath(path_value)
    if not raw_path or len(raw_path) > 4096 or _CONTROL.search(raw_path):
        _fail("ansible_invalid_path")
    path = Path(raw_path).expanduser()
    try:
        if path.is_symlink():
            _fail("ansible_symlink_input_rejected")
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size < 1:
            _fail("ansible_regular_file_required")
        if info.st_size > limit:
            _fail("ansible_input_too_large")
        if expected_suffixes and path.suffix.lower() not in expected_suffixes:
            _fail("ansible_invalid_file_extension")
        data = path.read_bytes()
    except AnsiblePreflightError:
        raise
    except (OSError, ValueError):
        _fail("ansible_input_unavailable")
    if not data or len(data) > limit:
        _fail("ansible_input_too_large" if len(data) > limit else "ansible_regular_file_required")
    return path, data


def _static_text(value, *, maximum: int, code: str):
    if not isinstance(value, str) or not value or len(value) > maximum or _CONTROL.search(value):
        _fail(code)
    if _TEMPLATE.search(value):
        _fail("ansible_dynamic_expression_rejected")
    return value


def _valid_host(value):
    if not isinstance(value, str) or not value or len(value) > 253 or _CONTROL.search(value):
        return False
    if value == "localhost":
        return True
    try:
        ipaddress.IPv4Address(value)
        return True
    except ipaddress.AddressValueError:
        pass
    # Deliberately static ASCII hostnames only; no inventory variables, IPv6
    # inventory syntax, shell metacharacters, commas, or Ansible host patterns.
    candidate = value[:-1] if value.endswith(".") else value
    if not candidate or any(not _DNS_LABEL.fullmatch(label) for label in candidate.split(".")):
        return False
    return not all(label.isdigit() for label in candidate.split("."))


def _parse_inventory(data: bytes):
    try:
        text = data.decode("utf-8-sig", errors="strict")
    except UnicodeError:
        _fail("ansible_inventory_not_utf8")
    groups = {}
    current = None
    line_count = 0
    for raw_line in text.splitlines():
        line_count += 1
        if line_count > 10000:
            _fail("ansible_inventory_too_many_lines")
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        if line.startswith("["):
            match = re.fullmatch(r"\[([A-Za-z][A-Za-z0-9_-]{0,63})\]", line)
            if not match:
                _fail("ansible_inventory_syntax_unsupported")
            current = match.group(1)
            if current.lower() in {"all", "ungrouped"} or current in groups:
                _fail("ansible_inventory_group_ambiguous")
            groups[current] = []
            continue
        if current is None:
            _fail("ansible_inventory_group_required")
        tokens = line.split()
        if len(tokens) != 1 or not _valid_host(tokens[0]):
            _fail("ansible_inventory_host_vars_or_pattern_rejected")
        if tokens[0] in groups[current]:
            _fail("ansible_inventory_duplicate_host")
        groups[current].append(tokens[0])
    if not groups or any(not members for members in groups.values()):
        _fail("ansible_inventory_empty_group")
    hosts = sorted({host for members in groups.values() for host in members})
    if not hosts:
        _fail("ansible_inventory_empty")
    if len(hosts) > MAX_HOSTS:
        _fail("ansible_inventory_host_limit")
    return groups, hosts


if yaml is not None:
    class _UniqueSafeLoader(yaml.SafeLoader):
        """PyYAML safe loader that rejects duplicate mapping keys."""

    def _construct_unique_mapping(loader, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError:
                _fail("ansible_yaml_unhashable_key")
            if duplicate:
                _fail("ansible_yaml_duplicate_key")
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    _UniqueSafeLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
    )


def _load_yaml(data: bytes):
    library = _optional_yaml()
    try:
        text = data.decode("utf-8-sig", errors="strict")
        if _CONTROL.search(text):
            _fail("ansible_yaml_control_character")
        # Anchors, aliases and explicit tags make static review harder and are
        # intentionally outside this small preflight language.
        for token in library.scan(text):
            if isinstance(token, (library.tokens.AnchorToken, library.tokens.AliasToken,
                                  library.tokens.TagToken)):
                _fail("ansible_yaml_anchor_alias_or_tag_rejected")
        documents = list(library.load_all(text, Loader=_UniqueSafeLoader))
    except AnsiblePreflightError:
        raise
    except Exception:
        _fail("ansible_yaml_invalid")
    if len(documents) != 1 or not isinstance(documents[0], list):
        _fail("ansible_playbook_must_be_one_list")
    plays = documents[0]
    if not 1 <= len(plays) <= MAX_PLAYS:
        _fail("ansible_play_count_limit")
    return plays


def _validate_args(module: str, args):
    if args is None:
        args = {}
    if not isinstance(args, dict) or any(not isinstance(k, str) for k in args):
        _fail("ansible_module_args_invalid")
    allowed = {
        "ansible.builtin.debug": {"msg"},
        "ansible.builtin.ping": {"data"},
        "ansible.builtin.setup": {"gather_subset"},
        "ansible.builtin.stat": {"path", "follow", "get_checksum"},
        "ansible.builtin.service_facts": set(),
        "ansible.builtin.package_facts": {"manager"},
        "ansible.builtin.getent": {"database", "key", "fail_key"},
    }[module]
    if set(args) - allowed:
        _fail("ansible_module_option_rejected")
    # Static strings only; Jinja/lookup expansion is never accepted.
    def check_strings(value):
        if isinstance(value, str):
            _static_text(value, maximum=1024, code="ansible_module_value_invalid")
        elif isinstance(value, list):
            if len(value) > 16:
                _fail("ansible_module_value_invalid")
            for item in value:
                check_strings(item)
        elif isinstance(value, dict):
            _fail("ansible_module_option_rejected")
        elif value is not None and type(value) not in (bool, int, float):
            _fail("ansible_module_value_invalid")
    check_strings(args)

    if module == "ansible.builtin.debug":
        if set(args) - {"msg"} or ("msg" in args and not isinstance(args["msg"], str)):
            _fail("ansible_debug_options_invalid")
        if "msg" in args and len(args["msg"]) > 1024:
            _fail("ansible_debug_message_too_long")
    elif module == "ansible.builtin.ping":
        if set(args) - {"data"} or ("data" in args and not isinstance(args["data"], str)):
            _fail("ansible_ping_options_invalid")
    elif module == "ansible.builtin.setup":
        if args.get("gather_subset") != ["min"]:
            _fail("ansible_setup_requires_minimal_subset")
    elif module == "ansible.builtin.stat":
        if (set(args) != {"path", "follow", "get_checksum"}
                or not isinstance(args.get("path"), str)
                or args.get("follow") is not False
                or args.get("get_checksum") is not False):
            _fail("ansible_stat_requires_no_follow_no_checksum")
        path = args["path"]
        if (not path.startswith("/") or path.startswith("//") or "/../" in path
                or path.endswith("/..") or "\\" in path):
            _fail("ansible_stat_path_rejected")
    elif module == "ansible.builtin.package_facts":
        if args and args.get("manager") not in {"auto", "apt", "rpm", "apk", "pacman"}:
            _fail("ansible_package_manager_rejected")
    elif module == "ansible.builtin.getent":
        if args.get("database") not in {
            "passwd", "group", "hosts", "services", "protocols", "networks"
        }:
            _fail("ansible_getent_database_rejected")
        if "key" in args and (not isinstance(args["key"], str) or len(args["key"]) > 256):
            _fail("ansible_getent_key_invalid")
        if "fail_key" in args and type(args["fail_key"]) is not bool:
            _fail("ansible_getent_fail_key_invalid")
    return


def _validate_playbook(plays, groups):
    task_count = 0
    module_counts = {}
    safe_plays = []
    for play in plays:
        if not isinstance(play, dict) or set(play) - {"name", "hosts", "gather_facts", "tasks"}:
            _fail("ansible_play_option_rejected")
        if set(play) != {"name", "hosts", "gather_facts", "tasks"}:
            _fail("ansible_play_required_field_missing")
        name = _static_text(play["name"], maximum=120, code="ansible_play_name_invalid")
        target = play["hosts"]
        if not isinstance(target, str) or (target != "all" and target not in groups):
            _fail("ansible_target_group_not_in_inventory")
        if play["gather_facts"] is not False:
            _fail("ansible_gather_facts_must_be_false")
        tasks = play["tasks"]
        if not isinstance(tasks, list):
            _fail("ansible_tasks_must_be_list")
        safe_tasks = []
        for task in tasks:
            task_count += 1
            if task_count > MAX_TASKS:
                _fail("ansible_task_limit")
            if (not isinstance(task, dict)
                    or set(task) - {"name", "tags"} - _MODULES
                    or "name" not in task):
                _fail("ansible_task_schema_rejected")
            module_keys = set(task).intersection(_MODULES)
            if len(module_keys) != 1 or len(set(task).intersection(
                    {"shell", "command", "raw", "script", "include_tasks", "import_tasks",
                     "include_role", "import_role", "copy", "template", "file",
                     "uri", "get_url", "git", "package", "apt", "yum", "dnf",
                     "user", "group", "cron", "lineinfile", "replace", "blockinfile"})):
                _fail("ansible_module_not_allowlisted")
            task_name = _static_text(task["name"], maximum=120, code="ansible_task_name_invalid")
            if "tags" in task:
                tags = task["tags"]
                if not isinstance(tags, list) or len(tags) > 16:
                    _fail("ansible_task_tags_invalid")
                for tag in tags:
                    _static_text(tag, maximum=64, code="ansible_task_tags_invalid")
            module = next(iter(module_keys))
            _validate_args(module, task[module])
            safe_tasks.append({"name": task_name, "module": module})
            module_counts[module] = module_counts.get(module, 0) + 1
        if not safe_tasks:
            _fail("ansible_empty_task_list")
        safe_plays.append({"name": name, "hosts": target, "tasks": safe_tasks})
    if not task_count:
        _fail("ansible_empty_playbook")
    return safe_plays, task_count, module_counts


def _analyze_bytes(playbook_path, playbook_bytes, inventory_path, inventory_bytes):
    groups, hosts = _parse_inventory(inventory_bytes)
    plays = _validate_playbook(_load_yaml(playbook_bytes), groups)
    safe_plays, task_count, module_counts = plays
    if any(play["hosts"] != "all" and play["hosts"] not in groups for play in safe_plays):
        _fail("ansible_target_group_not_in_inventory")
    import hashlib
    return {
        "state": "ok",
        "read_only": True,
        "playbook_name": playbook_path.name[:128],
        "inventory_name": inventory_path.name[:128],
        "playbook_sha256": hashlib.sha256(playbook_bytes).hexdigest(),
        "inventory_sha256": hashlib.sha256(inventory_bytes).hexdigest(),
        "groups": sorted(groups),
        "host_count": len(hosts),
        "play_count": len(safe_plays),
        "task_count": task_count,
        "module_counts": dict(sorted(module_counts.items())),
        "plays": safe_plays,
        "remote_execution": False,
        "output_retained": False,
    }


def analyze_playbook(playbook_path, inventory_path):
    """Validate a constrained static playbook and inventory without network access."""
    pb_path, pb_bytes = _read_regular(playbook_path, MAX_PLAYBOOK_BYTES, (".yml", ".yaml"))
    inv_path, inv_bytes = _read_regular(inventory_path, MAX_INVENTORY_BYTES, (".ini",))
    return _analyze_bytes(pb_path, pb_bytes, inv_path, inv_bytes)


def _validate_known_hosts(data: bytes):
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeError:
        _fail("ansible_known_hosts_invalid")
    entries = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if _CONTROL.search(line):
            _fail("ansible_known_hosts_invalid")
        parts = line.split()
        if parts and parts[0] in {"@cert-authority", "@revoked"}:
            parts = parts[1:]
        if len(parts) < 3 or not re.fullmatch(r"[A-Za-z0-9@._+-]{1,80}", parts[1]):
            _fail("ansible_known_hosts_invalid")
        try:
            key = base64.b64decode(parts[2].encode("ascii"), validate=True)
        except (ValueError, UnicodeError):
            _fail("ansible_known_hosts_invalid")
        if len(key) < 16 or len(parts[0]) > 4096:
            _fail("ansible_known_hosts_invalid")
        entries += 1
        if entries > 10000:
            _fail("ansible_known_hosts_invalid")
    if not entries:
        _fail("ansible_known_hosts_empty")


def _cancelled(cancelled):
    if cancelled is None:
        return False
    if not callable(cancelled):
        _fail("ansible_invalid_cancellation")
    try:
        return bool(cancelled())
    except Exception:
        return True


def _stop_process(process):
    try:
        if process.poll() is not None:
            return
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=0.5)
        except Exception:
            if os.name == "nt":
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=1)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def _run_one(executable, args, env, cwd, deadline, cancelled):
    if _cancelled(cancelled):
        return "cancelled", None
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return "timeout", None
    try:
        process = subprocess.Popen(
            [executable, *args], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            shell=False, cwd=str(cwd), env=env, close_fds=True,
            start_new_session=(os.name != "nt"),
            creationflags=(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0),
        )
    except Exception:
        return "unavailable", None
    while True:
        if _cancelled(cancelled):
            _stop_process(process)
            return "cancelled", None
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _stop_process(process)
            return "timeout", None
        try:
            code = process.wait(timeout=min(0.1, remaining))
            return ("ok", int(code)) if code == 0 else ("failed", int(code))
        except subprocess.TimeoutExpired:
            continue
        except Exception:
            _stop_process(process)
            return "unavailable", None


def run_check_mode(playbook_path, inventory_path, known_hosts_path, private_key_path, *,
                   username="", consent=False, timeout_seconds=60, cancelled=None,
                   executable_lookup=None):
    """Run the validated allowlist using Ansible --check --diff after explicit consent.

    All child stdout/stderr is discarded. The caller receives only a generic
    status and integer exit code; no command output, key bytes, or credentials
    are captured, logged, persisted, or exported.
    """
    if consent is not True:
        _fail("ansible_explicit_consent_required")
    if (type(timeout_seconds) is not int or not 10 <= timeout_seconds <= MAX_TIMEOUT_SECONDS):
        _fail("ansible_timeout_invalid")
    if not isinstance(username, str) or (username and not _USERNAME.fullmatch(username)):
        _fail("ansible_username_invalid")
    if _cancelled(cancelled):
        return {"state": "cancelled", "read_only": True, "output_retained": False}
    lookup = executable_lookup or shutil.which
    try:
        executable = lookup("ansible-playbook")
    except Exception:
        executable = None
    if not executable:
        return {"state": "unavailable", "code": "ansible_cli_not_installed",
                "read_only": True, "output_retained": False}

    pb_path, pb_bytes = _read_regular(playbook_path, MAX_PLAYBOOK_BYTES, (".yml", ".yaml"))
    inv_path, inv_bytes = _read_regular(inventory_path, MAX_INVENTORY_BYTES, (".ini",))
    kh_path, kh_bytes = _read_regular(known_hosts_path, MAX_KNOWN_HOSTS_BYTES)
    key_path, key_bytes = _read_regular(private_key_path, MAX_PRIVATE_KEY_BYTES)
    _validate_known_hosts(kh_bytes)
    analysis = _analyze_bytes(pb_path, pb_bytes, inv_path, inv_bytes)
    # Re-parse immediately before staging; the subprocess sees only these bounded
    # snapshots, not mutable paths supplied by the operator.
    deadline = time.monotonic() + timeout_seconds
    try:
        with tempfile.TemporaryDirectory(prefix="ors-ansible-r116-") as temporary:
            root = Path(temporary)
            home = root / "home"
            ssh_home = home / ".ssh"
            config_home = root / "config"
            local_tmp = root / "local"
            remote_tmp = root / "remote"
            collections = root / "collections"
            library = root / "library"
            roles = root / "roles"
            for directory in (home, ssh_home, config_home, local_tmp, remote_tmp, collections, library, roles):
                directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            staged_pb = root / ("playbook" + pb_path.suffix.lower())
            staged_inv = root / "inventory.ini"
            staged_hosts = ssh_home / "known_hosts"
            staged_key = ssh_home / "id_key"
            empty_hosts = ssh_home / "empty_known_hosts"
            empty_config = ssh_home / "empty_config"
            staged_pb.write_bytes(pb_bytes)
            staged_inv.write_bytes(inv_bytes)
            staged_hosts.write_bytes(kh_bytes)
            staged_key.write_bytes(key_bytes)
            empty_hosts.write_bytes(b"")
            empty_config.write_bytes(b"")
            if os.name != "nt":
                for file_path in (staged_pb, staged_inv, staged_hosts, staged_key, empty_hosts, empty_config):
                    os.chmod(file_path, 0o600)
            if _cancelled(cancelled):
                return {"state": "cancelled", "read_only": True, "output_retained": False}

            # No operator/global SSH config, proxy command, agent, password, custom
            # Ansible plugin/collection path or inherited ANSIBLE_* override.
            ssh_options = [
                "-F", shlex.quote(empty_config.as_posix()),
                "-o", "BatchMode=yes",
                "-o", "PreferredAuthentications=publickey",
                "-o", "PasswordAuthentication=no",
                "-o", "KbdInteractiveAuthentication=no",
                "-o", "StrictHostKeyChecking=yes",
                "-o", f"UserKnownHostsFile={shlex.quote(staged_hosts.as_posix())}",
                "-o", f"GlobalKnownHostsFile={shlex.quote(empty_hosts.as_posix())}",
                "-o", "ForwardAgent=no",
                "-o", "ClearAllForwardings=yes",
                "-o", "PermitLocalCommand=no",
                "-o", "ProxyCommand=none",
                "-o", "ControlMaster=no",
                "-o", "ControlPath=none",
                "-o", "ControlPersist=no",
                "-o", "ConnectTimeout=5",
                "-o", "ServerAliveInterval=5",
                "-o", "ServerAliveCountMax=1",
                "-i", shlex.quote(staged_key.as_posix()),
            ]
            cfg = (
                "[defaults]\n"
                "host_key_checking = True\n"
                "retry_files_enabled = False\n"
                "display_args_to_stdout = False\n"
                "forks = 1\n"
                "timeout = 5\n"
                "gathering = explicit\n"
                f"local_tmp = {local_tmp.as_posix()}\n"
                f"remote_tmp = {remote_tmp.as_posix()}\n"
                f"collections_path = {collections.as_posix()}\n"
                f"roles_path = {roles.as_posix()}\n"
                f"library = {library.as_posix()}\n"
                "\n[ssh_connection]\n"
                f"ssh_args = {' '.join(ssh_options)}\n"
                "pipelining = False\n"
            )
            config_file = config_home / "ansible.cfg"
            config_file.write_text(cfg, encoding="utf-8")
            allowed_env_keys = {
                "PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT",
                "TEMP", "TMP", "TMPDIR",
            }
            env = {key: value for key, value in os.environ.items()
                   if key.upper() in allowed_env_keys and isinstance(value, str)}
            env["HOME"] = str(home)
            env["USERPROFILE"] = str(home)
            env["ANSIBLE_CONFIG"] = str(config_file)
            env["ANSIBLE_HOST_KEY_CHECKING"] = "True"
            env["ANSIBLE_NOCOLOR"] = "1"
            env["ANSIBLE_RETRY_FILES_ENABLED"] = "False"
            command_common = [
                "--inventory", str(staged_inv),
                "--connection", "ssh",
                "--forks", "1",
                "--timeout", "5",
            ]
            if username:
                command_common.extend(["--user", username])
            syntax_args = [*command_common, "--syntax-check", str(staged_pb)]
            stage, code = _run_one(executable, syntax_args, env, root, deadline, cancelled)
            if stage != "ok":
                return {
                    "state": stage, "stage": "syntax", "exit_code": code,
                    "read_only": True, "output_retained": False,
                    "playbook_name": analysis["playbook_name"],
                    "host_count": analysis["host_count"], "task_count": analysis["task_count"],
                }
            if _cancelled(cancelled):
                return {"state": "cancelled", "read_only": True, "output_retained": False}
            check_args = [
                *command_common, "--check", "--diff", str(staged_pb),
            ]
            stage, code = _run_one(executable, check_args, env, root, deadline, cancelled)
            mapped_state = {
                "ok": "check_succeeded", "failed": "check_failed",
                "timeout": "timeout", "cancelled": "cancelled",
                "unavailable": "unavailable",
            }[stage]
            return {
                "state": mapped_state, "stage": "check", "exit_code": code,
                "read_only": True, "output_retained": False,
                "playbook_name": analysis["playbook_name"],
                "host_count": analysis["host_count"], "task_count": analysis["task_count"],
            }
    except AnsiblePreflightError:
        raise
    except Exception:
        _fail("ansible_runner_unavailable")


def main(argv=None):
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Offline Ansible playbook preflight (no network)")
    parser.add_argument("--playbook", required=True)
    parser.add_argument("--inventory", required=True)
    args = parser.parse_args(argv)
    try:
        result = analyze_playbook(args.playbook, args.inventory)
    except AnsiblePreflightError as exc:
        result = {"state": "error", "code": str(exc), "read_only": True,
                  "remote_execution": False}
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result.get("state") == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
