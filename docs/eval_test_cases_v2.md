# Eval test cases — Compliance Catch (v2, replaces eval_test_cases.md)

The old `eval_test_cases.md` was written for the abandoned
data-contract-validator idea and does not apply here — ignore it or
delete it. These 10 call-transcript scenarios are the real fixture list.

| # | Scenario | Targets | Ground truth |
|---|---|---|---|
| 1 | Agent states an explicit guaranteed return ("guaranteed 8% every year") | P-01 | Violation, high severity |
| 2 | Clean call — full disclosure, proper ID verification, no pressure | — | No violation (negative control) |
| 3 | Agent discusses account balance after only asking the customer's name (one identifier, not two) | P-03 | Violation, medium |
| 4 | Agent manufactures urgency ("only if you sign up in the next 3 minutes") | P-04 | Violation, medium |
| 5 | Agent calls a variable annuity "completely safe, you can't lose money" | P-07 | Violation, high |
| 6 | Agent silently enrolls the customer in a different product than requested | P-08 | Violation, medium |
| 7 | Agent implies a product isn't suitable "for someone your age" | P-06 | Violation, high |
| 8 | Customer discloses recent bereavement and confusion; agent proceeds with an upsell instead of slowing down | P-12 | Violation, high |
| 9 | Agent uses urgency language, but about a real external deadline ("the rate resets at midnight, that's not something I control") | P-04 (should NOT trigger) | No violation — tests false-positive avoidance |
| 10 | **Hard case:** agent never says "guarantee," but says "in fifteen years selling this, nobody's ever lost money" | P-01 (implied) | Violation, but only catchable via implication, not a keyword match — this is your headline hard case |

## Why this set works

- Cases 1, 3, 5, 6, 7, 8 are unambiguous positives — sanity-check that
  the pipeline catches the obvious stuff before trusting it on anything
  subtle.
- Case 2 is your only clean call — without a true negative, you can't
  measure false-positive rate at all.
- Case 9 is a deliberate near-miss: surface-level pattern matches P-04's
  trigger language but isn't actually a violation. The keyword baseline
  will almost certainly flag it; the point is showing the agent (with
  reasoning, not just matching) doesn't.
- Case 10 is the one worth writing first if you're short on time — it's
  the case that produces your Measured Improvement evidence and your
  Hot Take in one shot, however it resolves.

**Note:** case 6 was originally planned as a P-09 (recording disclosure)
violation, but that's an absence — nothing to quote — and the flagger is
designed to flag specific lines, not missing ones. Swapped to P-08
(unauthorized product substitution) instead, which has an explicit
violating line. P-09 stays in the policy document; it's just not
exercised by this fixture set, which is fine — a real eval set doesn't
need to trigger every rule.
