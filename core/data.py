"""Loading and locating the flat-JSON fixtures.

All paths are resolved relative to the repo root so scripts work regardless of
the caller's working directory.
"""
from __future__ import annotations

import glob
import json
import os
from typing import Dict, List

from core.models import Line, Rule, Transcript

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
TRANSCRIPTS_DIR = os.path.join(DATA_DIR, "transcripts")
POLICY_PATH = os.path.join(DATA_DIR, "policy.json")
GROUND_TRUTH_PATH = os.path.join(DATA_DIR, "ground_truth.json")


def load_policy(path: str = POLICY_PATH) -> List[Rule]:
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return [Rule(**r) for r in raw["rules"]]


def policy_index(policy: List[Rule]) -> Dict[str, Rule]:
    return {r.id: r for r in policy}


def flaggable_rules(policy: List[Rule]) -> List[Rule]:
    """Rules the per-line flagger may propose against — line-violation rules
    only. Absence/presence-based must-inform rules (e.g. recording disclosure)
    have no quotable line and would make the flagger flag greetings; they are
    handled separately (or, for this fixture set, simply not exercised)."""
    return [r for r in policy if r.mode == "line"]


def load_transcript(path: str) -> Transcript:
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    lines = [Line(**ln) for ln in raw["lines"]]
    return Transcript(id=raw["id"], lines=lines)


def load_all_transcripts(directory: str = TRANSCRIPTS_DIR) -> List[Transcript]:
    paths = sorted(glob.glob(os.path.join(directory, "*.json")))
    return [load_transcript(p) for p in paths]


def load_ground_truth(path: str = GROUND_TRUTH_PATH) -> Dict[str, dict]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
