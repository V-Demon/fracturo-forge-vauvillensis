#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FracturoPrompt Forge v2.1 - WEAPONISED EDITION
Générateur de prompts glitchés pour modèles de génération d'images.
Basé sur la théorie MTT et le Codex Vauvillensis.

Le script ne fait que concaténer des fragments de texte tirés du lexique JSON :
aucun code n'est exécuté, aucun accès réseau n'est effectué.

Usage :
  python3 fracturo_prompt_forge_v2.py --prompt "portrait" --level 0.9
  python3 fracturo_prompt_forge_v2.py -p "portrait" -w --rune ᚦ --archetype shadow
  python3 fracturo_prompt_forge_v2.py -p "caen street" -w --location CAEN_PROFONDE
  python3 fracturo_prompt_forge_v2.py -p "portrait" -w -c 5 --seed 42 --quiet
  python3 fracturo_prompt_forge_v2.py --list

Codes de sortie : 0 = succès, 1 = lexique introuvable/invalide ou erreur
d'écriture, 2 = arguments invalides.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

__version__ = "2.1.0"

# Chemin par défaut du lexique (relatif à ce fichier, indépendant du cwd)
LEXIQUE_PATH = Path(__file__).resolve().parent / "vauvillensis_lexicon_v2.json"

# --------------------------------------------------------------------------- #
# Constantes
# --------------------------------------------------------------------------- #

CLES_REQUISES: Dict[str, List[str]] = {
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
}

INCANTATION_TYPES = (
    "conditionals", "sql_injections", "bash_commands",
    "function_calls", "loop_structures", "python_code",
)

# (clé dans STRATE_2_CONCEPTS_MTT, préfixe affiché)
CATEGORIES_MTT = (
    ("locations", "LOCATION"),
    ("entities", "ENTITY"),
    ("states", "STATE"),
    ("artifacts", "ARTIFACT"),
)

PAIRES_BRACKETS = {"[": "]", "<": ">", "{": "}"}

NOMS_PALIERS = ("Subtil", "Modéré", "Avancé", "Total")
ENGINES = ("midjourney", "none")

# Plafonds documentés par Midjourney pour --weird (0-3000) et --chaos (0-100)
WEIRD_MAX = 3000


class LexiqueError(Exception):
    """Lexique introuvable, illisible ou incomplet."""


# --------------------------------------------------------------------------- #
# Utilitaires
# --------------------------------------------------------------------------- #

def _avertir(message: str) -> None:
    """Affiche un avertissement sur stderr (n'interfère pas avec --quiet)."""
    print(f"⚠️  {message}", file=sys.stderr)


def _norm(texte: str) -> str:
    """Normalise un identifiant : espaces/tirets -> '_', majuscules."""
    return re.sub(r"[\s\-]+", "_", texte.strip()).upper()


def _echantillon(rng, liste: List[str], n: int) -> List[str]:
    """n éléments distincts (tirage sans remise, borné à la taille de la liste)."""
    return rng.sample(liste, min(n, len(liste)))


def _uniques(tirer: Callable[[], str], n: int) -> List[str]:
    """Appelle `tirer` jusqu'à obtenir n valeurs distinctes (meilleur effort)."""
    vus: List[str] = []
    essais = 0
    while len(vus) < n and essais < n * 10:
        valeur = tirer()
        essais += 1
        if valeur not in vus:
            vus.append(valeur)
    return vus


def palier(niveau: float) -> int:
    """Index du palier de corruption : 0 subtil, 1 modéré, 2 avancé, 3 total."""
    if niveau < 0.3:
        return 0
    if niveau < 0.6:
        return 1
    if niveau < 0.9:
        return 2
    return 3


# --------------------------------------------------------------------------- #
# Chargement et validation du lexique
# --------------------------------------------------------------------------- #

def valider_lexique(lexique: Any) -> None:
    """Vérifie la présence des sections et clés utilisées par le script."""
    if not isinstance(lexique, dict):
        raise LexiqueError("la racine du lexique doit être un objet JSON")
    for section, cles in CLES_REQUISES.items():
        if section not in lexique:
            raise LexiqueError(f"section manquante : {section}")
        for cle in cles:
            if cle not in lexique[section]:
                raise LexiqueError(f"clé manquante : {section}.{cle}")
    if not lexique["RUNES_DATABASE"]["futhark_elder"]:
        raise LexiqueError("RUNES_DATABASE.futhark_elder est vide")


