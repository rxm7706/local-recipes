---
title: '136.1: Steward''s last two modules derive the station-packages directory from the root layout'
type: 'fix'
created: '2026-11-25'
status: 'in-review'
story: 136-1-steward-s-last-two-modules-derive-the-station-packages-directory-from-the-root-layout
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/five_tier.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_suite_reduction.py'
  - 'src/shared/packages/pyforge-steward/tests/meta/test_portability.py'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md'
  - 'docs/foundry/capability-ledger.yaml'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-steward-123-2-2`. `five_tier.py:70` and `preflight_suite_reduction.py:194` join `repo_root / "src" / "shared" / "packages"` by hand, and `tests/meta/test_portability.py` carries both in `LAYOUT_EXCEPTIONS` under `DW-steward-123-2-2`, so spec-pyforge-steward CAP-182's "every other module derives from it" is not met.

**Approach:** Derive both paths from `root_layout.STATION_PACKAGES_DIR`, delete the two `LAYOUT_EXCEPTIONS` entries in the same change (the test fails when an entry no longer applies), and record on the Spec's memlog that CAP-182's qualifier naming this row leaves its marker.

Ledger key: `136-1-steward-s-last-two-modules-derive-the-station-packages-directory-from-the-root-layout`.

### Living CAP citations

- spec-pyforge-steward CAP-182 (one module names this root's layout; the marker drops its `not met: every other module derives from it` qualifier through the memlog); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce what the row reports on the unchanged tree before changing it, and record the reproduction in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change a path either module returns.
- Never add a `LAYOUT_EXCEPTIONS` entry.
- Never add a flag, a capability or an architecture decision; a fix that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-steward-123-2-2` reports that `five_tier.py` and `preflight_suite_reduction.py` spell the station-packages directory segment by segment and that `test_portability.py` excepts both by name
**When** both modules derive the directory from `root_layout.STATION_PACKAGES_DIR` and the two `LAYOUT_EXCEPTIONS` entries are deleted
**Then** `LAYOUT_EXCEPTIONS` is empty, `test_portability.py` passes, every path the two modules returned before is the same path, and no steward module but `root_layout.py` joins those three segments
**And** the memlog of `spec-pyforge-steward` records that CAP-182's marker drops the qualifier naming `DW-steward-123-2-2`, and the row reads resolved

- **AC1 — No module but the layout module joins the segments.** Expected: exit 1 (no line matches).

  ```bash
  grep -rn -E '"src" */ *"shared" */ *"packages"' src/shared/packages/pyforge-steward/src/pyforge/steward --include='*.py'
  ```

- **AC2 — The exceptions map is empty and the portability test holds.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_portability.py -q
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-182 (one module names this root's layout; the marker drops its `not met: every other module derives from it` qualifier through the memlog); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the rows a lapsed blocker held close); operator ruling of 2026-11-25: "All 22 rows".
- Epic: Epic 136, minted with this story.
- Ledger key: `136-1-steward-s-last-two-modules-derive-the-station-packages-directory-from-the-root-layout`.
- Deferred-work row: `DW-steward-123-2-2`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."136"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the rows a lapsed blocker held close) and the operator's ruling of the same date. Not implemented.
- 2026-11-25: reproduced `DW-steward-123-2-2` on the unchanged tree: AC1's grep exited 0, naming `five_tier.py:70` (`return repo_root / "src" / "shared" / "packages"`) and `preflight_suite_reduction.py:194` (`pkg = repo_root / "src" / "shared" / "packages" / f"pyforge-{station}"`), and `test_portability.py` held both in `LAYOUT_EXCEPTIONS` under that id.
- 2026-11-25: implemented: both modules import `STATION_PACKAGES_DIR` from `.root_layout` and join `repo_root / STATION_PACKAGES_DIR` (the same path as before; no returned path changes); `LAYOUT_EXCEPTIONS` in `tests/meta/test_portability.py` is `{}` and its comment says why. No flag, capability or AD added.
- 2026-11-25: AC1 exit 1 (no line matches). AC2 exit 0 (37 passed). `lint-types`: ruff, ruff-format and mypy `ok` for pyforge-steward; the task as a whole exits 1 on `pyforge-atlas` mypy (`src/pyforge/atlas/observability.py:419`, a file another story is editing in this worktree). Touched modules (`test_preflight_suite_reduction.py`, `test_five_tier_check.py`, `test_preflight_concurrency.py`, `test_preflight_inherited_pytest_addopts.py`) pass; `test_preflight_concurrency.py`'s two-second timing test failed once under load (5.3 s) and passed on the re-run. `pyforge-steward-test` exit 0 (2161 passed, 14 skipped; 33 passed).
- 2026-11-25: left for the session lead: the `spec-pyforge-steward` SPEC marker and memlog line for CAP-182, the `DW-steward-123-2-2` row, the capability ledger and the scoped stamps. Noticed and not changed (outside this story's surface): `root_layout.py`'s module docstring, lines 6 to 8, still says the two modules spell the directory out segment by segment under `DW-steward-123-2-2`; that sentence is now stale.
- 2026-11-25: session lead: `root_layout.py`'s module docstring, which still said the two modules spell the path out under `DW-steward-123-2-2`, now says the test excepts no module (a stale line in the file the story's capability names; `test_portability.py` exit 0).
