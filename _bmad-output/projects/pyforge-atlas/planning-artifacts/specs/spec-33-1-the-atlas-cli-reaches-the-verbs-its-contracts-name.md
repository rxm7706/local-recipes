---
title: '33.1: The atlas CLI reaches the verbs its contracts name, from any directory'
type: 'fix'
created: '2026-10-18'
status: 'done'
baseline_revision: '13f2df37781f49457349d4317b4034d342da6591'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/__main__.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/parity.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/session.py
  - .claude/skills/pyforge-atlas/0.1.0/pyforge-atlas/SKILL.md
  - .claude/skills/bmad-agent-atlas/customize.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the atlas CLI reaches none of the verbs its skill, its persona, its parity gate and its MCP tool
inventory name, and the one form that works reads the wrong Kedro project from the repo root. Line numbers below are
at `13f2df3778`.

- **What happened.** On 2026-10-17 the operator asked for a data refresh and ran the SKF skill's quick-start command,
  `pixi run -e pyforge-atlas pyforge atlas run`, from the repo root. It exited 2: `Error: Got unexpected extra
  argument (run)`. The skill's `pyforge atlas catalog list` exits 2 the same way (`Got unexpected extra arguments
  (catalog list)`).
- **Cause 1: the binary is `run`.** `pyforge.atlas.__main__.main` (:67-:80) calls `configure_project("pyforge.atlas")`
  and returns `find_run_command(package_name)(*args, **kwargs)`. With no project `cli.py` and no `project` plugin
  entry point, `find_run_command` returns `kedro.framework.cli.project.run` itself (kedro 1.6.0,
  `framework/cli/utils.py:378`-`:406`). So `run` is an unexpected positional, `ipython` and `package` are unreachable,
  and a bare `pyforge atlas` starts a whole-`__default__` run.
- **Cause 2: four contracts describe a different CLI.**
  - `.claude/skills/pyforge-atlas/0.1.0/pyforge-atlas/SKILL.md` :40-:41, :59, :63, :117-:118 name `pyforge atlas run
    --pipeline <name>` and `pyforge atlas catalog list`.
  - `.claude/skills/bmad-agent-atlas/customize.toml` :38, the persona's RUN menu, names `pyforge atlas run --pipeline
    <name>`.
  - The FR-155 parity gate, `mcp/parity.py` (added 2026-09-10, `5bdfea9083`), takes its verbs from
    `__main__.discover_cli_verbs`, which reads `kedro.framework.cli.project.project_group.commands` (`ipython`,
    `package`, `run`). It checks that a declared verb exists in that group, never that the binary reaches it, so it
    has passed since that day.
  - `mcp/tools.py` `TOOL_SPECS` (:33-:66) declares each `run_*_pipeline` tool's CLI as `["run", "--pipeline", <name>]`.
- **Cause 3: from the repo root a run reads the repo root's `conf/`.** `KedroSession.create` takes its project path
  from `find_kedro_project(Path.cwd()) or Path.cwd()` (`framework/session/session.py:110`-`:111`). Measured from the
  repo root: `find_kedro_project` returns `None`, so the project path is the repo root and the conf source is the repo
  root's own `conf/` (one `base/knowledge.yml`), not atlas's catalog. Every real run today goes through a pixi task
  whose `cwd` is `src/shared/packages/pyforge-atlas` (`pyforge-atlas-bootstrap`, `viz-build`). The MCP face pins the
  member dir already: `mcp/session.py` :26 `PROJECT_ROOT`, `bootstrap_project(root)`, `KedroSession.create(
  project_path=root)`. Measured 2026-10-17 23:04, the operator's bare `pixi run -e pyforge-atlas pyforge atlas` from
  the repo root: `MissingConfigException: Given configuration path either does not exist or is not a valid directory:
  <repo>/conf/local`, raised in `context._get_catalog` before any node ran. An older root-relative write survives as
  the gitignored `<repo>/data/raw/` (`.staleness.json` sidecars for `vulnerability_basilisk_raw`,
  `vulnerability_basilisk_detail_raw` and `vcs_migration_detail_raw`, dated 2026-08-29); left in place, not this
  story's to delete.
- **Cause 4 (healed on the way): `--pipeline` is deprecated.** kedro 1.6.0's `run` emits a
  `KedroDeprecationWarning` for `--pipeline` and points at `--pipelines` (`framework/cli/project.py:280`-`:286`).
- **Latent test.** `test_main_version.py::test_version_not_first_token_does_not_short_circuit` asserts exit 2 for
  `main(["run", "--version"])` and says Click raised "No such option". It passed because `run` was the unexpected
  token, not because of `--version`.

**Operator rulings (2026-10-18, AskUserQuestion, verbatim choices):** "Fix the binary (Recommended)" over a docs-only
fix; "Print help (Recommended)" for a bare `pyforge atlas`.

**Approach:**
1. **Dispatch to the group.** `main` keeps its argv resolution and the first-token `--version` intercept unchanged.
   Below it, `bootstrap_project(PROJECT_ROOT)` (which configures the dotted `pyforge.atlas` package from `[tool.kedro]`
   and returns `ProjectMetadata`), then `project_group(*args, **kwargs)` with `obj=metadata` and `prog_name=
   "pyforge-atlas"` (`setdefault`, so a caller's own wins). `PROJECT_ROOT` is `Path(__file__).resolve().parents[3]`,
   the member dir, equal to `mcp/session.py`'s; a test pins the equality.
2. **Pin the cwd for the command only.** `os.chdir(PROJECT_ROOT)` before the dispatch and back to the caller's cwd in a
   `finally`, so `KedroSession.create` finds atlas's project from anywhere and an in-process caller (a test, a REPL) is
   left where it was. A relative path a user passes to `run` (`--config`, `--conf-source`) therefore resolves against
   the member dir; the README says so.
3. **Declared argv.** `TOOL_SPECS` declares `["run", "--pipelines", <name>]`; the parity meta-test asserts
   `--pipelines`.
4. **Tests.** A new `tests/unit/test_main_dispatch.py` replaces every `project_group` command's callback with a
   recorder and, from a foreign cwd, asserts for each verb `discover_cli_verbs()` returns that `main([verb])` exits 0,
   reaches that command, passes metadata for `pyforge.atlas` at `PROJECT_ROOT` as `obj` and runs it with the member
   dir as cwd; that every `TOOL_SPECS` argv parses through `main` to its pipeline; that the caller's cwd comes back;
   that a bare `main([])` lists the three verbs, runs nothing and exits 2 (Click >= 8.2 for a group with no
   command); and, in a real subprocess from an empty temp dir, that the bare CLI lists the verbs and writes nothing.
   `test_main_version.py`'s `run --version` test also asserts Click's `No such option '--version'` message.
5. **Docs.** The README gains a `## Run` section (the grammar, any cwd, `--pipelines`, datasets via MCP
   `list_atlas_datasets`). The skill's Quick Start, Common Workflows, CLI and Architecture text name the real grammar
   and drop `catalog list`; its stale `[SRC:…]` line citations into `__main__.py` and `mcp/tools.py`, and
   `provenance-map.json`'s `source_line`s, are re-pointed to the current lines. The persona's RUN prompt names
   `pyforge atlas run --pipelines <name>`. In-package text that still taught `kedro run --pipeline` (three
  `dashboard/app.py` page notes, a `dashboard/data.py` comment, `pipelines/semantic_packages/README.md`, a
  `tests/unit/mcp/test_audit_mapping.py` comment) names `pyforge atlas run --pipelines` (review should-fix 6). The
  README also says the front door (`pyforge-core`'s `PosixProcess`: captured output, `stdin=DEVNULL`) makes
  `pyforge atlas ipython` non-interactive and buffers a long run's log, so the shell and streamed runs use the
  `pyforge-atlas` binary directly; the skill's CLI block says the same.
6. **The real-process test cannot become a data refresh.** It runs with an unknown `KEDRO_ENV` and a 60 s timeout, so a
   regression back to a bare whole-DAG run fails at config load before any node runs (review should-fix 2; measured
   under the `find_run_command` mutation: failed in 5 s, no `data/` written).

Ledger key: `33-1-the-atlas-cli-reaches-the-verbs-its-contracts-name`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-9** (agents trigger and read the pipeline natively): its intent, an agent runs a named
  pipeline and reads the result, now holds on the CLI face as on the MCP face. A `fix`, so no CAP is minted; CAP-9's
  text does not change. Recorded as a decision on the Spec's memlog; `SPEC.md` is not hand-edited.
- **canopy:FR-13** (`pyforge <station> …` reaches the station binary's behaviour, dispatch only): unchanged;
  `pyforge-core` still forwards argv to `pyforge-atlas`, which now has the verbs.
- **AD-23** (one execution plane): the CLI and the MCP face now resolve the same project root.
- **No flag.** `spec-feature-flag-governance` Q1: a `fix` needs no flag; this spec carries neither a `flag:` block nor
  a `flag-exempt:` value, like the other atlas fix specs (28.1, 29.1, 31.1, 32.1).
- **Origin.** `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-18 entry (the atlas CLI has no verbs).

## Acceptance Criteria

- **AC1 — Every counted verb is reachable.** For each verb in `discover_cli_verbs()` (`ipython`, `package`, `run`),
  `main([verb])` exits 0 having invoked that command of `project_group` with `obj.package_name == "pyforge.atlas"`,
  `obj.project_path == PROJECT_ROOT` and `Path.cwd() == PROJECT_ROOT` during the call, started from a foreign cwd.
  Mutation: `main` back on `find_run_command` fails it (measured: 14 failures).
- **AC2 — The cwd pin is the command's only.** After `main(["run"])` returns, `Path.cwd()` is the caller's. Mutation:
  dropping `os.chdir(PROJECT_ROOT)` fails AC1's and AC2's cwd assertions (measured: 4 failures).
- **AC3 — One project root.** `__main__.PROJECT_ROOT == mcp.session.PROJECT_ROOT`, and it holds
  `conf/base/catalog.yml`.
- **AC4 — Declared argv parses.** Every `TOOL_SPECS` entry with a `cli` parses through `main` to `run` with
  `pipelines == [<name>]`; every `run_*_pipeline` tool declares `--pipelines`. Mutation: one tool back on
  `--pipeline` fails 2 tests, one in the parity meta-test and one in `test_main_dispatch.py`.
- **AC5 — A bare call runs nothing.** `main([])` and `python -m pyforge.atlas` from an empty temp dir list `ipython`,
  `package` and `run`, invoke no command, exit 2, and the temp dir stays empty.
- **AC6 — `--version` unchanged.** `test_main_version.py` passes unchanged except the `run --version` test, which also
  asserts `No such option '--version'` in stderr; `python -m pyforge.atlas --version` prints one line.
- **AC7 — A real run from the repo root.** `pixi run --frozen -e pyforge-atlas pyforge atlas run --pipelines seed_gaps`
  from the repo root runs atlas's own catalog and creates no new path at the repo root. *(Amended 2026-10-18 after
  review: the worktree's member `data/` is empty, and `seed_gaps` reads datasets other pipelines produce.)* Measured
  from the worktree root twice: with the default data root it raised `DatasetError: vulnerability_cwe_categories`, an
  atlas catalog entry under the member `data/` (the right project, no upstream data); with
  `PYFORGE_ATLAS_DATA_ROOT` set to a scratch copy of the primary checkout's member `data/` it exited 0, completed 4 of
  4 tasks, wrote the four `derived/seed_gaps_*` reports there, and emitted no `KedroDeprecationWarning`; `git status
  --porcelain --ignored` was byte-identical before and after. The default-root attempt left only the run-admission
  lock files under the member `data.locks/` (gitignored), nothing at the repo root.
- **AC8 — Docs name what exists.** No file under `.claude/skills/pyforge-atlas/`, `.claude/skills/bmad-agent-atlas/` or
  `src/shared/packages/pyforge-atlas/README.md` names `run --pipeline ` (singular) or `catalog list`; the README's
  `## Run` section and the skill's CLI block list `run --pipelines`, `run`, `ipython`, `package`; every skill
  `[SRC:…:Ln]` citation into `__main__.py` and `mcp/tools.py` lands on the named symbol.
- **AC9 — Gates.** `pixi run --frozen -e pyforge-atlas pyforge-atlas-test`, `kedro-test` and `kedro-catalog-check`
  exit 0; the atlas coverage gate exits 0; `pixi run --frozen -e pyforge-guild lint-types` exits 0; the planning
  detectors and `detectors-ci` exit 0; a full `pr-preflight` exits 0.
- **AC10 — Reconciled.** Every Spec `spec-surface-check` names gets a memlog surface-reconcile entry naming its paths
  and this story, and is stamped scoped, one `--spec` each; `spec-surface-check` then exits 0, re-run after the last
  edit.

## Boundaries & Constraints

**Always:**
- Dispatch to Kedro's own `project_group`, the group the parity gate reads. Read every verdict from its exit code.

**Never:**
- Never reimplement Kedro's routing, add a verb, or widen the surface to Kedro's global or plugin commands (that would
  put verbs on the binary the parity gate does not count).
- Never change a pipeline, a dataset, a catalog entry, an MCP tool's behaviour or the `--version` intercept.
- Never hand-edit `SPEC.md` or `sprint-status-ledger.yaml`.

**Residual risk:**
- **Relative paths given to `run`.** `--config ./x.yml`, a relative `--conf-source` or a relative `PYFORGE_ATLAS_*`
  value now resolves against the member dir, not the caller's cwd; the README states it. No caller in the repo passes
  one.
- **Outside the checkout.** `bootstrap_project` needs the member dir's `pyproject.toml`; the package is repo-local by
  design (`mcp/session.py`), so a wheel or conda install outside the checkout raises before `--help`. The README says
  "from any directory of the repo checkout". `bootstrap_project` also prepends the member `src/` to `sys.path` and
  `PYTHONPATH` in the caller's process (kedro's own behaviour).
- **The decks.** The atlas deck family (`presentations/pyforge-atlas/project/*.html`) still shows the old grammar; it
  changes only through the Design bridge, so it is herald's row `DW-herald-atlas-33-1-1` (the `DW-herald-102-3-1`
  precedent).
