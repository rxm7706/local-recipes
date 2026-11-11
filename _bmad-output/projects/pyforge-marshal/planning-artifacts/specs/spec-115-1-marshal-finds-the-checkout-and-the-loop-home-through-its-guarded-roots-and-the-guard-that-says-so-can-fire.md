---
title: "115.1: Marshal finds the checkout and the loop home through its guarded roots, and the guard that says so can fire"
type: 'fix'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: medium
story: '115.1'
spec: pyforge-marshal
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/config.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_checkout_root.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_watch.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_no_loop_home_run_state_read.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_no_loop_home_run_state_read_doctor_live_tree.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/benchmark.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/layer_savings_sources.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/context.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/gate.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/retire.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/teardown_preserve.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/engine_preserve.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/intent_gap_preserve.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/config.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_no_loop_home_run_state_read.py
warnings: []
deferred:
  - summary: >-
      `marshal watch` reads a loop run's last-fact time from the loop home's
      own bmad-loop journal, not from the published run-state plane.
    evidence: |-
      CAP-227 (amended 2026-11-10) moves every run-state read outside the
      publisher (which runs are live, story phase, commit, timing) to the
      published plane. `_default_ports.loop_last_fact` in cli/watch.py reads
      `<loop home>/.bmad-loop/runs/<run_id>/journal.jsonl` for the newest `ts`
      (a timing read) to rank a loop run against a dispatch run. Story 115.1
      resolves its root through BMAD_LOOP_HOME_ROOT, as `marshal init` does,
      and tags the line `CAP-4: loop-home FILE read -- run-state debt`; moving
      the read is new behaviour, which the operator ruling of 2026-11-10 (e)
      keeps out of this change. Every other site the honest guard names is
      marshal's own file, message text, run identity recovery, work
      durability or the supervisor's own budget sample, and is tagged with
      that reason instead.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Two audit defects about roots at `82a2b18828`. (1) A hard-coded root: `cli/land.py:1377`, `:1448` and `cli/deploy.py:3598` index `Path(__file__).resolve().parents[8]`, the bare form Story 82.1 replaced in `repo_root()`; under an installed package it lands in the environment prefix or raises `IndexError` after the PR merged. (2) A guard that cannot fire: `test_no_loop_home_run_state_read.py` adds the lines of every string constant to its docstring set, so any code line holding a string literal is exempt, and the forbidden patterns only occur inside string literals: a docstring-only rule names 29 lines in 18 files, the live test names 0. Behind it `cli/watch.py` reads `~/.bmad-loops` at three sites and ignores `BMAD_LOOP_HOME_ROOT`, which `cli/init.py` honours.

**Approach:** A fix under CAP-229 and CAP-227 (their amendments are in the memlog of 2026-11-10 and ride Story 114.1's render); no CAP minted. (1) `checkout_root()` in `cli/config.py` is the `__file__`-anchored half of `repo_root()` under its own name: it returns the ancestor only when it carries `_PACKAGE_SOURCE_RELPATH` and raises `RepoRootUnresolvedError` otherwise; it is separate on purpose, because tests monkeypatch `deploy.repo_root` into a sandbox and the scripts these loaders read belong to the checkout. (2) Replace `_docstring_lines` with real docstring positions (the first statement of a module, class or function when it is a string expression, and bare string-expression statements); then classify the 29 lines the honest rule names in 18 files: marshal's own journal and state filename constants and message strings get a tag saying they are marshal's files; real loop-home reads (`cli/status.py:782`, `:877`; `cli/benchmark.py:210`, `:285`; the supervisor's `state.json` reads; `cli/watch.py:694`) get the tag with their reason. A run-state read that CAP-227 says should move to the published plane is tagged as debt and carried as a `deferred:` entry in this spec's frontmatter; Story 116.5 runs the intake. `watch.py` reuses `cli/init.py`'s `_loop_home_root()`. The Doctor-file test (it climbs `MARSHAL_SRC.parents[3]` to reach pyforge-doctor) moves to its own `live_tree` module so the marshal-source guard stays in the package half.

Ledger key: `115-1-marshal-finds-the-checkout-and-the-loop-home-through-its-guarded-roots-and-the-guard-that-says-so-can-fire`. Type / Effort / Deps: fix / M / none.

