# Public contract — Steward

Companion to `SPEC.md` (CAP-179, ready 2026-11-10; FR-53; canopy:AD-7, the CLI is the sole public contract; decision
D1 of 2026-11-10: hand-written tables, no generator). It records everything steward serves to a caller and everything
it needs from the tree: every CLI verb path and flag, the verbs it has retired, the MCP tools and targets of the steward
face, every feature-flag key steward reads or owns, every environment variable it reads, every exit code it defines,
its entry points, the Python names other packages import from it, what it needs from the checkout, and the
estate-bound constants. Each row names the capability that carries it, qualified when another Spec owns it. A second
root that rebuilds steward from its Spec rebuilds this surface.

The guard is `src/shared/packages/pyforge-steward/tests/meta/test_public_contract.py` (a live-tree test). It derives
the code side and fails, naming the family and the item, when the code has an item this file lacks:

- **Verb paths and flags:** the argparse tree of `pyforge.steward.cli.build_parser()`. Every verb path that is a leaf,
  or a group that takes arguments of its own, is a row, and the row lists exactly that path's option strings and
  positionals (written `<dest>`). `-h`/`--help` is argparse's own on every path and is not listed. A verb whose flag is
  off stays in the parser, marked disabled in its help.
- **Feature-flag keys:** every string literal of the form `pyforge.<station>.<name>` in steward's source that is not a
  module path, and every key of `src/platform/config/flags.json` that steward owns (its `pyforge.steward.*`
  namespace, or `metadata.owner: steward`). A module path is a steward module or package on disk, or one of the
  other-station modules the test names in a fixed set (`pyforge.doctor.sources`, `pyforge.scribe.cli`, which
  `steward estate reconcile` runs with `python -m`); the test never reads another station's tree, so a new
  other-station literal is reported as a flag key until it joins that set. A literal of that shape that is not a flag
  key (the hook spec name) is a row of *Entry points*.
- **Environment variables:** an AST scan of steward's source for `os.environ` / `os.getenv` reads, and for reads
  through a local name bound to an expression over `os.environ` (`env = dict(os.environ)`), each name a literal, a
  module constant or another steward module's constant.
- **Exit codes:** every module-level `EXIT_*` constant in steward's source, by module and value.
- **MCP names:** the `*_TOOL` constants of django-steward's `mcp_asgi.py`, and the `STEWARD_DUTIES` keys and the
  `StationVerb("steward", ...)` row of django-pyforge's `station_cli.py`, read with `ast`, never imported.

The other way, it fails when this file or `SPEC.md` names a steward verb path in a code span that is neither in the
parser nor in *Retired verbs* below, or when a retired verb is in the parser again, and when a row under any `##`
heading below that holds a table names no capability (a bare `CAP-n` must be defined in `SPEC.md`).

Environment reads and flag keys built by concatenation or held in a value passed in at run time are out of an AST
scan's reach: a name assembled from pieces (`"STEWARD_" + name`), a mapping handed to a function as a parameter, or a
key built by an f-string is not derived, so the rows below that the scan cannot see are kept by hand (they are marked
*not derived*). An inherited read made by `pyforge.core` on steward's behalf is listed for the reader's sake and is
also not derived.

A literal that names a module is dropped from the flag-key scan even where the same string is also a flag key:
`pyforge.steward.budget`, `pyforge.steward.marketplace_pages` and `pyforge.steward.pages_duty` are modules and keys at
once, and only the flag tree's ownership rule (their `pyforge.steward.*` namespace) brings them in. A key outside
steward's namespace whose string is a listed module path would be missed by both. The test reds when a literal it
drops this way is a key of the flag tree and this paragraph does not name it.

How the test reads this file: only the table rows under the `##` headings, by their column names (*Verb path*,
*Flags*, *Arguments* for verbs; the first cell elsewhere, and the first two cells for an exit code; *Capability* on
every row), as backticked tokens. Prose is not read. Keep the headings and column names exact, and keep a `|` out of a
table cell.

## CLI verbs and flags

The program is `steward` (`[project.scripts] steward = "pyforge.steward.cli:main"`); the same tree is reached as
`pyforge steward` through pyforge-core's front door, and as `python -m pyforge.steward`. Run it from the repository
root. `main()` is the sole owner of the exit code (canopy:AD-8): a duty returns a `DutyResult` and never calls
`sys.exit()`. A duty whose kill switch is off stays listed in `--help`, marked `[disabled: flag … is off]`, and exits
2 (spec-feature-flag-governance:CAP-7).

