"""
vauv_theme — identité visuelle « crépuscule CRT » de l'éditeur.

Palette : indigo nocturne, cyan phosphore (action / focus), rose vif (sélection),
ambre (avertissement). Angles coupés (chanfreins) pour les panneaux, runes en
grand format, un seul moment animé : le décodage du sceau à l'ouverture.

Pour une typographie plus marquée, déposez des fichiers .ttf dans un dossier
« fonts » à côté du script : Orbitron, Rajdhani, Share Tech Mono sont détectées.
"""
from __future__ import annotations

import math
import random
import tempfile
from pathlib import Path
from string import Template

from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QFontDatabase, QLinearGradient, QPainter, QPainterPath,
                           QPen, QPixmap, QPolygonF, QRadialGradient)
from PySide6.QtWidgets import QFrame, QStyledItemDelegate, QStyle, QWidget

from vauv_core import AXIS_LABELS, PROFILE_AXES, Severity

# ════════════════════════════════════════════════════════════════════════════
#  Palette
# ════════════════════════════════════════════════════════════════════════════
C = dict(
    bg0="#0b0919", bg1="#12102a", bg2="#1a1738", bg3="#26204f",
    line="#312a5c", line2="#4b4189",
    text="#e4dfff", muted="#9d96d1", dim="#645c9c",
    cyan="#5ef2d6", cyan_hi="#9bfbea", rose="#ff5c9d", amber="#ffbf5e",
    red="#ff4d6a", info="#7fb2ff", violet="#a281ff",
)
SEV_COLOR = {Severity.ERROR: C["red"], Severity.WARNING: C["amber"], Severity.INFO: C["info"]}

UI_FONTS = ["Rajdhani", "Exo 2", "Bahnschrift", "Segoe UI", "Noto Sans", "Ubuntu", "Cantarell", "DejaVu Sans"]
MONO_FONTS = ["Share Tech Mono", "JetBrains Mono", "Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono"]
DISPLAY_FONTS = ["Orbitron", "Audiowide", "Bahnschrift", "Rajdhani", "Segoe UI Semibold", "DejaVu Sans"]
RUNE_FONTS = ["Noto Sans Runic", "Segoe UI Historic", "Segoe UI Symbol", "DejaVu Sans", "FreeSerif",
              "Junicode", "Arial Unicode MS"]

FONTS: dict[str, str] = {}


def _pick(cands: list[str], fams: set[str]) -> str:
    for c in cands:
        if c in fams:
            return c
    return cands[-1]


def setup_fonts(base_dir: Path) -> None:
    """Charge les polices locales éventuelles puis choisit les familles disponibles."""
    fdir = base_dir / "fonts"
    if fdir.is_dir():
        for f in list(fdir.glob("*.ttf")) + list(fdir.glob("*.otf")):
            QFontDatabase.addApplicationFont(str(f))
    fams = set(QFontDatabase.families())
    FONTS["ui"] = _pick(UI_FONTS, fams)
    FONTS["mono"] = _pick(MONO_FONTS, fams)
    FONTS["display"] = _pick(DISPLAY_FONTS, fams)
    FONTS["rune"] = _pick(RUNE_FONTS, fams)


def font(kind: str, px: int, bold: bool = False) -> QFont:
    f = QFont(FONTS.get(kind, "sans-serif"))
    f.setPixelSize(px)
    f.setBold(bold)
    return f


def rune_font(px: int) -> QFont:
    f = QFont()
    f.setFamilies([FONTS.get("rune", "DejaVu Sans")] + RUNE_FONTS)
    f.setPixelSize(px)
    return f


def qc(name: str, alpha: int | None = None) -> QColor:
    c = QColor(C.get(name, name))
    if alpha is not None:
        c.setAlpha(alpha)
    return c


# ════════════════════════════════════════════════════════════════════════════
#  Feuille de style
# ════════════════════════════════════════════════════════════════════════════
def arrow_png(color: str, up: bool = False) -> str:
    d = Path(tempfile.gettempdir()) / "vauv_editor_assets"
    d.mkdir(exist_ok=True)
    out = d / f"arrow_{'up' if up else 'down'}_{color.strip('#')}.png"
    if not out.exists():
        pm = QPixmap(10, 6)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(color))
        p.setPen(Qt.NoPen)
        pts = [QPointF(0.5, 5.5), QPointF(9.5, 5.5), QPointF(5, 0.5)] if up else \
              [QPointF(0.5, 0.5), QPointF(9.5, 0.5), QPointF(5, 5.5)]
        p.drawPolygon(QPolygonF(pts))
        p.end()
        pm.save(str(out))
    return out.as_posix()


