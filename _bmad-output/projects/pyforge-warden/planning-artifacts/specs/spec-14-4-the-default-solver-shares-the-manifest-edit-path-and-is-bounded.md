---
title: "14.4: The default solver shares the manifest edit path and is bounded"
type: 'fix'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-14-1-the-actuator-resolves-the-lowest-osv-fixed-release-the-estate-s-solver-accepts.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-14-2-the-actuator-edits-the-manifest-and-re-solves-the-lock-in-a-throwaway-copy.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/fix_solver.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/manifest_edit.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-24's real `--open-fix-prs` path resolves a target by asking the default pixi-lock solver to accept each
OSV-fixed candidate, and that solver fails on the estate's own manifests and runs unbounded (line numbers at
`03a7aff5d9`):
- `default_pixi_lock_solver` probes through its own two regexes (`_probe_pixi_toml_floor`, `src/shared/packages/pyforge-warden/src/pyforge/warden/fix_solver.py` about
  :152-171), which match only a double-quoted key or a single-quoted bare key. The bare-key form the repo uses,
  `pkg = ">=1.0"`, is never probed, and `pyproject.toml` and recipe dependencies are always rejected. The edit path the
  fix itself takes (`manifest_edit.edit_requirement_to_floor`, through `manifest_fixup.prepare_manifest_fix`) handles
  bare keys, so the two paths disagree (WAR-D-C2).
- `_edit_pixi_toml`'s last pattern (`src/shared/packages/pyforge-warden/src/pyforge/warden/manifest_edit.py` about :49-56) matches `pkg = ">=1.0"  # note` with the quoted
  value as its group and writes the floor back unquoted, which is invalid TOML.
- `resolve_fix_target`'s candidate loop (`fix_solver.py` about :121-131) has no cap and no total budget, each candidate
  copies the whole scanned tree (`.pixi/` and `.git` included, about :176-178), and each `pixi lock` may take
  `PIXI_LOCK_TIMEOUT_SECONDS = 600.0` (`src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py:177`) (WAR-M-D5).
- `PIXI_VERSION_RANGE = SpecifierSet(">=0.80.0,<0.81")` (`engines.py:174`) excludes the installed pixi 0.81.0, so the
  real path refuses on the workspace's own pixi, and nothing ties the range to `pixi.toml`'s `requires-pixi`.
- `DW-warden-14-1` (`_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md`, about :816) records that the default solver has never run end to
  end; the unit tests inject the seam only (WAR-D-R1).

EGM audit 2026-11-01, cluster WAR-CL-7; findings WAR-D-C2, WAR-D-R1, WAR-M-D5, accepted by the operator on 2026-11-01;
residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:**
- The default solver probes a candidate by editing its copy through `manifest_edit.edit_requirement_to_floor`, the one
  edit path `prepare_manifest_fix` uses, so `pixi.toml` bare keys, `pyproject.toml` and recipe requirement lines are all
  probed. `_probe_pixi_toml_floor` goes.
- `_edit_pixi_toml` keeps a quoted value quoted before a trailing comment and preserves the file's final newline, or
  its absence.
