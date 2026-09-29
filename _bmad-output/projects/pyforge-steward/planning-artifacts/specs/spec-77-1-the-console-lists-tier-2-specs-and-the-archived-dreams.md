---
title: "77.1: The console lists Tier-2 Specs and the archived Dreams"
type: 'fix'
created: '2026-09-29'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - src/platform/platformapp/front_door/runtime_catalog.py
  - src/platform/tests/test_console_parity_homes.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-one-chain-per-station:CAP-11` (operator ruling 2026-09-29) moves archived Dreams to `archive/docs/dreams/`
and retires `docs/specs/`. The host's front door reads both through `runtime_catalog.catalog_entries`:
- `"specs"` lists `docs/specs/*.md` stems. After doctor Story 37.1 it would list nothing, although the fleet has more than a
  hundred live Specs.
- `"archived"` lists every stem in `docs/dreams/`, live or archived: the same list as `"dreams"`. That is wrong today, and
  after the station fold PRs it would name no archived Dream at all.

CHAIN-STANDARD §11 requires every reader to follow before the PR that moves its files. The first reader set (doctor Epic
36, marshal Epic 75, herald Epic 33) missed this one, so it gates the first station fold PR as well as Story 37.1.

**Approach:** in `catalog_entries` only:
- `"specs"` lists the Spec folders that hold a `SPEC.md`: `_bmad-output/projects/*/planning-artifacts/specs/spec-*/` and
  `docs/governance/spec-*/`, by folder name, sorted.
- `"archived"` lists the stems under `archive/docs/dreams/*.md`, plus each `docs/dreams/*.md` whose frontmatter reads
  `status: archived` (the migration's remainder), de-duplicated and sorted.

The surface IDs, URLs, views and templates are unchanged. The catalog reads tracked files only and imports no station
package.

Ledger key: `77-1-the-console-lists-tier-2-specs-and-the-archived-dreams`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-one-chain-per-station:CAP-11` (the Guild's; Steward mints no CAP and no FR, the relay shape doctor's Epics 24, 25,
  32, 34 and 36 use); CHAIN-STANDARD §11.
- `pap:AD-2` (the host never imports `pyforge.*`).
- `spec-feature-flag-governance` Q1: a `fix` needs no flag.
- Siblings: doctor Story 37.1 (blocked on this story), atlas Story 26.1, herald Story 34.1, marshal Story 76.1; and the
  first reader set, doctor Stories 36.1 and 36.2, marshal Story 75.1, herald Story 33.1.

## Acceptance Criteria

- Given a fixture root with two Spec folders holding a `SPEC.md` and one without When `catalog_entries("specs", root)` runs
  Then it returns the two folder names, sorted
- Given a fixture root with one Dream under `archive/docs/dreams/`, one live Dream, and one `docs/dreams/` file reading
  `status: archived` When `catalog_entries("archived", root)` runs Then it returns the archived two and not the live one
- Given one slug in both Dream places When `catalog_entries("archived", root)` runs Then it is listed once
- Given an empty root When either surface is read Then it returns `[]`
- Given the running host When `/console/specs/` and `/console/archived/` are requested Then both return 200

## Tasks

1. Read `runtime_catalog.py` and `src/platform/tests/test_console_parity_homes.py`.
2. Change the `"specs"` and `"archived"` entries only. Read frontmatter with the stdlib, so the host adds no new
   dependency.
3. Add unit tests for every acceptance criterion beside `test_catalog_entries_empty_root`.
4. Run `pixi run -e pyforge-guild platform-ci-local -- --test` and `pixi run --frozen -e pyforge-steward
   pyforge-steward-test`, and read each exit code.
5. Reconcile every Spec `spec-surface-check` names for the edited files: memlog first, `git add`, then a scoped
   `--write-baseline --spec` for each.

## Boundaries & Constraints

**Always:**
- Keep every other surface's output unchanged.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not import a `pyforge.*` package in `src/platform/`.
- Do not move any Dream or Spec in this story.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| today's tree | archived Dreams still in `docs/dreams/` | `archived` lists them by frontmatter | — |
| after the moves | archived Dreams under the archive | `archived` lists them from the archive | — |
| folder without `SPEC.md` | a Spec folder that is empty | not listed | — |
| malformed frontmatter | a Dream with glued `---title:` | treated as not archived | no exception |

</intent-contract>

## Binding

Parent capability: `spec-one-chain-per-station:CAP-11` (Guild relay; no steward CAP or FR).
Dream: `docs/dreams/one-chain-per-station.md` → § *2026-09-29 — One archive home*.
Ledger key: `77-1-the-console-lists-tier-2-specs-and-the-archived-dreams`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none. This is a `fix` (`spec-feature-flag-governance` Q1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass (the platform lane).
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
