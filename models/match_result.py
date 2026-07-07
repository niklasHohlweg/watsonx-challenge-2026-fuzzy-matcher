"""
MatchResult dataclass — carries every signal produced by the scorer for a single pair.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Quality-tier labels (fixed — not exposed in UI)
TIER_EXACT = "Exact"
TIER_GOOD = "Good"
TIER_POSSIBLE = "Possible"
TIER_NO_MATCH = "No Match"

TIERS = (TIER_EXACT, TIER_GOOD, TIER_POSSIBLE, TIER_NO_MATCH)

# Tier colour codes for Excel output (openpyxl PatternFill hex values)
TIER_FILL_COLOURS: dict[str, str] = {
    TIER_EXACT:    "C6EFCE",
    TIER_GOOD:     "FFEB9C",
    TIER_POSSIBLE: "FFCCBB",
    TIER_NO_MATCH: "FFC7CE",
}

# Tier thresholds (combined_score >=)
TIER_THRESHOLDS: dict[str, float] = {
    TIER_EXACT:    0.97,
    TIER_GOOD:     0.80,
    TIER_POSSIBLE: 0.60,
}


def assign_tier(combined_score: float) -> str:
    """Return the quality-tier label for a given combined score."""
    if combined_score >= TIER_THRESHOLDS[TIER_EXACT]:
        return TIER_EXACT
    if combined_score >= TIER_THRESHOLDS[TIER_GOOD]:
        return TIER_GOOD
    if combined_score >= TIER_THRESHOLDS[TIER_POSSIBLE]:
        return TIER_POSSIBLE
    return TIER_NO_MATCH


@dataclass
class MatchResult:
    """One scored pair from the matching run."""

    # Row indices into the original DataFrames
    index_a: int = 0
    index_b: Optional[int] = None  # None when no match was found

    # Raw strings as they appeared in the source files
    raw_a: str = ""
    raw_b: str = ""  # Empty string when no match found

    # Normalized forms used for scoring
    norm_a: str = ""
    norm_b: str = ""

    # Individual signal scores (0.0 – 1.0)
    token_score: float = 0.0
    ratio_score: float = 0.0
    partial_score: float = 0.0

    # Final weighted score and quality label
    combined_score: float = 0.0
    tier: str = TIER_NO_MATCH
