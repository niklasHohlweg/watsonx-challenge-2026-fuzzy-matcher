"""
step2_matching — Step 2 widget: run matching in a background thread, show progress
and a lightweight results preview.

Public interface consumed by MainWindow:
    .prepare(file_a, col_a, file_b, col_b)   — called before the widget is shown
    .results                                  — list[MatchResult] after completion
    .matching_done                            — bool
    signal matching_finished()               — emitted when the run completes
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.excel_reader import ExcelFile
from models.match_result import MatchResult, TIER_FILL_COLOURS, TIERS
from workers.match_worker import MatchWorker
from ui.styles import BTN_PRIMARY, BTN_SECONDARY, BTN_DANGER

# Colour for tier cells in the sample table (light palette)
_TIER_QT_COLOURS: dict[str, str] = {
    tier: f"#{colour}" for tier, colour in TIER_FILL_COLOURS.items()
}


class Step2Widget(QWidget):
    """Step 2: run matching, live progress bar, summary + sample preview."""

    matching_finished = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._results: list[MatchResult] = []
        self._thread: QThread | None = None
        self._worker: MatchWorker | None = None
        self.matching_done = False

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 16)
        root.setSpacing(16)

        # Step header
        hdr = QLabel("Step 2 — Run Matching")
        hdr.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        hdr.setStyleSheet("color: #1F4E79;")
        root.addWidget(hdr)

        sub = QLabel(
            "Click Run Matching to compare the two selected columns. "
            "Processing runs in the background — the UI stays responsive."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #57606a;")
        root.addWidget(sub)

        # Button row
        btn_row = QHBoxLayout()
        self._run_btn = QPushButton("▶  Run Matching")
        self._run_btn.setFixedHeight(36)
        self._run_btn.setMinimumWidth(150)
        self._run_btn.setStyleSheet(BTN_PRIMARY)
        self._cancel_btn = QPushButton("✕  Cancel")
        self._cancel_btn.setFixedHeight(36)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setStyleSheet(BTN_DANGER)
        btn_row.addWidget(self._run_btn)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # Progress bar
        pb_layout = QVBoxLayout()
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%p%")
        self._progress_label = QLabel("Waiting to start…")
        self._progress_label.setStyleSheet("color: #57606a; font-size: 11px;")
        pb_layout.addWidget(self._progress_bar)
        pb_layout.addWidget(self._progress_label)
        root.addLayout(pb_layout)

        # Summary stats panel
        self._stats_box = QGroupBox("Results Summary")
        stats_grid = QHBoxLayout(self._stats_box)
        self._stat_labels: dict[str, QLabel] = {}
        for tier in TIERS:
            col_box = QVBoxLayout()
            tier_lbl = QLabel(tier)
            tier_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tier_lbl.setStyleSheet(
                f"background-color: {_TIER_QT_COLOURS[tier]}; "
                "color: #1f2328; "
                "border: 1px solid rgba(0,0,0,0.12); "
                "border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 12px;"
            )
            value_lbl = QLabel("—")
            value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            value_lbl.setStyleSheet("color: #1f2328; background: transparent;")
            pct_lbl = QLabel("")
            pct_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pct_lbl.setStyleSheet("color: #57606a; font-size: 12px; background: transparent;")
            col_box.addWidget(tier_lbl)
            col_box.addWidget(value_lbl)
            col_box.addWidget(pct_lbl)
            stats_grid.addLayout(col_box)
            self._stat_labels[tier] = (value_lbl, pct_lbl)  # type: ignore[assignment]
        self._stats_box.setVisible(False)
        root.addWidget(self._stats_box)

        # Sample table
        self._sample_box = QGroupBox("Sample Matches (top 5 + borderline 5)")
        sample_layout = QVBoxLayout(self._sample_box)
        self._sample_table = QTableWidget(0, 4)
        self._sample_table.setHorizontalHeaderLabels(
            ["File 1 Name", "File 2 Name", "Score", "Tier"]
        )
        self._sample_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._sample_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._sample_table.setAlternatingRowColors(False)
        self._sample_table.verticalHeader().setVisible(False)
        sample_layout.addWidget(self._sample_table)
        self._sample_box.setVisible(False)
        root.addWidget(self._sample_box)
        root.addStretch()

        # Wire buttons
        self._run_btn.clicked.connect(self._start_matching)
        self._cancel_btn.clicked.connect(self._cancel_matching)

    # ------------------------------------------------------------------
    # Public API

    def prepare(
        self,
        file_a: ExcelFile,
        col_a: str,
        file_b: ExcelFile,
        col_b: str,
    ) -> None:
        """Store inputs; called by MainWindow before showing this step."""
        self._file_a = file_a
        self._col_a = col_a
        self._file_b = file_b
        self._col_b = col_b
        # Reset state so re-running works after Back navigation
        self.matching_done = False
        self._results = []
        self._run_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress_bar.setValue(0)
        self._progress_label.setText("Waiting to start…")
        self._stats_box.setVisible(False)
        self._sample_box.setVisible(False)
        self._sample_table.setRowCount(0)

    @property
    def results(self) -> list[MatchResult]:
        return self._results

    # ------------------------------------------------------------------
    # Matching lifecycle

    def _start_matching(self) -> None:
        self._run_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._progress_bar.setValue(0)
        self._progress_label.setText("Starting…")
        self._stats_box.setVisible(False)
        self._sample_box.setVisible(False)

        self._worker = MatchWorker(
            df_a=self._file_a.dataframe,
            col_a=self._col_a,
            df_b=self._file_b.dataframe,
            col_b=self._col_b,
        )
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)

        Qt_ = Qt.ConnectionType.QueuedConnection
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress, Qt_)
        self._worker.finished.connect(self._on_finished, Qt_)
        self._worker.error.connect(self._on_error, Qt_)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _cancel_matching(self) -> None:
        if self._worker:
            self._worker.cancel()
        self._cancel_btn.setEnabled(False)
        self._progress_label.setText("Cancelling…")

    def _on_progress(self, current: int, total: int) -> None:
        pct = int(current / total * 100) if total else 0
        self._progress_bar.setValue(pct)
        self._progress_label.setText(f"Processing row {current:,} of {total:,}…")

    def _on_finished(self, results: list[MatchResult]) -> None:
        self._results = results
        self.matching_done = True
        self._cancel_btn.setEnabled(False)
        self._progress_bar.setValue(100)
        self._progress_label.setText(f"Done — {len(results):,} rows processed.")
        self._populate_stats(results)
        self._populate_sample(results)
        self._stats_box.setVisible(True)
        self._sample_box.setVisible(True)
        self.matching_finished.emit()

    def _on_error(self, msg: str) -> None:
        self._cancel_btn.setEnabled(False)
        self._run_btn.setEnabled(True)
        self._progress_label.setText(f"Error: {msg}")

    # ------------------------------------------------------------------
    # Stats & sample helpers

    def _populate_stats(self, results: list[MatchResult]) -> None:
        total = len(results)
        counts: dict[str, int] = {t: 0 for t in TIERS}
        for r in results:
            counts[r.tier] += 1

        for tier in TIERS:
            cnt = counts[tier]
            pct = (cnt / total * 100) if total else 0.0
            value_lbl, pct_lbl = self._stat_labels[tier]  # type: ignore[misc]
            value_lbl.setText(f"{cnt:,}")
            pct_lbl.setText(f"{pct:.1f}%")

    def _populate_sample(self, results: list[MatchResult]) -> None:
        sorted_res = sorted(results, key=lambda r: r.combined_score, reverse=True)
        sample = sorted_res[:5] + sorted_res[-5:] if len(sorted_res) > 5 else sorted_res
        # Deduplicate while preserving order
        seen_ids = set()
        unique_sample = []
        for r in sample:
            rid = id(r)
            if rid not in seen_ids:
                seen_ids.add(rid)
                unique_sample.append(r)

        self._sample_table.setRowCount(len(unique_sample))
        for row, r in enumerate(unique_sample):
            items = [
                QTableWidgetItem(r.raw_a),
                QTableWidgetItem(r.raw_b),
                QTableWidgetItem(f"{r.combined_score:.4f}"),
                QTableWidgetItem(r.tier),
            ]
            colour = _TIER_QT_COLOURS.get(r.tier, "#ffffff")
            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setBackground(
                    __import__("PySide6.QtGui", fromlist=["QColor"]).QColor(colour)
                )
                self._sample_table.setItem(row, col, item)
