# Public contract — pyforge-marshal

Companion to `SPEC.md` (spec-pyforge-marshal:CAP-304; decision D1 of the 2026-11-10 cutover readiness design pass). It
names every way marshal is addressed and every signal it emits: each CLI verb path and flag, each MCP tool, each
feature-flag key and environment variable it reads, each diagnostic code and each exit code. A reader holding only the
Spec folder can rebuild that surface from it; the behaviour behind each name is the capability that governs it in
`SPEC.md`. The persona grammar is `pyforge marshal …` (FR-13); the console script `marshal` takes the same verb paths.

The guard is `src/shared/packages/pyforge-marshal/tests/meta/test_public_contract.py`, a `live_tree` module of
marshal's suite (this file sits outside the package). It never types an inventory: `tests/_support/contract_inventory.py`
derives each family from the code that defines it, and the test compares the result with this file's tables both
ways. An item the code has and this file lacks fails as missing from the contract; a row this file keeps and the code
no longer has fails as stale in the contract; a checked cell that disagrees with the code fails as differing. Each
message names the item. A change that adds, removes or renames a verb path, a flag, a tool, a flag key, an
environment variable, a diagnostic code or an exit code changes this file in the same change. No script writes it.

How the test reads this file: the six `## ` sections below, by title, and in the three sections that hold more than one
table, the `### ` headings that name each table. In a table, a row's first backticked token is its item; the checked
cells are the flags of a CLI row (each backticked token that starts with `-`), the *Runs* cell of a `marshal-mcp` tool,
the *Verdict* of a finding code, the *Member* of a seed finding type, the *Meaning* of an every-verb exit code (its
backticked tokens, as a set) and the *Leaf* of a seed exit code. Every other cell, and all prose, is for the reader and
is not read.

## CLI verbs and flags

Read from `pyforge.marshal.cli.main._build_parser()`, the parser `marshal` (`pyforge.marshal.cli.main:main`) runs: every
sub-parser choice, nested, is a verb path, and the bare `marshal` is the root row. A row's flags are the option strings
of every action its own parser holds whose help is not suppressed, in parser order; argparse's `-h`/`--help` (on every
parser) and the positional arguments are not listed. A group row (`marshal factory`) names its own flags only; its
verbs are the rows under it. A verb whose kill switch is off stays listed and refuses with the usage code (see
*Feature-flag keys*). `marshal-mcp`, the second console script, is the stdio MCP server of the next section; its own
`--version` and `--help` start no server.

| Command | Flags |
|---|---|
| `marshal` | `--version` |
| `marshal adapters` | — |
| `marshal adapters conform` | `--format` |
| `marshal adapters entry-files` | `--format` |
| `marshal adapters matrix` | `--stale-after-days`, `--format` |
| `marshal adapters models` | `--write`, `--format` |
| `marshal adapters probe` | `--adapter`, `--format` |
| `marshal adapters smoke` | `--adapter`, `--timeout-seconds`, `--format` |
| `marshal adapters sync` | `--format` |
| `marshal benchmark` | — |
| `marshal benchmark compare` | `--project`, `--off`, `--on`, `--home`, `--story`, `--output`, `--format`, `--per-layer`, `--layer-legs` |
| `marshal benchmark structure-graph-dispatch` | `--project`, `--index-build-seconds`, `--index-bytes`, `--sync-seconds`, `--codegraph-reported-seconds`, `--files-indexed`, `--nodes`, `--edges`, `--output`, `--format` |
| `marshal check` | `--scope`, `--project`, `--format` |
| `marshal config` | `--project-policy`, `--project`, `--set`, `--materialize`, `--write-harness-policy`, `--format` |
| `marshal context` | — |
| `marshal context advisory` | `--project`, `--root`, `--format` |
| `marshal context bootstrap` | `--from`, `--offline`, `--tag`, `--repo`, `--root`, `--format` |
| `marshal context bundle` | `--project`, `--epic`, `--root`, `--expect-digest`, `--format` |
| `marshal context pack` | `--out`, `--source-commit`, `--root`, `--format` |
| `marshal context refresh` | `--project`, `--epic`, `--root`, `--format` |
| `marshal context retrieve` | `--project`, `--epic`, `--story`, `--root`, `--format` |
| `marshal deploy` | — |
| `marshal deploy batch-pr` | `--format` |
| `marshal deploy land-story` | `--justification`, `--since`, `--format` |
| `marshal deploy promote` | `--project`, `--format` |
| `marshal deploy reconcile-completions` | `--project`, `--format` |
| `marshal deploy recover-spec` | `--format` |
| `marshal deploy refresh-feed` | `--project`, `--format` |
| `marshal factory` | — |
| `marshal factory attach` | — |
| `marshal factory challenge` | `--project`, `--stage`, `--target`, `--section`, `--dream-section`, `--epic`, `--audit`, `--force`, `--format` |
| `marshal factory challenge resolve` | `--project`, `--report`, `--accept`, `--reject` |
| `marshal factory checkpoint` | — |
| `marshal factory dispatch` | `--stories`, `--format`, `--harness`, `--hold-landing` |
| `marshal factory dispatch-attach` | — |
| `marshal factory dispatch-resume` | `--format` |
| `marshal factory drain` | `--mode`, `--station`, `--stories`, `--leave-remaining`, `--once`, `--max-cycles`, `--tick-seconds`, `--campaign`, `--format`, `--harness`, `--max-in-flight`, `--retry-environment-blocks`, `--plan`, `--all-stories`, `--check-env` |
| `marshal factory resume` | `--format` |
| `marshal factory spin` | `--epic`, `--story`, `--max-count`, `--foreground`, `--format` |
| `marshal gate` | — |
| `marshal gate evaluate` | `--project`, `--run`, `--scope-check`, `--story`, `--format` |
| `marshal homes` | `--format` |
| `marshal init` | `--format` |
| `marshal land` | `--retire-live-branch`, `--format` |
| `marshal login` | `--pkce`, `--issuer`, `--client-id`, `--bearer-file` |
| `marshal planning` | — |
| `marshal planning chain-regenerate` | `--project`, `--dream`, `--chain-mode`, `--minimal`, `--resume`, `--root`, `--format`, `--live`, `--preserve-code-status`, `--no-preserve-code-status`, `--apply-orphans`, `--stage` |
| `marshal preflight` | `--acknowledge`, `--format` |
| `marshal preserve` | — |
| `marshal preserve list` | `--format`, `--station`, `--story`, `--producer`, `--state` |
| `marshal preserve push` | `--pending` |
| `marshal preserve retire` | `--evidence` |
| `marshal preserve tag` | `--story`, `--producer`, `--from`, `--provenance`, `--reason`, `--source`, `--run`, `--journal` |
| `marshal refresh` | `--project`, `--base`, `--format` |
| `marshal retire` | `--project`, `--execute`, `--format` |
| `marshal seed` | — |
| `marshal seed accept` | `--repo-root`, `--apply`, `--reason`, `--dry-run`, `--json`, `--quiet` |
| `marshal seed adopt` | `--repo-root`, `--apply`, `--yes`, `--agents`, `--skip`, `--force`, `--project`, `--dry-run`, `--json`, `--quiet` |
| `marshal seed check` | `--repo-root`, `--strict`, `--project`, `--json`, `--quiet` |
| `marshal seed explain` | `--json`, `--quiet` |
| `marshal seed init` | `--slug`, `--agents`, `--force`, `--dry-run`, `--json`, `--quiet` |
| `marshal seed kit` | `--repo-root`, `--apply`, `--project`, `--dry-run`, `--json`, `--quiet` |
| `marshal seed update` | `--repo-root`, `--run`, `--force`, `--include-seeded`, `--skip`, `--yes`, `--project`, `--dry-run`, `--json`, `--quiet` |
| `marshal seed version` | `--repo-root`, `--json`, `--quiet` |
| `marshal status` | `--project`, `--run`, `--escalations`, `--reconcile-ledger`, `--format` |
| `marshal teardown` | `--force`, `--abandon`, `--format` |
| `marshal upstream` | `--format` |
| `marshal watch` | `--project`, `--run`, `--fleet`, `--format` |

