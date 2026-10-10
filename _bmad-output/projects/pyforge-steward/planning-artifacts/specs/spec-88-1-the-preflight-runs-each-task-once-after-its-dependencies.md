---
title: "88.1: The preflight runs each task once, after its dependencies"
type: 'fix'
created: '2026-10-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py
  - pixi.toml
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pr-preflight` runs a task's dependencies twice, at the same time, into the same directories. Line
numbers below are at `5f141b983e`.

- **How the lanes are built.** `preflight.py` `_expand_task` (:96-:117) walks `pr-preflight-lanes`. It turns each
  task's `depends-on` into leaf lanes (:110-:112). When the task also has a `cmd`, it keeps the task as a lane too
  (:113-:114).
- **How the lanes run.** The pool (:700-:745) submits lanes in list order and puts no order between them. Each lane
  runs `pixi run --frozen -e <env> <task>` (:438) without `--skip-deps` (pixi 0.81.0 has the flag). So pixi runs
  the task's dependencies again inside that lane, while the same dependencies also run as their own lanes.
- **Where it bites.** Three of the live graph's 36 lanes carry `depends-on`: `pages-check` → `pages-build` →
  `docs-site-install`, `docs-site-sidebar` (all in `site`), and `docs-site-validate-sidebar` →
  `docs-site-validate-sidebar-order`. In one preflight `docs-site-install` (`npm ci` in `docs-site/`) runs three times
  and `pages-build` twice. They run at once and write into one `docs-site/` and one `dist/`. That breaks Story 71.3's
  boundary that concurrent lanes share no mutable state.
- **What breaks.** One red lane stops the run and cancels the rest (Story 71.10), so the whole preflight is lost, not
  only the pages lanes.

**Evidence** (the herald-sidecar chain worktree, head `71f555eeb5`, `.steward/preflight-runs.jsonl`):
- **Run `ced93a76-f521-4f09-9a52-d6e28f7da11e`** (15:09:48Z): all four pages lanes started 4.4 s in, and `pages-check`
  went red (exit 1). Its kept lane log (`/tmp/pyforge-preflight-xdz34kng/pages-check.log`) shows pixi running
  `docs-site-install`, `docs-site-sidebar` and `pages-build` inside the lane and failing with "FAILED:
  pyforge-unifying-strategy: download size mismatch: pyforge-unifying-strategy_infographic_deck-2026-09-15.pptx".
- **Run `fdba8d13-1ab9-4b35-bf83-ad279cd09ffe`** (15:12:04Z): the same shape, 1.8 s in. The log
  (`/tmp/pyforge-preflight-e18_y4ey/pages-check.log`) ends "assemble_pages: collision at herald/".
- **Both runs** journal `detectors-ci`, `pyforge-doctor-scripts-test`, `pyforge-doctor-aggregate-scripts-test` and
  `pages-build` as `cancelled` with `cancelled_by: pages-check`. Both pushes then went out under
  `PYFORGE_PREFLIGHT_SKIP` (`.steward/preflight-skips.log`, 15:25:22Z and 15:31:15Z).
- `pixi run --frozen -e site pages-check` alone exits 0. That is also what CI runs (`docsite-check.yml`:57,
  `dashboard.yml`:59): one pixi invocation, each dependency once.

**Approach:** every task stays its own lane, and a lane waits for its dependencies.
- **The graph.** `list_preflight_lanes` keeps returning every task with a `cmd` reachable from `pr-preflight-lanes`.
  Each lane also carries the lanes its task depends on. These are read from the same `depends-on` entries, through any
  aggregate without a `cmd`, and in each dependency's declared environment. A task reached twice in the same
  environment is one lane.
- **The run.** A lane starts only after every lane it depends on has finished `ok`. It runs as
  `pixi run --frozen --skip-deps -e <env> <task>`, so pixi never repeats a dependency the runner has already run.
  Lanes with no order between them still run concurrently, bounded by `--jobs`. The reduced-suite argv (Story
  71.9) and the injected `subprocess_argv_for_lane` keep their shapes; no suite lane has `depends-on` today.
- **A failed dependency.** A red lane is reported once, by its own name, as today. Every lane that depends on it,
  directly or through another lane, never starts. Without `--keep-going` it is journaled `cancelled` with
  `cancelled_by` the red lane, as Story 71.10 journals any lane the stop cut off. Under `--keep-going` it is
  journaled `not-run` with `blocked_by` the red lane, and the independent lanes keep running. Either way the exit is 1,
  and only the red lane is printed as red.
- **Selection is unchanged.** `preflight_ci.select_lanes` (Story 71.2) still decides which lanes run from the
  workflows. `pages-check` is selected exactly when `docsite-check.yml`'s paths fire, and its dependencies with it,
  because a step's `depends-on` closure is what selects them (`preflight_ci._closure`, :287). If a selected lane's
  dependency is not selected, the dependency is added and the journal says why, so `--skip-deps` can never run a lane
  without its dependencies.
- **Why this shape, per the steward spine.**
  - **AD-1 (wrap, never reimplement):** the graph is read from `pixi.toml`'s `depends-on` and re-declared nowhere.
    pixi still runs every task, and `--skip-deps` only tells it not to repeat work the runner has already done.
  - **AD-8 (a lane's verdict is its exit code):** every task keeps its own exit code and journal row, so a dependency
    that fails is named as itself.
  - **The rejected alternative:** dropping the dependency lanes and letting the dependent lane run them inside one
    `pixi run` would still run a dependency twice whenever two selected lanes share it. It would also report a
    `docs-site-install` failure as a red `pages-check`, and it would change the lane set Story 71.1 and 71.2 journal.

Ledger key: `88-1-the-preflight-runs-each-task-once-after-its-dependencies`.
Type / Effort / Deps: fix / M / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-159 (FR-32; Epic 71): Story 71.1's lane list and journal,
  Story 71.2's selection, Story 71.3's concurrent lanes that "share no mutable state", Story 71.10's `cancelled`
  journaling and Story 71.11's process cleanup. This story fixes the realization of shipped behaviour, so it needs no
  new CAP and no SPEC.md change.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag: it restores intended behaviour, and a
  flag would keep the bug reachable.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-10 (preflight deps run twice). Operator
  ruling 2026-10-10, verbatim: "Mint both (Recommended)".

## Acceptance Criteria

- **AC1 — The live graph lists each task once, with its dependencies.** **Given** the real `pixi.toml` **When**
  `list_preflight_lanes` runs **Then** no `(task, environment)` appears twice. `pages-check` depends on
  `pages-build`, `pages-build` on `docs-site-install` and `docs-site-sidebar`, and `docs-site-validate-sidebar` on
  `docs-site-validate-sidebar-order`. Every other lane has no dependency.
- **AC2 — Each task runs once, after its dependencies.**
  - **Given** a fixture `pixi.toml` with `a` (cmd) depending on `b` and `c` (cmds), `b` depending on `d`, and an
    independent `e`, and a recording fake runner, **When** the preflight runs with `--jobs 4`, **Then** each of
    `a`, `b`, `c`, `d`, `e` runs exactly once.
  - `d` finishes before `b` starts, and `b` and `c` finish before `a` starts. `e` overlaps the others.
  - The journal line has one row per task.
- **AC3 — The subprocess argv skips pixi's own dependency run.** **Given** the default subprocess lane **When** it
  builds its argv **Then** the argv is `pixi run --frozen --skip-deps -e <env> <task>` for every lane.
- **AC4 — A failed dependency is reported once and stops its dependents.**
  - **Given** AC2's graph and `d` faked to exit 1, **When** the preflight runs, **Then** it exits 1, `d` is the only
    lane journaled and printed `red`, and `b` and `a` never start.
  - Without `--keep-going`, `b` and `a` are journaled `cancelled` with `cancelled_by: d`.
  - With `--keep-going`, they are journaled `not-run` with `blocked_by: d`, and `c` and `e` still run `ok`.
- **AC5 — Selection is unchanged.** **Given** the fixture diffs in `tests/unit/test_preflight_selection.py` **When**
  lanes are selected **Then** every expected set is unchanged. `PAGES_CHECK_LEAVES` stays `{"pages-check",
  "pages-build", "docs-site-install", "docs-site-sidebar"}` and is selected exactly when `docsite-check.yml`'s paths
  fire (the `docs/dreams/` and `docsite/` fixtures). A new assertion pins the dependency edges among those four lanes
  (AC1). A selected lane whose dependency the workflows do not select pulls the dependency in, and the journal records
  why.
- **AC6 — The pages lanes no longer collide.** **Given** a fake runner that fails any lane started while another lane
  writing the same scratch marker is still running (the `docs-site/` and `dist/` shape) **When** the four pages lanes
  run **Then** they pass, and the same fake fails against the old flattening (mutation).
- **AC7 — Unchanged otherwise.** Story 71.3's install phase, per-lane scratch, `--jobs` bound and service mutex,
  Story 71.9's reduced suite lanes, Story 71.10's `cancelled_by`, Story 71.11's process cleanup and the exit codes
  0 / 1 / 2 / 130 keep their existing tests green with no change beyond the new dependency fields. A `depends-on`
  cycle is still exit 2.
- **AC8 — Mutation.**
  - Dropping `--skip-deps` from the argv fails AC3.
  - Starting a lane before its dependencies finish fails AC2.
  - Letting a dependent start after a red dependency fails AC4.
  - Emitting a task twice fails AC1.

## Boundaries & Constraints

**Always:**
- Read the graph only from `pixi.toml`'s `depends-on` (AD-1). Never add a second list of dependencies in steward
  code.
- Keep one lane per task and environment, each with its own exit code and journal row (AD-8).
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped: `spec-pyforge-steward`, `spec-pyforge-core` (it co-governs every station's `src/`) and any co-governor
  `spec-surface-check` names (AGENTS.md pre-PR item 5).

**Never:**
- Never skip a lane CI's rules select. Never let a lane run without its dependencies having run green in the same
  preflight.
- Never serialize lanes that have no order between them. Concurrency stays bounded only by `--jobs` and the service
  mutex.
- Never change `pixi.toml`'s tasks or their `depends-on` to work around this.
- Never change `pr-preflight`'s command line, the `pre-push` hook or `PYFORGE_PREFLIGHT_SKIP`.

**Residual risk:** a lane outside the preflight, run by hand while a preflight runs, can still write into the same
`docs-site/` or `dist/`. That sharing is outside this runner.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-10 (preflight deps run twice) entry.
- Epic: Epic 88 (a new fix epic, because Epic 71, which shipped CAP-159, is `done`).
- Ledger key: `88-1-the-preflight-runs-each-task-once-after-its-dependencies`.
- Ledger status at mint: `backlog`.
- Deps: none.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-guild pr-preflight` on a branch whose diff touches `docs/` or `docsite/`: the journal row for `pages-check` starts after `pages-build` ends, `pages-build` after `docs-site-install` and `docs-site-sidebar`, and `pages-check`'s lane log shows no `docs-site-install` or `pages-build` task header.
- Mutation: drop `--skip-deps` from the default argv and re-run the station suite; AC3 fails. Restore it.
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 after the memlog reconciles and scoped stamps.
