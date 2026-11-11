# Public contract — pyforge-core

Companion to `SPEC.md` (spec-pyforge-core:CAP-12; decision D1 of the 2026-11-10 cutover readiness design pass). It
names what the leaf `pyforge.core` offers a caller: every module and the capability that governs it, every public name
a station may import, the environment variables the leaf reads or sets, the feature-flag keys it reads, the exit codes
it defines, its entry points and its Python floor, so a second root can rebuild the leaf from Dream, memlog and Spec.
The leaf itself is spec-pyforge-core:CAP-1: pure stdlib at import, no third-party runtime dependency, and no import of
any `pyforge.<station>`.

The guard is `src/shared/packages/pyforge-core/tests/meta/test_public_contract.py`, a `live_tree` module of the core
suite. It derives each inventory from the source (an AST scan of `src/pyforge/core/*.py` and the package's
`pyproject.toml`) and compares it with this file both ways: an item the source has and this file lacks fails as
unlisted, and an item this file names and the source lacks fails as missing from the source. Each message names the
item. A change that adds, removes or renames a module, a public name, an environment variable, a flag key, an exit
code or an entry point changes this file in the same change.

How the test reads this file: the module headings under *Modules*, and in each module section the backticked tokens
of the paragraph that opens `Public names:` and of the one that opens `Estate-bound constants:`; the backticked cells
of the table rows under *Environment variables* (variable, role, modules), *Feature-flag keys* (key, modules), *Exit
codes* (name, value, modules) and *Entry points* (group, name, target); the backticked floor under *Python floor*.
Every module section opens a `Governed by:` paragraph, every capability this file cites in the qualified form must be
one its Spec defines, and an estate-bound constant must be a public name of its module. Other prose is not read.

A public name is a name a module binds at top level (a `def`, a `class`, an assignment or a `type` alias, also inside a
top-level `if`, `try` or `with`) with no leading underscore. A name a module imports is not one of its public names,
and no module declares `__all__`.

## Modules

One section per module of `pyforge.core`, `__init__` excepted. The primitives this Spec extracts come first
(spec-pyforge-core:CAP-2 to spec-pyforge-core:CAP-6), then the front door, then the modules the leaf hosts for another
Spec, each admitted by that Spec's own story as a shared grammar, reader or seam (the Constraint *No new primitive
earns a place on one caller*). A second implementation of an extracted primitive is spec-pyforge-core:CAP-7's to
refuse.

### `pyforge.core.atomic_write`

Governed by: spec-pyforge-core:CAP-2.

The one tmp-in-dir plus `os.replace` write every station calls, text or bytes, with the durability each retired copy
relied on.

Public names: `atomic_write`, `atomic_write_bytes`, `atomic_write_text`.

### `pyforge.core.verdict`

Governed by: spec-pyforge-core:CAP-3.

The verdict-lattice bookkeeping: `Lattice` holds one station's rank order and exit-code domain and states a narrowing
as a subset of another lattice's domain; `dispatch_exit_code` projects an exception to an exit code through a
station's own most-specific-first table. The values belong to each station (see *Exit codes*).

Public names: `Lattice`, `dispatch_exit_code`.

### `pyforge.core.report`

Governed by: spec-pyforge-core:CAP-4.

The base report envelope schema every station's report schema extends, and the pure dict merge that composes them.

Public names: `BASE_ENVELOPE_SCHEMA`, `compose`.

Estate-bound constants: `BASE_ENVELOPE_SCHEMA`, whose `$id` is `urn:local-recipes:pyforge-core:base-envelope-schema`,
in this estate's urn:local-recipes: namespace.

### `pyforge.core.errors`

Governed by: spec-pyforge-core:CAP-5.

The shared exception root: `except PyforgeError` catches every station error that re-parents to it.

Public names: `PyforgeError`.

### `pyforge.core.process`

Governed by: spec-pyforge-core:CAP-6.

The one sanctioned subprocess seam, marshal's `ProcessPort` design: `run` never raises on a non-zero exit, and
`PosixProcess` is the stdlib implementation every routed station uses.

Public names: `BytesProcessResult`, `PosixProcess`, `ProcessError`, `ProcessPort`, `ProcessResult`.

