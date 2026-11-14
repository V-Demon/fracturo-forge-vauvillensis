#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vauv_editor — Point d'entrée principal de l'éditeur de lexiques Vauvillensis.
Assemble le Document, les Pages, la Navigation et la boucle de validation.
"""
from __future__ import annotations
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QStackedWidget,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QStatusBar, QVBoxLayout, QWidget, QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence

import vauv_core as core
from vauv_theme import setup_fonts, stylesheet, C, font, qc, NavDelegate, ROLE_KIND, ROLE_CODE, ROLE_BADGE, Severity, SEV_COLOR
from vauv_widgets import Env, confirm
from vauv_pages import (
    OverviewPage, MetaPage, RecordPage, ProfilesPage,
    EnginesPage, ListsPage, RawJsonPage, page_header,
)
from vauv_preview import PreviewPage


class MainWindow(QMainWindow):
    def __init__(self, file_path: Path | None = None):
        super().__init__()
        self.setWindowTitle("Vauvillensis Lexicon Editor v3.1")
        self.setMinimumSize(1100, 700)

        # 1. Initialisation des polices et du style
        setup_fonts(Path(__file__).parent)
        self.setStyleSheet(stylesheet())

        # 2. Document et Environnement
        try:
            self.doc = core.Document.open(file_path) if file_path else core.Document(core.skeleton())
        except core.LexiconError as e:
            QMessageBox.critical(self, "Erreur de chargement", str(e))
            sys.exit(1)

        self.env = Env(self.doc)
        self.doc.subscribe(self.on_doc_changed)

        # 3. Interface Principale
        self.setup_ui()
        self.setup_menu()

        # 4. Premier chargement et validation
        self.build_navigation()
        self.on_doc_changed(None)  # Déclenche la validation initiale

        # 5. Ouvrir la page d'aperçu par défaut
        self.navigate(())

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # -- Navigation Latérale --
        self.nav = QListWidget()
        self.nav.setFixedWidth(240)
        self.nav.setItemDelegate(NavDelegate(self.nav))
        self.nav.currentItemChanged.connect(self.on_nav_changed)
        self.nav.setStyleSheet(
            f"QListWidget {{ background: {C['bg1']}; border-right: 1px solid {C['line']}; }}"
        )
        splitter.addWidget(self.nav)

        # -- Zone de Pages --
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background: {C['bg0']};")
        splitter.addWidget(self.stack)

        splitter.setSizes([240, 860])

        # -- Barre de statut --
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_path = QLabel("Non enregistré")
        self.lbl_path.setProperty("role", "mono")
        self.status_bar.addPermanentWidget(self.lbl_path)
        self.chips = QLabel("● 0   ● 0   ● 0")
        self.chips.setStyleSheet(f"color: {C['muted']}; font-family: monospace;")
        self.status_bar.addWidget(self.chips)

    def setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Fichier")
        act_new = QAction("Nouveau (Squelette)", self)
        act_new.setShortcut(QKeySequence.New)
        act_new.triggered.connect(lambda: self.new_document("skeleton"))
        file_menu.addAction(act_new)

        act_open = QAction("Ouvrir...", self)
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self.open_file)
        file_menu.addAction(act_open)

        act_save = QAction("Enregistrer", self)
        act_save.setShortcut(QKeySequence.Save)
        act_save.triggered.connect(self.save_file)
        file_menu.addAction(act_save)

        act_saveas = QAction("Enregistrer sous...", self)
        act_saveas.setShortcut(QKeySequence.SaveAs)
        act_saveas.triggered.connect(lambda: self.save_file(True))
        file_menu.addAction(act_saveas)

        file_menu.addSeparator()
        act_quit = QAction("Quitter", self)
        act_quit.setShortcut(QKeySequence.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        edit_menu = menubar.addMenu("Édition")
        act_undo = QAction("Annuler", self)
        act_undo.setShortcut(QKeySequence.Undo)
        act_undo.triggered.connect(lambda: self.doc.undo())
        edit_menu.addAction(act_undo)

        act_redo = QAction("Rétablir", self)
        act_redo.setShortcut(QKeySequence.Redo)
        act_redo.triggered.connect(lambda: self.doc.redo())
        edit_menu.addAction(act_redo)

    def build_navigation(self):
        self.nav.clear()
        self.pages = {}

        def add_group(title):
            it = QListWidgetItem(title)
            it.setData(ROLE_KIND, "group")
            it.setFlags(Qt.NoItemFlags)
            self.nav.addItem(it)

        def add_page(page):
            self.pages[page.prefix] = page
            self.stack.addWidget(page)
            page.navigate = self.navigate
            page.say = self.show_message

            it = QListWidgetItem(page.title)
            it.setData(ROLE_KIND, "page")
            it.setData(ROLE_CODE, page.code)
            it.setData(Qt.UserRole, page.prefix)
            self.nav.addItem(it)

        add_group("Général")
        add_page(OverviewPage(self.env))
        add_page(MetaPage(self.env))
        add_page(PreviewPage(self.env))  # ← LE PONT FORGE LIVE

        add_group("Registres")
        add_page(RecordPage(self.env, core.RECORDSETS["futhark"], "ᚠ", "Futhark ancien"))
        add_page(RecordPage(self.env, core.RECORDSETS["bindrunes"], "ᛝ", "Bindrunes"))
        add_page(RecordPage(self.env, core.RECORDSETS["rituals"], "◈", "Rituels"))
        add_page(RecordPage(self.env, core.RECORDSETS["synergies"], "✦", "Synergies"))
        add_page(RecordPage(self.env, core.RECORDSETS["eras"], "⏳", "Époques"))

        add_group("Strates")
        add_page(ListsPage(self.env, "Syntaxe & Glitch", "▓", (core.S1,)))
        add_page(ListsPage(self.env, "Concepts MTT", "◇", (core.S2,)))
        add_page(ListsPage(self.env, "Incantations", "⌘", (core.S4,)))
        add_page(ListsPage(self.env, "Motifs FracturoScript", "ᛝ", (core.S5,)))
        add_page(
            ListsPage(
                self.env, "Fractales Métamorphiques", "∞", (core.S7,),
                open_keys=True, noun="catégorie",
            )
        )

        add_group("Configuration")
        add_page(ProfilesPage(self.env, core.RECORDSETS["profiles"], "⚖️", "Profils de pondération"))
        add_page(EnginesPage(self.env, core.RECORDSETS["engines"], "🎛️", "Moteurs de génération"))
        add_page(RawJsonPage(self.env))

    def on_nav_changed(self, current, previous):
        if current is None or current.data(ROLE_KIND) != "page":
            return
        prefix = current.data(Qt.UserRole)
        if prefix in self.pages:
            self.stack.setCurrentWidget(self.pages[prefix])

    def navigate(self, prefix: tuple):
        for p_prefix, page in self.pages.items():
            if prefix == p_prefix or (len(prefix) > 0 and prefix[0] == p_prefix[0] if p_prefix else not prefix):
                for i in range(self.nav.count()):
                    it = self.nav.item(i)
                    if it.data(Qt.UserRole) == p_prefix:
                        self.nav.setCurrentItem(it)
                        page.focus_path(prefix)
                        return

    def on_doc_changed(self, origin):
        # 1. Valider
        issues = self.doc.validate()
        self.env.issues = core.IssueIndex(issues)

        # 2. Mettre à jour l'UI
        e, w, i = self.env.issues.total()
        self.chips.setText(f"● {e}   ● {w}   ● {i}")
        self.chips.setStyleSheet(
            f"color: {SEV_COLOR[Severity.ERROR] if e > 0 else SEV_COLOR[Severity.WARNING] if w > 0 else C['muted']}; "
            f"font-family: monospace;"
        )

        self.lbl_path.setText(f"{self.doc.name} {'*' if self.doc.dirty else ''}")
        self.setWindowTitle(
            f"Vauvillensis Editor v3.1 - {self.doc.name} {'*' if self.doc.dirty else ''}"
        )

        # 3. Propager aux pages
        for page in self.pages.values():
            page.apply_issues(self.env.issues)

        # 4. Mettre à jour les badges de navigation
        for i in range(self.nav.count()):
            it = self.nav.item(i)
            if it.data(ROLE_KIND) == "page":
                prefix = it.data(Qt.UserRole)
                worst = self.env.issues.worst(prefix)
                counts = self.env.issues.counts(prefix)
                total = sum(counts)
                if worst is not None and total > 0:
                    it.setData(ROLE_BADGE, (worst, total))
                else:
                    it.setData(ROLE_BADGE, None)

    def show_message(self, msg: str):
        self.status_bar.showMessage(msg, 3000)

    def new_document(self, template_id: str):
        if self.doc.dirty and not confirm(self, "Nouveau document", "Le document actuel n'est pas enregistré. Continuer ?"):
            return
        new_data = core.build_document_template(template_id, self.doc.data)
        self.doc.replace_all(new_data, label="Nouveau document")
        self.doc.path = None
        self.doc.saved_version = -1
        self.on_doc_changed(None)

    def open_file(self):
        if self.doc.dirty and not confirm(self, "Ouvrir", "Le document actuel n'est pas enregistré. Continuer ?"):
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir un lexique", str(Path.home()), "JSON Files (*.json)"
        )
        if path:
            try:
                self.doc = core.Document.open(path)
                self.doc.subscribe(self.on_doc_changed)
                self.env.doc = self.doc
                self.on_doc_changed(None)
            except core.LexiconError as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def save_file(self, save_as=False):
        try:
            if save_as or self.doc.path is None:
                path, _ = QFileDialog.getSaveFileName(
                    self, "Enregistrer sous", str(Path.home() / "lexique_v3.1.json"), "JSON Files (*.json)"
                )
                if not path:
                    return
                self.doc.save(path)
            else:
                self.doc.save()
            self.show_message("Document enregistré avec succès.")
        except core.LexiconError as e:
            QMessageBox.critical(self, "Erreur d'écriture", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Vauvillensis Editor")

    file_to_open = Path(sys.argv[1]) if len(sys.argv) > 1 else None

    window = MainWindow(file_to_open)
    window.show()
    sys.exit(app.exec())
