---
id: SPEC-artifact-chain-reconciliation
spec: artifact-chain-reconciliation
status: shipped
owner-dream: docs/dreams/artifact-chain-reconciliation.md
companions:
  - audit-method.md
  - dream-inventory-2026-08-10.md
  - resume-package-2026-08-10.md
sources:
  - ../../../../../../docs/dreams/artifact-chain-reconciliation.md
assumptions:
  - "Done-claim sampling depth: ≥3 stories per epic or 20% of the epic
    (whichever greater), all ACs checked on each sampled story; deepened per
    station if findings warrant."
  - "Execution vehicle is the operator's main session driving phases directly
    (quick-dev shape), not bmad-loop — consistent with the serial decision."
  - "The bmad-check-implementation-readiness gate-report class accepts the
    traceability-matrix format; if its template resists, the matrix is the
    report body and the template's summary wraps it."
open_questions:
  - "Complete-station demotion precedent: when sampling fails an AC on a
    shipped station, does the story reopen or does it become a coverage-debt
    row? Decide at first occurrence (non-blocking)."
  - "One-shot campaign or standing practice? Priced after the first pass
    (non-blocking)."
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Artifact-Chain Reconciliation — the pause-and-audit

## Why

A pain to solve and a mandate the factory sets itself: the fleet paused at
267/335 stories, and nearly every artifact in the dream-to-code chain (Dream →
Deck → Spec → Research → Brief → PRD → UX → Architecture → Context → Epics →
Sprint → TEA → Gates → Code → Tested → Retro → Status) was authored before most
of that code existed. The 68 remaining stories will drive implementation the
moment any station re-spins; the four queued decomposition chains will extend
chains whose truth is presumed, not measured. The mechanical layer is policed by
six detectors; the semantic layer — story premises, done-claim ACs, test
coverage of epics — has never been checked by anything but the artifacts' own
self-assessment. The ledger reports intent; only the code reports fact. This
audit measures the chain against the code, fleet-wide, before anything else is
built on it. **Completed stations are first-class scope, not close-out**: three
of the four queued decomposition chains (atlas, herald, doctor) extend
completed stations, so their audit gates decomposition exactly as the backlog
audit gates re-spin. **The scope is all of PyForge** — every Dream in
`docs/dreams/` (61 files: stations, capabilities, practices, applications),
every planning artifact, every chain stage, all code — and **correction is
pre-authorized in both directions**: a stale artifact is rebuilt against the
code, and code that diverged from a still-valid contract is corrected against
the artifact. Nothing silent, everything cited and landed in reviewable PRs.

## Capabilities

- **CAP-1**
  - **intent:** Operator can start the judgment audit on a mechanically clean
    fleet: full detector sweep as baseline, the 51 `[drift-presumed]` warns
    closed (atlas 24 name-then-stamp; mason 1; marshal 26 regenerate →
    verify outputs match → judge → scoped stamp), dangling commits
    dispositioned.
  - **success:** Six detectors + meta-suite green; zero `[drift-presumed]`
    fleet-wide.
- **CAP-2**
  - **intent:** Every one of the 68 remaining stories (steward 4 → mason 28 →
    marshal 35 + blocked 8-5) carries a cited verdict — `STILL-VALID` /
    `ALREADY-DONE` / `CONTRADICTED` / `NEEDS-RESPEC` / `DROP` — in a
    traceability-matrix gate report.
  - **success:** 68/68 verdict rows, each with `file:line` or command-output
    evidence; one gate report landed per unfinished station.
- **CAP-3**
  - **intent:** All five completed stations (atlas, doctor, herald, scribe,
    warden) audited at equal rigor: done-claims sampled per epic against code,
    every chain column reconciled (Spec status, retro promises, story-spec
    sets, board rows), statuses corrected to earned values.
  - **success:** Per-station gate report; every chain column verified or
    carries a dispositioned finding; Spec statuses match evidence.