- **The skill is SKF-compiled.** The edit is by hand, mirroring what a re-compile from the README's new `## Run`
  section would produce; `provenance-map.json`'s `source_line`s are re-pointed so `skf-audit-skill` reads current lines.

## I/O & Edge-Case Matrix

| Invocation | Today (`13f2df3778`) | After |
|---|---|---|
| `pyforge atlas run --pipelines core` (repo root) | exit 2, unexpected extra argument `run` | runs `core` against atlas's `conf/`, cwd restored |
| `pyforge atlas --pipelines core` (repo root) | `MissingConfigException` on `<repo>/conf/local` (the repo root's `conf/`) | exit 2, `No such option` (group options are `--help` only) |
| `pyforge atlas` (bare) | starts a whole-DAG run (from the repo root: `MissingConfigException`, measured) | prints the three commands, exit 2 |
| `pyforge atlas ipython` / `package` | exit 2, unexpected extra argument | Kedro's command, member dir as cwd |
| `pyforge atlas --version` | one line | one line |
| `pyforge atlas run --version` | exit 2 (`run` unexpected) | exit 2, `No such option '--version'` |
| `pyforge atlas catalog list` | exit 2 | exit 2, `No such command 'catalog'` (datasets: MCP `list_atlas_datasets`) |
| `main([...])` in-process | cwd unchanged | cwd unchanged |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-9, a `fix`, so no CAP is minted and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-18 entry (the atlas CLI has no verbs).
- Epic 33 / Story 33.1 in `planning-artifacts/epics.md`; ledger keys `epic-33`, `epic-33-retrospective`,
  `33-1-the-atlas-cli-reaches-the-verbs-its-contracts-name`.

## Spec Change Log

- 2026-10-18: minted with the implementation (hand-built on branch `chain-atlas-cli-verbs-2026-10-17`).
- 2026-10-18: independent review FAIL (1 blocker, 5 should-fix, 8 nits). Resolved: AC7 measured and amended (blocker);
  the real-process test pinned to an unknown `KEDRO_ENV` with a timeout (should-fix 2); the README's relative-path and
  checkout-only sentences (3, nit 8); the front door's non-interactive `ipython` documented (4); Epic 33's prose names
  Epic 2 / Story A1 for the CLI (5); in-package `kedro run --pipeline` text fixed and the decks filed as
  `DW-herald-atlas-33-1-1` (6); the skill notes its hand re-pointed citations (nit 7); a comment on `obj` (nit 9);
  AC4's attribution (nit 10); the Epic's Surface line (nit 11); the verb parametrize reads `project_group.commands`
  with one test tying it to `discover_cli_verbs()` (nit 13). Not changed: the memlog decision's typo (nit 12;
  memlogs are append-only).
- 2026-10-18: re-review PASS (no blocker or should-fix); its three new nits fixed (the skill's re-point note names this
  story's landing tree, Epic 33's Then clause matches AC7, marshal-policy `"33"` lists herald's deferred-work
  ledger). Promoted to `done`; the full `pr-preflight` runs on this tree before push.