def charger_lexique(chemin: Optional[Path] = None) -> Dict[str, Any]:
    """Charge et valide le lexique JSON. Lève LexiqueError en cas de problème."""
    chemin = Path(chemin) if chemin else LEXIQUE_PATH
    if not chemin.exists():
        raise LexiqueError(f"fichier lexique introuvable : {chemin}")
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            lexique = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise LexiqueError(f"lexique illisible ({chemin}) : {exc}") from exc
    valider_lexique(lexique)
    return lexique


# --------------------------------------------------------------------------- #
# Résolution des entrées utilisateur
# --------------------------------------------------------------------------- #

def resoudre_rune(rune: str, lexique: Dict[str, Any], rng=random) -> Dict[str, str]:
    """Retrouve une rune par caractère (ᚦ) ou par nom (Thurisaz, insensible à la casse).

    Si elle est inconnue : avertissement et rune aléatoire."""
    runes = lexique["RUNES_DATABASE"]["futhark_elder"]
    cle = rune.strip()
    for r in runes:
        if r["char"] == cle or r["name"].lower() == cle.lower():
            return r
    _avertir(f"Rune '{rune}' non trouvée, utilisation aléatoire")
    return rng.choice(runes)


def resoudre_archetype(archetype: str, lexique: Dict[str, Any], rng=random) -> str:
    """Normalise un archétype ('Wise-Old' -> 'wise_old').

    Si inconnu : avertissement et archétype aléatoire."""
    table = lexique["STRATE_3_ARCHETYPES_JUNG_EXTENDED"]
    cle = _norm(archetype).lower()
    if cle in table:
        return cle
    _avertir(f"Archétype '{archetype}' non trouvé, utilisation aléatoire "
             f"(valides : {', '.join(table)})")
    return rng.choice(list(table.keys()))


def lieux_connus(lexique: Dict[str, Any]) -> List[str]:
    """Lieux reconnus : enrichissables (STRATE_6) + lieux du lore (STRATE_2)."""
    cibles = set(lexique["STRATE_6_INVOCATION_TARGETS"]["locations_specific"])
    lore = {_norm(x) for x in lexique["STRATE_2_CONCEPTS_MTT"]["locations"]}
    return sorted(cibles | lore)


def trouver_coordonnee(location: str, lexique: Dict[str, Any]) -> Optional[str]:
    """Coordonnée fractale associée à un lieu.

    Correspondance sur un *segment* exact (séparateur '::'), puis par préfixe de
    segment (>= 3 caractères) : 'CAEN' retrouve ainsi CAEN_PROFONDE."""
    coords = lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]["fractal_coordinates"]
    for coord in coords:
        if location in coord.split("::")[1:]:
            return coord
    if len(location) >= 3:
        for coord in coords:
            if any(seg.startswith(location) for seg in coord.split("::")[1:]):
                return coord
    return None


# --------------------------------------------------------------------------- #
# Blocs de ciblage (--rune / --archetype / --location)
# --------------------------------------------------------------------------- #

def invoquer_rune_specifique(rune: str, lexique: Dict[str, Any], rng=random) -> List[str]:
    """Éléments liés à une rune (+ bindrunes qui la contiennent, p=0.5 chacune)."""
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
    """Éléments liés à un archétype jungien (terme + action + pseudo-code)."""
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
    """Éléments liés à un lieu (étiquette, coordonnée, features p=0.6 chacune)."""
    loc = _norm(location)
    coord = trouver_coordonnee(loc, lexique)
    if loc not in lieux_connus(lexique) and not coord:
        _avertir(f"Lieu '{location}' non répertorié : simple étiquette, sans "
                 f"coordonnées ni features (voir --list)")
    elements = [f"LOCATION:{loc}"]
    if coord:
        elements.append(f"COORD:{coord}")
    features = lexique["STRATE_6_INVOCATION_TARGETS"]["locations_specific"].get(loc, [])
    for feature in features:
        if rng.random() < 0.6:
            elements.append(f"FEATURE:{feature.upper()}")
    return elements


