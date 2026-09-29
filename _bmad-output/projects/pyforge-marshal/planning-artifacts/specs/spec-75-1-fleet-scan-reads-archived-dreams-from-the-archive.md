---
title: "75.1: fleet_scan reads archived Dreams from the archive"
type: 'chore'
created: '2026-09-29'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - scripts/fleet_scan.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_fleet_scan_currency_feeds.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-one-chain-per-station` CAP-11 (operator ruling 2026-09-29) moves archived Dreams from `docs/dreams/` to
`archive/docs/dreams/`. `scripts/fleet_scan.py` reads Dreams from `docs/dreams/` only, in two places:

- `scan_dreams()` (line ~1043) builds the console's Dream rows: slug, title, status, owner, archived reason. The
  console's Archived tab lists the rows whose status is `archived`. After the move those rows would vanish.
- `_fleet_chains()` (line ~1616) maps each Spec to a station, falling back to its `owner-dream`'s owner. Absorbed Specs
  point at archived satellite Dreams, so after the move their `owner-dream` would resolve to nothing and they would lose
  their station.

CHAIN-STANDARD §11 requires every reader that lists Dreams to follow them before the first fold PR moves a file.

**Approach:** both places also read `archive/docs/dreams/*.md`, after `docs/dreams/*.md`, and keep the first copy of each
slug. `DREAMS_DIR` stays as it is; a second constant names the archive. The row shape and the console's tabs do not change.
`_fleet_chains()`'s lookup is by stem, so it keeps working once the fold PR repoints each `owner-dream` to the archive path.

Ledger key: `75-1-fleet-scan-reads-archived-dreams-from-the-archive`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- `spec-one-chain-per-station` CAP-11 (the Guild's; Marshal mints no CAP and no FR, as Epic 74 does for
  `spec-feature-flag-governance`); CHAIN-STANDARD §11.
- `spec-feature-flag-governance` Q1: a `chore` needs no flag. This story keeps an existing surface's output the same across
  a planned file move.
- Siblings: doctor Stories 36.1 and 36.2, herald Story 33.1.

## Acceptance Criteria

- Given today's tree When `scan_dreams()` runs Then it returns exactly the rows it returns before this change
- Given a fixture archived Dream in `docs/dreams/` When it moves to `archive/docs/dreams/` Then `scan_dreams()` returns the same row for it (slug, title, status, owner, archived reason)
- Given one slug in both directories When `scan_dreams()` runs Then the `docs/dreams/` copy is returned, once
- Given an absorbed Spec whose `owner-dream` is repointed to the moved Dream's archive path When `_fleet_chains()` runs Then the Spec keeps its station
- Given no `archive/docs/dreams/` directory When the scan runs Then it behaves as today
- Given the archive read is removed When the moved-Dream test runs Then it fails (mutation)

## Tasks

1. Read `scan_dreams()` and `_fleet_chains()` in `scripts/fleet_scan.py`, and how
   `src/shared/packages/pyforge-doctor/tests/unit/test_fleet_scan_currency_feeds.py` loads the script and injects a temporary
   tree.
2. Add an archive-directory constant and read it in both places, `docs/dreams/` first, one row per slug.
3. Add `tests/scripts/test_fleet_scan_archive.py` covering every acceptance criterion, loading the real script the same way
   the doctor tests do.
4. Run the new test, `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`, and compare `fleet-picture` output on
   `main` before and after the change. Read each exit code.
5. Reconcile every Spec `spec-surface-check` names for `scripts/fleet_scan.py`: memlog first, `git add`, then a scoped
   `--write-baseline --spec` for each.

## Boundaries & Constraints

**Always:**
- Keep the row shape and every tab's meaning.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not move any Dream in this story.
- Do not repoint any `owner-dream`; the fold PRs do that.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| today's tree | no Dream moved | identical rows | — |
| Dream moved | archived Dream under the archive | same row | — |
| slug in both | two copies | `docs/dreams/` copy, once | — |
| Spec whose Dream moved | `owner-dream` repointed | station kept | — |
| no archive directory | — | as today | — |

</intent-contract>

## Binding

Parent capability: `spec-one-chain-per-station` CAP-11 (Guild relay; no marshal CAP or FR).
Dream: `docs/dreams/one-chain-per-station.md` → § *2026-09-29 — One archive home*.
Ledger key: `75-1-fleet-scan-reads-archived-dreams-from-the-archive`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none. This is a `chore` (`spec-feature-flag-governance` Q1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_fleet_scan_archive.py -q` — expected: pass.
- `pixi run -e pyforge-guild fleet-picture` before and after the change on `main` — expected: identical output.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
