---
title: "36.2: The sibling-drift check reads acknowledged Dreams under the archive"
type: 'chore'
created: '2026-09-29'
status: 'done'
baseline_revision: 'a04d17d946b148d986d8c159b2fadb973a472ab1'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py
deferred:
  - summary: >-
      `ruff format --check` is red for `pyforge-scribe`, so `lint-types` (the first leg of `pr-preflight`) is red on this branch, but the red is on `origin/main` and not in this diff.
    evidence: |-
      `src/shared/packages/pyforge-scribe/src/pyforge/scribe/catalog.py` is byte-identical to `origin/main`. `ruff format --diff` with the scribe package config wants `except OSError, subprocess.TimeoutExpired:` (PEP 758, py314) in place of the parenthesised tuple at line 387. Landed by scribe Story 25.1 (2026-09-30). The file sits in the surfaces of `spec-pyforge-scribe`, `spec-pyforge-core` and `spec-pyforge-unifying-strategy`, so a fix from this doctor story would need a memlog entry and a scoped stamp on three other stations' Specs and would collide with parallel dispatches; the owning station's next story should take the one-token fix. A `dispatch/*` branch skips `pr-preflight` (journaled), so this story's landing is not blocked by it.
    location: >-
      src/shared/packages/pyforge-scribe/src/pyforge/scribe/catalog.py:387
    severity: medium
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
