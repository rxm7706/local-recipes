---
title: '33.1: The deferred-work source reds a done story whose recommended follow-up review nothing carries'
type: 'feature'
created: '2026-09-28'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - docs/dreams/pyforge-doctor.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-66-1-finalize-carries-a-recommended-follow-up-review-into-the-deferred-work-ledger.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-66-2-every-landed-follow-up-recommendation-is-backfilled-and-held-by-a-meta-test.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-pyforge-marshal:CAP-275` carries a follow-up review that a landed story recommends: marshal Story 66.1
makes `dispatch_land_finalize` file a `DW-FRR-<story>` row (`origin: dispatch-followup-review`) for a story whose tracked spec
reads `status: done` with `followup_review_recommended: true`, and Story 66.2 backfills every spec that already reads so and
holds the invariant with a marshal meta test (`tests/meta/test_followup_review_carried.py`). That meta test runs in
`pyforge-marshal-test`, which fires on a marshal diff. A doctor, herald or steward PR that lands a flagged spec by hand, or
edits a ledger and drops a carrying row, is never checked. The operator ruled on 2026-09-28 that the invariant runs on every
PR — through Doctor's `deferred-work` source (`python -m pyforge.doctor.sources deferred-work`, the `deferred-work-check`
task, part of `detectors-ci`). Measured 2026-09-28 (a scratch count over the tracked trees): 210 tracked story specs read
`done` with the flag true; 18 have a carrying row; so the check must wait for 66.2's backfill.

**Approach:** in `sources/chain.py::_check_project_deferred_work`, for each tracked story spec
`planning-artifacts/specs/spec-*.md` of the project (the same files `discover_spec_frontmatter_deferrals` already parses —
read the frontmatter once, through `_frontmatter_parse`), a spec is in scope when `status` reads `done` and
`followup_review_recommended` is an explicit truthy (`true` / `yes` / `1`, case-insensitive — the rule marshal's
`core/dispatch_harness_done.followup_review_recommended` applies; absent, `false`, anything else or unparseable
frontmatter is out of scope). It is carried when the project's tracked `planning-artifacts/deferred-work-ledger.md` holds a
`DW-` entry (heading to next heading) whose `source_spec:` names the spec's filename and whose `origin:` is
`dispatch-followup-review` or `review-budget-followup` — marshal Story 66.2's predicate, reimplemented because Doctor imports
no station's internals. Each uncarried spec appends one finding of kind `followup-review-uncarried` (project, spec path),
which `_gather_deferred_work` turns into a FAIL like every other violation of this source (an unevaluable project stays a
WARN); `_deferred_work_message` names the spec and the remedy: carry it (a `DW-FRR-<story>` row via marshal's renderer, with
`source_spec:` naming the spec) or run the follow-up review, which leaves the flag `false`.

**Blocked until marshal Story 66.2 has landed; the operator flips it.** Before the backfill the check reds `main` 192 times.
The ledger key is minted `blocked` because marshal's `Deps:` parser is station-local, so a cross-station precondition is a
ledger gate (AGENTS.md § Known pitfalls; the herald 27.5 / steward 72.2 precedent). Do not start this story while 66.2 is
unlanded.

**Gate cleared 2026-10-10.** Marshal Story 66.2 is `done` on main: its landing, PR #1760 (merge `d8b2fb7cee`,
"Merge pyforge-marshal/66-2 into main"), is an ancestor of `origin/main` (`git merge-base --is-ancestor d8b2fb7cee
origin/main` exits 0 at `2d90c634f3`), and marshal's ledger row
`66-2-every-landed-follow-up-recommendation-is-backfilled-and-held-by-a-meta-test` reads `done`. Its meta test is on main
(`src/shared/packages/pyforge-marshal/tests/meta/test_followup_review_carried.py`), with the two carrying origins and the
`spec-deferred` negative this story's fixtures mirror. On the same tree `pixi run -e pyforge-guild deferred-work-check`
exits 0. The operator ruled the same day (verbatim): "yes flip the six cleared stories and dispatch them". The ledger key
moved `blocked -> backlog` through a worktree-local Tier-3 feed and `sprint-ledger-sync --project doctor
--allow-regression`; this spec is `ready-for-dev`. Re-read for staleness the same day: every path and symbol the story
names is still on main (`_check_project_deferred_work`, `discover_spec_frontmatter_deferrals`, `_frontmatter_parse`,
`_deferred_work_message`, `_gather_deferred_work` in `sources/chain.py`; marshal's
`core/dispatch_harness_done.followup_review_recommended`; `tests/unit/test_check_speed_budget.py`,
`tests/unit/test_sources_chain_deferred_work.py`). The 2026-09-28 counts in the Problem paragraph are the mint's
measurement and are left as written. No AC changes.

Ledger key: `33-1-the-deferred-work-source-reds-a-done-story-whose-recommended-follow-up-review-nothing-carries`.
Ledger status (do not edit the ledger): `backlog` (flipped from `blocked` on 2026-10-10 by the operator's ruling).
Type / Effort / Deps: feature / S / — (cross-project gate: marshal Story 66.2).

### Living CAP citations

- `spec-pyforge-doctor` CAP-86 (FR-19; extends CAP-36, the detector sees what it claims to check).
- Kinship: `spec-pyforge-marshal:CAP-275` (Stories 66.1 and 66.2) — the carry and the meta test whose predicate this reuses.

## Acceptance Criteria

- Given the tree after marshal Story 66.2 When `pixi run -e pyforge-guild deferred-work-check` runs Then no `followup-review-uncarried` finding is reported and it exits 0
- Given a fixture project with one tracked spec reading `status: done` and `followup_review_recommended: true` and a ledger with no row naming it When the source runs Then exactly one FAIL of kind `followup-review-uncarried` names the project and the spec
- Given the same fixture with a ledger row whose `source_spec:` names the spec and whose `origin:` is `dispatch-followup-review` (and, separately, `review-budget-followup`) When the source runs Then that finding is absent — for both row shapes marshal writes (66.1's `DW-FRR-<story>` rendering and the loop's `DW-FU-<story>` rendering with its added `origin:` line)
- Given the same fixture with a row naming the spec under `origin: spec-deferred <fingerprint>`, or a carrying row only in another project's ledger When the source runs Then the finding is still reported
- Given the flag `false`, the flag absent, the flag `no`, or `status: in-review` When the source runs Then no `followup-review-uncarried` finding is reported
- Given the new check removed from `_check_project_deferred_work` When the orphan fixture test runs Then it fails (mutation)
- Given the change When `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` runs Then it passes, `tests/unit/test_check_speed_budget.py` included

## Boundaries & Constraints

**Always:**
- Read tracked files only: the project's `planning-artifacts/specs/spec-*.md` and `planning-artifacts/deferred-work-ledger.md`.
  A Tier-3 dispatch journal is gitignored and absent on a runner; a follow-up that already ran is seen as the flag reading
  `false` (bmad-build-auto writes `false` before its one follow-up pass and forces it `false` at that pass's halt).
- Keep marshal 66.2's predicate exactly: same scope (`done` + explicit truthy), same carrying origins, same per-project
  ledger. Where the two could drift, the fixtures here use the shapes 66.2's meta test uses.
- Follow the source's convention: a violation is a FAIL; an unevaluable project is a WARN.

**Never:**
- Do not import `pyforge.marshal` or any station's internals.
- Do not change `scripts/deferred_work_intake.py`, the ledgers, or marshal's renderer; do not write any row.
- Do not edit `pixi.toml`: the `deferred-work-check` description is a summary that already omits this source's later
  checks, and the finding's own message names the rule.
- Do not start before marshal Story 66.2 has landed; do not flip this story's ledger key.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| orphan | `done` + flag `true`, no row | one FAIL `followup-review-uncarried` naming project and spec | — |
| carried by dispatch | row `origin: dispatch-followup-review`, `source_spec` names it | nothing | — |
| carried by the loop | row `origin: review-budget-followup`, `source_spec` names it | nothing | — |
| other origin | row names it under `spec-deferred …` | still the FAIL | — |
| other project | carrying row only in another project's ledger | still the FAIL | — |
| follow-up ran / explicit false | flag `false` | nothing | — |
| not done | `status: in-review` | nothing | — |
| unreadable frontmatter | unparseable block | out of scope | the existing unparseable handling is unchanged |
| unreadable project | ledger or specs unreadable | `deferred-work-unevaluable` WARN | as today |

</intent-contract>

## Source

Contract authored from `docs/dreams/pyforge-doctor.md`'s 2026-09-28 Realization-log entry *Proposed: a recommended
follow-up review is carried, and Doctor checks it on every PR* and `spec-pyforge-doctor` CAP-86, with the operator's
2026-09-28 ruling and the direction entry in the Spec's `.memlog.md`.

## Binding

Parent Spec capability: `spec-pyforge-doctor` CAP-86 (FR-19).
Dream: `docs/dreams/pyforge-doctor.md` § Realization log → *2026-09-28 — Proposed: a recommended follow-up review is carried, and Doctor checks it on every PR*.
Ledger key: `33-1-the-deferred-work-source-reds-a-done-story-whose-recommended-follow-up-review-nothing-carries`.
Ledger status at mint: `blocked` (cross-project gate: marshal Story 66.2). Flipped `blocked` → `backlog` 2026-10-10 by the operator's ruling (66.2 `done`), through the Tier-3 feed and `sprint-ledger-sync --project doctor --allow-regression`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild deferred-work-check` — expected: exit 0 on `main` after marshal Story 66.2.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new findings.

## Review Triage Log
