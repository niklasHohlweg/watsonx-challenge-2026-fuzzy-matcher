"""
normalizer — deterministic text normalization pipeline for company/account names.

Pipeline (applied in order):
  1. Strip / collapse whitespace
  2. Lowercase
  3. Remove punctuation (keep alphanumeric + spaces)
  4. Remove legal-entity suffixes (whole-word, case-insensitive)
  5. Strip generic stopwords
  6. Final whitespace collapse

Usage:
    from core.normalizer import normalize, tokenize

    normalize("Acme Trading GmbH & Co. KG")  # → "acme trading"
    tokenize("acme trading")                  # → ["acme", "trading"]
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Legal-entity suffix list — extend here as needed
# Ordered longest-first so multi-word suffixes are matched before sub-words.
# ---------------------------------------------------------------------------
_LEGAL_SUFFIXES: list[str] = [
    # Multi-word (must come first)
    "gmbh & co kg",
    "gmbh & co",
    "b v",
    "n v",
    # German / Austrian / Swiss
    "gmbh",
    "ag",
    "kg",
    "kgaa",
    "ohg",
    "gbr",
    "ug",
    "eg",
    "ev",
    "se",
    "partg",
    "gesbr",
    # UK / international
    "ltd",
    "llc",
    "llp",
    "plc",
    "inc",
    "corp",
    "co",
    "sa",
    "bv",
    "nv",
    "oy",
    "ab",
    "as",
    "spa",
    "srl",
    "sarl",
    "bvba",
    "pte",
    "sdn",
    "bhd",
    "pty",
    "pvt",
    "lp",
    "lp",
]

# Build a single regex that matches any suffix as a whole word.
# Suffixes are escaped so special chars (& . etc.) are treated literally.
_SUFFIX_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(s) for s in _LEGAL_SUFFIXES) + r")\b",
    re.IGNORECASE,
)

# Generic stopwords to drop after suffix removal
_STOPWORDS: frozenset[str] = frozenset({"the", "and", "of", "for", "a", "an"})

# Punctuation removal: keep only word chars and spaces
_PUNCT_PATTERN = re.compile(r"[^\w\s]")

# Internal whitespace collapse
_WS_PATTERN = re.compile(r"\s+")


def normalize(text: str) -> str:
    """
    Return the normalized form of *text*.

    The result is a lowercase string of meaningful tokens joined by single
    spaces.  Empty / whitespace-only input returns an empty string.
    """
    if not isinstance(text, str):
        text = "" if text is None else str(text)

    # 1. Strip / collapse whitespace
    text = text.strip()
    text = _WS_PATTERN.sub(" ", text)

    # 2. Lowercase
    text = text.lower()

    # 3. Remove punctuation
    text = _PUNCT_PATTERN.sub(" ", text)
    text = _WS_PATTERN.sub(" ", text).strip()

    # 4. Remove legal-entity suffixes (iterate to handle "GmbH & Co. KG" → "gmbh & co kg")
    prev = None
    while prev != text:
        prev = text
        text = _SUFFIX_PATTERN.sub(" ", text)
        text = _WS_PATTERN.sub(" ", text).strip()

    # 5. Strip stopwords
    tokens = [t for t in text.split() if t not in _STOPWORDS]

    # 6. Rejoin and return
    return " ".join(tokens)


def tokenize(normalized: str) -> list[str]:
    """
    Split a normalized string into its tokens.

    Returns an empty list for empty / whitespace-only input.
    """
    if not normalized:
        return []
    return normalized.split()
