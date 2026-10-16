import json
from pathlib import Path
import tempfile
import unittest

from engine import SearchIndex, StateStore
from install import configure_niri, BINDING


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = SearchIndex()

    def glyphs(self, query, **kwargs):
        return [symbol["glyph"] for symbol in self.index.search(query, **kwargs)]

    def test_common_queries_rank_correctly(self):
        for query, glyph in [("sum", "∑"), ("su", "∑"), ("summation", "∑"),
                             ("real numbers", "ℝ"), ("R", "ℝ"), ("mathbb{R}", "ℝ"),
                             ("gradient", "∇"), ("gradiant", "∇"),
                             ("sigma", "σ"), ("∑", "∑"), ("U+2211", "∑")]:
            with self.subTest(query=query):
                self.assertEqual(self.glyphs(query)[0], glyph)

    def test_case_sensitive_tex_and_styled_letters(self):
        for query, glyph in [(r"\mathbb{R}", "ℝ"), (r"\mathbb{r}", "𝕣"),
                             ("bold A", "𝐀"), ("bold a", "𝐚"),
                             (r"\Sigma", "Σ"), (r"\sigma", "σ")]:
            with self.subTest(query=query):
                self.assertEqual(self.glyphs(query)[0], glyph)
        self.assertNotIn("Σ", self.glyphs(r"\sigma"))

    def test_categories_and_empty_search(self):
        self.assertIn("ℝ", self.glyphs("/sets"))
        self.assertNotIn("∑", self.glyphs("/sets"))
        self.assertIn("α", self.glyphs("greek"))
        self.assertIn("→", self.glyphs("right arrow"))
        self.assertEqual(self.glyphs("zzzznonexistent"), [])
        self.assertEqual(self.glyphs("/sets greek"), [])
        self.assertEqual(self.glyphs("/sets favorites", favorites=["∑"]), [])
        self.assertEqual(self.glyphs("greek", category="Sets"), [])
        self.assertTrue(self.glyphs("/styled letters"))

    def test_favorites_and_recents_do_not_override_relevance(self):
        self.assertEqual(self.glyphs("", favorites=["ℝ"])[0], "ℝ")
        self.assertEqual(self.glyphs("favorites", favorites=["ℝ"]), ["ℝ"])
        self.assertEqual(self.glyphs("recent", recent=["∇", "ℝ"]), ["∇", "ℝ"])
        self.assertEqual(self.glyphs("sum", favorites=["Σ"], recent=["Σ"])[0], "∑")


class StateTests(unittest.TestCase):
    def test_state_persists_and_toggle_is_reversible(self):
        with tempfile.TemporaryDirectory() as directory:
            store = StateStore(Path(directory) / "state.json")
            self.assertEqual(store.read(), {"favorites": [], "recent": []})
            store.update("ℝ", favorite=True)
            self.assertEqual(store.read()["favorites"], ["ℝ"])
            store.update("ℝ", favorite=True)
            store.update("∑")
            store.update("∇")
            store.update("∑")
            self.assertEqual(store.read(), {"favorites": [], "recent": ["∑", "∇"]})

    def test_corrupted_state_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text('{"favorites": "invalid"}')
            with self.assertRaises(ValueError):
                StateStore(path).update("ℝ", favorite=True)
            self.assertEqual(json.loads(path.read_text())["favorites"], "invalid")


class InstallTests(unittest.TestCase):
    def test_binding_insertion_is_idempotent(self):
        original = 'binds {\n    Mod+Period { spawn "walker" "--provider" "symbols"; }\n}\n'
        configured = configure_niri(original)
        self.assertIn(BINDING, configured)
        self.assertEqual(configure_niri(configured), configured)

    def test_existing_other_binding_is_preserved(self):
        with self.assertRaises(ValueError):
            configure_niri('binds {\n    Mod+apostrophe { spawn "other"; }\n}\n')
