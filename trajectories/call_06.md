# Trajectory — call_06

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
    "line": 3,
    "quote": "Actually, I went ahead and enrolled you in our Premium Checking tier instead since it has more features.",
    "policy_id": "P-08",
    "reasoning": "Agent substitutes or upgrades the product without the customer's consent.",
    "severity": "medium"
  }
]
```

## 2. verifier:recheck  ·  `offline-heuristic`  ·  2026-08-29T10:05:10

**Input**

```
{
  "quote": "Actually, I went ahead and enrolled you in our Premium Checking tier instead since it has more features.",
  "policy_id": "P-08",
  "rule_text": "Agents must not enroll or upgrade a customer into a different product than the one requested without explicit, recorded consent."
}
```

**Output**

```json
{
  "verdict": "yes",
  "justification": "Offline scoped re-check on the single line + cited rule."
}
```
