"""Safe, deterministic local-client inventory filtering. Author: Abdelhalim Talbi."""
from client_readiness_view import readiness_rows

def visible_local_clients(report, issues_only=False):
    """Return display rows and (visible,total) counts, without altering the report."""
    rows = readiness_rows(report)
    raw = report["rows"][:32]
    if len(raw) != len(rows):
        raise ValueError("Malformed inventory row")
    if issues_only:
        rows = [row for row, item in zip(rows, raw) if item.get("ready") is not True]
    return rows, len(rows), len(raw)
