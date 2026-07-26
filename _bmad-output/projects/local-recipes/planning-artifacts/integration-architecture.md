---
doc_type: integration-architecture
project_name: local-recipes
date: 2026-07-25
parts_integrated: 5
source_pin: 'conda-forge-expert v8.79.1'
---

# Integration Architecture: How the Five Parts Connect

> **Re-grounded 2026-07-25** (source_pin → v8.79.1). **A fifth part joined, and it integrates by *refusing* most of the existing contracts.** `src/shared/packages/` hosts `pyforge-packages` — five hatchling-built dists on one PEP 420 `pyforge` namespace. Contracts 1–7 are preserved (with fact corrections); **Contracts 8–12 are new** and cover the PEP 420 namespace, the extras-gated one-directional package edges, the second MCP server, the frozen report schemas, and the parallel-reimplementation/parity relationship with Part 2 — including the one place a legacy contract was deliberately **not** inherited (`_http.py` global credential injection, "FIXED, not ported"). Cross-cutting sections updated: **19 pixi envs** in two families, the `_http.py` auth chain restated as **two separate chains** (SSL trust vs. per-request auth) with **21 `<HOST>_BASE_URL`** mirror vars, permission gates, CI gates, and a new **spec-surface governance** contract. Corrections to statements that were **wrong, not merely stale**, are marked inline at each site: Contract 5's GitHub scheme (**Bearer**, not `token`), truststore mis-listed as an auth step, the auth chain presented as linear when it **branches on host**, Contract 3's timeouts (**600 s** for `update_cve_database`), and the MCP-registration failure mode (registered in `~/.claude.json` by design — the "missing `.mcp.json`" line described a **non-goal as deferred work**). Stale figures raised to live: the atlas schema version, the BMAD installer (**6.10.0**), the skill catalogue (**89**), the project count (**14**), and Part 2's CLI count (**17**). Re-verified **unchanged**: 46 legacy MCP tools, schema v29, 22 executable atlas phases (23 cataloged), G1–G106, and the JFROG_API_KEY cross-host leak (still live in `_http.py`).


The five parts of `local-recipes` are conceptually separable but **operationally interdependent** — with one important asymmetry. Parts 1–4 (the factory) are tightly coupled by a shared `scripts/` directory, a shared data directory, and a shared auth chain. **Part 5 (the product line) is coupled to almost none of that on purpose**: it shares the pixi workspace and the `pyforge` namespace, and nothing else. Reading Part 5's contracts as "more of the same" is the single easiest way to misunderstand this system.

This document is the contract sheet: what each part expects from the others, where data flows, where coupling lives, where it is deliberately absent, and where the cross-cutting concerns (auth, env vars, security, governance) sit.

A rebuild that gets the parts right individually but misses these contracts will produce a non-functional system. Read this *after* the four architecture docs (`architecture-{conda-forge-expert,cf-atlas,mcp-server,bmad-infra}.md`); Part 5 has no part-doc, so its detail lives here and in `_bmad-output/projects/pyforge-*/planning-artifacts/`.

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
              │  - 89 skills (93 dirs) │                       │  - 10-step loop     │
              │  - 6-layer config      │ ◀── Rule 2: retro ────│  - 5 critical       │
              │  - 14 projects         │    closeout updates   │    constraints      │
              │  - marker + 2 symlinks │    SKILL.md +         │  - SKILL.md         │
              │    (BOTH; C11)         │    CHANGELOG          │  - 15 reference     │
              │  - bmad-loop harness   │                       │  - 9 guides         │
              └────────────────────────┘                       │  - 66 Tier 1 scripts│
                                                                └─────────┬───────────┘
                                                                          │ Tier 1 scripts
                                                                          │ are imported by
                                                                          │ Parts 2 + 3
                                              ┌───────────────────────────┼───────────────────────┐
                                              │                           │                       │
                                              ▼ (atlas pipeline)          ▼ (MCP wire format)     │
                                ┌──────────────────────────┐   ┌────────────────────────┐         │
                                │   Part 2: cf_atlas        │   │  Part 3: MCP server     │         │
                                │   - 22 exec. phases       │   │  - 46 tools (44 sync    │         │
                                │     (B → S; 23 cataloged) │◀──│    + 2 async), stdio    │         │
                                │   - schema v29            │   │  - thin subprocess      │         │
                                │     21 tables / 5 views   │   │    wrappers over Tier 1 │         │
                                │   - 17 CLIs               │   │  - registered in        │         │
                                │   - S3/cf-graph offline   │   │    ~/.claude.json,      │         │
                                │     backends              │   │    NOT in-repo (C7b)    │         │
                                └────────┬─────────────────┘   └──────────┬─────────────┘         │
                                         │                                  │                       │
                                         │  C12: parity, NOT replacement    │                       │
                                         │  (legacy stays authoritative)    │                       │
                                         ▼                                  │                       │
        ┌─────────────────────────────────────────────────┐                │                       │
        │  Part 5: pyforge-packages  (src/shared/packages/)│                │                       │
        │  ONE PEP 420 namespace `pyforge` — no __init__   │  C8            │                       │
        │  ┌──────────────┐                                │                │                       │
        │  │pyforge-warden│◀── gate=[…] extras ──┬─ atlas  │  C9 (one-way)  │                       │
        │  │  ComplianceR.│                      └─ doctor │                │                       │
        │  └──────────────┘                                │                │                       │
        │  pyforge-atlas ── own 11-tool FastMCP server ────┼──▶ C10          │                       │
        │       └── Parquet + Ibis→DuckDB (no .duckdb)     │                │                       │
        │  pyforge-herald · pyforge-scribe · pyforge-doctor│                │                       │
        │  6 lean envs, all no-default-feature = true      │                │                       │
        └────────────────────┬────────────────────────────┘                │                       │
                             │  ✗ does NOT use the shared data dir          │                       │
                             │  ✗ does NOT use _http.py                     │                       │
                             ▼                                              │                       │
                          ┌───────────────────────────────────────────────────┐                     │
                          │  Shared state: .claude/data/conda-forge-expert/   │◀────────────────────┘
                          │  ★ ABSENT in this checkout (gitignored, unbuilt)  │
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
                          │  Cross-cutting auth chain — PARTS 1–3 ONLY:        │
                          │  .claude/skills/conda-forge-expert/scripts/_http.py│
                          │  SSL: REQUESTS_CA_BUNDLE / SSL_CERT_FILE →         │
                          │       truststore.inject_into_ssl() → certifi       │
                          │  1. JFROG_API_KEY → X-JFrog-Art-Api                │
                          │     ★ leaks to every host (mitigation: subshell)   │
                          │  2. JFROG_USERNAME+PASSWORD → Basic                │
                          │  3. ~/.netrc → Basic                               │
                          │  4. GITHUB_TOKEN/GH_TOKEN → Bearer (github.com)    │
                          │  5. unauthenticated                                │
                          │  + 21 <HOST>_BASE_URL mirror-routing vars          │
                          └───────────────────────────────────────────────────┘
                                    ▲
                                    │ Part 5 does NOT inherit this. pyforge-atlas'
                                    │ catalog.yml: global injection "FIXED, not
                                    │ ported" — per-dataset credentials only (C12)