# --------------------------------------------------------------------------- #
# Briques de génération
# --------------------------------------------------------------------------- #

def _jetons_glitch(lexique, rng, n: int) -> List[str]:
    """Erreurs système décorées de brackets : [KERNEL_PANIC], ::NaN, {FAIL}…"""
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


def construire_elements_niveau(lexique, rng, niveau: float) -> List[str]:
    """Éléments pour un niveau de corruption 0.0-1.0 (paliers cumulatifs).

    0.0-0.3 Subtil   : jetons glitch (erreurs + brackets)
    0.3-0.6 Modéré   : + séquence de runes, protocoles, concepts MTT
    0.6-0.9 Avancé   : + archétype, incantations
    0.9-1.0 Total    : + FracturoScript pur (répétitions, miroirs, dégradation,
                         hex, stack traces, buffer overflow, temporel, coordonnée)
    """
    p = palier(niveau)
    s1 = lexique["STRATE_1_SYNTAX_GLITCH"]
    s3 = lexique["STRATE_3_ARCHETYPES_JUNG_EXTENDED"]
    s5 = lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]
    e: List[str] = []

    e += _jetons_glitch(lexique, rng, rng.randint(1, 3) if p == 0 else rng.randint(2, 4))

    if p >= 1:
        e.append(_sequence_runes(lexique, rng, 3, 6))
        e += _echantillon(rng, s1["protocols"], rng.randint(1, 2))
        e += _concepts_mtt(lexique, rng, rng.randint(1, 3))

    if p >= 2:
        cle = rng.choice(list(s3.keys()))
        e.append(f"ARCHETYPE:{cle.upper()}")
        e.append(f"JUNGIAN_{rng.choice(s3[cle]).upper()}")
        e += _incantations(lexique, rng, rng.randint(1, 3))

    if p >= 3:
        e.append(rng.choice(s5["repetition_patterns"]))
        e.append(rng.choice(s5["mirror_sequences"]))
        e.append(rng.choice(s5["degradation_strings"]))
        e += _echantillon(rng, s5["hex_sequences"], rng.randint(2, 4))
        e += _echantillon(rng, s5["stack_traces"], rng.randint(1, 3))
        e.append(rng.choice(s5["buffer_overflows"]))
        e.append(rng.choice(s5["temporal_signatures"]))
        e.append(rng.choice(s5["fractal_coordinates"]))
    return e


def construire_elements_weaponised(lexique, rng) -> List[str]:
    """Pipeline WEAPONISED : toutes les strates, intensité maximale.

    Ajoute 22 à 38 éléments (hors blocs de ciblage), sans doublon dans les
    tirages de listes (hex, stack traces, protocoles, incantations…)."""
    s1 = lexique["STRATE_1_SYNTAX_GLITCH"]
    s4 = lexique["STRATE_4_INCANTATIONS_PSEUDOCODE"]
    s5 = lexique["STRATE_5_FRACTUROSCRIPT_PATTERNS"]
    e: List[str] = []

    e.append(_sequence_runes(lexique, rng, 5, 12))                 # 1. runes
    e.append(_conflit_archetypes(lexique, rng, 2, 4))              # 2. conflit
    e += _incantations(lexique, rng, rng.randint(3, 6))            # 3. incantations
    e.append(rng.choice(s5["buffer_overflows"]))                   # 4. FracturoScript
    e.append(rng.choice(s5["degradation_strings"]))
    e.append(rng.choice(s5["temporal_signatures"]))                # 5. temporel
    e += _echantillon(rng, s5["hex_sequences"], rng.randint(3, 6))  # 6. hex
    e += _echantillon(rng, s5["stack_traces"], rng.randint(2, 4))   # 7. stack traces
    e += _echantillon(rng, s1["protocols"], rng.randint(2, 4))      # 8. protocoles
    # 9. (v2.1) sections auparavant inutilisées
    e += _jetons_glitch(lexique, rng, rng.randint(2, 4))
    e += _echantillon(rng, s5["mirror_sequences"], rng.randint(1, 2))
    e += _echantillon(rng, s5["repetition_patterns"], rng.randint(1, 2))
    e += _concepts_mtt(lexique, rng, rng.randint(2, 4))
    e.append(rng.choice(s4["regex_patterns"]))
    return e


