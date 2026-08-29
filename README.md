# Compliance Catch

A two-stage LLM agent that reviews financial-services call transcripts for
compliance violations and **grounds every flag it reports** against the source
text and the specific rule it cites.

## Who this is for — and the bottleneck

Compliance and QA teams at banks, lenders, and insurers have to check call-center
conversations for rule-breaking (illegal guarantees, undisclosed fees, high-pressure
tactics, skipped identity checks). The bottleneck is coverage: a human team can
only manually spot-check a **tiny fraction** of calls — our random-sample baseline
reviews **\~5%**. Everything else goes unreviewed. Compliance Catch reviews **100%**
of calls and grounds every flag it raises, so a reviewer's time goes to confirmed,
quoted, rule-cited findings instead of listening to calls at random.

## Why it matters

A missed violation isn't a bug ticket — it's a mis-sold product, a regulatory
finding, or a fine. But the opposite failure matters too: a tool that flags
everything trains reviewers to ignore it. The goal is full coverage *with*
grounding, so each flag is cheap for a human to confirm or dismiss.

## How it works

```
transcript + policy ─▶ Flagger ─▶ candidate flags ─▶ Verifier ─▶ Router ─▶ report
   (full context)      (pass 1)                       (pass 2)              (grounded /
                                                                            needs review)
```

**Flagger (pass 1)** — sees the *full* transcript and *full* policy list, and
proposes candidate violations: `{line, quote, policy_id, reasoning, severity}`.

**Verifier (pass 2) — the headline differentiator.** Two **independent** checks,
not one model grading itself:
1. **Programmatic quote check** (plain Python, no LLM). Is the flagged `quote`
   present verbatim (whitespace-normalized) at the stated line? If not → routed
   straight to *needs review*, no LLM call spent. This is what makes the
   grounding real instead of a model re-asserting its own confidence.
2. **Scoped policy re-check** (narrow LLM call). Shown *only* the one quoted
   line and the *one* cited rule — never the whole transcript or policy — and
   asked yes/no. "No" downgrades to *needs review*; "yes" marks it *grounded*.

**Router** — assembles the clean per-call report: quote, policy citation,
severity, status, reasoning. Nothing else.

Every flagger and verifier call is written to [`/trajectories`](trajectories)
as JSON plus a human-readable Markdown render, so a reviewer can follow
instructions → response → decision without reading the code.

**Provider.** The agent runs on **Gemini**, one `GEMINI_API_KEY`. The flagger and
verifier models are set by `FLAGGER_MODEL` / `VERIFIER_MODEL` (defaults in
`core/llm.py`) — different Google accounts expose different model
IDs, so rather than hardcode one here, the **exact model IDs used to produce the
committed results and trajectories are recorded** in
`eval/results/results_gemini.json` (`models`
field) and in every [`trajectories/*.json`](trajectories) (`model` per stage).
That's the source of truth for "what actually ran." With no key, the same code
path falls back to a deterministic offline pattern-matcher — a smoke test only
(see §Evaluation results), never a reported result.

## Baselines

Two baselines set the bar the agent has to beat, each a fair stand-in for how the
problem gets handled without an agent:

- **Random 5% sample** — reviews ~5% of calls (seeded, reproducible) and reports
  only what that slice catches. This *is* the status quo: it mirrors the manual
  spot-check rate a human team actually sustains, so it's the honest measure of
  the coverage gap.
- **Keyword match** — a short keyword/regex list per rule, scanning 100% of
  calls with no grounding. This is the "simple script" a team would realistically
  build first, so it's the fair bar for whether the LLM agent earns its keep.

## Improvement Changelog

The real iteration history — what was tried, the evidence it produced, and what
changed as a result:

