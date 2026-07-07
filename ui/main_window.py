"""
main_window — MainWindow, AppState, and top-level wizard navigation.

Architecture:
    MainWindow
     ├── QStackedWidget
     │    ├── Step1Widget  (index 0)
     │    ├── Step2Widget  (index 1)
     │    └── Step3Widget  (index 2)
     └── bottom navigation bar: Back / Next buttons

AppState is a simple dataclass shared (by reference) with all step widgets.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.excel_reader import ExcelFile
from models.match_result import MatchResult
from ui.step1_input import Step1Widget
from ui.step2_matching import Step2Widget
from ui.step3_output import Step3Widget
from ui.styles import BTN_PRIMARY, BTN_SECONDARY

APP_VERSION = "1.0.0"


@dataclass
class AppState:
    """Shared mutable state passed between wizard steps."""

    file_a: Optional[ExcelFile] = None
    file_b: Optional[ExcelFile] = None
    col_a: str = ""
    col_b: str = ""
    results: list[MatchResult] = field(default_factory=list)
    extra_cols_a: list[str] = field(default_factory=list)
    extra_cols_b: list[str] = field(default_factory=list)


_STEP_TITLES = [
    "Step 1 of 3 — File Selection",
    "Step 2 of 3 — Run Matching",
    "Step 3 of 3 — Export",
]


class MainWindow(QMainWindow):
    """Top-level application window hosting the three-step wizard."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Fuzzy Account Matcher")
        self.setMinimumSize(960, 680)

        self._state = AppState()

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Step indicator label
        self._step_label = QLabel(_STEP_TITLES[0])
        self._step_label.setFont(QFont("Segoe UI", 9))
        self._step_label.setStyleSheet(
            "background: #1F4E79; color: #ffffff; padding: 6px 16px;"
        )
        main_layout.addWidget(self._step_label)

        # Stacked widget
        self._stack = QStackedWidget()
        self._step1 = Step1Widget()
        self._step2 = Step2Widget()
        self._step3 = Step3Widget()
        self._stack.addWidget(self._step1)   # index 0
        self._stack.addWidget(self._step2)   # index 1
        self._stack.addWidget(self._step3)   # index 2
        main_layout.addWidget(self._stack, stretch=1)

        # Bottom navigation bar — use QFrame so the border-top renders reliably
        nav_bar = QFrame()
        nav_bar.setFrameShape(QFrame.Shape.NoFrame)
        nav_bar.setStyleSheet(
            "QFrame { background-color: #f7f8fa; border-top: 1px solid #e5e7eb; }"
        )
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(16, 10, 16, 10)

        self._back_btn = QPushButton("← Back")
        self._back_btn.setFixedHeight(34)
        self._back_btn.setMinimumWidth(100)
        self._back_btn.setEnabled(False)
        self._back_btn.setStyleSheet(BTN_SECONDARY)

        self._next_btn = QPushButton("Next →")
        self._next_btn.setFixedHeight(34)
        self._next_btn.setMinimumWidth(100)
        self._next_btn.setEnabled(False)
        self._next_btn.setStyleSheet(BTN_PRIMARY)

        nav_layout.addWidget(self._back_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self._next_btn)
        main_layout.addWidget(nav_bar)

        # Signals
        self._back_btn.clicked.connect(self._go_back)
        self._next_btn.clicked.connect(self._go_next)

        # Step 1: enable Next as soon as both files are ready
        self._step1.step1_ready.connect(lambda: self._next_btn.setEnabled(True))

        # Step 2: enable Next when matching finishes
        self._step2.matching_finished.connect(lambda: self._next_btn.setEnabled(True))

        # Menu bar
        self._build_menu()

        # Try to load app icon
        self._load_icon()

    # ------------------------------------------------------------------
    # Navigation

    def _go_next(self) -> None:
        idx = self._stack.currentIndex()

        if idx == 0:
            # Leaving Step 1 → capture state, prepare Step 2
            self._state.file_a = self._step1.file_a
            self._state.file_b = self._step1.file_b
            self._state.col_a = self._step1.col_a or ""
            self._state.col_b = self._step1.col_b or ""
            self._step2.prepare(
                self._state.file_a,
                self._state.col_a,
                self._state.file_b,
                self._state.col_b,
            )

        elif idx == 1:
            # Leaving Step 2 → capture results, prepare Step 3
            self._state.results = self._step2.results
            self._step3.prepare(
                self._state.file_a,
                self._state.col_a,
                self._state.file_b,
                self._state.col_b,
                self._state.results,
            )

        new_idx = idx + 1
        self._stack.setCurrentIndex(new_idx)
        self._step_label.setText(_STEP_TITLES[new_idx])
        self._back_btn.setEnabled(True)
        # Next is disabled until the new step signals readiness
        if new_idx == 1:
            # Next on step 2 only enabled after matching completes
            self._next_btn.setEnabled(self._step2.matching_done)
        elif new_idx == 2:
            # Step 3 has no Next button
            self._next_btn.setEnabled(False)
            self._next_btn.setVisible(False)

    def _go_back(self) -> None:
        idx = self._stack.currentIndex()
        new_idx = idx - 1
        self._stack.setCurrentIndex(new_idx)
        self._step_label.setText(_STEP_TITLES[new_idx])
        self._back_btn.setEnabled(new_idx > 0)
        self._next_btn.setVisible(True)

        if new_idx == 0:
            self._next_btn.setEnabled(self._step1.is_ready())
        elif new_idx == 1:
            self._next_btn.setEnabled(self._step2.matching_done)

    # ------------------------------------------------------------------
    # Menu

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")
        restart_act = QAction("&Restart (clear all)", self)
        restart_act.setShortcut("Ctrl+R")
        restart_act.triggered.connect(self._restart)
        file_menu.addAction(restart_act)
        file_menu.addSeparator()
        quit_act = QAction("&Quit", self)
        quit_act.setShortcut("Ctrl+Q")
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        about_act = QAction("&About", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    def _restart(self) -> None:
        self._state = AppState()
        self._stack.setCurrentIndex(0)
        self._step_label.setText(_STEP_TITLES[0])
        self._back_btn.setEnabled(False)
        self._next_btn.setEnabled(False)
        self._next_btn.setVisible(True)

    def _show_about(self) -> None:
        dlg = QMessageBox(self)
        dlg.setWindowTitle("About Fuzzy Account Matcher")
        dlg.setText(
            f"<b>Fuzzy Account Matcher</b> v{APP_VERSION}<br><br>"
            "Cross-platform desktop tool for fuzzy-matching company and account names "
            "between two Excel files.<br><br>"
            "Algorithm: Jaccard token similarity (40%) + rapidfuzz ratio (35%) "
            "+ partial ratio (25%)<br><br>"
            "Built with Python, PySide6, pandas, openpyxl, and rapidfuzz."
        )
        dlg.setIcon(QMessageBox.Icon.Information)
        dlg.exec()

    # ------------------------------------------------------------------

    def _load_icon(self) -> None:
        import sys
        from pathlib import Path

        base = Path(__file__).parent.parent
        if sys.platform == "win32":
            icon_path = base / "resources" / "icons" / "app.ico"
        else:
            icon_path = base / "resources" / "icons" / "app.icns"

        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
