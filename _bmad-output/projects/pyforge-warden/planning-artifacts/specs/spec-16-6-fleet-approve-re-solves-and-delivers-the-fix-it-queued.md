---
title: "16.6: Fleet approve re-solves and delivers the fix it queued"
type: 'fix'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-3-each-fleet-fix-waits-in-a-proposal-queue-for-operator-approval.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-14-3-the-actuator-opens-the-fix-as-a-draft-pr-on-an-estate-repo.md
  - src/shared/packages/django-warden/src/django_warden_fabric/tasks.py
  - src/shared/packages/django-warden/src/django_warden_fabric/proposals.py
  - src/platform/tests/test_warden_fleet_proposals.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** the one Blocker that survived the EGM audit's triage (WAR-D-C1). Story 16.3's approve path never delivers
the fix it queued (line numbers at `03a7aff5d9`):
- `_run_fix_actuator` (`src/shared/packages/django-warden/src/django_warden_fabric/tasks.py` about :350-366) calls `run_actuator` without `fixed_version_candidates` or
  `manifest_locations`. With `pyforge.warden.fix_target_resolution` on, every `vuln:` proposal fails on "no fixed-version
  candidates"; with it off, the draft PR carries an empty tree.
- Queue time runs the actuator in dry-run, which prepares no edit (Stories 14.1 and 14.2 forbid the solver under
  dry-run), so `planned_paths_json` is always empty and the approve has no inputs (WAR-D-R3).
- `FixProposal.target` stores the outcome's `subject`, the package name, not the resolved version (`src/shared/packages/django-warden/src/django_warden_fabric/proposals.py`
  about :64-74).
- `src/platform/tests/test_warden_fleet_proposals.py` patches `_run_fix_actuator` (about :236-241), so no test runs the
  real actuator on the approve path.

EGM audit 2026-11-01, cluster WAR-CL-1; findings WAR-D-C1 and WAR-D-R3, accepted by the operator on 2026-11-01;
residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:**
- Factor the `manifest_locations` builder out of `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` (about :1296-1307) into a public `pyforge.warden` helper
  that takes an inventory and returns the canonical-subject-keyed locations; `cli.py` calls it, unchanged in behaviour.
- At queue time, `proposals.py` stores the dry-run `fix_resolution` target in `FixProposal.target` and keeps the
  candidates in the scan's stored `report_json`; it never stores a diff.