### `pyforge.core.dispatch`

Governed by: spec-pyforge-unifying-strategy:CAP-5 and spec-pyforge-core:CAP-11; the bare-noun aliases are
spec-pyforge-marshal:CAP-192's, and the front-door kill switch is spec-feature-flag-governance:CAP-7's.

The `pyforge <station> <noun> <verb>` front door: it maps a station token to that distribution's primary console script
and forwards the rest of argv through `PosixProcess`; a roster station that is not installed is refused naming the
environment it runs in. No station duty logic lives here.

Public names: `DispatchError`, `EXIT_NOT_FOUND`, `EXIT_USAGE`, `FRONT_DOOR_ENVIRONMENT_FLAG_KEY`, `NOUN_ALIASES`,
`PREPARATORY_UNINTROSPECTABLE`, `SKIP_DISTRIBUTIONS`, `dispatch_argv`, `main`, `primary_console_script`,
`resolve_script_map`, `script_map_from_installed`, `script_map_from_packages_root`, `scripts_from_pyproject`,
`station_token_from_dist_name`.

Estate-bound constants: `resolve_script_map`, whose packages-root arithmetic holds this estate's layout: with no script
map, no packages root and no installed station distribution, it takes `Path(__file__).resolve().parents[4]` as the
packages root, and only when that directory is named packages (the `src/shared/packages/` tree).

### `pyforge.core.roster`

Governed by: spec-pyforge-steward:CAP-137.

The one Guild station roster, short form, and the mechanical long form used for paths, packages and pixi
environments.

Public names: `STATIONS`, `long_form`.

### `pyforge.core.hooks`

Governed by: spec-pyforge-unifying-strategy:CAP-18.

The one hook-spec and plugin-registration shape: the entry-point group `pyforge.core.hooks`, the registry that loads
it, the in-tree dummy plugin for the example spec `pyforge.core.example`, and the owner-matched verdict publish that
refuses a second verdict.

Public names: `DummyPlugin`, `ENTRY_POINT_GROUP`, `EXAMPLE_HOOK_OWNER`, `EXAMPLE_HOOK_SPEC`, `EXAMPLE_HOOK_SPEC_NAME`,
`HOOK_POINTS`, `HookPlugin`, `HookSpec`, `NOT_PLUGIN_SURFACES`, `PluginError`, `PluginRegistry`, `SecondVerdictError`,
`publish_verdict`.

### `pyforge.core.client`

Governed by: spec-pyforge-unifying-strategy:CAP-6.

The host-relative station API client (stdlib only) a portal or CLI reaches a station service through, carrying the
caller's identity.

Public names: `API_VERSION_HEADER`, `PyForgeStationClient`, `StationClientError`, `Transport`, `form_urlencode`,
`parse_request_path`, `urllib_request`.

### `pyforge.core.assertion`

Governed by: spec-pyforge-unifying-strategy:CAP-6.

The host-mint assertion client: the CLI never signs; it posts the caller's IdP bearer to the host mint, which signs the
audience-bound assertion.

Public names: `ALG`, `AUDIENCE_PREFIX`, `CLAIM_AUD`, `CLAIM_DELEGATED_BY`, `CLAIM_EXP`, `CLAIM_IAT`, `CLAIM_ROLES`,
`CLAIM_SUB`, `DELEGATED_BY`, `HostMintClient`, `HostMintError`, `MAX_TTL_SECONDS`, `Transport`.

### `pyforge.core.station_port`

Governed by: spec-pyforge-unifying-strategy:CAP-6.

The in-process station API port: co-located portals reach a station through a registered invoker instead of HTTP
loopback, unless `STATION_REMOTE` selects the HTTP path.

Public names: `InProcessInvoker`, `STATION_REMOTE_ENV`, `StationPortError`, `invoke_in_process`, `is_station_remote`,
`register_in_process_invoker`, `replace_in_process_invoker`, `reset_in_process_invoker`.

### `pyforge.core.flags`

Governed by: spec-feature-flag-governance:CAP-5 and spec-feature-flag-governance:CAP-7, with
spec-pyforge-unifying-strategy:CAP-13.

