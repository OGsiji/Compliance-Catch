# Compliance Catch — eval results (agent provider: `gemini`)

_Generated 2026-08-30T07:31:23 · 10 fixtures · models: flagger `gemini-2.5-flash`, verifier `gemini-flash-lite-latest`_

| Metric | Random 5% rate | Keyword match | Flagger only (no verifier) | Agent (full) |
|---|---|---|---|---|
| Coverage (% reviewed) | 10.0% | 100.0% | 100.0% | 100.0% |
| Violations caught (TP) | 0 | 5 | 8 | 8 |
| False negatives | 8 | 3 | 0 | 0 |
| Recall | 0.0 | 0.625 | 1.0 | 1.0 |
| Precision — per-call | 0.0 | 0.625 | 0.615 | 0.8 |
| Precision — strict (line + rule) | 0.0 | 0.455 | 0.4 | 0.571 |
| False positives — per-call | 0 | 3 | 5 | 2 |
| False positives — strict (line + rule) | 0 | 6 | 12 | 6 |
| Routed to needs-review | 0 | 0 | 0 | 6 |

**Headline:** the keyword baseline flags the external-deadline near-miss (call_09, a false positive) and misses the implied guarantee (call_10); the agent reviews 100% of calls with recall 1.0. Precision is shown under both conventions — per-call (line ignored) and strict (line + rule); the gap is the multi-rule/multi-line flags on call_05 and call_10 that the single-label ground truth cannot credit (see the README Hot Take). The flagger alone produced 20 candidate flags; 0 (0%) fail the verbatim quote check — exactly what the verifier's grounding step 1 removes before anything is reported.
