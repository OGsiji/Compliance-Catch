# Reproduction

The scored result is the **Gemini agent** (needs a `GEMINI_API_KEY`). The tests
and the **offline smoke test** need no credentials — but the offline run is a
plumbing check, not a reported result (see the note in step 3).

## If you don't have reliable model access

You do not need a working API key to verify the reported result. The committed
[`trajectories/`](trajectories) directory contains the **full logged
input/output of an actual Gemini run across all 10 calls** (a JSON and a
Markdown file per call), and [`eval/results/`](eval/results) contains the
resulting scored tables. Together these are sufficient to check the numbers in
the README without running anything. `make test` and `make baseline` require no
credentials and confirm the codebase itself runs correctly. `make agent` and
`make eval` require a `GEMINI_API_KEY` only if you want to reproduce the live run
yourself — not to verify the claims already made in the README.

## Requirements

- Python 3.9+
- For the agent: `pip install -r requirements.txt` and a `GEMINI_API_KEY`

## Make targets (thin wrappers)

`make help` lists them. Each wraps a raw command — shown underneath so Windows
users without `make` can run them directly:

| Target | Raw command |
|---|---|
| `make setup` | `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` |
| `make baseline` | the two `python -c` one-liners below (no key) |
| `make agent` | `python -m agent.pipeline --provider gemini` |
| `make eval` | `python -m eval.run_eval --provider gemini` |
| `make test` | `python -m unittest discover -s tests -v` |
| `make clean` | remove `__pycache__` dirs and `.venv` |

`make baseline` raw equivalent:
```bash
python -c "from core.data import load_all_transcripts as L; from baseline.keyword_match import keyword_flags as K; [print(t.id, sorted({f['policy_id'] for f in K(t)})) for t in L()]"
python -c "from core.data import load_all_transcripts as L; from baseline.random_sample import review as R; print({k: v['reviewed'] for k, v in R(L()).items()})"
```

## 1. The scored result — real Gemini agent

```bash
cp .env.example .env    # set GEMINI_API_KEY
set -a; source .env; set +a
pip install -r requirements.txt
make eval               # or: python -m eval.run_eval --provider gemini
```

Writes `eval/results/results_gemini.md` / `.json`. Measured:

| Metric | Random 5% | Keyword | **Gemini agent** |
|---|---|---|---|
| Coverage | 10% | 100% | **100%** |
| Violations caught | 0 | 5 | **8 / 8** |
| Recall | 0.0 | 0.63 | **1.0** |
| Precision | 0.0 | 0.63 | **0.571** (strict) |

The flagger and verifier models default to the values in `core/llm.py` and are
overridable via `FLAGGER_MODEL` / `VERIFIER_MODEL` (different Google accounts
offer different model IDs). The **exact IDs used for the committed run** are
recorded in `eval/results/results_gemini.json` (`models` field) and in each
`trajectories/*.json`. Temperature 0. Recall and coverage are stable;
precision is 0.571 under strict line-and-rule scoring (0.80 per call) — the gap
is the call_05/call_10 extra-but-real flags described in the README Hot take.
Model outputs are not guaranteed bit-identical across revisions, so the exact
false-positive count on those two calls may vary slightly run to run.

> **Model IDs move.** The plan originally named `gemini-2.5-flash-lite`, but that
> ID is now retired for new API keys (returns 404). The `-latest` aliases track a
> live model. Override any stage with `FLAGGER_MODEL` / `VERIFIER_MODEL`.

> **Free-tier quotas are small.** The very newest models expose only ~20
> requests/day free; the defaults (`gemini-2.5-flash` + `gemini-flash-lite-latest`)
> have larger quotas. If a call still hits `429`, the harness retries with backoff
> (honoring the server's suggested delay) and, failing that, marks the call
> unreviewed and continues rather than crashing.

## 2. Offline smoke test (no key) — plumbing only

```bash
make test        # 9 tests, no key
python -m eval.run_eval --provider offline   # confirms the pipeline runs end to end
```

This runs the deterministic pattern-matcher (`core/heuristics.py`) so the whole
flag → verify → route → score path executes without credentials. **Its scores are
not a result.** The pattern list was written with knowledge of these 10 fixtures
(it contains literal phrases from the transcripts), so a perfect offline score is
expected and meaningless as evidence of general capability. It exists to prove
the plumbing, and for CI.

The 9 tests cover: the pipeline runs end to end on all 10 fixtures; the
programmatic quote check rejects fabricated quotes and wrong line numbers and
normalizes whitespace; the keyword baseline demonstrably false-positives on
call_09 and misses call_10; the random sample reviews exactly 1/10 calls; and the
pattern-aggregation groups rules across ≥2 calls.

## 3. (Optional) audio round-trip

```bash
pip install gTTS
python scripts/generate_sample_audio.py
# Transcribe + run the pipeline in one step (writes nothing into the fixture set):
python -m agent.pipeline --audio data/audio/call_01.mp3 --provider gemini
```

## Determinism notes

- Offline smoke test: fully deterministic.
- Random-sample baseline: seeded (`SEED = 42`), so coverage selection is stable.
- Gemini calls: temperature 0, but outputs are not guaranteed bit-identical
  across model revisions; recall/coverage are stable, precision may vary by the
  odd flag on call_05/call_10. The programmatic quote check keeps grounding stable
  regardless.

## Scoring definition

Strict single-label matching, per call:
- **True positive** — the system cites the ground-truth rule for a violation call.
- **False negative** — a violation call where it does not cite the correct rule.
- **False positive** — flagging a clean call, **or** citing any rule/line other
  than the single ground-truth (line, policy) on a violation call.
- **Coverage** — share of calls actually reviewed.

Ground truth is single-label and single-line. On call_05 and call_10 the Gemini
agent grounds additional *real* violations the answer key doesn't label (a second
rule and a second line — see the README Hot take), which strict scoring counts
against precision (0.571). A per-call policy-set scoring collapses these to 0.80.
Full per-call detail is written to `eval/results/results_<provider>.json`.

## Data provenance

`data/ground_truth.json` is the eval oracle and is **never** passed to the
flagger or verifier — it is read only by `eval/run_eval.py`. The 10 transcripts
and 12 policy rules are synthetic, authored by hand for this eval.