_QSS = Template(r"""
* { font-family: "$ui"; font-size: 14px; color: $text; outline: 0; }
QMainWindow, QDialog, QMessageBox, QInputDialog { background: $bg0; }
QWidget#page, QWidget#central, QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }
QToolTip { background: $bg3; color: $text; border: 1px solid $cyan; padding: 5px 8px; }
QLabel { background: transparent; }
QLabel[role="muted"] { color: $muted; }
QLabel[role="hint"] { color: $dim; font-size: 12px; }
QLabel[role="title"] { font-family: "$display"; font-size: 20px; letter-spacing: 1px; }
QLabel[role="h2"] { font-family: "$display"; font-size: 15px; color: $cyan; }
QLabel[role="mono"] { font-family: "$mono"; color: $muted; }
QLabel[role="field"] { color: $muted; font-size: 13px; padding-top: 6px; }
QLabel[role="empty"] { color: $dim; font-size: 15px; }

QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: $bg2; border: 1px solid $line; border-radius: 0; padding: 5px 8px;
    font-family: "$mono"; font-size: 13px; selection-background-color: $rose; selection-color: #14091f; }
QLineEdit:hover, QPlainTextEdit:hover, QComboBox:hover, QDoubleSpinBox:hover { border-color: $line2; }
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: $cyan; background: $bg3; }
QLineEdit:read-only { color: $muted; }
QWidget#field[issue="error"] QLineEdit, QWidget#field[issue="error"] QPlainTextEdit,
QWidget#field[issue="error"] QComboBox, QWidget#field[issue="error"] QDoubleSpinBox,
QWidget#field[issue="error"] QListWidget { border-color: $red; }
QWidget#field[issue="warning"] QLineEdit, QWidget#field[issue="warning"] QPlainTextEdit,
QWidget#field[issue="warning"] QComboBox, QWidget#field[issue="warning"] QDoubleSpinBox,
QWidget#field[issue="warning"] QListWidget { border-color: $amber; }
QWidget#field[issue="info"] QLineEdit, QWidget#field[issue="info"] QPlainTextEdit,
QWidget#field[issue="info"] QComboBox { border-color: $info; }

QComboBox { padding-right: 26px; }
QComboBox::drop-down { border: none; width: 24px; subcontrol-origin: padding; subcontrol-position: center right; }
QComboBox::down-arrow { image: url($arrow_down); width: 10px; height: 6px; }
QComboBox QAbstractItemView { background: $bg2; border: 1px solid $cyan; selection-background-color: $bg3;
    selection-color: $cyan; padding: 2px; font-family: "$mono"; }

QPushButton, QToolButton { background: transparent; border: 1px solid $line2; padding: 6px 14px; color: $text; }
QPushButton:hover, QToolButton:hover { border-color: $cyan; color: $cyan_hi; background: $bg2; }
QPushButton:pressed, QToolButton:pressed { background: $bg3; }
QPushButton:disabled, QToolButton:disabled { color: $dim; border-color: $line; }
QPushButton:focus { border-color: $cyan; }
QPushButton[primary="true"] { background: $cyan; border-color: $cyan; color: #06141a; font-weight: 600; }
QPushButton[primary="true"]:hover { background: $cyan_hi; color: #06141a; }
QPushButton[danger="true"]:hover { border-color: $red; color: $red; }
QToolButton[tiny="true"] { padding: 3px 8px; font-family: "$mono"; }
QToolButton[chip="true"] { border: 1px solid $line2; padding: 2px 8px; background: $bg2; }
QToolButton[chip="true"]:hover { border-color: $rose; color: $rose; }
QToolButton::menu-indicator { image: none; width: 0; }
QToolButton[ghost="true"] { border-color: transparent; padding: 6px 10px; }
QToolButton[ghost="true"]:hover { border-color: $line2; }
QToolButton[stat="true"] { border: 1px solid $line; padding: 3px 10px; font-family: "$mono"; font-size: 12px; }
QToolButton[stat="true"]:checked { background: $bg3; border-color: $line2; }

QListWidget, QTreeWidget, QTreeView { background: $bg1; border: 1px solid $line; alternate-background-color: $bg1;
    show-decoration-selected: 1; }
QListWidget::item { padding: 5px 8px; border-left: 2px solid transparent; }
QListWidget::item:hover, QTreeWidget::item:hover { background: $bg2; }
QListWidget::item:selected, QTreeWidget::item:selected { background: $bg3; border-left: 2px solid $rose; color: $text; }
QListWidget[mono="true"] { font-family: "$mono"; font-size: 13px; }
QListWidget QLineEdit { border: 1px solid $cyan; padding: 2px 6px; }
QHeaderView::section { background: $bg2; color: $muted; border: none; border-bottom: 1px solid $line; padding: 5px 8px; }

QScrollBar:vertical { background: transparent; width: 11px; margin: 0; }
QScrollBar::handle:vertical { background: $line2; min-height: 36px; margin: 2px 2px; }
QScrollBar::handle:vertical:hover { background: $cyan; }
QScrollBar:horizontal { background: transparent; height: 11px; margin: 0; }
QScrollBar::handle:horizontal { background: $line2; min-width: 36px; margin: 2px 2px; }
QScrollBar::handle:horizontal:hover { background: $cyan; }
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page { background: none; border: none; width: 0; height: 0; }

QSlider::groove:horizontal { height: 4px; background: $bg3; }
QSlider::sub-page:horizontal { background: $cyan; }
QSlider::handle:horizontal { background: $bg0; border: 2px solid $cyan; width: 10px; margin: -6px 0; }
QSlider::handle:horizontal:hover { border-color: $rose; background: $rose; }

QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid $line2; background: $bg2; }
QCheckBox::indicator:checked { background: $cyan; border-color: $cyan; }

QSplitter::handle { background: $bg0; }
QSplitter::handle:horizontal { width: 6px; }
QSplitter::handle:vertical { height: 6px; }
QSplitter::handle:hover { background: $line; }

QMenuBar { background: $bg0; border-bottom: 1px solid $line; padding: 2px 6px; }
QMenuBar::item { padding: 5px 10px; background: transparent; }
QMenuBar::item:selected { background: $bg3; color: $cyan; }
QMenu { background: $bg1; border: 1px solid $line2; padding: 4px; }
QMenu::item { padding: 6px 26px 6px 14px; }
QMenu::item:selected { background: $bg3; color: $cyan; }
QMenu::item:disabled { color: $dim; }
QMenu::separator { height: 1px; background: $line; margin: 4px 8px; }

QStatusBar { background: $bg0; border-top: 1px solid $line; color: $muted; }
QStatusBar::item { border: none; }
QDockWidget { color: $muted; }
QDockWidget::title { background: $bg1; padding: 6px 10px; border-top: 1px solid $line; }
QMessageBox QLabel { color: $text; }
QProgressBar { background: $bg2; border: none; height: 4px; }
QProgressBar::chunk { background: $cyan; }
QGroupBox { border: 1px solid $line; margin-top: 10px; padding: 10px 8px 6px 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; color: $muted; }
""")


