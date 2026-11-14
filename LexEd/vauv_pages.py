"""
vauv_pages — les écrans de l'éditeur.

  OverviewPage   aperçu et accès rapide à chaque section
  MetaPage       META_DATA
  RecordPage     liste maître + formulaire (runes, bindrunes, cibles, rituels, synergies, époques)
  ProfilesPage   RecordPage + radar interactif
  EnginesPage    RecordPage + plages de paramètres et aperçu du suffixe
  ListsPage      strates en listes de textes (S1 à S7, cibles par archétype / lieu)
  RawJsonPage    édition directe du JSON, avec contrôle avant application
"""
from __future__ import annotations

import copy
import re
from typing import Any, Callable

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMenu, QPlainTextEdit, QPushButton, QScrollArea, QSplitter,
                               QStackedWidget, QToolButton, QVBoxLayout, QWidget)

import vauv_core as core
from vauv_core import (CATEGORY_LABELS, ENTRY_TEMPLATES, PLACEHOLDER_RE, RUNTIME_PLACEHOLDERS, EntryTemplate, Field,
                       IssueIndex, RecordSet, Severity, find_references, format_path, unique_key)
from vauv_theme import C, SEV_COLOR, HudFrame, RadarChart, font, qc, rune_font
from vauv_widgets import (MISSING, Env, FormPanel, PairListField, StrListField, ask_key, confirm, repolish, tool)

# ════════════════════════════════════════════════════════════════════════════
#  Éléments communs
# ════════════════════════════════════════════════════════════════════════════


def label(text: str, role: str = "", wrap: bool = False) -> QLabel:
    l = QLabel(text)
    if role:
        l.setProperty("role", role)
    l.setWordWrap(wrap)
    return l


class IssueChips(QWidget):
    """Trois pastilles : erreurs, avertissements, infos."""
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None, clickable: bool = False):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.btns: list[QToolButton] = []
        for sev, name in ((Severity.ERROR, "erreur"), (Severity.WARNING, "avertissement"), (Severity.INFO, "info")):
            b = QToolButton()
            b.setProperty("stat", True)
            b.setToolTip(f"Nombre de {name}s")
            b.setStyleSheet(f"QToolButton {{ color: {SEV_COLOR[sev]}; }}")
            if clickable:
                b.setCursor(Qt.PointingHandCursor)
                b.clicked.connect(self.clicked.emit)
            else:
                b.setAttribute(Qt.WA_TransparentForMouseEvents)
                b.setStyleSheet(b.styleSheet() + "QToolButton { border-color: transparent; background: transparent; }")
            lay.addWidget(b)
            self.btns.append(b)
        self.set_counts(0, 0, 0)

    def set_counts(self, e: int, w: int, i: int, hide_zero: bool = False) -> None:
        for b, n, g in zip(self.btns, (e, w, i), ("●", "●", "●")):
            b.setText(f"{g} {n}")
            b.setVisible(not (hide_zero and n == 0))


def page_header(title: str, subtitle: str) -> tuple[QWidget, IssueChips]:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(2, 0, 2, 0)
    col = QVBoxLayout()
    col.setSpacing(2)
    col.addWidget(label(title, "title"))
    col.addWidget(label(subtitle, "mono"))
    lay.addLayout(col, 1)
    chips = IssueChips()
    lay.addWidget(chips, 0, Qt.AlignRight | Qt.AlignTop)
    return w, chips


def scroll_wrap(inner: QWidget) -> QScrollArea:
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.NoFrame)
    sa.setWidget(inner)
    return sa


class Page(QWidget):
    def __init__(self, env: Env, title: str, code: str, prefix: tuple, subtitle: str = ""):
        super().__init__()
        self.setObjectName("page")
        self.env, self.title, self.code, self.prefix = env, title, code, tuple(prefix)
        self.subtitle = subtitle or " › ".join(prefix)
        self.stale = True
        self.navigate: Callable[[tuple], None] = lambda path: None
        self.say: Callable[[str], None] = lambda msg: None

    def reload(self) -> None:
        self.stale = False

    def mark_stale(self) -> None:
        self.stale = True

    def showEvent(self, e) -> None:
        if self.stale:
            self.reload()
        super().showEvent(e)

    def focus_path(self, path: tuple) -> None:
        pass

    def apply_issues(self, idx: IssueIndex) -> None:
        pass

    def summary(self) -> str:
        return ""

    @property
    def doc(self):
        return self.env.doc


def root_layout(page: QWidget) -> QVBoxLayout:
    lay = QVBoxLayout(page)
    lay.setContentsMargins(22, 18, 22, 14)
    lay.setSpacing(14)
    return lay


# ════════════════════════════════════════════════════════════════════════════
#  Aperçu
# ════════════════════════════════════════════════════════════════════════════
class StatCard(HudFrame):
    def __init__(self, code: str, title: str, on_click: Callable[[], None]):
        super().__init__(accent="rose", chamfer=10, cuts="tr")
        self._click = on_click
        self.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(2)
        top = QHBoxLayout()
        self.code = label(code, "mono")
        self.badge = QLabel("")
        top.addWidget(self.code)
        top.addStretch(1)
        top.addWidget(self.badge)
        lay.addLayout(top)
        self.title = QLabel(title)
        self.title.setFont(font("ui", 16, True))
        lay.addWidget(self.title)
        self.sub = label("", "muted")
        lay.addWidget(self.sub)

    def update_info(self, summary: str, worst: Severity | None, count: int) -> None:
        self.sub.setText(summary)
        if worst is None:
            self.badge.setText("")
        else:
            self.badge.setText(f"● {count}")
            self.badge.setStyleSheet(f"color: {SEV_COLOR[worst]}; font-family: monospace;")

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            self._click()


