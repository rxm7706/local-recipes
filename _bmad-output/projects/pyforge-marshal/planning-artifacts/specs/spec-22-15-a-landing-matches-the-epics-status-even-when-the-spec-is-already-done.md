---
title: "22.15: A landing matches the epics status even when the spec is already done"
type: 'fix'
created: '2026-10-07'
status: 'ready-for-dev'
baseline_revision: '966b166f76797916b96286b88587aa6f10f8240d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-13-a-landing-sets-the-story-s-epics-status-to-match-the-ledger.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py
  - src/shared/packages/pyforge-doctor/tests/meta/test_epics_status_tracks_the_ledger.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 22.13's `epics.md` flip only runs when the landing also has to publish the spec's `done`. In the
usual case it has nothing to publish, so the flip never runs.

- **Where it happens.** `_promote_tracked_spec` in `dispatch_land_finalize/__main__.py` (about :678-:772) reads the
  tracked spec at `origin/main`, and at about :722 returns `(False, None)` when
  `status in promotion.TERMINAL_SPEC_STATUSES`. That return comes before the Story 22.13 step that rewrites the
  story's `**Status:**` line (about :733-:757). A dispatch session normally sets its own story spec to `done` on the
  branch, so after the merge the spec is already `done` on `main`, the function returns early, and the epics line
  stays where it was. The call site (about :886) also skips the function for a key the Tier-3 route promoted in the
  same run (`key not in tier3_promoted_keys`). That route never touches `epics.md` either.
- **The live case.** Herald 28.1 landed on 2026-10-07 (PR #1892, merge `6b3a1c4c30`). Its ledger promotion
  (`966b166f76`) touched only `sprint-status-ledger.yaml`, and
  `_bmad-output/projects/pyforge-herald/planning-artifacts/epics.md` still reads `**Status:** backlog` under
  `### Story 28.1:`. That is the same mismatch Story 22.13 was minted to stop, and doctor's
  `test_live_tree_every_doctor_epics_status_matches_the_ledger` reds on the same shape for a doctor story.

**Approach:** separate the epics step from the spec publish. On every corroborated landing whose tracked spec is
`done` or pre-done at `origin/main`, finalize matches the landed story's `**Status:**` line to `done` with the
existing pure helpers (`promotion.epics_has_story_heading`, `promotion.set_epics_story_status`):

- spec pre-done: publish the spec and the epics line in one commit, as Story 22.13 does today;
- spec already `done`: publish only the epics line, as its own `commit_paths_onto_remote_tip` commit;
- the epics line already reads `done`: publish nothing;
- key promoted by the Tier-3 route this run: still match the line, since that route leaves `epics.md` alone.

The existing `MRS-DISP-047` WARN rules for a missing `epics.md` or a missing `### Story N.M:` heading stay as they are.
A WARN never fails or rolls back a landing.

Ledger key: `22-15-a-landing-matches-the-epics-status-even-when-the-spec-is-already-done`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-162 (← `spec-marshal-single-story-dispatch` CAP-4; Story 22.4,
  the landing through the existing machinery; Story 22.13, the epics flip this story completes). This is a gap in
  shipped behaviour, so no new CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-07 (landing gaps, again), item 1.

## Acceptance Criteria

- Given a tracked spec that reads `status: done` at `origin/main` and a station `epics.md` whose `### Story 28.1: …`
  section ends with `**Status:** backlog` When finalize lands 28.1 Then exactly one commit is published onto
  `origin/main`, its only path is `epics.md`, that line reads `**Status:** done`, and no other line in the file
  changes.
- Given a tracked spec that reads `status: in-review` at `origin/main` When finalize lands the story Then the spec and
  the epics line are published in one commit, as before (the Story 22.13 tests pass unchanged).
- Given a `done` spec and an epics line that already reads `**Status:** done` When finalize runs Then
  `commit_paths_onto_remote_tip` is not called for the epics step. A re-run of finalize publishes nothing.
- Given a key the Tier-3 route promoted in this run When finalize runs Then the story's epics line is matched to
  `done` on `origin/main`.
- Given a tracked spec that reads `status: blocked` or `status: superseded` When finalize runs Then `epics.md` is not
  published.
- Given a `done` spec and a story section with no `**Status:**` line, or two adjacent stories in one epic When one
  lands Then no line is added and the other story's line is untouched.
- Given a `done` spec and `epics.md` missing, or no `### Story N.M:` heading for the key When finalize runs Then the
  landing completes and journals one `MRS-DISP-047` WARN naming the reason.
- Given the new epics step removed (mutation) When the station suite runs Then the test that lands a story whose spec
  is already `done` fails.

## Boundaries & Constraints

**Always:**
- Reuse `promotion.epics_has_story_heading` and `promotion.set_epics_story_status` unchanged. I/O stays in
  `dispatch_land_finalize`.
- Read `epics.md` and the spec at `ORIGIN_MAIN`, the ref finalize has just fetched, and publish through
  `commit_paths_onto_remote_tip` so the operator checkout never moves (CAP-233).
- Keep the step idempotent: when the line already matches, publish nothing.
- Reconcile the governed files on their owning Specs' memlogs and stamp them scoped (`spec-pyforge-marshal` and the
  co-governor `spec-pyforge-core`; AGENTS.md pre-PR item 5).

**Never:**
- Never add a `**Status:**` line to a story that has none.
- Never change any status but the landed story's own, and never to anything but `done`.
- Never override a `blocked` or `superseded` spec, and never rewrite a spec that is already `done`.
- Never fail or roll back a landing because `epics.md` could not be updated.
- Never import `pyforge.doctor` from marshal code.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-07 (landing gaps, again) entry.
- Epic: Epic 22 (a fix joins its own epic, which reopens; doctor Story 41.5).
- Ledger key: `22-15-a-landing-matches-the-epics-status-even-when-the-spec-is-already-done`.
- Ledger status at mint: `backlog`.
- Deps: —.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- Mutation: remove the epics step for an already-`done` spec and re-run the station suite. The new test fails. Restore it.
- After the next real landing: the landed story's `**Status:**` line in its station's `epics.md` reads `done` on `main`.
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 after the memlog reconciles and scoped stamps.
