"""
vauv_core — cœur (sans Qt) de l'éditeur de lexiques Vauvillensis / RiftForge.

Contient :
  * le schéma déclaratif (champs, ensembles d'enregistrements, strates) ;
  * la validation (structure, types, bornes, références croisées) ;
  * les gabarits (document complet et entrées individuelles) ;
  * la lecture / écriture (détection des clés en double, écriture atomique,
    mise en forme proche du fichier d'origine pour des diffs lisibles) ;
  * le Document : données + historique annuler/rétablir + notifications.

Utilisable seul :   python vauv_core.py mon_lexique.json
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any, Callable, Iterable

KeyPath = tuple  # tuple[str | int, ...]

# ════════════════════════════════════════════════════════════════════════════
#  Constantes de structure
# ════════════════════════════════════════════════════════════════════════════
S_META = "META_DATA"
S_RUNES = "RUNES_DATABASE"
S1 = "STRATE_1_SYNTAX_GLITCH"
S2 = "STRATE_2_CONCEPTS_MTT"
S3 = "STRATE_3_ARCHETYPES_JUNG_EXTENDED"
S4 = "STRATE_4_INCANTATIONS_PSEUDOCODE"
S5 = "STRATE_5_FRACTUROSCRIPT_PATTERNS"
S6 = "STRATE_6_INVOCATION_TARGETS"
S7 = "STRATE_7_METAMORPHIC_FRACTALS"
S8 = "STRATE_8_RITUAL_TEMPLATES"
S9 = "STRATE_9_SYNERGIES"
S10 = "STRATE_10_ERAS"
S_PROFILES = "PROFILES"
S_ENGINES = "ENGINES_EXTENDED"

SECTION_ORDER = (S_META, S_RUNES, S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S_PROFILES, S_ENGINES)

ELEMENTS = ("fire", "water", "earth", "air", "ice")

ELDER_FUTHARK = (
    ("ᚠ", "Fehu"), ("ᚢ", "Uruz"), ("ᚦ", "Thurisaz"), ("ᚨ", "Ansuz"), ("ᚱ", "Raido"),
    ("ᚲ", "Kenaz"), ("ᚷ", "Gebo"), ("ᚹ", "Wunjo"), ("ᚺ", "Hagalaz"), ("ᚾ", "Nauthiz"),
    ("ᛁ", "Isa"), ("ᛃ", "Jera"), ("ᛇ", "Eihwaz"), ("ᛈ", "Perthro"), ("ᛉ", "Algiz"),
    ("ᛊ", "Sowilo"), ("ᛏ", "Tiwaz"), ("ᛒ", "Berkana"), ("ᛖ", "Ehwaz"), ("ᛗ", "Mannaz"),
    ("ᛚ", "Laguz"), ("ᛜ", "Ingwaz"), ("ᛞ", "Dagaz"), ("ᛟ", "Othala"),
)

# Catégories attendues dans les strates « listes » (clé de strate -> clés).
STRATA_LISTS: dict[str, tuple[str, ...]] = {
    S1: ("brackets", "errors", "protocols"),
    S2: ("locations", "entities", "states", "artifacts"),
    S3: ("shadow", "anima", "trickster", "wise_old", "hero", "self"),
    S4: ("conditionals", "sql_injections", "bash_commands", "function_calls",
         "loop_structures", "python_code", "regex_patterns"),
    S5: ("repetition_patterns", "mirror_sequences", "degradation_strings", "hex_sequences",
         "stack_traces", "buffer_overflows", "fractal_coordinates", "temporal_signatures"),
    S7: ("self_reference", "spiral_patterns", "echo_chains", "temporal_loops", "yin_yang_pairs"),
}
# Strates où l'on peut ajouter / renommer / supprimer des catégories.
OPEN_KEY_PATHS: set[KeyPath] = {
    (S3,), (S6, "archetypes_specific"), (S6, "locations_specific"),
}

CATEGORY_LABELS = {
    "brackets": "Délimiteurs", "errors": "Erreurs", "protocols": "Protocoles",
    "locations": "Lieux", "entities": "Entités", "states": "États", "artifacts": "Artefacts",
    "shadow": "Ombre", "anima": "Anima", "trickster": "Farceur", "wise_old": "Vieux sage",
    "hero": "Héros", "self": "Soi",
    "conditionals": "Conditions", "sql_injections": "Injections SQL", "bash_commands": "Commandes bash",
    "function_calls": "Appels de fonction", "loop_structures": "Boucles", "python_code": "Code Python",
    "regex_patterns": "Expressions régulières",
    "repetition_patterns": "Répétitions", "mirror_sequences": "Séquences miroir",
    "degradation_strings": "Dégradations", "hex_sequences": "Séquences hexa",
    "stack_traces": "Traces de pile", "buffer_overflows": "Débordements",
    "fractal_coordinates": "Coordonnées fractales", "temporal_signatures": "Signatures temporelles",
    "self_reference": "Auto-référence", "spiral_patterns": "Spirales", "echo_chains": "Chaînes d'échos",
    "temporal_loops": "Boucles temporelles", "yin_yang_pairs": "Paires yin-yang",
}

PROFILE_AXES = tuple(f"S{i}" for i in range(1, 9))
AXIS_LABELS = {
    "S1": "Syntaxe glitch", "S2": "Concepts MTT", "S3": "Archétypes", "S4": "Incantations",
    "S5": "Fracturoscript", "S6": "Cibles", "S7": "Fractales", "S8": "Rituels",
}
RUNTIME_PLACEHOLDERS = {"seed"}   # paramètres fournis à l'exécution, sans plage

RUNIC_RE = re.compile(r"^[\u16A0-\u16FF]$")
HEX_SIG_RE = re.compile(r"^0x[A-Z0-9_]+$")
VERSION_RE = re.compile(r"^\d+(\.\d+)*$")
PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


class Severity(IntEnum):
    ERROR = 0
    WARNING = 1
    INFO = 2


SEVERITY_LABEL = {Severity.ERROR: "Erreur", Severity.WARNING: "Avertissement", Severity.INFO: "Info"}


# ════════════════════════════════════════════════════════════════════════════
#  Schéma déclaratif des champs
# ════════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str          # str text rune runestr runelist float int enum ref strlist record
    required: bool = True
    choices: tuple = ()
    ref: str = ""      # archetypes synergies eras locations rune_names rune_chars
    strict: bool = True   # valeur inconnue / hors bornes : ERREUR (sinon AVERTISSEMENT)
    min: float | None = None
    max: float | None = None
    step: float = 0.05
    fields: tuple = ()
    hint: str = ""
    empty: Severity = Severity.WARNING
    default: Any = None
    pattern: str = ""


@dataclass(frozen=True)
class RecordSet:
    id: str
    title: str
    path: KeyPath
    container: str                 # "list" | "dict"
    fields: tuple
    label: str = "{key}"           # affichage dans la liste maîtresse
    header: tuple = ()             # champs portés par le conteneur lui-même (dict)
    key_label: str = "Identifiant"
    key_ref: str = ""              # clé choisie parmi des valeurs dynamiques
    noun: str = "entrée"
    extra: str = ""                # "ranges" (moteurs)


E, W, I = Severity.ERROR, Severity.WARNING, Severity.INFO

FUTHARK_FIELDS = (
    Field("char", "Rune", "rune", empty=E, hint="Un seul caractère runique (U+16A0 à U+16FF)."),
    Field("name", "Nom", "str", empty=E),
    Field("meaning", "Sens", "str", empty=I, hint="Mots-clés en snake_case, ex. wealth_primal_energy."),
    Field("element", "Élément", "enum", choices=ELEMENTS, strict=False, empty=I),
    Field("archetype", "Concept associé", "str", empty=I, hint="Ex. creation, threshold, wisdom."),
)
BINDRUNE_FIELDS = (
    Field("chars", "Runes liées", "runestr", empty=E, hint="Suite de runes formant la bindrune."),
    Field("meaning", "Sens", "str", empty=W),
)
RUNE_TARGET_FIELDS = (
    Field("char", "Rune", "rune", ref="rune_chars", empty=E),
    Field("actions", "Actions", "strlist", hint="Verbes d'invocation associés à la rune."),
)
RITUAL_FIELDS = (
    Field("base", "Scène de base", "text", empty=E, hint="Description anglaise de l'image à générer."),
    Field("runes", "Runes", "runelist"),
    Field("archetype", "Archétype", "ref", ref="archetypes"),
    Field("incantations", "Incantations", "strlist"),
    Field("glitch_level", "Niveau de glitch", "float", min=0.0, max=1.0, step=0.05, default=0.5),
    Field("synergie_trigger", "Synergie déclenchée", "ref", ref="synergies"),
    Field("era", "Époque", "ref", ref="eras", required=False),
)
SYNERGY_FIELDS = (
    Field("trigger", "Déclencheur", "record", fields=(
        Field("rune", "Rune", "rune", ref="rune_chars"),
        Field("archetype", "Archétype", "ref", ref="archetypes"),
        Field("location", "Lieu", "ref", ref="locations", strict=False),
    )),
    Field("incantation", "Incantation", "text"),
    Field("effect", "Effet", "str"),
    Field("hex_signature", "Signature hexa", "str", pattern=HEX_SIG_RE.pattern,
          hint="Format 0xNOM_123 (majuscules, chiffres, souligné)."),
)
ERA_FIELDS = (
    Field("description", "Description", "str"),
    Field("locations", "Lieux", "strlist"),
    Field("entities", "Entités", "strlist"),
    Field("states", "États", "strlist"),
    Field("aesthetic", "Esthétique", "str", hint="Étiquettes séparées par des virgules."),
)
PROFILE_FIELDS = tuple(
    Field(a, f"{a}  {AXIS_LABELS[a]}", "float", min=0.0, max=2.0, step=0.05, strict=False, default=1.0)
    for a in PROFILE_AXES
)
ENGINE_FIELDS = (
    Field("suffix", "Suffixe de prompt", "str", empty=I,
          hint="Utilisez {param} pour insérer un paramètre, ex. --chaos {chaos}."),
    Field("note", "Note", "str", required=False, empty=I),
)

RECORDSETS: dict[str, RecordSet] = {rs.id: rs for rs in (
    RecordSet("futhark", "Futhark ancien", (S_RUNES, "futhark_elder"), "list", FUTHARK_FIELDS,
              label="{char}  {name}", noun="rune"),
    RecordSet("bindrunes", "Bindrunes", (S_RUNES, "bindrunes_custom"), "dict", BINDRUNE_FIELDS,
              label="{key}", key_label="Nom", noun="bindrune"),
    RecordSet("rune_targets", "Cibles par rune", (S6, "runes_by_name"), "dict", RUNE_TARGET_FIELDS,
              label="{key}", key_label="Nom de rune", key_ref="rune_names", noun="cible"),
    RecordSet("rituals", "Rituels", (S8,), "dict", RITUAL_FIELDS, label="{key}",
              header=(Field("description", "Description de la strate", "text", required=False, empty=I),),
              key_label="Identifiant du rituel", noun="rituel"),
    RecordSet("synergies", "Synergies", (S9,), "dict", SYNERGY_FIELDS, label="{key}",
              header=(Field("description", "Description de la strate", "text", required=False, empty=I),),
              key_label="Identifiant de la synergie", noun="synergie"),
    RecordSet("eras", "Époques", (S10,), "dict", ERA_FIELDS, label="{key}",
              key_label="Année ou nom", noun="époque"),
    RecordSet("profiles", "Profils", (S_PROFILES,), "dict", PROFILE_FIELDS, label="{key}",
              key_label="Nom du profil", noun="profil"),
    RecordSet("engines", "Moteurs", (S_ENGINES,), "dict", ENGINE_FIELDS, label="{key}",
              key_label="Nom du moteur", noun="moteur", extra="ranges"),
)}


# ════════════════════════════════════════════════════════════════════════════
#  Chemins, problèmes, index
# ════════════════════════════════════════════════════════════════════════════
def get_path(data: Any, path: Iterable, default: Any = None) -> Any:
    cur = data
    for k in path:
        try:
            cur = cur[k]
        except (KeyError, IndexError, TypeError):
            return default
    return cur


def format_path(path: KeyPath) -> str:
    return " › ".join(f"#{p + 1}" if isinstance(p, int) else str(p) for p in path)


@dataclass(frozen=True)
class Issue:
    severity: Severity
    path: KeyPath
    message: str
    code: str = ""

    @property
    def path_str(self) -> str:
        return format_path(self.path)


class IssueIndex:
    """Index des problèmes par préfixe de chemin (pastilles, surlignage)."""

    def __init__(self, issues: Iterable[Issue] = ()):
        self.issues = list(issues)
        self._worst: dict[KeyPath, Severity] = {}
        self._counts: dict[KeyPath, list[int]] = {}
        self._exact: dict[KeyPath, list[Issue]] = {}
        for i in self.issues:
            self._exact.setdefault(i.path, []).append(i)
            for n in range(1, len(i.path) + 1):
                p = i.path[:n]
                if p not in self._worst or i.severity < self._worst[p]:
                    self._worst[p] = i.severity
                self._counts.setdefault(p, [0, 0, 0])[int(i.severity)] += 1

    def worst(self, path: KeyPath) -> Severity | None:
        return self._worst.get(tuple(path))

    def counts(self, path: KeyPath) -> tuple[int, int, int]:
        return tuple(self._counts.get(tuple(path), (0, 0, 0)))  # type: ignore[return-value]

    def at(self, path: KeyPath) -> list[Issue]:
        return self._exact.get(tuple(path), [])

    def total(self) -> tuple[int, int, int]:
        c = [0, 0, 0]
        for i in self.issues:
            c[int(i.severity)] += 1
        return tuple(c)  # type: ignore[return-value]


# ════════════════════════════════════════════════════════════════════════════
#  Valeurs dynamiques (références croisées)
# ════════════════════════════════════════════════════════════════════════════
def _dict_keys(data: Any, path: KeyPath, skip: tuple = ("description",)) -> list[str]:
    d = get_path(data, path)
    return [k for k in d if k not in skip] if isinstance(d, dict) else []


def choices_for(ref: str, data: dict) -> list[tuple[str, str]]:
    """Valeurs possibles (valeur, libellé) pour une référence dynamique."""
    if ref == "archetypes":
        return [(k, k) for k in _dict_keys(data, (S3,))]
    if ref == "synergies":
        return [(k, k) for k in _dict_keys(data, (S9,))]
    if ref == "eras":
        return [(k, k) for k in _dict_keys(data, (S10,))]
    if ref == "locations":
        v = get_path(data, (S2, "locations"), [])
        return [(x, x) for x in v if isinstance(x, str)] if isinstance(v, list) else []
    fut = get_path(data, (S_RUNES, "futhark_elder"), [])
    fut = [r for r in fut if isinstance(r, dict)] if isinstance(fut, list) else []
    if ref == "rune_names":
        return [(r["name"], r["name"]) for r in fut if isinstance(r.get("name"), str)]
    if ref == "rune_chars":
        return [(r["char"], f"{r['char']}  {r.get('name', '')}".rstrip())
                for r in fut if isinstance(r.get("char"), str)]
    return []


def default_for(f: Field, data: dict | None = None) -> Any:
    data = data or {}
    if f.default is not None:
        return copy.deepcopy(f.default)
    k = f.kind
    if k in ("str", "text", "runestr"):
        return ""
    if k in ("strlist", "runelist"):
        return []
    if k in ("float", "int"):
        v = f.min if f.min is not None else 0
        return float(v) if k == "float" else int(v)
    if k == "enum":
        return f.choices[0] if f.choices else ""
    if k in ("ref", "rune"):
        ch = choices_for(f.ref, data) if f.ref else []
        return ch[0][0] if ch else ""
    if k == "record":
        return {sub.key: default_for(sub, data) for sub in f.fields}
    return ""


def blank_record(fields: Iterable[Field], data: dict | None = None) -> dict:
    return {f.key: default_for(f, data) for f in fields if f.required}


def unique_key(base: str, existing: Iterable[str]) -> str:
    existing = set(existing)
    if base not in existing:
        return base
    n = 2
    while f"{base}_{n}" in existing:
        n += 1
    return f"{base}_{n}"


# ════════════════════════════════════════════════════════════════════════════
#  Validation
# ════════════════════════════════════════════════════════════════════════════
def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


class _Validator:
    def __init__(self, data: Any):
        self.d = data
        self.issues: list[Issue] = []
        self.fut_chars = {c for c, _ in choices_for("rune_chars", data)} if isinstance(data, dict) else set()
        self.archetypes = {c for c, _ in choices_for("archetypes", data)} if isinstance(data, dict) else set()
        self.locations = {c for c, _ in choices_for("locations", data)} if isinstance(data, dict) else set()
        self.synergies = {c for c, _ in choices_for("synergies", data)} if isinstance(data, dict) else set()
        self.eras = {c for c, _ in choices_for("eras", data)} if isinstance(data, dict) else set()

    # -- utilitaires -------------------------------------------------------
    def add(self, sev: Severity, path: KeyPath, msg: str, code: str = "") -> None:
        self.issues.append(Issue(sev, tuple(path), msg, code))

    def container(self, path: KeyPath, typ: type, required: bool = True) -> Any:
        v = get_path(self.d, path, None)
        if v is None:
            if required:
                self.add(E, path, "Section ou champ manquant.", "missing")
            return None
        if not isinstance(v, typ):
            names = {dict: "un objet", list: "une liste", str: "un texte"}
            self.add(E, path, f"Doit être {names.get(typ, typ.__name__)} (trouvé : {type(v).__name__}).", "type")
            return None
        return v

    def str_list(self, path: KeyPath, value: Any, unique: bool = True) -> list:
        if not isinstance(value, list):
            self.add(E, path, f"Doit être une liste de textes (trouvé : {type(value).__name__}).", "type")
            return []
        seen: dict[str, int] = {}
        for i, x in enumerate(value):
            p = path + (i,)
            if not isinstance(x, str):
                self.add(E, p, f"L'élément n°{i + 1} n'est pas un texte ({type(x).__name__}).", "type")
            elif not x.strip():
                self.add(E, p, f"Élément n°{i + 1} vide.", "empty")
            else:
                if x != x.strip():
                    self.add(W, p, f"Espaces superflus autour de « {x.strip()} ».", "whitespace")
                if unique:
                    if x in seen:
                        self.add(W, p, f"Doublon de l'élément n°{seen[x] + 1} (« {x} »).", "duplicate")
                    else:
                        seen[x] = i
        return value

    # -- validation générique d'un champ ------------------------------------
    def field(self, path: KeyPath, f: Field, value: Any) -> None:
        k = f.kind
        sev_range = E if f.strict else W
        if k in ("str", "text"):
            if not isinstance(value, str):
                return self.add(E, path, f"« {f.label} » doit être un texte.", "type")
            if not value.strip():
                return self.add(f.empty, path, f"« {f.label} » est vide.", "empty")
            if f.pattern and not re.match(f.pattern, value):
                self.add(W, path, f"« {f.label} » : format inattendu ({f.hint or f.pattern}).", "pattern")
        elif k == "rune":
            if not isinstance(value, str) or not value:
                return self.add(f.empty, path, f"« {f.label} » est vide.", "empty")
            if not RUNIC_RE.match(value):
                return self.add(E, path, f"« {value} » n'est pas un unique caractère runique.", "rune")
            if f.ref and value not in self.fut_chars:
                self.add(W, path, f"La rune {value} n'existe pas dans le Futhark ancien déclaré.", "ref")
        elif k == "runestr":
            if not isinstance(value, str) or not value:
                return self.add(f.empty, path, f"« {f.label} » est vide.", "empty")
            bad = [c for c in value if not RUNIC_RE.match(c)]
            if bad:
                return self.add(E, path, f"Caractères non runiques : {' '.join(sorted(set(bad)))}", "rune")
            out = sorted({c for c in value if c not in self.fut_chars})
            if out:
                self.add(I, path, f"Runes hors Futhark ancien déclaré : {' '.join(out)}", "ref")
        elif k == "runelist":
            if not isinstance(value, list):
                return self.add(E, path, "Doit être une liste de runes.", "type")
            if not value:
                self.add(W, path, "Aucune rune.", "empty")
            for i, c in enumerate(value):
                p = path + (i,)
                if not isinstance(c, str) or not RUNIC_RE.match(c):
                    self.add(E, p, f"« {c} » n'est pas un unique caractère runique.", "rune")
                elif c not in self.fut_chars:
                    self.add(W, p, f"La rune {c} n'existe pas dans le Futhark ancien déclaré.", "ref")
        elif k in ("float", "int"):
            if not _is_num(value):
                return self.add(E, path, f"« {f.label} » doit être un nombre.", "type")
            if k == "int" and isinstance(value, float) and not value.is_integer():
                self.add(E, path, f"« {f.label} » doit être un entier.", "type")
            if f.min is not None and value < f.min:
                self.add(E, path, f"« {f.label} » = {value} est inférieur au minimum {f.min}.", "range")
            if f.max is not None and value > f.max:
                self.add(sev_range, path, f"« {f.label} » = {value} dépasse le maximum {f.max}.", "range")
        elif k == "enum":
            if not isinstance(value, str):
                return self.add(E, path, f"« {f.label} » doit être un texte.", "type")
            if not value:
                return self.add(f.empty, path, f"« {f.label} » est vide.", "empty")
            if value not in f.choices:
                self.add(sev_range, path, f"« {value} » n'est pas dans : {', '.join(f.choices)}.", "enum")
        elif k == "ref":
            if not isinstance(value, str):
                return self.add(E, path, f"« {f.label} » doit être un texte.", "type")
            if not value:
                return self.add(E if f.strict else f.empty, path, f"« {f.label} » est vide.", "empty")
            allowed = {c for c, _ in choices_for(f.ref, self.d)}
            if value not in allowed:
                self.add(sev_range, path, f"« {value} » est introuvable ({f.label.lower()}).", "ref")
        elif k == "strlist":
            self.str_list(path, value)
        elif k == "record":
            if not isinstance(value, dict):
                return self.add(E, path, f"« {f.label} » doit être un objet.", "type")
            self.record(path, value, f.fields)

    def record(self, path: KeyPath, rec: dict, fields: tuple, allow_extra: bool = False) -> None:
        known = {f.key for f in fields}
        for f in fields:
            if f.key not in rec:
                if f.required:
                    self.add(E, path + (f.key,), f"Champ obligatoire « {f.key} » absent.", "missing")
                continue
            self.field(path + (f.key,), f, rec[f.key])
        if not allow_extra:
            for k in rec:
                if k not in known:
                    self.add(I, path + (k,), f"Champ « {k} » non prévu par le schéma.", "unknown")

    # -- sections ------------------------------------------------------------
    def run(self) -> list[Issue]:
        if not isinstance(self.d, dict):
            self.add(E, (), "La racine du fichier doit être un objet JSON.", "type")
            return self.issues
        for k in SECTION_ORDER:
            if k not in self.d:
                self.add(E, (k,), f"Section « {k} » absente.", "missing")
        for k in self.d:
            if k not in SECTION_ORDER:
                self.add(W, (k,), f"Section « {k} » inconnue.", "unknown")
        self.meta()
        self.runes()
        for key in (S1, S2, S3, S4, S5, S7):
            self.strata_lists(key)
        self.s5_patterns()
        self.s6()
        self.s7_pairs()
        self.records_rituals()
        self.records_synergies()
        self.records_eras()
        self.profiles()
        self.engines()
        order = {k: n for n, k in enumerate(SECTION_ORDER)}
        self.issues.sort(key=lambda i: (order.get(i.path[0], 99) if i.path else -1, int(i.severity)))
        return self.issues

    def meta(self) -> None:
        m = self.container((S_META,), dict)
        if m is None:
            return
        keys = ("version", "codex", "classification", "target_engine", "theory", "warning", "changelog")
        for k in keys:
            if k not in m:
                self.add(W, (S_META, k), f"Métadonnée « {k} » absente.", "missing")
            elif not isinstance(m[k], str):
                self.add(E, (S_META, k), f"« {k} » doit être un texte.", "type")
            elif not m[k].strip():
                self.add(W, (S_META, k), f"« {k} » est vide.", "empty")
        v = m.get("version")
        if isinstance(v, str) and v.strip() and not VERSION_RE.match(v):
            self.add(W, (S_META, "version"), f"Version « {v} » : format attendu 3.1 ou 3.1.2.", "pattern")

    def runes(self) -> None:
        r = self.container((S_RUNES,), dict)
        if r is None:
            return
        fut = self.container((S_RUNES, "futhark_elder"), list)
        if fut is not None:
            if len(fut) != 24:
                self.add(I, (S_RUNES, "futhark_elder"), f"{len(fut)} runes déclarées (le Futhark ancien en compte 24).", "count")
            seen_c: dict[str, int] = {}
            seen_n: dict[str, int] = {}
            for i, rec in enumerate(fut):
                p = (S_RUNES, "futhark_elder", i)
                if not isinstance(rec, dict):
                    self.add(E, p, "Chaque rune doit être un objet.", "type")
                    continue
                self.record(p, rec, FUTHARK_FIELDS)
                c, n = rec.get("char"), rec.get("name")
                if isinstance(c, str) and c:
                    if c in seen_c:
                        self.add(E, p + ("char",), f"Rune {c} déjà déclarée (#{seen_c[c] + 1}).", "duplicate")
                    seen_c.setdefault(c, i)
                if isinstance(n, str) and n:
                    if n in seen_n:
                        self.add(E, p + ("name",), f"Nom « {n} » déjà utilisé (#{seen_n[n] + 1}).", "duplicate")
                    seen_n.setdefault(n, i)
        bind = self.container((S_RUNES, "bindrunes_custom"), dict)
        if bind is not None:
            for name, rec in bind.items():
                p = (S_RUNES, "bindrunes_custom", name)
                if not isinstance(rec, dict):
                    self.add(E, p, "Chaque bindrune doit être un objet.", "type")
                    continue
                self.record(p, rec, BINDRUNE_FIELDS)

    def strata_lists(self, key: str) -> None:
        sec = self.container((key,), dict)
        if sec is None:
            return
        expected = STRATA_LISTS[key]
        open_keys = (key,) in OPEN_KEY_PATHS
        if not open_keys:
            for k in expected:
                if k not in sec:
                    self.add(E, (key, k), f"Catégorie « {k} » absente.", "missing")
        for k, v in sec.items():
            p = (key, k)
            if not open_keys and k not in expected:
                self.add(W, p, f"Catégorie « {k} » non prévue par le schéma.", "unknown")
            if k == "yin_yang_pairs":
                continue
            self.str_list(p, v)
        if open_keys and not sec:
            self.add(W, (key,), "Aucun archétype déclaré.", "empty")

    def s5_patterns(self) -> None:
        sec = get_path(self.d, (S5,))
        if not isinstance(sec, dict):
            return
        for i, s in enumerate(sec.get("mirror_sequences", []) if isinstance(sec.get("mirror_sequences"), list) else []):
            if not isinstance(s, str):
                continue
            n = len(s) // 2
            ok = len(s) % 2 == 1 and s[n] == "_" and s[:n] == s[n + 1:][::-1]
            if not ok:
                self.add(W, (S5, "mirror_sequences", i),
                         f"« {s} » n'est pas de la forme X_reverse(X).", "mirror")
        for key, pred, msg in (
            ("hex_sequences", lambda s: re.match(r"^0x\S+$", s), "doit commencer par 0x et ne pas contenir d'espace"),
            ("fractal_coordinates", lambda s: s.startswith("[") and "::" in s, "format attendu [lat, lon]::LIEU::TYPE"),
        ):
            vals = sec.get(key)
            if isinstance(vals, list):
                for i, s in enumerate(vals):
                    if isinstance(s, str) and s.strip() and not pred(s.strip()):
                        self.add(W, (S5, key, i), f"« {s} » : {msg}.", "pattern")

    def s6(self) -> None:
        sec = self.container((S6,), dict)
        if sec is None:
            return
        rbn = self.container((S6, "runes_by_name"), dict)
        fut = get_path(self.d, (S_RUNES, "futhark_elder"), [])
        by_name = {r.get("name"): r.get("char") for r in fut if isinstance(r, dict)} if isinstance(fut, list) else {}
        if rbn is not None:
            for name, rec in rbn.items():
                p = (S6, "runes_by_name", name)
                if not isinstance(rec, dict):
                    self.add(E, p, "Chaque cible doit être un objet.", "type")
                    continue
                self.record(p, rec, RUNE_TARGET_FIELDS)
                if name not in by_name:
                    self.add(W, p, f"« {name} » n'existe pas dans le Futhark ancien.", "ref")
                elif isinstance(rec.get("char"), str) and rec["char"] != by_name[name]:
                    self.add(E, p + ("char",),
                             f"La rune de « {name} » devrait être {by_name[name]} (trouvé : {rec['char']}).", "mismatch")
            for name in by_name:
                if name not in rbn:
                    self.add(W, (S6, "runes_by_name"), f"Aucune cible pour la rune « {name} ».", "missing")
        arch = self.container((S6, "archetypes_specific"), dict)
        if arch is not None:
            for k, v in arch.items():
                self.str_list((S6, "archetypes_specific", k), v)
                if k not in self.archetypes:
                    self.add(W, (S6, "archetypes_specific", k), f"L'archétype « {k} » n'existe pas dans S3.", "ref")
            for a in self.archetypes:
                if a not in arch:
                    self.add(W, (S6, "archetypes_specific"), f"Aucune action pour l'archétype « {a} ».", "missing")
        loc = self.container((S6, "locations_specific"), dict)
        if loc is not None:
            for k, v in loc.items():
                self.str_list((S6, "locations_specific", k), v)
                if k not in self.locations:
                    self.add(W, (S6, "locations_specific", k),
                             f"Le lieu « {k} » n'est pas déclaré dans S2 › locations.", "ref")

    def s7_pairs(self) -> None:
        pairs = get_path(self.d, (S7, "yin_yang_pairs"))
        if pairs is None:
            return
        if not isinstance(pairs, list):
            return self.add(E, (S7, "yin_yang_pairs"), "Doit être une liste de paires.", "type")
        for i, pr in enumerate(pairs):
            p = (S7, "yin_yang_pairs", i)
            if not (isinstance(pr, list) and len(pr) == 2 and all(isinstance(x, str) and x.strip() for x in pr)):
                self.add(E, p, "Une paire contient exactement deux textes non vides.", "pair")

    def records_rituals(self) -> None:
        sec = self.container((S8,), dict)
        if sec is None:
            return
        if "description" in sec and not isinstance(sec["description"], str):
            self.add(E, (S8, "description"), "Doit être un texte.", "type")
        for k, rec in sec.items():
            if k == "description":
                continue
            p = (S8, k)
            if not isinstance(rec, dict):
                self.add(E, p, "Un rituel doit être un objet.", "type")
                continue
            self.record(p, rec, RITUAL_FIELDS)
            if not rec.get("incantations"):
                self.add(W, p + ("incantations",), "Aucune incantation.", "empty")

    def records_synergies(self) -> None:
        sec = self.container((S9,), dict)
        if sec is None:
            return
        sigs: dict[str, str] = {}
        used = {r.get("synergie_trigger") for r in (get_path(self.d, (S8,), {}) or {}).values()
                if isinstance(r, dict)} if isinstance(get_path(self.d, (S8,)), dict) else set()
        for k, rec in sec.items():
            if k == "description":
                continue
            p = (S9, k)
            if not isinstance(rec, dict):
                self.add(E, p, "Une synergie doit être un objet.", "type")
                continue
            self.record(p, rec, SYNERGY_FIELDS)
            s = rec.get("hex_signature")
            if isinstance(s, str) and s:
                if s in sigs:
                    self.add(W, p + ("hex_signature",), f"Signature déjà utilisée par « {sigs[s]} ».", "duplicate")
                sigs.setdefault(s, k)
            if used and k not in used:
                self.add(I, p, "Aucun rituel ne déclenche cette synergie.", "unused")

    def records_eras(self) -> None:
        sec = self.container((S10,), dict)
        if sec is None:
            return
        for k, rec in sec.items():
            p = (S10, k)
            if not isinstance(rec, dict):
                self.add(E, p, "Une époque doit être un objet.", "type")
                continue
            self.record(p, rec, ERA_FIELDS)
        if not sec:
            self.add(W, (S10,), "Aucune époque déclarée.", "empty")

    def profiles(self) -> None:
        sec = self.container((S_PROFILES,), dict)
        if sec is None:
            return
        for k, rec in sec.items():
            p = (S_PROFILES, k)
            if not isinstance(rec, dict):
                self.add(E, p, "Un profil doit être un objet.", "type")
                continue
            self.record(p, rec, PROFILE_FIELDS)
        if not sec:
            self.add(W, (S_PROFILES,), "Aucun profil déclaré.", "empty")

    def engines(self) -> None:
        sec = self.container((S_ENGINES,), dict)
        if sec is None:
            return
        target = get_path(self.d, (S_META, "target_engine"), "")
        for name, rec in sec.items():
            p = (S_ENGINES, name)
            if not isinstance(rec, dict):
                self.add(E, p, "Un moteur doit être un objet.", "type")
                continue
            if "suffix" not in rec:
                self.add(E, p + ("suffix",), "Champ obligatoire « suffix » absent.", "missing")
            suffix = rec.get("suffix", "")
            if not isinstance(suffix, str):
                self.add(E, p + ("suffix",), "« suffix » doit être un texte.", "type")
                suffix = ""
            if "note" in rec and not isinstance(rec["note"], str):
                self.add(E, p + ("note",), "« note » doit être un texte.", "type")
            ranges = {k: v for k, v in rec.items() if k not in ("suffix", "note")}
            for k, v in ranges.items():
                if not (isinstance(v, list) and len(v) == 2 and all(_is_num(x) for x in v)):
                    self.add(E, p + (k,), "Une plage est une liste [min, max] de deux nombres.", "range")
                elif v[0] > v[1]:
                    self.add(E, p + (k,), f"Plage inversée : {v[0]} > {v[1]}.", "range")
            used = set(PLACEHOLDER_RE.findall(suffix))
            for ph in sorted(used):
                if ph not in ranges and ph not in RUNTIME_PLACEHOLDERS:
                    self.add(E, p + ("suffix",), f"Le paramètre {{{ph}}} n'a pas de plage [min, max].", "placeholder")
            for k in ranges:
                if k not in used:
                    self.add(W, p + (k,), f"La plage « {k} » n'est pas utilisée dans le suffixe.", "unused")
            if isinstance(target, str) and target and name not in target:
                self.add(I, p, f"« {name} » n'est pas cité dans META_DATA › target_engine.", "meta")


def validate(data: Any) -> list[Issue]:
    return _Validator(data).run()


# ════════════════════════════════════════════════════════════════════════════
#  Références (renommage en cascade)
# ════════════════════════════════════════════════════════════════════════════
def find_references(data: dict, container: KeyPath, key: str) -> list[tuple[KeyPath, str]]:
    """Chemins qui pointent vers `key`. Renvoie (chemin, "value" | "key")."""
    refs: list[tuple[KeyPath, str]] = []
    rituals = get_path(data, (S8,), {})
    rituals = rituals if isinstance(rituals, dict) else {}
    if container == (S9,):
        for k, r in rituals.items():
            if isinstance(r, dict) and r.get("synergie_trigger") == key:
                refs.append(((S8, k, "synergie_trigger"), "value"))
    elif container == (S10,):
        for k, r in rituals.items():
            if isinstance(r, dict) and r.get("era") == key:
                refs.append(((S8, k, "era"), "value"))
    elif container == (S3,):
        for k, r in rituals.items():
            if isinstance(r, dict) and r.get("archetype") == key:
                refs.append(((S8, k, "archetype"), "value"))
        syn = get_path(data, (S9,), {})
        for k, r in (syn.items() if isinstance(syn, dict) else []):
            if isinstance(r, dict) and get_path(r, ("trigger", "archetype")) == key:
                refs.append(((S9, k, "trigger", "archetype"), "value"))
        if key in (get_path(data, (S6, "archetypes_specific"), {}) or {}):
            refs.append(((S6, "archetypes_specific", key), "key"))
    return refs


# ════════════════════════════════════════════════════════════════════════════
#  Gabarits : documents complets
# ════════════════════════════════════════════════════════════════════════════
ENGINE_DEFAULTS: dict[str, dict] = {
    "midjourney": {"suffix": "--weird {weird} --style raw --chaos {chaos}", "weird": [0, 3000],
                   "chaos": [0, 100], "note": "plafonds documentés respectés"},
    "stable_diffusion": {"suffix": "--cfg {cfg} --steps {steps} --seed {seed}", "cfg": [1, 30],
                         "steps": [20, 80], "note": "seed réutilise la graine du forge"},
    "flux": {"suffix": "--guidance {cfg} --steps {steps}", "cfg": [1, 10], "steps": [10, 50],
             "note": "guidance = cfg flux"},
    "dalle": {"suffix": "", "note": "pas de paramètres suffixe (API prompt-only)"},
    "grok": {"suffix": "--weird {weird} --chaos {chaos}", "weird": [0, 5000], "chaos": [0, 100],
             "note": "Grok accepte des weird plus élevés"},
    "none": {"suffix": ""},
}


def skeleton() -> dict:
    """Squelette vierge conforme au schéma v3.1 (Futhark pré-rempli : caractères et noms)."""
    d: dict[str, Any] = {}
    d[S_META] = {
        "version": "1.0", "codex": "Nouveau_Codex", "classification": "CHIMERA_FRACTUROSCRIPT",
        "target_engine": "Multi (midjourney/stable_diffusion/flux/dalle/grok/none)",
        "theory": "MTT_Memetic_Temporal_Theory", "warning": "USE_WITH_CAUTION",
        "changelog": "v1.0 : création depuis le gabarit vierge",
    }
    d[S_RUNES] = {
        "futhark_elder": [{"char": c, "name": n, "meaning": "", "element": "", "archetype": ""}
                          for c, n in ELDER_FUTHARK],
        "bindrunes_custom": {},
    }
    for key in (S1, S2, S3, S4, S5, S7):
        d[key] = {k: [] for k in STRATA_LISTS[key]}
    d[S6] = {
        "runes_by_name": {n: {"char": c, "actions": []} for c, n in ELDER_FUTHARK},
        "archetypes_specific": {a: [] for a in STRATA_LISTS[S3]},
        "locations_specific": {},
    }
    d[S8] = {"description": ""}
    d[S9] = {"description": ""}
    d[S10] = {}
    d[S_PROFILES] = {"balanced": {a: 1.0 for a in PROFILE_AXES}}
    d[S_ENGINES] = copy.deepcopy(ENGINE_DEFAULTS)
    return d


def bump_version(v: str) -> str:
    parts = v.split(".") if isinstance(v, str) and VERSION_RE.match(v) else ["1", "0"]
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def derive_new_version(data: dict) -> dict:
    """Copie du document avec version incrémentée et ligne de changelog à compléter."""
    d = copy.deepcopy(data)
    meta = d.setdefault(S_META, {})
    new = bump_version(meta.get("version", "1.0"))
    old_log = meta.get("changelog", "")
    meta["version"] = new
    meta["changelog"] = f"v{new} : (à compléter)" + (f" | {old_log}" if old_log else "")
    return d


def clear_contents(data: dict) -> dict:
    """Copie qui garde la structure et le Futhark, mais vide les contenus."""
    d = copy.deepcopy(data)

    def wipe(o: Any) -> Any:
        if isinstance(o, list):
            return []
        if isinstance(o, dict):
            return {k: wipe(v) for k, v in o.items()}
        return o

    for key in (S1, S2, S4, S5, S7):
        if isinstance(d.get(key), dict):
            d[key] = {k: [] for k in d[key]}
    if isinstance(d.get(S3), dict):
        d[S3] = {k: [] for k in d[S3]}
    s6 = d.get(S6)
    if isinstance(s6, dict):
        for k, rec in (s6.get("runes_by_name") or {}).items():
            if isinstance(rec, dict):
                rec["actions"] = []
        s6["archetypes_specific"] = {k: [] for k in (s6.get("archetypes_specific") or {})}
        s6["locations_specific"] = {}
    for key in (S8, S9):
        d[key] = {"description": (d.get(key) or {}).get("description", "")} if isinstance(d.get(key), dict) else {}
    d[S10] = {}
    if isinstance(d.get(S_RUNES), dict):
        d[S_RUNES]["bindrunes_custom"] = {}
    meta = d.setdefault(S_META, {})
    meta["version"] = "1.0"
    meta["changelog"] = "v1.0 : création depuis une structure existante"
    return d


DOCUMENT_TEMPLATES = (
    ("skeleton", "Squelette vierge",
     "Toutes les sections du schéma v3.1, Futhark pré-rempli (caractères et noms), profils et moteurs de base."),
    ("derive", "Nouvelle version du document ouvert",
     "Copie complète avec numéro de version incrémenté et ligne de changelog à compléter."),
    ("clear", "Structure du document ouvert, sans contenu",
     "Garde les sections, le Futhark, les profils et les moteurs ; vide listes, rituels, synergies et époques."),
)


def build_document_template(tid: str, current: dict | None) -> dict:
    if tid == "skeleton" or current is None:
        return skeleton()
    if tid == "derive":
        return derive_new_version(current)
    if tid == "clear":
        return clear_contents(current)
    raise KeyError(tid)


# ════════════════════════════════════════════════════════════════════════════
#  Gabarits : entrées individuelles
# ════════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class EntryTemplate:
    id: str
    label: str
    hint: str
    build: Callable[[dict], tuple[str, Any]]   # data -> (clé suggérée, valeur)


def _first(data: dict, ref: str) -> str:
    ch = choices_for(ref, data)
    return ch[0][0] if ch else ""


def _ritual(arch: str | None, glitch: float, era: str | None = None) -> Callable[[dict], tuple[str, Any]]:
    def build(data: dict) -> tuple[str, Any]:
        archs = [c for c, _ in choices_for("archetypes", data)]
        rec = {
            "base": "", "runes": [_first(data, "rune_chars")] if _first(data, "rune_chars") else [],
            "archetype": arch if arch in archs else (archs[0] if archs else ""),
            "incantations": [], "glitch_level": glitch,
            "synergie_trigger": _first(data, "synergies"),
        }
        if era and era in [c for c, _ in choices_for("eras", data)]:
            rec["era"] = era
        return "nouveau_rituel", rec
    return build


def _profile(value: float | None, copy_of: str | None = None) -> Callable[[dict], tuple[str, Any]]:
    def build(data: dict) -> tuple[str, Any]:
        if copy_of:
            src = get_path(data, (S_PROFILES, copy_of))
            if isinstance(src, dict):
                return f"{copy_of}_copie", copy.deepcopy(src)
        return "nouveau_profil", {a: float(value if value is not None else 1.0) for a in PROFILE_AXES}
    return build


def _engine(kind: str) -> Callable[[dict], tuple[str, Any]]:
    def build(data: dict) -> tuple[str, Any]:
        if kind == "mj":
            return "nouveau_moteur", copy.deepcopy(ENGINE_DEFAULTS["midjourney"])
        if kind == "sd":
            return "nouveau_moteur", copy.deepcopy(ENGINE_DEFAULTS["stable_diffusion"])
        return "nouveau_moteur", {"suffix": "", "note": ""}
    return build


def _blank(rs_id: str, base_key: str) -> Callable[[dict], tuple[str, Any]]:
    def build(data: dict) -> tuple[str, Any]:
        rs = RECORDSETS[rs_id]
        rec = blank_record(rs.fields, data)
        if rs_id == "synergies":
            rec["hex_signature"] = "0xNEW_1"
        return base_key, rec
    return build


def _bind_full(data: dict) -> tuple[str, Any]:
    chars = "".join(c for c, _ in choices_for("rune_chars", data))
    return "SIGIL", {"chars": chars, "meaning": ""}


def _rune_target(data: dict) -> tuple[str, Any]:
    have = set(_dict_keys(data, (S6, "runes_by_name")))
    for c, n in choices_for("rune_chars", data):
        name = n.split("  ", 1)[-1]
        if name not in have:
            return name, {"char": c, "actions": []}
    return "Nouvelle_rune", {"char": "", "actions": []}


ENTRY_TEMPLATES: dict[str, tuple[EntryTemplate, ...]] = {
    "futhark": (EntryTemplate("blank", "Rune vierge", "Caractère, nom et sens à renseigner.",
                              lambda d: ("", {"char": "", "name": "", "meaning": "", "element": "", "archetype": ""})),),
    "bindrunes": (
        EntryTemplate("blank", "Bindrune vierge", "Nom et suite de runes à renseigner.",
                      _blank("bindrunes", "NOUVELLE")),
        EntryTemplate("sigil", "Sceau complet", "Les 24 runes du Futhark dans l'ordre (comme VAUV).", _bind_full),
    ),
    "rune_targets": (EntryTemplate("next", "Prochaine rune sans cible",
                                   "Pré-remplit avec la première rune du Futhark qui n'a pas encore de cible.",
                                   _rune_target),),
    "rituals": (
        EntryTemplate("blank", "Rituel vierge", "Tous les champs obligatoires, valeurs neutres.", _ritual(None, 0.5)),
        EntryTemplate("shadow", "Révélation d'ombre", "Archétype shadow, glitch 0.85.", _ritual("shadow", 0.85)),
        EntryTemplate("trickster", "Porte du chaos", "Archétype trickster, glitch 0.95.", _ritual("trickster", 0.95)),
        EntryTemplate("fractal", "Pli temporel hors-temps", "Archétype wise_old, époque FRACTAL, glitch 0.9.",
                      _ritual("wise_old", 0.9, "FRACTAL")),
    ),
    "synergies": (EntryTemplate("blank", "Synergie vierge",
                                "Déclencheur rune + archétype + lieu, effet et signature.",
                                _blank("synergies", "nouvelle_synergie")),),
    "eras": (EntryTemplate("blank", "Époque vierge", "Description, trois listes et esthétique.",
                           _blank("eras", "2100")),),
    "profiles": (
        EntryTemplate("neutral", "Neutre (tout à 1.0)", "Toutes les strates à poids 1.0.", _profile(1.0)),
        EntryTemplate("silent", "Silence (tout à 0.0)", "Toutes les strates désactivées.", _profile(0.0)),
        EntryTemplate("max", "Maximum (tout à 2.0)", "Toutes les strates au plafond.", _profile(2.0)),
        EntryTemplate("copy_balanced", "Copie de « balanced »", "Part du profil équilibré existant.",
                      _profile(None, "balanced")),
    ),
    "engines": (
        EntryTemplate("prompt", "Prompt seul", "Aucun paramètre de suffixe.", _engine("none")),
        EntryTemplate("mj", "Style Midjourney", "Paramètres weird et chaos.", _engine("mj")),
        EntryTemplate("sd", "Style Stable Diffusion", "Paramètres cfg, steps et seed.", _engine("sd")),
    ),
}


# ════════════════════════════════════════════════════════════════════════════
#  Lecture / écriture
# ════════════════════════════════════════════════════════════════════════════
class LexiconError(Exception):
    """Erreur de lecture ou d'écriture, avec un message lisible."""


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict:
    out: dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"Clé en double « {k} » : le JSON l'accepte mais la première valeur serait perdue.")
        out[k] = v
    return out