```

---

## The Integration Contracts (1–12, plus 7b)

Each contract is a relationship between two parts (or a part and a shared resource) that the rebuild must reproduce faithfully.

**Contracts 1–7** are the original factory contracts (Parts 1–4). They are preserved as written where still true, with dated **Correction (2026-07-25)** notes where a stated fact turned out to be wrong or has gone stale. **7b** is split out rather than renumbered so the original seven keep their familiar numbers — it covers MCP server registration, which the previous version got backwards.

**Contracts 8–12** are new, and every one of them concerns Part 5. Note their character: four of the five are about *decoupling* — what Part 5 declines to share. That asymmetry is the design, not an oversight.

### Contract 1: Part 1 ↔ Part 2 — Shared `scripts/` directory

**Description**: cf_atlas lives **inside** Part 1's `.claude/skills/conda-forge-expert/scripts/` directory. The orchestrator (`conda_forge_atlas.py`), the 22 executable phase functions, the query CLIs, and the support modules (`_cf_graph_versions.py`, `_parquet_cache.py`, `_sbom.py`) are all in this directory alongside Part 1's recipe-lifecycle scripts.

**Why this coupling exists**: the atlas serves Part 1's recipe-authoring queries (`scan_for_vulnerabilities`, `check_dependencies`, `behind-upstream`, etc.). Moving the atlas to a separate directory would force Part 1's scripts to import across a module boundary that doesn't exist today.

**Rebuild implication**: don't try to separate Part 2 into its own subdirectory or package. The shared `scripts/` is the contract.

**Correction (2026-07-25)**: this contract is intact, but it is no longer the *only* atlas. Part 5's `pyforge-atlas` is a separate, properly-packaged reimplementation living outside `.claude/` entirely (Contract 12). The rule above still binds the legacy pipeline — it is not an argument against the reimplementation, and a rebuild should not "resolve" the apparent tension by merging them.

### Contract 2: Parts 1+2 → Shared data directory

**Description**: Both parts read/write `.claude/data/conda-forge-expert/`. Part 2 owns the writes (atlas phases populate `cf_atlas.db`, the cve_manager populates `cve/`, vdb tools populate `vdb/`); Part 1 owns the reads (recipe-lifecycle scripts query cf_atlas.db for intelligence).

**Data directory contents** (as documented; see the correction below):
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

**Correction (2026-07-25)**: the "(verified)" tag on the contents list is no longer honest — **`.claude/data/conda-forge-expert/` does not exist in this checkout at all**. It is gitignored and the atlas has never been built in this working tree. The list above is the *expected* layout per the code that writes it (which is verifiable), not an observed directory listing (which is not). Mark every downstream row-count, cache-size or freshness claim accordingly. **[UNVERIFIABLE IN THIS CHECKOUT]**

**Also**: Part 5 does **not** participate in this contract. `pyforge-atlas` writes Parquet under its own `data/<layer>/<dataset>/`; the two stores never share a path.

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
- Timeout enforcement (`subprocess.run(..., timeout=120)` default; **600 s for `update_cve_database`**)
- Pixi env consistency (`sys.executable` — the pixi env interpreter — guarantees the correct interpreter)
- JSON-stdout contract (each script accepts `--json` and emits structured output)

**Tool surface** (46 total): **21 recipe-authoring · 21 atlas-intelligence · 2 project-scanning** (`scan_project`, `env_inspect`) **· 2 infra** (`run_system_health_check`, `update_mapping_cache`). **44 sync + 2 async** — the two async are `update_cve_database` and `trigger_build`, i.e. exactly the long-running ones.

**Auth boundary**: the server contains **zero auth code**. Credentials are applied inside the subprocess, by the Tier 1 script's `_http` import (Contract 5). A rebuild that adds an auth layer to the server breaks the boundary.

**Tier 1 script invariant**: any script wrapped by an MCP tool MUST:
1. Accept `--json` flag
2. Emit valid JSON on stdout
3. Use exit code as informational only (the JSON is authoritative)
4. Direct error diagnostics to stderr (captured by `_run_script` on JSONDecodeError fallback)

**Rebuild implication**: keep the wrapper pattern thin. Don't inline logic into the MCP tool body — it belongs in Tier 1.

**Correction (2026-07-25)**: this contract now describes only the *legacy* server. Part 5's `pyforge-atlas` ships a second FastMCP server that follows the **opposite** pattern — in-process Kedro/Ibis calls, not subprocess wrappers, because it wraps its own library rather than a foreign script tree. See Contract 10. Never quote a combined tool count.

### Contract 4: Part 4 → Part 1 — Two CLAUDE.md mandates

Defined in `CLAUDE.md` § "BMAD ↔ conda-forge-expert integration":

**Rule 1 (skill invocation)**: any BMAD agent whose task touches conda-forge work must invoke `Skill: conda-forge-expert` before producing recipe code or running recipe tooling. The skill's 10-step loop, Operating Principles, and Critical Constraints override BMAD story instructions when they conflict.

**Rule 2 (retro closeout)**: every BMAD effort that did conda-forge work must run `bmad-retrospective` at closeout, with findings landing as edits to `SKILL.md` / `reference/*` / `guides/*` / `CHANGELOG.md`. Skill version bumps per semver.

**Why these are at the integration layer, not within either part**: BMAD doesn't know what conda-forge work looks like; CFE doesn't know what a BMAD story is. The integration rules sit at the boundary and govern the handoff.

**Enforcement mechanism**: there isn't one. The rules are written prose; agents are expected to read CLAUDE.md and project-context.md on spawn and apply them. Auto-memory entries (`feedback_bmad_uses_cfe_skill.md`, `feedback_bmad_runs_cfe_retro.md`) reinforce them across sessions but don't enforce.

**Rebuild implication**: CLAUDE.md is load-bearing. A rebuild that doesn't reproduce Rules 1 + 2 verbatim will degrade BMAD-CFE coordination silently.

**Correction (2026-07-25)**: two additions to the mandate set, same prose-enforced character. (1) **CI-gate pre-emption**: any PR touching files outside `recipes/` must carry the `maintenance` label, and any PR touching `pixi.toml` must ship a regenerated `environment.yaml` — pre-empted at PR-open, not after red CI (see Cross-Cutting Concerns § CI gates). Since every Part 4 and Part 5 change is outside `recipes/` by definition, this is now a routine part of the BMAD↔repo handoff. (2) **Story-spec promotion**: `bmad-loop` drafts a story spec into the run's gitignored `implementation-artifacts/`; after merge it must be **promoted into the tracked `planning-artifacts/specs/`**. Story specs are durable, not Tier-3. The motivating incident (pyforge-warden losing 13 of 31 story specs to worktree teardown) is exactly the silent degradation this contract section exists to prevent.

### Contract 5: Parts 1–3 → `_http.py` cross-cutting auth chain

**Description**: every outbound HTTP request from Parts 1, 2 and 3 routes through `.claude/skills/conda-forge-expert/scripts/_http.py` (1,024 LOC). Auth lives **entirely** here.

**Two separate chains, and the previous version of this contract merged them into one.**

**SSL trust chain** — applied **once at process start** via `inject_ssl_truststore()`, not per request:
1. `REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE` — explicit enterprise CA bundle
2. `truststore.inject_into_ssl()` — system OS trust anchors
3. Python default (certifi)

**Auth chain** — per request, via `auth_headers_for(url)`, **first match wins, and it branches on host**:
1. `JFROG_API_KEY` → `X-JFrog-Art-Api` header — ★ unconditional, applied to *every* host
2. elif `JFROG_USERNAME` + `JFROG_PASSWORD` → `Authorization: Basic`
3. elif host is `github.com` / `api.github.com` → `GITHUB_TOKEN` or `GH_TOKEN` as **`Authorization: Bearer`**; if neither is set, `~/.netrc` → Basic
4. else (any non-GitHub host) → `~/.netrc` (or `$NETRC`) → Basic
5. otherwise unauthenticated

`skip_auth=True` returns an empty dict without consulting any env var or netrc entry — the call-site opt-out for known-public endpoints (e.g. `dev.azure.com`'s public feedstock-builds project). Its docstring names it the mitigation "until a host allowlist lands".

**Correction (2026-07-25)** — three things in the previous version of this contract were **wrong**, not merely stale:
- The GitHub step used `Authorization: token <...>`. It is **`Bearer`** (`_http.py` line 223). A rebuild copying the old scheme would send a header GitHub no longer accepts for fine-grained tokens.
- **truststore was listed as step 1 of the *auth* chain.** It is not an auth step — it is TLS/CA verification, applied once at process start, in a different function. Conflating them demotes the real step 1 (the JFrog header), which is the step carrying the security defect.
- The chain was presented as **linear**; it is **host-branching**, and `JFROG_USERNAME`/`JFROG_PASSWORD` Basic auth was missing entirely.

> **Defect found while verifying this contract (2026-07-25):** `_http.py`'s **two docstrings disagree with each other**. The module header (lines 13–17) orders the chain `… 3. ~/.netrc → 4. GITHUB_TOKEN`, while `auth_headers_for`'s own docstring (lines 190–193) orders it `… 3. GITHUB_TOKEN (github.com) → 4. ~/.netrc`. The **implementation matches the latter**: for GitHub hosts the token is tried before netrc. The module header is wrong. This is worth fixing at the source — it is precisely the kind of stale header that propagated the error into this document.

**Per-host env-var overrides**: there are **21** `<HOST>_BASE_URL` mirror-routing variables (the previous list of 5 was a sample presented as the set). Grouped:
- Conda + Python ecosystem: `CONDA_FORGE_BASE_URL`, `PYPI_BASE_URL`, `PYPI_JSON_BASE_URL`, `S3_PARQUET_BASE_URL`, `ANACONDA_API_BASE_URL` (legacy alias `ANACONDA_API_BASE`)
- Git forges: `GITHUB_BASE_URL`, `GITHUB_RAW_BASE_URL`, `GITHUB_API_BASE_URL`, `GITLAB_API_BASE_URL`, `CODEBERG_API_BASE_URL`
- Phase L registries: `NPM_BASE_URL`, `CRAN_BASE_URL`, `CPAN_BASE_URL`, `LUAROCKS_BASE_URL`, `CRATES_BASE_URL`, `RUBYGEMS_BASE_URL`, `MAVEN_BASE_URL`, `NUGET_BASE_URL`
- Vulnerability scanning: `OSV_API_BASE_URL`, `OSV_VULNS_BUCKET_URL`

**Why `_http.py` lives in Part 1's `scripts/`**: it's a Tier 1 module that Parts 1+2 import directly; Part 3 indirectly inherits it through subprocess execution of Tier 1 scripts. BMAD doesn't use it (BMAD doesn't fetch HTTP). **Part 5 deliberately does not use it** — see Contract 12.

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

**Correction (2026-07-25)**: `vuln-db` is no longer the *only* env-separation contract — it is now the mildest instance of a general rule. Six **product** envs (Contract 8) each set `no-default-feature = true`, which is a stronger separation than `vuln-db`'s (they exclude the default dependency set entirely rather than adding to it). The rationale generalizes accordingly: env membership is a **contract**, and a cross-env dependency union silently drops deps — it has broken `main` twice (PRs #113, #115). See Cross-Cutting Concerns § Pixi env contract.

### Contract 7: Part 3 ↔ Out-of-band state files

**Description**: two files at **repo root** (not inside `.claude/`) bridge async tool state between Part 3 and Part 1:

| File | Writer | Reader | Purpose |
|---|---|---|---|
| `build_summary.json` | Part 1's `local_builder.py` (invoked via Part 3's `trigger_build`) | Part 3's `get_build_summary()` | Build outcome — status, artifacts, log path |
| `build.pid` | Part 3's `trigger_build` startup | Part 3's `_active_build` cleanup | Process ID of running build |

Both gitignored. Tolerated when absent.

**Why repo root, not `.claude/data/`**: historical — predates the structured data directory. Could be migrated to `.claude/data/conda-forge-expert/build_summary.json` in a future cleanup, but no current pressure.

**Rebuild implication**: place these files at repo root for compatibility, or migrate the convention with a same-PR change to both writers and readers.

### Contract 7b: Part 3 ↔ Claude Code — server registration lives outside the repo

**Description**: the legacy MCP server is registered in **`~/.claude.json`** (user-level), with **stdio** transport. There is **no `.mcp.json` in the repo**, and `.claude/settings.json` carries **no `mcpServers` block**.

**Correction (2026-07-25)** — the previous version of this document recorded "missing `.mcp.json` registration (deferred work)" as a failure mode, and the build order listed "(Recommended) `.mcp.json` registration" as a step. That framed a **deliberate state as an outstanding task**. The consequence of getting this backwards is real in both directions:
- A rebuild that "fixes" it by adding `.mcp.json` changes the trust posture — an in-repo registration auto-offers the server to anyone who clones, rather than requiring the operator to register it.
- A rebuild that *omits* registration entirely produces a clone where **no MCP tool works and nothing says why**, because the working configuration lives in a file the repo doesn't contain.

**Rebuild implication**: treat server registration as an explicit **operator setup step**, documented in the deployment guide — not as a repo artifact, and not as deferred work. Part 5's `pyforge-atlas` server (Contract 10) has the same property.

### Contract 8: Part 5 internal — one PEP 420 namespace, five distributions

**Description**: `src/shared/packages/` holds five hatchling-built distributions that share a single **PEP 420 implicit namespace**, `pyforge`:

| dist | module | py | console script |
|---|---|---|---|
| `pyforge-warden` | `pyforge.warden` | ≥3.12 | `warden` |
| `pyforge-atlas` | `pyforge.atlas` | **≥3.14** | `pyforge-atlas` |
| `pyforge-herald` | `pyforge.herald` | ≥3.12 | `herald` |
| `pyforge-scribe` | `pyforge.scribe` | ≥3.12 | `scribe` |
| `pyforge-doctor` | `pyforge.doctor` | **≥3.14** | `doctor` |

**The contract is an absence**: **no distribution ships `src/pyforge/__init__.py`.** That is what lets any subset of the five be installed together — from conda, from PyPI, or from the workspace — and still resolve `pyforge.warden` alongside `pyforge.atlas`. Adding that file to any one distribution silently shadows the others' subpackages: an install-time failure with no import error, only missing modules.

**Workspace mechanics**: each dist carries its own `[package]` `pixi.toml` (making it a pixi workspace member) and **no `[workspace]` table**. The root `pixi.toml` `[workspace]` sets `preview = ["pixi-build"]` and deliberately has **no `members` key** — pixi through 0.72.2 has no such key; members are declared via **path dependencies**. A comment in `pixi.toml` records this explicitly, answering a review suggestion that proposed adding `members`.

**Rebuild implication**: assert the absence of `src/pyforge/__init__.py` in a test. It is the kind of invariant a well-meaning scaffolding tool will "helpfully" violate.

### Contract 9: Part 5 internal — extras-gated, one-directional package edges

**Description**: `pyforge-atlas` and `pyforge-doctor` each declare an optional-dependency group `gate = ["pyforge-warden"]`. **Nothing imports in reverse** — warden has no knowledge of atlas or doctor.

**Why one-directional and optional**: it keeps an external conda install of atlas or doctor **warden-optional**. A consumer who wants the pipeline but not the compliance gate installs the base dist and gets a working tool.

**The in-repo/on-disk divergence that matters**: in this repo, warden **is** default-installed at feature level for atlas (AC-8), so a developer always has the gate available. It is deliberately **not** a package run-dep. Those two facts look contradictory in a manifest diff and are not: the *env* provides it for development, the *package* declines to require it for distribution.

For `pyforge-doctor` the extra is **declared but not yet wired** — Doctor's consolidation of warden findings is designed, not implemented (its verbs are stubs; only `doctor --version` / `--help` work).

**Rebuild implication**: don't "simplify" by promoting the extra to a run-dep. That silently makes warden mandatory for every external consumer of atlas and doctor, which is the exact coupling this contract exists to prevent.

### Contract 10: Part 5 → Claude Code — a second, additive MCP server

**Description**: `pyforge-atlas` ships its own FastMCP server at `pyforge/atlas/mcp/server.py` with **11 `@mcp.tool()`** registrations:

- 7 pipeline runners: `run_core_pipeline`, `run_vcs_health_pipeline`, `run_pypi_intelligence_pipeline`, `run_vulnerability_pipeline`, `run_seed_gaps_pipeline`, `run_universal_sbom_pipeline`, `run_derived_artifacts_pipeline`
- 4 introspection/query: `read_atlas_dataset`, `list_atlas_pipelines`, `list_atlas_datasets`, `query_vizro_ai`

**This is separate from and additive to the legacy 46-tool server (Contract 3).** The two surfaces:
- expose **different** capabilities (recipe lifecycle + cf_atlas queries vs. Kedro pipeline execution + Parquet dataset reads)
- follow **different** internal patterns (subprocess wrappers over a foreign script tree vs. in-process calls into its own library)
- are registered **independently** by the operator (Contract 7b)

**Rebuild implication**: never quote a combined tool count, and never route a legacy tool through the new server or vice versa. The counts to state are "46 (legacy)" and "11 (pyforge-atlas)". Conflating them is the most likely documentation error in this area, which is why it is called out in three places.

### Contract 11: Part 4 internal — the active-project switch is marker **plus** symlinks

**Description**: selecting the active BMAD project requires **two** things to agree:

1. the `.active-project` marker file (`_bmad/custom/.active-project`), resolved by `_bmad/scripts/resolve_config.py` in priority order CLI flag > `BMAD_ACTIVE_PROJECT` env var > marker > none; and
2. two **gitignored symlinks**:
   ```
   _bmad-output/planning-artifacts       -> projects/<slug>/planning-artifacts
   _bmad-output/implementation-artifacts -> projects/<slug>/implementation-artifacts
   ```

**Why the symlinks are the load-bearing half**: `_bmad/bmm/config.yaml` hard-codes `planning_artifacts: "{project-root}/_bmad-output/planning-artifacts"`, and that key **does not compose** with a project's `output_folder` override. So **every BMAD skill that writes planning artifacts resolves through the symlinks**, not through the marker. The marker governs config layering; the symlinks govern where bytes land.

**The failure mode** is silent and cross-project: when the two disagree, a write-skill targets the *other* project. Live near-miss 2026-07-14 — symlinks on `pyforge-warden`, marker on `local-recipes`; a routine local-recipes doc re-sync would have overwritten pyforge-warden's PRD, epics and architecture.

**Mitigations, in order of strength**:
- Always switch via `scripts/bmad-switch <slug>` — since 2026-07-14 it re-points the symlinks **atomically and writes the marker last**, so a failed re-point cannot desync. Never hand-edit the marker.
- `scripts/bmad-switch --current` / `--list` warn on desync; heed the warning before any write-skill.
- **HARD rule (2026-07-25): parallel agents address projects by physical path and never call `scripts/bmad-switch`.** The marker+symlink pair is per-working-tree global state — a mutex nobody holds. Reading another project's artifacts never requires switching; read the path directly.

**Rebuild implication**: reproduce **both halves**, and reproduce the atomic ordering inside `bmad-switch`. A rebuild that ships only the marker will appear to work for one project and corrupt the second.

### Contract 12: Part 5 ↔ Part 2 — parallel reimplementation bound by parity, *not* a replacement

**Description**: `pyforge-atlas` reimplements Part 2's pipeline on Kedro/Dagster/Parquet. The v8.79.0 CHANGELOG states the relationship explicitly: it "is a parallel reimplementation, not a replacement of `conda_forge_atlas.py`… authored no conda recipes and changed no operational guidance." **The legacy pipeline remains authoritative.**

**Shape of the reimplementation**:
- **7 modular pipelines**: `core`, `pypi_intelligence`, `vulnerability`, `vcs_health`, `universal_sbom`, `seed_gaps`, `derived_artifacts` — a regrouping of the 22 executable phases, not a renumbering
- **Dagster is quarantined**: `orchestration/definitions.py` is the **only** module permitted to import `dagster` / `kedro_dagster` (AD-1 / AD-6)
- **Storage**: Parquet under `data/<layer>/<dataset>/`, read by **Ibis→DuckDB at query time** (AD-4, "Ibis → DuckDB ONLY"). **There is no persisted `.duckdb` file** — DuckDB is an engine over Parquet, never a store
- **Contracts**: `conf/base/catalog.yml` (800 lines)

**The binding artifact** is the `parity/` package — `frame_diff.py`, `evidence.py`, `legacy_surface.py` — plus **frozen per-node JSON parity fixtures**. This is the verification contract: the reimplementation is correct exactly insofar as its frames match the legacy pipeline's on the frozen fixtures. Parity is the gate for any future cutover; until then, two pipelines coexist by design.

**The contract deliberately NOT inherited** — and this is the most instructive line in the whole document. `conf/base/catalog.yml`'s header states that the legacy `_http.py` **global credential injection is "FIXED, not ported"**: no global injection exists in the reimplementation; a credential attaches **per-dataset**, only where the destination host requires it, and one dataset is annotated with `skip_auth` semantics so that **no credential is ever attached to that host**.

That is the direct architectural answer to Contract 5's `JFROG_API_KEY` cross-host leak — the defect that has been "deferred to v2" across several release lines. A working design now exists in-repo. Backporting it into `_http.py` is an implementation task, not a design task.

**Rebuild implication**: build both, and build the parity fixtures with them. A rebuild that ships only the reimplementation loses the verification contract *and* the legacy behaviour it is measured against; a rebuild that ships only the legacy pipeline loses the credential fix. Do not resolve the duplication by cutting over — the cutover criterion is parity, and parity is the artifact that decides.

---

## Cross-Cutting Concerns

### Pixi env contract

**18 envs in two families.** The isolation is itself a contract: it is what lets `pyforge-atlas` and `pyforge-doctor` require Python **≥3.14** while warden/herald/scribe require **≥3.12** and the factory runs 3.12 — three floors that no single solve could satisfy.

**Family 1 — 9 factory envs** (compose shared features; inherit the fat default `[dependencies]`):

| Env | Used by | Purpose |
|---|---|---|
| `local-recipes` (default) | Parts 1, 2, 3 (most operations) | Recipe lifecycle + atlas read/write + MCP server. Exposes **111** tasks (its own 106 + grayskull's 4 + conda-smithy's 1) |
| `vuln-db` | Parts 1, 2 (vuln-specific operations only) | AppThreat vdb-dependent work (Phase G/G', `scan_for_vulnerabilities`) |
| `grayskull` | Part 1 (`generate_recipe_from_pypi`) | grayskull for PyPI→conda recipe scaffolding |
| `conda-smithy` | Part 1 (lint + CI fidelity) | `conda-smithy recipe-lint` |
| `build` | Parts (build operations) | rattler-build via cross-platform features |
| `linux`, `osx`, `win` | Parts (per-platform builds) | Platform-specific build configurations |
| `gcloud` | Part 2 (Phase P BigQuery downloads) | gcloud SDK for `pypi.file_downloads` queries |

**Family 2 — 6 product envs**, every one `no-default-feature = true` (excludes the fat default `[dependencies]`: python 3.14 + pixi + conda + pip + uv):

| Env | Carries |
|---|---|
| `pyforge-warden` | built `pyforge-warden` + conda run-deps + pytest |
| `pyforge-atlas` | built `pyforge-atlas` (Kedro/Dagster) — the env `bmad-loop` worktrees materialize, never the fat `local-recipes` one |
| `pyforge-doctor` | built `pyforge-doctor` + jsonschema + pytest |
| `pyforge-scribe` | built `pyforge-scribe` + typer/pydantic + pytest |
| `pyforge-herald` | built `pyforge-herald` + mcp + pytest |
| `bmad-ui` | locally-built `bmad-dashboard` + `mybmad-dashboard` (consume-not-submit mirrors) |

**Failure mode — treat this as a contract, not a preference**: a cross-env dependency **union silently drops deps**. It has broken `main` **twice** — PRs #113 and #115 each restored dependencies a manifest union had dropped. There is no automated detector; manifest consolidation must be reviewed explicitly.

**Default env directive**: `# default-env: local-recipes` at the top of `[environments]` in `pixi.toml`. `scripts/load-env.sh` parses this and activates the named env.

### CI gates every PR must satisfy

The inherited staged-recipes linter (`.github/workflows/scripts/linter.py`) exits **1** on either of two conditions, and both must be pre-empted at PR-open time rather than diagnosed from red CI:

1. **Any file changed outside `recipes/`** — docs, `.github/`, `src/`, `scripts/`, `pixi.toml`, `_bmad-output/`, dashboards — unless the PR carries the **`maintenance` label**.
2. **`environment.yaml` out of sync with `pixi.toml`** — an exact `.rstrip()` string comparison against `pixi project export conda-environment -e build`. **This check is ungated by the label**: the `maintenance` label does not suppress it.

The workflow re-triggers on `labeled` / `unlabeled` for exactly this reason.

**Why this belongs in the integration doc**: it is a contract between the repo's *fork identity* and every part except Part 1. Any Part 4 or Part 5 change is outside `recipes/` by definition, and every Part 5 env change touches `pixi.toml` — so both gates fire on the normal working path. Recipe-only PRs need neither.

### Env-var inheritance from launch shell

Every part inherits env vars from the shell that launched Claude Code (or the pixi env). Critical env vars:

| Env var | Required for | Risk |
|---|---|---|
| `JFROG_API_KEY` | JFrog auth | **Cross-host leak** — see Contract 5 |
| `JFROG_USERNAME` / `JFROG_PASSWORD` | JFrog Basic auth (step 2) | Same blast radius as above when set |
| `GITHUB_TOKEN` / `GH_TOKEN` | GitHub auth (Part 1 `submit_pr`, Part 2 Phase K + N) | Lower risk; host-scoped to github.com by `_http.py` |
| 21 × `<HOST>_BASE_URL` overrides | Air-gap / internal mirrors | Required for offline operation; see `deployment-guide.md` |
| `REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE` | Enterprise CA bundle (SSL chain, not auth) | Highest-priority TLS trust source |
| `GEMINI_API_KEY` | Part 3 `gemini_server.py` | Only if Gemini bridge is used |
| `VDB_HOME` | Phases G + G' + scan_for_vulnerabilities | Set automatically by `vuln-db` env activation |
| `PHASE_F_SOURCE` / `PHASE_H_SOURCE` | Atlas backend selection | Defaults are sane (`auto` / `pypi-json`) |
| `BOOTSTRAP_<STEP>_TIMEOUT` | Atlas step timeouts | Override for cold `--fresh` runs |
| `BMAD_ACTIVE_PROJECT` | Part 4 active-project resolution (priority 2) | **Only half the switch** — does not move the symlinks (Contract 11) |
| `BMAD_LOOP_HOME_ROOT` | `bmad-loop` home location | Defaults to `~/.bmad-loops/<slug>`; long paths panic pixi-build-python 0.8.3 |

**Part 5 inherits none of the auth vars by design.** `pyforge-atlas` resolves credentials per-dataset from its Kedro catalog, so exporting `JFROG_API_KEY` into a Part 5 shell has no effect on its egress — a property worth knowing before debugging an "auth isn't applying" report.

### Permission gates (Claude Code)

`.claude/settings.json` (committed) declares the allow/deny lists for tools Claude Code can invoke. `.claude/settings.local.json` (gitignored) accumulates user-approved namespaced tools as they're invoked (e.g., `mcp__conda_forge_server__submit_pr`).

The permission UI applies to:
- Bash commands (with glob patterns)
- WebFetch (per-domain)
- MCP tools (per-namespace + per-tool) — **now spanning two servers** (Contracts 3 and 10), each approved independently
- Skill invocations

**What `.claude/settings.json` does NOT contain**: an `mcpServers` block. Server registration is user-level, in `~/.claude.json` (Contract 7b). The permission file governs *whether a tool may run*; it does not govern *whether the server exists*.

**Permission gates are part of the governance layer, not the execution layer.** Per the charter doctrine, Skills are the unit of execution while the deterministic harness — `bmad-loop`, the sandbox/permission gates, and the CI verify gates — is the unit of governance, and is deliberately **not** a skill. A rebuild that implements the harness *as* a skill collapses that separation and puts the hand that builds in charge of the gate that judges.

**Rebuild implication**: ship `.claude/settings.json` with a sensible default allow-list (the current one allows `Bash(curl *)`, `Bash(rattler-build *)`, `Bash(pixi run *)`, `Bash(git push)` without `--force`, etc.). Users will accumulate their own approvals in `.local.json`.

### Spec-surface governance

`scripts/spec_surface_check.py` enforces, over `git ls-files`:

- **coverage** — every tracked file matches ≥1 spec `surface:` glob (declared in `SPEC.md` frontmatter) **or** a reason-tagged entry in `scripts/spec_surface_allowlist.txt`. No silent exemptions; every allowlist entry is printed with its reason.
- **drift** — a governed file changed (vs. `scripts/.spec-surface-baseline.json`) while its spec's `.memlog.md` did not move: code drifting out from under its contract.

Specs are keyed **`<project>/<spec>`**, never the bare directory name — the same slug legitimately exists in two projects, and a bare-name key silently dropped one surface. Exits non-zero on any finding: "never false-green."

Live (2026-07-25): **22 specs · 7,888 tracked files · 6,323 governed · 1,567 allowlisted**.

**Why it is a cross-cutting concern and not a part**: it governs *all five parts* uniformly, and it is the only mechanism in the system that notices a file nobody claimed. Note the direct consequence for this document's own tier: adding a new file under `planning-artifacts/` that no spec surface claims is a HARD `uncovered` finding — new planning artifacts must land inside an existing governed surface, which is why this doc grew Contracts 8–12 rather than spawning a `part-5-architecture.md`.

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
6. cfa.init_schema(conn) — idempotent migration to v29.
7. cfa.run_single_phase("F", conn) →
       phase_f_downloads() reads PHASE_F_SOURCE env var →
       branches to _phase_f_via_api / _phase_f_via_s3 / _phase_f_via_auto →
       each branch routes outbound HTTP through _http.py (Contract 5) →
       writes rows to packages + package_version_downloads tables.
8. JSON result returned to subprocess; stdout printed to cron log.
```

Phase F doesn't touch BMAD, Part 1's recipe-lifecycle, or Part 3's MCP server. Same for the other 21 executable phases when run via `atlas-phase`.

### The same refresh, via Part 5 (parallel path)

```
1. `pixi run -e pyforge-atlas <pipeline task>`  — a LEAN env, no factory deps
2. Kedro resolves conf/base/catalog.yml (800 lines) for the pipeline's datasets.
3. Credentials attach PER DATASET, only where the destination host needs one.
       ✗ NO _http.py.  ✗ NO global JFROG_API_KEY injection ("FIXED, not ported").
       One dataset is annotated skip_auth: no credential ever reaches that host.
4. Nodes execute on the Dagster plane defined ONLY in
   orchestration/definitions.py (AD-1/AD-6).
5. Outputs land as Parquet under data/<layer>/<dataset>/.
       ✗ NOT .claude/data/conda-forge-expert/.  ✗ NO .duckdb file is written.
6. Reads go through Ibis → DuckDB at QUERY time (AD-4), via semantic/metrics.py.
7. parity/frame_diff.py compares the resulting frames against frozen per-node
   JSON fixtures captured from the legacy pipeline → parity evidence.
```

**Both paths run today, and that is the design** (Contract 12). Step 7 — not step 5 — is what makes the second path trustworthy. Note that steps 3 and 5 are each a *deliberate non-inheritance* of a factory contract; a reader who expects Contract 2 or Contract 5 to apply here will misdiagnose every credential and every output path.

### A Part 5 gate run (warden dogfooding itself)

```
1. `pixi run -e pyforge-warden warden <scan args>`
2. pyforge.warden analyzers produce findings across its axes.
3. Findings are serialized against the FROZEN schema:
       pyforge/warden/data/report-schema.json
       $id: urn:local-recipes:pyforge-warden:report-schema — title: ComplianceReport
4. verdict.py — the SOLE owner of the exit-code projection — maps the report
   to an exit code. Nothing else in the package may decide the verdict.
5. CI consumes the exit code as the gate.
```

The doctrine "the hand that builds is never the gate that judges" is realized here structurally: findings and verdict live in different modules, and the verdict module is single-owner. `pyforge-doctor` mirrors the shape exactly (`urn:local-recipes:pyforge-doctor:report-schema`, title `DoctorReport`, its own `verdict.py`) and its stated purpose is to consolidate pyforge-warden + cf_atlas signals into that one envelope — making it the clearest example of the cross-part contract pattern the whole system is built on.

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
| MCP server not registered in a fresh clone | Part 3 / Part 5 | **Correction**: this was recorded as "missing `.mcp.json` (deferred work)". Registration lives in `~/.claude.json` **by design** (Contract 7b); the failure mode is a clone with no server and no explanation. Fix by documenting operator setup, not by adding `.mcp.json` |
| `cf_atlas.db` schema older than **v29** | Parts reading the DB | `init_schema()` runs on every connection open and migrates additively; safe to call on stale DBs |
| `pypi_conda_map.json` stale (>7d) | Part 1 name resolution | `update_mapping_cache` MCP tool refreshes; TTL is informational, not enforced |
| Multiple BMAD projects writing to same artifacts | Part 4 multi-project | **Correction**: the marker alone does **not** resolve this — write-skills resolve through the two symlinks (Contract 11). Marker/symlink desync silently targets the *other* project (near-miss 2026-07-14). `bmad-switch` re-points atomically, marker last; parallel agents must use physical paths and never switch |
| Build's `build.pid` leaks (orphan process) | Part 3 trigger_build | Manual cleanup; `_active_build` reference is per-server-process only |
| Stray `src/pyforge/__init__.py` added to any dist | Part 5 internal (C8) | Silently shadows the other four dists' subpackages — missing modules, no import error. Assert the absence in a test |
| `gate` extra promoted to a run-dep | Part 5 internal (C9) | Makes `pyforge-warden` mandatory for every external consumer of atlas/doctor, destroying the warden-optional install. Review manifest "simplifications" |
| Cross-env dependency union drops deps | All parts → pixi | Has broken `main` twice (PRs #113, #115). No automated detector; explicit review of manifest consolidation is the only guard |
| The two MCP surfaces get conflated | Parts 3 + 5 | Documented as separate and additive (46 legacy + 11 atlas); never quote a combined count, never cross-route a tool |
| Parity fixtures rot while the legacy pipeline moves | Part 5 ↔ Part 2 (C12) | Frozen per-node fixtures diffed by `parity/frame_diff.py`; a legacy change that breaks parity is a finding, not a silent divergence |
| PR reds on the inherited staged-recipes linter | All parts → CI | Pre-empt at PR-open: `maintenance` label for any non-`recipes/` change; regenerate `environment.yaml` on any `pixi.toml` change (**ungated** by the label) |
| Story spec lost to worktree teardown | Part 4 → Tier 2 | Story specs are **durable/tracked**: promote from the run's gitignored `implementation-artifacts/` into `planning-artifacts/specs/` after merge. pyforge-warden lost 13 of 31 before this convention existed |
| Long loop-home paths panic pixi-build-python 0.8.3 | Part 4 harness | Loop homes at `~/.bmad-loops/<slug>`; `BMAD_LOOP_HOME_ROOT` overrides |

---

## Versioning Discipline Across Parts

| Part | Version source | Bump trigger |
|---|---|---|
| Part 1 (skill) | `CHANGELOG.md` TL;DR + `MANIFEST.yaml: version` (separate surfaces) | Semver: PATCH for fixes, MINOR for new gotchas/sections, MAJOR for breaking workflow changes. CHANGELOG bumps on every release; MANIFEST bumps only on portability protocol changes (currently **v7.0.0**; release is **v8.79.1**). |
| Part 2 (cf_atlas) | `SCHEMA_VERSION` constant in `conda_forge_atlas.py` (line 139) + CHANGELOG of skill | Schema version increments on every additive migration. Currently **v29**. |
| Part 3 (MCP server) | No explicit version — implied by Part 1's CHANGELOG | If MCP tool signature changes, treat as Part 1 MINOR bump. |
| Part 4 (BMAD) | `_bmad/bmm/config.yaml` header (Generated by BMAD installer Version: **6.10.0**) | Set by BMAD installer; bump via `bmad-method` package upgrade. |
| **Part 5 (products)** | **Five independent** `pyproject.toml: version` surfaces, one per dist | Product semver, decoupled from the skill release line. A skill release does **not** imply a product release, or vice versa. |
| **Part 5 (report schemas)** | `$id`-carrying `report-schema.json` per product (`urn:local-recipes:pyforge-{warden,doctor}:report-schema`) | **Frozen contracts.** Any change is consumer-visible; the `$id` is the compatibility handle, so a breaking change needs a new one, not an edit. |
| **Part 5 (parity fixtures)** | Frozen per-node JSON fixtures under `pyforge-atlas`' `parity/` scope | Re-captured only when the legacy pipeline's behaviour intentionally changes — otherwise a diff is a **finding**, not a refresh trigger (Contract 12). |

**Six version surfaces now, not four**, and they intentionally do not move together. The rebuild trap is assuming one release line: bumping the skill does not release the products, and shipping a product does not invalidate the atlas schema.

**Project-context drift contract**: `_bmad-output/projects/local-recipes/project-context.md` carries a drift-detection rule (its "Humans" sync note) keyed to a `last_synced_skill_version` MINOR pin. When Part 1's CHANGELOG ships a new MINOR (currently **v8.79.1**), the contract signals re-sync of the volatile sections is needed.

**Spec drift contract** (stronger, and automated): `scripts/spec_surface_check.py` fails when a governed file changes while its spec's `.memlog.md` stays still. Unlike the project-context pin — which *signals* — this one **exits non-zero**, making it the only enforced versioning discipline in the system.

---

## What a Rebuild Must Reproduce Faithfully

If any of these break, the system silently degrades:

1. **The shared `scripts/` directory** (Contract 1) — Parts 1 + 2 live together. Don't separate. (This binds the *legacy* atlas only; it is not an argument against Part 5.)
2. **The shared data directory** (Contract 2) — `.claude/data/conda-forge-expert/` is the single source of mutable state **for Parts 1–3**. Part 5 does not use it.
3. **The thin-wrapper subprocess pattern** (Contract 3) — the legacy server's tools shell out to Part 1's `scripts/`. Don't inline.
4. **CLAUDE.md Rules 1 + 2** (Contract 4) — without these, BMAD-CFE coordination is anarchy. Now joined by CI-gate pre-emption and story-spec promotion.
5. **`_http.py` as the only outbound HTTP path for Parts 1–3** (Contract 5) — including the JFROG_API_KEY mitigation discipline, and the correct **Bearer** scheme for GitHub.
6. **The `vuln-db` env separation** (Contract 6) — don't bundle AppThreat into the default env.
7. **Out-of-band state files at repo root** (Contract 7) — `build_summary.json` + `build.pid`. (Or migrate the convention atomically.)
7b. **MCP registration as an operator step, not a repo artifact** (Contract 7b) — `~/.claude.json`, stdio; no `.mcp.json`.
8. **The absent `src/pyforge/__init__.py`** (Contract 8) — a PEP 420 namespace defined by a file that must not exist. Assert it.
9. **One-directional, extras-gated package edges** (Contract 9) — `gate = ["pyforge-warden"]` stays an extra, never a run-dep.
10. **Two MCP surfaces, additive and separate** (Contract 10) — 46 legacy + 11 atlas. Never merged, never combined in a count.
11. **Marker *and* symlinks for the active project** (Contract 11) — both halves, atomic ordering, and physical paths for parallel agents.
12. **Parity, not cutover** (Contract 12) — `parity/` fixtures bind the reimplementation to the legacy pipeline; and the credential fix (`_http.py` global injection "FIXED, not ported") must survive the rebuild.

Plus the cross-cutting items (19 pixi envs in two families, env-var inheritance, permission gates, CI gates, spec-surface governance) are setup conditions, not contracts per se, but the rebuild must establish them before any part can function.

**The one-line summary of what changed**: a rebuild that reproduces Contracts 1–7 faithfully now produces only the *factory*. The product line is reproduced by honouring what Part 5 refuses to share — and four of the five new contracts are exactly that refusal.

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
           │  + promote the story spec into        │ durable, NOT Tier-3
           │    planning-artifacts/specs/ (tracked)│
           └──────────────────────────────────────┘
```

This is the canonical flow **for factory work**, and every other factory workflow (atlas refresh, vulnerability scan, project documentation) is a subset of it.

**It is not the canonical flow for Part 5.** A product story runs the other shape entirely:

```
        Dream (docs/dreams/*.md, Tier 0)
                    │  BMAD distils
                    ▼
        Spec (Tier 2, planning-artifacts/) — Why · Capabilities ·
              Constraints · Non-goals · Success signal
                    │  derived from an append-only .memlog.md,
                    │  RE-RENDERED, never hand-patched
                    ▼
        bmad-loop: DEV → VERIFY → REVIEW → VERIFY → COMMIT
              fresh tmux session per stage, worktree isolation,
              `--frozen` verify commands, squash merge
              home: ~/.bmad-loops/<slug>
                    │
                    ▼
        pixi run -e pyforge-<product> …   (lean env, no factory deps)
                    │
                    ▼
        gate: verdict.py → exit code   |   spec_surface_check.py → coverage+drift
                    │
                    ▼
        merge → PROMOTE the story spec into planning-artifacts/specs/ (tracked)
```

Two things distinguish it. First, no `conda-forge-expert` invocation and no Rule-2 CFE retro — Part 5 work touches no recipe, so Rules 1 and 2 do not fire (they fire only when a story touches conda-forge work, which for Part 5 is the exception, not the rule). Second, the governing artifact is a **Spec**, and the harness — not a skill — is what enforces the loop. Skills execute; the harness governs; and per doctrine the harness is deliberately not itself a skill.
