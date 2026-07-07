"""
Tests for core/excel_reader.py
"""
from __future__ import annotations

import io
import tempfile
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from core.excel_reader import ExcelFile, ExcelReadError, load_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_xlsx(data: dict[str, list], path: str) -> None:
    """Write a minimal xlsx file from a dict of {column: [values]}."""
    df = pd.DataFrame(data)
    df.to_excel(path, index=False, engine="openpyxl")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLoadFile:
    def test_normal_file(self, tmp_path):
        p = tmp_path / "test.xlsx"
        _write_xlsx({"Company": ["Acme", "Beta"], "Country": ["DE", "US"]}, str(p))
        ef = load_file(str(p))
        assert isinstance(ef, ExcelFile)
        assert ef.columns == ["Company", "Country"]
        assert len(ef.dataframe) == 2

    def test_blank_header_cells(self, tmp_path):
        """Unnamed columns should become 'Column N'."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Name", None, "Value"])
        ws.append(["Acme", "X", 1])
        p = tmp_path / "blank_headers.xlsx"
        wb.save(str(p))

        ef = load_file(str(p))
        assert ef.columns[1] == "Column 2"

    def test_non_excel_extension_raises(self, tmp_path):
        p = tmp_path / "data.csv"
        p.write_text("a,b\n1,2")
        with pytest.raises(ExcelReadError, match="Unsupported file type"):
            load_file(str(p))

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ExcelReadError, match="File not found"):
            load_file(str(tmp_path / "does_not_exist.xlsx"))

    def test_corrupted_file_raises(self, tmp_path):
        p = tmp_path / "corrupt.xlsx"
        p.write_bytes(b"this is not a valid xlsx file")
        with pytest.raises(ExcelReadError):
            load_file(str(p))

    def test_sheet_names_populated(self, tmp_path):
        p = tmp_path / "multi.xlsx"
        with pd.ExcelWriter(str(p), engine="openpyxl") as writer:
            pd.DataFrame({"A": [1]}).to_excel(writer, sheet_name="Sheet1", index=False)
            pd.DataFrame({"B": [2]}).to_excel(writer, sheet_name="Sheet2", index=False)
        ef = load_file(str(p))
        assert "Sheet1" in ef.sheet_names
        assert "Sheet2" in ef.sheet_names

    def test_duplicate_column_names_deduplicated(self, tmp_path):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Name", "Name", "Value"])
        ws.append(["A", "B", 1])
        p = tmp_path / "dupes.xlsx"
        wb.save(str(p))
        ef = load_file(str(p))
        # First "Name" stays, second gets suffix
        assert ef.columns[0] == "Name"
        assert ef.columns[1] != "Name"
