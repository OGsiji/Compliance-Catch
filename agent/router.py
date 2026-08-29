"""The router — assembles the final, judge-facing per-call report.

Nothing beyond: quote, policy citation, severity, status, reasoning. This is
the artifact End-to-End Quality is scored on, so it is kept deliberately clean.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from core.models import Flag, ReportItem, Rule, Verdict


def build_report(flag_verdicts: List[Tuple[Flag, Verdict]],
                 policy_idx: Dict[str, Rule]) -> List[ReportItem]:
    report: List[ReportItem] = []
    for flag, verdict in flag_verdicts:
        rule = policy_idx.get(flag.policy_id)
        title = rule.title if rule else "(unknown policy)"
        reasoning = verdict.detail or flag.reasoning
        report.append(ReportItem(
            line=flag.line,
            quote=flag.quote,
            policy_id=flag.policy_id,
            policy_title=title,
            severity=flag.severity,
            status=verdict.status,
            reasoning=reasoning,
        ))
    # Grounded first, then by line number — stable, judge-friendly ordering.
    report.sort(key=lambda r: (r.status != "grounded", r.line))
    return report
