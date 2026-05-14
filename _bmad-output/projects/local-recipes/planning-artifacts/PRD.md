---
doc_type: prd
project_name: local-recipes
date: 2026-05-12
version: '1.2.0'
status: approved
tentative_decisions_applied: 2026-05-12
decisions_confirmed: 2026-05-12
source_pin: 'conda-forge-expert v8.0.0'
re_validated: 2026-05-13
input_docs:
  - planning-artifacts/index.md
  - planning-artifacts/project-overview.md
  - planning-artifacts/integration-architecture.md
  - project-context.md
edit_history:
  - { date: '2026-05-13', via: 'bmad-edit-prd', delta: 'v7.8.1 → v7.9.0 sync after actionable-scope audit (docs/specs/atlas-pypi-universe-split.md): schema v19 → v20, +pypi_universe side table, +pypi-only-candidates CLI/MCP, +Phase D split. PATCH bump (no FR/NFR scope shift; count-and-pin sync).' }
  - { date: '2026-05-13', via: 'bmad-correct-course', delta: 'v7.9.0 → v8.0.0 sync after structural-enforcement + persona-profile bundle (docs/specs/conda-forge-expert-v8.0.md): schema v20 → v21, +v_actionable_packages view, +Phase H serial-aware eligible-rows gate (pypi_version_serial_at_fetch column), +bootstrap-data --profile {maintainer,admin,consumer} with gh-user / phase-L-sources auto-detection, +tests/meta/test_actionable_scope.py, 5 catalog rows 📋 → ✅. Wave C (drop vuln_total) DEFERRED — 4 consumers found, retro-atlas-pypi-universe-split-2026-05-13.md corrected. MINOR bump (no FR/NFR scope shift; new persona-aware UX surface counts as feature-level addition, no breaking PRD-level change — backward-compatible CLI flag).' }
---

# Product Requirements Document: `local-recipes` Rebuild

> **Rebuild target:** the AI-assisted, semi-autonomous conda-forge packaging factory + offline-tolerant package-intelligence layer + 35-tool MCP API + BMAD multi-project planning infrastructure. **Not the 1,415 existing recipes** — those are outputs.

---

## 1. Vision

**An AI agent — given an empty repo, pixi, and Claude Code — can stand up the full `local-recipes` system (Parts 1-4) and produce conda-forge-ready recipes on first authoring, in any network environment from open-internet to fully air-gapped.**

The rebuild target is the **factory**, not its outputs. A successful rebuild reproduces the four parts faithfully enough that the next conda-forge recipe authored by the system passes review on first land — same as today.

---

## 2. Background & Context

### Why rebuild?

This PRD does not assume a destruction event. The rebuild target supports:

1. **Bootstrapping a clean fork** for an organization that wants the system but cannot accept this repo's full git history (license/audit reasons).
2. **Internal proliferation** — replicating the pattern into adjacent repos (`presenton-pixi-image`, `deckcraft`, etc.) without copy-pasting the skill files.
3. **Disaster-recovery readiness** — a documented architecture is a recoverable architecture.
4. **Onboarding clarity** — new contributors should understand the system from documents, not by reading 4,300 lines of `conda_forge_atlas.py`.

### What's in scope

