"""Pass 2 — the verifier. Two INDEPENDENT checks, not one self-assessment.

Step 1 (plain Python, no LLM): does the flagged quote appear verbatim
        (whitespace-normalized) at the stated line? Fail -> needs review,
        and step 2 is skipped (saves a call).
Step 2 (narrow LLM call): shown ONLY the one quoted line and the ONE cited
        rule. Yes -> grounded. No -> needs review.
"""
from __future__ import annotations

from typing import Dict, Optional

from core import heuristics
from core.llm import GeminiClient
from core.models import Flag, Rule, Transcript, Verdict, STATUS_GROUNDED, STATUS_NEEDS_REVIEW
from core.prompts import VERIFIER_SYSTEM, verifier_user_prompt
from core.text import normalize_ws
from core.trajectory import TrajectoryLogger


def quote_matches(transcript: Transcript, flag: Flag) -> bool:
    """Step 1: verbatim, whitespace-normalized match at the stated line."""
    line_text = transcript.line_text(flag.line)
    if line_text is None:
        return False
    return normalize_ws(flag.quote) != "" and normalize_ws(flag.quote) in normalize_ws(line_text)


class Verifier:
    def __init__(self, client: Optional[GeminiClient], logger: TrajectoryLogger,
                 model: Optional[str] = None):
        self.client = client
        self.logger = logger
        self.model = model or (client.verifier_model if client else "offline-heuristic")

    def verify(self, transcript: Transcript, flag: Flag,
               policy_idx: Dict[str, Rule]) -> Verdict:
        # --- Step 1: programmatic quote check ---
        if not quote_matches(transcript, flag):
            verdict = Verdict(
                quote_ok=False, recheck_verdict=None, status=STATUS_NEEDS_REVIEW,
                detail="Quote not found verbatim at the stated line.",
            )
            self.logger.record(
                transcript.id, "verifier:quote_check", "python",
                {"line": flag.line, "quote": flag.quote,
                 "line_text": transcript.line_text(flag.line)},
                verdict.to_dict(),
            )
            return verdict

        rule = policy_idx.get(flag.policy_id)
        if rule is None:
            verdict = Verdict(
                quote_ok=True, recheck_verdict=None, status=STATUS_NEEDS_REVIEW,
                detail=f"Cited policy id {flag.policy_id!r} is not in the policy.",
            )
            self.logger.record(
                transcript.id, "verifier:quote_check", "python",
                {"line": flag.line, "quote": flag.quote, "policy_id": flag.policy_id},
                verdict.to_dict(),
            )
            return verdict

        # --- Step 2: scoped policy re-check (line + one rule only) ---
        recheck, detail = self._recheck(transcript.id, flag, rule)
        status = STATUS_GROUNDED if recheck == "yes" else STATUS_NEEDS_REVIEW
        return Verdict(quote_ok=True, recheck_verdict=recheck, status=status, detail=detail)

    def _recheck(self, call_id: str, flag: Flag, rule: Rule):
        if self.client is None:
            yes = heuristics.line_violates_rule(flag.quote, flag.policy_id)
            verdict = "yes" if yes else "no"
            detail = "Offline scoped re-check on the single line + cited rule."
            self.logger.record(
                call_id, "verifier:recheck", self.model,
                {"quote": flag.quote, "policy_id": flag.policy_id, "rule_text": rule.text},
                {"verdict": verdict, "justification": detail},
            )
            return verdict, detail

        system = VERIFIER_SYSTEM
        user = verifier_user_prompt(flag.quote, flag.policy_id, rule.text)
        parsed, raw = self.client.complete_json(system, user, self.model)
        verdict = "yes" if str((parsed or {}).get("verdict", "")).strip().lower() == "yes" else "no"
        detail = str((parsed or {}).get("justification", "")).strip()
        self.logger.record(
            call_id, "verifier:recheck", self.model,
            {"system": system, "user": user},
            {"raw": raw, "verdict": verdict, "justification": detail},
        )
        return verdict, detail
