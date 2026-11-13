# Public contract — pyforge-testing-kit

Companion to `SPEC.md` (CAP-6; FR-253). It records the public surface of `pyforge.testing_kit`, the shared
test-support kit that eight stations' tests import: every module and its public names, the pytest fixtures and
markers, the run-dependencies, the members bound to this estate and the Python floor. The kit is routed `rebuild`
(ruling 3 of 2026-11-10): a second root that rebuilds it from this Spec rebuilds this surface.

The guard is `src/shared/packages/pyforge-testing-kit/tests/meta/test_public_contract.py`, a live-tree module (it
reads this file). It reads the kit's source with `ast` (nothing is imported) and its `pyproject.toml`, and fails
naming the item when the kit has a module, public name, fixture, marker, run-dependency or floor this file lacks, or
this file names one the kit lacks. A change to the kit's surface edits this file in the same change.

How the test reads this file: the `##` headings below; under `## Modules`, one `###` heading per module, written
`` ### `pyforge.testing_kit` `` or `` ### `pyforge.testing_kit.<module>` ``; under `## Fixtures and markers`, the
`### Fixtures` and `### Markers` headings; in each of those sections and under `## Run-dependencies` and
`## Estate-bound members`, the first backticked token of each line that starts with `- `; under `## Python floor`, the
first backticked version. Prose is not read. A public name is a module-level function, class or assignment whose name
does not start with `_`; for the package itself it is `__all__`.

## Modules

### `pyforge.testing_kit`

The package re-exports these names (`__all__`) from its submodules; `__version__` is `0.1.0`. `pyforge` is a PEP 420
namespace shared across stations, so the kit ships no `src/pyforge/__init__.py`.

- `BasePage` — from `page_object`.
- `CliResult` — from `cli_runner`.
- `CliRunner` — from `cli_runner`.
- `FrozenClock` — from `auth_http_time`.
- `LoopHome` — from `db_factory`.
- `MockGitHubAPI` — from `auth_http_time`.
- `MockRunner` — from `cli_runner`.
- `MockSupervisor` — from `db_factory`.
- `MockWorktree` — from `page_object`.
- `ORIGIN_MAIN` — from `branch_diff_guard`.
- `RunJournal` — from `db_factory`.
- `RunStateFactory` — from `db_factory`.
- `WorktreePage` — from `page_object`.
- `assert_flag_off_verb` — from `flags`.
- `changed_paths_since` — from `branch_diff_guard`.
- `commit_files` — from `branch_diff_guard`.
- `commit_subject` — from `branch_diff_guard`.
- `commits_since` — from `branch_diff_guard`.
- `diff_text_since` — from `branch_diff_guard`.
- `existed_at_ref` — from `branch_diff_guard`.
- `flag_states` — from `flags`.
- `flagd_tree` — from `flags`.
- `installed_flags` — from `flags`.
- `invoke_cli` — from `cli_runner`.
- `make_flag_provider_fixture` — from `flags`.
- `pyforge_import_offenders` — from `branch_diff_guard`.
- `record_factory` — from `db_factory`.
- `unsanctioned_commits` — from `branch_diff_guard`.

The `cfe_surface` names are not re-exported: import them from `pyforge.testing_kit.cfe_surface`.

### `pyforge.testing_kit.auth_http_time`

The auth/HTTP/time mock family, seeded from Marshal's `mock_github_api.py` and the timing surface of
`mock_supervisor.py`.

- `MockGitHubAPI` — an in-memory GitHub API: create, get, merge, list and update pull requests; get and delete
  branches.
- `FrozenClock` — a deterministic clock (`start`, `heartbeat_interval=5`, `idle_threshold=60`): `now`, `advance`,
  `advance_heartbeat`, `is_idle`. Tests advance time explicitly instead of sleeping.

### `pyforge.testing_kit.branch_diff_guard`

The git mechanics of the fleet's whole-branch diff-guard meta-tests; each guard's policy stays in the test that owns
it. Every `git` call runs through `pyforge.core.process.PosixProcess`. A base ref that does not resolve skips the
calling test (`pytest.skip`) instead of raising; an `origin/<branch>` base is read by its full refname.

