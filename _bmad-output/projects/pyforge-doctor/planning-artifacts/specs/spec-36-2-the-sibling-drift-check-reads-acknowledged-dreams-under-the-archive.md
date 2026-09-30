---
title: "36.2: The sibling-drift check reads acknowledged Dreams under the archive"
type: 'chore'
created: '2026-09-29'
status: 'in-review'
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

- No independent review has run yet (implementation and review stay separate).

## Auto Run Result

Status: in-review

**Summary.** `_local_fingerprints` now reads `docs/dreams/*.md` and then `archive/docs/dreams/*.md` (`_LOCAL_DREAM_DIRS`, live first). Each slug keeps its first parsed fingerprint (`out.setdefault`), so the `docs/dreams/` copy wins a tie. A missing directory, a directory whose `glob` raises `OSError` and an unreadable file are each skipped. The fingerprint, the acknowledgement rule, the messages, the sibling coordinates and the fail-open paths are untouched. `_gather`'s `if not local` guard needed no change: an archive-only tree is non-empty.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py` -- archive read, module docstring (CHAIN-STANDARD section 11 reader rule).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py` -- eight new tests (nine cases) appended.
- `spec-pyforge-doctor/.memlog.md`, `spec-pyforge-core/.memlog.md` -- surface-reconcile events; `spec-pyforge-unifying-strategy/.memlog.md` -- co-governor carry (see Residual).
- `scripts/.spec-surface-baseline.json` -- three scoped stamps.

**AC to test map.**
- AC 1, AC 2 (silent): `test_acknowledged_dream_is_silent_in_either_home[live|archive]`
- AC 2 (re-fire): `test_stale_acknowledgement_refires_identically_before_and_after_the_move`
- AC 3: `test_live_copy_wins_when_a_slug_is_in_both_homes` (both directions)
- AC 4: `test_no_archive_directory_behaves_as_before`
- AC 5: live measurement below
- Matrix edges: `test_archive_only_tree_still_reports`, `test_archive_dreams_are_merged_with_live_ones`, `test_unlistable_archive_dir_is_skipped_and_live_dreams_survive`, `test_unreadable_file_is_skipped_in_the_archive`

**Mutation AC (run by hand).** `_LOCAL_DREAM_DIRS` cut to `(("docs", "dreams"),)`, file restored afterwards. First run: 4 failed, 37 passed, and `test_acknowledged_dream_is_silent_in_either_home[archive]` still passed (an unseen Dream is silent too, so silence alone was a vacuous oracle). That test now also asserts the archived Dream's acknowledgement is parsed and the sibling fetch ran. Second run: 5 failed, 36 passed, the `[archive]` case among the failures. Unmutated: 41 passed.

**AC 5 (live, real sibling, GH token from `gh auth token`).** `gather` on this tree returns `()` before (docs only) and `()` after (docs plus archive); the six archived Dreams are read (146 local slugs), none shares a filename with the sibling.

**Verification (exit codes read directly).**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- exit 0, 3073 passed, 1 skipped.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test-coverage` -- exit 0 (`sibling_dreams.py` 99%, floor 80%).
- `lint-types`: ruff and mypy are green for every package; `ruff-format` is red for `pyforge-scribe` only (`catalog.py:387`, present on `origin/main`, not this diff).
- `pixi run -e pyforge-guild spec-surface-check` -- exit 0, no findings, after the scoped stamps.

**Residual.** Stamping `spec-pyforge-core` re-baselined files that only its memlog had been clearing; that surfaced two `drift-presumed` WARNs for `spec-pyforge-unifying-strategy` (`cutover_root.py`, `test_cutover_root.py`, both changed under steward Story 76.1 and already reconciled in core's memlog). They were cleared with a memlog event on that Spec and a scoped stamp. The stamps also carry baselines for other memlog-reconciled files of the three Specs.
