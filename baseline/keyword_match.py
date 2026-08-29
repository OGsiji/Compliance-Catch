"""Keyword/regex baseline — the 'simple script' the rubric names explicitly.

Scans every line of every call for a short keyword list per policy rule and
flags matches with no severity and no grounding. It reviews 100% of calls but
has no notion of context: it will flag the external-deadline near-miss (call_09)
and miss the implied guarantee (call_10). Those failures are the point.
"""
from __future__ import annotations

import re
from typing import Dict, List

from core.models import Transcript

# Deliberately crude: surface strings only, no disambiguation.
KEYWORDS: Dict[str, List[str]] = {
    "P-01": ["guarantee", "guaranteed", "no way to lose"],
    "P-04": ["right now", "act now", "next 3 minutes", "before then",
             "limited time", "sign up now", "another call waiting"],
    "P-06": ["your age", "for a man", "for a woman", "people like you"],
    "P-07": ["safe", "risk-free", "riskfree", "can't lose", "no risk"],
    "P-08": ["instead", "enrolled you", "upgraded you"],
}


def keyword_flags(transcript: Transcript) -> List[dict]:
    flags: List[dict] = []
    for ln in transcript.lines:
        if ln.speaker.lower() != "agent":
            continue
        low = ln.text.lower()
        for policy_id, words in KEYWORDS.items():
            for w in words:
                if re.search(r"\b" + re.escape(w) + r"\b", low):
                    flags.append({"line": ln.line, "quote": ln.text,
                                  "policy_id": policy_id, "keyword": w})
                    break  # one flag per policy per line
    return flags
