"""
vauv_widgets — éditeurs de champs construits à partir du schéma (vauv_core.Field).

Chaque FieldWidget expose :
    set_value(v)               affiche une valeur sans émettre de signal
    changed(value)             émis uniquement sur une saisie de l'utilisateur
    refresh_choices()          recharge les listes liées (archétypes, runes…)
    apply_issues(index, path)  surligne les problèmes de validation
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
                               QFrame, QGridLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLayout, QLineEdit, QListWidget,
                               QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QSizePolicy, QSlider,
                               QSpinBox, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from vauv_core import (ELDER_FUTHARK, Field, IssueIndex, Severity, choices_for, default_for)
from vauv_theme import SEV_COLOR, qc, rune_font

MISSING = object()   # valeur « champ absent » (champ optionnel décoché)
_SEV_PROP = {Severity.ERROR: "error", Severity.WARNING: "warning", Severity.INFO: "info"}


class Env:
    """Contexte partagé : document courant + index des problèmes de validation."""

    def __init__(self, doc):
        self.doc = doc
        self.issues = IssueIndex()

    def choices(self, ref: str) -> list[tuple[str, str]]:
        return choices_for(ref, self.doc.data)

    def runes(self) -> list[tuple[str, str]]:
        r = self.choices("rune_chars")
        return r or [(c, f"{c}  {n}") for c, n in ELDER_FUTHARK]


def repolish(w: QWidget) -> None:
    for x in [w] + w.findChildren(QWidget):
        x.style().unpolish(x)
        x.style().polish(x)


def tool(text: str, tip: str = "", tiny: bool = True, parent: QWidget | None = None) -> QToolButton:
    b = QToolButton(parent)
    b.setText(text)
    b.setToolTip(tip)
    b.setProperty("tiny", tiny)
    b.setCursor(Qt.PointingHandCursor)
    return b


def ask_key(parent: QWidget, title: str, label: str, default: str, existing: set[str],
            choices: list[str] | None = None) -> str | None:
    """Demande un identifiant valide et non utilisé ; None si annulé."""
    while True:
        if choices:
            text, ok = QInputDialog.getItem(parent, title, label, choices, 0, True)
        else:
            text, ok = QInputDialog.getText(parent, title, label, QLineEdit.Normal, default)
        if not ok:
            return None
        text = text.strip()
        if not text:
            QMessageBox.warning(parent, title, "L'identifiant ne peut pas être vide.")
        elif text in existing:
            QMessageBox.warning(parent, title, f"« {text} » existe déjà. Choisissez un autre identifiant.")
            default = text
        else:
            return text


def confirm(parent: QWidget, title: str, text: str, ok_label: str = "Confirmer", danger: bool = False) -> bool:
    box = QMessageBox(QMessageBox.Question, title, text, QMessageBox.NoButton, parent)
    yes = box.addButton(ok_label, QMessageBox.AcceptRole)
    yes.setProperty("danger", danger)
    box.addButton("Annuler", QMessageBox.RejectRole)
    box.exec()
    return box.clickedButton() is yes


# ════════════════════════════════════════════════════════════════════════════
#  Mise en page « flux » (puces de runes)
# ════════════════════════════════════════════════════════════════════════════
class FlowLayout(QLayout):
    def __init__(self, parent: QWidget | None = None, spacing: int = 6):
        super().__init__(parent)
        self._items: list = []
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, i: int):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i: int):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, w: int) -> int:
        return self._do(QRect(0, 0, w, 0), True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        s = QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        return s

    def _do(self, rect: QRect, test: bool) -> int:
        x, y, line_h = rect.x(), rect.y(), 0
        for it in self._items:
            w = it.sizeHint()
            if x + w.width() > rect.right() and line_h > 0:
                x, y, line_h = rect.x(), y + line_h + self.spacing(), 0
            if not test:
                it.setGeometry(QRect(QPoint(x, y), w))
            x += w.width() + self.spacing()
            line_h = max(line_h, w.height())
        return y + line_h - rect.y()


class RunePicker(QFrame):
    """Fenêtre flottante : grille des runes du Futhark."""
    picked = Signal(str)

    def __init__(self, runes: list[tuple[str, str]], parent: QWidget | None = None):
        super().__init__(parent, Qt.Popup)
        self.setStyleSheet(f"RunePicker {{ background: {qc('bg1').name()}; border: 1px solid {qc('cyan').name()}; }}")
        g = QGridLayout(self)
        g.setContentsMargins(8, 8, 8, 8)
        g.setSpacing(4)
        for n, (ch, label) in enumerate(runes):
            b = QToolButton()
            b.setText(ch)
            b.setFont(rune_font(22))
            b.setToolTip(label)
            b.setProperty("chip", True)
            b.setFixedSize(40, 40)
            b.clicked.connect(lambda _=False, c=ch: (self.picked.emit(c), self.close()))
            g.addWidget(b, n // 8, n % 8)

    def popup_at(self, anchor: QWidget) -> None:
        self.move(anchor.mapToGlobal(QPoint(0, anchor.height() + 2)))
        self.show()


# ════════════════════════════════════════════════════════════════════════════
#  Base
# ════════════════════════════════════════════════════════════════════════════
class FieldWidget(QWidget):
    changed = Signal(object)

    def __init__(self, f: Field, env: Env, parent: QWidget | None = None):
        super().__init__(parent)
        self.f, self.env = f, env
        self.setObjectName("field")
        self._loading = False

    def set_value(self, v: Any) -> None:  # pragma: no cover
        raise NotImplementedError

    def refresh_choices(self) -> None:
        pass

    def set_issue(self, sev: Severity | None, tip: str = "") -> None:
        prop = _SEV_PROP.get(sev, "") if sev is not None else ""
        if self.property("issue") != prop:
            self.setProperty("issue", prop)
            repolish(self)
        self.setToolTip(tip or (self.f.hint if self.f else ""))

    def apply_issues(self, idx: IssueIndex, path: tuple) -> None:
        sev = idx.worst(path)
        msgs = [i.message for i in idx.issues if i.path[:len(path)] == path][:5]
        self.set_issue(sev, "\n".join(msgs))


# ════════════════════════════════════════════════════════════════════════════
#  Champs simples
# ════════════════════════════════════════════════════════════════════════════
class LineField(FieldWidget):
    def __init__(self, f: Field, env: Env, parent: QWidget | None = None):
        super().__init__(f, env, parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.edit = QLineEdit()
        self.edit.setUndoRedoEnabled(False)
        self.edit.textEdited.connect(self.changed.emit)
        lay.addWidget(self.edit, 1)
        if f.kind in ("rune", "runestr"):
            self.edit.setFont(rune_font(20))
            if f.kind == "rune":
                self.edit.setMaxLength(1)
                self.edit.setFixedWidth(64)
                self.edit.setAlignment(Qt.AlignCenter)
            b = tool("Runes…", "Choisir dans le Futhark", tiny=False)
            b.clicked.connect(self._pick)
            lay.addWidget(b)
            if f.kind == "rune":
                lay.addStretch(1)

    def _pick(self) -> None:
        pk = RunePicker(self.env.runes(), self)
        pk.picked.connect(self._picked)
        pk.popup_at(self.edit)

    def _picked(self, ch: str) -> None:
        txt = ch if self.f.kind == "rune" else self.edit.text() + ch
        self.edit.setText(txt)
        self.changed.emit(txt)

    def set_value(self, v: Any) -> None:
        t = v if isinstance(v, str) else ("" if v in (None, MISSING) else str(v))
        if self.edit.text() != t:
            self.edit.setText(t)


class TextAreaField(FieldWidget):
    def __init__(self, f: Field, env: Env, parent: QWidget | None = None):
        super().__init__(f, env, parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.edit = QPlainTextEdit()
        self.edit.setUndoRedoEnabled(False)
        self.edit.setFixedHeight(84)
        self.edit.textChanged.connect(self._on)
        lay.addWidget(self.edit)

    def _on(self) -> None:
        if not self._loading:
            self.changed.emit(self.edit.toPlainText())

    def set_value(self, v: Any) -> None:
        t = v if isinstance(v, str) else ""
        if self.edit.toPlainText() != t:
            self._loading = True
            self.edit.setPlainText(t)
            self._loading = False


class ChoiceField(FieldWidget):
    """Liste déroulante : énumération fixe ou référence dynamique (archétypes, lieux, runes…)."""

    def __init__(self, f: Field, env: Env, parent: QWidget | None = None):
        super().__init__(f, env, parent)
        self._value = ""
        self._editable = not f.strict
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        self.combo.setMinimumWidth(220)
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        if f.kind == "rune":
            self.combo.setFont(rune_font(16))
        if self._editable:
            self.combo.setEditable(True)
            self.combo.setInsertPolicy(QComboBox.NoInsert)
            self.combo.lineEdit().setUndoRedoEnabled(False)
            self.combo.editTextChanged.connect(self._on_text)
        else:
            self.combo.currentIndexChanged.connect(self._on_index)
        lay.addWidget(self.combo)
        lay.addStretch(1)
        self._rebuild("")

    def _options(self) -> list[tuple[str, str]]:
        if self.f.choices:
            return [(c, c) for c in self.f.choices]
        return self.env.choices(self.f.ref)

    def _rebuild(self, value: str) -> None:
        self._loading = True
        self.combo.clear()
        opts = self._options()
        if not self._editable and value not in [v for v, _ in opts]:
            self.combo.addItem("—" if value == "" else f"{value}   (introuvable)", value)
        for v, label in opts:
            self.combo.addItem(label, v)
        i = self.combo.findData(value)
        if i >= 0:
            self.combo.setCurrentIndex(i)
        if self._editable:
            self.combo.setEditText(value)
        self._loading = False

    def refresh_choices(self) -> None:
        self._rebuild(self._value)

    def _on_index(self, i: int) -> None:
        if self._loading or i < 0:
            return
        self._value = self.combo.itemData(i)
        self.changed.emit(self._value)

    def _on_text(self, t: str) -> None:
        if self._loading:
            return
        self._value = t
        self.changed.emit(t)

    def set_value(self, v: Any) -> None:
        self._value = v if isinstance(v, str) else ""
        self._rebuild(self._value)


class NumberField(FieldWidget):
    def __init__(self, f: Field, env: Env, parent: QWidget | None = None):
        super().__init__(f, env, parent)
        self._int = f.kind == "int"
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.slider: QSlider | None = None
        if f.min is not None and f.max is not None:
            self._n = max(1, int(round((f.max - f.min) / f.step)))
            self.slider = QSlider(Qt.Horizontal)
            self.slider.setRange(0, self._n)
            self.slider.setMinimumWidth(180)
            self.slider.valueChanged.connect(self._from_slider)
            lay.addWidget(self.slider, 1)
        self.spin = QSpinBox() if self._int else QDoubleSpinBox()
        self.spin.setRange(-10**9, 10**9) if self._int else self.spin.setRange(-1e6, 1e6)
        if not self._int:
            self.spin.setDecimals(2)
            self.spin.setSingleStep(f.step)
        self.spin.setButtonSymbols(QSpinBox.NoButtons)
        self.spin.setFixedWidth(84)
        self.spin.setAlignment(Qt.AlignRight)
        self.spin.valueChanged.connect(self._from_spin)
        lay.addWidget(self.spin)
        if self.slider is None:
            lay.addStretch(1)

    def _emit(self, v: float) -> None:
        self.changed.emit(int(v) if self._int else round(float(v), 4))

    def _from_spin(self, v: float) -> None:
        if self._loading:
            return
        if self.slider is not None:
            self._loading = True
            self.slider.setValue(int(round((v - self.f.min) / self.f.step)))
            self._loading = False
        self._emit(v)

    def _from_slider(self, i: int) -> None:
        if self._loading:
            return
        v = round(self.f.min + i * self.f.step, 4)
        self._loading = True
        self.spin.setValue(v)
        self._loading = False
        self._emit(v)

    def set_value(self, v: Any) -> None:
        ok = isinstance(v, (int, float)) and not isinstance(v, bool)
        x = float(v) if ok else 0.0
        self._loading = True
        self.spin.setValue(int(x) if self._int else x)
        if self.slider is not None:
            self.slider.setValue(max(0, min(self._n, int(round((x - self.f.min) / self.f.step)))))
        self._loading = False


# ════════════════════════════════════════════════════════════════════════════
#  Liste de textes
# ════════════════════════════════════════════════════════════════════════════
class BulkDialog(QDialog):
    def __init__(self, items: list[str], title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(640, 520)
        lay = QVBoxLayout(self)
        lay.addWidget(self._lbl("Un élément par ligne. Les lignes vides sont ignorées."))
        self.edit = QPlainTextEdit("\n".join(items))
        self.edit.setUndoRedoEnabled(True)
        lay.addWidget(self.edit, 1)
        bb = QDialogButtonBox()
        ok = bb.addButton("Appliquer", QDialogButtonBox.AcceptRole)
        ok.setProperty("primary", True)
        bb.addButton("Annuler", QDialogButtonBox.RejectRole)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    @staticmethod
    def _lbl(t: str) -> QLabel:
        l = QLabel(t)
        l.setProperty("role", "muted")
        return l

    def items(self) -> list[str]:
        return [ln.rstrip("\r") for ln in self.edit.toPlainText().split("\n") if ln.strip()]


class StrListField(FieldWidget):
    def __init__(self, f: Field, env: Env, parent: QWidget | None = None, compact: bool = False,
                 title: str = "Édition en bloc"):
        super().__init__(f, env, parent)
        self._value: list[str] = []
        self._title = title
        self._new: QListWidgetItem | None = None
        self._flags: dict[int, Severity] = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        bar = QHBoxLayout()
        bar.setSpacing(4)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filtrer…")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._apply_filter)
        if not compact:
            bar.addWidget(self.filter, 1)
        else:
            self.filter.hide()
            bar.addStretch(1)
        self.count = QLabel("")
        self.count.setProperty("role", "hint")
        bar.addWidget(self.count)
        lay.addLayout(bar)

        self.list = QListWidget()
        self.list.setProperty("mono", True)
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setDefaultDropAction(Qt.MoveAction)
        self.list.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        if compact:
            self.list.setMinimumHeight(110)
            self.list.setMaximumHeight(190)
        else:
            self.list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.list.itemChanged.connect(lambda _i: QTimer.singleShot(0, self._sync))
        m = self.list.model()
        m.rowsMoved.connect(lambda *_: QTimer.singleShot(0, self._sync))
        m.rowsRemoved.connect(lambda *_: QTimer.singleShot(0, self._sync))
        self.list.itemDelegate().closeEditor.connect(lambda *_: QTimer.singleShot(0, self._cleanup_new))
        lay.addWidget(self.list, 1)
        QShortcut(QKeySequence.Delete, self.list, activated=self.remove_selected).setContext(Qt.WidgetShortcut)

        row = QHBoxLayout()
        row.setSpacing(4)
        for text, tip, fn in (("+ Ajouter", "Ajouter un élément (Entrée pour valider)", self.add),
                              ("− Retirer", "Retirer la sélection (Suppr)", self.remove_selected),
                              ("↑", "Monter la sélection", lambda: self.move(-1)),
                              ("↓", "Descendre la sélection", lambda: self.move(1)),
                              ("Bloc…", "Éditer tous les éléments dans une zone de texte", self.bulk),
                              ("Dédoublonner", "Supprimer les doublons exacts", self.dedupe)):
            b = tool(text, tip)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)

    # -- état ----------------------------------------------------------------
    def _texts(self) -> list[str]:
        return [self.list.item(i).text() for i in range(self.list.count())]

    def _sync(self) -> None:
        if self._loading:
            return
        t = self._texts()
        if t != self._value:
            self._value = t
            self._update_count()
            self.changed.emit(list(t))

    def _update_count(self) -> None:
        n = self.list.count()
        self.count.setText(f"{n} élément{'s' if n > 1 else ''}")

    def _make_item(self, text: str) -> QListWidgetItem:
        it = QListWidgetItem(text)
        it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsDragEnabled)
        return it

    def set_value(self, v: Any) -> None:
        items = [x if isinstance(x, str) else str(x) for x in v] if isinstance(v, list) else []
        if items == self._value and self.list.count() == len(items):
            return
        self._loading = True
        sel = [self.list.row(i) for i in self.list.selectedItems()]
        self.list.clear()
        for t in items:
            self.list.addItem(self._make_item(t))
        self._value = items
        for r in sel:
            if r < self.list.count():
                self.list.item(r).setSelected(True)
        self._loading = False
        self._update_count()
        self._paint_flags()
        self._apply_filter(self.filter.text())

    # -- actions ---------------------------------------------------------------
    def add(self) -> None:
        if self.filter.text():
            self.filter.clear()
        it = self._make_item("")
        rows = sorted(self.list.row(i) for i in self.list.selectedItems())
        at = rows[-1] + 1 if rows else self.list.count()
        self._loading = True
        self.list.insertItem(at, it)
        self._loading = False
        self._new = it
        self.list.setCurrentItem(it)
        self.list.scrollToItem(it)
        self.list.editItem(it)

    def _cleanup_new(self) -> None:
        it, self._new = self._new, None
        if it is not None and self.list.row(it) >= 0 and not it.text().strip():
            self._loading = True
            self.list.takeItem(self.list.row(it))
            self._loading = False
        self._sync()

    def remove_selected(self) -> None:
        rows = sorted((self.list.row(i) for i in self.list.selectedItems()), reverse=True)
        if not rows:
            return
        self._loading = True
        for r in rows:
            self.list.takeItem(r)
        self._loading = False
        nxt = min(rows[-1], self.list.count() - 1)
        if nxt >= 0:
            self.list.setCurrentRow(nxt)
        self._sync()

    def move(self, delta: int) -> None:
        rows = sorted(self.list.row(i) for i in self.list.selectedItems())
        if not rows or (delta < 0 and rows[0] == 0) or (delta > 0 and rows[-1] == self.list.count() - 1):
            return
        texts = self._texts()
        for r in (rows if delta < 0 else reversed(rows)):
            texts[r], texts[r + delta] = texts[r + delta], texts[r]
        self.set_value(texts)
        self._loading = True
        self.list.clearSelection()
        for r in rows:
            self.list.item(r + delta).setSelected(True)
        self._loading = False
        self.changed.emit(list(texts))

    def bulk(self) -> None:
        dlg = BulkDialog(self._texts(), self._title, self)
        if dlg.exec():
            self._flags = {}
            self.set_value(dlg.items())
            self.changed.emit(list(self._value))

    def dedupe(self) -> None:
        seen, out = set(), []
        for t in self._texts():
            if t not in seen:
                seen.add(t)
                out.append(t)
        if len(out) != self.list.count():
            self.set_value(out)
            self.changed.emit(list(out))

    def _apply_filter(self, text: str) -> None:
        t = text.strip().lower()
        for i in range(self.list.count()):
            self.list.item(i).setHidden(bool(t) and t not in self.list.item(i).text().lower())

    # -- validation ------------------------------------------------------------
    def apply_issues(self, idx: IssueIndex, path: tuple) -> None:
        flags: dict[int, Severity] = {}
        tips: dict[int, str] = {}
        for i in idx.issues:
            if len(i.path) == len(path) + 1 and i.path[:len(path)] == path and isinstance(i.path[-1], int):
                n = i.path[-1]
                if n not in flags or i.severity < flags[n]:
                    flags[n] = i.severity
                tips[n] = (tips[n] + "\n" if n in tips else "") + i.message
        self._flags, self._tips = flags, tips
        self._paint_flags()
        self.set_issue(None, "")

    def _paint_flags(self) -> None:
        tips = getattr(self, "_tips", {})
        for i in range(self.list.count()):
            it = self.list.item(i)
            sev = self._flags.get(i)
            if sev is None:
                it.setData(Qt.ForegroundRole, None)
                it.setData(Qt.BackgroundRole, None)
                it.setToolTip("")
            else:
                col = QColor(SEV_COLOR[sev])
                it.setForeground(QBrush(col))
                bg = QColor(col)
                bg.setAlpha(28)
                it.setBackground(QBrush(bg))
                it.setToolTip(tips.get(i, ""))


class PairListField(FieldWidget):
    """Liste de paires de textes (ex. yin_yang_pairs)."""

    def __init__(self, f: Field, env: Env, parent: QWidget | None = None, headers: tuple[str, str] = ("Pôle A", "Pôle B")):
        super().__init__(f, env, parent)
        self._value: list[list[str]] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(list(headers))
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(f"QTableWidget {{ background: {qc('bg1').name()}; border: 1px solid {qc('line').name()}; "
                                 f"font-family: monospace; }} QTableWidget::item {{ padding: 4px 8px; }} "
                                 f"QTableWidget::item:selected {{ background: {qc('bg3').name()}; "
                                 f"border-left: 2px solid {qc('rose').name()}; }}")
        self.table.itemChanged.connect(lambda _i: self._sync())
        lay.addWidget(self.table, 1)
        row = QHBoxLayout()
        for text, tip, fn in (("+ Ajouter", "Ajouter une paire", self.add), ("− Retirer", "Retirer la paire", self.remove),
                              ("↑", "Monter", lambda: self.move(-1)), ("↓", "Descendre", lambda: self.move(1))):
            b = tool(text, tip)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)

    def _read(self) -> list[list[str]]:
        out = []
        for r in range(self.table.rowCount()):
            a, b = self.table.item(r, 0), self.table.item(r, 1)
            out.append([a.text() if a else "", b.text() if b else ""])
        return out

    def _sync(self) -> None:
        if self._loading:
            return
        v = self._read()
        if v != self._value:
            self._value = v
            self.changed.emit([list(p) for p in v])

    def set_value(self, v: Any) -> None:
        pairs = []
        for p in (v if isinstance(v, list) else []):
            p = p if isinstance(p, list) else [str(p)]
            pairs.append([str(p[0]) if len(p) > 0 else "", str(p[1]) if len(p) > 1 else ""])
        if pairs == self._value and self.table.rowCount() == len(pairs):
            return
        self._loading = True
        self.table.setRowCount(len(pairs))
        for r, (a, b) in enumerate(pairs):
            self.table.setItem(r, 0, QTableWidgetItem(a))
            self.table.setItem(r, 1, QTableWidgetItem(b))
        self._value = pairs
        self._loading = False

    def add(self) -> None:
        r = self.table.currentRow() + 1 if self.table.currentRow() >= 0 else self.table.rowCount()
        self._loading = True
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(""))
        self.table.setItem(r, 1, QTableWidgetItem(""))
        self._loading = False
        self.table.setCurrentCell(r, 0)
        self.table.editItem(self.table.item(r, 0))

    def remove(self) -> None:
        r = self.table.currentRow()
        if r >= 0:
            self._loading = True
            self.table.removeRow(r)
            self._loading = False
            self._sync()

    def move(self, d: int) -> None:
        r = self.table.currentRow()
        v = self._read()
        if r < 0 or not 0 <= r + d < len(v):
            return
        v[r], v[r + d] = v[r + d], v[r]
        self.set_value(v)
        self.table.setCurrentCell(r + d, 0)
        self.changed.emit([list(p) for p in v])

    def apply_issues(self, idx: IssueIndex, path: tuple) -> None:
        for r in range(self.table.rowCount()):
            sev = idx.worst(path + (r,))
            for c in (0, 1):
                it = self.table.item(r, c)
                if it:
                    if sev is None:
                        it.setBackground(QBrush())
                    else:
                        bg = QColor(SEV_COLOR[sev])
                        bg.setAlpha(34)
                        it.setBackground(QBrush(bg))
        self.set_issue(None, "")


# ════════════════════════════════════════════════════════════════════════════
#  Liste de runes (puces)
# ════════════════════════════════════════════════════════════════════════════
class RuneListField(FieldWidget):
    def __init__(self, f: Field, env: Env, parent: QWidget | None = None):
        super().__init__(f, env, parent)
        self._value: list[str] = []
        self._flags: dict[int, Severity] = {}
        self.flow = FlowLayout(self, 6)
        self._rebuild()

    def _rebuild(self) -> None:
        while self.flow.count():
            it = self.flow.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for i, ch in enumerate(self._value):
            b = QToolButton()
            b.setText(ch)
            b.setFont(rune_font(24))
            b.setProperty("chip", True)
            b.setFixedSize(46, 46)
            b.setCursor(Qt.PointingHandCursor)
            sev = self._flags.get(i)
            if sev is not None:
                b.setStyleSheet(f"QToolButton {{ border-color: {SEV_COLOR[sev]}; }}")
            b.clicked.connect(lambda _=False, n=i, w=b: self._menu(n, w))
            self.flow.addWidget(b)
        add = QToolButton()
        add.setText("+")
        add.setProperty("chip", True)
        add.setFixedSize(46, 46)
        add.setToolTip("Ajouter une rune")
        add.clicked.connect(lambda: self._pick(None, add))
        self.flow.addWidget(add)
        self.updateGeometry()

    def _menu(self, n: int, w: QWidget) -> None:
        m = QMenu(self)
        m.addAction("Remplacer…", lambda: self._pick(n, w))
        a = m.addAction("Déplacer à gauche", lambda: self._move(n, -1))
        a.setEnabled(n > 0)
        b = m.addAction("Déplacer à droite", lambda: self._move(n, 1))
        b.setEnabled(n < len(self._value) - 1)
        m.addSeparator()
        m.addAction("Retirer", lambda: self._remove(n))
        m.exec(w.mapToGlobal(QPoint(0, w.height())))

    def _pick(self, n: int | None, anchor: QWidget) -> None:
        pk = RunePicker(self.env.runes(), self)
        pk.picked.connect(lambda ch: self._apply(n, ch))
        pk.popup_at(anchor)

    def _apply(self, n: int | None, ch: str) -> None:
        v = list(self._value)
        if n is None:
            v.append(ch)
        else:
            v[n] = ch
        self._commit(v)

    def _move(self, n: int, d: int) -> None:
        v = list(self._value)
        v[n], v[n + d] = v[n + d], v[n]
        self._commit(v)

    def _remove(self, n: int) -> None:
        v = list(self._value)
        del v[n]
        self._commit(v)

    def _commit(self, v: list[str]) -> None:
        self._value = v
        self._flags = {}
        self._rebuild()
        self.changed.emit(list(v))

    def set_value(self, v: Any) -> None:
        nv = [x for x in v if isinstance(x, str)] if isinstance(v, list) else []
        if nv != self._value:
            self._value = nv
            self._rebuild()

    def apply_issues(self, idx: IssueIndex, path: tuple) -> None:
        flags = {i: idx.worst(path + (i,)) for i in range(len(self._value))}
        flags = {k: s for k, s in flags.items() if s is not None}
        if flags != self._flags:
            self._flags = flags
            self._rebuild()
        self.set_issue(idx.worst(path) if idx.at(path) else None, "\n".join(i.message for i in idx.at(path)))


# ════════════════════════════════════════════════════════════════════════════
#  Enregistrement imbriqué, champ optionnel, formulaire
# ════════════════════════════════════════════════════════════════════════════
class RecordField(FieldWidget):
    def __init__(self, f: Field, env: Env, parent: QWidget | None = None):
        super().__init__(f, env, parent)
        self._value: dict = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.form = FormPanel(f.fields, env)
        self.form.changed.connect(self._sub)
        lay.addWidget(self.form)

    def _sub(self, key: str, v: Any) -> None:
        self._value[key] = v
        self.changed.emit(dict(self._value))

    def set_value(self, v: Any) -> None:
        self._value = dict(v) if isinstance(v, dict) else {}
        self.form.set_record(self._value)

    def refresh_choices(self) -> None:
        self.form.refresh_choices()

    def apply_issues(self, idx: IssueIndex, path: tuple) -> None:
        self.form.apply_issues(idx, path)


class OptionalField(FieldWidget):
    """Champ facultatif : case à cocher + éditeur ; décoché = clé absente du JSON."""

    def __init__(self, f: Field, env: Env, inner: FieldWidget, parent: QWidget | None = None):
        super().__init__(f, env, parent)
        self.inner = inner
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        self.check = QCheckBox("Définir")
        self.check.toggled.connect(self._toggle)
        lay.addWidget(self.check)
        lay.addWidget(inner, 1)
        inner.changed.connect(self.changed.emit)
        inner.setEnabled(False)

    def _toggle(self, on: bool) -> None:
        if self._loading:
            return
        self.inner.setEnabled(on)
        if on:
            v = default_for(self.f, self.env.doc.data)
            self.inner.set_value(v)
            self.changed.emit(v)
        else:
            self.changed.emit(MISSING)

    def set_value(self, v: Any) -> None:
        present = v is not MISSING and v is not None
        self._loading = True
        self.check.setChecked(present)
        self.inner.setEnabled(present)
        self._loading = False
        if present:
            self.inner.set_value(v)

    def refresh_choices(self) -> None:
        self.inner.refresh_choices()

    def apply_issues(self, idx: IssueIndex, path: tuple) -> None:
        self.inner.apply_issues(idx, path)


def build_field(f: Field, env: Env) -> FieldWidget:
    k = f.kind
    if k == "text":
        w: FieldWidget = TextAreaField(f, env)
    elif k in ("enum", "ref") or (k == "rune" and f.ref):
        w = ChoiceField(f, env)
    elif k in ("float", "int"):
        w = NumberField(f, env)
    elif k == "strlist":
        w = StrListField(f, env, compact=True)
    elif k == "runelist":
        w = RuneListField(f, env)
    elif k == "record":
        w = RecordField(f, env)
    else:
        w = LineField(f, env)
    return w if f.required else OptionalField(f, env, w)


class FormPanel(QWidget):
    """Formulaire généré depuis une liste de Field."""
    changed = Signal(str, object)

    def __init__(self, fields: tuple, env: Env, parent: QWidget | None = None, label_width: int = 150):
        super().__init__(parent)
        self.fields = fields
        self.env = env
        self.widgets: dict[str, FieldWidget] = {}
        g = QGridLayout(self)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(16)
        g.setVerticalSpacing(10)
        g.setColumnMinimumWidth(0, label_width)
        g.setColumnStretch(1, 1)
        for r, f in enumerate(fields):
            lab = QLabel(f.label)
            lab.setProperty("role", "field")
            lab.setFixedWidth(label_width)
            lab.setAlignment(Qt.AlignRight | Qt.AlignTop)
            w = build_field(f, env)
            w.changed.connect(lambda v, k=f.key: self.changed.emit(k, v))
            self.widgets[f.key] = w
            cell = QVBoxLayout()
            cell.setSpacing(3)
            cell.addWidget(w)
            if f.hint and f.kind not in ("record",):
                h = QLabel(f.hint)
                h.setProperty("role", "hint")
                h.setWordWrap(True)
                cell.addWidget(h)
            g.addWidget(lab, r, 0, Qt.AlignTop)
            g.addLayout(cell, r, 1)
        g.setRowStretch(len(fields), 1)

    def set_record(self, rec: Any) -> None:
        rec = rec if isinstance(rec, dict) else {}
        for f in self.fields:
            w = self.widgets[f.key]
            if f.key in rec:
                w.set_value(rec[f.key])
            else:
                w.set_value(default_for(f, self.env.doc.data) if f.required else MISSING)

    def set_field_value(self, key: str, v: Any) -> None:
        self.widgets[key].set_value(v)

    def refresh_choices(self) -> None:
        for w in self.widgets.values():
            w.refresh_choices()

    def apply_issues(self, idx: IssueIndex, base: tuple) -> None:
        for f in self.fields:
            self.widgets[f.key].apply_issues(idx, base + (f.key,))
