"""R120: qualify the installed Ansible CLI using a fixed localhost-only playbook.

This is a QA smoke harness, not the production Ansible runner. It never accepts
operator playbooks, inventories, hosts, credentials, or extra CLI arguments. Both
commands use generated files, force the local connection and limit execution to
localhost, discard child output, and run in a private temporary workspace.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable

_MAX_TIMEOUT_SECONDS = 30
_MIN_TIMEOUT_SECONDS = 5
_PLAYBOOK = """- name: OpenRemote Studio local-only qualification
  hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: Execute deterministic local diagnostic
      ansible.builtin.debug:
        msg: ORS_R120_LOCAL_ONLY_QUALIFICATION
"""
_INVENTORY = "localhost ansible_connection=local\n"


def _result(state: str, code: str, *, stage: str, exit_code=None):
    """Keep results deliberately small and independent of child output."""
    result = {
        "state": state,
        "code": code,
        "stage": stage,
        "remote_target_used": False,
        "output_retained": False,
    }
    if type(exit_code) is int:
        result["exit_code"] = exit_code
    return result


def _controlled_environment(root: Path) -> dict[str, str]:
    """Build an allowlisted child environment; do not inherit user/agent config."""
    env: dict[str, str] = {}
    for name in (
        "PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT",
        "LANG", "LC_ALL", "TMP", "TEMP", "TMPDIR",
    ):
        value = os.environ.get(name)
        if value:
            env[name] = value

    home = root / "home"
    env.update({
        "HOME": str(home),
        "USERPROFILE": str(home),
        "ANSIBLE_CONFIG": str(root / "ansible.cfg"),
        "ANSIBLE_HOME": str(root / "ansible-home"),
        "ANSIBLE_LOCAL_TEMP": str(root / "local"),
        "ANSIBLE_REMOTE_TEMP": str(root / "remote"),
        "ANSIBLE_ROLES_PATH": str(root / "roles"),
        "ANSIBLE_COLLECTIONS_PATH": str(root / "collections"),
        "ANSIBLE_NOCOLOR": "1",
        "ANSIBLE_FORCE_COLOR": "0",
        "ANSIBLE_HOST_KEY_CHECKING": "True",
        "ANSIBLE_RETRY_FILES_ENABLED": "False",
        "ANSIBLE_DEPRECATION_WARNINGS": "False",
        "PYTHONNOUSERSITE": "1",
    })
    return env


def _invoke(executable: str, arguments: list[str], *, cwd: Path,
            env: dict[str, str], timeout_seconds: float):
    """Run one fixed CLI stage without shell or output capture."""
    if timeout_seconds <= 0:
        return "timeout", None
    try:
        completed = subprocess.run(
            [executable, *arguments],
            cwd=str(cwd),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            close_fds=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "timeout", None
    except (OSError, ValueError):
        return "unavailable", None
    code = getattr(completed, "returncode", None)
    if type(code) is not int:
        return "unavailable", None
    return ("ok", 0) if code == 0 else ("failed", code)


def qualify_local_cli(*, timeout_seconds: int = 20,
                      executable_lookup: Callable[[str], str | None] | None = None):
    """Run syntax-check plus check-mode against generated localhost-only input.

    No remote target, operator input, SSH key or network integration is involved.
    Every subprocess receives a fresh allowlisted environment and a hard timeout.
    The result never includes stdout/stderr, command output, or filesystem content.
    """
    if type(timeout_seconds) is not int or not _MIN_TIMEOUT_SECONDS <= timeout_seconds <= _MAX_TIMEOUT_SECONDS:
        return _result("rejected", "ansible_timeout_invalid", stage="preflight")

    lookup = executable_lookup or shutil.which
    try:
        executable = lookup("ansible-playbook")
    except Exception:
        executable = None
    if not isinstance(executable, str) or not executable.strip():
        return _result("unavailable", "ansible_cli_not_installed", stage="discovery")
    executable = os.path.abspath(executable)

    deadline = time.monotonic() + timeout_seconds
    try:
        with tempfile.TemporaryDirectory(prefix="ors-ansible-r120-") as directory:
            root = Path(directory)
            try:
                os.chmod(root, 0o700)
            except OSError:
                # Windows uses its inherited temporary-directory ACL; the runner
                # does not claim a DACL inspection from this QA-only harness.
                pass
            for name in ("home", "ansible-home", "local", "remote", "roles", "collections"):
                child = root / name
                child.mkdir(mode=0o700)

            playbook = root / "local-qualification.yml"
            inventory = root / "localhost.ini"
            playbook.write_text(_PLAYBOOK, encoding="utf-8", newline="\n")
            inventory.write_text(_INVENTORY, encoding="ascii", newline="\n")
            config = root / "ansible.cfg"
            config.write_text(
                "[defaults]\n"
                "host_key_checking = True\n"
                "retry_files_enabled = False\n"
                "deprecation_warnings = False\n"
                "interpreter_python = auto_silent\n"
                f"roles_path = {root / 'roles'}\n"
                f"collections_path = {root / 'collections'}\n"
                f"local_tmp = {root / 'local'}\n"
                f"remote_tmp = {root / 'remote'}\n"
                "collections_scan_sys_path = False\n",
                encoding="utf-8", newline="\n",
            )
            for path in (playbook, inventory, config):
                try:
                    os.chmod(path, 0o600)
                except OSError:
                    pass

            env = _controlled_environment(root)
            common = ["--inventory", str(inventory), "--limit", "localhost"]
            remaining = deadline - time.monotonic()
            syntax_state, syntax_code = _invoke(
                executable,
                [*common, "--syntax-check", str(playbook)],
                cwd=root, env=env, timeout_seconds=remaining,
            )
            if syntax_state != "ok":
                code = {
                    "failed": "ansible_cli_syntax_check_failed",
                    "timeout": "ansible_cli_timeout",
                    "unavailable": "ansible_cli_unavailable",
                }[syntax_state]
                return _result(syntax_state, code, stage="syntax_check", exit_code=syntax_code)

            remaining = deadline - time.monotonic()
            check_state, check_code = _invoke(
                executable,
                [*common, "--connection", "local", "--forks", "1",
                 "--check", "--diff", str(playbook)],
                cwd=root, env=env, timeout_seconds=remaining,
            )
            if check_state != "ok":
                code = {
                    "failed": "ansible_cli_local_check_failed",
                    "timeout": "ansible_cli_timeout",
                    "unavailable": "ansible_cli_unavailable",
                }[check_state]
                return _result(check_state, code, stage="localhost_check", exit_code=check_code)

            return {
                "state": "qualified",
                "code": "ansible_cli_local_only_pass",
                "stage": "complete",
                "stages": {"syntax_check": "passed", "localhost_check": "passed"},
                "remote_target_used": False,
                "output_retained": False,
            }
    except (OSError, RuntimeError, ValueError):
        return _result("unavailable", "ansible_local_workspace_unavailable", stage="workspace")


if __name__ == "__main__":  # safe manual QA entry point
    import json
    print(json.dumps(qualify_local_cli(), sort_keys=True))