def loads(text: str) -> dict:
    try:
        data = json.loads(text, object_pairs_hook=_no_duplicates)
    except json.JSONDecodeError as e:
        raise LexiconError(f"JSON invalide, ligne {e.lineno}, colonne {e.colno} : {e.msg}") from e
    except ValueError as e:
        raise LexiconError(str(e)) from e
    if not isinstance(data, dict):
        raise LexiconError("La racine du fichier doit être un objet JSON.")
    return data


def load_file(path: str | Path) -> dict:
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except OSError as e:
        raise LexiconError(f"Lecture impossible : {e.strerror or e}") from e
    except UnicodeDecodeError as e:
        raise LexiconError("Le fichier n'est pas encodé en UTF-8.") from e
    return loads(text)


_WIDTH = 125        # largeur max d'une ligne « en ligne » (objet ou liste compacts)
_PACK_WIDTH = 81    # largeur de remplissage des longues listes de mots courts


def _scalar(x: Any) -> bool:
    return not isinstance(x, (dict, list))


def _inline(v: Any) -> str:
    if isinstance(v, dict):
        return "{" + ", ".join(f"{json.dumps(k, ensure_ascii=False)}: {_inline(x)}" for k, x in v.items()) + "}"
    if isinstance(v, list):
        return "[" + ", ".join(_inline(x) for x in v) + "]"
    return json.dumps(v, ensure_ascii=False)


