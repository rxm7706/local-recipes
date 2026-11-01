---
title: "16.7: A fleet run is time-bounded, and an approval re-scans before it opens"
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
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-2-a-fleet-run-scans-each-inventoried-repo-one-verdict-per-repo.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-3-each-fleet-fix-waits-in-a-proposal-queue-for-operator-approval.md
  - src/shared/packages/django-warden/src/django_warden_fabric/tasks.py
  - src/shared/packages/django-warden/src/django_warden_fabric/fleet.py
  - src/shared/packages/django-warden/src/django_warden_fabric/models.py
  - src/shared/packages/django-warden/src/django_warden_fabric/proposals.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-26 states no failure modes, and the fleet code has no time bounds and no stale-approval guard (line
numbers at `03a7aff5d9`; WAR-M-D4):
- `scan_fleet_repo` and `open_fix_proposal` (`src/shared/packages/django-warden/src/django_warden_fabric/tasks.py`) declare no `soft_time_limit` or `time_limit`, unlike
  `run_fleet_inventory` (about :135-140), and `shallow_clone` (`src/shared/packages/django-warden/src/django_warden_fabric/fleet.py` about :41-79) runs `git clone` with no
  timeout, so one hung clone leaves a run `RUNNING` forever.
- A failed repo does get `FleetRepoScan` `FAILED`, but the run row records no failed or skipped repo counts, so a run
  that ends `SUCCEEDED` as a job (Story 16.2's decision, `spec-16-2-…md` I/O matrix) says nothing about its misses.
- The approve re-clones without re-scanning, so it can open a fix for a finding the repo no longer has; no approval
  expires.
- Dropped as already handled: double-approve and dismiss (`src/shared/packages/django-warden/src/django_warden_fabric/proposals.py` about :83-128). The read/write token split
  waits on the open credential ruling.

EGM audit 2026-11-01, cluster WAR-CL-8; finding WAR-M-D4, accepted by the operator on 2026-11-01; residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:**
- `scan_fleet_repo` and `open_fix_proposal` take soft and hard time limits, reusing the values `run_fleet_inventory`
  uses (the general pool's 300 s hard limit, Story 16.1's spec Change Log); `shallow_clone` passes a timeout to its
  `git` calls, and a timeout is that repo's `FAILED` row with the reason.
- `FleetRun` gains failed and skipped repo counts, filled when the run finalizes; a `0004` migration ships with its
  covering Liquibase changeset under `src/platform/db/changelog/changes/` and a `src/platform/db/sqlmigrate-map.yaml`
  entry.
- The approve re-scans the fresh clone with `warden scan` before acting, and refuses with a `failed` actuation when the
  proposal's finding id is absent from the fresh report. A configurable approval expiry (a setting with a default,
  named in this spec at implementation) refuses an older proposal the same way.
- A memlog decision on `spec-pyforge-warden` names the bounds and the approve-time re-scan; CAP-26 success names them
  through a `bmad-spec` re-derive.

Ledger key: `16-7-a-fleet-run-is-time-bounded-and-an-approval-re-scans-before-it-opens`.
Type / Effort / Deps: fix / L / S-16.6 (both change the approve path in `tasks.py` and `proposals.py`).

### Living CAP citations

