"""Safe local client launch diagnostics. No secrets or network probes.
Author: Abdelhalim Talbi.
"""
import errno

CLIENT_LABELS = {'SSH': 'ssh', 'SFTP': 'sftp', 'RDP': 'mstsc', 'VNC': 'vncviewer'}

def launch_failure(protocol, error):
    """Classify local process-launch failures without echoing exception text/paths."""
    client = CLIENT_LABELS.get(protocol, 'client externe')
    if isinstance(error, FileNotFoundError):
        code, advice = 'client_missing', 'Installez le client ou corrigez son chemin dans PATH.'
    elif isinstance(error, PermissionError):
        code, advice = 'access_denied', 'Vérifiez les droits d’exécution et la stratégie de sécurité Windows.'
    elif isinstance(error, OSError) and error.errno == errno.ENOEXEC:
        code, advice = 'invalid_executable', 'Vérifiez la compatibilité et l’intégrité du programme client.'
    elif isinstance(error, OSError):
        code, advice = 'process_error', 'Consultez les journaux Windows et vérifiez le programme client.'
    elif isinstance(error, (ValueError, RuntimeError)):
        code, advice = 'preflight_rejected', 'Vérifiez les paramètres et le précontrôle de cette connexion.'
    else:
        raise TypeError('unsupported launch failure')
    return {'scope': 'local_launch_only', 'code': code,
            'message': f'Impossible de lancer {client}. {advice}',
            'remote_status_verified': False}
