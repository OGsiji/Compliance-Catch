# Reproduction

Every result in the README is reproducible from a clean checkout. The scored
eval and the tests need **no credentials** (they use the deterministic offline
provider); add a Gemini key only to exercise the real model path.

## Requirements

- Python 3.9+
- (Real model only) `pip install -r requirements.txt` and a `GEMINI_API_KEY`

## 1. Reproduce the results table (offline, no key)

```bash
python -m eval.run_eval --provider offline
```

Writes `eval/results/results_offline.md` and `.json`. Expected:

| Metric | Random 5% | Keyword | Agent |
|---|---|---|---|
| Coverage | 10% | 100% | 100% |
| Violations caught | 0 | 5 | 8 |
| False positives | 0 | 3 | 0 |
| False negatives | 8 | 3 | 0 |
| Precision / Recall | 0.0 / 0.0 | 0.63 / 0.63 | 1.0 / 1.0 |

## 2. Run the test suite (offline, no key)

```bash
python -m unittest discover -s tests -v
```

7 tests: offline pipeline reproduces ground truth on all 10 fixtures; the
programmatic quote check rejects fabricated quotes and wrong line numbers and
normalizes whitespace; the keyword baseline demonstrably false-positives on
call_09 and misses call_10; the random sample reviews exactly 1/10 calls.

## 3. Run against the real Gemini model

```bash
cp .env.example .env    # set GEMINI_API_KEY
set -a; source .env; set +a
pip install -r requirements.txt
python -m eval.run_eval --provider gemini      # writes results_gemini.md
python -m agent.pipeline --call call_10 --provider gemini
```

Flagger uses `gemini-2.5-flash`; the verifier's scoped re-check uses
`gemini-flash-lite-latest`. Requests run at temperature 0 for determinism.
Every call is logged under `trajectories/`.

> **Model IDs move.** The plan originally named `gemini-2.5-flash-lite`, but
> that ID is now retired for new API keys (returns 404). The `-latest` aliases
> track a live model. Override any stage with `FLAGGER_MODEL` / `VERIFIER_MODEL`.

> **Free-tier quotas are small.** The newest models expose only ~20 requests/day
> on the free tier; a single 10-call eval (flagger + verifier ≈ 20 calls) can
> exhaust it and return `429 RESOURCE_EXHAUSTED`. The harness retries with
> backoff (honoring the server's suggested delay) and, if a call still fails,
> marks that call unreviewed and continues rather than crashing. If you see
> coverage below 100% on the Gemini run, that is a quota artifact, not a
> pipeline defect — the deterministic offline eval is the stable reference.

## 4. (Optional) audio round-trip

```bash
pip install gTTS
python scripts/generate_sample_audio.py
python -m agent.transcribe data/audio/call_01.mp3 --id call_01_audio \
    --out data/transcripts/call_01_audio.json
python -m agent.pipeline --call call_01_audio
```

## Determinism notes

- Offline provider: fully deterministic.
- Random-sample baseline: seeded (`SEED = 42`), so coverage selection is stable.
- Gemini calls: temperature 0, but model outputs are not guaranteed
  bit-identical across model revisions; the programmatic quote check keeps
  grounding stable regardless.

## Scoring definition

Strict single-label matching, per call:
- **True positive** — the system cites the ground-truth rule for a violation call.
- **False negative** — a violation call where it does not cite the correct rule.
- **False positive** — flagging a clean call, **or** citing any rule other than
  the ground-truth one on a violation call (e.g. keyword "instead" → P-08 on
  call_07, "right now" → P-04 on call_08).
- **Coverage** — share of calls actually reviewed.

Disclosed limitation: ground truth is single-label, so a genuinely multi-rule
utterance would be penalized for the second rule. In this fixture set the agent
never cites a second rule, so only the keyword baseline's spurious matches are
exposed; the agent is not unfairly penalized. Full per-call detail (which rules
each system flagged) is written to `eval/results/results_<provider>.json`.

## Data provenance

`data/ground_truth.json` is the eval oracle and is **never** passed to the
flagger or verifier — it is read only by `eval/run_eval.py`. The 10 transcripts
and 12 policy rules are synthetic, authored per `docs/eval_test_cases_v2.md`.