| Verb path | Flags | Arguments | Capability | What it does |
|---|---|---|---|---|
| `steward` | `--version` | — | spec-pyforge-unifying-strategy:CAP-5 | The program. `--version` prints `steward <version>`; a bare `steward` prints help and exits 0. |
| `steward keys encrypt` | `--recipient`, `-r`, `--output`, `-o` | `<file>` | CAP-1 | age-encrypts a file to a recipient. |
| `steward keys decrypt` | `--identity`, `-i`, `--output`, `-o` | `<file>` | CAP-1 | age-decrypts a file with an identity. |
| `steward keys rotate` | `--scope`, `--new-identity`, `--inventory` | — | CAP-1 | Rotates an issued identity, re-encrypting every secret it protects. |
| `steward keys list` | `--inventory`, `--json` | — | CAP-1 | Lists the known credential identities from `.steward/keys-inventory.yaml`, never a secret value. |
| `steward keys audit` | `--drift`, `--path`, `--secrets`, `--inventory` | — | CAP-1, CAP-164 | Scans for host-unscoped credential attachment (`--drift`) or plaintext secrets (`--secrets`); `--inventory` checks that no payload serves both GitHub Enterprise scopes. |
| `steward keys revoke` | `--scope`, `--inventory` | — | CAP-1 | Marks a credential retired and prints manual remediation guidance. |
| `steward keys exec` | `--scope`, `--approval`, `--inventory` | `<argv>` | CAP-164 | Runs the command after `--` with a scoped GitHub Enterprise token in `GH_ENTERPRISE_TOKEN` and `GH_HOST`, the only delivery path; behind `pyforge.steward.ghe_fleet_credentials`. |
| `steward deploy perimeter` | `--workers`, `--cache-backend`, `--channel-layer-backend`, `--trusted-address`, `--tls-cert`, `--tls-key`, `--output-dir`, `--app-db-role`, `--audit-retention-db-role`, `--asgi-application` | — | CAP-114 | Validates a dashboard deployment's cross-worker shareability and renders its daphne and nginx manifests; behind `pyforge.steward.deploy_perimeter`. |
| `steward deploy static` | `--board`, `--panel`, `--access-column` | — | CAP-116 | Writes a board as a self-contained static export under `docs/dashboard/<board>/`; refuses a board with an access column. The file lands through a pull request. |
| `steward deploy nic validate` | `-f`, `--config` | — | CAP-176 | Runs `nic validate` on a tracked NIC config. |
| `steward deploy nic up` | `-f`, `--config` | — | CAP-176, CAP-177, CAP-178 | Runs `nic deploy`, then installs the config's packs as Argo CD Applications behind `pyforge.steward.nkp_packs`; refuses a missing pack CLI before `nic` starts. |
| `steward deploy nic kubeconfig` | `-f`, `--config` | — | CAP-176 | Runs `nic kubeconfig`. |
| `steward deploy nic outputs` | `-f`, `--config` | — | CAP-176 | Runs `nic outputs`. |
| `steward deploy nic down` | `-f`, `--config` | — | CAP-176 | Runs `nic destroy --auto-approve`. All five `deploy nic` verbs sit behind `pyforge.steward.nkp_deploy`. |
| `steward provision` | `--list-modules`, `--module`, `--prove-class-path`, `--plugin`, `--skill`, `--env`, `--runner`, `--list`, `--json`, `--verify` | — | CAP-3, CAP-18, CAP-19, CAP-20, CAP-29, CAP-35 | Materializes, lists and verifies pixi environments (`--env`, `--list`, `--verify`); provisions a BMAD module (`--module`, `--list-modules`); installs a consented labs skill (`--plugin labs --skill`); proves the fresh-clone class path. Flags, not nested verbs. |
| `steward budget set` | `--cap` | — | CAP-4 | Declares a machine-readable ceiling (`1500usd/month`). |
| `steward budget show` | `--json` | — | CAP-4 | Prints the declared ceilings. |
| `steward budget check` | — | — | CAP-4 | Reports spend against the ceiling; v1 has no metered source and exits 3. Every `budget` verb sits behind `pyforge.steward.budget`. |
| `steward sync reconcile` | `--github-item`, `--jira-issue`, `--schedule`, `--config`, `--dry-run` | — | CAP-57, CAP-58, CAP-59, CAP-60, CAP-61 | Re-reads a linked GitHub Projects V2 item and Jira issue and converges the divergent side; `--schedule` reconciles every linked item in one run. |
| `steward workspace start` | `--from`, `--json` | `<slug>` | CAP-104, CAP-158 | Creates a scratch worktree on a new branch from `origin/main` (or `--from`) and records it. |
| `steward workspace ls` | `--json` | — | CAP-105 | Lists the tool's own scratch worktrees from bookkeeping, no git subprocess. |
| `steward workspace status` | `--json` | `<slug>` | CAP-106, CAP-158 | Reports dirty, ahead and merged per owned worktree. |
| `steward workspace clean` | `--merged-only`, `--delete`, `--json` | `<slug>` | CAP-107, CAP-108, CAP-155, CAP-157, CAP-165 | Removes merged worktrees, archived rather than deleted, only the ones it created; parks unlanded commits as a preserve tag behind `pyforge.steward.workspace_preserve_tag`. |
| `steward upgrade bmad-core` | `--target`, `--apply`, `--branch`, `--installer`, `--no-shims`, `--json`, `--package-root`, `--installed-package-root`, `--catalog-dir`, `--repo-root`, `--installed-version` | — | CAP-9, CAP-10, CAP-11, CAP-14, CAP-15, CAP-16, CAP-17 | The pre-flight diff for a target bmad-method release, or the deliberate `--apply` on a review branch with the custom-surface reconcile. |
| `steward upgrade pin-fan-out` | `--package`, `--from`, `--to`, `--repo-root`, `--loops-home`, `--json` | — | CAP-12 | Report only: every pin site a bmad-loop or bmad-method move touches, moved or not. |
| `steward upgrade prove-landed` | `--repo-root`, `--loops-home`, `--no-init`, `--json` | — | CAP-13 | One verdict after an apply: `bmad-drift-check`'s exit, the CFE meta-tests, each loop home's `bmad-loop init` and `validate`. |
| `steward upgrade verify` | `--repo-root`, `--loops-home`, `--no-init`, `--json` | — | CAP-13 | An alias of `steward upgrade prove-landed`. |
| `steward suite pipeline-truth` | `--repo-root`, `--baseline`, `--json` | — | CAP-21 | Upstream, recipe, channel, installed and wired state for the 13 bmad-suite packages, drift named per stage. |
| `steward suite advance` | `--package`, `--repo-root`, `--baseline`, `--dry-run`, `--json` | — | CAP-22 | Advances one stale suite package end to end to a reviewable pull request, never auto-merged. |
| `steward init` | `--json` | — | CAP-48 | Reports the pixi, git, gh and podman prerequisites with named remedies. |
| `steward shell-init` | `--json` | — | CAP-48 | Emits an idempotent PATH, completions and environment snippet for `eval`. |
| `steward setup` | `--json`, `--url`, `--dest`, `--env` | — | CAP-48, CAP-154 | Clones when `--dest` is missing, runs `pixi install`, installs the pre-commit hooks (behind `pyforge.steward.setup_hooks`). |
| `steward initrepo` | `--json`, `--repo`, `--env` | — | CAP-48 | Scaffolds `pyforge.toml` when absent, materializes the environment, runs `steward validate-fast`. |
| `steward validate-fast` | `--json`, `--repo`, `--env` | — | CAP-48 | The fast green gate: prerequisites, `environment.yaml` sync, a `steward --version` smoke. |
| `steward restore` | `--drill`, `--backup-path` | — | CAP-180 | Restores a custom-format dump into a scratch database and asserts the manifest's row counts through the host's `src/platform/db/postgres_backup.py`. |
| `steward revoke` | `--sub`, `--python` | — | CAP-180 | Runs the host's `manage.py revoke_subject --sub <id> --json` and reports what it said. |
| `steward track assemble` | `--run-dir`, `--out` | — | CAP-54 | Writes one tracked `track.json` from a run directory's journal, gate record and state; not a detector. |
| `steward guards catalog` | — | — | CAP-55 | Prints the seven-category Guard library. |
| `steward guards lacking` | `--spec` | — | CAP-55 | The Guard categories a Spec (or the library) still lacks; never a PR verdict. |
| `steward guards source-ground` | `--text`, `--repo` | — | CAP-55 | Requires a resolvable `[source: path]` on each claim of a text; not a PR gate. |
| `steward cutover plan` | `--regenerate`, `--append`, `--check`, `--ledger`, `--json` | — | spec-python-foundry-cutover:CAP-9 | Generates (`--regenerate`, `--append`, behind `pyforge.steward.cutover_ledger_write`) or validates (`--check`, the default; exit 1 on a finding) `docs/foundry/capability-ledger.yaml`. |
| `steward cutover flip` | `--to`, `--flags` | — | spec-python-foundry-cutover:CAP-8 | Sets `pyforge.cutover_root`; refused while a Marshal loop runs; stamps the Realization log. |
| `steward ledger-query` | `--unimplemented`, `--unlinked`, `--ready`, `--running`, `--station`, `--status`, `--epic`, `--search`, `--format`, `--output`, `--sync-postgres`, `--flag` | — | CAP-146, CAP-147, CAP-148, CAP-149, CAP-150 | One query engine over every station's tracked ledger; exporters behind the `ledger_query_*` keys, overridable with `--flag`. |
| `steward catalog` | `--catalog`, `--json` | — | CAP-117 | The estate BMAD catalog; a bare `steward catalog` runs `check`. |
| `steward catalog check` | `--catalog`, `--json` | — | CAP-117 | Binds declared backends and sources to plugins, validates listings, detects manifest drift. |
| `steward catalog list` | `--catalog`, `--json` | — | CAP-120 | Every listing with its source and trust tier. |
| `steward catalog render` | `--check`, `--catalog`, `--json` | — | CAP-117, CAP-120, CAP-123, CAP-169 | Regenerates the Claude and Codex marketplace manifests (estate catalog: also the Frame index and browse list); `--check` reports drift and writes nothing. |
| `steward catalog pointers` | `--catalog`, `--json` | — | CAP-117 | Prints how the installer, Claude and Codex point at this catalog. |
| `steward catalog ship` | `--backend`, `--output`, `--catalog`, `--json` | — | CAP-119 | Materializes the vendored snapshot and runs the default (conda) ship backend. |
| `steward catalog publish` | `--listing`, `--review`, `--dry-run`, `--catalog`, `--json` | — | CAP-118 | Appends a reviewed module row to `registry/estate.yaml`; refuses without a review record. |
| `steward measure` | `--measures-dir`, `--json` | — | CAP-44 | The Build League measure catalog. |
| `steward measure check` | `--measures-dir`, `--json` | — | CAP-44, CAP-45 | Validates measure declarations: new rows start off, archived ids are never reused. |
| `steward measure list` | `--measures-dir`, `--json` | — | CAP-44 | Every measure with its dimension, source and state. |
| `steward load` | `--corridor`, `--json` | — | CAP-139 | The extract corridor; transports are declared in `corridor.yaml`. |
| `steward load inbound` | `--file`, `--waybill`, `--transport` | — | CAP-139 | Loads an inbound extract, idempotent on batch sha and waybill. |
| `steward load outbound` | `--file`, `--waybill`, `--transport`, `--slice`, `--signer` | — | CAP-139, CAP-142 | Loads an outbound extract; default deny without a named slice and signer. |
| `steward passport` | `--json` | — | CAP-140 | Vendor work-passport identity. |
| `steward passport mint` | `--vendor-id`, `--jira-key`, `--github-item-id`, `--title` | — | CAP-140 | Mints a fresh Work Passport UUID per inbound key; never merges by key. |
| `steward glass` | `--json` | — | CAP-141 | As-of glass: standup and shipped freshness over the inbound corridor. |
| `steward glass export` | `--format`, `--flag` | — | CAP-141 | Renders the two-row standup and shipped table, behind `pyforge.steward.glass_export` (or `--flag enable_glass_export=true`). |
| `steward quarantine` | `--json`, `--corridor` | — | CAP-143 | The shelf for inbound rows without a passport. |
| `steward quarantine admit` | `--vendor-id`, `--jira-key`, `--github-item-id`, `--title`, `--arrived-at` | — | CAP-143 | Admits an inbound row without a passport; mints during the configured window, then refuses to mint. |
| `steward quarantine shelf` | `--include-linked` | — | CAP-143 | Lists the unlinked rows on the shelf. |
| `steward session check` | `--repo`, `--project`, `--json` | — | CAP-5, CAP-162 | One verdict over the seven session preconditions; the bmad-method finding is `bmad-drift-check`'s exit, read by command (spec-pyforge-steward:CAP-182). |
| `steward deck-drift` | `--slug`, `--path`, `--artifact-key`, `--bridge-state`, `--baseline` | — | CAP-135 | Flags silent size or etag drift on a pulled Design deck against a steward-owned baseline sidecar; Herald owns the pull. |
| `steward estate plan` | `--json`, `--due` | — | CAP-167 | Dry-runs the pin upgrade through the pin policy; `--due` exits non-zero when the last journal is older than 30 days or absent; exits 3 when the pixi dry run fails. |
| `steward estate refresh` | `--transitive` | — | CAP-167 | Runs the upgrade, restores losses, re-locks and journals. `--transitive` (`pixi update`) is operator-only, denied to agents by the session hook. |
| `steward estate reconcile` | — | — | CAP-167 | Regenerates the derived surfaces, runs the gating checks, reconciles spec-surface drift. |
| `steward estate verify` | `--env`, `--lane`, `--probe`, `--all`, `--keep`, `--ignore-ci-pauses`, `--budget-minutes` | — | CAP-167 | Installs the default tier in a detached worktree and runs the CI lanes and realization probes. |
| `steward estate realize` | `--plan`, `--yes`, `--all`, `--journal` | — | CAP-167 | Re-applies side-effect installs for moved register rows; agents run `--plan`, `--yes` is the operator's. |
| `steward estate status` | `--json`, `--all` | — | CAP-167 | Prints the last estate refresh journal (`--all`: every one). Every `estate` verb sits behind `pyforge.steward.estate_refresh`. |
| `steward ci status` | `--json` | — | CAP-166 | The pause state of every CI surface, one table or `ci-status-schema` JSON; exit 1 with the envelope on stdout on a partial read. |
| `steward ci vars` | `--refresh` | — | CAP-166 | Reads, or with `--refresh` rewrites, the gitignored `.steward/ci-vars.json` snapshot. |
| `steward ci pause` | `--reason`, `--review-by`, `--yes`, `--i-am-removing-a-merge-gate` | `<target>` | CAP-166 | Pauses a CI surface; a dry run unless `--yes` (operator only). |
| `steward ci resume` | `--yes` | `<target>` | CAP-166 | Resumes a paused CI surface; a dry run unless `--yes`. Every `ci` verb sits behind `pyforge.steward.ci_pause_control`. |
| `steward pages build` | `--json`, `--dry-run`, `--stamp`, `--site-url` | — | CAP-168 | Writes `docs-site/src/content/fleet-status.json`, runs `pages-check`, reports the tree hash. |
| `steward pages deploy` | `--dry-run`, `--wait` | — | CAP-168 | Triggers one `pages.yml` run on `main` and names it. |
| `steward pages status` | `--json`, `--site-url` | — | CAP-168 | The live root, the last `pages.yml` run and the registry verdict. Every `pages` verb sits behind `pyforge.steward.pages_duty`. |
| `steward preflight verify-deferred` | `--since` | — | CAP-159 | Lists the runs that left lanes to CI and the pushes that skipped the preflight, then runs the full preflight on HEAD: exit 0 green, 1 red, 3 could not run. |

