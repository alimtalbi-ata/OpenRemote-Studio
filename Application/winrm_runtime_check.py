"""Offline packaged WinRM dependency probe. No network or secret resolution.

Author: Abdelhalim Talbi.
"""


def runtime_dependency_available():
    """Verify optional WinRM transport modules exist in the *running* interpreter.

    Used by the frozen executable smoke gate. No Session is instantiated.
    """
    try:
        import winrm
        import requests_ntlm
        import spnego
        from winrm.protocol import Protocol
        from requests.adapters import HTTPAdapter
    except (ImportError, AttributeError):
        return False
    return (callable(getattr(winrm, 'Session', None))
            and callable(Protocol) and callable(HTTPAdapter)
            and callable(getattr(requests_ntlm, 'HttpNtlmAuth', None))
            and callable(getattr(spnego, 'client', None)))
