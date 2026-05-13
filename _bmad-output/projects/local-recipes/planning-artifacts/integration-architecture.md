---
doc_type: integration-architecture
project_name: local-recipes
date: 2026-05-12
parts_integrated: 4
source_pin: 'conda-forge-expert v7.9.0'
---

# Integration Architecture: How the Four Parts Connect

The four parts of `local-recipes` are conceptually separable but **operationally interdependent**. This document is the contract sheet: what each part expects from the others, where data flows, where coupling lives, and where the cross-cutting concerns (auth, env vars, security) sit.

A rebuild that gets the parts right individually but misses these contracts will produce a non-functional system. Read this *after* the four architecture docs (`architecture-{conda-forge-expert,cf-atlas,mcp-server,bmad-infra}.md`).

---

## Topology

```
                                  ┌───────────────────────────────┐
                                  │     User / Claude Code         │
                                  └──────────────┬─────────────────┘
                                                 │
                          ┌──────────────────────┴──────────────────────┐
                          │                                              │
                          ▼ (BMAD-driven planning + dev)                  ▼ (direct conda-forge work)
              ┌────────────────────────┐                       ┌─────────────────────┐
              │  Part 4: BMAD          │ ─── Rule 1: invoke ──▶│  Part 1: CFE skill  │
              │  - 65 skills           │                       │  - 10-step loop     │
              │  - 6-layer config      │ ◀── Rule 2: retro ────│  - 5 critical       │
              │  - 3 active projects   │    closeout updates   │    constraints      │
              │  - active-project      │    SKILL.md +         │  - SKILL.md         │
              │    resolution          │    CHANGELOG          │  - 11 reference     │
              └────────────────────────┘                       │  - 8 guides         │
                                                                │  - 42 Tier 1 scripts│
                                                                └─────────┬───────────┘
                                                                          │ Tier 1 scripts
                                                                          │ are imported by
                                                                          │ Parts 2 + 3
                                              ┌───────────────────────────┼───────────────────────┐
                                              │                           │                       │
                                              ▼ (atlas pipeline)          ▼ (MCP wire format)     │
                                ┌──────────────────────────┐   ┌────────────────────────┐         │
                                │   Part 2: cf_atlas        │   │  Part 3: MCP server     │         │
                                │   - 17 phases (B → N)     │   │  - 35 tools             │         │
                                │   - schema v19            │◀──│  - thin subprocess      │         │
                                │   - 17 CLIs               │   │    wrappers over Tier 1 │         │
                                │   - S3/cf-graph offline   │   │  - auto-started by      │         │
                                │     backends              │   │    Claude Code          │         │
                                └────────┬─────────────────┘   └──────────┬─────────────┘         │
                                         │                                  │                       │
                                         └────────────┬─────────────────────┘                       │
                                                      ▼                                              │
                          ┌───────────────────────────────────────────────────┐                     │
                          │  Shared state: .claude/data/conda-forge-expert/   │◀────────────────────┘
                          │  - cf_atlas.db (SQLite WAL)                       │
                          │  - vdb/, vdb-cache/                                │
                          │  - cve/                                            │
                          │  - pypi_conda_map.json                             │
                          │  - cf-graph-countyfair.tar.gz                      │
                          │  - cache/parquet/                                  │
                          └───────────────────────────────────────────────────┘
                                                      │
                                                      ▼
                          ┌───────────────────────────────────────────────────┐
                          │  Cross-cutting auth chain:                         │
                          │  .claude/skills/conda-forge-expert/scripts/_http.py│
                          │  - truststore (native CA)                          │
                          │  - JFROG_API_KEY → X-JFrog-Art-Api header          │
                          │    ★ leaks to every host (mitigation: subshell)    │
                          │  - GitHub token → Authorization: token             │
                          │  - .netrc fallback                                 │
                          └───────────────────────────────────────────────────┘
```

---

## The 7 Integration Contracts

Each contract is a relationship between two parts (or a part and a shared resource) that the rebuild must reproduce faithfully.

### Contract 1: Part 1 ↔ Part 2 — Shared `scripts/` directory

