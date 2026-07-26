---
doc_type: architecture
part_id: mcp-server
display_name: FastMCP server
project_type_id: backend
date: 2026-07-25
source_pin: 'conda-forge-expert v8.79.1'
---

# Architecture: MCP Server (Part 3)

> **Re-verified 2026-07-25** (source_pin → **v8.79.1**; reconciler pass per SYNC-RUNBOOK). **The server did not change** since the last pass — no tool added or removed, same framework, same subprocess pattern. This pass is correction only.
>
> **Corrected — the headline:** the **surface split was wrong in every prior version of this doc**, and wrong in two mutually inconsistent ways at once (the body said "18 recipe-authoring / 22 atlas / 2 infra" summing to 42, while the At-a-Glance table and prose elsewhere said 46). Re-derived tool-by-tool from the live decorators: **21 recipe-authoring · 21 atlas-intelligence · 2 project-scanning · 2 infrastructure = 46**. Every "42" in this document has been retired.
>
> **Also corrected:** server LOC 2,084 → **2,266** (91,126 bytes); `gemini_server.py` 178 → **340 lines** and **5 tools**, not 2; and — most consequentially — the **registration story was wrong**, see § *Server Registration with Claude Code*.
>
> **Re-verified unchanged:** 46 `@mcp.tool` registrations and zero `@mcp.resource` / `@mcp.prompt`; `mcp = FastMCP("conda-forge-expert")` at `:19`; exactly 2 `async def` tools (`update_cve_database` `:820`, `trigger_build` `:867`), both taking `ctx: Context`; `_run_script(script_path, args, input_text=None, timeout=120)` at `:83`; stdio transport via a bare `mcp.run()` at `:2266`; `_PYTHON = sys.executable`; `mcp_call.py` at 42 lines; the three-layer error discipline; zero auth code in the server.
>
> **New in the neighbourhood:** a **second, separate MCP server** now exists in-repo (`src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/server.py`, 11 tools) belonging to the Kedro reimplementation. It is additive and unrelated to this one — see § *The second MCP server*.


The MCP server is the **wire format** between Claude Code's MCP runtime and Parts 1+2's canonical Python scripts. It exposes **46** tools across four surfaces (recipe-authoring, atlas-intelligence, project-scanning, infrastructure), each implemented as a thin subprocess wrapper over a Tier 1 script. The server is **not** where the logic lives — it's where the logic is **named** for the MCP protocol.

**Surface deltas since v8.11.1:** the atlas-intelligence surface added `pypi_intelligence` (v8.1.0; the rich filter chain `--score-min`, `--activity`, `--license-ok`, `--noarch-python-candidate`, `--min-downloads`, per-channel `--in-*`, `--sort-by score|downloads|serial|name`), the Phase F+ Wave-3 reads `platform_breakdown` / `pyver_breakdown` / `channel_split` (v8.19.0), and the cyclonedx-universe-inventory quartet `export_purls` / `universe_sbom` / `inventory_match` / `recommend_2027`; the recipe-authoring surface added `download_pr_artifacts` (v8.14.0 PR-artifact downloader). Total: **46**.

**Deliberately *not* exposed:** the four seed-gap suggesters (`lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap`) plus `library-futures`, `add-handoff`, and `mapping-gap` are CLI/pixi-only by design. The old claim that "every CLI has an MCP-tool counterpart" is false and has been removed here and in Part 2.

Without Part 3, every BMAD agent would have to invoke pixi tasks directly (slow, bash-shaped, lossy round-tripping through stdout JSON). With Part 3, BMAD agents and Claude Code call `mcp__conda_forge_server__<tool>` natively with structured arguments and typed responses.

---

## Mission

> **Expose Parts 1 + 2 as MCP tools so Claude Code and BMAD agents can invoke them with structured args + JSON responses without shell round-tripping.**

Operationalized:
- 46 tools registered via `@mcp.tool()` decorators on a single `FastMCP("conda-forge-expert")` instance. **Zero `@mcp.resource` and zero `@mcp.prompt`** — the server is a pure tool surface.
- Each tool's body is a thin `_run_script(SCRIPT_PATH, args, ...)` invocation that subprocess-executes a Tier 1 script and parses JSON stdout.
- Started by Claude Code over **stdio**, from a **global** registration in `~/.claude.json` (`mcpServers.conda_forge_server`) — *not* by path-convention auto-discovery, and *not* from anything in this repo. See § *Server Registration with Claude Code*.

---

## At a Glance

