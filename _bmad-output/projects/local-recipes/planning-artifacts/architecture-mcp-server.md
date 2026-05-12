---
doc_type: architecture
part_id: mcp-server
display_name: FastMCP server
project_type_id: backend
date: 2026-05-12
source_pin: 'conda-forge-expert v7.7'
---

# Architecture: MCP Server (Part 3)

The MCP server is the **wire format** between Claude Code's MCP runtime and Parts 1+2's canonical Python scripts. It exposes 35 tools across three surfaces (recipe-authoring, atlas-intelligence, project-scanning), each implemented as a thin subprocess wrapper over a Tier 1 script. The server is **not** where the logic lives — it's where the logic is **named** for the MCP protocol.

Without Part 3, every BMAD agent would have to invoke pixi tasks directly (slow, bash-shaped, lossy round-tripping through stdout JSON). With Part 3, BMAD agents and Claude Code call `mcp__conda_forge_server__<tool>` natively with structured arguments and typed responses.

---

## Mission

> **Expose Parts 1 + 2 as MCP tools so Claude Code and BMAD agents can invoke them with structured args + JSON responses without shell round-tripping.**

Operationalized:
- 35 tools registered via `@mcp.tool()` decorators on a single `FastMCP("conda-forge-expert")` instance.
- Each tool's body is a thin `_run_script(SCRIPT_PATH, args, ...)` invocation that subprocess-executes a Tier 1 script and parses JSON stdout.
- Auto-discovered by Claude Code by path convention (`.claude/tools/*.py`); no `.mcp.json` registration currently (known gap, see Deferred Work below).

---

## At a Glance