- At approve time, `_run_fix_actuator` builds `manifest_locations` on the fresh clone through the helper and passes
  `fixed_version_candidates` from the stored `report_json` actuation `fix_resolution`; the actuator re-resolves on the
  clone (approve-time re-resolution, WAR-M-C3's sub-point).
- An approve that would yield no `manifest_fix` records a `failed` actuation on the proposal and opens no PR.
- The platform test drives the real `run_actuator` with a fake forge client passed through its `client` parameter and a
  stubbed solver seam, and asserts the commit and the refuse path.
- A memlog decision on `spec-pyforge-warden` records the handoff (the queue records the dry-run target and candidates,
  never a diff; the approve re-solves on the fresh clone), which supersedes Story 16.3's "planned diff summary"
  through this story. Story 16.3 is done and is not edited.

Ledger key: `16-6-fleet-approve-re-solves-and-delivers-the-fix-it-queued`.
Type / Effort / Deps: fix / M / S-14.4 (the approve re-solve runs the default solver that Story 14.4 fixes).

### Living CAP citations

- `spec-pyforge-warden` CAP-26 (FR-43) — the fleet's approve-then-open path; CAP-24 (FR-41) — the actuator path it
  opens through. A `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag
  (`pyforge.warden.fleet_fix_proposals` keeps gating the queue and the approve).

## Acceptance Criteria

- **AC1 — The queue stores the target.** Given a fleet run whose dry-run actuation planned a `vuln:` fix with
  `fix_resolution` target `1.3.0`, When the run finalizes, Then the `FixProposal.target` is `1.3.0`, not the package
  name, and the proposal stores no diff.
- **AC2 — The approve delivers.** Given that proposal and a fixture clone whose manifest declares the package, When the
  operator approves it and `open_fix_proposal` runs, Then the real `run_actuator` (not patched) receives the stored
  candidates and the clone's `manifest_locations`, and the fake forge client records one draft PR on a `warden/fix/`
  branch whose one commit carries the manifest edit to the target floor.
- **AC3 — No fix, no PR.** Given an approve whose re-solve yields no `manifest_fix` (no candidate accepted, or no
  declaring manifest), When it runs, Then the proposal records a `failed` actuation with the reason and the fake forge
  client records zero writes.
- **AC4 — One helper.** Given the new public helper, When `warden scan` builds its actuator inputs, Then it calls the
  helper and its output is unchanged (the existing CLI tests stay green).
- **AC5 — The contract follows.** A memlog decision on `spec-pyforge-warden` records the queue-then-re-solve handoff; no
  `SPEC.md` hand edit.
- **AC6 — Green.** `pixi run --frozen -e pyforge-warden pyforge-warden-test` and
  `pixi run -e pyforge-guild platform-ci-local -- --test` pass.

## Boundaries & Constraints

**Always:** nothing auto-opens on a fleet repo: zero forge writes until an approve, one per approval; the fleet
repository is admitted only through `authorized_fleet_repo`; the scanned clone is never written outside its throwaway
copy; failures are `failed` actuation outcomes, never a rung or an exit code.

**Never:** run a live approve against the designated organisation: the credential for a live fleet write is not ruled (`spec-pyforge-warden/.memlog.md`, the 2026-10-11 decision, item 9), so the code path is tested against a fake
forge client only; store a diff at queue time; edit Story 16.3's text or ledger row; hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-warden` CAP-26 (FR-43) — Warden scans the fleet; each fix waits for the operator's
  approval.
- Parent capability: `spec-pyforge-warden` CAP-24 (FR-41) — the actuator path an approved proposal opens through.

Parent: CAP-26

- EGM audit findings carried: WAR-D-C1 (the one Blocker that survived triage) and WAR-D-R3 (cluster WAR-CL-1; accepted
  2026-11-01; one memlog event each on `spec-pyforge-warden/.memlog.md`); residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 16 — a fix story joins its done epic (operator rule 2026-10-04; doctor Story 41.5 lets the epic key roll up
  to `in-progress`).
- Ledger key: `16-6-fleet-approve-re-solves-and-delivers-the-fix-it-queued`.
- Ledger status at mint: `backlog`.
- Deps: S-14.4.
- Surface: `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/actuator.py`, `src/shared/packages/django-warden/src/django_warden_fabric/tasks.py`, `src/shared/packages/django-warden/src/django_warden_fabric/proposals.py`,
  `src/platform/tests/test_warden_fleet_proposals.py`.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Minted 2026-11-01 by the EGM audit landing (marshal Story 113.7, spec-pyforge-marshal:CAP-302); mode in-PR: built in the audit's landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass (the `django-warden` tests under
  `src/platform/tests/`, including `src/platform/tests/test_warden_fleet_proposals.py` and
  `src/platform/tests/test_warden_fleet_run.py`).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks:**
- `grep -n "_run_fix_actuator" src/platform/tests/test_warden_fleet_proposals.py` — expected: no `patch(` of it.

## Auto Run Result

Status: done

Summary: implemented 2026-11-01 in the EGM audit landing worktree (branch `egm-audit-2026-11`, not committed).
The fleet approve now re-solves on the fresh clone and delivers the fix it queued, or records `failed` with zero
forge writes.