| Stage | What you tried and why | Evidence | Decision / Learning |
| --- | --- | --- | --- |
| **Baselines + fixtures** | Build 10 fixtures + held-out ground truth, then the two baselines, to quantify the gap before any agent. | Keyword: 5/8 caught, 3 false positives. Random 5%: 1/10 calls reviewed. | Bar set: 100% coverage is the prize; keyword's false alarms are the quality gap to beat. |
| **Offline smoke test** | Deterministic pattern-matcher so the whole flag→verify→route→score path runs with no key. | Pipeline runs end to end; 9 tests pass with zero credentials. | Keep it as CI/plumbing only — its pattern list is fitted to the fixtures, so its score is not a result. |
| **First Gemini run** | Wire the real model and run the full eval. | Hit `429`/`503` on the free tier; 2 calls dropped, coverage fell to 80%. | Added retry-with-backoff (honoring the server's delay) + per-call isolation; moved the flagger to `gemini-2.5-flash` for a larger free quota. |
| **Precision audit** | Suspicious that "2 false positives" was too clean, audited every grounded flag line-by-line. | The harness's per-call convention reported 2 FPs (precision 0.80); a line-aware count found **6** real extra flags (0.571) — the convention was hiding 4. | Report precision as a range and lead with the strict 0.571; save per-call detail for audit. |
| **Ground-truth finding** | Read the actual reasoning behind the extra flags on call_05/call_10. | All extra flags are verbatim, quote-checked lines; both clean calls flagged nothing. | It's the answer key under-labeling real violations, not the agent over-flagging (see Hot take). Future work: multi-label ground truth. |

## Evaluation results

The system scored as "the agent" is the **real Gemini pipeline**. Its measured
numbers against the two baselines over the same 10 held-out fixtures:

| Metric | Random 5% | Keyword match | **Gemini agent** |
| --- | --- | --- | --- |
| Coverage (% reviewed) | 10% | 100% | **100%** |
| Violations caught | 0 / 8 | 5 / 8 | **8 / 8** |
| Recall | 0.0 | 0.63 | **1.0** |
| Precision | 0.0 | 0.63 | **0.571** |

**Recall is 1.0 — the agent missed nothing.** Precision is **0.571 under strict
line-and-rule scoring** (a flag counts only if its exact line *and* rule match
the single ground-truth label). Under a per-call convention — right rule *somewhere*
on a violation call — precision is **0.80**. The gap between the two is entirely
call_05 and call_10, where the agent grounded extra *real* violations the answer
key doesn't label; on the two genuinely-clean calls it flagged nothing. See the
[Hot take](#hot-take).

The two cases that separate a scanner from an agent:
- **call&#95;09** ("the rate resets at midnight… that's not something I control") —
  surface urgency language, but a genuine external deadline. The keyword
  baseline flags it (**false positive**); the agent does not.
- **call&#95;10** ("in fifteen years selling this, nobody's ever lost money") — an
  implied guarantee with no keyword to match. The keyword baseline misses it
  (**false negative**); the agent grounds it.

### Offline mode is a smoke test, not a second result

The pipeline also runs with **no API key**, via a deterministic pattern-matcher
(`core/heuristics.py`). Its *only* purpose is to confirm the whole
flag → verify → route → score path executes end to end — for CI and for reading
the code without credentials. **It is not a second agent and its scores are not
reported as results.** Its pattern list was written with knowledge of these 10
fixtures — it literally contains phrases like `"nobody's walked away with less"`
lifted from call_10 — so it is fitted to this exact test set. A perfect offline
score is expected and is not evidence of any general capability.

## Hot take

The single most valuable component is **free**: the plain-Python quote check.
Most of the reliability gain over the keyword baseline comes not from a bigger
model but from *forcing every claim to cite a verbatim line and one specific
rule*, then throwing away anything that can't survive that grounding. Cheap
verification beats confident generation.

**Finding — the answer key is coarser than reality.** Calls 05 and 10 were each
written with a second line reinforcing the labeled violation, and ground truth
deliberately labels only one line per call. Running the real agent exposed the
fixtures under-labeling in two ways: (1) multi-line — it caught both the labeled
line and the unlabeled reinforcing line for the same rule (e.g. call_05 line 5,
'designed to be risk-free for your principal', P-07); and (2) multi-rule — the
offending utterances violate two overlapping rules at once ('completely safe,
you can't lose money' is both an implied guarantee, P-01, and a risk
misrepresentation, P-07), so it grounded both. Every one of these is a verbatim,
quote-checked line, and both genuinely-clean calls (02, 09) were flagged with
nothing — so this is the ground truth under-labeling real violations, not the
agent inventing them. Under strict line-and-rule scoring they count against
precision (0.571); a future iteration would extend ground truth to allow
multiple labeled (line, policy) violations per call, recovering precision toward
1.0.

## Known limitations

Specific to what was and wasn't tested — not general hedging.

- **Audio was tested on clean TTS, not real calls.** The round-trip was
  validated only on synthetic text-to-speech audio. Real telephony audio is
  compressed and narrowband, with background noise, crosstalk, and accents that
  TTS never produces. Transcription accuracy on real call audio has **not** been
  tested and must not be inferred from the clean-TTS result.
- **Only clean two-speaker turn-taking was exercised.** The test audio had
  exactly two speakers alternating cleanly. Real calls can include a third party
  joining, hold/transfer hand-offs, an IVR voice, or overlapping speech — none
  of which was tested. Speaker diarization (labeling Agent vs Customer) is
  expected to degrade under any of these.
- **Violations by omission are out of scope by design.** The flagger can only
  flag a line it can quote. A whole class of real compliance failures are
  *omissions* — a required disclosure never made, an identity check skipped, a
  cooling-off notice not given. There is no line to quote, so this architecture
  cannot catch them as designed, and a meaningful share of real-world violations
  fall in this category.
- **Real audio means real PII leaving the building.** Real customer calls
  contain PII — account numbers, sometimes spoken SSNs — which this design would
  send to a third-party API. That is a data-governance and vendor-agreement
  question, not something code fixes, and it is a precondition to any real
  deployment, not a TODO.
- **Free-tier throughput is far below call-center volume.** The free API tier is
  orders of magnitude below real call volume. Production would require paid
  throughput, request queuing, and active cost management — none of which this
  build addresses.

## What pre-existed vs. what's new this weekend

Disclosure of reuse. The only pre-existing dependency is **audio-transcription-system**,
a separate prior project. This build reuses exactly two things from it: the
general *approach* of turning call audio into the transcript JSON schema, and the
shared `GEMINI_API_KEY` (one credential to document).

Everything in this repository was written this weekend. Specifically,
`agent/transcribe.py` was written fresh from the google-genai SDK and the approach
described in `docs/IMPLEMENTATION_PLAN.md`; the audio-transcription-system's own
source code was **not opened, read, or copied** while writing it — verified: no
such source exists in this repo or its git history, and it was not referenced
during the build. The reuse is conceptual and credential-level, not code-level.

## Cost and reproducibility

This is transparency about what it costs a judge to reproduce the eval — not a
claim that the system is free or that "free" is a competitive advantage. At this
eval's scale — 10 calls, roughly 20–30 total API requests (one flagger call per
transcript plus one scoped verifier call per surviving flag) — a full Gemini run
stays within Google's free tier. Free-tier terms change, so rather than hardcode a
rate limit, see the official pricing:
<https://ai.google.dev/gemini-api/docs/pricing>. `REPRODUCTION.md`
has the full cost/runtime breakdown and the exact model IDs used.

---

## Running it yourself

Requires Python 3.9+. `make test` and `make baseline` need **no** dependencies
or API key; `make agent` / `make eval` need a `GEMINI_API_KEY`.

### With `make` (recommended)

| Command | What it does | Needs key? |
| --- | --- | --- |
| `make setup` | create the venv and install dependencies | — |
| `make test` | run the 9-test suite | no |
| `make baseline` | run both baselines over the fixtures | no |
| `make agent` | run the Gemini agent over all transcripts | yes |
| `make eval` | score baselines + agent vs. ground truth (writes `eval/results/`) | yes |
| `make clean` | remove caches and the venv | — |

```bash
make setup
cp .env.example .env      # add GEMINI_API_KEY (only for make agent / make eval)
make eval                 # scored result on the real Gemini agent
make test                 # no key needed
```

`make help` lists every target.

### Without `make` (raw equivalents, e.g. Windows)

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt  # make setup
python -m unittest discover -s tests -v          # make test  (no key)
python -m eval.run_eval --provider gemini        # make eval
python -m agent.pipeline --provider gemini       # make agent
python -m eval.run_eval --provider offline       # no key: offline smoke test
python -m agent.pipeline --call call_10 --provider gemini   # inspect one call end-to-end
```

## Repo layout

```
data/            policy.json · transcripts/ · ground_truth.json (held out) · audio/
core/            shared library: models, data loading, prompts, heuristics, LLM client, logging
baseline/        random_sample.py · keyword_match.py
agent/           flagger.py · verifier.py · router.py · pipeline.py · transcribe.py (optional)
eval/            run_eval.py · results/ (per-run tables + patterns.md = recurring-rule aggregation)
trajectories/    per-call JSON + Markdown logs
tests/           end-to-end + unit tests (run on the offline smoke test)
scripts/         generate_sample_audio.py (optional TTS demo)
```

## Optional: audio ingestion

Audio is an alternative front-end that produces the *same* transcript JSON the
flagger already consumes — nothing downstream changes.

```bash
pip install gTTS
python scripts/generate_sample_audio.py                         # make sample clips
# One command: transcribe the audio, then run the full pipeline on it.
python -m agent.pipeline --audio data/audio/call_01.mp3 --provider gemini
```

The round-trip was validated once on clean TTS audio: `call_01.mp3` transcribed
back with correct Agent/Customer labels and the "I can guarantee you'll see at
least 8%" line intact, and the pipeline then ran unchanged on it. This is a
capability demo, not a robustness claim — see [Known limitations](#known-limitations)
for exactly what was and wasn't tested.

See `docs/IMPLEMENTATION_PLAN.md` for the full
build spec and the exact instructions handed to each agent stage.