## MCP tools

Marshal has two MCP surfaces. Persona tool names are taken from this section (steward:S-124.5).

### `marshal-mcp` (stdio)

`pyforge.marshal.mcp.server.build_server()` registers exactly the tools `pyforge.marshal.mcp.tools.TOOL_SPECS` lists
(spec-pyforge-marshal:CAP-23 amended 2026-11-10, Story 115.3); the guard reads both, so a registration with no spec is
listed too. Each tool but `list_marshal_tools` runs the `marshal` CLI in-process with the argv its spec names (a
`{name}` token is a required argument; a tool's optional arguments add their flags), and returns the CLI's JSON
report. Marshal policy registers the server as `[mcp_servers.marshal]` with the PATH-relative command `marshal-mcp`.

| Tool | Runs | What it does |
|---|---|---|
| `list_marshal_tools` | — | Lists the tool names with their CLI argv templates; runs no CLI. |
| `marshal_check` | `marshal check --format json` | The detector registry; optional `scope`, `project`. |
| `marshal_homes` | `marshal homes --format json` | Every discovered loop home and its isolation. |
| `marshal_preflight` | `marshal preflight {slug} --format json` | Preflights one project's loop home. |
| `marshal_preserve_list` | `marshal preserve list --format json` | Local preserve tags; optional `station`, `story`, `producer`, `state`. |
| `marshal_preserve_push` | `marshal preserve push` | Pushes preserve/archive tags through the content gate (`pending` adds `--pending`); refuses with the usage code while `pyforge.marshal.preserve_refs` is off. |
| `marshal_preserve_retire` | `marshal preserve retire {tag}` | Retires a preserve tag in the ledger with `--evidence`; refuses with the usage code while `pyforge.marshal.preserve_refs` is off. |
| `marshal_refresh` | `marshal refresh --format json` | Refreshes loop homes from main; optional `project`, `base`. |
| `marshal_status` | `marshal status --format json` | Fleet-wide runtime status; optional `project`. |
| `marshal_upstream` | `marshal upstream --format json` | The tracked upstream contribution register. |
| `marshal_watch` | `marshal watch --format json` | Watches a pinned run, a station's run or the fleet; optional `project`, `run`, `fleet`. |

### Station face (`POST /stations/marshal/mcp`)

The platform host's face for marshal, `django_marshal_portal/mcp_asgi.py` in `django-marshal`. The guard reads its
tool names by AST, never by import: each `@<server>.tool(name=...)` decorator and each `*_tool=` keyword of its
`attach_supervised_start_get` call, the three held-loop names resolved through `django_pyforge.supervisor`'s
constants. Every call carries a signed assertion (`docs/how-to/reach-a-station-mcp-endpoint.md`).

| Tool | What it does |
|---|---|
| `start_loop` | Takes a target `<slug>/<story>` and returns a run handle at once. Its row of the closed verb table (spec-pyforge-unifying-strategy:CAP-20, canopy:AD-24, steward Epic 119; the operator's ruling of 2026-11-06, "Dispatch, gated") runs `marshal factory dispatch <slug> <story> --format json` in `pyforge-guild`, at most once, and only for a `pyforge:admin` caller while `pyforge.steward.start_loop_dispatch` is on; that flag ships off, and any other caller is refused before a run row exists. |
| `get_loop` | Fetches a run by its handle. |
| `run_loop` | The supervisor's tool key `start_loop` hands its work to, bound to the verb-table row above; a client starts it only through `start_loop`. |
| `publish_loop_run` | Publishes an externally owned loop run to the supervisor store and returns its handle (`payload` is an explicit field). |
| `heartbeat_loop_run` | Keeps a held loop run alive. |
| `complete_loop_run` | Terminalizes a held loop run with a status and a result. |
| `list_loop_story_tasks` | The published per-story task records of one loop home (`project_slug`). |
| `marshal_watch` | `marshal watch`'s report, run as `pyforge marshal watch --format json` (or `marshal watch`) with `project`, `run` or `fleet`. |

## Feature-flag keys

Every string constant in a marshal module shaped `pyforge.<station>.<key>` that names no module (no `<key>.py` and no
`<key>/` under that station's package), plus the root-of-record seam: a module that imports `root_of_record` from
`pyforge.core.cutover_root` reads `pyforge.core.cutover_root.CUTOVER_FLAG`, so `pyforge.cutover_root` is marshal's key
too, though no marshal module holds the string (Story 115.4, spec-pyforge-marshal:CAP-208). The flags themselves live
in `src/platform/config/flags.json`, read through `pyforge.core.flags`; most marshal keys are the Epic 110 kill
switches (spec-feature-flag-governance), and a verb whose switch is off stays listed and exits with the usage code.
`pyforge.marshal.front_door_environment` is marshal-owned but read by `pyforge.core.dispatch`, so it belongs to the
core contract, not this table.

| Key | What it gates |
|---|---|
| `pyforge.cutover_root` | The root of record (`local-recipes` or `foundry`); marshal reads its forge repository slug through it for `marshal land`, the dispatch landing, `deploy batch-pr` and `marshal watch` (steward Story 44.12). |
| `pyforge.marshal.adapter_fanout` | Kill switch: adapters projected from one contract (Story 110.11). |
| `pyforge.marshal.branch_merged_divergence` | Kill switch: a branch is never merged on ancestry alone (Story 110.19). |
| `pyforge.marshal.completion_from_facts` | Kill switch: completion is judged from git and process facts, never self-reports (Story 110.15). |
| `pyforge.marshal.context_pipeline` | Kill switch: the declared `[context]` pipeline (Story 110.21). |
| `pyforge.marshal.dispatch_codegraph_index` | Kill switch: every dispatch session opens on the shared codegraph index (Story 110.31). |
| `pyforge.marshal.dispatch_lands_via_land` | Kill switch: a dispatch lands through the existing landing machinery, never a second path (Story 110.17). |
| `pyforge.marshal.dispatch_only_fleet_rows` | Kill switch: a dispatch-only checkout still has fleet rows (Story 110.23). |
| `pyforge.marshal.drain_followup_review` | Kill switch: a drain runs the follow-up review a landed story recommended, gated by its deferred-work row (Story 110.30). |
| `pyforge.marshal.egm_audit` | `factory challenge --audit`: one sweep reports where the fleet stands (Story 113.5). |
| `pyforge.marshal.egm_challenge` | `marshal factory challenge`: a fresh-context review of one chain artifact (Story 113.1). |
| `pyforge.marshal.egm_dispatch_readiness` | Dispatch runs the readiness stage before the dev session starts (Story 113.3). |
| `pyforge.marshal.egm_policy_block` | The `[challenge]` policy block configures the challenger; absent means off (Story 113.2). |
| `pyforge.marshal.egm_resolve_bridge` | `factory challenge resolve`: an accepted finding travels the chain's only write path (Story 113.6). |
| `pyforge.marshal.egm_retro_drift` | The drift stage reads an epic's code against its Spec at retro time (Story 113.4). |
| `pyforge.marshal.fleet_status` | Kill switch: fleet visibility, `marshal status` (Story 110.5). |
| `pyforge.marshal.followup_review_to_ledger` | Kill switch: a recommended follow-up review is carried into the deferred-work ledger, never dropped (Story 110.26). |
| `pyforge.marshal.gate_evaluate` | Kill switch: gates you can run, `marshal gate evaluate` (Story 110.4). |
| `pyforge.marshal.genesis_state_file` | Kill switch: the Genesis-owned state file `.marshal/seed-state.yml` (Story 110.12). |
| `pyforge.marshal.guild_env_shellouts` | Kill switch: marshal's shell-outs name the guild environment (Story 110.24). |
| `pyforge.marshal.landing_ci_pauses` | A landing records which CI surfaces were paused when it merged (Story 100.1). |
| `pyforge.marshal.landing_memlog_union` | Kill switch: a landing unions append-only memlogs instead of refusing (Story 110.32). |
| `pyforge.marshal.ledger_promotion_to_origin` | Kill switch: a landing's ledger promotion reaches `origin/main`, and a failed one is never silent (Story 110.27). |
| `pyforge.marshal.loop_homes` | Kill switch: loop homes and isolation (Story 110.2). |
| `pyforge.marshal.loop_runner` | Not a `flags.json` key: the name of the `pyforge.core.hooks` hook spec marshal's loop runner plugs into (Story 26.1; `bmad-loop` is the default plugin). The derivation admits it because it is shaped like one. |
| `pyforge.marshal.managed_regions` | Kill switch: managed-region upgrades (Story 110.8). |
| `pyforge.marshal.model_list_refresh` | Kill switch: an operator-run refresh reads every harness's live model list and reports drift (Story 110.33). |
| `pyforge.marshal.one_in_flight_per_station` | Kill switch: one story in flight per station; cross-station dispatches run concurrently (Story 110.18). |
| `pyforge.marshal.policy_composition` | Kill switch: policy composition, `marshal config` (Story 110.6). |
| `pyforge.marshal.preserve_refs` | Preserved work has one grammar and one verb, `marshal preserve`; teardown refuses to remove a loop home holding unpreserved work; a preserve reaches origin only through the content gate (Stories 87.3, 87.7, 87.15). |
| `pyforge.marshal.promotion_on_landing` | Kill switch: promotion runs on landing, not on memory (Story 110.22). |
| `pyforge.marshal.recall_context_layer` | Kill switch: the recall injection is its own context layer (Story 110.36). |
| `pyforge.marshal.recall_dev_pass` | Kill switch: a dev pass receives relevant team-memory feedback before it starts (Story 110.34). |
| `pyforge.marshal.recall_miss_injects_nothing` | Kill switch: a recall miss or failure injects nothing (Story 110.37). |
| `pyforge.marshal.recall_review_pass` | Kill switch: a review pass sees the same feedback the dev pass saw (Story 110.35). |
| `pyforge.marshal.refresh_proven_push` | Kill switch: a loop-home refresh sends its proven fast-forward past the pre-push preflight, journaled (Story 110.25). |
| `pyforge.marshal.seed_adopt` | Kill switch: `marshal seed adopt` onto a living repository (Story 110.9). |
| `pyforge.marshal.seed_check` | Kill switch: `marshal seed check` in CI (Story 110.10). |
| `pyforge.marshal.seed_check_rendered_paths` | Kill switch: `marshal seed check` judges the paths the manifest means, never its unrendered placeholders (Story 110.29). |
| `pyforge.marshal.seed_explain` | Kill switch: the operating model as data, `marshal seed explain` (Story 110.7). |
| `pyforge.marshal.single_followup_review` | Kill switch: after the harness exits, at most one follow-up review, then land (Story 110.20). |
| `pyforge.marshal.supervised_runs` | Kill switch: supervised unattended runs (Story 110.3). |
| `pyforge.marshal.supervisor_shell_finalize` | Kill switch: the supervisor finalizes when the harness cannot run a shell (Story 110.13). |
| `pyforge.marshal.switch_script_placement` | Kill switch: the switch script runs where it is documented to run, or says in one line why it cannot (Story 110.28). |
| `pyforge.marshal.verify_before_landing` | Kill switch: a session's self-report is input to verification, never the verdict (Story 110.16). |
| `pyforge.marshal.verify_fix_loop` | A verification refusal goes back to the session that wrote the change for one fix turn (Story 85.1). |
| `pyforge.marshal.watch` | Kill switch: `marshal watch` reports what changed and a recommended delay (Story 110.14). |

## Environment variables

The value of every module-level `ENV_*` or `*_ENV` string constant in a marshal module, and the key of every
`os.environ` / `os.getenv` access whose key is a literal or a module-level constant: `os.environ[K]`,
`os.environ.get`, `pop` or `setdefault`, `os.getenv`, `K in os.environ`, `.get` on an expression holding `os.environ`,
a key of a dict literal that spreads `**os.environ`, and a key read from or set in a child environment a function
builds from `os.environ` (or takes as a parameter named `environ`). A name computed at run time is not listed: an
adapter's `credential_env` (named in policy), a harness profile's or wrapper's declared environment, and the budget
variables `marshal factory dispatch` passes to a session.

| Variable | Role |
|---|---|
| `BMAD_ACTIVE_PROJECT` | Read: the project when `--project` is absent (`config`, `gate`, `deploy`, `seed`, `factory dispatch`, seed's projects index). Set: in a dispatched or skill-invoked session's environment, to the project it serves. |
| `BMAD_LOOP_HOME_ROOT` | Read: the loop-home root (default `~/.bmad-loops`); a relative value is anchored to the working directory once. |
| `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` | Removed from the environment of a `factory challenge` session, so no extra `CLAUDE.md` reaches the reviewer. |
| `CURSOR_CONFIG_DIR` | Read from a Cursor launch environment: Cursor's config directory, as `cursor-agent` resolves it. |
| `GIT_ALTERNATE_OBJECT_DIRECTORIES` | Set in a git child environment: the repository's real object store, behind a throwaway one. |
| `GIT_OBJECT_DIRECTORY` | Set in a git child environment: a throwaway object store for `commit-tree`, deleted afterwards. |
| `MARSHAL_EGM_PLUGINS_ROOT` | Read: the Claude Code plugins root `factory challenge` checks the pinned EGM plugin under (default `~/.claude/plugins`). |
| `MARSHAL_SKILL_TIMEOUT` | Read: the skill-invoke harness's timeout in seconds. |
| `MARSHAL_STATE_HOME` | Read: marshal's machine-scoped state directory (default `~/.local/state/pyforge-marshal`). |
| `PATH` | Set in a dispatched session's environment: the resolved CLI's directory is put first. |
| `PYFORGE_HOST` | Read: the platform host the run publisher posts to (default `http://127.0.0.1:8000`). |
| `PYFORGE_IDP_BEARER_FILE` | Read: the bearer file the run publisher and `marshal login` use. |
| `PYTHONUNBUFFERED` | Set to `1` in a detached `bmad-loop` child's environment. |
| `XDG_CONFIG_HOME` | Read from a Cursor launch environment: the fallback base of Cursor's config directory. |

## Diagnostic codes

Two vocabularies. The first is the finding-code registry every marshal verb emits through; the second is the closed
conformance vocabulary of `marshal seed check` and the other seed verbs.

### `MRS-*` finding codes

`pyforge.marshal.core.findings.REGISTERED_CODES` (format `MRS-<AREA>-<NNN>`, never reused or renumbered; marshal's AD-15), each
with the lattice member `pyforge.marshal.core.verdict.classify` gives it (marshal's AD-31). `unclassified` marks a registered code
`classify` has no member for: it raises for `MRS-CHAIN-005`, `MRS-PREFLIGHT-016` and `MRS-REFRESH-008`, though each is
emitted, so this table records the gap as the code holds it.

| Code | Verdict |
|---|---|
| `MRS-ADP-001` | `error` |
| `MRS-ADP-002` | `error` |
| `MRS-ADP-003` | `error` |
| `MRS-ADP-004` | `unevaluable` |
| `MRS-ADP-005` | `unevaluable` |
| `MRS-ADP-006` | `error` |
| `MRS-ADP-007` | `warn` |
| `MRS-ADP-008` | `error` |
| `MRS-ADP-009` | `warn` |
| `MRS-ADP-010` | `warn` |
| `MRS-ADP-011` | `warn` |
| `MRS-ADP-012` | `error` |
| `MRS-ADP-013` | `unevaluable` |
| `MRS-ADP-014` | `unevaluable` |
| `MRS-ADP-015` | `error` |
| `MRS-ADP-016` | `warn` |
| `MRS-BENCH-001` | `error` |
| `MRS-BENCH-002` | `error` |
| `MRS-BENCH-003` | `error` |
| `MRS-BENCH-004` | `warn` |
| `MRS-BENCH-005` | `error` |
| `MRS-CHAIN-001` | `unevaluable` |
| `MRS-CHAIN-002` | `error` |
| `MRS-CHAIN-003` | `error` |
| `MRS-CHAIN-004` | `warn` |
| `MRS-CHAIN-005` | `unclassified` |
| `MRS-CHECK-001` | `warn` |
| `MRS-CHECK-002` | `error` |
| `MRS-CHECK-003` | `error` |
| `MRS-CHECK-004` | `unevaluable` |
| `MRS-CHK-001` | `error` |
| `MRS-CHK-002` | `error` |
| `MRS-CHK-003` | `error` |
| `MRS-CONFORM-001` | `error` |
| `MRS-CTX-001` | `unevaluable` |
| `MRS-CTX-002` | `warn` |
| `MRS-CTX-003` | `warn` |
| `MRS-CTX-004` | `unevaluable` |
| `MRS-CTX-005` | `warn` |
| `MRS-CTX-006` | `warn` |
| `MRS-CTX-007` | `unevaluable` |
| `MRS-CTX-008` | `warn` |
| `MRS-CTX-009` | `warn` |
| `MRS-DEPLOY-001` | `warn` |
| `MRS-DEPLOY-002` | `warn` |
| `MRS-DEPLOY-003` | `unevaluable` |
| `MRS-DEPLOY-004` | `warn` |
| `MRS-DEPLOY-005` | `warn` |
| `MRS-DEPLOY-006` | `unevaluable` |
| `MRS-DEPLOY-007` | `unevaluable` |
| `MRS-DEPLOY-008` | `error` |
| `MRS-DEPLOY-009` | `warn` |
| `MRS-DEPLOY-010` | `gate-failed` |
| `MRS-DEPLOY-011` | `error` |
| `MRS-DEPLOY-012` | `warn` |
| `MRS-DEPLOY-013` | `scope-violation` |
| `MRS-DEPLOY-014` | `error` |
| `MRS-DEPLOY-015` | `error` |
| `MRS-DEPLOY-016` | `error` |
| `MRS-DEPLOY-017` | `error` |
| `MRS-DEPLOY-018` | `error` |
| `MRS-DEPLOY-019` | `unevaluable` |
| `MRS-DEPLOY-020` | `gate-failed` |
| `MRS-DEPLOY-021` | `warn` |
| `MRS-DEPLOY-022` | `warn` |
| `MRS-DEPLOY-023` | `warn` |
| `MRS-DEPLOY-024` | `warn` |
| `MRS-DEPLOY-025` | `error` |
| `MRS-DEPLOY-026` | `warn` |
| `MRS-DEPLOY-027` | `warn` |
| `MRS-DEPLOY-028` | `warn` |
| `MRS-DISP-001` | `error` |
| `MRS-DISP-002` | `error` |
| `MRS-DISP-003` | `error` |
| `MRS-DISP-004` | `error` |
| `MRS-DISP-005` | `error` |
| `MRS-DISP-006` | `error` |
| `MRS-DISP-007` | `error` |
| `MRS-DISP-008` | `error` |
| `MRS-DISP-009` | `warn` |
| `MRS-DISP-010` | `warn` |
| `MRS-DISP-011` | `error` |
| `MRS-DISP-012` | `error` |
| `MRS-DISP-013` | `warn` |
| `MRS-DISP-014` | `error` |
| `MRS-DISP-015` | `error` |
| `MRS-DISP-016` | `error` |
| `MRS-DISP-017` | `error` |
| `MRS-DISP-018` | `error` |
| `MRS-DISP-019` | `error` |
| `MRS-DISP-020` | `error` |
| `MRS-DISP-021` | `error` |
| `MRS-DISP-022` | `warn` |
| `MRS-DISP-023` | `error` |
| `MRS-DISP-024` | `warn` |
| `MRS-DISP-025` | `warn` |
| `MRS-DISP-026` | `error` |
| `MRS-DISP-027` | `warn` |
| `MRS-DISP-028` | `warn` |
| `MRS-DISP-029` | `warn` |
| `MRS-DISP-030` | `error` |
| `MRS-DISP-031` | `warn` |
| `MRS-DISP-032` | `error` |
| `MRS-DISP-033` | `warn` |
| `MRS-DISP-034` | `error` |
| `MRS-DISP-035` | `error` |
| `MRS-DISP-036` | `warn` |
| `MRS-DISP-037` | `warn` |
| `MRS-DISP-038` | `error` |
| `MRS-DISP-039` | `error` |
| `MRS-DISP-040` | `error` |
| `MRS-DISP-041` | `error` |
| `MRS-DISP-042` | `warn` |
| `MRS-DISP-043` | `warn` |
| `MRS-DISP-044` | `error` |
| `MRS-DISP-045` | `error` |
| `MRS-DISP-046` | `warn` |
| `MRS-DISP-047` | `warn` |
| `MRS-DISP-048` | `error` |
| `MRS-DISP-049` | `warn` |
| `MRS-DISP-050` | `error` |
| `MRS-DISP-051` | `error` |
| `MRS-DISP-052` | `error` |
| `MRS-DISP-053` | `warn` |
| `MRS-DISP-054` | `warn` |
| `MRS-DISP-055` | `warn` |
| `MRS-DISP-056` | `error` |
| `MRS-DISP-057` | `error` |
| `MRS-DISP-058` | `error` |
| `MRS-DISP-059` | `error` |
| `MRS-DISP-060` | `error` |
| `MRS-DISP-061` | `error` |
| `MRS-DISP-062` | `error` |
| `MRS-DISP-063` | `error` |
| `MRS-DISP-064` | `warn` |
| `MRS-DISP-065` | `warn` |
| `MRS-DISP-066` | `warn` |
| `MRS-DISP-067` | `warn` |
| `MRS-DRAIN-001` | `error` |
| `MRS-DRAIN-002` | `error` |
| `MRS-DRAIN-003` | `warn` |
| `MRS-DRAIN-004` | `warn` |
| `MRS-DRAIN-005` | `warn` |
| `MRS-DRAIN-006` | `warn` |
| `MRS-DRAIN-007` | `warn` |
| `MRS-DRAIN-008` | `warn` |
| `MRS-DRAIN-009` | `warn` |
| `MRS-DRAIN-010` | `error` |
| `MRS-DRAIN-011` | `error` |
| `MRS-DRAIN-012` | `error` |
| `MRS-DRAIN-013` | `error` |
| `MRS-DRAIN-014` | `error` |
| `MRS-DRAIN-015` | `error` |
| `MRS-DRAIN-016` | `warn` |
| `MRS-DRAIN-017` | `warn` |
| `MRS-DRAIN-018` | `warn` |
| `MRS-DRAIN-019` | `warn` |
| `MRS-DRAIN-020` | `warn` |
| `MRS-DRAINPLAN-001` | `error` |
| `MRS-DRAINPLAN-002` | `warn` |
| `MRS-DRAINPLAN-003` | `warn` |
| `MRS-DRAINPLAN-004` | `warn` |
| `MRS-DRAINPLAN-005` | `unevaluable` |
| `MRS-ENTRY-001` | `warn` |
| `MRS-GATE-001` | `gate-failed` |
| `MRS-GATE-002` | `unevaluable` |
| `MRS-GATE-003` | `unevaluable` |
| `MRS-GATE-004` | `warn` |
| `MRS-GATE-005` | `unevaluable` |
| `MRS-GATE-006` | `gate-failed` |
| `MRS-GATE-007` | `scope-violation` |
| `MRS-GATE-008` | `scope-violation` |
| `MRS-GATE-009` | `unevaluable` |
| `MRS-GATE-010` | `scope-violation` |
| `MRS-GATE-011` | `scope-violation` |
| `MRS-GATE-012` | `warn` |
| `MRS-GATE-013` | `warn` |
| `MRS-GATE-014` | `warn` |
| `MRS-GATE-015` | `gate-failed` |
| `MRS-GATE-016` | `unevaluable` |
| `MRS-GATE-017` | `warn` |
| `MRS-GATE-018` | `gate-failed` |
| `MRS-GATE-019` | `gate-failed` |
| `MRS-GATE-020` | `gate-failed` |
| `MRS-GATE-021` | `gate-failed` |
| `MRS-GATE-022` | `gate-failed` |
| `MRS-HOMES-001` | `error` |
| `MRS-HOMES-002` | `error` |
| `MRS-HOMES-003` | `error` |
| `MRS-IDENT-001` | `unevaluable` |
| `MRS-IDENT-002` | `unevaluable` |
| `MRS-IDXF-001` | `warn` |
| `MRS-IDXF-002` | `warn` |
| `MRS-IDXF-003` | `warn` |
| `MRS-IDXF-004` | `warn` |
| `MRS-INIT-001` | `unevaluable` |
| `MRS-INIT-002` | `unevaluable` |
| `MRS-INIT-003` | `error` |
| `MRS-INIT-004` | `error` |
| `MRS-INIT-005` | `error` |
| `MRS-JOURNAL-001` | `unevaluable` |
| `MRS-JOURNAL-002` | `unevaluable` |
| `MRS-LAND-001` | `error` |
| `MRS-LAND-002` | `error` |
| `MRS-LAND-003` | `warn` |
| `MRS-LAND-004` | `gate-failed` |
| `MRS-LAND-005` | `warn` |
| `MRS-LAND-006` | `error` |
| `MRS-LAND-007` | `error` |
| `MRS-LAND-008` | `warn` |
| `MRS-LAND-009` | `warn` |
| `MRS-LAND-010` | `warn` |
| `MRS-LAND-011` | `warn` |
| `MRS-LAND-012` | `warn` |
| `MRS-LAND-013` | `warn` |
| `MRS-MATRIX-001` | `warn` |
| `MRS-MATRIX-002` | `error` |
| `MRS-MDL-001` | `warn` |
| `MRS-MDL-002` | `warn` |
| `MRS-MDL-003` | `warn` |
| `MRS-PLAN-001` | `warn` |
| `MRS-POLICY-001` | `unevaluable` |
| `MRS-POLICY-002` | `unevaluable` |
| `MRS-POLICY-003` | `unevaluable` |
| `MRS-POLICY-004` | `unevaluable` |
| `MRS-POLICY-005` | `warn` |
| `MRS-POLICY-006` | `unevaluable` |
| `MRS-POLICY-007` | `warn` |
| `MRS-POLICY-008` | `warn` |
| `MRS-POLICY-009` | `unevaluable` |
| `MRS-POLICY-010` | `unevaluable` |
| `MRS-PREFLIGHT-001` | `error` |
| `MRS-PREFLIGHT-002` | `error` |
| `MRS-PREFLIGHT-003` | `error` |
| `MRS-PREFLIGHT-004` | `error` |
| `MRS-PREFLIGHT-005` | `error` |
| `MRS-PREFLIGHT-006` | `error` |
| `MRS-PREFLIGHT-007` | `error` |
| `MRS-PREFLIGHT-008` | `error` |
| `MRS-PREFLIGHT-009` | `error` |
| `MRS-PREFLIGHT-010` | `unevaluable` |
| `MRS-PREFLIGHT-011` | `warn` |
| `MRS-PREFLIGHT-012` | `error` |
| `MRS-PREFLIGHT-013` | `warn` |
| `MRS-PREFLIGHT-014` | `error` |
| `MRS-PREFLIGHT-015` | `warn` |
| `MRS-PREFLIGHT-016` | `unclassified` |
| `MRS-PRESERVE-001` | `error` |
| `MRS-PRESERVE-002` | `gate-failed` |
| `MRS-PRESERVE-003` | `gate-failed` |
| `MRS-REFRESH-001` | `error` |
| `MRS-REFRESH-002` | `warn` |
| `MRS-REFRESH-003` | `warn` |
| `MRS-REFRESH-004` | `warn` |
| `MRS-REFRESH-005` | `warn` |
| `MRS-REFRESH-006` | `warn` |
| `MRS-REFRESH-007` | `warn` |
| `MRS-REFRESH-008` | `unclassified` |
| `MRS-RETIRE-001` | `unevaluable` |
| `MRS-RETIRE-002` | `warn` |
| `MRS-RETIRE-003` | `warn` |
| `MRS-RETIRE-004` | `warn` |
| `MRS-SMOKE-001` | `unevaluable` |
| `MRS-SMOKE-002` | `error` |
| `MRS-SMOKE-003` | `error` |
| `MRS-SMOKE-004` | `warn` |
| `MRS-SMOKE-005` | `unevaluable` |
| `MRS-SMOKE-006` | `error` |
| `MRS-SMOKE-007` | `warn` |
| `MRS-SPIN-001` | `unevaluable` |
| `MRS-SPIN-002` | `error` |
| `MRS-SPIN-003` | `error` |
| `MRS-SPIN-004` | `warn` |
| `MRS-SPIN-005` | `error` |
| `MRS-SPIN-006` | `warn` |
| `MRS-SPIN-007` | `warn` |
| `MRS-SPIN-008` | `warn` |
| `MRS-SPIN-009` | `warn` |
| `MRS-SPIN-010` | `error` |
| `MRS-SPIN-011` | `error` |
| `MRS-SPIN-012` | `warn` |
| `MRS-SPIN-013` | `warn` |
| `MRS-SPIN-014` | `unevaluable` |
| `MRS-SPIN-015` | `warn` |
| `MRS-SPIN-016` | `warn` |
| `MRS-SPIN-017` | `warn` |
| `MRS-SPIN-018` | `warn` |
| `MRS-STATUS-001` | `warn` |
| `MRS-STATUS-002` | `warn` |
| `MRS-STATUS-003` | `unevaluable` |
| `MRS-STATUS-004` | `warn` |
| `MRS-STATUS-005` | `warn` |
| `MRS-STATUS-006` | `unevaluable` |
| `MRS-STATUS-007` | `unevaluable` |
| `MRS-STATUS-008` | `warn` |
| `MRS-STATUS-009` | `warn` |
| `MRS-STATUS-010` | `warn` |
| `MRS-STATUS-011` | `warn` |
| `MRS-STATUS-012` | `warn` |
| `MRS-STATUS-013` | `warn` |
| `MRS-STATUS-014` | `warn` |
| `MRS-STATUS-015` | `warn` |
| `MRS-STATUS-016` | `warn` |
| `MRS-STATUS-017` | `warn` |
| `MRS-STATUS-018` | `warn` |
| `MRS-SUPV-001` | `warn` |
| `MRS-SUPV-002` | `warn` |
| `MRS-SUPV-003` | `warn` |
| `MRS-SUPV-004` | `warn` |
| `MRS-SUPV-005` | `warn` |
| `MRS-SUPV-006` | `warn` |
| `MRS-SUPV-007` | `warn` |
| `MRS-SUPV-008` | `warn` |
| `MRS-SUPV-009` | `warn` |
| `MRS-SUPV-010` | `warn` |
| `MRS-SUPV-011` | `warn` |
| `MRS-SUPV-012` | `warn` |
| `MRS-SUPV-013` | `warn` |
| `MRS-SUPV-014` | `warn` |
| `MRS-SUPV-015` | `warn` |
| `MRS-TEARDOWN-001` | `unevaluable` |
| `MRS-TEARDOWN-002` | `error` |
| `MRS-TEARDOWN-003` | `error` |
| `MRS-TEARDOWN-004` | `error` |
| `MRS-TEARDOWN-005` | `error` |
| `MRS-TEARDOWN-006` | `error` |
| `MRS-TEARDOWN-007` | `error` |
| `MRS-UPSTREAM-001` | `warn` |
| `MRS-UPSTREAM-002` | `warn` |
| `MRS-WATCH-001` | `error` |
| `MRS-WATCH-002` | `error` |
| `MRS-WATCH-003` | `warn` |
| `MRS-WATCH-004` | `warn` |

### Seed finding types

`pyforge.marshal.seed.detect.findings.FindingType`: the wire value each seed finding carries, with its enum member. The
severity a type carries is decided where it is emitted; each type's remedy is `REMEDIES` in the same module.

| Type | Member |
|---|---|
| `artifact-missing` | `ARTIFACT_MISSING` |
| `artifact-skipped` | `ARTIFACT_SKIPPED` |
| `derived-stale` | `DERIVED_STALE` |
| `kit-instrument-unavailable` | `KIT_INSTRUMENT_UNAVAILABLE` |
| `kit-item-missing` | `KIT_ITEM_MISSING` |
| `kit-item-stale` | `KIT_ITEM_STALE` |
| `legacy-present` | `LEGACY_PRESENT` |
| `managed-file-modified` | `MANAGED_FILE_MODIFIED` |
| `managed-region-missing` | `MANAGED_REGION_MISSING` |
| `managed-region-modified` | `MANAGED_REGION_MODIFIED` |
| `model-behind` | `MODEL_BEHIND` |
| `never-write-violation` | `NEVER_WRITE_VIOLATION` |
| `opted-out` | `OPTED_OUT` |
| `referenced-dep-missing` | `REFERENCED_DEP_MISSING` |
| `slug-unresolved` | `SLUG_UNRESOLVED` |
| `state-invalid` | `STATE_INVALID` |
| `target-escapes-repo` | `TARGET_ESCAPES_REPO` |
| `uncovered` | `UNCOVERED` |

## Exit codes

Two domains (spec-pyforge-marshal:CAP-13 amended 2026-11-10, Story 115.3). `marshal` returns a code from the first for
every verb, and a `seed` verb may also return a code from the second; any other value a handler returns is clamped to
the usage code.

### Every verb

`pyforge.marshal.core.verdict.GUARDED_EXIT_CODES`, marshal's AD-7 frozen domain: the verdict lattice projected to exit codes
(`exit_code_for`) plus the boundary constants `EXIT_OK`, `EXIT_USAGE` and `EXIT_SIGINT`. The *Meaning* cell names the
lattice members and constants that equal the code.

| Code | Meaning | Notes |
|---|---|---|
| `0` | `EXIT_OK`, `clean`, `warn` | Success; a warning never changes the exit code. |
| `1` | `unevaluable` | Marshal could not evaluate. The only code besides `0` and `130` relayed unchanged from a child process. |
| `2` | `EXIT_USAGE`, `scope-violation` | argparse's usage error, a verb whose kill switch is off, a handler's out-of-domain return; also the scope-violation rung. |
| `3` | `gate-failed` | A gate failed. |
| `4` | `error` | A real operation was attempted and failed or was blocked. |
| `130` | `EXIT_SIGINT` | Interrupted (`KeyboardInterrupt`). |

### The `seed` verb group

`pyforge.marshal.seed.errors.SEED_EXIT_CODES`: one code per leaf of `SeedError` (FR-126), admitted from a handler only
when the dispatched command is `seed`.

| Code | Leaf | Notes |
|---|---|---|
| `1` | `ConformanceFailure` | The repository failed conformance (HARD findings). |
| `2` | `UsageError` | An invalid argument or flag. |
| `3` | `PreconditionFailure` | A dirty worktree, a target that is not a git repository, or hand-edited managed content. |
| `4` | `NeverWriteViolation` | A write target matched the never-write set (marshal's AD-61). |
| `5` | `StateInvalid` | `.marshal/seed-state.yml` missing, unreadable or failing its schema. |
| `10` | `InternalError` | An unanticipated internal failure. |
