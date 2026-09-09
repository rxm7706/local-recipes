---
title: A document's prose agrees with its own status
type: dream
owner: doctor
status: dreamt   # 2026-09-09 — raised by the fleet-readiness pass (§ 2.4 D1) after six
                 # documents in one sweep were found contradicting their own frontmatter
---

# A document's prose agrees with its own status

## The Dream

The document tier drifts faster than any detector polices it. `bmad-drift-check` guards
frontmatter *vocabulary* (is `status:` a legal value) and *counts* (does the artifact's
stated number match ground truth). `dreams-hygiene` guards *presence* (does a Dream carry
a status, a Realization log, a Spec). Nothing guards the one thing a reader actually
believes: that the **body still means what the frontmatter says**.

One readiness pass, 2026-09-09, found **six** documents where it does not — and none of
them is exotic:

- `docs/dreams/pyforge-scribe.md` reads `status: realized` while its own body says
  "3 of 9 stories complete overall" (`:69`); its Spec repeats the same stale figure.
- `docs/dreams/pyforge-herald.md` and `spec-pyforge-herald` both describe a mid-build
  station under `realized`/`shipped`.
- `docs/governance/spec-pyforge-charter/SPEC.md` declares `open_questions: []` (`:16`)
  while its own memlog carries a question opened 2026-07-31 that no later entry closes
  (`.memlog.md:9`, the `owner: guild` Lexicon question).
- `spec-unified-container` sits `shipped` over a container the estate does not build.

Every one of these is a lie a machine can catch, and every one of them was found by a
human reading carefully — which is exactly the labour this fleet exists to stop paying.

The Dream is a warn-only check that reads a Dream's or a Spec's prose beside its own
`status:` and reports the contradiction. Cheap signals, honestly bounded, never a gate.

## Candidate signals (each proven on the six live cases, or dropped)

- **Progress phrases under a terminal status.** A body matching "N of M stories" (or
  "N/M", "N of M capabilities") where `N < M`, under `realized` / `shipped` / `done`.
  Catches scribe's Dream and its Spec directly.
- **`open_questions: []` over a live memlog question.** The Spec declares no open
  questions while the companion `.memlog.md`'s last `(question)`/`(open)` entry has no
  subsequent `(decision)` closing it. Catches the Charter's Spec — where it is not
  hygiene at all: Charter CAP-2 makes the Lexicon's own integrity constitutional.
- **Future-tense build language under a terminal status.** A body whose section headings
  or lead sentences are still promissory ("will", "is being built", "queued", "not yet")
  under `realized`/`shipped`. Catches the herald pair. The loosest of the three, and the
  one most likely to be narrowed or dropped once measured.
- **A frontmatter status comment that contradicts the ledger it cites.** The
  `status: realized   # … → Epic 14 backlog` shape, where the named epic reads `done`.
  Found live on `bmad-method-version-drift`; mechanical, and the cheapest of all.

Each signal ships only after it is shown to fire on its named live case **and** to stay
silent across the rest of the tier. A signal that cannot demonstrate both is not shipped
— it is recorded as measured-and-rejected, with the number.

## What it looks like when real

- One more ambient row in the doctor report and the fleet-picture ATTENTION block,
  beside `dream-vocab` and `spec-status-missing`: *"`pyforge-scribe.md` reads `realized`
  but its body says 3 of 9 stories complete (`:69`)."*
- The finding names the **line** it read, never a verdict on the document. A reader
  disagrees with the check by fixing the prose or the status — never by arguing with a
  score.
- The tier stops needing a readiness pass to find this class. The 2026-09-09 sweep is the
  validation fixture: six documents, six findings, and nothing else.

## Constraints / Non-goals

- **Warn-only, fail-open, read-only.** Never a second PR verdict —
  `pyforge.doctor.verdict.exit_code_for` is the sole exit-code owner
  (`tests/meta/test_verdict_sole_ownership.py`); never a mutation — doctor's NFR-1 holds.
  An unparseable document degrades to a named finding, never to silence.
- **No natural-language judgement.** Every signal is a bounded textual pattern with a
  named line number. This is not "does the prose feel current" — a check that cannot
  point at a line is not shipped.
- **False positives are the expensive failure here, not false negatives.** A tier-wide
  narrative check that cries wolf gets muted, and a muted detector is worse than none.
  Each signal carries its measured precision over the live tier at the time it shipped.
- **Not a rewriter.** It never edits prose, flips a status, or proposes replacement text.
  Reconciliation is the [[chain-currency-sweep]] loop's job; this is its detector half.
- **Not a replacement for `bmad-drift-check` or `dreams-hygiene`.** Vocabulary, counts and
  presence stay where they are; this adds only the narrative axis none of them own.

## Kinships

[[capability-effect-check]] (minted the same day from the same pass — the two halves of
"the artifact says done and the estate disagrees": that one asks whether code reaches a
capability, this one asks whether prose agrees with a status) ·
[[sibling-dreams-drift]] (the shape — ambient, warn-only, fail-open, one Source — and the
standing lesson that a detector's join must be proven against live documents before its
story closes) · [[bmad-drift-new-artifact-shape]] (the sibling detector class this
extends: it polices frontmatter vocabulary and counts, never narrative) ·
[[chain-currency-sweep]] (the reconciler loop that clears what this reports; detector and
reconciler are the same two-layer pattern applied one tier down) ·
[[pyforge-charter]] (CAP-2 — the Lexicon's own integrity — makes one of the six cases
constitutional rather than cosmetic) · [[pyforge-doctor]] (the station).

## Realization log

- **2026-09-09** — Captured. Raised as D1 of the fleet-readiness decision batch
  (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
  § 2.4, operator-approved the same day) by two independent station reports — guild § E-5
  and scribe § E-3 — after each ran into the same missing detector from a different
  station. Six documents in one pass; the pass itself is the validation fixture.
