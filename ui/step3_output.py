"""
step3_output — Step 3 widget: column selection and Excel export.

Public interface consumed by MainWindow:
    .prepare(file_a, col_a, file_b, col_b, results) — call before showing
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.excel_reader import ExcelFile
from core.exporter import build_workbook
from models.match_result import MatchResult, TIERS, TIER_EXACT, TIER_GOOD, TIER_POSSIBLE, TIER_NO_MATCH
from ui.styles import BTN_PRIMARY, BTN_SECONDARY

_SETTINGS_KEY_LAST_EXPORT = "FuzzyMatcher/LastExportDir"


class _ExportWorker(__import__("PySide6.QtCore", fromlist=["QObject"]).QObject):
    """Runs build_workbook() off the main thread."""

    finished = Signal()
    error = Signal(str)

    def __init__(self, results, df_a, extra_a, df_b, extra_b, path, active_tiers, deduplicate, parent=None):
        super().__init__(parent)
        self._args = (results, df_a, extra_a, df_b, extra_b, path)
        self._active_tiers = active_tiers
        self._deduplicate = deduplicate

    def run(self):
        try:
            build_workbook(*self._args, active_tiers=self._active_tiers, deduplicate=self._deduplicate)
            self.finished.emit()
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


class _ColumnPanel(QWidget):
    """Scrollable checkbox list with Select All / Select None for one file."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        btn_row = QHBoxLayout()
        all_btn = QPushButton("Select All")
        none_btn = QPushButton("Select None")
        all_btn.setFixedHeight(28)
        none_btn.setFixedHeight(28)
        all_btn.setStyleSheet(BTN_SECONDARY)
        none_btn.setStyleSheet(BTN_SECONDARY)
        btn_row.addWidget(all_btn)
        btn_row.addWidget(none_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self._list = QListWidget()
        self._list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self._list)

        all_btn.clicked.connect(self._select_all)
        none_btn.clicked.connect(self._select_none)

        self._fixed_col: str | None = None

    def populate(self, columns: list[str], fixed_col: str | None = None) -> None:
        """Fill the list; *fixed_col* is pre-checked and read-only."""
        self._fixed_col = fixed_col
        self._list.clear()
        for col in columns:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if col == fixed_col:
                item.setCheckState(Qt.CheckState.Checked)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setToolTip("This column is always included (used for matching).")
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            self._list.addItem(item)

    def checked_columns(self) -> list[str]:
        """Return list of checked column names (excludes fixed col, added separately)."""
        result = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.checkState() == Qt.CheckState.Checked and item.text() != self._fixed_col:
                result.append(item.text())
        return result

    def _select_all(self) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.text() != self._fixed_col:
                item.setCheckState(Qt.CheckState.Checked)

    def _select_none(self) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.text() != self._fixed_col:
                item.setCheckState(Qt.CheckState.Unchecked)


