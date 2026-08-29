# Changelog

## 0.2.0 — real Gemini integration + audio verified

### Added
- **Verified audio round-trip.** gTTS generates sample clips for call_01/02/10;
  `agent/transcribe.py` transcribes `call_01.mp3` back through Gemini with
  correct Agent/Customer labels and the guarantee line preserved. New
  `python -m agent.pipeline --audio <file>` runs transcription → pipeline in one
  step (in-memory, no scored-fixture pollution).
- **Resilient LLM client.** Exponential-backoff retries on transient upstream
  errors (429/5xx), honoring the server's suggested retry delay; the eval now
  isolates per-call failures (marks the call unreviewed) instead of aborting.

### Changed
- **Model IDs.** `gemini-2.5-flash-lite` is retired for new API keys (404);
  defaults are now `gemini-2.5-flash` (flagger) and `gemini-flash-lite-latest`
  (verifier), split across models so their free-tier quotas don't compete.
- Pinned `google-genai>=1.40,<2.0` (matches the installed 1.47 SDK API).

### Scoring + a real-model finding
- Switched to strict single-label scoring: a flag citing the *wrong* rule counts
  as a false positive, not just flags on clean calls (keyword baseline: FP 1 → 3,
  precision 0.83 → 0.63). Per-call detail now saved to `results_<provider>.json`.
- Real Gemini run: 100% coverage, 8/8 caught, recall 1.0, precision 0.8. The two
  "false positives" are the agent grounding *both* P-01 and P-07 on call_05 and
  call_10 — defensible multi-rule violations the single-label ground truth can't
  credit. A labelling limitation, not a pipeline error.

### Known limitation
- Gemini free-tier daily quotas are small (~20 req/day on the newest models); a
  full Gemini eval can hit `429` and mark a call or two unreviewed. The
  deterministic offline eval is the stable, reproducible reference. Default
  models (`gemini-2.5-flash` + `gemini-flash-lite-latest`) have larger quotas.

## 0.1.0 — initial build

### Added
- **Policy + fixtures.** 12-rule `policy.json`; 10 synthetic transcripts and a
  held-out `ground_truth.json` covering guarantees, identity verification,
  pressure tactics, risk misrepresentation, discrimination, unauthorized
  substitution, and vulnerable-customer handling, plus a clean control and an
  external-deadline near-miss.
- **Two baselines.** Seeded 5% random sample (dramatizes the coverage gap) and
  a keyword/regex matcher (100% coverage, no grounding).
- **Two-stage agent.** Flagger (full context) → Verifier (programmatic verbatim
  quote check, then a scoped single-line/single-rule LLM re-check) → Router
  (clean grounded/needs-review report).
- **Pluggable provider.** Gemini 2.5 Flash / Flash-Lite via one `GEMINI_API_KEY`,
  with a deterministic offline heuristic provider so the whole pipeline, eval,
  and tests run with zero credentials.
- **Eval harness.** Scores both baselines and the agent against ground truth:
  coverage, TP/FP/FN, precision, recall; writes a Markdown + JSON results table.
- **Trajectory logging.** Every flagger/verifier call written to `/trajectories`
  as JSON and a human-readable Markdown render.
- **Tests.** 7 offline tests covering grounding, baseline weaknesses, and
  full-fixture reproduction of ground truth.
- **Optional audio ingestion.** `agent/transcribe.py` (Gemini audio → transcript
  JSON, failures isolated) and `scripts/generate_sample_audio.py` (gTTS).

### The hard case (call_10) and what it revealed
The implied-guarantee case ("nobody's ever lost money") has no keyword to match,
so it exposed the real design lesson: reliability came from **grounding**, not
model size. The free programmatic quote check plus a deliberately narrow re-check
(one line, one rule) is what let the agent hit 1.0 precision while the keyword
baseline sat at 0.63 — the basis for the README hot take.
