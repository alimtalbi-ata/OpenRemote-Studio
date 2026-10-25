"""Generate versioned Word/PDF release dossier from repository facts.
Only used in CI; generated examples are explicitly illustrative.
Author: Abdelhalim Talbi.
"""
from pathlib import Path
from docx import Document
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from xml.sax.saxutils import escape

root = Path(__file__).resolve().parents[1]
version = (root / "VERSION.txt").read_text(encoding="utf-8").strip()
dest = root / "05-Documentation"
dest.mkdir(exist_ok=True)
sections = [
    ("Scope", "OpenRemote Studio V" + version + " — Windows candidate. Author: Abdelhalim Talbi."),
    ("Primary workflows", "Connections, Sessions, Diagnostics and Transfers are the four main views. Ctrl+1 to Ctrl+4 navigate them."),
    ("SFTP history", "The Transfers workspace shows local, read-only transfer journal entries. Revisiting the tab refreshes the journal. Corrupt journal snapshots clear the table and show a neutral error."),
    ("Session safety", "Reconnect is rejected if local session observations are malformed or a sibling local process is still active. A local process does not prove remote connectivity."),
    ("Quality gates", "GitHub Windows CI checks Python unit tests, PowerShell syntax, PE/ZIP structure, isolated portable startup, runtime DLLs and Qt platform plugin."),
    ("Known limits", "Real-world multi-host SSH/SFTP/RDP/VNC acceptance tests, signed binaries and real UI screenshots are not evidenced by this document. No fictional screenshots are included."),
    ("Next versions", "V31.6: interrupted SFTP transfer integrity. V31.7: GUI interaction and accessibility. V31.8: structured security audit. V31.9: Windows end-to-end qualification."),
]
# Version-specific addendum, sourced from the tracked R96 design note.
# This is architecture documentation, NOT an assertion that live WinRM passed.
if (dest / "V31.8-R96-WINRM-SERVICES-QT.md").is_file():
    sections.extend([
        ("R96 - Windows services read-only", "Outils > Services Windows WinRM: a separate Qt tab displays name, display label, state and startup mode. Up to 128 entries are shown. A text filter works locally and never performs a new WinRM POST."),
        ("R96 - consent and lifecycle", "Offline by default. HTTPS certificate validation and explicit consent are mandatory. A transient masked password or injected runtime provider is used; the UI does not persist or export secrets. A generation gate rejects stale results after consent or endpoint changes, and prevents concurrent POST while a previous call drains."),
        ("R96 - quality cases", "Eight Qt tests with synthetic WinRM clients cover offline safety, local filtering, truncation, stale cancellation, redacted exceptions, malformed data, empty display names and unsupported operations. Seven backend R95 tests cover the fixed CIM query and bounded normalization. CI results must be checked against the exact commit."),
        ("R96 - unverified boundaries", "No real Windows Server WinRM HTTPS acceptance test, physical Windows operator walkthrough, vault reference integration, R96 panel screenshot, or pywinrm runtime bundling is asserted. The OpenSSH integration suite does not qualify WinRM. No simulated screenshot is presented as real."),
        ("R96 - architecture", "Qt WinRMServicesPanel -> single QRunnable with fixed operation 'services' -> WinRMServicesReadOnly -> pywinrm optional TLS-validated transport -> fixed Get-CimInstance Win32_Service -> validated JSON <=128 rows -> local QTreeWidget filter. No arbitrary PowerShell or remote writes."),
    ])
# R99 release addendum: source facts and explicit unverified boundaries.
if (dest / "V31.8-R99-WINRM-WINCRED-REFERENCE.md").is_file():
    sections.extend([
        ("R99 - WinCred reference", "The optional wincred:<target> field in both Windows inventory and services panels resolves an existing Windows Credential Manager Generic Credential inside the worker after explicit operator consent. No credential creation, export or persistence is performed by the WinRM panel."),
        ("R99 - fail closed", "The target uses a bounded ASCII allowlist. Invalid references are rejected before network access. Provider exceptions become fixed error codes; no raw error or secret reaches the UI. Editing the endpoint, account or reference revokes consent and cancels pending work."),
        ("R99 - verification", "Six pure contract tests and five Qt synthetic transport tests are included. The Windows CI must run them at the exact source SHA. Local POSIX Qt tests may be skipped if PySide6 is absent."),
        ("R99 - unverified", "No real Windows Server WinRM HTTPS acceptance test, actual Windows Credential Manager integration test on a workstation, physical Windows operator test or screenshot of the R99 reference flow is asserted. pywinrm remains optional; Windows installer inclusion is not established by these tests."),
    ])
# R100: distinguish real local WinCred QA from unverified remote WinRM.
if (dest / "V31.8-R100-WINCRED-NATIVE-BOUNDARIES.md").is_file():
    sections.extend([
        ("R100 - WinCred memory boundary", "Generic Credential blobs are rejected if the native type is wrong, the byte length is zero, odd or greater than 2560, or decoded UTF-16 contains NUL. Native memory is freed on success and rejected blobs."),
        ("R100 - real Windows CredMan test", "The Windows CI test writes a random session-only Generic Credential to the isolated runner account, reads it through the production wincred: resolver and deletes it in finally. No remote server is contacted. Results must be checked on the exact commit."),
        ("R100 - limits", "Real Windows Credential Manager testing does NOT qualify WinRM HTTPS against Windows Server, TLS trust chains, NTLM/Kerberos in production, physical Windows UI operation or pywinrm bundling. No screenshots are invented."),
    ])