class OverviewPage(Page):
    def __init__(self, env: Env):
        super().__init__(env, "Aperçu", "◇", (), "Vue d'ensemble du document")
        self.pages: list[Page] = []
        self.cards: dict[int, StatCard] = {}
        lay = root_layout(self)
        head, self.chips = page_header("Aperçu", "Vue d'ensemble du document")
        lay.addWidget(head)
        self.card = HudFrame(accent="cyan", chamfer=16)
        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(24, 20, 24, 20)
        self.l_codex = QLabel("")
        self.l_codex.setFont(font("display", 22, True))
        self.l_ver = label("", "muted")
        self.l_path = label("", "mono")
        self.l_sigil = QLabel("".join(c for c, _ in core.ELDER_FUTHARK))
        self.l_sigil.setFont(rune_font(26))
        self.l_sigil.setStyleSheet(f"color: {C['cyan']}; letter-spacing: 4px;")
        self.l_sigil.setWordWrap(True)
        for w in (self.l_codex, self.l_ver, self.l_path, self.l_sigil):
            cl.addWidget(w)
        lay.addWidget(self.card)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        lay.addWidget(scroll_wrap(self.grid_host), 1)

    def set_pages(self, pages: list[Page]) -> None:
        self.pages = [p for p in pages if p is not self and p.prefix]
        for n, p in enumerate(self.pages):
            c = StatCard(p.code, p.title, lambda p=p: self.navigate(p.prefix))
            self.cards[id(p)] = c
            self.grid.addWidget(c, n // 3, n % 3)
        for col in range(3):
            self.grid.setColumnStretch(col, 1)
        self.grid.setRowStretch(len(self.pages) // 3 + 1, 1)

    def reload(self) -> None:
        super().reload()
        m = self.doc.get((core.S_META,), {}) or {}
        self.l_codex.setText(str(m.get("codex", "Sans nom")))
        bits = [f"version {m['version']}" if "version" in m else "", str(m.get("classification", "")),
                str(m.get("theory", ""))]
        self.l_ver.setText("   ".join(b for b in bits if b))
        self.l_path.setText(str(self.doc.path) if self.doc.path else "Document non enregistré")
        for p in self.pages:
            c = self.cards[id(p)]
            e, w, i = self.env.issues.counts(p.prefix)
            worst = self.env.issues.worst(p.prefix)
            c.update_info(p.summary(), worst, e + w + i)
        self.chips.set_counts(*self.env.issues.total())

    def apply_issues(self, idx: IssueIndex) -> None:
        self.reload()


# ════════════════════════════════════════════════════════════════════════════
#  Métadonnées
# ════════════════════════════════════════════════════════════════════════════
META_LABELS = {
    "version": "Version", "codex": "Codex", "classification": "Classification", "target_engine": "Moteurs visés",
    "theory": "Théorie", "warning": "Avertissement", "changelog": "Journal des changements",
}


class MetaPage(Page):
    def __init__(self, env: Env):
        super().__init__(env, "Métadonnées", "—", (core.S_META,), core.S_META)
        lay = root_layout(self)
        head, self.chips = page_header("Métadonnées", core.S_META)
        lay.addWidget(head)
        self.frame = HudFrame(accent="cyan")
        fl = QVBoxLayout(self.frame)
        fl.setContentsMargins(26, 24, 26, 22)
        self.host = QVBoxLayout()
        fl.addLayout(self.host)
        fl.addStretch(1)
        lay.addWidget(scroll_wrap(self.frame), 1)
        self.form: FormPanel | None = None
        self._keys: list[str] = []

    def _fields(self, keys: list[str]) -> tuple:
        return tuple(Field(k, META_LABELS.get(k, k), "text" if k == "changelog" else "str", empty=Severity.WARNING,
                           pattern=core.VERSION_RE.pattern if k == "version" else "",
                           hint="Format 3.1 ou 3.1.2." if k == "version" else "")
                     for k in keys)

    def reload(self) -> None:
        super().reload()
        meta = self.doc.get((core.S_META,))
        meta = meta if isinstance(meta, dict) else {}
        keys = [k for k in META_LABELS if k in meta] + [k for k in meta if k not in META_LABELS]
        keys = keys or list(META_LABELS)
        if self.form is None or keys != self._keys:
            if self.form is not None:
                self.form.setParent(None)
                self.form.deleteLater()
            self._keys = keys
            self.form = FormPanel(self._fields(keys), self.env, label_width=170)
            self.form.changed.connect(self._changed)
            self.host.addWidget(self.form)
        self.form.set_record(meta)
        self.apply_issues(self.env.issues)

    def _changed(self, key: str, v: Any) -> None:
        if not isinstance(self.doc.get((core.S_META,)), dict):
            self.doc.set((core.S_META,), {}, label="Création de META_DATA")
        self.doc.set((core.S_META, key), v, label=f"Modification de {key}", coalesce=("meta", key), origin=self)

    def apply_issues(self, idx: IssueIndex) -> None:
        if self.form:
            self.form.apply_issues(idx, (core.S_META,))
        self.chips.set_counts(*idx.counts((core.S_META,)), hide_zero=True)

    def focus_path(self, path: tuple) -> None:
        if self.form and len(path) > 1 and path[1] in self.form.widgets:
            self.form.widgets[path[1]].setFocus()

    def summary(self) -> str:
        m = self.doc.get((core.S_META,), {}) or {}
        return f"version {m.get('version', '?')}"


# ════════════════════════════════════════════════════════════════════════════
#  Enregistrements : liste maître + formulaire
# ════════════════════════════════════════════════════════════════════════════
GLYPH_FIELD = {"futhark": "char", "bindrunes": "chars", "rune_targets": "char"}


class _Fmt(dict):
    def __missing__(self, key: str) -> str:
        return ""


class RecordPage(Page):
    side_extra = False   # True : le widget annexe se place à droite du formulaire

    def __init__(self, env: Env, rs: RecordSet, code: str, title: str, subtitle: str = ""):
        super().__init__(env, title, code, rs.path, subtitle)
        self.rs = rs
        self.current: Any = None
        self._loading = False
        root = root_layout(self)
        head, self.chips = page_header(title, self.subtitle)
        root.addWidget(head)

        self.head_form: FormPanel | None = None
        if rs.header:
            self.head_form = FormPanel(rs.header, env, label_width=150)
            self.head_form.changed.connect(self._head_changed)
            root.addWidget(self.head_form)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        root.addWidget(split, 1)

        # ── colonne de gauche
        left = HudFrame(accent="rose", chamfer=12)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(14, 18, 14, 18)
        ll.setSpacing(8)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filtrer…")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._apply_filter)
        ll.addWidget(self.filter)
        self.list = QListWidget()
        self.list.setProperty("mono", True)
        self.list.currentItemChanged.connect(self._on_select)
        ll.addWidget(self.list, 1)
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        self.btn_add = QToolButton()
        self.btn_add.setText("+ Nouveau")
        self.btn_add.setProperty("tiny", True)
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.tpls = ENTRY_TEMPLATES.get(rs.id, ())
        if len(self.tpls) > 1:
            m = QMenu(self.btn_add)
            for t in self.tpls:
                a = m.addAction(t.label)
                a.setToolTip(t.hint)
                a.triggered.connect(lambda _=False, t=t: self._add(t))
            self.btn_add.setMenu(m)
            self.btn_add.setPopupMode(QToolButton.InstantPopup)
            self.btn_add.setToolTip("Créer à partir d'un gabarit")
        else:
            self.btn_add.clicked.connect(lambda: self._add(self.tpls[0]))
            self.btn_add.setToolTip(self.tpls[0].hint if self.tpls else "")
        row1.addWidget(self.btn_add)
        self.btn_dup = tool("Dupliquer", "Copie de l'élément sélectionné")
        self.btn_dup.clicked.connect(self._duplicate)
        row1.addWidget(self.btn_dup)
        self.btn_ren = tool("Renommer", "Changer l'identifiant (met à jour les références)")
        self.btn_ren.clicked.connect(self._rename)
        self.btn_ren.setVisible(rs.container == "dict")
        row1.addWidget(self.btn_ren)
        row1.addStretch(1)
        ll.addLayout(row1)
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        self.btn_del = tool("Supprimer", "Supprimer l'élément sélectionné")
        self.btn_del.setProperty("danger", True)
        self.btn_del.clicked.connect(self._delete)
        self.btn_up = tool("↑", "Monter")
        self.btn_up.clicked.connect(lambda: self._move(-1))
        self.btn_dn = tool("↓", "Descendre")
        self.btn_dn.clicked.connect(lambda: self._move(1))
        for b in (self.btn_del, self.btn_up, self.btn_dn):
            row2.addWidget(b)
        row2.addStretch(1)
        ll.addLayout(row2)
        split.addWidget(left)

        # ── panneau de droite
        right = HudFrame(accent="cyan", chamfer=12)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 14, 4, 14)
        self.stack = QStackedWidget()
        rl.addWidget(self.stack)
        self.empty = QWidget()
        el = QVBoxLayout(self.empty)
        self.empty_lbl = label("", "empty", wrap=True)
        self.empty_lbl.setAlignment(Qt.AlignCenter)
        el.addWidget(self.empty_lbl)
        self.stack.addWidget(self.empty)

        detail = QWidget()
        dl = QVBoxLayout(detail)
        dl.setContentsMargins(22, 6, 22, 10)
        dl.setSpacing(12)
        top = QHBoxLayout()
        self.glyph = QLabel("")
        self.glyph.setStyleSheet(f"color: {C['cyan']};")
        self.glyph.setWordWrap(True)
        self.glyph.hide()
        top.addWidget(self.glyph)
        tcol = QVBoxLayout()
        self.d_title = QLabel("")
        self.d_title.setFont(font("display", 18, True))
        self.d_sub = label("", "muted")
        tcol.addWidget(self.d_title)
        tcol.addWidget(self.d_sub)
        top.addLayout(tcol, 1)
        dl.addLayout(top)
        self.form = FormPanel(rs.fields, env, label_width=150)
        self.form.changed.connect(self._form_changed)
        self.extra = self.make_extra()
        if self.extra is not None and self.side_extra:
            hb = QHBoxLayout()
            hb.setSpacing(20)
            hb.addWidget(self.form, 1)
            hb.addWidget(self.extra, 0, Qt.AlignTop)
            dl.addLayout(hb)
        else:
            dl.addWidget(self.form)
            if self.extra is not None:
                dl.addWidget(self.extra)
        dl.addStretch(1)
        self.stack.addWidget(scroll_wrap(detail))
        split.addWidget(right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([330, 900])
        left.setMinimumWidth(270)
        left.setMaximumWidth(460)

    # -- points d'extension -------------------------------------------------------
    def make_extra(self) -> QWidget | None:
        return None

    def update_extra(self, rec: dict) -> None:
        pass

    # -- accès aux données --------------------------------------------------------
    def container(self) -> Any:
        c = self.doc.get(self.rs.path)
        want = list if self.rs.container == "list" else dict
        return c if isinstance(c, want) else None

    def ids(self) -> list:
        c = self.container()
        if c is None:
            return []
        if self.rs.container == "list":
            return list(range(len(c)))
        skip = {f.key for f in self.rs.header}
        return [k for k in c if k not in skip]

    def record(self, id_: Any) -> dict:
        c = self.container()
        try:
            r = c[id_]
        except (KeyError, IndexError, TypeError):
            return {}
        return r if isinstance(r, dict) else {}

    def path_of(self, id_: Any) -> tuple:
        return self.rs.path + (id_,)

    def item_text(self, id_: Any) -> str:
        rec = self.record(id_)
        vals = _Fmt({f.key: rec.get(f.key) if isinstance(rec.get(f.key), str) else "" for f in self.rs.fields})
        vals["key"] = id_ + 1 if self.rs.container == "list" else id_
        txt = self.rs.label.format_map(vals).strip()
        return txt or f"(sans nom {id_ + 1})" if self.rs.container == "list" else (txt or "(sans nom)")

    def summary(self) -> str:
        n = len(self.ids())
        return f"{n} {self.rs.noun}{'s' if n > 1 else ''}"

    # -- affichage ------------------------------------------------------------------
    def reload(self) -> None:
        super().reload()
        ids = self.ids()
        cur = self.current
        self._loading = True
        self.list.clear()
        for id_ in ids:
            it = QListWidgetItem(self.item_text(id_))
            it.setData(Qt.UserRole, id_)
            if self.rs.id in ("futhark", "bindrunes", "rune_targets"):
                it.setFont(rune_font(15)) if False else None
            self.list.addItem(it)
        self._loading = False
        if cur not in ids and ids:
            cur = ids[min(cur, len(ids) - 1)] if isinstance(cur, int) and self.rs.container == "list" else ids[0]
        self._select(cur if ids else None)
        if self.head_form:
            c = self.container()
            self.head_form.set_record(c if c is not None else {})
        self._apply_filter()
        self.apply_issues(self.env.issues)

    def _select(self, id_: Any) -> None:
        self._loading = True
        self.current = id_
        for r in range(self.list.count()):
            if self.list.item(r).data(Qt.UserRole) == id_ and type(self.list.item(r).data(Qt.UserRole)) is type(id_):
                self.list.setCurrentRow(r)
                break
        else:
            self.list.setCurrentRow(-1)
        self._loading = False
        self._show_current()

    def _on_select(self, item: QListWidgetItem | None, _prev=None) -> None:
        if self._loading:
            return
        self.current = item.data(Qt.UserRole) if item else None
        self._show_current()
        self.apply_issues(self.env.issues)

    def _show_current(self) -> None:
        has = self.current is not None and self.container() is not None
        for b in (self.btn_dup, self.btn_ren, self.btn_del, self.btn_up, self.btn_dn):
            b.setEnabled(has)
        if not has:
            self.empty_lbl.setText(f"Aucun(e) {self.rs.noun} pour l'instant.\nUtilisez « + Nouveau » pour en créer "
                                   f"à partir d'un gabarit." if self.container() is not None else
                                   f"La section {' › '.join(self.rs.path)} est absente ou invalide.\n"
                                   f"Utilisez « + Nouveau » pour la recréer.")
            self.stack.setCurrentIndex(0)
            return
        rec = self.record(self.current)
        self.form.set_record(rec)
        self.stack.setCurrentIndex(1)
        self._refresh_titles(rec)
        self.update_extra(rec)

    def _refresh_titles(self, rec: dict) -> None:
        self.d_title.setText(self.item_text(self.current) if self.rs.container == "dict" else
                             str(rec.get("name") or rec.get("char") or f"{self.rs.noun} {self.current + 1}"))
        gk = GLYPH_FIELD.get(self.rs.id)
        g = ""
        if gk:
            g = rec.get(gk) if isinstance(rec.get(gk), str) else ""
        elif self.rs.id == "rituals":
            g = " ".join(x for x in (rec.get("runes") or []) if isinstance(x, str))
        elif self.rs.id == "synergies":
            t = rec.get("trigger")
            g = t.get("rune", "") if isinstance(t, dict) and isinstance(t.get("rune"), str) else ""
        self.glyph.setVisible(bool(g))
        self.glyph.setFont(rune_font(52 if len(g) <= 4 else 30 if len(g) <= 12 else 20))
        self.glyph.setMaximumWidth(480)
        self.glyph.setText(g)
        if self.rs.container == "list":
            self.d_sub.setText(f"{self.rs.noun.capitalize()} n°{self.current + 1}")
        else:
            self.d_sub.setText(f"{' › '.join(self.rs.path)} › {self.current}")

    def _apply_filter(self, *_a) -> None:
        t = self.filter.text().strip().lower()
        for r in range(self.list.count()):
            self.list.item(r).setHidden(bool(t) and t not in self.list.item(r).text().lower())

    # -- édition ---------------------------------------------------------------------
    def _form_changed(self, key: str, v: Any) -> None:
        if self.current is None:
            return
        path = self.path_of(self.current) + (key,)
        try:
            if v is MISSING:
                if self.doc.get(path, MISSING) is not MISSING:
                    self.doc.remove(path, label=f"Retrait de {key}", origin=self)
            else:
                self.doc.set(path, v, label=f"Modification de {key}", coalesce=("rec", path), origin=self)
        except KeyError as e:
            self.say(f"Modification impossible : {e}")
            return
        self._after_edit()

    def _head_changed(self, key: str, v: Any) -> None:
        if self.container() is None:
            return
        path = self.rs.path + (key,)
        if v is MISSING:
            if self.doc.get(path, MISSING) is not MISSING:
                self.doc.remove(path, origin=self)
        else:
            self.doc.set(path, v, label=f"Modification de {key}", coalesce=("head", path), origin=self)

    def _after_edit(self) -> None:
        rec = self.record(self.current)
        it = self.list.currentItem()
        if it is not None:
            it.setText(self.item_text(self.current))
        self._refresh_titles(rec)
        self.update_extra(rec)

    def _ensure_container(self) -> None:
        if self.container() is None:
            self.doc.set(self.rs.path, {} if self.rs.container == "dict" else [],
                         label=f"Création de {' › '.join(self.rs.path)}")

    def _existing_keys(self) -> set[str]:
        c = self.container()
        return set(c) if isinstance(c, dict) else set()

    def _insert_index(self) -> int | None:
        c = self.container()
        if self.current is None or c is None:
            return None
        if self.rs.container == "list":
            return self.current + 1
        keys = list(c)
        return keys.index(self.current) + 1 if self.current in keys else None

    def _add(self, tpl: EntryTemplate) -> None:
        self._ensure_container()
        suggestion, value = tpl.build(self.doc.data)
        value = copy.deepcopy(value)
        if self.rs.container == "dict":
            existing = self._existing_keys()
            choices = None
            if self.rs.key_ref:
                free = [v for v, _ in self.env.choices(self.rs.key_ref) if v not in existing]
                if suggestion in free:
                    free.remove(suggestion)
                    free.insert(0, suggestion)
                choices = free or None
            key = ask_key(self, f"Nouveau : {self.rs.noun}", self.rs.key_label + " :",
                          unique_key(suggestion or "nouveau", existing), existing, choices)
            if key is None:
                return
            if self.rs.id == "rune_targets":
                for ch, lab in self.env.choices("rune_chars"):
                    if lab.split("  ", 1)[-1] == key:
                        value["char"] = ch
            self.doc.add_key(self.rs.path, key, value, self._insert_index(), label=f"Ajout de {key}", origin=self)
            self.current = key
        else:
            self.current = self.doc.insert(self.rs.path, self._insert_index(), value,
                                           label=f"Ajout : {self.rs.noun}", origin=self)
        self.reload()
        self.say(f"{self.rs.noun.capitalize()} ajouté(e) depuis le gabarit « {tpl.label} ».")

    def _duplicate(self) -> None:
        if self.current is None:
            return
        value = copy.deepcopy(self.record(self.current))
        if self.rs.container == "dict":
            existing = self._existing_keys()
            key = ask_key(self, "Dupliquer", self.rs.key_label + " de la copie :",
                          unique_key(f"{self.current}_copie", existing), existing)
            if key is None:
                return
            self.doc.add_key(self.rs.path, key, value, self._insert_index(), label=f"Copie de {self.current}", origin=self)
            self.current = key
        else:
            self.current = self.doc.insert(self.rs.path, self._insert_index(), value, label="Copie", origin=self)
        self.reload()

    def _rename(self) -> None:
        if self.current is None or self.rs.container != "dict":
            return
        existing = self._existing_keys() - {self.current}
        new = ask_key(self, "Renommer", self.rs.key_label + " :", self.current, existing)
        if new is None or new == self.current:
            return
        n = self.doc.rename_key(self.rs.path, self.current, new, label=f"Renommage de {self.current}", origin=self)
        self.current = new
        self.reload()
        self.say(f"Renommé en « {new} »" + (f" ; {n} référence(s) mise(s) à jour." if n else "."))

    def _delete(self) -> None:
        if self.current is None:
            return
        refs = find_references(self.doc.data, self.rs.path, self.current) if self.rs.container == "dict" else []
        msg = f"Supprimer « {self.item_text(self.current)} » ?"
        if refs:
            msg += f"\n\n{len(refs)} référence(s) pointent vers cet élément et deviendront invalides."
        if not confirm(self, "Suppression", msg, "Supprimer", danger=True):
            return
        ids = self.ids()
        pos = ids.index(self.current)
        self.doc.remove(self.path_of(self.current), label=f"Suppression de {self.item_text(self.current)}", origin=self)
        left = self.ids()
        self.current = left[min(pos, len(left) - 1)] if left else None
        self.reload()

    def _move(self, d: int) -> None:
        if self.current is None:
            return
        if self.doc.move(self.rs.path, self.current, d, origin=self):
            if self.rs.container == "list":
                self.current += d
            self.reload()

    # -- navigation / validation -------------------------------------------------------
    def focus_path(self, path: tuple) -> None:
        rest = path[len(self.prefix):]
        if rest and rest[0] in self.ids():
            self._select(rest[0])
            self.apply_issues(self.env.issues)
            if len(rest) > 1 and rest[1] in self.form.widgets:
                self.form.widgets[rest[1]].setFocus()

    def apply_issues(self, idx: IssueIndex) -> None:
        for r in range(self.list.count()):
            it = self.list.item(r)
            id_ = it.data(Qt.UserRole)
            sev = idx.worst(self.path_of(id_))
            it.setForeground(QBrush(QColor(SEV_COLOR[sev]) if sev is not None and sev < Severity.INFO else qc("text")))
            msgs = [i.message for i in idx.issues if i.path[:len(self.path_of(id_))] == self.path_of(id_)][:4]
            it.setToolTip("\n".join(msgs))
        if self.current is not None and self.container() is not None:
            self.form.apply_issues(idx, self.path_of(self.current))
        if self.head_form:
            self.head_form.apply_issues(idx, self.rs.path)
        self.chips.set_counts(*idx.counts(self.rs.path), hide_zero=True)


class ProfilesPage(RecordPage):
    side_extra = True

    def make_extra(self) -> QWidget:
        self.radar = RadarChart(2.0, 0.05)
        self.radar.setFixedSize(340, 340)
        self.radar.valueChanged.connect(self._radar)
        return self.radar

    def update_extra(self, rec: dict) -> None:
        self.radar.set_values(rec)

    def _radar(self, axis: str, v: float) -> None:
        self.form.set_field_value(axis, v)
        self._form_changed(axis, v)


class EngineRanges(QWidget):
    """Plages [min, max] d'un moteur et aperçu du suffixe."""
    edited = Signal(str, object)         # nom, [min, max] ou MISSING
    renamed = Signal(str, str)
    add_requested = Signal()
    fill_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(label("Plages de paramètres", "h2"))
        lay.addWidget(label("Chaque {paramètre} du suffixe doit avoir une plage [min, max].", "hint"))
        self.rows = QVBoxLayout()
        self.rows.setSpacing(6)
        lay.addLayout(self.rows)
        bar = QHBoxLayout()
        b = tool("+ Ajouter une plage", "", tiny=False)
        b.clicked.connect(self.add_requested.emit)
        self.b_fill = tool("Créer les plages manquantes", "Ajoute une plage pour chaque {paramètre} du suffixe", tiny=False)
        self.b_fill.clicked.connect(self.fill_requested.emit)
        bar.addWidget(b)
        bar.addWidget(self.b_fill)
        bar.addStretch(1)
        lay.addLayout(bar)
        lay.addWidget(label("Aperçu du suffixe (valeurs médianes)", "field"))
        self.preview = QLabel("")
        self.preview.setProperty("role", "mono")
        self.preview.setStyleSheet(f"background: {C['bg2']}; border: 1px solid {C['line']}; padding: 8px 10px; "
                                   f"color: {C['cyan']}; font-family: monospace;")
        self.preview.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.preview.setWordWrap(True)
        lay.addWidget(self.preview)
        self._names: list[str] = []
        self._widgets: dict[str, tuple] = {}

    @staticmethod
    def _num(x: float) -> Any:
        return int(x) if float(x).is_integer() else round(x, 4)

    def set_engine(self, rec: dict) -> None:
        from PySide6.QtWidgets import QDoubleSpinBox
        ranges = {k: v for k, v in rec.items() if k not in ("suffix", "note")}
        names = list(ranges)
        if names != self._names:
            while self.rows.count():
                it = self.rows.takeAt(0)
                if it.widget():
                    it.widget().deleteLater()
            self._widgets.clear()
            for n in names:
                row = QWidget()
                hl = QHBoxLayout(row)
                hl.setContentsMargins(0, 0, 0, 0)
                hl.setSpacing(8)
                ed = QLineEdit(n)
                ed.setFixedWidth(160)
                ed.setUndoRedoEnabled(False)
                ed.editingFinished.connect(lambda n=n, ed=ed: self._rename(n, ed))
                lo, hi = QDoubleSpinBox(), QDoubleSpinBox()
                for s in (lo, hi):
                    s.setRange(-1e9, 1e9)
                    s.setDecimals(2)
                    s.setFixedWidth(110)
                    s.setButtonSymbols(QDoubleSpinBox.NoButtons)
                    s.setAlignment(Qt.AlignRight)
                lo.valueChanged.connect(lambda _v, n=n: self._emit(n))
                hi.valueChanged.connect(lambda _v, n=n: self._emit(n))
                rm = tool("✕", "Retirer cette plage")
                rm.clicked.connect(lambda _=False, n=n: self.edited.emit(n, MISSING))
                for w in (ed, label("min", "hint"), lo, label("max", "hint"), hi, rm):
                    hl.addWidget(w)
                hl.addStretch(1)
                self.rows.addWidget(row)
                self._widgets[n] = (ed, lo, hi)
            self._names = names
        for n in names:
            v = ranges[n]
            ed, lo, hi = self._widgets[n]
            ok = isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v)
            a, b = (float(v[0]), float(v[1])) if ok else (0.0, 0.0)
            for s, x in ((lo, a), (hi, b)):
                if abs(s.value() - x) > 1e-9:
                    s.blockSignals(True)
                    s.setValue(x)
                    s.blockSignals(False)
        suffix = rec.get("suffix", "") if isinstance(rec.get("suffix"), str) else ""
        used = set(PLACEHOLDER_RE.findall(suffix))
        self.b_fill.setEnabled(any(p not in ranges and p not in RUNTIME_PLACEHOLDERS for p in used))

        def sub(m: re.Match) -> str:
            n = m.group(1)
            v = ranges.get(n)
            if isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
                return str(self._num((v[0] + v[1]) / 2))
            return "12345" if n in RUNTIME_PLACEHOLDERS else m.group(0)
        self.preview.setText(PLACEHOLDER_RE.sub(sub, suffix).strip() or "(aucun suffixe : prompt seul)")

    def _emit(self, n: str) -> None:
        ed, lo, hi = self._widgets[n]
        a, b = lo.value(), hi.value()
        self.edited.emit(n, [self._num(a), self._num(b)])

    def _rename(self, old: str, ed: QLineEdit) -> None:
        new = ed.text().strip()
        if new and new != old:
            self.renamed.emit(old, new)


class EnginesPage(RecordPage):
    def make_extra(self) -> QWidget:
        self.ranges = EngineRanges()
        self.ranges.edited.connect(self._range_edited)
        self.ranges.renamed.connect(self._range_renamed)
        self.ranges.add_requested.connect(self._range_add)
        self.ranges.fill_requested.connect(self._range_fill)
        return self.ranges

    def update_extra(self, rec: dict) -> None:
        self.ranges.set_engine(rec)

    def _range_edited(self, name: str, v: Any) -> None:
        path = self.path_of(self.current) + (name,)
        if v is MISSING:
            self.doc.remove(path, label=f"Retrait de la plage {name}", origin=self)
            self._after_edit()
        else:
            self.doc.set(path, v, label=f"Plage {name}", coalesce=("range", path), origin=self)
            self._after_edit()

    def _range_renamed(self, old: str, new: str) -> None:
        rec = self.record(self.current)
        if new in rec or new in ("suffix", "note"):
            self.say(f"« {new} » est déjà utilisé dans ce moteur.")
            self._after_edit()
            self.ranges._names = []
            self.ranges.set_engine(rec)
            return
        self.doc.rename_key(self.path_of(self.current), old, new, cascade=False, label=f"Renommage de la plage {old}", origin=self)
        self._after_edit()

    def _range_add(self) -> None:
        rec = self.record(self.current)
        name = unique_key("param", set(rec))
        self.doc.set(self.path_of(self.current) + (name,), [0, 100], label="Ajout d'une plage", origin=self)
        self._after_edit()

    def _range_fill(self) -> None:
        rec = self.record(self.current)
        used = PLACEHOLDER_RE.findall(rec.get("suffix", "") if isinstance(rec.get("suffix"), str) else "")
        with self.doc.batch("Création des plages manquantes", self):
            for p in dict.fromkeys(used):
                if p not in rec and p not in RUNTIME_PLACEHOLDERS:
                    self.doc.set(self.path_of(self.current) + (p,), [0, 100], origin=self)
        self._after_edit()


# ════════════════════════════════════════════════════════════════════════════
#  Strates en listes de textes
# ════════════════════════════════════════════════════════════════════════════
class ListsPage(Page):
    def __init__(self, env: Env, title: str, code: str, base: tuple, subtitle: str = "", open_keys: bool = False,
                 noun: str = "catégorie"):
        super().__init__(env, title, code, base, subtitle)
        self.open_keys, self.noun = open_keys, noun
        self.cat: str | None = None
        self._loading = False
        root = root_layout(self)
        head, self.chips = page_header(title, self.subtitle)
        root.addWidget(head)
        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        root.addWidget(split, 1)

        left = HudFrame(accent="rose", chamfer=12)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(14, 18, 14, 18)
        ll.setSpacing(8)
        self.cats = QListWidget()
        self.cats.currentItemChanged.connect(self._on_cat)
        ll.addWidget(self.cats, 1)
        if open_keys:
            row = QHBoxLayout()
            row.setSpacing(4)
            b_add = tool(f"+ Nouvelle {noun}", "")
            b_add.clicked.connect(self._add_cat)
            b_ren = tool("Renommer", "Renomme la clé et met à jour les références")
            b_ren.clicked.connect(self._rename_cat)
            b_del = tool("Supprimer", "")
            b_del.setProperty("danger", True)
            b_del.clicked.connect(self._del_cat)
            for b in (b_add, b_ren, b_del):
                row.addWidget(b)
            row.addStretch(1)
            ll.addLayout(row)
        split.addWidget(left)
        left.setMinimumWidth(240)
        left.setMaximumWidth(400)

        right = HudFrame(accent="cyan", chamfer=12)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(22, 18, 22, 16)
        rl.setSpacing(10)
        self.d_title = QLabel("")
        self.d_title.setFont(font("display", 18, True))
        self.d_sub = label("", "muted")
        rl.addWidget(self.d_title)
        rl.addWidget(self.d_sub)
        self.stack = QStackedWidget()
        self.str_editor = StrListField(Field("items", "", "strlist"), env, title="Édition en bloc")
        self.str_editor.changed.connect(self._edited)
        self.pair_editor = PairListField(Field("pairs", "", "strlist"), env)
        self.pair_editor.changed.connect(self._edited)
        self.empty = label("Aucune catégorie.", "empty")
        self.empty.setAlignment(Qt.AlignCenter)
        for w in (self.str_editor, self.pair_editor, self.empty):
            self.stack.addWidget(w)
        rl.addWidget(self.stack, 1)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        split.setSizes([300, 900])

    # -- données ---------------------------------------------------------------------
    def section(self) -> dict | None:
        s = self.doc.get(self.prefix)
        return s if isinstance(s, dict) else None

    def cat_keys(self) -> list[str]:
        s = self.section()
        return [k for k, v in s.items() if isinstance(v, list)] if s else []

    def cat_label(self, k: str) -> str:
        return CATEGORY_LABELS.get(k, k.replace("_", " ").capitalize())

    def summary(self) -> str:
        s = self.section() or {}
        n = sum(len(v) for v in s.values() if isinstance(v, list))
        return f"{n} éléments, {len(self.cat_keys())} catégories"

    def reload(self) -> None:
        super().reload()
        keys = self.cat_keys()
        cur = self.cat if self.cat in keys else (keys[0] if keys else None)
        self._loading = True
        self.cats.clear()
        for k in keys:
            n = len(self.doc.get(self.prefix + (k,), []))
            it = QListWidgetItem(f"{self.cat_label(k)}   {n}")
            it.setData(Qt.UserRole, k)
            it.setToolTip(k)
            self.cats.addItem(it)
        self._loading = False
        self._select(cur)
        self.apply_issues(self.env.issues)

    def _select(self, key: str | None) -> None:
        self._loading = True
        self.cat = key
        for r in range(self.cats.count()):
            if self.cats.item(r).data(Qt.UserRole) == key:
                self.cats.setCurrentRow(r)
                break
        else:
            self.cats.setCurrentRow(-1)
        self._loading = False
        self._show()

    def _on_cat(self, item: QListWidgetItem | None, _p=None) -> None:
        if self._loading:
            return
        self.cat = item.data(Qt.UserRole) if item else None
        self._show()
        self.apply_issues(self.env.issues)

    def _is_pairs(self, key: str) -> bool:
        v = self.doc.get(self.prefix + (key,), [])
        return key == "yin_yang_pairs" or (isinstance(v, list) and v and all(isinstance(x, list) for x in v))

    def _show(self) -> None:
        if self.cat is None:
            self.d_title.setText("")
            self.d_sub.setText("")
            self.stack.setCurrentWidget(self.empty)
            return
        v = self.doc.get(self.prefix + (self.cat,), [])
        self.d_title.setText(self.cat_label(self.cat))
        self.d_sub.setText(" › ".join(self.prefix + (self.cat,)))
        if self._is_pairs(self.cat):
            self.pair_editor.set_value(v)
            self.stack.setCurrentWidget(self.pair_editor)
        else:
            self.str_editor.set_value(v)
            self.stack.setCurrentWidget(self.str_editor)

    def _edited(self, v: list) -> None:
        if self.cat is None:
            return
        self.doc.set(self.prefix + (self.cat,), v, label=f"Modification de {self.cat_label(self.cat)}",
                     coalesce=("list", self.prefix, self.cat), origin=self)
        it = self.cats.currentItem()
        if it is not None:
            it.setText(f"{self.cat_label(self.cat)}   {len(v)}")

    # -- catégories (clés ouvertes) -----------------------------------------------------
    def _add_cat(self) -> None:
        existing = set(self.section() or {})
        k = ask_key(self, f"Nouvelle {self.noun}", "Clé technique (snake_case) :", "nouvelle", existing)
        if k is None:
            return
        if self.section() is None:
            self.doc.set(self.prefix, {}, label="Création de la section")
        self.doc.add_key(self.prefix, k, [], label=f"Ajout de {k}", origin=self)
        self.cat = k
        self.reload()

    def _rename_cat(self) -> None:
        if not self.cat:
            return
        existing = set(self.section() or {}) - {self.cat}
        k = ask_key(self, "Renommer", "Nouvelle clé :", self.cat, existing)
        if k is None or k == self.cat:
            return
        n = self.doc.rename_key(self.prefix, self.cat, k, label=f"Renommage de {self.cat}", origin=self)
        self.cat = k
        self.reload()
        self.say(f"Renommé en « {k} »" + (f" ; {n} référence(s) mise(s) à jour." if n else "."))

    def _del_cat(self) -> None:
        if not self.cat:
            return
        refs = find_references(self.doc.data, self.prefix, self.cat)
        msg = f"Supprimer « {self.cat} » et ses {len(self.doc.get(self.prefix + (self.cat,), []))} éléments ?"
        if refs:
            msg += f"\n\n{len(refs)} référence(s) pointent vers cette clé et deviendront invalides."
        if confirm(self, "Suppression", msg, "Supprimer", danger=True):
            keys = self.cat_keys()
            pos = keys.index(self.cat)
            self.doc.remove(self.prefix + (self.cat,), label=f"Suppression de {self.cat}", origin=self)
            keys = self.cat_keys()
            self.cat = keys[min(pos, len(keys) - 1)] if keys else None
            self.reload()

    # -- navigation / validation ------------------------------------------------------------
    def focus_path(self, path: tuple) -> None:
        rest = path[len(self.prefix):]
        if rest and rest[0] in self.cat_keys():
            self._select(rest[0])
            self.apply_issues(self.env.issues)
            if len(rest) > 1 and isinstance(rest[1], int):
                if self.stack.currentWidget() is self.str_editor and rest[1] < self.str_editor.list.count():
                    self.str_editor.list.setCurrentRow(rest[1])
                    self.str_editor.list.scrollToItem(self.str_editor.list.item(rest[1]))
                elif self.stack.currentWidget() is self.pair_editor:
                    self.pair_editor.table.setCurrentCell(rest[1], 0)

    def apply_issues(self, idx: IssueIndex) -> None:
        for r in range(self.cats.count()):
            it = self.cats.item(r)
            k = it.data(Qt.UserRole)
            sev = idx.worst(self.prefix + (k,))
            it.setForeground(QBrush(QColor(SEV_COLOR[sev]) if sev is not None and sev < Severity.INFO else qc("text")))
        if self.cat is not None:
            ed = self.pair_editor if self.stack.currentWidget() is self.pair_editor else self.str_editor
            ed.apply_issues(idx, self.prefix + (self.cat,))
        self.chips.set_counts(*idx.counts(self.prefix), hide_zero=True)


# ════════════════════════════════════════════════════════════════════════════
#  JSON brut
# ════════════════════════════════════════════════════════════════════════════
class JsonHighlighter(QSyntaxHighlighter):
    TOKEN = re.compile(r'(?P<key>"(?:\\.|[^"\\])*"(?=\s*:))|(?P<str>"(?:\\.|[^"\\])*")|'
                       r'(?P<num>-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|(?P<lit>\btrue\b|\bfalse\b|\bnull\b)|(?P<punc>[\[\]{},:])')

    def __init__(self, parent):
        super().__init__(parent)

        def fmt(color: str, bold: bool = False) -> QTextCharFormat:
            f = QTextCharFormat()
            f.setForeground(QColor(C[color]))
            if bold:
                f.setFontWeight(QFont.Bold)
            return f
        self.f = {"key": fmt("cyan"), "str": fmt("amber"), "num": fmt("violet"), "lit": fmt("rose", True),
                  "punc": fmt("dim")}

    def highlightBlock(self, text: str) -> None:
        for m in self.TOKEN.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self.f[m.lastgroup])


