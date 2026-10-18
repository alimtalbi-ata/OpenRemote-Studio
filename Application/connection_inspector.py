"""Read-only, credential-free connection summary. Author: Abdelhalim Talbi."""

def inspect_connection(connection, favorites=(), active_ids=()):
    if not connection:
        return 'Sélectionnez une connexion dans l’arborescence.'
    protocol=str(connection.get('protocol') or 'Inconnu')
    name=str(connection.get('name') or 'Sans nom')
    host=str(connection.get('host') or 'Non défini')
    port=str(connection.get('port') or 'Par défaut')
    group=str(connection.get('group') or 'Sans groupe')
    identity=connection.get('id')
    return '\n'.join((f'Connexion : {name}',f'Protocole : {protocol}',f'Cible : {host}:{port}',f'Groupe : {group}',f'Favori : {"Oui" if identity in favorites else "Non"}',f'Client local actif : {"Oui" if identity in active_ids else "Non"}', 'Statut distant : non vérifié'))