The fleet-wide CLI flag contract: the flag tree's per-environment overlays and metadata checks, `read_boolean` (the one
optional dynamic OpenFeature load of spec-pyforge-core:CAP-1, falling back to the leaf's own structural read), the
`require` / `disabled_help` gate a station's CLI wraps, and `kill_switch_on`, the reader of a retrofit kill switch. It
resolves the tree through `pyforge.core.cutover_root.resolve_flags_path` and defines no exit code.

Public names: `CLEANUP_DAYS`, `DEFAULT_ENVIRONMENT`, `ENVIRONMENTS`, `ENV_ENVIRONMENT`, `FlagCleanupDateError`,
`FlagClockMismatchError`, `FlagConfigError`, `FlagMetadataDateError`, `FlagMetadataError`, `FlagMetadataMissingError`,
`FlagMetadataNotAStringError`, `FlagOff`, `FlagTreeError`, `METADATA_FIELDS`, `OVERLAYS_FILE_NAME`,
`OverlayDocumentError`, `OverlayNotAVariantError`, `OverlayUnknownKeyError`, `OverlayUnknownVariantError`,
`UnknownEnvironmentError`, `check_environment`, `check_metadata`, `compose`, `current_environment`, `disabled_help`,
`kill_switch_on`, `load_overlays`, `overlays_path_for`, `read_boolean`, `render`, `require`.

### `pyforge.core.cutover_root`

Governed by: fnd:CAP-8 and spec-pyforge-core:CAP-13.

The reader of `pyforge.cutover_root`, the writer lock and root of record, and the one function that answers the root
of record and its forge slug: `root_of_record` reads the tree as the current environment renders it, or answers the
default root with source `default` when no tree is in reach; `forge_slug_for` maps a root to its slug with no I/O.
`resolve_flags_path` is the one tree resolution `pyforge.core.flags` uses too.

Public names: `CUTOVER_FLAG`, `CUTOVER_VARIANTS`, `CutoverRootError`, `DEFAULT_CUTOVER_ROOT`, `ENV_FLAGS_PATH`,
`FORGE_SLUGS`, `LOCAL_DEV_RELATIVE`, `RootOfRecord`, `forge_slug_for`, `read_cutover_root`, `resolve_flags_path`,
`root_of_record`.

Estate-bound constants: `LOCAL_DEV_RELATIVE` (`src/platform/config/flags.json`, looked for in the working directory and
each parent), and `FORGE_SLUGS`, the one home of the slug table (`rxm7706/local-recipes` for local-recipes,
`rxm7706/python-foundry` for foundry).

### `pyforge.core.landing_evidence`

Governed by: spec-pyforge-marshal:CAP-126, amended by spec-pyforge-marshal:CAP-247 and spec-pyforge-marshal:CAP-255.

The one shared grammar of landing-evidence shapes (merge-subject templates, branch-name grammars, the recovery-landing
convention) that doctor and marshal both classify landings with, so neither imports the other.

Public names: `BranchDerivedShape`, `DISPATCH_BRANCH_PREFIX`, `LandingEvidenceMatch`, `LandingEvidenceShape`,
`PRE_CONVENTION_RECOVERY_COMMITS`, `RECOVERY_LANDING_CONVENTION`, `StoryKeyRef`, `classify_branch_name`,
`classify_commit`, `classify_merge_subject`, `conformance_fixtures`, `merged_story_keys`,
`parse_bmadloop_branch_name`, `parse_bmadloop_merge_subject`, `parse_github_pr_merge_subject`,
`parse_land_branch_name`, `parse_recovery_commit_sha`, `parse_recovery_commit_subject`, `parse_station_branch_name`,
`parse_story_direct_commit_subject`, `parse_templated_merge_subject`.

Estate-bound constants: `PRE_CONVENTION_RECOVERY_COMMITS`, the recovery commits of this repository's history that
predate the convention, recognized by abbreviated sha.

### `pyforge.core.preserve_refs`

Governed by: spec-pyforge-marshal:CAP-287, with spec-pyforge-steward:CAP-165.

The one grammar for preserved-work refs: render and parse of the `refs/tags/preserve/` and `refs/tags/archive/` names,
the snapshot commit, the annotated tag writer, the content gate, the one-refspec push, and the readers every preserve
reader shares.

