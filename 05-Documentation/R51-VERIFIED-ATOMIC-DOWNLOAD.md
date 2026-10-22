# OpenRemote Studio R51 — verified atomic SFTP downloads
Author: Abdelhalim Talbi
Date: 2026-10-22

Problem: a successful SFTP get() call can return fewer bytes than the remote file, yet the previous atomic download implementation published that truncated file.

Change: add an opt-in verify_remote_size boolean to download_atomic. In strict mode compare local temporary file size with remote size before/after get(), compare available modification timestamps, and fail without replacing an existing destination when metadata changes. Qt SFTP downloads and the live OpenSSH smoke test should use strict mode.

Validation requirements: deterministic fake SFTP tests for truncated payload, remote mutation, cancellation, cleanup, and compatibility; OpenSSH live protocol run; Windows Native build; cumulative verification. These latter gates are not claimed until CI executes on the published commit.

Limits: remote size and timestamp are not a cryptographic hash or atomic remote snapshot. Do not infer content integrity for same-size corruption.