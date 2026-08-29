# Compliance Catch — eval results (agent provider: `gemini`)

_Generated 2026-08-29T23:55:28 · 10 fixtures · models: flagger `gemini-2.5-flash`, verifier `gemini-flash-lite-latest`_

| Metric | Random 5% | Keyword match | Agent | Δ (keyword → agent) |
|---|---|---|---|---|
| Coverage (% reviewed) | 10.0% | 100.0% | 100.0% | 0.0% |
| Violations caught (TP) | 0 | 5 | 8 | +3 |
| False negatives | 8 | 3 | 0 | -3 |
| Recall | 0.0 | 0.625 | 1.0 | +0.375 |
| Precision — per-call | 0.0 | 0.625 | 0.8 | +0.175 |
| Precision — strict (line + rule) | 0.0 | 0.455 | 0.571 | +0.116 |
| False positives — per-call | 0 | 3 | 2 | -1 |
| False positives — strict (line + rule) | 0 | 6 | 6 | 0 |
| Routed to needs-review | 0 | 0 | 6 | +6 |

**Headline:** the keyword baseline flags the external-deadline near-miss (call_09, a false positive) and misses the implied guarantee (call_10); the agent reviews 100% of calls with recall 1.0. Precision is shown under both conventions — per-call (line ignored) and strict (line + rule); the gap is the multi-rule/multi-line flags on call_05 and call_10 that the single-label ground truth cannot credit (see the README Hot Take).
