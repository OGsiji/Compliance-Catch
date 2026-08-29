"""Optional audio ingestion — an alternative front-end that produces the SAME
data/transcripts/call_XX.json schema the flagger already consumes.

Nothing downstream changes: audio is just another way to make a transcript.
Transcription is isolated by design — a bad file or API error is reported and
returned as an error, never allowed to crash a batch or the core eval.

Honest limitations (see README): transcription errors can hide or fabricate a
violation, and the verifier checks the flagger against the *transcribed* text,
not the true audio — so a bad transcription is a real failure mode.

Usage:
  python -m agent.transcribe data/audio/call_01.mp3 --id call_01 \
      --out data/transcripts/call_01.json
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Optional

from core.data import REPO_ROOT
from core.models import Line, Transcript

TRANSCRIBE_MODEL = os.getenv("TRANSCRIBE_MODEL", "gemini-flash-latest")

TRANSCRIBE_PROMPT = """\
Transcribe this two-party phone call between a financial-services Agent and a
Customer. Return valid JSON only, an object with a single key "lines" whose
value is a list of objects: {"line": <int, starting at 1>, "speaker": "Agent"
or "Customer", "text": "<verbatim words>"}. Label the speakers as exactly
"Agent" and "Customer" based on who is representing the company vs. who is the
caller — do NOT use "Speaker 1"/"Speaker 2". Preserve wording verbatim."""


@dataclass
class TranscriptionResult:
    ok: bool
    transcript: Optional[Transcript]
    error: Optional[str]


def transcribe_audio(path: str, call_id: str,
                     api_key: Optional[str] = None) -> TranscriptionResult:
    """Transcribe one audio file to the transcript schema. Never raises."""
    if not os.path.exists(path):
        return TranscriptionResult(False, None, f"File not found: {path}")
    try:
        from google import genai
    except ImportError as exc:
        return TranscriptionResult(False, None, f"google-genai not installed: {exc}")

    key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        return TranscriptionResult(False, None, "No GEMINI_API_KEY / GOOGLE_API_KEY set.")

    try:
        from google.genai import types
        client = genai.Client(api_key=key)
        uploaded = client.files.upload(file=path)
        resp = client.models.generate_content(
            model=TRANSCRIBE_MODEL,
            contents=[uploaded, TRANSCRIBE_PROMPT],
            config=types.GenerateContentConfig(
                response_mime_type="application/json", temperature=0),
        )
        raw = (resp.text or "").strip()
        data = json.loads(raw)
        lines = [Line(line=int(l["line"]), speaker=str(l["speaker"]),
                      text=str(l["text"])) for l in data.get("lines", [])]
        if not lines:
            return TranscriptionResult(False, None, "Transcription returned no lines.")
        return TranscriptionResult(True, Transcript(id=call_id, lines=lines), None)
    except Exception as exc:  # isolate all failures
        return TranscriptionResult(False, None, f"Transcription failed: {exc}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Transcribe audio to a transcript JSON.")
    ap.add_argument("audio", help="Path to the audio file.")
    ap.add_argument("--id", required=True, help="Call id, e.g. call_01.")
    ap.add_argument("--out", default=None, help="Output transcript JSON path.")
    args = ap.parse_args(argv)

    result = transcribe_audio(args.audio, args.id)
    if not result.ok:
        print(f"[transcribe] ERROR: {result.error}")
        return 1

    payload = {"id": result.transcript.id,
               "lines": [{"line": l.line, "speaker": l.speaker, "text": l.text}
                         for l in result.transcript.lines]}
    out = args.out or os.path.join(REPO_ROOT, "data", "transcripts", f"{args.id}.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print(f"[transcribe] wrote {out} ({len(payload['lines'])} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
