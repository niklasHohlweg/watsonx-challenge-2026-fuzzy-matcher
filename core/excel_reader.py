"""
excel_reader — load an Excel file into a pandas DataFrame and expose metadata.

Usage:
    from core.excel_reader import load_file, ExcelFile, ExcelReadError

    ef = load_file("/path/to/data.xlsx")
    print(ef.columns)   # ['Company Name', 'Country', ...]
    print(ef.dataframe) # full pandas DataFrame
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd


class ExcelReadError(Exception):
    """Raised when an Excel file cannot be loaded."""


@dataclass
class ExcelFile:
    """Container for a loaded Excel file's metadata and data."""

    path: str
    sheet_names: list[str]
    columns: list[str]       # sanitized column names
    dataframe: pd.DataFrame  # full data, first (or requested) sheet


def load_file(path: str, sheet_index: int = 0) -> ExcelFile:
    """
    Load *path* (xlsx/xls) and return an ExcelFile.

    Parameters
    ----------
    path:
        Absolute or relative path to the Excel file.
    sheet_index:
        Zero-based index of the sheet to load (default 0).

    Raises
    ------
    ExcelReadError
        On any problem reading the file (wrong type, corrupt, missing sheet).
    """
    p = Path(path)

    if p.suffix.lower() not in {".xlsx", ".xls", ".xlsm"}:
        raise ExcelReadError(
            f"Unsupported file type '{p.suffix}'. Please select an .xlsx or .xls file."
        )

    if not p.exists():
        raise ExcelReadError(f"File not found: {path}")

    try:
        # Read sheet names first so we can validate sheet_index
        xl = pd.ExcelFile(path, engine="openpyxl")
        sheet_names: list[str] = xl.sheet_names

        if sheet_index >= len(sheet_names):
            raise ExcelReadError(
                f"Sheet index {sheet_index} out of range "
                f"(file has {len(sheet_names)} sheet(s))."
            )

        df = xl.parse(sheet_names[sheet_index], header=0)
    except ExcelReadError:
        raise
    except Exception as exc:
        raise ExcelReadError(
            f"Could not read '{p.name}': {exc}"
        ) from exc

    # Sanitize column names -----------------------------------------------
    sanitized: list[str] = []
    seen: dict[str, int] = {}
    for i, col in enumerate(df.columns):
        name = str(col).strip()
        if not name or name.lower().startswith("unnamed"):
            name = f"Column {i + 1}"
        # deduplicate
        if name in seen:
            seen[name] += 1
            name = f"{name} ({seen[name]})"
        else:
            seen[name] = 0
        sanitized.append(name)

    df.columns = sanitized

    return ExcelFile(
        path=str(path),
        sheet_names=sheet_names,
        columns=sanitized,
        dataframe=df,
    )
