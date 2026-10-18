"""Read-only PAM profile matching. No secret access. Author: Abdelhalim Talbi."""
from pam_refs import parse_reference

def resolve_pam_profile(reference,profiles):
    ref=parse_reference(reference)
    if ref is None:
        return {'configured':False,'provider':None,'profiles':[],'ready':True,'reason':'Aucune référence PAM'}
    matches=sorted((p['name'] for p in profiles if p['provider']==ref.provider),key=str.casefold)
    return {'configured':True,'provider':ref.provider,'profiles':matches,'ready':False,
            'reason':('Profil fournisseur trouvé, mais aucun connecteur PAM actif' if matches
                      else 'Aucun profil fournisseur correspondant ; aucun connecteur PAM actif')}
