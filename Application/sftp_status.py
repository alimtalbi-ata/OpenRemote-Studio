"""Safe, actionable SFTP status messages for the Qt cockpit.

Never interpolate untrusted exception messages, file paths, credentials or
network endpoints into the UI. Author: Abdelhalim Talbi.
"""

_MESSAGES = {
    'InterruptedError': 'Transfert SFTP annulé.',
    'FileExistsError': 'Le fichier distant existe déjà : aucun écrasement effectué.',
    'FileNotFoundError': 'Fichier ou répertoire introuvable.',
    'PermissionError': 'Accès refusé : vérifiez les autorisations.',
    'TimeoutError': 'Délai de connexion ou de transfert dépassé.',
    'ConnectionError': 'Connexion interrompue : vérifiez le réseau.',
    'ConnectionResetError': 'Connexion interrompue : vérifiez le réseau.',
    'ConnectionAbortedError': 'Connexion interrompue : vérifiez le réseau.',
    'BrokenPipeError': 'Connexion interrompue : vérifiez le réseau.',
    'ValueError': 'Transfert refusé : chemin ou intégrité à vérifier.',
    'OSError': 'Erreur de transfert SFTP : vérifiez le réseau et les droits.',
    'RuntimeError': 'Transfert impossible : une opération concurrente peut être active.',
}


def sftp_failure_text(error_code):
    """Accept only exact, allowlisted error *types*, never arbitrary details."""
    if type(error_code) is not str:
        return 'Erreur de transfert SFTP (détails masqués).'
    return _MESSAGES.get(error_code, 'Erreur de transfert SFTP (détails masqués).')


def sftp_journal_failure_text(stage='error'):
    """Report audit failure without including potentially sensitive exceptions."""
    if stage == 'completed':
        return 'Transfert effectué, mais audit non confirmé : vérifiez le journal.'
    if stage == 'cancel':
        return 'Journal indisponible : annulation demandée.'
    if stage == 'stopped':
        return 'Journal indisponible : transfert interrompu par sécurité.'
    return 'Transfert refusé : journal d’audit indisponible.'