| Field | Value |
|---|---|
| Primary file | `.claude/tools/conda_forge_server.py` |
| Auxiliary servers | `gemini_server.py` (Gemini API bridge), `mcp_call.py` (JSON-RPC shell client) |
| Framework | FastMCP (`from fastmcp import FastMCP, Context`) |
| MCP instance name | `conda-forge-expert` (declared at module level: `mcp = FastMCP("conda-forge-expert")`) |
| Total `@mcp.tool` registrations | **35** (verified via `grep -c "@mcp.tool" conda_forge_server.py`) |
| Sync tools | 33 |
| Async tools | 2 (`update_cve_database`, `trigger_build` — long-running) |
| Lines of code | 1,199 (`conda_forge_server.py`) + 143 (`gemini_server.py`) + 42 (`mcp_call.py`) |
| Auto-start mechanism | Claude Code path-convention discovery of `.claude/tools/*.py` |
| Tool namespace (from caller's side) | `mcp__conda_forge_server__<tool_name>` |
| Pixi env for execution | `local-recipes` (server runs in the env where Claude Code was launched) |

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

## The 35 Tools by Surface

### Recipe-authoring surface (17 tools)

The 10-step autonomous loop (Part 1) calls these tools in order. All are sync except `trigger_build` (async).

| Tool | Tier 1 script | Used by step |
|---|---|---|
| `validate_recipe(recipe_path)` | `validate_recipe.py` | Step 2 |
| `check_dependencies(recipe_path, suggest=True, channel=None, subdirs=None)` | `dependency-checker.py` | Step 3 helper |
| `generate_recipe_from_pypi(package_name, version=None)` | `recipe-generator.py` | Step 1 |
| `scan_for_vulnerabilities(recipe_path)` | `vulnerability_scanner.py` | Step 4 |
| `trigger_build(...) [async]` | `local_builder.py` | Step 6 |
| `get_build_summary()` | (reads `build_summary.json` at repo root) | Step 7 |
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

### Atlas-intelligence surface (16 tools)

All read against `cf_atlas.db` (Part 2). All sync. `update_cve_database` is async because it can take 5-10 minutes.

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
| `cve_watcher(...)` | `cve_watcher.py` | package_version_vulns (Phase G') + vdb/ |
| `package_health(name)` | composite of Part 1 scripts | packages + feedstock_health join |
| `query_atlas(...)` | `detail_cf_atlas.py` / direct DB | packages (generic) |
| `my_feedstocks(maintainer)` | `feedstock_lookup.py` | package_maintainers + GitHub user |
| `scan_project(...)` | `scan_project.py` | packages + inventory_cache/ + ~28 input formats |
| `update_cve_database(force=False, ctx=Context) [async]` | `cve_manager.py` | cve/ feed cache |
| `update_mapping_cache(force=False)` | `mapping_manager.py` | pypi_conda_map.json |
| `get_conda_name(pypi_name)` | `name_resolver.py` | pypi_conda_mappings/* |

### Infrastructure / system surface (2 tools)

| Tool | Tier 1 script | Purpose |
|---|---|---|
| `run_system_health_check()` | `health_check.py` | Validate pixi env, MCP server availability, atlas freshness |
| `get_build_summary()` | (reads JSON file directly, not subprocess) | Build outcome inspector |

---

## Tool Implementation Pattern

Every tool follows the same skeleton (90% of the 35 tools are 5-10 lines of body code):

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

### `gemini_server.py` (143 lines)

A second FastMCP server exposing Google Gemini as MCP tools. Used as a fallback / alternative model backend when Claude Code's primary inference is unavailable or rate-limited. Requires `GEMINI_API_KEY` env var. Two tools:
- `gemini_chat(model, messages, ...)` — chat completion
- `gemini_list_models()` — model enumeration

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

---

## Server Registration with Claude Code

**Current state**: Claude Code auto-discovers `.claude/tools/*.py` MCP servers by **path convention**. There is **no explicit `.mcp.json`** in this repo or in the user's `~/.claude/` config (verified 2026-05-12).

**Settings approval surface**: `.claude/settings.local.json` has user-approved permissions for `mcp__conda_forge_server__*` namespaced tools, confirming the namespace works and tools have been invoked successfully.

**Deferred work** (per `docs/specs/claude-team-memory.md` Q13): adopt `.mcp.json` and `.claude/agents/*.md` for explicit `tools/conda_forge_server.py` + `tools/gemini_server.py` registration. This would make MCP-server discovery portable across Claude Code installations and audit-able from a single config file. Currently inventoried as a missing surface; not blocking for v1.

**Implication for rebuild**: a fresh repo will need `.mcp.json` if the rebuild target includes "works on first Claude Code launch in a new install." Without it, you rely on Claude Code's path-convention auto-discovery, which has changed across Claude Code versions.

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
1. Server starts: `python .claude/tools/conda_forge_server.py` (stdio transport).
2. `mcp = FastMCP("conda-forge-expert")` registers the server.
3. All `@mcp.tool()` decorators register their wrapped function's name, docstring, and type-hints into the tool schema.
4. Claude Code sends `tools/list` MCP request; server responds with all 35 tool schemas.
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
- `.claude/settings.json` declares the global allow/deny lists.
- `.claude/settings.local.json` declares user-approved namespaced tools (e.g., `mcp__conda_forge_server__submit_pr`).
- The MCP server itself has no auth — anything that can read its stdio can invoke any tool.

**Trust boundary**: the MCP server runs **inside** the user's Claude Code session, with the user's filesystem and network credentials. There is no sandbox. Tier 1 scripts that mutate the filesystem (`edit_recipe`, `migrate_to_v1`, `submit_pr`) are gated by Claude Code's permission UI before invocation.

**JFROG_API_KEY leak applies here too**: the MCP server inherits the env vars Claude Code was launched with. If `JFROG_API_KEY` is set, every outbound HTTP from every Tier 1 script invocation will leak it (per `docs/enterprise-deployment.md` § 2). Mitigation: launch Claude Code with `JFROG_API_KEY` unset, or use the subshell pattern documented in `deployment-guide.md`.

---

## Deferred Work (per claude-team-memory spec)

Captured from `docs/specs/claude-team-memory.md` Q13 and surfaced here so the rebuild includes them:

1. **Add `.mcp.json`** to the repo root, registering `conda_forge_server.py` and `gemini_server.py` explicitly. Makes discovery portable.
2. **Add `.claude/agents/*.md`** entries that declare which agent should use which MCP tools (currently implicit via CLAUDE.md prose).
3. **Inventory the MCP-only tools** (no public CLI): `update_cve_database`, `update_mapping_cache`, `lookup_feedstock`, `get_feedstock_context`, `enrich_from_feedstock`, `check_dependencies`, `check_github_version`, `get_conda_name`. Consider promoting some to Tier 2 wrappers for shell-accessibility.

---

## Integration Points (recap)

See `integration-architecture.md` for full cross-part contracts. Summary:

- **← Part 1 (skill)**: every MCP tool wraps a Tier 1 canonical script. Part 1's `scripts/` is the implementation; Part 3 is the wire format.
- **← Part 2 (cf_atlas)**: 16 of the 35 tools query `cf_atlas.db` directly (via Tier 1 scripts). Part 3 doesn't talk to the DB itself — it shells out.
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
   - 35 `@mcp.tool()` decorated functions, one per Part 1 / Part 2 capability.
4. **Out-of-band state files**: ensure `build_summary.json` + `build.pid` paths are agreed with Part 1's `local_builder.py`.
5. **Auxiliary servers** (optional): `gemini_server.py` for Gemini bridge; `mcp_call.py` for shell-side JSON-RPC.
6. **Register with Claude Code**: write `.mcp.json` (recommended for portability); or rely on path-convention auto-discovery (current state).
7. **Settings approvals**: as users run tools, `.claude/settings.local.json` accumulates approved namespaces. No bulk-approve mechanism currently.
8. **Tests**: integration tests in `.claude/skills/conda-forge-expert/tests/integration/` that exercise MCP-shape invocations via `mcp_call.py`. (Currently sparse; a meta-test that asserts every Tier 1 script with a `main()` is wrapped by some MCP tool would catch drift.)

Rebuild order: Part 3 must exist after Parts 1 and 2 (which it wraps), but before Part 4 routinely consumes it (BMAD agents depend on MCP-tool availability for conda-forge work).
