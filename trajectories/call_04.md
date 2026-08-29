# Trajectory — call_04

## 1. flagger  ·  `offline-heuristic`  ·  2026-08-29T10:05:10

**Input**

```
{
  "note": "offline heuristic flagger",
  "n_lines": 7
}
```

**Output**

```json
[
  {
    "line": 5,
    "quote": "4.9%, but I should mention, this rate is only available if you sign up in the next 3 minutes, I have another call waiting after this.",
    "policy_id": "P-04",
    "reasoning": "Agent manufactures artificial urgency to force an immediate decision.",
    "severity": "medium"
  }
]
```

## 2. verifier:recheck  ·  `offline-heuristic`  ·  2026-08-29T10:05:10

**Input**

```
{
  "quote": "4.9%, but I should mention, this rate is only available if you sign up in the next 3 minutes, I have another call waiting after this.",
  "policy_id": "P-04",
  "rule_text": "Agents must not use artificial urgency to pressure a customer into an immediate decision on a financial product."
}
```

**Output**

```json
{
  "verdict": "yes",
  "justification": "Offline scoped re-check on the single line + cited rule."
}
```