- `ORIGIN_MAIN` — `"refs/remotes/origin/main"`, every guard's default base.
- `diff_text_since` — `(root, *, base=ORIGIN_MAIN, pathspec=None, require=None) -> str`: raw `git diff` text.
- `changed_paths_since` — `(root, *, base=ORIGIN_MAIN, pathspec=None, require=None, include_untracked=False,
  always_include=()) -> list[str]`: paths changed since `base`, sorted.
- `existed_at_ref` — `(root, path, *, ref=ORIGIN_MAIN) -> bool`: the path was already in `ref`'s tree.
- `pyforge_import_offenders` — `(paths, root) -> list[str]`: `"rel:lineno"` for each `import pyforge` / `from
  pyforge...` in the given Python files.
- `commits_since` — `(root, *, base=ORIGIN_MAIN, pathspec=None, no_merges=True) -> list[str]`: full SHAs on
  `base..HEAD` touching `pathspec`.
- `commit_subject` — `(root, sha) -> str`.
- `commit_files` — `(root, sha) -> list[str]`.
- `unsanctioned_commits` — `(root, *, pathspec, changelog_path, base=ORIGIN_MAIN) -> list[str]`: commits touching
  `pathspec` that are not a sanctioned retro (subject `retro:` or `retro(<scope>):` and `changelog_path` moved in
  the same commit), plus uncommitted dirty paths under `pathspec`.

### `pyforge.testing_kit.cfe_surface`

The conda-forge-expert surface, defined once (Story 83.19); marshal's dispatch keeps a runtime mirror that its unit
suite holds to these definitions. Estate-bound: see `## Estate-bound members`.

- `CFE_CHANGELOG_PATH` — `".claude/skills/conda-forge-expert/CHANGELOG.md"`.
- `CFE_SURFACE_PREFIXES` — the skill and scripts trees, as path prefixes.
- `CFE_SURFACE_FILES` — the CFE MCP server, `.claude/tools/conda_forge_server.py`.
- `CFE_GIT_PATHSPECS` — the whole surface as git pathspecs, for `unsanctioned_commits(pathspec=...)`.
- `is_cfe_surface_path` — `(path) -> bool`: the repository-relative path is on the surface.

### `pyforge.testing_kit.cli_runner`

The CLI-runner family, seeded from Marshal's `mock_runner.py`, and the real-CLI invoker.

- `MockRunner` — a story or CLI runner with deterministic verdicts: `run`, `get_result`, `set_verdict`,
  `add_finding`, `reset`.
- `CliRunner` — an alias of `MockRunner`.
- `CliResult` — frozen dataclass `(exit_code: int, output: str)`; `output` is stdout then stderr.
- `invoke_cli` — `(main, argv) -> CliResult`: runs a station's `main(argv)` in-process; the exit code is the return
  value or `SystemExit.code` read the way `sys.exit` reads it (`None` is 0, an int is itself, anything else is
  printed to stderr and is 1); ANSI colour codes are stripped from the output; any other exception propagates.

### `pyforge.testing_kit.db_factory`

The DB-factory family, seeded from Marshal's `mock_supervisor.py` and the store factories of its archived
`tests/conftest.py`.

- `MockSupervisor` — a stateful supervised-run factory: `attach`, `detach`, `send_heartbeat`, `detect_idle`,
  `escalate`, `get_escalations`, `set_heartbeat_callback`.
- `RunStateFactory` — an alias of `MockSupervisor`.
- `LoopHome` — `(path)`: a loop home on disk. `LoopHome.provision(path)` creates `.bmad-loop/tier3` and
  `.bmad-loop/state.json` under `path`; `teardown` removes the tree and refuses while work is in progress.
- `RunJournal` — an append-only journal with deterministic serialization: `append`, `read_all`.
- `record_factory` — `(**fields) -> dict`: a plain progress, claim or notice shaped record.

### `pyforge.testing_kit.flags`

The feature-flag family (spec-feature-flag-governance CAP-4, marshal Story 74.1): a flagged story runs with its flag
ON and again OFF through OpenFeature's client API and its `InMemoryProvider`.

