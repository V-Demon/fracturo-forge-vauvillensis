#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vauv_preview — Onglet "Forge Live" : teste le lexique en temps réel.

Génère un prompt glitché à partir du document en cours d'édition,
sans dépendance à fracturo_prompt_forge_v3.py. Ainsi le preview
reflète toujours exactement ce qui est édité.
"""
from __future__ import annotations

import random
import re
from typing import Any, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import vauv_core as core
from vauv_theme import C, HudFrame, font, qc
from vauv_widgets import Env


# ═══════════════════════════════════════════════════════════════
# Moteur de génération minimal (autonome, sans la forge)
# ═══════════════════════════════════════════════════════════════

def _runes_chars(data: dict) -> List[str]:
    fut = data.get(core.S_RUNES, {}).get("futhark_elder", [])
    return [r["char"] for r in fut if isinstance(r, dict) and isinstance(r.get("char"), str)]


def _runes_by_name(data: dict) -> dict:
    return data.get(core.S6, {}).get("runes_by_name", {})


def _archetypes(data: dict) -> List[str]:
    s3 = data.get(core.S3, {})
    return [k for k in s3 if isinstance(s3[k], list)]


def _locations(data: dict) -> List[str]:
    return [x for x in data.get(core.S2, {}).get("locations", []) if isinstance(x, str)]


def _bindrunes(data: dict) -> dict:
    return data.get(core.S_RUNES, {}).get("bindrunes_custom", {})


def _pick(rng: random.Random, lst: list, n: int = 1) -> list:
    n = min(n, len(lst))
    return rng.sample(lst, n) if n > 0 else []


def _bruit_casse(texte: str, rng: random.Random, p: float = 0.4) -> str:
    return "".join(c.upper() if c.isalpha() and rng.random() < p else c for c in texte)


def generer_prompt_preview(
    base: str,
    data: dict,
    *,
    niveau: float,
    weaponised: bool,
    rune_char: Optional[str] = None,
    archetype: Optional[str] = None,
    location: Optional[str] = None,
    engine: str = "none",
    seed: Optional[int] = None,
) -> str:
    """Génère un prompt glitché à partir des données brutes du lexique."""
    rng = random.Random(seed)
    elements: List[str] = []

    # ── Ciblage (S6) ──
    if rune_char:
        by_name = _runes_by_name(data)
        name = None
        for n, rec in by_name.items():
            if isinstance(rec, dict) and rec.get("char") == rune_char:
                name = n
                break
        if name:
            elements.append(f"RUNE:{name.upper()}")
            actions = rec.get("actions", []) if isinstance(rec, dict) else []
            if actions:
                elements.append(f"ACTION:{rng.choice(actions).upper()}")
        elements.append(rune_char * rng.randint(3, 7))
        # Bindrunes associées
        for bname, brec in _bindrunes(data).items():
            if isinstance(brec, dict) and rune_char in brec.get("chars", "") and rng.random() < 0.5:
                elements.append(f"BINDRUNE:{bname}_{brec.get('meaning', '').upper()}")

    if archetype and archetype in _archetypes(data):
        terms = data[core.S3].get(archetype, [])
        if terms:
            elements.append(f"ARCHETYPE:{archetype.upper()}")
            elements.append(f"JUNGIAN_{rng.choice(terms).upper()}")

    if location:
        elements.append(f"LOCATION:{location}")
        loc_features = data.get(core.S6, {}).get("locations_specific", {}).get(location, [])
        for f in loc_features:
            if rng.random() < 0.6:
                elements.append(f"FEATURE:{f.upper()}")

    # ── Strates selon niveau ──
    p_bruit = 0.0
    if weaponised:
        # Toutes les strates, version condensée
        s1 = data.get(core.S1, {})
        s2 = data.get(core.S2, {})
        s4 = data.get(core.S4, {})
        s5 = data.get(core.S5, {})

        # S1 : jetons glitch
        brackets = s1.get("brackets", ["[", "]"])
        errors = s1.get("errors", ["NULL_POINTER"])
        for _ in range(rng.randint(2, 4)):
            b = rng.choice(brackets)
            e = rng.choice(errors)
            elements.append(f"{b}{e}")

        # S2 : protocoles + concepts
        for _ in range(rng.randint(1, 3)):
            protos = s1.get("protocols", [])
            if protos:
                elements.append(rng.choice(protos))
        for cat in ("locations", "entities", "states"):
            lst = s2.get(cat, [])
            if lst:
                elements.append(f"{cat.upper()}:{rng.choice(lst)}")

        # S4 : incantations
        inc_types = ("conditionals", "sql_injections", "bash_commands", "function_calls", "loop_structures", "python_code")
        for _ in range(rng.randint(3, 6)):
            t = rng.choice(inc_types)
            lst = s4.get(t, [])
            if lst:
                elements.append(rng.choice(lst))

        # S5 : FracturoScript
        for cat in ("hex_sequences", "stack_traces", "mirror_sequences", "degradation_strings", "repetition_patterns"):
            lst = s5.get(cat, [])
            if lst:
                elements.append(rng.choice(lst))
        if s5.get("buffer_overflows"):
            elements.append(rng.choice(s5["buffer_overflows"]))
        if s5.get("temporal_signatures"):
            elements.append(rng.choice(s5["temporal_signatures"]))
        if s5.get("fractal_coordinates"):
            elements.append(rng.choice(s5["fractal_coordinates"]))

        # S7 : métamorphose
        s7 = data.get(core.S7, {})
        for cat in ("self_reference", "spiral_patterns", "echo_chains", "temporal_loops"):
            lst = s7.get(cat, [])
            if lst:
                elements.append(rng.choice(lst))
        pairs = s7.get("yin_yang_pairs", [])
        if pairs:
            a, b = rng.choice(pairs)
            elements.append(f"YIN_YANG:{a}_{b}")

        p_bruit = 0.7
    else:
        # Mode par niveaux (paliers cumulatifs)
        palier = 0 if niveau < 0.3 else 1 if niveau < 0.6 else 2 if niveau < 0.9 else 3
        s1 = data.get(core.S1, {})
        s2 = data.get(core.S2, {})
        s3 = data.get(core.S3, {})
        s4 = data.get(core.S4, {})
        s5 = data.get(core.S5, {})
        s7 = data.get(core.S7, {})

        if palier >= 0:
            brackets = s1.get("brackets", ["[", "]"])
            errors = s1.get("errors", ["NULL_POINTER"])
            for _ in range(rng.randint(1, 3)):
                b = rng.choice(brackets)
                e = rng.choice(errors)
                elements.append(f"{b}{e}")

        if palier >= 1:
            chars = _runes_chars(data)
            if chars:
                elements.append("RUNE_SEQUENCE:" + "".join(rng.choices(chars, k=rng.randint(3, 6))))
            protos = s1.get("protocols", [])
            if protos:
                elements.append(rng.choice(protos))
            for cat in ("locations", "entities", "states"):
                lst = s2.get(cat, [])
                if lst:
                    elements.append(f"{cat.upper()}:{rng.choice(lst)}")

        if palier >= 2:
            archs = _archetypes(data)
            if archs:
                a = rng.choice(archs)
                terms = s3.get(a, [])
                if terms:
                    elements.append(f"ARCHETYPE:{a.upper()}")
                    elements.append(f"JUNGIAN_{rng.choice(terms).upper()}")
            inc_types = ("conditionals", "sql_injections", "bash_commands", "function_calls")
            for _ in range(rng.randint(1, 3)):
                t = rng.choice(inc_types)
                lst = s4.get(t, [])
                if lst:
                    elements.append(rng.choice(lst))

        if palier >= 3:
            for cat in ("hex_sequences", "stack_traces", "mirror_sequences", "degradation_strings"):
                lst = s5.get(cat, [])
                if lst:
                    elements.append(rng.choice(lst))
            if s5.get("buffer_overflows"):
                elements.append(rng.choice(s5["buffer_overflows"]))
            if s5.get("temporal_signatures"):
                elements.append(rng.choice(s5["temporal_signatures"]))
            # S7
            for cat in ("spiral_patterns", "echo_chains", "temporal_loops"):
                lst = s7.get(cat, [])
                if lst:
                    elements.append(rng.choice(lst))
            pairs = s7.get("yin_yang_pairs", [])
            if pairs:
                a, b = rng.choice(pairs)
                elements.append(f"YIN_YANG:{a}_{b}")

        p_bruit = max(0.0, niveau - 0.3)

    # ── Assemblage ──
    corps = ", ".join(elements)
    if rng.random() < p_bruit:
        corps = _bruit_casse(corps, rng)

    morceaux = [base, corps] if corps else [base]

    # Suffixe moteur
    if engine != "none":
        engines = data.get(core.S_ENGINES, {})
        spec = engines.get(engine)
        if isinstance(spec, dict):
            gabarit = spec.get("suffix", "")
            if gabarit.strip():
                valeurs: dict = {}
                if "{weird}" in gabarit:
                    plages = spec.get("weird", [0, 3000])
                    hi = plages[1] if isinstance(plages, list) and len(plages) == 2 else 3000
                    valeurs["weird"] = rng.randint(int(hi * 0.8), hi) if weaponised else int(niveau * hi)
                if "{chaos}" in gabarit:
                    plages = spec.get("chaos", [0, 100])
                    hi = plages[1] if isinstance(plages, list) and len(plages) == 2 else 100
                    valeurs["chaos"] = rng.randint(hi // 2, hi) if weaponised else int(niveau * hi)
                try:
                    morceaux.append(gabarit.format(**valeurs))
                except KeyError:
                    pass

    return ", ".join(m for m in morceaux if m)


# ═══════════════════════════════════════════════════════════════
# Page Preview
# ═══════════════════════════════════════════════════════════════

class PreviewPage(QWidget):
    """Onglet "Forge Live" : génère un prompt à partir du lexique édité."""

    def __init__(self, env: Env, parent: QWidget | None = None):
        super().__init__(parent)
        self.env = env
        self.setObjectName("page")

        # Attributs attendus par vauv_editor
        self.title = "Forge Live"
        self.code = "⚡"
        self.prefix = ()
        self.subtitle = "Test du lexique en temps réel"
        self.navigate = lambda path: None
        self.say = lambda msg: None
        self.stale = True

        # Layout principal
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 14)
        lay.setSpacing(14)

        # ── En-tête ──
        head = QHBoxLayout()
        title_lbl = QLabel("Forge Live")
        title_lbl.setFont(font("display", 20, True))
        title_lbl.setStyleSheet(f"color: {qc('cyan').name()};")
        head.addWidget(title_lbl)
        self.status = QLabel("En attente...")
        self.status.setProperty("role", "mono")
        head.addWidget(self.status, 0, Qt.AlignRight)
        lay.addLayout(head)

        # ── Splitter gauche/droite ──
        splitter = QSplitter(Qt.Horizontal)

        # Panneau de contrôle (gauche)
        ctrl = HudFrame(accent="rose", chamfer=12)
        cl = QVBoxLayout(ctrl)
        cl.setContentsMargins(16, 16, 16, 16)
        cl.setSpacing(12)

        # Prompt de base
        cl.addWidget(QLabel("Prompt de base :"))
        self.prompt_base = QLineEdit()
        self.prompt_base.setPlaceholderText("Portrait d'un RuneSmith")
        self.prompt_base.setFont(font("mono", 13))
        cl.addWidget(self.prompt_base)

        # Weaponised
        self.cb_weaponised = QCheckBox("Mode WEAPONISED (toutes strates)")
        cl.addWidget(self.cb_weaponised)

        # Slider niveau
        cl.addWidget(QLabel("Niveau de corruption :"))
        self.slider_level = QSlider(Qt.Horizontal)
        self.slider_level.setRange(0, 100)
        self.slider_level.setValue(70)
        cl.addWidget(self.slider_level)
        self.lbl_level = QLabel("0.70")
        self.lbl_level.setProperty("role", "mono")
        self.lbl_level.setAlignment(Qt.AlignRight)
        cl.addWidget(self.lbl_level)
        self.slider_level.valueChanged.connect(lambda v: self.lbl_level.setText(f"{v / 100:.2f}"))
        self.cb_weaponised.toggled.connect(lambda on: self.slider_level.setDisabled(on))

        # Sélecteurs
        cl.addWidget(QLabel("Rune ciblée :"))
        self.combo_rune = QComboBox()
        self.combo_rune.addItem("(aucune)", "")
        cl.addWidget(self.combo_rune)

        cl.addWidget(QLabel("Archétype :"))
        self.combo_arch = QComboBox()
        self.combo_arch.addItem("(aucun)", "")
        cl.addWidget(self.combo_arch)

        cl.addWidget(QLabel("Lieu :"))
        self.combo_loc = QComboBox()
        self.combo_loc.addItem("(aucun)", "")
        cl.addWidget(self.combo_loc)

        cl.addWidget(QLabel("Moteur :"))
        self.combo_engine = QComboBox()
        cl.addWidget(self.combo_engine)

        cl.addStretch(1)

        # Bouton générer
        self.btn_generate = QPushButton("⚡ GÉNÉRER LE PROMPT")
        self.btn_generate.setProperty("primary", True)
        self.btn_generate.setFont(font("ui", 14, True))
        self.btn_generate.clicked.connect(self._generate)
        cl.addWidget(self.btn_generate)

        splitter.addWidget(ctrl)

        # Panneau de sortie (droite)
        out = HudFrame(accent="cyan", chamfer=12)
        ol = QVBoxLayout(out)
        ol.setContentsMargins(16, 16, 16, 16)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(font("mono", 12))
        self.output.setStyleSheet(
            f"background: {C['bg0']}; color: {C['text']}; "
            f"border: 1px solid {C['line']}; padding: 8px;"
        )
        ol.addWidget(self.output, 1)

        btn_copy = QPushButton("📋 Copier dans le presse-papiers")
        btn_copy.clicked.connect(lambda: self.output.selectAll() and self.output.copy())
        ol.addWidget(btn_copy)

        splitter.addWidget(out)
        splitter.setSizes([380, 720])
        lay.addWidget(splitter, 1)

    # ── Rechargement des sélecteurs depuis le doc ──
    def reload(self) -> None:
        self.stale = False
        data = self.env.doc.data

        # Runes
        self.combo_rune.clear()
        self.combo_rune.addItem("(aucune)", "")
        for r in data.get(core.S_RUNES, {}).get("futhark_elder", []):
            if isinstance(r, dict):
                ch = r.get("char", "")
                nm = r.get("name", "")
                self.combo_rune.addItem(f"{ch}  {nm}", ch)

        # Archétypes
        self.combo_arch.clear()
        self.combo_arch.addItem("(aucun)", "")
        for a in _archetypes(data):
            self.combo_arch.addItem(a, a)

        # Lieux
        self.combo_loc.clear()
        self.combo_loc.addItem("(aucun)", "")
        for loc in _locations(data):
            self.combo_loc.addItem(loc, loc)

        # Moteurs
        self.combo_engine.clear()
        engines = data.get(core.S_ENGINES, {})
        for name in engines:
            self.combo_engine.addItem(name, name)
        if "none" not in engines:
            self.combo_engine.addItem("none", "none")

    def showEvent(self, e) -> None:
        if self.stale:
            self.reload()
        super().showEvent(e)

    def focus_path(self, path: tuple) -> None:
        pass

    def apply_issues(self, idx) -> None:
        pass

    def summary(self) -> str:
        return "Forge Live"

    # ── Génération ──
    def _generate(self) -> None:
        base = self.prompt_base.text().strip() or "void"
        niveau = self.slider_level.value() / 100.0
        weaponised = self.cb_weaponised.isChecked()
        rune_char = self.combo_rune.currentData() or None
        archetype = self.combo_arch.currentData() or None
        location = self.combo_loc.currentData() or None
        engine = self.combo_engine.currentData() or "none"
        seed = random.SystemRandom().randrange(2 ** 32)

        try:
            prompt = generer_prompt_preview(
                base,
                self.env.doc.data,
                niveau=niveau,
                weaponised=weaponised,
                rune_char=rune_char,
                archetype=archetype,
                location=location,
                engine=engine,
                seed=seed,
            )
            self.output.setPlainText(prompt)
            self.status.setText(f"✅ Généré (seed={seed})")
            self.status.setStyleSheet(f"color: {C['cyan']};")
        except Exception as e:
            self.output.setPlainText(f"❌ Erreur de génération :\n\n{type(e).__name__}: {e}")
            self.status.setText("Erreur")
            self.status.setStyleSheet(f"color: {C['red']};")
