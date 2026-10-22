# R52 — SFTP verified atomic download

Author: Abdelhalim Talbi.

Scope: verify remote size and mtime before publishing an atomic local download. On any mismatch or cancellation, preserve the previous destination and remove the temporary file. This is not a cryptographic integrity guarantee.

Acceptance gates: deterministic unit tests; OpenSSH real transfer; Windows native and cumulative CI on the same commit; verified Windows Setup/Portable SHA-256. No automatic merge.

Status: implementation pending code publication; do not claim CI qualification for this document alone.
