# OpenRemote Studio V31.5 — Consolidation et qualification

Auteur : Abdelhalim Talbi  
Statut : candidate Windows, **ne pas qualifier avant succès CI**.

## Périmètre effectivement développé
- Navigation principale : Connexions, Sessions, Diagnostics, Transferts (Ctrl+1 à Ctrl+4).
- Historique SFTP dans un onglet réutilisable, sans fenêtre modale.
- Rafraîchissement à chaque retour dans la vue ; libération des références à la fermeture.
- Module `transfer_presentation.py` indépendant de Qt ; validation des lignes avant affichage.
- Journal indisponible ou corrompu : vider les résultats périmés, afficher un message neutre, ne pas exposer les chemins des exceptions.
- Reconnexion des sessions : refus prudent lorsque les observations locales sont malformées.
- Tests unitaires de navigation, raccourcis, cycle de vie et format des journaux.

## Matrice de contrôle et limites
| Composant | Contrôle réalisé | Limite à qualifier |
|---|---|---|
| Registre de connexions | validation, unicité, écriture atomique et rollback | restauration après panne réelle |
| Sessions | identification PID/connexion, reconnexion prudente | connectivité distante réelle non démontrée par PID |
| SSH / SFTP | tests automatisés existants ; historique en lecture seule | essais E2E multi-serveurs et transferts massifs |
| RDP / VNC / WEB | intégrations natives du build Windows | recette sur clients et environnements réels |
| Interface | contrats de navigation et raccourcis, contrôles de source | captures UI Windows réelles non incluses dans ce document |
| Packaging | workflow GitHub Windows natif et artefacts liés au commit | signature Authenticode et tests antivirus multi-postes |

Les contrôles de source ne remplacent pas une recette interactive humaine. Aucune capture fictive ne doit être présentée comme une capture réelle.

## Plan prévisionnel
- **V31.6 — Intégrité des transferts** : journal transactionnel, reprise après interruption, tests d'annulation et d'erreurs disque, vérification de fichiers.
- **V31.7 — Simplification de l'interface** : actions contextuelles, état vide explicite, accessibilité clavier, tests GUI Qt automatisés.
- **V31.8 — Sécurité et audit** : événements structurés, corrélation d'opérations, masquage des secrets, export d'audit vérifiable.
- **V31.9 — Stabilisation Windows** : tests E2E SSH/SFTP/RDP/VNC, installation propre et mise à niveau, packaging cumulatif et documentation illustrée.

## Critères de sortie
1. Tous les tests CI du commit de livraison réussissent.
2. Les exécutables Windows sont construits depuis ce commit exact.
3. Le SHA-256 de chaque fichier distribué est publié.
4. Les écarts non testés en environnement réel sont explicitement signalés.
5. La branche `main` reste inchangée jusqu'à validation de la pull request.