What changed:
- `src/shared/packages/pyforge-warden/src/pyforge/warden/manifest_locations.py` (new): the public helper.
  `manifest_locations_from_inventory(inventory)` is the one builder (canonical subject keys, same-name provenance
  unioned, the `pypi_identity` second key), moved verbatim out of `cli.py`. `manifest_locations_for_target(target)`
  discovers and extracts a tree's Python manifests (best effort: an unparsable manifest gives no location) and calls
  it. It only reads.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py`: `warden scan` calls the helper (AC4). The unused
  `_canonical_subject_key` import and the stale docstring line are updated.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/actuator.py`: `run_actuator(..., require_manifest_fix=False)`.
  When it is true, a proposal with no prepared manifest edit records `failed` with the reason (`no manifest fix: a
  removal fix has no manifest edit` / `the manifest edit is off (pyforge.warden.fix_manifest_edit)` / `no manifest
  location map`) before any forge call. The default is unchanged. The module docstring's line saying that target
  resolution is deferred, stale since Story 14.1, is fixed.
- `src/shared/packages/django-warden/src/django_warden_fabric/proposals.py`: `FixProposal.target` is the dry-run
  `fix_resolution.target`, or `""` when there is none (a removal, or resolution off). It is never the package name
  (AC1). Only paths go in `planned_paths_json`, never a diff.
- `src/shared/packages/django-warden/src/django_warden_fabric/tasks.py`: `_run_fix_actuator` passes the scan's stored
  candidates (`_stored_fix_candidates`), `manifest_locations_for_target(clone_dir)`, the solver seam
  `_fleet_fix_solver()` (`None` means the default pixi solver) and `require_manifest_fix=True` (AC2, AC3).
- Tests: `src/shared/packages/pyforge-warden/tests/unit/test_manifest_locations.py` (new, 5 tests; the CLI test spies
  that `warden scan` hands the helper's map to the actuator and that the approve builder reads the same tree to the
  same map). `src/shared/packages/pyforge-warden/tests/unit/test_actuator_require_manifest_fix.py` (new, 5 tests).
  `src/platform/tests/test_warden_fleet_proposals.py`: the patched `_run_fix_actuator` test is replaced. There is a
  new AC1 test, an AC2 test that drives the real `run_actuator` on a real `file://` clone and asserts one draft PR
  whose head is the `warden/fix/` ref and whose one commit's one blob carries `"requests>=2.32.0",`, and an AC3 test
  over three cases (no candidate accepted, no declaring manifest, removal) that asserts `failed` with the reason and
  zero forge calls.
- AC5: a decision entry on `spec-pyforge-warden/.memlog.md` records the queue-then-re-solve handoff and the CAP-26
  approve success it now promises. A surface-reconcile event names every changed path. `SPEC.md` was not edited.

Deviation, recorded: AC2 and the Approach say "a fake forge client passed through its `client` parameter".
`src/platform/` never imports `pyforge.*` (AGENTS.md § Policy), and three warden meta guards fail on any such import
in the diff (`test_src_platform_has_no_pyforge_import`, both `test_story_does_not_add_pyforge_under_src_platform`).
So the platform test cannot build a forge client object. The fake forge sits one layer lower, at the HTTP seam the
real `GitHubForgeClient` calls (`urllib.request.urlopen`, with a test `GITHUB_TOKEN` and
`GITHUB_API_URL=https://forge.invalid`). It records every Git Data call. This is stricter than a protocol fake: it
proves the real client's branch, blob, tree, commit and draft-pull sequence. The solver is stubbed through the
`django_warden_fabric.tasks._fleet_fix_solver` seam. Only the forge is faked; the actuator is not patched.

Decision taken (flags): the approve respects `pyforge.warden.fix_target_resolution` and
`pyforge.warden.fix_manifest_edit`, the same way the queue's dry-run does. It does not force them on. With either
flag off, an approve records `failed` ("no manifest fix: ...") and opens nothing.
`fix_draft_pr_estate_enabled=True` stays forced, as Story 16.3 set it. No flag was added.

Commands run (exit codes read from `$?`):
- `pixi run --frozen -e pyforge-warden pyforge-warden-test`: 0 (2226 passed; 265 passed). The first run was 1
  because the platform test imported `pyforge.warden`; that import was removed and the run was repeated.
- `pixi run -e pyforge-guild platform-ci-local -- --test`: 0 (`RESULT: PASS`: manage.py check, ruff, ruff format,
  mypy, the policy suite 98 passed, the full suite 1359 passed and 14 skipped). Two earlier runs exited 1: one raced
  a mid-edit file, and one had a URL-prefix assertion bug in the new test.
