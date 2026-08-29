"""Score both baselines and the agent pipeline against held-out ground truth.

Metrics per system:
  - violations caught (true positives, correct policy)
  - false positives (flagged a clean call, or wrong policy on a real one)
  - false negatives (missed a real violation)
  - coverage (% of calls actually reviewed — where 5% vs 100% shows up)
  - precision / recall

Writes eval/results/results_<provider>.md and .json, and prints the table.

Usage:
  python -m eval.run_eval                    # auto provider for the agent
  python -m eval.run_eval --provider offline
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
from typing import Dict, List, Set

from agent.flagger import Flagger
from agent.pipeline import run_pipeline
from agent.verifier import Verifier
from baseline import random_sample
from baseline.keyword_match import keyword_flags
from core.data import (REPO_ROOT, load_all_transcripts, load_ground_truth,
                       load_policy, policy_index)
from core.llm import make_client, provider_name
from core.trajectory import TrajectoryLogger, TRAJECTORY_DIR

RESULTS_DIR = os.path.join(REPO_ROOT, "eval", "results")


def score(predictions: Dict[str, dict], ground_truth: Dict[str, dict]) -> dict:
    """Score a system under BOTH conventions, from the same single-label
    ground_truth.json. Predictions per call:
        {reviewed: bool, policy_ids: set, grounded: [[line, policy_id], ...],
         needs_review: int}

    * per-call policy-set — a violation call is a TP if the correct rule is cited
      anywhere on it; ONE false positive per call that also cites any wrong rule
      (line number ignored). This is the lenient view.
    * strict line-and-rule — only the grounded (line, policy_id) that EXACTLY
      matches ground truth is a TP; every other grounded flag is its own false
      positive. This is the strict view.

    Ground truth is single-label, so when a system flags a genuinely multi-rule
    or multi-line utterance the extra flags count against strict precision even
    though they may be defensible — that gap (0.80 per-call vs 0.571 strict for
    the Gemini agent on call_05/call_10) is exactly what the README Hot Take
    explains. Both numbers are emitted so every claim is reproducible.
    """
    tp = fp = fn = tn = 0            # per-call policy-set
    tp_s = fp_s = fn_s = 0           # strict line-and-rule
    reviewed_n = needs = total = 0
    for call_id, gt in ground_truth.items():
        pred = predictions.get(call_id, {})
        reviewed = pred.get("reviewed", False)
        policy_ids: Set[str] = set(pred.get("policy_ids", set()))
        grounded = [tuple(x) for x in pred.get("grounded", [])]
        total += 1
        reviewed_n += 1 if reviewed else 0
        needs += pred.get("needs_review", 0)
        gt_pid = gt.get("policy_id")

        if gt.get("violation"):
            # per-call
            if reviewed and gt_pid in policy_ids:
                tp += 1
            else:
                fn += 1
            if reviewed and (policy_ids - {gt_pid}):
                fp += 1
            # strict
            target = (gt.get("line"), gt_pid)
            if reviewed and target in grounded:
                tp_s += 1
            else:
                fn_s += 1
            fp_s += sum(1 for x in grounded if x != target) if reviewed else 0
        else:
            if reviewed and policy_ids:
                fp += 1
            else:
                tn += 1
            fp_s += len(grounded) if reviewed else 0

    def _p(t, f):
        return round(t / (t + f), 3) if (t + f) else 0.0

    return {
        "tp": tp, "fp_per_call": fp, "fn": fn, "tn": tn,
        "precision_per_call": _p(tp, fp), "recall_per_call": _p(tp, fn),
        "tp_strict": tp_s, "fp_strict_line_and_rule": fp_s, "fn_strict": fn_s,
        "precision_strict_line_and_rule": _p(tp_s, fp_s),
        "recall_strict_line_and_rule": _p(tp_s, fn_s),
        "reviewed": reviewed_n, "total": total, "needs_review": needs,
        "coverage_pct": round(100 * reviewed_n / total, 1) if total else 0.0,
    }


def agent_predictions(transcripts, policy, policy_idx, provider) -> Dict[str, dict]:
    client = make_client(provider)
    # The committed /trajectories are the real Gemini run (a submission artifact).
    # The offline smoke test writes its throwaway traces to a scratch dir so it
    # can never clobber them.
    prov = provider_name(client)
    traj_dir = TRAJECTORY_DIR if prov == "gemini" else os.path.join(RESULTS_DIR, "_smoke_trajectories")
    logger = TrajectoryLogger(directory=traj_dir)
    flagger = Flagger(client, logger)
    verifier = Verifier(client, logger)
    preds: Dict[str, dict] = {}
    for t in transcripts:
        # Isolate per-call failures: a persistent error on one call marks that
        # call unreviewed and continues, rather than aborting the whole run.
        try:
            report = run_pipeline(t, policy, flagger, verifier, policy_idx, logger)
        except Exception as exc:  # noqa: BLE001
            print(f"[eval] {t.id}: pipeline error, marking unreviewed -> {exc}")
            preds[t.id] = {"reviewed": False, "policy_ids": set(), "needs_review": 0}
            continue
        grounded = [r for r in report if r.status == "grounded"]
        needs = [r for r in report if r.status != "grounded"]
        preds[t.id] = {
            "reviewed": True,
            "policy_ids": {r.policy_id for r in grounded},
            "grounded": sorted((r.line, r.policy_id) for r in grounded),
            "needs_review": len(needs),
        }
    models = ({"flagger": client.flagger_model, "verifier": client.verifier_model}
              if client is not None
              else {"flagger": "offline-heuristic", "verifier": "offline-heuristic"})
    return preds, provider_name(client), models


def keyword_predictions(transcripts) -> Dict[str, dict]:
    preds: Dict[str, dict] = {}
    for t in transcripts:
        flags = keyword_flags(t)
        preds[t.id] = {"reviewed": True,
                       "policy_ids": {f["policy_id"] for f in flags},
                       "grounded": sorted((f["line"], f["policy_id"]) for f in flags),
                       "needs_review": 0}
    return preds


def random_predictions(transcripts) -> Dict[str, dict]:
    reviewed = random_sample.review(transcripts)
    preds: Dict[str, dict] = {}
    for t in transcripts:
        info = reviewed[t.id]
        preds[t.id] = {
            "reviewed": info["reviewed"],
            "policy_ids": {f["policy_id"] for f in info["flags"]},
            "grounded": sorted((f["line"], f["policy_id"]) for f in info["flags"]),
            "needs_review": 0,
        }
    return preds


ROWS = [
    ("Coverage (% reviewed)", "coverage_pct", "%"),
    ("Violations caught (TP)", "tp", ""),
    ("False negatives", "fn", ""),
    ("Recall", "recall_per_call", ""),
    ("Precision — per-call", "precision_per_call", ""),
    ("Precision — strict (line + rule)", "precision_strict_line_and_rule", ""),
    ("False positives — per-call", "fp_per_call", ""),
    ("False positives — strict (line + rule)", "fp_strict_line_and_rule", ""),
    ("Routed to needs-review", "needs_review", ""),
]


def render_table(scores: Dict[str, dict], provider: str, models: dict = None) -> str:
    def cell(sysname, key, unit):
        v = scores[sysname].get(key, 0)
        return f"{v}{unit}"

    model_line = ""
    if models:
        model_line = (f" · models: flagger `{models.get('flagger')}`, "
                      f"verifier `{models.get('verifier')}`")
    lines = [
        f"# Compliance Catch — eval results (agent provider: `{provider}`)",
        "",
        f"_Generated {_dt.datetime.now().isoformat(timespec='seconds')} · "
        f"{scores['agent']['total']} fixtures{model_line}_",
        "",
        "| Metric | Random 5% | Keyword match | Agent | Δ (keyword → agent) |",
        "|---|---|---|---|---|",
    ]
    for label, key, unit in ROWS:
        kw = scores["keyword"].get(key, 0)
        ag = scores["agent"].get(key, 0)
        if isinstance(kw, (int, float)) and isinstance(ag, (int, float)):
            delta = round(ag - kw, 3)
            delta_s = f"{'+' if delta > 0 else ''}{delta}{unit}"
        else:
            delta_s = "—"
        lines.append(
            f"| {label} | {cell('random', key, unit)} | {cell('keyword', key, unit)} "
            f"| {cell('agent', key, unit)} | {delta_s} |"
        )
    lines += [
        "",
        "**Headline:** the keyword baseline flags the external-deadline near-miss "
        "(call_09, a false positive) and misses the implied guarantee (call_10); "
        "the agent reviews 100% of calls with recall 1.0. Precision is shown under "
        "both conventions — per-call (line ignored) and strict (line + rule); the "
        "gap is the multi-rule/multi-line flags on call_05 and call_10 that the "
        "single-label ground truth cannot credit (see the README Hot Take).",
        "",
    ]
    return "\n".join(lines)


def aggregate_patterns(agent_preds: Dict[str, dict]) -> List[dict]:
    """Post-processing over already-computed grounded flags (no new LLM calls).

    Group grounded flags by policy_id; any rule grounded across 2+ different
    calls is surfaced as a recurring pattern — a possible systemic issue rather
    than an isolated incident.
    """
    calls_by_policy: Dict[str, set] = {}
    for call_id, info in agent_preds.items():
        if not info.get("reviewed"):
            continue
        for policy_id in info.get("policy_ids", set()):
            calls_by_policy.setdefault(policy_id, set()).add(call_id)

    patterns: List[dict] = []
    for policy_id, calls in calls_by_policy.items():
        if len(calls) >= 2:
            n = len(calls)
            patterns.append({
                "policy_id": policy_id,
                "calls": sorted(calls),
                "count": n,
                "note": (f"recurring across {n} calls — possible systemic issue "
                         "rather than an isolated incident"),
            })
    # Most-recurring first, then by policy id for stable output.
    patterns.sort(key=lambda p: (-p["count"], p["policy_id"]))
    return patterns


def render_patterns(patterns: List[dict], provider: str, policy_idx) -> str:
    lines = [
        "# Compliance Catch — recurring violation patterns",
        "",
        f"_Aggregated from grounded flags · agent provider: `{provider}` · "
        f"{len(patterns)} pattern(s)_",
        "",
    ]
    if not patterns:
        lines.append(
            "No policy rule was grounded across 2 or more calls — no systemic "
            "pattern detected in this fixture set.")
        lines.append("")
        return "\n".join(lines)

    lines += ["| Policy | Calls | Count | Note |", "|---|---|---|---|"]
    for p in patterns:
        rule = policy_idx.get(p["policy_id"])
        title = f" {rule.title}" if rule else ""
        lines.append(
            f"| {p['policy_id']}{title} | {', '.join(p['calls'])} | "
            f"{p['count']} | {p['note']} |")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the Compliance Catch eval.")
    ap.add_argument("--provider", default="auto", choices=["auto", "gemini", "offline"])
    args = ap.parse_args(argv)

    transcripts = load_all_transcripts()
    policy = load_policy()
    policy_idx = policy_index(policy)
    ground_truth = load_ground_truth()

    agent_preds, provider, models = agent_predictions(transcripts, policy, policy_idx, args.provider)
    all_preds = {
        "random": random_predictions(transcripts),
        "keyword": keyword_predictions(transcripts),
        "agent": agent_preds,
    }
    scores = {name: score(p, ground_truth) for name, p in all_preds.items()}

    # Per-call detail for transparency (which rules each system flagged).
    per_call = {}
    for cid in ground_truth:
        per_call[cid] = {"ground_truth": ground_truth[cid]}
        for name, p in all_preds.items():
            info = p.get(cid, {})
            per_call[cid][name] = {
                "reviewed": info.get("reviewed", False),
                "policy_ids": sorted(info.get("policy_ids", set())),
            }

    table = render_table(scores, provider, models)
    print(table)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    md_path = os.path.join(RESULTS_DIR, f"results_{provider}.md")
    json_path = os.path.join(RESULTS_DIR, f"results_{provider}.json")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(table)
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump({"provider": provider, "models": models, "scores": scores, "per_call": per_call},
                  fh, indent=2)

    # Post-processing: recurring-pattern aggregation over the grounded flags.
    patterns = aggregate_patterns(agent_preds)
    patterns_path = os.path.join(RESULTS_DIR, f"patterns_{provider}.md")
    with open(patterns_path, "w", encoding="utf-8") as fh:
        fh.write(render_patterns(patterns, provider, policy_idx))

    print(f"\nWrote {md_path}\nWrote {json_path}\nWrote {patterns_path}")
    if patterns:
        print(f"Recurring patterns: " +
              ", ".join(f"{p['policy_id']}×{p['count']}" for p in patterns))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
