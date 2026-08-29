"""Deterministic offline stand-in for the LLM.

When no GEMINI_API_KEY is configured, the flagger and verifier fall back to
these hand-written rules so the *entire* pipeline, eval harness, and tests run
end-to-end with zero credentials. This is explicitly a demo/CI stand-in, not
the headline agent: real reasoning (especially on the implied cases) comes from
Gemini once a key is present. See README for the honest framing.

The heuristics encode a few disambiguations a naive keyword list can't — e.g.
they refuse to flag an urgency line that disclaims control over an external
deadline (call_09) — which is exactly the gap between the keyword baseline and
a reasoning agent.
"""
from __future__ import annotations

import re
from typing import List

from core.models import Flag, Rule, Transcript

# Default severity per policy, aligned with how these violations are labelled.
DEFAULT_SEVERITY = {
    "P-01": "high", "P-02": "medium", "P-03": "medium", "P-04": "medium",
    "P-05": "medium", "P-06": "high", "P-07": "high", "P-08": "medium",
    "P-09": "low", "P-10": "medium", "P-11": "high", "P-12": "high",
}

# --- line-level positive patterns (used by both flagger and scoped verifier) ---
GUARANTEE_PATTERNS = [
    r"\bi can guarantee\b", r"\bguarantee you\b", r"\bguaranteed returns?\b",
    r"\bguaranteed \d", r"\byou'?ll see at least\b",
    r"\bnobody'?s ever lost\b", r"\bnobody'?s walked away with less\b",
    r"\bnever lost money\b", r"\bno way to lose\b",
]
RISK_PATTERNS = [
    r"\bcompletely safe\b", r"\bperfectly safe\b", r"\btotally safe\b",
    r"\bcan'?t lose money\b", r"\brisk[- ]?free\b", r"\bno risk\b",
    r"\bzero risk\b",
]
URGENCY_PATTERNS = [
    r"\bin the next \d+\s*(minute|second|hour)", r"\bnext \d+\s*minutes?\b",
    r"\bonly (available|if you sign up)\b", r"\bact now\b",
    r"\bsign up now\b", r"\banother call waiting\b", r"\bright now or\b",
    r"\bbefore you hang up\b",
]
# If an urgency line disclaims control over a genuine external deadline, it is
# not a high-pressure tactic — this is the reasoning the keyword baseline lacks.
EXTERNAL_DEADLINE_GUARD = [
    r"not something i control", r"not in my control", r"out of my hands",
    r"fed rate", r"rate resets", r"statutory", r"regulatory",
]
DISCRIMINATION_PATTERNS = [
    r"\bfor someone your age\b", r"\bat your age\b", r"\bsomeone of your\b",
    r"\bfor a (wo)?man\b", r"\bpeople like you\b", r"\byour (religion|gender|race)\b",
]
SUBSTITUTION_PATTERNS = [
    r"\benrolled you in\b", r"\bsigned you up\b", r"\bupgraded you\b",
    r"\bwent ahead and enrolled\b", r"\bput you (in|on)\b.*\binstead\b",
    r"\binstead\b.*\b(tier|plan|package|premium)\b",
    r"\b(tier|plan|package|premium)\b.*\binstead\b",
]
UPSELL_PATTERNS = [
    r"\benroll\b", r"\bpremium\b", r"\bpackage\b", r"\bgreat time to\b",
    r"\bupgrade\b", r"\badd[- ]on\b", r"\badvisory\b",
]
DISCLOSURE_PATTERNS = [
    r"\bbalance is\b", r"\baccount balance\b", r"\byour balance\b",
    r"\bpending transfer\b", r"\btransaction history\b",
]
VULNERABILITY_PATTERNS = [
    r"passed away", r"\bpassed\b", r"bereave", r"widow",
    r"don'?t (really )?understand", r"i'?m (a little )?scattered",
    r"confused", r"hardship", r"lost my job", r"can'?t afford",
]
IDENTIFIER_PATTERNS = {
    "name": r"\b(full )?name\b",
    "dob": r"\b(date of birth|dob|birth)\b",
    "account_number": r"\b(account number|last four|last 4)\b",
    "ssn": r"\b(social security|ssn)\b",
    "address": r"\b(address|zip code|postal)\b",
}


