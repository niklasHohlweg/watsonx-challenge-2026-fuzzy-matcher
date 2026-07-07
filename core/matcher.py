"""
matcher — orchestrates row-by-row matching between two DataFrames.

Public API:
    run(df_a, col_a, df_b, col_b, threshold=0.60, progress_cb=None)
        → list[MatchResult]

For each row in df_a, all rows in df_b are scored; the best-scoring match
is kept if it is at or above *threshold*.  Rows without a qualifying match
receive a MatchResult with tier=TIER_NO_MATCH and index_b=None.

Performance note:
    The current O(n×m) nested loop is adequate for datasets up to ~5 000×5 000.
    For larger datasets, replace the inner loop with rapidfuzz.process.cdist
    (vectorised C-backed distance matrix) or add a TF-IDF cosine pre-filter
    to reduce candidate pairs before full scoring.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Optional

import pandas as pd

from core.scorer import score
from models.match_result import MatchResult, TIER_NO_MATCH

# Emit a progress callback at most every N rows to limit signal overhead
_PROGRESS_INTERVAL = 50


def run(
    df_a: pd.DataFrame,
    col_a: str,
    df_b: pd.DataFrame,
    col_b: str,
    threshold: float = 0.60,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    interrupted_cb: Optional[Callable[[], bool]] = None,
) -> list[MatchResult]:
    """
    Match every row in *df_a* against the best candidate from *df_b*.

    Parameters
    ----------
    df_a, df_b:
        Source DataFrames.
    col_a, col_b:
        Column names to compare (must exist in the respective DataFrames).
    threshold:
        Minimum combined_score to consider a pair a valid match.
    progress_cb:
        Optional callable(current_row, total_rows).  Called every
        _PROGRESS_INTERVAL rows and on completion.
    interrupted_cb:
        Optional callable() → bool.  If it returns True the loop exits
        early and returns whatever results have been accumulated so far.

    Returns
    -------
    list[MatchResult]
        One entry per row in df_a.  index_a and index_b reference the
        original DataFrame integer indices (df.index values).
    """
    names_b: list[str] = [str(v) if pd.notna(v) else "" for v in df_b[col_b]]
    indices_b: list[int] = list(df_b.index)
    total_a = len(df_a)

    results: list[MatchResult] = []

    for row_num, (idx_a, row_a) in enumerate(df_a.iterrows()):
        # Check for cancellation
        if interrupted_cb and interrupted_cb():
            break

        raw_a = str(row_a[col_a]) if pd.notna(row_a[col_a]) else ""

        best: Optional[MatchResult] = None

        for idx_b, raw_b in zip(indices_b, names_b):
            candidate = score(raw_a, raw_b)
            candidate.index_a = int(idx_a)
            candidate.index_b = int(idx_b)
            if best is None or candidate.combined_score > best.combined_score:
                best = candidate

        if best is None:
            # df_b was empty
            results.append(
                MatchResult(
                    index_a=int(idx_a),
                    index_b=None,
                    raw_a=raw_a,
                    tier=TIER_NO_MATCH,
                )
            )
        elif best.combined_score < threshold:
            # Best found but below threshold → No Match (keep score for reference)
            best.tier = TIER_NO_MATCH
            best.index_b = None
            results.append(best)
        else:
            results.append(best)

        # Emit progress
        if progress_cb and (
            row_num % _PROGRESS_INTERVAL == 0 or row_num == total_a - 1
        ):
            progress_cb(row_num + 1, total_a)

    return results