## Boundaries & Constraints

**Always:**
- Each remaining loop-home read carries `CAP-4: loop-home FILE read` with a reason or a deferred-work id.
- Outside a source checkout the land loaders are absent and report MRS-LAND-011; the deploy loader's error folds into MRS-DEPLOY-027.

**Never:**
- No kill switch (operator ruling of 2026-11-10); no new `MRS-*` code.
- Never edit the deferred-work ledger from this story; the `deferred:` entry is the form spec-112-1 declares.
- Never change a test's assertion to make the guard pass.

## Acceptance Criteria

- **AC1 — No bare parent index remains in the two landing modules, code or docstring.**

  ```bash
  ! git grep -nE 'parents\[[0-9]+\]' -- src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py
  ```

  Expected: exit 0 (at `82a2b18828`: 5 hits).

- **AC2 — The checkout helper in both layouts: the editable anchor returns the repository; a module file outside any checkout makes both land loaders return None and the deploy loader raise the error `_repair_tier3_feed` folds into MRS-DEPLOY-027.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_checkout_root.py -q
  ```

  Expected: exit 0.

- **AC3 — The guard rejects its fixture: a temp module holding `home = Path.home() / ".bmad-loops" / slug` untagged yields one offender; the same line tagged, in a docstring or in `help=` yields none; the whole module passes on the tree.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_no_loop_home_run_state_read.py -q && pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_no_loop_home_run_state_read.py -q -k 'fires or tagged or docstring or help'
  ```

  Expected: exit 0; the second run selects 4 or more tests.

- **AC4 — The Doctor-file test sits in its own live_tree module, and the marshal-source guard reads only the package.**

  ```bash
  grep -q '^pytestmark = pytest.mark.live_tree' src/shared/packages/pyforge-marshal/tests/meta/test_no_loop_home_run_state_read_doctor_live_tree.py && ! grep -nE 'parents\[|pyforge-doctor' src/shared/packages/pyforge-marshal/tests/meta/test_no_loop_home_run_state_read.py && pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_no_loop_home_run_state_read_doctor_live_tree.py -q -m live_tree
  ```

  Expected: exit 0.

- **AC5 — watch builds no loop-home path from the home directory itself, and honours the override.**

  ```bash
  ! git grep -n 'Path.home() / ".bmad-loops"' -- src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py && pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_watch.py -q
  ```

  Expected: exit 0 (at `82a2b18828`: 3 hits).

- **AC6 — The existing landing and root tests pass unchanged.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_land.py src/shared/packages/pyforge-marshal/tests/unit/test_deploy.py src/shared/packages/pyforge-marshal/tests/unit/test_repo_root.py -q
  ```

  Expected: exit 0.

- **AC7 — Lint and types hold.**

  ```bash
  pixi run -e pyforge-guild lint-types
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-229 and CAP-227 (amended 2026-11-10). FR-136 body sentence and FR-249 (written by Story 114.1).

- Epic: Epic 115 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 115.1: Marshal finds the checkout and the loop home through its guarded roots, and the guard that says so can fire`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The Spec says what marshal is, and its roots come from one place.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda.

## Notes

- Deferred row this story's finding feeds (written by Story 116.5): DW-marshal-115-1-1 (`adapters/published_plane.py` is referenced only by a Doctor test).
- Story 115.4 follows this story because both edit `cli/land.py`, `cli/deploy.py` and `cli/watch.py`.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10) and the memlog entries of `spec-pyforge-marshal` came first; `SPEC.md` is rendered by Story 114.1.

## Gate findings (build, BUILD-1)

- 2026-11-11, `pixi run -e pyforge-guild deferred-work-check` (exit 2): `spec-frontmatter-only-deferral` for this spec's frontmatter `deferred:` row (`marshal watch` reads a loop run's last-fact time from the loop home's own bmad-loop journal), which has no twin in `pyforge-marshal/planning-artifacts/deferred-work-ledger.md`. Not fixed here, by plan: this story never edits that ledger; Story 116.5 (BUILD-17) owns it and runs the intake. The finding stays red at each wave gate until 116.5 lands the twin, unless the orchestrator moves the intake earlier.