- **CAP-4**
  - **intent:** The TEA column is refreshed by measurement: per-epic
    AC → covering-test map across all 8 stations; an AC with no test becomes a
    visible, non-gating coverage-debt row for operator disposition.
  - **success:** Coverage table present per epic in the gate reports.
- **CAP-5**
  - **intent:** Audit verdicts become repairs in both directions: artifact
    diverged from code → artifact rebuilt through the owning skills
    (`bmad-correct-course`, `bmad-sprint-planning` + `sprint-ledger-sync`,
    `bmad-document-project`, `bmad-generate-project-context`,
    `dashboard-gen`), each landing with a memlog entry naming its paths and a
    scoped stamp; code diverged from a still-valid contract → code corrected
    via quick-dev with tests; decisions corrected via `bmad-correct-course`,
    recorded.
  - **success:** Every fix traceable to a verdict row and an owning-skill or
    tested-code landing; detectors green after each landing PR.
- **CAP-6**
  - **intent:** Each of the four queued decomposition chains (atlas → herald →
    doctor → steward) starts only after its owning station's audit gate report
    has landed.
  - **success:** Every decomposition PR cites the landed gate report it builds
    on.
- **CAP-7**
  - **intent:** Operator can make the resume decision on measured artifacts:
    final baseline re-stamp, board regeneration, fleet-picture, and a
    per-station go/no-go summary.
  - **success:** Baseline stamped; board matches ledger; the 68-story
    projection is backed by verdict rows rather than presumption.
- **CAP-8**
  - **intent:** The non-station estate is audited too: every Dream in
    `docs/dreams/` gets a verdict row — status truth against the README state
    definitions, chain completeness, satellite-consolidation correctness,
    stranded artifacts.
  - **success:** 61/61 Dreams dispositioned in an inventory gate report.

## Constraints

- **Serial, one context.** Audits execute serially in the main session, in
  this order: steward → mason → marshal → the five completed stations → the
  full non-station inventory; no agent fan-out. Operator decisions 2026-08-10.
- **Citation-or-nothing.** A verdict without `file:line` or command output is
  rejected in review. Prose is not an audit output — matrix rows only.
- **Detectors own mechanical facts.** Counts, pins, hashes, ledger totals come
  from the instruments; the audit spends judgment only (premises, AC truth,
  coverage meaning).
- **Anchoring guard.** Verdicts ground in code; done-claims are sampled cold;
  every landing PR is preceded by blind, lens-diverse parallel review (one
  structural, one coverage/edge-case, neither shown self-assessments).
- **S-13.2.** Artifact rewrites only through owning skills + memlog + scoped
  stamp. Ledger only via `sprint-ledger-sync`; board only via `dashboard-gen`.
  No satellite docs — gate reports land in each station's own
  `planning-artifacts/`.
- **The pause holds per station.** No station builds until its audit lands; a
  landing gates that station only, not the fleet.
- **Correction pre-authorized, nothing silent.** Rebuilding and correcting
  specs, code, decisions, and artifacts is standing-authorized (operator,
  2026-08-10) — but every correction traces to a verdict row and lands in a
  reviewable PR; a change without a recorded verdict is out of contract.
- **Tier-C untouched** (Dream/Deck/UX) unless the audit proves one
  contradicted.

## Non-goals

- Not a Tier-C refresh — no deck or UX work for polish.
- Not a new detector — the semantic layer cannot be mechanically gated;
  pretending otherwise mints a false-green instrument.
- Not a reconstruction of atlas's lost story-spec originals — 30/32
  contract-specs is the accepted end state.
- Not a re-spin — no station starts building under this spec.
- Not a reopening of the four decomposition chains' content decisions absent
  audit evidence — their start is gated; evidence-driven corrections go
  through `bmad-correct-course`, recorded.

## Success signal

Every one of the 335 stories is either code-verified or carries a cited
verdict with its correction landed; all eight station chains, the five
completed stations' statuses, and all 61 Dreams reconcile against code;
detectors green; the four decomposition chains and any re-spin proceed on
artifacts measured true rather than presumed — demonstrable by opening any
gate report and following any row's citation into the code it names.
