# OpenRemote Studio — Audit qualité, fiabilité et UX (V31.9)
Auteur : Abdelhalim Talbi

## Constat vérifié dans les sources
- `Application/qt_app.py` : environ 3 555 lignes, 247 définitions de fonctions/méthodes. La fenêtre mélange présentation Qt, orchestration et accès aux données. Le risque majeur est une régression transversale lors de chaque modification.
- `Application/core.py` : stockage JSON avec écriture temporaire, `fsync` et `os.replace` ; validation et logique d'import regroupées. Les entrées JSON mal formées étaient susceptibles de déclencher une exception technique `AttributeError` au lieu d'une erreur de domaine.
- `session_selection.py` et `session_presentation.py` : frontières sans Qt ni réseau déjà disponibles ; réutilisables pour isoler la logique métier et tester les états sans interface.

## Priorités (ordre de réalisation)
1. **P0 — Registre et sessions** : entrée invalide = erreur métier explicite ; import tout-ou-rien ; rollback sur échec de sauvegarde ; unicité des identifiants ; reconnecter uniquement la session exacte ; ne pas assimiler PID actif et session distante saine.
2. **P0 — SSH/SFTP** : erreurs actionnables, validation hôte/port, hôte distant et clés connus, transferts annulables et vérification d'intégrité ; aucun secret dans journaux ni affichage.
3. **P1 — UI** : navigation primaire « Connexions | Sessions | Transferts | Historique | Paramètres ». Une action primaire par écran, recherche toujours visible, états vides explicites, badges d'état local distincts de la connectivité distante, raccourcis clavier, retours d'erreur compréhensibles.
4. **P1 — Découpage** : extraire progressivement services, modèles et contrôleurs hors `qt_app.py`, avec tests unitaires avant remplacement des appels UI. Pas de réécriture monolithique.
5. **P1 — Auditabilité** : journaux structurés horodatés, ID d'opération, événement et résultat, exclusion des secrets, manifeste SHA256 et provenance commit/build.
6. **P2 — Distribution** : installer et portable autonomes, smoke test Windows sur ZIP extrait sans PYTHONPATH ; essais complémentaires sur un second PC ; signature et vérification de provenance à prévoir.

## Décisions de conception UI
- Connexions : liste/table avec nom, protocole, hôte, groupe, état local ; double-clic = ouvrir ; bouton « Nouvelle connexion ».
- Sessions : statut « Processus local actif » plutôt que « Connecté » tant qu'aucune sonde distante n'atteste la session.
- Transferts : source, destination, progression, pause/annulation, journal d'erreur consultable.
- Paramètres avancés masqués par défaut, mais accessibles ; pas de suppression de fonctions sans remplacement.
- Accessibilité : navigation clavier, libellés textuels en plus des couleurs, focus visible, dimensions adaptables.

## Critères de sortie
- Tests du domaine et de l'import verts ; zéro régression SSH/SFTP/RDP/VNC.
- Tests Qt des flux principaux, captures **réelles** et contrôles clavier avant validation ergonomique.
- Binaires issus du même commit que les sources documentées.
- Toute simulation ou capture non exécutée doit être explicitement identifiée.

## État de preuve
Le document décrit un audit statique du code consulté et des travaux planifiés. Il ne constitue pas une validation ergonomique visuelle, un test réel de connexion distante, ni une recette sur un PC Windows tiers.
