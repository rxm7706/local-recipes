---
title: '82.1: Gate evaluate finds the real repository under an installed package and never passes having run nothing'
type: 'fix'
created: '2026-10-02'
status: 'done'
baseline_revision: 'e537a533144fd0b5f65586ddb5a42b74eb65b62c'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
warnings: [oversized]
deferred:
  - summary: >-
      Three sibling loaders still resolve `scripts/promote_sprint_status.py` through `Path(__file__).resolve().parents[8]`, so they break under an installed package the way `repo_root()` did.
    evidence: |-
      `cli/chain.py:96` (`_load_promote`, raises RuntimeError when the file is missing), `cli/land.py:1278` (returns None, so land skips the feed sync) and `cli/deploy.py:3490` (asserts). None is a `repo_root()` consumer, the story's intent keeps every other consumer's call unchanged, and `cli/deploy.py` deliberately avoids `repo_root()` so `tests/unit/test_deploy.py` can redirect it. The script is a repo file the artifact does not ship, so the fix needs an anchor decision, not a one-line swap.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/chain.py:96
    severity: medium
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

### 2026-10-02 — Review pass
- verdicts: 28 findings — high 0, medium 2, low 20, false 6, maybe-false 0
- findings:
  - `[low]` `[reject]` Blind: a cwd inside an unrelated git checkout still ends in MRS-GATE-004 (warn, exit 0) — the outcome is real, but the intent selects the invocation directory's git root as the installed-layout anchor and says not to change MRS-GATE-004's meaning for an unconfigured allowlist; the same warn already happens in the editable layout for a slug with no policy file; a guard would add a branch for a case the intent excludes.
  - `[low]` `[reject]` Blind: `GitVcs.repo_common_root` is unvalidated for a submodule, bare repo or `--separate-git-dir` — the adapter is the one `cli/init.py:640-649` already uses and the intent names; no run was shown reaching an installed marshal inside such a repo; a validation guard is more than a direct correction.
  - `[false]` `[reject]` Blind: `dispatch_land_finalize/__main__.py:761` would traceback on the typed error — `dispatch_land.py` spawns it with `cwd=git_repo_root`, so under an installed layout `repo_root()` resolves through git and does not raise; a hand-run `python -m` outside any repo fails loudly, which is correct.
  - `[medium]` `[defer]` Blind: the sibling `parents[8]` loaders (`cli/chain.py:96`, `cli/land.py:1278`, `cli/deploy.py:3490`) break under an installed package and no follow-up records them — real and pre-existing, not a `repo_root()` consumer, and the fix needs an anchor decision; recorded in frontmatter `deferred`.
  - `[low]` `[patch]` Blind: the `_resolve_policy_source` docstring was reworded, no test pins the fence under the installed layout, and the gate module docstring omits the new `root-unresolved` scope and the `None` root — the stale module docstring was real and is fixed (a `root-unresolved` paragraph added to `cli/gate.py`'s module docstring); the fence-test claim is rejected because the fence is unchanged code and AC2 already runs a real policy through it.
  - `[low]` `[reject]` Blind: non-gate consumers get a plain stderr line with no JSON envelope, an unhelpful message, and a doubled cause — real but cosmetic; the relay exists only to keep `main()` never-raising, the intent keeps other consumers' calls unchanged, and a JSON branch is more than a direct correction.
  - `[low]` `[patch]` Blind: the `except OSError` around `.is_dir()` is untested — real (a mutation removing it left all 22 tests green); a test was added (`test_an_unreadable_editable_probe_falls_through_to_the_git_root`) and a re-run mutation of the guard now fails it. Grouped with the verification-gap row.
  - `[low]` `[reject]` Blind: several tests prove less than they appear (the editable test compares to the same expression, the registry test counts by source regex, the root-failure ordering is unpinned) — no named harm; the editable comparison is literally AC5's "same root as today", the ordering is what AC3's "one finding" asks for.
  - `[false]` `[reject]` Blind: ledger and memlog bookkeeping is inconsistent or incomplete — `python scripts/spec_surface_reconcile.py` and `spec-surface-check` both exit 0 with the memlog entries as written; the older `verified:` lines under DW-FU-2-1-7 are history, not the current status, and no stamp is needed for a check that passes.
  - `[low]` `[reject]` Edge: submodule/bare/`--separate-git-dir` root unchecked — same claim and same reason as the Blind row above.
  - `[low]` `[reject]` Edge: an unrelated git repo lacking the project tree is accepted unchecked — same claim and same reason as the Blind wrong-cwd row above.
  - `[low]` `[patch]` Edge: `repo_root()` is re-called at `conventional_project_policy_path` and `_resolve_policy_source`, so a later call could fail and escape `evaluate_gate` — the invocation directory is constant so the answers agree, and `main()`'s relay catches an escape; the real defect is the "FIRST and ONCE" comment, corrected in `cli/gate.py`. Grouped with the two "ONCE" rows below.
  - `[false]` `[reject]` Edge: `dispatch_land_finalize` gets a raw traceback and exit 1 — same refutation as the Blind finalize row: the sanctioned spawn runs in a git root.
  - `[low]` `[reject]` Edge: non-gate `--format json` consumers get no envelope — same claim and same reason as the Blind JSON row.
  - `[low]` `[reject]` Edge: the editable probe hardcodes `src/shared/packages/pyforge-marshal`, which a foundry-tree move would break — the intent names exactly this path as the "is the repository" marker, and the move is speculative (`pyforge.cutover_root` has not flipped).
  - `[low]` `[reject]` Edge: the installed-layout root is the cwd's git root, so `gate evaluate` in an untrusted repo runs that repo's policy commands — this is AC2's required behaviour (run the checkout's real `verify_commands` from the main checkout) and equals running a repo's own test task; no containment contract changes.
  - `[low]` `[reject]` Edge (claim): "never passes having run nothing" is false for a wrong-cwd git root — same claim and same reason as the Blind wrong-cwd row; the Design Notes record the unconfigured-allowlist case.
  - `[low]` `[patch]` Edge (claim): the comment says the root is resolved "FIRST and ONCE" but two consumers call `repo_root()` again — fixed in the same `cli/gate.py` comment edit as the re-resolution row.
  - `[false]` `[reject]` Edge (claim): only `cli/main.py` relays the typed error, so "main() never raises" misses the finalizer — same refutation as the Blind finalize row.
  - `[low]` `[patch]` Verification gap: no test drives the `except OSError` branch of the editable probe — verified by mutation, fixed by the added test; the re-run mutation (`except ZeroDivisionError`) fails it.
  - `[false]` `[reject]` Intent alignment: the tests patch `config.__file__` in-process instead of installing a built artifact — AC1-AC4 are phrased at `__file__`-in-a-prefix level ("Given `repo_root()` evaluated with `__file__` inside an environment prefix"), which is what the tests build.
  - `[low]` `[reject]` Intent alignment: AC6 is met only implicitly — re-run here: the bare `Path(__file__).resolve().parents[8]` restored in `repo_root()` fails 18 of 23 tests in `test_repo_root.py`; the one test that pins the old warn/exit-0 shape is a documented witness, harmless.
  - `[low]` `[reject]` Intent alignment: the tests use a synthetic `acme` project and a linked worktree for the loop home — AC2 asks for the project's `verify_commands` run with the main checkout as `cwd`; a marker file present only in the main checkout shows exactly that.
  - `[false]` `[reject]` Intent alignment: `dispatch_land_finalize` has no relay for the typed error — same refutation as the Blind finalize row.
  - `[low]` `[patch]` Intent alignment: repeated `repo_root()` calls inside `evaluate_gate` — same root cause as the "ONCE" comment rows; fixed by the same `cli/gate.py` comment edit.
  - `[low]` `[reject]` Intent alignment: root failure now preempts the slug-shape and policy findings in the installed-outside-repo case — AC3 asks for exactly one could-not-evaluate finding; no harm is named, and the editable layout is unaffected.
  - `[medium]` `[defer]` Intent alignment: the same `parents[8]` assumption in the three sibling loaders — same claim and same deferral as the Blind sibling-loader row.
  - `[low]` `[reject]` Intent alignment: `cli/seed.py:64` and `:170` still describe `repo_root()` as `__file__`-derived — the comments' point (seed resolves the operator-named target, not `repo_root()`) still holds, and the intent forbids touching `cli/seed.py`.

