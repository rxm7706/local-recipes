---
title: "113.19: An audit run reads the Dream entry its slice cites"
type: 'fix'
created: '2026-11-05'
status: 'done'
baseline_revision: 'd28d532eaf'
review_loop_iteration: 1
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

- Parked at `backlog` by the session owner on 2026-11-05 and started the same day on the operator's word. It reruns no audit.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-302

- Finding: N2 in `research/egm-audit-2026-11-05.md`.
- Epic: Epic 113.

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: exit 0.
- `cli.audit_plan` on the live tree, cutting slices only and starting no session — expected: no gap and no run on `newest`.

## Spec Change Log

- 2026-11-05: minted at `backlog` by marshal Story 113.18.
- 2026-11-05: carried by hand in an interactive session on the operator's "Do it here", so the run is unmeasured. `SPEC.md` is re-derived by an anchored script, as Story 113.18's were, on the operator's approval for this session.
- 2026-11-05: two findings from the live tree widen the Approach, and the Intent above stays as minted. (1) Doctor's cited bullet sits under `## Fold — one chain (2026-09-17)`, not a Realization log, so any dated bullet in a Dream counts. (2) Herald's CAP-61, mason's CAP-35 and warden's CAP-26 cite no Dream entry, so the citation fix alone leaves all nine of their runs on `newest`. The Dream does link them, from the other side: a bullet's `→ CAP-n` names what it minted. AC3's order stands, and `names-cap` gains tiers: a heading's own text, then a dated bullet's `→`, then a heading whose section only runs through a mention. The last tier exists because a dated heading's section runs through a `## Realization log` below it, and that log holds the audit's own lines.
- 2026-11-05: on the live tree the plan now takes 9 `cited` and 15 `names-cap`, none `newest`, and no gap. The 2026-11-05 sweep took 12 `newest`. Doctor's slice grows to CAP-92..CAP-93, which both cite the entry. Atlas's three runs reach `names-cap` only on the last tier, through a mention in the 2026-10-26 bullet and the audit's own log line, both under `## 2026-09-17 — One-chain fold`. Read them as weak: CAP-72 cites no entry, and the reviewer gets the right bullet only because it sits inside that section.
- 2026-11-05: an independent review on the diff found 2 high, 3 medium and 3 low, all fixed here. High: no scoped stamp and no co-governor entry on `spec-pyforge-core`, and three status sources that disagreed. Medium: a title could not match a bullet whose bold lead is only the date (416 of 876 dated bullets), so the wrong entry came back as `cited`; CAP-302 denied a route the code took on atlas; and a bullet's first arrow read the whole bullet, so prose such as `6.11.0 → 6.12.0` counted. Low: an old marker showed `—` instead of `unknown`; CAP-298, two docstrings and `epics.md` had drifted; five mutations survived and now have tests.
- 2026-11-05: two limits stay, on purpose. A Dream of bullets alone now takes `newest` where it used to refuse, and CAP-302 says so; no audited Dream has that shape. A cited title that nothing carries still reports `cited` on the last entry of its date; no live citation does.
