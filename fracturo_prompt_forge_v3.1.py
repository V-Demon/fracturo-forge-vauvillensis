#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  FRACTURO PROMPT FORGE v3.1 — RIFT FORGE PROTOCOL          ║
║  Chimère : Fusion Claude+DeepSeek v3.0 + Ritual Engine     ║
║  Codex Vauvillensis | Théorie MTT | Reality Cracking        ║
╚══════════════════════════════════════════════════════════════╝

Usage :
  python3 fracturo_prompt_forge_v3.1.py -p "prompt" -l 0.9
  python3 fracturo_prompt_forge_v3.1.py --template chaos_gate -w
  python3 fracturo_prompt_forge_v3.1.py -p "x" -e 2075 -g 10
  python3 fracturo_prompt_forge_v3.1.py -p "temple" -x 7 --seed 666
  python3 fracturo_prompt_forge_v3.1.py --template rift_forge --engine grok
"""
from __future__ import annotations
import argparse
import json
import random
import re
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

__version__ = "3.1.0"
LEXIQUE_PATH = Path(__file__).resolve().parent / "vauvillensis_lexicon_v3.1.json"
LEXIQUE_FALLBACK = Path(__file__).resolve().parent / "vauvillensis_lexicon_v3.json"
GRIMOIRE_DIR = Path(__file__).resolve().parent / "grimoires"

# ═══════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════

STRATES = ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8")
CLES_REQUISES_V31: Dict[str, List[str]] = {
    "RUNES_DATABASE": ["futhark_elder", "bindrunes_custom"],
    "STRATE_1_SYNTAX_GLITCH": ["brackets", "errors", "protocols"],
    "STRATE_2_CONCEPTS_MTT": ["locations", "entities", "states", "artifacts"],
    "STRATE_3_ARCHETYPES_JUNG_EXTENDED": [],
    "STRATE_4_INCANTATIONS_PSEUDOCODE": [
        "conditionals", "sql_injections", "bash_commands", "function_calls",
        "loop_structures", "python_code", "regex_patterns",
    ],
    "STRATE_5_FRACTUROSCRIPT_PATTERNS": [
        "repetition_patterns", "mirror_sequences", "degradation_strings",
        "hex_sequences", "stack_traces", "buffer_overflows",
        "fractal_coordinates", "temporal_signatures",
    ],
    "STRATE_6_INVOCATION_TARGETS": ["archetypes_specific", "locations_specific"],
    "STRATE_7_METAMORPHIC_FRACTALS": [
        "self_reference", "spiral_patterns", "echo_chains",
        "temporal_loops", "yin_yang_pairs",
    ],
    "STRATE_8_RITUAL_TEMPLATES": [],
    "STRATE_9_SYNERGIES": [],
    "STRATE_10_ERAS": [],
}

PALETTE_STRATES: Dict[str, Dict[str, Any]] = {
    "S1": {"nom": "Syntax Glitch",    "couleur": 196, "glyphe": "▓"},
    "S2": {"nom": "Concepts MTT",     "couleur": 51,  "glyphe": "◇"},
    "S3": {"nom": "Archétypes Jung",  "couleur": 129, "glyphe": "☯"},
    "S4": {"nom": "Incantations",     "couleur": 208, "glyphe": "⌘"},
    "S5": {"nom": "FracturoScript",   "couleur": 46,  "glyphe": "ᛝ"},
    "S6": {"nom": "Invocation",       "couleur": 213, "glyphe": "✦"},
    "S7": {"nom": "Métamorphose",     "couleur": 250, "glyphe": "∞"},
    "S8": {"nom": "Ritual Template",  "couleur": 220, "glyphe": "◈"},
}

INCANTATION_TYPES = (
    "conditionals", "sql_injections", "bash_commands",
    "function_calls", "loop_structures", "python_code",
)
CATEGORIES_MTT = (
    ("locations", "LOCATION"),
    ("entities", "ENTITY"),
    ("states", "STATE"),
    ("artifacts", "ARTIFACT"),
)
PAIRES_BRACKETS = {"[": "]", "<": ">", "{": "}"}
NOMS_PALIERS = ("Subtil", "Modéré", "Avancé", "Total", "Rift")
PALETTES_CLI = ("fengshui", "mono", "none")


class LexiqueError(Exception):
    """Lexique introuvable, illisible ou incomplet."""


# ═══════════════════════════════════════════════════════════════
# UTILITAIRES
# ═══════════════════════════════════════════════════════════════

def _avertir(message: str) -> None:
    print(f"⚠️  {message}", file=sys.stderr)


def _norm(texte: str) -> str:
    return re.sub(r"[\s\-]+", "_", texte.strip()).upper()


def _echantillon(rng, liste: List[str], n: int) -> List[str]:
    return rng.sample(liste, min(n, len(liste)))


def _uniques(tirer: Callable[[], str], n: int) -> List[str]:
    vus: List[str] = []
    essais = 0
    while len(vus) < n and essais < n * 10:
        valeur = tirer()
        essais += 1
        if valeur not in vus:
            vus.append(valeur)
    return vus


def palier(niveau: float) -> int:
    if niveau < 0.3:
        return 0
    if niveau < 0.6:
        return 1
    if niveau < 0.9:
        return 2
    return 3


# ═══════════════════════════════════════════════════════════════
# CHARGEMENT ET VALIDATION DU LEXIQUE
# ═══════════════════════════════════════════════════════════════

def valider_lexique(lexique: Any) -> None:
    if not isinstance(lexique, dict):
        raise LexiqueError("la racine du lexique doit être un objet JSON")
    for section, cles in CLES_REQUISES_V31.items():
        if section not in lexique:
            raise LexiqueError(f"section manquante : {section}")
        for cle in cles:
            if cle not in lexique[section]:
                raise LexiqueError(f"clé manquante : {section}.{cle}")
    if not lexique["RUNES_DATABASE"]["futhark_elder"]:
        raise LexiqueError("RUNES_DATABASE.futhark_elder est vide")
    if not lexique.get("PROFILES"):
        raise LexiqueError("PROFILES est vide")
    engines = lexique.get("ENGINES_EXTENDED", {})
    for req in ("midjourney", "none"):
        if req not in engines:
            raise LexiqueError(f"ENGINES_EXTENDED doit contenir '{req}'")
    strates_valides = set(STRATES)
    for nom, poids in lexique["PROFILES"].items():
        inconnues = set(poids) - strates_valides
        if inconnues:
            raise LexiqueError(f"profil '{nom}' : strates inconnues {inconnues}")


def _completer_lexique(lexique: Dict[str, Any]) -> Dict[str, Any]:
    ajouts: List[str] = []
    if "STRATE_8_RITUAL_TEMPLATES" not in lexique:
        lexique["STRATE_8_RITUAL_TEMPLATES"] = {}
        ajouts.append("STRATE_8 (vide)")
    if "STRATE_9_SYNERGIES" not in lexique:
        lexique["STRATE_9_SYNERGIES"] = {}
        ajouts.append("STRATE_9 (vide)")
    if "STRATE_10_ERAS" not in lexique:
        lexique["STRATE_10_ERAS"] = {}
        ajouts.append("STRATE_10 (vide)")
    if ajouts:
        _avertir(f"lexique incomplet : ajouts par défaut pour {', '.join(ajouts)}")
    return lexique


def charger_lexique(chemin: Optional[Path] = None) -> Dict[str, Any]:
    if chemin is not None:
        cibles = [Path(chemin)]
    else:
        cibles = [p for p in (LEXIQUE_PATH, LEXIQUE_FALLBACK) if p.exists()]
    if not cibles:
        raise LexiqueError(f"fichier lexique introuvable (essayé : {LEXIQUE_PATH}, {LEXIQUE_FALLBACK})")
    derniere: Optional[LexiqueError] = None
    for cible in cibles:
        if not cible.exists():
            derniere = LexiqueError(f"fichier lexique introuvable : {cible}")
            continue
        try:
            with open(cible, "r", encoding="utf-8") as f:
                lexique = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            derniere = LexiqueError(f"lexique illisible ({cible}) : {exc}")
            continue
        lexique = _completer_lexique(lexique)
        valider_lexique(lexique)
        return lexique
    raise derniere or LexiqueError("aucun lexique chargeable")


# ═══════════════════════════════════════════════════════════════
# RÉSOLUTION DES ENTRÉES UTILISATEUR
# ═══════════════════════════════════════════════════════════════

def resoudre_rune(rune: str, lexique: Dict[str, Any], rng=random) -> Dict[str, str]:
    runes = lexique["RUNES_DATABASE"]["futhark_elder"]
    cle = rune.strip()
    for r in runes:
        if r["char"] == cle or r["name"].lower() == cle.lower():
            return r
    _avertir(f"Rune '{rune}' non trouvée, utilisation aléatoire")
    return rng.choice(runes)


def resoudre_archetype(archetype: str, lexique: Dict[str, Any], rng=random) -> str:
    table = lexique["STRATE_3_ARCHETYPES_JUNG_EXTENDED"]
    cle = _norm(archetype).lower()
    if cle in table:
        return cle
    _avertir(f"Archétype '{archetype}' non trouvé, utilisation aléatoire")
    return rng.choice(list(table.keys()))


def lieux_connus(lexique: Dict[str, Any]) -> List[str]:
    cibles = set(lexique["STRATE_6_INVOCATION_TARGETS"]["locations_specific"])
    lore = {_norm(x) for x in lexique["STRATE_2_CONCEPTS_MTT"]["locations"]}
    return sorted(cibles | lore)


def trouver_coordonnee(location: str, lexique: Dict[str, Any]) -> Optional[str]:
    coords = lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["fractal_coordinates"]
    for coord in coords:
        if location in coord.split("::")[1:]:
            return coord
    if len(location) >= 3:
        for coord in coords:
            if any(seg.startswith(location) for seg in coord.split("::")[1:]):
                return coord
    return None


# ═══════════════════════════════════════════════════════════════
# INVOKEURS CIBLÉS (S6)
# ═══════════════════════════════════════════════════════════════

def invoquer_rune_specifique(rune: str, lexique: Dict[str, Any], rng=random) -> List[str]:
    data = resoudre_rune(rune, lexique, rng)
    elements = [
        f"RUNE:{data['name'].upper()}",
        f"MEANING:{data['meaning']}",
        f"ELEMENT:{data['element'].upper()}",
        f"ARCHETYPE:{data['archetype'].upper()}",
        data["char"] * rng.randint(3, 7),
    ]
    for nom, bind in lexique["RUNES_DATABASE"]["bindrunes_custom"].items():
        if data["char"] in bind["chars"] and rng.random() < 0.5:
            elements.append(f"BINDRUNE:{nom}_{bind['meaning']}")
    return elements


def invoquer_archetype_specifique(archetype: str, lexique: Dict[str, Any], rng=random) -> List[str]:
    cle = resoudre_archetype(archetype, lexique, rng)
    terme = rng.choice(lexique["STRATE_3_ARCHETYPES_JUNG_EXTENDED"][cle])
    elements = [f"ARCHETYPE:{cle.upper()}", f"JUNGIAN_{terme.upper()}"]
    actions = lexique["STRATE_6_INVOCATION_TARGETS"]["archetypes_specific"].get(cle)
    if actions:
        action = rng.choice(actions)
        elements.append(f"ACTION:{action.upper()}")
        elements.append(f"if (archetype == '{cle}') {{ {action}(); }}")
    return elements


def invoquer_location_specifique(location: str, lexique: Dict[str, Any], rng=random) -> List[str]:
    loc = _norm(location)
    coord = trouver_coordonnee(loc, lexique)
    elements = [f"LOCATION:{loc}"]
    if coord:
        elements.append(f"COORD:{coord}")
    features = lexique["STRATE_6_INVOCATION_TARGETS"]["locations_specific"].get(loc, [])
    for feature in features:
        if rng.random() < 0.6:
            elements.append(f"FEATURE:{feature.upper()}")
    return elements


# ═══════════════════════════════════════════════════════════════
# SYSTÈME DE SYNERGIES (S9)
# ═══════════════════════════════════════════════════════════════

def detecter_synergie(rune: Optional[str], archetype: Optional[str],
                     location: Optional[str], lexique: Dict[str, Any]) -> Optional[Dict]:
    synergies = lexique.get("STRATE_9_SYNERGIES", {})
    for nom, syn in synergies.items():
        if not isinstance(syn, dict):   # ← AJOUTER CETTE LIGNE
            continue                     # ← SAUTE "description"
        trigger = syn["trigger"]
        match_rune = (rune is None or rune == trigger.get("rune"))
        match_arch = (archetype is None or archetype.lower() == trigger.get("archetype", "").lower())
        match_loc = (location is None or location.upper() == trigger.get("location", "").upper())
        matches = sum([match_rune, match_arch, match_loc])
        if matches >= 2:
            return {"name": nom, **syn}
    return None


def activer_synergie(synergie: Dict) -> List[str]:
    return [
        f"═══ SYNERGY::{synergie['name'].upper()} ═══",
        synergie["incantation"],
        f"EFFECT::{synergie['effect']}",
        f"SIG::{synergie['hex_signature']}",
    ]


# ═══════════════════════════════════════════════════════════════
# TEMPLATES D'INVOCATION (S8)
# ═══════════════════════════════════════════════════════════════

def appliquer_template(template_nom: str, lexique: Dict[str, Any]) -> Optional[Dict]:
    templates = lexique.get("STRATE_8_RITUAL_TEMPLATES", {})
    if template_nom not in templates:
        _avertir(f"Template '{template_nom}' inconnu. Valides : {list(templates.keys())}")
        return None
    return templates[template_nom]


def deployer_template(template: Dict, lexique: Dict[str, Any], rng=random) -> Tuple[List[str], float, Optional[str]]:
    elements = [f"═══ TEMPLATE::{template['base'][:40].upper()}... ═══"]
    for rune in template.get("runes", []):
        elements.extend(invoquer_rune_specifique(rune, lexique, rng))
    if template.get("archetype"):
        elements.extend(invoquer_archetype_specifique(template["archetype"], lexique, rng))
    for inc in template.get("incantations", []):
        elements.append(inc)
    glitch_level = template.get("glitch_level", 0.8)
    synergie_trigger = template.get("synergie_trigger")
    return elements, glitch_level, synergie_trigger


# ═══════════════════════════════════════════════════════════════
# MODE RÉCURSION TEMPORELLE (S10 - ERA)
# ═══════════════════════════════════════════════════════════════

def injecter_era(era: str, lexique: Dict[str, Any], rng=random) -> List[str]:
    era = era.upper()
    eras = lexique.get("STRATE_10_ERAS", {})
    if era not in eras:
        _avertir(f"Era '{era}' inconnue. Valides : {list(eras.keys())}")
        return []
    data = eras[era]
    elements = [
        f"═══ ERA::{era} ═══",
        f"PHASE::{data.get('description', 'UNKNOWN')}::",
    ]
    if rng.random() < 0.7 and data.get("locations"):
        elements.append(f"LOCATION::{rng.choice(data['locations'])}")
    if rng.random() < 0.6 and data.get("entities"):
        elements.append(f"ENTITY::{rng.choice(data['entities'])}")
    if rng.random() < 0.7 and data.get("states"):
        elements.append(f"STATE::{rng.choice(data['states'])}")
    elements.append(f"AESTHETIC::{data.get('aesthetic', 'glitch')}")
    return elements


# ═══════════════════════════════════════════════════════════════
# BRIQUES DE GÉNÉRATION PAR STRATE
# ═══════════════════════════════════════════════════════════════

def _jetons_glitch(lexique, rng, n: int) -> List[str]:
    s1 = lexique["STRATE_1_SYNTAX_GLITCH"]
    def tirer() -> str:
        err = rng.choice(s1["errors"])
        b = rng.choice(s1["brackets"])
        return f"{b}{err}{PAIRES_BRACKETS[b]}" if b in PAIRES_BRACKETS else f"{b}{err}"
    return _uniques(tirer, n)


def _sequence_runes(lexique, rng, lo: int, hi: int) -> str:
    chars = [r["char"] for r in lexique["RUNES_DATABASE"]["futhark_elder"]]
    return "RUNE_SEQUENCE:" + "".join(rng.choices(chars, k=rng.randint(lo, hi)))


def _conflit_archetypes(lexique, rng, lo: int, hi: int) -> str:
    cles = list(lexique["STRATE_3_ARCHETYPES_JUNG_EXTENDED"].keys())
    choisis = rng.sample(cles, k=min(rng.randint(lo, hi), len(cles)))
    return "ARCHETYPE_CONFLICT:" + "_VS_".join(choisis).upper()


def _incantations(lexique, rng, n: int) -> List[str]:
    s4 = lexique["STRATE_4_INCANTATIONS_PSEUDOCODE"]
    return _uniques(lambda: rng.choice(s4[rng.choice(INCANTATION_TYPES)]), n)


def _concepts_mtt(lexique, rng, n: int) -> List[str]:
    s2 = lexique["STRATE_2_CONCEPTS_MTT"]
    def tirer() -> str:
        cle, prefixe = rng.choice(CATEGORIES_MTT)
        return f"{prefixe}:{rng.choice(s2[cle])}"
    return _uniques(tirer, n)


def _fractales_s7(lexique, rng, n_self: int = 1) -> List[str]:
    s7 = lexique["STRATE_7_METAMORPHIC_FRACTALS"]
    e: List[str] = []
    e += _echantillon(rng, s7["self_reference"], n_self)
    e.append(rng.choice(s7["spiral_patterns"]))
    e.append(rng.choice(s7["echo_chains"]))
    e.append(rng.choice(s7["temporal_loops"]))
    a, b = rng.choice(s7["yin_yang_pairs"])
    e.append(f"YIN_YANG:{a}_{b}")
    return e


def construire_elements_niveau(lexique, rng, niveau: float) -> Dict[str, List[str]]:
    p = palier(niveau)
    s1 = lexique["STRATE_1_SYNTAX_GLITCH"]
    s3 = lexique["STRATE_3_ARCHETYPES_JUNG_EXTENDED"]
    s5 = lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]
    e: Dict[str, List[str]] = {s: [] for s in STRATES}
    e["S1"] += _jetons_glitch(lexique, rng, rng.randint(1, 3) if p == 0 else rng.randint(2, 4))
    if p >= 1:
        e["S2"].append(_sequence_runes(lexique, rng, 3, 6))
        e["S2"] += _echantillon(rng, s1["protocols"], rng.randint(1, 2))
        e["S2"] += _concepts_mtt(lexique, rng, rng.randint(1, 3))
    if p >= 2:
        cle = rng.choice(list(s3.keys()))
        e["S3"].append(f"ARCHETYPE:{cle.upper()}")
        e["S3"].append(f"JUNGIAN_{rng.choice(s3[cle]).upper()}")
        e["S4"] += _incantations(lexique, rng, rng.randint(1, 3))
    if p >= 3:
        e["S5"].append(rng.choice(s5["repetition_patterns"]))
        e["S5"].append(rng.choice(s5["mirror_sequences"]))
        e["S5"].append(rng.choice(s5["degradation_strings"]))
        e["S5"] += _echantillon(rng, s5["hex_sequences"], rng.randint(2, 4))
        e["S5"] += _echantillon(rng, s5["stack_traces"], rng.randint(1, 3))
        e["S5"].append(rng.choice(s5["buffer_overflows"]))
        e["S5"].append(rng.choice(s5["temporal_signatures"]))
        e["S5"].append(rng.choice(s5["fractal_coordinates"]))
        e["S7"] += _fractales_s7(lexique, rng, n_self=1)
    return e


def construire_elements_weaponised(lexique, rng) -> Dict[str, List[str]]:
    s1 = lexique["STRATE_1_SYNTAX_GLITCH"]
    s4 = lexique["STRATE_4_INCANTATIONS_PSEUDOCODE"]
    s5 = lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]
    e: Dict[str, List[str]] = {s: [] for s in STRATES}
    e["S2"].append(_sequence_runes(lexique, rng, 5, 12))
    e["S3"].append(_conflit_archetypes(lexique, rng, 2, 4))
    e["S4"] += _incantations(lexique, rng, rng.randint(3, 6))
    e["S5"].append(rng.choice(s5["buffer_overflows"]))
    e["S5"].append(rng.choice(s5["degradation_strings"]))
    e["S5"].append(rng.choice(s5["temporal_signatures"]))
    e["S5"] += _echantillon(rng, s5["hex_sequences"], rng.randint(3, 6))
    e["S5"] += _echantillon(rng, s5["stack_traces"], rng.randint(2, 4))
    e["S2"] += _echantillon(rng, s1["protocols"], rng.randint(2, 4))
    e["S1"] += _jetons_glitch(lexique, rng, rng.randint(2, 4))
    e["S5"] += _echantillon(rng, s5["mirror_sequences"], rng.randint(1, 2))
    e["S5"] += _echantillon(rng, s5["repetition_patterns"], rng.randint(1, 2))
    e["S2"] += _concepts_mtt(lexique, rng, rng.randint(2, 4))
    e["S4"].append(rng.choice(s4["regex_patterns"]))
    e["S7"] += _fractales_s7(lexique, rng, n_self=rng.randint(1, 2))
    return e


# ═══════════════════════════════════════════════════════════════
# PONDÉRATION PAR PROFIL
# ═══════════════════════════════════════════════════════════════

def _resoudre_poids(lexique: Dict[str, Any], profil: Optional[str], weights_cli: Optional[str]) -> Dict[str, float]:
    poids: Dict[str, float] = {s: 1.0 for s in STRATES}
    if profil:
        table = lexique.get("PROFILES", {})
        if profil not in table:
            raise ValueError(f"profil inconnu : {profil} (valides : {', '.join(table)})")
        for s in STRATES:
            poids[s] = float(table[profil].get(s, 1.0))
    if weights_cli:
        for morceau in weights_cli.split(","):
            morceau = morceau.strip()
            if not morceau:
                continue
            if "=" not in morceau:
                raise ValueError(f"poids invalide : '{morceau}' (format S1=2.0)")
            cle, val = morceau.split("=", 1)
            cle = cle.strip().upper()
            if cle not in STRATES:
                raise ValueError(f"strate inconnue dans --weights : {cle}")
            try:
                poids[cle] = max(0.0, float(val))
            except ValueError:
                raise ValueError(f"poids non numérique : {morceau}")
    return poids


def _appliquer_poids(elements: Dict[str, List[str]], poids: Dict[str, float], rng) -> Dict[str, List[str]]:
    sortie: Dict[str, List[str]] = {}
    for cle, lst in elements.items():
        w = poids.get(cle, 1.0)
        if w <= 0 or not lst:
            sortie[cle] = []
            continue
        n_cible = max(1, round(len(lst) * w))
        sortie[cle] = lst if n_cible >= len(lst) else _echantillon(rng, lst, n_cible)
    return sortie


# ═══════════════════════════════════════════════════════════════
# MOTEURS (SUFFIXE PARAMÉTRIQUE)
# ═══════════════════════════════════════════════════════════════

def _bornes(lexique: Dict[str, Any], engine: str, cle: str, defaut: Tuple[int, int]) -> Tuple[int, int]:
    spec = lexique.get("ENGINES_EXTENDED", {}).get(engine, {})
    bornes = spec.get(cle, list(defaut))
    return int(bornes[0]), int(bornes[1])


def parametres_moteur(engine: str, niveau: float, weaponised: bool, rng,
                     lexique: Optional[Dict[str, Any]] = None, seed: Optional[int] = None) -> str:
    if engine == "none":
        return ""
    if lexique is None:
        lexique = {"ENGINES_EXTENDED": {
            "midjourney": {"suffix": "--weird {weird} --style raw --chaos {chaos}",
                          "weird": [0, 3000], "chaos": [0, 100]},
            "none": {"suffix": ""},
        }}
    spec = lexique["ENGINES_EXTENDED"].get(engine)
    if not spec:
        raise ValueError(f"engine inconnu du lexique : {engine}")
    gabarit = spec.get("suffix", "")
    if not gabarit:
        return ""
    valeurs: Dict[str, Any] = {}
    if "{weird}" in gabarit:
        lo, hi = _bornes(lexique, engine, "weird", (0, 3000))
        valeurs["weird"] = rng.randint(int(lo * 0.8), hi) if weaponised \
            else int(niveau * hi * rng.uniform(0.6, 1.0))
    if "{chaos}" in gabarit:
        lo, hi = _bornes(lexique, engine, "chaos", (0, 100))
        valeurs["chaos"] = rng.randint(max(lo, hi // 2), hi) if weaponised \
            else int(niveau * hi)
    if "{cfg}" in gabarit:
        lo, hi = _bornes(lexique, engine, "cfg", (1, 10))
        valeurs["cfg"] = rng.randint(lo, hi)
    if "{steps}" in gabarit:
        lo, hi = _bornes(lexique, engine, "steps", (20, 80))
        valeurs["steps"] = rng.randint(lo, hi)
    if "{seed}" in gabarit:
        valeurs["seed"] = seed if seed is not None else rng.randrange(2 ** 32)
    return gabarit.format(**valeurs)


def _bruit_de_casse(texte: str, rng, p_maj: float = 0.4) -> str:
    return "".join(c.upper() if rng.random() < p_maj else c.lower() for c in texte)


# ═══════════════════════════════════════════════════════════════
# REVEALER CYBER-FENG-SHUI
# ═══════════════════════════════════════════════════════════════

class Revealer:
    def __init__(self, actif: bool = True, ascii_mode: bool = False,
                 largeur: int = 72, palette: str = "fengshui", flux=None) -> None:
        self.flux = flux or sys.stdout
        self.ascii = ascii_mode or palette == "none"
        self.palette = palette
        self.largeur = max(40, largeur)
        self.actif = actif and not self.ascii and self._est_tty()
        self._t0: Optional[datetime] = None

    def _est_tty(self) -> bool:
        try:
            return bool(self.flux.isatty())
        except (AttributeError, ValueError):
            return False

    def _c(self, strate: str) -> str:
        if not self.actif:
            return ""
        if self.palette == "mono":
            return "\x1b[38;5;250m"
        return f"\x1b[38;5;{PALETTE_STRATES.get(strate, {'couleur': 250})['couleur']}m"

    def _r(self) -> str:
        return "\x1b[0m" if self.actif else ""

    def _glyphe(self, strate: str) -> str:
        if self.ascii:
            return "*"
        return PALETTE_STRATES.get(strate, {"glyphe": "·"})["glyphe"]

    def debut(self, total_strates: int) -> None:
        if not self.actif:
            return
        self._t0 = datetime.now()
        titre = " RIFT FORGE — RÉVÉLATION "
        pad = max(0, (self.largeur - len(titre)) // 2)
        self.flux.write(f"\n{'═' * pad}{titre}{'═' * pad}\n")

    def strate(self, cle: str, elements: List[str]) -> None:
        if not self.actif or not elements:
            return
        info = PALETTE_STRATES.get(cle, {"nom": cle})
        c, r = self._c(cle), self._r()
        self.flux.write(f"{c}{self._glyphe(cle)} {info['nom']:<22}{r}\n")
        for e in elements:
            tronque = e if len(e) <= self.largeur - 6 else e[: self.largeur - 9] + "..."
            self.flux.write(f"  {c}│{r} {tronque}\n")
        self.flux.flush()

    def synergie(self, nom: str, effet: str) -> None:
        if not self.actif:
            return
        c, r = "\x1b[38;5;220m", "\x1b[0m"
        self.flux.write(f"\n{c}◈ SYNERGIE DÉTECTÉE : {nom.upper()}{r}\n")
        self.flux.write(f"{c}  → {effet}{r}\n")
        self.flux.flush()

    def barre(self, fait: int, total: int, strate: str = "S5") -> None:
        if not self.actif:
            return
        n = max(1, int(self.largeur * 0.6))
        plein = int(n * fait / max(1, total))
        c, r = self._c(strate), self._r()
        self.flux.write(f"\r{c}[{'█' * plein}{'░' * (n - plein)}] {100 * fait // max(1, total):>3}%{r}")
        self.flux.flush()

    def fin(self) -> Optional[float]:
        if not self.actif or not self._t0:
            return None
        dt = (datetime.now() - self._t0).total_seconds()
        self.flux.write(f"\n{'─' * self.largeur}\n")
        return dt


# ═══════════════════════════════════════════════════════════════
# API PRINCIPALE
# ═══════════════════════════════════════════════════════════════

def _aplatir(elements: Dict[str, List[str]]) -> List[str]:
    plat: List[str] = []
    for cle in STRATES:
        plat.extend(elements.get(cle, []))
    return plat


def generer_prompt(
    prompt_base: str,
    lexique: Dict[str, Any],
    *,
    niveau: float = 0.7,
    weaponised: bool = False,
    rune: Optional[str] = None,
    archetype: Optional[str] = None,
    location: Optional[str] = None,
    era: Optional[str] = None,
    template: Optional[str] = None,
    rng=None,
    engine: str = "midjourney",
    bruit_casse: bool = True,
    revealer: Optional[Revealer] = None,
    weights: Optional[Dict[str, float]] = None,
    profile: Optional[str] = None,
    weights_cli: Optional[str] = None,
    seed: Optional[int] = None,
    retour_details: bool = False,
) -> Union[str, Dict[str, Any]]:
    if not 0.0 <= niveau <= 1.0:
        raise ValueError(f"niveau hors de [0, 1] : {niveau}")
    engines_dispo = tuple(lexique.get("ENGINES_EXTENDED", {"midjourney": {}, "none": {}}).keys())
    if engine not in engines_dispo:
        raise ValueError(f"engine inconnu : {engine} (valides : {', '.join(engines_dispo)})")
    rng = rng if rng is not None else random.Random()
    t0 = datetime.now()
    poids = weights if weights is not None else _resoudre_poids(lexique, profile, weights_cli)
    elements: Dict[str, List[str]] = {s: [] for s in STRATES}
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "niveau": niveau,
        "rune": rune, "archetype": archetype, "location": location,
        "era": era, "template": template, "weaponised": weaponised,
        "seed": seed, "synergie_detectee": None,
    }

    # ── TEMPLATE (S8) ──
    synergie_trigger = None
    if template:
        tpl = appliquer_template(template, lexique)
        if tpl:
            tpl_elements, glitch_level, synergie_trigger = deployer_template(tpl, lexique, rng)
            elements["S8"] = tpl_elements
            niveau = max(niveau, glitch_level)
            if tpl.get("era"):
                era = tpl.get("era")

    # ── ERA (S10) ──
    if era:
        elements["S2"] += injecter_era(era, lexique, rng)

    # ── INVOKEURS CIBLÉS (S6) ──
    if rune:
        elements["S6"] += invoquer_rune_specifique(rune, lexique, rng)
    if archetype:
        elements["S6"] += invoquer_archetype_specifique(archetype, lexique, rng)
    if location:
        elements["S6"] += invoquer_location_specifique(location, lexique, rng)

    # ── SYNERGIE (S9) ──
    synergie = detecter_synergie(rune, archetype, location, lexique)
    if synergie:
        metadata["synergie_detectee"] = synergie["name"]
        elements["S6"] += activer_synergie(synergie)
        if revealer:
            revealer.synergie(synergie["name"], synergie["effect"])
    elif synergie_trigger:
        syn_trig = lexique.get("STRATE_9_SYNERGIES", {}).get(synergie_trigger)
        if syn_trig:
            metadata["synergie_detectee"] = synergie_trigger
            elements["S6"] += activer_synergie(syn_trig)
            if revealer:
                revealer.synergie(synergie_trigger, syn_trig["effect"])

    # ── STRATES SELON NIVEAU ──
    if weaponised:
        construits = construire_elements_weaponised(lexique, rng)
        p_bruit = 0.7
    else:
        construits = construire_elements_niveau(lexique, rng, niveau)
        p_bruit = max(0.0, niveau - 0.3)
    construits = _appliquer_poids(construits, poids, rng)
    for s in STRATES:
        elements[s] += construits[s]

    # ── REVEALER ──
    if revealer is not None:
        non_vides = [s for s in STRATES if elements[s]]
        revealer.debut(len(non_vides))
        for i, s in enumerate(non_vides, 1):
            revealer.strate(s, elements[s])
            revealer.barre(i, len(non_vides), s)

    # ── ASSEMBLAGE ──
    corps = ", ".join(_aplatir(elements))
    if bruit_casse and rng.random() < p_bruit:
        corps = _bruit_de_casse(corps, rng)
    morceaux = [prompt_base, corps]
    suffixe = parametres_moteur(engine, niveau, weaponised, rng, lexique, seed)
    if suffixe:
        morceaux.append(suffixe)
    prompt = ", ".join(m for m in morceaux if m)

    if revealer is not None:
        revealer.fin()

    metadata["hash"] = hashlib.sha256(prompt.encode()).hexdigest()[:16]
    metadata["longueur"] = len(prompt)

    if retour_details:
        dt = (datetime.now() - t0).total_seconds()
        return {
            "prompt": prompt,
            "elements_par_strate": elements,
            "poids": poids,
            "engine": engine,
            "suffixe": suffixe,
            "mode": "WEAPONISED" if weaponised else f"Level {niveau} ({NOMS_PALIERS[min(palier(niveau), 4)]})",
            "seed": seed,
            "timings": {"total_s": round(dt, 4)},
            "metadata": metadata,
        }
    return prompt


# ═══════════════════════════════════════════════════════════════
# MODE ÉCHO (DÉGRADATION PROGRESSIVE)
# ═══════════════════════════════════════════════════════════════

def generer_echo(prompt_base: str, lexique: Dict[str, Any], count: int = 5,
                 degradation: float = 0.1, **kwargs) -> List[Dict]:
    resultats = []
    niveau = 0.5
    for i in range(count):
        rituel = generer_prompt(
            prompt_base, lexique,
            niveau=min(1.0, niveau + (i * degradation)),
            seed=(kwargs.get("seed") or 666) + i,
            retour_details=True, **kwargs
        )
        rituel["metadata"]["echo_index"] = i
        rituel["metadata"]["echo_degradation"] = round(niveau, 2)
        resultats.append(rituel)
        niveau += degradation
    return resultats


# ═══════════════════════════════════════════════════════════════
# GRIMOIRE (SAUVEGARDE STRUCTURÉE)
# ═══════════════════════════════════════════════════════════════

def sauvegarder_grimoire(rituels: List[Dict], nom: str, metadata_globale: Dict):
    GRIMOIRE_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = GRIMOIRE_DIR / f"{nom}_{timestamp}.json"
    grimoire = {
        "codex": "Vauvillensis_v3.1_RiftForge",
        "engine": f"FracturoPrompt Forge v{__version__}",
        "created": datetime.now().isoformat(),
        "metadata_globale": metadata_globale,
        "rituels": rituels,
        "lignee_memetique": hashlib.sha256(
            json.dumps(rituels, ensure_ascii=False).encode()
        ).hexdigest()[:32]
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(grimoire, f, ensure_ascii=False, indent=2)
    print(f"📖 Grimoire sauvegardé : {filename}")
    return filename


# ═══════════════════════════════════════════════════════════════
# INTERFACE CLI
# ═══════════════════════════════════════════════════════════════

BANNER = f"""
╔══════════════════════════════════════════════════════════════╗
║   🔮 FRACTURO PROMPT FORGE v{__version__} — RIFT FORGE PROTOCOL 🔮     ║
║   Chimère : Claude+DeepSeek v3.0 × Ritual Engine            ║
║   Codex Vauvillensis | Théorie MTT | Reality Cracking       ║
╚══════════════════════════════════════════════════════════════╝
"""


def afficher_aide():
    print(BANNER)
    print("""