- `resolve_fix_target` caps the candidate list and bounds the loop with a total solve budget; an overrun is a `failed`
  actuation outcome. `PIXI_LOCK_TIMEOUT_SECONDS` becomes configurable (the Spec's Resource-bounds constraint). The
  per-candidate `copytree` ignores `.pixi/` and `.git`.
- `PIXI_VERSION_RANGE` is retested and widened to admit the workspace pixi, and tied to `requires-pixi`: an entry in
  `scripts/pixi_version_registry.py`, or a test that reads `pixi.toml`.
- `tests/unit/test_fix_solver_seam.py` gains the bare-key, trailing-comment and last-line-without-newline cases with
  `run_pixi_lock` stubbed, and an opt-in integration test runs the real `pixi lock` on a hermetic fixture repo.
  `DW-warden-14-1` closes.
- A memlog decision on `spec-pyforge-warden` records the shared edit path, the cap, the budget and the configurable
  timeout; CAP-24 success names the bound through a `bmad-spec` re-derive.

Ledger key: `14-4-the-default-solver-shares-the-manifest-edit-path-and-is-bounded`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-warden` CAP-24 (FR-41) — the fix-PR actuator finishes the fix on the estate's repos. A `fix`, so no
  new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag (the 14.1 and 14.2 flags keep gating the path).

## Acceptance Criteria

- **AC1 — Every declaration form is probed.** Given fixture repos that declare the vulnerable package as a `pixi.toml`
  bare key (`pkg = ">=1.0"`), a quoted key, a `pyproject.toml` dependency and a recipe requirement line, with
  `run_pixi_lock` stubbed to accept, When the default solver probes a candidate, Then each probe edits the copy through
  `edit_requirement_to_floor` and returns `accepted`; no form is rejected for its syntax.
- **AC2 — The edit writes valid TOML.** Given `pkg = ">=1.0"  # pinned` and, separately, a declaration on the file's
  last line with no final newline, When `edit_requirement_to_floor` sets the floor, Then the value stays quoted, the
  comment survives, the final-newline state is unchanged, and `tomllib` parses the result.
- **AC3 — The loop is bounded.** Given more candidates than the cap, or a stubbed solver slower than the total budget,
  When `resolve_fix_target` runs, Then it stops at the cap or the budget and returns a `failed` resolution naming the
  bound; the status and exit code are unchanged.
- **AC4 — The copy is lean.** Given a scan target with `.pixi/` and `.git` directories, When a candidate is probed, Then
  the copy holds neither, and the scanned tree is byte-identical after the run.
- **AC5 — The workspace pixi is in range.** Given the workspace's pixi (0.81.0 at mint), When the real path checks
  `PIXI_VERSION_RANGE`, Then it is admitted; and a test (or a `scripts/pixi_version_registry.py` entry checked by
  `pixi-version-check`) fails when the range and `pixi.toml`'s `requires-pixi` drift apart.
- **AC6 — The real path runs once.** Given an opt-in marker (excluded from the default loop), When the integration test
  runs, Then the real `pixi lock` re-solves a hermetic fixture repo's copy at a candidate floor.
- **AC7 — The records close.** `DW-warden-14-1` carries a `resolution:` naming this story and a `verified:` line citing
  the `path:line` of the new test; a memlog decision records the bound, and CAP-24 success names it through a
  `bmad-spec` re-derive.
- **AC8 — Green.** `pixi run --frozen -e pyforge-warden pyforge-warden-test` passes.

## Boundaries & Constraints

**Always:** one manifest edit path for the probe and the fix; the scanned tree is never written; every failure is a
`failed` actuation outcome, never a rung, a status or an exit code; pixi runs only on the real `--open-fix-prs` path,
through `_engine_env()`.

**Never:** add a second regex set for the probe; run a real `pixi lock` in the default test loop; widen the version
range without a test against the installed pixi; hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-warden` CAP-24 (FR-41) — the fix-PR actuator finishes the fix on the estate's repos;
  a fix, no new CAP.

Parent: CAP-24

- EGM audit findings carried: WAR-D-C2, WAR-D-R1, WAR-M-D5 (cluster WAR-CL-7; accepted 2026-11-01; one memlog event
  each on `spec-pyforge-warden/.memlog.md`); residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Deferred work: closes `DW-warden-14-1`.
- Epic: Epic 14 — a fix story joins its done epic (operator rule 2026-10-04; doctor Story 41.5 lets the epic key roll up
  to `in-progress`).
- Ledger key: `14-4-the-default-solver-shares-the-manifest-edit-path-and-is-bounded`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-warden/src/pyforge/warden/fix_solver.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/manifest_edit.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/manifest_fixup.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py`,
  `src/shared/packages/pyforge-warden/tests/unit/test_fix_solver_seam.py`, `src/shared/packages/pyforge-warden/tests/unit/test_manifest_edit.py`, `scripts/pixi_version_registry.py`,
  `_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md`.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Minted 2026-11-01 by the EGM audit landing (marshal Story 113.7, spec-pyforge-marshal:CAP-302); mode in-PR: built in the audit's landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_fix_solver_seam.py src/shared/packages/pyforge-warden/tests/unit/test_manifest_edit.py src/shared/packages/pyforge-warden/tests/unit/test_manifest_fixup.py src/shared/packages/pyforge-warden/tests/unit/test_fix_target_resolution.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Run before the push:**
- The opt-in real-`pixi lock` integration test, by its marker, on a machine with the workspace pixi — expected: pass.
- `pixi run -e pyforge-guild pixi-version-check` when the registry gains an entry — expected: exit 0.

## Auto Run Result

Status: done

Summary: implemented 2026-11-01 in the EGM audit landing worktree (branch `egm-audit-2026-11`, uncommitted; the
session owner commits). Every AC is met in code and tests; the CAP-24 success re-derive (AC7's last clause) is
recorded as a memlog decision and waits for the session's `bmad-spec` re-derive phase.

What changed:
- `fix_solver.py` — `_probe_pixi_toml_floor` and its two regexes are gone. `default_pixi_lock_solver` copies the scan
  target, walks the copy for `pixi.toml` / `pyproject.toml` / `meta.yaml` / `recipe.yaml`
  (`manifest_edit.MANIFEST_FILE_NAMES`) and sets the floor through `edit_requirement_to_floor`, the edit path
  `prepare_manifest_fix` takes; exactly one edited manifest is required (a package declared in two manifests is
  refused, as the fix refuses it), then `pixi lock` runs (AC1). `resolve_fix_target` gains `max_candidates`
  (`MAX_FIX_CANDIDATES = 5`), `solve_budget_seconds` (`FIX_SOLVE_BUDGET_SECONDS = 1800.0`, per finding),
  `pixi_lock_timeout_seconds` and an injectable `clock`: it starts no solve once the budget is spent, stops after the
  cap, and returns `target=None` with a `failure_detail` naming the bound, which the actuator turns into a `failed`
  outcome (AC3). The default solver's lock timeout is `min(pixi_lock_timeout_seconds, remaining budget)`.
- `manifest_fixup.py` — new `copy_scan_target` (`copytree` with `.pixi` and `.git` ignored), used by both the solver
  probe and `prepare_manifest_fix` (AC4); the plan reads the edited manifest with `newline=""`.
- `manifest_edit.py` — `_edit_pixi_toml` matches a bare or quoted key with a double- or single-quoted value and an
  optional trailing comment, using only `[ \t]` around the value, so the quotes and comment survive and no line break
  is consumed (the old `\s*$` ate the final newline and a following blank line; the old fourth pattern wrote
  `pkg = >=x  # note`, invalid TOML). An unquoted value is never written. `edit_requirement_to_floor` reads and
  writes with `newline=""`, so a CRLF manifest stays CRLF (AC2).
- `engines.py` — `PIXI_VERSION_RANGE` is `>=0.80.0,<0.82` (admits CI's 0.80.0 and the workspace 0.81.0, still closed
  before 0.82); `run_pixi_lock(cwd, timeout=PIXI_LOCK_TIMEOUT_SECONDS)` makes the timeout configurable and runs
  `pixi lock --manifest-path <cwd>`. Found while building AC6: under a `pixi run` parent, `pixi lock` in a copy with no
  `pixi.toml` / `pyproject.toml` falls back to the exported `PIXI_PROJECT_MANIFEST` and re-solves the host workspace's
  own lock; recipe-only and pyproject-only probes now reach `pixi lock`, so the pin is required (AC5, Boundary: the
  scanned tree and host are never written).
- Range drift (AC5) is held by a test, not a `scripts/pixi_version_registry.py` entry: a registry floor site would be
  bumped by `bump-pixi-version` without its `<0.82` ceiling, producing an empty range; the test reds both directions
  instead. `scripts/pixi_version_registry.py` is unchanged, so `pixi-version-check` is not owed.
- Tests: `tests/unit/test_fix_solver_seam.py` (AC1 four declaration forms with a spy on `edit_requirement_to_floor`
  and `run_pixi_lock` stubbed; two-manifest refusal; AC4 lean copy plus byte-identical scan tree; AC3 cap, budget and
  timeout-never-outruns-budget); `tests/unit/test_manifest_edit.py` (AC2: trailing comment, last line without
  newline, final newline, blank line after, literal string, CRLF — each parsed by `tomllib` — and no unquoted write);
  `tests/unit/test_manifest_fixup.py` (fix path lean copy, CRLF kept in the plan); `tests/unit/test_fix_target_resolution.py`
  (cap is a `failed` actuation outcome); `tests/unit/test_engine_env_deptry.py` (`--manifest-path` argv, timeout
  pass-through); `tests/meta/test_engine_version_range_sync.py` (range floor equals `requires-pixi`'s floor; 0.80.0 and
  0.81.0 in, 0.82.0 out); `tests/integration/test_fix_solver_real_pixi.py` (AC6, `@pytest.mark.slow`, skipped without
  pixi: the real `pixi lock` re-solves a hermetic local `file://` channel fixture's copy at floor 1.3.0, rejects an
  unsolvable 9.9.9, and refuses a manifest-less copy without touching the host `pixi.lock`). The old code fails the
  AC2 trailing-comment, final-newline and blank-line cases (checked against `HEAD`'s `_edit_pixi_toml`).
- Records (AC7): `DW-warden-14-1` carries `resolution:` this story's key and `verified:` citing
  `src/shared/packages/pyforge-warden/tests/integration/test_fix_solver_real_pixi.py:73`, status `closed`;
  `spec-pyforge-warden/.memlog.md` has the surface-reconcile event and a decision naming the bound for the CAP-24
  re-derive.

Commands run (exit codes read from `$?`):
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — 0 (2201 unit+meta passed, 265 integration/other passed).
- `pixi run --frozen -e pyforge-warden pytest …/test_fix_solver_seam.py …/test_manifest_edit.py …/test_manifest_fixup.py …/test_fix_target_resolution.py -q` — 0 (53 passed).
- `pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/integration/test_fix_solver_real_pixi.py -m slow -q` — 0 (3 passed, real pixi 0.81.0).
- `pixi run --frozen -e pyforge-warden pytest …/tests/meta/test_engine_version_range_sync.py …/tests/unit/test_engine_env_deptry.py -q` — 0 (61 passed).
- Unit coverage of the touched modules (private `--cov-report` run): `fix_solver.py` 98%, `manifest_edit.py` 92%,
  `manifest_fixup.py` 83%, `engines.py` 81% — all above the 80% touched-module floor.
- `ruff check` and `ruff format --check` (pyforge-guild's ruff, warden's `[tool.ruff]`) over the 11 changed Python
  files — 0 / 0.
- `pixi run --frozen -e pyforge-guild lint-types` — 1, from the `ruff` verb on `pyforge-doctor` alone (an import-order
  finding in another station's in-flight test file, not this story's); `pyforge-warden` ruff ok.
  `python scripts/lint_types.py ruff-format` — 0; `python scripts/lint_types.py mypy` — 0 (all ten packages, warden ok).

## Spec Change Log

- 2026-11-01: minted `backlog` from the EGM fleet audit (marshal Story 113.7): cluster WAR-CL-7, findings WAR-D-C2,
  WAR-D-R1 and WAR-M-D5, accepted by the operator; mode in-PR.

## Review Triage Log

- **Review 1 (2026-11-01, reviewer: independent session) — PASS.**
  - Checked: the diffs of `fix_solver.py`, `manifest_edit.py`, `manifest_fixup.py`, `engines.py`, the seven test files and the deferred-work ledger against AC1-AC8 and the Boundaries; callers of `run_pixi_lock`, `resolve_fix_target` and `default_pixi_lock_solver` (only the actuator and `prepare_manifest_fix`).
  - Common evidence (one run for all eight stories, exit codes read from `$?`): `pixi run --frozen -e pyforge-warden pyforge-warden-test` exit 0 (2255 unit+meta, 265 other); the twelve touched warden unit/meta test files together exit 0 (290 passed, 0 skipped; opengrep 1.30.2 and osv-scanner present); `ruff check` and `ruff format --check` over every changed warden, django-warden and platform test file exit 0; `python scripts/lint_types.py ruff-format` exit 0 and `python scripts/lint_types.py mypy` exit 0 (`pyforge-warden ok`); `pixi run --frozen -e pyforge-guild lint-types` exit 1 only from `pyforge-doctor`'s I001 in `tests/unit/test_sources_pages_liveness.py`, another station's in-flight file (`pyforge-warden` and `django-warden` ruff legs ok); `pixi run -e pyforge-guild platform-ci-local -- --test` (private ports) exit 0, RESULT: PASS, 1377 passed / 14 skipped; touched warden modules' unit coverage all at or above 81%. Mutations ran on scratch copies only (warden via `PYTHONPATH`, django-warden via `pytest -o pythonpath=`), never on the worktree.
  - AC6: `pytest src/shared/packages/pyforge-warden/tests/integration/test_fix_solver_real_pixi.py -m slow` exit 0 (3 passed, real pixi 0.81.0); the root `pixi.lock` mtime and size were unchanged after it. The default loop excludes it (`-m "not slow"`).
  - Mutations: HEAD's `_edit_pixi_toml` turns 5 AC2 cases red (trailing-comment, final-newline, blank-line-after, literal-string, crlf; last-line-no-newline already passed under the old code); dropping the `[:max_candidates]` slice turns 2 red; dropping the `.pixi`/`.git` ignore turns 2 red; disabling the budget check turns 1 red.
  - AC5: the range admits 0.81.0 and the meta test reds a floor drift from `requires-pixi` (test route, not a registry entry, as the AC allows). AC7: `DW-warden-14-1` carries `resolution:` and `verified:` citing `test_fix_solver_real_pixi.py:73`, the test's `def` line.
  - Carried forward, not held against the story: the CAP success-line change is recorded on `spec-pyforge-warden/.memlog.md`; `SPEC.md` is unchanged, as required, and the line waits for the session owner's `bmad-spec` re-derive.
  - Observations for the session owner, not failures: (a) the probe walks every `pixi.toml` / `pyproject.toml` / `meta.yaml` / `recipe.yaml` in the copy and refuses a package declared in more than one, while `prepare_manifest_fix` decides from the scan's `manifest_locations`, so a second declaring manifest the scan does not attribute (a vendored or fixture directory) makes the solver refuse a fix the edit could make; (b) a recipe-only or pyproject-only repo with no pixi workspace still never gets `accepted` from the real `pixi lock` (AC1 holds with the lock stubbed, as written); (c) the copy has no `.git`, so a pixi path dependency whose version comes from VCS (setuptools-scm, hatch-vcs) cannot be locked there (the Approach mandates the ignore); (d) the 1800 s per-finding budget is above the fleet approve task's 240 s soft limit (Story 16.7), so on the fleet path the Celery limit is the effective bound.
  - Failures: none.
