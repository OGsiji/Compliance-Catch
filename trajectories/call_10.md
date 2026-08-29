# Trajectory — call_10

## 1. flagger  ·  `offline-heuristic`  ·  2026-08-29T10:05:10

**Input**

```
{
  "note": "offline heuristic flagger",
  "n_lines": 6
}
```

**Output**

```json
[
  {
    "line": 3,
    "quote": "That's a fair concern. But honestly, in the fifteen years I've sold this product, nobody's ever lost money.",
    "policy_id": "P-01",
    "reasoning": "Agent states or implies a guarantee of returns or that no money can be lost.",
    "severity": "high"
  },
  {
    "line": 5,
    "quote": "There's always some risk on paper, but in practice, like I said, nobody's walked away with less than they put in.",
    "policy_id": "P-01",
    "reasoning": "Agent states or implies a guarantee of returns or that no money can be lost.",
    "severity": "high"
  }
]
```

## 2. verifier:recheck  ·  `offline-heuristic`  ·  2026-08-29T10:05:10

**Input**

```
{
  "quote": "That's a fair concern. But honestly, in the fifteen years I've sold this product, nobody's ever lost money.",
  "policy_id": "P-01",
  "rule_text": "Agents must not state or imply that any account, investment, or product will guarantee returns, gains, principal protection, or freedom from loss."
}
```

**Output**

```json
{
  "verdict": "yes",
  "justification": "Offline scoped re-check on the single line + cited rule."
}
```

## 3. verifier:recheck  ·  `offline-heuristic`  ·  2026-08-29T10:05:10

**Input**

```
{
  "quote": "There's always some risk on paper, but in practice, like I said, nobody's walked away with less than they put in.",
  "policy_id": "P-01",
  "rule_text": "Agents must not state or imply that any account, investment, or product will guarantee returns, gains, principal protection, or freedom from loss."
}
```

**Output**

```json
{
  "verdict": "yes",
  "justification": "Offline scoped re-check on the single line + cited rule."
}
```
