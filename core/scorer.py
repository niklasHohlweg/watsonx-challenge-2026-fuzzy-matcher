"""
scorer — weighted similarity scoring for a pair of raw name strings.

Scoring formula:
    token_score   = Jaccard similarity on normalized token sets          (weight 0.40)
    ratio_score   = rapidfuzz.fuzz.ratio(norm_a, norm_b) / 100          (weight 0.35)
    partial_score = rapidfuzz.fuzz.partial_ratio(norm_a, norm_b) / 100  (weight 0.25)

    combined = 0.40 * token + 0.35 * ratio + 0.25 * partial

Quality tiers (fixed):
    Exact    >= 0.97
    Good     >= 0.80
    Possible >= 0.60
    No Match  < 0.60
"""
from __future__ import annotations

from rapidfuzz import fuzz

from core.normalizer import normalize, tokenize
from models.match_result import MatchResult, assign_tier

# Algorithm weights
_W_TOKEN = 0.40
_W_RATIO = 0.35
_W_PARTIAL = 0.25


def _jaccard(tokens_a: list[str], tokens_b: list[str]) -> float:
    """
    Jaccard similarity on two token lists.

    Returns 1.0 if both lists are empty (both names normalized away).
    Returns 0.0 if exactly one list is empty.
    """
    set_a = set(tokens_a)
    set_b = set(tokens_b)

    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union


def score(name_a: str, name_b: str) -> MatchResult:
    """
    Compute a weighted similarity score between two raw name strings.

    Normalization is applied internally; callers pass raw strings.

    Parameters
    ----------
    name_a, name_b:
        Raw name strings as read from the source Excel files.

    Returns
    -------
    MatchResult
        Populated with individual scores, combined score, and tier.
        index_a / index_b are left at their zero defaults and must be
        filled in by the caller (matcher.py).
    """
    norm_a = normalize(name_a)
    norm_b = normalize(name_b)

    tokens_a = tokenize(norm_a)
    tokens_b = tokenize(norm_b)

    token_s = _jaccard(tokens_a, tokens_b)
    ratio_s = fuzz.ratio(norm_a, norm_b) / 100.0
    partial_s = fuzz.partial_ratio(norm_a, norm_b) / 100.0

    combined = _W_TOKEN * token_s + _W_RATIO * ratio_s + _W_PARTIAL * partial_s
    # Clamp to [0, 1] to guard against floating-point drift
    combined = max(0.0, min(1.0, combined))

    return MatchResult(
        raw_a=name_a,
        raw_b=name_b,
        norm_a=norm_a,
        norm_b=norm_b,
        token_score=token_s,
        ratio_score=ratio_s,
        partial_score=partial_s,
        combined_score=combined,
        tier=assign_tier(combined),
    )
