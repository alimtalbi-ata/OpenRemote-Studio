# OpenRemote Studio V22.6 — Windows OneClick

Auteur : Abdelhalim Talbi.

## Construction

Double-cliquer sur `BUILD-WINDOWS.cmd` sur Windows 10/11 x64. Le script vérifie les outils de construction, tente leur installation via winget, installe les dépendances Python de compilation et produit un installateur Inno Setup et une version portable. Réseau et droits peuvent être requis. Aucun Python nécessaire sur le poste cible.

## Interface

La barre principale privilégie Connexion, Assistant, Connecter, SFTP et Diagnostic. Les outils avancés restent dans les menus. Le diagnostic local s’ouvre dans un onglet réutilisable, pas une fenêtre modale répétée.

## Dépendances d’exécution

RDP utilise mstsc Windows. SSH/SFTP requièrent les clients OpenSSH locaux selon la fonction. VNC nécessite une visionneuse externe compatible et n’est pas installée silencieusement. PAM dépend des produits tiers et de leurs licences. Les clients tiers ne sont pas prétendus intégrés.

## Qualification

Tests Python et ZIP validés sous Linux. Aucune compilation ou recette GUI Windows n’a été exécutée ici. Voir `docs/AUDIT-V22.6.md`.


## V22.6 — Qualité du build Windows
Correctifs des contrôles PowerShell et inventaire du poste de build : `docs/AUDIT-V22.6.md`. Lancer `BUILD-WINDOWS.cmd` sur Windows.

## V22.6 — Aide intégrée
Nouvel onglet de démarrage rapide réutilisable, accessible par le bouton Aide, le menu Aide et F1. Aucune connexion réseau automatique.

## V22.6 — Recherche et filtres plus intuitifs
Compteur de résultats, états vides explicites et bouton Effacer filtres. Voir `docs/AUDIT-V22.6.md`.

## V22.6 — Panneau contextuel
Les actions de la connexion sélectionnée sont désactivées en absence de sélection. Le menu Affichage permet de masquer ou restaurer le panneau. Voir docs/AUDIT-V22.6.md.

## V22.6 — Navigation unifiée
Accès direct Connexions / Sessions / Diagnostics et raccourcis Ctrl+1/2/3. Voir docs/AUDIT-V22.6.md.

## V22.6 — Navigation active
Boutons de navigation cochables et synchronisés avec les onglets, noms accessibles, sans connexion automatique. Voir docs/AUDIT-V22.6.md.

## V22.6
Raccourcis clavier centralisés : Ctrl+Shift+F efface les filtres, Ctrl+E bascule les favoris. Voir docs/AUDIT-V22.6.md.

## V22.6 — Sélection persistante
Le rafraîchissement conserve la sélection si la connexion reste visible ; une sélection filtrée disparaît. Voir docs/AUDIT-V22.6.md.

## V22.6 — Panneau de connexion clarifié
Actions groupées Session / Informations, infobulles, noms accessibles, raccourcis de l’aide actualisés. Voir `docs/AUDIT-V22.6.md`.

## V22.6 — Panneau contextuel modulaire
Le dock de connexion est extrait dans `inspector_panel.py` et testé séparément. Voir `docs/AUDIT-V22.6.md`.

## V22.6 — Accueil guidé
Cinq actions rapides accessibles dès l’accueil, composant `home_workspace.py` réutilisable. Voir `docs/AUDIT-V22.6.md`.

## V22.6 — Sessions plus lisibles
États locaux explicites, message de liste vide, reconnexion contextuelle désactivée sans session terminée. Voir docs/AUDIT-V22.6.md.

## V22.6 — Diagnostic local intégré
Synthèse de disponibilité des clients SSH/SFTP/RDP/VNC et conseils contextuels dans l’onglet Diagnostics, sans test réseau ni lecture de secrets. Voir `docs/AUDIT-V22.6.md`.

## V22.6 — Gate cryptographique de livraison
Le script de vérification Windows contrôle désormais le manifeste SHA-256, les doublons et les empreintes des binaires, et refuse un ancien installateur résiduel. Voir `docs/AUDIT-V22.6.md`.

## V22.6 — Release ZIP hardening
Windows release verification now reads each compressed entry, rejects duplicate/unsafe paths and unexpected release artifacts. See docs/AUDIT-V22.6.md.

## V22.6 — Correctif critique nettoyage release
La suppression initiale des anciens binaires cible désormais la version en cours (V22.6), et non V18.1. Voir `docs/AUDIT-V22.6.md`.

## V22.6 — Nettoyage cumulatif des anciennes releases
Le script de construction nettoie les archives portables et installateurs de toutes les versions précédentes avant de produire les nouveaux livrables. Voir `docs/AUDIT-V22.6.md`.