# R104: WinRM remote display fields are untrusted, including injected adapters.
if (dest / "V31.8-R104-WINRM-DISPLAY-TRUST.md").is_file():
    sections.extend([
        ("R104 - Unicode display trust", "The read-only WinRM backend rejects invisible Unicode format characters, bidirectional controls, surrogates, line separators and Unicode noncharacters in remote CIM display fields. International visible text remains supported."),
        ("R104 - Qt validation boundary", "The Windows OS/disks and services Qt panels revalidate untrusted normalized results, including custom injected adapters, before populating the UI. Invalid disks, impossible free-space counts and spoofed service names are rejected with neutral errors."),
        ("R104 - evidence and limits", "Five backend tests passed locally; three Qt tests require Windows PySide6 CI and must be checked on the exact commit. No real Windows Server WinRM HTTPS session, CA/NTLM authentication or physical Windows operator walkthrough has been qualified. No R104 screenshot is claimed."),
    ])
# R103: external WinRM exception boundary and Qt signal redaction.
if (dest / "V31.8-R103-WINRM-EXCEPTION-BOUNDARIES.md").is_file():
    sections.extend([
        ("R103 - untrusted WinRM errors", "External session factories, run_ps calls and response properties may throw exceptions containing secrets. Both read-only backends now normalize all external exceptions to fixed error codes and suppress chained provider context."),
        ("R103 - Qt signal privacy", "The Qt worker emits only allowlisted error codes. Unexpected WinRMError strings from injected clients cannot enter the signal payload. Explicit consent, verified HTTPS, offline default and fixed CIM read-only commands are unchanged."),
        ("R103 - qualification boundary", "Hostile in-memory transports are covered by backend tests; Qt signal tests require PySide6 and Windows CI. Real Windows Server WinRM HTTPS, CA/NTLM/Kerberos and physical operator UI remain unverified. No R103 screenshots are claimed."),
    ])
# R102: reject ambiguous remote WinRM responses without leaking provider errors.
if (dest / "V31.8-R102-WINRM-STRICT-RESPONSE.md").is_file():
    sections.extend([
        ("R102 - strict WinRM reply decoding", "OS/disk and Windows service inventory now share a bounded UTF-8 JSON decoder: 1-65536 bytes, unique object keys, finite JSON values and integer status code. Invalid or deeply nested payloads are rejected."),
        ("R102 - redaction and offline guarantee", "Unexpected transport response property errors are replaced with fixed error codes without exposing provider exceptions or remote stderr. No network is attempted without explicit operator consent; fixed CIM queries and TLS validation are unchanged."),
        ("R102 - qualification boundary", "Six new synthetic-transport tests plus existing R93 and R95 regression tests run locally. A real Windows Server WinRM HTTPS session, CA validation, NTLM/Kerberos in situ, physical Windows operator test and R102 screenshots remain unverified."),
    ])

# R101: packaged WinRM transport does not certify a real remote WinRM session.
if (dest / "V31.8-R101-WINRM-PACKAGED-RUNTIME.md").is_file():
    sections.extend([
        ("R101 - Windows WinRM packaged runtime", "The Windows build installs pywinrm 0.5.x and explicitly collects winrm and spnego modules in PyInstaller. The executable supports an offline dependency self-check without network or credential access."),
        ("R101 - binary acceptance gate", "The build executes the offline WinRM dependency self-check against both PyInstaller output and the independently extracted portable ZIP, with bounded timeouts. Missing modules block publication. Windows CI results must be checked at the exact commit."),
        ("R101 - unchanged security model", "WinRM remains disabled by default and uses only fixed read-only CIM queries over HTTPS with certificate validation. Credentials are resolved in memory after operator consent; errors are redacted."),
        ("R101 - unverified limits", "An importable WinRM dependency graph is not a successful connection to a real Windows Server. TLS trust, NTLM authentication, least-privilege remote access, physical Windows operator tests and real R101 screenshots remain unverified. The architecture SVG is conceptual, not a screenshot."),
    ])
doc = Document()
doc.add_heading("OpenRemote Studio V" + version, 0)
doc.add_paragraph("Windows release quality dossier | Abdelhalim Talbi")
for heading, body in sections:
    doc.add_heading(heading, level=1)
    doc.add_paragraph(body)
doc.save(dest / ("Dossier-V" + version + ".docx"))
styles = getSampleStyleSheet()
story = [Paragraph(escape("OpenRemote Studio V" + version), styles["Title"]), Spacer(1, 14)]
for heading, body in sections:
    story.extend([Paragraph(escape(heading), styles["Heading2"]), Paragraph(escape(body), styles["BodyText"]), Spacer(1, 12)])
SimpleDocTemplate(str(dest / ("Dossier-V" + version + ".pdf"))).build(story)
print("Generated versioned DOCX/PDF release dossier for V" + version)
