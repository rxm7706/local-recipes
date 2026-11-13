# Public contract — Warden

Companion to `SPEC.md` (CAP-28, FR-45; decision D1 of the 2026-11-10 cutover readiness plan). It lists every
surface a caller of warden reaches, so a second root can rebuild that surface from the Spec folder alone: the CLI
verb and every flag, the `[tool.pyforge-warden]` keys, the exit codes, status rungs, error kinds and finding-id
families, the feature flags with their value in each environment, the environment variables warden reads and the ones
it sets, the MCP tools and the operator management commands of its portal package, `django-warden`; then the hook
book, the report's open slots, the engines and bundled data, the symbols other packages import and where each
capability's code lives (sections 8 to 11 and *Where each capability lives*, Story 26.3). The proof map is
`proof-map.md` (Story 26.2).

The guard is `src/shared/packages/pyforge-warden/tests/meta/test_public_contract.py`. It derives each inventory from
the code (the parser `cli._build_parser()` builds, `config._RECOGNIZED_KEYS` and `config.EffectiveConfig`,
`verdict.LATTICE`, `models.Status`, `models.ErrorKind`, the finding-id families in `models.py`, the bundled report
schema, an AST scan of the kernel and of `django-warden` for flag constants and environment reads and sets, the
`@server.tool()` functions of `mcp_asgi.py` and the files under `management/commands/`) and compares it both ways with
the tables below: an item the code has and this file does not list fails as unlisted, and a row naming something the
code no longer has fails as a stale row. A change that adds a flag, key, rung, error kind, feature flag, variable, tool
or command adds its row here in the same change.

How the test reads this file: only the table rows under the eleven headings of sections 1 to 7, which must stay
exact. In each row it reads the backticked tokens of the first cell, and the cells this file's tables name as checked:
a key's default and CLI flag, a rung's order and exit, a feature flag's four values and its readers, a variable's unit,
role and modules, a tool's arguments, a command's arguments and flag, and that the last cell cites a CAP where the
table has one. Prose is not read. Module paths are relative to each package's `src/` directory: `pyforge/warden/` is the kernel
(`src/shared/packages/pyforge-warden/src/`), `django_warden_fabric/` is `django-warden`
(`src/shared/packages/django-warden/src/`).

Sections 8 to 11 and *Where each capability lives* are held the same way, both ways, by
`src/shared/packages/pyforge-warden/tests/meta/test_contract_surface.py`: the hook specs, the entry points of the
package's `pyproject.toml` and the optional scanner ids; the key sets the report's open slots are emitted with; the
engines' range constants, the bundled data and the refresh scripts; every `pyforge.warden` import a tracked file under
`src/` or `scripts/` outside the package makes (read as text, so a subprocess source string counts); and per
capability, the Spec's CAP ids, the paths named (each must exist) and the Specs whose `surface:` covers them. It reads
the backticked tokens of each row's first cell and of the cells its tables name below; prose is not read.

## 1. CLI

The program is `warden` (`[project.scripts] warden = "pyforge.warden.cli:main"`). Its one verb is `warden scan <path>`,
which is the same verb as `pyforge warden scan <path>` through pyforge-core's `pyforge` dispatcher; run either from the
repository root. `-h`/`--help` on both parsers is argparse's own and is not listed. `--doctor` is a flag on `scan`, not
a second verb. A usage error, `--bypass` without `--reason` included, exits 2. A CLI flag overrides the
`[tool.pyforge-warden]` key of the same name (section 2). The rows are the verb, its positional, its 23 options,
then the top-level `--version`.

| Argument | Form and default | CAP |
|---|---|---|
| `scan` | The one verb: scan a project directory and emit the compliance report. | CAP-1 |
| `<path>` | Positional and optional: the directory to scan; default `.`. | CAP-1 |
| `--format` | `text` (default) or `json`. `json` puts exactly one schema-valid `ComplianceReport` on stdout; `text` prints one summary line that is not contract. | CAP-7 |
| `--sbom-output` | `PATH`; unset by default. Writes a CycloneDX 1.6 SBOM to `PATH` beside the report; a render or write failure is a stderr diagnostic and never changes the exit code. | CAP-7 |
| `--deterministic` | Switch. Accepted and changes nothing today: the report is already byte-identical by default (the flag stays reserved, operator ruling 2026-11-10). | CAP-10 |
| `--allow-empty` | Switch. When manifests parse but extraction yields nothing, the exit is 0 while the status stays `indeterminate`. | CAP-3 |
| `--fail-on` | `critical`, `high`, `medium`, `low` or `none`; unset by default, so the `fail-on` key, else `critical`. The vulnerability tier at or above which a finding composes `policy-violation`. | CAP-5 |
| `--fail-under-coverage` | A number in [0, 100]; unset by default, so the key, else 0.0 (off). An axis whose coverage falls below it composes `indeterminate`. | CAP-5 |
| `--allow-licenses` | `SPDX_IDS`, comma-separated. A resolved licence not in the list is denied; activates licence gating. | CAP-5 |
| `--deny-licenses` | `SPDX_IDS`, comma-separated. A resolved licence in the list is denied, over `--allow-licenses`; activates licence gating. | CAP-5 |
| `--max-lag` | `N`, a non-negative integer. A component more than N releases behind composes `policy-violation`; activates currency gating. | CAP-5 |
| `--require-lts` | Switch. Activates currency gating; it performs no LTS-specific enforcement. | CAP-5 |
| `--fail-on-eol` | Switch. An `eol` currency verdict composes `policy-violation`. | CAP-5 |
| `--warn-as-error` | Switch. A composed `warn` exits 1; the status stays `warn`. | CAP-5 |
| `--min-epss` | `N` in [0, 1]. An EPSS score at or above N composes `policy-violation`; an absent or stale EPSS feed then composes at least `indeterminate`. | CAP-5 |
| `--bypass` | Switch; needs `--reason`. Every still-non-clean finding becomes `bypassed` and a `.warden-waivers.yaml` stanza is printed to stdout, never written. | CAP-6 |
| `--reason` | Text: the waiver reason the `--bypass` stanza records. No prompts, ever. | CAP-6 |
| `--warn-only` | Switch. Every still-blocking rung is downgraded to `warn` before the verdict composes. | CAP-9 |
| `--doctor` | Switch. An environment self-check instead of a scan (engines, the offline OSV database, the KEV, EPSS and end-of-life feeds): exit 0 when healthy, else 2, never 1. | CAP-8 |
| `--baseline` | `PATH` to a committed `.warden-baseline.yaml`; the findings it lists are suppressed. A missing or invalid file is a loud error. | CAP-9 |
| `--baseline-emit` | Switch. Prints candidate baseline entries (stdout under `text`, stderr under `json`); never changes the status or the exit. | CAP-9 |
| `--open-fix-prs` | Switch. The post-verdict fix-PR actuator; credentials and repo from the environment (section 5). | CAP-12, CAP-24 |
| `--fix-prs-dry-run` | Switch. Plans the actuator and opens no socket; wins over `--open-fix-prs`. | CAP-12, CAP-24 |
| `--pixi-environment` | `NAME`. Scopes `pixi.lock` extraction to one pixi environment. | CAP-18 |
| `--pixi-platform` | `PLATFORM` under that environment; the host's platform when unset, for interactive scans only. | CAP-18 |
| `--version` | Top level, before the verb: prints `warden <version>` and exits 0. | CAP-1 |