| Field | Value |
|---|---|
| Primary file | `.claude/tools/conda_forge_server.py` |
| Auxiliary servers | `gemini_server.py` (Gemini API bridge, 340 lines, 5 tools), `mcp_call.py` (JSON-RPC shell client, 42 lines) |
| Second server, unrelated | `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/server.py` (11 tools) — the Kedro reimplementation's own server; **do not conflate** |
| Framework | FastMCP (`from fastmcp import FastMCP, Context`) |
| MCP instance name | `conda-forge-expert` (module level, `conda_forge_server.py:19`) |
| Total `@mcp.tool` registrations | **46** (verified via `grep -c "@mcp.tool"`, 2026-07-25) |
| `@mcp.resource` / `@mcp.prompt` | **0 / 0** — tools only |
| Sync tools | 44 |
| Async tools | 2 — `update_cve_database` (`:820`), `trigger_build` (`:867`); both take `ctx: Context` and emit progress |
| Lines of code | **2,266** / 91,126 bytes (`conda_forge_server.py`) + 340 (`gemini_server.py`) + 42 (`mcp_call.py`) |
| Transport | **stdio** — bare `mcp.run()` at `:2266`, i.e. FastMCP's default |
| Start mechanism | **Global registration in `~/.claude.json`** under `mcpServers.conda_forge_server`; `type: "stdio"`, `command` pinned to `<repo>/.pixi/envs/local-recipes/bin/python3`, server path as its single arg. Nothing in the repo registers it |
| Tool namespace (from caller's side) | `mcp__conda_forge_server__<tool_name>` |
| Pixi env for execution | `local-recipes` — pinned by the registration's absolute `command` path, *not* inherited from Claude Code's launch env |
| Subprocess interpreter | `_PYTHON = sys.executable` (so Tier 1 scripts run in the same env the server runs in) |
| Default subprocess timeout | 120 s; raised per-tool to 600 s (`update_cve_database`, `download_pr_artifacts`, and the four purl/BOM/2027 tools), 300 s (`submit_pr`, `prepare_submission_branch`), 180 s (`env_inspect`), 60 s (`my_feedstocks`) |
| Auth code in the server | **None.** All auth/enterprise routing lives in Part 1's `scripts/_http.py`, imported by each subprocess |

---

## Architecture Pattern: Thin Wrapper Over Tier 1

```
┌──────────────────────────────────────────────────────────────────────┐
│  Claude Code / BMAD agent                                            │
│  calls: mcp__conda_forge_server__validate_recipe(recipe_path="...")  │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ MCP JSON-RPC over stdio
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  .claude/tools/conda_forge_server.py                                 │
│  (FastMCP server process, started by Claude Code at session boot)    │
│                                                                       │
│    @mcp.tool()                                                       │
│    def validate_recipe(recipe_path: str) -> str:                     │
│        args = ["--json", recipe_path]                                │
│        result = _run_script(VALIDATE_SCRIPT, args)                   │
│        return json.dumps(result, indent=2)                           │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ subprocess.run([_PYTHON, SCRIPT_PATH, *args])
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  .claude/skills/conda-forge-expert/scripts/validate_recipe.py        │
│  (Tier 1 canonical implementation; reads --json flag, emits JSON)   │
│                                                                       │
│    Imports: yaml, jsonschema, _http, rattler-build CLI...            │
│    Returns: structured validation result on stdout                   │
└──────────────────────────────────────────────────────────────────────┘
```

**Why subprocess and not direct import?**
1. **Isolation**: a misbehaving Tier 1 script can't crash the MCP server process — it dies in its own subprocess.
2. **Timeout enforcement**: `_run_script` has a `timeout` parameter (default 120s) with `subprocess.TimeoutExpired` handling.
3. **Pixi-env consistency**: `_PYTHON = sys.executable` (the env Claude Code launched in) is passed to subprocess explicitly, guaranteeing the right conda env.
4. **JSON-out contract**: each Tier 1 script accepts `--json` and emits structured stdout; the server parses with `json.loads(result.stdout)` and falls back to error+stdout+stderr+exit_code on JSONDecodeError.

**Cost of subprocess pattern**: per-call overhead of ~100ms (Python interpreter startup + import time). For interactive tools this is invisible. For tight-loop tools like `query_atlas`, the overhead is meaningful but acceptable; if it becomes a bottleneck, direct-import refactor is the escape hatch.

---

## The 46 Tools by Surface

> **This section was materially wrong and has been rebuilt from the live decorators (2026-07-25).** Two incompatible splits had accumulated in this document — a body claiming "18 recipe-authoring / 22 atlas / 2 infra = 42" and headline prose claiming 46 — and the reconciliation was fudged with a footnote about double-counting `get_build_summary`. Neither split matched the file. The correct partition is **21 / 21 / 2 / 2 = 46**, with every tool in exactly one bucket and no double-counting:

| Surface | Count | Tools |
|---|---|---|
| **Recipe-authoring** | **21** | `validate_recipe`, `check_dependencies`, `generate_recipe_from_pypi`, `edit_recipe`, `optimize_recipe`, `update_recipe`, `update_recipe_from_github`, `check_github_version`, `migrate_to_v1`, `scan_for_vulnerabilities`, `update_cve_database`, `analyze_build_failure`, `trigger_build`, `get_build_summary`, `prepare_submission_branch`, `submit_pr`, `download_pr_artifacts`, `lookup_feedstock`, `enrich_from_feedstock`, `get_feedstock_context`, `get_conda_name` |
| **Atlas-intelligence** | **21** | `staleness_report`, `platform_breakdown`, `pyver_breakdown`, `channel_split`, `feedstock_health`, `whodepends`, `behind_upstream`, `cve_watcher`, `version_downloads`, `release_cadence`, `find_alternative`, `adoption_stage`, `pypi_only_candidates`, `pypi_intelligence`, `package_health`, `query_atlas`, `my_feedstocks`, `export_purls`, `universe_sbom`, `inventory_match`, `recommend_2027` |
| **Project-scanning** | **2** | `scan_project`, `env_inspect` |
| **Infrastructure** | **2** | `run_system_health_check`, `update_mapping_cache` |

**Boundary note, flagged not forced:** a spec archive under the `pyforge-atlas` project asserts "23 of 46 atlas-relevant". The 2-tool delta is exactly `scan_project` + `env_inspect`, which are classed here as project-scanning but *do* read `cf_atlas.db`. Both numbers are defensible under different definitions of "atlas-relevant" — 21 by primary purpose, 23 by data dependency. Neither is wrong; state which definition you mean.

### Recipe-authoring surface (21 tools)

The autonomous loop (Part 1) calls these tools in order. All are sync except `trigger_build` and `update_cve_database` (async).

| Tool | Tier 1 script | Used by step |
|---|---|---|
| `validate_recipe(recipe_path)` | `validate_recipe.py` | Step 2 |
| `check_dependencies(recipe_path, suggest=True, channel=None, subdirs=None)` | `dependency-checker.py` | Step 3 helper |
| `generate_recipe_from_pypi(package_name, version=None)` | `recipe-generator.py` | Step 1 |
| `scan_for_vulnerabilities(recipe_path)` | `vulnerability_scanner.py` | Step 4 |
| `trigger_build(...) [async]` | `local_builder.py` | Steps 7a (native, mandatory) / 7b (Docker, opt-in) |
| `get_build_summary()` | (reads `build_summary.json` at repo root — no subprocess) | Step 8 |
| `update_cve_database(force, ctx) [async]` | `cve_manager.py` | (feeds step 4; 600 s timeout) |
| `get_conda_name(pypi_name)` | `name_resolver.py` | Step 3 helper (PyPI→conda resolution) |
| `lookup_feedstock(pkg_name, no_cache=False)` | `feedstock_lookup.py` | Step 3 helper |
| `enrich_from_feedstock(recipe_path, dry_run=False)` | `feedstock_enrich.py` | Step 3 helper |
| `get_feedstock_context(pkg_name, max_open=50, max_closed=10, no_cache=False)` | `feedstock_context.py` | Step 3 helper |
| `edit_recipe(recipe_path, actions: List[Dict])` | `recipe_editor.py` | Step 3 |
| `analyze_build_failure(error_log, first_only=False)` | `failure_analyzer.py` | Step 8 |
| `optimize_recipe(recipe_path)` | `recipe_optimizer.py` | Step 5 |
| `update_recipe(recipe_path, dry_run=False)` | `recipe_updater.py` | (autotick / version bumps) |
| `prepare_submission_branch(...)` | `submit_pr.py --prepare-only` | Step 8b |
| `submit_pr(...)` | `submit_pr.py` | Step 9-10 |
| `update_recipe_from_github(...)` | `github_updater.py` | (GitHub-only sources) |
| `check_github_version(recipe_path=None, github_repo=None)` | `github_version_checker.py` | (autotick check) |
| `migrate_to_v1(recipe_path)` | `feedstock-migrator.py` | (v0→v1 migration) |
| `download_pr_artifacts(...)` | `pr_artifacts.py` | (v8.14.0; fetch PR build artifacts into a local channel) |

### Atlas-intelligence surface (21 tools)

All read against `cf_atlas.db` (Part 2). **All 21 are sync** — the two async tools both live on the recipe-authoring surface. *(The rows for `scan_project` / `env_inspect` are retained below for continuity but belong to the project-scanning surface; `update_cve_database`, `update_mapping_cache` and `get_conda_name` likewise appear below but are counted under recipe-authoring / infrastructure. The four purl-and-BOM tools added by the cyclonedx effort — `export_purls`, `universe_sbom`, `inventory_match`, `recommend_2027`, all with 600 s timeouts — are part of this 21.)*

| Tool | Tier 1 script | Reads from |
|---|---|---|
| `staleness_report(...)` | `staleness_report.py` | packages + Phase H + Phase F + Phase N |
| `feedstock_health(...)` | `feedstock_health.py` | packages + Phase M + Phase N |
| `whodepends(...)` | `whodepends.py` | dependencies (Phase J) |
| `behind_upstream(...)` | `behind_upstream.py` | upstream_versions + packages.latest_conda_version |
| `version_downloads(...)` | `version_downloads.py` | package_version_downloads (Phase F) |
| `release_cadence(...)` | `release_cadence.py` | upstream_versions_history (Phase L) |
| `find_alternative(name, limit=10)` | `find_alternative.py` | packages similarity |
| `adoption_stage(...)` | `adoption_stage.py` | packages (Phase B + Phase F) |
| `pypi_only_candidates(limit=100, min_serial=0)` | `pypi_only_candidates.py` | pypi_universe LEFT JOIN packages (Phase D, v7.9.0+) |
| `pypi_intelligence(...)` | `pypi_intelligence.py` | pypi_intelligence side table (v8.1.0; score / activity / cross-channel BOOLs / packaging shape) |
| `platform_breakdown(...)` | `platform_breakdown.py` | package_platform_downloads (Phase F+, v8.19.0; ARM/win/EOL share) |
| `pyver_breakdown(...)` | `pyver_breakdown.py` | package_pyver_downloads (Phase F+, v8.19.0; `--policy-check` python_min bump-safe flags) |
| `channel_split(...)` | `channel_split.py` | package_channel_downloads (Phase F+, v8.19.0; defaults-channel migration opportunities) |
| `cve_watcher(...)` | `cve_watcher.py` | package_version_vulns (Phase G') + vdb/ |
| `package_health(name)` | composite of Part 1 scripts | packages + feedstock_health join |
| `query_atlas(...)` | `detail_cf_atlas.py` / direct DB | packages (generic) |
| `my_feedstocks(maintainer, triage=False, limit=25, include_archived=False)` | `my_feedstocks.py` (v8.5.0; was direct SQL → `feedstock_lookup.py`) | `package_maintainers` join + composite urgency score (Phase G CVE / Phase N CI-red / Phase M stuck-bot / Phase H upstream lag / open PRs+issues). `triage=True` ranks by score and emits severity-banded punch list |
| `env_inspect(mode, environment, prefix, scope, sbom_format, diff_to, no_live, include, exclude)` | `env_inspect.py` (v8.5.0; renamed from `env_roots.py` at v8.5.1) | 8-mode dispatcher: `default` (roots) / `audit` / `freshness` / `security` / `bus_factor` / `licenses` / `sbom` / `diff`. All modes share `--scope {roots,explicits,all}`. Atlas-stale warning + live PyPI fetch (default-on, 6h disk cache) |
| `scan_project(...)` | `scan_project.py` | packages + inventory_cache/ + ~28 input formats |
| `update_cve_database(force=False, ctx=Context) [async]` | `cve_manager.py` | cve/ feed cache |
| `update_mapping_cache(force=False)` | `mapping_manager.py` | pypi_conda_map.json |
| `get_conda_name(pypi_name)` | `name_resolver.py` | pypi_conda_mappings/* |

### Infrastructure / system surface (2 tools)

| Tool | Tier 1 script | Purpose |
|---|---|---|
| `run_system_health_check()` | `health_check.py` | Validate pixi env, MCP server availability, atlas freshness |
| `update_mapping_cache(force=False)` | `mapping_manager.py` | Refresh the PyPI→conda mapping cache (`pypi_conda_map.json`) |

*(`get_build_summary()` was previously listed here as well as under recipe-authoring — the duplication is what produced the bogus "42" total. It is counted once, under recipe-authoring, where the loop uses it.)*

---

## Tool Implementation Pattern

Every tool follows the same skeleton (~90% of the 46 tools are 5-10 lines of body code; the `env_inspect` dispatcher is ~30 lines because of the 8-mode flag mapping):

```python
@mcp.tool()
def validate_recipe(recipe_path: str) -> str:
    """Validate a conda-forge recipe (recipe.yaml or meta.yaml) against best practices."""
    args = ["--json", recipe_path]
    result = _run_script(VALIDATE_SCRIPT, args)
    return json.dumps(result, indent=2)
```

The `_run_script(script_path, args, input_text=None, timeout=120)` helper:
1. Checks `script_path.exists()`; returns `{"error": "Script not found"}` if missing.
2. Builds `cmd = [_PYTHON, str(script_path)] + args`.
3. `subprocess.run(cmd, capture_output=True, text=True, check=False, input=input_text, timeout=timeout)`.
4. Parses `result.stdout` as JSON.
5. On JSONDecodeError: returns `{"error": "Failed to parse JSON output", "stdout": ..., "stderr": ..., "exit_code": ...}`.
6. On TimeoutExpired: returns `{"error": "Script timed out after {timeout}s", "script": str(script_path)}`.

**Key invariants every Tier 1 script must honor for MCP compatibility**:
- Accept `--json` flag and emit structured JSON on stdout.
- Exit code is informational; the JSON is authoritative.
- Stderr is captured for failure diagnosis; stdout is the contract.

---

## Async Tools (2)

Two tools wrap subprocess calls that can run for minutes. They're declared `async def` so the MCP server doesn't block other calls.

### `trigger_build`

```python
@mcp.tool()
async def trigger_build(recipe_path: str, config: str = "linux-64", ...) -> str:
    # Spawns build in background; tracks _active_build (module-level Popen ref)
    # Writes PID to build.pid (repo root)
    # Returns immediately with {"status": "started", "pid": ...}
    # Caller polls get_build_summary() to learn outcome
```

Pattern: **fire-and-forget**. The server tracks `_active_build: Optional[subprocess.Popen]` at module level. When the build finishes, the wrapped script writes `build_summary.json` to repo root, which `get_build_summary()` reads.

### `update_cve_database`

```python
@mcp.tool()
async def update_cve_database(force: bool = False, ctx: Context | None = None) -> str:
    # AppThreat vdb refresh is 5-10 min; ctx is the MCP progress-reporting handle
```

Uses MCP's `Context` parameter for streaming progress updates back to the caller.

---

## Out-of-Band State

Two files at **repo root** (not inside `.claude/`) bridge async tool state:

| File | Written by | Read by | Purpose |
|---|---|---|---|
| `build_summary.json` | wrapped `rattler-build` invocation (via `trigger_build`) | `get_build_summary()` | Build outcome (status, artifacts, log path) |
| `build.pid` | `trigger_build` startup | `_active_build` cleanup logic | Process ID of running build (for kill / status checks) |

These are gitignored. The server tolerates their absence (returns `{"status": "no_build_pending"}` etc.).

---

## Auxiliary Servers

### `gemini_server.py` (340 lines, 5 tools)

A FastMCP server exposing Google Gemini as MCP tools. Used as a fallback / alternative model backend when Claude Code's primary inference is unavailable or rate-limited. Requires `GEMINI_API_KEY` env var. Registered globally as `gemini` in `~/.claude.json`, alongside `conda_forge_server`.

*(Corrected 2026-07-25: this was recorded as 178 lines with **two** tools — `gemini_chat` and `gemini_list_models`. The file carries **5** `@mcp.tool` registrations; only those two are currently surfaced to this session, so the other three are present in source but not enumerated here.)*

Posts directly to `https://generativelanguage.googleapis.com/v1beta` via `urllib.request` (no fastmcp-internal HTTP).

Not part of the conda-forge surface — listed here because it's in the same `.claude/tools/` directory and follows the same FastMCP pattern.

### `mcp_call.py` (42 lines)

A **shell-side fallback client** that speaks MCP JSON-RPC directly to `conda_forge_server.py`. Used when you want to invoke an MCP tool from a script or terminal without going through Claude Code:

```bash
python .claude/tools/mcp_call.py validate_recipe '{"recipe_path": "recipes/numpy/recipe.yaml"}'
```

The client:
1. Sends `initialize` then `tools/call` JSON-RPC messages on stdin.
2. Parses stdout line-by-line looking for the response with `id == 2`.
3. Returns the parsed result or `{"error": "no response", "stderr": ...}`.

300-second timeout. Used primarily by `bootstrap-data` and by humans debugging the MCP layer.

### The second MCP server (`pyforge/atlas/mcp/server.py`, 11 tools)

**Additive and separate — do not conflate it with `conda_forge_server.py`.** The Kedro/Dagster reimplementation of the atlas (`src/shared/packages/pyforge-atlas/`, Part 2 § *The Kedro reimplementation*) ships its **own** FastMCP server at `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/server.py` with **11** `@mcp.tool()` registrations, reading Parquet via Ibis→DuckDB rather than shelling out to Tier 1 scripts. Two independent servers now exist in this repo; only `conda_forge_server.py` is registered in `~/.claude.json` and only it backs the `mcp__conda_forge_server__*` namespace. Nothing about this document's 46-tool surface changes because of it.

---

## Server Registration with Claude Code

> **Corrected 2026-07-25 — this section previously described a mechanism that is not what happens.** The claim was "Claude Code auto-discovers `.claude/tools/*.py` MCP servers by **path convention**." It does not. The server is started from an **explicit global registration**.

**Actual state** (verified 2026-07-25):

- The server is registered **globally**, in the user's `~/.claude.json`, under `mcpServers.conda_forge_server`:

  ```json
  { "type": "stdio",
    "command": "<repo>/.pixi/envs/local-recipes/bin/python3",
    "args": ["<repo>/.claude/tools/conda_forge_server.py"],
    "env": {} }
  ```

- There is **no `.mcp.json`** at the repo root, and `.claude/settings.json` has **no `mcpServers` block**. Nothing in this repository registers the server.
- The registration sits in the **top-level** `mcpServers` map, not under `projects[<repo path>].mcpServers` — that project entry's map is empty.
- The `command` is an **absolute path into `.pixi/envs/local-recipes/`**. This, not Claude Code's launch environment, is what pins the execution env — a detail worth knowing, because `_PYTHON = sys.executable` then propagates that same interpreter to every Tier 1 subprocess.
- Sibling servers `gemini` and `claude-design` are registered the same way, globally.

**Consequences that follow from this being global rather than in-repo:**

1. **The repo is not self-sufficient.** A fresh clone plus a fresh Claude Code install has **no** conda-forge MCP tools until someone edits `~/.claude.json` by hand. Nothing in the repo, and no documentation in it, currently states this.
2. **The absolute paths are machine-specific.** The registration hard-codes this checkout's location; it does not survive a move or a second clone.
3. **The pixi env must already be materialized.** The `command` path only exists after `pixi install -e local-recipes`; a bare clone yields a registration pointing at a non-existent interpreter.

**Deferred work** (per `docs/specs/claude-team-memory.md` Q13, still open): adopt a repo-root `.mcp.json` registering `conda_forge_server.py` + `gemini_server.py`, and `.claude/agents/*.md` entries declaring which agent uses which tools (currently implicit via CLAUDE.md prose). This would make the server portable and auditable from one in-repo file, and would fix consequence (1) above.

**Implication for rebuild**: a rebuilt repo **needs** `.mcp.json` if the target includes "works on first Claude Code launch in a new install." Do not rely on path-convention auto-discovery — this checkout is not evidence that it works, because it is not what is happening here.

---

## How a BMAD Agent Calls the MCP Server

```
BMAD agent (e.g. bmad-quick-dev) decides to validate a recipe.
   │
   ▼
Agent emits tool_use block: 
   { tool: "mcp__conda_forge_server__validate_recipe",
     args: { recipe_path: "recipes/numpy/recipe.yaml" } }
   │
   ▼
Claude Code's MCP runtime routes to the conda_forge_server.py instance.
   │
   ▼
Server's @mcp.tool() decorator dispatches to validate_recipe(recipe_path).
   │
   ▼
validate_recipe() subprocess-execs .claude/skills/conda-forge-expert/scripts/validate_recipe.py
                  with [_PYTHON, "--json", "recipes/numpy/recipe.yaml"]
   │
   ▼
The script imports yaml, jsonschema, etc.; reads recipe.yaml; runs validation;
emits JSON on stdout: { "valid": true, "warnings": [], "errors": [] }
   │
   ▼
_run_script() parses the JSON; returns the dict to the @mcp.tool wrapper.
   │
   ▼
The tool function returns json.dumps(result, indent=2) to the MCP runtime.
   │
   ▼
Claude Code surfaces the result as the tool_use's tool_result.
   │
   ▼
BMAD agent reads the result, decides next action (continue / fix / abort).
```

---

## Performance & Concurrency

**Per-call overhead** (subprocess pattern):
- Python interpreter startup: ~80-100ms
- Import time for Tier 1 script: ~50-200ms (depends on script's deps)
- Script work time: variable (validate_recipe: ~500ms; behind_upstream: ~50ms; trigger_build: minutes)
- Total: ~200-400ms baseline + script work

**Concurrency**: FastMCP processes tool calls sequentially within one server instance. Async tools (`trigger_build`, `update_cve_database`) yield to the event loop so other tools can interleave, but the underlying `subprocess.run` is still blocking until completion.

**Sequential-tool bottleneck**: a BMAD agent that fires `query_atlas` 50 times in a tight loop will see ~10s wall-clock latency just for subprocess overhead. **Mitigation**: pass batch queries via a single `--json` payload where the Tier 1 script accepts batched input. Several scripts (`scan_project`, `behind_upstream`, `feedstock_health`) already support this.

**Atlas tools are not bottlenecked by the DB**: SQLite WAL mode handles concurrent reads cheaply. The bottleneck is subprocess fork + import, not DB I/O.

---

## Tool Discovery & Schema Surfacing

When Claude Code loads the MCP server:
1. Server starts over stdio from the `~/.claude.json` registration: `<repo>/.pixi/envs/local-recipes/bin/python3 .claude/tools/conda_forge_server.py`.
2. `mcp = FastMCP("conda-forge-expert")` registers the server.
3. All `@mcp.tool()` decorators register their wrapped function's name, docstring, and type-hints into the tool schema.
4. Claude Code sends `tools/list` MCP request; server responds with all 46 tool schemas.
5. **Tool schemas surface at call time**: Claude Code includes them in the model's context only when the model is about to call a tool, not on every turn. Reduces token cost.

This is why CLAUDE.md says "tool schemas surface at call time" — Claude Code's MCP runtime lazy-fetches them.

---

## Error Handling Discipline

Three error layers, top to bottom:

1. **Tool layer** (`validate_recipe` etc.): never raises Python exceptions out to the MCP runtime. Returns `{"error": "..."}` JSON instead.
2. **`_run_script` layer**: catches `FileNotFoundError`, `JSONDecodeError`, `TimeoutExpired`, and generic `Exception`. Returns structured error dict.
3. **Tier 1 script layer**: should emit `{"error": "..."}` JSON on its own failure modes; never expect callers to parse Python tracebacks from stderr.

This three-layer discipline means a misbehaving Tier 1 script that crashes mid-execution will still produce a structured error response to the MCP caller, not a crashed server.

---

## Security & Permission Model

Claude Code's permission gates apply to MCP tool invocations:
- `.claude/settings.json` declares the global allow/deny lists. *(It contains **no `mcpServers` block** — the server is not registered from the repo; see § Server Registration.)*
- `.claude/settings.local.json` declares user-approved namespaced tools (e.g., `mcp__conda_forge_server__submit_pr`).
- **The MCP server contains zero auth code** — anything that can read its stdio can invoke any tool.

**Where auth actually lives**: entirely in Part 1's `scripts/_http.py` (**1,024 LOC**), which every subprocess-launched Tier 1 script imports. The server never sees a credential; it just inherits an environment and passes it down. The chain, in order:

1. **SSL/TLS**: `REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE` → `truststore.inject_into_ssl()` (idempotent via `inject_ssl_truststore()`) → `certifi` fallback.
2. **Auth**: `JFROG_API_KEY` → `X-JFrog-Art-Api` header · then `JFROG_USERNAME` + `JFROG_PASSWORD` → Basic · then `~/.netrc` / `$NETRC` → Basic · then `GITHUB_TOKEN` / `GH_TOKEN` → Bearer (**github.com only**) · then unauthenticated.
3. **Routing**: 21 `<HOST>_BASE_URL` env vars redirect every external host to an internal mirror (`BIOCONDA_`, `CODEBERG_API_`, `CONDA_FORGE_`, `CPAN_`, `CRAN_`, `CRATES_`, `ENDOFLIFE_`, `GITHUB_API_`, `GITHUB_`, `GITHUB_RAW_`, `GITLAB_API_`, `LUAROCKS_`, `MAVEN_`, `NPM_`, `NUGET_`, `PYPI_`, `PYPI_JSON_`, `PYTORCH_`, `ROBOSTACK_STAGING_`, `RUBYGEMS_`, `S3_PARQUET_`).

**Trust boundary**: the MCP server runs **inside** the user's Claude Code session, with the user's filesystem and network credentials. There is no sandbox. Tier 1 scripts that mutate the filesystem (`edit_recipe`, `migrate_to_v1`, `submit_pr`) are gated by Claude Code's permission UI before invocation.

**JFROG_API_KEY cross-host leak — STILL UNRESOLVED (re-confirmed 2026-07-25).** When `JFROG_API_KEY` is set, `_http.py` attaches the `X-JFrog-Art-Api` header **unconditionally, to every outbound request regardless of destination host** — so a GitHub or PyPI fetch carries the Artifactory credential. The MCP server inherits whatever environment its registered `command` is launched with, so every Tier 1 subprocess it spawns inherits the leak too (per `docs/enterprise-deployment.md` § 2). Mitigation remains procedural only: launch with `JFROG_API_KEY` unset, or use the subshell pattern in `deployment-guide.md`.

> **A fix already exists, in the other implementation.** The Kedro reimplementation's `conf/base/catalog.yml` header states the global credential injection is **"FIXED, not ported"**: no global injection exists there, a JFrog key may attach **only** to a dataset whose endpoint-base resolves to an Artifactory host, and no shipped catalog entry carries the key at all. That per-destination credential model is the shape the legacy `_http.py` chain needs; it is the single most valuable thing to port back.

---

## Deferred Work (per claude-team-memory spec)

Captured from `docs/specs/claude-team-memory.md` Q13 and surfaced here so the rebuild includes them:

1. **Add `.mcp.json`** to the repo root, registering `conda_forge_server.py` and `gemini_server.py` explicitly. Makes discovery portable — and, per § Server Registration, is the only way a fresh clone gets these tools at all today.
2. **Add `.claude/agents/*.md`** entries that declare which agent should use which MCP tools (currently implicit via CLAUDE.md prose).
3. **Inventory the MCP-only tools** (no public CLI): `update_cve_database`, `update_mapping_cache`, `lookup_feedstock`, `get_feedstock_context`, `enrich_from_feedstock`, `check_dependencies`, `check_github_version`, `get_conda_name`. Consider promoting some to Tier 2 wrappers for shell-accessibility.
4. **The mirror gap**: 7 atlas read CLIs have **no** MCP tool (`mapping-gap`, `add-handoff`, `library-futures`, and the four seed-gap suggesters). This is a deliberate design choice, not an oversight — they are propose-only, git-review-gated tools whose output a human disposes of. Recorded here so a future "make it 1:1" impulse is a decision rather than an accident.
5. **Add a coverage meta-test**: assert every Tier 1 script with a `main()` is either wrapped by an MCP tool or on an explicit CLI-only allowlist. Would have caught both the surface-split drift and the missing-`.mcp.json` gap.

---

## Integration Points (recap)

See `integration-architecture.md` for full cross-part contracts. Summary:

- **← Part 1 (skill)**: every MCP tool wraps a Tier 1 canonical script. Part 1's `scripts/` is the implementation; Part 3 is the wire format.
- **← Part 2 (cf_atlas)**: **21 of the 46** tools are atlas-intelligence reads against `cf_atlas.db`, plus **2** project-scanning tools (`scan_project`, `env_inspect`) that also read it — so 21 or 23 depending on the definition used (see the boundary note in § The 46 Tools by Surface). All go via Tier 1 scripts; v8.5.0's `env_inspect` adds atlas joins for the freshness/security/bus-factor/licenses modes; v8.19.0's `platform_breakdown` / `pyver_breakdown` / `channel_split` read the Phase F+ breakdown tables). Part 3 doesn't talk to the DB itself — it shells out.
- **→ Part 4 (BMAD)**: every BMAD agent doing conda-forge work invokes tools via `mcp__conda_forge_server__*` per CLAUDE.md integration rules.
- **→ Enterprise layer**: each tool's subprocess inherits the env (including `JFROG_API_KEY`); the leak mitigation lives at the launch-shell layer.

---

## Rebuild checklist for Part 3

1. **Prerequisites**: Part 1 must exist (Tier 1 scripts to wrap).
2. **Add fastmcp to pixi**: `fastmcp = "*"` under `[feature.local-recipes.pypi-dependencies]` or equivalent.
3. **Author `.claude/tools/conda_forge_server.py`**:
   - Module-level `mcp = FastMCP("conda-forge-expert")` instance.
   - SCRIPT_DIR constants pointing at Part 1's `scripts/`.
   - `_PYTHON = sys.executable` for subprocess.
   - `_run_script(script_path, args, input_text=None, timeout=120)` helper.
   - 46 `@mcp.tool()` decorated functions (21 recipe-authoring / 21 atlas / 2 project-scanning / 2 infra). NOT one per Part 1 + Part 2 capability — 7 atlas read CLIs are deliberately CLI/pixi-only.
   - Zero `@mcp.resource` / `@mcp.prompt`; stdio transport via a bare `mcp.run()`.
4. **Out-of-band state files**: ensure `build_summary.json` + `build.pid` paths are agreed with Part 1's `local_builder.py`.
5. **Auxiliary servers** (optional): `gemini_server.py` for Gemini bridge; `mcp_call.py` for shell-side JSON-RPC.
6. **Register with Claude Code**: write a repo-root `.mcp.json` — **required**, not optional. The live repo instead relies on a hand-written global entry in `~/.claude.json` with machine-absolute paths, which does not survive a clone (see § Server Registration).
7. **Settings approvals**: as users run tools, `.claude/settings.local.json` accumulates approved namespaces. No bulk-approve mechanism currently.
8. **Tests**: integration tests in `.claude/skills/conda-forge-expert/tests/integration/` that exercise MCP-shape invocations via `mcp_call.py`. (Currently sparse; a meta-test that asserts every Tier 1 script with a `main()` is wrapped by some MCP tool would catch drift.)

Rebuild order: Part 3 must exist after Parts 1 and 2 (which it wraps), but before Part 4 routinely consumes it (BMAD agents depend on MCP-tool availability for conda-forge work).
