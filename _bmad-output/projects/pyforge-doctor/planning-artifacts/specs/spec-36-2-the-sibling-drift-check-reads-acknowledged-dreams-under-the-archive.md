---
title: "36.2: The sibling-drift check reads acknowledged Dreams under the archive"
type: 'chore'
created: '2026-09-29'
status: 'done'
baseline_revision: 'a04d17d946b148d986d8c159b2fadb973a472ab1'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the sibling-drift check (spec-pyforge-doctor CAP-71, extended by CAP-82) diffs the Dreams this repo shares
with `openteams-ai/mgmt-wf-python-modernization`, and honours a local `sibling-acknowledged:` hash. It builds its local side
in `sources/sibling_dreams.py::_local_fingerprints`, which reads only `docs/dreams/*.md`. Seven local Dreams carry an
acknowledgement: `pyforge-doctor` (live) and six archived ones (`package-inventory-eligibility`, `pixi-container-image`,
`django-accelerator-framework`, `enterprise-data-models-and-apis`, `miniforge-installer`, `reusable-cicd-workflows`).
`spec-one-chain-per-station` CAP-11 moves archived Dreams to `archive/docs/dreams/`. After that move, the check would stop
seeing those six, and their acknowledgements would stop suppressing the drift they were written for.

**Approach:** `_local_fingerprints` also reads `archive/docs/dreams/*.md`. When a slug exists in both places, the
`docs/dreams/` copy wins. Nothing else changes: the fingerprint, the acknowledgement rule and the messages stay as they are.
CHAIN-STANDARD §11 requires this before the first fold PR moves a file.

