"""5% random-sample baseline — dramatizes the coverage gap.

Reviews ~5% of calls (round up to at least 1). Sampled calls are run through
the keyword matcher; everything else is reported as 'not reviewed'. With 10
calls that is 1 reviewed / 9 unreviewed = 10% coverage.

Sampling is seeded so the baseline is reproducible run-to-run.
"""
from __future__ import annotations

import math
import random
from typing import Dict, List

from baseline.keyword_match import keyword_flags
from core.models import Transcript

SAMPLE_RATE = 0.05
SEED = 42


def sample_call_ids(call_ids: List[str], rate: float = SAMPLE_RATE,
                    seed: int = SEED) -> List[str]:
    n = max(1, math.ceil(len(call_ids) * rate))
    rng = random.Random(seed)
    return sorted(rng.sample(sorted(call_ids), n))


def review(transcripts: List[Transcript], rate: float = SAMPLE_RATE,
           seed: int = SEED) -> Dict[str, dict]:
    """Return {call_id: {"reviewed": bool, "flags": [...]}}."""
    ids = [t.id for t in transcripts]
    sampled = set(sample_call_ids(ids, rate, seed))
    out: Dict[str, dict] = {}
    for t in transcripts:
        if t.id in sampled:
            out[t.id] = {"reviewed": True, "flags": keyword_flags(t)}
        else:
            out[t.id] = {"reviewed": False, "flags": []}
    return out
