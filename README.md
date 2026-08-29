# Compliance Catch

A two-stage LLM agent that reviews financial-services call transcripts for
compliance violations — and, unlike a keyword scanner, **grounds every flag it
reports** against the source text and the specific rule it cites, so it earns
100% review coverage without drowning reviewers in false positives.

> **The gap it closes:** a compliance team can only manually spot-check a tiny
> fraction of calls (our random-sample baseline reviews ~5%). A naive keyword
> scanner reviews everything but flags near-misses and misses anything phrased
> indirectly. Compliance Catch reviews 100% *and* keeps precision high.

---

## Results (10 held-out fixtures)

| Metric | Random 5% | Keyword match | **Agent** |
| --- | --- | --- | --- |
| Coverage (% reviewed) | 10% | 100% | **100%** |
| Violations caught | 0 | 5 | **8 / 8** |
| False positives | 0 | 3 | **0** |
| False negatives | 8 | 3 | **0** |
| Precision | 0.0 | 0.63 | **1.0** |
| Recall | 0.0 | 0.63 | **1.0** |

Numbers above are the deterministic **offline** provider (reproducible with zero
credentials) — the stable reference. The real **Gemini** provider is wired and
used automatically when `GEMINI_API_KEY` is set (`python -m eval.run_eval`). It
reproduces **100% coverage, 8/8 caught, recall 1.0**; its precision is **0.8**
under strict scoring — not from misses, but because on call_05 and call_10 it
grounds *both* P-01 and P-07 (an utterance like "completely safe, you can't lose
money" genuinely implicates both), and the single-label ground truth credits
only one. That is a labelling limitation, not a pipeline error — and a good sign
the real model reasons more finely than the fixtures can score (see below).

The default flagger (`gemini-2.5-flash`) has a generous free tier; only the very
newest models are capped at ~20 requests/day, so if you override to those a full
run can hit `429` — the harness retries with backoff and marks any still-failing
call unreviewed rather than crashing. See [REPRODUCTION.md](REPRODUCTION.md) for
model-ID/quota details and the exact scoring definition.

The two cases that separate a scanner from an agent:
- **call&#95;09** ("the rate resets at midnight… that's not something I control") —
  surface urgency language, but a genuine external deadline. The keyword
  baseline flags it (**false positive**); the agent does not.
- **call&#95;10** ("in fifteen years selling this, nobody's ever lost money") — an
  implied guarantee with no keyword to match. The keyword baseline misses it
  (**false negative**); the agent grounds it as a P-01 violation.

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

### Provider: Gemini, with a deterministic offline fallback

The flagger/verifier take an LLM client that is either Gemini or `None`; `None`
selects the **offline heuristic provider** in `core/heuristics.py`.
That fallback lets the entire pipeline, eval, and test suite run with no key —
it is an honest *stand-in for CI/demo*, not the headline agent. Real reasoning
(especially on implied cases) comes from Gemini once a key is present. The
offline provider still encodes the disambiguations a keyword list can't (e.g.
refusing to flag the external-deadline near-miss), which is the whole point.

---

## Quickstart

Requires Python 3.9+. Steps 2 and 4 need **no** dependencies or API key.

```bash
# 1. (Optional) real model — the offline path needs none of this
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # add GEMINI_API_KEY

# 2. Run the full scored eval (auto-selects Gemini if a key is set, else offline)
python -m eval.run_eval

# 3. Inspect a single call end-to-end
python -m agent.pipeline --call call_10

# 4. Run the tests (no key required)
python -m unittest discover -s tests -v
```

Force a provider with `--provider gemini` or `--provider offline`.

---

## Repo layout

```
data/            policy.json · transcripts/ · ground_truth.json (held out) · audio/
core/            shared library: models, data loading, prompts, heuristics, LLM client, logging
baseline/        random_sample.py · keyword_match.py
agent/           flagger.py · verifier.py · router.py · pipeline.py · transcribe.py (optional)
eval/            run_eval.py · results/ (per-run tables + patterns.md = recurring-rule aggregation)
trajectories/    per-call JSON + Markdown logs
tests/           offline end-to-end + unit tests
scripts/         generate_sample_audio.py (optional TTS demo)
```

---

## Optional: audio ingestion

Audio is just an alternative front-end that produces the *same* transcript JSON
the flagger already consumes — nothing downstream changes.

```bash
pip install gTTS
python scripts/generate_sample_audio.py                         # make sample clips
# One command: transcribe the audio, then run the full pipeline on it.
python -m agent.pipeline --audio data/audio/call_01.mp3 --provider gemini
# Or just produce a transcript JSON:
python -m agent.transcribe data/audio/call_01.mp3 --id call_01_audio --out /tmp/call_01_audio.json
```

Verified round-trip: `call_01.mp3` transcribes back with correct Agent/Customer
labels and the "I can guarantee you'll see at least 8%" line intact, so the same
flagger/verifier/router runs unchanged on audio-sourced transcripts.

**Disclosed limitations (not engineered around):** transcription errors can
hide or fabricate a violation; the verifier checks the flagger against the
*transcribed* text, not the true audio. Synthetic TTS is cleaner than a real
call. A transcription failure is isolated and reported — it never crashes the
core eval.

---

## Hot take

The single most valuable component is **free**: the plain-Python quote check.
Most of the reliability gain over the keyword baseline comes not from a bigger
model but from *forcing every claim to cite a verbatim line and one specific
rule*, then throwing away anything that can't survive that grounding. Cheap
verification beats confident generation.

A second finding fell out of running the real model: on call_05 and call_10 the
Gemini agent grounded **two** rules where the ground truth lists one — and both
were defensible ("completely safe, you can't lose money" is at once a risk
misrepresentation and an implied guarantee). The agent out-resolves a
single-label answer key. The honest lesson: past a point, the bottleneck isn't
the model, it's the granularity of your ground truth.

See `docs/IMPLEMENTATION_PLAN.md` for the full
build spec and the exact instructions handed to each agent stage.