class RawJsonPage(Page):
    def __init__(self, env: Env):
        super().__init__(env, "JSON brut", "{}", (), "Édition directe du document")
        root = root_layout(self)
        head, self.chips = page_header("JSON brut", "Édition directe du document")
        root.addWidget(head)
        frame = HudFrame(accent="rose", chamfer=12)
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(14, 18, 14, 14)
        self.edit = QPlainTextEdit()
        self.edit.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.edit.setFont(font("mono", 13))
        self.edit.setUndoRedoEnabled(True)
        self.edit.setTabStopDistance(28)
        self.hl = JsonHighlighter(self.edit.document())
        self.edit.textChanged.connect(self._text_changed)
        fl.addWidget(self.edit, 1)
        bar = QHBoxLayout()
        self.status = QLabel("")
        bar.addWidget(self.status, 1)
        self.b_reload = QPushButton("Recharger depuis le document")
        self.b_reload.clicked.connect(self.reload)
        self.b_apply = QPushButton("Appliquer au document")
        self.b_apply.setProperty("primary", True)
        self.b_apply.clicked.connect(self._apply)
        bar.addWidget(self.b_reload)
        bar.addWidget(self.b_apply)
        fl.addLayout(bar)
        root.addWidget(frame, 1)
        self._loading = False
        self._text_dirty = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._check)

    def reload(self) -> None:
        super().reload()
        self._loading = True
        self.edit.setPlainText(core.dumps(self.doc.data))
        self._loading = False
        self._text_dirty = False
        self._check()

    def showEvent(self, e) -> None:
        if self.stale and not self._text_dirty:
            self.reload()
        QWidget.showEvent(self, e)

    def _text_changed(self) -> None:
        if not self._loading:
            self._text_dirty = True
            self._timer.start()

    def _check(self) -> None:
        try:
            core.loads(self.edit.toPlainText())
            ok, msg = True, ("Modifications non appliquées" if self._text_dirty else "JSON identique au document")
        except core.LexiconError as e:
            ok, msg = False, str(e)
        self.status.setText(msg)
        self.status.setStyleSheet(f"color: {C['cyan'] if ok else C['red']}; font-family: monospace;")
        self.b_apply.setEnabled(ok and self._text_dirty)

    def _apply(self) -> None:
        try:
            data = core.loads(self.edit.toPlainText())
        except core.LexiconError as e:
            self.status.setText(str(e))
            return
        self.doc.replace_all(data, label="Édition du JSON brut", origin=self)
        self._text_dirty = False
        self._check()
        self.say("JSON appliqué au document.")