Public names: `ARCHIVE_REF_PREFIX`, `ATTEMPT_PRESERVE_BRANCH_PREFIX`, `ATTEMPT_PRESERVE_DIRTY_PREFIX`,
`ContentGateFinding`, `ContentGateReason`, `DEFAULT_PER_FILE_MAX_BYTES`, `DEFAULT_PUSH_CAP_PER_RUN`,
`DEFAULT_PUSH_CAP_PER_STORY`, `LocalPreserveTag`, `ORIGIN_MAIN`, `ORIGIN_REMOTE`, `PREFLIGHT_PRESERVE_TAGS_PROOF_ENV`,
`PRESERVE_PRODUCERS`, `PRESERVE_PURGE_LIST_REL`, `PRESERVE_REF_PREFIX`, `PRESERVE_TRAILERS`, `PROVENANCE_VALUES`,
`ParsedArchiveRef`, `ParsedPreserveRef`, `PreserveGitError`, `PreserveObservation`, `PreserveRecord`,
`PreserveRefConflictError`, `PreserveRefError`, `PreserveRefNameError`, `PreserveState`, `PreserveTrailers`,
`PurgeList`, `PushPreserveResult`, `REMOTE_PROBE_TIMEOUT_S`, `TagPreserveResult`, `default_purge_list_path`,
`is_preserve_tag_ref`, `list_local_preserve_tags`, `list_pending_preserve_refs`, `list_preserves`, `load_purge_list`,
`normalize_ref`, `observe_preserve_debt`, `parse_archive_ref`, `parse_preserve_ref`, `preserve_artifact_reachable`,
`push_preserve_ref`, `recovery_refs_for_run`, `ref_exists_local`, `ref_on_origin`, `remote_ref_names`,
`render_archive_heads_ref`, `render_archive_tags_ref`, `render_preserve_ref`, `run_content_gate`, `short_ref_name`,
`snapshot_worktree_commit`, `tag_preserve`.

Estate-bound constants: `PRESERVE_PURGE_LIST_REL` (`docs/governance/preserve-purge-list.json`, relative to the
repository root).

### `pyforge.core.published_loop`

Governed by: spec-pyforge-unifying-strategy:CAP-17, with spec-pyforge-marshal:CAP-227 (the published-plane read that
replaces a loop-home read).

The read side of the run-state publisher: `fetch_story_tasks` calls the host's `list_loop_story_tasks` MCP tool on
`/stations/marshal/mcp` through `PyForgeStationClient` and `HostMintClient`, and answers nothing (so the caller falls
back) when the plane is unreachable or the reply does not parse.

Public names: `fetch_story_tasks`.

### `pyforge.core.league_measure`

Governed by: spec-pyforge-steward:CAP-46.

The published-measure cite gate: only a measure whose state is `on` in steward's measure catalog may be cited as
steering work. It has no importer outside its own unit tests.

Public names: `LeagueMeasureError`, `MEASURE_CATALOG_RELATIVE`, `MeasureCiteVerdict`, `load_measure_states`,
`parse_measure_catalog`, `resolve_repo_root`, `validate_measure_cite`.

Estate-bound constants: `MEASURE_CATALOG_RELATIVE`
(`_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/measure-catalog.md`, relative to
the repository root).

## Environment variables

A role is `read` (the leaf reads it) or `set` (the leaf sets it in its own environment, or hands it to a child).

