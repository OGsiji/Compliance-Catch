# Nigerian-context transcripts (qualitative, unscored)

Three synthetic, hand-written calls in Nigerian English with Nigerian Pidgin
code-switching, used for an informal check of how the pipeline handles
non-US-English phrasing. They live in this subfolder so the scored eval (which
globs only `data/transcripts/*.json`) never loads them, and they have **no
entry in `ground_truth.json`**. Lender names, people, and numbers are fictional.

Run one with `make call CALL=ng_01 PROVIDER=gemini`; trajectories land in
`trajectories/ng_0*.{json,md}`.

What each call was written to contain (the author's intent, not a scored
answer key):

| Call | Scenario | Intended violations |
| --- | --- | --- |
| `ng_01` | Loan-app collections call, heavy Pidgin | P-03 line 3 (balance before ID check) · P-11 line 5 (contact-list shaming threat) and line 7 (police threat for a civil debt) · P-04 lines 5/11 (6pm deadline) · P-12 line 9 (top-up loan pushed after the customer discloses job loss) · P-02 line 11 (interest deflected) |
| `ng_02` | SME loan-terms call, English with light code-switching | P-04 line 7 ("only until we end this call") · P-02 line 11 (management fee + insurance disclosed only after acceptance at line 8) · P-10 line 13 (dissatisfaction brushed off, no escalation path) |
| `ng_03` | Collections call done right, Pidgin | None — control. Recording disclosure, ID check before account details, bereavement handled per P-12, complaints path given. Tests whether Pidgin alone triggers flags. |

Omissions (no cooling-off notice in `ng_02`, no recording disclosure in
`ng_01`) are presence-mode rules the line-level flagger cannot quote, so they
are out of scope by design — see the main README's Known limitations.

## What happened (Gemini run, 2026-10-22)

Flagger `gemini-2.5-flash`, verifier `gemini-flash-lite-latest`; full records in
`trajectories/ng_0*.md`.

| Call | Grounded | Sent to needs review | Missed entirely |
| --- | --- | --- | --- |
| `ng_01` | P-03 L3 · P-11 L5 · P-11 L7 · P-12 L9 · P-04 L11 · P-04 L13 | P-02 L11 | — |
| `ng_02` | P-04 L7 | P-02 L9 · P-02 L11 · P-10 L13 | — |
| `ng_03` | — | — | — (no candidate flags at all) |

- **The flagger surfaced every intended violation** (9 of 9) despite the Pidgin,
  and proposed nothing on the clean Pidgin control call.
- **No grounded flag is wrong.** All but one match an intended violation; the
  extra, P-04 on `ng_01` L13 ("Think fast o"), is a defensible second read of
  the same pressure.
- **The three intended violations that were demoted all need context outside
  the quoted line.** The verifier sees only that line, so it can't see that
  the `ng_01` interest dodge (L11) answers a direct question at L10, that the
  `ng_02` fee (L11) came *after* the customer accepted at L8, or that the
  dismissal at L13 answers a complaint at L12. Same pattern as `call_15`'s P-02 miss. They still
  reach a human as needs review rather than being dropped.
