# Windows V15.8 — Construction et recette

Auteur : Abdelhalim Talbi.

1. Sur Windows 10/11 x64, exécuter `windows\preflight-windows.ps1`.
2. Construire via `windows\build-windows.ps1`.
3. Pour tester réellement installation, démarrage GUI puis désinstallation dans un répertoire temporaire : `windows\build-windows.ps1 -RunInstallSmoke`. Cette option installe et désinstalle l’application : à lancer sur une VM Windows de qualification.
4. La recette SSH, RDP, VNC, SFTP et PAM exige des cibles de test et une validation humaine.

La recette utilise un APPDATA/LOCALAPPDATA temporaires. En cas d’échec après installation, le répertoire temporaire est conservé pour diagnostic et nettoyage manuel. Aucune capture Windows réelle n'est incluse.
