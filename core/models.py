"""Typed data models shared across the pipeline.

Plain dataclasses keep the flat-JSON contract explicit without pulling in a
schema library. Every model round-trips to/from the JSON shapes documented in
docs/IMPLEMENTATION_PLAN.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional

SEVERITIES = ("low", "medium", "high")
STATUS_GROUNDED = "grounded"
STATUS_NEEDS_REVIEW = "needs review"


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    text: str
    # "line"     — violated by something the agent says (quotable on one line)
    # "presence" — a must-inform rule violated by omission (no line to quote);
    #              these are NOT handed to the per-line flagger.
    mode: str = "line"


@dataclass(frozen=True)
class Line:
    line: int
    speaker: str
    text: str


@dataclass
class Transcript:
    id: str
    lines: List[Line]

    def line_text(self, line_no: int) -> Optional[str]:
        for ln in self.lines:
            if ln.line == line_no:
                return ln.text
        return None

    def agent_lines(self) -> List[Line]:
        return [ln for ln in self.lines if ln.speaker.lower() == "agent"]


@dataclass
class Flag:
    """A candidate violation proposed by the flagger (pass 1)."""

    line: int
    quote: str
    policy_id: str
    reasoning: str
    severity: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Verdict:
    """Output of the two-step verifier for a single flag."""

    quote_ok: bool
    recheck_verdict: Optional[str]  # "yes" | "no" | None (skipped)
    status: str                     # grounded | needs review
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReportItem:
    """The final, judge-facing artifact — nothing more than this."""

    line: int
    quote: str
    policy_id: str
    policy_title: str
    severity: str
    status: str
    reasoning: str

    def to_dict(self) -> dict:
        return asdict(self)
