# OpenRemote Studio — Audit technique et feuille de route (18 octobre 2026)

Auteur : Abdelhalim Talbi  
Base inspectée : branche `develop/v31.8-windows-ci`, VERSION.txt = 31.4.  
**Portée : audit statique ciblé du dépôt et des journaux GitHub Actions ; ce document n'est pas une certification fonctionnelle exhaustive.**

## 1. Constats vérifiés

| Priorité | Constat | Conséquence | Action |
|---|---|---|---|
| P0 | Build Windows #16 : Inno Setup compile l'installateur, mais la validation ZIP bloque ensuite sur les chemins d'entrée Windows. | Aucun livrable publiable avant tous les gates. | Normaliser les chemins ZIP dans tous les vérificateurs, ajouter tests ZIP avec séparateurs Windows et relancer CI. |
| P0 | La chaîne exige un runtime Python et le plugin Qt dans le ZIP portable. | Risque de distribution non autonome si un composant manque. | Tester l'archive extraite hors arbre source, avec PATH/PYTHONPATH isolés, et un vrai lancement GUI sur Windows. |
| P0 | Le manifeste source historique doit être régénéré à partir d'un checkout propre dans CI ; des journaux/locks de build sont créés localement. | Risque de fausses anomalies ou de faux sentiment d'intégrité. | Distinguer inventaire des sources versionnées, sorties temporaires et manifeste de livraison ; signer les releases à terme. |
| P1 | `Application/qt_app.py` fait ~3 555 lignes / 218 Ko et contient dialogues, fenêtre principale, logique de sessions, historique, routes et orchestration. | Couplage fort, revue/test difficiles, régressions UI. | Extraire progressivement les contrôleurs et widgets sans changer les comportements ni les API publiques utilisées par les tests. |
| P1 | La construction passe par CMD, bootstrap PowerShell, build PowerShell, plusieurs vérificateurs Python/PowerShell et Inno Setup. | Plusieurs sources de vérité pour les validations et les chemins. | Garder un point d'entrée `BUILD-WINDOWS.cmd`, factoriser les règles communes de packaging et produire un rapport machine lisible unique. |
| P1 | Dépendances runtime exprimées en plages (`PySide6>=6.7,<7`, `paramiko>=3.4,<5`, `cryptography>=43,<48`). | Builds non reproductibles dans le temps. | Générer un lock de compilation Windows x64 avec empreintes, séparer dépendances runtime et build ; conserver une politique de mises à jour. |
| P1 | État local composé de JSON, vault chiffré et SQLite (`connections.json`, `routes.json`, `workspace.json`, `transfers.sqlite3`, etc.). | Risques de cohérence, corruption et migrations partielles. | Définir schémas versionnés, migrations atomiques, backups, recovery et tests de panne ; ne jamais écrire de secrets dans les logs. |
| P2 | README principalement organisé en notes de versions ; documentation distribuée sur plusieurs répertoires. | Parcours utilisateur et mainteneur peu direct. | Créer un portail de documentation stable, puis archiver les notes historiques sans suppression. |

## 2. Rationalisation proposée

Architecture cible **progressive** (ne pas déplacer massivement les fichiers avant stabilisation des builds) :

```text
Application/
  openremote/
    domain/         # modèles Connection, Route, Session, Transfer
    services/       # SSH/SFTP, diagnostics, politiques, vault
    persistence/    # stores JSON/SQLite, schémas et migrations
    integrations/   # RDP, VNC, PAM, clients externes
    ui/
      widgets/      # composants réutilisables
      dialogs/      # édition connexion, saut SSH, chemin
      controllers/  # coordination UI/services
    security/       # redaction, contrôle d'accès, gestion secrets
  qt_app.py         # façade de compatibilité, point d'entrée existant
  tests/
  windows/          # build/packaging natif
02-Compilation/     # wrapper unique, gates, rapports CI
05-Documentation/   # utilisateur, admin, développeur, sécurité
07-Manifestes/      # manifestes de sources et release distincts
Binary/Vx.y/        # installateur + portable + checksums + rapports
```

