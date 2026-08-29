# Compliance Catch — eval results (agent provider: `gemini`)

_Generated 2026-08-29T22:05:51 · 10 fixtures · models: flagger `gemini-2.5-flash`, verifier `gemini-flash-lite-latest`_

| Metric | Random 5% | Keyword match | Agent | Δ (keyword → agent) |
|---|---|---|---|---|
| Coverage (% reviewed) | 10.0% | 100.0% | 100.0% | 0.0% |
| Violations caught (TP) | 0 | 5 | 8 | +3 |
| False positives | 0 | 3 | 2 | -1 |
| False negatives | 8 | 3 | 0 | -3 |
| Precision | 0.0 | 0.625 | 0.8 | +0.175 |
| Recall | 0.0 | 0.625 | 1.0 | +0.375 |
| Routed to needs-review | 0 | 0 | 0 | 0 |

**Headline:** the keyword baseline flags the external-deadline near-miss (call_09, a false positive) and misses the implied guarantee (call_10); the agent grounds every flag against the transcript and the one cited rule, so it keeps 100% coverage without paying for it in false positives.