## V22.6 — Contrôle des runtimes embarqués
Le BuildKit vérifie désormais le plugin Qt Windows `qwindows.dll` et la DLL Python embarquée avant la création du ZIP, puis lors de la vérification de la livraison. Voir `docs/AUDIT-V22.6.md`.


## V22.6
Validation exhaustive du manifeste SHA-256 de livraison ; détails dans `docs/AUDIT-V22.6.md`.

## V22.6 — Diagnostic local filtrable
Cocher « Afficher uniquement les clients à corriger » pour isoler les dépendances manquantes. Le compteur affiche la sélection et le total ; la copie conserve les conseils complets. Voir `docs/AUDIT-V22.6.md`.

## V22.6 — Correction de la recherche depuis l’accueil
Suppression de la redéfinition qui empêchait le retour à l’onglet Connexions. Voir `docs/AUDIT-V22.6.md`.


## V22.6 — Windows portable compact

`BUILD-WINDOWS.cmd -SingleExe` produit un ZIP portable contenant un unique exécutable et un installateur Inno Setup basé sur ce même exécutable. Sans option, le mode onedir reste disponible. Construction à effectuer sur Windows x64 ; aucun .exe Windows précompilé n’est inclus. Voir `docs/AUDIT-V22.6.md`.

## V22.6 — Recette d'installation bornée
Le test d'installation/désinstallation dispose d'un délai maximal et d'un chemin d'installateur cohérent avec la version. `BUILD-WINDOWS.cmd -SingleExe -RunInstallSmoke` active la recette sur un poste Windows. Les exécutables ne sont pas présents dans ce ZIP source.

## V22.6 — Détails de session partageables
Menu contextuel Sessions : copier les métadonnées du processus sélectionné, sans lignes de commande ni secrets. Voir docs/AUDIT-V22.6.md.

## V22.6 — Cohérence Connexions / Sessions
Sélection par connexion + PID centralisée et testée, détails et reconnexion alignés. Voir `docs/AUDIT-V22.6.md`.

## V22.6 — Identité des sessions
Normalisation des PID et refus des identités de processus ambiguës. Voir `docs/AUDIT-V22.6.md`.

## V22.6 — Reconnexion exacte
La reconnexion valide désormais le PID réellement sélectionné, sans choisir un autre processus terminé. Voir docs/AUDIT-V22.6.md.

## V22.6 — Reconnexion depuis Connexions
Sélection explicite du PID terminé et revalidation avant lancement. Voir `docs/AUDIT-V22.6.md`.


## V22.6
Revalidation du choix de reconnexion sur un instantané récent, tests de non-régression et audit dans `docs/AUDIT-V22.6.md`.

## Correctif V22.6 — Cibles supprimées
Les actions de reconnexion des deux vues Sessions vérifient la présence de la connexion avant de consommer un candidat. Voir docs/AUDIT-V22.6.md.

## V22.6 — Reconnexion fiable
Correction de la consommation prématurée de candidat lors de la navigation, contrôle de connexion supprimée et version Inno Setup cohérente. Voir docs/AUDIT-V22.6.md.


## V22.6 — Audit du cycle de vie des sessions
Réconciliation d’historique idempotente, état inconnu explicite en cas d’erreur `poll`, blocage conservateur des reconnexions et des lancements concurrents, libellés UI cohérents. Voir `docs/AUDIT-V22.6.md`.


## V22.6
Contrôleur commun de reconnexion pour les trois parcours UI ; dix nouveaux tests. Voir `docs/AUDIT-V22.6.md`.

## V22.6 — Actions usuelles guidées
Barre principale clarifiée : Nouvelle connexion, Ouvrir, Vérifier accès, Transfert SFTP, Diagnostic local et Aide. Les actions nécessitant une connexion sont désactivées en absence de sélection et SFTP n’est disponible que pour SSH/SFTP. Voir `docs/AUDIT-V22.6.md`.

## V22.6 — Accès rapides sur l’accueil
Favoris et connexions récentes accessibles directement : clic pour sélectionner, double-clic pour ouvrir. Voir docs/AUDIT-V22.6.md.


## V22.6 — Accès rapides fiables
État vide explicite, activation clavier, exclusion des identifiants ambigus, contrôles de sélection renforcés. Voir `docs/AUDIT-V22.6.md`.

## V22.6 — Accueil allégé
Les actions primaires restent dans la barre permanente ; l’accueil affiche un guidage et des raccourcis complémentaires. Voir `docs/AUDIT-V22.6.md`.

## V22.6 — Barre adaptative
Les actions secondaires basculent dans « Plus ▾ » selon la largeur. Voir `docs/AUDIT-V22.6.md`.


## V22.6 — Sessions indéterminées

La vue Sessions affiche désormais le nombre de processus à état inconnu et propose un filtre dédié. Voir `docs/AUDIT-V22.6.md`.
