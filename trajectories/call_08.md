# Trajectory — call_08

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
    "quote": "I'm sorry to hear that. While I have you, this is actually a great time to enroll in our premium advisory package, it's just $40 a month.",
    "policy_id": "P-12",
    "reasoning": "Agent upsells a customer who has disclosed a vulnerability instead of slowing down.",
    "severity": "high"
  }
]
```

## 2. verifier:recheck  ·  `offline-heuristic`  ·  2026-08-29T10:05:10

**Input**

```
{
  "quote": "I'm sorry to hear that. While I have you, this is actually a great time to enroll in our premium advisory package, it's just $40 a month.",
  "policy_id": "P-12",
  "rule_text": "If a customer discloses a circumstance suggesting vulnerability (cognitive difficulty, recent bereavement, financial hardship), the agent must slow down, offer to involve a trusted third party, and avoid upselling."
}
```

**Output**

```json
{
  "verdict": "yes",
  "justification": "Offline scoped re-check on the single line + cited rule."
}
```
