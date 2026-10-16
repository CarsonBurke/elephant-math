import unittest
import unicodedata

from catalog import build_catalog


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.records = build_catalog()
        self.by_glyph = {record["glyph"]: record for record in self.records}

    def test_unique_assigned_characters_and_exact_metadata(self):
        self.assertGreater(len(self.records), 1200)
        self.assertEqual(len(self.records), len(self.by_glyph))
        self.assertEqual(len(self.records), len({r["codepoint"] for r in self.records}))
        for record in self.records:
            glyph = record["glyph"]
            self.assertEqual(len(glyph), 1)
            self.assertEqual(record["name"], unicodedata.name(glyph))
            self.assertEqual(record["codepoint"], f"U+{ord(glyph):04X}")
            self.assertTrue(record["label"])
            self.assertTrue(record["category"])
            self.assertIsInstance(record["priority"], int)
            self.assertEqual(len(record["aliases"]), len(set(record["aliases"])))
            self.assertNotIn(" ", record["latex"])

    def test_common_symbols_have_semantic_and_tex_aliases(self):
        expectations = {
            "∑": ["summation", "sigma", "\\sum", "sum"],
            "∇": ["gradient operator", "del", "nabla", "\\nabla"],
            "ℝ": ["reals", "R", "bb R", "mathbb{R}", "\\mathbb{R}"],
            "ℤ": ["integers"],
        }
        for glyph, aliases in expectations.items():
            record = self.by_glyph[glyph]
            for alias in aliases:
                self.assertIn(alias, record["aliases"] + [record["label"].lower()])
        self.assertGreater(self.by_glyph["∑"]["priority"], self.by_glyph["Σ"]["priority"])
        self.assertNotIn("\\sum", self.by_glyph["Σ"]["aliases"])
        self.assertNotIn("\\sum", self.by_glyph["σ"]["aliases"])

    def test_every_assigned_mathematical_alphanumeric_is_present(self):
        for code in range(0x1D400, 0x1D800):
            glyph = chr(code)
            if unicodedata.name(glyph, ""):
                self.assertIn(glyph, self.by_glyph)

    def test_styled_latin_case_and_legacy_holes(self):
        self.assertEqual(self.by_glyph["𝑥"]["label"], "Italic x")
        self.assertEqual(self.by_glyph["𝑋"]["label"], "Italic X")
        self.assertIn("\\mathit{x}", self.by_glyph["𝑥"]["aliases"])
        self.assertIn("\\mathit{X}", self.by_glyph["𝑋"]["aliases"])
        self.assertIn("bold alpha", self.by_glyph["𝛂"]["aliases"])
        self.assertIn("mathbb{r}", self.by_glyph["𝕣"]["aliases"])
        self.assertNotIn("mathbb{R}", self.by_glyph["𝕣"]["aliases"])
        self.assertEqual(self.by_glyph["𝚤"]["latex"], "\\mathit{\\imath}")
        self.assertEqual(self.by_glyph["𝛓"]["latex"], "\\boldsymbol{\\varsigma}")
        for glyph in "ℬℰℱℋℐℒℳℛℯℊℴℭℌℑℜℨℎ":
            self.assertIn(glyph, self.by_glyph)

    def test_avoids_incomplete_glyph_parts(self):
        for record in self.records:
            self.assertNotIn("SUMMATION TOP", record["name"])
            self.assertNotIn("SUMMATION BOTTOM", record["name"])

    def test_greek_variant_commands_are_distinct(self):
        for letter, variant in [("ε", "ϵ"), ("φ", "ϕ")]:
            self.assertNotEqual(self.by_glyph[letter]["latex"], self.by_glyph[variant]["latex"])
        self.assertEqual(self.by_glyph["λ"]["latex"], "\\lambda")
        self.assertEqual(self.by_glyph["∌"]["latex"], "\\not\\ni")

    def test_builds_independent_records(self):
        self.records[0]["aliases"].append("changed")
        self.assertNotIn("changed", build_catalog()[0]["aliases"])


if __name__ == "__main__":
    unittest.main()