| In scope | Out of scope |
|---|---|
| Pixi monorepo scaffolding (8 envs, ~50 tasks) | The 1,415 recipes under `recipes/` |
| conda-forge-expert skill (Part 1, ~42 scripts + docs) | Recipe-specific upstream patches |
| cf_atlas data pipeline (Part 2, 17 phases, schema v20) | Historical CHANGELOG entries (only TL;DR + structure) |
| FastMCP server (Part 3, 36 tools) | Auxiliary `gemini_server.py` (optional) |
| BMAD installer (Part 4, 65 skills, multi-project) | Personal `.envrc` files, IDE-specific config |
| Enterprise/air-gap layer (`_http.py`, JFrog) | Production JFrog mirror setup (operator's problem) |
| Tests (41 files + meta-tests for invariants) | Recipe corpus tests (covered by conda-forge CI) |
| Documentation (SKILL.md, reference, guides, quickref) | This repo's existing `docs/specs/` (preserved as inputs, not rebuilt) |

---

## 3. Users & Jobs-to-be-Done

### Primary users

#### U1: Maintainer (rxm7706 today, future operators)

**JTBD-1.1**: "Author a new conda-forge recipe with confidence that it will pass review on first land."
- Today: 10-step autonomous loop in Claude Code via `conda-forge-expert` skill.
- Success: ≤15 min from `pixi run generate-recipe -- <pkg>` to `pixi run submit-pr -- <pkg>` for a noarch:python package; no review revisions on first PR.

**JTBD-1.2**: "Diagnose why a build failed without reading 4,000 lines of rattler-build output."
- Today: `analyze_build_failure` MCP tool + `guides/ci-troubleshooting.md`.
- Success: failure cause identified in ≤3 min; root-cause fix applied via `edit_recipe`.

**JTBD-1.3**: "Find which of my feedstocks have new upstream releases."
- Today: `behind-upstream` / `staleness-report` CLIs querying cf_atlas.db.
- Success: weekly cron produces a triage list; no per-feedstock manual checks.

**JTBD-1.4**: "Plan a multi-recipe feature with BMAD without losing track of conda-forge constraints."
- Today: BMAD↔CFE integration rules in CLAUDE.md (mandatory skill invocation + retro).
- Success: BMAD-driven story-spec implementations produce conda-forge-ready recipes; no late-stage "wait, this violates STD-001" surprises.

#### U2: Enterprise operator (air-gap / JFrog admin)

**JTBD-2.1**: "Stand up `local-recipes` inside an air-gapped enterprise without modifying the codebase."
- Today: `.pixi/config.toml` + `*_BASE_URL` env vars + JFrog mirrors.
- Success: full atlas build runs without touching `pypi.org`, `api.anaconda.org`, or AWS S3 directly; only JFrog endpoints.

**JTBD-2.2**: "Operate without leaking credentials to unintended hosts."
- Today: subshell pattern + per-shell `JFROG_API_KEY` discipline.
- Success: zero `X-JFrog-Art-Api` headers in non-JFrog access logs (verified by audit).

#### U3: AI agent (Claude Code or BMAD agent)

**JTBD-3.1**: "On first activation in a conda-forge task, find the constraints and tools I need without re-reading the entire codebase."
- Today: SKILL.md + project-context.md + INDEX.md cascade.
- Success: a Claude Code agent reads ≤3 files before producing a first-pass recipe.

**JTBD-3.2**: "After completing a recipe authoring effort, update the skill with novel findings."
- Today: Rule 2 retro mandate in CLAUDE.md.
- Success: skill version bumps appropriately; CHANGELOG TL;DR reflects every closed effort.

### Secondary users

#### U4: Downstream conda-forge reviewers

JTBD-4.1: Review recipes produced by `local-recipes` without paying a complexity tax. Success: PR descriptions explain non-obvious decisions; recipes pass lint clean.

#### U5: Future contributor (human or agent) to `local-recipes` itself

JTBD-5.1: Add a new MCP tool / pipeline phase / skill reference without breaking invariants. Success: meta-tests catch three-place-rule violations; CHANGELOG entry is written by the contributor, not requested by reviewer.

---

## 4. Goals & Non-Goals

### Goals

| ID | Goal | Measurable outcome |
|---|---|---|
| G1 | **Faithful rebuild of Parts 1-4** | All 36 MCP tools functional; all 17 atlas phases run; bmad-switch + 6-layer merge work; 64 real skills load (42 BMAD + 21 engineering + 1 CFE; the legacy stray `.claude/skills/data/` dir is not recreated) |
| G2 | **First-pass recipe authoring success rate ≥90%** | First-pass conda-forge PR acceptance (no review-comment revisions on lint/policy issues) ≥9 of 10 recent recipes |
| G3 | **Atlas refresh resilient to interrupts** | Mid-run kill of `bootstrap-data --fresh` resumes cleanly via `phase_state` cursor + TTL gates; ≤5% rework |
| G4 | **Air-gap operation parity** | Full atlas build + recipe authoring + PR submission run with all `*_BASE_URL` set to JFrog endpoints + `JFROG_API_KEY` correctly scoped; zero cross-host leak |
| G5 | **MCP server availability ≥99% during a Claude Code session** | Server auto-starts at session boot; tool calls fail gracefully on script error without crashing the server |
| G6 | **Drift-detection contract enforces re-sync discipline** | When skill CHANGELOG ships a new MINOR, `last_synced_skill_version` pin signals re-sync; project-context.md and PRD/architecture re-verified within 1 week |
| G7 | **BMAD multi-project hygiene** | `scripts/bmad-switch --current` accurate; per-project `.bmad-config.toml` overlays apply; no cross-project artifact pollution |

### Non-goals

| ID | Non-goal | Rationale |
|---|---|---|
| NG1 | Rebuild the 1,415 recipes | Recipes are outputs of the system, not part of it |
| NG2 | Match the existing repo's git history | History is not architecturally significant |
| NG3 | Support conda-build as a parallel build engine | Pixi + rattler-build is the chosen path; conda-build is migration-only |
| NG4 | Implement an enterprise admin UI | CLI + Claude Code is the surface; no web UI |
| NG5 | Match every PATCH-level CHANGELOG entry verbatim | Rebuild tracks MINOR-level functional parity; PATCH fixes accrue post-rebuild via normal retro discipline |
| NG6 | Implement the `.mcp.json` deferred work | Current path-convention discovery is sufficient; explicit registration is a v2 enhancement |
| NG7 | Implement the `_http.py` host-aware refactor | Mitigation patterns (subshell scoping) are documented; architectural fix is a v2 enhancement |

---

## 5. Features

Features are organized by Part. Each feature has an ID, priority (P0 = must-ship, P1 = should-ship, P2 = nice-to-have), and a one-line acceptance description.

### Part 1: conda-forge-expert skill (15 features)

| ID | Feature | Priority | Acceptance |
|---|---|---|---|
| F1.1 | 3-tier directory architecture | P0 | `scripts/` + `.claude/scripts/.../conda-forge-expert/` + `.claude/data/conda-forge-expert/` directories exist with the discipline enforced by `tests/meta/test_all_scripts_runnable.py` |
| F1.2 | 10-step autonomous loop in SKILL.md | P0 | SKILL.md § "Primary Workflow: The Autonomous Loop" enumerates 10 ordered steps with step 8b as the human gate |
| F1.3 | 5 Critical Constraints | P0 | SKILL.md § "Critical Constraints" enumerates: never-mix-formats, stdlib-required, python-min, PyPI-url-pattern, build.bat-call-prefix |
| F1.4 | 42 Tier 1 canonical scripts | P0 | All 42 scripts in `scripts/` accept `--json` and emit valid JSON on stdout |
| F1.5 | 34 Tier 2 CLI wrappers + pixi tasks | P0 | All 34 wrappers in `.claude/scripts/conda-forge-expert/` delegate to Tier 1 via subprocess; each has a matching pixi task |
| F1.6 | 17-lint-code recipe optimizer | P0 | `optimize_recipe` flags STD-001 through OPT-NNN with structured output |
| F1.7 | 6 Recipe Authoring Gotchas (G1-G6) | P0 | SKILL.md § "Recipe Authoring Gotchas" enumerates G1-G6 with cause + fix |
| F1.8 | 41 recipe templates across 13 ecosystems | P0 | `templates/` contains v1 + v0 variants for python, rust, go, c-cpp, r, java, ruby, dotnet, fortran, multi-output, nodejs, perl + conda-forge-yml config-template; verified 41 files (39 `.yaml` + 2 `.yml`) / 13 dirs at 2026-05-12 |
| F1.9 | 11 reference docs + 8 guides + 2 quickrefs | P0 | All documentation files exist with content; `INDEX.md` task→tool navigator points correctly |
| F1.10 | `MANIFEST.yaml` + `install.py` portability | P1 | The skill can be moved to another repo and `install.py` bootstraps the wrappers + pixi tasks |
| F1.11 | Build failure protocol | P0 | SKILL.md § "Build Failure Protocol" enumerates stop/preserve/analyze/root-cause/apply/retry with 3-cycle escalation |
| F1.12 | Migration protocol (v0 → v1) | P0 | `migrate_to_v1` uses feedrattler; "strangler pattern" — migrate-in-same-PR-as-touch |
| F1.13 | Mapping subsystem (PyPI ↔ conda) | P0 | `pypi_conda_mappings/` (current) + `mappings/` (legacy) coexist; `name_resolver.py` uses both |
| F1.14 | 41 tests (unit + integration + meta) | P0 | `pixi run test` passes offline subset; `pixi run test-all` passes full suite (meta-tests enforce three-place rule + schema-header invariant) |
| F1.15 | CHANGELOG.md with TL;DR | P0 | TL;DR section reflects the current MINOR/PATCH version; older entries chronological |

### Part 2: cf_atlas data pipeline (12 features)

| ID | Feature | Priority | Acceptance |
|---|---|---|---|
| F2.1 | SQLite schema v20 with 12 tables (incl. `pypi_universe` side table separating PyPI directory from working set) | P0 | `init_schema()` creates packages + 11 supporting tables; SCHEMA_VERSION constant matches; v19→v20 migration moves `relationship='pypi_only'` rows from `packages` to `pypi_universe` idempotently |
| F2.2 | 17 phases (B → N) via PHASES registry | P0 | `conda_forge_atlas.py:PHASES` list matches the 17-tuple order; case-insensitive `get_phase()` works |
| F2.3 | `bootstrap-data` orchestrator | P0 | `--fresh`, `--resume`, `--status`, `--no-vdb`, `--no-cf-atlas`, `--phase-h-source` flags; per-step timeouts via `BOOTSTRAP_<STEP>_TIMEOUT` |
| F2.4 | `atlas-phase <ID>` single-phase CLI | P0 | `--reset-ttl`, `--list`; supports B/B.5/B.6/C/C.5/D/E/E.5/F/G/G'/H/J/K/L/M/N |
| F2.5 | TTL gates on F/G/H/K phases | P0 | Scoped `UPDATE packages SET *_fetched_at = NULL` predicates match phase eligibility; tested by `test_atlas_phase_reset_ttl.py` |
| F2.6 | `phase_state` checkpointing on B/D/N | P0 | Cursor stored + read; status enum (in_progress/completed/failed); resume skips items ≤ cursor |
| F2.7 | Phase F S3 parquet backend | P0 | `PHASE_F_SOURCE=auto\|anaconda-api\|s3-parquet`; auto path probes api.anaconda.org, falls through |
| F2.8 | Phase H cf-graph offline backend | P0 | `PHASE_H_SOURCE=pypi-json\|cf-graph`; `--fresh` defaults to cf-graph for fast cold-start |
| F2.9 | 60s progress heartbeat + capped cadence | P0 | `progress_every = min(max(N, len // 40), 2500)` + 60s wall-clock heartbeat closes "Phase H hangs" UX bug |
| F2.10 | 17 public CLIs (orchestration + 15 query) | P0 | All have Tier 2 wrappers + pixi tasks; all read-side CLIs offline-safe |
| F2.11 | Phase G/G' require `vuln-db` env | P0 | Phases short-circuit cleanly if `vuln-db` not active; `VDB_HOME` env var auto-set by env activation |
| F2.12 | Idempotent additive schema migrations | P0 | `init_schema()` on a stale DB migrates to v19 without data loss |

### Part 3: FastMCP server (8 features)

| ID | Feature | Priority | Acceptance |
|---|---|---|---|
| F3.1 | `conda_forge_server.py` with `FastMCP("conda-forge-expert")` | P0 | Server starts via stdio transport; registers as `conda-forge-expert` |
| F3.2 | 36 `@mcp.tool()` registrations (incl. `pypi_only_candidates` added in v7.9.0; v8.0.0 surface is unchanged — persona profiles are CLI-only) | P0 | All 36 tools enumerated in `architecture-mcp-server.md` § "The Tools by Surface" are present and functional |
| F3.3 | Thin-subprocess wrapper pattern | P0 | Every tool body is ≤30 lines; delegates via `_run_script(SCRIPT_PATH, args)` |
| F3.4 | `_run_script` helper with 3-tier error handling | P0 | Handles FileNotFoundError, JSONDecodeError, TimeoutExpired; returns structured error dict |
| F3.5 | 2 async tools (`trigger_build`, `update_cve_database`) | P0 | Async tools use `Context` for progress reporting; fire-and-forget pattern for builds |
| F3.6 | Out-of-band state files (`build_summary.json`, `build.pid`) | P0 | Files at repo root; tolerated when absent |
| F3.7 | `mcp_call.py` JSON-RPC client | P1 | Allows shell-side tool invocation outside Claude Code; 300s timeout |
| F3.8 | `gemini_server.py` auxiliary | P2 | Gemini API bridge; requires `GEMINI_API_KEY`; not required for primary flow |

### Part 4: BMAD infrastructure (10 features)

| ID | Feature | Priority | Acceptance |
|---|---|---|---|
| F4.1 | BMAD-METHOD v6.6.0 installer | P0 | `_bmad/` directory with `config.toml` + `config.user.toml` + `bmm/` + `core/` + `scripts/` |
| F4.2 | 6-layer config merge | P0 | `resolve_config.py` merges layers 1-6 in priority order; verified by per-layer override tests |
| F4.3 | Active-project resolution (4 priorities) | P0 | `--project <slug>` > `BMAD_ACTIVE_PROJECT` env > `_bmad/custom/.active-project` > none |
| F4.4 | `scripts/bmad-switch` CLI | P0 | `--list`, `--current`, `--clear`, `<slug>` all work; slug validation rejects bad inputs |
| F4.5 | 64 real skills (target) / 65 entries in current repo | P0 | **42 BMAD-installer** (6 personas + 9 planning + 3 discovery + 3 research + 2 implementation + 4 sprint/retro + 5 review + 10 process/facilitation) + **21 engineering-practice** (separate from installer) + **1 repo-specific** (`conda-forge-expert`) = **64 real skills**. Current repo state shows 65 because `.claude/skills/data/` is a stray directory (no SKILL.md inside, contains old `conda-forge-expert/` subdir); the rebuild does NOT recreate this stray. All loadable via `Skill` tool. |
| F4.6 | `conda-forge-expert` repo-specific skill | P0 | Lives at `.claude/skills/conda-forge-expert/`; Parts 1-3 reference it |
| F4.7 | Per-skill customization layer | P1 | `_bmad/custom/<skill>.toml` files merge with skill's `customize.toml` via `resolve_customization.py` |
| F4.8 | Multi-project directory layout | P0 | `_bmad-output/projects/<slug>/` with `planning-artifacts/` + `implementation-artifacts/` per project |
| F4.9 | CLAUDE.md BMAD↔CFE integration rules | P0 | Rule 1 (mandate skill invocation) + Rule 2 (mandate retro closeout) codified verbatim |
| F4.10 | `project-context.md` with drift-detection contract | P0 | Foundational rules + `last_synced_skill_version` MINOR pin + `(Sync: ...)` tags per section |

### Cross-cutting features (7 features)

| ID | Feature | Priority | Acceptance |
|---|---|---|---|
| FX.1 | `_http.py` auth chain (truststore + JFrog + GitHub + .netrc) | P0 | Single source of outbound HTTP for all parts; per-host `*_BASE_URL` overrides functional |
| FX.2 | 8 pixi envs | P0 | `linux`, `osx`, `win`, `build`, `grayskull`, `conda-smithy`, `local-recipes` (default), `vuln-db` |
| FX.3 | JFROG_API_KEY cross-host leak mitigation docs | P0 | Documented in CLAUDE.md + project-context.md + docs/enterprise-deployment.md + deployment-guide.md |
| FX.4 | `vuln-db` env separation | P0 | AppThreat vdb deps NOT in default env; activation hook sets `VDB_HOME` |
| FX.5 | `docs/pixi-config-jfrog.example.toml` starter | P1 | Drop-in `.pixi/config.toml` template for JFrog deployments |
| FX.6 | Permission gate config (`.claude/settings.json`) | P0 | Sensible default allow-list; per-namespace MCP tool permissions; `--force` push denied |
| FX.7 | `build-locally.py` Docker wrapper | P0 | Linux builds run in Docker; osx/win run on host; cross-compile via SDKs/ |

**Total features: 52** across the 4 parts + cross-cutting.

---

## 6. Success Metrics

Quantitative measures that determine rebuild success. Measured post-deploy on a fresh installation.

### Functional parity metrics

| Metric | Target | How measured |
|---|---|---|
| MCP tools functional | 35 / 35 | `mcp_call.py <tool>` returns valid JSON for each |
| Atlas phases run to completion | 17 / 17 | `atlas-phase <ID>` exits 0 for each on a non-fresh DB |
| Pixi envs build cleanly | 8 / 8 | `pixi install -e <env>` succeeds for each |
| Skills load via Skill tool | 65 / 65 | Each skill activatable via `Skill:` invocation |
| BMAD active projects | 3 / 3 | `scripts/bmad-switch --list` lists local-recipes, deckcraft, presenton-pixi-image |

### Performance metrics

| Metric | Target | Note |
|---|---|---|
| `bootstrap-data --fresh` cold time (auto-mode) | ≤90 min | Was 30-45 min in production; rebuild can budget 2x slack |
| `bootstrap-data --resume` warm time (TTL gates active) | ≤45 min | Same as production |
| `atlas-phase F` (S3 parquet, warm) | ≤30 sec | Parquet cache hit |
| `atlas-phase H` (cf-graph, cold) | ≤60 sec | Bulk local file scan |
| Single MCP tool call overhead (subprocess) | ≤500 ms | Includes Python startup + script import + JSON encode |
| `pixi run validate -- recipes/<pkg>` | ≤5 sec | rattler-build --render + schema validation |

### Quality metrics

| Metric | Target | Note |
|---|---|---|
| Test suite pass rate (`pixi run test`) | 100% | Offline subset, deterministic |
| Test suite pass rate (`pixi run test-all`) | ≥98% | Full suite incl. network/slow; allows transient network failures |
| Meta-test enforcement (`test_all_scripts_runnable.py`) | 100% | Every Tier 1 script accounted for |
| First-pass conda-forge PR acceptance | ≥90% | Recipes authored by the rebuilt system pass review on first land |

### Air-gap metrics

| Metric | Target |
|---|---|
| Full atlas build with `JFROG_API_KEY` unset | Pass |
| Full atlas build with `*_BASE_URL` set to JFrog endpoints | Pass |
| Zero `X-JFrog-Art-Api` headers in non-JFrog access logs (operator audit) | Pass |
| Recipe submission with `JFROG_API_KEY` scoped to subshell | Pass |

---

## 7. Constraints & Assumptions

### Technical constraints

| ID | Constraint | Rationale |
|---|---|---|
| C1 | **Pixi 0.67.2+** as the only env manager | No conda, no venv, no manual env setup |
| C2 | **Python 3.11+** | `_bmad/scripts/*.py` use stdlib `tomllib` (3.11+) |
| C3 | **rattler-build, not conda-build** | Modern build engine; v0 conda-build is migration-only |
| C4 | **v1 `recipe.yaml`, not v0 `meta.yaml`** | All new recipes; v0 is migration source only |
| C5 | **SQLite (WAL mode)** for cf_atlas.db | Single-file portability; concurrent reads; no DB server |
| C6 | **FastMCP** for MCP server | Python-native; auto-discovery by Claude Code |
| C7 | **BMAD-METHOD v6.6.0+** | Multi-project layout requires v6.6 |
| C8 | **No public-host hard dependencies** (atlas pipeline) | Air-gap support via S3 parquet + cf-graph backends |
| C9 | **All HTTP through `_http.py`** | Single auth chain; consistent JFROG/GitHub/.netrc handling |

### Business / operational constraints

| ID | Constraint | Rationale |
|---|---|---|
| C10 | **BSD-3-Clause license** | Compatible with conda-forge ecosystem |
| C11 | **`rxm7706` as default maintainer** | The current operator's identity |
| C12 | **Five target platforms** | linux-64 + linux-aarch64 + osx-64 + osx-arm64 + win-64 (matches conda-forge expectations) |
| C13 | **Drift-detection contract is non-negotiable** | `last_synced_skill_version` MINOR pin is the rebuild's correctness backstop |

### Assumptions

| ID | Assumption | Risk if false |
|---|---|---|
| A1 | Operator has Docker available for Linux builds | High — `recipe-build-docker` task can't run; must use `recipe-build` directly on host |
| A2 | Operator has `gh` CLI installed and authenticated | High — `submit_pr` / `prepare_pr` fail; rebuilt system unusable for PRs |
| A3 | Claude Code is the primary execution surface | Medium — for shell-only operators, `mcp_call.py` is the fallback; BMAD workflows still need Claude Code |
| A4 | JFrog Artifactory has Conda + PyPI Remote Repositories configured (for air-gap deployments) | Medium — operator must configure mirrors; pre-rebuild blocker if mirrors don't exist |
| A5 | `github.com` is reachable (or proxied) for cf-graph tarball | Low — Phase H fallback to pypi-json path if github.com unreachable |
| A6 | Operator does not commit `JFROG_API_KEY` to `~/.bashrc` | Critical — cross-host leak guaranteed if true; doc warning is the only mitigation |

---

## 8. Open Questions → Confirmed Decisions

The 7 open questions below are **CONFIRMED by operator (rxm7706) 2026-05-12**, with the recommended outcome accepted in each case. PRD status flips to `approved`. Sprint planning is unblocked across all 5 waves.

History: tentatively resolved 2026-05-12 → operator-confirmed 2026-05-12 (same day, single review pass).

### Q-PRD-01 (Part 3, P1) → TENTATIVE: include `.mcp.json` in v1

**Should the rebuild include `.mcp.json` registration for the MCP server?**

- **Pros**: portable across Claude Code installations; explicit; survives Claude Code version changes
- **Cons**: extra file to maintain; current path-convention discovery works
- **Recommendation**: include in v1 rebuild; the cost is minimal and the operator benefit (no surprises in fresh installs) is high
- **Source**: deferred per `docs/specs/claude-team-memory.md` Q13

**✅ CONFIRMED DECISION (2026-05-12, operator-approved): ACCEPTED — include `.mcp.json` in v1.**
- **Story confirmed**: E10.S9 (Author `.mcp.json` registration) stands as written.
- **Operator override**: If you change this to "defer", move E10.S9 to deferred work (DW11) and update the readiness report.

### Q-PRD-02 (cross-cutting, P0) → TENTATIVE: carry forward; refactor in v2

**Should `_http.py` be refactored to be host-aware in the rebuild, or carry forward the cross-host leak as a documented constraint?**

- **Pros (refactor now)**: architecturally eliminates the security risk
- **Cons**: substantially more complex `_http.py`; requires per-host policy tables; risk of breaking some currently-working flows
- **Recommendation**: carry forward as documented constraint in v1; refactor in v2. Justification: mitigation patterns are well-documented in 3 places; refactor scope is large enough to warrant its own design pass
- **Source**: deferred per auto-memory `project_http_jfrog_unconditional_injection.md`

**✅ CONFIRMED DECISION (2026-05-12, operator-approved): ACCEPTED — defer host-aware refactor to v2.**
- **No story changes**: DW2 (in §9) covers the v2 work; v1 ships with documentation-based mitigation.
- **Risk acknowledged**: PRD R8 (operator hygiene as security boundary) explicitly accepts this trade-off.
- **Operator override**: If you decide to refactor in v1, add a new epic (Epic 3.5 between current Epic 3 and Epic 4) with ~6-8 stories covering host-allow-list policy tables + per-host-config + unit tests. Estimate: 1-2 sprint-weeks.

### Q-PRD-03 (Part 1, P2) → TENTATIVE: promote G6 to SKILL.md

**Should the rebuild promote G6 (`get_build_summary` false negatives) from CHANGELOG v7.7.1 to SKILL.md § "Recipe Authoring Gotchas"?**

- **Pros**: closes a known doc drift; agents reading SKILL.md first will see the warning
- **Cons**: SKILL.md is already 914 lines
- **Recommendation**: yes — add G6 to SKILL.md as part of v1 rebuild; cost is one paragraph
- **Source**: noted in `architecture-conda-forge-expert.md` § Recipe Authoring Gotchas

**✅ CONFIRMED DECISION (2026-05-12, operator-approved): ACCEPTED — promote G6 to SKILL.md.**
- **Story confirmed**: E6.S1f (SKILL.md gotchas section) includes G6 (was "G1-G6" but noted as Q-PRD-03 dependent).
- **Closes doc drift**: this is one of the "no drift on rebuild" benefits.
- **Operator override**: trivial to revert — drop G6 from E6.S1f acceptance criteria.

### Q-PRD-04 (Part 2, P1) → TENTATIVE: simple 60s backoff in v1

**Should Phase K (VCS version lookup) include built-in rate-limit backoff in the rebuild?**

- **Pros**: closes the GitHub secondary rate-limit failure mode; reduces operator pain
- **Cons**: backoff logic adds complexity; current `--reset-ttl`-per-day cron pattern works
- **Recommendation**: add a simple 60s-on-403-secondary backoff; full exponential backoff is a v2 enhancement
- **Source**: auto-memory `project_phase_k_secondary_rate_limit.md`

**✅ CONFIRMED DECISION (2026-05-12, operator-approved): ACCEPTED — simple 60s-on-403 backoff in v1; full exponential deferred to v2.**
- **New story added**: E8.S17 (Phase K secondary-rate-limit backoff) — see Epic 8 in `epics.md`.
- **Scope**: detect HTTP 403 with `secondary rate limit` body; sleep 60s; retry once; if still 403, mark `github_version_last_error` and skip the row.
- **Acceptance**: synthetic-fixture test: 403 → sleep → retry → success path; 403 → sleep → 403 → error path. Both tested.
- **Estimated complexity**: S (~10-15 LOC + test).
- **Operator override**: drop E8.S17 to revert; existing TTL pattern still works.

### Q-PRD-05 (Part 4, P0) → TENTATIVE: include empty sibling-project stubs

**Should the rebuild include sibling BMAD projects (`deckcraft`, `presenton-pixi-image`) or just `local-recipes`?**

- **Pros (siblings included)**: rebuilt repo immediately supports multi-project pattern; better testbed for active-project resolution
- **Cons**: siblings have their own complexity; some are gitignored
- **Recommendation**: rebuild includes empty `_bmad-output/projects/{deckcraft,presenton-pixi-image}/` directories + `.bmad-config.toml` stubs; full sibling artifacts are out of scope (operator imports them as needed)
- **Source**: open

**✅ CONFIRMED DECISION (2026-05-12, operator-approved): ACCEPTED — empty sibling stubs + .bmad-config.toml.**
- **Story confirmed**: E2.S7 (Create deckcraft + presenton-pixi-image stubs) stands as written.
- **Scope**: each sibling gets `_bmad-output/projects/<slug>/` with empty `planning-artifacts/` + `implementation-artifacts/` + a single `.bmad-config.toml` declaring the project name + empty overrides. No content.
- **Validation**: `scripts/bmad-switch --list` returns 3 project names (`local-recipes`, `deckcraft`, `presenton-pixi-image`).
- **Operator override**: drop E2.S7 to skip; only `local-recipes` would exist. (Not recommended — defeats the multi-project testbed value.)

### Q-PRD-06 (cross-cutting, P1) → TENTATIVE: include CI templates with `.template.yml` suffix

**Should the rebuild include CI pipelines (Azure DevOps + GitHub Actions)?**

- **Pros**: rebuilt repo is immediately CI-ready
- **Cons**: CI is operator-environment-specific (Azure org, GitHub repo URL, secrets)
- **Recommendation**: include CI templates as `.azure-pipelines/*.template.yml` + `.github/workflows/*.template.yml`; operator renames + customizes
- **Source**: open

**✅ CONFIRMED DECISION (2026-05-12, operator-approved): ACCEPTED — ship CI as `.template.yml` files; operator renames + customizes.**
- **Story confirmed**: E12.S9 (Author CI pipeline templates) stands as written.
- **Scope**: `.azure-pipelines/recipe.yml.template`, `.github/workflows/sync-pypi-mappings.yml.template`, `.github/workflows/*.yml.template` covering build + lint + sync-mappings.
- **Documentation**: `deployment-guide.md` § CI / CD includes "rename + customize" instructions.
- **Operator override**: if you'd rather ship empty placeholders or skip entirely, drop or modify E12.S9.

### Q-PRD-07 (Part 1, P2) → TENTATIVE: do NOT commit macOS SDK; document acquisition

**Should the rebuild include the macOS SDK (`SDKs/MacOSX11.0.sdk.tar.xz`) for cross-compile?**

- **Pros**: enables linux-host → osx-64 cross-compile out-of-the-box
- **Cons**: 200MB committed binary; license compliance concerns
- **Recommendation**: do NOT commit; document SDK acquisition + extraction in `deployment-guide.md`; provide `pixi run build-local-setup-sdk` task that fetches from operator-provided location
- **Source**: open

**✅ CONFIRMED DECISION (2026-05-12, operator-approved): ACCEPTED — do not commit SDK; provide acquisition docs + setup task.**
- **Story confirmed**: E13.S2 (Author `docs/enterprise-deployment.md`) includes a "Cross-compile SDK acquisition" subsection.
- **Pixi task confirmed**: `pixi run build-local-setup-sdk` task in `pixi.toml` (already exists in Wave 1 Epic 1 scope; no change needed).
- **Operator override**: if you do want to commit the SDK, add it to `SDKs/` and remove the acquisition docs. Be aware of the licensing risk.

---

### Decision summary

| Q-PRD | Decision | Affected stories | Operator status |
|---|---|---|---|
| Q-PRD-01 | INCLUDE `.mcp.json` | E10.S9 confirmed | ✅ CONFIRMED 2026-05-12 |
| Q-PRD-02 | DEFER host-aware refactor | None (DW2 stands) | ✅ CONFIRMED 2026-05-12 |
| Q-PRD-03 | PROMOTE G6 to SKILL.md | E6.S1f scope expanded | ✅ CONFIRMED 2026-05-12 |
| Q-PRD-04 | SIMPLE 60s backoff | **E8.S17 added** | ✅ CONFIRMED 2026-05-12 |
| Q-PRD-05 | INCLUDE sibling stubs | E2.S7 confirmed | ✅ CONFIRMED 2026-05-12 |
| Q-PRD-06 | INCLUDE CI templates | E12.S9 confirmed | ✅ CONFIRMED 2026-05-12 |
| Q-PRD-07 | DO NOT commit SDK | E13.S2 scope expanded | ✅ CONFIRMED 2026-05-12 |

**Net story changes**: +1 story (E8.S17 for Q-PRD-04). All decisions confirmed; PRD §12 sign-off promoted to `approved`.

---

## 9. Deferred Work (out of scope for v1 rebuild)

Captured here so they aren't forgotten. All have detailed treatment in source docs.

| ID | Description | Source |
|---|---|---|
| DW1 | `.mcp.json` server registration (if Q-PRD-01 chooses defer) | `docs/specs/claude-team-memory.md` Q13 |
| DW2 | `_http.py` host-aware refactor | `project_http_jfrog_unconditional_injection.md` |
| DW3 | Phase K rate-limit exponential backoff | `project_phase_k_secondary_rate_limit.md` |
| DW4 | Phase F+ richer metrics (rolling 30/90-day downloads, trend slope) | `docs/specs/atlas-phase-f-s3-backend.md` Waves 2-3 |
| DW5 | `platform_breakdown`, `pyver_breakdown`, `channel_split` MCP tools | Same spec, Wave 3 |
| DW6 | conda-forge-tracker subsystem | `docs/specs/conda-forge-tracker.md` |
| DW7 | copilot-bridge VS Code extension | `docs/specs/copilot-bridge-vscode-extension.md` |
| DW8 | DB-GPT conda-forge packaging | `docs/specs/db-gpt-conda-forge.md` |
| DW9 | Claude team memory subsystem | `docs/specs/claude-team-memory.md` |
| DW10 | Cursor SDK local recipe | `_bmad-output/projects/local-recipes/implementation-artifacts/spec-cursor-sdk-local-recipe.md` |

---

## 10. Risks

| ID | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Skill version drift between rebuild start and finish | High | Medium | Pin to v8.0.0 at PRD re-validation time (2026-05-13). PRD v1.1.0 was re-pinned v7.7 → v7.8.1 via `bmad-correct-course` per `sprint-change-proposal-2026-05-12.md`. PRD v1.1.1 was re-pinned v7.8.1 → v7.9.0 via `bmad-edit-prd` after the actionable-scope audit (`docs/specs/atlas-pypi-universe-split.md`) closed 4 phase-denominator findings; retro at `implementation-artifacts/retro-atlas-pypi-universe-split-2026-05-13.md`. PRD v1.2.0 was re-pinned v7.9.0 → v8.0.0 via `bmad-correct-course` after the structural-enforcement + persona-profile bundle (`docs/specs/conda-forge-expert-v8.0.md`) shipped schema v21's `v_actionable_packages` view + Phase H serial-gate + `bootstrap-data --profile {maintainer,admin,consumer}` (Wave C `vuln_total` drop deferred — 4 actual consumers found, retro corrected); retro at `implementation-artifacts/retro-conda-forge-expert-v8.0-2026-05-13.md`. |
| R2 | Operator misconfigures `_http.py` and creates a worse cross-host leak | Medium | High | Comprehensive doc in 3+ places; subshell pattern is the simplest mitigation; consider DW2 promotion if any incidents |
| R3 | rattler-build introduces breaking change during rebuild | Low | High | Pin `rattler-build-conda-compat >=1.2.0,<2.0.0a0` (already in pixi.toml); track upstream releases |
| R4 | BMAD-METHOD ships v7.0 with breaking changes to skill format | Medium | Medium | Pin BMAD installer version; defer upgrade to a post-rebuild dedicated effort |
| R5 | Operator runs rebuild on a host without Docker | Medium | High | Document as A1 assumption; rebuild deployment-guide.md includes Docker setup or "non-Docker" fallback path |
| R6 | conda-forge changes Python floor before rebuild ships | Medium | Low | Floor is documented in SKILL.md + project-context.md + Part 1's `python-min-policy.md`; update in same retro |
| R7 | New conda-forge lint code added post-rebuild | High | Low | Run `optimize_recipe.py` against the upstream conda-forge linter periodically; add the code to the 17 |

---

## 11. Dependencies

### External dependencies (cannot rebuild without)

- **Pixi runtime** (`pixi 0.67.2+`) — operator installs separately
- **BMAD-METHOD** installer — operator installs via `bmad-method` PyPI package (or equivalent)
- **rattler-build CLI** — pixi-managed
- **gh CLI** — pixi-managed
- **conda-forge ecosystem** (channels, conda-forge.yml schema, lint rules) — read-only dependency

### Internal sequencing dependencies

Per `project-parts.json`'s `rebuild_dependencies.build_order`:

1. **Part 4 (BMAD infra)** — must exist for planning to happen
2. **Part 1 (CFE skill)** — every other code part references it
3. **Part 2 (cf_atlas)** — extends Part 1's `scripts/`
4. **Part 3 (MCP server)** — wraps Part 1's scripts

Cross-cutting (`_http.py`, pixi.toml, `JFROG_API_KEY` discipline) should land in Part 1 to bootstrap Parts 2 and 3.

---

## 11.5 Timeline

This is a **personal-time rebuild effort with no firm calendar deadline**. The operator (rxm7706) drives sprint cadence based on availability. Targets below are aspirational ranges, not commitments.

| Milestone | Aspirational target | Status |
|---|---|---|
| PRD approved (this doc) | within 2 weeks of issue date | draft |
| Architecture + epics approved | within 4 weeks of PRD approval | draft |
| Wave 1 complete (Foundation) | within 8 weeks of approval (~3 sprints) | not started |
| Wave 2 complete (Part 1 skill) | within 18 weeks of approval (~8 sprints) | not started |
| Wave 3 complete (cf_atlas) | within 26 weeks of approval (~6 sprints after Wave 2) | not started |
| Wave 4 complete (Parts 3+4) | within 30 weeks of approval (~2 sprints after Wave 3) | not started |
| Wave 5 complete (hardening) | within 34 weeks of approval (~2 sprints after Wave 4) | not started |
| Rebuild signed off | within 36 weeks of approval | not started |

**Sprint cadence assumption**: 1 sprint = 1 week of focused effort (AI-assisted development changes the math significantly vs. traditional estimates).

**Re-baseline trigger**: if the operator goes 2+ weeks without progress in any wave, re-baseline the schedule at the next retro. Aspirational targets above are **not commitments**; they exist so the rebuild has a sense of direction.

**Status flip mechanism**: when an actual completion date is recorded, replace the aspirational target with `YYYY-MM-DD` and update `status` to `complete`. The frontmatter `status` field flips from `draft` → `in_progress` → `complete` accordingly.

---

## 12. Approvals & Sign-off

**PRD APPROVED 2026-05-12.** All sign-off conditions met:

- [x] **Q-PRD-01 through Q-PRD-07 confirmed (2026-05-12)** — operator (rxm7706) accepted all 7 recommendations
- [x] **Operator (rxm7706) acknowledges scope** — confirmed via decision approval
- [x] Architecture doc consolidating Parts 1-4 produced (`architecture.md`)
- [x] Epics + stories produced (`epics.md` — 193 stories, 0 XL after MF4 splits + Q-PRD-04 addition)
- [x] Validation report (`validation-report-PRD.md`) — REVISE verdict superseded by MF2 + MF3 applications
- [x] Implementation readiness report (`implementation-readiness-report.md`) — CONDITIONAL_READY → **READY** after MF1 confirmation
- [ ] First epic's stories estimated and assigned (next step: begin Sprint 1 = Epic 1 Pixi Monorepo Bootstrap)

**Status history**:
- 2026-05-12 (initial): `status: draft`
- 2026-05-12 (after MF2 + MF3 applied): `status: draft` (still pending decisions)
- 2026-05-12 (after tentative decisions applied): `status: tentative_approved`
- **2026-05-12 (after operator confirmation): `status: approved`** ← currently here

**Re-baseline triggers** (after approval):
- Skill CHANGELOG ships v7.8.0+ (MINOR bump) → re-verify volatile PRD sections (Features §5, Open Decisions §8, Success Metrics §6 air-gap)
- Operator overrides a confirmed decision → revise the affected stories + bump PRD version
- New must-fix items surfaced in implementation → may require PRD revision and re-approval cycle

---

## Appendix A: Glossary

- **Tier 1** — canonical Python implementation in `.claude/skills/conda-forge-expert/scripts/`
- **Tier 2** — thin CLI wrappers in `.claude/scripts/conda-forge-expert/`
- **Tier 3** — runtime data state in `.claude/data/conda-forge-expert/`
- **CFE** — conda-forge-expert skill (Part 1)
- **MCP** — Model Context Protocol (Anthropic's tool-use protocol)
- **BMAD** — the AI-driven dev framework (`bmad-method`)
- **CFEP-25** — conda-forge Enhancement Proposal #25 (python_min triad)
- **G1-G6** — Recipe Authoring Gotchas in SKILL.md
- **STD-001 / TEST-002 / etc.** — Lint codes from `recipe_optimizer.py`
- **Phase B/F/H/K/N/...** — atlas pipeline phases
- **TTL gate** — phase eligibility predicate based on `*_fetched_at` column
- **phase_state** — checkpoint table tracking phase progress + cursors

## Appendix C: JTBD ↔ Feature Traceability Matrix

Maps each of the 52 features in §5 to its **primary JTBD** (the user job it most directly serves) and optional **secondary JTBD(s)** (additional jobs it supports). Resolves Step D6 finding in `validation-report-PRD.md`.

### Part 1: conda-forge-expert skill (15 features)

| Feature | Primary JTBD | Secondary | Why this serves the JTBD |
|---|---|---|---|
| F1.1 (3-tier architecture) | JTBD-3.1 | JTBD-5.1 | Discipline lets new agents navigate; meta-test enforces |
| F1.2 (10-step autonomous loop) | JTBD-1.1 | JTBD-3.1 | The loop IS the agent's mental model of recipe authoring |
| F1.3 (5 Critical Constraints) | JTBD-1.1 | JTBD-4.1 | Non-negotiables prevent auto-rejection |
| F1.4 (42 Tier 1 scripts) | JTBD-1.1 | JTBD-3.1 | Behavior source-of-truth |
| F1.5 (34 Tier 2 wrappers + tasks) | JTBD-1.1 | JTBD-1.4 | Pixi-task surface for shell + BMAD use |
| F1.6 (17-lint-code optimizer) | JTBD-1.1 | JTBD-4.1 | Catches lint issues pre-review |
| F1.7 (G1-G6 gotchas) | JTBD-1.2 | JTBD-3.1 | Non-obvious failures enumerated so agents avoid them |
| F1.8 (41 templates / 13 ecosystems) | JTBD-1.1 | — | Recipe scaffolding |
| F1.9 (11 reference + 8 guides + 2 quickrefs) | JTBD-3.1 | JTBD-1.2, JTBD-5.1 | Documentation cascade |
| F1.10 (MANIFEST.yaml + install.py) | JTBD-5.1 | — | Portability enables reuse in other repos |
| F1.11 (Build failure protocol) | JTBD-1.2 | JTBD-3.1 | Diagnosis workflow under pressure |
| F1.12 (Migration protocol) | JTBD-1.1 | — | v0→v1 strangler pattern |
| F1.13 (Mapping subsystem) | JTBD-1.1 | — | PyPI→conda name resolution |
| F1.14 (41 tests) | JTBD-5.1 | JTBD-1.1 | Regression protection during rebuild + future work |
| F1.15 (CHANGELOG with TL;DR) | JTBD-3.2 | JTBD-5.1 | Drift-detection source for project-context re-sync |

### Part 2: cf_atlas data pipeline (12 features)

| Feature | Primary JTBD | Secondary | Why this serves the JTBD |
|---|---|---|---|
| F2.1 (SQLite schema v20) | JTBD-1.3 | — | Single source of intelligence data; `pypi_universe` side table separates PyPI directory from conda-actionable working set |
| F2.2 (17 phases via PHASES registry) | JTBD-1.3 | JTBD-2.1 | Pipeline structure enables refresh + air-gap |
| F2.3 (`bootstrap-data` orchestrator) | JTBD-1.3 | JTBD-2.1 | Single command refreshes everything |
| F2.4 (`atlas-phase <ID>` CLI) | JTBD-1.3 | — | Cheap single-phase refresh |
| F2.5 (TTL gates on F/G/H/K) | JTBD-1.3 | JTBD-2.1 | Stale-row re-fetch cheap; full rebuild rare |
| F2.6 (`phase_state` checkpointing) | JTBD-1.3 | — | Mid-run kill resumes cheaply |
| F2.7 (Phase F S3 parquet backend) | JTBD-2.1 | — | Closes api.anaconda.org dependency |
| F2.8 (Phase H cf-graph backend) | JTBD-2.1 | JTBD-1.3 | Closes pypi.org dependency; fast cold start |
| F2.9 (60s heartbeat + capped cadence) | JTBD-1.3 | — | "Phase H hangs" UX bug closed |
| F2.10 (17 public CLIs) | JTBD-1.3 | JTBD-4.1 | Read-side intelligence surface |
| F2.11 (Phase G/G' require vuln-db) | JTBD-2.1 | JTBD-1.1 | Vulnerability scanning data |
| F2.12 (Idempotent schema migrations) | JTBD-5.1 | — | Safe to re-run on stale DBs |

### Part 3: FastMCP server (8 features)

| Feature | Primary JTBD | Secondary | Why this serves the JTBD |
|---|---|---|---|
| F3.1 (FastMCP server + name) | JTBD-3.1 | JTBD-1.4 | MCP wire format for Claude Code |
| F3.2 (35 `@mcp.tool()` registrations) | JTBD-3.1 | JTBD-1.4 | Tool surface for agents |
| F3.3 (Thin subprocess wrapper pattern) | JTBD-5.1 | — | Maintainability; logic in Tier 1, wire format in Part 3 |
| F3.4 (`_run_script` 3-tier error handling) | JTBD-3.1 | — | Graceful failure; server doesn't crash |
| F3.5 (2 async tools) | JTBD-1.1 | — | Long-running builds + CVE refresh don't block |
| F3.6 (Out-of-band state files) | JTBD-3.1 | — | Async build outcome bridging |
| F3.7 (`mcp_call.py` JSON-RPC client) | JTBD-5.1 | — | Shell-side fallback (operator-as-user; covers a 5th persona JTBD: "Operate without Claude Code") |
| F3.8 (`gemini_server.py` auxiliary) | (No primary JTBD) | — | **Justification weak** — P2 priority; serves "fallback model backend" need that isn't a primary JTBD. Consider moving to deferred work if no operator demand. |

### Part 4: BMAD infrastructure (10 features)

| Feature | Primary JTBD | Secondary | Why this serves the JTBD |
|---|---|---|---|
| F4.1 (BMAD installer v6.6.0) | JTBD-1.4 | — | Planning framework substrate |
| F4.2 (6-layer config merge) | JTBD-1.4 | JTBD-5.1 | Multi-project / multi-operator config without conflict |
| F4.3 (Active-project resolution) | JTBD-1.4 | — | Right project context per command |
| F4.4 (`scripts/bmad-switch`) | JTBD-1.4 | — | Operator interface for active-project |
| F4.5 (65 installed skills) | JTBD-1.4 | JTBD-3.1 | Planning + dev + review surfaces |
| F4.6 (`conda-forge-expert` skill) | JTBD-1.1 | (all) | Part 1 anchor |
| F4.7 (Per-skill customization) | JTBD-5.1 | — | Override defaults without forking skills |
| F4.8 (Multi-project layout) | JTBD-1.4 | JTBD-5.1 | Sibling projects coexist |
| F4.9 (CLAUDE.md BMAD↔CFE rules) | JTBD-1.4 | JTBD-3.2 | Rules 1 + 2 prevent coordination failures |
| F4.10 (project-context.md + drift contract) | JTBD-3.1 | JTBD-3.2 | Foundational rules every agent reads |

### Cross-cutting (7 features)

| Feature | Primary JTBD | Secondary | Why this serves the JTBD |
|---|---|---|---|
| FX.1 (`_http.py` auth chain) | JTBD-2.1 | JTBD-2.2 | Single auth chain enables env-var-driven overrides |
| FX.2 (8 pixi envs) | JTBD-1.1 | JTBD-2.1 | Per-task tooling without conflict |
| FX.3 (JFROG_API_KEY leak docs) | JTBD-2.2 | — | Operator hygiene for the system's most consequential security constraint |
| FX.4 (vuln-db env separation) | JTBD-1.1 | — | Default env stays lean |
| FX.5 (`docs/pixi-config-jfrog.example.toml`) | JTBD-2.1 | — | Copy-pasteable starter for JFrog deployments |
| FX.6 (`.claude/settings.json` permission gates) | JTBD-1.1 | JTBD-2.2 | Defaults safe; `--force` push denied |
| FX.7 (`build-locally.py` Docker wrapper) | JTBD-1.1 | — | Linux builds don't pollute host env |

### JTBD coverage check

11 JTBDs × 52 features cross-checked: **every JTBD has ≥1 primary feature serving it**.

| JTBD | Count of primary features | Lowest-coverage JTBD |
|---|---|---|
| JTBD-1.1 (author recipe) | 15 | — |
| JTBD-1.2 (diagnose build failure) | 2 | — |
| JTBD-1.3 (find feedstocks with new upstream) | 6 | — |
| JTBD-1.4 (plan multi-recipe feature) | 7 | — |
| JTBD-2.1 (air-gap deployment) | 5 | — |
| JTBD-2.2 (no credential leak) | 1 | ⚠️ Single feature serves this JTBD; consider whether FX.3 alone is sufficient |
| JTBD-3.1 (agent on first activation) | 7 | — |
| JTBD-3.2 (retro updates skill) | 1 | ⚠️ Single feature (F1.15 CHANGELOG) serves this; the retro contract itself is in F4.9 |
| JTBD-4.1 (reviewer experience) | 0 → secondary on F1.3, F1.6 | ⚠️ No primary feature for JTBD-4.1 — reviewer experience comes from upstream side-effects of F1.3 + F1.6 |
| JTBD-5.1 (future contributor) | 7 | — |
| (operator-without-Claude-Code, implicit in F3.7) | 1 | ⚠️ Not a formally-defined JTBD; consider adding to §3 |

### Findings from the matrix

1. **F3.8 (Gemini auxiliary) has no primary JTBD.** Confirms validation finding D6. Either define a "fallback model backend" JTBD or move F3.8 to deferred work.
2. **JTBD-4.1 (reviewer experience) has zero primary features.** All features serving it do so as secondary effects. Either (a) acknowledge this is intentional (reviewer experience is downstream of authoring quality, not a direct PRD target) or (b) add a primary feature like "Recipe self-explanation in PR description."
3. **JTBD-2.2 (no credential leak) is served by only one feature** — FX.3 (documentation). The architectural fix (DW2 `_http.py` host-aware refactor) is deferred. Document this explicitly: the system's primary defense against the JFROG leak is operator discipline, not architecture.
4. **F3.7 (mcp_call.py) implies a 5th persona** ("operator without Claude Code"). Either define explicitly in §3 or accept it as latent.

---

## Appendix B: References

Primary input documents:
- [planning-artifacts/index.md](./index.md)
- [planning-artifacts/project-overview.md](./project-overview.md)
- [planning-artifacts/architecture-conda-forge-expert.md](./architecture-conda-forge-expert.md)
- [planning-artifacts/architecture-cf-atlas.md](./architecture-cf-atlas.md)
- [planning-artifacts/architecture-mcp-server.md](./architecture-mcp-server.md)
- [planning-artifacts/architecture-bmad-infra.md](./architecture-bmad-infra.md)
- [planning-artifacts/integration-architecture.md](./integration-architecture.md)
- [project-context.md](../project-context.md)

Supporting:
- [CLAUDE.md](../../../../CLAUDE.md)
- [.claude/skills/conda-forge-expert/CHANGELOG.md](../../../../.claude/skills/conda-forge-expert/CHANGELOG.md)
- [docs/enterprise-deployment.md](../../../../docs/enterprise-deployment.md)