def _flat(v: Any) -> bool:
    if isinstance(v, dict):
        return all(_scalar(x) or (isinstance(x, list) and all(_scalar(y) for y in x)) for x in v.values())
    if isinstance(v, list):
        return all(_scalar(x) for x in v)
    return True


def _pack(items: list[str], indent: str) -> str:
    lines, cur = [], indent
    for n, it in enumerate(items):
        piece = it + ("," if n < len(items) - 1 else "")
        if cur.strip() and len(cur) + 1 + len(piece) > _PACK_WIDTH:
            lines.append(cur)
            cur = indent + piece
        else:
            cur = (cur + " " + piece) if cur.strip() else (indent + piece)
    lines.append(cur)
    return "\n".join(lines)


def _fmt(v: Any, level: int, lead: int) -> str:
    pad = "  " * level
    inner = "  " * (level + 1)
    if isinstance(v, dict):
        if not v:
            return "{}"
        if level >= 2 and _flat(v):
            s = _inline(v)
            if lead + len(s) <= _WIDTH:
                return s
        parts = []
        for k, x in v.items():
            key = json.dumps(k, ensure_ascii=False)
            parts.append(f"{inner}{key}: " + _fmt(x, level + 1, len(inner) + len(key) + 2))
        return "{\n" + ",\n".join(parts) + f"\n{pad}}}"
    if isinstance(v, list):
        if not v:
            return "[]"
        if all(_scalar(x) for x in v):
            s = _inline(v)
            if lead + len(s) <= _WIDTH:
                return s
            items = [_inline(x) for x in v]
            if all(isinstance(x, str) for x in v) and sum(len(i) for i in items) / len(items) <= 32:
                return "[\n" + _pack(items, inner) + f"\n{pad}]"
            return "[\n" + ",\n".join(inner + i for i in items) + f"\n{pad}]"
        if all(isinstance(x, (dict, list)) and _flat(x) and len(_inline(x)) + len(inner) <= _WIDTH for x in v):
            return "[\n" + ",\n".join(inner + _inline(x) for x in v) + f"\n{pad}]"
        return "[\n" + ",\n".join(inner + _fmt(x, level + 1, len(inner)) for x in v) + f"\n{pad}]"
    return json.dumps(v, ensure_ascii=False)


