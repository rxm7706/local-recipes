---
title: '82.1: Gate evaluate finds the real repository under an installed package and never passes having run nothing'
type: 'fix'
created: '2026-10-02'
status: 'in-review'
baseline_revision: 'e537a533144fd0b5f65586ddb5a42b74eb65b62c'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
warnings: [oversized]
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

## Code Map

Paths are under `src/shared/packages/pyforge-marshal/` (`M` = `src/pyforge/marshal`).

- `M/cli/config.py:480-498` -- `repo_root()` (the one anchor) and `conventional_project_policy_path`; `PolicyIOError` (`:501`) is the typed-error-with-finding precedent; `PyforgeError` is already imported.
- `M/adapters/vcs_git.py:214` -- `GitVcs.repo_common_root(start)`: main checkout from any worktree, `VcsCommandError` outside a repo (`M/ports/vcs.py:189`); `M/cli/init.py:640-649` is the invocation-directory precedent.
- `M/cli/gate.py:701` -- `evaluate_gate`: `repo_root` imported by name (`:177-184`); consumers `_resolve_policy_source` (`:404`) and `root = repo_root()` (`:812`) -> `process.run(tokens, cwd=root)` (`:936`). `_render_text` (`:1097`) reads `data["root"]`, `["scope"]`, `["scope_note"]`, so an early envelope carries all three.
- `M/core/findings.py:1403` (`REGISTERED_CODES`, last gate code `MRS-GATE-015` at `:1946`) and `M/core/verdict.py:1247` -- `MRS-GATE-016` is free; UNEVALUABLE tier is `MRS-GATE-002/003/005/009`.
- `M/cli/main.py:385-408` -- `main()` relays only `SystemExit`/`KeyboardInterrupt`; any other consumer's typed error would traceback.
- `tests/unit/test_cli.py:1004` -- `_conventional_policy` patches BOTH `repo_root` bindings with `lambda: tmp_path` (keep it working); `tests/unit/test_harness_policy_render.py:556` -- the editable-only guard; `tests/unit/test_findings.py:418`, `tests/unit/test_verdict.py` -- registry tests.
- Read-only: `M/cli/seed.py` (own target-repo resolution); the `Path(__file__).resolve().parents[8]` script loaders in `M/cli/chain.py:96`, `M/cli/land.py:1278`, `M/cli/deploy.py:3490` load `scripts/promote_sprint_status.py` and are not `repo_root()` consumers.

## Tasks & Acceptance

**Execution:**
- `M/cli/config.py` -- add `RepoRootUnresolvedError(PyforgeError, Exception)`; `repo_root()` returns `parents[8]` only when that ancestor exists and has `src/shared/packages/pyforge-marshal/`, else `GitVcs().repo_common_root(Path.cwd())`; a `VcsCommandError`/`OSError` becomes the typed error -- never an index past the ancestors.
- `M/cli/gate.py` -- `evaluate_gate` resolves `repo_root()` first; on the typed error return one `MRS-GATE-016` finding (ERROR) with `data` `slug`/`root: None`/`policy_source: None`/`scope`/`scope_note`, run nothing; `_render_text` prints `root: (unresolved)` for `None`.
- `M/core/findings.py`, `M/core/verdict.py` -- register `MRS-GATE-016` as `Verdict.UNEVALUABLE`, comment in the neighbours' style.
- `M/cli/main.py` -- relay `RepoRootUnresolvedError` from any other consumer as one stderr line and the UNEVALUABLE exit, so `main()` still never raises.
- `tests/unit/test_repo_root.py` (new) -- the six ACs against a patched `config.__file__` and a real tmp git checkout plus linked worktree; the mutation case runs the bare `parents[8]` against the same layout and asserts it misses; `tests/unit/test_findings.py`, `tests/unit/test_verdict.py` -- pin `MRS-GATE-016`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- DW-FU-2-1-7 `status: closed` plus a `resolved:` line naming this story.

**Acceptance Criteria:** the six in the contract above, unchanged.

## Spec Change Log

## Design Notes

The installed-layout branch is cwd-dependent by design and so is not cached (a cache would pin the first caller's worktree). `parents[8]` is kept as the editable answer, not replaced by a walk, so the editable root is byte-identical to today. A git root that lacks the project policy still composes `MRS-GATE-004`: that is the genuinely-unconfigured case, and `data["root"]` names where it looked.

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
