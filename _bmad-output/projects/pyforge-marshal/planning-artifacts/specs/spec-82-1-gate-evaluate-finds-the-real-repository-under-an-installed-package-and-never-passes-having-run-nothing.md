---
title: '82.1: Gate evaluate finds the real repository under an installed package and never passes having run nothing'
type: 'fix'
created: '2026-10-02'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `cli/config.py::repo_root()` (`:480-493`) returns `Path(__file__).resolve().parents[8]`, an index that is
right only for the editable source layout. Under an installed package (the wheel, sdist or conda artifact the build tasks
produce) it lands inside the environment prefix, so `conventional_project_policy_path` (`:496-498`) misses, `verify_commands`
composes to `()`, and `gate evaluate` reports `MRS-GATE-004` (`Verdict.WARN`, `core/verdict.py:850`) and exits 0 having run
no gate: a false green. The same root is the gate's `cwd` (`cli/gate.py:812`, `process.run(tokens, cwd=root)` at `:936`)
and its containment anchor (`:404`), so a mis-resolved root gates the wrong tree. On a prefix with fewer than nine
ancestors `parents[8]` raises a bare `IndexError` that escapes `main()`. The only guard,
`test_conventional_project_policy_path_lands_on_the_repo_root` (`tests/unit/test_harness_policy_render.py:556`), can only
ever run against the editable tree. Re-verified at HEAD a7cdb91fe4 (DW-FU-2-1-7, critical).

**Approach:**

- `repo_root()` keeps the `__file__`-derived root only when it is the repository (it carries this package's own source
  tree, `src/shared/packages/pyforge-marshal/`); otherwise it resolves the git common root of the invocation directory, the
  `repo_common_root` anchor `cli/init.py:640-649` already uses, so every worktree and loop home resolves to the one main
  checkout, as the editable install does today.
- It never indexes past a path's ancestors; when neither anchor yields a repository it raises a typed error, not
  `IndexError`.
- `evaluate_gate` turns that error into one could-not-evaluate finding (a new `MRS-GATE-*` code, `Verdict.UNEVALUABLE`,
  registered in `core/findings.py` and `core/verdict.py`) and a non-zero exit, never bare defaults and `MRS-GATE-004`.
- Every other `repo_root()` consumer keeps its call; only the anchor changes.

Ledger key: `82-1-gate-evaluate-finds-the-real-repository-under-an-installed-package-and-never-passes-having-run-nothing`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-3 (gates you can run; a verdict never false-greens) and Story 2.1 (FR-19, FR-20, FR-21; AD-4,
  AD-17, AD-26). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given `repo_root()` evaluated with `__file__` inside an environment prefix (no `src/shared/packages/pyforge-marshal/` above it) and the invocation directory inside a git checkout When it runs Then it returns that checkout's git common root
- Given the same installed layout When `marshal gate evaluate --project <slug>` runs from a loop home or story worktree of the checkout Then the project's real `verify_commands` run with the main checkout as `cwd` and the verdict reflects their exit codes
- Given an installed layout invoked outside any repository When `gate evaluate` runs Then it reports one could-not-evaluate finding and exits non-zero, with no `MRS-GATE-004` and no traceback
- Given a prefix with fewer than nine ancestors When `repo_root()` runs Then no `IndexError` escapes
- Given the editable source layout When `repo_root()` runs Then it returns the same root as today
- Given `repo_root()` restored to the bare `Path(__file__).resolve().parents[8]` When the installed-layout test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** One anchor function, `cli/config.py::repo_root()`, for every consumer. Fail loud: a root that cannot be resolved
is unevaluable, never a green. Close DW-FU-2-1-7 in `deferred-work-ledger.md` when the story lands (status `closed`, a
`resolved:` line naming this story).

**Never:** Do not resolve the root from the current directory alone when the `__file__` root is the repository (the
reason `repo_root()` avoids CWD: `marshal config` runs from loop homes and worktrees). Do not change `MRS-GATE-004`'s
meaning for a genuinely unconfigured allowlist. Do not touch `cli/seed.py`'s own target-repo resolution.

</intent-contract>

## Binding

Parent: Story 2.1 and `spec-pyforge-marshal` CAP-3; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-1-gate-evaluate-finds-the-real-repository-under-an-installed-package-and-never-passes-having-run-nothing`.
Ledger status at mint: `backlog`.
Deps: —.
Closes: DW-FU-2-1-7.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

- No review has run yet.
