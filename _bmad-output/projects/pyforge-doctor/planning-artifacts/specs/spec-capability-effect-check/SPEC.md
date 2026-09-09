---
spec: capability-effect-check
status: draft
owner-dream: docs/dreams/capability-effect-check.md
surface: []
companions:
  - ../../../../pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
sources:
  - ../../../../../../docs/dreams/capability-effect-check.md
open_questions:
  - "Where does this Spec re-home when `spec-intelligence-hub` reaches `ready`? Epic 49's
     binding note says the realization gate re-homes to `hub:CAP-*` Guards. Expected to be a
     pointer change (owner-dream / Kinship), not a migration — but the ruling belongs to
     steward's C4 bundle and doctor should not pre-empt it."
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. The source document listed in frontmatter is for traceability only.

# SPEC — A capability is not done until something exercises it

## Why

A pain to solve, measured. The fleet's ledgers read 737 of 775 stories `done` and the fleet
is not switched on: the 2026-09-09 readiness pass found **eighteen** capabilities of one
identical shape — a `done` epic, merged code, a green suite, and a named success criterion
never exercised in the running estate. `risk-tiered-review-depth` is `shipped` with zero
callers outside `tests/unit/test_gate.py`; `marshal-token-economy` is 24/24 `done` with every
layer off; `marshal-parallel-dispatch-fanout` has `max_parallel = 1` everywhere and has never
run a wave. Three of those four were visible only by grepping for call sites — no board, no
detector and no ledger could tell. This Spec is the cheap, ambient half of the realization
gate: a doctor Source that asks, of every declared capability, *is anything reaching this?*,
answered in the same breath as `story-status-check` answers *did the story land?*. The
criterion itself stays on `spec-pyforge-unifying-strategy` (steward Story 49.2); this Spec is
the implementation half, relayed to doctor by the 2026-09-09 decision batch § 2.3 C8 —
because `spec-pyforge-doctor`'s surface is `src/shared/packages/pyforge-doctor/**` and a
foreign story writing a module there is an edit `spec-surface-check` reds at merge.

## The join key

The check joins on **`(spec-slug, CAP-N)`** — the pair `board.py`'s `_parse_declared_cap_ids`
and `_cited_cap_ids_by_spec` already produce for chain-completeness INV-A. That key reaches
code through the citing story's `Surface:` line in the owning station's `epics.md`, and
reaches evidence through an optional `verified:` line on the CAP in `SPEC.md`. Nothing new is
parsed that the fleet does not already parse. The key is named up front deliberately:
`sibling-dreams-drift` shipped against a join (`title:`) the estate does not share and has
been structurally incapable of a finding since it merged.

## Capabilities

- **CAP-1 — the caller-outside-its-own-tests check.**
  - **intent:** For every declared capability whose citing story names Python surfaces, the
    check reports whether any symbol those surfaces define is referenced from outside that
    module and outside tests.
  - **success:** Run over every `pyforge-*` package in `src/shared/packages/`, it names
    `risk-tiered-review-depth`'s `classify_review_tier` / `resolve_review_cycles` — zero
    callers outside `core/gate.py` and `tests/unit/test_gate.py`, measured 2026-09-09 — as a
    live finding, and stays silent for a capability with real callers.

- **CAP-2 — the `verified:` line, rendered per CAP.**
  - **intent:** A capability may carry `verified: <date> — <what was exercised, where>` on the
    CAP itself in `SPEC.md`; the check renders that line beside the capability and reports a
    `shipped`/`realized` capability that carries none.
  - **success:** The "realized versus verified" column the Unifying Strategy's own 2026-09-09
    review asked for is produced mechanically from `SPEC.md`, never hand-maintained; a CAP
    with a current `verified:` line produces no finding.

- **CAP-3 — it renders where the operator already looks.**
  - **intent:** The new Source appears in the doctor report and the `fleet-picture` ATTENTION
    block beside `story-status-check`, via a `report-schema.json` entry and membership in the
    detectors task set.
  - **success:** One `detectors` run answers both "did the story land" and "is the capability
    reached"; the two remain separate modules with separate check names.

## Constraints

- **Advisory, always.** Warn at most, never a second PR verdict:
  `pyforge.doctor.verdict.exit_code_for` is the sole exit-code owner, pinned by
  `tests/meta/test_verdict_sole_ownership.py`.
- **Read-only** (doctor NFR-1): the check never authors a `verified:` line, flips a status, or
  moves a ledger row.
- **Fail-open, and say so.** An unreadable `epics.md`, an absent surface path, or a station
  with no ledger degrades to a *named finding*, never to silence — a bare `return ()` renders
  "could not look" as "looked and agreed" (`sibling_dreams.py:45,:48`).
- **The join is proven on live data before the first story closes.** A fixture that builds both
  sides from one synthetic value cannot reproduce a live failure — precisely how
  `sibling-dreams-drift` shipped silent. At least one finding must be demonstrated against the
  real fleet, and the demonstration recorded.
- **A dedicated Source module**, not an extension of `sources/factory.py`'s BMAD_DRIFT: a
  capability's `verified:` line and its call sites are a different artifact class from a
  deferred-work ledger entry, a Dream, or a planning-spine feeds edge (`bmad_method.py:9-20`
  is doctor's own written precedent).

## Non-goals

- Not a coverage tool and not a call-graph resolver: "has a caller outside its own test file"
  is a bounded, whole-word textual reach over declared surfaces — deliberately cheap,
  deliberately approximate, and honest about it in the finding text.
- Not a re-implementation of `story-status-check`: that answers "did it land", this answers
  "is it reached"; they render together and stay separate modules.
- Not a judgement. The check distinguishes "nobody noticed" from "we chose not to"; it does
  not decide which one is acceptable.

## Success signal

An operator reading `detectors` output sees "story 33.4 landed" and, on the next line, "and
nothing calls it" — not three weeks later in a readiness pass. The check goes silent when a
capability has live callers and a current `verified:` line.

## Assumptions

- The citing story's `Surface:` line in `epics.md` is a usable code pointer for most
  capabilities. Where a capability's surfaces are documents rather than modules, CAP-1 is not
  applicable and CAP-2's `verified:` line is the only signal — the check must report "not
  applicable, document surface" rather than a false "no callers".
