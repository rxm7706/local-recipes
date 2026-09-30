---
title: "77.1: The console lists Tier-2 Specs and the archived Dreams"
type: 'fix'
created: '2026-09-29'
status: 'done'
baseline_revision: 'd4ed036eb7f317a1650a72afb64c618bb41539c9'
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

## Code Map

- `src/platform/platformapp/front_door/runtime_catalog.py` -- `catalog_entries` mapping: `"specs"` (line 41, `_stems(docs/specs)`)
  and `"archived"` (line 46, `_stems(docs/dreams)`) are the only two entries to change; `"guild"` and `"dreams"` keep reading
  `docs/dreams`. `_stems`, `_story_specs`, `_ledger_titles`, `_projects` are the local helper idiom (stdlib `Path`, `[]` when
  the directory is missing).
- `src/platform/platformapp/front_door/views.py:113` -- `console_catalog` calls `catalog_entries(surface_id)` with no root;
  read-only, unchanged.
- `src/platform/platformapp/front_door/console_parity.py` -- `Surface`/`HOMES` rows for `specs` and `archived`; ids and URLs
  stay, so read-only.
- `src/platform/tests/test_console_parity_homes.py:213` -- `test_catalog_entries_empty_root` is the sibling for the new
  unit tests; `test_catalog_pages_scan_tracked_files` (line 190) already asserts both console URLs return 200 (AC 5).
- Live-tree evidence (2026-09-30): 175 `spec-*` matches under the two Spec homes, 171 with a `SPEC.md`, no duplicate folder
  name; `spec-*` also matches story-spec `.md` files, which drop out on the `SPEC.md` test; `archive/docs/dreams/` holds 6
  stems; `docs/dreams/*.md` frontmatter carries inline YAML comments (`status: archived   # 2026-09-16 …`) and 35 files open
  with a glued `---title:` line (not frontmatter).

## Tasks & Acceptance

**Execution:**
- `src/platform/platformapp/front_door/runtime_catalog.py` -- `"specs"` -> `_spec_folders(base)`; `"archived"` ->
  `_archived_dreams(base)`; add `_frontmatter_status(path)` (stdlib, first line must be `---`, stops at the closing `---`,
  strips an inline ` #` comment and quotes, returns `None` on anything else) -- the two surfaces read the Tier-2 homes
- `src/platform/tests/test_console_parity_homes.py` -- unit tests beside `test_catalog_entries_empty_root` for every AC and
  the malformed-frontmatter matrix row, on `tmp_path` fixture roots -- proves the contract without the live tree

**Acceptance Criteria:** the five Given/When/Then rows in the intent contract above; the fifth (both console URLs return 200)
is already asserted by `test_catalog_pages_scan_tracked_files`.

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

## Spec Change Log

_Empty until the first `bad_spec` loopback._

## Review Triage Log

- No independent review has run yet (implementation and review stay separate). _(Mint-time line; superseded by the entry below.)_