- `pixi run --frozen -e pyforge-guild lint-types`: 1, from one finding outside this story: ruff I001 in
  `src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py`, another station's in-flight file in
  this shared worktree. Every lint-types leg for this story's packages passes: `ruff` django-warden and
  pyforge-warden ok; `python scripts/lint_types.py ruff-format` 0; `python scripts/lint_types.py mypy` 0 (all ten
  pyforge-* ok).
- `src/platform` ruff check and ruff format --check on `tests/test_warden_fleet_proposals.py`: 0.
- Manual check: `grep -n "_run_fix_actuator" src/platform/tests/test_warden_fleet_proposals.py`: no match (exit 1),
  so there is no `patch(` of it.

## Spec Change Log

- 2026-11-01: minted `backlog` from the EGM fleet audit (marshal Story 113.7): cluster WAR-CL-1, findings WAR-D-C1
  (Blocker) and WAR-D-R3, accepted by the operator; the live-approve credential stays the operator's; mode in-PR.
- 2026-11-01: implemented (in-review). The fake forge for AC2 sits at the HTTP seam rather than the `client`
  parameter, because `src/platform/` never imports `pyforge.*`. The approve respects the two actuator fix flags.

## Review Triage Log

- **Review 1 (2026-11-01, reviewer: independent session) — PASS.**
  - Checked: `manifest_locations.py` (new), the `cli.py`, `actuator.py`, `proposals.py` and `tasks.py` diffs and the tests against AC1-AC6 and the Boundaries; manual check `grep -n _run_fix_actuator src/platform/tests/test_warden_fleet_proposals.py` has no match (exit 1); no changed platform test imports `pyforge`.
  - Common evidence (one run for all eight stories, exit codes read from `$?`): `pixi run --frozen -e pyforge-warden pyforge-warden-test` exit 0 (2255 unit+meta, 265 other); the twelve touched warden unit/meta test files together exit 0 (290 passed, 0 skipped; opengrep 1.30.2 and osv-scanner present); `ruff check` and `ruff format --check` over every changed warden, django-warden and platform test file exit 0; `python scripts/lint_types.py ruff-format` exit 0 and `python scripts/lint_types.py mypy` exit 0 (`pyforge-warden ok`); `pixi run --frozen -e pyforge-guild lint-types` exit 1 only from `pyforge-doctor`'s I001 in `tests/unit/test_sources_pages_liveness.py`, another station's in-flight file (`pyforge-warden` and `django-warden` ruff legs ok); `pixi run -e pyforge-guild platform-ci-local -- --test` (private ports) exit 0, RESULT: PASS, 1377 passed / 14 skipped; touched warden modules' unit coverage all at or above 81%. Mutations ran on scratch copies only (warden via `PYTHONPATH`, django-warden via `pytest -o pythonpath=`), never on the worktree.
  - The four warden platform test files alone, against a private PostgreSQL: 106 passed, 1 skipped (the designated-organisation leak guard, which needs an operator-local `.warden/fleet-target.toml`).
  - Mutations: dropping `fixed_version_candidates=` turns 4 red, including the AC2 delivery test; dropping `require_manifest_fix=True` turns the AC3 removal case red; dropping `manifest_locations=` turns 3 red; storing the subject as the target turns the AC1 and AC2 tests red.
  - Deviation accepted: the fake forge sits at the `urllib` seam instead of `run_actuator`'s `client` parameter, because `src/platform` must not import `pyforge.*`; it records the real client's Git Data sequence (one blob, tree, commit, `warden/fix/` ref, draft pull).
  - AC5: the memlog decision records the queue-then-re-solve handoff; no `SPEC.md` edit.
  - Observations for the session owner, not failures: the queue still creates removal (`hygiene:DEP002`) proposals that no approve can now deliver (each records `failed`, 'a removal fix has no manifest edit'); the approve can open at a higher floor than `FixProposal.target` shows when the re-solve rejects the stored lowest candidate.
  - Failures: none.
