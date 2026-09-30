---
title: "75.1: fleet_scan reads archived Dreams from the archive"
type: 'chore'
created: '2026-09-29'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'c8f74d5657bc67459115281f75afbbd577401c09'
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

- Given today's tree When `scan_dreams()` runs Then every row read from `docs/dreams/` is exactly what it was before this change, and the only additions are the six Dreams already under `archive/docs/dreams/` (`deckcraft`, `design-code-bridge`, `herald-pitch-deck-family-expansion`, `modernist-identity`, `pyforge-genesis`, `video-scripts`), each reported as archived (location is the archive signal, whatever its frontmatter `status`), with their fleet chains
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
| today's tree | no Dream moved | `docs/dreams/` rows identical; the six already-archived Dreams added as archived | — |
| Dream moved | archived Dream under the archive | same row | — |
| slug in both | two copies | `docs/dreams/` copy, once | — |
| Spec whose Dream moved | `owner-dream` repointed | station kept | — |
| no archive directory | — | as today | — |

</intent-contract>

## Spec Change Log

- 2026-09-30 -- operator ruling, unblocked (contract amended; recorded on `spec-one-chain-per-station`'s memlog and `epics.md` Story 75.1): take this spec's own option 1 -- read every `archive/docs/dreams/*.md`. The six Dreams already there (`deckcraft`, `design-code-bridge`, `herald-pitch-deck-family-expansion`, `modernist-identity`, `pyforge-genesis`, `video-scripts`) become visible now, which is CAP-11's intent ("the console's Archived column still counts archived Dreams"). None of the six reads `status: archived`, so a Dream read from `archive/docs/dreams/` is reported as archived whatever its frontmatter says (CHAIN-STANDARD §11: a Dream is live in `docs/dreams/` or archived under `archive/`); a slug in both places is read from `docs/dreams/`. Criterion 1, the matrix row and the fleet-picture check are reworded to match. First bring `origin/main` into this branch (merge, never rebase); the work already done is kept.

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
- `pixi run -e pyforge-guild fleet-picture` before and after the change on `main` — expected: identical except that the six already-archived Dreams (and their chains) are now counted, as archived.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).

## Auto Run Result

Status: in-review (implemented under the 2026-09-30 operator ruling; no independent review has run yet).

Changed:

- `scripts/fleet_scan.py`
  - Adds `ARCHIVE_DREAMS_DIR` (`archive/docs/dreams/`) beside the unchanged `DREAMS_DIR`, and one helper, `_dream_files()`. The helper reads `docs/dreams/*.md` and then `archive/docs/dreams/*.md`, skips `README.md`, keeps the first copy of each slug, and returns `(path, in_archive)` pairs.
  - `scan_dreams()` and `_fleet_chains()` both iterate `_dream_files()`. A Dream read from the archive reads `status: archived` whatever its frontmatter says. The row shape does not change.
  - Two dead locals are removed from code this story reads: `proj` in `_stage_globs` and `total_h` in the velocity block.
- `tests/scripts/test_fleet_scan_archive.py` (new, allowlisted under `tests/**`). It loads the real script by `importlib` into temporary trees and has one test per acceptance criterion, plus a frontmatter-override test.
- `spec-pyforge-marshal/.memlog.md`: a surface-reconcile event for `scripts/fleet_scan.py`.
- `origin/main` is merged into the branch twice, never rebased: `c8f74d5657` (the ruling's precondition), then `14434a231e` (scribe 25.1, #1686).

Evidence:

- New test, 7 tests: exit 0 in `-e pyforge-guild` and exit 0 in `-e pyforge-ci`, the CI lane's environment.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: exit 0, with 8939 passed and 1 skipped. Measured after the second merge.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test`: exit 0, with 1039 passed and 7 skipped.
- `detectors-ci`: exit 0 after the second merge. Before that merge it exited 1 on `bmad-estate-check` alone. The cause was a `skills` section drift from the gitignored `.claude/skills/caveman/`, which is not this story's; scribe 25.1 on `main` fixed it.
- `spec-surface-check`: exit 0.
- Criterion 1 on today's tree. The before/after `scan_dreams()` snapshot:
  - Dream rows go from 174 to 180. The `docs/dreams/` rows are byte-identical.
  - The only additions are `deckcraft`, `design-code-bridge`, `herald-pitch-deck-family-expansion`, `modernist-identity`, `pyforge-genesis` and `video-scripts`, all reading `archived`.
  - Fleet chains go from 183 to 189, with no existing chain changed. Five of the new chains carry `pyforge-herald`; `pyforge-genesis` has no project and owner `guild`.
  - The Archived tab goes from 119 to 125, with every earlier row unchanged.
  - Backlog rows are unchanged. The practice list gains `modernist-identity`.
- Mutation: with the archive tuple removed from `_dream_files()`, 6 of the 7 tests fail, including the moved-Dream test. The file was restored and checked with `cmp`. The test suite also carries its own mutation test: it rewrites a copy of the script to read only the live directory and asserts that the moved-Dream check fails.
- `fleet-picture` exited 0 before and after. The only differences were live fleet state (scribe 25.1 building, the loop homes two commits further behind). `fleet-picture` does not read `fleet_scan.py`, so the six Dreams do not appear there; they appear in the console data (`fleet_scan.py` output) measured above.

Spec surface: `spec-surface-check` names no Spec. `scripts/fleet_scan.py` is governed by `spec-pyforge-marshal` alone, and its memlog moved in this change. The memlog entry is written, and the scoped `--write-baseline --spec pyforge-marshal/spec-pyforge-marshal` stamp is left to the landing, because a dispatch never stamps its own baseline.

Left open (outside this story's two read sites; each still builds a `docs/dreams/<slug>.md` path and needs the same treatment before the first fold PR moves a Dream):

- `scan_specs()` sets a Spec row's `dream` from `DREAMS_DIR`.
- The per-chain Dream-stage glob in `_stage_globs` and the Dream path in `_last_touched`.
- `_GIT_SCOPES` does not include `archive/`.
- `build_archived` links every archived row to `docs/dreams/<slug>.md`, which is wrong for the six archive Dreams. None of the six has an `archived_reason`, so each shows as "retired".
- `board._load_dashboard_generate` repoints `REPO_ROOT` and `DREAMS_DIR` but not `ARCHIVE_DREAMS_DIR`. This is harmless while the script resolves its repo root to the same tree.
- `pyforge-genesis` (`owner: guild`, not in `GUILD_DREAMS`) now raises a `[dreams] WARN` and a `[fleet] WARN` (no spec directory and no station owner). Both are advisory.
