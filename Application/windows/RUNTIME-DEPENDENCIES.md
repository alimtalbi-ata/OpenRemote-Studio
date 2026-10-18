# Dépendances Windows — V16.4

- Python/PySide6/Paramiko/Cryptography : intégrés à l’exécutable PyInstaller, **aucune installation Python sur le poste cible**.
- RDP : client Windows mstsc.exe, fourni par les éditions Windows compatibles.
- SSH/SFTP : clients OpenSSH Windows (fonctionnalités facultatives Windows), vérifier dans Diagnostic clients Windows. Une installation peut nécessiter les droits administrateur.
- VNC : visionneuse tierce selon politique entreprise ; **non intégrée** et jamais installée silencieusement.
- PAM/vault : dépend de la solution de l’entreprise ; pas de secret ou client tiers installé automatiquement.
- Compilation : BUILD-WINDOWS.cmd installe si besoin Python 3.12 et Inno Setup via winget, après lancement volontaire du script. Les téléchargements requièrent Internet et peuvent être bloqués par les politiques d’entreprise.
- En cas d’échec de téléchargement, la construction échoue explicitement, sans prétendre produire un installateur.
