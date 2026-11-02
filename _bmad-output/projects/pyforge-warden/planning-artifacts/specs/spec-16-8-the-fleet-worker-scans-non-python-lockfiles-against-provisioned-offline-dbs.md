---
title: "16.8: The fleet worker scans non-Python lockfiles against provisioned offline DBs"
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
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-4-non-python-lockfiles-scan-through-osv-scanner-s-own-parsers.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-12-4-the-offline-osv-database-is-provisioned-in-ci.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/osv-db-offline-provisioning-decision.md
  - scripts/platform-provision-osv-offline-db.sh
  - src/shared/packages/django-warden/src/django_warden_fabric/tasks.py
  - src/shared/packages/django-warden/src/django_warden_fabric/proposals.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-26's npm clause assumes offline OSV databases nothing provisions, and leaves the outcome of a
non-Python proposal unstated (line numbers at `03a7aff5d9`; WAR-M-Z2):
- `scripts/platform-provision-osv-offline-db.sh` provisions only `osv-scanner/PyPI/all.zip` (:12), and only CI runs it
  (`.github/workflows/platform-ci.yml` about :864). The fleet worker sets no offline-database cache, so a real npm, Go
  or Cargo scan routes to `indeterminate` with `offline-db-unavailable-ecosystem` (`src/shared/packages/pyforge-warden/src/pyforge/warden/native_lockfiles.py` about
  :220-221). That is not egress: osv-scanner runs `--offline`.
- `src/shared/packages/django-warden/src/django_warden_fabric/proposals.py` (about :58) queues a proposal for any planned `vuln:` outcome, including an npm one that CAP-24's
  edit set (`pixi.toml`, `pyproject.toml`, recipes) cannot fix.
- Rejected as taste: the claim that CAP-26 bundles three capabilities (the Dream split the npm clause into Story 16.4).

**Operator ruling 2026-11-01** (the `spec-pyforge-warden` memlog's decision of that date): a non-PyPI or conda
vulnerability proposal is never queued — only a `vuln:` finding on a PyPI or conda component queues one.

EGM audit 2026-11-01, cluster WAR-CL-6; finding WAR-M-Z2, accepted by the operator on 2026-11-01; residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:**
- Extend `scripts/platform-provision-osv-offline-db.sh` to provision the npm, Go and crates.io databases beside PyPI,
  idempotently, keeping its already-provisioned short-circuit per ecosystem.
- Point the fleet worker's scan environment at the provisioned cache (`OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`, read from
  a setting); a missing database for an ecosystem stays `indeterminate`, never `clean`.
- `proposals.py` queues only `vuln:` outcomes whose component is PyPI or conda; any other ecosystem's finding is
  recorded in the run's report and queues nothing.