**Description**: cf_atlas lives **inside** Part 1's `.claude/skills/conda-forge-expert/scripts/` directory. The orchestrator (`conda_forge_atlas.py`), the 17 phase functions, the 15 query CLIs, and the support modules (`_cf_graph_versions.py`, `_parquet_cache.py`, `_sbom.py`) are all in this directory alongside Part 1's recipe-lifecycle scripts.

**Why this coupling exists**: the atlas serves Part 1's recipe-authoring queries (`scan_for_vulnerabilities`, `check_dependencies`, `behind-upstream`, etc.). Moving the atlas to a separate directory would force Part 1's scripts to import across a module boundary that doesn't exist today.

**Rebuild implication**: don't try to separate Part 2 into its own subdirectory or package. The shared `scripts/` is the contract.

### Contract 2: Parts 1+2 → Shared data directory

**Description**: Both parts read/write `.claude/data/conda-forge-expert/`. Part 2 owns the writes (atlas phases populate `cf_atlas.db`, the cve_manager populates `cve/`, vdb tools populate `vdb/`); Part 1 owns the reads (recipe-lifecycle scripts query cf_atlas.db for intelligence).

**Data directory contents** (verified):
- `cf_atlas.db` + `cf_atlas.db-shm` + `cf_atlas.db-wal` — SQLite (WAL mode) primary
- `cf_atlas_meta.json` — atlas run metadata
- `cf-graph-countyfair.tar.gz` — cf-graph offline snapshot
- `pypi_conda_map.json` — PyPI→conda name cache
- `vdb/`, `vdb-cache/` — AppThreat vulnerability DB
- `cve/` — CVE feed cache
- `cache/parquet/` — Phase F S3 monthly parquet cache (created on demand)
- `inventory_cache/` — scan_project inventory cache (created on demand)

**Gitignored** — `_bmad-output/.gitignore` and root `.gitignore` exclude this directory entirely. Refreshable via `bootstrap-data --fresh` (full) or `atlas-phase <ID>` (single).

**Rebuild implication**: data directory location is referenced by name in many scripts. Changing it requires a sweep.

### Contract 3: Part 3 → Part 1 — Thin subprocess wrapper pattern

**Description**: Every `@mcp.tool()` in `conda_forge_server.py` is a thin wrapper that subprocess-execs a Tier 1 script from Part 1's `scripts/`. The pattern is consistent:

```python
@mcp.tool()
def validate_recipe(recipe_path: str) -> str:
    args = ["--json", recipe_path]
    result = _run_script(VALIDATE_SCRIPT, args)
    return json.dumps(result, indent=2)
```

`VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_recipe.py"` where `SCRIPTS_DIR = Path(__file__).parent.parent / "skills" / "conda-forge-expert" / "scripts"`.

