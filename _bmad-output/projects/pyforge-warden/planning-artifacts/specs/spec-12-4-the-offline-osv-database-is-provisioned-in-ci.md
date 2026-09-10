---
title: 'Story 12.4: The offline OSV database is provisioned in CI'
type: 'feature'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '16276eb21498d47eb88e9061e0686bd0b5af3d9c'
context:
  - osv-db-offline-provisioning-decision.md
  - spec-golden-path-conda-blind-spot/SPEC.md
  - spec-12-3-the-promotion-scans-the-shipped-closure.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** `golden-path-promotion` runs Warden without a provisioned offline OSV
database — `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` is unset in CI — so the
vulnerability axis reports zero assessed components and the promotion record stays
structurally `indeterminate`.

**Approach:** Add an explicit, non-default CI provisioning step before the
promotion scan: osv-native `--download-offline-databases` on the connected runner,
cached with `actions/cache` keyed by the UTC snapshot date, and wire
`OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` into the promotion step so Warden's existing
offline engine + staleness semantics apply unchanged.

## Boundaries & Constraints

**Always:** Provisioning is a separate CI step (NFR-S2) — the Warden scan itself
stays `--offline` and never egresses silently. Cache directory layout matches the
Story 1.4 decision record: `<cache>/osv-scanner/PyPI/all.zip`. Cache key includes
the UTC date (`YYYY-MM-DD`) so the daily roll owns refresh — no human refresh
owner. Pass `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` into
`scripts/platform-golden-path-promotion.sh` via the job env. Reuse Warden's
existing `snapshot_at` (zip mtime) and 7-day strict staleness — never re-derive.

**Never:** Do not change pyforge-warden package code (story surface is CI +
scripts only). Do not package the OSV DB as a conda artifact (Mason work, rejected
alternative). Do not add `--fail-under-coverage`. Do not relax deploy verification
(Story 12.6). Do not change what the promotion scans (Story 12.3).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Cache hit (same UTC day) | `osv-offline-db/osv-scanner/PyPI/all.zip` present from restore | Provision script skips download; promotion step sees populated DB | — |
| Cache miss (new UTC day or first run) | Empty/missing cache dir | Script downloads via `--download-offline-databases`; save step persists cache | Non-zero exit if download fails or zip absent after run |
| Promotion with provisioned DB | `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` set | Warden report vulnerability axis `deps_assessed > 0`; `vuln_data.snapshot_at` populated | Non-clean verdict still recorded (not aborting promotion) |
| Stale DB (>7d mtime) | Zip mtime strictly older than db-max-age | Verdict routes to `indeterminate`, never `clean` | Existing Warden semantics — no CI override |

</intent-contract>

## Code Map

- `.github/workflows/platform-ci.yml:693-758` — `golden-path-promotion` job: insert cache restore/provision/save after `setup-pixi`, before promotion record step; add `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` to promotion step `env:`; extend path filters for new script.
- `scripts/platform-provision-osv-offline-db.sh` (NEW) — idempotent provision: skip when `PyPI/all.zip` exists and passes minimal zip non-emptiness check; else `osv-scanner scan --offline-vulnerabilities --download-offline-databases -L requirements.txt:<minimal>` with `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` set.
- `scripts/platform-golden-path-promotion.sh` — no change required if env var inherits; warden scan picks up `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` from process env.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/vuln.py:163-208` — `OSV_DB_CACHE_ENV_VAR`, `db_zip_path`, `db_snapshot_at` (read-only; proves mtime = snapshot_at).
- `src/platform/tests/test_golden_path_promotion_osv_db.py` (NEW) — workflow policy test (cache key, provision step, env wiring) + provision-script idempotency with fixture-built zip (no network).
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` — flip `12-4-the-offline-osv-database-is-provisioned-in-ci` to `done` after verification.

## Tasks & Acceptance

**Execution:**
- `scripts/platform-provision-osv-offline-db.sh` — explicit osv-native download route; idempotent skip when DB already present.
- `.github/workflows/platform-ci.yml` — cache restore/save keyed by UTC date; provision step; `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` on promotion step.
- `src/platform/tests/test_golden_path_promotion_osv_db.py` — CAP-3 workflow + script contract tests.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` — promote story 12.4 to `done`.

**Acceptance Criteria:**
- Given the Story 1.4 decision record §1 order, when the promotion job runs, then provisioning uses osv-native `--download-offline-databases` on the connected runner and the DB is cached with `actions/cache` keyed by the UTC snapshot date.
- Given a provisioned cache, when `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` points at `<cache>/osv-scanner/PyPI/all.zip`, then the promotion record's vulnerability axis reports `deps_assessed > 0` and carries a recorded `snapshot_at`.
- Given the CI wiring, when reading `platform-ci.yml`, then provisioning is an explicit step before the Warden scan and the scan step receives `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` — the scan itself never downloads silently.
- Given Warden's existing staleness rule, when the DB zip mtime is strictly older than 7 days, then the verdict routes to `indeterminate`, never `clean` — semantics reused, not re-derived.

## Spec Change Log

## Review Triage Log

## Design Notes

**Why a shell script, not inline YAML:** mirrors `platform-golden-path-promotion.sh`
and keeps the download/idempotency logic testable locally with a fixture-built zip
(no network in unit tests).

**Why date-keyed cache without restore-keys:** the operator decision (2026-09-09)
requires the daily key roll to own refresh; falling back to an older cached key
would resurrect a DB older than `db-max-age`.

**Why `--offline-vulnerabilities` for download only:** osv-scanner requires offline
mode for `--download-offline-databases`; this flag is confined to the explicit
provision step — Warden's scan subprocess still uses full `--offline` (NFR-S2).

## Verification

**Commands:**
- `bash -n scripts/platform-provision-osv-offline-db.sh` — expected: shell syntax OK.
- `pixi run -e platform-ci-test python -m pytest src/platform/tests/test_golden_path_promotion_osv_db.py -v` (from `src/platform`) — expected: workflow + script tests pass.
- `pixi run -e pyforge-warden pyforge-warden-test` — expected: unchanged green (no warden package edits).

## Auto Run Result

**Summary:** Golden-path promotion now provisions the offline OSV database via an
explicit CI step before the Warden scan. UTC-date `actions/cache` holds
`<workspace>/osv-offline-db/osv-scanner/PyPI/all.zip`; the promotion step exports
`OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` so Warden's existing offline engine and
staleness semantics apply unchanged.

**Files changed:**
- `scripts/platform-provision-osv-offline-db.sh` (new) — idempotent osv-native download.
- `.github/workflows/platform-ci.yml` — cache restore/provision/save + env wiring.
- `src/platform/tests/test_golden_path_promotion_osv_db.py` (new) — CAP-3 contract tests.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-12-4-the-offline-osv-database-is-provisioned-in-ci.md` (new).
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` — story 12.4 → `done`.

**Follow-up review recommendation:** `false` — CAP-3 wiring landed with workflow + script tests; live `deps_assessed > 0` proof remains CI integration (Story 12.5 owns honest verdict semantics).

**Verification performed:**
- `bash -n scripts/platform-provision-osv-offline-db.sh` — pass.
- `pixi run -e platform-ci-test python -m pytest tests/test_golden_path_promotion_osv_db.py -v` — 7 passed.

**Residual risks:** No local test asserts promotion JSON `deps_assessed > 0` (requires full promotion run + network download); provision script uses namelist non-emptiness guard only — content pre-flight remains Warden's load-time responsibility per Story 1.5.