def parametres_moteur(engine: str, niveau: float, weaponised: bool, rng) -> str:
    """Suffixe de paramètres. `midjourney` respecte les plafonds documentés
    (--weird <= 3000, --chaos <= 100) ; `none` n'ajoute rien."""
    if engine == "none":
        return ""
    if weaponised:
        weird = rng.randint(2500, WEIRD_MAX)
        chaos = rng.randint(50, 100)
    else:
        weird = int(niveau * WEIRD_MAX * rng.uniform(0.6, 1.0))
        chaos = int(niveau * 60)
    return f"--weird {weird} --style raw --chaos {chaos}"


def _bruit_de_casse(texte: str, rng, p_maj: float = 0.4) -> str:
    return "".join(c.upper() if rng.random() < p_maj else c.lower() for c in texte)


# --------------------------------------------------------------------------- #
# API principale
# --------------------------------------------------------------------------- #

def generer_prompt(
    prompt_base: str,
    lexique: Dict[str, Any],
    *,
    niveau: float = 0.7,
    weaponised: bool = False,
    rune: Optional[str] = None,
    archetype: Optional[str] = None,
    location: Optional[str] = None,
    rng=None,
    engine: str = "midjourney",
    bruit_casse: bool = True,
) -> str:
    """Génère un prompt glitché.

    - Les blocs de ciblage (rune / archétype / lieu) fonctionnent dans tous les modes.
    - `weaponised=True` ignore `niveau` et active toutes les strates.
    - `rng` : instance `random.Random` (graine reproductible) ; défaut : aléatoire.
    - Le `prompt_base` est toujours conservé tel quel, en tête de sortie : seule
      la partie générée subit l'altération de casse.
    """
    if not 0.0 <= niveau <= 1.0:
        raise ValueError(f"niveau hors de [0, 1] : {niveau}")
    if engine not in ENGINES:
        raise ValueError(f"engine inconnu : {engine} (valides : {', '.join(ENGINES)})")
    rng = rng if rng is not None else random.Random()

    elements: List[str] = []
    if rune:
        elements += invoquer_rune_specifique(rune, lexique, rng)
    if archetype:
        elements += invoquer_archetype_specifique(archetype, lexique, rng)
    if location:
        elements += invoquer_location_specifique(location, lexique, rng)

    if weaponised:
        elements += construire_elements_weaponised(lexique, rng)
        p_bruit = 0.7
    else:
        elements += construire_elements_niveau(lexique, rng, niveau)
        p_bruit = max(0.0, niveau - 0.3)

    corps = ", ".join(elements)
    if bruit_casse and rng.random() < p_bruit:
        corps = _bruit_de_casse(corps, rng)

    morceaux = [prompt_base, corps]
    suffixe = parametres_moteur(engine, niveau, weaponised, rng)
    if suffixe:
        morceaux.append(suffixe)
    return ", ".join(m for m in morceaux if m)


def generer_prompt_weaponised(prompt_base, lexique, rune=None, archetype=None,
                              location=None, rng=None, **kwargs) -> str:
    """Compatibilité v2.0 : équivalent de generer_prompt(..., weaponised=True)."""
    return generer_prompt(prompt_base, lexique, weaponised=True, rune=rune,
                          archetype=archetype, location=location, rng=rng, **kwargs)


def generer_prompt_glitche(prompt_base, niveau, lexique, rune=None, archetype=None,
                           location=None, rng=None, **kwargs) -> str:
    """Mode par niveaux (remplace le stub `generer_prompt_glitche_v1`)."""
    return generer_prompt(prompt_base, lexique, niveau=niveau, rune=rune,
                          archetype=archetype, location=location, rng=rng, **kwargs)


# --------------------------------------------------------------------------- #
# Interface en ligne de commande
# --------------------------------------------------------------------------- #

