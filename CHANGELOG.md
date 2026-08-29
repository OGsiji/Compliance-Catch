# Changelog

## 0.3.1 — cleanup + reproducibility hardening

### Changed
- Removed internal planning docs (`docs/`) and stray/offline result artifacts;
  README/REPRODUCTION now point to `core/prompts.py` for the disclosed agent
  instructions.
- Result artifacts are provider-scoped (`patterns_<provider>.md`); the offline
  smoke test writes its scores and traces to gitignored scratch locations so it
  can never clobber the committed Gemini results or `/trajectories`.

### Added
- `pyproject.toml` (installable package, pinned `google-genai==1.47.0`, optional
  `audio` extra) and a pinned `requirements.txt`.
- GitHub Actions CI running the test suite, baselines, and the offline smoke eval
  on Python 3.9/3.11/3.12 — with **no API key** — on every push.

## 0.3.0 — honest positioning + tooling

### Changed
- **Gemini is the only reported result.** README/REPRODUCTION restructured so the
  offline mode is described purely as a deterministic smoke test (fixture-fitted;
  its pattern list contains literal transcript phrases), removed from any results
  table, and never compared against Gemini.
- **Precision reported honestly as a range.** Line-aware strict scoring gives the
  Gemini agent precision **0.571** (0.80 per-call), recall **1.0**. The gap is
  fully explained: on call_05/call_10 the agent grounds extra *real* violations
  (a second line and a second overlapping rule) that the single-label ground
  truth doesn't credit — see the README Hot take. Scoring logic and
  `ground_truth.json` were left unchanged; only the explanation was added.

### Added
- **Makefile** — thin wrappers (`setup`, `baseline`, `agent`, `eval`, `test`,
  `clean`) over the documented commands; no logic changes to baseline/agent/eval.
- **README "Known limitations"** — concrete, audio-specific scope statements
  (clean-TTS-only, two-speaker-only, omission violations out of scope by design,
  PII/data-governance, free-tier throughput).

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
model size. (A later flagger-only ablation refined this — the two grounding steps
do different jobs: the quote check guarantees integrity while the scoped re-check
does the precision-lifting judgment; see the README Hot Take.)
