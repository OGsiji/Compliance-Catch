# Trajectory — call_07

## 1. flagger  ·  `offline-heuristic`  ·  2026-08-29T10:05:10

**Input**

```
{
  "note": "offline heuristic flagger",
  "n_lines": 5
}
```

**Output**

```json
[
  {
    "line": 3,
    "quote": "Honestly, an aggressive growth fund really isn't suitable for someone your age, I'd steer you toward something more conservative instead.",
    "policy_id": "P-06",
    "reasoning": "Agent implies differential treatment based on a protected characteristic.",
    "severity": "high"
  }
]
```

## 2. verifier:recheck  ·  `offline-heuristic`  ·  2026-08-29T10:05:10

**Input**

```
{
  "quote": "Honestly, an aggressive growth fund really isn't suitable for someone your age, I'd steer you toward something more conservative instead.",
  "policy_id": "P-06",
  "rule_text": "Agents must not make statements that reference or imply differential treatment based on a customer's age, race, gender, religion, national origin, or disability."
}
```

**Output**

```json
{
  "verdict": "yes",
  "justification": "Offline scoped re-check on the single line + cited rule."
}
```
