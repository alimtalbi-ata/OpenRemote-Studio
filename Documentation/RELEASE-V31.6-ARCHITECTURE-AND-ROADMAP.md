# OpenRemote Studio V31.6 — Architecture, quality and forward plan

Author: Abdelhalim Talbi

## Delivered scope (source changes)
- SFTP journal: terminal transfer states cannot be overwritten by late callbacks.
- SFTP journal: persisted progress is monotonic and excludes boolean values.
- SFTP queue: progress cannot regress; cancellation does not free the active slot until worker completion; completion requires a real boolean.
- Transfers workspace: reopening after tab closure no longer passes None to Qt indexOf.
- Regression tests cover the above failure modes.

## Security and reliability invariants
- A transfer cancelled or completed is never silently resurrected.
- Cancellation requests do not imply a successful interruption until worker acknowledgement.
- UI journal remains read-only; malformed records fail closed.
- No automatic transfer replay after restart.
- V31.6 CI must prove isolated Windows portable startup and installer packaging.

## Qualification evidence and limitations
GitHub Actions produces native Windows binaries and test logs. This document is a scope and release plan, not evidence that any particular CI run passed. Hardware and remote-server interoperability, code signing, and real-world SSH/SFTP/RDP/VNC acceptance remain separate qualification gates. No screenshots are claimed.

## Next architecture milestones
- V31.7: transfer cancellation state machine (requested, acknowledged, completed), remote size and content verification, resumable transfers with stable identity and change detection.
- V31.8: keyboard-only workflows, accessible labels, navigation focus order, tab lifecycle tests using real Qt in Windows CI.
- V31.9: structured audit trail with retention/redaction, explicit session ownership, no secrets in logs.
- V32.0: provider adapters for SSH/SFTP/RDP/VNC, contract tests, capability matrix, plugin boundaries.
- V32.1: end-to-end Windows test matrix across clean hosts, installation/uninstallation and independent portable distribution.

## Architectural debt and decisions
Application/qt_app.py remains a large Qt monolith; split progressively into presenter, domain services, and infrastructure adapters without changing behavior in one large rewrite. Use typed data boundaries, fail-closed validation, versioned migrations, and explicit evidence at every release.