`five_tier.py` is a check library with no verb (canopy:AD-14's five-tier completeness, read by
`tests/meta/test_five_tier_check.py` and `.github/workflows/pyforge-pip-install.yml`); it is not part of the CLI.

## Retired verbs

A retired verb is a usage error (exit 2). This file and `SPEC.md` may name these and no other verb the parser lacks.

| Verb path | Retired | Now | Capability |
|---|---|---|---|
| `steward deploy dashboard` | 2026-10-15, Story 102.3 | `steward pages build` and `steward pages deploy`; the Pages artifact is built by the one Pages workflow | CAP-2 (retired 2026-10-15; superseded by CAP-168) |
| `steward deploy status` | 2026-10-15, Story 102.3 | `steward pages status` | CAP-2 (retired 2026-10-15; superseded by CAP-168) |
| `steward cutover apply` | 2026-11-10, Story 121.2 (operator ruling 2: copying trees into foundry is retired) | none: the ledger row decides each capability's mode (`steward cutover plan`) | spec-python-foundry-cutover:CAP-9 |

## MCP face

Steward's station face is `POST /stations/steward/mcp` on the platform host. The host code is django-steward's
(`src/shared/packages/django-steward/src/django_steward_portal/mcp_asgi.py`, built by django-pyforge's
`build_station_mcp_asgi`) and django-pyforge's closed verb table (`src/shared/packages/django-pyforge/src/django_pyforge/station_cli.py`);
this package ships no MCP server. How to start the host and send a request: `docs/how-to/reach-a-station-mcp-endpoint.md`.
The table runs every target in `pyforge-guild` and counts exits 0 and 1 as a result.

