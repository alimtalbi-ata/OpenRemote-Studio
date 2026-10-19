"""Pure presentation helpers for read-only SFTP transfer history.
Author: Abdelhalim Talbi.
"""

TRANSFER_COLUMNS = ('ID', 'Connexion', 'Opération', 'Chemin distant',
                    'Chemin local', 'État', 'Progression', 'Mise à jour')
TRANSFER_STATES = ('Tous', 'waiting', 'running', 'done', 'failed',
                   'cancelled', 'interrupted')


def transfer_query_state(label):
    """Convert the UI's all-state label to the journal query sentinel."""
    return None if label == 'Tous' else label


def transfer_row_cells(row):
    """Bound display values; no mutation or execution of remote operations."""
    if not isinstance(row, (tuple, list)) or len(row) != len(TRANSFER_COLUMNS):
        raise ValueError('Ligne de transfert invalide')
    return tuple('' if value is None else str(value) for value in row)


def transfer_count_label(count):
    if not isinstance(count, int) or count < 0:
        raise ValueError('Nombre de transferts invalide')
    return f'{count} entrées · consultation uniquement'