def stylesheet() -> str:
    return _QSS.substitute(
        ui=FONTS["ui"], mono=FONTS["mono"], display=FONTS["display"],
        arrow_down=arrow_png(C["cyan"]), **C,
    )


# ════════════════════════════════════════════════════════════════════════════
#  Panneau à angles coupés
# ════════════════════════════════════════════════════════════════════════════
def chamfer_path(r: QRectF, c: float, cuts: str = "tr,bl") -> QPainterPath:
    p = QPainterPath()
    tl, tr, br, bl = ("tl" in cuts), ("tr" in cuts), ("br" in cuts), ("bl" in cuts)
    p.moveTo(r.left() + (c if tl else 0), r.top())
    p.lineTo(r.right() - (c if tr else 0), r.top())
    if tr:
        p.lineTo(r.right(), r.top() + c)
    p.lineTo(r.right(), r.bottom() - (c if br else 0))
    if br:
        p.lineTo(r.right() - c, r.bottom())
    p.lineTo(r.left() + (c if bl else 0), r.bottom())
    if bl:
        p.lineTo(r.left(), r.bottom() - c)
    p.lineTo(r.left(), r.top() + (c if tl else 0))
    if tl:
        p.lineTo(r.left() + c, r.top())
    p.closeSubpath()
    return p


