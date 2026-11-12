# -*- coding: utf-8 -*-
"""Tests de FracturoPrompt Forge v2.1 (stdlib uniquement).

Lancer :  python3 -m unittest discover -s tests -v
"""
import contextlib
import io
import json
import random
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fracturo_prompt_forge_v2 as forge  # noqa: E402

LEX = forge.charger_lexique()


def lancer(*argv):
    """Exécute main() et renvoie (code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = forge.main(list(argv))
        except SystemExit as exc:  # argparse
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class TestLexique(unittest.TestCase):
    def test_charge_et_valide(self):
        self.assertEqual(LEX["META_DATA"]["version"], "2.1")
        self.assertEqual(len(LEX["RUNES_DATABASE"]["futhark_elder"]), 24)

    def test_fichier_absent(self):
        with self.assertRaises(forge.LexiqueError):
            forge.charger_lexique(Path("/inexistant/lex.json"))

    def test_json_invalide(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.json"
            p.write_text("{pas du json", encoding="utf-8")
            with self.assertRaises(forge.LexiqueError):
                forge.charger_lexique(p)

    def test_cle_manquante(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.json"
            p.write_text(json.dumps({"RUNES_DATABASE": {}}), encoding="utf-8")
            with self.assertRaises(forge.LexiqueError):
                forge.charger_lexique(p)

    def test_coherence_archetypes(self):
        """Chaque archétype a ses actions dans STRATE_6."""
        for cle in LEX["STRATE_3_ARCHETYPES_JUNG_EXTENDED"]:
            self.assertIn(cle, LEX["STRATE_6_INVOCATION_TARGETS"]["archetypes_specific"])


class TestReproductibilite(unittest.TestCase):
    def test_meme_graine_meme_sortie(self):
        a = forge.generer_prompt("x", LEX, weaponised=True, rng=random.Random(7))
        b = forge.generer_prompt("x", LEX, weaponised=True, rng=random.Random(7))
        self.assertEqual(a, b)

    def test_graines_differentes(self):
        a = forge.generer_prompt("x", LEX, weaponised=True, rng=random.Random(1))
        b = forge.generer_prompt("x", LEX, weaponised=True, rng=random.Random(2))
        self.assertNotEqual(a, b)

    def test_cli_seed(self):
        _, o1, _ = lancer("-p", "x", "-w", "--seed", "5", "-q")
        _, o2, _ = lancer("-p", "x", "-w", "--seed", "5", "-q")
        self.assertEqual(o1, o2)


class TestPromptBase(unittest.TestCase):
    def test_prompt_base_jamais_altere(self):
        """La casse aléatoire ne touche pas le prompt de l'utilisateur."""
        for seed in range(100):
            p = forge.generer_prompt("PoRtRaIt Z", LEX, weaponised=True, rng=random.Random(seed))
            self.assertTrue(p.startswith("PoRtRaIt Z, "), p[:40])


