"""Minimal privacy-safe GUI startup evidence. Author: Abdelhalim Talbi.

Never persist exception messages, traceback, credentials or connection names.
"""
import json
import os
from pathlib import Path
from datetime import datetime, timezone

STAGES = frozenset({'qt_init', 'main_window', 'event_loop', 'shutdown'})

def diagnostics_path(env=None):
    env = os.environ if env is None else env
    root = env.get('LOCALAPPDATA') or env.get('APPDATA')
    if not root:
        root = str(Path.home() / '.openremote')
    return Path(root) / 'OpenRemoteStudio' / 'diagnostics' / 'startup.jsonl'

def record_startup(stage, outcome, error=None, path=None):
    if stage not in STAGES or outcome not in ('ok', 'failed'):
        raise ValueError('invalid startup state')
    if error is not None and not isinstance(error, BaseException):
        raise ValueError('invalid error')
    event = {'schema': 'openremote.startup.v1', 'utc': datetime.now(timezone.utc).isoformat(),
             'stage': stage, 'outcome': outcome}
    if error is not None:
        event['error_type'] = type(error).__name__[:80]
    target = Path(path) if path is not None else diagnostics_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    # Best-effort local evidence. No exception messages or stack traces.
    with target.open('a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=True, separators=(',', ':')) + '\n')
    return event

def safe_record(stage, outcome, error=None, path=None):
    try:
        return record_startup(stage, outcome, error, path)
    except (OSError, ValueError):
        return None