## 2. Configuration keys

The 13 keys of a `[tool.pyforge-warden]` table in `pyproject.toml` and/or `pixi.toml`, beside the scanned project.
Precedence per key: the CLI flag, then `pyproject.toml`, then `pixi.toml`, then the default below. A conflict between the
two files is reported by name and value on stderr and never changes the exit code; an unrecognized key is a
`config-validation` error (exit 2). A key with no CLI flag is set in TOML only. `fix-pr-estate-repos` names both roots,
A and B, so the actuator needs no `pyforge.cutover_root` read (decision D3).

| Key | Default | CLI flag | CAP |
|---|---|---|---|
| `fail-on` | `critical` | `--fail-on` | CAP-5 |
| `fail-under-coverage` | `0.0` (off) | `--fail-under-coverage` | CAP-5 |
| `dep001-block-confidence` | `verified` (the other value is likely) | none (TOML only) | CAP-5 |
| `waiver-default-expiry-days` | `14` | none (TOML only) | CAP-6 |
| `fail-on-kev` | `true` | none (TOML only) | CAP-5 |
| `allow-licenses` | empty | `--allow-licenses` | CAP-5 |
| `deny-licenses` | empty | `--deny-licenses` | CAP-5 |
| `max-lag` | unset | `--max-lag` | CAP-5 |
| `require-lts` | `false` | `--require-lts` | CAP-5 |
| `fail-on-eol` | `false` | `--fail-on-eol` | CAP-5 |
| `warn-as-error` | `false` | `--warn-as-error` | CAP-5 |
| `min-epss` | unset | `--min-epss` | CAP-5 |
| `fix-pr-estate-repos` | `rxm7706/local-recipes`, `rxm7706/python-foundry` | none (TOML only) | CAP-24 |

## 3. Exit codes, status rungs, error kinds and finding ids

`verdict.py` is the sole owner of the lattice and the exit projection; the full projection, how engine exit codes are
read and the never-false-green corpus are in `verdict-contract.md`.

### 3.1 Exit codes

The set is frozen and closed: adding a code is a MAJOR change.

| Exit | Means |
|---|---|
| `0` | `clean`, `warn`, `bypassed` or `not-applicable`; the sanctioned exit downgrades (`--allow-empty`, `--warn-only`); a healthy `--doctor`; `--version` and `--help`. |
| `1` | `policy-violation` or `indeterminate`; a `warn` under `--warn-as-error`. |
| `2` | `error`: an operational failure of one of the error kinds below, a usage error, or an unhealthy `--doctor`. |
| `130` | Interrupted (SIGINT). |

### 3.2 Status rungs

The seven rungs, in lattice order (1 is the strongest), with the exit each projects to.

| Rung | Order | Exit |
|---|---|---|
| `error` | 1 | 2 |
| `policy-violation` | 2 | 1 |
| `indeterminate` | 3 | 1 |
| `warn` | 4 | 0 |
| `bypassed` | 5 | 0 |
| `clean` | 6 | 0 |
| `not-applicable` | 7 | 0 |

### 3.3 Error kinds

The nine typed error kinds (a closed set); each composes the `error` rung and exit 2. An error's status driver uses the
reserved `error:<kind>:<subject>` id, outside the finding-id families.

| Error kind | Routed to |
|---|---|
| `unparsable-manifest` | the developer |
| `engine-unavailable` | the platform |
| `engine-output-unrecognized` | the tool's maintainers |
| `engine-output-unparseable` | the tool's maintainers |
| `engine-execution-failed` | the tool's maintainers |
| `engine-timeout` | the tool's maintainers |
| `config-parse` | the tool's maintainers |
| `config-validation` | the tool's maintainers |
| `internal-error` | the tool's maintainers |

### 3.4 Finding-id families

Every finding id is one of these families; ids are stable, deterministic and single-line, and every family is
waivable with an expiry. The grammar and its verdict encoding are in `verdict-contract.md` and
`_bmad-output/projects/pyforge-warden/planning-artifacts/finding-id-verdict-encoding-decision.md`.

