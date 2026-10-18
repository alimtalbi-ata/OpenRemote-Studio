"""Pure, offline status model for the connection browser. Author: Abdelhalim Talbi."""

def filter_status(total: int, visible: int, query: str = "", favorites_only: bool = False) -> tuple[str, bool]:
    if total < 0 or visible < 0 or visible > total:
        raise ValueError("invalid connection counts")
    if not total:
        return "Aucune connexion enregistrée · cliquez sur ＋ Connexion pour commencer.", False
    if not visible:
        if query.strip() or favorites_only:
            return "Aucun résultat · effacez la recherche ou désactivez le filtre Favoris.", True
        return "Aucune connexion visible.", False
    label = f"{visible} connexion" + ("s" if visible > 1 else "")
    if visible != total:
        label += f" sur {total}"
    return label, bool(query.strip() or favorites_only)
