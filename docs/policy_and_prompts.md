# Policy document + agent prompts

## policy.json content

```json
{
  "rules": [
    {"id": "P-01", "title": "No guaranteed returns",
     "text": "Agents must not state or imply that any account, investment, or product will guarantee returns, gains, principal protection, or freedom from loss."},
    {"id": "P-02", "title": "Fee disclosure",
     "text": "Any fee, penalty, charge, or rate relevant to the product being discussed must be clearly stated to the customer before they commit to opening, upgrading, or purchasing it."},
    {"id": "P-03", "title": "Identity verification",
     "text": "Account-specific details (balance, transaction history, personal information) may not be discussed until the customer's identity has been verified using at least two identifiers."},
    {"id": "P-04", "title": "No high-pressure tactics",
     "text": "Agents must not use artificial urgency to pressure a customer into an immediate decision on a financial product."},
    {"id": "P-05", "title": "Cooling-off period",
     "text": "For credit products and insurance add-ons, the agent must inform the customer of their right to cancel within the statutory cooling-off period."},
    {"id": "P-06", "title": "No discriminatory language",
     "text": "Agents must not make statements that reference or imply differential treatment based on a customer's age, race, gender, religion, national origin, or disability."},
    {"id": "P-07", "title": "Accurate risk representation",
     "text": "Agents must not understate the risk level of an investment product or describe a variable-return product as safe or risk-free."},
    {"id": "P-08", "title": "No unauthorized product substitution",
     "text": "Agents must not enroll or upgrade a customer into a different product than the one requested without explicit, recorded consent."},
    {"id": "P-09", "title": "Call recording disclosure",
     "text": "Agents must inform the customer that the call may be recorded for quality and compliance purposes, at or near the start of the call."},
    {"id": "P-10", "title": "Complaint handling",
     "text": "If a customer expresses dissatisfaction or asks to file a complaint, the agent must acknowledge it and provide the complaint escalation path."},
    {"id": "P-11", "title": "No unauthorized collections threats",
     "text": "Agents must not threaten legal action, wage garnishment, or credit consequences that are not accurate or authorized by policy."},
    {"id": "P-12", "title": "Vulnerable customer protocol",
     "text": "If a customer discloses a circumstance suggesting vulnerability (cognitive difficulty, recent bereavement, financial hardship), the agent must slow down, offer to involve a trusted third party, and avoid upselling."}
  ]
}
```

12 rules, spanning disclosure, pressure tactics, discrimination, risk
representation, and vulnerable-customer handling — enough spread that
your 10 transcripts can each target a different rule without repeating.

## Flagger prompt

```
You are reviewing a customer service call transcript for a financial
services company for compliance violations. You will be given the full
transcript (numbered lines, each with a speaker label) and a list of
compliance policy rules, each with an ID and full text.

Your job: identify every line where the Agent's language plausibly
violates one of the listed policy rules. For each candidate violation,
output:
- line: the line number
- quote: the exact text of that line, copied verbatim from the transcript
- policy_id: the ID of the rule you believe is violated
- reasoning: one sentence explaining why
- severity: low, medium, or high

Only flag lines spoken by the Agent. Do not paraphrase the quote — copy
it exactly as it appears in the transcript, since a downstream system
will verify it against the original text. It's fine to flag a borderline
case; a second system will independently check every flag you produce.
It is not fine to invent a quote that isn't there.

Output valid JSON only: a list of objects with the fields above.
```

## Verifier — step 1 (no prompt, plain Python)

Normalize whitespace on both sides, then check `quote` is an exact
substring of the transcript text at the stated `line`. Fail → route to
"needs review" immediately, skip step 2 (saves an LLM call and money).

## Verifier — step 2 (scoped LLM re-check)

```
You are checking a single flagged compliance issue. You will be given
exactly one line from a call transcript and the text of exactly one
policy rule — nothing else.

Line: "{quote}"
Policy rule {policy_id}: "{rule_text}"

Question: does this line, on its own, violate this specific rule?
Consider both explicit and clearly implied violations — for example, a
strong implied guarantee counts even without the word "guarantee."
Answer with:
- verdict: yes or no
- justification: one sentence

Output valid JSON only.
```

Deliberately narrow — this call never sees the full policy list or the
full transcript, only the one line and the one rule. That's what limits
its ability to hallucinate a justification for something unrelated.
