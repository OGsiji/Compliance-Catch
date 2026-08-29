# Trajectory — call_05

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
    "quote": "I understand, but honestly, this one is completely safe, you can't lose money with it.",
    "policy_id": "P-07",
    "reasoning": "Agent describes a variable-return product as safe or risk-free.",
    "severity": "high"
  },
  {
    "line": 5,
    "quote": "Even then, it's designed to be risk-free for your principal.",
    "policy_id": "P-07",
    "reasoning": "Agent describes a variable-return product as safe or risk-free.",
    "severity": "high"
  }
]
```

## 2. verifier:recheck  ·  `offline-heuristic`  ·  2026-08-29T10:05:10

**Input**

```
{
  "quote": "I understand, but honestly, this one is completely safe, you can't lose money with it.",
  "policy_id": "P-07",
  "rule_text": "Agents must not understate the risk level of an investment product or describe a variable-return product as safe or risk-free."
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
  "quote": "Even then, it's designed to be risk-free for your principal.",
  "policy_id": "P-07",
  "rule_text": "Agents must not understate the risk level of an investment product or describe a variable-return product as safe or risk-free."
}
```

**Output**

```json
{
  "verdict": "yes",
  "justification": "Offline scoped re-check on the single line + cited rule."
}
```
