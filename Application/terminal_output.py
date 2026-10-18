"""Bounded output rendering helpers for SSH command pane. Author: Abdelhalim Talbi."""
import re
ANSI_RE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\))")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

def readable_output(data: bytes, limit: int = 65536) -> str:
    """Bound a single chunk and remove terminal control sequences before showing text."""
    if limit < 1: raise ValueError("limit must be positive")
    data = bytes(data)[-limit:]
    return CONTROL_RE.sub("", ANSI_RE.sub("", data.decode("utf-8", errors="replace")))

def command_is_valid(value: str, max_length: int = 4096) -> bool:
    return bool(value.strip()) and len(value) <= max_length and not any(ch in value for ch in ("\x00", "\r", "\n"))
