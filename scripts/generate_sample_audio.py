"""Generate synthetic sample audio for a few calls (optional bonus demo).

Reproducible: rerun this one script to regenerate the clips — no manual
recording. Uses gTTS (free, scriptable). Two 'voices' are simulated by
alternating the gTTS accent (tld) for Agent vs Customer; per-line MP3 clips are
concatenated into one file per call.

Only a few representative calls are generated (the guarantee case, the clean
call, and the hard implied-guarantee case) — this is a capability demo for the
video, not a replacement for the text-based scored eval.

Usage:
  pip install gTTS
  python scripts/generate_sample_audio.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data import REPO_ROOT, TRANSCRIPTS_DIR, load_transcript

AUDIO_DIR = os.path.join(REPO_ROOT, "data", "audio")
SAMPLE_CALLS = ["call_01", "call_02", "call_10"]
# Distinct accents stand in for two speakers.
VOICE_TLD = {"agent": "com", "customer": "co.uk"}


def generate(call_id: str) -> str:
    try:
        from gtts import gTTS
    except ImportError as exc:
        raise SystemExit("gTTS is not installed. Run: pip install gTTS") from exc

    transcript = load_transcript(os.path.join(TRANSCRIPTS_DIR, f"{call_id}.json"))
    os.makedirs(AUDIO_DIR, exist_ok=True)
    out_path = os.path.join(AUDIO_DIR, f"{call_id}.mp3")

    # Concatenate per-line MP3 frames. Plain byte concatenation plays back fine
    # for a demo and avoids an ffmpeg dependency.
    with open(out_path, "wb") as out_fh:
        for ln in transcript.lines:
            tld = VOICE_TLD.get(ln.speaker.lower(), "com")
            tmp = os.path.join(AUDIO_DIR, f".{call_id}_{ln.line}.mp3")
            gTTS(text=ln.text, lang="en", tld=tld).save(tmp)
            with open(tmp, "rb") as part:
                out_fh.write(part.read())
            os.remove(tmp)
    return out_path


def main() -> int:
    for call_id in SAMPLE_CALLS:
        path = generate(call_id)
        print(f"wrote {path}")
    print("\nNow run the whole pipeline straight from audio (no scored-fixture pollution):")
    print("  python -m agent.pipeline --audio data/audio/call_01.mp3 --provider gemini")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
