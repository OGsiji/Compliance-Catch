"""Text normalization shared by the flagger, the programmatic quote check,
and the keyword baseline. Keeping this in one place means 'does the quote
match?' is defined exactly once."""
from __future__ import annotations


def normalize_ws(s: str) -> str:
    """Collapse all runs of whitespace to single spaces and strip ends.

    This is the canonical form used when comparing a flagged quote against the
    transcript, so trivial spacing differences never route a real flag to
    'needs review'.
    """
    return " ".join((s or "").split())


def contains_normalized(haystack: str, needle: str) -> bool:
    """True if `needle` is a whitespace-normalized substring of `haystack`."""
    return normalize_ws(needle).lower() in normalize_ws(haystack).lower()