def afficher_menu() -> None:
    print("\n" + "=" * 70)
    print(f" FRACTURO PROMPT FORGE v{__version__} - WEAPONISED EDITION 🔮")
    print("   Codex Vauvillensis - Théorie MTT - Reality Cracking Protocol")
    print("=" * 70)
    print("\n📊 Niveaux de corruption (cumulatifs, --level) :")
    print("  0.0 - 0.3  : Subtil   (jetons glitch : erreurs + brackets)")
    print("  0.3 - 0.6  : Modéré   (+ runes, protocoles, concepts MTT)")
    print("  0.6 - 0.9  : Avancé   (+ archétype, incantations)")
    print("  0.9 - 1.0  : Total    (+ FracturoScript pur)")
    print("  --weaponised : Maximum (toutes strates ; --level ignoré)")
    print("\n🎯 Invocation ciblée (tous modes) :")
    print("  --rune ᚦ | Thurisaz   --archetype shadow   --location CAEN_PROFONDE")
    print("  (voir --list pour les valeurs valides)")
    print("\n" + "=" * 70 + "\n")


def lister_options(lexique: Dict[str, Any]) -> None:
    print("🔱 Runes (--rune : caractère ou nom)")
    for r in lexique["RUNES_DATABASE"]["futhark_elder"]:
        print(f"  {r['char']}  {r['name']:<9} {r['meaning']}")
    print("\n👁️  Archétypes (--archetype)")
    for cle in lexique["STRATE_3_ARCHETYPES_JUNG_EXTENDED"]:
        print(f"  {cle}")
    print("\n📍 Lieux (--location) ; * = enrichi (features), c = coordonnée fractale")
    specifiques = lexique["STRATE_6_INVOCATION_TARGETS"]["locations_specific"]
    for loc in lieux_connus(lexique):
        marque = "*" if loc in specifiques else " "
        coord = "c" if trouver_coordonnee(loc, lexique) else " "
        print(f"  {marque}{coord} {loc}")


def sauvegarder(prompts: List[str], chemin: str, mode: str, base: str,
                seed: int, engine: str) -> Path:
    """Écrit les prompts en UTF-8. Un nom sans '.txt' reçoit un suffixe horodaté."""
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    cible = Path(chemin if chemin.endswith(".txt") else f"{chemin}_{horodatage}.txt")
    cible.parent.mkdir(parents=True, exist_ok=True)
    with open(cible, "w", encoding="utf-8") as f:
        f.write(f"# FracturoPrompt Forge v{__version__} - {datetime.now()}\n")
        f.write(f"# Mode: {mode}\n")
        f.write(f"# Engine: {engine}\n")
        f.write(f"# Seed: {seed}\n")
        f.write(f"# Prompt original: {base}\n\n")
        for i, prompt in enumerate(prompts, 1):
            f.write(f"## Variation {i}\n{prompt}\n\n")
    return cible


def _niveau_type(valeur: str) -> float:
    try:
        f = float(valeur)
    except ValueError:
        raise argparse.ArgumentTypeError(f"nombre attendu, reçu '{valeur}'")
    if not 0.0 <= f <= 1.0:
        raise argparse.ArgumentTypeError(f"doit être compris entre 0.0 et 1.0 (reçu {f})")
    return f


def _entier_positif(valeur: str) -> int:
    try:
        n = int(valeur)
    except ValueError:
        raise argparse.ArgumentTypeError(f"entier attendu, reçu '{valeur}'")
    if n < 1:
        raise argparse.ArgumentTypeError(f"doit être >= 1 (reçu {n})")
    return n


