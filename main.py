"""
main.py — Application entry point.

Usage:
    python main.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the package root is on sys.path when run directly (e.g. `python main.py`)
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow

# ---------------------------------------------------------------------------
# Application-wide stylesheet — enforces a light theme regardless of the OS
# dark-mode setting so every widget has readable contrast.
# ---------------------------------------------------------------------------
_APP_STYLESHEET = """
/* ── Global ───────────────────────────────────────────────────────────── */
QWidget {
    background-color: #ffffff;
    color: #1f2328;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

/* ── Main window chrome ───────────────────────────────────────────────── */
QMainWindow, QStackedWidget {
    background-color: #ffffff;
}

QMenuBar {
    background-color: #f7f8fa;
    color: #1f2328;
    border-bottom: 1px solid #e5e7eb;
}
QMenuBar::item:selected {
    background-color: #e5e7eb;
}
QMenu {
    background-color: #ffffff;
    color: #1f2328;
    border: 1px solid #d0d7de;
}
QMenu::item:selected {
    background-color: #dbeafe;
    color: #1e3a5f;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #f0f6ff;
    color: #1f4e79;
    border: 1px solid #3b82d4;
    border-radius: 5px;
    padding: 5px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #dbeafe;
    border-color: #1f4e79;
}
QPushButton:pressed {
    background-color: #bfdbfe;
}
QPushButton:disabled {
    background-color: #f0f0f0;
    color: #9ca3af;
    border-color: #d1d5db;
}

/* Primary action button (Export / Run Matching) — accent blue */
QPushButton#primary {
    background-color: #1f4e79;
    color: #ffffff;
    border: 1px solid #1a3f63;
}
QPushButton#primary:hover {
    background-color: #1a3f63;
}
QPushButton#primary:pressed {
    background-color: #163354;
}
QPushButton#primary:disabled {
    background-color: #9ca3af;
    border-color: #9ca3af;
}

/* ── Text inputs ──────────────────────────────────────────────────────── */
QLineEdit {
    background-color: #ffffff;
    color: #1f2328;
    border: 1px solid #d0d7de;
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: #bfdbfe;
}
QLineEdit:read-only {
    background-color: #f7f8fa;
    color: #57606a;
}
QLineEdit:focus {
    border-color: #3b82d4;
}

/* ── Combo boxes ──────────────────────────────────────────────────────── */
QComboBox {
    background-color: #ffffff;
    color: #1f2328;
    border: 1px solid #d0d7de;
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 28px;
}
QComboBox:disabled {
    background-color: #f0f0f0;
    color: #9ca3af;
}
QComboBox:focus {
    border-color: #3b82d4;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #1f2328;
    border: 1px solid #d0d7de;
    selection-background-color: #dbeafe;
    selection-color: #1e3a5f;
    outline: none;
}

/* ── Group boxes ──────────────────────────────────────────────────────── */
QGroupBox {
    background-color: #f7f8fa;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: 600;
    color: #1f2328;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #1f4e79;
    font-weight: 700;
    font-size: 12px;
}

/* ── List widgets (column checkboxes) ────────────────────────────────── */
QListWidget {
    background-color: #ffffff;
    color: #1f2328;
    border: 1px solid #d0d7de;
    border-radius: 4px;
    alternate-background-color: #f7f8fa;
    outline: none;
}
QListWidget::item {
    padding: 3px 6px;
    color: #1f2328;
}
QListWidget::item:selected {
    background-color: #dbeafe;
    color: #1e3a5f;
}
QListWidget::item:hover {
    background-color: #f0f6ff;
}
QListWidget::item:disabled {
    color: #6b7280;
    background-color: #f7f8fa;
}

/* ── Progress bar ─────────────────────────────────────────────────────── */
QProgressBar {
    background-color: #e5e7eb;
    border: 1px solid #d0d7de;
    border-radius: 4px;
    color: #1f2328;
    text-align: center;
    height: 18px;
}
QProgressBar::chunk {
    background-color: #3b82d4;
    border-radius: 3px;
}

/* ── Table widget (sample matches) ───────────────────────────────────── */
QTableWidget {
    background-color: #ffffff;
    color: #1f2328;
    gridline-color: #e5e7eb;
    border: 1px solid #d0d7de;
    border-radius: 4px;
    alternate-background-color: #f7f8fa;
    outline: none;
}
QTableWidget::item {
    padding: 4px 8px;
    color: #1f2328;
}
QHeaderView::section {
    background-color: #1f4e79;
    color: #ffffff;
    font-weight: 700;
    padding: 5px 8px;
    border: none;
    border-right: 1px solid #163354;
}
QHeaderView {
    background-color: #1f4e79;
}

/* ── Scroll bars ──────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #f7f8fa;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #c0c9d4;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #9ca3af;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #f7f8fa;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #c0c9d4;
    border-radius: 5px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background: #9ca3af;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Tool tips ────────────────────────────────────────────────────────── */
QToolTip {
    background-color: #1f2328;
    color: #ffffff;
    border: none;
    border-radius: 3px;
    padding: 4px 8px;
    font-size: 12px;
}

/* ── Message boxes ────────────────────────────────────────────────────── */
QMessageBox {
    background-color: #ffffff;
    color: #1f2328;
}
QMessageBox QLabel {
    color: #1f2328;
}

/* ── Dialog boxes ─────────────────────────────────────────────────────── */
QDialog {
    background-color: #ffffff;
    color: #1f2328;
}
"""


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("FuzzyMatcher")
    app.setOrganizationName("FuzzyMatcher")
    app.setApplicationVersion("1.0.0")

    # Force Fusion style so the stylesheet overrides apply uniformly on all
    # platforms (especially macOS, which otherwise applies a dark-mode palette
    # that fights with light inline colour values).
    app.setStyle("Fusion")

    # Override the palette to a clean light base so widgets that don't pick
    # up the stylesheet still render with light backgrounds.
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#1f2328"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f7f8fa"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#1f2328"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#f0f6ff"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#1f4e79"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#dbeafe"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#1e3a5f"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9ca3af"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#9ca3af"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#9ca3af"))
    app.setPalette(palette)

    app.setStyleSheet(_APP_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
