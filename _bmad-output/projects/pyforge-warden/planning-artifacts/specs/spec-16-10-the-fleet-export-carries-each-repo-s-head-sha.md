---
title: "16.10: The fleet export carries each repo's head_sha"
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
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-1-warden-inventories-a-ghe-organisation-s-repos.md
  - src/shared/packages/django-warden/src/django_warden_fabric/fleet_inventory.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/fleet_github_rest.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/fleet_inventory_sensor.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** warden's fleet inventory export is the data Atlas reads (`spec-pyforge-atlas:CAP-61`), and atlas's sensor
rejects it: `parse_fleet_inventory`
(`src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/fleet_inventory_sensor.py` about :62-65) returns
`None` for any row without a non-empty `head_sha`, and `export_document` (`src/shared/packages/django-warden/src/django_warden_fabric/fleet_inventory.py` about :271-279 at
`03a7aff5d9`) writes `full_name`, `default_branch`, `clone_url` and `archived` only. The question has been open since
2026-10-10 (Story 16.1's spec, *Named, not fixed here*; the 2026-10-11 memlog decision, item 9). CAP-26 success also
leaves the export's fields unpinned (WAR-M-Z3; its keys-not-blobs part is refuted: that rule governs the Celery
message).

**Operator ruling 2026-11-01** (the `spec-pyforge-warden` memlog's decision of that date): add `head_sha`.

EGM audit 2026-11-01, cluster WAR-CL-4; finding WAR-M-Z3, accepted by the operator on 2026-11-01; residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:**
- The `GET`-only client (`src/shared/packages/pyforge-warden/src/pyforge/warden/fleet_github_rest.py`) reads each repo's default-branch tip (one `GET` per repo), and
  `export_document` writes it as `head_sha` on each `repos[]` row.
- A repo whose tip cannot be read (an empty repo has none) goes to the export's `skipped` list with its reason, never
  to `repos[]` without `head_sha`.
- A test proves the export meets the acceptance rule of atlas's `parse_fleet_inventory`, reading the export as data.
- CAP-26 success pins the export fields (`full_name`, `default_branch`, `clone_url`, `archived`, `head_sha`) through
  the `spec-pyforge-warden` `bmad-spec` re-derive (with WAR-CL-3's), with the rest of WAR-CL-4's scoping (the proposal
  lifecycle is never a verdict; `platform-ci-local -- --test` is the platform suite).

Ledger key: `16-10-the-fleet-export-carries-each-repo-s-head-sha`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-warden` CAP-26 (FR-43) — the inventory is published as data other stations read. A `fix`, so no new
  CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag (`pyforge.warden.fleet_inventory` keeps gating the
  inventory).

## Acceptance Criteria

- **AC1 — Each row carries `head_sha`.** Given the fictional fixture organisation `example-org` of three repos and a
  fixture client with no real network, When the inventory runs, Then the export's `repos[]` holds three rows, each with
  `full_name`, `default_branch`, `clone_url`, `archived` and a non-empty `head_sha` equal to the fixture's tip.
- **AC2 — Reads stay `GET`.** Given the AC1 run, Then every request the client issued is a `GET`, and the token is
  never in the export, a log, the Celery message or error text.
- **AC3 — An unreadable tip is skipped.** Given a fixture repo with no commits, When the inventory runs, Then it is
  listed under `skipped` with its reason and absent from `repos[]`.
- **AC4 — Atlas accepts the export.** Given the AC1 export read as data, Then it meets the acceptance rule of atlas's
  `parse_fleet_inventory` (every row has a non-empty `full_name` and `head_sha`); no station imports
  `django_warden_fabric` or `pyforge.warden` for it.
- **AC5 — The target stays private.** The leak-guard tests stay green; fixtures name `example-org` only.
- **AC6 — The contract follows.** CAP-26 success pins the five export fields through a `bmad-spec` re-derive; no
  `SPEC.md` hand edit.
- **AC7 — Green.** `pixi run --frozen -e pyforge-warden pyforge-warden-test` and
  `pixi run -e pyforge-guild platform-ci-local -- --test` pass.

## Boundaries & Constraints

**Always:** the inventory is read-only (`GET` for REST); the export path stays gitignored; no tracked file names the
designated organisation, its repositories or its projects.

**Never:** change atlas's sensor (the ruling chose warden's export over relaxing it); write a partial export on a typed
error; hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-warden` CAP-26 (FR-43) — the fleet inventory, published as data
  (`spec-pyforge-atlas:CAP-61` reads it); a fix, no new CAP.

Parent: CAP-26

- EGM audit finding carried: WAR-M-Z3 (cluster WAR-CL-4; accepted 2026-11-01; one memlog event on
  `spec-pyforge-warden/.memlog.md`); operator ruling 2026-11-01 (the memlog decision of that date); residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 16 — a fix story joins its done epic (operator rule 2026-10-04; doctor Story 41.5 lets the epic key roll up
  to `in-progress`).
- Ledger key: `16-10-the-fleet-export-carries-each-repo-s-head-sha`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Surface: `src/shared/packages/django-warden/src/django_warden_fabric/fleet_inventory.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/fleet_github_rest.py`, `src/platform/tests/test_warden_fleet_inventory.py`,
  `src/shared/packages/pyforge-warden/tests/unit/test_fleet_github_rest.py`.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Minted 2026-11-01 by the EGM audit landing (marshal Story 113.7, spec-pyforge-marshal:CAP-302); mode in-PR: built in the audit's landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_fleet_github_rest.py -q` — expected: pass.
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass (the `django-warden` tests under
  `src/platform/tests/`, including `src/platform/tests/test_warden_fleet_inventory.py` and its leak-guard tests).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Auto Run Result

Status: done

Summary: implemented 2026-11-01 in the EGM audit landing worktree (branch `egm-audit-2026-11`); not committed.

What changed:
- `src/shared/packages/pyforge-warden/src/pyforge/warden/fleet_github_rest.py` — after every listing page is read, the
  GET-only client reads each listed repo's default-branch tip with one
  `GET /repos/{owner}/{repo}/git/ref/heads/{branch}` (owner and repo quoted as one segment each, the branch keeping its
  slashes) and `ListedRepo` carries it as `head_sha` (a 40- or 64-hex commit id). A 409 (empty repository) or a 404 (no
  default branch), a ref answer naming no commit id, or a `full_name` that is not `owner/repo` puts the repo under
  `skipped` with its page, position, name and reason, never in `repos`; `skipped` stays in page and position order.
  Any other tip-read failure (401, 403, 5xx, transport) fails the whole listing typed. `FleetInventoryApiError` gains
  `http_status` (the HTTP error number only; `None` otherwise) so the client can tell those cases apart; its message
  is unchanged. The token path (pinned connection, splice, cleared frames) is untouched and reused for the tip reads.
- `src/shared/packages/django-warden/src/django_warden_fabric/fleet_inventory.py` — `ListedRepoFields` gains `head_sha`;
  `export_document` writes it on every `repos[]` row and refuses (`ExportRowWithoutHeadShaError`, a
  `FleetInventoryError`, its text naming the row index only) a listed repo without one; `run_fleet_inventory_sync`
  builds the export before any `FleetRepo` upsert, so a refused export changes nothing. The time-limit comment now
  says the repo count, not the page count, sets the run time.
- Tests: `src/shared/packages/pyforge-warden/tests/unit/test_fleet_github_rest.py` (existing exchange lists extended
  with the tip reads; new: every row carries the fixture tip, tip reads are GET with the token on no frame, 409/404
  skipped with the reason, skip ordering, malformed ref answers skipped, any other HTTP or transport failure raised
  typed with no token, path quoting, non-owner/repo names skipped with no request, the commit-id rule) and
  `src/platform/tests/test_warden_fleet_inventory.py` (fixture rows carry `head_sha`; the export's row keys are exactly
  the five pinned fields; the real client's export meets the row rule read from atlas's `parse_fleet_inventory` source
  as an AST, never imported, and that sensor imports neither `django_warden_fabric` nor `pyforge.warden`; a 409/404 tip
  is skipped in the export and not upserted; a listing row without `head_sha` writes no export and upserts nothing; a
  503 on a tip read leaves no export, no row and no token).

ACs: AC1 (`test_inventory_three_repos`, `test_real_client_run_is_get_only_and_never_persists_the_token`,
`test_each_listed_repo_carries_its_default_branch_tip`); AC2 (the same, plus the `tip-read-http-error` case of
`test_real_client_failure_never_carries_the_token` and `test_any_other_tip_read_failure_fails_the_whole_listing`);
AC3 (`test_a_repo_with_no_tip_is_skipped_never_listed`, `test_a_repo_with_no_tip_is_skipped_with_its_reason`);
AC4 (`test_export_meets_the_atlas_sensor_acceptance_rule`); AC5 (leak-guard tests green; fixtures name `example-org`
only); AC6 (memlog event appended stating the CAP-26 success change for the `bmad-spec` re-derive; no `SPEC.md` edit);
AC7 (below).

Commands (exit codes read from `$?`):
- `pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_fleet_github_rest.py -q` — exit 0 (70 passed).
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — exit 0 (unit 2255 passed; integration 265 passed).
- `pixi run -e pyforge-guild platform-ci-local -- --test` (run with `PLATFORM_CI_LOCAL_PG_PORT=25437`,
  `PLATFORM_CI_LOCAL_REDIS_PORT=26387`, `PLATFORM_CI_LOCAL_TAG=w1610` and a scratch work dir, to stay off other
  agents' runs) — exit 0 (system checks, ruff, ruff format, mypy, policy suite 98 passed, full suite 1377 passed / 14
  skipped).
- `ruff check` / `ruff format --check` (the pyforge-guild binary, each package's own `[tool.ruff]`) on the four changed
  files — exit 0 / exit 0.
- `mypy --cache-dir .mypy_cache/pyforge-guild -p pyforge.warden` (from the package, pyforge-guild env; the package's
  `lint-types` slice) — exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — exit 1, red only on `pyforge-doctor`'s
  `tests/unit/test_sources_pages_liveness.py` import order (another station's in-flight edit in this shared worktree,
  not touched here); the `pyforge-warden` and `django-warden` ruff legs report ok.

Dev notes:
- The tip read uses `git/ref/heads/{branch}` (the smallest answer). It needs the token to read repository contents;
  the `gh` login's OAuth token does. A token that can list but not read a repo would get 404s, and those repos would
  land under `skipped` with `HTTP 404`, visible in the export rather than silent.
- One GET per repo makes the repo count the run's cost: at a few hundred ms a request, the inventory's 240 s soft limit
  covers several hundred repos. A larger organisation fails the run and writes no export. The limits are shared with
  the other fleet tasks (Story 16.7's bounds) and were not changed here.

## Spec Change Log

- 2026-11-01: minted `backlog` from the EGM fleet audit (marshal Story 113.7): cluster WAR-CL-4, finding WAR-M-Z3,
  accepted by the operator; operator ruling 2026-11-01 (add `head_sha`); mode in-PR.
- 2026-11-01: implemented and set `in-review` (dev); two events appended to `spec-pyforge-warden/.memlog.md`
  (the surface reconcile, and the CAP-26 success change for the re-derive).

## Review Triage Log

- **Review 1 (2026-11-01, reviewer: independent session) — PASS.**
  - Checked: the `fleet_github_rest.py` and `fleet_inventory.py` diffs and the tests against AC1-AC7 and the Boundaries; atlas's `parse_fleet_inventory` is unchanged and requires `full_name` and `head_sha`; the platform test reads it as an AST and finds no `django_warden_fabric` or `pyforge.warden` import in the sensor; the only `ListedRepo` constructor is the client's own.
  - Common evidence (one run for all eight stories, exit codes read from `$?`): `pixi run --frozen -e pyforge-warden pyforge-warden-test` exit 0 (2255 unit+meta, 265 other); the twelve touched warden unit/meta test files together exit 0 (290 passed, 0 skipped; opengrep 1.30.2 and osv-scanner present); `ruff check` and `ruff format --check` over every changed warden, django-warden and platform test file exit 0; `python scripts/lint_types.py ruff-format` exit 0 and `python scripts/lint_types.py mypy` exit 0 (`pyforge-warden ok`); `pixi run --frozen -e pyforge-guild lint-types` exit 1 only from `pyforge-doctor`'s I001 in `tests/unit/test_sources_pages_liveness.py`, another station's in-flight file (`pyforge-warden` and `django-warden` ruff legs ok); `pixi run -e pyforge-guild platform-ci-local -- --test` (private ports) exit 0, RESULT: PASS, 1377 passed / 14 skipped; touched warden modules' unit coverage all at or above 81%. Mutations ran on scratch copies only (warden via `PYTHONPATH`, django-warden via `pytest -o pythonpath=`), never on the worktree.
  - The four warden platform test files alone, against a private PostgreSQL: 106 passed, 1 skipped (the operator-local leak guard; fixtures name `example-org` only).
  - Mutation: dropping `head_sha` from the export row turns 6 red, including AC1, AC3 and AC4.
  - Carried forward, not held against the story: the CAP success-line change is recorded on `spec-pyforge-warden/.memlog.md`; `SPEC.md` is unchanged, as required, and the line waits for the session owner's `bmad-spec` re-derive.
  - Observation, not a failure: one tip GET per repo makes the repo count set the inventory's run time under the 240 s soft limit (recorded by the implementer).
  - Failures: none.
