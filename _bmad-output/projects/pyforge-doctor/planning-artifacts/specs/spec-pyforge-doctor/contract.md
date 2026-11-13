# Public contract — Doctor

Companion to `SPEC.md` (CAP-97, FR-28; decision D1 of the 2026-11-10 cutover readiness plan). It records everything
Doctor serves to a caller and everything a second root must provide for Doctor to run: every verb path and option of
`doctor` and of the sources dispatcher `python -m pyforge.doctor.sources`, the MCP tools django-doctor serves for it,
the feature-flag keys it reads, the environment variables it reads and the ones it sets for a child process, its exit
codes, every Source with its scope, subject, governing capability and check codes, the computed `check=` sites, the
imports that leave the package, the inputs each source reads, its identity constants, the scripts outside the package
that belong to its chain, and its Python floor. A second root that rebuilds Doctor from its Spec rebuilds this surface.
Nothing generates this file and no verb renders it: it is written by hand, and a change that adds a verb, option, tool,
key, variable, exit code, Source, check code, computed site or import adds its row here in the same change.

The guard is `src/shared/packages/pyforge-doctor/tests/meta/test_public_contract.py`, a live-tree module (it reads this
Spec folder and django-doctor). It derives the code side and compares it both ways with the tables below: an item the
code has and this file lacks fails as *missing*, and a row naming something the code no longer has fails as *stale*.
The code side, family by family:

- **Verbs and options:** the parsers `pyforge.doctor.__main__._build_parser()` and
  `pyforge.doctor.sources.__main__._build_parser()` build, walked through their subparsers. `-h`/`--help` is
  argparse's own on every path and is not listed; a positional is listed by its name.