def construire_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=f"FracturoPrompt Forge v{__version__} - générateur de prompts glitchés"
    )
    p.add_argument("--prompt", "-p", type=str, help="Prompt de base à glitcher")
    p.add_argument("--level", "-l", type=_niveau_type, default=None,
                   help="Niveau de corruption 0.0-1.0 (défaut : 0.7 ; ignoré avec --weaponised)")
    p.add_argument("--rune", "-r", type=str, default=None,
                   help="Rune à invoquer : caractère (ᚦ) ou nom (Thurisaz)")
    p.add_argument("--archetype", "-a", type=str, default=None,
                   help="Archétype jungien : shadow, anima, trickster, wise_old, hero, self")
    p.add_argument("--location", "-loc", type=str, default=None,
                   help="Lieu MTT (ex. CAEN_PROFONDE, BEAUMONT_HAGUE) ; voir --list")
    p.add_argument("--weaponised", "-w", action="store_true",
                   help="Active toutes les strates (intensité maximale)")
    p.add_argument("--count", "-c", type=_entier_positif, default=1,
                   help="Nombre de variations (défaut : 1)")
    p.add_argument("--seed", type=int, default=None,
                   help="Graine aléatoire pour une sortie reproductible")
    p.add_argument("--engine", choices=ENGINES, default="midjourney",
                   help="Suffixe de paramètres : 'midjourney' (--weird/--style/--chaos, "
                        "plafonds respectés) ou 'none' (aucun suffixe)")
    p.add_argument("--no-case-noise", action="store_true",
                   help="Désactive l'altération aléatoire de la casse")
    p.add_argument("--save", "-s", type=str, default=None,
                   help="Sauvegarde dans un fichier (suffixe horodaté si le nom ne finit pas par .txt)")
    p.add_argument("--lexicon", type=Path, default=None,
                   help="Chemin d'un lexique JSON alternatif")
    p.add_argument("--quiet", "-q", action="store_true",
                   help="Sortie minimale : uniquement les prompts, un par ligne")
    p.add_argument("--list", action="store_true",
                   help="Liste les runes, archétypes et lieux valides, puis quitte")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    # Évite les UnicodeEncodeError (runes, émojis) sur les consoles non-UTF-8
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    parser = construire_parser()
    args = parser.parse_args(argv)

    try:
        lexique = charger_lexique(args.lexicon)
    except LexiqueError as exc:
        print(f"❌ Erreur lexique : {exc}", file=sys.stderr)
        return 1

    if args.list:
        lister_options(lexique)
        return 0
    if not args.prompt:
        parser.error("--prompt/-p est requis (sauf avec --list)")

    if args.weaponised and args.level is not None:
        _avertir("--level est ignoré en mode --weaponised")
    niveau = 0.7 if args.level is None else args.level

    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(2 ** 32)
    rng = random.Random(seed)
    mode = "WEAPONISED" if args.weaponised else \
        f"Level {niveau} ({NOMS_PALIERS[palier(niveau)]})"

    if not args.quiet:
        afficher_menu()
        print(f"📝 Prompt original: {args.prompt}")
        print(f"⚔️  MODE: {mode}")
        if args.rune:
            print(f"🔱 Rune invoquée: {args.rune}")
        if args.archetype:
            print(f"👁️  Archétype activé: {args.archetype}")
        if args.location:
            print(f"📍 Localisation ciblée: {args.location}")
        print(f"🔢 Nombre de variations: {args.count}")
        print(f"🎲 Graine: {seed} (rejouable avec --seed {seed})")
        print("\n" + "-" * 70 + "\n")

    prompts: List[str] = []
    for i in range(args.count):
        prompt = generer_prompt(
            args.prompt, lexique,
            niveau=niveau, weaponised=args.weaponised,
            rune=args.rune, archetype=args.archetype, location=args.location,
            rng=rng, engine=args.engine, bruit_casse=not args.no_case_noise,
        )
        prompts.append(prompt)
        if args.quiet:
            print(prompt)
        else:
            print(f"✨ Variation {i + 1}/{args.count}:\n")
            print(prompt)
            print("\n" + "-" * 70 + "\n")

    if args.save:
        try:
            cible = sauvegarder(prompts, args.save, mode, args.prompt, seed, args.engine)
        except OSError as exc:
            print(f"❌ Écriture impossible : {exc}", file=sys.stderr)
            return 1
        if not args.quiet:
            print(f"💾 Prompts sauvegardés dans: {cible}")

    if not args.quiet:
        print("✅ Génération terminée!")
        print("💡 Copiez le prompt dans votre générateur d'images ; "
              "le résultat dépend du modèle utilisé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
