# Trajectory — call_03

## 1. flagger  ·  `offline-heuristic`  ·  2026-08-29T10:05:10

**Input**

```
{
  "note": "offline heuristic flagger",
  "n_lines": 8
}
```

**Output**

```json
[
  {
    "line": 5,
    "quote": "Okay Lena, let me pull that up... your checking account balance is $3,214.60, and you have a pending transfer of $500 going out tomorrow.",
    "policy_id": "P-03",
    "reasoning": "Agent discloses account-specific details before verifying two identifiers.",
    "severity": "medium"
  }
]
```

## 2. verifier:recheck  ·  `offline-heuristic`  ·  2026-08-29T10:05:10

**Input**

```
{
  "quote": "Okay Lena, let me pull that up... your checking account balance is $3,214.60, and you have a pending transfer of $500 going out tomorrow.",
  "policy_id": "P-03",
  "rule_text": "Account-specific details (balance, transaction history, personal information) may not be discussed until the customer's identity has been verified using at least two identifiers."
}
```

**Output**

```json
{
  "verdict": "yes",
  "justification": "Offline scoped re-check on the single line + cited rule."
}
```
