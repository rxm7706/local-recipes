---
spec: status-body-consistency
status: draft
owner-dream: docs/dreams/status-body-consistency.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/status-body-consistency.md
open_questions:
  - "Scope: Dreams and Specs only, or every tracked planning artifact (PRD, architecture
     spine, runbook)? Recommendation is Dreams + Specs for v1 — the two tiers with a
     machine-readable `status:` — recording the wider tier as a later capability if the
     first four signals earn it."
  - "Does a finding on a document another station owns need that station's acknowledgement
     before it renders? Doctor's Charter §6 answer (the verdict on an artifact belongs to
     the station that does NOT produce it) argues no, but five of the six live cases are
     foreign documents, so the question wants an explicit ruling rather than an assumption."
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate. The source document listed in frontmatter is for traceability only.

# SPEC — A document's prose agrees with its own status

## Why

A pain to solve, found twice independently in one pass. The document tier drifts faster than
any detector polices it: `bmad-drift-check` guards frontmatter *vocabulary* and *counts*,
`dreams-hygiene` guards *presence* — nothing guards the thing a reader actually believes,
that the body still means what the frontmatter says. The 2026-09-09 readiness pass found
**six** documents where it does not, and the axis was raised independently by two station
reports (guild § E-5, scribe § E-3), which is itself the evidence that no existing detector
owns it. Each of the six is a lie a machine can catch, and each was found by a human reading
carefully — exactly the labour this fleet exists to stop paying.

## The validation set

The pass's six documents **are** the validation set, and each signal must be proven against
its named live case before it ships:

1. `docs/dreams/pyforge-scribe.md` — `status: realized` over ":69 — 3 of 9 stories complete overall".
2. `spec-pyforge-scribe` — the same stale figure under `shipped`.
3. `docs/dreams/pyforge-herald.md` — `realized` over a mid-build body.
4. `spec-pyforge-herald` — the same.
5. `docs/governance/spec-pyforge-charter/SPEC.md:16` — `open_questions: []` while `.memlog.md:9` carries an `(open)` 2026-07-31 question no later entry closes.
6. `spec-unified-container` — `shipped` over a container the estate does not build.

## Capabilities

- **CAP-1 — progress-phrase-under-terminal-status.**
  - **intent:** Report a body matching an "N of M stories/capabilities" (or "N/M") phrase with
    N < M under `status: realized`/`shipped`/`done`.
  - **success:** Fires on the scribe Dream (`:69`) and its Spec, stays silent across the rest
    of the tier, and the finding names the line it read.

- **CAP-2 — `open_questions: []` over a live memlog question.**
  - **intent:** Report a Spec declaring no open questions while its companion `.memlog.md`'s
    last `(question)`/`(open)` entry has no subsequent `(decision)` closing it.
  - **success:** Fires on `docs/governance/spec-pyforge-charter` (`SPEC.md:16` vs
    `.memlog.md:9`). For that case this is not hygiene: Charter CAP-2 makes the Lexicon's own
    integrity constitutional, so a hidden Lexicon question is a constitutional defect.

- **CAP-3 — promissory language under a terminal status.**
  - **intent:** Report a body whose section headings or lead sentences are still
    forward-looking ("will", "is being built", "queued", "not yet") under `realized`/`shipped`.
  - **success:** Fires on the herald Dream+Spec pair *and* stays quiet elsewhere. This is the
    loosest signal; if it cannot do both, it ships as measured-and-rejected with its number,
    never as a muted check.

- **CAP-4 — a status comment that contradicts the ledger it cites.**
  - **intent:** Report a frontmatter `status:` comment naming an epic/story whose live ledger
    row disagrees.
  - **success:** Fires on the `status: realized   # … → Epic 14 backlog` shape found live on
    `docs/dreams/bmad-method-version-drift.md` while `epic-14` reads `done`. The cheapest and
    most mechanical of the four.

- **CAP-5 — it renders where the operator already looks.**
  - **intent:** A `report-schema.json` entry plus detectors membership, so the finding appears
    beside `dream-vocab` and (once C8 lands) `spec-status-missing`.
  - **success:** The finding shows up in the doctor report and the `fleet-picture` ATTENTION
    block without a separate detector invocation.

## Constraints

- **Warn-only, fail-open, read-only.** Never a second PR verdict —
  `pyforge.doctor.verdict.exit_code_for` is the sole exit-code owner, pinned by
  `tests/meta/test_verdict_sole_ownership.py`; never a mutation (doctor NFR-1); an
  unparseable document degrades to a named finding, never to silence.
- **No natural-language judgement.** Every signal is a bounded textual pattern that can point
  at a line number. A check that cannot name the line it read is not shipped.
- **False positives are the expensive failure mode here, not false negatives.** A tier-wide
  narrative check that cries wolf gets muted, and a muted detector is worse than none. Each
  signal carries its measured precision over the live tier at the time it ships.

## Non-goals

- Not a rewriter: it never edits prose, flips a status, or proposes replacement text —
  reconciliation is the `chain-currency-sweep` loop's job; this is its detector half.
- Not a replacement for `bmad-drift-check` or `dreams-hygiene`: vocabulary, counts and
  presence stay where they are. This adds only the narrative axis none of them own.

## Success signal

One more ambient row in the doctor report and the `fleet-picture` ATTENTION block —
*"`pyforge-scribe.md` reads `realized` but its body says 3 of 9 stories complete (`:69`)"* —
and the tier stops needing a readiness pass to find this class. The 2026-09-09 sweep is the
validation fixture: six documents, six findings, and nothing else.

## Assumptions

- The six live cases are representative of the class rather than a one-off cluster. If a
  signal's measured precision over the whole tier is poor, the honest outcome is to drop that
  signal with its number recorded — never to widen the threshold until it looks clean.
