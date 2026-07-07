"""
Integration tests for core/matcher.py
"""
from __future__ import annotations

import pandas as pd
import pytest

from core.matcher import run
from models.match_result import TIER_NO_MATCH, TIER_EXACT, TIER_GOOD


def _make_df(names: list[str], col: str = "Name") -> pd.DataFrame:
    return pd.DataFrame({col: names})


class TestMatcherRun:
    def test_output_count_matches_df_a_length(self):
        df_a = _make_df(["Acme", "Beta Corp", "Gamma GmbH"])
        df_b = _make_df(["Acme Inc", "Beta Corporation", "Delta AG"])
        results = run(df_a, "Name", df_b, "Name")
        assert len(results) == len(df_a)

    def test_best_match_selected(self):
        df_a = _make_df(["Acme Trading"])
        df_b = _make_df(["Acme Trading GmbH", "Totally Different Company", "Acme"])
        results = run(df_a, "Name", df_b, "Name")
        # The best match should be one of the Acme variants, not "Totally Different"
        assert results[0].raw_b != "Totally Different Company"

    def test_no_match_when_below_threshold(self):
        df_a = _make_df(["Volkswagen"])
        df_b = _make_df(["Microsoft", "Apple", "Amazon"])
        results = run(df_a, "Name", df_b, "Name", threshold=0.60)
        assert results[0].tier == TIER_NO_MATCH

    def test_index_a_correct(self):
        df_a = _make_df(["Acme", "Beta"])
        df_b = _make_df(["Acme Inc", "Beta Corp"])
        results = run(df_a, "Name", df_b, "Name")
        for i, result in enumerate(results):
            assert result.index_a == i

    def test_empty_df_b_gives_no_match(self):
        df_a = _make_df(["Acme"])
        df_b = _make_df([])
        results = run(df_a, "Name", df_b, "Name")
        assert len(results) == 1
        assert results[0].tier == TIER_NO_MATCH

    def test_exact_identical_names(self):
        df_a = _make_df(["Acme Trading GmbH"])
        df_b = _make_df(["Totally Different", "Acme Trading GmbH"])
        results = run(df_a, "Name", df_b, "Name")
        assert results[0].tier == TIER_EXACT

    def test_progress_callback_called(self):
        df_a = _make_df([f"Company {i}" for i in range(10)])
        df_b = _make_df(["Reference Co"])
        calls = []
        run(df_a, "Name", df_b, "Name", progress_cb=lambda c, t: calls.append((c, t)))
        assert len(calls) > 0
        # Final call should report total
        assert calls[-1][0] == len(df_a)

    def test_cancellation_stops_early(self):
        df_a = _make_df([f"Company {i}" for i in range(200)])
        df_b = _make_df(["Reference"])
        call_count = [0]

        def cb(c, t):
            call_count[0] += 1

        # Cancel after 1 row
        interrupted = [False]
        def cancel_after_first():
            result = interrupted[0]
            interrupted[0] = True  # cancel from 2nd check onward
            return result

        results = run(df_a, "Name", df_b, "Name", progress_cb=cb, interrupted_cb=cancel_after_first)
        # Should have stopped well before processing all 200 rows
        assert len(results) < 200