⚔️  MODES D'INVOCATION :
  --prompt, -p TEXT       Prompt de base (requis sauf --template)
  --level, -l FLOAT       Niveau 0.0-1.0 (défaut: 0.7 ; ignoré avec -w)
  --rune, -r RUNE         Rune spécifique (ᚦ, ᚺ, ᛁ, ᛞ, etc.)
  --archetype, -a ARCH    Archétype (shadow, trickster, hero...)
  --location, -loc LOC    Localisation (CAEN_PROFONDE, etc.)
  --era, -e ERA           Époque (2025 | 2075 | FRACTAL)
  --template, -t TPL      Template pré-construit
  --weaponised, -w        Mode weaponised maximal
  --engine, -eng NAME     Moteur (midjourney, stable_diffusion, flux, dalle, grok, none)

🎨 RÉVÉLATION FENG-SHUI :
  --reveal / --no-reveal  Force/désactive le Revealer
  --ascii                 Mode ASCII (pas d'ANSI)
  --palette NAME          fengshui | mono | none
  --width N               Largeur du Revealer (>= 40)

⚖️  PONDÉRATION :
  --profile NAME          Profil (minimal, balanced, jungian, glitch, maximal, ritual, echo, rift)
  --weights 'S1=2,S3=0.5' Surcharge des poids

🔁 MODES SPÉCIAUX :
  --echo, -x COUNT        Mode écho (dégradation progressive)
  --grimoire, -g COUNT    Génère N variations + sauvegarde JSON
  --seed, -s INT          Graine reproductible
  --count, -c INT         Nombre de variations (défaut: 1)
  --format text|json      Format de sortie
  --dry-run               Valide et affiche le plan sans générer
  --stats                 Affiche un récapitulatif
  --list                  Liste runes/archétypes/lieux valides
  --profiles              Liste profils et moteurs
  --quiet, -q             Sortie minimale

📋 TEMPLATES DISPONIBLES :
  shadow_revelation | temporal_fold | chaos_gate
  rune_smith_forge | memetic_contagion | echo_guillaume | rift_forge

🔱 EXEMPLES :
  python3 fracturo_prompt_forge_v3.1.py -p "RuneSmith" -r ᚦ -a shadow -l 0.9
  python3 fracturo_prompt_forge_v3.1.py --template chaos_gate -w --engine grok
  python3 fracturo_prompt_forge_v3.1.py -p "Caen" -e 2075 -g 10 --profile rift
  python3 fracturo_prompt_forge_v3.1.py -p "temple" -x 7 --seed 666
  python3 fracturo_prompt_forge_v3.1.py --template rift_forge --engine grok -w
""")


def lister_options(lexique: Dict[str, Any]) -> None:
    print("🔱 Runes (--rune : caractère ou nom)")
    for r in lexique["RUNES_DATABASE"]["futhark_elder"]:
        print(f"  {r['char']}  {r['name']:<9} {r['meaning']}")
    print("\n👁️  Archétypes (--archetype)")
    for cle in lexique["STRATE_3_ARCHETYPES_JUNG_EXTENDED"]:
        print(f"  {cle}")
    print("\n📍 Lieux (--location)")
    for loc in lieux_connus(lexique):
        print(f"  {loc}")
    print("\n⏳ Eras (--era)")
    for era in lexique.get("STRATE_10_ERAS", {}):
        print(f"  {era}")
    print("\n📜 Templates (--template)")
    for tpl, data in lexique.get("STRATE_8_RITUAL_TEMPLATES", {}).items():
        if isinstance(data, dict):
            print(f"  {tpl}")

    print("\n◈ Synergies (détection automatique)")
    for syn, data in lexique.get("STRATE_9_SYNERGIES", {}).items():
        if isinstance(data, dict):
            print(f"  {syn}")


def lister_profils(lexique: Dict[str, Any]) -> None:
    print("⚖️  Profils de pondération (--profile)")
    for nom, poids in lexique.get("PROFILES", {}).items():
        if not isinstance(poids, dict):
            continue
        detail = " ".join(f"{s}={poids.get(s, 1.0):.1f}" for s in STRATES)
        print(f"  {nom:<10} {detail}")
    print("\n🎛️  Moteurs (--engine)")
    for nom, spec in lexique.get("ENGINES_EXTENDED", {}).items():
        if not isinstance(spec, dict):
            continue
        suffixe = spec.get("suffix") or "(aucun)"
        print(f"  {nom:<16} {suffixe}")


def main(argv: Optional[List[str]] = None) -> int:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description=f"FracturoPrompt Forge v{__version__}")
    parser.add_argument("--prompt", "-p", type=str, default=None)
    parser.add_argument("--level", "-l", type=float, default=None)
    parser.add_argument("--rune", "-r", type=str, default=None)
    parser.add_argument("--archetype", "-a", type=str, default=None)
    parser.add_argument("--location", "-loc", type=str, default=None)
    parser.add_argument("--era", "-e", type=str, default=None)
    parser.add_argument("--template", "-t", type=str, default=None)
    parser.add_argument("--weaponised", "-w", action="store_true")
    parser.add_argument("--engine", "-eng", type=str, default="midjourney")
    parser.add_argument("--reveal", dest="reveal", action="store_true", default=None)
    parser.add_argument("--no-reveal", dest="reveal", action="store_false")
    parser.add_argument("--ascii", action="store_true")
    parser.add_argument("--palette", choices=PALETTES_CLI, default="fengshui")
    parser.add_argument("--width", type=int, default=72)
    parser.add_argument("--profile", type=str, default=None)
    parser.add_argument("--weights", type=str, default=None)
    parser.add_argument("--echo", "-x", type=int, default=0)
    parser.add_argument("--grimoire", "-g", type=int, default=0)
    parser.add_argument("--seed", "-s", type=int, default=None)
    parser.add_argument("--count", "-c", type=int, default=1)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--profiles", action="store_true")
    parser.add_argument("--quiet", "-q", action="store_true")
    parser.add_argument("--lexicon", type=Path, default=None)
    parser.add_argument("--no-case-noise", action="store_true")

    args = parser.parse_args(argv)

    try:
        lexique = charger_lexique(args.lexicon)
    except LexiqueError as exc:
        print(f"❌ Erreur lexique : {exc}", file=sys.stderr)
        return 1

    if args.list:
        lister_options(lexique)
        return 0
    if args.profiles:
        lister_profils(lexique)
        return 0

    if not args.prompt and not args.template:
        parser.error("--prompt ou --template requis")

    if args.weaponised and args.level is not None:
        _avertir("--level est ignoré en mode --weaponised")

    try:
        poids = _resoudre_poids(lexique, args.profile, args.weights)
    except ValueError as exc:
        parser.error(str(exc))

    if args.engine not in lexique.get("ENGINES_EXTENDED", {}):
        parser.error(f"--engine '{args.engine}' absent du lexique")

    niveau = 0.7 if args.level is None else args.level
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(2 ** 32)
    rng = random.Random(seed)
    mode = "WEAPONISED" if args.weaponised else f"Level {niveau} ({NOMS_PALIERS[min(palier(niveau), 4)]})"

    if args.dry_run:
        strates = [s for s, w in poids.items() if w > 0]
        print(f"[DRY-RUN] Lexique OK")
        print(f"[DRY-RUN] Mode: {mode}  Engine: {args.engine}  Profil: {args.profile or '(défaut)'}")
        print(f"[DRY-RUN] Poids: " + " ".join(f"{s}={poids[s]:.1f}" for s in STRATES))
        print(f"[DRY-RUN] Strates: {','.join(strates) if strates else '(aucune)'}")
        if args.rune:
            print(f"[DRY-RUN] Rune: {args.rune}  Arch: {args.archetype or '-'}  Loc: {args.location or '-'}")
        if args.era:
            print(f"[DRY-RUN] Era: {args.era}")
        if args.template:
            print(f"[DRY-RUN] Template: {args.template}")
        return 0

    revealer_actif = args.reveal if args.reveal is not None else (not args.quiet and args.format == "text")
    revealer = Revealer(
        actif=revealer_actif, ascii_mode=args.ascii,
        largeur=args.width, palette=args.palette,
    )

    if not args.quiet and args.format == "text":
        afficher_aide()
        print(f"📝 Base     : {args.prompt or '(template)'}")
        print(f"⚔️  MODE     : {mode}")
        if args.profile: print(f"⚖️  Profil   : {args.profile}")
        if args.rune: print(f"🔱 Rune    : {args.rune}")
        if args.archetype: print(f"👁️  Arch    : {args.archetype}")
        if args.location: print(f"📍 Loc    : {args.location}")
        if args.era: print(f"⏳ Era    : {args.era}")
        if args.template: print(f"📜 Template: {args.template}")
        if args.weaponised: print(f"💀 Weaponised: OUI")
        print(f"🎲 Seed   : {seed}")
        print(f"🔢 Count  : {args.count}")
        print("\n" + "-" * 70 + "\n")

    prompts: List[str] = []
    details_all: List[Dict[str, Any]] = []

    # ── MODE ÉCHO ──
    if args.echo > 0:
        base = args.prompt or "void"
        print(f"🌊 MODE ÉCHO : {args.echo} variations avec dégradation progressive\n")
        resultats = generer_echo(
            base, lexique, args.echo,
            rune=args.rune, archetype=args.archetype, location=args.location,
            era=args.era, template=args.template, weaponised=args.weaponised,
            engine=args.engine, seed=seed,
        )
        for i, r in enumerate(resultats, 1):
            print(f"═══ ÉCHO {i}/{args.echo} (dégradation: {r['metadata'].get('echo_degradation', '?')}) ═══")
            print(r["prompt"])
            print()
            prompts.append(r["prompt"])
            details_all.append(r)
        if args.save:
            sauvegarder_grimoire(details_all, args.save, {"mode": "echo", "count": args.echo})
        return 0

    # ── MODE GRIMOIRE ──
    if args.grimoire > 0:
        base = args.prompt or "void"
        print(f"📖 GRIMOIRE : {args.grimoire} rituels en cours d'invocation...\n")
        for i in range(args.grimoire):
            seed_i = seed + i
            r = generer_prompt(
                base, lexique, niveau=niveau, weaponised=args.weaponised,
                rune=args.rune, archetype=args.archetype, location=args.location,
                era=args.era, template=args.template, rng=random.Random(seed_i),
                engine=args.engine, weights=poids, seed=seed_i, retour_details=True,
            )
            details_all.append(r)
            prompts.append(r["prompt"])
            print(f"  [{i+1}/{args.grimoire}] {r['metadata']['hash']}")
        metadata_globale = {
            "prompt_base": base, "count": args.grimoire,
            "level": niveau, "rune": args.rune, "archetype": args.archetype,
            "location": args.location, "era": args.era, "template": args.template,
        }
        sauvegarder_grimoire(details_all, "grimoire", metadata_globale)
        return 0

    # ── MODE STANDARD ──
    for i in range(args.count):
        seed_i = seed + i
        r = generer_prompt(
            args.prompt or "void", lexique,
            niveau=niveau, weaponised=args.weaponised,
            rune=args.rune, archetype=args.archetype, location=args.location,
            era=args.era, template=args.template, rng=random.Random(seed_i),
            engine=args.engine, bruit_casse=not args.no_case_noise,
            revealer=revealer if args.format == "text" else None,
            weights=poids, seed=seed_i, retour_details=(args.format == "json" or args.stats),
        )
        if isinstance(r, dict):
            prompts.append(r["prompt"])
            details_all.append(r)
        else:
            prompts.append(r)

        if args.format == "text" and not args.quiet:
            print(f"✨ Variation {i+1}/{args.count}:\n")
            print(prompts[-1])
            print("\n" + "-" * 70 + "\n")

    if args.format == "json":
        if args.quiet:
            for d in details_all:
                print(json.dumps(d, ensure_ascii=False))
        else:
            print(json.dumps({"seed": seed, "mode": mode, "engine": args.engine,
                            "variations": details_all}, ensure_ascii=False, indent=2))
    elif args.quiet:
        for p in prompts:
            print(p)

    if args.stats:
        total_elem = sum(len(_aplatir(d["elements_par_strate"])) for d in details_all)
        duree = sum(d["timings"]["total_s"] for d in details_all)
        par_strate = {s: sum(len(d["elements_par_strate"][s]) for d in details_all) for s in STRATES}
        flux = sys.stdout if not args.quiet else sys.stderr
        print(f"\n📊 STATS  seed={seed}  variations={args.count}  éléments={total_elem}  durée={duree:.3f}s", file=flux)
        print("   par strate: " + " ".join(f"{s}={n}" for s, n in par_strate.items()), file=flux)

    if not args.quiet and args.format == "text":
        print("✅ Génération terminée!")
        print("💡 Copiez le prompt dans votre générateur d'images favori.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
