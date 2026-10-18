## V30.9 — Qualification de concurrence Windows

Ajout de `02-Compilation/TEST-CONCURRENCE-WINDOWS.ps1`, qui lance des processus PowerShell distincts pour contrôler le verrou exclusif, le refus d’une compilation concurrente, la libération après sortie normale et l’unicité des journaux. Le mode `-LockProbeHoldSeconds` ne compile pas de binaires et reste limité à 120 secondes. Ce test d’intégration exige Windows et n’a pas été exécuté sous Linux.

OpenRemote Studio V30.0 — centralisation des artefacts Windows dans Binary/Installer et Binary/Portable.

Construction sur Windows 10/11 x64 : 02-Compilation\BUILD-WINDOWS.cmd.
Aucun binaire Windows precompile dans ce ZIP : environnement de construction Linux.
Auteur : Abdelhalim Talbi.


V30.0: validation de signature PE du Setup.exe et dossier Binary explicite. Binaires Windows non compilés.


## V30.2 — correction de la chaîne Windows
Les scripts de fabrication et de vérification lisent désormais la version depuis le fichier racine `VERSION.txt`, conformément à la structure cumulative. Avant correction, ils recherchaient `Application/VERSION.txt`, absent, et bloquaient la compilation. Les répertoires `Binary/Installer` et `Binary/Portable` sont des emplacements de sortie et ne contiennent pas de binaires précompilés.


### V30.2 — Correction critique de publication Windows
Les chemins PowerShell des fichiers Setup.exe et Portable.zip utilisent maintenant des chaînes expansibles pour résoudre la version effective. La chaîne est prête pour qualification sur Windows, sans prétendre fournir des binaires précompilés.


## V30.3 — Publication transactionnelle Windows
Le build prépare `Binary/.staging-V30.3-<identifiant>/` et publie après vérifications dans `Binary/V30.3/Installer` et `Binary/V30.3/Portable`. Un échec ne supprime pas les versions déjà publiées. Une version publiée n'est jamais écrasée implicitement. Correction de l'interpolation PowerShell dans `verify-release.ps1`. Aucun exécutable Windows précompilé n'est fourni dans ce ZIP source.

## V30.7 — Sécurité des archives portables
Contrôle anti-traversée, collisions de casse, liens symboliques, noms Windows ambigus et limites de décompression avant publication.


### V30.7 — Qualification portable extrait
Le build Windows teste désormais le démarrage réel de l’exécutable extrait du ZIP portable dans un répertoire temporaire indépendant avant publication. Il refuse aussi immédiatement de reconstruire une version déjà publiée. Tests natifs Windows à réaliser.

## V30.7 — verrou de compilation et journaux indépendants

La commande officielle `02-Compilation\BUILD-WINDOWS.cmd` utilise un verrou exclusif `Binary/.windows-build.lock` tenu pendant la compilation complète. Une seconde compilation est refusée sans altérer la première. Le journal est horodaté et doté d’un identifiant unique (`Binary/build-*.log`) pour conserver les preuves des tentatives. Le fichier de verrou persiste après fermeture mais n’empêche pas un nouveau lancement, car seule sa possession exclusive compte. L’exécution directe du script interne `build-windows.ps1` contourne cette protection et n’est pas prise en charge comme point d’entrée utilisateur. La qualification Windows native reste à réaliser.

## V30.9 — crash recovery du verrou Windows
Le test TEST-CONCURRENCE-WINDOWS.ps1 vérifie aussi la libération du verrou après terminaison forcée du processus propriétaire. À exécuter sous Windows ; les tests Python ne remplacent pas cette recette native.
