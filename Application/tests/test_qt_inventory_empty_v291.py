import pathlib
import unittest


class InventoryEmptyStateContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (pathlib.Path(__file__).resolve().parents[1] / 'qt_app.py').read_text(encoding='utf-8')

    def test_no_connections_guidance(self):
        self.assertIn('Aucune connexion enregistrée.', self.source)
        self.assertIn('Nouvelle connexion', self.source)

    def test_filtered_empty_state_has_reset(self):
        self.assertIn('Aucun résultat pour ces filtres.', self.source)
        self.assertIn('Effacer filtres', self.source)

    def test_nonempty_restores_tooltip(self):
        self.assertIn("self.tree.setToolTip('Double-clic : ouvrir", self.source)
