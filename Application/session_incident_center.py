"""Read-only incident index for Sessions. Author: Abdelhalim Talbi."""
from session_diagnostics import explain_session_failure
import re

_SECRET_KEYS = (
    r"aws[_-]?secret[_-]?access[_-]?key|secret[_-]?access[_-]?key|"
    r"client[_-]?secret|proxy-authorization|authorization|private[_-]?key|"
    r"access[_-]?key|access[_-]?token|refresh[_-]?token|session[_-]?token|"
    r"oauth[_-]?token|id[_-]?token|csrf[_-]?token|x-api-key|x-auth-token|"
    r"api[_-]?key|set-cookie|password|passwd|pwd|token|secret|cookie"
)
_SECRET_ASSIGNMENT = re.compile(
    r'''(?ix)
    (?P<prefix>(?<![\w-])["']?(?:''' + _SECRET_KEYS + r''')["']?\s*[:=]\s*)
    (?P<value>
        "(?:\\.|[^"\\])*"
        | '(?:\\.|[^'\\])*'
        | (?:Bearer|Basic)\s+(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\S+)
        | \[[A-Z0-9_]+\]
        | [^\s,;}\]]+
    )
    '''
)
_CLI_SECRET = re.compile(
    r'''(?ix)
    (?P<prefix>(?<![\w-])--?(?:''' + _SECRET_KEYS + r''')\s*(?:=|\s+))
    (?P<value>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\[[A-Z0-9_]+\]|[^\s,;]+)
    '''
)
_BEARER_OR_BASIC = re.compile(
    r'''(?i)\b(?P<scheme>Bearer|Basic)\s+(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\S+)'''
)
_JWT = re.compile(
    r'''(?<![A-Za-z0-9_-])(eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,})(?![A-Za-z0-9_-])'''
)
_URL_CREDENTIALS = re.compile(r"(?i)(://[^\s/@:]+:)[^\s/@]+(@)")
_COOKIE_HEADER = re.compile(r'''(?im)(?<![\w-])["']?(cookie|set-cookie)["']?\s*[:=]\s*([^\r\n]+)''')
_PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN (?P<label>(?:[A-Z0-9-]+ )?PRIVATE KEY|PGP PRIVATE KEY BLOCK)-----"
    r".*?(?:-----END (?P=label)-----|\Z)",
    re.IGNORECASE | re.DOTALL,
)


_ENV_SECRET_ASSIGNMENT = re.compile(
    r'''(?ix)
    (?P<prefix>(?<![A-Za-z0-9_])["']?(?P<key>[A-Za-z_][A-Za-z0-9_]{0,127})["']?\s*[:=]\s*)
    (?P<value>
        "(?:\\.|[^"\\])*"
        | '(?:\\.|[^'\\])*'
        | \{[^\r\n]*\}
        | \[[^\]\r\n]*\]
        | [^\s,;}]+
    )
    '''
)


def _is_sensitive_env_key(name):
    """Recognize credential-bearing variable names, including product prefixes."""
    normalized = re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")
    parts = set(filter(None, normalized.split("_")))
    if parts.intersection({
        "SECRET", "TOKEN", "PASSWORD", "PASSWD", "PWD", "CREDENTIAL",
        "CREDENTIALS", "COOKIE", "AUTHORIZATION", "BEARER", "JWT",
        "KUBECONFIG", "NETRC",
    }):
        return True
    if any(marker in normalized for marker in (
        "API_KEY", "ACCESS_KEY", "PRIVATE_KEY", "SIGNING_KEY",
        "ENCRYPTION_KEY", "GPG_KEY", "SSH_KEY", "AUTH_CONFIG",
        "AUTH_KEY", "AUTH_TOKEN", "CONNECTION_STRING", "CONNECTION_URI",
        "DATABASE_URL", "DB_URL", "REDIS_URL", "MONGO_URL", "JDBC_URL",
        "APPLICATION_CREDENTIALS",
    )):
        return True
    if normalized.endswith((
        "SECRET", "TOKEN", "PASSWORD", "PASSWD", "PWD", "CREDENTIAL",
        "CREDENTIALS",
    )):
        return True
    return normalized == "AUTH" or normalized.endswith("_AUTH")


