"""Pass 1 — the flagger.

Proposes candidate violations from the full transcript against the full policy
list. With a Gemini client it uses the documented flagger prompt; with no key
it falls back to deterministic heuristics. Either way it emits Flag objects and
logs the call to the trajectory.
"""
from __future__ import annotations

from typing import List, Optional

from core import heuristics
from core.data import flaggable_rules
from core.llm import GeminiClient
from core.models import Flag, Rule, Transcript
from core.prompts import FLAGGER_SYSTEM, flagger_user_prompt
from core.trajectory import TrajectoryLogger

VALID_SEVERITY = {"low", "medium", "high"}


def _transcript_block(transcript: Transcript) -> str:
    return "\n".join(f"{ln.line}. {ln.speaker}: {ln.text}" for ln in transcript.lines)


def _policy_block(policy: List[Rule]) -> str:
    return "\n".join(f"{r.id} ({r.title}): {r.text}" for r in policy)


class Flagger:
    def __init__(self, client: Optional[GeminiClient], logger: TrajectoryLogger,
                 model: Optional[str] = None):
        self.client = client
        self.logger = logger
        self.model = model or (client.flagger_model if client else "offline-heuristic")

    def run(self, transcript: Transcript, policy: List[Rule]) -> List[Flag]:
        # Only line-violation rules are flaggable per line; must-inform rules
        # (recording disclosure, cooling-off) would make the flagger flag
        # greetings for what they *fail* to say.
        policy = flaggable_rules(policy)
        if self.client is None:
            flags = heuristics.flag_transcript(transcript, policy)
            self.logger.record(
                transcript.id, "flagger", self.model,
                {"note": "offline heuristic flagger", "n_lines": len(transcript.lines)},
                [f.to_dict() for f in flags],
            )
            return flags

        system = FLAGGER_SYSTEM
        user = flagger_user_prompt(_transcript_block(transcript), _policy_block(policy))
        parsed, raw = self.client.complete_json(system, user, self.model)
        flags = self._parse(parsed, transcript)
        self.logger.record(
            transcript.id, "flagger", self.model,
            {"system": system, "user": user},
            {"raw": raw, "flags": [f.to_dict() for f in flags]},
        )
        return flags

    @staticmethod
    def _parse(parsed, transcript: Transcript) -> List[Flag]:
        if isinstance(parsed, dict):
            items = parsed.get("flags", [])
        elif isinstance(parsed, list):
            items = parsed
        else:
            items = []
        valid_ids = {ln.line for ln in transcript.lines}
        flags: List[Flag] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            try:
                line = int(it.get("line"))
            except (TypeError, ValueError):
                continue
            if line not in valid_ids:
                continue
            severity = str(it.get("severity", "medium")).lower()
            if severity not in VALID_SEVERITY:
                severity = "medium"
            flags.append(Flag(
                line=line,
                quote=str(it.get("quote", "")),
                policy_id=str(it.get("policy_id", "")).strip(),
                reasoning=str(it.get("reasoning", "")).strip(),
                severity=severity,
            ))
        return flags
