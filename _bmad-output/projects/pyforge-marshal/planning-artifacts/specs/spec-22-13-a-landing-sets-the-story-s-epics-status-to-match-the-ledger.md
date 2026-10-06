---
title: "22.13: A landing sets the story's epics status to match the ledger"
type: 'fix'
created: '2026-10-06'
status: 'ready-for-dev'
baseline_revision: '7ab1f2d7b79f4e0c91755c060e902bb3cb1fcc6a'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py
  - src/shared/packages/pyforge-doctor/tests/meta/test_epics_status_tracks_the_ledger.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a dispatch landing leaves the story's `**Status:**` line in its station's `epics.md` at `backlog`.

- **Where it happens.** `dispatch_land_finalize` (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py`)
  publishes the story spec's `done` (`promotion.set_spec_status`, about :694-:730) and the ledger promotion onto the
  `origin/main` tip through `commit_paths_onto_remote_tip`. Nothing touches `epics.md`.
- **The live cost.** On 2026-10-05 doctor 34.3, herald 27.1 and mason 19.1 all landed automatically with their
  ledgers and story specs at `done` and `epics.md` at `backlog`. Doctor's
  `tests/meta/test_epics_status_tracks_the_ledger.py::test_live_tree_every_doctor_epics_status_matches_the_ledger`
  then failed CI `doctor-test` on `main` and on every branch until hand PRs #1882 and #1884 fixed the three lines.
- **The line's shape.** Stories that carry one have a line `**Status:** <word>` inside their `### Story N.M: …`
  section (`epics_status_mismatches` in the doctor test reads the last such line before the next `### Story`
  heading; the first word is the status). Most marshal stories carry no such line.

**Approach:** in the same publish that sets the story spec to `done`, set the landed story's `**Status:**` line in
`_bmad-output/projects/<slug>/planning-artifacts/epics.md` to `done`, through a pure helper in `core/promotion.py`
(text in, text out: find the `### Story N.M:` section, replace the first word after `**Status:**` on its status
line, leave any trailing text). No line, no change.

Ledger key: `22-13-a-landing-sets-the-story-s-epics-status-to-match-the-ledger`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-162 (← `spec-marshal-single-story-dispatch` CAP-4; Story 22.4,
  the landing through the existing machinery). A gap in shipped behaviour; no new CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-06 (landing gaps), item 1.

## Acceptance Criteria

- Given a station `epics.md` whose `### Story 34.3: …` section ends with `**Status:** backlog` When finalize lands
  34.3 Then the published commit sets that line to `**Status:** done` and no other line in the file changes.
- Given a status line with trailing text (`**Status:** backlog — waiting on 76.1`) When it is set Then only the first
  word changes.
- Given a story section with no `**Status:**` line When finalize lands it Then `epics.md` is not part of the publish.
- Given two stories with the same epic and adjacent sections When one lands Then the other's status line is untouched.
- Given `epics.md` missing, or no `### Story N.M:` heading for the key When finalize runs Then the landing still
  completes and journals one WARN naming the reason.
- Given the helper call removed (mutation) When the station suite runs Then the new tests fail.

## Boundaries & Constraints

**Always:**
- One pure helper in `core/promotion.py`; I/O stays in `dispatch_land_finalize`.
- Publish the `epics.md` change in the same `commit_paths_onto_remote_tip` commit as the spec status, so the two never
  disagree on `main`.
- Reconcile the governed files on their owning Specs' memlogs and stamp them scoped (`spec-pyforge-marshal` and the
  co-governor `spec-pyforge-core`; AGENTS.md pre-PR item 5).

**Never:**
- Never add a `**Status:**` line to a story that has none.
- Never change any status but the landed story's own, and never to anything but `done`.
- Never fail or roll back a landing because `epics.md` could not be updated.
- Never import `pyforge.doctor` from marshal code.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-06 (landing gaps) entry.
- Epic: Epic 22 (a fix joins its own epic, which reopens; doctor Story 41.5).
- Ledger key: `22-13-a-landing-sets-the-story-s-epics-status-to-match-the-ledger`.
- Ledger status at mint: `backlog`.
- Deps: —.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- Mutation: remove the helper call and re-run the station suite; the new tests fail. Restore it.
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 after the memlog reconciles and scoped stamps.