| Family | Id grammar |
|---|---|
| `vuln` | `vuln:<advisory-id>:<pkg>@<ver>` |
| `hygiene` | `hygiene:<DEP-code>:<module-or-pkg>` |
| `indeterminate` | `indeterminate:<reason>:<pkg>` |
| `license` | `license:<spdx-id-or-unknown>:<pkg>@<ver>` |
| `currency` | `currency:<reason>:<subject>@<ver>`, the reason one of eol, over-lag and unknown |

### 3.5 Report schema

The report's JSON Schema ships in the package as `data/report-schema.json`; `report.REPORT_SCHEMA_VERSION` stamps each
report. The schema is frozen at 1.1.0 (operator ruling 2026-11-10): no story widens it.

| Schema `$id` | Version |
|---|---|
| `urn:local-recipes:pyforge-warden:report-schema` | `1.1.0` |

## 4. Feature flags

The nine `pyforge.warden.*` keys: the value of each in `src/platform/config/flags.json` (its `defaultVariant`) and, per
environment, as `src/platform/config/flag-overlays.json` composes it; the modules that read it; what flag-off does.

| Key | flags.json | dev | staging | production | Reader | Flag-off behaviour |
|---|---|---|---|---|---|---|
| `pyforge.warden.fix_target_resolution` | off | on | on | off | `pyforge/warden/actuator.py` | The upgrade proposal cites the advisory and the current version; no target version is resolved (CAP-24). |
| `pyforge.warden.fix_manifest_edit` | off | on | on | off | `pyforge/warden/actuator.py` | The fix pull request carries no manifest diff (CAP-24). |
| `pyforge.warden.fix_draft_pr_estate` | off | on | on | off | `pyforge/warden/actuator.py` | No draft pull request opens on an estate repo (CAP-24). |
| `pyforge.warden.sast_opengrep` | off | on | on | off | `pyforge/warden/cli.py`, `pyforge/warden/sast.py` | `opengrep` is not a selectable optional scanner, even when `WARDEN_OPTIONAL_SCANNERS` names it (CAP-25). |
| `pyforge.warden.non_python_ecosystems` | off | on | on | off | `pyforge/warden/cli.py` | Non-Python lockfiles (npm, Go, Cargo and the other ecosystems osv-scanner parses natively) are not discovered (CAP-26). |
| `pyforge.warden.fleet_inventory` | off | on | on | off | `django_warden_fabric/management/commands/warden_fleet_inventory.py`, `django_warden_fabric/views.py` | The portal action refuses (HTTP 403) and `warden_fleet_inventory` is listed as disabled and exits 2 (CAP-29). |
| `pyforge.warden.fleet_scan` | off | on | on | off | `django_warden_fabric/management/commands/warden_fleet_run.py` | `warden_fleet_run` is listed as disabled and exits 2: no fleet run starts (CAP-29). |
| `pyforge.warden.fleet_fix_proposals` | off | on | on | off | `django_warden_fabric/management/commands/warden_fleet_approve.py`, `django_warden_fabric/proposals.py`, `django_warden_fabric/views.py` | A fleet scan queues no proposal, an approve is refused (the portal action with HTTP 403), and `warden_fleet_approve` is listed as disabled and exits 2 (CAP-29). |
| `pyforge.warden.fleet_project_items` | off | on | on | off | `django_warden_fabric/management/commands/warden_fleet_project_items.py`, `django_warden_fabric/views.py` | The portal action refuses (HTTP 403) and `warden_fleet_project_items` is listed as disabled and exits 2 (CAP-29). |