### 2026-09-30 — Review pass
- verdicts: 28 findings — high 0, medium 3, low 13, false 12, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind Hunter: 34 archived Dreams with a glued `---title:` opener are left out of `archived` — the outcome is real but specified: the matrix row "malformed frontmatter -> treated as not archived, no exception" mandates it. Root cause is 34 pre-existing malformed openers (doctor's one_chain already reports them as unreadable frontmatter); the fold PRs move them under `archive/docs/dreams/`, which the reader lists regardless of frontmatter. Recorded as a residual risk.
  - `[medium]` `[patch]` Blind Hunter: no test proves the headline regression on the real tree — `test_catalog_pages_scan_tracked_files` asserted only HTTP 200 for the two pages, and `console_catalog.html` renders `<li class="empty">none</li>` with a 200 for an empty list. Patched: the test now asserts `<li>spec-one-chain-per-station</li>` on `/console/specs/` and `<li>deckcraft</li>` on `/console/archived/`. Grouped with the Verification Gap and Intent Alignment rows on the same root cause.
  - `[low]` `[reject]` Blind Hunter: Specs under `archive/_bmad-output` and `archive/docs/governance` are listed nowhere — the intent names exactly two Spec homes by glob and asks for no archived-Spec list; the fix is new behaviour, not a correction.
  - `[low]` `[reject]` Blind Hunter: the eager `mapping` dict now runs both new readers on every surface — real, measured on the live tree at 4.7 ms before and 16.7 ms after per `catalog_entries` call; the eager dict is the pre-existing shape, and the fix (lazy mapping) rewrites every entry, which Task 2 excludes ("the `specs` and `archived` entries only").
  - `[false]` `[reject]` Blind Hunter: the baseline stamp carries other stories' paths the 77.1 memlog entry does not name — every stamped path is already named on this Spec's memlog (76.1, 76.2, 25.1 entries, counts 1-5 each) and both guards exit 0. Moot now: the scoped stamp is reverted, see Auto Run Result.
  - `[low]` `[reject]` Blind Hunter: the Code Map has stale line references and stale evidence (175/171, 35 glued) — the figures were mine and are wrong; the fix edits this build's spec, which triage rejects. The measured figures are in Auto Run Result.
  - `[low]` `[reject]` Blind Hunter: `_spec_folders` collapses same-named folders with no test — no duplicate exists on the live tree (175 folders, 175 unique names) and the intent does not specify a duplicate rule for `specs`; pinning it would encode an unrequested contract.
  - `[low]` `[reject]` Blind Hunter: `_frontmatter_status` edge cases (BOM untested, case-sensitive, first `status:` wins, mismatched quotes, binary test name) — none occurs in `docs/dreams/`; the reader matches doctor's parse on the live tree (124 to 124); the fix is guards and tests beyond the matrix.
  - `[false]` `[reject]` Blind Hunter: the spec records no run evidence for its Verification commands — Auto Run Result records each command and exit code.
  - `[false]` `[reject]` Edge Case Hunter: glued `---title:` Dreams marked archived are missing — same claim and refutation as the first row.
  - `[low]` `[reject]` Edge Case Hunter: eager mapping runs both readers for every surface — same as the fourth row.
  - `[low]` `[reject]` Edge Case Hunter: `docs/dreams/archive/pyforge-unifying-strategy-2026-08-23-topology.md` is missed by the non-recursive glob — the file exists, but the intent names `docs/dreams/*.md` and the `dreams` and `guild` surfaces read the same non-recursive glob; one file, and recursion is a behaviour change.
  - `[low]` `[reject]` Edge Case Hunter: dot-named project dirs and same-named Specs are collapsed — no dot-named project dir exists (`ls -a _bmad-output/projects` shows none) and no duplicate name exists; a guard would answer a case nobody reached.
  - `[false]` `[reject]` Edge Case Hunter: `_frontmatter_status` returns `''` for an empty `status:` and reads an unclosed block to EOF — its only caller compares `== "archived"`, which `''` never equals, and a Dream is a small file; no bad outcome.
  - `[low]` `[reject]` Edge Case Hunter: the spec's live-tree evidence (175/171) is off, and 181 tracked `SPEC.md` files include archive ones — same as the sixth row.
  - `[false]` `[reject]` Edge Case Hunter: the console shows about 136 archived Dreams where 170 exist — same claim and refutation as the first row.
  - `[medium]` `[patch]` Verification Gap: the AC 5 page test never observes the new Specs and Archived lists — same root cause and same patch as the second row.
  - `[low]` `[reject]` Verification Gap: duplicate Spec folder names are not pinned (filed as defer) — same as the seventh row; low and this story's own code, so not a defer.
  - `[low]` `[reject]` Verification Gap: CRLF and BOM handling is untested (filed as defer) — same as the eighth row; no live file has a BOM or CRLF.
  - `[false]` `[reject]` Verification Gap, other: 34 glued Dreams marked archived are excluded — same as the first row.
  - `[low]` `[reject]` Verification Gap, other: `_frontmatter_status` differs from doctor's `_frontmatter_parse` on a leading HTML banner and a BOM — the host cannot import doctor (`pap:AD-2`) and Task 2 mandates a stdlib reader; the two agree on the live tree.
  - `[false]` `[reject]` Verification Gap, other: bare `pytest` on the file needs Postgres — every test in that file, including the sibling `test_catalog_entries_empty_root`, sits under the module `django_db` marker and runs in the lane that provisions it.
  - `[medium]` `[patch]` Intent Alignment: the tests exercise `catalog_entries` only, and the one page test asserts a status — same root cause and same patch as the second row.
  - `[false]` `[reject]` Intent Alignment: "other surfaces unchanged" is guarded for `dreams` only — the diff changes only the `specs` and `archived` mapping entries (read in the diff), so no other surface can move.
  - `[low]` `[reject]` Intent Alignment: the Code Map's 175 folders differ from the measured count — same as the sixth row.
  - `[false]` `[reject]` Intent Alignment: 124 of about 158 archived Dreams are listed today — same as the first row.
  - `[false]` `[reject]` Intent Alignment: silent resolutions (spec-name de-duplication, inline-comment and quote stripping, "tracked" as a glob) — none contradicts the intent; the comment stripping is required (the live tree carries `status: archived   # …`), and every other reader here globs the same way.
  - `[false]` `[reject]` Intent Alignment: the diff adds tests beyond the intent's list (unreadable and non-UTF-8 files) — additive coverage of the `OSError` branch, not a defect.

## Auto Run Result

Status: done

**Summary.** The console's `specs` and `archived` surfaces now read the Tier-2 homes. `specs` lists the folder names of `spec-*` folders that hold a `SPEC.md` under `_bmad-output/projects/*/planning-artifacts/specs/` and `docs/governance/`, sorted and de-duplicated. `archived` lists the stems under `archive/docs/dreams/*.md` plus each `docs/dreams/*.md` whose frontmatter reads `status: archived`, de-duplicated and sorted. The frontmatter reader is stdlib only. Surface IDs, URLs, views and templates are unchanged, and `src/platform/` imports no `pyforge.*`.

**Files changed.**
- `src/platform/platformapp/front_door/runtime_catalog.py` -- `_spec_folders`, `_archived_dreams`, `_frontmatter_status`; the two mapping entries repointed.
- `src/platform/tests/test_console_parity_homes.py` -- six unit tests for every acceptance criterion and the matrix rows; the page test now asserts real entries on both pages.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md` -- surface-reconcile entry naming both paths (the one Spec that governs them; `spec-surface` names no co-governor).
- This story spec -- Code Map, Design Notes, triage log, result.

**Review.** 28 findings across four layers. Patches applied: 1 entry (medium, three rows, one root cause). Deferred: none. Rejected: 25, each with its reason in the log above.

**Verification** (exit codes read from files, never a pipe; run on the final tree):
- `pixi run -e pyforge-guild platform-ci-local -- --test` -- exit 0 (96 policy tests, 1057 full-suite passed, 13 skipped).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- exit 0 (1896 passed, 2 skipped).
- `pixi run -e pyforge-guild spec-surface-check` -- exit 0; `python scripts/spec_surface_reconcile.py` -- exit 0.
- Matrix Test Audit: every matrix row has a covering test, collected and passed in the lane (`test_catalog_specs_lists_tier2_spec_folders`, `..._archived_unions_archive_home_and_marked_dreams`, `..._archived_lists_a_slug_in_both_places_once`, `..._archived_ignores_malformed_frontmatter`, `..._archived_survives_an_unreadable_dream`, `..._specs_and_archived_empty_root`).
- Coverage: the lane does not measure the platform's 100% floor, so I ran the six new tests DB-free under `coverage`: `runtime_catalog.py` misses only lines 27-30 (`_repo_root`'s image-shape fallback, not new code, covered by other tests in the full suite); every new line (57-97) is covered.

**Stamp reverted, against the story's Task 5.** The implementation pass ran a scoped `--write-baseline --spec pyforge-steward/spec-pyforge-unifying-strategy`, following Task 5, but this run's dispatch instruction is "never pass `--write-baseline`". I restored `scripts/.spec-surface-baseline.json` to its `baseline_revision` content (zero diff). Both guards exit 0 on the memlog entry alone. The stamp is left to the landing.

**Corrected live-tree figures** (2026-09-30; the Code Map above is wrong on these): 176 `spec-*` directories under the two Spec homes, 175 holding a `SPEC.md`, 175 unique names (1,393 raw glob matches once story-spec `.md` files count); 34 Dreams (not 35) open with a glued `---title:`.

**Residual risks.**
- On today's tree, `archived` lists 130 Dreams (124 from `docs/dreams/` plus the 6 under `archive/docs/dreams/`) and omits 34 marked `status: archived` behind a glued opener, as the matrix requires; the fold PRs close it.
- Archived Specs under `archive/` and the one Dream under `docs/dreams/archive/` are listed nowhere; the intent does not ask for them.
- Each catalog call now does about 12 ms more work on every console page.

Follow-up review recommended: `false` (one patched entry, verdict medium).

## Design Notes

`archived` is a union, not a move: today the archived Dreams still sit in `docs/dreams/` (marked by frontmatter), after the
fold PRs they sit under `archive/docs/dreams/`. One reader serves both, so the fold PRs need no second catalog change.
A frontmatter status is the first-line-`---` block only; a file that does not open with `---` (the glued `---title:` form)
is not archived, by the matrix row, and never raises.