Ledger key: `36-2-the-sibling-drift-check-reads-acknowledged-dreams-under-the-archive`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- `spec-one-chain-per-station` CAP-11 (the Guild's; the Epic 34 relay shape, so no doctor CAP or FR); CHAIN-STANDARD §11.
- `spec-pyforge-doctor` CAP-71 and CAP-82 (the check being extended).
- `spec-feature-flag-governance` Q1: a `chore` needs no flag. This story keeps an existing check's output the same across a
  planned file move.

## Acceptance Criteria

- Given an acknowledged Dream fixture in `docs/dreams/` When the check runs Then it reports what it reports today (no change)
- Given the same Dream moved to `archive/docs/dreams/` When the check runs Then it reads the acknowledgement there and reports the same result as before the move
- Given one slug in both `docs/dreams/` and `archive/docs/dreams/` with different acknowledgement hashes When the check runs Then it uses the `docs/dreams/` copy
- Given no `archive/docs/dreams/` directory When the check runs Then it behaves as today
- Given today's `main` When the check runs Then its findings are unchanged
- Given the archive read is removed When the moved-Dream test runs Then it fails (mutation)

## Tasks

1. Read `sources/sibling_dreams.py` end to end and `tests/unit/test_sources_sibling_dreams.py`.
2. Extend `_local_fingerprints` to read `archive/docs/dreams/*.md` after `docs/dreams/*.md`, keeping the first copy of each
   slug. Keep its `OSError` handling.
3. Add tests for every acceptance criterion, on `tmp_path` fixtures (no network; the sibling side stubbed the way the
   existing tests stub it).
4. Run `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` and read the exit code.
5. Reconcile every Spec `spec-surface-check` names (`spec-pyforge-doctor`, and `spec-pyforge-core` as co-governor): memlog
   first, `git add`, then a scoped `--write-baseline --spec` for each.

## Boundaries & Constraints

**Always:**
- Keep the fingerprint and acknowledgement rules byte-for-byte.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not move any Dream in this story.
- Do not change the sibling repository coordinates or the fail-open paths (unreachable, unauthenticated).
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dream in `docs/dreams/` | acknowledged | as today | — |
| Dream moved to the archive | acknowledged | same result as before the move | — |
| slug in both places | different hashes | `docs/dreams/` copy used | — |
| no archive directory | — | as today | — |
| unreadable file | `OSError` | skipped, as today | fail-open |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py:154` -- `_local_fingerprints(target)`, the only edit site. Today: one `docs/dreams` dir, `is_dir()` guard returns `{}`, `glob` `OSError` returns `{}`, per-file `read_text` `OSError` is skipped, `out[path.stem] = fp`.
- `sibling_dreams.py:69` -- `_gather` does `if not local: return ()` right after; an archive-only tree must still count as non-empty.
- `sibling_dreams.py:246` -- `_diff_shared_slugs` reads `sibling_acknowledged` off the local fingerprint; unchanged (fingerprint and ack rule stay byte-for-byte).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py` -- helpers `_write_local_dream`, `_write_local_dream_with_ack`, `_fingerprint`; sibling side stubbed by `monkeypatch.setattr(sibling_dreams, "_fetch_sibling_fingerprints", ...)`. New tests append at the end, same helpers.
- Read-only evidence (measured 2026-09-30): `archive/docs/dreams/` holds six Dreams (`deckcraft`, `design-code-bridge`, `herald-pitch-deck-family-expansion`, `modernist-identity`, `pyforge-genesis`, `video-scripts`), none with a filename in the sibling's `docs/dreams` (17 files). Live `gather` on this tree before the change: `[]`. So AC 5 holds by construction and is re-measured after.
- Governors (baseline): `spec-pyforge-doctor` (tests file) and `spec-pyforge-core` (`sibling_dreams.py`); `spec-surface-check` names the final list.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py` -- loop `_local_fingerprints` over `docs/dreams` then `archive/docs/dreams`; skip a missing dir, skip a dir whose `glob` raises `OSError`, keep `out.setdefault`-style first-wins per slug; update the module docstring's "``docs/dreams/``" line -- CHAIN-STANDARD §11 reader rule.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py` -- add one test per contract AC plus the two I/O-matrix edges (archive-only tree, `OSError` in one dir/file) -- every AC needs an executable oracle.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` and `spec-pyforge-core/.memlog.md` -- memlog `event` naming each governed path changed, then `git add`, then scoped `--write-baseline --spec` (never bare).

**Acceptance Criteria:** the six in the intent contract above, verbatim; each maps to a named test, and the mutation AC is run by hand (archive read removed, moved-Dream test red) and logged in the Auto Run Result.

## Binding

Parent capability: `spec-one-chain-per-station` CAP-11 (Guild relay; no doctor CAP or FR).
Dream: `docs/dreams/one-chain-per-station.md` → § *2026-09-29 — One archive home*.
Ledger key: `36-2-the-sibling-drift-check-reads-acknowledged-dreams-under-the-archive`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none. This is a `chore` (`spec-feature-flag-governance` Q1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

### 2026-09-30 — Review pass
- verdicts: 25 findings — high 0, medium 9, low 7, false 9, maybe-false 0
- findings:
  - `[medium]` `[patch]` Blind 1: a live `docs/dreams/` listing `OSError` now continues to the archive (before it returned `{}`), and no test exercised it — measured: the `continue` -> `break` mutant passed all 41 tests, and the change would drop the six archived acknowledgements this story protects. Fixed: the unlistable-directory test is parametrized over which home raises, asserts the raising `glob` was hit, and asserts the other home's slug survives; the `break` mutant now fails `[live-raises]`.
  - `[false]` `[reject]` Blind 2: the story's purpose is never demonstrated on the six real Dreams — refuted: the intent forbids moving any Dream in this story; AC 2 is the unit-level demonstration (same acknowledged Dream in either home, identical result, in both the silent and the re-fire leg), and AC 5 was measured live (`[]` before, `[]` after, sibling reachable, 146 local slugs incl. the six archived).
  - `[false]` `[reject]` Blind 3: only one mutant run — refuted by measurement: `setdefault` -> plain assignment fails 1 test (3 after the patch), directories swapped fails 1 (3 after), archive read removed fails 7 after the patch; the one survivor, the `break` handler, is Blind 1.
  - `[low]` `[patch]` Blind 4: the unlistable-archive test passes even if the archive is never listed and never records that `glob` was hit. Fixed with the same parametrized rewrite: a hit counter asserts the raising directory was listed exactly once.
  - `[low]` `[patch]` Blind 5: `assert not (tmp_path / "archive").exists()` cannot fail because nothing writes under `archive/`, and the `[live]` case compares with nothing. Fixed: the two vacuous asserts are deleted and the test asserts the single finding's `check`; the no-archive behaviour stays pinned by the existing pre-change tests.
  - `[medium]` `[patch]` Blind 6 (two parts): (a) an `archive/docs/dreams` that is a file or broken symlink is untested — refuted for that half: `is_dir()` is false and it takes the same `continue` as the missing-directory case that `test_no_archive_directory_behaves_as_before` pins; (b) a live copy that does not parse beside a valid archive copy — real, grouped with Edge 2. Fixed with the `seen` set and two tests (malformed and unreadable live copy).
  - `[low]` `[patch]` Blind 7: stale adjacent text — the `SIBLING_DREAMS_DRIFT` registration comment in `sources/__init__.py` says "both local docs/dreams and the sibling", and the module docstring's story list lacks 36.2. Fixed both. The Code Map's pre-edit line numbers and a dated note on `docs/dreams/pyforge-doctor.md` are not acted on: the first would edit this build's spec, the second belongs to a doctor CAP this Guild relay does not mint.
  - `[medium]` `[defer]` Blind 8: `ruff-format` is red for `pyforge-scribe` (`catalog.py:387`) and `pr-preflight` was not run — verified: the file is byte-identical to `origin/main` and `ruff format --diff` wants `except OSError, subprocess.TimeoutExpired:`; pre-existing, in three other stations' Spec surfaces. Recorded in frontmatter `deferred`. The `pr-preflight` omission is not acted on: the spec's Verification lists the commands run here and a `dispatch/*` branch skips the hook (journaled).
  - `[false]` `[reject]` Blind 9: the third Spec (`spec-pyforge-unifying-strategy`) was stamped outside scope — refuted: Task 5 says "every Spec `spec-surface-check` names" and the detector named it after core's stamp; of the 29 paths its stamp moved, 0 are missing from its own memlog (checked by script against `git show` of the pre-change baseline), and `spec_surface_reconcile.py` exits 0.
  - `[false]` `[reject]` Blind 10: the baseline mixes other stories' accepted drift with no breakdown — refuted: per Spec 21 / 18 / 29 paths moved (2 + 1 + 4 of them new), every one named in its own Spec's memlog; the Auto Run Result's Residual already attributes the carry.
  - `[low]` `[reject]` Blind 11: the doctor and core memlog entries repeat the change in different words — memlogs are append-only and each Spec names only its own governed paths by design; the fix would rewrite logged lines, and no caller reads one against the other.
  - `[low]` `[reject]` Edge 1: a non-UTF-8 archived file raises `UnicodeDecodeError`, which the `OSError` handler misses, so `degrade_on_exception` turns the whole gather into one WARN — real but the handler shape is unchanged from before this story (the live files had the same exposure), the outcome is a loud WARN not silence, and the fix adds a guard beyond "keep its `OSError` handling".
  - `[medium]` `[patch]` Edge 2: a live copy that is unreadable or unparseable let the archive copy stand in (`setdefault` ran only after a successful parse), so a stale archive acknowledgement substituted for the live Dream — reproduced. Fixed: `_local_fingerprints` keeps a `seen` set of stems added by listing order before read and parse; the first home to list a slug owns it. Tests: malformed live copy, unreadable live copy. The `seen`-less mutant fails both.
  - `[medium]` `[patch]` Edge 3: no test raised `OSError` from the live directory's listing — same root as Blind 1, same fix.
  - `[medium]` `[patch]` Edge 4 (claim): AC 3's "docs/dreams/ copy wins" held only when that copy parsed — same root as Edge 2, same fix; the live-wins test still passes both legs.
  - `[low]` `[patch]` Edge 5: the registry comment in `sources/__init__.py:381` names one local Dream home — same as Blind 7, fixed.
  - `[medium]` `[patch]` Verification gap: the `OSError`-on-listing test covers only the archive directory, so `continue` -> `break` survives (41 passed, reproduced by the layer and by me) — same root as Blind 1, same fix.
  - `[medium]` `[patch]` Verification gap, other 1: a malformed or unreadable live copy falls through to the archive copy — same root as Edge 2, same fix.
  - `[low]` `[patch]` Verification gap, other 2: the archive-exists asserts in the no-archive test are vacuous — same as Blind 5, fixed.
  - `[false]` `[reject]` Intent (a): the tests exercise `gather` and `_local_fingerprints`, not the `doctor check --sibling-dreams` CLI entry, and read no real Dream file — refuted: `gather` is the check's public entry (the CLI only forwards to it and the diff does not touch the forwarding); a real-file, real-network test is excluded by the spec's "no network" task.
  - `[false]` `[reject]` Intent (b): no acknowledged Dream sits in the archive today, so the archive read contributes nothing to real findings — refuted as a defect: that is the stated state (the intent says "after that move" and "do not move any Dream in this story"; the Code Map records it); the read must exist before the first fold PR moves a file.
  - `[false]` `[reject]` Intent (c): AC 5 and AC 6 are recorded in prose, not encoded — refuted: AC 6 is a mutation run by hand by definition and its oracle is the suite failing when the read is removed (7 failures, re-measured); AC 5 is a live measurement of `main` and cannot be a no-network unit test.
  - `[medium]` `[patch]` Intent (d): no test covers a live copy that is unreadable or unparseable beside an archive copy, and the code and the spec's wording admit two grains — same root as Edge 2; Task 2's "keeping the first copy of each slug" and the Approach's "the `docs/dreams/` copy wins when a slug exists in both places" settle it on the file-presence grain, which the `seen` set implements.
  - `[false]` `[reject]` Intent (e): the whole archive directory now joins the local side, so an archived Dream sharing a filename with the sibling is compared, and an archive-only tree now reaches the fetch path — refuted as a defect: both follow from the Approach ("also reads `archive/docs/dreams/*.md`") and from "same result as before the move" (a moved Dream must keep being compared); the real tree always has `docs/dreams/`, and the archive-only path is pinned by `test_archive_only_tree_still_reports`.
  - `[false]` `[reject]` Intent (f): the footprint goes beyond the two named Specs (a third memlog and stamp, 135 baseline lines) — same as Blind 9 and Blind 10, refuted the same way.

### 2026-09-30 — Review pass (follow-up on a `done` spec)
- verdicts: 19 findings — high 0, medium 1, low 8, false 10, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind 1: AC 5 ("today's `main` findings unchanged") has no test or recorded evidence, and the six archived files might add drift WARNs — carried from Intent (c) and Blind 2: the Auto Run Result records the live run (`[]` before, `[]` after, real sibling, 146 local slugs incl. the six archive-only Dreams, none sharing a filename with the sibling's 17); re-checked this pass that `archive/docs/dreams/` holds exactly those six files.
  - `[low]` `[reject]` Blind 2: the `except OSError` around `dreams_dir.glob(...)` is dead on py3.14 and the unlistable-directory test patches `glob` to raise — verified: a `chmod 000` directory gives `is_dir() True` and `glob` returns `[]`, no raise, so the handler is defensive only. Not worth acting on: the guard is pre-existing, Task 2 says "Keep its `OSError` handling", the parametrized test pins the `continue` (a `break` there fails it), and no user meets a defect from an unreachable guard.
  - `[low]` `[reject]` Blind 3: the second doctor memlog entry quotes 'first PARSED copy wins', wording the first entry never used — verified: the first entry says "first copy of a slug wins"; the quote paraphrases the pre-patch behaviour and the same entry states the change (a `seen` set) explicitly, so no reader is misled about what was ratified. Memlogs are append-only (Blind 11); a fix would rewrite a logged line.
  - `[false]` `[reject]` Blind 4: the `spec-pyforge-doctor` stamp accepted a `docs/MAP.md` hash change that no recent doctor memlog entry names — refuted: `docs/MAP.md` is not in this diff (carry from scribe Epic 24 in the baseline), the doctor memlog names it (Story 21.1, line 574), and `python scripts/spec_surface_reconcile.py` exits 0 with "no drift", the guard's own verdict; same class as Blind 10.
  - `[false]` `[reject]` Blind 5: the diff re-stamps `spec-pyforge-unifying-strategy`, which this story does not touch — carried from Blind 9: Task 5 says "every Spec `spec-surface-check` names", the detector named it after core's stamp, and every path it moved is named in its own memlog.
  - `[low]` `[reject]` Blind 6: a slug in both homes, or an unparseable live copy, resolves silently — the intent excludes the fix: "Nothing else changes: the fingerprint, the acknowledgement rule and the messages stay as they are", and an advisory finding is new output on a warn-only check. No named caller diverges.
  - `[low]` `[reject]` Blind 7: findings do not record which home the local Dream came from — same exclusion as Blind 6 (messages and evidence stay as they are); an additive `local_home` key is new schema surface for no demonstrated failure.
  - `[medium]` `[defer]` Blind 8: the story defers a red `lint-types` (`ruff format` on scribe `catalog.py:387`) instead of fixing it — carried from Blind 8 of the first pass: still on `origin/main`, still in three other stations' Spec surfaces (memlog plus scoped stamps, parallel-dispatch collision); already in frontmatter `deferred`, not added again; `python scripts/lint_types.py ruff-format` this pass is red for `catalog.py:387` only and `pyforge-doctor` is `ok`.
  - `[false]` `[reject]` Blind 9: `test_no_archive_directory_behaves_as_before` asserts only a count and a check name, so AC 4 is not pinned — refuted: the 190 added lines delete nothing, so every pre-change test still runs on a tree with no `archive/` and asserts the full message and evidence (`test_shared_filenames_report_live_divergence_shape`, `test_sibling_acknowledged_hash_mismatch_refires_naming_both_hashes`, `test_owner_axis_drift_emits_warn`); a message or evidence regression in the no-archive path fails those.
  - `[low]` `[patch]` Blind 10: the `SIBLING_DREAMS_DRIFT` registration comment in `sources/__init__.py` still says "Diffs shared Dream titles" although the check compares status, owner, content-hash and title — verified against `_COMPARED_AXES` and the module docstring; the diff already edits the adjacent line. Fixed: the comment names the four axes; doctor memlog event names the path; `spec_surface_reconcile.py` exits 0.
  - `[low]` `[reject]` Blind 11: thin coverage for an archive that is a file or broken symlink, a non-Dream `.md` in the archive, an archive-only slug absent from the sibling, and `gather` with a broken live copy — the file or broken-symlink half was refuted in Blind 6a (`is_dir()` false takes the `continue` the missing-directory test pins); the rest run through the parse and `is_dir()` paths the live home already exercises (`test_local_fingerprints_skip_unusable_files`, `test_one_sided_slugs_emit_nothing`, `test_archive_dreams_are_merged_with_live_ones`), the archive holds no README today, and no failure was shown.
  - `[low]` `[reject]` Edge 1: a non-UTF-8 file raises `UnicodeDecodeError`, missed by the `OSError` handler, so `degrade_on_exception` turns the gather into one WARN — carried from Edge 1 of the first pass (the handler shape is unchanged from before this story, the outcome is a loud WARN, the fix adds a guard beyond "keep its `OSError` handling").
  - `[false]` `[reject]` Edge 2 (claim): the code uses a `seen` set, not `setdefault`-style first-wins, so a broken live copy silences that slug and any archive acknowledgement — refuted: the intent contract says "keeping the first copy of each slug" and "the `docs/dreams/` copy wins", and its matrix row is "unreadable file: skipped, as today, fail-open". A live file that fails to parse gave no fingerprint before this story; the `seen` set keeps that result for every slug that has a live file, and a stale archive hash cannot stand in for a broken live Dream. The Code Map's "`setdefault`-style" is spec prose outside the contract.
  - `[low]` `[reject]` Verification gap (other): a non-UTF-8 archived Dream raises `UnicodeDecodeError` past the `OSError` handler — same as Edge 1 (carried, `low`). The layer reported no verification gap: five of six mutants were killed; the `glob` to `rglob` mutant survives and the layer marked it not a realistic regression on a flat directory.
  - `[false]` `[reject]` Intent (1): AC 5 is not exercised by any test and the intent places it at the real tree — carried from Intent (c): a live measurement cannot be a no-network unit test; recorded in the Auto Run Result.
  - `[false]` `[reject]` Intent (2): the diff picks first-listed-wins where the intent does not choose between that and first-parsed-wins — same as Edge 2: the intent's text, its matrix and the "as today" rule settle it on file presence; that reading changes no result for a slug that has a live file.
  - `[false]` `[reject]` Intent (3): the intent's premise (seven acknowledged Dreams, `pyforge-doctor` live) does not match the tree — verified: six `docs/dreams/*.md` files carry a frontmatter `sibling-acknowledged:` line and `pyforge-doctor.md` mentions it only in prose; no code or test relies on the count and the check reads the line from whichever Dream has it, so no bad outcome occurs at any diff location, and the intent contract is not this build's to edit.
  - `[false]` `[reject]` Intent (4): the governance footprint is larger than Task 5's two Specs — carried from Blind 9, Blind 10 and Intent (f).
  - `[false]` `[reject]` Intent (5): a comment-only edit to `sources/__init__.py` sits outside the stated tasks — refuted: it is comment-only with no behaviour change, adjacent to the check being extended, and covered by the "broken window in what you touch" rule; it is the same edit Blind 7 of the first pass triaged as a patch.

### 2026-09-30 — Operator landing (the deferral is resolved)
- The landing was refused twice (MRS-DISP-038): the branch's appends to `spec-pyforge-doctor`, `spec-pyforge-core` and `spec-pyforge-unifying-strategy`'s `.memlog.md` conflicted with steward Story 76.2's. `origin/main` was merged in and the three memlogs resolved as an ordered union (main first, then this story; every entry from both sides kept, no duplicates).
- The frontmatter deferral (Blind 8 of both passes: `ruff format` red for `pyforge-scribe` at `catalog.py:387`) is **resolved** and removed from `deferred:`: PR #1690 (`d923bdfd1b`) reformatted that line on `main`, and the merge brings it here; `ruff format --check` on the file exits 0 on this branch. No deferred-work ledger twin is needed.
- Re-verified after the merge: `pyforge-doctor-test` exit 0 (3077 passed, 1 skipped).

## Auto Run Result

Status: done

**Summary.** `_local_fingerprints` reads `docs/dreams/*.md` and then `archive/docs/dreams/*.md` (`_LOCAL_DREAM_DIRS`, live first). The first home to list a slug owns it (a `seen` set of stems, added before read and parse), so the `docs/dreams/` copy wins a tie, and a live copy that is unreadable or fails to parse leaves the slug absent instead of letting an archive copy stand in. A missing directory, a directory whose `glob` raises `OSError` (in either home) and an unreadable file are each skipped. The fingerprint, the acknowledgement rule, the messages, the sibling coordinates and the fail-open paths are untouched. `_gather`'s `if not local` guard needed no change: an archive-only tree is non-empty.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py` -- archive read with first-lister-owns-the-slug precedence; docstrings name the CHAIN-STANDARD section 11 reader rule and Story 36.2.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- comment only: the `SIBLING_DREAMS_DRIFT` registration names both local Dream homes.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py` -- 12 new test cases (44 in the file, 41 before the review patches).
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md` -- surface-reconcile events (implementation and review patches); `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md` -- co-governor carry (see Residual).
- `scripts/.spec-surface-baseline.json` -- scoped stamps for the three Specs, none bare; the last re-stamp (doctor, core) moved exactly the four entries the review patches touched.

**AC to test map.**
- AC 1, AC 2 (silent): `test_acknowledged_dream_is_silent_in_either_home[live|archive]`
- AC 2 (re-fire): `test_stale_acknowledgement_refires_identically_before_and_after_the_move`
- AC 3: `test_live_copy_wins_when_a_slug_is_in_both_homes` (both directions), plus `test_malformed_live_copy_is_not_replaced_by_the_archive_copy` and `test_unreadable_live_copy_is_not_replaced_by_the_archive_copy`
- AC 4: `test_no_archive_directory_behaves_as_before`
- AC 5: live measurement below
- AC 6: mutation run below
- Matrix edges: `test_archive_only_tree_still_reports`, `test_archive_dreams_are_merged_with_live_ones`, `test_unlistable_dir_is_skipped_and_the_other_home_survives[live-raises|archive-raises]`, `test_unreadable_file_is_skipped_in_the_archive`

**Mutation (run by hand on the final code, file restored byte-identical each time).** Unmutated: 44 passed. Archive read removed (AC 6): 7 failed. Plain assignment without the `seen` check: 3 failed. Directories swapped: 3 failed. `seen` check dropped with `setdefault` after the parse: 2 failed. Glob-`OSError` handler `continue` -> `break`: 1 failed (`[live-raises]`); before the review patches this mutant passed all 41 tests.

**AC 5 (live, real sibling, GH token from `gh auth token`, read-only GETs).** `gather` on this tree returns `[]` before the change and `[]` after the final code (findings byte-identical); the worktree env reads 146 local slugs, including the six archive-only Dreams (`deckcraft`, `design-code-bridge`, `herald-pitch-deck-family-expansion`, `modernist-identity`, `pyforge-genesis`, `video-scripts`), none of which shares a filename with the sibling's 17.

**Review (one pass, four layers, 25 findings: high 0, medium 9, low 7, false 9).**
- Patches applied, 5 entries: (1) live-directory listing `OSError` coverage (medium; Blind 1, Edge 3, Verification gap) -- test parametrized over both homes with a hit counter; (2) a broken live copy yielding to the archive copy (medium; Blind 6b, Edge 2, Edge 4, Verification gap other 1, Intent d) -- `seen` set plus two tests; (3) the unlistable-archive test not proving the listing (low; Blind 4); (4) vacuous `archive/` exists asserts (low; Blind 5, Verification gap other 2); (5) stale registry comment and story list (low; Blind 7 first part, Edge 5). Patched counts by entry verdict: high 0, medium 2, low 3.
- Deferred, 1: `ruff-format` red for `pyforge-scribe` at `catalog.py:387` (medium, pre-existing on `origin/main`; frontmatter `deferred`, `location` is that path).
- Rejected, with reasons in the Review Triage Log: Blind 2, 3, 9, 10 and Intent a, b, c, e, f as `false` (each refuted by measurement or by the intent's own text); Blind 11 (append-only memlogs) and Edge 1 (non-UTF-8 archived file: same handler shape as before, loud WARN, fix adds a guard) as `low`; the pre-edit Code Map line numbers, the `docs/dreams/pyforge-doctor.md` note and the `pr-preflight` omission in Blind 7 and Blind 8 are not acted on, with reasons in their rows.

**Follow-up review recommendation: `true`.** Two `medium` entries were patched on a first pass. The unverified risk: the `seen`-set ownership rule in `_local_fingerprints` (a broken live copy suppresses the archive copy, the file-presence reading of "first copy of each slug") and its three new tests landed after the review layers ran, so no independent reviewer has read them. The five mutants above kill it, but a reviewer should confirm that file-presence precedence is the grain the operator wants for a slug that is broken live and acknowledged in the archive.

**Verification (exit codes read directly, none through a pipe).**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- exit 0, 3076 passed, 1 skipped.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test-coverage` -- exit 0 (`sibling_dreams.py` 99%, floor 80%; total 92%).
- `python scripts/lint_types.py ruff` -- exit 0; `python scripts/lint_types.py mypy` -- exit 0; `python scripts/lint_types.py ruff-format` -- exit 1, for `pyforge-scribe` `catalog.py:387` only (`pyforge-doctor` is `ok`; deferred above).
- `pixi run -e pyforge-guild spec-surface-check` -- exit 0, no findings, after the scoped stamps.
- `python scripts/spec_surface_reconcile.py` -- exit 0 ("every tracked file governed or allowlisted; no drift").
- Matrix audit: each of the five I/O-matrix rows has a covering test that ran and passed in the verbose run (41 of 41 at the time; 44 of 44 now).
- Not run: the full `pr-preflight` (it would red on the deferred scribe lane, and a `dispatch/*` branch skips it, journaled); nothing was pushed and no PR was opened.

**Residual.** Stamping `spec-pyforge-core` re-baselined files that only its memlog had been clearing; that surfaced two `drift-presumed` WARNs for `spec-pyforge-unifying-strategy` (`cutover_root.py`, `test_cutover_root.py`, both changed under steward Story 76.1 and already reconciled in core's memlog). They were cleared with a memlog event on that Spec and a scoped stamp; I verified by script against the pre-change baseline that every one of the 29 paths that stamp moved is named in that Spec's own memlog. The stamps also carry baselines for other memlog-reconciled files of the three Specs. The Code Map above keeps the pre-edit line numbers of `sibling_dreams.py`.

### Follow-up review pass (2026-09-30)

The first pass recommended one follow-up on a named risk: the `seen`-set ownership rule and its three late tests had no independent reader. This pass ran four fresh layers (Blind Hunter, Edge Case Hunter, Verification Gap Reviewer, Intent Alignment Auditor) on the diff since `baseline_revision`.

**Summary.** 19 findings: high 0, medium 1, low 8, false 10, maybe-false 0. One entry patched (`low`), one carried deferral (`medium`, already in frontmatter `deferred`, not added again), 17 rejected with reasons in the Review Triage Log. The named risk is settled: no layer found a defect in the file-presence grain. The intent contract ("keeping the first copy of each slug", "the `docs/dreams/` copy wins", matrix row "unreadable file: skipped, as today, fail-open") supports it, and it leaves every slug that has a live file with the result it had before this story. The Verification Gap Reviewer ran its own mutants (archive and live swapped, duplicate-slug skip removed, `continue` to `return`, `continue` to `break`, `seen.add` after the parse) and each failed at least one test.

**Files changed this pass:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- comment only: the `SIBLING_DREAMS_DRIFT` registration comment names the compared axes (status, owner, content-hash, title) instead of "titles".
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` -- surface-reconcile event naming `sources/__init__.py`, the only governed path this pass changed; the S-13.7 guard names no co-governor for it.

**Patches applied, 1 (by entry verdict: high 0, medium 0, low 1):** the stale registry comment (Blind 10). **Deferred, 0 new:** the scribe `ruff-format` row is carried and already in `deferred:` with `location` `src/shared/packages/pyforge-scribe/src/pyforge/scribe/catalog.py:387`. **Rejected, 17:** each row in the log; `low` rejections are Blind 2, 3, 6, 7, 11, Edge 1 and the Verification-gap "other"; the ten `false` rows are refuted by measurement, by the intent's own text, or carried from the first pass.

**Follow-up review recommendation: `false`.** No `high` was patched, and this was the single allowed follow-up.

**Verification (exit codes read directly, none through a pipe).**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- exit 0, 3076 passed, 1 skipped.
- `python scripts/lint_types.py ruff` -- exit 0; `python scripts/lint_types.py ruff-format` -- exit 1 for `pyforge-scribe` `catalog.py:387` only (`pyforge-doctor` is `ok`; deferred above).
- `pixi run --frozen -e pyforge-guild spec-surface-check` -- exit 0.
- `python scripts/spec_surface_reconcile.py` -- exit 1 with `[drift] pyforge-doctor/spec-pyforge-doctor: .../sources/__init__.py changed but the spec's memlog did not move` right after the comment edit; exit 0 ("every tracked file governed or allowlisted; no drift") after the memlog event.
- Not run: `pr-preflight` (a `dispatch/*` branch skips it, journaled, and it reds on the deferred scribe lane); nothing pushed, no PR opened.

**Residual.** `--write-baseline` was not passed, per this run's rule, so the stamped baseline hash for `sources/__init__.py` under `spec-pyforge-doctor` predates the comment edit; the memlog event reconciles it and a human-invoked scoped stamp (`--spec pyforge-doctor/spec-pyforge-doctor`, after `git add`, from a clean tree) refreshes it. Intent premise, not code: the contract says `pyforge-doctor` carries a `sibling-acknowledged:` line, but `docs/dreams/pyforge-doctor.md` mentions it only in prose; the six named archived Dreams carry it.