## Auto Run Result

Status: done

**Summary.** `cli/config.py::repo_root()` keeps the `__file__`-derived root only when `parents[8]` exists and carries `src/shared/packages/pyforge-marshal/`; otherwise it returns the git common root of the invocation directory (`GitVcs.repo_common_root`, the `cli/init.py` anchor), never indexing past the path's ancestors. When neither anchor yields a repository it raises `RepoRootUnresolvedError`. `evaluate_gate` turns that into one `MRS-GATE-016` finding (`Verdict.UNEVALUABLE`, non-zero exit) with nothing run, and `main()` relays it from any other consumer as one stderr line plus the UNEVALUABLE exit. DW-FU-2-1-7 is closed in `deferred-work-ledger.md`.

**Files changed** (under `src/shared/packages/pyforge-marshal/` unless noted).
- `src/pyforge/marshal/cli/config.py` -- layout-aware `repo_root()` and the new `RepoRootUnresolvedError`.
- `src/pyforge/marshal/cli/gate.py` -- `evaluate_gate` resolves the root first and returns the one could-not-evaluate envelope; `_render_text` prints `root: (unresolved)`; module docstring and the root comment updated (review patches).
- `src/pyforge/marshal/cli/main.py` -- relays `RepoRootUnresolvedError` from other consumers.
- `src/pyforge/marshal/core/findings.py`, `src/pyforge/marshal/core/verdict.py` -- register `MRS-GATE-016` as UNEVALUABLE.
- `tests/unit/test_repo_root.py` (new), `tests/unit/test_findings.py`, `tests/unit/test_verdict.py` -- the six ACs, the registry pins, and the unreadable-probe test added in review.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- DW-FU-2-1-7 closed with a `resolved:` line.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` -- two surface-reconcile entries naming every governed path.

**Review.** 28 findings: patches applied 3 groups (gate module docstring; "FIRST and ONCE" comment; the unreadable-probe test), all low; deferred 1 (the sibling `parents[8]` loaders, medium, `deferred:` in the frontmatter); rejected 22 with the reasons recorded row by row above (6 false, 16 low).

**Follow-up review recommended:** `false` (no high patched, no two medium patched; patched by verdict: high 0, medium 0, low 3 groups).

**Verification.** Run after the review patches, exit codes read directly: `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` exit 0 (9789 passed, 1 skipped, 12 deselected); `pixi run --frozen -e pyforge-ci pyforge-deps-test` exit 0 (130 passed, 3 skipped); `python scripts/spec_surface_reconcile.py` exit 0; `spec-surface-check`, `lint-types`, `story-status-check` and `deferred-work-check` exit 0. One earlier full-suite run under heavy machine load (374 s against 84 s) failed `tests/integration/test_dispatch_structure_graph_real.py::test_a_damaged_copied_index_is_cleared_and_rebuilt_with_init`; that file passes alone (4 passed) and the next full run is green, so it is load-related, not this change. The AC6 mutation (bare `Path(__file__).resolve().parents[8]` restored in `repo_root()`) fails 18 of 23 tests in `test_repo_root.py`; the guard mutation (`except OSError` removed) fails the added unreadable-probe test. The deferral was promoted to the tracked ledger with `python scripts/deferred_work_intake.py --fix --project marshal` (`DW-marshal-82-1`).

**Residual risks.** The installed-layout answer depends on the invocation directory by design; a cwd inside a git repository that lacks the project's policy still reports `MRS-GATE-004` (the genuine unconfigured case, `data["root"]` names where it looked). `dispatch_land_finalize` and the three sibling loaders are not relayed or fixed here (see the deferred item).