| Variable | Role | Modules | Meaning |
|---|---|---|---|
| `PYFORGE_FLAGS_PATH` | `read` | `pyforge.core.cutover_root` | The flag tree's path. `resolve_flags_path` reads it before walking up from the working directory for `LOCAL_DEV_RELATIVE`; `pyforge.core.flags` reaches the tree only through that function. |
| `PYFORGE_ENVIRONMENT` | `read` | `pyforge.core.flags` | The environment the tree is rendered for: `dev` (the default when unset), `staging` or `production`; any other value raises `UnknownEnvironmentError`. |
| `STATION_REMOTE` | `read` | `pyforge.core.station_port` | `1` (also `true`, `yes`) selects the HTTP path over the in-process station port. |
| `PYFORGE_HOST` | `read` | `pyforge.core.published_loop` | The host the published plane is read from (default `http://127.0.0.1:8000`). |
| `PYFORGE_IDP_BEARER_FILE` | `read` | `pyforge.core.published_loop` | The file holding the operator's IdP bearer, presented to the host mint. |
| `PYFORGE_PREFLIGHT_PRESERVE_TAGS_PROOF` | `set` | `pyforge.core.preserve_refs` | Set to `1` around the one-refspec push of a preserve tag, so the repository's pre-push hook knows the push carries preserve tags only. |
| `GIT_INDEX_FILE` | `set` | `pyforge.core.preserve_refs` | A private index while the snapshot commit is built, so the working tree's index is untouched. |
| `GIT_AUTHOR_NAME` | `set` | `pyforge.core.preserve_refs` | The snapshot commit's author, `pyforge-preserve`. |
| `GIT_AUTHOR_EMAIL` | `set` | `pyforge.core.preserve_refs` | The snapshot commit's author email. |
| `GIT_COMMITTER_NAME` | `set` | `pyforge.core.preserve_refs` | The snapshot commit's committer, as the author. |
| `GIT_COMMITTER_EMAIL` | `set` | `pyforge.core.preserve_refs` | The snapshot commit's committer email, as the author's. |
| `PYTHONUNBUFFERED` | `set` | `pyforge.core.process` | `1` in a detached child's environment, so its output reaches its log as written. |
| `PYTHONSAFEPATH` | `set` | `pyforge.core.process` | `1` in a detached child's environment, so the interpreter's installed packages run, never a module in the working directory. |

## Feature-flag keys

| Key | Modules | Meaning |
|---|---|---|
| `pyforge.cutover_root` | `pyforge.core.cutover_root` | The writer lock and root of record (fnd:CAP-8): `local-recipes` or `foundry`. The operator flips it by hand; nothing flips it automatically. |
| `pyforge.marshal.front_door_environment` | `pyforge.core.dispatch` | The kill switch of the front door's environment-naming refusal (spec-pyforge-core:CAP-11): off reads an uninstalled roster station as an unknown station. |

A string in the leaf's own `pyforge.core` namespace is not a flag key: `pyforge.core.hooks` is the entry-point group,
and `pyforge.core.example` the example hook spec's name.

## Exit codes

| Name | Value | Modules | Means |
|---|---|---|---|
| `EXIT_USAGE` | `2` | `pyforge.core.dispatch` | An unknown station, an option where a station belongs, a bare `pyforge` or `--help`, or a roster station not installed here. |
| `EXIT_NOT_FOUND` | `127` | `pyforge.core.dispatch` | The station's console script could not be started. |

Otherwise `pyforge.core.dispatch.main` returns the child's own exit code unchanged. The verdict lattice in
`pyforge.core.verdict` defines no value: a station builds its `Lattice` from its own members and exit values, and
`Lattice.exit_codes` is that station's frozen exit-code domain; a narrowing (doctor's domain inside warden's) is
`Lattice.narrows`. `pyforge.core.flags` defines none either: a station's `main()` catches `FlagOff` and returns its own
usage code.

## Entry points

| Group | Name | Target |
|---|---|---|
| `console_scripts` | `pyforge` | `pyforge.core.dispatch:main` |
| `pyforge.core.hooks` | `dummy` | `pyforge.core.hooks:DummyPlugin` |

A station registers a plugin on `pyforge.core.hooks` and never declares a group of its own
(spec-pyforge-unifying-strategy:CAP-18).

## Python floor

`>=3.14` (`requires-python` in the package's `pyproject.toml`; decision D6 of the 2026-11-10 design pass).
`pyforge.core.process` uses the unparenthesised multi-type `except` clause Python 3.14 admits, so the leaf does not
import on an older interpreter.

## Not part of the contract

- A name with a leading underscore: module-private helpers and constants, whatever their reach.
- `__version__`, the one name `pyforge.core` (the package's `__init__`) binds; a caller imports from a module, never
  from the package.
- A name a module imports from another module: it is part of the module that defines it.
- The test suites under `src/shared/packages/pyforge-core/tests/`, the build files, and `py.typed`.