class TestWeaponised(unittest.TestCase):
    def test_bornes_elements(self):
        for seed in range(300):
            e = forge.construire_elements_weaponised(LEX, random.Random(seed))
            self.assertTrue(22 <= len(e) <= 38, (seed, len(e)))

    def test_pas_de_doublon_dans_les_listes(self):
        for seed in range(200):
            e = forge.construire_elements_weaponised(LEX, random.Random(seed))
            hexs = [x for x in e if x in LEX["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["hex_sequences"]]
            self.assertEqual(len(hexs), len(set(hexs)))
            self.assertEqual(len(e), len(set(e)), seed)

    def test_suffixe_dans_les_plafonds(self):
        for seed in range(200):
            p = forge.generer_prompt("x", LEX, weaponised=True, rng=random.Random(seed))
            m = re.search(r"--weird (\d+) --style raw --chaos (\d+)$", p)
            self.assertIsNotNone(m, p[-60:])
            self.assertTrue(2500 <= int(m.group(1)) <= 3000)
            self.assertTrue(50 <= int(m.group(2)) <= 100)

    def test_engine_none(self):
        p = forge.generer_prompt("x", LEX, weaponised=True, rng=random.Random(1), engine="none")
        self.assertNotIn("--weird", p)

    def test_methode_compat_v20(self):
        p = forge.generer_prompt_weaponised("x", LEX, rune="ᚦ", rng=random.Random(3))
        self.assertIn("ᚦ", p)


class TestNiveaux(unittest.TestCase):
    def test_paliers(self):
        self.assertEqual([forge.palier(n) for n in (0, 0.29, 0.3, 0.59, 0.6, 0.89, 0.9, 1.0)],
                         [0, 0, 1, 1, 2, 2, 3, 3])

    def test_contenu_par_palier(self):
        for seed in range(50):
            rng = lambda: random.Random(seed)  # noqa: E731
            e0 = forge.construire_elements_niveau(LEX, rng(), 0.1)
            e1 = forge.construire_elements_niveau(LEX, rng(), 0.4)
            e2 = forge.construire_elements_niveau(LEX, rng(), 0.7)
            e3 = forge.construire_elements_niveau(LEX, rng(), 0.95)
            has = lambda e, pre: any(x.startswith(pre) for x in e)  # noqa: E731
            self.assertFalse(has(e0, "RUNE_SEQUENCE"))
            self.assertTrue(has(e1, "RUNE_SEQUENCE"))
            self.assertFalse(has(e1, "ARCHETYPE:"))
            self.assertTrue(has(e2, "ARCHETYPE:"))
            self.assertFalse(any(x in LEX["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["temporal_signatures"] for x in e2))
            self.assertTrue(any(x in LEX["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["temporal_signatures"] for x in e3))

    def test_croissance_de_la_densite(self):
        n = lambda niv: len(forge.construire_elements_niveau(LEX, random.Random(1), niv))  # noqa: E731
        self.assertLess(n(0.1), n(0.4))
        self.assertLess(n(0.4), n(0.7))
        self.assertLess(n(0.7), n(0.95))

    def test_niveau_invalide(self):
        with self.assertRaises(ValueError):
            forge.generer_prompt("x", LEX, niveau=1.5)

    def test_suffixe_niveau_dans_les_plafonds(self):
        for seed in range(100):
            for niv in (0.0, 0.5, 1.0):
                p = forge.generer_prompt("x", LEX, niveau=niv, rng=random.Random(seed))
                m = re.search(r"--weird (\d+) --style raw --chaos (\d+)$", p)
                self.assertLessEqual(int(m.group(1)), 3000)
                self.assertLessEqual(int(m.group(2)), 100)

    def test_mode_niveau_honore_le_ciblage(self):
        """Régression v2.0 : le mode sans --weaponised ignorait rune/archétype/lieu."""
        p = forge.generer_prompt("x", LEX, niveau=0.2, rune="ᚦ", archetype="shadow",
                                 location="GANIL_SITE", rng=random.Random(1), bruit_casse=False)
        self.assertIn("RUNE:THURISAZ", p)
        self.assertIn("ARCHETYPE:SHADOW", p)
        self.assertIn("LOCATION:GANIL_SITE", p)


class TestCiblage(unittest.TestCase):
    def test_rune_par_caractere_et_par_nom(self):
        a = forge.invoquer_rune_specifique("ᚦ", LEX, random.Random(1))
        b = forge.invoquer_rune_specifique("thurisaz", LEX, random.Random(1))
        self.assertEqual(a, b)
        self.assertEqual(a[0], "RUNE:THURISAZ")

    def test_rune_inconnue_avertit(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            e = forge.invoquer_rune_specifique("Z", LEX, random.Random(1))
        self.assertIn("non trouvée", err.getvalue())
        self.assertTrue(e[0].startswith("RUNE:"))

    def test_bindrune(self):
        trouves = set()
        for seed in range(100):
            for x in forge.invoquer_rune_specifique("ᚦ", LEX, random.Random(seed)):
                if x.startswith("BINDRUNE:"):
                    trouves.add(x.split("_")[0])
        self.assertEqual(trouves, {"BINDRUNE:THARK", "BINDRUNE:NITHH"})

    def test_archetype_normalise(self):
        e = forge.invoquer_archetype_specifique("Wise-Old", LEX, random.Random(1))
        self.assertEqual(e[0], "ARCHETYPE:WISE_OLD")

    def test_archetype_invalide_avertit(self):
        """Régression v2.0 : l'archétype invalide était ignoré silencieusement."""
        code, _, err = lancer("-p", "x", "-w", "-a", "foo", "-q")
        self.assertEqual(code, 0)
        self.assertIn("Archétype 'foo' non trouvé", err)

    def test_coordonnees_tous_les_lieux_enrichis(self):
        """Régression v2.0 : CAEN_PROFONDE et ROUEN_NEO_GOTHIC n'avaient pas de COORD."""
        for loc in LEX["STRATE_6_INVOCATION_TARGETS"]["locations_specific"]:
            e = forge.invoquer_location_specifique(loc, LEX, random.Random(1))
            self.assertTrue(any(x.startswith("COORD:") for x in e), loc)

    def test_alias_caen(self):
        e = forge.invoquer_location_specifique("caen", LEX, random.Random(1))
        self.assertIn("COORD:[49.1829N, 0.3707W]::CAEN_PROFONDE::DEPTH_7", e)

    def test_normalisation_lieu(self):
        e = forge.invoquer_location_specifique("ganil site", LEX, random.Random(1))
        self.assertEqual(e[0], "LOCATION:GANIL_SITE")

    def test_lieu_inconnu(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            e = forge.invoquer_location_specifique("Atlantide", LEX, random.Random(1))
        self.assertEqual(e, ["LOCATION:ATLANTIDE"])
        self.assertIn("non répertorié", err.getvalue())

    def test_pas_de_faux_positif_sur_sous_chaine(self):
        self.assertIsNone(forge.trouver_coordonnee("AE", LEX))
        self.assertIsNone(forge.trouver_coordonnee("X", LEX))

    def test_lieux_du_lore_sans_avertissement(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            forge.invoquer_location_specifique("DIVE_SUR_MER_GLITCH_HARBOR", LEX, random.Random(1))
        self.assertEqual(err.getvalue(), "")


class TestCLI(unittest.TestCase):
    def test_niveau_invalide(self):
        code, _, err = lancer("-p", "x", "-l", "1.5")
        self.assertEqual(code, 2)
        self.assertIn("entre 0.0 et 1.0", err)

    def test_count_invalide(self):
        for v in ("0", "-3", "abc"):
            self.assertEqual(lancer("-p", "x", "-c", v)[0], 2)

    def test_prompt_requis(self):
        self.assertEqual(lancer()[0], 2)

    def test_lexique_absent_code_1(self):
        code, _, err = lancer("-p", "x", "--lexicon", "/nope.json")
        self.assertEqual(code, 1)
        self.assertIn("introuvable", err)

    def test_list(self):
        code, out, _ = lancer("--list")
        self.assertEqual(code, 0)
        self.assertIn("Thurisaz", out)
        self.assertIn("CAEN_PROFONDE", out)

    def test_quiet_une_ligne_par_prompt(self):
        code, out, _ = lancer("-p", "x", "-c", "3", "-q", "--seed", "1")
        self.assertEqual(code, 0)
        self.assertEqual(len(out.strip().splitlines()), 3)

    def test_level_ignore_avec_weaponised(self):
        _, _, err = lancer("-p", "x", "-w", "-l", "0.2", "-q")
        self.assertIn("--level est ignoré", err)

    def test_no_case_noise(self):
        _, out, _ = lancer("-p", "x", "-w", "--no-case-noise", "-q", "--seed", "3", "--engine", "none")
        self.assertIn("RUNE_SEQUENCE:", out)  # casse d'origine conservée

    def test_save_horodate_et_nom_exact(self):
        with tempfile.TemporaryDirectory() as d:
            code, _, _ = lancer("-p", "x", "-w", "-c", "2", "-q", "--seed", "9",
                                "-s", str(Path(d) / "sub" / "batch"))
            self.assertEqual(code, 0)
            fichiers = list((Path(d) / "sub").glob("batch_*.txt"))
            self.assertEqual(len(fichiers), 1)
            txt = fichiers[0].read_text(encoding="utf-8")
            self.assertIn("# Seed: 9", txt)
            self.assertIn("## Variation 2", txt)

            lancer("-p", "x", "-q", "-s", str(Path(d) / "exact.txt"))
            self.assertTrue((Path(d) / "exact.txt").exists())

    def test_ecriture_impossible_code_1(self):
        code, _, err = lancer("-p", "x", "-q", "-s", "/proc/interdit/x.txt")
        self.assertEqual(code, 1)

    def test_sortie_non_quiet_contient_graine(self):
        _, out, _ = lancer("-p", "x", "-w", "--seed", "11")
        self.assertIn("Graine: 11", out)


class TestImport(unittest.TestCase):
    def test_pas_d_effet_de_bord(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            import importlib
            importlib.reload(forge)
        self.assertEqual(out.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
