"""
Tests for core/normalizer.py
"""
from __future__ import annotations

import pytest

from core.normalizer import normalize, tokenize


class TestNormalize:
    def test_all_caps(self):
        assert normalize("ACME TRADING") == "acme trading"

    def test_suffix_stripping_gmbh(self):
        assert normalize("Acme GmbH") == "acme"

    def test_suffix_stripping_gmbh_co_kg(self):
        result = normalize("Acme GmbH & Co. KG")
        assert result == "acme"

    def test_suffix_stripping_inc(self):
        assert normalize("Acme Inc.") == "acme"

    def test_suffix_stripping_ltd(self):
        assert normalize("Acme Ltd") == "acme"

    def test_suffix_stripping_llc(self):
        assert normalize("Acme LLC") == "acme"

    def test_punctuation_removed(self):
        result = normalize("Acme, Trading & Co.")
        assert "," not in result
        assert "." not in result

    def test_empty_string(self):
        assert normalize("") == ""

    def test_whitespace_only(self):
        assert normalize("   ") == ""

    def test_already_clean(self):
        assert normalize("acme trading") == "acme trading"

    def test_stopword_removal(self):
        result = normalize("The Company of the Year")
        assert "the" not in result.split()
        assert "of" not in result.split()

    def test_none_value(self):
        # Should not raise; coerce to empty
        assert normalize(None) == ""  # type: ignore[arg-type]

    def test_numeric_string(self):
        result = normalize("123")
        assert result == "123"

    def test_leading_trailing_whitespace(self):
        assert normalize("  Acme  ") == "acme"

    def test_repeated_suffix_removal(self):
        """Ensure iterative suffix removal handles compound suffixes."""
        result = normalize("Acme AG & Co. KG")
        assert result == "acme"


class TestTokenize:
    def test_basic(self):
        assert tokenize("acme trading") == ["acme", "trading"]

    def test_empty(self):
        assert tokenize("") == []

    def test_single_token(self):
        assert tokenize("acme") == ["acme"]