class HudFrame(QFrame):
    """Panneau : fond bg1, contour fin, deux angles coupés et deux repères lumineux."""

    def __init__(self, parent: QWidget | None = None, accent: str = "cyan", chamfer: int = 12,
                 cuts: str = "tr,bl", fill: str = "bg1"):
        super().__init__(parent)
        self._accent, self._c, self._cuts, self._fill = accent, chamfer, cuts, fill
        self.setContentsMargins(0, 0, 0, 0)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = chamfer_path(r, self._c, self._cuts)
        p.fillPath(path, qc(self._fill))
        p.setPen(QPen(qc("line"), 1))
        p.drawPath(path)
        p.setPen(QPen(qc(self._accent), 2))
        L = 22
        if "tr" in self._cuts:
            p.drawLine(QPointF(r.right() - self._c - L, r.top()), QPointF(r.right() - self._c, r.top()))
            p.drawLine(QPointF(r.right(), r.top() + self._c), QPointF(r.right(), r.top() + self._c + L))
        if "bl" in self._cuts:
            p.drawLine(QPointF(r.left() + self._c, r.bottom()), QPointF(r.left() + self._c + L, r.bottom()))
            p.drawLine(QPointF(r.left(), r.bottom() - self._c), QPointF(r.left(), r.bottom() - self._c - L))


# ════════════════════════════════════════════════════════════════════════════
#  Marque et sceau animé (seul mouvement spontané de l'interface)
# ════════════════════════════════════════════════════════════════════════════
class GlowTitle(QWidget):
    def __init__(self, text: str, sub: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._text, self._sub = text, sub
        self.setFixedHeight(54)
        self.setMinimumWidth(250)

    def sizeHint(self) -> QSize:
        return QSize(280, 54)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        f = font("display", 26, True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 3)
        path = QPainterPath()
        path.addText(2, 32, f, self._text)
        g = QLinearGradient(0, 0, path.boundingRect().width() + 4, 0)
        g.setColorAt(0, qc("cyan"))
        g.setColorAt(1, qc("rose"))
        for w, a in ((9, 22), (5, 40), (2.5, 70)):
            pen = QPen(qc("cyan", a), w)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.drawPath(path)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(g))
        p.drawPath(path)
        p.setPen(qc("muted"))
        p.setFont(font("mono", 12))
        p.drawText(3, 49, self._sub)


class SigilStrip(QWidget):
    """Rangée de runes qui « se décodent » une fois à l'ouverture."""
    NOISE = "ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈᛉᛊᛏᛒᛖᛗᛚᛜᛞᛟ▒░▓<>/\\|01"

    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._target = list(text)
        self._shown = list(text)
        self._lock = [0] * len(text)
        self._frame = 0
        self._timer = QTimer(self)
        self._timer.setInterval(42)
        self._timer.timeout.connect(self._tick)
        self.setFixedSize(len(text) * 17 + 8, 30)

    def play(self) -> None:
        rnd = random.Random()
        self._frame = 0
        self._lock = [int(6 + i * 1.15 + rnd.random() * 7) for i in range(len(self._target))]
        self._timer.start()

    def _tick(self) -> None:
        self._frame += 1
        done = True
        for i, t in enumerate(self._target):
            if self._frame >= self._lock[i]:
                self._shown[i] = t
            else:
                self._shown[i] = random.choice(self.NOISE)
                done = False
        self.update()
        if done:
            self._timer.stop()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setFont(rune_font(18))
        for i, ch in enumerate(self._shown):
            locked = self._timer.isActive() is False or self._frame >= self._lock[i]
            p.setPen(qc("cyan" if locked else "rose", 235 if locked else 150))
            p.drawText(QRectF(4 + i * 17, 0, 17, self.height()), Qt.AlignCenter, ch)