def _matches_any(text: str, patterns: List[str]) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in patterns)


def _reason(policy_id: str) -> str:
    return {
        "P-01": "Agent states or implies a guarantee of returns or that no money can be lost.",
        "P-03": "Agent discloses account-specific details before verifying two identifiers.",
        "P-04": "Agent manufactures artificial urgency to force an immediate decision.",
        "P-06": "Agent implies differential treatment based on a protected characteristic.",
        "P-07": "Agent describes a variable-return product as safe or risk-free.",
        "P-08": "Agent substitutes or upgrades the product without the customer's consent.",
        "P-12": "Agent upsells a customer who has disclosed a vulnerability instead of slowing down.",
    }.get(policy_id, "Agent language plausibly violates this policy rule.")


def _flag(line_no: int, text: str, policy_id: str) -> Flag:
    return Flag(
        line=line_no,
        quote=text,
        policy_id=policy_id,
        reasoning=_reason(policy_id),
        severity=DEFAULT_SEVERITY.get(policy_id, "medium"),
    )


def flag_transcript(transcript: Transcript, policy: List[Rule]) -> List[Flag]:
    """Propose candidate flags for a whole transcript (offline flagger)."""
    active = {r.id for r in policy}
    flags: List[Flag] = []
    seen_identifiers: set = set()
    vulnerability_disclosed = False

    for ln in transcript.lines:
        text = ln.text
        is_agent = ln.speaker.lower() == "agent"

        # Track context established by earlier lines (either speaker).
        for name, pat in IDENTIFIER_PATTERNS.items():
            if re.search(pat, text.lower()):
                seen_identifiers.add(name)
        if not is_agent and _matches_any(text, VULNERABILITY_PATTERNS):
            vulnerability_disclosed = True

        if not is_agent:
            continue

        # P-01 guarantees / P-07 risk (mutually exclusive by phrasing).
        if "P-01" in active and _matches_any(text, GUARANTEE_PATTERNS):
            flags.append(_flag(ln.line, text, "P-01"))
        if "P-07" in active and _matches_any(text, RISK_PATTERNS):
            flags.append(_flag(ln.line, text, "P-07"))

        # P-04 urgency, unless it disclaims an external deadline.
        if ("P-04" in active and _matches_any(text, URGENCY_PATTERNS)
                and not _matches_any(text, EXTERNAL_DEADLINE_GUARD)):
            flags.append(_flag(ln.line, text, "P-04"))

        # P-06 discriminatory language.
        if "P-06" in active and _matches_any(text, DISCRIMINATION_PATTERNS):
            flags.append(_flag(ln.line, text, "P-06"))

        # P-08 unauthorized substitution.
        if "P-08" in active and _matches_any(text, SUBSTITUTION_PATTERNS):
            flags.append(_flag(ln.line, text, "P-08"))

        # P-03 account disclosure before two identifiers verified.
        if ("P-03" in active and _matches_any(text, DISCLOSURE_PATTERNS)
                and len(seen_identifiers) < 2):
            flags.append(_flag(ln.line, text, "P-03"))

        # P-12 upsell after a disclosed vulnerability.
        if ("P-12" in active and vulnerability_disclosed
                and _matches_any(text, UPSELL_PATTERNS)):
            flags.append(_flag(ln.line, text, "P-12"))

    return flags


def line_violates_rule(quote: str, policy_id: str) -> bool:
    """Scoped, line-only re-check used by the offline verifier (step 2).

    Sees only the quoted line and the cited policy id — mirrors the narrow
    Gemini call that never receives the full transcript or policy list.
    """
    patterns = {
        "P-01": GUARANTEE_PATTERNS,
        "P-07": RISK_PATTERNS,
        "P-06": DISCRIMINATION_PATTERNS,
        "P-08": SUBSTITUTION_PATTERNS,
        "P-03": DISCLOSURE_PATTERNS,
        "P-12": UPSELL_PATTERNS,
    }.get(policy_id)
    if policy_id == "P-04":
        return (_matches_any(quote, URGENCY_PATTERNS)
                and not _matches_any(quote, EXTERNAL_DEADLINE_GUARD))
    if patterns is None:
        return False
    return _matches_any(quote, patterns)
