# Dépendances Windows — V16.4

- Python/PySide6/Paramiko/Cryptography : intégrés à l’exécutable PyInstaller, **aucune installation Python sur le poste cible**.
- RDP : client Windows mstsc.exe, fourni par les éditions Windows compatibles.
- SSH/SFTP : clients OpenSSH Windows (fonctionnalités facultatives Windows), vérifier dans Diagnostic clients Windows. Une installation peut nécessiter les droits administrateur.
- VNC : visionneuse tierce selon politique entreprise ; **non intégrée** et jamais installée silencieusement.
- PAM/vault : dépend de la solution de l’entreprise ; pas de secret ou client tiers installé automatiquement.
- Compilation : BUILD-WINDOWS.cmd installe si besoin Python 3.12 et Inno Setup via winget, après lancement volontaire du script. Les téléchargements requièrent Internet et peuvent être bloqués par les politiques d’entreprise.
- En cas d’échec de téléchargement, la construction échoue explicitement, sans prétendre produire un installateur.

## V31.8 — R101 (25 octobre 2026)

- `pywinrm>=0.5,<0.6` est installé dans l'environnement **de compilation**, puis embarqué dans l'installateur et le portable via PyInstaller (`winrm` et `spnego` collectés explicitement). Aucun Python externe n'est requis sur le poste cible.
- Un contrôle **offline** `OpenRemoteStudio.exe --check-winrm-runtime` retourne 0 si le graphe `winrm`/`requests_ntlm`/`spnego`/`requests` est importable et fonctionnel au niveau des symboles requis, 13 sinon. Il n'ouvre aucun socket, n'accède à aucun secret et n'initialise pas de session WinRM.
- Le build Windows échoue avant publication si ce contrôle échoue dans le dossier PyInstaller ou après extraction du portable. Le build vérifie toujours séparément l'interface Qt.
- **Limite** : la disponibilité des bibliothèques ne prouve pas la compatibilité NTLM/TLS avec un Windows Server réel, ni la présence d'un compte à privilèges minimaux. Ces scénarios restent UNVERIFIED.