| Name | Kind | Runs | Capability |
|---|---|---|---|
| `start_duty` | MCP tool | Takes `target` (one of the three below) and `assertion`; starts a supervised run and returns `{"handle": …}` at once. | spec-pyforge-unifying-strategy:CAP-20 |
| `get_duty` | MCP tool | Takes `handle` and `assertion`; returns the supervisor's record of that run. | spec-pyforge-unifying-strategy:CAP-20 |
| `run_duty` | supervisor runner, not an MCP tool | The `start_duty` payload: the closed table's steward row. Behind `pyforge.steward.start_tool_cli`. | spec-pyforge-unifying-strategy:CAP-20 |
| `ci-status` | target | `steward ci status --json` | spec-pyforge-unifying-strategy:CAP-20, CAP-166 |
| `estate-plan` | target | `steward estate plan --json` | spec-pyforge-unifying-strategy:CAP-20, CAP-167 |
| `estate-status` | target | `steward estate status --json` | spec-pyforge-unifying-strategy:CAP-20, CAP-167 |

## Feature-flag keys

Read only through `pyforge.core.flags` from the one tree `src/platform/config/flags.json`, composed per environment by
`src/platform/config/flag-overlays.json`. *Default* is the tree's `defaultVariant`, followed by each overlay (dev,
staging) whose value differs from it; production differs from no default here. A kill switch (default on) refuses its verb with exit 2 when off (spec-feature-flag-governance:CAP-7).