- `spec-pyforge-warden` CAP-26 (FR-43) — Warden scans the fleet, one verdict per repo, and each fix waits for the
  operator. A `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- **AC1 — Tasks are bounded.** Given the Celery task registry, When `scan_fleet_repo` and `open_fix_proposal` are
  inspected, Then each declares a `soft_time_limit` below its `time_limit`, at the values `run_fleet_inventory` uses.
- **AC2 — A hung clone ends.** Given a `git clone` stub that never returns before the clone timeout, When the fleet run
  scans that repo, Then its `FleetRepoScan` row ends `FAILED` naming the timeout, the other repos proceed, and the run
  ends `SUCCEEDED` as a job.
- **AC3 — The run counts its misses.** Given a three-repo run with one failed clone and one archived repo, When the run
  finalizes, Then the run row records 1 failed and 1 skipped; no status outside the job vocabulary appears.
- **AC4 — A vanished finding is refused.** Given a queued proposal whose finding a fresh scan of the clone no longer
  reports, When the operator approves it, Then the proposal records a `failed` actuation naming the vanished finding
  and the fake forge client records zero writes.
- **AC5 — An old approval is refused.** Given a proposal older than the configured approval expiry, When it is approved,
  Then it is refused the same way, and the expiry can be changed through its setting.
- **AC6 — The migration is whole.** `makemigrations --check` reports no change for `warden_fabric`; the `0004`
  migration has its covering changeset and its `sqlmigrate-map.yaml` entry, and `sqlmigrate-extraction` passes.
- **AC7 — The contract follows.** A memlog decision records the bounds and the approve-time re-scan; CAP-26 success
  names them through a `bmad-spec` re-derive.
- **AC8 — Green.** `pixi run -e pyforge-guild platform-ci-local -- --test` and
  `pixi run --frozen -e pyforge-warden pyforge-warden-test` pass.

## Boundaries & Constraints

**Always:** a job status is never a verdict; a run stays `SUCCEEDED` as a job when some repos fail; the Celery message
carries ids only (keys-not-blobs); every throwaway clone is removed after a success, a failure and a timeout.

**Never:** add a fleet-level verdict; change double-approve or dismiss behaviour; run a live fleet write (the credential for a live fleet write is not ruled (`spec-pyforge-warden/.memlog.md`, the 2026-10-11 decision, item 9));
hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-warden` CAP-26 (FR-43) — Warden scans the fleet, one verdict per repo; a fix, no new
  CAP.

Parent: CAP-26

- EGM audit finding carried: WAR-M-D4 (cluster WAR-CL-8; accepted 2026-11-01; one memlog event on
  `spec-pyforge-warden/.memlog.md`); residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 16 — a fix story joins its done epic (operator rule 2026-10-04; doctor Story 41.5 lets the epic key roll up
  to `in-progress`).
- Ledger key: `16-7-a-fleet-run-is-time-bounded-and-an-approval-re-scans-before-it-opens`.
- Ledger status at mint: `backlog`.
- Deps: S-16.6.
- Surface: `src/shared/packages/django-warden/src/django_warden_fabric/tasks.py`, `src/shared/packages/django-warden/src/django_warden_fabric/fleet.py`, `src/shared/packages/django-warden/src/django_warden_fabric/models.py`, `src/shared/packages/django-warden/src/django_warden_fabric/migrations/` (a new `0004` migration),
  `src/shared/packages/django-warden/src/django_warden_fabric/proposals.py`, `src/platform/db/changelog/changes/`, `src/platform/db/sqlmigrate-map.yaml`,
  `src/platform/tests/test_warden_fleet_run.py`, `src/platform/tests/test_warden_fleet_proposals.py`.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Minted 2026-11-01 by the EGM audit landing (marshal Story 113.7, spec-pyforge-marshal:CAP-302); mode in-PR: built in the audit's landing PR.

## Verification

**Commands:**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass (the `django-warden` tests under
  `src/platform/tests/`, including `src/platform/tests/test_warden_fleet_run.py` and
  `src/platform/tests/test_warden_fleet_proposals.py`; the covering changeset under `sqlmigrate-extraction`).
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Auto Run Result

Status: done

Summary: implemented 2026-11-01 in the EGM audit landing worktree (branch `egm-audit-2026-11`, not committed). A fleet
run is now time-bounded and counts its misses, and an approve refuses an expired proposal or a finding a fresh scan of
the clone no longer reports, as a failed actuation with zero forge writes.

What changed:
- `src/shared/packages/django-warden/src/django_warden_fabric/tasks.py`: `scan_fleet_repo` and `open_fix_proposal`
  declare `soft_time_limit=FLEET_INVENTORY_SOFT_TIME_LIMIT_SECONDS` (240) and
  `time_limit=FLEET_INVENTORY_TIME_LIMIT_SECONDS` (300), the constants `run_fleet_inventory` uses (AC1).
  `finalize_fleet_run` fills `failed_repo_count` (the run's `FAILED` rows) and `skipped_repo_count` (its `SUCCEEDED`
  rows whose error starts `skipped: `, the archived marker, now the `_SKIPPED_ARCHIVED` constant). The run still ends
  `SUCCEEDED` (AC3). `open_fix_proposal` first refuses an approval whose proposal is older than the expiry
  (`_approval_expiry_reason`; age = `approved_at - created_at`), before any clone (AC5). After the clone it re-scans
  with `_run_warden_engines(clone_dir)` (plain `warden scan`, no dry-run actuation) and refuses a finding id that the
  fresh report's `findings` no longer lists (`_vanished_finding_reason`; the reason names the finding, the clone's
  commit and the scan exit) (AC4). Both refusals go through `_refuse_proposal`: state `failed`, `error` = the reason,
  `pr_url` empty, and no actuator or forge call.
