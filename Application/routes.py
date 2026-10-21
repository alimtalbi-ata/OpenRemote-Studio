"""Routes with non-destructive legacy PAM quarantine.
Author: Abdelhalim Talbi.
"""
import json
from core import Store
from gateways import validate_route
from pam_refs import parse_reference

class RouteStore(Store):
    def _snapshot_for_save(self):
        routes = []
        seen = set()
        for raw in self.items:
            if not isinstance(raw, dict) or not isinstance(raw.get('id'), str) or not raw['id']:
                raise ValueError('Identifiant de route invalide')
            if raw['id'] in seen:
                raise ValueError('Routes dupliquées')
            seen.add(raw['id'])
            route = validate_route(raw.get('route'))
            parse_reference(route.get('vault_ref', ''))
            routes.append({'id': raw['id'], 'route': route})
        return routes

    def __init__(self,path):
        self.invalid_routes={}
        super().__init__(path)

    def read(self):
        if not self.path.exists():return []
        data=json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data,list):raise ValueError("Routes invalides")
        routes=[]
        seen=set()
        for raw in data:
            if not isinstance(raw,dict) or not isinstance(raw.get("id"),str) or not raw["id"]:
                raise ValueError("Identifiant de route invalide")
            if raw["id"] in seen:raise ValueError("Routes dupliquées")
            seen.add(raw["id"])
            route=validate_route(raw.get("route"))
            try:
                parse_reference(route.get("vault_ref",""))
            except ValueError as exc:
                # Keep the exact original entry; never silently enable an invalid route.
                self.invalid_routes[raw["id"]]=str(exc)
            routes.append({"id":raw["id"],"route":route})
        return routes

    def set_route(self,connection_id,route):
        checked=validate_route(route)
        parse_reference(checked.get("vault_ref",""))
        value={"id":connection_id,"route":checked}
        old=self.items
        self.items=[x for x in old if x["id"]!=connection_id]+[value]
        try:self.save()
        except Exception:
            self.items=old
            raise
        self.invalid_routes.pop(connection_id,None)

    def for_connection(self,connection_id):
        if connection_id in self.invalid_routes:
            raise ValueError("Route désactivée : référence PAM héritée invalide. "
                             "Corrigez-la via Passerelle / Rebond. "
                             +self.invalid_routes[connection_id])
        return next((x["route"] for x in self.items if x["id"]==connection_id),{})

    def raw_for_edit(self,connection_id):
        """Access original fields for guided correction, never for connection launch."""
        return next((x["route"].copy() for x in self.items if x["id"]==connection_id),{})

    def remove_route(self,connection_id):
        old=self.items
        self.items=[item for item in old if item["id"]!=connection_id]
        try:self.save()
        except Exception:
            self.items=old
            raise
        self.invalid_routes.pop(connection_id,None)