# ════════════════════════════════════════════════════════════════════════════
#  Voile CRT : lignes de balayage + vignette (mis en cache, insensible à la souris)
# ════════════════════════════════════════════════════════════════════════════
class ScanlineOverlay(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self._cache: QPixmap | None = None
        parent.installEventFilter(self)
        self.setGeometry(parent.rect())

    def eventFilter(self, obj, ev) -> bool:
        if obj is self.parent() and ev.type() in (QEvent.Resize, QEvent.Show):
            self.setGeometry(self.parent().rect())
            self.raise_()
        return False

    def paintEvent(self, _e) -> None:
        if self._cache is None or self._cache.size() != self.size():
            pm = QPixmap(self.size())
            pm.fill(Qt.transparent)
            q = QPainter(pm)
            q.setPen(QPen(QColor(0, 0, 0, 34), 1))
            for y in range(0, self.height(), 3):
                q.drawLine(0, y, self.width(), y)
            g = QRadialGradient(self.rect().center(), max(self.width(), self.height()) * 0.72)
            g.setColorAt(0.0, QColor(0, 0, 0, 0))
            g.setColorAt(0.7, QColor(0, 0, 0, 0))
            g.setColorAt(1.0, QColor(4, 2, 14, 120))
            q.fillRect(self.rect(), g)
            q.end()
            self._cache = pm
        QPainter(self).drawPixmap(0, 0, self._cache)


# ════════════════════════════════════════════════════════════════════════════
#  Navigation latérale
# ════════════════════════════════════════════════════════════════════════════
ROLE_KIND = Qt.UserRole + 1     # "group" | "page"
ROLE_CODE = Qt.UserRole + 2     # "S3", "—" …
ROLE_BADGE = Qt.UserRole + 3    # (Severity, count) ou None


class NavDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index) -> QSize:
        return QSize(220, 30 if index.data(ROLE_KIND) == "page" else 34)

    def paint(self, p: QPainter, option, index) -> None:
        kind = index.data(ROLE_KIND)
        r = QRectF(option.rect)
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        if kind == "group":
            p.setPen(qc("dim"))
            p.setFont(font("ui", 12, True))
            p.drawText(r.adjusted(14, 10, 0, 0), Qt.AlignLeft | Qt.AlignVCenter, index.data(Qt.DisplayRole))
            p.setPen(QPen(qc("line"), 1))
            tw = p.fontMetrics().horizontalAdvance(index.data(Qt.DisplayRole))
            p.drawLine(QPointF(r.left() + 22 + tw, r.center().y() + 5), QPointF(r.right() - 12, r.center().y() + 5))
            p.restore()
            return
        sel = bool(option.state & QStyle.State_Selected)
        hov = bool(option.state & QStyle.State_MouseOver)
        if sel:
            p.fillRect(r, qc("bg3"))
            p.fillRect(QRectF(r.left(), r.top(), 3, r.height()), qc("rose"))
        elif hov:
            p.fillRect(r, qc("bg2"))
        code = index.data(ROLE_CODE) or ""
        p.setFont(font("mono", 12))
        p.setPen(qc("rose" if sel else "dim"))
        p.drawText(QRectF(r.left() + 14, r.top(), 34, r.height()), Qt.AlignLeft | Qt.AlignVCenter, code)
        p.setFont(font("ui", 14, sel))
        p.setPen(qc("text" if sel else "muted"))
        p.drawText(QRectF(r.left() + 50, r.top(), r.width() - 90, r.height()), Qt.AlignLeft | Qt.AlignVCenter,
                   index.data(Qt.DisplayRole))
        badge = index.data(ROLE_BADGE)
        if badge:
            sev, n = badge
            col = SEV_COLOR[sev]
            br = QRectF(r.right() - 38, r.center().y() - 9, 28, 18)
            p.setPen(QPen(QColor(col), 1))
            p.setBrush(QColor(col).darker(400))
            p.drawRoundedRect(br, 3, 3)
            p.setFont(font("mono", 11, True))
            p.setPen(QColor(col))
            p.drawText(br, Qt.AlignCenter, str(n if n < 100 else "99+"))
        p.restore()


