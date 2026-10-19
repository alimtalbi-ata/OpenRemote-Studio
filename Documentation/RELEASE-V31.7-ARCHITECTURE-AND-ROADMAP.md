# OpenRemote Studio V31.7 — Windows cumulative delivery

Author: Abdelhalim Talbi

## Changes
- Resumable SFTP downloads now re-check remote file size immediately before atomic local publication.
- Remote size metadata must be a non-negative integer, not a boolean or coercible string.
- A changed remote size blocks replacement of an existing local file.
- Regression tests cover changed size, partial preservation, and malformed remote size.

## Verification and limits
The versioned Windows native qualification workflow runs tests, binary structure validation, isolated portable smoke tests, and installer qualification. A successful CI run is necessary before calling V31.7 qualified. File-size equality is not a cryptographic content-integrity guarantee. Remote metadata and content can still race between checks.

## Next engineering priorities
- V31.8: cryptographic end-to-end verification where the remote protocol supports it, remote identity pinning, and cancellation acknowledgements.
- V31.9: Qt UI automation with real keyboard focus and navigation tests.
- V32.0: domain service extraction from qt_app.py, adapter contract tests and secure audit event schemas.
- V32.1: multi-environment Windows acceptance tests and release reproducibility.

## Cumulative archive contract
One versioned ZIP should contain Windows installer and portable binaries, a source snapshot, DOCX/PDF documentation, CI reports, and SHA-256 checksums. Never present binaries from a previous version as current.