**Règle de migration :** extraire une seule responsabilité à la fois, maintenir les imports historiques, faire passer les tests existants, mesurer le temps de démarrage et comparer captures UI réelles avant/après.

## 3. Priorisation produit

**P0 — livrable réellement utilisable :** installation/désinstallation propre ; portable autonome ; gestion fiable des connexions SSH ; terminal interactif ; transfert SFTP avec reprise/annulation ; stockage sûr des identifiants ; diagnostic de connexion clair ; gestion des erreurs sans gel UI.

**P1 — productivité quotidienne :** onglets/sessions persistantes, recherche et tags, profils et groupes, sauts SSH/bastions, transferts en file, raccourcis clavier, export/import de configuration sans secrets par défaut, historique local consultable, thèmes/accessibilité.

**P2 — entreprise :** RDP/VNC via clients externes détectés et clairement annoncés ; coffre/vault et rotation ; journaux d'audit redigés ; politiques par profil ; observabilité des sessions ; diagnostics reproductibles ; support de parc important.

**P3 — évolutions après fiabilisation :** synchronisation chiffrée multi-postes, gestion d'équipe, plugins documentés, inventaire automatique, intégrations PAM natives validées, mises à jour signées. Ne pas promettre une intégration distante tant qu'elle n'est pas implémentée et testée.

## 4. Versions proposées (cibles, non releases publiées)

- **V31.8 — stabilisation Windows :** finir les gates ZIP/PE, smoke GUI extrait, installation/désinstallation, checksums, artefacts CI téléchargeables ; aucun faux PASS.
- **V31.9 — architecture et dette :** cartographie des modules, extraction des premiers contrôleurs de `qt_app.py`, séparation des erreurs UI/services, tests unitaires de régression.
- **V32.0 — expérience cœur de produit :** simplifier l'écran Connexions, terminal/SSH et SFTP ; navigation clavier, recherche, feedback de transfert, diagnostics contextuels ; mesures UX avant/après.
- **V32.1 — données et sécurité :** migration versionnée JSON/SQLite, backup/restauration, coffre, redaction logs, tests d'accès et résilience.
- **V32.2 — déploiement entreprise :** signature des binaires, SBOM, provenance build, scan dépendances, installateur silencieux, politiques de mise à jour et tests Windows 10/11.
- **V32.3 — extensibilité :** interfaces d'intégration stables pour RDP/VNC/PAM, capability detection et documentation développeur.

## 5. Critères de sortie non négociables

1. Tests unitaires et régressions verts sur Python cible, UTF-8 explicite.
2. Installateur et ZIP portable générés sur runner Windows, vrais PE valides, checksums et inventaire.
3. Exécution de la version portable extraite **sans Python installé ni accès au dépôt** ; présence des DLL/Qt nécessaires.
4. Installation, lancement, désinstallation, absence de résidus critiques, avec rapports et captures **réelles** lorsque réalisables.
5. Contrôle de sécurité des ZIP (traversal, doublons, corruption), des secrets et de la configuration.
6. Documentation Word/PDF à jour intégrée au ZIP cumulatif ; pas de captures fictives présentées comme réelles.
7. Version, notes de migration, tests, limites et statut PASS/PARTIAL/FAIL explicites.

## 6. Décisions d'ingénierie

- Préserver `main` ; travailler sur branche dédiée et PR.
- Prioriser correction de la distribution et usage SSH/SFTP avant nouvelles fonctions.
- Interdire les contournements silencieux des tests, et conserver les résultats négatifs dans les rapports.
- Maintenir le crédit auteur « Abdelhalim Talbi » dans les écrans À propos et livrables.
- Faire précéder toute suppression ou déplacement d'une recherche de références et d'une suite de non-régression.

## 7. Mesures à instrumenter

Temps de démarrage à froid, mémoire au repos, délai de connexion SSH, temps de première réponse terminal, débit SFTP, taux de reprise réussie, durée du build, taille du setup/portable, taux de succès des tests et nombre d'erreurs UI non gérées. Établir d'abord une baseline réelle sur Windows ; ne pas inventer de valeurs.