class Step3Widget(QWidget):
    """Step 3: column selection and export."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._results: list[MatchResult] = []
        self._file_a: ExcelFile | None = None
        self._file_b: ExcelFile | None = None
        self._col_a: str | None = None
        self._col_b: str | None = None
        self._export_thread: QThread | None = None
        self._export_worker: _ExportWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 16)
        root.setSpacing(16)

        hdr = QLabel("Step 3 — Choose Output Columns & Export")
        hdr.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        hdr.setStyleSheet("color: #1F4E79;")
        root.addWidget(hdr)

        sub = QLabel(
            "Select which additional columns from each file should appear in the output. "
            "The comparison columns are always included. Click Export when ready."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #57606a;")
        root.addWidget(sub)

        # Fixed columns note
        fixed_note = QLabel(
            "Output fixed columns (always included):  "
            "<b>#</b> | <b>File1_Name</b> | <b>File2_Name</b> | <b>Score</b> | <b>Tier</b>"
        )
        fixed_note.setStyleSheet(
            "background-color: #eef2ff; color: #1f2328; "
            "border: 1px solid #c7d2fe; border-radius: 4px; "
            "padding: 7px 12px; font-size: 12px;"
        )
        root.addWidget(fixed_note)

        # Tier filter — which tiers appear in the Matched sheet on open
        tier_box = QGroupBox("Matched sheet — show tiers on open")
        tier_layout = QHBoxLayout(tier_box)
        tier_layout.setSpacing(20)

        self._tier_checks: dict[str, QCheckBox] = {}
        tier_colours = {
            TIER_EXACT:    "#C6EFCE",
            TIER_GOOD:     "#FFEB9C",
            TIER_POSSIBLE: "#FFCCBB",
            TIER_NO_MATCH: "#FFC7CE",
        }
        for tier in TIERS:
            cb = QCheckBox(tier)
            cb.setChecked(tier == TIER_EXACT)   # default: Exact only
            cb.setStyleSheet(
                f"QCheckBox {{ font-weight: 600; color: #1f2328; }}"
                f"QCheckBox::indicator:checked {{ background-color: {tier_colours[tier]}; "
                f"border: 2px solid #555; border-radius: 3px; }}"
                f"QCheckBox::indicator:unchecked {{ background-color: #ffffff; "
                f"border: 2px solid #9ca3af; border-radius: 3px; }}"
            )
            self._tier_checks[tier] = cb
            tier_layout.addWidget(cb)

        tier_layout.addStretch()
        root.addWidget(tier_box)

        # Deduplication option
        dedup_box = QGroupBox("Duplicate handling")
        dedup_layout = QHBoxLayout(dedup_box)
        dedup_layout.setSpacing(12)

        self._dedup_check = QCheckBox(
            "Remove File B duplicates — keep only the best match per File B row"
        )
        self._dedup_check.setChecked(False)
        self._dedup_check.setStyleSheet(
            "QCheckBox { font-weight: 600; color: #1f2328; }"
            "QCheckBox::indicator:checked { background-color: #dbeafe; "
            "border: 2px solid #3b82d4; border-radius: 3px; }"
            "QCheckBox::indicator:unchecked { background-color: #ffffff; "
            "border: 2px solid #9ca3af; border-radius: 3px; }"
        )
        dedup_hint = QLabel(
            "When the same File B entry is the best match for multiple File A rows, "
            "only the highest-scoring pair is kept. The rest are moved to Unmatched."
        )
        dedup_hint.setWordWrap(True)
        dedup_hint.setStyleSheet("color: #57606a; font-size: 11px;")

        dedup_col = QVBoxLayout()
        dedup_col.setSpacing(4)
        dedup_col.addWidget(self._dedup_check)
        dedup_col.addWidget(dedup_hint)
        dedup_layout.addLayout(dedup_col)
        dedup_layout.addStretch()
        root.addWidget(dedup_box)

        # Two column panels
        panels_row = QHBoxLayout()
        panels_row.setSpacing(20)

        self._panel_a = _ColumnPanel("File 1")
        box_a = QGroupBox("File 1 — additional columns")
        box_a.setLayout(QVBoxLayout())
        box_a.layout().addWidget(self._panel_a)

        self._panel_b = _ColumnPanel("File 2")
        box_b = QGroupBox("File 2 — additional columns")
        box_b.setLayout(QVBoxLayout())
        box_b.layout().addWidget(self._panel_b)

        panels_row.addWidget(box_a)
        panels_row.addWidget(box_b)
        root.addLayout(panels_row)

        # Export button
        export_row = QHBoxLayout()
        export_row.addStretch()
        self._export_btn = QPushButton("Export Excel…")
        self._export_btn.setFixedHeight(38)
        self._export_btn.setMinimumWidth(180)
        self._export_btn.setStyleSheet(BTN_PRIMARY)
        export_row.addWidget(self._export_btn)
        root.addLayout(export_row)

        self._export_btn.clicked.connect(self._do_export)

    # ------------------------------------------------------------------
    # Public API

    def prepare(
        self,
        file_a: ExcelFile,
        col_a: str,
        file_b: ExcelFile,
        col_b: str,
        results: list[MatchResult],
    ) -> None:
        self._file_a = file_a
        self._col_a = col_a
        self._file_b = file_b
        self._col_b = col_b
        self._results = results

        self._panel_a.populate(file_a.columns, fixed_col=col_a)
        self._panel_b.populate(file_b.columns, fixed_col=col_b)

    # ------------------------------------------------------------------
    # Export

    def _do_export(self) -> None:
        from PySide6.QtCore import QSettings
        settings = QSettings("FuzzyMatcher", "FuzzyMatcher")
        last_dir = settings.value(_SETTINGS_KEY_LAST_EXPORT, "")

        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save output Excel file",
            str(Path(last_dir) / "fuzzy_match_results.xlsx"),
            "Excel files (*.xlsx)",
        )
        if not out_path:
            return

        if not out_path.endswith(".xlsx"):
            out_path += ".xlsx"

        settings.setValue(_SETTINGS_KEY_LAST_EXPORT, str(Path(out_path).parent))

        # Collect selected columns, active tiers, and dedup flag
        extra_a = self._panel_a.checked_columns()
        extra_b = self._panel_b.checked_columns()
        active_tiers = [t for t, cb in self._tier_checks.items() if cb.isChecked()]
        if not active_tiers:
            active_tiers = list(TIERS)  # nothing checked → show all
        deduplicate = self._dedup_check.isChecked()

        # Build progress dialog
        progress = QProgressDialog("Exporting Excel file…", None, 0, 0, self)
        progress.setWindowTitle("Exporting…")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(300)

        self._export_worker = _ExportWorker(
            self._results,
            self._file_a.dataframe,
            extra_a,
            self._file_b.dataframe,
            extra_b,
            out_path,
            active_tiers,
            deduplicate,
        )
        self._export_thread = QThread(self)
        self._export_worker.moveToThread(self._export_thread)

        Qt_ = Qt.ConnectionType.QueuedConnection
        self._export_thread.started.connect(self._export_worker.run)
        # Worker → thread: quit the thread when work finishes/errors
        self._export_worker.finished.connect(self._export_thread.quit)
        self._export_worker.error.connect(self._export_thread.quit)
        # Thread → main thread (QueuedConnection): UI must only be touched here
        self._export_thread.finished.connect(progress.close, Qt_)
        self._export_thread.finished.connect(
            lambda: self._export_success(out_path), Qt_
        )
        # Worker error goes via queued slot so NSWindow is created on main thread
        self._export_worker.error.connect(self._export_error, Qt_)
        # Cleanup after the thread stops
        self._export_worker.finished.connect(self._export_worker.deleteLater)
        self._export_thread.finished.connect(self._export_thread.deleteLater)

        self._export_thread.start()
        progress.exec()

    def _export_success(self, path: str) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        msg = QMessageBox(self)
        msg.setWindowTitle("Export complete")
        msg.setText(f"File saved successfully:\n{path}")
        msg.setIcon(QMessageBox.Icon.Information)
        open_btn = msg.addButton("Open file", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("Close", QMessageBox.ButtonRole.AcceptRole)
        msg.exec()

        if msg.clickedButton() == open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _export_error(self, msg: str) -> None:
        err = QMessageBox(self)
        err.setWindowTitle("Export failed")
        err.setText(f"Could not save the file:\n\n{msg}\n\nIf the file is open in Excel, please close it and try again.")
        err.setIcon(QMessageBox.Icon.Critical)
        err.exec()
