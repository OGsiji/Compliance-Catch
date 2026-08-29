# Compliance Catch — implementation plan
This is the master build spec. `README_draft.md` and `eval_test_cases.md` (already produced) plug into this as the problem framing and the fixture list — this document is the "how to actually build it" layer, including what to hand a coding agent to scaffold the repo.
## Repo layout
```javascript
/data
  policy.json            # ~12 compliance rules
  transcripts/            # 10 synthetic call transcripts
  ground_truth.json       # violation labels, held out from the agent
/baseline
  random_sample.py         # 5% coverage baseline
  keyword_match.py         # simple rule-based baseline
/agent
  flagger.py               # pass 1: proposes candidate violations
  verifier.py               # pass 2: grounds or routes to review
  router.py                 # combines into the final report
/eval
  run_eval.py                # runs baseline + agent, scores against ground truth
  results/                    # output tables, one per run
/trajectories                # raw + human-readable logs per call
README.md
REPRODUCTION.md
CHANGELOG.md
.env.example
```
## Data schemas
**`policy.json`** — a flat list, each rule independently citable:
```javascript
{
  "rules": [
    {"id": "P-01", "title": "No guaranteed returns",
     "text": "Agents must not state or imply that any account or investment will guarantee returns, gains, or protection from loss."},
    {"id": "P-02", "title": "Fee disclosure",
     "text": "Any fee, penalty, or charge relevant to the product being discussed must be stated before the customer commits."},
    {"id": "P-03", "title": "Identity verification",
     "text": "Account-specific details may not be discussed until the customer's identity has been verified."}
  ]
}
```
Aim for ~10-15 rules covering a spread: guarantees, disclosures, pressure tactics, discriminatory language, identity verification, unauthorized substitutions, required cooling-off periods. Write these before anything else — the flagger and verifier both depend on this file existing and being final.
**`transcripts/call_XX.json`**:
```javascript
{
  "id": "call_01",
  "lines": [
    {"line": 1, "speaker": "Agent", "text": "..."},
    {"line": 2, "speaker": "Customer", "text": "..."}
  ]
}
```
**`ground_truth.json`** (eval-only, never shown to the agent):
```javascript
{
  "call_01": {"violation": true, "policy_id": "P-01", "line": 14, "severity": "high"},
  "call_02": {"violation": false}
}
```
## Baseline
- `random_sample.py` — selects ~5% of calls (round up to 1 if the set is small), reports only what that sample catches; everything else is reported as "not reviewed." This is what dramatizes the coverage gap.
- `keyword_match.py` — a short keyword/regex list per policy rule (e.g. "guarantee", "guaranteed return" for P-01), scans every call, flags matches with no severity or grounding. This is the "simple script/template" baseline the rubric names explicitly.
## Agent pipeline
**Flagger (`flagger.py`)**
- Input: full transcript + full policy list
- Prompt shape: "Review this transcript against the policy rules below. For each candidate violation, output the line number, the exact quoted text, the policy rule id you suspect it breaks, a one-sentence justification, and an initial severity (low/medium/high)."
- Output: JSON list of candidate flags — `{line, quote, policy_id, reasoning, severity}`
**Verifier (`verifier.py`)** — two independent checks, not one LLM self-assessment:
1. **Programmatic quote check** (plain Python, no LLM) — does `quote` appear verbatim (whitespace-normalized) at the stated `line` in the transcript? Fail → route straight to "needs review," no LLM call needed. This is the check that makes the verification real rather than another model asserting confidence.
2. **Scoped policy re-check** (narrow LLM call) — shown only the quoted line and the text of the one cited rule, nothing else. Prompt: "Does this line violate this specific rule? Answer yes/no with one sentence." No → downgrade to "needs review." Yes → mark grounded.
**Router (`router.py`)**
- Produces the final per-call report: quote, policy citation, severity, status (grounded / needs review), reasoning — nothing else. This is the artifact End-to-End Quality is scored on, so keep it exactly this clean.
## Eval harness (`eval/run_eval.py`)
Runs both baselines and the agent pipeline over the same 10 fixtures, scores against `ground_truth.json`: violations caught, false positives, false negatives, coverage (% of calls actually reviewed — this is where 5% vs 100% becomes visible), and writes the results table in the format the PDF suggests (metric / baseline / agent / change).
## Trajectory logging
Every flagger and verifier call writes to `/trajectories` as JSON (`{timestamp, stage, input, output, model}`), plus a markdown rendering per call so a judge can follow instructions → tool response → decision without reading raw JSON.
## Build order
1. **Tonight** — repo skeleton, `policy.json`, environment/dependencies pinned. Model choice: Gemini 2.5 Flash for the flagger, Gemini 2.5 Flash-Lite for the verifier's scoped re-check — both free tier, same `GEMINI_KEY` already needed for audio-transcription-system, so only one credential to document
2. **Day 1 AM** — write the 10 transcripts + `ground_truth.json` by hand (use `eval_test_cases_v2.md` as the scenario list — the earlier `eval_test_cases.md` was for a different, abandoned idea; ignore it)
3. **Day 1 midday** — both baselines + eval harness skeleton (even with the agent stubbed out, this lets you test scoring logic early)
4. **Day 1 PM – Day 2 AM** — flagger; iterate on the prompt against a few fixtures manually before trusting it
5. **Day 2 midday** — verifier: programmatic check first (it's free and catches a lot), then the scoped LLM re-check
6. **Day 2 PM** — router, full eval run, save results + trajectories
7. **Day 2 evening** — fix whatever the hard case (unit-drift, or whichever ambiguous case you wrote) actually reveals; this becomes your changelog's real final entry and the hot take
8. **Day 3** — README with real numbers, REPRODUCTION.md, record video, submit with hours to spare
Audio ingestion and deployment are both explicitly out of this order — add audio only if 1-7 are solid with time left; skip deployment entirely.
## Instructions to hand your coding agent
Paste this as the initial brief (adjust the model/API specifics to what you're actually using):
> Build a Python project matching the repo layout below. Two-stage agent pipeline: a flagger that proposes candidate compliance violations in a call transcript against a policy document, and a verifier that independently grounds each flag — first with a plain string match confirming the quoted line exists verbatim in the transcript, then with a narrow LLM call shown only that line and the one cited policy rule (not the full document). Flags that fail either check go to a "needs review" bucket instead of being reported as confirmed. Also build two baselines (5% random sample, keyword matching) and an eval script that scores both against a held-out ground truth file and writes a results table. Log every LLM call (prompt + response) to /trajectories as JSON. No database, no web UI — CLI scripts and flat JSON files only. [paste repo layout, schemas, and prompt shapes from above]
Keep this instruction text — the PDF requires disclosing the actual instructions that shaped each agent, and this is that record.
## Audio ingestion (optional, added after the core pipeline works)
Architecture: audio is just an alternative way to produce the same `data/transcripts/call_XX.json` schema the flagger already consumes. Nothing downstream (baseline, flagger, verifier, router, eval) changes. The system accepts either input path:
- a transcript JSON directly (the default, already built)
- a raw audio file, converted to that same JSON by `agent/transcribe.py` before being handed to the flagger
**Test audio samples:**
- Commit actual audio files into `/data/audio/` directly in the repo — no external hosting, no Google Drive dependency (that was the whole point of extracting a subset instead of depending on the full audio-transcription-system service).
- Generate them with a free, scriptable TTS tool (gTTS or pyttsx3) using two distinct voices for Agent and Customer — reproducible by rerunning one script, not manual recording. Prompt the transcription step to label speakers directly as "Agent" and "Customer" rather than generic "Speaker 1/2", to avoid a separate, error-prone role-mapping step.
- Only generate audio for 2-3 representative calls (e.g. call_01, the clean call_02, and the hard case call_10) — this is a bonus capability demonstration for the video, not a replacement for the 10-transcript scored eval, which stays text-based and already works.
**Known limitations to disclose honestly, not engineer around:**
- Transcription errors upstream can hide or fabricate a violation — the verifier checks the flagger's output against the transcribed text, not the "true" audio, so a bad transcription is a real failure mode.
- Synthetic TTS audio is cleaner than a real call (no crosstalk, no filler words) — the audio demo proves the pipeline connects end to end, it doesn't prove real-world robustness.
- A transcription failure (bad audio, API error) must not block the core eval — isolate it, report it, don't let it crash the run.