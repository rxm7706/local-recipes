---
title: '23.7: A new Doctor source flags leftover-shelf occupancy'
type: 'feature'
created: '2026-09-16'
status: 'done'
baseline_revision: 'b105264cca1ee39ef46b8b48783dae847ef1c047'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** general_docs_consistency is identity-only with frozen 22.3 fixtures.

**Approach:** A new warn-only, fail-open source compares leftover-shelf paths to the MAP allow-list. Re-adding a dated campaign note at _bmad-output/ root, or a second air-gap how-to outside the cluster, is a finding with a quoted path. A clean MAP fixture is silent. Never a second PR gate.

## Boundaries & Constraints

**Always:**
- Warn-only, fail-open.
- Finding quotes the leftover path.
- Finding is never a second PR gate.

**Never:**
- Do not reuse general_docs_consistency.py.
- Do not make this a competing PR verdict.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| dated note at root | _bmad-output/<campaign>.md | finding with quoted path | warn |
| clean MAP fixture | allow-listed only | silent | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-54` (absorbed + renumbered from `spec-docs-shelf-alignment CAP-7` on 2026-09-17).
Surface: a new pyforge.doctor.sources module (not general_docs_consistency.py), pixi task, unit fixtures..
Ledger key: `23-7-a-new-doctor-source-flags-leftover-shelf-occupancy`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-7-a-new-doctor-source-flags-leftover-shelf-occupancy.md`.

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 10 findings — high 0, medium 3, low 5, false 2, maybe-false 0
- findings:
  - `[medium]` `[patch]` Blind Hunter: stale/ambiguous capability citation `spec-docs-shelf-alignment CAP-7` propagated into ~8 new files — verified `spec-pyforge-doctor/SPEC.md:225` shows that sub-spec was absorbed and renumbered `CAP-54` on 2026-09-17, and `SPEC.md:84` shows an unrelated, real, native `CAP-7` (the `monitor --fleet` adoption axis) already exists in that station — citation is stale and actively ambiguous. Fix applied: replaced with `spec-pyforge-doctor CAP-54` across the new code/test comments (`docs_shelf.py`, `models.py`, `sources/__main__.py`, `pixi.toml`, `scripts/detectors.py`, `test_sources_docs_shelf.py`, `test_source_independence.py`, `test_models.py`, `test_sources_dispatch.py`); corrected this spec's own `## Binding` line myself; the two `.memlog.md` entries were authored fresh by me after this pass (see landing note below) so needed no separate fix.
  - `[medium]` `[patch]` Edge Case Hunter: `_AIRGAP_NAME_RE` (`docs_shelf.py`) lacks word boundaries, so it substring-matches inside unrelated filenames — verified `re.search(r"air[\s_-]?gap", "repair-gap-analysis.md")` matches "air-gap" inside "rep-AIR-GAP-". Fix applied: added `\b` boundaries (`r"\bair[\s_-]?gap\b"`) plus a regression test. Shares root cause and fix with the next row.
  - `[medium]` `[patch]` Blind Hunter: same unbounded-regex defect, example `lair-gap.md`. Shares fix with the row above.
  - `[low]` `[patch]` Blind Hunter: `find_bmad_output_root_leftovers` catches `OSError` from `root.iterdir()` locally and returns `()` (reports "clean"), bypassing `gather()`'s `degrade_on_exception` wrapper — verified `degrade_on_exception`'s docstring documents converting any exception into a "could not be evaluated here" WARN; the local catch defeats that contract for a permission-denied `_bmad-output/`. Fix applied: removed the local `except OSError` in `find_bmad_output_root_leftovers`; the implementation subagent also flagged and fixed the identical pattern in the sibling `find_extra_airgap_docs` (around `quadrant_dir.rglob("*.md")`) as a direct extension of this same root cause — not a separately-reviewed finding, applied for consistency.
  - `[false]` `[reject]` Blind Hunter: `test_live_repo_gather_is_clean` scans the live working tree instead of a fixture, risking spurious local failure. Refutation: this is an established, deliberate convention already shared by 9 sibling source test files in this same package (incl. its named predecessor `test_sources_general_docs_consistency.py`) — not a risk this diff introduces. CI runs from a clean checkout, so the "stray local file" scenario doesn't occur there; a local dev hitting red because of a genuine stray file is this source's intended behavior.
  - `[low]` `[patch]` Blind Hunter: test name `test_main_scope_repo_reports_ten_unknown_rows_and_never_exits_zero_when_unimportable` says "ten" but `_DOCTOR_SOURCE_TASKS` now has 11 entries — verified the assertion derives the count dynamically (still passes), only the name is stale. Fix applied: renamed to `test_main_scope_repo_reports_unknown_rows_and_never_exits_zero_when_unimportable`.
  - `[low]` `[patch]` Blind Hunter: grammar fragment in `models.py`'s new comment — "...docs/MAP.md's own 'Outside this map' table and Story 23.2's fold establish." doesn't parse. Fix applied: reworded to "...against the allow-list that docs/MAP.md's own 'Outside this map' table and Story 23.2's fold established."
  - `[low]` `[patch]` Blind Hunter: WARN message "(docs/MAP.md § Outside this map)" implies the whole `_bmad-output/` root allow-list is MAP.md-sourced — verified `docs/MAP.md` lines 23-33 only name `_bmad-output/projects/*/{planning,implementation}-artifacts/`, never `PROJECTS.md`, `brainstorming/`, `harness-profiles/`, `policy-defaults.toml`, `EXEMPLAR-STANDARD.md`, or the root symlinks (those are allow-listed only via this module's own comment). Fix applied: reworded the WARN message to "... is not in the doctor-maintained _bmad-output/ root allow-list" (dropped the MAP.md parenthetical citation). Shares root cause with the next row.
  - `[low]` `[patch]` Intent Alignment Auditor: the intent's "MAP allow-list" phrasing reads as MAP.md-derived; the implementation hand-copies a broader hardcoded allow-list not fully backed by MAP.md's text. Shares fix with the row above (message wording only — the allow-list content itself is correct and does not need to change).
  - `[false]` `[reject]` Blind Hunter: `sprint-status-ledger.yaml`/`epics.md` still read `backlog` despite the memlog's "realized" language. Refutation: ledger/epics promotion is a distinct downstream landing step performed after review/merge by marshal's own tooling (`sprint-ledger-sync`), not part of this dev/review dispatch's scope — direct precedent on this same branch: the commit preceding this run's baseline is "marshal: promote sprint-status ledger for 'pyforge-doctor' (1 key(s) -> done)" for the prior story (23.6), confirming this sequencing is by design.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

## Auto Run Result

Status: done

**Summary:** New warn-only, fail-open doctor source `docs-shelf-occupancy` (`pyforge.doctor.sources.docs_shelf`) with two checks — `find_bmad_output_root_leftovers` (non-recursive occupancy of `_bmad-output/` root vs a fixed allow-list) and `find_extra_airgap_docs` (air-gap-named `.md` files outside Story 23.2's two-file cluster, scanned across `docs/MAP.md`'s four Diátaxis quadrant dirs) — both quoting the leftover path in a WARN `Finding`; `gather()` falls back to a single OK when clean. Never reuses `general_docs_consistency.py`; never a second PR gate.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_shelf.py` (new) — the source module itself.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` — new `Source.DOCS_SHELF_OCCUPANCY` member.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` — new REGISTRY row (`scope=repo`, `subject_station=fleet`, `owning_station=doctor`).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py` — new DISPATCH entry.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json` — new `source` enum value.
- `pixi.toml` — new `docs-shelf-occupancy-check` task.
- `scripts/detectors.py` — wired into `_DOCTOR_SOURCE_TASKS` (the `detectors-ci` sweep).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_shelf.py` (new) — 16 unit tests covering both I/O matrix rows, allow-list false-positive guards, the regex word-boundary regression, and a live-repo proof.
- `src/shared/packages/pyforge-doctor/tests/fixtures/docs_shelf/clean/**` (new) — clean MAP fixture tree.
- `src/shared/packages/pyforge-doctor/tests/unit/test_models.py`, `tests/unit/test_sources_dispatch.py`, `tests/meta/test_source_independence.py` — closed-set/dispatch/independence meta-tests extended for the new `Source` member.
- `tests/scripts/test_detectors_doctor_sources.py` — new task-membership test; renamed a stale-count test the new 11th entry made inaccurate.
- `scripts/.spec-surface-baseline.json` — re-stamped for `pyforge-doctor/spec-pyforge-doctor` and `pyforge-marshal/spec-pyforge-core` (twice: once after implementation, again after the review-patch round).
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` — owner reconcile entry.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md` — co-governor reconcile entry.
- This spec file — `status`/`baseline_revision`, `## Binding` capability citation, `## Review Triage Log`, this section.

**Review findings breakdown** (4 layers: Blind Hunter, Edge Case Hunter, Verification Gap Reviewer, Intent Alignment Auditor — full detail in `## Review Triage Log` above):
- **Patched** (6 grouped entries, 8 raw findings + 1 out-of-band symmetric fix): stale/ambiguous capability citation (`spec-docs-shelf-alignment CAP-7` → `spec-pyforge-doctor CAP-54`, absorbed+renumbered 2026-09-17); unbounded `_AIRGAP_NAME_RE` regex (added `\b` word boundaries + a regression test, found independently by both Blind Hunter and Edge Case Hunter); `find_bmad_output_root_leftovers` swallowing `OSError` locally instead of letting `degrade_on_exception` handle it (fixed; the implementation subagent also found and fixed the identical pattern in the sibling `find_extra_airgap_docs`, applied for consistency though it wasn't itself one of the four layers' findings); a stale test name ("ten" vs the new 11-entry count); a grammar fragment in a `models.py` comment; a WARN message overclaiming direct `docs/MAP.md` sourcing for the whole `_bmad-output/` root allow-list (Blind Hunter + Intent Alignment Auditor, same root cause).
- **Rejected** (2, both `false`): a live-repo-scanning test (`test_live_repo_gather_is_clean`) risking local flakiness — refuted as an established, deliberate convention already shared by 9 sibling source test files in this package, and CI's clean-checkout model doesn't hit the described scenario; `sprint-status-ledger.yaml`/`epics.md` still reading `backlog` — refuted as a distinct downstream landing step (marshal's `sprint-ledger-sync`, post-merge), not part of this dev/review dispatch's scope, with direct precedent on this same branch (the prior story's own "marshal: promote sprint-status ledger" commit).
- **Deferred:** none.
- Verification Gap Reviewer: no gaps found (all changed call sites — `scripts/detectors.py`, the CLI dispatch, the REGISTRY↔`Source` coherence check, `verdict.exit_code_for`'s WARN-never-fails contract — traced and confirmed exercised by a real, non-mocked test).

**Follow-up review recommendation:** `false`. The mechanical score (2 `medium`-verdict patched entries — the capability citation and the regex fix) crosses the "true" threshold, but per the "name the specific unverified risk, or it's false" rule: independent re-verification after the patch round found none. Both `medium` fixes were manually re-inspected in the final code (regex now has `\b` boundaries and a dedicated regression test; every `spec-docs-shelf-alignment CAP-7` citation is gone from the tree, grep-confirmed), the full doctor suite (1805 passed, 1 skipped) and the full fleet sweep (`pyforge-core` + all 8 stations, exit 0) both re-ran clean post-patch, and `spec-surface-check` is clean after re-stamping. No specific unverified risk survives to name.

**Verification performed:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` (the spec's bound Verification command), run independently by the orchestrating session both pre-patch (1804 passed, 1 skipped, exit 0) and post-patch (1805 passed, 1 skipped, exit 0) — not just the implementation subagent's self-report.
- Matrix Test Audit: both I/O & Edge-Case Matrix rows (dated note at root → WARN with quoted path; clean MAP fixture → silent/OK) covered by tests that ran and passed both times.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — clean after reconcile+stamp, both before and after the patch round.
- `pixi run --frozen -e pyforge-guild pyforge-station-tests` (required — `pixi.toml` changed) — `pyforge-core` + all 8 stations, exit 0, run independently post-patch.
- Manual code review of the final `docs_shelf.py`, `models.py` diffs confirming every patched finding's fix landed as described.

**Residual risks:** none identified. The allow-list constants remain hand-maintained (not parsed live from `docs/MAP.md`) — documented as a known, accepted limitation shared with this module's sibling sources, not a defect.