- `F` — the `TypeVar` `flag_states` is typed with (bound to a callable).
- `ON` — `"on"`, the variant and pytest id of the ON state.
- `OFF` — `"off"`, the variant and pytest id of the OFF state.
- `FLAG_PROVIDER_FIXTURE` — `"flag_provider"`, the fixture's name.
- `installed_flags` — context manager `(values: Mapping[str, bool])`: installs an `InMemoryProvider` holding
  `values` as the default provider and puts the prior provider back on exit, even when the body raises; a value
  that is not a `bool` is refused with `ValueError`.
- `make_flag_provider_fixture` — `() -> fixture`: builds the `flag_provider` fixture (see `## Fixtures and markers`).
- `flag_states` — decorator `(key)`: runs the test twice, `key` ON then OFF (ids `on`, `off`).
- `flagd_tree` — `(tmp_path, flags: dict[str, str], *, name="flags.json") -> Path`: writes a flagd FILE tree in the
  shape of `src/platform/config/flags.json` (`flags` → key → `state`, `variants`, `defaultVariant`; no
  `metadata`); a non-dict mapping or a variant other than `on`/`off` is refused with `ValueError`.
- `assert_flag_off_verb` — `(main, verb, usage_code, *, args=()) -> CliResult`: asserts the OFF case of a flagged
  CLI verb: listed in `--help`, marked disabled on its own entry, and refusing with the station's usage code.

### `pyforge.testing_kit.page_object`

The page-object family, seeded from Marshal's `mock_worktree.py`.

- `BasePage` — a minimal page-object base: `is_valid`.
- `MockWorktree` — a navigable workspace without real git: `create`, `delete`, `is_valid`, `get_branch`.
- `WorktreePage` — a `BasePage` over a `MockWorktree`: `open`, `close`, `is_valid`.

## Fixtures and markers

The kit registers no pytest plugin (no `pytest11` entry point): nothing reaches a station's tests until the station
imports the kit.

### Fixtures

- `flag_provider` — built by `make_flag_provider_fixture()`. A station binds it once in its `conftest.py`
  (`flag_provider = make_flag_provider_fixture()`), or a test using it fails with `fixture 'flag_provider' not
  found`. It installs the `InMemoryProvider` for the test and yields the `{key: bool}` mapping it was given
  (`request.param` when parametrized, empty otherwise).

### Markers

- `parametrize` — pytest's own, applied by `flag_states(key)`: `flag_provider` parametrized indirectly with
  `{key: True}` then `{key: False}`, ids `on` and `off`.
- `usefixtures` — pytest's own, applied by `flag_states(key)` with `flag_provider`, so a decorated test needs no
  argument.
- `unit` — declared by the kit's own suite (`pyproject.toml`, `[tool.pytest.ini_options]`): a fast unit test.
- `live_tree` — declared by the kit's own suite: a module that reads the repository outside the kit. `-m "not
  live_tree"` is the package half, which runs with no host package on the path (CAP-7); `-m live_tree` is the
  live-tree half; `pyforge-testing-kit-test` runs both.

## Run-dependencies

Declared in `pyproject.toml` (`[project] dependencies`) and `pixi.toml` (`[package.run-dependencies]`). The
stdlib-leaf premise of Q-26 was retired on 2026-09-30 (marshal Story 74.1).

- `pyforge-core` — `branch_diff_guard` runs every `git` call through `pyforge.core.process.PosixProcess`.
  `pyforge-core` does not depend on the kit.
- `openfeature-sdk` — `>=0.10.0`; `flags` installs its `InMemoryProvider`, imported inside the functions that need it.

`pytest` is imported inside the functions that need it (`make_flag_provider_fixture`, `flag_states` and
`branch_diff_guard`'s skip on a missing base ref) and is not declared: every consumer is itself a pytest test
module, and a bare `import pyforge.testing_kit` imports neither `pytest` nor `openfeature`.

## Estate-bound members

- `pyforge.testing_kit.cfe_surface` — names this repository's conda-forge-expert surface (the skill tree, its
  scripts tree, the CFE MCP server and the CFE `CHANGELOG.md`). It stays A-only with that surface: a root without
  conda-forge-expert does not rebuild it (DW-marshal-118-1-1; its expiry is mason:S-39.2).

## Python floor

`3.14` — `requires-python = ">=3.14"` in `pyproject.toml`; the kit's code and suite run on the estate's Python 3.14.
