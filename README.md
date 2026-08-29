# Compliance Catch

A two-stage LLM agent that reviews financial-services call transcripts for
compliance violations — and, unlike a keyword scanner, **grounds every flag it
reports** against the source text and the specific rule it cites, so it earns
100% review coverage while catching violations a keyword list can't.

> **The gap it closes:** a compliance team can only manually spot-check a tiny
> fraction of calls (our random-sample baseline reviews ~5%). A naive keyword
> scanner reviews everything but flags near-misses and misses anything phrased
> indirectly. Compliance Catch reviews 100% *and* grounds every flag.

---

## Results — the agent vs. the baselines (10 held-out fixtures)

The system being scored as "the agent" is the **real Gemini pipeline**
(`gemini-2.5-flash` flagger + `gemini-flash-lite-latest` verifier). These are
its measured numbers, against the two baselines over the same fixtures:

| Metric | Random 5% | Keyword match | **Gemini agent** |
| --- | --- | --- | --- |
| Coverage (% reviewed) | 10% | 100% | **100%** |
| Violations caught | 0 / 8 | 5 / 8 | **8 / 8** |
| Recall | 0.0 | 0.63 | **1.0** |
| Precision | 0.0 | 0.63 | **0.571** |

**Recall is 1.0 — the agent missed nothing.** Precision is **0.571 under strict
line-and-rule scoring** (0.80 if scored per call instead). The entire gap comes
from two fixtures where the agent grounded *extra real violations the answer key
didn't label* — not false alarms; on the two genuinely-clean calls it flagged
nothing. See the [Hot take](#hot-take) for the full breakdown.

The two cases that separate a scanner from an agent:
- **call_09** ("the rate resets at midnight… that's not something I control") —
  surface urgency language, but a genuine external deadline. The keyword
  baseline flags it (**false positive**); the agent does not.
- **call_10** ("in fifteen years selling this, nobody's ever lost money") — an
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

---

## How it works

```
transcript + policy ─▶ Flagger ─▶ candidate flags ─▶ Verifier ─▶ Router ─▶ report
   (full context)      (pass 1)                       (pass 2)              (grounded /
                                                                            needs review)
```

**Flagger (pass 1)** — sees the *full* transcript and *full* policy list, and
proposes candidate violations: `{line, quote, policy_id, reasoning, severity}`.

**Verifier (pass 2)** — two **independent** checks, not one model grading itself:
1. **Programmatic quote check** (plain Python, no LLM). Is the flagged `quote`
   present verbatim (whitespace-normalized) at the stated line? If not → routed
   straight to *needs review*, no LLM call spent. This is what makes the
   grounding real instead of a model re-asserting confidence.
2. **Scoped policy re-check** (narrow LLM call). Shown *only* the one quoted
   line and the *one* cited rule — never the whole transcript or policy — and
   asked yes/no. "No" downgrades to *needs review*; "yes" marks it *grounded*.

**Router** — assembles the clean per-call report: quote, policy citation,
severity, status, reasoning. Nothing else.

Every flagger and verifier call is written to [`/trajectories`](trajectories)
as JSON plus a human-readable Markdown render, so a reviewer can follow
instructions → response → decision without reading the code.

### Provider

The agent runs on **Gemini** — `gemini-2.5-flash` (flagger) and
`gemini-flash-lite-latest` (verifier), one `GEMINI_API_KEY`. With no key, the
same code path falls back to the deterministic offline pattern-matcher described
above, which is a smoke test only — never a reported result.

---

## Quickstart

Requires Python 3.9+. The tests and the offline smoke test need **no**
dependencies or API key; the scored agent needs a Gemini key.

```bash
# 1. Real agent — install deps and add your key
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # add GEMINI_API_KEY

# 2. Run the scored eval on the real Gemini agent
python -m eval.run_eval --provider gemini

# 3. Inspect a single call end-to-end
python -m agent.pipeline --call call_10 --provider gemini

# 4. Run the tests (no key required)
python -m unittest discover -s tests -v

# (No key? `python -m eval.run_eval --provider offline` runs the smoke test.)
```

---

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

---

## Optional: audio ingestion

Audio is an alternative front-end that produces the *same* transcript JSON the
flagger already consumes — nothing downstream changes.

```bash
pip install gTTS
python scripts/generate_sample_audio.py                         # make sample clips
# One command: transcribe the audio, then run the full pipeline on it.
python -m agent.pipeline --audio data/audio/call_01.mp3 --provider gemini
# Or just produce a transcript JSON:
python -m agent.transcribe data/audio/call_01.mp3 --id call_01_audio --out /tmp/call_01_audio.json
```

The round-trip was validated once on clean TTS audio: `call_01.mp3` transcribed
back with correct Agent/Customer labels and the "I can guarantee you'll see at
least 8%" line intact, and the pipeline then ran unchanged on it. This is a
capability demo, not a robustness claim — see **Known limitations** below for
exactly what was and wasn't tested.

---

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

---

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

See [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) for the full
build spec and the exact instructions handed to each agent stage.