# ════════════════════════════════════════════════════════════════════════════
#  Radar des profils (les sommets se déplacent à la souris)
# ════════════════════════════════════════════════════════════════════════════
class RadarChart(QWidget):
    valueChanged = Signal(str, float)

    def __init__(self, vmax: float = 2.0, step: float = 0.05, parent: QWidget | None = None):
        super().__init__(parent)
        self.vmax, self.step = vmax, step
        self.axes = PROFILE_AXES
        self._vals: dict[str, float] = {a: 0.0 for a in self.axes}
        self._drag: str | None = None
        self._hover: str | None = None
        self.setMinimumSize(280, 280)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)

    def set_values(self, rec: dict) -> None:
        for a in self.axes:
            v = rec.get(a)
            self._vals[a] = float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0
        self.update()

    def _geom(self) -> tuple[QPointF, float]:
        c = QPointF(self.width() / 2, self.height() / 2)
        return c, max(40.0, min(self.width(), self.height()) / 2 - 42)

    def _dir(self, i: int) -> QPointF:
        th = -math.pi / 2 + i * 2 * math.pi / len(self.axes)
        return QPointF(math.cos(th), math.sin(th))

    def _pt(self, i: int, v: float) -> QPointF:
        c, R = self._geom()
        d = self._dir(i)
        k = R * max(0.0, min(v, self.vmax)) / self.vmax
        return QPointF(c.x() + d.x() * k, c.y() + d.y() * k)

    def _axis_at(self, pos: QPointF) -> int:
        c, _ = self._geom()
        ang = math.atan2(pos.y() - c.y(), pos.x() - c.x()) + math.pi / 2
        n = len(self.axes)
        return int(round((ang % (2 * math.pi)) / (2 * math.pi / n))) % n

    def _apply(self, pos: QPointF, axis_i: int) -> None:
        c, R = self._geom()
        d = self._dir(axis_i)
        proj = (pos.x() - c.x()) * d.x() + (pos.y() - c.y()) * d.y()
        v = max(0.0, min(self.vmax, proj / R * self.vmax))
        v = round(round(v / self.step) * self.step, 4)
        a = self.axes[axis_i]
        if abs(self._vals[a] - v) > 1e-9:
            self._vals[a] = v
            self.valueChanged.emit(a, v)
            self.update()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            i = self._axis_at(e.position())
            self._drag = self.axes[i]
            self._apply(e.position(), i)

    def mouseMoveEvent(self, e) -> None:
        i = self._axis_at(e.position())
        if self._drag:
            self._apply(e.position(), self.axes.index(self._drag))
        elif self._hover != self.axes[i]:
            self._hover = self.axes[i]
            self.update()

    def mouseReleaseEvent(self, _e) -> None:
        self._drag = None
        self.update()

    def leaveEvent(self, _e) -> None:
        self._hover = None
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c, R = self._geom()
        n = len(self.axes)
        # anneaux
        for k in range(1, 5):
            poly = QPolygonF([self._pt(i, self.vmax * k / 4) for i in range(n)])
            p.setPen(QPen(qc("line2" if k == 2 else "line"), 1, Qt.SolidLine if k == 2 else Qt.DotLine))
            p.setBrush(Qt.NoBrush)
            p.drawPolygon(poly)
            p.setPen(qc("dim"))
            p.setFont(font("mono", 10))
            p.drawText(QPointF(c.x() + 4, c.y() - R * k / 4 + 11), f"{self.vmax * k / 4:g}")
        p.setPen(QPen(qc("line"), 1))
        for i in range(n):
            p.drawLine(c, self._pt(i, self.vmax))
        # surface
        poly = QPolygonF([self._pt(i, self._vals[a]) for i, a in enumerate(self.axes)])
        g = QRadialGradient(c, R)
        g.setColorAt(0, qc("cyan", 30))
        g.setColorAt(1, qc("rose", 90))
        for w, al in ((7, 25), (3.5, 60)):
            p.setPen(QPen(qc("cyan", al), w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawPolygon(poly)
        p.setBrush(QBrush(g))
        p.setPen(QPen(qc("cyan"), 1.6))
        p.drawPolygon(poly)
        # sommets + étiquettes
        for i, a in enumerate(self.axes):
            pt = self._pt(i, self._vals[a])
            active = a in (self._drag, self._hover)
            p.setPen(QPen(qc("amber" if active else "cyan_hi"), 1.5))
            p.setBrush(qc("amber" if active else "bg0"))
            s = 5 if active else 4
            p.drawPolygon(QPolygonF([QPointF(pt.x(), pt.y() - s), QPointF(pt.x() + s, pt.y()),
                                     QPointF(pt.x(), pt.y() + s), QPointF(pt.x() - s, pt.y())]))
            lp = self._pt(i, self.vmax * 1.0)
            d = self._dir(i)
            tx, ty = lp.x() + d.x() * 22, lp.y() + d.y() * 18
            p.setFont(font("mono", 12, True))
            p.setPen(qc("amber" if active else "text"))
            p.drawText(QRectF(tx - 24, ty - 10, 48, 14), Qt.AlignCenter, a)
            p.setFont(font("mono", 11))
            p.setPen(qc("amber" if active else "muted"))
            p.drawText(QRectF(tx - 30, ty + 3, 60, 14), Qt.AlignCenter, f"{self._vals[a]:.2f}")
