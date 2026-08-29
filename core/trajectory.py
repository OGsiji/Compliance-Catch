"""Trajectory logging.

Every flagger and verifier call is recorded so a judge can follow
instructions -> tool response -> decision without reading the pipeline code.
Each call writes:
  trajectories/<call_id>.json  — machine-readable list of stage records
  trajectories/<call_id>.md    — the same records rendered for humans

A record is {timestamp, stage, model, input, output}.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Any, Dict, List

from core.data import REPO_ROOT

TRAJECTORY_DIR = os.path.join(REPO_ROOT, "trajectories")


class TrajectoryLogger:
    def __init__(self, directory: str = TRAJECTORY_DIR, enabled: bool = True):
        self.directory = directory
        self.enabled = enabled
        self._by_call: Dict[str, List[dict]] = {}
        if self.enabled:
            os.makedirs(self.directory, exist_ok=True)

    def record(self, call_id: str, stage: str, model: str,
               input_obj: Any, output_obj: Any) -> None:
        if not self.enabled:
            return
        self._by_call.setdefault(call_id, []).append({
            "timestamp": _dt.datetime.now().isoformat(timespec="seconds"),
            "stage": stage,
            "model": model,
            "input": input_obj,
            "output": output_obj,
        })

    def flush(self, call_id: str) -> None:
        if not self.enabled:
            return
        records = self._by_call.get(call_id, [])
        json_path = os.path.join(self.directory, f"{call_id}.json")
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(records, fh, indent=2, ensure_ascii=False)
        md_path = os.path.join(self.directory, f"{call_id}.md")
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(self._render_markdown(call_id, records))

    @staticmethod
    def _render_markdown(call_id: str, records: List[dict]) -> str:
        out = [f"# Trajectory — {call_id}", ""]
        for i, rec in enumerate(records, 1):
            out.append(f"## {i}. {rec['stage']}  ·  `{rec['model']}`  ·  {rec['timestamp']}")
            out.append("")
            out.append("**Input**")
            out.append("")
            out.append("```")
            out.append(_as_text(rec["input"]))
            out.append("```")
            out.append("")
            out.append("**Output**")
            out.append("")
            out.append("```json")
            out.append(_as_text(rec["output"]))
            out.append("```")
            out.append("")
        return "\n".join(out)


def _as_text(obj: Any) -> str:
    if isinstance(obj, str):
        return obj
    return json.dumps(obj, indent=2, ensure_ascii=False)
