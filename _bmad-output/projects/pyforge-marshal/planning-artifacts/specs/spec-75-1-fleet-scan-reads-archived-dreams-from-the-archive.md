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

Status: blocked
Blocking condition: intent gap. The approach (read `archive/docs/dreams/*.md` in both places) contradicts Acceptance Criterion 1 ("today's tree: `scan_dreams()` returns exactly the rows it returns before this change") and the manual check that `fleet-picture` output is identical before and after.

Evidence (measured 2026-09-29 in the dispatch worktree, before any code change):

- `archive/docs/dreams/` already holds six Dream files (last touched by commit `e07834580d8`, and older ones): `deckcraft.md` (status `specified`, owner `herald`), `design-code-bridge.md` (`realized`, `herald`), `herald-pitch-deck-family-expansion.md` (`dreamt`, `herald`), `modernist-identity.md` (`realized`, `herald`), `pyforge-genesis.md` (`specified`, `guild`), `video-scripts.md` (`dreamt`, `herald`).
- None has `status: archived`, and none has a twin in `docs/dreams/`, so the "first copy of each slug" rule does not drop any of them.
- `scan_dreams()` (`scripts/fleet_scan.py:1043`) and `_fleet_chains()` (`scripts/fleet_scan.py:1616`) read only `docs/dreams/*.md` today. An unconditional archive read adds six Dream rows and six fleet chains to today's output, and `pyforge-genesis` (`owner: guild`, not in `GUILD_DREAMS`) also gains a `[dreams] WARN`. Criterion 1 and the identical-`fleet-picture` check then fail.

Two readings lead to different, observable outcomes, and nothing in the spec selects between them:

1. **Read every `archive/docs/dreams/*.md`** (the Approach as written). The six stragglers become visible in the console and the fleet chains now. Criterion 1 and the identical-output check must be reworded to "the `docs/dreams/` rows are unchanged and the archive rows are added".
2. **Read only archive Dreams whose frontmatter says `status: archived`** (the "moved archived Dream keeps its row" case). Every criterion holds as written, but the six stragglers stay hidden, and the filter is a rule the spec does not state. CHAIN-STANDARD §11 says an archived Dream sits under `archive/docs/dreams/`; it does not say every file there reads `status: archived`.

Questions for the operator:

1. Should the six existing `archive/docs/dreams/` files appear in the console and fleet chains after this story (reading 1), or stay out until a fold PR restates their status (reading 2)?
2. Whichever reading holds, which criterion text changes (Criterion 1 and the manual `fleet-picture` check for reading 1; the Approach and a new "non-archived file in the archive" criterion for reading 2)?

Also noted, not part of the blocker: `scripts/fleet_scan.py:1139` (`scan_specs()` sets a Spec row's `dream` from `DREAMS_DIR / f"{slug}.md"`) and the per-chain artifact globs at lines 1924, 1934, 2104 and 2647 build `docs/dreams/<slug>.md` paths. The spec names two read sites only; these will need the same treatment before the first fold PR moves a Dream.

No code, test, ledger or `SPEC.md` file was changed. Only this story spec's `status` moved.