def dumps(data: dict) -> str:
    """JSON lisible, proche de la mise en forme manuelle d'origine (sections séparées par une ligne vide)."""
    if not isinstance(data, dict):
        return json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if not data:
        return "{}\n"
    blocks = []
    for k, v in data.items():
        key = json.dumps(k, ensure_ascii=False)
        blocks.append(f"  {key}: " + _fmt(v, 1, 2 + len(key) + 2))
    return "{\n" + ",\n\n".join(blocks) + "\n}\n"


def save_file(path: str | Path, data: dict, backup: bool = True) -> None:
    """Écriture atomique (fichier temporaire puis remplacement) + copie .bak optionnelle."""
    path = Path(path)
    text = dumps(data)
    try:
        loads(text)  # garde-fou : ce qu'on écrit doit se relire
        path.parent.mkdir(parents=True, exist_ok=True)
        if backup and path.exists():
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
    except OSError as e:
        raise LexiconError(f"Écriture impossible : {e.strerror or e}") from e


# ════════════════════════════════════════════════════════════════════════════
#  Document : données + historique + notifications
# ════════════════════════════════════════════════════════════════════════════
class Document:
    def __init__(self, data: dict | None = None, path: str | Path | None = None):
        self.data: dict = data if data is not None else skeleton()
        self.path: Path | None = Path(path) if path else None
        self._undo: list[tuple[str, dict, int]] = []
        self._redo: list[tuple[str, dict, int]] = []
        self._counter = 0
        self.version = 0
        self.saved_version = 0
        self._listeners: list[Callable[[Any], None]] = []
        self._batch = 0
        self._batch_pushed = False
        self._batch_dirty = False
        self._last_coalesce: tuple[Any, float] = (None, 0.0)
        if data is not None and path is None:
            self.saved_version = -1   # document issu d'un gabarit : jamais enregistré

    # -- E/S -------------------------------------------------------------------
    @classmethod
    def open(cls, path: str | Path) -> "Document":
        return cls(load_file(path), path)

    def save(self, path: str | Path | None = None, backup: bool = True) -> None:
        target = Path(path) if path else self.path
        if target is None:
            raise LexiconError("Aucun chemin de fichier défini.")
        save_file(target, self.data, backup=backup)
        self.path = target
        self.saved_version = self.version
        self._emit("save")

    @property
    def dirty(self) -> bool:
        return self.version != self.saved_version

    @property
    def name(self) -> str:
        return self.path.name if self.path else "sans titre.json"

    # -- notifications ---------------------------------------------------------
    def subscribe(self, fn: Callable[[Any], None]) -> None:
        self._listeners.append(fn)

    def _emit(self, origin: Any = None) -> None:
        for fn in list(self._listeners):
            fn(origin)

    # -- historique ------------------------------------------------------------
    @property
    def undo_label(self) -> str | None:
        return self._undo[-1][0] if self._undo else None

    @property
    def redo_label(self) -> str | None:
        return self._redo[-1][0] if self._redo else None

    def _push(self, label: str, coalesce: Any) -> None:
        now = time.monotonic()
        if self._batch > 0:
            if self._batch_pushed:
                return
            self._batch_pushed = True
        elif coalesce is not None and coalesce == self._last_coalesce[0] \
                and now - self._last_coalesce[1] < 1.5 and self._undo:
            self._last_coalesce = (coalesce, now)
            return
        self._undo.append((label, copy.deepcopy(self.data), self.version))
        if len(self._undo) > 300:
            del self._undo[0]
        self._redo.clear()
        self._last_coalesce = (coalesce, now) if coalesce is not None and self._batch == 0 else (None, 0.0)

    def _changed(self, origin: Any) -> None:
        self._counter += 1
        self.version = self._counter
        if self._batch:
            self._batch_dirty = True
        else:
            self._emit(origin)

    @contextmanager
    def batch(self, label: str, origin: Any = None):
        if self._batch == 0:
            self._batch_pushed = False
            self._batch_dirty = False
            self._batch_label = label
        self._batch += 1
        try:
            yield
        finally:
            self._batch -= 1
            if self._batch == 0 and self._batch_dirty:
                self._batch_dirty = False
                self._emit(origin)

    def undo(self) -> bool:
        if not self._undo:
            return False
        label, snap, ver = self._undo.pop()
        self._redo.append((label, copy.deepcopy(self.data), self.version))
        self.data, self.version = snap, ver
        self._last_coalesce = (None, 0.0)
        self._emit(None)
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        label, snap, ver = self._redo.pop()
        self._undo.append((label, copy.deepcopy(self.data), self.version))
        self.data, self.version = snap, ver
        self._last_coalesce = (None, 0.0)
        self._emit(None)
        return True

    # -- accès -----------------------------------------------------------------
    def get(self, path: KeyPath, default: Any = None) -> Any:
        return get_path(self.data, path, default)

    def _parent(self, path: KeyPath) -> Any:
        parent = get_path(self.data, path[:-1], _MISSING)
        if parent is _MISSING or not isinstance(parent, (dict, list)):
            raise KeyError(f"Chemin introuvable : {format_path(path[:-1])}")
        return parent

    # -- mutations -------------------------------------------------------------
    def set(self, path: KeyPath, value: Any, label: str = "Modification",
            coalesce: Any = None, origin: Any = None) -> bool:
        path = tuple(path)
        parent = self._parent(path)
        key = path[-1]
        exists = (key in parent) if isinstance(parent, dict) else (isinstance(key, int) and -len(parent) <= key < len(parent))
        if exists and type(parent[key]) is type(value) and parent[key] == value:
            return False
        self._push(label, coalesce)
        parent[key] = copy.deepcopy(value)
        self._changed(origin)
        return True

    def insert(self, path: KeyPath, index: int | None, value: Any, label: str = "Ajout", origin: Any = None) -> int:
        lst = self.get(path)
        if not isinstance(lst, list):
            raise KeyError(f"Liste introuvable : {format_path(path)}")
        index = len(lst) if index is None else max(0, min(index, len(lst)))
        self._push(label, None)
        lst.insert(index, copy.deepcopy(value))
        self._changed(origin)
        return index

    def add_key(self, path: KeyPath, key: str, value: Any, index: int | None = None,
                label: str = "Ajout", origin: Any = None) -> None:
        d = self.get(path)
        if not isinstance(d, dict):
            raise KeyError(f"Objet introuvable : {format_path(path)}")
        if key in d:
            raise KeyError(f"La clé « {key} » existe déjà.")
        self._push(label, None)
        items = list(d.items())
        items.insert(len(items) if index is None else index, (key, copy.deepcopy(value)))
        d.clear()
        d.update(items)
        self._changed(origin)

    def remove(self, path: KeyPath, label: str = "Suppression", origin: Any = None) -> None:
        path = tuple(path)
        parent = self._parent(path)
        self._push(label, None)
        del parent[path[-1]]
        self._changed(origin)

    def rename_key(self, path: KeyPath, old: str, new: str, cascade: bool = True,
                   label: str = "Renommage", origin: Any = None) -> int:
        """Renomme une clé en conservant l'ordre ; met à jour les références. Renvoie leur nombre."""
        d = self.get(path)
        if not isinstance(d, dict) or old not in d:
            raise KeyError(f"Clé introuvable : {old}")
        if new == old:
            return 0
        if new in d:
            raise KeyError(f"La clé « {new} » existe déjà.")
        refs = find_references(self.data, tuple(path), old) if cascade else []
        with self.batch(label, origin):
            self._push(label, None)
            items = [(new if k == old else k, v) for k, v in d.items()]
            d.clear()
            d.update(items)
            for rpath, kind in refs:
                if kind == "value":
                    parent = get_path(self.data, rpath[:-1])
                    parent[rpath[-1]] = new
                else:
                    rd = get_path(self.data, rpath[:-1])
                    ritems = [(new if k == old else k, v) for k, v in rd.items()]
                    rd.clear()
                    rd.update(ritems)
            self._changed(origin)
        return len(refs)

    def move(self, path: KeyPath, key: Any, delta: int, label: str = "Déplacement", origin: Any = None) -> bool:
        """Déplace un élément de liste (index) ou une clé d'objet de `delta` positions."""
        c = self.get(path)
        if isinstance(c, list):
            i, j = key, key + delta
            if not (0 <= i < len(c) and 0 <= j < len(c)):
                return False
            self._push(label, None)
            c.insert(j, c.pop(i))
        elif isinstance(c, dict):
            keys = list(c)
            i = keys.index(key)
            j = i + delta
            if not (0 <= j < len(keys)):
                return False
            self._push(label, None)
            keys.insert(j, keys.pop(i))
            items = [(k, c[k]) for k in keys]
            c.clear()
            c.update(items)
        else:
            return False
        self._changed(origin)
        return True

    def replace_all(self, data: dict, label: str = "Remplacement du document", origin: Any = None) -> None:
        self._push(label, None)
        self.data = copy.deepcopy(data)
        self._changed(origin)

    def validate(self) -> list[Issue]:
        return validate(self.data)


_MISSING = object()


# ════════════════════════════════════════════════════════════════════════════
#  Ligne de commande
# ════════════════════════════════════════════════════════════════════════════
def _cli(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Valide un lexique Vauvillensis (.json).")
    ap.add_argument("file", help="fichier JSON à valider")
    ap.add_argument("--format", action="store_true", help="réécrit le fichier avec la mise en forme standard")
    ap.add_argument("--quiet", action="store_true", help="n'affiche que le résumé")
    args = ap.parse_args(argv)
    try:
        doc = Document.open(args.file)
    except LexiconError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    issues = doc.validate()
    if not args.quiet:
        for i in issues:
            print(f"[{SEVERITY_LABEL[i.severity]:<13}] {i.path_str or '(racine)'} : {i.message}")
    e, w, i_ = IssueIndex(issues).total()
    print(f"\n{e} erreur(s), {w} avertissement(s), {i_} info(s) — {args.file}")
    if args.format:
        save_file(args.file, doc.data, backup=True)
        print("Fichier réécrit (copie .bak conservée).")
    return 1 if e else 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