| Key | Default | Read by | Capability |
|---|---|---|---|
| `pyforge.steward.budget` | on (kill switch) | `cli.py` (`steward budget`) | CAP-4 |
| `pyforge.steward.ci_pause_control` | off; dev on | `ci.py`, `preflight_ci.py`, `pages_duty.py` (`steward ci`, the preflight's pause filter) | CAP-166 |
| `pyforge.steward.cutover_ledger_write` | on (kill switch) | `cutover.py` (`steward cutover plan --regenerate` and `--append`) | spec-python-foundry-cutover:CAP-9 |
| `pyforge.steward.deploy_perimeter` | on (kill switch) | `cli.py` (`steward deploy perimeter`) | CAP-114 |
| `pyforge.steward.estate_refresh` | off; dev on | `estate.py` (every `estate` verb) | CAP-167 |
| `pyforge.steward.frame_upstream_check` | on (kill switch) | `frames.py` (`python -m pyforge.steward.frames --upstream-check`) | CAP-6 |
| `pyforge.steward.ghe_fleet_credentials` | off | `keys.py`, `cli.py` (`steward keys exec`, the GitHub Enterprise host) | CAP-164 |
| `pyforge.steward.glass_export` | off | `glass.py`, `sprint_ledger_query.py` (`steward glass export`) | CAP-141 |
| `pyforge.steward.ledger_query_dossier_export` | off | `sprint_ledger_query.py` (`steward ledger-query --format static-dossier`) | CAP-147 |
| `pyforge.steward.ledger_query_herald_facts` | off | `sprint_ledger_query.py` (`--format herald-facts`) | CAP-147 |
| `pyforge.steward.ledger_query_jira_github_matrix` | off | `sprint_ledger_query.py` (`--format sync-matrix`, `jira-csv`, `github-json`) | CAP-147 |
| `pyforge.steward.ledger_query_postgres_sync` | off | `sprint_ledger_query.py` (`--sync-postgres`) | CAP-147 |
| `pyforge.steward.ledger_query_vizro_dataset` | off | `sprint_ledger_query.py` (`--format atlas-dataset`) | CAP-147 |
| `pyforge.steward.marketplace_pages` | off; dev on | `marketplace_pages.py` (the marketplace Pages index; `--flag-env` hands it to `pages.yml`) | CAP-171 |
| `pyforge.steward.nkp_deploy` | on (kill switch) | `cli.py`, `deploy_nic.py` (`steward deploy nic`) | CAP-176 |
| `pyforge.steward.nkp_packs` | on (kill switch) | `deploy_nic_packs.py` (the pack step of `steward deploy nic up`) | CAP-177 |
| `pyforge.steward.pages_duty` | off; dev on | `pages.py`, `pages_duty.py` (`steward pages`, and `pages.yml`'s no-op skip, mount and release asset) | CAP-168 |
| `pyforge.steward.preflight_ci_arbitrates` | off; dev on | `preflight.py` (the touched scope when `PYFORGE_PREFLIGHT_SCOPE` is unset) | CAP-159 |
| `pyforge.steward.preflight_critical_path` | on (kill switch) | `preflight.py` (lanes admitted longest-first by cores) | CAP-175 |
| `pyforge.steward.setup_hooks` | on (kill switch) | `cli.py` (`steward setup`) | CAP-154 |
| `pyforge.steward.sync_github_only_marker` | off; dev and staging on | `sync.py` (skip a board item marked GitHub-only) | CAP-60 |
| `pyforge.steward.workspace_clean` | on (kill switch) | `cli.py` (`steward workspace clean`) | CAP-107 |
| `pyforge.steward.workspace_full_refs` | on (kill switch) | `cli.py` (`steward workspace start`, `status`, `clean`) | CAP-158 |
| `pyforge.steward.workspace_own_worktrees_only` | on (kill switch) | `cli.py` (`steward workspace clean`) | CAP-108 |
| `pyforge.steward.workspace_preserve_tag` | off | `workspace.py` (preserve tag before a removal) | CAP-165 |
| `pyforge.steward.herald_webhook_sidecar` | off; dev on | the host: `django_pyforge/sidecar_forward.py`; owned by steward, not read by this package | CAP-69 |
| `pyforge.steward.object_store_consumer` | off; dev and staging on | the host: `django_pyforge/object_store.py`; owned by steward, not read by this package | CAP-163 |
| `pyforge.steward.start_loop_dispatch` | off | the host: `django_pyforge/station_cli.py` (`start_loop` only for an admin); owned by steward | spec-pyforge-unifying-strategy:CAP-20 |
| `pyforge.steward.start_tool_cli` | on (kill switch) | the host: `django_pyforge/station_cli.py` (every start tool's verb table); owned by steward | spec-pyforge-unifying-strategy:CAP-20 |
| `pyforge.steward.station_client_identity` | on (kill switch) | the host: `django_pyforge/station_client.py`; owned by steward | spec-pyforge-unifying-strategy:CAP-6 |
| `pyforge.steward.stations_index` | off; dev on | the host: `src/platform/config/stations_index.py`; owned by steward | spec-pyforge-unifying-strategy:CAP-3 |
| `pyforge.cutover_root` | `local-recipes` (variants `local-recipes`, `foundry`) | written by `steward cutover flip`; read by `pyforge.core.cutover_root` (metadata owner steward). The operator flips it by hand once the Launch slice is proven | spec-python-foundry-cutover:CAP-8 |

## Environment variables

Steward also hands its whole environment to some children (minus named scrubs); that copy is not a read of any one
name and is not listed. Names steward sets for a child and never reads: `GH_HOST` and `GH_ENTERPRISE_TOKEN` (`steward
keys exec`, after removing the ambient GitHub token variables), `KUBECONFIG` (the pack step), the names of the config's
`.env` secrets (`steward deploy nic`; the config chooses them), `PIXI_FROZEN` (`steward session check`'s
`bmad-drift-check` child), `TMPDIR`, `COVERAGE_FILE`, `PYTEST_XDIST_AUTO_NUM_WORKERS` and the `GITHUB_*` step
variables (the preflight's lanes and its CI-rule evaluator), and the git identity (`GIT_AUTHOR_*`, `GIT_COMMITTER_*`)
with `GIT_DIR` and `GIT_WORK_TREE` of the preflight's snapshot git. Names steward sets for a child that it also reads
(each a row below): `CONDA_PREFIX` (`steward provision`'s installer child), `PATH` (`steward upgrade bmad-core
--apply`'s installer), `BMAD_ACTIVE_PROJECT` (`steward upgrade bmad-core`'s config-layer probe), `GIT_INDEX_FILE`
(the snapshot index) and `PYFORGE_PREFLIGHT_SCOPE` (`steward preflight verify-deferred`'s child). `steward shell-init`
sets nothing itself: it prints `PYFORGE_REPO_ROOT` and `PATH` for the caller's shell to export.

| Variable | Read by | Effect | Capability |
|---|---|---|---|
| `BMAD_ACTIVE_PROJECT` | `session.py` | The Tier-3 feed project of `steward session check` when `--project` is absent (before the marker file). `upgrade.py` also drops it from the installer's environment. | CAP-5 |
| `CONDA_PREFIX` | `deploy_nic.py`, `provision.py`, `catalog.py` | Where `nic` is found (`$CONDA_PREFIX/bin/nic`); the active environment when the Guild env directory is absent; a wielded module's installed share tree. | CAP-176, CAP-3, CAP-117 |
| `DJANGO_SETTINGS_MODULE` | `dashboard/corridor_load.py`, `dashboard/glass_query.py`, `dashboard/passport_mint.py`, `dashboard/passport_sync.py` | Unset and Django unconfigured: the module configures Django itself before an ORM write. | CAP-139, CAP-140, CAP-141 |
| `GITHUB_API_BASE_URL` | `keys.py` | Set to a host other than github.com, with `pyforge.steward.ghe_fleet_credentials` on: the GitHub Enterprise host `steward keys` resolves. | CAP-164 |
| `GIT_INDEX_FILE` | `preflight_ci.py` | Removed from git's environment before the preflight reads the tree, then pointed at a snapshot index. `preflight_verify.py` also scrubs the git hook variables (`GIT_DIR`, `GIT_WORK_TREE` and four more) before the full preflight (*not derived*). | CAP-159 |
| `PATH` | `bootstrap.py`, `upgrade.py` | `steward shell-init` prepends `~/.pixi/bin`; `steward upgrade bmad-core --apply` prepends the pixi bin to the installer's `PATH` and looks the installer up there. | CAP-48, CAP-14 |
| `PIXI_ENVIRONMENT_NAME` | `preflight.py` | The invoking environment of a lane whose dependency names none (default `pyforge-guild`). | CAP-159 |
| `PIXI_PROJECT_ROOT` | `preflight.py`, `preflight_budget.py` | The repository root of `python -m pyforge.steward.preflight` and of its `--budget` report (default `.`). | CAP-159, CAP-175 |
| `PYFORGE_PREFLIGHT_SCOPE` | `preflight.py` | `touched` or `full`; unset follows `pyforge.steward.preflight_ci_arbitrates`. `steward preflight verify-deferred` sets it to `full` for its child. | CAP-159 |
| `PYFORGE_REPO_ROOT` | `dashboard/views_htmx.py` | The repository root the HTMX ledger views read when the Django setting of the same name is absent. | CAP-146 |
| `PYFORGE_STUDIO_ROOT` | `suite.py` | The Manticore studio root the wired-or-not probe reads (default under the home directory). | CAP-21, CAP-34 |
| `PYTEST_ADDOPTS` | `preflight.py`, `preflight_suite_reduction.py` | A lane's own pytest options are kept and the lane's basetemp and cache flags appended; a reduced suite strips the inherited ones. | CAP-159, CAP-175 |
| `SOPS_AGE_KEY_FILE` | `deploy_nic.py` | The age identity that decrypts the config's `.env` when the config names an `env:` secret. | CAP-176 |
| `PYFORGE_ASSERTION_PUBLIC_KEY` | `dashboard/consumers.py` | The public key the `/ws/events/` consumer verifies an assertion with, when the Django setting is absent. | spec-pyforge-unifying-strategy:CAP-8 |
| `REDIS_BROKER_URL` | `dashboard/consumers.py` | The broker the `/ws/events/` consumer streams from, when the Django setting is absent. | spec-pyforge-unifying-strategy:CAP-8 |
| `STEWARD_EXPORT_WEBHOOK_SECRET` | `dashboard/export.py` | The HMAC secret of a refused-export webhook, read fresh on every refusal, never defaulted. | CAP-113 |
| `GITHUB_BASE_REF` | `preflight_ci.py` (*not derived*: read from the environment mapping the CI-rule evaluator is handed) | The base ref a workflow step sees; `main` when unset. | CAP-159 |
| `PYFORGE_FLAGS_PATH` | inherited through `pyforge.core.cutover_root` (*not derived*) | The flag tree every key above is read from. | spec-pyforge-core:CAP-13 |
| `PYFORGE_ENVIRONMENT` | inherited through `pyforge.core.flags` (*not derived*) | The overlay the tree is read under (`dev` when unset). | spec-feature-flag-governance:CAP-5 |

## Exit codes

`main()` acts on a duty's `DutyResult`: ok is 0, not ok is 1, unless the duty requests a documented code in
`details["exit_code"]`. A crash is never 1. `steward deploy nic` passes `nic`'s own non-zero exit through, and
`steward keys exec` passes its child's (both *not derived*: the code is the child's, not a constant).

| Code | Constants | Program | Meaning | Capability |
|---|---|---|---|---|
| `0` | `cli.EXIT_OK` | `steward` | The duty ran and reported ok; also `--help`, `--version` and a bare `steward`. | CAP-179 (canopy:AD-8) |
| `1` | `cli.EXIT_FAILED` | `steward` | A duty ran and reported not ok: the only legitimate 1 (`steward cutover plan --check` with a finding, `steward ci status` on a partial read, `steward estate plan --due` overdue). | CAP-179 (canopy:AD-8) |
| `1` | `ci.EXIT_CI_GH_FAILED` | `steward` | `steward ci pause` or `steward ci resume` with `--yes`: `gh variable set` or `delete` failed. | CAP-166 |
| `1` | `estate_reconcile.EXIT_RECONCILE_CHECKS` | `steward` | `steward estate reconcile`: a gating check failed. | CAP-167 |
| `2` | `cli.EXIT_USAGE` | `steward` | Usage: an argparse error or a retired verb; a kill switch or a flag-gated verb whose flag is off; a bad `PYFORGE_ENVIRONMENT` or overlay; the usage refusals of `steward deploy nic`, `steward cutover plan`, `steward workspace clean` and `steward keys exec`. | CAP-179 (canopy:AD-8), spec-feature-flag-governance:CAP-7 |
| `3` | `cli.EXIT_BUDGET_NOT_CONFIGURED` | `steward` | `steward budget check`: no metered spend source is configured (the only answer v1 gives). | CAP-4 |
| `3` | `ci.EXIT_CI_REFUSAL` | `steward` | `steward ci`: `pyforge.steward.ci_pause_control` is off, or gh cannot read. | CAP-166 |
| `3` | `pages_duty.EXIT_PAGES_REFUSAL` | `steward` | `steward pages`: `pyforge.steward.pages_duty` is off; refused before any subprocess. | CAP-168 |
| `3` | `estate.EXIT_ESTATE_REFUSAL` | `steward` | `steward estate plan` refuses when its pixi upgrade dry run fails, on every path and ahead of `--due` (Story 123.3); every estate verb when `pyforge.steward.estate_refresh` is off; `steward estate refresh` on a dirty tree, on `main`, or when a step refuses (the files reset to the base commit). | CAP-167 |
| `3` | `preflight_verify.EXIT_CANNOT_RUN` | `steward` | `steward preflight verify-deferred`: the full preflight could not run (no pixi, or its configuration error). | CAP-159 |
| `70` | `cli.EXIT_INTERNAL` | `steward` | An internal error: an exception escaped a duty (EX_SOFTWARE). | CAP-179 (canopy:AD-8) |
| `130` | `cli.EXIT_INTERRUPTED`, `preflight_verify.EXIT_INTERRUPTED` | `steward` | Interrupted (128 + SIGINT); `steward preflight verify-deferred` when its child was. | CAP-179 (canopy:AD-8), CAP-159 |
| `0` | `preflight.EXIT_OK` | `python -m pyforge.steward.preflight` | Every selected lane passed. | CAP-159 |
| `1` | `preflight.EXIT_LANE_RED` | `python -m pyforge.steward.preflight` | A lane failed. | CAP-159 |
| `2` | `preflight.EXIT_CONFIG` | `python -m pyforge.steward.preflight` | The lane graph or the scope could not be read. | CAP-159 |
| `130` | `preflight.EXIT_INTERRUPT` | `python -m pyforge.steward.preflight` | Interrupted; running lanes are stopped. | CAP-159 |
| `0` | `preflight_budget.EXIT_OK` | `python -m pyforge.steward.preflight --budget` | Every lane is within 1.5 times its budget. | CAP-175 |
| `1` | `preflight_budget.EXIT_OVER_BUDGET` | `python -m pyforge.steward.preflight --budget` | A lane's median is over 1.5 times its budget (a warning; never the preflight's verdict). | CAP-175 |
| `2` | `preflight_budget.EXIT_CANNOT_EVALUATE` | `python -m pyforge.steward.preflight --budget` | The journal or `docs/governance/preflight-budgets.toml` could not be read. | CAP-175 |
| `0` | `frames.EXIT_OK` | `python -m pyforge.steward.frames` | Every Frame passes the four-field preflight. | CAP-53 |
| `1` | `frames.EXIT_FAIL` | `python -m pyforge.steward.frames` | A Frame fails it. | CAP-53 |
| `2` | `frames.EXIT_COULD_NOT_RUN`, `frames.EXIT_USAGE` | `python -m pyforge.steward.frames` | Could not run; `--upstream-check` with `pyforge.steward.frame_upstream_check` off (steward's usage code, no new one). | CAP-53, CAP-6 |

## Entry points

| Entry point | Kind | Runs | Capability |
|---|---|---|---|
| `steward` | console script | `pyforge.steward.cli:main`, the CLI above. | spec-pyforge-unifying-strategy:CAP-5 |
| `pyforge steward` | pyforge-core front door | The same `steward` script through `pyforge.core.dispatch`. | spec-pyforge-unifying-strategy:CAP-5 |
| `python -m pyforge.steward` | module | `__main__.py`: the same `main()`. `python -m pyforge.steward.cli` is the same again. | spec-pyforge-unifying-strategy:CAP-5 |
| `python -m pyforge.steward.preflight` | module | The pre-push preflight runner: pixi task `pr-preflight` (the `pre-push` hook), and with `--budget` the warn-only budget report, pixi task `preflight-budget` (`preflight_budget.py`). | CAP-159, CAP-175 |
| `python -m pyforge.steward.frames` | module | The Frame four-field preflight (pixi task `frame-preflight`); `--upstream-check` (pixi task `frame-upstream-check`) checks against the pinned upstream validator. | CAP-53, CAP-6 |
| `python -m pyforge.steward.marketplace_pages` | module | Renders the marketplace Pages index; `--flag-env` prints `PYFORGE_MARKETPLACE_PAGES=1` or `0` for `pages.yml`. | CAP-171 |
| `python -m pyforge.steward.preflight_budget` | module | The budget report alone, the same as `--budget` above. | CAP-175 |
| `pyforge.core.hooks` | entry-point group | Six default plugins of `deploy_profiles.py`: `harness`, `splunk`, `storagegrid`, `eplx-gha`, `tachyon`, `jira`. | spec-pyforge-unifying-strategy:CAP-18 |
| `pyforge.steward.deploy_profile` | hook spec name | The hook spec those plugins register on (owner `steward`); a name of the flag-key shape that is not a flag key. | spec-pyforge-unifying-strategy:CAP-18 |

## Python names other packages import

Steward's public contract is its CLI (canopy:AD-7); these imports are the exceptions that exist today, each named so a
second root keeps them or retires them deliberately. The list is every hit of `git grep -nE '(from|import)
pyforge\.steward' -- ':!src/shared/packages/pyforge-steward'` that imports a name (re-run 2026-11-11), plus the one
load by name (`asgi.py`); a private name is flagged where it is used. A bare `import pyforge.steward` smoke
(`.github/workflows/copilot-setup-steps.yml`) and the `python -m pyforge.steward…` entry points above import no name
and are not rows.

| Importer | Names | Capability |
|---|---|---|
| django-atlas `django_atlas_portal/board.py` | `pyforge.steward.dashboard.cache.get_master_dataset`, `pyforge.steward.dashboard.declarations.AccessDeclaration`, `pyforge.steward.dashboard.filtering.filter_by_role`, `pyforge.steward.dashboard.filtering.search` | CAP-110 |
| django-pyforge `django_pyforge/assertion/client.py` | `pyforge.steward.provision.load_pixi_environments`, `pyforge.steward.provision.repo_root` (a function-local import) | CAP-3 |
| the host `src/platform/ingest/github_projects/` (`graphql.py`, `pipeline.py`, `source.py`, `test_github_metrics_dlt.py`) | `pyforge.steward.keys.HostScopedCredential`, `pyforge.steward.sync.TransportFn`, `pyforge.steward.sync.TransportResponse`, `pyforge.steward.sync.github_graphql_request`, and `pyforge.steward.sync._default_transport`: a private name the host still imports under DW-steward-74-1 (the public `pyforge.steward.sync.default_transport` is the same object since Story 123.2) | CAP-66 |
| the host `src/platform/config/asgi.py` | `pyforge.steward.dashboard.asgi.application`, loaded by name with `importlib.import_module` for `/ws/events/` | spec-pyforge-unifying-strategy:CAP-8 |
| `scripts/pages_build_stamp.py`, `scripts/pages_fleet_status.py`, `scripts/pages_artifact_download.py` | from `pyforge.steward.pages`: `PAGES_DUTY_FLAG`, `build_json`, `decide_deploy`, `tree_hash`, `FLEET_STATUS_REL`, `fleet_status_document`, `ARTIFACTS_PER_PAGE`, `EXPORT_BRANCH`, `KEDRO_VIZ_ARTIFACT`, `KEDRO_VIZ_DEST_REL`, `KEDRO_VIZ_ENV_PREFIX`, `KEDRO_VIZ_WORKFLOW`, `export_artifacts_endpoint`, `newest_export_run` | CAP-168 |
| `tests/scripts/test_session_denial_forms.py` | `pyforge.steward.cli.build_parser`, to prove each sanctioned form a session denial names parses | CAP-5 |
| pyforge-herald `tests/meta/test_preflight_pages_lane.py` | from `pyforge.steward.preflight`: `list_preflight_lanes`, `DOCS_SITE_TASKS`, `EXIT_OK`, `LaneRunContext`, `run_preflight`, `SCOPE_FULL`, `SCOPE_TOUCHED`, `touched_cut`; from `pyforge.steward.preflight_ci`: `select_lanes`, `Selection`, `filter_matches`, and `pyforge.steward.preflight_ci._step_matches`, a private name (it proves `pr-preflight` runs `pages-check` when `pages.yml`'s pull-request paths change) | CAP-159 |
| `scripts/guild_image_ci.sh`, `scripts/platform-ci-local.sh` (an inline `python -` heredoc) | `pyforge.steward.preflight_ci.emit_twin_banner`, the paused-surface banner of a manual CI twin (Story 99.5) | CAP-166 |
| `.claude/skills/bmad-sprint-ledger-query/SKILL.md` (its documented engine API) | `pyforge.steward.sprint_ledger_query.SprintLedgerQueryEngine`, `pyforge.steward.sprint_ledger_query.get_runnable_backlog` | CAP-146 |
| `docs/foundry/marketplace/README.md` (its documented render snippet) | `pyforge.steward.marketplace_pages.write_plugin_manifests`, `pyforge.steward.marketplace_pages.write_site_from_index` | CAP-171 |

## What steward needs from the tree

The package's wheel holds `src/pyforge/steward/` (with `data/`); everything below lives in the checkout. Paths are
relative to the repository root, which `repo_root()` finds by walking up to the root sentinel.

| Need | Used by | Capability |
|---|---|---|
| `scripts/bmad-loop-worktree`, the root sentinel: `repo_root()` (bootstrap, budget, provision, sprint_ledger_query, suite, upgrade, workspace) walks up to the directory that holds it; `steward provision --env --runner` runs it | every duty that reads the checkout | CAP-3, CAP-48 |
| The data directories outside the wheel: `src/shared/packages/pyforge-steward/catalog/`, `corridor/` and `measures/` (each from `root_layout.STEWARD_PACKAGE_DIR`) | `steward catalog`, `steward load`, `steward quarantine`, `steward measure` | CAP-117, CAP-139, CAP-44 |
| `scripts/pin_policy_check.py`, `scripts/pin_policy_restore.py`, `scripts/bump_pixi_version.py`, `scripts/llms_full_check.py`, `scripts/pixi_env_matrix.py`, `scripts/docs_environments.py`, `scripts/docs_pixi_tasks.py`, `scripts/bmad_estate_check.py`, `scripts/pixi_version_check.py`, `scripts/target_version_check.py`, `scripts/sbom_gap_derive.py`, `scripts/spec_surface_check.py`, `.claude/scripts/conda-forge-expert/bmad_suite_metapackage.py` (run by subprocess) | `steward estate` (`estate.py`, `estate_realize.py`, `estate_reconcile.py`, `estate_verify.py`) | CAP-167 |
| `scripts/pages_build_stamp.py` | `steward pages build --stamp` | CAP-168 |
| `scripts/coverage_gates_ci.py` | the preflight's reduced-suite lanes (`preflight_suite_reduction.py`) | CAP-175 |
| `.claude/scripts/conda-forge-expert/github_updater.py` (else the skill's own copy) | `steward suite advance` (the autotick step) | CAP-22 |
| The CFE HTTP delegate `.claude/skills/conda-forge-expert/scripts/_http.py`, located and loaded by `keys.py` | `steward keys audit --drift`, the GitHub Enterprise host | CAP-49, CAP-164 |
| A module skill's `scripts/merge-config.py` and `scripts/merge-help-csv.py`, run with `uv run` | `steward provision --module` | CAP-18 |
| Pixi tasks it shells: `pages-check` (`-e site`), `pr-preflight` and `bmad-drift-check` (`-e pyforge-guild`), every lane of `pr-preflight-lanes`, `pre-commit install` and `steward --version` (setup, validate-fast), and the three attended rows of `steward estate verify` (`pyforge-atlas-test` under `CI=1`, `pyforge-herald-browser-check`, `scribe-pg-up` then `pyforge-scribe-test`) | `steward pages build`, `steward preflight verify-deferred`, `steward session check`, `steward upgrade prove-landed`, the preflight, `steward setup`, `steward validate-fast`, `steward estate verify` | CAP-168, CAP-159, CAP-162, CAP-13, CAP-48, CAP-167 |
| Other commands it shells in `pyforge-guild`: `marshal seed check --json`, `scribe capture --type project` (a pause or resume with `--yes`), `python -m pyforge.scribe.cli catalog bmad-estate --write` and `python -m pyforge.doctor.sources` (estate reconcile); plain `pixi install`, `pixi upgrade`, `pixi lock --check` and `pixi project export conda-environment -e build` | `steward session check`, `steward ci pause`, `steward ci resume`, `steward estate reconcile`, `steward provision`, `steward estate refresh` | CAP-162, CAP-166, CAP-167, CAP-3 |
| No other station is imported: a verdict another station owns is read from that station's command by exit code (`session.py`'s former `pyforge.doctor` import left with Story 123.3, so no exception and no deferred-work id remains) | `tests/meta/test_portability.py` holds it | CAP-182 |
| `bmad_loop`, an optional import: `upgrade.py` reads the shipped `bmad_loop_hook.py` from the installed package when it is importable, else from its own catalog | `steward upgrade prove-landed` (the loop-home relay refresh) | CAP-13 |
| The `[dashboard]` extra (Django, Channels, daphne): only `pyforge.steward.dashboard` imports it, and the base package runs its CLI without it | the host and django-atlas | CAP-109, CAP-115 |
| Tracked files it reads: `pixi.toml`, `environment.yaml`, `docs/governance/ci-surfaces.yaml`, `docs/governance/pin-policy.yaml`, `docs/governance/realization-register.yaml`, `docs/governance/preflight-budgets.toml`, `docs/foundry/capability-ledger.yaml`, `docs/foundry/frames/`, `docs/foundry/marketplace/`, `.github/workflows/*.yml`, `_bmad/_config/manifest.yaml`, every station's `planning-artifacts/sprint-status-ledger.yaml` and `epics.md`, `.steward/keys-inventory.yaml`, and this Spec's `install-class-playbook.md` and `install-matrix.md` | the duties that name them | CAP-166, CAP-167, CAP-175, spec-python-foundry-cutover:CAP-9, CAP-123, CAP-169, CAP-159, CAP-10, CAP-146, CAP-1, CAP-27 |
| Local state under `.steward/` (gitignored, all but the tracked `keys-inventory.yaml`): the preflight journals `preflight-runs.jsonl` and `preflight-skips.log`, `estate-refresh/` journals, `ci-vars.json`, `ci-status.json`, the workspace bookkeeping, `deck-integrity-baseline.json`, `keys-exec.log` | the duties that write them | CAP-159, CAP-156, CAP-167, CAP-166, CAP-104, CAP-135, CAP-164 |

## Estate-bound constants

`pyforge.steward.root_layout` (`root_layout.py`, Story 123.2) is the one module that names this checkout's layout and
repository; `tests/meta/test_portability.py` reds a second module that names either. The four identity values name
this checkout, not the root of record, and do not follow a flip of `pyforge.cutover_root` (operator ruling
2026-11-10). The flag tree's relative path is `pyforge.core.cutover_root.LOCAL_DEV_RELATIVE`, not restated here.

| Constant | Value | Used by | Capability |
|---|---|---|---|
| `root_layout.STATION_PACKAGES` | `src/shared/packages` (with `STATION_PACKAGES_DIR`, `STEWARD_PACKAGE_DIR`, `MARSHAL_PACKAGE_DIR` derived from it) | the data directories, `steward upgrade pin-fan-out`, the preflight's station paths | CAP-182 |
| `root_layout.CI_DEFAULT_REPOSITORY` | `rxm7706/local-recipes` | `steward ci`: the repository whose workflows and pause variables it reads (`ci.DEFAULT_REPO`) | CAP-182 |
| `root_layout.BOOTSTRAP_DEFAULT_URL` | `https://github.com/rxm7706/local-recipes.git` | `steward setup --url`'s default: the clone must hold the root sentinel | CAP-182 |
| `root_layout.MARKETPLACE_GIT_URL` | `https://github.com/rxm7706/local-recipes.git` | the public marketplace's clone URL (`catalog.PUBLIC_MARKETPLACE_GIT_URL`), published from `docs/foundry/marketplace` | CAP-182 |
| `root_layout.MARKETPLACE_OWNER` | `rxm7706` | the owner name the rendered `marketplace.json` names | CAP-182 |
