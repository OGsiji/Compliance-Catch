"""End-to-end orchestration: flag -> verify -> route for a single transcript,
plus a CLI to run the agent over all fixtures and print/save the reports.

Usage:
  python -m agent.pipeline                 # all transcripts, auto provider
  python -m agent.pipeline --provider offline
  python -m agent.pipeline --call call_10 --provider gemini
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Dict, List

from agent.flagger import Flagger
from agent.router import build_report
from agent.verifier import Verifier
from core.data import (REPO_ROOT, load_all_transcripts, load_policy,
                       load_transcript, policy_index)
from core.llm import make_client, provider_name
from core.models import ReportItem, Rule, Transcript
from core.trajectory import TrajectoryLogger


@dataclass
class CallResult:
    call_id: str
    provider: str
    report: List[ReportItem]

    def to_dict(self) -> dict:
        return {
            "call_id": self.call_id,
            "provider": self.provider,
            "report": [r.to_dict() for r in self.report],
        }


def run_pipeline(transcript: Transcript, policy: List[Rule],
                 flagger: Flagger, verifier: Verifier,
                 policy_idx: Dict[str, Rule],
                 logger: TrajectoryLogger) -> List[ReportItem]:
    flags = flagger.run(transcript, policy)
    flag_verdicts = [(f, verifier.verify(transcript, f, policy_idx)) for f in flags]
    logger.flush(transcript.id)
    return build_report(flag_verdicts, policy_idx)


def _print_report(call_id: str, report: List[ReportItem]) -> None:
    print(f"\n=== {call_id} ===")
    if not report:
        print("  (no candidate violations)")
        return
    for r in report:
        mark = "✔ grounded" if r.status == "grounded" else "… needs review"
        print(f"  [{mark}] line {r.line} · {r.policy_id} {r.policy_title} · {r.severity}")
        print(f"      quote: {r.quote}")
        print(f"      why:   {r.reasoning}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the compliance agent pipeline.")
    ap.add_argument("--provider", default="auto", choices=["auto", "gemini", "offline"])
    ap.add_argument("--call", default=None, help="Run a single call id, e.g. call_10.")
    ap.add_argument("--audio", default=None,
                    help="Transcribe this audio file first, then run the pipeline on it.")
    ap.add_argument("--out", default=None, help="Write reports as JSON to this path.")
    args = ap.parse_args(argv)

    policy = load_policy()
    policy_idx = policy_index(policy)
    client = make_client(args.provider)
    provider = provider_name(client)
    # Only the real Gemini run writes to the committed /trajectories; offline
    # (smoke) runs write throwaway traces to a scratch dir instead.
    import os as _os
    from core.trajectory import TRAJECTORY_DIR
    from core.data import REPO_ROOT as _ROOT
    traj_dir = TRAJECTORY_DIR if provider == "gemini" else _os.path.join(_ROOT, "eval", "results", "_smoke_trajectories")
    logger = TrajectoryLogger(directory=traj_dir)
    flagger = Flagger(client, logger)
    verifier = Verifier(client, logger)

    if args.audio:
        # Audio front-end: same schema, same pipeline. Isolated failure.
        from agent.transcribe import transcribe_audio
        call_id = args.call or os.path.splitext(os.path.basename(args.audio))[0]
        result = transcribe_audio(args.audio, call_id)
        if not result.ok:
            print(f"[pipeline] audio transcription failed: {result.error}")
            return 1
        print(f"Transcribed {args.audio} -> {call_id} ({len(result.transcript.lines)} lines)")
        transcripts = [result.transcript]
    elif args.call:
        path = os.path.join(REPO_ROOT, "data", "transcripts", f"{args.call}.json")
        transcripts = [load_transcript(path)]
    else:
        transcripts = load_all_transcripts()

    print(f"Provider: {provider}")
    results: List[CallResult] = []
    for t in transcripts:
        report = run_pipeline(t, policy, flagger, verifier, policy_idx, logger)
        results.append(CallResult(t.id, provider, report))
        _print_report(t.id, report)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump([r.to_dict() for r in results], fh, indent=2, ensure_ascii=False)
        print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
