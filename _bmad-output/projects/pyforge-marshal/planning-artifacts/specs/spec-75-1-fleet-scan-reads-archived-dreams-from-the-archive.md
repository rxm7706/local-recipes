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
deferred:
  - summary: >-
      fleet_scan's per-chain Dream lookups still build only `docs/dreams/<slug>.md`, so a chain whose Dream sits under
      `archive/docs/dreams/` reads as having no Dream.
    evidence: |-
      The dream-stage glob in `_stage_globs` (scripts/fleet_scan.py:1962 and :1971), the `_GIT_SCOPES` date index (:1723)
      and the `_last_touched` Dream prefix in `scan_fleet` (:2141) name only `docs/dreams/`. A `scan_fleet({}, None)` probe
      on 2026-09-30 showed all six archive chains (deckcraft, design-code-bridge, herald-pitch-deck-family-expansion,
      modernist-identity, pyforge-genesis, video-scripts) with `noDream: true`, a `dream` gap and `chainAudit.verdict: fail`.
      The rows are archived, so they stay out of the live flags and counts, and doctor's
      `chain-completeness --layers --project pyforge-herald` still reads 15/15. After a fold PR moves a live chain's Dream,
      that chain would lose its dream stage and date the same way. CHAIN-STANDARD §11 requires these readers to follow the
      move, as Stories, before the first fold PR moves a file. Doctor's `test_every_stage_glob_is_inside_the_git_date_index`
      requires the glob and `_GIT_SCOPES` to change together. `scan_specs()` (:1169) and `build_archived()`'s link (:2686)
      also build only the live path, but they are reached only from the uncalled `_generate()` (the next item). No sibling
      Story (doctor 36.1 and 36.2, herald 33.1, steward 77.1) covers these sites, and this story's intent names exactly two
      read sites, so they need their own Story before any fold PR.
    location: >-
      scripts/fleet_scan.py:1971
    severity: medium
  - summary: >-
      `_generate()` in scripts/fleet_scan.py has no caller, and it alone reaches `scan_dreams`, `scan_specs`,
      `build_archived`, `scan_guild` and `scan_backlog`.
    evidence: |-
      `main()` prints "retired" and returns 2, and `_generate` appears in the file only at its definition
      (scripts/fleet_scan.py:3568; verified 2026-09-30). So this story's `scan_dreams()` change, and the Archived-tab, Guild
      and Backlog effects the reviewers measured, are exercised only by tests. Those readers drift unobserved: for example
      `build_archived` links the six archive Dreams to `docs/dreams/<slug>.md`, which does not exist, and `scan_backlog`
      lists an archived `type: practice` Dream (modernist-identity) under practices as well as under Archived. The problem
      predates this story. Whether to delete the retired console generator and its readers, or rewire them, is not this
      story's decision.
    location: >-
      scripts/fleet_scan.py:3568
    severity: low
  - summary: >-
      Doctor's `chain-completeness --layers --json` stdout carries fleet_scan's `[fleet]` lines ahead of the JSON array, so
      the output cannot be parsed as JSON.
    evidence: |-
      `board._gather_chain_layers_audit` calls `gen.scan_fleet({}, None)`
      (src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py:1274). fleet_scan prints its `[fleet]` lines
      to stdout, and `sources/__main__.py` prints the JSON after them. On 2026-09-30 the review counted 40 such lines ahead of
      the payload. The problem predates this story, which adds one line (`[fleet] WARN chain 'pyforge-genesis' …`). The fix
      belongs at doctor's call site (capture or redirect stdout around the call), or in a change to fleet_scan's print
      stream that every other loader would see.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py:1274
    severity: medium
  - summary: >-
      Comments in doctor's board.py still say the loader imports `docs/dashboard/generate.py`, but the code loads
      `scripts/fleet_scan.py`.
    evidence: |-
      board.py:1129 and the comment block at :1499 name `docs/dashboard/generate.py`. The loaders (`_load_dashboard_generate`
      at :1524, and `_gather_chain_layers_audit`) load `<target>/scripts/fleet_scan.py`. The comments predate this story, and
      they sit in pyforge-doctor's package, under doctor's Spec surface, not this story's.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py:1499
    severity: low
  - summary: >-
      `scan_dreams()` does not strip an inline YAML comment from a Dream's frontmatter values, so a `status:` line with a
      trailing `# …` is read with the comment attached.
    evidence: |-
      scripts/fleet_scan.py:1087 takes `line.split(":", 1)[1].strip()`, whereas `_frontmatter_scalars` (:1628) strips
      comments. Six Dreams under docs/dreams/ carry an inline comment on their `status:` line (verified 2026-09-30; for
      example adaptive-model-tiering, bmad-cursor-interactive-routing and cursor-native-tier-map). Each of them then fails the
      `DREAM_STATUSES` check with a `[dreams] WARN`. The problem predates this story. Fixing it here would change rows read
      from `docs/dreams/`, which acceptance criterion 1 requires to stay identical. The function is also reached only from
      the uncalled `_generate()` (the second item).
    location: >-
      scripts/fleet_scan.py:1087
    severity: low
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