`PYFORGE_ENVIRONMENT` unset means dev, so a run in this repository reads all nine on; staging reads them on and
production off. Every reader passes default False, so a run that resolves no flag tree reads them off, with one named
WARN on stderr. Flags are read through `pyforge.core.flags.read_boolean`, whose contract (pyforge-core's) names
`PYFORGE_FLAGS_PATH` and `PYFORGE_ENVIRONMENT`: the management commands reach it through `require` and `disabled_help`,
and `proposals.py` calls it directly; the portal views evaluate the same composed tree through
`django_pyforge.flags.evaluate_from_source`, also with default False.

## 5. Environment variables

Each row is one variable in one unit and one role. The kernel's roles: `read` (the scan and the actuator read it) and
`set for engine` (the kernel sets it in an engine subprocess's environment). `django-warden`'s roles: `read`,
`pass-through` (credentials a fleet `git` call inherits through `os.environ`, never put in argv or a URL), `set` (set
for the actuator or the in-process scan) and `setting` (a Django setting the host's settings module may define). The
kernel reads exactly seven variables and sets exactly four for engines.

| Variable | Unit | Role | Where | CAP |
|---|---|---|---|---|
| `GITHUB_TOKEN` | kernel | read | `pyforge/warden/actuator.py` | CAP-12: the forge token, first choice |
| `GH_TOKEN` | kernel | read | `pyforge/warden/actuator.py` | CAP-12: the forge token when `GITHUB_TOKEN` is unset |
| `GITHUB_REPOSITORY` | kernel | read | `pyforge/warden/actuator.py` | CAP-12: the target repo, `owner/name` |
| `GITHUB_API_URL` | kernel | read | `pyforge/warden/actuator.py` | CAP-12: the API base, else the public GitHub API |
| `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` | kernel | read | `pyforge/warden/vuln.py` | CAP-11: the offline OSV database root; unset means no database and an `indeterminate` vulnerability axis |
| `PYFORGE_WARDEN_FEED_CACHE_DIR` | kernel | read | `pyforge/warden/feeds.py` | CAP-11: the KEV, EPSS and end-of-life cache root; no default |
| `WARDEN_OPTIONAL_SCANNERS` | kernel | read | `pyforge/warden/scanner_plugins.py` | CAP-27: comma-separated optional scanner ids to enable (CAP-23, CAP-25) |
| `NO_COLOR` | kernel | set for engine | `pyforge/warden/engines.py` | CAP-10: `1` for every engine subprocess, through the single subprocess helper |
| `SEMGREP_SEND_METRICS` | kernel | set for engine | `pyforge/warden/engines.py` | CAP-25: `off` for opengrep |
| `OPENGREP_ENABLE_VERSION_CHECK` | kernel | set for engine | `pyforge/warden/engines.py` | CAP-25: `0` for opengrep |
| `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` | kernel | set for engine | `pyforge/warden/engines.py`, `pyforge/warden/native_lockfiles.py` | CAP-11, CAP-26: the resolved database root, handed to osv-scanner |
| `WARDEN_FLEET_TARGET_CONFIG` | django-warden | read | `django_warden_fabric/fleet_inventory.py` | CAP-29: the fleet target config, else `.warden/fleet-target.toml` under the checkout |
| `WARDEN_FLEET_INVENTORY_PATH` | django-warden | read | `django_warden_fabric/fleet_inventory.py` | CAP-29: the inventory export, else `.warden/fleet-inventory.json` |
| `WARDEN_FLEET_PROJECT_ITEMS_PATH` | django-warden | read | `django_warden_fabric/fleet_project_items.py` | CAP-29: the project-items export, else `.warden/fleet-project-items.json` |
| `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` | django-warden | read | `django_warden_fabric/tasks.py` | CAP-29: read only to restore the worker's own value after a fleet scan |
| `GITHUB_TOKEN` | django-warden | pass-through | `django_warden_fabric/fleet.py` | CAP-29 |
| `GH_TOKEN` | django-warden | pass-through | `django_warden_fabric/fleet.py` | CAP-29 |
| `GH_ENTERPRISE_TOKEN` | django-warden | pass-through | `django_warden_fabric/fleet.py` | CAP-29 |
| `GITHUB_ENTERPRISE_TOKEN` | django-warden | pass-through | `django_warden_fabric/fleet.py` | CAP-29 |
| `GITHUB_REPOSITORY` | django-warden | set | `django_warden_fabric/tasks.py` | CAP-29: the approved proposal's repo, in the environment handed to the actuator |
| `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` | django-warden | set | `django_warden_fabric/tasks.py` | CAP-29: the fleet scan's offline databases, for the in-process scan only |
| `WARDEN_OSV_DB_CACHE_DIRECTORY` | django-warden | setting | `django_warden_fabric/tasks.py` | CAP-29: the per-ecosystem offline databases the fleet worker scans against |
| `WARDEN_FLEET_APPROVAL_EXPIRY_SECONDS` | django-warden | setting | `django_warden_fabric/fleet.py`, `django_warden_fabric/tasks.py` | CAP-29: the approval expiry, default 604800 (seven days) |
| `COMPLIANCE_FACE_BLOB_ROOT` | django-warden | setting | `django_warden_fabric/tasks.py`, `django_warden_fabric/views.py` | CAP-16: where uploaded manifests are kept, default the system temp directory |

`PYFORGE_ENVIRONMENT` and `PYFORGE_FLAGS_PATH` reach warden only through `pyforge.core.flags` (section 4), never read by
warden's own code. The portal's start tool (section 6) hands `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` and
`PYFORGE_WARDEN_FEED_CACHE_DIR` through to the `warden scan` it runs.

## 6. MCP tools

Warden's station face is `POST /stations/warden/mcp` on the platform host: `django-warden`'s `mcp_asgi.py` builds it
(`build_warden_mcp_asgi`, mounted by the app config's `mcp_asgi_app`). Both tools need an assertion, and neither reuses
another station's tool name. `start_audit` returns a handle at once and runs the supervisor runner `run_audit`, the
warden row of django-pyforge's closed verb table (Epic 119): `warden scan <target> --format json` in the
`pyforge-warden` environment, the target a directory under the checkout (the portal's default is `src/platform`),
results 0 and 1 (2 is an audit that did not finish).

| Tool | Arguments | Returns | CAP |
|---|---|---|---|
| `start_audit` | `target`, `assertion` | A handle, at once; a run bound comes back as the projected refusal the portal renders. | spec-pyforge-unifying-strategy:CAP-4, spec-pyforge-unifying-strategy:CAP-20 |
| `get_audit` | `handle`, `assertion` | The supervisor run for that handle. | spec-pyforge-unifying-strategy:CAP-4, spec-pyforge-unifying-strategy:CAP-20 |

## 7. Management commands

The four operator commands of `django-warden`, run through the platform host's `src/platform/manage.py`. Each refuses
while its flag is off: its help is marked disabled and it exits 2. Nothing starts a fleet run but `warden_fleet_run`.

| Command | Arguments | Flag | What it does | CAP |
|---|---|---|---|---|
| `warden_fleet_inventory` | none | `pyforge.warden.fleet_inventory` | Inventories every repo of the operator-designated github.com organisation (read from the gitignored fleet target config) and prints the run id; a bad config exits 1. | CAP-29 |
| `warden_fleet_run` | `organisation` | `pyforge.warden.fleet_scan` | Starts a fleet run over every inventoried repo of the organisation, one `warden scan` verdict per repo, and prints the run id. | CAP-29 |
| `warden_fleet_approve` | `proposal_id`, `--operator` | `pyforge.warden.fleet_fix_proposals` | Approves one queued fix proposal so it opens as a draft PR; `--operator` (default `cli`) is recorded on the approval; a refused approve is a command error. | CAP-29 |
| `warden_fleet_project_items` | none | `pyforge.warden.fleet_project_items` | Inventories the items of the operator-designated github.com Projects and prints the run id; a bad config exits 1. | CAP-29 |

## 8. Hook specs, plugin entry points and optional scanner ids

Warden's PR gate is a hook book on pyforge-core's shared registration API, `pyforge.core.hooks` (CAP-27). Warden owns
all three hook specs; scanners attach to scan and aggregate, and only warden publishes on the verdict spec
(`hooks.publish_pr_gate_verdict`, owner-matched). `verdict.py` stays the sole owner of the lattice and the exit
projection; a hook never projects an exit.

### 8.1 Hook specs

The test derives this table from `hooks.PR_GATE_HOOK_SPECS` and reads each row's owner.

| Hook spec | Owner | What plugins do there | CAP |
|---|---|---|---|
| `pyforge.warden.pr_gate.scan` | `warden` | Every scanner plugin, default and optional, attaches here (`around`). | CAP-27 |
| `pyforge.warden.pr_gate.aggregate` | `warden` | Scanner plugins may attach to fold their output before the verdict. | CAP-27 |
| `pyforge.warden.pr_gate.verdict` | `warden` | Owner-matched: only warden's `WardenVerdictOwner` publishes; a second publisher is refused. | CAP-27 |

### 8.2 Plugin entry points

The package declares one entry-point group, `pyforge.core.hooks` (core's `ENTRY_POINT_GROUP`), and no other: never a
`pyforge.warden.hooks` or `pyforge.warden.plugins` group. Warden does not `load_entry_points()` the shared group (other
stations' plugins would load); `scanner_plugins.scanner_plugin_registry()` registers its own plugins in-tree. The
test reads each row's object, scanner id and kind (`default` runs in every scan; `optional` runs only when enabled).

| Entry point | Object | Scanner id | Kind | CAP |
|---|---|---|---|---|
| `warden-null` | `pyforge.warden.scanner_plugins:NullScanPlugin` | `null` | default | CAP-27 |
| `warden-deptry` | `pyforge.warden.scanner_plugins:DeptryScanPlugin` | `deptry` | default | CAP-27 |
| `warden-osv` | `pyforge.warden.scanner_plugins:OsvScanPlugin` | `osv` | default | CAP-27 |
| `warden-license` | `pyforge.warden.scanner_plugins:LicenseScanPlugin` | `license` | default | CAP-27 |
| `warden-currency` | `pyforge.warden.scanner_plugins:CurrencyScanPlugin` | `currency` | default | CAP-27 |
| `warden-checkmarx` | `pyforge.warden.scanner_plugins:CheckmarxScanPlugin` | `checkmarx` | optional | CAP-27 |
| `warden-sonar` | `pyforge.warden.scanner_plugins:SonarScanPlugin` | `sonar` | optional | CAP-27 |
| `warden-blackduck` | `pyforge.warden.scanner_plugins:BlackduckScanPlugin` | `blackduck` | optional | CAP-27 |
| `warden-ghas` | `pyforge.warden.scanner_plugins:GhasScanPlugin` | `ghas` | optional | CAP-27 |
| `warden-profile-local` | `pyforge.warden.scanner_plugins:ProfileLocalScanPlugin` | `profile-local` | optional | CAP-27 |

### 8.3 Optional scanner ids

The seven ids of `scanner_plugins.OPTIONAL_SCANNER_IDS`, each enabled by naming it in `WARDEN_OPTIONAL_SCANNERS`
(comma-separated, section 5). An unknown id is a `config-validation` error (exit 2); an enabled id whose plugin is
absent is omitted, not an error (`OPTIONAL_ABSENT_IS_NOT_FAILURE`). `opengrep` and `tea-test-review` are ids, not entry
points: their plugins are registered directly in `scanner_plugin_registry()` and append advisory notes (section 9),
never a finding. The five stubs append one schema-legal `indeterminate:<id>:plugin` finding each. The test reads each
row's entry points (`none` when there is none) and plugin class.

| Scanner id | Entry point | Plugin class | How it runs | CAP |
|---|---|---|---|---|
| `checkmarx` | `warden-checkmarx` | `CheckmarxScanPlugin` | Stub: no vendor SDK. | CAP-27 |
| `sonar` | `warden-sonar` | `SonarScanPlugin` | Stub: no vendor SDK. | CAP-27 |
| `blackduck` | `warden-blackduck` | `BlackduckScanPlugin` | Stub: no vendor SDK. | CAP-27 |
| `ghas` | `warden-ghas` | `GhasScanPlugin` | Stub: no vendor SDK; the SAST slot `opengrep` sits beside it. | CAP-27 |
| `profile-local` | `warden-profile-local` | `ProfileLocalScanPlugin` | Stub. | CAP-27 |
| `opengrep` | none | `OpengrepScanPlugin` | Runs the `opengrep` engine (section 10.1) with the bundled `sast-rules/`; selectable only while the flag `pyforge.warden.sast_opengrep` is on (section 4). | CAP-25 |
| `tea-test-review` | none | `TeaAdvisoryScanPlugin` | Runs BMAD TEA's `tea-test-review` (section 10.1); refuses with `config-validation` when the `suite:AD-9` module roster (steward's spine) has no `tea` entry. | CAP-23 |

## 9. The report's open slots

The report schema stays closed and frozen at 1.1.0 (section 3.5, operator ruling 2026-11-10): no story widens it. Its
`advisory` (array or null) and `actuation` (object or null) properties carry no inner schema, so this table is their
only typing: the key set each record is emitted with, and the builder that emits it. Neither slot ever moves a rung, the
status or the exit code. `advisory` is null unless an optional advisory scanner contributed a note; `actuation` is null
unless `--open-fix-prs` or `--fix-prs-dry-run` ran. The test drives each builder and reads each row's keys, its optional
keys (present only when set) and that its builder cell names a module that exists.

| Record | Keys | Optional keys | Built by |
|---|---|---|---|
| `advisory[] (opengrep)` | `tool`, `rule_id`, `path`, `line`, `severity`, `summary` | none | `pyforge/warden/sast.py`: `OpengrepAdvisoryNote.to_dict` (CAP-25) |
| `advisory[] (tea-test-review)` | `tool`, `score`, `recommendation`, `summary` | none | `pyforge/warden/tea_advisory.py`: `TeaAdvisoryScanPlugin`, a run with a trusted verdict (CAP-23) |
| `advisory[] (tea-test-review, skipped)` | `tool`, `skipped`, `reason`, `summary` | none | `pyforge/warden/tea_advisory.py`: `TeaAdvisoryScanPlugin`, a run that started and gave no trusted verdict (CAP-23) |
| `actuation` | `dry_run`, `outcomes` | none | `pyforge/warden/actuator.py`: `Actuation.to_json_dict` (CAP-12, CAP-24) |
| `actuation.outcomes[]` | `finding_id`, `action`, `subject`, `status`, `pr_url`, `detail` | `fix_resolution`, `manifest_fix`, `ecosystem` | `pyforge/warden/actuator.py`: one per proposal, sorted by `finding_id`; `status` is `planned`, `opened`, `skipped` or `failed` (CAP-12, CAP-24, CAP-26) |
| `actuation.outcomes[].fix_resolution` | `target`, `candidates`, `attempts`, `solver`, `failure_detail` | none | `pyforge/warden/fix_solver.py`: `FixTargetResolution.to_json_dict` (CAP-24) |
| `actuation.outcomes[].fix_resolution.attempts[]` | `candidate`, `verdict` | none | `pyforge/warden/fix_solver.py`: `verdict` is `accepted` or `rejected` (CAP-24) |
| `actuation.outcomes[].manifest_fix` | `files` | none | `pyforge/warden/actuator.py` from `manifest_fixup.ManifestFixPlan` (CAP-24) |
| `actuation.outcomes[].manifest_fix.files[]` | `path`, `content` | none | `pyforge/warden/actuator.py` from `manifest_fixup.ManifestFileChange` (CAP-24) |

## 10. Engines, bundled data and refresh scripts

### 10.1 Engines and tested ranges

Each engine runs as a subprocess through the kernel's single subprocess helper in `engines.py` (CAP-10). A range is a
tested range, not a pin (NFR-C1): an engine outside it is `engine-unavailable` (exit 2), never a silent pass, and
`--doctor` reports it. The test derives the rows from every `*_VERSION_RANGE` constant of `engines.py` plus
`tea-test-review`, which has none, and reads each row's range.

| Engine | Tested range | Where it comes from | CAP |
|---|---|---|---|
| `deptry` | `>=0.25.1,<0.26` | conda-forge, a run-dependency of the package's own `pixi.toml` at the same range (`tests/meta/test_engine_version_range_sync.py`). | CAP-4 |
| `osv-scanner` | `>=2.4.0,<2.5` | conda-forge, a run-dependency of the package's own `pixi.toml` at the same range; reads the offline database (section 5). | CAP-4, CAP-11 |
| `pixi` | `>=0.80.0,<0.82` | The workspace's pixi; the floor is the root `pixi.toml`'s `requires-pixi`. The fix-target solver runs `pixi lock` on a throwaway copy. | CAP-24 |
| `opengrep` | `>=1.30.2,<1.31` | The estate `SelfExplainML` channel, linux-64 only, a run-dependency of the package's `pixi.toml` at the same range. | CAP-25 |
| `tea-test-review` | none | BMAD TEA's headless CLI, run as `tea-test-review --base refs/remotes/origin/main --agent claude` under an 1800 s budget, so it needs the `tea` roster entry and an agent CLI on `PATH` (`--agent claude`); provisioned under `spec-pyforge-steward:CAP-33`. | CAP-23 |

### 10.2 Bundled data

The entries of the package's `data/` directory, each with what dates it and the kernel module that reads it. The test
derives the readers (the modules holding the entry's name as an exact string constant) and reads the reader cell.

| Entry | Freshness | Read by | CAP |
|---|---|---|---|
| `conda_pypi_map.json` | No snapshot date: the map (conda name to PyPI identity) carries none, and nothing checks its age. Regenerated from conda-forge-expert's atlas `export-purls` by `src/shared/packages/pyforge-warden/scripts/generate_conda_pypi_map.py`. | `pyforge/warden/mapping.py` | CAP-2 |
| `lts-registry.yaml` | Its own `updated:` date, at most `180` days old, or the currency axis is `indeterminate`. A copy of conda-forge-expert's canonical registry, re-copied when that changes. | `pyforge/warden/currency.py` | CAP-4 |
| `report-schema.json` | Frozen at 1.1.0 (section 3.5). | `pyforge/warden/report.py` | CAP-7 |
| `sast-rules/` | The estate-owned opengrep rules; versioned with the package. | `pyforge/warden/sast.py` | CAP-25 |

### 10.3 Refresh scripts

The package's dev and ops scripts that provision the feed caches the scan then reads offline (CAP-11). They are not
part of the installed package and nothing in it calls them: they are the whole opt-in online surface for the feeds.
Each defaults `--cache-dir` to `PYFORGE_WARDEN_FEED_CACHE_DIR`. The offline OSV database is provisioned separately
(CAP-20's `scripts/platform-provision-osv-offline-db.sh`).

| Script | What it writes | CAP |
|---|---|---|
| `src/shared/packages/pyforge-warden/scripts/refresh_kev_feed.py` | The CISA Known Exploited Vulnerabilities catalog cache. | CAP-11 |
| `src/shared/packages/pyforge-warden/scripts/refresh_epss_feed.py` | The FIRST.org EPSS feed cache. | CAP-11 |
| `src/shared/packages/pyforge-warden/scripts/refresh_endoflife_feed.py` | The endoflife.date product cache (`--product SLUG` narrows it). | CAP-11 |

## 11. Python import surface

Every `pyforge.warden` module a tracked file under `src/` or `scripts/` outside the package imports, the names it
imports and the files that import it. Other packages reach warden this way today, although the skill and the Frame say
"do not import": a rebuild keeps every name below or breaks its importer. The test's derivation is the count of record:
it reads every such file as text (so the source strings handed to `python -c` are seen), and leaves out only the files
of its `IMPORT_FIXTURE_FILES` allowlist, which quote an import line as a fixture or a comment and import nothing. A
module imported whole (`import pyforge.warden.cli`) lists its importer with no name of its own.

| Module | Names | Importers |
|---|---|---|
| `pyforge.warden` | `__version__`, `engines`, `models`, `report`, `verdict` | `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/universal_sbom/gate.py`, `src/shared/packages/pyforge-atlas/tests/unit/test_import_smoke.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_checks_registry.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_cli_check.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_sources_warden.py` |
| `pyforge.warden.actuator` | `run_actuator` | `src/shared/packages/django-warden/src/django_warden_fabric/tasks.py` |
| `pyforge.warden.cli` | `main` | `src/platform/tests/policy/test_warden_platform_env_import.py`, `src/shared/packages/django-warden/src/django_warden_fabric/tasks.py` |
| `pyforge.warden.discovery` | `PIXI_LOCK_KIND` | `src/platform/tests/test_golden_path_promotion_closure.py` |
| `pyforge.warden.engines` | `DeptryEngine`, `DoctorCheck`, `run_doctor_checks` | `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/universal_sbom/gate.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/warden.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_checks_registry.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_cli_check.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_sources_warden.py` |
| `pyforge.warden.extract.lockfiles` | `PixiLockExtractor` | `src/platform/tests/test_golden_path_promotion_closure.py` |
| `pyforge.warden.feeds` | `write_endoflife_cache`, `write_kev_cache` | `src/platform/tests/test_golden_path_promotion_verdict.py` |
| `pyforge.warden.fleet_github_graphql` | `GitHubGraphQLProjectItemsClient` | `src/shared/packages/django-warden/src/django_warden_fabric/tasks.py` |
| `pyforge.warden.fleet_github_rest` | `FleetInventoryApiError`, `GitHubRestOrgReposClient` | `src/shared/packages/django-warden/src/django_warden_fabric/tasks.py` |
| `pyforge.warden.hygiene` | `has_adjacent_python_source`, `hygiene_rung` | `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/universal_sbom/gate.py` |
| `pyforge.warden.inventory` | `ResolvedInventory` | `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/universal_sbom/gate.py` |
| `pyforge.warden.manifest_locations` | `manifest_locations_for_target` | `src/shared/packages/django-warden/src/django_warden_fabric/tasks.py` |
| `pyforge.warden.models` | `Finding`, `ScannedManifest`, `Severity`, `SeverityTier`, `Status` | `src/platform/tests/test_golden_path_promotion_closure.py`, `src/shared/packages/django-warden/src/django_warden_fabric/tasks.py`, `src/shared/packages/pyforge-atlas/tests/unit/policy_gate/test_policy_gate.py` |
| `pyforge.warden.routing` | `DefaultRouter` | `src/platform/tests/test_golden_path_promotion_closure.py` |
| `pyforge.warden.verdict` | `LATTICE` | `src/shared/packages/pyforge-doctor/tests/meta/test_verdict_narrows_warden.py` |

## Where each capability lives

The twelfth section. One row per capability of `SPEC.md`: the package or path its code lives in, and the Spec whose
`surface:` governs that code (what `spec-surface-check` reads; `none` when no Spec's `surface:` covers a path the row
names). The kernel is `src/shared/packages/pyforge-warden/` (module paths as `pyforge/warden/...`), on this Spec's
surface; `spec-pyforge-core` co-governs its `src/` (every station's `src/` is on core's surface) and is not repeated
below. `django-warden` (module paths as `django_warden_fabric/...`) realizes CAP-16, CAP-17 and CAP-29 on
`spec-pyforge-unifying-strategy`'s surface. CAP-19 to CAP-22 live in platform scripts and workflows. By the operator's
ruling of 2026-11-10 this table is the answer to audit MUST 9: `spec-pyforge-warden` does not co-govern
`django-warden`, and its `surface:` block does not move. The test reads the CAP id of each row's first cell, the path
tokens of the second (each must exist) and the Spec tokens of the third, against every station Spec's `surface:`.

| CAP | Code | Code's governing Spec |
|---|---|---|
| CAP-1 | `pyforge/warden/cli.py`, `pyforge/warden/verdict.py`, `pyforge/warden/report.py` | `spec-pyforge-warden` |
| CAP-2 | `pyforge/warden/extract/`, `pyforge/warden/discovery.py`, `pyforge/warden/routing.py`, `pyforge/warden/mapping.py`, `pyforge/warden/data/conda_pypi_map.json` | `spec-pyforge-warden` |
| CAP-3 | `pyforge/warden/discovery.py`, `pyforge/warden/inventory.py`, `pyforge/warden/report.py` | `spec-pyforge-warden` |
| CAP-4 | `pyforge/warden/hygiene.py`, `pyforge/warden/vuln.py`, `pyforge/warden/license.py`, `pyforge/warden/currency.py`, `pyforge/warden/verdict.py` | `spec-pyforge-warden` |
| CAP-5 | `pyforge/warden/config.py`, `pyforge/warden/interfaces.py`, `pyforge/warden/verdict.py` | `spec-pyforge-warden` |
| CAP-6 | `pyforge/warden/waiver.py` | `spec-pyforge-warden` |
| CAP-7 | `pyforge/warden/report.py`, `pyforge/warden/sbom.py`, `pyforge/warden/data/report-schema.json` | `spec-pyforge-warden` |
| CAP-8 | `pyforge/warden/models.py`, `pyforge/warden/engines.py`, `pyforge/warden/cli.py` | `spec-pyforge-warden` |
| CAP-9 | `pyforge/warden/cli.py`, `pyforge/warden/waiver.py` | `spec-pyforge-warden` |
| CAP-10 | `pyforge/warden/engines.py`, `pyforge/warden/report.py` | `spec-pyforge-warden` |
| CAP-11 | `pyforge/warden/vuln.py`, `pyforge/warden/feeds.py`, `src/shared/packages/pyforge-warden/scripts/refresh_kev_feed.py`, `src/shared/packages/pyforge-warden/scripts/refresh_epss_feed.py`, `src/shared/packages/pyforge-warden/scripts/refresh_endoflife_feed.py` | `spec-pyforge-warden` |
| CAP-12 | `pyforge/warden/actuator.py` | `spec-pyforge-warden` |
| CAP-13 | `pyforge/warden/sources.py`, `pyforge/warden/inventory.py` | `spec-pyforge-warden` |
| CAP-14 | `pyforge/warden/eligibility.py` | `spec-pyforge-warden` |
| CAP-15 | `pyforge/warden/eligibility_sbom.py`, `pyforge/warden/sbom.py` | `spec-pyforge-warden` |
| CAP-16 | `django_warden_fabric/views.py`, `django_warden_fabric/tasks.py`, `django_warden_fabric/models.py` | `spec-pyforge-unifying-strategy` |
| CAP-17 | `django_warden_fabric/phases.py`, `django_warden_fabric/views.py` | `spec-pyforge-unifying-strategy` |
| CAP-18 | `pyforge/warden/cli.py`, `pyforge/warden/extract/lockfiles.py` | `spec-pyforge-warden` |
| CAP-19 | `scripts/platform-golden-path-promotion.sh`; the `golden-path-promotion` job of `.github/workflows/platform-ci.yml` | `spec-pyforge-steward` (the script); `none` (the workflow) |
| CAP-20 | `scripts/platform-provision-osv-offline-db.sh`; the database cache of `.github/workflows/platform-ci.yml` | `none` |
| CAP-21 | `scripts/platform-golden-path-promotion.sh` (it assembles the promotion record) | `spec-pyforge-steward` |
| CAP-22 | `scripts/platform-deploy-verify-promotion.py`, `.github/workflows/platform-deploy.yml` | `spec-pyforge-steward` (the script); `none` (the workflow) |
| CAP-23 | `pyforge/warden/tea_advisory.py`, `pyforge/warden/engines.py` | `spec-pyforge-warden` |
| CAP-24 | `pyforge/warden/actuator.py`, `pyforge/warden/fix_solver.py`, `pyforge/warden/manifest_edit.py`, `pyforge/warden/manifest_fixup.py`, `pyforge/warden/manifest_locations.py` | `spec-pyforge-warden` |
| CAP-25 | `pyforge/warden/sast.py`, `pyforge/warden/data/sast-rules/`, `pyforge/warden/engines.py` | `spec-pyforge-warden` |
| CAP-26 | `pyforge/warden/fleet_github_rest.py`, `pyforge/warden/fleet_github_graphql.py`, `pyforge/warden/native_lockfiles.py`, `pyforge/warden/manifest_locations.py` | `spec-pyforge-warden` |
| CAP-27 | `pyforge/warden/hooks.py`, `pyforge/warden/scanner_plugins.py`, `src/shared/packages/pyforge-warden/pyproject.toml` | `spec-pyforge-warden` |
| CAP-28 | This file, `proof-map.md`, and the tests `src/shared/packages/pyforge-warden/tests/meta/test_public_contract.py` and `src/shared/packages/pyforge-warden/tests/meta/test_contract_surface.py` | `spec-pyforge-warden` |
| CAP-29 | `django_warden_fabric/fleet.py`, `django_warden_fabric/fleet_inventory.py`, `django_warden_fabric/fleet_project_items.py`, `django_warden_fabric/proposals.py`, `django_warden_fabric/tasks.py`, `django_warden_fabric/views.py`, `django_warden_fabric/models.py`, `django_warden_fabric/management/commands/` | `spec-pyforge-unifying-strategy` |

### What warden does not mint

Surfaces a caller of warden reaches whose capability another Spec owns. The test checks that each cited capability
exists in that Spec and that each path named exists.

| Surface | Where it lives | Capability |
|---|---|---|
| The MCP face: `start_audit` and `get_audit` (section 6) | `django_warden_fabric/mcp_asgi.py` | `spec-pyforge-unifying-strategy:CAP-4`, `spec-pyforge-unifying-strategy:CAP-20` |
| The station skill and the persona | `.claude/skills/pyforge-warden/`, `.claude/skills/bmad-agent-warden/` | `spec-pyforge-unifying-strategy:CAP-15`, `spec-pyforge-unifying-strategy:CAP-16` |
| The two review lenses warden wields, `bmad-os-review-pr` and `bmad-os-findings-triage` (warden Story 11.1) | `.claude/skills/bmad-os-review-pr/`, `.claude/skills/bmad-os-findings-triage/` | `spec-pyforge-steward:CAP-32` (Station routing) |
| The TEA advisory's provisioning: the `tea` roster entry and the `tea-test-review` task (section 10.1) | steward's `provision --module tea` | `spec-pyforge-steward:CAP-33` |

### Recorded as-is

Literals a caller meets that this contract records without changing them. The test derives each from the code.

| Literal | Where | Owner |
|---|---|---|
| `urn:local-recipes:pyforge-warden:report-schema` | `pyforge/warden/data/report-schema.json` | Warden: the frozen schema `$id` (section 3.5); a second root keeps it. |
| `DEFAULT_AUDIT_TARGET = "src/platform"` | `django_warden_fabric/mcp_asgi.py` | Steward's code (`spec-pyforge-unifying-strategy`): the target `start_audit` and the portal scan when none is given. |
| `/compliance/check` | `src/platform/config/station_api.py` | Steward's code (`spec-pyforge-unifying-strategy`): the warden station API's check route, a stub that answers `accepted` and scans nothing. |