def _redact_environment_assignment(match):
    # Preserve the more specific R128 marker when the value is already a JWT.
    if match.group("key").upper() == "JWT" and "[REDACTED_JWT]" in match.group("value"):
        return match.group(0)
    if _is_sensitive_env_key(match.group("key")):
        return match.group("prefix") + "[REDACTED]"
    return match.group(0)


def _safe_text(value, limit):
    """Normalize plain scalars and redact common secret formats without stringifying arbitrary objects."""
    if type(value) is str:
        text = value[:4096]
    elif type(value) in (int, float, bool):
        text = str(value)
    else:
        # External adapter objects may have a hostile or sensitive __str__.
        text = ""
    text = _PRIVATE_KEY_BLOCK.sub("[REDACTED_PRIVATE_KEY_BLOCK]", text)
    text = _URL_CREDENTIALS.sub(r"\1[REDACTED]\2", text)
    text = _SECRET_ASSIGNMENT.sub(lambda match: match.group("prefix") + "[REDACTED]", text)
    text = _CLI_SECRET.sub(lambda match: match.group("prefix") + "[REDACTED]", text)
    text = _BEARER_OR_BASIC.sub(lambda match: match.group("scheme") + " [REDACTED]", text)
    text = _JWT.sub("[REDACTED_JWT]", text)
    text = _ENV_SECRET_ASSIGNMENT.sub(_redact_environment_assignment, text)
    # Cookie headers may contain multiple key/value pairs; redact the remainder
    # of that header line so a second cookie is not left behind after a semicolon.
    text = _COOKIE_HEADER.sub(lambda match: match.group(1) + "=[REDACTED]", text)
    text = "".join(character if character.isprintable() else " " for character in text)
    return text[:limit]

def incident_index(rows, query='', only_errors=True):
    """Build navigable cards without trusting PID alone as session identity."""
    if not isinstance(rows,(list,tuple)):
        raise TypeError('rows must be a sequence')
    result=[]
    term=str(query).strip().casefold()
    for ordinal,row in enumerate(rows):
        if not isinstance(row,dict):
            continue
        state=row.get('status')
        failed=state=='exited' and type(row.get('exit_code')) is int and row['exit_code']!=0
        uncertain=state=='unknown' or (state=='exited' and row.get('exit_code') is None)
        if only_errors and not (failed or uncertain):
            continue
        identity=row.get('connection_id')
        if not isinstance(identity,str) or not identity.strip():
            continue
        name=str(row.get('name') or identity)
        proto=str(row.get('protocol') or '').upper()
        if term and term not in (name+' '+identity+' '+proto).casefold():
            continue
        report=explain_session_failure(row)
        # Row position is only a navigation hint; consumer must revalidate process identity.
        result.append({'connection_id':identity,'row_index':ordinal,'name':name,
            'protocol':proto,'status':state,'diagnostic':report,
            'requires_revalidation':True,'can_reconnect':False})
    return sorted(result,key=lambda x:(0 if x['diagnostic']['severity']=='error' else 1,x['name'].casefold(),x['row_index']))

def incident_counts(items):
    return {'total':len(items),'errors':sum(i['diagnostic']['severity']=='error' for i in items),
            'uncertain':sum(i['diagnostic']['severity']=='warning' for i in items)}

def format_incident_index(items):
    if not items:return 'Aucune erreur locale ou session incertaine détectée.'
    return '\n\n'.join(f"{i['name']} [{i['protocol']}] — {i['diagnostic']['summary']}\n"+
        '\n'.join('• '+action for action in i['diagnostic']['actions']) for i in items)


def incident_export(items):
    """Export a sanitized support summary; never export raw process arguments or secrets."""
    if not isinstance(items,(list,tuple)):
        raise TypeError('items must be a sequence')
    safe=[]
    for item in items:
        if not isinstance(item,dict):
            continue
        diagnostic=item.get('diagnostic') or {}
        if not isinstance(diagnostic,dict):
            diagnostic={}
        safe.append({'connection_id':_safe_text(item.get('connection_id',''),128),
                     'protocol':_safe_text(item.get('protocol',''),16),
                     'severity':_safe_text(diagnostic.get('severity','unknown'),32),
                     'summary':_safe_text(diagnostic.get('summary',''),500),
                     'requires_revalidation':True,'can_reconnect':False})
    return {'schema':'openremote.incidents.v1','incidents':safe,'count':len(safe)}