- CAP-26 success names the per-ecosystem offline database as a precondition and the ruled non-Python proposal outcome,
  through the `spec-pyforge-warden` `bmad-spec` re-derive (with WAR-CL-3's).

Ledger key: `16-8-the-fleet-worker-scans-non-python-lockfiles-against-provisioned-offline-dbs`.
Type / Effort / Deps: fix / M / S-16.6 (both change the queue in `proposals.py`).

### Living CAP citations

- `spec-pyforge-warden` CAP-26 (FR-43) — the security axis for the lockfile ecosystems osv-scanner parses natively. A
  `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag
  (`pyforge.warden.non_python_ecosystems` keeps gating discovery).

## Acceptance Criteria

- **AC1 — The databases are provisioned.** Given an empty cache directory and a connected runner, When
  `scripts/platform-provision-osv-offline-db.sh` runs, Then the cache holds `PyPI`, `npm`, `Go` and `crates.io`
  databases; a second run is a no-op for each one already present.
- **AC2 — The worker reads them.** Given a fleet repo whose `package-lock.json` pins a known-vulnerable npm version and
  a fixture cache that holds the npm database, When `scan_fleet_repo` runs, Then the stored report carries the `vuln:`
  finding for it and no `offline-db-unavailable-ecosystem` finding.
- **AC3 — A missing database stays honest.** Given the same repo and a cache without the npm database, When it is
  scanned, Then the security axis is `indeterminate`, never `clean`.
- **AC4 — No non-Python proposal.** Given the AC2 run, When it finalizes, Then no `FixProposal` exists for the npm
  finding, while a PyPI or conda `vuln:` outcome in the same run still queues one.
- **AC5 — Offline.** The scan runs osv-scanner with `--offline`; the suite opens no socket (fixture databases only).
- **AC6 — The contract follows.** CAP-26 success names the per-ecosystem offline database and the ruled non-Python
  proposal outcome through a `bmad-spec` re-derive; no `SPEC.md` hand edit.
- **AC7 — Green.** `pixi run -e pyforge-guild platform-ci-local -- --test` and
  `pixi run --frozen -e pyforge-warden pyforge-warden-test` pass.

## Boundaries & Constraints

**Always:** the scan stays `--offline`; provisioning runs only on a connected runner or an operator's machine, never
inside the scan; container and artifact scanning stay out of scope.

**Never:** queue a proposal for an npm, Go or Cargo finding; download a database from inside a test; hand-edit
`SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-warden` CAP-26 (FR-43) — the fleet's security axis over non-Python lockfiles; a fix,
  no new CAP.

Parent: CAP-26

- EGM audit finding carried: WAR-M-Z2 (cluster WAR-CL-6; accepted 2026-11-01; one memlog event on
  `spec-pyforge-warden/.memlog.md`); operator ruling 2026-11-01 (the memlog decision of that date); residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 16 — a fix story joins its done epic (operator rule 2026-10-04; doctor Story 41.5 lets the epic key roll up
  to `in-progress`).
- Ledger key: `16-8-the-fleet-worker-scans-non-python-lockfiles-against-provisioned-offline-dbs`.
- Ledger status at mint: `backlog`.
- Deps: S-16.6.
- Surface: `scripts/platform-provision-osv-offline-db.sh`, `src/shared/packages/django-warden/src/django_warden_fabric/tasks.py`, `src/shared/packages/django-warden/src/django_warden_fabric/proposals.py`,
  `.github/workflows/platform-ci.yml`, `src/platform/tests/test_warden_fleet_run.py`,
  `src/platform/tests/test_warden_fleet_proposals.py`.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Minted 2026-11-01 by the EGM audit landing (marshal Story 113.7, spec-pyforge-marshal:CAP-302); mode in-PR: built in the audit's landing PR.

## Verification

**Commands:**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass (the `django-warden` tests under
  `src/platform/tests/`, including `src/platform/tests/test_warden_fleet_run.py` and
  `src/platform/tests/test_warden_fleet_proposals.py`).
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).
- `bash -n scripts/platform-provision-osv-offline-db.sh` — expected: exit 0.

**Run before the push:**
- On a connected machine: `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY=<scratch dir> pixi run -e pyforge-warden bash scripts/platform-provision-osv-offline-db.sh`
  — expected: the four databases present, and a second run reports each as already provisioned.

## Auto Run Result

Status: done

Summary: implemented 2026-11-01 in the EGM audit landing worktree (branch `egm-audit-2026-11`, not committed). The
provisioning script now fills the PyPI, npm, Go and crates.io offline databases. The fleet worker scans against the
cache a setting names. Only a `vuln:` finding on a PyPI or conda component queues a proposal (operator ruling
2026-11-01).

What changed:
- `scripts/platform-provision-osv-offline-db.sh` (AC1): it checks each of `PyPI`, `npm`, `Go`, `crates.io` under
  `<cache>/osv-scanner/<eco>/all.zip` with the existing non-empty-zip test. It prints "already provisioned" for each
  present one, and exits 0 before it needs `osv-scanner` when all four are present. Otherwise it writes one minimal
  bootstrap input per missing ecosystem only (`requirements.txt`, a v3 `package-lock.json`, a `go.mod`, a
  `Cargo.lock`) and runs one `osv-scanner scan --offline-vulnerabilities --download-offline-databases -L ...` over
  them. It then re-checks each one and names every database still missing.
- `src/shared/packages/django-warden/src/django_warden_fabric/tasks.py` (AC2, AC3, AC5): `_run_warden_engines` runs
  the in-process `warden scan` inside `_osv_db_cache_env()`. That reads the `WARDEN_OSV_DB_CACHE_DIRECTORY` setting
  (`FLEET_OSV_DB_CACHE_SETTING`) with `getattr(settings, ...)`, sets osv-scanner's own
  `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` for the call, and restores the worker's environment afterwards. When the
  setting is unset, the worker's own environment stands. The fleet scan, the approve-time re-scan (Story 16.7) and
  the compliance job all go through it. No settings file changed, the same pattern as Story 16.7's expiry setting.
  The scan stays `--offline`. An ecosystem with no database stays
  `indeterminate:offline-db-unavailable-ecosystem:<eco>`, which is unchanged warden behaviour.
- `src/shared/packages/django-warden/src/django_warden_fabric/proposals.py` (AC4): `queue_proposals_from_scan` skips
  an outcome whose `ecosystem` is present and is neither `pypi` nor `conda` (`_is_non_python_outcome`). Its finding
  and its outcome stay in the scan's stored `report_json`. Hygiene `DEP002` removal outcomes are unchanged: they are
  deptry's, so always Python, and the ruling is about vulnerability proposals.
- Deviation from the Surface, needed for AC4: the stored report named no ecosystem for a finding. `Finding` has no
  ecosystem slot, and the outcome carried only `subject`, so `proposals.py` had nothing to queue on. In a mixed repo a
  name match could not tell an npm `lodash` from a PyPI one. So warden labels the outcome:
  `src/shared/packages/pyforge-warden/src/pyforge/warden/actuator.py` adds `PROutcome.ecosystem` (emitted by
  `to_json_dict` only when set, an additive key in the report's open `actuation` slot, so no schema change and no
  existing output moves) and `label_outcome_ecosystems`.
  `src/shared/packages/pyforge-warden/src/pyforge/warden/native_lockfiles.py` adds `native_vuln_ecosystems` (each
  `vuln:` finding a native lockfile scan produced, mapped to `Ecosystem.value`: `npm`, `golang`, `cargo`, ...).
  `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` labels the actuation right after `run_actuator`. The
  CLI's own `--open-fix-prs` behaviour is unchanged.
- `.github/workflows/platform-ci.yml` is not changed. Its daily cache key already rolls, so the first run on the day
  this lands downloads the three new databases beside the restored PyPI one, and every later day's cache holds all
  four. The golden-path step needs nothing else.
- Tests:
  - `src/platform/tests/test_warden_fleet_run.py` runs the real in-process scan over the real `osv-scanner`, against
    fixture databases built from warden's in-repo OSV records. The fixture sets the flags, writes an empty KEV feed,
    removes any inherited OSV cache variable, and puts an argv-logging `osv-scanner` wrapper on `PATH`.
    - AC2/AC5: a repo with the `npm_vuln` lock and the setting at an npm cache yields
      `vuln:PDOS-NPM-FIXTURE-0001:...` and no `offline-db-unavailable-ecosystem` finding. The worker's environment is
      restored, and every logged `scan` argv has `--offline` and no `--download-offline-databases`.
    - AC3: with a PyPI-only cache, the status is `indeterminate`, driven by `...-ecosystem:npm`.
    - AC4 end to end: `run_fleet_run` over a repo holding `vuln_high` and the npm lock queues
      `vuln:PDOS-FIXTURE-0002:...` and not the npm finding, whose outcome is `planned` with `ecosystem: npm`.
  - `src/platform/tests/test_warden_fleet_proposals.py`: a hand-built report with npm, golang and cargo-labelled
    outcomes, a conda-labelled one and an unlabelled one queues exactly the last two. The native findings stay in the
    stored report.
  - `src/platform/tests/test_golden_path_promotion_osv_db.py` (also outside the Surface): with the new script, its
    PyPI-only skip test would have downloaded three real databases from inside the suite, against the Boundary. It now
    builds all four databases and asserts that the fake `osv-scanner` is never called. A new AC1 test drives the
    script with a fake `osv-scanner` that writes a zip per `-L` input. An empty cache gets all four from one call with
    the four inputs. A re-run reports four "already provisioned" lines and makes no call. Removing `npm/all.zip` makes
    the next run pass only `package-lock.json`.
  - `src/shared/packages/pyforge-warden/tests/unit/test_non_python_lockfiles.py`: unit tests for
    `native_vuln_ecosystems` and `label_outcome_ecosystems`, and a CLI test where one `--fix-prs-dry-run` scan of a
    mixed project labels the npm outcome `npm` and leaves the PyPI one unlabelled. This test was mutation-checked on a
    scratch copy of the package: dropping the `cli.py` label line makes it fail.
- AC6: one surface-reconcile event naming every path above, and one event stating CAP-26's new success, were appended
  to `spec-pyforge-warden/.memlog.md`. CAP-26 takes them through the `bmad-spec` re-derive phase (with WAR-CL-3).
  `SPEC.md` was not edited.

Commands run (exit codes read from `$?`):
- `bash -n scripts/platform-provision-osv-offline-db.sh`: 0.
- Run before the push, on this connected machine, into a scratch dir:
  `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY=<scratch> pixi run --frozen -e pyforge-warden bash scripts/platform-provision-osv-offline-db.sh`:
  0, provisioned `PyPI` (36M), `npm` (210M), `Go` (13M) and `crates.io` (3.6M) in about 15 s. The second run: 0, four
  "already provisioned" lines. A real `warden scan --fix-prs-dry-run` of a `lodash@4.17.20` lock against that cache
  gave five `vuln:GHSA-...:lodash@4.17.20` findings, each outcome `planned` with `ecosystem: npm`.
- `pixi run --frozen -e pyforge-warden pyforge-warden-test`: 0 (2229 passed; 265 passed).
- `pixi run --frozen -e pyforge-warden pyforge-warden-coverage-gate`: 0. It measures committed changes only, so it
  reported no touched module here.
- `mypy --cache-dir .mypy_cache/pyforge-guild -p pyforge.warden` (pyforge-guild's mypy, from the package directory,
  the `lint-types` mypy leg for this package): 0, no issues in 44 files.
- `ruff check` / `ruff format --check` (pyforge-guild's ruff, each package's own config) over the changed
  pyforge-warden and django-warden files, and platform-ci-test's ruff over the three platform test files: 0 / 0.
- `pixi run -e pyforge-guild platform-ci-local -- --test`: 0. `RESULT: PASS` (manage.py check, ruff, ruff format,
  mypy over 192 files, the policy suite with 98 passed, sqlmigrate extraction ok with 20 first-party migrations, the
  full suite with 1372 passed and 14 skipped). The 14 skips are the same count as before this change.

## Spec Change Log

- 2026-11-01: minted `backlog` from the EGM fleet audit (marshal Story 113.7): cluster WAR-CL-6, finding WAR-M-Z2,
  accepted by the operator; operator ruling 2026-11-01 (a non-PyPI or conda vulnerability proposal is never queued);
  mode in-PR.
- 2026-11-01: implemented, `in-review`. Deviation from the Surface: three pyforge-warden modules
  (`actuator.py`, `native_lockfiles.py`, `cli.py`) label each native lockfile finding's actuation outcome with its
  ecosystem, because the stored report had nothing for `proposals.py` to queue on.
  `src/platform/tests/test_golden_path_promotion_osv_db.py` changed so that no test downloads a database.
  `.github/workflows/platform-ci.yml` is unchanged.

## Review Triage Log

- **Review 1 (2026-11-01, reviewer: independent session) — PASS.**
  - Checked: the provisioning script (`bash -n` exit 0), `_osv_db_cache_env`, the `proposals.py` filter, `PROutcome.ecosystem`, `label_outcome_ecosystems`, `native_vuln_ecosystems` and the `cli.py` label line against AC1-AC7 and the Boundaries; the Surface deviation (three pyforge-warden modules) is needed for AC4 and recorded.
  - Common evidence (one run for all eight stories, exit codes read from `$?`): `pixi run --frozen -e pyforge-warden pyforge-warden-test` exit 0 (2255 unit+meta, 265 other); the twelve touched warden unit/meta test files together exit 0 (290 passed, 0 skipped; opengrep 1.30.2 and osv-scanner present); `ruff check` and `ruff format --check` over every changed warden, django-warden and platform test file exit 0; `python scripts/lint_types.py ruff-format` exit 0 and `python scripts/lint_types.py mypy` exit 0 (`pyforge-warden ok`); `pixi run --frozen -e pyforge-guild lint-types` exit 1 only from `pyforge-doctor`'s I001 in `tests/unit/test_sources_pages_liveness.py`, another station's in-flight file (`pyforge-warden` and `django-warden` ruff legs ok); `pixi run -e pyforge-guild platform-ci-local -- --test` (private ports) exit 0, RESULT: PASS, 1377 passed / 14 skipped; touched warden modules' unit coverage all at or above 81%. Mutations ran on scratch copies only (warden via `PYTHONPATH`, django-warden via `pytest -o pythonpath=`), never on the worktree.
  - The four warden platform test files alone, against a private PostgreSQL: 106 passed, 1 skipped; the AC2, AC3 and AC4 tests run the real osv-scanner `--offline` against fixture databases, and the provisioning tests use a fake osv-scanner (no download).
  - Mutation: removing the ecosystem filter in `proposals.py` turns 2 red (the queue test and the end-to-end run).
  - Reports carrying `ecosystem` validate against `report-schema.json` at 1.1.0 (reviewer probe; `actuation` is an open slot).
  - Not re-run by the reviewer: the live connected provisioning (it downloads about 260 MB of OSV databases); the implementer's run is recorded, and the fake-scanner test covers the per-ecosystem logic.
  - Carried forward, not held against the story: the CAP success-line change is recorded on `spec-pyforge-warden/.memlog.md`; `SPEC.md` is unchanged, as required, and the line waits for the session owner's `bmad-spec` re-derive.
  - Observations for the session owner, not failures: platform-ci's daily golden-path cache miss now downloads all four databases (about 260 MB, was 36 MB); `_osv_db_cache_env` sets `os.environ` for the scan's duration, which is safe under a prefork worker but not under a threaded pool.
  - Failures: none.