### 2026-09-30 — Review pass
- verdicts: 35 findings — high 0, medium 4, low 21, false 10, maybe-false 0
- review diff base: `origin/main`, not `baseline_revision`. A second `origin/main` merge (`14434a231e`, scribe 25.1) landed on the branch after the baseline, so a diff against `c8f74d5657` would have shown that merge's changes as this story's.
- entries (grouped by shared root cause; each member keeps its own row below):
  - P1 (low): BH-10, VG-6. The docstrings, comments and return annotation in the touched functions were stale.
  - P2 (medium): BH-5, EC-7. The live-tree chain comparison is not robust to a fold PR.
  - P3 (low): EC-6. `archive_only` was built in stem order, not path order.
  - G1, deferred as the first `deferred:` item (medium): BH-3, IA-3, IA-8, BH-2, EC-1, EC-8, VG-3. The per-chain Dream lookups still read only `docs/dreams/`.
  - The first-pass defers D2 to D5 are the remaining `deferred:` items: VG-1 is D2, VG-4 is D3, VG-5 is D4 and VG-7 is D5.
- findings:
  - `[low]` `[reject]` IA-1: the tests call only `scan_dreams()` and `_fleet_chains()`. No test runs `build_archived`, `scan_fleet`, `apply_owner`, `scan_guild`, `scan_backlog`, `gate_ownership` or `fleet-picture`. — Not worth fixing. `build_archived`, `scan_guild` and `scan_backlog` are reached only from `_generate()`, which has no caller. `fleet-picture` does not read `fleet_scan.py`. `scan_fleet` runs live through doctor's `chain-completeness --layers`, and the Verification Gap layer ran that green (15/15 for pyforge-herald). Tests for code with no live caller would be new work, not a direct correction.
  - `[false]` `[reject]` IA-2: the Archived tab grows from 119 to 125 entries, with six `retired` reasons and dead `docs/dreams/<slug>.md` links. — Refuted. `build_archived` is called only from `_generate()` (scripts/fleet_scan.py:3568), which has no caller, and `main()` prints "retired" and returns 2. No Archived tab is rendered from this code.
  - `[low]` `[defer]` IA-3: the six new chains' dream stage looks only at `docs/dreams/<slug>.md` and reads as unreached, and a Dream moved later would lose its own chain's dream stage and date. — G1, recorded as the first `deferred:` item. The intent's Problem names exactly two read sites, and §11 needs the per-chain lookups as their own Story before the first fold PR.
  - `[false]` `[reject]` IA-4: the Guild and Backlog views change (Herald's Dream count goes from 11 to 16, `constitutive` gains pyforge-genesis, and the practices list gains modernist-identity). — Refuted. `scan_guild` and `scan_backlog` are reached only from the uncalled `_generate()`.
  - `[false]` `[reject]` IA-5: the scan output gains two pyforge-genesis warnings and different summary counts, and Task 4's `fleet-picture` comparison is not in the diff. — Refuted. The `[dreams]` WARN and the `[dreams]`, `[archived]` and `[guild]` summaries come from the uncalled `_generate()` path. The live `[fleet] WARN chain 'pyforge-genesis': no spec directory and no station owner` is true: the chain has no Spec directory, and `owner: guild` names no station. The `fleet-picture` comparison was run, and it is recorded under Auto Run Result.
  - `[low]` `[reject]` IA-6: the criterion-1 and criterion-5 tests use the changed module with the archive disabled as "before", not `main`'s code, and they check the six additions as a subset. — Not worth fixing. The subset check is deliberate, so the test survives fold PRs. A direct comparison with `main` was run and is recorded under Auto Run Result: 174 rows became 180, with the first 174 byte-identical, and 183 chains became 189, with none changed. A golden copy of `main`'s rows would need test data that every Dream edit breaks.
  - `[false]` `[reject]` IA-7: doctor's loader resets `REPO_ROOT` and `DREAMS_DIR` but not `ARCHIVE_DREAMS_DIR`. — Refuted. `board.py` loads `<target>/scripts/fleet_scan.py`, and that copy derives `REPO_ROOT` from its own `__file__`. So `ARCHIVE_DREAMS_DIR` already resolves inside the target tree; the doctor fixture writes its own `pixi.toml` and `docs/dreams` there. The reviewer also notes that the two paths agree in today's callers.
  - `[low]` `[defer]` IA-8: `scan_specs()`, `_stage_globs()`, `_last_touched()`, `_GIT_SCOPES` and `build_archived()`'s link still read only `docs/dreams/`, which falls short of the Problem's "every reader". — G1, recorded as the first `deferred:` item.
  - `[false]` `[reject]` BH-1: the Archived tab shows six rows with broken links and a guessed `retired` reason. — Refuted on the same grounds as IA-2: `build_archived` has no live caller.
  - `[low]` `[defer]` BH-2: the six new fleet chains read `noDream: true`, carry a `dream` gap and fail chainAudit, because the dream-stage glob, `_last_touched` and `_GIT_SCOPES` look only in `docs/dreams/`. — G1, recorded as the first `deferred:` item. The rows are archived, so they stay out of the live flags and counts, and doctor's live chain-layers audit is unchanged.
  - `[medium]` `[defer]` BH-3: the left-open readers have no home. The memlog hands them to "the fold PRs to follow", but §11 says reader changes "land as Stories before the first fold PR moves a file", and the spec carried `deferred: []`. — G1, recorded as the first `deferred:` item (location `scripts/fleet_scan.py:1971`). No sibling Story covers these sites: doctor 36.1 and 36.2, herald 33.1 and steward 77.1 do not. The intent's Problem names exactly two read sites, so the per-chain lookups are outside this story and need their own Story before any fold PR.
  - `[false]` `[reject]` BH-4: `ARCHIVE_DREAMS_DIR` is fixed at import time, so repointing `REPO_ROOT` does not move it. — Refuted on the same grounds as IA-7.
  - `[medium]` `[patch]` BH-5: the live-tree test asserts `set(live_chains) <= set(chains)`, and that the new chains are exactly the archive stems. Both assertions fail on the first fold PR that moves a Dream that is some Spec's `owner-dream`, or that shares a slug with a Spec folder. — P2 applied in `tests/scripts/test_fleet_scan_archive.py`. The test now compares, in order, only the chains whose slug (`c[0]`) and `owner-dream` parent (`c[4]`) are not archive stems. It checks the chains named for archive stems as a sorted list, each reading `archived`.
  - `[low]` `[reject]` BH-6: the criterion-5 test cannot fail, and criterion 1's "before" is not the pre-change code. — Not worth fixing. The criterion-5 test fails if the archive branch raises or adds rows when the directory is missing, which is what criterion 5 guards. The "before" point is answered under IA-6.
  - `[low]` `[reject]` BH-7: a slug in both directories is hidden silently, and it needs a `[dreams] WARN`. — Not worth fixing. CHAIN-STANDARD §11 moves a Dream with `git mv`, so a copy left in both places is unlikely in everyday use. The fix adds a new branch and a new output line. The 2026-09-30 operator ruling already says which copy wins.
  - `[low]` `[reject]` BH-8: the status override discards a conflict between frontmatter and location instead of reporting it. — Not worth fixing. The 2026-09-30 operator ruling makes location the archive signal whatever the frontmatter says. A warning adds a branch, and it would fire by design on five of today's six archive Dreams.
  - `[false]` `[reject]` BH-9: rules meant for live Dreams fire on archived ones. pyforge-genesis adds a permanent `[dreams] WARN … owner 'guild' is reserved` and a `[fleet] WARN`, and it joins `scan_guild()`'s constitutive list. — Refuted. The guild-owner `[dreams]` WARN and the constitutive list are on the uncalled `_generate()` path. The live `[fleet] WARN` is true for this chain.
  - `[low]` `[patch]` BH-10: comments and docstrings in the touched code contradict the new rule. This covers `build_archived`'s block comment and docstring, `_fleet_chains()`'s docstring and its 4-tuple return type, and `scan_dreams()`'s row-shape docstring. — P1 applied in `scripts/fleet_scan.py`.
    - The `scan_dreams()` docstring now lists the row keys `slug, title, status, owner, type, chain`, plus `blockedOn` and `archived_reason`.
    - `_fleet_chains()` is annotated `list[tuple[str, str, str, str, str]]`, and its docstring documents `parent` and the archive path.
    - `build_archived`'s comment and docstring now say that a Dream read from `archive/docs/dreams/` also reads `archived`.
  - `[low]` `[reject]` BH-11: no test covers the console readers, and two cases are untested: `README.md` inside the archive directory, and an archive file with no frontmatter. — Not worth fixing. The console readers have no live caller (IA-2). The README skip is one shared line in `_dream_files()`, and the Verification Gap mutation run showed that removing it fails the suite. A file with no frontmatter follows the unchanged parse path.
  - `[low]` `[reject]` BH-12: the memlog's surface-reconcile entry leaves out the visible side effects, and it does not say where the operator ruling is recorded. — Not worth fixing. The entry names Story 75.1, and this spec's Spec Change Log and Auto Run Result carry the ruling's record (`spec-one-chain-per-station`'s memlog and `epics.md` Story 75.1) and the side effects. An appended memlog event is not rewritten.
  - `[low]` `[defer]` EC-1: an archive-only Dream becomes a fleet chain, but the dream-stage glob still reads only `docs/dreams/{slug}.md`, so six archived rows show `noDream`. — G1, recorded as the first `deferred:` item.
  - `[low]` `[reject]` EC-2: pyforge-genesis's chain has project `''`. So `_last_touched`'s `_bmad-output/projects` prefix matches every project, and `updated` reads 2026-09-30, not the file's date. — Not worth fixing. pyforge-genesis is the only chain with an empty project. Its row is archived, no live consumer reads its `updated`, and the fix adds a guard.
  - `[false]` `[reject]` EC-3: a Dream read from the archive gets the link `docs/dreams/<slug>.md` in `build_archived`. — Refuted on the same grounds as IA-2.
  - `[false]` `[reject]` EC-4: a caller that repoints `REPO_ROOT` and `DREAMS_DIR` after import reads the archive of the import-time root. — Refuted on the same grounds as IA-7.
  - `[low]` `[reject]` EC-5: when a fold copies a Dream instead of moving it, the same slug is in both directories and no signal is emitted. — Not worth fixing, for the same reasons as BH-7.
  - `[low]` `[patch]` EC-6: `archive_only` is sorted by stem, but `_dream_files()` sorts by path. The two orders diverge when one stem plus `-` is a prefix of another. — P3 applied in `tests/scripts/test_fleet_scan_archive.py`. `archive_only` is now built from `sorted(fs.ARCHIVE_DREAMS_DIR.glob("*.md"))`, in path order, which matches `_dream_files()`.
  - `[medium]` `[patch]` EC-7: the live-tree test fails when an archived Dream has its own Spec, or a child Spec whose `owner-dream` points at it. — Grouped with BH-5 (same defect). P2 applied: the chain comparison now skips chains whose slug or `owner-dream` parent is an archive stem.
  - `[low]` `[defer]` EC-8: the fleet rows for moved Dreams change on the first fold PR (`noDream` flips, a `dream` gap appears, chainAudit fails, and the Archived link dangles), although the intent says the surface's output stays the same across the move. — G1, recorded as the first `deferred:` item. The Archived-link part is on the uncalled path (IA-2).
  - `[low]` `[defer]` VG-1: the `scan_dreams()` half of the story changes a function nothing live calls. Its only caller, `_generate()`, has no caller, and `main()` returns 2. — The problem predates this story, so it is deferred as the second `deferred:` item (location `scripts/fleet_scan.py:3568`). The intent names `scan_dreams()` explicitly, and whether to retire or rewire the console generator is not this story's decision.
  - `[false]` `[reject]` VG-2: in the unused path, archive rows would render wrong. The `build_archived` link is dead, modernist-identity appears under both Archived and practices, and pyforge-genesis sits in constitutive. — Refuted as a live defect: the reviewer places it on the uncalled `_generate()` path, and nothing renders it. The drift is recorded in the second `deferred:` item's evidence.
  - `[low]` `[defer]` VG-3: archive chains are marked as having no Dream. — G1, recorded as the first `deferred:` item.
  - `[medium]` `[defer]` VG-4: `python -m pyforge.doctor.sources chain-completeness --layers --json` stdout cannot be parsed as JSON, because fleet_scan's `[fleet]` lines reach stdout ahead of the payload; this diff adds one more line. — The problem predates this story (40 lines were already there), so it is deferred as the third `deferred:` item (location `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py:1274`). The fix belongs at doctor's call site, or in fleet_scan's print stream, which every loader sees.
  - `[low]` `[defer]` VG-5: stale comments in `board.py` say the loader imports `docs/dashboard/generate.py`, but the code loads `scripts/fleet_scan.py`. — The comments predate this story and sit in doctor's package, so they are deferred as the fourth `deferred:` item (location `board.py:1499`).
  - `[low]` `[patch]` VG-6: `_fleet_chains` is annotated `list[tuple[str, str, str, str]]`, but it returns 5-tuples. — Grouped with BH-10 (same defect: the touched function's stale contract). P1 applied: the annotation now names five `str`.
  - `[low]` `[defer]` VG-7: `scan_dreams` does not strip an inline YAML comment from `status:`, for example in adaptive-model-tiering. — The problem predates this story, so it is deferred as the fifth `deferred:` item (location `scripts/fleet_scan.py:1087`). Fixing it here would change rows read from `docs/dreams/`, which criterion 1 requires to stay identical.
- verification after the patch: the new test passed (7 passed, exit 0); `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` passed (8939 passed, 1 skipped, exit 0); `pixi run -e pyforge-guild spec-surface-check` exited 0; `python scripts/spec_surface_reconcile.py` exited 0.

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