- `src/shared/packages/django-warden/src/django_warden_fabric/fleet.py`: `shallow_clone(..., timeout=None)` bounds both
  `git` calls by `FLEET_CLONE_TIMEOUT_SECONDS = 120.0` (read at call time). A timeout raises `FleetCloneTimeoutError`
  ("git clone timed out after 120 s (<scrubbed url>)"), which becomes that repo's `FAILED` row. The `finally` still
  removes the clone (AC2). Named here, as the Approach asked: the approval-expiry setting is
  `WARDEN_FLEET_APPROVAL_EXPIRY_SECONDS` (`FLEET_APPROVAL_EXPIRY_SETTING`), default
  `FLEET_APPROVAL_EXPIRY_DEFAULT_SECONDS = 604800` (seven days), read with `getattr(settings, ...)`, so no settings
  file changed.
- Healed tissue in the same function: a `git` failure is re-raised as `FleetCloneError` (scrubbed stderr tail, return
  code), and the timeout is re-raised `from None`. The platform logger renders frame locals (`structlog`
  `dict_tracebacks`), and a chained `CalledProcessError` / `TimeoutExpired` carried `subprocess.run`'s frame, whose
  locals hold the credential-bearing env passed to `git`. This is the same reason `run_fleet_project_items` already
  clears its frames.
- `src/shared/packages/django-warden/src/django_warden_fabric/models.py`: `FleetRun.failed_repo_count` and
  `FleetRun.skipped_repo_count` (`PositiveIntegerField(default=0)`).
- `src/shared/packages/django-warden/src/django_warden_fabric/migrations/0004_fleet_run_repo_counts.py` (new), its
  changeset `src/platform/db/changelog/changes/python-agent-platform-24-warden-fabric-0004-fleet-run-repo-counts.sql`
  (new, `python-agent-platform:24`, from `sqlmigrate` against PostgreSQL, with rollback), the include in
  `src/platform/db/changelog/db.changelog-master.yaml` straight after `:23`, and the
  `warden_fabric.0004_fleet_run_repo_counts: 24` entry in `src/platform/db/sqlmigrate-map.yaml` (AC6).
- `proposals.py` is not changed: double-approve and dismiss are untouched (Boundary), and both refusals live in the
  open task, where AC4's refusal is recorded.
- Tests. `src/platform/tests/test_warden_fleet_run.py` gains five: the AC1 registry bounds; the AC2 hung clone (a `git`
  stub on `PATH` that execs `sleep 60` for a `hung-clone` URL and real `git` otherwise, with the clone timeout at 1 s;
  the row is `FAILED` naming `FleetCloneTimeoutError` and "timed out after 1 s", the other three repos and the run
  `SUCCEEDED`, `failed_repo_count == 1`, all four clone directories removed); the AC3 counts (one good, one bad clone,
  one archived: 1 failed, 1 skipped, statuses inside `JobStatus`); and the AC6 `makemigrations warden_fabric --check
  --dry-run`. `src/platform/tests/test_warden_fleet_proposals.py` gains a `_FreshScan` stub of `_run_warden_engines`
  (it asserts it reads the fresh clone, not a dry run), the AC4 test (a vanished finding: `failed` naming it, solver
  never called, zero forge calls, clone removed) and the AC5 test with three cases: the default expiry refuses an
  8-day-old proposal, the setting at 60 s refuses a 2-minute-old one, and the setting at 30 days lets an 8-day-old one
  open. Story 16.6's two approve tests now stub the fresh scan to still report their finding, since without the stub
  the real scan of the clean fixture would refuse it.
