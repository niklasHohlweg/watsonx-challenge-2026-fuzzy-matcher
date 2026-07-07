"""
step1_input — Step 1 widget: file pickers and comparison-column dropdowns.

Signals emitted:
    step1_ready()  — both files loaded and comparison columns selected
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.excel_reader import ExcelFile, ExcelReadError, load_file
from ui.styles import BTN_PRIMARY, BTN_SECONDARY

_SETTINGS_KEY_LAST_DIR = "FuzzyMatcher/LastDir"


class _FilePanel(QWidget):
    """One side-panel for a single file (Browse + column selector)."""

    file_loaded = Signal(object)   # ExcelFile
    load_error = Signal(str)

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._excel_file: ExcelFile | None = None

        # --- Layout ---------------------------------------------------------
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        title = QLabel(label)
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        root.addWidget(title)

        # Path row
        path_row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setReadOnly(True)
        self._path_edit.setPlaceholderText("No file selected…")
        self._path_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._browse_btn = QPushButton("Browse…")
        self._browse_btn.setFixedWidth(110)
        self._browse_btn.setStyleSheet(BTN_SECONDARY)
        self._browse_btn.clicked.connect(self._browse)
        path_row.addWidget(self._path_edit)
        path_row.addWidget(self._browse_btn)
        root.addLayout(path_row)

        # Row count
        self._row_count_label = QLabel("")
        self._row_count_label.setStyleSheet("color: #57606a; font-size: 11px;")
        root.addWidget(self._row_count_label)

        # Column selector
        col_label = QLabel("Compare column:")
        self._col_combo = QComboBox()
        self._col_combo.setEnabled(False)
        self._col_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        root.addWidget(col_label)
        root.addWidget(self._col_combo)

        # Inline error label
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #cc0000; font-size: 11px;")
        self._error_label.setWordWrap(True)
        root.addWidget(self._error_label)

        root.addStretch()

    # ------------------------------------------------------------------

    def _browse(self) -> None:
        from PySide6.QtCore import QSettings
        settings = QSettings("FuzzyMatcher", "FuzzyMatcher")
        last_dir = settings.value(_SETTINGS_KEY_LAST_DIR, "")

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel file",
            last_dir,
            "Excel files (*.xlsx *.xls *.xlsm);;All files (*)",
        )
        if not path:
            return

        settings.setValue(_SETTINGS_KEY_LAST_DIR, str(Path(path).parent))

        self._error_label.setText("")
        try:
            ef = load_file(path)
        except ExcelReadError as exc:
            self._error_label.setText(f"⚠  {exc}")
            self._path_edit.setText("")
            self._col_combo.clear()
            self._col_combo.setEnabled(False)
            self._row_count_label.setText("")
            self._excel_file = None
            self.load_error.emit(str(exc))
            return

        self._excel_file = ef
        self._path_edit.setText(path)
        self._row_count_label.setText(f"Loaded: {len(ef.dataframe):,} rows")

        self._col_combo.clear()
        self._col_combo.addItems(ef.columns)
        self._col_combo.setEnabled(True)

        self.file_loaded.emit(ef)

    # ------------------------------------------------------------------
    # Public helpers

    @property
    def excel_file(self) -> ExcelFile | None:
        return self._excel_file

    @property
    def selected_column(self) -> str | None:
        if self._col_combo.isEnabled() and self._col_combo.count():
            return self._col_combo.currentText()
        return None

    def reset(self) -> None:
        """Clear the panel back to its initial state."""
        self._path_edit.clear()
        self._row_count_label.clear()
        self._col_combo.clear()
        self._col_combo.setEnabled(False)
        self._error_label.clear()
        self._excel_file = None


class Step1Widget(QWidget):
    """
    Full Step 1 view: two side-by-side file panels.

    Emits step1_ready() when both panels have a loaded file + selected column.
    """

    step1_ready = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 16)
        root.setSpacing(16)

        # Step header
        hdr = QLabel("Step 1 — Select Files & Comparison Columns")
        hdr.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        hdr.setStyleSheet("color: #1F4E79;")
        root.addWidget(hdr)

        sub = QLabel(
            "Choose one Excel file per side, then pick the column that contains the "
            "company or account name you want to match."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #57606a;")
        root.addWidget(sub)

        # Two panels side by side
        panels_row = QHBoxLayout()
        panels_row.setSpacing(24)

        self._panel_a = _FilePanel("File 1", self)
        self._panel_b = _FilePanel("File 2", self)

        box_a = QGroupBox()
        box_a.setLayout(QVBoxLayout())
        box_a.layout().addWidget(self._panel_a)

        box_b = QGroupBox()
        box_b.setLayout(QVBoxLayout())
        box_b.layout().addWidget(self._panel_b)

        panels_row.addWidget(box_a)
        panels_row.addWidget(box_b)
        root.addLayout(panels_row)
        root.addStretch()

        # Wire readiness checks
        for panel in (self._panel_a, self._panel_b):
            panel.file_loaded.connect(self._check_ready)
            panel._col_combo.currentIndexChanged.connect(self._check_ready)

    # ------------------------------------------------------------------

    def _check_ready(self) -> None:
        if (
            self._panel_a.excel_file is not None
            and self._panel_b.excel_file is not None
            and self._panel_a.selected_column is not None
            and self._panel_b.selected_column is not None
        ):
            self.step1_ready.emit()

    # ------------------------------------------------------------------
    # Public accessors used by MainWindow

    @property
    def file_a(self) -> ExcelFile | None:
        return self._panel_a.excel_file

    @property
    def file_b(self) -> ExcelFile | None:
        return self._panel_b.excel_file

    @property
    def col_a(self) -> str | None:
        return self._panel_a.selected_column

    @property
    def col_b(self) -> str | None:
        return self._panel_b.selected_column

    def is_ready(self) -> bool:
        return (
            self._panel_a.excel_file is not None
            and self._panel_b.excel_file is not None
            and self._panel_a.selected_column is not None
            and self._panel_b.selected_column is not None
        )
