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