- Mutation-checked on a scratch copy of the package (`pytest -o pythonpath=` pointing at the copy). Each test reds when
  its line is removed: the time limits (AC1), the `timeout=` on the git calls (AC2 reds after 61 s with a
  `CalledProcessError`), the failed count (AC2 and AC3), the vanished refusal (AC4), the expiry refusal (AC5), and the
  setting lookup (AC5's shortened and lengthened cases).
- AC7: one surface-reconcile event and one decision (bounds, counts, expiry setting, approve-time re-scan) appended to
  `spec-pyforge-warden/.memlog.md`. CAP-26's success line takes it through the `bmad-spec` re-derive phase. `SPEC.md`
  was not edited.

Not covered, by design: a hard-limit (300 s) kill ends the worker process. Its `finally` does not run, and the chord's
callback does not fire, so that run keeps `RUNNING`. The soft limit (240 s) and the clone timeout (120 s) both act
before it and are caught as the repo's `FAILED` row. A hard-limit sweep would be a new behaviour, not this fix.

Commands run (exit codes read from `$?`):
- `pixi run -e pyforge-guild platform-ci-local -- --test` (private ports `PLATFORM_CI_LOCAL_PG_PORT=25481`,
  `PLATFORM_CI_LOCAL_REDIS_PORT=26381` and a scratch work dir, so it cannot collide with a parallel run): 0.
  `RESULT: PASS` (manage.py check, ruff, ruff format, mypy, the policy suite with 98 passed, sqlmigrate extraction
  ok with 20 first-party migrations, the full suite with 1367 passed and 14 skipped).
- `pixi run --frozen -e pyforge-warden pyforge-warden-test`: 0 (2226 passed; 265 passed).
- The two warden fleet test files alone, against a throwaway PostgreSQL: 0 (27 passed). `manage.py makemigrations
  warden_fabric --check --dry-run`: 0 ("No changes detected"). `python -m db.sqlmigrate_extraction`: 0.
- `pixi run --frozen -e pyforge-guild lint-types`: 1, from one finding outside this story: ruff I001 in
  `src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py`, another station's in-flight file.
  `[lint-types] ruff django-warden` reported `ok`. The task stops after its ruff leg, so `pixi run --frozen -e
  pyforge-guild ruff-format` ran alone: 0 (`ruff-format django-warden ok`). django-warden has no `[tool.mypy]`. The
  platform test files passed platform-ci-local's mypy.
- `ruff check` and `ruff format --check` over the changed django-warden files (its own `[tool.ruff]`) and the two
  platform test files (the platform's own): 0.

Review follow-up 2026-11-01: `src/platform/tests/test_warden_fleet_proposals.py` no longer imports `urllib.request`,
a raw-HTTP import that pyforge-doctor's `test_story_does_not_add_pyforge_under_src_platform` refuses under
`src/platform`. The `forge` fixture monkeypatches the string target `"urllib.request.urlopen"`, and the fake's
`request` parameter is typed by a local `_ForgeRequest` Protocol (`full_url`, `data`, `get_method`). Every assertion is
unchanged. Exit codes read from `$?`: the doctor meta-test file 0 (7 passed; the detector found the import at HEAD and
finds none now); the platform test file against a throwaway PostgreSQL and Redis 0 (15 passed); `ruff check`,
`ruff format --check` and the platform's `mypy` on the file 0. Surface-reconcile event appended to
`spec-pyforge-unifying-strategy/.memlog.md`.

## Spec Change Log

- 2026-11-01: minted `backlog` from the EGM fleet audit (marshal Story 113.7): cluster WAR-CL-8, finding WAR-M-D4,
  accepted by the operator; the double-approve and dismiss sub-claims dropped as handled; mode in-PR.
- 2026-11-01: implemented, `in-review`. Approval expiry setting named: `WARDEN_FLEET_APPROVAL_EXPIRY_SECONDS`, default
  604800 s (seven days); clone timeout `FLEET_CLONE_TIMEOUT_SECONDS` = 120 s; changeset `python-agent-platform:24`.

## Review Triage Log

- **Review 1 (2026-11-01, reviewer: independent session) — PASS.**
  - Checked: the `tasks.py`, `fleet.py` and `models.py` diffs, migration `0004`, changeset `python-agent-platform:24` (with rollback), its master include and its `sqlmigrate-map.yaml` entry, and the tests against AC1-AC8 and the Boundaries; platform-ci-local's sqlmigrate extraction ok (20 first-party migrations) and `test_warden_fabric_migrations_are_whole`; the migration's import style matches `0003` (django-warden's ruff excludes migrations).
  - Common evidence (one run for all eight stories, exit codes read from `$?`): `pixi run --frozen -e pyforge-warden pyforge-warden-test` exit 0 (2255 unit+meta, 265 other); the twelve touched warden unit/meta test files together exit 0 (290 passed, 0 skipped; opengrep 1.30.2 and osv-scanner present); `ruff check` and `ruff format --check` over every changed warden, django-warden and platform test file exit 0; `python scripts/lint_types.py ruff-format` exit 0 and `python scripts/lint_types.py mypy` exit 0 (`pyforge-warden ok`); `pixi run --frozen -e pyforge-guild lint-types` exit 1 only from `pyforge-doctor`'s I001 in `tests/unit/test_sources_pages_liveness.py`, another station's in-flight file (`pyforge-warden` and `django-warden` ruff legs ok); `pixi run -e pyforge-guild platform-ci-local -- --test` (private ports) exit 0, RESULT: PASS, 1377 passed / 14 skipped; touched warden modules' unit coverage all at or above 81%. Mutations ran on scratch copies only (warden via `PYTHONPATH`, django-warden via `pytest -o pythonpath=`), never on the worktree.
  - The four warden platform test files alone, against a private PostgreSQL: 106 passed, 1 skipped (the operator-local leak guard).
  - Mutations: no expiry check turns 2 red (AC5 default and shortened); a failed count fixed at 0 turns 2 red (AC2, AC3); no fresh-scan check turns the AC4 test red.
  - The logged exception for `FleetCloneTimeoutError` / `FleetCloneError` (structlog frame locals) showed only the `tasks` and `fleet` frames and no chained `subprocess` frame, so the credential-bearing env is not rendered.
  - Carried forward, not held against the story: the CAP success-line change is recorded on `spec-pyforge-warden/.memlog.md`; `SPEC.md` is unchanged, as required, and the line waits for the session owner's `bmad-spec` re-derive.
  - Observations for the session owner, not failures: a hard-limit (300 s) kill still leaves the run `RUNNING` (recorded by the implementer); the approve's 240 s soft limit now covers the clone, the fresh scan and the pixi solve together (Story 14.4's budget is 1800 s).
  - Failures: none.

- **Review 2 (2026-11-01, reviewer: independent session, review follow-up) — PASS.**
  - Scope: drop the raw-HTTP `import urllib.request` the story added to `src/platform/tests/test_warden_fleet_proposals.py`, which pyforge-doctor's `test_story_does_not_add_pyforge_under_src_platform` refuses under `src/platform`, keeping every assertion.
  - Checked: the diff against HEAD touches only the import block (`import urllib.request` gone, `from typing import Protocol` added), the `forge` fixture (`monkeypatch.setattr("urllib.request.urlopen", recording)`, the same module attribute warden's `fleet_github_rest.py` calls through) and a new local `_ForgeRequest` Protocol (`full_url`, `data`, `get_method`, the three members the fake reads) typing `_RecordingForge.__call__`'s `request`. The list of `assert` lines is identical to HEAD's. No other file under `src/platform`, `django-warden` or `pyforge-warden` changed.
  - Fails without the fix: the meta-test's own `_raw_http_imports` finds `import urllib.request` in the HEAD file and nothing in the `origin/main` file, so the test's "added since origin/main" set holds that import at HEAD and is empty now.
  - Evidence (exit codes read from `$?`): `pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/meta/test_portal_fleet_pulse.py -q` 0 (7 passed); the platform test file in the `platform-ci-test` env, run from `src/platform` against a throwaway PostgreSQL (pgvector) and Redis on private ports, 0 (15 passed); `ruff check` 0, `ruff format --check` 0 and the platform's `mypy` 0 on the file.
  - Governor: the baseline lists the path under `pyforge-steward/spec-pyforge-unifying-strategy` alone; the follow-up's surface-reconcile event on that Spec's `.memlog.md` names it (one `updated:` key). `pixi run --frozen -e pyforge-guild spec-surface-check` exit 0 with no finding on this path. Not stamped (a stamp waits for a clean tree).
  - Observations for the session owner, not failures: the same check warns `drift-presumed` on three other `spec-pyforge-unifying-strategy` paths changed in HEAD's commit f742908321 and not named by its memlog (`src/platform/tests/test_golden_path_promotion_osv_db.py`, django-warden migration `0004_fleet_run_repo_counts.py`, changelog `python-agent-platform-24-warden-fabric-0004-fleet-run-repo-counts.sql`); reconcile them before the scoped stamp. The memlog diff also carries steward Story 29.4's surface-reconcile line, which belongs to that story's follow-up, not this one.
  - Failures: none.