**Why subprocess, not direct import**:
- Process isolation (a buggy Tier 1 script doesn't crash the server)
- Timeout enforcement (`subprocess.run(..., timeout=120)`)
- Pixi env consistency (`_PYTHON = sys.executable` guarantees correct interpreter)
- JSON-stdout contract (each script accepts `--json` and emits structured output)

**Tier 1 script invariant**: any script wrapped by an MCP tool MUST:
1. Accept `--json` flag
2. Emit valid JSON on stdout
3. Use exit code as informational only (the JSON is authoritative)
4. Direct error diagnostics to stderr (captured by `_run_script` on JSONDecodeError fallback)

**Rebuild implication**: keep the wrapper pattern thin. Don't inline logic into the MCP tool body — it belongs in Tier 1.

### Contract 4: Part 4 → Part 1 — Two CLAUDE.md mandates

Defined in `CLAUDE.md` § "BMAD ↔ conda-forge-expert integration":

**Rule 1 (skill invocation)**: any BMAD agent whose task touches conda-forge work must invoke `Skill: conda-forge-expert` before producing recipe code or running recipe tooling. The skill's 10-step loop, Operating Principles, and Critical Constraints override BMAD story instructions when they conflict.

**Rule 2 (retro closeout)**: every BMAD effort that did conda-forge work must run `bmad-retrospective` at closeout, with findings landing as edits to `SKILL.md` / `reference/*` / `guides/*` / `CHANGELOG.md`. Skill version bumps per semver.

**Why these are at the integration layer, not within either part**: BMAD doesn't know what conda-forge work looks like; CFE doesn't know what a BMAD story is. The integration rules sit at the boundary and govern the handoff.

**Enforcement mechanism**: there isn't one. The rules are written prose; agents are expected to read CLAUDE.md and project-context.md on spawn and apply them. Auto-memory entries (`feedback_bmad_uses_cfe_skill.md`, `feedback_bmad_runs_cfe_retro.md`) reinforce them across sessions but don't enforce.

**Rebuild implication**: CLAUDE.md is load-bearing. A rebuild that doesn't reproduce Rules 1 + 2 verbatim will degrade BMAD-CFE coordination silently.

### Contract 5: All parts → `_http.py` cross-cutting auth chain

**Description**: every outbound HTTP request from any of the four parts routes through `.claude/skills/conda-forge-expert/scripts/_http.py`. The chain (in order):

1. **truststore** (native OS CA store) — corporate CA / JFrog TLS termination
2. **`JFROG_API_KEY` → `X-JFrog-Art-Api` header** — ★ leaks to every host when set
3. **`GITHUB_TOKEN` → `Authorization: token <...>`** — scoped to `api.github.com` + `github.com/api/v3/`
4. **.netrc fallback** — for other authenticated hosts

**Per-host env-var overrides** (used to point at internal mirrors):
- `CONDA_FORGE_BASE_URL` — conda channel mirror
- `S3_PARQUET_BASE_URL` — Phase F S3 backend mirror
- `PYPI_BASE_URL` — pypi.org mirror
- `ANACONDA_API_BASE` — api.anaconda.org mirror
- `GITHUB_API_BASE_URL` — api.github.com mirror (rare)

**Why `_http.py` lives in Part 1's `scripts/`**: it's a Tier 1 module that Parts 1+2 import directly; Part 3 indirectly inherits it through subprocess execution of Tier 1 scripts. BMAD doesn't use it (BMAD doesn't fetch HTTP).

**The JFROG_API_KEY cross-host leak** (Critical Constraint):
- Symptom: when `JFROG_API_KEY` is exported in the shell, `_http.make_request()` attaches `X-JFrog-Art-Api` to every outbound request regardless of destination.
- Affected hosts: `pypi.org`, `github.com`, `api.anaconda.org`, AWS S3, etc.
- Mitigation pattern: `( unset JFROG_API_KEY; <command> )` subshell scoping
- Full documentation: `docs/enterprise-deployment.md` § 2 → "Cross-host credential leak" + `_bmad-output/projects/local-recipes/project-context.md` § Air-Gapped/Enterprise

**Rebuild implication**: `_http.py` is the single biggest piece of cross-cutting code. Tests for it are sparse (mostly integration); a rebuild should add explicit unit tests for the auth chain ordering and the cross-host leak mitigation.

### Contract 6: Parts 1+2 → `vuln-db` pixi env

**Description**: Phase G + Phase G' (vulnerability scoring) and Part 1's `scan_for_vulnerabilities` require the AppThreat vulnerability database (`vdb/`). The database is populated by tooling that runs in the `vuln-db` pixi env, which has the `appthreat-vulnerability-db` PyPI package as a dependency.

**Pixi env separation rationale**: AppThreat vdb pulls ~500MB of NVD + GHSA + OSV + npm + Snyk advisory data on install. Keeping it in a separate pixi env (vs. bundling into `local-recipes`) keeps the default env lean (~1.5GB vs. ~2GB).

**Env activation pattern**:
- `pixi run -e vuln-db update-cve-db` — refresh the vdb data
- `pixi run -e vuln-db bootstrap-data` — full atlas bootstrap including Phase G/G' (which need vdb importable)
- `pixi run -e local-recipes <anything-else>` — default

**`VDB_HOME` env var**: set by `vuln-db` env's activation hook to `$PIXI_PROJECT_ROOT/.claude/data/conda-forge-expert/vdb`. Atlas Phase G reads this env var to locate the database.

**Rebuild implication**: keep envs separate. Conda-resolve concerns get cheaper when the default env is lean; vuln-db users pay the cost only when scanning.

### Contract 7: Part 3 ↔ Out-of-band state files

**Description**: two files at **repo root** (not inside `.claude/`) bridge async tool state between Part 3 and Part 1:

