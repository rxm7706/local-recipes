---
title: "113.19: An audit run reads the Dream entry its slice cites"
type: 'fix'
created: '2026-11-05'
status: 'backlog'
baseline_revision: '836a2ee286'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** In the 2026-11-05 sweep, 12 of 24 Dream-bearing runs took `dream_choice: newest`: every run on doctor, herald, mason
and warden. Their reviewers read an unrelated entry and reported Dream links as broken. At least six high findings were artifacts
of this, and 446 findings came from those runs. CAP-302 allows the fallback and the sweep exits 0, so nothing in `fleet.md` warns
a reader.

**Approach:** A fix under CAP-302, no new CAP and no flag. Read the citation forms the live Specs use, such as an entry named by
date and italic title, and let a dated Realization-log bullet serve as the Dream context. Keep the fallback for a slice that cites
nothing, and make every run's choice visible in the reports.

Ledger key: `113-19-an-audit-run-reads-the-dream-entry-its-slice-cites`. Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **CAP-302** — one audit sweep says where the fleet stands; re-derived with the citation forms it reads.

## Acceptance Criteria

- **AC1 — A title selects the entry.** A slice citing a date and a title selects that entry among the entries sharing the date, with `dream_choice: cited`.
- **AC2 — A dated bullet can serve.** A cited date that only a Realization-log bullet carries yields that bullet as the Dream context.
- **AC3 — The fallback stays.** A slice citing nothing keeps today's order: `names-cap`, then `newest`.
- **AC4 — The report tells.** `fleet.md` and each station report name every run's `dream_choice`, and `fleet.md` counts the `newest` runs.
- **AC5 — The contract follows.** CAP-302 is re-derived, the scoped stamp lands, and `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` exits 0.

## Boundaries & Constraints

- Parked at `backlog` by the session owner on 2026-11-05. It reruns no audit.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-302

- Finding: N2 in `research/egm-audit-2026-11-05.md`.
- Epic: Epic 113.

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: exit 0.

## Spec Change Log

- 2026-11-05: minted at `backlog` by marshal Story 113.18.
