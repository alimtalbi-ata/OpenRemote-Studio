"""Discoverable tool catalog. No shell command execution from catalog data."""
TOOLS = (
 ('Réseau','Ping','ping','Vérifier la connectivité ICMP'),
 ('Réseau','DNS','nslookup','Résolution DNS'),
 ('Réseau','Traceroute','traceroute','Chemin réseau vers une cible'),
 ('Réseau','Test TCP','tcp','Tester un port TCP avec délai'),
 ('Accès','SSH intégré','ssh','Console SSH dans un onglet'),
 ('Accès','SFTP','sftp','Navigateur de fichiers distant'),
 ('Accès','Client externe','connect','Ouvrir le client natif disponible'),
 ('Sécurité','Coffre','vault','Déverrouiller le coffre local'),
 ('Sécurité','Secret','secret','Associer un secret à une connexion'),
 ('Espace de travail','Diviser','split','Créer un panneau de travail secondaire'),
)
def search_tools(query):
    q=query.strip().casefold()
    return [x for x in TOOLS if not q or q in ' '.join(x).casefold()]