| File | Writer | Reader | Purpose |
|---|---|---|---|
| `build_summary.json` | Part 1's `local_builder.py` (invoked via Part 3's `trigger_build`) | Part 3's `get_build_summary()` | Build outcome — status, artifacts, log path |
| `build.pid` | Part 3's `trigger_build` startup | Part 3's `_active_build` cleanup | Process ID of running build |

Both gitignored. Tolerated when absent.

**Why repo root, not `.claude/data/`**: historical — predates the structured data directory. Could be migrated to `.claude/data/conda-forge-expert/build_summary.json` in a future cleanup, but no current pressure.

**Rebuild implication**: place these files at repo root for compatibility, or migrate the convention with a same-PR change to both writers and readers.

---

## Cross-Cutting Concerns

### Pixi env contract

8 envs, each with a specific role:

| Env | Used by | Purpose |
|---|---|---|
| `local-recipes` (default) | Parts 1, 2, 3 (most operations) | Recipe lifecycle + atlas read/write + MCP server |
| `vuln-db` | Parts 1, 2 (vuln-specific operations only) | AppThreat vdb-dependent work (Phase G/G', `scan_for_vulnerabilities`) |
| `grayskull` | Part 1 (`generate_recipe_from_pypi`) | grayskull for PyPI→conda recipe scaffolding |
| `conda-smithy` | Part 1 (lint + CI fidelity) | `conda-smithy recipe-lint` |
| `build` | Parts (build operations) | rattler-build via cross-platform features |
| `linux`, `osx`, `win` | Parts (per-platform builds) | Platform-specific build configurations |

**Default env directive**: `# default-env: local-recipes` at the top of `[environments]` in `pixi.toml`. `scripts/load-env.sh` parses this and activates the named env.

### Env-var inheritance from launch shell

Every part inherits env vars from the shell that launched Claude Code (or the pixi env). Critical env vars:

| Env var | Required for | Risk |
|---|---|---|
| `JFROG_API_KEY` | JFrog auth | **Cross-host leak** — see Contract 5 |
| `GITHUB_TOKEN` | GitHub auth (Part 1 `submit_pr`, Part 2 Phase K + N) | Lower risk; scoped to GitHub by `_http.py` |
| `*_BASE_URL` overrides | Air-gap / internal mirrors | Required for offline operation; see `deployment-guide.md` |
| `GEMINI_API_KEY` | Part 3 `gemini_server.py` | Only if Gemini bridge is used |
| `VDB_HOME` | Phases G + G' + scan_for_vulnerabilities | Set automatically by `vuln-db` env activation |
| `PHASE_F_SOURCE` / `PHASE_H_SOURCE` | Atlas backend selection | Defaults are sane (`auto` / `pypi-json`) |
| `BOOTSTRAP_<STEP>_TIMEOUT` | Atlas step timeouts | Override for cold `--fresh` runs |

### Permission gates (Claude Code)

`.claude/settings.json` (committed) declares the allow/deny lists for tools Claude Code can invoke. `.claude/settings.local.json` (gitignored) accumulates user-approved namespaced tools as they're invoked (e.g., `mcp__conda_forge_server__submit_pr`).

The permission UI applies to:
- Bash commands (with glob patterns)
- WebFetch (per-domain)
- MCP tools (per-namespace + per-tool)
- Skill invocations

**Rebuild implication**: ship `.claude/settings.json` with a sensible default allow-list (the current one allows `Bash(curl *)`, `Bash(rattler-build *)`, `Bash(pixi run *)`, `Bash(git push)` without `--force`, etc.). Users will accumulate their own approvals in `.local.json`.

---

## Data Flow Examples

### Authoring a new recipe (BMAD-driven)

```
1. User: "Package <pkg> for conda-forge"
2. Claude Code activates BMAD (bmad-quick-dev) given the request shape.
3. BMAD reads project-context.md → sees Rule 1 → invokes Skill: conda-forge-expert.
4. CFE skill activates → reads SKILL.md.
5. CFE step 1: generate_recipe_from_pypi (MCP tool) →
       Part 3 conda_forge_server.py @mcp.tool →
       subprocess to Part 1 recipe-generator.py →
       which calls grayskull (in grayskull pixi env), post-processes, writes recipe.yaml.
6. CFE step 2-7: validate / scan / optimize / build → similar subprocess paths.
7. CFE step 8b: prepare_submission_branch → pushes to fork, returns fork_branch_url.
8. Human inspects fork_branch_url in browser. (Critical: submit_pr is ungated.)
9. CFE step 9-10: submit_pr(dry_run=True), then submit_pr() → PR opens.
10. BMAD effort closeout → Rule 2 → bmad-retrospective →
       updates SKILL.md if novel findings, bumps skill version, writes CHANGELOG entry.
11. Next BMAD spawn: re-reads project-context.md; checks last_synced_skill_version pin.
       If MINOR bumped, triggers re-sync of project-context.md against new SKILL.md.
```

Every arrow is a cross-part contract.

### Atlas refresh (cron-driven)

```
1. Cron: `pixi run -e local-recipes atlas-phase F` (weekly)
2. Tier 2 wrapper: .claude/scripts/conda-forge-expert/atlas_phase.py
3. Subprocess: Tier 1 .claude/skills/conda-forge-expert/scripts/atlas_phase.py
4. atlas_phase.py imports conda_forge_atlas as cfa.
5. cfa.open_db() opens .claude/data/conda-forge-expert/cf_atlas.db (WAL mode).
6. cfa.init_schema(conn) — idempotent migration to v19.
7. cfa.run_single_phase("F", conn) →
       phase_f_downloads() reads PHASE_F_SOURCE env var →
       branches to _phase_f_via_api / _phase_f_via_s3 / _phase_f_via_auto →
       each branch routes outbound HTTP through _http.py (Contract 5) →
       writes rows to packages + package_version_downloads tables.
8. JSON result returned to subprocess; stdout printed to cron log.
```

Phase F doesn't touch BMAD, Part 1's recipe-lifecycle, or Part 3's MCP server. Same for the other 16 phases when run via `atlas-phase`.

### Air-gapped recipe authoring (JFrog-routed)

```
1. Operator launches Claude Code with JFROG_API_KEY UNSET (mitigation pattern).
2. .pixi/config.toml configured to use JFrog conda mirror as default channel.
3. CONDA_FORGE_BASE_URL + PYPI_BASE_URL + S3_PARQUET_BASE_URL set to JFrog endpoints.
4. JFROG_API_KEY set ONLY in shells touching JFrog (e.g. bootstrap-data refresh):
       ( export JFROG_API_KEY=...; pixi run -e local-recipes bootstrap-data )
5. Recipe authoring runs unmolested; _http.py routes to internal mirrors via *_BASE_URL.
6. submit_pr / prepare_submission_branch run in a shell WITHOUT JFROG_API_KEY,
   so no header leaks to github.com.
```

---

## Failure Modes at Integration Boundaries

| Failure | Where | Mitigation |
|---|---|---|
| BMAD agent ignores Rule 1 (skips CFE skill for conda-forge work) | Part 4 ↔ Part 1 | Auto-memory feedback entry reinforces across sessions; reviewer catches in PR review |
| BMAD effort closes without Rule 2 retro | Part 4 ↔ Part 1 | Skill drift accumulates silently until next conda-forge effort hits it. Currently no automated enforcement. |
| Tier 1 script doesn't emit JSON | Part 3 ↔ Part 1 | `_run_script` falls back to `{"error": "Failed to parse JSON output", stdout, stderr, exit_code}` — caller sees the error |
| `JFROG_API_KEY` set in shell that calls external hosts | All parts → enterprise | Documented in 3 places (CLAUDE.md, project-context.md, enterprise-deployment.md); no automated detection |
| MCP server not auto-discovered by Claude Code | Part 3 | Currently relies on path-convention; missing `.mcp.json` registration (deferred work) |
| `cf_atlas.db` schema older than v19 | Parts reading the DB | `init_schema()` runs on every connection open and migrates additively; safe to call on stale DBs |
| `pypi_conda_map.json` stale (>7d) | Part 1 name resolution | `update_mapping_cache` MCP tool refreshes; TTL is informational, not enforced |
| Multiple BMAD projects writing to same artifacts | Part 4 multi-project | Active-project marker resolves before writes; no enforcement if marker not set (silently writes to global `_bmad-output/`) |
| Build's `build.pid` leaks (orphan process) | Part 3 trigger_build | Manual cleanup; `_active_build` reference is per-server-process only |

---

## Versioning Discipline Across Parts

| Part | Version source | Bump trigger |
|---|---|---|
| Part 1 (skill) | `CHANGELOG.md` TL;DR + `MANIFEST.yaml: version` (separate surfaces) | Semver: PATCH for fixes, MINOR for new gotchas/sections, MAJOR for breaking workflow changes. CHANGELOG bumps on every release; MANIFEST bumps only on portability protocol changes (currently v7.0.0; release is v7.7.2). |
| Part 2 (cf_atlas) | `SCHEMA_VERSION` constant in `conda_forge_atlas.py:113` + CHANGELOG of skill | Schema version increments on every additive migration. Currently v19. |
| Part 3 (MCP server) | No explicit version — implied by Part 1's CHANGELOG | If MCP tool signature changes, treat as Part 1 MINOR bump. |
| Part 4 (BMAD) | `_bmad/bmm/config.yaml` header (Generated by BMAD installer Version: 6.6.0) | Set by BMAD installer; bump via `bmad-method` package upgrade. |

**Project-context drift pin**: `_bmad-output/projects/local-recipes/project-context.md` frontmatter `last_synced_skill_version` pins to a MINOR (currently `v7.8`). When Part 1's CHANGELOG ships a new MINOR, the pin signals re-sync needed.

---

## What a Rebuild Must Reproduce Faithfully

If any of these break, the system silently degrades:

1. **The shared `scripts/` directory** (Contract 1) — Parts 1 + 2 live together. Don't separate.
2. **The shared data directory** (Contract 2) — `.claude/data/conda-forge-expert/` is the single source of mutable state.
3. **The thin-wrapper subprocess pattern** (Contract 3) — Part 3's tools shell out to Part 1's `scripts/`. Don't inline.
4. **CLAUDE.md Rules 1 + 2** (Contract 4) — without these, BMAD-CFE coordination is anarchy.
5. **`_http.py` as the only outbound HTTP path** (Contract 5) — including the JFROG_API_KEY mitigation discipline.
6. **The `vuln-db` env separation** (Contract 6) — don't bundle AppThreat into the default env.
7. **Out-of-band state files at repo root** (Contract 7) — `build_summary.json` + `build.pid`. (Or migrate the convention atomically.)

Plus the cross-cutting items (pixi envs, env-var inheritance, permission gates) are setup conditions, not contracts per se, but the rebuild must establish them before Parts 1-3 can function.

---

## Visual: A Single Recipe-Authoring Effort End-to-End

```
                  user prompt: "package <pkg>"
                              │
                              ▼
           ┌──────────────────────────────────────┐
           │  Claude Code activates BMAD skill    │ Part 4
           │  bmad-quick-dev                       │
           └──────────────┬───────────────────────┘
                          │ reads project-context.md
                          │ sees Rule 1 mandate
                          ▼
           ┌──────────────────────────────────────┐
           │  Skill: conda-forge-expert            │ Part 1 activated
           │  Reads SKILL.md (10-step loop)        │
           └──────────────┬───────────────────────┘
                          │
                          ▼
           ┌──────────────────────────────────────┐
           │  10 MCP tool calls in sequence:       │ Part 3 invoked
           │  generate → validate → edit → scan    │
           │  → optimize → trigger_build → ...     │
           └──────────────┬───────────────────────┘
                          │ each tool subprocesses to:
                          ▼
           ┌──────────────────────────────────────┐
           │  Tier 1 Python scripts                │ Part 1 implementation
           │  read/write recipe.yaml + query      │
           │  cf_atlas.db via _http.py             │
           └──────────────┬───────────────────────┘
                          │
                          ▼
           ┌──────────────────────────────────────┐
           │  Shared data: cf_atlas.db, vdb/,      │ Parts 1+2 shared
           │  cve/, mapping caches                 │
           └──────────────┬───────────────────────┘
                          │ build green, PR opened
                          ▼
           ┌──────────────────────────────────────┐
           │  Effort closeout: bmad-retrospective  │ Part 4 ← Part 1
           │  Updates SKILL.md / CHANGELOG.md /    │ Rule 2
           │  reference/* / guides/*               │
           └──────────────────────────────────────┘
```

This is the canonical flow. Every other workflow (atlas refresh, vulnerability scan, project documentation) is a subset.