- **MCP tools:** the module-level `*_TOOL` constants of django-doctor's `mcp_asgi.py`, read with `ast`.
- **Feature-flag keys:** every call of a flag reader in the package, keyed by key, module and reader:
  `pyforge.core.flags`'s `read_boolean`, `kill_switch_on`, `require` and `disabled_help`, `django_pyforge.flags`'s
  `evaluate_boolean` and `evaluate_cli_boolean`, and each OpenFeature client evaluation method (`get_<type>_value`
  and `get_<type>_details`, sync and async). The key is read where the reader takes it, positionally or by keyword
  (`key=`; OpenFeature's `flag_key=`), and evaluated like a check code (a literal or a module constant). A reader is
  read under any name the module binds to it (`from pyforge.core.flags import read_boolean as rb`,
  `rb = fl.read_boolean`, `get = client.get_boolean_value`) and on any name bound to a flags module
  (`from pyforge.core import flags as fl`, `import pyforge.core.flags as fl`, `pyforge.core.flags.<reader>`);
  `require` and `disabled_help`, common names, count only when bound from a flags module. It fails closed: a key no
  reading resolves, a key a `*` or `**` argument may carry, and a reader loaded as a value (a callback,
  `functools.partial`) read `<expr>`, and need a row like any other key.
- **Environment variables:** an AST scan of the package for `os.environ.get(...)`, `.setdefault(...)`,
  `.pop(...)`, `os.getenv(...)`, `os.environ[...]` and `... in os.environ`, the key read from the first positional
  argument or the `key=` keyword; `os.environb` counts as the environment (its bytes key decoded); `environ` /
  `environb` / `getenv` are read under any name the module binds to them (`from os import environ as E`,
  `E = os.environ`), and so is a copy of the environment (`env = dict(os.environ)`, `os.environ.copy()`,
  `{**os.environ}`, a copy of a copy) in the function that makes it, or anywhere for a module-level copy; and, apart,
  the keys set on a copy of `os.environ` handed to a child.
- **Exit codes:** the module-level `EXIT_*` / `_EXIT_*` constants of `verdict.py`, with their numbers.
- **Sources:** the `Source` enum, `sources.REGISTRY` (scope and subject) and the dispatcher's `DISPATCH`.
- **Check codes:** every `check=` keyword in the package, and the argument in `check`'s place of a `Finding(...)` that
  has no `check=` keyword (`Finding` under any name the module binds to it, `from ... import Finding as F` included):
  a string literal; a module-level constant (an f-string over other constants and `Source.<M>.value` included); or a
  helper's parameter the helper never rebinds, resolved through the helper's call sites to the literal or constant
  each caller passes, or to the parameter's default where a caller omits it. A public helper such as
  `degrade_on_exception` is read in every module; a private one in its own module and in each module that imports it
  by name (`from .<module> import _emit`), directly or through a re-export (a module that imported it by name, any
  number of hops, a package `__init__` included), never in a module that merely defines a function of the same name
  (three modules each define their own `_finding`). A `check=False` is a subprocess flag, not a code. Anything else is a
  computed site (next family).
- **Computed check sites:** a `check=` whose value is none of the above, keyed by module, function and expression (a
  helper parameter the helper rebinds before `check=`, such as `name = str(name)`, included); a `Finding(...)` whose
  code may come through a `*` or `**` argument, keyed the same way (`*rest`, `**kwargs`); a helper the resolution
  cannot follow, keyed by module, helper and parameter (it fails closed: a method; a private helper reached through
  an attribute in any module, `self._emit(...)` or `<module>._emit(...)`, since the AST cannot tell whose attribute
  it is; a private helper imported under another name anywhere along a re-export chain, or by a module that also
  defines that name; a call whose `*` or `**` argument may bind the parameter or that omits it with no default; the
  helper loaded as a value, such as a callback; a public helper imported under another name; or a helper no call
  binds); in a module whose `check=` reads
  `<row>['kind']`, an item row's `"kind"` value that is not a literal or constant, keyed by module, function and value;
  and a computed environment read, keyed the same way with its keys. The codes of a computed site that the code still
  enumerates are counted as check codes: the `"kind"` values of the item rows of a module whose `check=` reads
  `<row>['kind']` (`{"kind": ...}`, `dict(kind=...)`, `<row>['kind'] = ...`, `<row>.update(kind=...)` and
  `<row>.setdefault('kind', ...)`; never a Finding's `evidence=` dict), the strings a loop binds over a literal
  tuple, and the `HygieneFindingKind` member a site names.
- **Imports:** every import, function-local and `TYPE_CHECKING` ones included, that leaves the package and the
  standard library, by dotted name.

How the test reads this file: only the table rows under the thirteen `##` headings, located by the first header cell
of each table (`Verb`, `Tool`, `Key`, `Variable read`, `Variable set for a child process`, `Code`, `Source`, `Module`,
`Import`, `Constant`, `Script`), and in each row the backticked tokens of the cells the family names; a table whose
first header cell is anything else is prose. It also checks that every Source names a governing capability and the
modules that name it, that every check-code row's module is one of its Source's modules, that every identity
constant equals the code's value, that every script listed exists, and that the Python floor matches
`pyproject.toml`. Module paths are relative to `src/shared/packages/pyforge-doctor/src/pyforge/doctor/`.

## CLI

The program is `doctor` (`[project.scripts] doctor = "pyforge.doctor.__main__:main"`); `pyforge doctor …` reaches the
same parser through pyforge-core's dispatcher. `main` always returns an int; only `verdict.py` projects findings to an
exit code. The sources dispatcher is the module `python -m pyforge.doctor.sources`: one Source per run, judged against
the current working directory (it takes no target), which the `*-check` pixi tasks and `scripts/detectors.py` run.

| Verb | What it does |
|---|---|
| `doctor` | the program; `--version` only, every other option belongs to a verb |
| `doctor check` | pre-flight: warden's engine self-check, env hygiene, and the opt-in categories (CAP-1, CAP-4) |
| `doctor monitor` | fleet pulse over cf_atlas's Watch axes (CAP-2, CAP-6, CAP-7) |
| `doctor diagnose` | one target: gather, grade, and with `--prescribe` partition, rank and name a root cause (CAP-3, CAP-5, CAP-8) |
| `doctor backlog-intake` | tracked deferred-work entries that name one epic or story, fleet wide (CAP-10) |
| `doctor flags` | the feature-flag actuator group; its one verb is below |
| `doctor flags kill-switch` | disable one flag of the FILE-resolver tree and count it (CAP-96, Doctor's one actuator) |
| `python -m pyforge.doctor.sources` | the sources dispatcher: run one `DISPATCH` Source (CAP-93) |

### `doctor` options

| Verb | Option | Kind | Default and choices |
|---|---|---|---|
| `doctor` | `--version` | flag | prints `doctor 0.1.0`; top-level only |
| `doctor check` | `path` | positional, optional | `.` |
| `doctor check` | `--engines` | option, optional `NAME` | absent; alone runs the whole category, `NAME` one cataloged check (`--list`) |
| `doctor check` | `--env` | option, optional `NAME` | absent; as `--engines` |
| `doctor check` | `--durability` | flag | whole category only |
| `doctor check` | `--bmad-core` | flag | opt-in only, never in the zero-flag run; offline under `--scope repo` |
| `doctor check` | `--sibling-dreams` | flag | opt-in only; fail-open without a token |
| `doctor check` | `--scope` | choice | `all`; one of `repo`, `runtime`, `all` |
| `doctor check` | `--list` | flag | print the check catalog and run nothing |
| `doctor check` | `--json` | flag | one schema-valid DoctorReport on stdout |
| `doctor monitor` | `--fleet` | flag, required | names the scope the verb watches |
| `doctor monitor` | `--watch` | option `AXIS[,AXIS...]` | `staleness,cve`; axes `staleness`, `cve`, `abandonment`, `adoption`, `behind-upstream` |
| `doctor monitor` | `--target` | option `MAINTAINER` | absent; scope every axis to one maintainer or feedstock |
| `doctor monitor` | `--source` | option `SOURCE` | absent; filter the rendered output to one Finding source |
| `doctor monitor` | `--json` | flag | one schema-valid DoctorReport on stdout |
| `doctor monitor` | `--surface` | option `PATH` | absent; also write the fleet-health surface file (CAP-6, NFR-1's sanctioned write) |
| `doctor diagnose` | `--target` | option `TARGET`, required | the feedstock or maintainer; an existing directory also gets the engines and env checks |
| `doctor diagnose` | `--prescribe` | flag | partition, rank and name the root cause |
| `doctor diagnose` | `--json` | flag | one schema-valid DoctorReport on stdout |
| `doctor backlog-intake` | `identifier` | positional, required | an epic (`13`) or story (`13.1`, `13-1`), optionally prefixed `Epic ` or `Story ` |
| `doctor backlog-intake` | `path` | positional, optional | `.` |
| `doctor backlog-intake` | `--json` | flag | one schema-valid DoctorReport on stdout |
| `doctor flags kill-switch` | `--flag` | option, required | the flag key to disable |
| `doctor flags kill-switch` | `--reason` | option, required | the operator's reason, recorded on the metric label |
| `doctor flags kill-switch` | `--flags-path` | option | absent; the tree `django_pyforge.flags.resolve_tree_path()` names |

### Sources dispatcher options

| Verb | Option | Kind | Default and choices |
|---|---|---|---|
| `python -m pyforge.doctor.sources` | `source` | positional, required | one `DISPATCH` name (the Sources table's `yes` rows) |
| `python -m pyforge.doctor.sources` | `--json` | flag | the findings as a JSON array of `Finding.to_json_dict()` |
| `python -m pyforge.doctor.sources` | `--groundtruth` | flag | `bmad-drift` only: print its six live facts instead of findings |
| `python -m pyforge.doctor.sources` | `--dreams` | flag | `dream-chain` only: the Dream-tier hygiene mode (the `dreams-hygiene` gather) |
| `python -m pyforge.doctor.sources` | `--layers` | flag | `chain-completeness` only, with `--project`: the per-project chain audit (`chain-layers-audit`) |
| `python -m pyforge.doctor.sources` | `--project` | option `SLUG` | required with `--layers`, refused without it |
| `python -m pyforge.doctor.sources` | `--base` | option `REV` | `ledger-regression` and `ledger-direction` only; default `refs/remotes/origin/main` |
| `python -m pyforge.doctor.sources` | `--head` | option `REV` | `ledger-regression` only; default `HEAD` |
| `python -m pyforge.doctor.sources` | `--inv` | option `INV...` | `dream-chain` and `chain-completeness` only: keep findings whose evidence `inv` is named |

## MCP tools

Doctor's package serves no MCP itself. django-doctor (`src/shared/packages/django-doctor/`) hosts the face at
`POST /stations/doctor/mcp` (`build_doctor_mcp_asgi`), realized under spec-pyforge-unifying-strategy:CAP-20: a start
tool returns a job, a get tool reads it, and the supervisor runs the station's row of the closed verb table through the
registered runner (canopy:AD-24).

| Tool | Constant | Role | Realized under |
|---|---|---|---|
| `start_scan` | `START_SCAN_TOOL` | start a scan job on the supervisor | spec-pyforge-unifying-strategy:CAP-20 |
| `get_scan` | `GET_SCAN_TOOL` | read a scan job's state and result | spec-pyforge-unifying-strategy:CAP-20 |
| `run_scan` | `RUN_SCAN_TOOL` | the runner the supervisor calls (`run_start_tool("doctor", "run_scan", payload)`) | spec-pyforge-unifying-strategy:CAP-20 |

## Feature-flag keys

None. Doctor reads no feature-flag key: `doctor flags kill-switch` takes the key it disables as an argument (`--flag`)
and carries no flag of its own (CAP-96). Two sources read the root of record through
`pyforge.core.cutover_root.root_of_record()` (`writer-lock`, `capability-ledger`); that function, not Doctor, names the
`pyforge.cutover_root` key (spec-pyforge-core:CAP-13). A key Doctor read would be a row of a `Key | Module | Reader`
table here: the key (or `<expr>` where the reading rules above cannot resolve it), the module and the reader's name,
each in backticks.

## Environment variables

Read:

| Variable read | Module | Function | Read for |
|---|---|---|---|
| `GH_TOKEN` | `sources/sibling_dreams.py` | `_operator_token` | the operator token for the sibling repository's GitHub Contents API; first of the two |
| `GITHUB_TOKEN` | `sources/sibling_dreams.py` | `_operator_token` | the same, when `GH_TOKEN` is empty; with neither, `sibling-dreams-drift` is one fail-open WARN |

Set for a child process, never read (listed apart): every `cli_bridge` call copies `os.environ` and sets `NO_COLOR` so
an ANSI-coloured table cannot corrupt the output it parses.

| Variable set for a child process | Module | Value |
|---|---|---|
| `NO_COLOR` | `cli_bridge.py` | `1`, in `run_cli_json`, `run_git`, `run_pytest`, `run_check_script` and `run_argv` |

## Exit codes

`doctor` (and `pyforge doctor`): the closed domain `{0, 2, 130}`, a subset of warden's `{0, 1, 2, 130}` that omits the
policy rung `1`, because Doctor reports operability, not policy (AD-2). `verdict.exit_code_for` is the one projection:
any `fail` finding is `2`; `ok`, `warn` and no findings are `0`. An argparse usage error, a refused kill switch and an
internal error also exit `2`; `130` is the SIGINT path at the CLI boundary.

| Code | Constant | Meaning |
|---|---|---|
| `0` | `_EXIT_OK` | no `fail` finding (a `warn` never changes the exit) |
| `2` | `_EXIT_FAIL` | at least one `fail` finding; also a usage error or a refused actuator |
| `130` | `EXIT_SIGINT` | interrupted |

The sources dispatcher exits through the same `exit_code_for`, plus:

| Dispatcher exit | When |
|---|---|
| `0` | the gathered findings hold no `fail` (an `unmeasured` source too: its findings are WARNs) |
| `2` | a `fail` finding; a usage error (an unknown Source, a flag on the wrong Source); `--groundtruth` that could not read its facts |
| `130` | interrupted (`check-layout` once drove a browser and could hang) |

The aggregate `{0, 1, 2}` belongs to `scripts/detectors.py`, not to Doctor, and is listed only to keep the two apart:

| Aggregate exit | When (scripts/detectors.py) |
|---|---|
| `0` | every row `pass` or `unmeasured` (all of a row's findings are gather failures, `models.is_gather_failure`) |
| `1` | a row with findings |
| `2` | a row `unknown` (the detector could not run) |

## Sources

Every member of the closed `Source` enum, with its `REGISTRY` row (every row's `owning_station` is `doctor`). Scope
`repo` reads tracked files and git history and runs anywhere; `runtime` reads host or network state. *Dispatcher*
`yes` means a `DISPATCH` entry: `python -m pyforge.doctor.sources <name>` runs it, and so do its pixi task and
`scripts/detectors.py`; *Reached by* names the pixi task where one exists. The ten FR-15 sources resolve under CAP-93; every later Source names its own capability or the
qualified outcome it mechanizes. Capability ids without a prefix are spec-pyforge-doctor's.

| Source | Scope | Subject | Dispatcher | Governing capability | Modules | Reached by |
|---|---|---|---|---|---|---|
| `warden-doctor` | repo | warden | no | CAP-1 (AD-1: warden's self-check, relayed) | `sources/warden.py`, `__main__.py` | `doctor check --engines [NAME]` |
| `staleness-report` | repo | atlas | no | CAP-2 | `sources/atlas.py` | `doctor monitor --fleet --watch staleness` |
| `cve-watcher` | repo | atlas | no | CAP-2 | `sources/atlas.py` | `--watch cve` |
| `behind-upstream` | repo | atlas | no | CAP-2 (CAP-8 reads it for the safe-upgrade target) | `sources/atlas.py` | `--watch behind-upstream` |
| `feedstock-health` | repo | atlas | no | CAP-2 (the abandonment axis) | `sources/atlas.py` | `--watch abandonment` |
| `release-cadence` | repo | atlas | no | CAP-2 (the abandonment axis) | `sources/atlas.py` | `--watch abandonment` |
| `env-hygiene` | repo | doctor | no | CAP-1 | `checks/env_hygiene.py` | `doctor check --env [NAME]` |
| `marshal-durability` | repo | marshal | no | CAP-9 | `sources/marshal.py` | `doctor check --durability` |
| `adoption` | repo | atlas | no | CAP-7 | `sources/atlas.py` | `--watch adoption` |
| `ledger-regression` | repo | marshal | yes | CAP-93 | `sources/ledger.py` | `ledger-regression-check` |
| `ledger-direction` | repo | marshal | yes | CAP-79 (CAP-78, CAP-85) | `sources/ledger.py` | `ledger-direction-check` |
| `story-status` | repo | marshal | yes | CAP-93 | `sources/marshal.py` | `story-status-check` |
| `chain-completeness` | repo | marshal | yes | CAP-93 (CAP-57) | `sources/board.py` | `chain-completeness-check` |
| `dashboard-drift` | repo | marshal | yes | CAP-93 (a reintroduction gate for the retired console) | `sources/board.py` | `retired-console-check` |
| `check-layout` | repo | marshal | yes | CAP-93 (a reintroduction gate for the retired console) | `sources/board.py` | `dashboard-layout-check` |
| `dream-chain` | repo | marshal | yes | CAP-93 (CAP-58) | `sources/chain.py` | `dream-chain-check` |
| `spec-surface` | repo | marshal | yes | CAP-93 (CAP-88) | `sources/chain.py` | `spec-surface-check` |
| `deferred-work` | repo | marshal | yes | CAP-93 (CAP-35, CAP-36, CAP-86) | `sources/chain.py` | `deferred-work-check` |
| `forward-dependency` | repo | marshal | yes | CAP-93 | `sources/deps.py` | `forward-dependency-check` |
| `bmad-drift` | repo | marshal | yes | CAP-93 (CAP-11, CAP-12) | `sources/factory.py` | `bmad-drift-check` |
| `bmad-output-hygiene` | repo | fleet | yes | CAP-42 and CAP-43 | `sources/hygiene.py` | `bmad-output-hygiene-check` |
| `due-for-verification` | repo | marshal | yes | CAP-26 (CAP-27 to CAP-32) | `sources/chain.py` | `due-for-verification-check` |
| `bmad-method-version-drift` | repo | marshal | yes | CAP-13, CAP-14 and CAP-16 (CAP-15: ambient) | `sources/bmad_method.py` | `doctor check --bmad-core`, `bmad-method-version-drift-check` |
| `backlog-intake` | repo | marshal | no | CAP-10 | `sources/backlog_intake.py` | `doctor backlog-intake` |
| `sibling-dreams-drift` | repo | fleet | yes | CAP-71 and CAP-82 | `sources/sibling_dreams.py` | `doctor check --sibling-dreams`, dispatcher |
| `ci-pause-drift` | runtime | steward | yes | CAP-89 | `sources/ci_pause_drift.py` | dispatcher |
| `pages-liveness` | runtime | steward | yes | CAP-91 | `sources/pages_liveness.py` | dispatcher |
| `dreams-hygiene` | repo | marshal | yes | spec-pyforge-marshal:CAP-296 | `sources/chain.py` | `dreams-hygiene-check`, `dream-chain --dreams` |
| `chain-layers-audit` | repo | marshal | no | spec-pyforge-marshal:CAP-104 (read by CAP-20's sweep) | `sources/board.py` | `chain-completeness --layers --project SLUG` |
| `platform-policy-suite` | repo | steward | yes | CAP-98 | `sources/platform_policy.py` | `platform-policy-suite-check` |
| `bmad-render-config-ambiguity` | repo | steward | yes | CAP-99 | `sources/bmad_config.py` | `bmad-render-config-ambiguity-check` |
| `frozen-path-changed` | repo | steward | yes | CAP-94 | `sources/frozen_path.py` | `frozen-path-changed-check` |
| `capability-effect` | repo | fleet | yes | CAP-17, CAP-18 and CAP-19 | `sources/capability_effect.py` | `capability-effect-check` |
| `status-body-consistency` | repo | fleet | yes | CAP-72 to CAP-76 | `sources/status_body_consistency.py` | `status-body-consistency-check` |
| `pixi-currency-ledger` | repo | fleet | yes | CAP-69 | `sources/pixi_currency.py` | `pixi-currency-staleness-check` |
| `general-docs-consistency` | repo | fleet | yes | CAP-62 | `sources/general_docs_consistency.py` | `general-docs-consistency-check` |
| `docs-shelf-occupancy` | repo | fleet | yes | CAP-54 | `sources/docs_shelf.py` | `docs-shelf-occupancy-check` |
| `capability-ledger` | repo | steward | yes | CAP-95 and CAP-87 | `sources/capability_ledger.py` | `capability-ledger-check` |
| `chain-sprawl` | repo | fleet | yes | spec-one-chain-per-station:CAP-2 | `sources/one_chain.py` | `chain-sprawl-check` |
| `fr-without-cap` | repo | fleet | yes | CAP-92 | `sources/one_chain.py` | `fr-without-cap-check` |
| `fold-complete` | repo | fleet | yes | spec-one-chain-per-station:CAP-11 | `sources/one_chain.py` | `fold-complete-check` |
| `docs-map-hygiene` | repo | fleet | yes | CAP-83 (CAP-90) | `sources/docs_map_hygiene.py` | `docs-map-hygiene-check` |
| `live-proof-surface` | repo | fleet | yes | CAP-77 | `sources/live_proof_surfaces.py` | `live-proof-surface-check` |
| `docs-currency` | repo | fleet | yes | CAP-84 (CAP-90) | `sources/docs_currency.py` | `docs-currency-check` |
| `frontmatter-duplicate-keys` | repo | fleet | yes | CAP-81 and CAP-86 | `sources/frontmatter_duplicate_keys.py` | `frontmatter-duplicate-keys-check` |
| `writer-lock` | repo | fleet | yes | CAP-100 | `sources/writer_lock.py` | dispatcher |

A source that measured nothing reads `unmeasured` on the aggregate: every finding a gather failure (a WARN with
evidence `unevaluable: true`, a `degrade_on_exception` WARN, the atlas sentinel `doctor.sources.atlas`). A source whose
subject is absent reports one `<source>-unevaluable` WARN, never an OK or nothing (CAP-93 as amended 2026-11-10).

## Check codes

Every code a Finding of each Source can carry, by the module that emits it. A code shared by two Sources of one module
(`ledger-inventory`, `rekey-map-unreadable`, `unparseable-frontmatter`, `doctor.sources.atlas`) is listed under each.
The computed sites below add no code of their own except the ones listed here (the loop and `"kind"` literals) and
warden's DoctorCheck names, which warden's contract lists.

| Source | Module | Codes |
|---|---|---|
| `warden-doctor` | `sources/warden.py` | `pyforge-warden` (the sentinel when warden is absent or raises; otherwise each warden DoctorCheck name) |
| `staleness-report` | `sources/atlas.py` | `atlas-staleness`, `doctor.sources.atlas` |
| `cve-watcher` | `sources/atlas.py` | `atlas-cve`, `doctor.sources.atlas` |
| `behind-upstream` | `sources/atlas.py` | `atlas-behind-upstream`, `doctor.sources.atlas` |
| `feedstock-health` | `sources/atlas.py` | `atlas-feedstock-health`, `doctor.sources.atlas` |
| `release-cadence` | `sources/atlas.py` | `atlas-release-cadence`, `doctor.sources.atlas` |
| `adoption` | `sources/atlas.py` | `atlas-adoption-stage`, `atlas-version-downloads`, `doctor.sources.atlas` |
| `env-hygiene` | `checks/env_hygiene.py` | `unconditional-credential-injection`, `env-hygiene` |
| `marshal-durability` | `sources/marshal.py` | `marshal-durability-git`, `marshal-durability-regression`, `marshal-durability-total`, `ledger-inventory`, `ledger-unreadable`, `ledger-untracked` |
| `story-status` | `sources/marshal.py` | `story-status`, `story-status-unevaluable`, `bare-merge-diff-unreadable` |
| `ledger-regression` | `sources/ledger.py` | `ledger-regression`, `ledger-inventory`, `ledger-key-moved`, `ledger-unreadable`, `ledger-deleted`, `done-key-regressed`, `rekey-map-dangling`, `rekey-map-malformed`, `rekey-map-unreadable` |
| `ledger-direction` | `sources/ledger.py` | `ledger-direction`, `ledger-direction-unevaluable`, `bare-merge-diff-unreadable`, `rekey-map-unreadable` |
| `chain-completeness` | `sources/board.py` | `chain-completeness`, `chain-completeness-unevaluable`, `spec-status-roster-degraded`, `spec-status-missing`, `delivered-spec-not-decomposed`, `spec-not-decomposed`, `unparseable-ledger-key`, `canonical-epics-declares-no-stories`, `story-without-ledger-key`, `ledger-key-without-story`, `epic-heading-without-ledger-key`, `ledger-epic-key-without-heading`, `board-diverges-from-ledger` |
| `chain-layers-audit` | `sources/board.py` | `chain-layers-audit`, `chain-layers-audit-unevaluable`, `chain-audit-verdict`, `chain-audit-checkpoint-layers`, `chain-audit-checkpoint-coherence`, `chain-audit-checkpoint-staleness`, `chain-audit-checkpoint-orphans` |
| `dashboard-drift` | `sources/board.py` | `dashboard-drift` |
| `check-layout` | `sources/board.py` | `console-bar-layout` |
| `dream-chain` | `sources/chain.py` | `dream-chain`, `dream-chain-unevaluable`, `unparseable-frontmatter`, `prd-not-sharded`, `architecture-not-sharded`, `epics-missing`, `spec-without-dream-link`, `dream-without-spec`, `owner-unassigned`, `spec-location-mismatch`, `constitutive-roster-degraded` |
| `dreams-hygiene` | `sources/chain.py` | `dreams-hygiene`, `dreams-hygiene-unevaluable`, `spec-status-roster-degraded`, `unparseable-frontmatter`, `dream-vocab`, `dream-unowned`, `missing-title`, `dream-status-trailing-comment`, `realization-log-missing`, `historical-section-too-long`, `kinship-wikilink-dead`, `readme-table-drift`, `readme-table-orphan`, `dream-readme-missing`, `specified-spec-not-ready` |
| `spec-surface` | `sources/chain.py` | `spec-surface`, `spec-surface-unevaluable`, `no-baseline`, `drift`, `drift-presumed`, `drift-blind`, `stale-surface`, `stale-allowlist`, `ungoverned` |
| `deferred-work` | `sources/chain.py` | `deferred-work`, `deferred-work-unevaluable`, `no-deferred-work-baseline`, `stale-deferred-work-baseline`, `no-tracked-ledger`, `tier3-entry-unidentified`, `tier3-only-deferral`, `ledger-entry-unstatused`, `ledger-entry-unidentified`, `spec-frontmatter-only-deferral`, `followup-review-uncarried`, `verified-line-uncited` |
| `due-for-verification` | `sources/chain.py` | `due-for-verification`, `due-for-verification-unevaluable`, `due-for-verification-cluster`, `verification-coverage` |
| `forward-dependency` | `sources/deps.py` | `forward-dep`, `coverage`, `partial`, `no-dispatch`, `unmeasured` |
| `bmad-drift` | `sources/factory.py` | `bmad-drift`, `bmad-drift-unevaluable`, `pin-missing`, `pin-behind`, `stale-rule`, `surface-changed`, `baseline-corrupt`, `no-baseline`, `count-stale`, `count-source-unreadable`, `phase-list-stale`, `spec-status-stale`, `deferred-stale`, `archive-misplaced`, `stray-file`, `tracked-impl-artifact`, `uncovered`, `coverage-summary`, `dream-vocab`, `dream-unowned`, `pixi-env-matrix-stale` |
| `bmad-output-hygiene` | `sources/hygiene.py` | `bmad-output-hygiene`, `bmad-output-hygiene-unevaluable`, `dead-test-scaffolding`, `hollow-sprint-status`, `orphan-file`, `orphan-file-unevaluable`, `readme-placeholder`, `stale-dream-status`, `hygiene-check-unevaluable`, `station-unevaluable` |
| `bmad-method-version-drift` | `sources/bmad_method.py` | `bmad-method-version-drift`, `bmad-method-floor-unparseable`, `bmad-method-manifest-divergence`, `bmad-method-upstream-drift`, `bmad-suite-floor-drift`, `bmad-suite-upstream-drift`, `bmad-recipe-upstream-drift`, `bmad-channel-drift` |
| `backlog-intake` | `sources/backlog_intake.py` | `backlog-intake` |
| `sibling-dreams-drift` | `sources/sibling_dreams.py` | `sibling-dreams-drift`, `sibling-dreams-unreachable` |
| `ci-pause-drift` | `sources/ci_pause_drift.py` | `ci-pause-drift`, `ci-pause-stuck`, `ci-pause-overdue`, `ci-pause-partial`, `ci-pause-unobserved` |
| `pages-liveness` | `sources/pages_liveness.py` | `pages-liveness`, `pages-liveness-stale`, `pages-liveness-unavailable` |
| `platform-policy-suite` | `sources/platform_policy.py` | `tests-policy`, `platform-ci-test-env`, `platform-policy-suite-unevaluable` |
| `bmad-render-config-ambiguity` | `sources/bmad_config.py` | `bmad-render-config-ambiguity`, `bmad-render-config-ambiguity-unevaluable` |
| `frozen-path-changed` | `sources/frozen_path.py` | `frozen-path-changed`, `frozen-path-changed-unevaluable` |
| `capability-effect` | `sources/capability_effect.py` | `capability-effect`, `capability-effect-unevaluable`, `capability-effect-no-caller`, `capability-effect-no-surface-line`, `capability-effect-absent-surface-path`, `capability-effect-document-surface`, `capability-effect-unreadable-epics`, `capability-effect-verified` |
| `status-body-consistency` | `sources/status_body_consistency.py` | `status-body-consistency`, `status-body-consistency-unevaluable`, `status-body-progress-phrase`, `status-body-open-questions`, `status-body-promissory-language`, `status-body-status-comment`, `status-body-status-comment-unresolvable`, `status-body-unparseable`, `spec-status-roster-degraded` |
| `pixi-currency-ledger` | `sources/pixi_currency.py` | `pixi-currency-ledger-current`, `pixi-currency-ledger-stale`, `pixi-currency-ledger-unreadable`, `pixi-currency-dream-unreadable`, `pixi-currency-pixi-toml-unreadable` |
| `general-docs-consistency` | `sources/general_docs_consistency.py` | `general-docs-consistency`, `general-docs-consistency-unevaluable`, `general-docs-agents-herald-marshal`, `general-docs-station-gate-advisory`, `general-docs-unreadable` |
| `docs-shelf-occupancy` | `sources/docs_shelf.py` | `docs-shelf-occupancy`, `docs-shelf-occupancy-unevaluable`, `docs-shelf-airgap-cluster`, `docs-shelf-bmad-output-root`, `docs-shelf-stale-archive-citation` |
| `capability-ledger` | `sources/capability_ledger.py` | `capability-ledger`, `capability-ledger-unevaluable` (each row rule, orphan-row to a-only-expiry-unquoted, is the evidence kind of a capability-ledger finding, not a code) |
| `chain-sprawl` | `sources/one_chain.py` | `chain-sprawl`, `chain-sprawl-unexempted`, `chain-sprawl-exempt`, `chain-sprawl-no-baseline`, `chain-sprawl-no-vocabulary` |
| `fr-without-cap` | `sources/one_chain.py` | `fr-without-cap`, `fr-without-cap-no-baseline`, `fr-cites-non-capability`, `fr-cap-unresolved`, `fr-id-unhyphenated`, `fr-id-malformed`, `fr-duplicate-id`, `fr-counted-run`, `fr-arrow-no-title-overlap`, `fr-baselined`, `fr-baseline-stale`, `fr-baseline-grown`, `fr-baseline-base-unread`, `fr-prd-unreadable` |
| `fold-complete` | `sources/one_chain.py` | `fold-complete`, `fold-complete-ok`, `fold-complete-incomplete`, `fold-complete-no-owner`, `fold-complete-no-station-dream`, `fold-complete-archived-in-live-tree`, `fold-complete-baselined`, `fold-complete-no-baseline` |
| `docs-map-hygiene` | `sources/docs_map_hygiene.py` | `docs-map-hygiene` |
| `live-proof-surface` | `sources/live_proof_surfaces.py` | `live-proof-surface` |
| `docs-currency` | `sources/docs_currency.py` | `docs-currency-ok`, `docs-currency-generated-stale`, `docs-currency-authored-stale`, `docs-currency-map-render`, `docs-currency-map-unreadable`, `docs-currency-skill-dir-hygiene` |
| `frontmatter-duplicate-keys` | `sources/frontmatter_duplicate_keys.py` | `frontmatter-duplicate-key`, `frontmatter-unreadable`, `frontmatter-duplicate-keys-unevaluable` |
| `writer-lock` | `sources/writer_lock.py` | `writer-lock`, `writer-lock-unevaluable` |

## Computed check sites

A `check=` whose code is not a literal, a module constant or a helper argument that resolves to one, or a helper the
resolution cannot follow (the reading rules above; none today: every helper's every caller binds its parameter, and
`_gather_engines` is a site of its own because it rebinds its parameter, `name = str(name)`). Each
site has its own row, and a new one fails the guard until its row is added here; that keeps "every diagnostic" true
without refactoring these call sites. Two sites in one function with one expression are one row.

| Module | Function | Expression | Codes come from |
|---|---|---|---|
| `__main__.py` | `_gather_engines` | `name` | the `NAME` given to `--engines` (`_run_check`'s `engines_name`), a warden DoctorCheck name `checks.registry` validated; the parameter is rebound as `str(name)` before `check=` |
| `sources/board.py` | `_gather_chain_completeness` | `item['kind']` | the `"kind"` literals of board.py's item dicts (the `chain-completeness` row of § Check codes) |
| `sources/board.py` | `_gather_chain_layers_audit` | `check` | the loop over `_CHAIN_AUDIT_CHECKPOINTS` (`chain-audit-checkpoint-*`), passed to `_checkpoint_finding` |
| `sources/chain.py` | `_gather_dream_chain` | `item['kind']` | chain.py's `"kind"` literals (the `dream-chain` row) |
| `sources/chain.py` | `_gather_dreams_hygiene` | `roster_err['kind']` | `_load_dream_roster`'s `dreams-hygiene-unevaluable` |
| `sources/chain.py` | `_gather_spec_surface` | `item['kind']` | chain.py's `"kind"` literals (the `spec-surface` row); two sites |
| `sources/chain.py` | `_gather_deferred_work` | `item['kind']` | chain.py's `"kind"` literals (the `deferred-work` row) |
| `sources/chain.py` | `_wrap_as_findings` | `item['kind']` | chain.py's `"kind"` literals (the `due-for-verification` row) |
| `sources/hygiene.py` | `_check_dead_test_scaffolding` | `HygieneFindingKind.DEAD_TEST_SCAFFOLDING.value` | `dead-test-scaffolding` |
| `sources/hygiene.py` | `_check_hollow_sprint_status` | `HygieneFindingKind.HOLLOW_SPRINT_STATUS.value` | `hollow-sprint-status` |
| `sources/hygiene.py` | `_check_orphan_files` | `HygieneFindingKind.ORPHAN_FILE.value` | `orphan-file` |
| `sources/hygiene.py` | `_check_readme_placeholder` | `HygieneFindingKind.README_PLACEHOLDER.value` | `readme-placeholder` |
| `sources/hygiene.py` | `_check_stale_dream_status` | `HygieneFindingKind.STALE_DREAM_STATUS.value` | `stale-dream-status` |
| `sources/ledger.py` | `gather` | `item['kind']` | ledger.py's `"kind"` literals (the `ledger-regression` row); two sites |
| `sources/status_body_consistency.py` | `gather_progress_phrase` | `f.check` | a Finding built with a literal code in the same module, re-sourced |
| `sources/status_body_consistency.py` | `gather_open_questions_reconcile` | `f.check` | as above |
| `sources/status_body_consistency.py` | `gather_promissory_language` | `f.check` | as above |
| `sources/status_body_consistency.py` | `gather_status_comment_reconcile` | `f.check` | as above |
| `sources/warden.py` | `gather` | `check.name` | each `pyforge.warden.engines.DoctorCheck` name; warden's contract lists them |

`cli_bridge.py`'s five `check=False` keywords are `subprocess.run` flags, not codes, and are not sites.

The one computed environment read:

| Module | Function | Key expression | Keys |
|---|---|---|---|
| `sources/sibling_dreams.py` | `_operator_token` | `key` | `GH_TOKEN`, `GITHUB_TOKEN` |

## Bridges and import closure

Every import that leaves the package and the standard library. `pyproject.toml` declares `jsonschema`, `mcp`,
`PyYAML` and `pyforge-core`; `pyforge-warden` is the optional `gate` extra (AD-1); `prometheus_client` and
`django_pyforge` are undeclared and guarded. Eight `pyforge.core` modules are imported; no other station's package is,
except warden's engines through the one declared relay (`tests/meta/test_source_independence.py`).

| Import | Kind | Imported by | For |
|---|---|---|---|
| `pyforge.core.verdict` | required | `verdict.py` | `Lattice`: the exit domain as a computed subset of warden's (spec-pyforge-core:CAP-3) |
| `pyforge.core.report` | required | `__main__.py` | `BASE_ENVELOPE_SCHEMA`, `compose`: the DoctorReport envelope (spec-pyforge-core:CAP-4) |
| `pyforge.core.hooks` | required | `hooks.py` | `HookSpec`, `PluginRegistry`: the `doctor-gather` and `doctor-prescribe` entry points |
| `pyforge.core.landing_evidence` | required | `bare_merge.py`, `sources/ledger.py`, `sources/marshal.py` | merge-subject and branch-name parsing (CAP-78, CAP-80) |
| `pyforge.core.published_loop` | required, function-local | `sources/marshal.py` | `fetch_story_tasks`: the published loop's run state for `story-status` |
| `pyforge.core.roster` | required | `sources/chain.py`, `sources/one_chain.py` | `STATIONS` |
| `pyforge.core.cutover_root` | required | `sources/capability_ledger.py`, `sources/writer_lock.py` | `root_of_record`, `LOCAL_DEV_RELATIVE`, `CutoverRootError` (spec-pyforge-core:CAP-13) |
| `pyforge.core.flags` | required | `sources/writer_lock.py` | `OVERLAYS_FILE_NAME`, a file name; no flag is read |
| `pyforge.warden.engines` | optional (`gate` extra), function-local | `sources/warden.py` | `run_doctor_checks` and its `DoctorCheck` rows; absent, one FAIL `pyforge-warden` |
| `django_pyforge.flags` | optional, function-local | `__main__.py` | `resolve_tree_path` for `doctor flags kill-switch` without `--flags-path` |
| `prometheus_client` | optional, guarded | `actuators/flag_kill_switch.py` | the `pyforge_doctor_flag_kill_switch_total{flag, reason}` counter |
| `mcp` | required, function-local | `sources/atlas.py` | `ClientSession`: cf_atlas over MCP first (AD-6) |
| `mcp.client.stdio` | required, function-local | `sources/atlas.py` | `stdio_client` to `.claude/tools/conda_forge_server.py` |
| `jsonschema` | required | `__main__.py`, `sources/docs_currency.py`, `sources/docs_map_hygiene.py` | `data/report-schema.json` and `data/docs-map-schema.json` |
| `yaml` | required | `sources/bmad_method.py`, `sources/capability_ledger.py`, `sources/chain.py`, `sources/docs_currency.py`, `sources/factory.py`, `sources/frontmatter_duplicate_keys.py`, `sources/frozen_path.py`, `sources/hygiene.py` | frontmatter, ledgers and manifests |
| `yaml.nodes` | required | `sources/frontmatter_duplicate_keys.py` | the duplicate-key-recording loader |

The other bridges are out of process, and `cli_bridge.py` is the one module that spawns a subprocess (AD-5): argv as a
list, never a shell, a timeout on every call, `NO_COLOR=1` set.

| Bridge | Through | For |
|---|---|---|
| warden's contract | `pyforge.warden.engines.run_doctor_checks`, `DoctorCheck`; `pyforge.warden.verdict.LATTICE` (read by `tests/meta/test_verdict_narrows_warden.py` only) | `warden-doctor`; the exit domain narrows warden's |
| atlas over MCP or CLI | MCP stdio to `.claude/tools/conda_forge_server.py`; else `cli_bridge.run_cli_json` on `.claude/scripts/conda-forge-expert/<axis script>.py --json` | the six atlas Sources (AD-6) |
| steward | `cli_bridge.run_argv`: `python -m pyforge.core.dispatch steward ci status --json` | `ci-pause-drift` (never steward's code, never GitHub) |
| platform-ci-test pytest | `cli_bridge.run_pytest` with `.pixi/envs/platform-ci-test/bin/python` on `src/platform/tests/policy` | `platform-policy-suite` |
| git | `cli_bridge.run_git` | ledgers at a ref, merge bases, changed paths, `git ls-files`, `git log` |
| repo scripts Doctor executes | `sources.locate_checkout_script`: from Doctor's own checkout, never the judged target; `scripts/fleet_scan.py` (`chain-layers-audit`), `scripts/pixi_env_matrix.py` (`bmad-drift`), the `scripts/docs_*.py` generators `docs/map.yaml` names (`docs-currency`, via `cli_bridge.run_check_script`) | the code those sources reuse |
| HTTP | `urllib`: the Pages root (`pages-liveness`), the GitHub Contents API (`sibling-dreams-drift`), npm, PyPI, anaconda.org and GitHub release APIs (`bmad-method-version-drift`'s upstream half) | the three network-reading sources |

## Inputs each source reads

What a root must provide for each Source to measure rather than report `<source>-unevaluable` (paths are repository
paths; `<p>` is `_bmad-output/projects/<p>/planning-artifacts`).

| Source | Reads |
|---|---|
| `warden-doctor` | `pyforge.warden.engines.run_doctor_checks(target)`: the engines installed in the environment |
| `staleness-report` | cf_atlas over MCP or `staleness_report.py --json` |
| `cve-watcher` | cf_atlas over MCP or `cve_watcher.py --json --severity C` |
| `behind-upstream` | cf_atlas over MCP or `behind_upstream.py --json` |
| `feedstock-health` | cf_atlas over MCP or `feedstock_health.py --json --filter stuck` and `--filter bad` |
| `release-cadence` | cf_atlas over MCP or `release_cadence.py --json` |
| `env-hygiene` | every `*.py` under the target, parsed (never executed), less git-ignored and test paths |
| `marshal-durability` | each project's tracked `<p>/sprint-status-ledger.yaml` and its git history; `<p>/marshal-policy.toml` |
| `adoption` | cf_atlas over MCP or `adoption_stage.py --json` and `version_downloads.py --json` |
| `ledger-regression` | each `<p>/sprint-status-ledger.yaml` at the base and head refs; `<p>/marshal-policy.toml`; the rekey maps `<p>/rekey-*.md` |
| `ledger-direction` | each ledger against the git history of `refs/remotes/origin/main` (bare and templated merges); the rekey maps |
| `story-status` | the Tier-3 feeds `_bmad-output/projects/pyforge-*/implementation-artifacts/sprint-status.yaml`, the tracked ledgers, loop run state (`.bmad-loop/runs/*/state.json`, the published loop) and merge history |
| `chain-completeness` | each project's `<p>/epics*.md`, `<p>/sprint-status-ledger.yaml`, `<p>/specs/spec-*/SPEC.md`, `<p>/prds/*/prd.md`; `docs/governance/guild-roster.json` |
| `dashboard-drift` | the absence of `docs/dashboard/data.js`, `docs/dashboard/generate.py`, `docs/dashboard/check_render.js`, `scripts/dashboard_watch.py` and the four retired console tasks in `pixi.toml` |
| `check-layout` | the absence of `docs/dashboard/data.js` and `docs/dashboard/generate.py` |
| `dream-chain` | `docs/dreams/*.md`; every Spec's `SPEC.md` frontmatter under `_bmad-output/projects/*/planning-artifacts/specs/` and `docs/governance/spec-*/`; each project's PRD, architecture and epics sharding; `docs/governance/guild-roster.json` |
| `spec-surface` | `scripts/.spec-surface-baseline.json`; every Spec's `surface:` and `surface-drift-exclude:` globs; `scripts/spec_surface_allowlist.txt`; `git ls-files` and `refs/remotes/origin/main` |
| `deferred-work` | each project's `<p>/deferred-work-ledger.md`; the Tier-3 `implementation-artifacts/deferred-work.md`; `scripts/.deferred-work-baseline.json`; story-spec frontmatter (`deferred:`, `followup_review_recommended`); `SPEC.md` `verified:` lines |
| `forward-dependency` | each project's `<p>/epics*.md` `**Deps:**` fields and `<p>/sprint-status-ledger.yaml` |
| `bmad-drift` | `_bmad-output/projects/pyforge-marshal/` (`.sync-baseline.json`, `SYNC-RUNBOOK.md`, the planning and Tier-3 trees it classifies); `pixi.toml`, `pixi.lock`; `scripts/pixi_env_matrix.py` (Doctor's checkout); `.claude/skills/`; `docs/dreams/`; `docs/governance/guild-roster.json` |
| `bmad-output-hygiene` | every project under `_bmad-output/projects/` (tests, `sprint-status.yaml`, `README.md`, files outside `hygiene_definitions`' allow-list); `docs/dreams/` |
| `due-for-verification` | each project's tracked `<p>/deferred-work-ledger.md` and the git churn of the paths its entries name |
| `bmad-method-version-drift` | the installed `_bmad/` manifest; `pixi.toml`'s declared floors; `recipes/bmad-suite/suite-members.yaml` and the `recipes/*/recipe.yaml` it names; upstream registries over HTTP (skipped under `--scope repo`) |
| `backlog-intake` | `_bmad-output/projects/*/planning-artifacts/deferred-work-ledger.md` |
| `sibling-dreams-drift` | `docs/dreams/*.md` and `archive/docs/dreams/*.md`; the sibling repository's `docs/dreams` over the GitHub Contents API with `GH_TOKEN` or `GITHUB_TOKEN` |
| `ci-pause-drift` | steward's `ci status --json` report |
| `pages-liveness` | the Pages root's `Last-Modified` (`PAGES_ROOT_URL`); `git log` of the published inputs (`docs/index.md`, `docs/404.md`, the four quadrants, `docs/dashboard`, `docs/foundry/marketplace`, `docs-site`, `docs/map.yaml`) |
| `dreams-hygiene` | `docs/dreams/*.md` frontmatter and bodies; the `docs/dreams/README.md` table; `docs/governance/guild-roster.json`; Spec statuses |
| `chain-layers-audit` | one project's planning chain through `scripts/fleet_scan.py` (Doctor's checkout) and `dream-chain`'s orphan index |
| `platform-policy-suite` | `src/platform/tests/policy`; the `platform-ci-test` environment's interpreter |
| `bmad-render-config-ambiguity` | `_bmad/config.toml`, `_bmad/config.user.toml`, `_bmad/custom/config.toml`, `_bmad/custom/config.user.toml` |
| `frozen-path-changed` | `docs/foundry/capability-ledger.yaml` (schema `pyforge.capability-ledger/v1`); the paths changed between `refs/remotes/origin/main` and `HEAD` |
| `capability-effect` | every Spec's capabilities and `verified:` lines; each project's `epics.md` `Surface:` lines; `git grep` of the code outside its tests |
| `status-body-consistency` | Spec, story-spec and Dream frontmatter and bodies; each `.memlog.md`; `<p>/sprint-status-ledger.yaml`; `docs/governance/guild-roster.json` |
| `pixi-currency-ledger` | `archive/docs/dreams/pixi-candidate-currency.md`'s four ledgers; `pixi.toml`'s git history |
| `general-docs-consistency` | station `README.md` files against `.claude/skills/*/skill-brief.yaml`; `AGENTS.md` against `docs/dreams/pyforge-herald.md` |
| `docs-shelf-occupancy` | `docs/MAP.md`'s "Outside this map" table; the `_bmad-output/` root; the air-gap pair under `docs/how-to/` and `docs/explanation/` |
| `capability-ledger` | `docs/foundry/capability-ledger.yaml`; the live `SPEC.md` files; each station's `sprint-status-ledger.yaml`; the flag tree through `root_of_record`; an injected clock |
| `chain-sprawl` | `docs/dreams/*.md`; the Spec folders; `docs/governance/chain-sprawl-baseline.json`; `docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md`; `docs/governance/guild-roster.json` |
| `fr-without-cap` | every station PRD `<p>/prds/*/prd.md`; the station Specs' capability definitions; `docs/governance/fr-baseline.json` at `HEAD` and at the merge base |
| `fold-complete` | `archive/docs/dreams/`; the station Dreams `docs/dreams/pyforge-*.md`; `docs/governance/fold-complete-baseline.json` |
| `docs-map-hygiene` | `docs/MAP.md`; `docs/tutorials/`, `docs/how-to/`, `docs/reference/`, `docs/explanation/`; `docs/map.yaml` against `data/docs-map-schema.json` |
| `live-proof-surface` | this Spec folder's `live-proof-surfaces.md` (CAP-77's catalog); the paths the change touched |
| `docs-currency` | `docs/map.yaml`, `docs/MAP.md`, the mapped pages and their `git log`; the `scripts/docs_*.py` generators (Doctor's checkout); `.claude/skills/` |
| `frontmatter-duplicate-keys` | every tracked story spec `_bmad-output/projects/*/planning-artifacts/specs/spec-*.md` (`git ls-files`) |
| `writer-lock` | `src/platform/config/flags.json` and `flag-overlays.json` at the merge base (`git show`); `docs/governance/guild-roster.json` (`roots.this`, the `chain-write-off-the-writer` session denial); the changed paths |

## Identity constants

Literals that name this repository or its published identity. A rebuild on another root changes these rows and nothing
else of the contract.

| Constant | Module | Value | Use |
|---|---|---|---|
| `PAGES_ROOT_URL` | `sources/pages_liveness.py` | `https://rxm7706.github.io/local-recipes/` | the published Pages root `pages-liveness` probes |
| `_SIBLING_OWNER` | `sources/sibling_dreams.py` | `openteams-ai` | the sibling repository's owner |
| `_SIBLING_REPO` | `sources/sibling_dreams.py` | `mgmt-wf-python-modernization` | the sibling repository |
| `$id` | `data/report-schema.json` | `urn:local-recipes:pyforge-doctor:report-schema` | the DoctorReport schema (frozen; additive changes only) |
| `$id` | `data/docs-map-schema.json` | `urn:local-recipes:pyforge-doctor:docs-map-schema` | the `docs/map.yaml` schema (CAP-90) |

## Scripts outside the package

Scripts under `scripts/` that realize a capability of this Spec, and two that belong to other chains and are named so
nobody counts them as Doctor's.

| Script | Realizes | Chain |
|---|---|---|
| `scripts/fleet_picture.py` | CAP-32, CAP-44 and CAP-58: the ambient fleet report (never a gate) | spec-pyforge-doctor |
| `scripts/deferred_work_promote.py` | CAP-45, CAP-46 and CAP-47 (each retired 2026-11-10: a closed one-time campaign); the script stays | spec-pyforge-doctor |
| `scripts/spec_surface_check.py` | CAP-59: the scoped `--write-baseline` stamp | spec-pyforge-doctor |
| `scripts/fr_baseline.py` | CAP-92: the only writer of `docs/governance/fr-baseline.json` | spec-pyforge-doctor |
| `scripts/flag_inventory.py` | spec-feature-flag-governance:CAP-7 (doctor Story 34.4): the per-station flag inventory report | spec-feature-flag-governance |
| `scripts/mason_cfe_surface_check.py` | Mason's CFE-surface guard (FR-45, AD-15) | spec-pyforge-mason, not Doctor's |
| `scripts/memlog_fidelity_check.py` | the memlog fidelity harness (Epic 44) | spec-python-foundry-cutover, not Doctor's |

## Python floor

Python 3.14 (decision D6). `pyproject.toml` declares `requires-python` as `>=3.14`, `[tool.ruff]` declares
`target-version` as `py314`, and `[tool.mypy]` declares `python_version` as `3.14`.
