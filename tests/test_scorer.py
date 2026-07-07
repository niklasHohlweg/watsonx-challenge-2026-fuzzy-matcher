"""
Tests for core/scorer.py and models/match_result.py
"""
from __future__ import annotations

import pytest

from core.scorer import score, _jaccard
from models.match_result import (
    TIER_EXACT,
    TIER_GOOD,
    TIER_POSSIBLE,
    TIER_NO_MATCH,
    MatchResult,
)


class TestJaccard:
    def test_identical_sets(self):
        assert _jaccard(["a", "b"], ["a", "b"]) == 1.0

    def test_disjoint_sets(self):
        assert _jaccard(["a"], ["b"]) == 0.0

    def test_partial_overlap(self):
        j = _jaccard(["a", "b", "c"], ["b", "c", "d"])
        assert abs(j - 2 / 4) < 1e-9  # |intersection|=2, |union|=4

    def test_both_empty(self):
        assert _jaccard([], []) == 1.0

    def test_one_empty(self):
        assert _jaccard(["a"], []) == 0.0
        assert _jaccard([], ["a"]) == 0.0


class TestScore:
    def test_identical_names_exact_tier(self):
        r = score("Acme Trading GmbH", "Acme Trading GmbH")
        assert r.tier == TIER_EXACT
        assert r.combined_score >= 0.97

    def test_close_variant_good_tier(self):
        r = score("Acme Trading", "ACME Trading GmbH")
        assert r.tier in (TIER_EXACT, TIER_GOOD)

    def test_partial_match_possible_tier(self):
        # Use a case where the shared token ratio is strong enough to push past 0.60.
        # "Acme Trading" vs "Acme Trading International" — 2/3 token overlap + high partial.
        r = score("Acme Trading", "Acme Trading International")
        assert r.tier in (TIER_POSSIBLE, TIER_GOOD, TIER_EXACT)

    def test_unrelated_names_no_match(self):
        r = score("Volkswagen AG", "Microsoft Corporation")
        assert r.tier == TIER_NO_MATCH

    def test_empty_string_both(self):
        r = score("", "")
        # Both normalize to empty; jaccard returns 1.0, ratio 1.0 → Exact
        assert r.combined_score == pytest.approx(1.0, abs=0.01)

    def test_empty_string_one_side(self):
        r = score("Acme", "")
        assert r.tier == TIER_NO_MATCH

    def test_result_fields_populated(self):
        r = score("Acme GmbH", "Acme")
        assert r.raw_a == "Acme GmbH"
        assert r.raw_b == "Acme"
        assert r.norm_a == "acme"
        assert r.norm_b == "acme"
        assert 0.0 <= r.token_score <= 1.0
        assert 0.0 <= r.ratio_score <= 1.0
        assert 0.0 <= r.partial_score <= 1.0
        assert 0.0 <= r.combined_score <= 1.0

    def test_combined_score_clamped(self):
        r = score("X", "X")
        assert r.combined_score <= 1.0
        assert r.combined_score >= 0.0
