---
id: SPEC-code-audit-remediation-2026-07-26
spec: code-audit-remediation
status: ready
owner-dream: n/a
program: regenerable-factory
surface:
  - .claude/skills/conda-forge-expert/**
  - .claude/tools/**
  - .claude/hooks/**
  - src/shared/packages/pyforge-atlas/**
  - src/shared/packages/pyforge-warden/**
  - src/shared/packages/pyforge-{doctor,herald,marshal,mason,scribe,steward}/**  # W6 dependency-completeness sweep (audited, in sync, unchanged)
  - .gitignore
sources:
  - Cursor codebase audit session 2026-07-26 (conda-forge-expert MCP layer, pyforge-atlas, pyforge-warden)
  - Remediation waves W1–W7e on branch fix/code-audit-remediation-2026-07-26 (2026-07-26…2026-07-27)
  - BMAD handoff rewrite 2026-07-27 (Spec usable without PR merge)
---

# Code audit remediation — consolidated findings & fix map

Traceability contract: every implementation commit references one or more **Finding IDs**
(`AUD-<area>-<nnn>`). Status values: `open` | `in-progress` | `fixed` | `deferred` | `wont-fix`.

## Summary

**This Spec is the portable contract.** Assume the implementation PR on branch
`fix/code-audit-remediation-2026-07-26` may never merge. Downstream teams must be able to:

1. **Review** every finding and disposition from this document alone.
2. **Update** project PRDs / architecture / story specs (BMAD planning chain).
3. **Implement** remaining work via `bmad-spec` → stories → `bmad-dev-auto` / `bmad-loop`,
   using the branch (or a worktree checkout of it) only as **reference code / guide**,
   not as a required merge dependency.

| Field | Value |
|---|---|
| Spec ID | `SPEC-code-audit-remediation-2026-07-26` |
| Spec status | `ready` (Round-3 remediation waves **W7–W7e complete**; residual work is deferred DWs + one open infra finding) |
| Reference branch | `fix/code-audit-remediation-2026-07-26` (local-recipes) |
| Canonical suites (post-W7e) | warden **1962 passed**; atlas **809 passed** / 19 skipped |
| Primary projects | `local-recipes` (this Spec), `pyforge-warden`, `pyforge-atlas` |
| Parallel-agent rule | Write under `_bmad-output/projects/<slug>/…` physical paths; **never** `scripts/bmad-switch` from parallel agents |

### Disposition vocabulary (use these exact terms in stories)

| Term | Meaning |
|---|---|
| **IMPLEMENT** | Code (and tests) changed on the reference branch — re-apply or port from branch files listed under the finding |
| **DEMOTE_DOC** | Spec/PRD/epic/story wording corrected to match shipped reality; no (or only comment) code change |
| **KEEP_DEFER** | Intentionally not done; tracked in a named DW ledger entry; BMAD story must bind to that DW |
| **DEFER** (legacy synonym) | Same as KEEP_DEFER when a DW exists; otherwise create the DW first |
| **wont-fix** | Explicitly rejected (e.g. AUD-WARDEN-004) |
| **open** | Still actionable, no closing disposition yet (only AUD-WARDEN-009 in Round-2 leftovers) |

### Final disposition census (Round-3 + prior rounds on this branch)

| Bucket | Count / IDs | Notes |
|---|---|---|
| Fixed (code or doc-closed) | Round-3 W-011…031 + A-014…045/047–048 (+ A-049 docs); prior rounds per finding bodies | Master matrix in § Handoff |
| KEEP_DEFER (DW-bound) | **A-032** → DW-B7-4; **A-046** → DW-AD23-1; **A-049** bench → DW-F1-1 | Atlas ledger |
| Deferred product/security (CFE, pre-R3) | AUD-CFE-003, 004; AUD-ATLAS-003, 004, 005; AUD-WARDEN-005–008 | Need product/architecture stories — see § Follow-up register |
| Open (infra) | **AUD-WARDEN-009** | `slow` corpus hang — BMAD story under pyforge-warden |
| wont-fix | AUD-WARDEN-004 | Reverted; do not re-litigate |

### ✅ Suites (measured on the reference branch after W7e)

| Suite | Canonical task | Result |
|---|---|---|
| pyforge-warden | `pixi run -e pyforge-warden pyforge-warden-test` | **1962 passed, 0 failed** |
| pyforge-atlas | `pixi run -e pyforge-atlas kedro-test` | **809 passed, 0 failed**, 19 skipped |
| pyforge-marshal | `pixi run -e pyforge-marshal pyforge-marshal-test` | **155 passed** |
| pyforge-herald | `pixi run -e pyforge-herald pyforge-herald-test` | **140 passed**, 2 skipped |
| pyforge-doctor | `pixi run -e pyforge-doctor pyforge-doctor-test` | **69 passed** |
| pyforge-steward | `pixi run -e pyforge-steward pyforge-steward-test` | **19 passed** |
| pyforge-scribe | `pixi run -e pyforge-scribe pyforge-scribe-test` | **18 passed** |
| pyforge-mason | `pixi run -e pyforge-mason pyforge-mason-test` | **11 passed** |
| sentinel (repo-level) | `pixi run -e local-recipes wiki-test` | **4 passed** |
| dependency gate (all 8 pkgs) | `pixi run -e pyforge-ci pyforge-deps-test` | **58 passed** (W6b) |

**Earlier deltas (unchanged):** AUD-WARDEN-004 → `wont-fix`; AUD-ATLAS-010…013 fixed;
AUD-WARDEN-010 fixed; AUD-REPO-001 standing gate (`pyforge-deps-test`).

**Atlas is dependency-complete** (`AUD-ATLAS-010`): `kedro-test` runs standalone in `pyforge-atlas`.

---

## Handoff — BMAD / bmad-loop / bmad-dev-auto (read this first)

### How another team should consume this Spec

1. **Treat this file as Tier-2 source of truth** for the audit remediation effort
   (`_bmad-output/projects/local-recipes/planning-artifacts/specs/`).
2. **For each remaining deferred/open finding**, run `bmad-spec` (or `bmad-create-story`) under
   the owning project slug (`pyforge-atlas` or `pyforge-warden`), with acceptance criteria that
   cite the Finding ID and the DW id where present.
3. **Reference implementation:** check out branch `fix/code-audit-remediation-2026-07-26`
   (or cherry-pick / read files listed in each finding’s **Files** / wave table). Do **not**
   assume `main` already contains the fixes.
4. **Verify** only via canonical pixi tasks (table above). Never bare `python -m pytest` as a
   baseline (Round-1 lesson — environment noise masks real signal).
5. **Parallel agents:** write to `_bmad-output/projects/<slug>/…` physical paths; set
   `BMAD_ACTIVE_PROJECT=<slug>` per invocation; never call `scripts/bmad-switch` from a fan-out.

### Suggested BMAD story seeds (remaining work only)

| Seed ID | Project | Intent | Acceptance oracle (framework-neutral) |
|---|---|---|---|
| SEED-ATLAS-032 | pyforge-atlas | Stream `build_universe_sbom` — no full in-memory `components[]` | Peak RSS / chunked emit; DW-B7-4 closed; universe BOM consumers still validate |
| SEED-ATLAS-046 | pyforge-atlas | Run-admission / single-writer for MCP+CLI concurrent triggers | Concurrent second writer rejected or queued; DW-AD23-1 closed; spine AD-23 re-promoted only after proof |
| SEED-ATLAS-049 | pyforge-atlas | Attended F1 cold/warm benchmark + operator sign-off | Thresholds in story spec pre-run; DW-F1-1 closed; blocked on DW-B4-2 |
| SEED-WARDEN-009 | pyforge-warden | Cap `slow` corpus oracle — no indefinite `conda_build` spin | `pytest-timeout` (or equivalent) + oracle exits; corpus task usable in CI |
| SEED-CFE-003/004 | local-recipes / CFE | MCP sandbox + URL allowlist product decision | Architecture decision recorded; path/SSRF policy module or explicit wont-fix |
| SEED-CFE-RETRO | local-recipes | Rule-2 CFE skill retro for this audit’s `.claude/` deltas | `conda-forge-expert` CHANGELOG entry + gotcha/constraint updates from W1 path guards |

### Follow-up register (ops / docs / not Round-3 code)

| Item | Why | Owner hint |
|---|---|---|
| Regenerate `environment.yaml` | Root `pixi.toml` changed on the reference branch; staged-recipes sync check is ungated | Before any PR that includes `pixi.toml`: `pixi project export conda-environment -e build > environment.yaml` |
| `maintenance` label | Any PR touching outside `recipes/` | `gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance` |
| Exclude `.vscode/` unless intentional | Local IDE settings appeared untracked during the Cursor session | Do not commit unless the team wants shared editor settings |
| CFE Rule-2 retro | Branch touched `.claude/skills/conda-forge-expert/` + tools/hooks | SEED-CFE-RETRO above |
| Promote story specs already synced | Warden 31 + atlas 32 story specs set to `status: shipped` on the reference branch | If branch never merges, re-apply those frontmatter edits from the branch or from W7-product / W7d notes |
| DW ledger entries | DW-B7-4 added; DW-AD23-1 / DW-F1-1 / DW-G3 notes updated on reference branch | Re-apply from `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md` if needed |

### Master disposition matrix — Round-3 (AUD-WARDEN-011…031, AUD-ATLAS-014…049)

| ID | Disposition | Wave | Primary files / DW | Note for implementers |
|---|---|---|---|---|
| W-011 | IMPLEMENT | W7 | `engines.py`, `vuln.py` | Empty OSV parse / exit-1 → unparseable |
| W-012 | IMPLEMENT | W7 | `feeds.py`, conftest | Hollow KEV/EPSS → None; fixtures ≥1 CVE |
| W-013 | IMPLEMENT | W7 | `discovery.py` | Symlink file confine under scan root |
| W-014 | IMPLEMENT | W7 | `waiver.py` | Baseline-emit excludes provenance sentinels |
| W-015 | IMPLEMENT | W7b | `vuln.py` | All-malformed packages → unparseable |
| W-016 | IMPLEMENT | W7b | `vuln.py` | CVSS 3.0 + 3.1 prefixes |
| W-017 | IMPLEMENT | W7c | `vuln.py`, `engines.py` | 5 MiB zip entry / 20 MiB engine output caps |
| W-018 | IMPLEMENT | W7c | `hygiene.py`, `engines.py` | No-identity → excluded + finding |
| W-019 | IMPLEMENT | W7c | `engines.py` | `deps_assessed` = covered count |
| W-020 | IMPLEMENT | W7b | `waiver.py` | Unique-key YAML loader |
| W-021 | IMPLEMENT | W7c | `interfaces.py`, baseline YAML | Ids `name@version` / `@unspecified` |
| W-022 | IMPLEMENT | W7c | `license.py` | Dedupe findings by id |
| W-023 | IMPLEMENT | W7e | `vuln.py` | `_scan_osv_zip` + mtime cache |
| W-024 | IMPLEMENT | W7c | `actuator.py` | PR body Subject only |
| W-025 | IMPLEMENT | W7c | `cli.py` | Keep argparse gates on config fail |
| W-026 | DEMOTE_DOC | W7-product | warden `prd.md` / `epics.md` | Only `--fail-under-coverage` |
| W-027 | DEMOTE_DOC | W7-product | warden PRD/epics | `fail-on-kev` TOML-only |
| W-028 | DEMOTE_DOC | W7e | `spec-6-3-…md` | Finding-only `!python-runtime` |
| W-029 | DEMOTE_DOC | W7-product | schema/models comments | `license_data` reserved null |
| W-030 | DEMOTE_DOC | W7d | 31 story specs + prd/epics | All `status: shipped` |
| W-031 | IMPLEMENT | W7d | scan harness + report schema tests | Unmask feeds/license; exit matrix |
| A-014 | IMPLEMENT | W7 | `migration_status.py` | Slug gate |
| A-015 | IMPLEMENT | W7 | `incremental_parquet.py` | `merge_on` upsert |
| A-016 | IMPLEMENT | W7 | `sbom_intake.py` | Path confine |
| A-017 | IMPLEMENT | W7 | policy gate hygiene path | Allowlist roots |
| A-018 | IMPLEMENT | W7 | `mcp/session.py` | Pin project root |
| A-019 | IMPLEMENT | W7b | publish verify | Chunk path confine |
| A-020 | IMPLEMENT | W7b | BigQuery dataset | ISO-UTC timestamps |
| A-021 | IMPLEMENT | W7b | `lasuite.py` | http(s)+host |
| A-022 | IMPLEMENT | W7b | request datasets | Sanitize path segments |
| A-023 | IMPLEMENT | W7b | vuln nodes | Join miss → unscoped |
| A-024 | IMPLEMENT | W7b | `refresh.py` VDB | Corrupt → DatasetError |
| A-025 | IMPLEMENT | W7b | `sbom_intake.py` | Path escape not offline |
| A-026 | IMPLEMENT | W7c | `dashboard/data.py` | Bare TypeError re-raises |
| A-027 | IMPLEMENT | W7c | `dashboard/data.py` | Data-root resolve |
| A-028 | IMPLEMENT | W7c | pypi_intelligence nodes | Collect + one concat |
| A-029 | IMPLEMENT | W7c | refresh/basilisk/migration | mkstemp atomic write |
| A-030 | IMPLEMENT | W7c | vulnerability nodes | Vectorized groupby |
| A-031 | IMPLEMENT | W7c | `incremental_parquet.py` | None TTL → all stale |
| A-032 | KEEP_DEFER | W7e | DW-B7-4 | Streaming BOM — see SEED-ATLAS-032 |
| A-033 | IMPLEMENT | W7b/W7c | `publish/emitter.py` | `\Z` |
| A-034 | IMPLEMENT | W7c | `rag/store.py` | Close on init fail |
| A-035 | IMPLEMENT | W7c | `rate_limit.py` | NaN/Inf → 0.0 |
| A-036 | DEMOTE_DOC | W7e | `event_source.py` + DW-G3 | Intentional cursor |
| A-037 | IMPLEMENT | W7c | `validation.py` | Non-DF → halt |
| A-038 | IMPLEMENT | W7c | `sbom_intake.py` | 10 MiB intake cap |
| A-039 | IMPLEMENT | W7e | `vcs_health/nodes.py` | downloads groupby.max |
| A-040 | IMPLEMENT | W7c | `lasuite.py` | doc_id slug |
| A-041 | DEMOTE_DOC | W7-product | spine FR-9 + DW-D2 | Honest-core 8 pages |
| A-042 | DEMOTE_DOC | W7-product | AD-9 | Registry-as-DATA |
| A-043 | IMPLEMENT | W7-product | `mcp/tools.py` | Stamp envelope |
| A-044 | IMPLEMENT | W7-product | dashboard pages | AD-17 stamps |
| A-045 | DEMOTE_DOC | W7-product | 32 atlas story specs | `status: shipped` |
| A-046 | KEEP_DEFER | W7e | DW-AD23-1 | See SEED-ATLAS-046 |
| A-047 | DEMOTE_DOC | W7-product | intake/CLAUDE.md | Shipped ≠ retirement |
| A-048 | DEMOTE_DOC | W7-product | A2/B6 notes | Historical 73 vs live 86 |
| A-049 | DEMOTE_DOC + KEEP_DEFER | W7-product/W7e | DW-F1-1 | Docs closed; bench remains |

### Reference code map (where to look on the branch)

| Area | Paths on `fix/code-audit-remediation-2026-07-26` |
|---|---|
| Warden engines / vuln / feeds / discovery / waiver / hygiene / license / actuator / cli | `src/shared/packages/pyforge-warden/src/pyforge/warden/` |
| Warden dogfood baseline | `src/shared/packages/pyforge-warden/.warden-baseline.yaml` |
| Warden tests (031 matrix, 023 zip cache, harness smokes) | `…/tests/conformance/`, `…/tests/unit/test_vuln.py` |
| Atlas datasets / dashboard / MCP / validation / lasuite / rag / pipelines | `src/shared/packages/pyforge-atlas/src/pyforge/atlas/` |
| Atlas DW ledger | `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md` |
| Warden PRD/epics/story specs (030/028 doc sync) | `_bmad-output/projects/pyforge-warden/planning-artifacts/` |
| Atlas spine / story specs (041–049) | `_bmad-output/projects/pyforge-atlas/planning-artifacts/` |
| CFE path guards | `.claude/skills/conda-forge-expert/scripts/`, `.claude/tools/` |
| Dep completeness gate | `tests/packaging/test_dependency_completeness.py` |

---

## CFE / conda-forge-expert / MCP

### AUD-CFE-001 — Path traversal in PR submission (High)
- **Severity:** High
- **Category:** Security
- **Files:** `.claude/skills/conda-forge-expert/scripts/submit_pr.py`, `.claude/tools/conda_forge_server.py`
- **Finding:** `recipe_name` joined as `REPO_ROOT / "recipes" / recipe_name` without rejecting `..` or `/`; can copy files outside `recipes/` to a public fork.
- **Fix:** Add `_validate_recipe_name()`; resolve `recipe_dir` and require `is_relative_to(REPO_ROOT / "recipes")`.
- **Status:** fixed

### AUD-CFE-002 — Unrestricted YAML edit via MCP (High)
- **Severity:** High
- **Category:** Security
- **Files:** `.claude/skills/conda-forge-expert/scripts/recipe_editor.py`
- **Finding:** Only `.yaml`/`.yml` suffix check; any YAML file in the repo can be modified.
- **Fix:** Confine writable paths to `recipes/` subtree (resolved path guard).
- **Status:** fixed

### AUD-CFE-003 — MCP destructive ops without sandbox (High)
- **Severity:** High
- **Category:** Security / ops
- **Files:** `.claude/tools/conda_forge_server.py`
- **Finding:** 46 tools accept agent paths with no allowlist; documented only.
- **Fix:** **Deferred** — requires product decision (auth layer). Mitigate via AUD-CFE-001/002/004 path guards.
- **BMAD pickup:** SEED-CFE-003/004 — architecture decision + optional sandbox; Rule-2 CFE retro must
  record whatever lands in `conda-forge-expert` CHANGELOG.
- **Status:** deferred

### AUD-CFE-004 — SSRF via recipe hash/download URLs (High)
- **Severity:** High
- **Category:** Security
- **Files:** `recipe_editor.py`, `recipe-generator.py`
- **Finding:** `requests.get(url)` with no host/scheme allowlist.
- **Fix:** **Deferred** — needs enterprise URL policy module shared with `_http.py`.
- **BMAD pickup:** pair with SEED-CFE-003/004; reuse `_http.py` truststore/auth chain patterns.
- **Status:** deferred

### AUD-CFE-005 — Partial SQL injection in `query_atlas` (Medium)
- **Severity:** Medium
- **Category:** Security
- **Files:** `.claude/tools/conda_forge_server.py` (`query_atlas`)
- **Finding:** `order_by` and creative `select`/`where` allow arbitrary read SQL fragments.
- **Fix:** Validate `order_by`/`select` against allowlist regex; block `;`, `--`, subqueries.
- **Status:** fixed

### AUD-CFE-006 — `trigger_build` not confined to `recipes/` (Medium)
- **Severity:** Medium
- **Category:** Security
- **Files:** `.claude/tools/conda_forge_server.py` (`trigger_build`)
- **Finding:** Any existing recipe.yaml path can be built.
- **Fix:** Reuse recipes-dir path guard before build.
- **Status:** fixed

### AUD-CFE-007 — N+1 SQLite in `scan_project.enrich_with_atlas` (Medium)
- **Severity:** Medium
- **Category:** Performance
- **Files:** `.claude/skills/conda-forge-expert/scripts/scan_project.py`
- **Finding:** Per-dependency query; connection never closed.
- **Fix:** Batch `IN (...)` queries; `with sqlite3.connect(...)`.
- **Status:** fixed

### AUD-CFE-008 — `.secrets` not in tracked `.gitignore` (Medium)
- **Severity:** Medium
- **Category:** Security
- **Files:** `.gitignore`
- **Finding:** Only `.env` ignored; `.secrets` relies on local exclude.
- **Fix:** Add `.secrets`, `.env.github` patterns.
- **Status:** fixed

### AUD-CFE-009 — Provenance hook logic bugs (Medium)
- **Severity:** Medium
- **Category:** Logic
- **Files:** `.claude/hooks/post-tool-call.py`
- **Finding:** `http_request` never returns body; `--wait_for_response` argparse wrong; exit always 0.
- **Fix:** Return response; `action="store_true"`; propagate errors.
- **Status:** fixed

### AUD-CFE-010 — Gemini API key in query string (Medium)
- **Severity:** Medium
- **Category:** Security
- **Files:** `.claude/tools/gemini_server.py`
- **Finding:** Key in `?key=` URL.
- **Fix:** Use `x-goog-api-key` header.
- **Status:** fixed

### AUD-CFE-011 — Force-push fork main (Low)
- **Severity:** Low (operational)
- **Files:** `submit_pr.py`
- **Fix:** **Deferred** — intentional fork sync; document or switch to `--force-with-lease`.
- **Status:** deferred

### AUD-CFE-012 — `mcp_call.py` unconstrained invocation (Low)
- **Severity:** Low
- **Fix:** **Deferred** — trusted-operator CLI wrapper.
- **Status:** deferred

---

## pyforge-atlas

### AUD-ATLAS-001 — Arbitrary file read via `sbom_intake_path` (High)
- **Severity:** High
- **Category:** Security
- **Files:** `src/pyforge/atlas/datasets/sbom_intake.py`, `conf/base/catalog.yml`
- **Finding:** Runtime param can point outside project `data/`.
- **Fix:** Resolve path; require under Kedro project `data/` root (or catalog filepath parent).
- **Status:** fixed

### AUD-ATLAS-002 — Factory-status reads legacy `docs/specs/` (Medium) — **partially fixed**
- **Severity:** Medium
- **Category:** Logic / spec drift
- **Files:** `dashboard/factory_status.py`, `dashboard/app.py`
- **Finding:** Data layer pointed at Tier-1 legacy specs.
- **Fix:** `factory_status.py` → BMAD Tier-2 (done pre-branch); sync `app.py` stamp Card text.
- **Status:** fixed

### AUD-ATLAS-003 — MCP no auth + full dataset load (High)
- **Severity:** High
- **Category:** Security / performance
- **Files:** `mcp/server.py`, `mcp/tools.py`
- **Fix:** **Deferred** — deployment auth; add row-limit guard in `read_dataset` as partial mitigation.
- **Status:** deferred

### AUD-ATLAS-004 — Vuln read path: empty store vs no vulns (High)
- **Severity:** High
- **Category:** Logic / C0-adjacent (AD-13)
- **Files:** `pipelines/vulnerability/nodes.py`
- **Finding:** Empty vdb → empty rollup, no staleness/indeterminate marker.
- **Fix:** **Deferred** — requires dataset→node staleness contract extension (DW-B5-4).
- **Status:** deferred

### AUD-ATLAS-005 — Phase P BigQuery catalog interim (High)
- **Severity:** High
- **Files:** `conf/base/catalog.yml`, `datasets/request_datasets.py`
- **Fix:** **Deferred** — attended credentialed flip only (NFR-2).
- **Status:** deferred

### AUD-ATLAS-006 — `read_bmad_spec_key` last-write-wins (Medium)
- **Severity:** Medium
- **Files:** `dashboard/factory_status.py`
- **Fix:** Prefer `SPEC.md` status; skip companion `.md` unless no SPEC.
- **Status:** fixed

### AUD-ATLAS-007 — `RateLimitedScheduler` thread safety (Medium)
- **Severity:** Medium
- **Files:** `datasets/rate_limit.py`
- **Fix:** Add `threading.Lock` around token bucket mutations.
- **Status:** fixed

### AUD-ATLAS-008 — Vuln node O(n) Python filter (Medium)
- **Severity:** Medium
- **Files:** `pipelines/vulnerability/nodes.py` (`per_version_vulns`)
- **Fix:** Replace list-comp filter with merge/join.
- **Status:** fixed

### AUD-ATLAS-009 — Dashboard DuckDB connection churn (Low)
- **Fix:** **Deferred** — perf optimization pass.
- **Status:** deferred

### AUD-ATLAS-010 — atlas was not dependency-complete; `kedro-test` could not collect its own suite (High)
- **Severity:** High (raised from Medium — the root cause is undeclared runtime deps, not a test-env gap)
- **Category:** Build / packaging integrity
- **Files:** `src/shared/packages/pyforge-atlas/pyproject.toml`,
  `src/shared/packages/pyforge-atlas/pixi.toml`, root `pixi.toml` (`[feature.pyforge-atlas]`)
- **Finding:** the atlas package declared only 3 runtime deps (`kedro`, `kedro-datasets`,
  `kedro-dagster`) while `pyforge.atlas` **hard-imports at module level** `pandas`, `pyarrow`,
  `pyyaml`, `pandera`, `duckdb`, `ibis`, `boring_semantic_layer`, `dagster`, `vizro`, `a2a`,
  `google.protobuf`, `pydantic`, `pydantic_core`, `openlineage`, `opentelemetry`, and `attr`.
  Two consequences:
  1. `pixi run -e pyforge-atlas kedro-test` died at **collection on 17 modules**
     (`Interrupted: 17 errors during collection`). A task that can never pass in its own env is a
     false CI signal — anyone trusting `kedro-test` as the atlas gate was running **zero** tests,
     and the collection exit is easy to misread as an environment hiccup.
  2. The suite only appeared to pass because the fat `local-recipes` env happened to supply the
     missing libraries. The package's "lean runtime deps" comment was therefore a latent lie: an
     install carrying only the declared deps raises `ImportError` as soon as anything past the
     pipeline registry is touched.
- **Fix (applied):** made the package genuinely dependency-complete, verified by AST-scanning
  `src/` for module-level third-party imports and classifying each as hard vs guarded
  (try/except or function-local):
  - **`pyproject.toml`** — all 21 hard-imported distributions moved into `[project.dependencies]`.
    Only the two genuinely guarded surfaces stay optional: `mcp` (`fastmcp`) and `nl` (`vizro-ai`),
    joining the pre-existing `gate` extra, plus a convenience `all`.
  - **member `pixi.toml`** — `[package.run-dependencies]` mirrors that set with conda names, so the
    built `.conda` is self-sufficient rather than relying on the ambient env.
  - **root `pixi.toml`** — `[feature.pyforge-atlas.dependencies]` now carries only *test* tooling
    (`pytest`, `numpy`, `playwright-python`, `kedro-viz`, `hatchling`, `python-build`), mirroring
    warden's package-vs-feature split. `kedro-mcp` is deliberately **not** added: the mcp test
    poisons it via `sys.modules["kedro_mcp"] = None` to prove it is never load-bearing, and
    `test_ad1_import_direction` forbids importing it anywhere in `pyforge.atlas`.
- **Verified:** `pixi run -e pyforge-atlas kedro-test` → **787 passed, 19 skipped, 0 failed**
  (was 17 collection errors). Byte-identical outcome to the `local-recipes` run, so the two envs
  are now at true parity and atlas no longer depends on `local-recipes`. The 19 skips are all
  DuckDB extension (`vss`, `httpfs`) and wasm-artifact provisioning — **not** the two extras, so
  keeping `fastmcp`/`vizro-ai` optional costs no coverage. Wheel + sdist still build, and the
  generated `METADATA` carries all 21 `Requires-Dist` entries plus the 4 `Provides-Extra`.
- **Repo-rule follow-through:** `pixi.toml` changed, so `environment.yaml` was re-exported per
  CLAUDE.md (`pixi project export conda-environment -e build`) — **unchanged**, since the edit
  touches the atlas feature and not the `build` env. `pixi.lock` is updated and must be committed.
- **Status:** fixed

### AUD-ATLAS-013 — a `sentinel` test was misfiled inside the atlas package, uncollectable everywhere (Medium)
- **Severity:** Medium
- **Category:** Test placement / cross-package coupling
- **Files:** was `src/shared/packages/pyforge-atlas/tests/factory/test_sentinel_knowledge.py`
- **Finding:** this test imports `sentinel.knowledge.*` — a **repo-level** module in `src/sentinel`,
  not part of `pyforge-atlas` at all and not a dependency of it. Sitting inside the atlas test tree
  it failed collection with `ModuleNotFoundError: No module named 'sentinel'` in **every**
  environment, including `local-recipes`, so its 4 tests had never run. It was also the one hard
  blocker to AUD-ATLAS-010: no amount of atlas dependency completeness can satisfy an import of a
  different package's code. The sibling `tests/factory/` files correctly target
  `pyforge.atlas.factory` and always passed, which is what made the outlier easy to miss.
- **Fix (applied):** moved to repo-level `tests/sentinel/`, and wired a
  `pixi run -e local-recipes wiki-test` task (with `PYTHONPATH=src`) next to the other `wiki-*`
  tasks so it is not orphaned. **The 4 tests now pass** — previously-dead coverage recovered.
- **Status:** fixed

### AUD-ATLAS-011 — pandas 3.0 `str` dtype coerces `None` → `NaN`, breaking None-identity contracts (High)
- **Severity:** High
- **Category:** Correctness / dependency migration
- **Files:** `pipelines/core/nodes.py` (`attribute_feedstocks`, `_pick_feedstock`);
  `tests/pipelines/core/test_nodes.py`; `tests/pipelines/seed_gaps/test_nodes.py`;
  `tests/semantic/test_bsl_metric_parity.py`; `tests/semantic/test_maintainer_dimension.py`
- **Finding:** the env ships **pandas 3.0.3 / numpy 2.5.1**, where a list of strings containing
  `None` is inferred as the new default `str` dtype whose missing sentinel is **`NaN`, not `None`**.
  Verified minimally: `df['c'] = ['a', None]` → `dtype('str')`, `value is None` → `False`,
  `repr` → `nan`. `NaN` is **truthy** and is not identity-equal to `None`, so every
  `x is None` test and every `if x:` guard written for pandas 2.x silently flips.
  This single root cause explains **all 6** non-Playwright atlas failures, in two different ways:
  - **Production defect (1).** `_pick_feedstock` correctly returns `None` for a NaN `feedstocks`
    cell (it even carries a comment warning that "NaN is truthy"), but `attribute_feedstocks`
    then loses that `None` at the list→column assignment boundary. The function's documented
    contract — `# NaN cell -> None, no crash` — is broken in the shipped code, and downstream
    `feedstock_name is None` checks will not fire.
  - **Corrupted test oracles (5).** The parity fixtures build DataFrames containing `None`, which
    becomes `NaN` before the oracle ever sees it, so the *test* computes the wrong expectation
    while production is right. Concretely, `_legacy_is_actionable` faithfully mirrors the legacy
    `COALESCE(latest_status,'active')='active'` SQL, but receives `nan` instead of `None`, so its
    `latest_status is not None` guard passes and `nan == "active"` yields `False` — while the ibis
    path correctly reads SQL `NULL`, applies `fill_null("active")`, and returns `True`.
    **The production metric is correct here; the test is the thing that is wrong.** Same shape in
    `_legacy_ci_red(nan)` and in `test_maintainer_dimension`, where a `None` dict key became `nan`.
- **Pre-existing:** yes — confirmed by stashing every branch edit and re-running against the
  pristine tree: the same 6 fail identically. **Not a regression from this branch.**
- **Fix (applied):** `None` is restored as the missing sentinel wherever a None-identity contract
  exists, by pinning those columns to `object` dtype. `dtype=object` is the *only* construction
  that survives — verified empirically: a plain list assign, and even an explicitly-built
  `numpy` object ndarray, both still land as `str` dtype; only `pd.Series(..., dtype=object)` keeps
  `None`.

  Production (3 sites):
  1. `pipelines/core/nodes.py::attribute_feedstocks` — output column built via
     `pd.Series(..., index=out.index, dtype=object)`, restoring the documented
     `NaN cell -> None` contract.
  2. `pipelines/seed_gaps/nodes.py::report_license_map_gap` — `suggested_spdx` pinned to object
     dtype so the `report`-tier "no single candidate" signal stays `None`.
  3. `semantic/metrics.py::ci_red` — see **AUD-ATLAS-012** (found while fixing this; a distinct
     root cause, fixed alongside).

  Tests (3 oracles): added a `_nullable_str()` helper in `test_bsl_metric_parity.py` (mirroring the
  `pd.array(..., dtype="Int64")` style the fixtures already used for nullable integers) and applied
  it to the `latest_status` / `ci_status` fixtures so the legacy anchors receive real `None`;
  normalized the NULL-maintainer **group key** in `test_maintainer_dimension.py`, where the NaN is
  on the *result* side rather than in the fixture.
- **Sweep for other instances:** every other `.isin()` in the atlas source is a *pandas* mask used
  for row filtering, where NaN correctly yields `False` — `ci_red` was the only ibis boolean
  dimension. Of the remaining columns built from lists that can contain `None`
  (`activity_band`, `serial_delta`, `cwe_category`, `epss_score`, `epss_percentile`,
  `pypi_last_serial`), none has a `None`-identity consumer in src or tests, and `_classify_cwe`
  always returns a string (`"Other"` fallback), never `None`. No further sites to fix.
- **Status:** fixed

### AUD-ATLAS-012 — `ci_red` reports an unobserved red default branch on NULL `ci_status` (Medium)
- **Severity:** Medium
- **Category:** Correctness / false-signal
- **Files:** `semantic/metrics.py:135-154` (`ci_red`); surfaced by
  `tests/semantic/test_bsl_metric_parity.py::test_feedstock_health_filters_match_legacy`
- **Finding:** `ci_red` was `t.ci_status.isin(_CI_RED_STATES)` with **no null handling**, so a NULL
  `ci_status` (CI state never observed) yields SQL `NULL` rather than `False`. That NULL reaches the
  dashboard as `NaN` via `load_feedstock_health`, and because **`NaN` is truthy** any downstream
  truthiness check renders an unknown-CI feedstock as **CI-red** — a red default branch we never
  observed. The legacy predicate is a `--filter`, where a NULL simply fails to match and is
  therefore *not* ci-red, so this also broke legacy parity.
  The asymmetry is the tell: both sibling predicates in the very same model coalesce explicitly
  (`has_open_prs` and `has_open_issues` are each `.fill_null(0) > 0`); only `ci_red` did not.
- **Fix:** `t.ci_status.isin(_CI_RED_STATES).fill_null(False)` — restores legacy filter semantics
  and makes the dimension a true two-valued boolean like its siblings.
- **Discovered by:** the AUD-ATLAS-011 investigation. Note this one is **not** a pandas-version
  issue — it is a genuine missing null-coalesce that pandas 3.0 merely made visible.
- **Status:** fixed

---

## pyforge-warden

### AUD-WARDEN-001 — Monorepo root scan cost (High)
- **Severity:** High
- **Category:** Performance / ops
- **Files:** `discovery.py`, `cli.py`
- **Fix:** **Deferred** — document + future scoped discovery; not a one-line code fix.
- **Status:** deferred

### AUD-WARDEN-002 — OSV zip re-scanned per unversioned component (High)
- **Severity:** High
- **Category:** Performance
- **Files:** `vuln.py`, `engines.py`
- **Fix:** Build in-memory index `{pypi_name: advisory_ids}` once per scan from zip.
- **Status:** fixed

### AUD-WARDEN-003 — Deptry `requirements_files` escape scan root (Medium)
- **Severity:** Medium
- **Category:** Security
- **Files:** `engines.py` (`_deptry_requirements_sources`)
- **Fix:** Resolve paths; reject if not under `target.resolve()`.
- **Status:** fixed

### AUD-WARDEN-004 — `OsvEngine` clears `vuln_data` on version-check failure (Medium) — **INVALID, reverted**
- **Severity:** Medium (as originally filed)
- **Category:** Logic
- **Files:** `engines.py`
- **Original finding:** `vuln_data` set to `None` on the version-check / mkstemp / engine-error
  paths even though the OSV DB had already been read by the content pre-flight.
- **Why it is NOT a defect (re-audit 2026-07-26, round 2):** `vuln_data` is the vulnerability
  axis's *provenance-of-assessment* record, not a "did we open the zip" flag. Populating it with
  `max_age_ok=True` on a path where the engine never ran would assert valid vulnerability
  provenance for an axis that was never assessed — precisely the false-green this tool exists to
  prevent. The `None`-on-every-unassessed-path rule is deliberate and is pinned by **7 assertions**:
  `tests/conformance/test_osv_engine.py:178,201,212,454` and
  `tests/unit/test_osv_engine_exit_codes.py:113,137,156`.
- **Resolution:** the round-1 change was **reverted**; all three error paths return `vuln_data=None`
  as originally written. `tests/conformance/test_osv_engine.py::test_out_of_range_version_never_invokes_the_real_osv_scan`
  was red under the round-1 change and is green again after the revert (1936 passed, 0 failed).
- **Status:** wont-fix (original behavior is correct)

### AUD-WARDEN-005 — `--deterministic` no-op vs CAP-10 (Medium)
- **Fix:** **Deferred** — spec/code reconciliation; not a quick fix.
- **Status:** deferred

### AUD-WARDEN-006 — Global DEP001 trust downgrade (Medium)
- **Fix:** **Deferred** — intentional Gap-A tradeoff per architecture.
- **Status:** deferred

### AUD-WARDEN-007 — `--warn-only` / KEV CI misconfiguration (Medium)
- **Fix:** **Deferred** — documentation only.
- **Status:** deferred

### AUD-WARDEN-008 — Duplicate discovery walks (Low)
- **Fix:** **Deferred** — perf pass.
- **Status:** deferred

### AUD-WARDEN-009 — `slow`-marked corpus oracle spins indefinitely in `conda_build` (Medium)
- **Severity:** Medium
- **Category:** Test infrastructure / CI
- **Files:** `tests/conformance/test_extraction_oracle.py` (+ the `slow` marker set run by
  `pyforge-warden-test-corpus-oracle`)
- **Finding:** running the warden suite **without** `-m "not slow"` never terminates. Observed
  spinning at **423s** wall clock, CPU-bound in
  `.pixi/envs/.../conda_build/variants.py:518` (confirmed by `SIGINT` traceback), with **no child
  process** — so it is an in-process compute/loop in `conda_build`'s variant expansion, not a
  subprocess wait. It has no timeout, so in CI it would burn the job's whole budget and report as a
  generic timeout rather than a test failure.
- **Fix:** **Not fixed on this branch** (test-infrastructure scope). Recommended: add
  `pytest-timeout` — it is **not currently installed**, so there is no per-test guard anywhere in
  this repo — and cap the differential oracles, then bound `conda_build`'s variant matrix.
- **Impact on the baseline:** none. The default fast loop (`-m "not slow"`) excludes it and is
  fully green (post-W7e: **1962 passed**). This only bites whoever runs the corpus-oracle task.
- **BMAD pickup:** SEED-WARDEN-009 — story under `pyforge-warden`; ACs: corpus-oracle task completes
  or fails loud within a bounded wall clock; fast loop unchanged.
- **Status:** open (filed, not fixed)

### AUD-WARDEN-010 — `packageurl-python` missing from the conda run-deps; the `.conda` got it only as somebody else's transitive (Medium)
- **Severity:** Medium (latent High — it breaks on a dependency-graph change nobody in this repo controls)
- **Category:** Build / packaging integrity
- **Files:** `src/shared/packages/pyforge-warden/pixi.toml`
- **Finding:** `sbom.py:77` does an unconditional `from packageurl import PackageURL`.
  `packageurl-python` was declared in `pyproject.toml` (so the **wheel** was correct) but was
  **absent** from the member `pixi.toml`'s `[package.run-dependencies]`, so the built `.conda`
  never required it. Installs still worked — but only by luck: `cyclonedx-python-lib` requires
  `packageurl-python (>=0.11,<2)`, so it arrived as an **undeclared transitive**. The moment
  cyclonedx drops it or re-bounds it, a conda install of warden resolves perfectly and then dies at
  `import` time on the user's machine.
- **Why nothing caught it:** the three obvious guards each look the wrong way. `deptry` (including
  warden's own dogfood scan) reads `pyproject.toml`, where the dep was present. The test suite runs
  in the pixi env, where the transitive satisfies the import. `test_engine_version_range_sync.py`
  guards the two *engine* pins only. The sibling `pyforge-marshal` has exactly the right guard
  (`tests/meta/test_manifest_sync.py`, strict pyproject↔pixi set equality) — warden simply never
  got the equivalent.
- **Fix (applied):** added `packageurl-python = "*"` to `[package.run-dependencies]` with a comment
  recording why, and — the durable part — added
  `tests/meta/test_manifest_dependency_parity.py` (5 tests) enforcing that every
  `[project.dependencies]` entry is a conda run-dep, that every run-dep is either declared or in a
  documented `_CONDA_ONLY` allowlist (`python`, `deptry`, `osv-scanner` — the engines are
  subprocess executables, not importable distributions), that shared pins agree, and that the
  allowlist itself cannot be widened into a loophole.
- **Verified:** the guard was **mutation-tested** — commenting the new line out reproduces the
  original defect as a clear failure (`absent from pixi.toml [package.run-dependencies]:
  ['packageurl-python']`) and restoring it goes green, so it is not a vacuous test. The `.conda`
  was rebuilt from scratch (the first build silently reused a cached artifact) and its
  `info/index.json` `depends` now lists `packageurl-python`. Suite: **1941 passed** (1936 + the 5
  new guards). Warden's dogfood scan still exits 0 with no new findings.
- **Status:** fixed

---

## Round-3 — deep re-audit findings (2026-07-26; waves W7–W7e closed 2026-07-26/27)

Sources: four read-only audits (atlas/warden × spec-contract/source) plus a second atlas source
pass. Excluded already-filed items (AUD-ATLAS-001–013, AUD-WARDEN-001–010, AUD-REPO-001).
**Full disposition for every Round-3 ID is in § Handoff → Master disposition matrix.** Wave history:

- **W7** P0 fixed 2026-07-26 (AUD-WARDEN-011…014, AUD-ATLAS-014…018)
- **W7b** P1 fixed 2026-07-26 (AUD-WARDEN-015/016/020, AUD-ATLAS-019…025; also A-033)
- **W7-product** 2026-07-27 (AUD-WARDEN-026–029; AUD-ATLAS-041–049 — demote/stamp/defer)
- **W7c** P2 code 2026-07-27 (warden 017–022/024–025; atlas 026–031/033–035/037–038/040)
- **W7d** process/test-quality 2026-07-27 (AUD-WARDEN-030–031)
- **W7e** deferred closeout 2026-07-27 — IMPLEMENT 023/039; DEMOTE_DOC 028/036; KEEP_DEFER 032/046/049
- **Still residual:** atlas DW-bound 032/046/049; open AUD-WARDEN-009; pre-R3 CFE-003/004 etc.

### Priority triage (historical — used to order W7–W7e; residual work is only the SEED table)

| Priority | IDs | Why | Outcome |
|---|---|---|---|
| **P0 false-green** | AUD-WARDEN-011, 012, 014 | Clean/exit-0 while assessment failed or was bypassed | **fixed** (W7) |
| **P0 security** | AUD-WARDEN-013; AUD-ATLAS-014, 016, 017, 018 | Path escape / arbitrary read-write / unconstrained scan roots | **fixed** (W7) |
| **P0 data-loss** | AUD-ATLAS-015 | Routine runs delete fresh PyPI rows from the store | **fixed** (W7) |
| **P1 security** | AUD-ATLAS-019–022; AUD-WARDEN-020 | Manifest/URL/SSRF/SQL and waiver YAML integrity | **fixed** (W7b) |
| **P1 false-clean / C0** | AUD-ATLAS-023–025; AUD-WARDEN-015–016 | Empty/corrupt security paths look clean | **fixed** (W7b) |
| **P2 perf/correctness** | AUD-ATLAS-028–032; AUD-WARDEN-017–019, 021–025 | Hot loops, coverage lies, finding-id collisions | **fixed** except A-032 KEEP_DEFER (W7c/W7e) |
| **P3 doc/status** | AUD-ATLAS-041–049; AUD-WARDEN-026–031 | Spec claims vs shipped reality | **fixed**/demoted; A-046/049 KEEP_DEFER |

---

### pyforge-warden — Round-3 (code)

### AUD-WARDEN-011 — osv-scanner exit 0/1 + empty parse composes CLEAN (High) — **FALSE GREEN**
- **Severity:** High
- **Category:** Logic / C0
- **Files:** `engines.py` (~1626), `vuln.py` (~1057–1062, ~907–909), `interfaces.py` (~520–524)
- **Finding:** Exit codes 0 and 1 are treated identically as success. Schema-drifted JSON
  (`results` missing/not a list) and package entries with `vulnerabilities[]` but no usable
  `groups[]` both return **0 findings + 0 errors**. Combined with inventory driverless CLEAN rungs
  for `cve_match_level=exact`, known-vulnerable pinned deps can exit 0 with full claimed coverage.
  A unit test currently **encodes** the empty-parse-as-success behavior.
- **Fix:** When `exit_code==1` (or synthesized lines non-empty) and parse yields zero vuln findings,
  emit `ENGINE_OUTPUT_UNPARSEABLE` / axis indeterminate; treat non-empty `vulnerabilities[]` without
  `groups[]` as parse error. Update the locking test.
- **Status:** fixed

### AUD-WARDEN-012 — Hollow KEV/EPSS cache (`{"vulnerabilities":[]}`) disarms gates (High) — **FALSE GREEN**
- **Severity:** High
- **Category:** Logic / C0
- **Files:** `feeds.py` (~217–230, ~370–380), `engines.py` (~1146–1148, ~1223–1225)
- **Finding:** Empty-but-parseable caches load as `{}` (not `None`), so no unavailable/stale finding
  fires. `--fail-on-kev` / `--min-epss` never escalate. Contrasts with OSV's `_db_has_valid_advisory`
  content pre-flight. Ambient test fixtures rely on zero-entry caches.
- **Fix:** Treat zero-entry catalogs as unusable (`None`); give test fixtures ≥1 synthetic entry.
- **Status:** fixed

### AUD-WARDEN-013 — Symlinked manifest file outside scan root is followed and parsed (High)
- **Severity:** High
- **Category:** Security
- **Files:** `discovery.py` (~108–151); reads via `extract/_identity.py`, `license.py`
- **Finding:** Symlinked *directories* fail closed; a symlink to an existing regular file
  (`environment.yml → /tmp/secrets.yml`) is `stat()`-followed, parsed, and appears in the inventory
  / report. Live-confirmed.
- **Fix:** `lstat` + confine resolved target under scan root (mirror deptry `requirements_files`).
- **Status:** fixed

### AUD-WARDEN-014 — `--baseline-emit` proposes whole-axis provenance sentinels (High) — **FALSE GREEN**
- **Severity:** High
- **Category:** Logic / C0
- **Files:** `waiver.py` (~851–860, ~693–701)
- **Finding:** Only `EMPTY_EXTRACTION_DRIVER_ID` is excluded from baseline emit. Fixed ids like
  `indeterminate:vuln-data-stale:vuln-database`, `…:kev-feed`, `…:lts-registry` are proposed;
  committing them permanently bypasses those conditions (rung → BYPASSED, exit 0).
- **Fix:** Exclude all whole-scan provenance subjects (shared frozenset with empty-extraction).
- **Status:** fixed

### AUD-WARDEN-015 — Malformed per-package OSV entries silently dropped (High)
- **Severity:** High
- **Category:** Logic (same class as 011)
- **Files:** `vuln.py` (~894–909, ~1067–1072)
- **Finding:** Shape mismatches return `[]` with no error record; success path still claims coverage.
- **Fix:** Track expected vs parsed packages; zero usable packages → unparseable/indeterminate.
- **Status:** fixed

### AUD-WARDEN-016 — CVSS v3.0 vectors never scored for name-level CRITICAL (Medium)
- **Files:** `vuln.py` (~598–611, ~500–534)
- **Finding:** Accepts `CVSS_V3` type but parser requires `CVSS:3.1/` prefix → under-alerts FR13.
- **Status:** fixed

### AUD-WARDEN-017 — Unbounded OSV zip entry / engine-output reads (Medium)
- **Files:** `vuln.py` zip walks; `engines.py` (~336) engine output `read_bytes`
- **Finding:** No per-entry or NFR-S5 size caps (manifests use `read_bounded_text`).
- **Disposition (2026-07-27):** **IMPLEMENT** — `_read_zip_json_capped` (5 MiB/entry) + `_read_engine_output_text` (20 MiB).
- **Status:** fixed

### AUD-WARDEN-018 — Hygiene synthesis “third bucket” invisible to coverage (Medium)
- **Files:** `hygiene.py` (~272–274), `engines.py` (~1050–1064)
- **Finding:** Components skipped as not hygiene-covered never reach `lines` nor `excluded`;
  `deps_assessed=len(lines)` over-claims vs `deps_total`.
- **Disposition (2026-07-27):** **IMPLEMENT** — hygiene-covered + no `pypi_identity` → `excluded` + `no_identity_hygiene_finding`.
- **Status:** fixed

### AUD-WARDEN-019 — License/Currency engines always claim `deps_assessed=inventory.count` (Medium)
- **Files:** `engines.py` (~1813–1821, ~1858–1870)
- **Disposition (2026-07-27):** **IMPLEMENT** — `deps_assessed` = count of `*_covered`.
- **Status:** fixed

### AUD-WARDEN-020 — Waiver YAML allows duplicate keys; baseline rejects them (Medium)
- **Files:** `waiver.py` (`safe_load` vs baseline `_UniqueKeySafeLoader`)
- **Status:** fixed

### AUD-WARDEN-021 — Name-only indeterminate finding ids suppress every version/ecosystem (Medium)
- **Files:** `interfaces.py` (~536–555)
- **Finding:** `indeterminate:<token>:<name>` lacks `@version` / ecosystem; one waiver covers all.
- **Disposition (2026-07-27):** **IMPLEMENT** — ids use `name@version` / `@unspecified`; dogfood baseline updated.
- **Status:** fixed

### AUD-WARDEN-022 — License axis emits duplicate ids for cross-ecosystem duplicates (Medium)
- **Files:** `license.py` (~790–797); absorbed by policy dedupe
- **Finding:** Coverage claims both assessed; report keeps one. Currency already dedupes.
- **Disposition (2026-07-27):** **IMPLEMENT** — `license_findings` dedupe by id (currency pattern).
- **Status:** fixed

### AUD-WARDEN-023 — Multiple full OSV zip walks per scan (Medium / perf)
- **Files:** `vuln.py` pre-flight + name-level index (+ legacy path)
- **Note:** Related to AUD-WARDEN-002 (index helps unversioned path; pre-flight still separate).
- **Disposition (2026-07-27):** **IMPLEMENT** — `_scan_osv_zip` single walk + one-entry mtime/size cache shared by pre-flight + critical index.
- **Status:** fixed

### AUD-WARDEN-024 — Actuator embeds finding messages (paths) into GitHub PR bodies (Medium)
- **Files:** `actuator.py` (~167–194)
- **Disposition (2026-07-27):** **IMPLEMENT** — PR body uses `Subject:` only (no `finding.message`).
- **Status:** fixed

### AUD-WARDEN-025 — Config validation failure falls back to `EffectiveConfig.default()` (Medium)
- **Files:** `cli.py` (~1093–1104)
- **Finding:** Exit 2 still, but intended CLI gates silently dropped before error recorded.
- **Disposition (2026-07-27):** **IMPLEMENT** — re-apply argparse-validated gates only (not full `default()`).
- **Status:** fixed

### pyforge-warden — Round-3 (spec / CLI surface)

### AUD-WARDEN-026 — PRD `--require-full-coverage` not in CLI (High / spec-drift)
- **Files:** `prd.md`; `cli.py` has `--fail-under-coverage` only
- **Disposition (2026-07-27):** **DEMOTE_DOC** — Story 3.3 Never forbids the flag; PRD/epics demoted to `--fail-under-coverage` only.
- **Status:** fixed

### AUD-WARDEN-027 — PRD `--fail-on-kev` not in CLI; TOML-only (High / spec-drift)
- **Files:** `prd.md`; `config.py` `fail_on_kev`; `test_config.py` asserts no CLI flag
- **Disposition (2026-07-27):** **DEMOTE_DOC** — intentional TOML-only; PRD/epics/story 6.4 title aligned to TOML `fail-on-kev`.
- **Status:** fixed

### AUD-WARDEN-028 — FR34 `runtime_python` report field never shipped (High / spec-drift)
- **Files:** `prd.md`; schema/models — only `!python-runtime` finding exists
- **Disposition (2026-07-27):** **DEMOTE_DOC** — accepted finding-only shape; `spec-6-3` I/O matrix + boundaries updated (no schema widen).
- **Status:** fixed

### AUD-WARDEN-029 — FR38 `license_data` schema slot always null (High / spec-drift)
- **Files:** `report-schema.json`; `report.py` never sets it; tests assert `None`
- **Disposition (2026-07-27):** **DEMOTE_DOC** — reserved nullable (metadata-sourced license axis); schema + FR38 + models comment updated.
- **Status:** fixed

### AUD-WARDEN-030 — Story-spec status drift: 15 of 31 still `draft`/`in-review` (Low / process)
- **Note:** Overlaps AUD-WARDEN-005 (`--deterministic` already deferred). Architecture Gap A /
  FR40 overclaim / epic 6.6 AC tense are doc-only companions — fold into a single doc-sync pass.
- **Disposition (2026-07-27):** **DEMOTE_DOC** — all 31 story specs → `status: shipped` (+ sync
  stamp); PRD Gap A open-item #1 collapsed; NFR-C1 + epic 6.6 AC cite shipped engine ranges;
  review M5 marked resolved (FR40 `actuation`).
- **Status:** fixed

### AUD-WARDEN-031 — Conformance harness masks feed-absence / real license metadata (Medium / test-quality)
- **Files:** `tests/conftest.py` ambient feeds; `test_scan_harness.py` license monkeypatch;
  `test_report_schema.py` exit matrix omits indeterminate pairings
- **Disposition (2026-07-27):** **IMPLEMENT** — keep ambient + Fix 9; add unmasked feed-absence
  + real-metadata license smokes; exit matrix generated from `_LEGAL_EXITS_BY_STATUS`.
- **Status:** fixed

---

### pyforge-atlas — Round-3 (code)

### AUD-ATLAS-014 — `MigrationDetailDataset` path traversal → arbitrary `.json` write (High)
- **Severity:** High
- **Category:** Security
- **Files:** `datasets/migration_status.py` (`_partition_filename`, `_atomic_write`, `migration_names`)
- **Finding:** Remotely-fetched migration keys (incl. `../…`) become partition filenames; parent
  `mkdir` + write escape the data root. Same unvalidated name flows into `_detail_url`.
- **Fix:** Strict slug regex (reuse `wiki._require_safe_segment` / `rag._valid_identifier` pattern).
- **Status:** fixed

### AUD-ATLAS-015 — `pypi_current_versions` overwritten with only eligible delta (High) — **DATA LOSS**
- **Severity:** High
- **Category:** Correctness
- **Files:** `pipelines/pypi_intelligence/nodes.py` (~305–325); `datasets/incremental_parquet.py` save
- **Finding:** Node returns only stale/eligible rows; sink is full overwrite (no merge). Fresh
  packages deleted every run. `stale_mask`/`fresh_mask` have **zero callers**. Propagates into
  `derive_release_velocity`.
- **Fix:** Load+upsert before save, or give `IncrementalParquetDataset.save` merge-on-key semantics.
- **Status:** fixed
  - Landed as catalog `merge_on: pypi_name` on `IncrementalParquetDataset` (Kedro forbids
    same dataset as both node input and output). Cold `load()` of a missing payload returns
    an empty DataFrame.

### AUD-ATLAS-016 — `TransitiveResolverDataset` lacks path confinement of sibling intake (High)
- **Files:** `datasets/sbom_intake.py` (~433–480); shared `sbom_intake_path` catalog param
- **Finding:** After AUD-ATLAS-001 fixed intake, resolver still does raw `Path(...).read_text()`.
- **Status:** fixed

### AUD-ATLAS-017 — F4 `hygiene_source_dir` unconstrained (High)
- **Files:** `pipelines/universal_sbom/gate.py` (~154–178)
- **Status:** fixed

### AUD-ATLAS-018 — MCP `project_path` accepts arbitrary Kedro roots (High)
- **Files:** `mcp/session.py`, `mcp/tools.py` — amplifies AUD-ATLAS-003 (no auth)
- **Status:** fixed

### AUD-ATLAS-019 — `verify_manifest` follows chunk paths without emit-side traversal checks (Medium)
- **Files:** `publish/emitter.py` (~205–211)
- **Status:** fixed

### AUD-ATLAS-020 — BigQuery query via unvalidated `.format(start_ts=…)` (Medium)
- **Files:** `datasets/request_datasets.py` (~375–385)
- **Status:** fixed

### AUD-ATLAS-021 — La Suite `LASUITE_BASE_URL` lacks scheme/host validation (SSRF) (Medium)
- **Files:** `factory/lasuite.py` — contrast `nl/backend.py::_valid_base_url`
- **Status:** fixed

### AUD-ATLAS-022 — PyPI per-project URL built from unsanitized project name (Medium)
- **Files:** `datasets/request_datasets.py` (~190–196)
- **Status:** fixed

### AUD-ATLAS-023 — `per_version_vulns` inner-merge on conda_name vs vdb package_name can empty (Medium)
- **Files:** `pipelines/vulnerability/nodes.py` (~345–358) — false-clean “no vulns”
- **Related:** AUD-ATLAS-004 (empty store vs no vulns)
- **Status:** fixed

### AUD-ATLAS-024 — Corrupt/unreadable VDB → empty DataFrame treated as no vulns (Medium)
- **Files:** `datasets/refresh.py` (~448–460); vuln nodes empty-frame early return
- **Status:** fixed

### AUD-ATLAS-025 — `TransitiveResolverDataset` swallows exceptions as `resolution: unresolved` (Medium)
- **Files:** `datasets/sbom_intake.py` (~454–480) — errors look like intentional AD-13 offline
- **Status:** fixed

### AUD-ATLAS-026 — Dashboard BSL loader masks `TypeError` as empty page (Medium)
- **Files:** `dashboard/data.py` (~86–98)
- **Disposition (2026-07-27):** **IMPLEMENT** — bare `TypeError` re-raises; Ibis subclasses still degrade.
- **Status:** fixed

### AUD-ATLAS-027 — `PYFORGE_ATLAS_DATA_ROOT` + relative parquet can escape intended tree (Medium)
- **Files:** `dashboard/data.py` (~50–66)
- **Disposition (2026-07-27):** **IMPLEMENT** — `default_data_root().resolve()` + `resolve_under_data_root()`.
- **Status:** fixed

### AUD-ATLAS-028 — `enrich_pypi_intelligence` O(N²) concat-in-loop (Medium / perf)
- **Files:** `pipelines/pypi_intelligence/nodes.py` (~503–517)
- **Disposition (2026-07-27):** **IMPLEMENT** — collect rows then one concat; last-wins per `pypi_name`.
- **Status:** fixed

### AUD-ATLAS-029 — Fixed `.tmp` atomic-write race across three datasets (Medium)
- **Files:** `datasets/refresh.py`, `basilisk.py`, `migration_status.py` `_atomic_write`
- **Fix:** Unique temp via `mkstemp`; unlink only on failure; fsync before replace.
- **Disposition (2026-07-27):** **IMPLEMENT** — as above.
- **Status:** fixed

### AUD-ATLAS-030 — `summarize_vdb_vulns` Python groupby loop (Medium / perf)
- **Files:** `pipelines/vulnerability/nodes.py` (~289–306)
- **Disposition (2026-07-27):** **IMPLEMENT** — vectorized `groupby.agg` + critical-high sum.
- **Status:** fixed

### AUD-ATLAS-031 — `IncrementalParquetDataset` with `ttl_seconds=None` treats all rows fresh (Medium)
- **Files:** `datasets/incremental_parquet.py` (~337–338)
- **Disposition (2026-07-27):** **IMPLEMENT** — `ttl_seconds is None` → all-stale (fail-closed).
- **Status:** fixed

### AUD-ATLAS-032 — Full-universe SBOM built via `iterrows()` entirely in memory (Medium)
- **Files:** `pipelines/derived_artifacts/nodes.py` (~37–60) (`build_universe_sbom`)
- **Disposition (2026-07-27):** **KEEP_DEFER** — CPU `iterrows`→zip is not the fix; memory/streaming is. Tracked as **DW-B7-4** in
  `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md`.
- **BMAD pickup:** SEED-ATLAS-032 — `bmad-spec` under `pyforge-atlas`; ACs must require chunked/JSONL
  (or equivalent) emit + catalog/save shape; prove consumers still validate; close DW-B7-4.
- **Reference (not a complete fix):** do not treat a column-`zip` micro-refactor on the branch as done.
- **Status:** deferred

### AUD-ATLAS-033 — `_SAFE_NAME_RE` uses `$` (trailing newline slips) (Low)
- **Files:** `publish/emitter.py` (~62) — use `\Z` like `rag/store.py`
- **Disposition (2026-07-27):** **IMPLEMENT** — already `\Z` (noted in W7b; status closed here).
- **Status:** fixed

### AUD-ATLAS-034 — `DuckdbVssRagStore.__init__` leaks connection on construction failure (Low)
- **Files:** `rag/store.py` (~147–159)
- **Disposition (2026-07-27):** **IMPLEMENT** — `close()` owned conn on `__init__` failure.
- **Status:** fixed

### AUD-ATLAS-035 — `parse_retry_after` treats `NaN` as retry-immediately (Low)
- **Files:** `datasets/rate_limit.py` (~93–98)
- **Disposition (2026-07-27):** **IMPLEMENT** — NaN/Inf → `0.0`.
- **Status:** fixed

### AUD-ATLAS-036 — Event sensor drops late low-`seq` permanently (Low)
- **Files:** `orchestration/event_source.py`
- **Disposition (2026-07-27):** **DEMOTE_DOC** — intentional RSS-cursor semantics (docstring + AD-5 recovery); DW-G3 `audit_note` stamped.
- **Status:** fixed

### AUD-ATLAS-037 — `PanderaValidator` skips when output is not a DataFrame (Low)
- **Files:** `validation.py`
- **Disposition (2026-07-27):** **IMPLEMENT** — registered frame contract + non-frame → `ContractViolation` halt.
- **Status:** fixed

### AUD-ATLAS-038 — SBOM intake reads unbounded file size (Low)
- **Files:** `sbom_intake.py`
- **Disposition (2026-07-27):** **IMPLEMENT** — 10 MiB `_read_intake_text` cap (propagates as `DatasetError`).
- **Status:** fixed

### AUD-ATLAS-039 — `classify_migration_readiness` downloads lookup Python loop (Low / perf)
- **Files:** `vcs_health/nodes.py`
- **Disposition (2026-07-27):** **IMPLEMENT** — `groupby.max()` downloads lookup (classification cartesian unchanged).
- **Status:** fixed

### AUD-ATLAS-040 — `LaSuiteClient.update_document` unvalidated `doc_id` in URL path (Low)
- **Files:** `factory/lasuite.py`
- **Disposition (2026-07-27):** **IMPLEMENT** — `_require_doc_id` slug gate on update/get/parent.
- **Status:** fixed

### pyforge-atlas — Round-3 (spec / AD)

### AUD-ATLAS-041 — SPEC/epics claim 28 CLI pages; shipped dashboard has ~8–9 (High / spec-drift)
- **Disposition (2026-07-27):** **DEMOTE_DOC** — honest-core 8 pages + factory-status; full 28 → DW-D2. Spine FR-9 + D2 `audit_note` updated.
- **Status:** fixed

### AUD-ATLAS-042 — FR-10 / AD-9: `DEFAULT_CONTRACTS` empty; “inline pandera” docs contradict registry (High)
- **Files:** `validation.py`; ARCHITECTURE-SPINE AD-9
- **Disposition (2026-07-27):** **DEMOTE_DOC** — AD-9 rewritten to registry-as-DATA (empty registry intentional).
- **Status:** fixed

### AUD-ATLAS-043 — AD-17: MCP `read_dataset` returns raw rows, no advisory timestamp (High)
- **Files:** `mcp/tools.py`
- **Disposition (2026-07-27):** **IMPLEMENT** — envelope `{dataset, build_stamp, value}`; tests updated.
- **Status:** fixed

### AUD-ATLAS-044 — AD-17: data dashboard pages lack build stamps (only factory-status) (Medium)
- **Files:** `dashboard/app.py`
- **Disposition (2026-07-27):** **IMPLEMENT** — AD-17 stamp on every data/shell page legibility card.
- **Status:** fixed

### AUD-ATLAS-045 — 25/32 story specs status frontmatter drift (`regenerated`/`review`/missing YAML) (Medium)
- **Disposition (2026-07-27):** **DEMOTE_DOC** — all 32 story specs now `status: shipped` (YAML frontmatter).
- **Status:** fixed

### AUD-ATLAS-046 — AD-23: no run-admission / single-writer for concurrent MCP/CLI triggers (High / AD)
- **Files:** `mcp/session.py` (`bootstrapped_session`); spine AD-23 (demoted 2026-07-27)
- **Disposition (2026-07-27):** **KEEP_DEFER** — spine demoted; tracked as **DW-AD23-1** (admission not started —
  shipped = shared Kedro plane only).
- **BMAD pickup:** SEED-ATLAS-046 — file/DB lock or Dagster run-queue across MCP + CLI; concurrent second
  writer must reject/queue; re-promote AD-23 only after proof; close DW-AD23-1.
- **Status:** **fixed 2026-07-29** — the deferral above is history, not live state. pyforge-atlas
  Story 10.6 (`spec-10-6-make-run-admission-real-or-stop-claiming-it.md`) built it:
  `pyforge/atlas/admission.py` + `RunAdmissionHooks` in `settings.HOOKS` take one `filelock` OS
  file lock per output dataset, so a concurrent second writer over an overlapping set is rejected
  (or retried to an explicitly requested finite deadline). Every exit criterion this entry set is
  met: the concurrent second writer is rejected — proven by a two-process gate that spawns a real
  second OS process (`tests/test_admission.py`) — `DW-AD23-1` is closed in the atlas ledger, and
  spine AD-23 was re-promoted only on that proof, with its three residual boundaries carried
  explicitly (single-machine `flock`; process-local release on the Dagster plane; before-hook
  stranding) as `DW-AD23-2`. The Dagster run-queue option was explicitly rejected: it governs only
  daemon-routed runs and would leave every MCP trigger unguarded.

### AUD-ATLAS-047 — SPEC claims credentialed parity sign-off + legacy retirement (High / stale-doc)
- **Evidence:** retirement gate refuses fixture-mode; legacy `conda_forge_atlas.py` still live
- **Disposition (2026-07-27):** **DEMOTE_DOC** — intake/`CLAUDE.md`/B4 `audit_note` qualify shipped ≠ retirement.
- **Status:** fixed

### AUD-ATLAS-048 — Catalog entry count stale in story specs (73 vs live 86) (Medium)
- **Disposition (2026-07-27):** **DEMOTE_DOC** — A2/B6 historical 73 notes; live pin remains `EXPECTED_TOTAL=86`.
- **Status:** fixed

### AUD-ATLAS-049 — F1 attended cold/warm benchmark not delivered; top-level `shipped` overclaims (Medium)
- **Disposition (2026-07-27):** **DEMOTE_DOC** (+ benchmark stays **KEEP_DEFER**/DW-F1-1) — F1/`shipped_scope_note`/`CLAUDE.md` qualified on the reference branch. DuckDB singularity half already shipped.
- **BMAD pickup:** SEED-ATLAS-049 — attended cold/warm run; thresholds fixed in story spec **before** the
  run (SM-3); blocked on DW-B4-2 legacy retirement; operator sign-off closes DW-F1-1.
- **Status:** fixed (docs) / deferred (benchmark)

---

## Implementation waves (this branch)

| Wave | Finding IDs | Scope |
|------|-------------|-------|
| W1 | AUD-CFE-001, 002, 006, AUD-CFE-008, 009, 010, AUD-CFE-005 | CFE path guards, gitignore, hooks, gemini |
| W2 | AUD-ATLAS-002, 006, 007, 008, AUD-ATLAS-001 | Atlas dashboard + datasets + perf |
| W3 | AUD-WARDEN-002, 003, ~~004~~, AUD-CFE-007 | Warden engines + scan_project batch |
| W4 | AUD-CFE-005 | query_atlas hardening |
| W5 | AUD-WARDEN-004 (revert), AUD-ATLAS-011, AUD-ATLAS-012 | Round-2 corrections + pandas-3.0 fixes — see below |
| W6 | AUD-WARDEN-010 | Dependency-completeness sweep across **all 8** `pyforge-*` packages — see below |
| W6b | AUD-REPO-001 | The sweep's auditor became a permanent 58-test gate (`pyforge-deps-test`) |
| W7 | AUD-WARDEN-011…016, 020; AUD-ATLAS-014…025 | Round-3 **P0+P1** — **fixed** (see W7 below); P2 closed in W7c |
| W7-product | AUD-WARDEN-026–029; AUD-ATLAS-041–049 | Product/spec triage — demote docs / thin AD-17 stamps / defer schema+admission+benchmark (2026-07-27) |
| W7c | AUD-WARDEN-017–022, 024–025; AUD-ATLAS-026–031, 033–035, 037–038, 040 | Round-3 **P2 code** — **fixed** (2026-07-27) |
| W7d | AUD-WARDEN-030–031 | Round-3 process + test-quality — **fixed** (2026-07-27) |
| W7e | AUD-WARDEN-023/028; AUD-ATLAS-032/036/039/046/049 | Deferred closeout — implement 023/039; demote 028/036; keep 032/046/049 |

Deferred items remain tracked above for follow-up branches.

### W5 — round-2 re-audit corrections (2026-07-26)

The round-2 re-audit ran the suites through their **canonical pixi tasks** for the first time
(round 1 had invoked `python -m pytest` directly, which silently produced ~21F/17E of pure
environment noise in warden and masked the real signal). That surfaced one self-inflicted
regression and three new findings:

| ID | Change | Outcome |
|----|--------|---------|
| AUD-WARDEN-004 | **Reverted** the round-1 `vuln_data` change | Warden back to **1936 passed / 0 failed** |
| AUD-ATLAS-011 | **Fixed** — pandas 3.0 `None`→`NaN`; 3 production sites + 3 test oracles | fixed |
| AUD-ATLAS-012 | **Fixed** — `ci_red` missing `fill_null(False)` (found via 011) | fixed |
| AUD-ATLAS-010 | **Fixed** — atlas made dependency-complete; `kedro-test` runs standalone | fixed |
| AUD-ATLAS-013 | **Fixed** — misfiled `sentinel` test relocated; 4 dead tests recovered | fixed |
| AUD-WARDEN-009 | Filed — `slow` corpus oracle spins in `conda_build` | open (test-infra scope) |

**Files touched by the AUD-ATLAS-010 dependency-completeness work** (note these are manifests, so
the PR carries the `maintenance` label and the updated `pixi.lock`):

- `src/shared/packages/pyforge-atlas/pyproject.toml` — 21 runtime deps + `mcp`/`nl`/`all` extras
- `src/shared/packages/pyforge-atlas/pixi.toml` — matching conda `[package.run-dependencies]`
- `pixi.toml` — atlas feature reduced to test-only tooling; new `wiki-test` task
- `pixi.lock` — re-solved
- `tests/sentinel/test_sentinel_knowledge.py` — relocated out of the atlas package

**Process lesson:** round 1 marked AUD-WARDEN-004 `fixed` without running the suite through the
canonical task, so a change that contradicted 7 explicit assertions was recorded as a fix. Any
finding whose fix touches emission/provenance semantics must be validated against the package's own
task before being marked `fixed`.

### W6 — dependency-completeness sweep, all 8 `pyforge-*` packages (2026-07-26)

`AUD-ATLAS-010` was found by accident, so the same audit was run deliberately across **every**
`pyforge-*` package in `src/shared/packages/`. Method per package: AST-scan `src/` for third-party
imports, classify each as **hard** (module-level, unconditional) vs **guarded** (inside
`try/except` or a function body), resolve each import name to its distribution name, and diff
against `[project.dependencies]` and `[package.run-dependencies]`. Then the acceptance test that
actually matters — **run the suite in the package's own `no-default-feature` env**.

| Package | Hard imports | pyproject | conda run-deps | Own-env suite | Verdict |
|---|---|---|---|---|---|
| pyforge-atlas | 21 | 21 | 22 | **792 passed**, 19 skipped | complete (W5) |
| pyforge-warden | 6 | 6 | 9 | **1941 passed** | **1 gap → AUD-WARDEN-010, fixed** |
| pyforge-doctor | 0 (pure stdlib) | 1 | 2 | **69 passed** | complete |
| pyforge-herald | 0 (`mcp` lazy) | 1 | 2 | **140 passed**, 2 skipped | complete |
| pyforge-marshal | 0 (pure stdlib) | 4 | 5 | **155 passed** | complete |
| pyforge-mason | 0 (pure stdlib) | 0 | 1 | **11 passed** | complete |
| pyforge-scribe | 2 | 2 | 3 | **18 passed** | complete |
| pyforge-steward | 0 (pure stdlib) | 0 | 1 | **19 passed** | complete |

**3,145 tests pass across the 8 packages, each in its own environment** (+4 repo-level `sentinel`).
Only warden had a real gap. The `run-deps` column exceeds `pyproject` by exactly the documented
conda-only set (`python` everywhere; plus `deptry` + `osv-scanner` for warden).

**Deliberately NOT changed — over-declaration is not a defect here.** Four packages declare deps
they never import at module level, which `deptry` would flag as DEP002. Each was checked and each is
intentional and documented in-file, so removing them would be second-guessing a reviewed decision:
- `pyforge-doctor` (`jsonschema`), `pyforge-marshal` (`jsonschema`, `pyyaml`, `tomlkit`, `psutil`) —
  these packages **ship a JSON schema** for their report envelope; the dep exists for consumers
  validating against it, and the test suites do exactly that.
- `pyforge-herald` (`mcp`) — a genuine run-dep imported **function-locally** (lazy-import pattern,
  `mcp_transport.py:611`), already documented as such in its `pixi.toml`.

**Skip audit (no-false-green check):** every skip across all 8 suites was confirmed **not** to be a
missing Python dependency — otherwise a skip would mask exactly the incompleteness being hunted.
Herald's 2 are an opt-in live-network spike (`HERALD_LIVE_DESIGN=1`); atlas's 19 are DuckDB
**extension** cache (`vss`, `httpfs`) and an unbuilt wasm artifact. Neither is a manifest concern.

**Durable guards added** (the reason this cannot silently regress). The gap class is structural:
`pyproject.toml` and `pixi.toml` duplicate the dependency set by hand with no single source of
truth, so parity needs a tripwire, not vigilance. `pyforge-marshal` already had one; it is now on
the two packages with the most to lose:
- `pyforge-warden/tests/meta/test_manifest_dependency_parity.py` (5 tests, new file)
- `pyforge-atlas/tests/test_scaffold_layout.py` (5 tests appended — 23 hand-duplicated pins, the
  largest exposure in the repo; also pins AC-8, that `pyforge-warden` never becomes a run-dep)

Both were **mutation-tested** rather than merely observed green: dropping a dep and drifting a pin
each produce the intended named failure, and both go green on restore.

### W6b — the auditor itself became a test (`AUD-REPO-001`)

The sweep above was run with a throwaway script, which meant the *method* was one-shot: it would
catch nothing on the next commit. It is now a permanent, parameterized gate — and it closes a hole
the in-package parity tests structurally cannot see.

**The gap the parity tests leave.** Parity only proves the two manifests **agree with each other**.
Add a bare `import httpx` at module level and declare it in neither, and every parity test stays
green while the package is incomplete again — exactly the `AUD-ATLAS-010` shape. Completeness must
be checked against the **code**, not against the other manifest. The two checks compose into the
guarantee that actually matters: *hard imports ⊆ pyproject deps* (completeness) **and** *pyproject
deps ⊆ conda run-deps* (parity) ⟹ the built `.conda` satisfies every unconditional import.

| Artifact | What it is |
|---|---|
| `tests/packaging/test_dependency_completeness.py` | 58 tests: completeness + parity + pins + version, parameterized over all 8 packages |
| `pixi run -e pyforge-ci pyforge-deps-test` | canonical task, ~0.3s |

**Three design choices worth recording:**

1. **Repo-level, glob-discovered — not eight per-package copies.** The failure mode being guarded is
   *someone forgetting*, so the guard must not itself depend on being remembered. It discovers
   `src/shared/packages/pyforge-*`, so a package added next month is covered the day it lands; eight
   hand-copied tests would silently not exist for it. The in-package parity tests
   (warden, atlas, marshal) are kept as deliberate overlap: those fire inside the package's own
   suite, where the author editing it sees them without running a separate task.
2. **Zero third-party imports** — pure `ast` + `tomllib` + `pathlib`. It is wired into the leanest
   env in the repo (`pyforge-ci`, which carries no runtime libraries at all) as the standing proof
   that a dependency audit never needs the dependencies it audits. That also **resolves the W6
   coverage note**: doctor, herald, mason, scribe, and steward are now guarded too, via one
   implementation instead of five near-identical files.
3. **Hard vs deferred is the whole judgement.** Only *unconditional module-level* imports are
   enforced. Imports inside `try/except` (the AD-13 degrade-with-a-hint pattern), a function body
   (lazy import), or `if TYPE_CHECKING` (annotation-only, never executes) are reported but not
   required — that is what makes an extra legitimate. A plain `if` counts as **hard** on purpose: a
   reader cannot prove it is optional, so it should fail loudly rather than be quietly excused.

**Validated in both directions** — a gate is only worth its green tick if its red is real:

| Mutation | Expected | Result |
|---|---|---|
| Undeclare `duckdb` in atlas `pyproject.toml` (still hard-imported) | fail | ✅ 2 failed (completeness + parity) |
| Drop `packageurl-python` from warden conda run-deps (replays AUD-WARDEN-010) | fail | ✅ 1 failed |
| Add bare `import httpx` to `scribe/capture.py` — **the new capability** | fail | ✅ 1 failed |
| Same import behind `try/except ImportError` | **pass** | ✅ 58 passed |
| Same import under `if TYPE_CHECKING:` | **pass** | ✅ 58 passed |
| Same import inside a function body | **pass** | ✅ 58 passed |

The three negative cases matter as much as the positives: a gate that false-fires on the repo's own
legitimate optional-import patterns gets disabled, and then guards nothing.

**Vacuity guards.** Because every assertion is parameterized over discovered packages, a broken glob
would collapse the suite to zero cases and report success. Three tests exist solely to prevent that:
discovery must find all 8 known packages, each must have both manifests, and each must have a
non-empty `src/` to scan. A fourth rejects `MODULE_ALIASES` entries that merely restate PEP 503
normalization, so the alias table cannot rot into noise.

**Import-name resolution** is a curated `MODULE_ALIASES` table (9 entries — `yaml`→`pyyaml`,
`attr`→`attrs`, `google`→`protobuf`, `ibis`→`ibis-framework`, `a2a`→`a2a-sdk`,
`packageurl`→`packageurl-python`, `cyclonedx`→`cyclonedx-python-lib`,
`openlineage`→`openlineage-python`, `opentelemetry`→{api,sdk}) plus PEP 503 identity. Deliberately
**not** `importlib.metadata.packages_distributions()`: that would make the result depend on which
env happens to be running and would need the deps installed. An unresolvable module fails with an
instruction to add the mapping — noise, never silence.

**Scratch retired:** `.cursor/depcheck.py` was deleted; this test supersedes it.

**Not wired into CI — flagged, not decided.** No workflow in `.github/workflows/` runs any pyforge
suite today (CI here is inherited staged-recipes recipe-building), and there is no pre-commit
config. So this gate runs when the task is invoked, not automatically on push. Adding a `src/`-scoped
workflow is a real scope decision — note CLAUDE.md's PR gate: any change outside `recipes/` needs
the `maintenance` label.

### W7 — Round-3 P0 cluster (2026-07-26)

Closed the false-green / path-escape / data-loss P0 set from the Round-3 intake:

| ID | Fix |
|----|-----|
| AUD-WARDEN-011 | OSV empty-parse / exit-1 → `ENGINE_OUTPUT_UNPARSEABLE` (no silent CLEAN) |
| AUD-WARDEN-012 | Hollow KEV/EPSS caches → `None`; ambient fixtures seed ≥1 synthetic CVE |
| AUD-WARDEN-013 | Manifest discovery: `lstat` + confine symlink targets under scan root |
| AUD-WARDEN-014 | `--baseline-emit` excludes whole-axis provenance sentinels |
| AUD-ATLAS-014 | Migration names: strict slug regex before partition write / URL |
| AUD-ATLAS-015 | `IncrementalParquetDataset(merge_on=…)` upserts Phase H eligible delta |
| AUD-ATLAS-016 | `TransitiveResolverDataset` reuses `_resolve_intake_path` confinement |
| AUD-ATLAS-017 | F4 `hygiene_source_dir` confined under allowlist (package / cwd / tmp) |
| AUD-ATLAS-018 | MCP `project_path` pinned to atlas `PROJECT_ROOT` |

**Verified:** `pyforge-warden-test` → **1946 passed**; `kedro-test` → **801 passed**, 19 skipped.

### W7b — Round-3 P1 security + false-clean (2026-07-26)

| ID | Fix |
|----|-----|
| AUD-ATLAS-019 | `verify_manifest` confines chunk paths under site root |
| AUD-ATLAS-020 | BigQuery `start_ts`/`end_ts` strict ISO-UTC before `.format` |
| AUD-ATLAS-021 | `LASUITE_BASE_URL` requires `http(s)` + host |
| AUD-ATLAS-022 | PyPI/anaconda path segments sanitized |
| AUD-ATLAS-023 | `per_version_vulns` join miss falls back to unscoped (no false-clean) |
| AUD-ATLAS-024 | Corrupt VDB raises `DatasetError` (absent still AD-13 empty) |
| AUD-ATLAS-025 | Resolver path-escape re-raises `DatasetError` (not offline) |
| AUD-WARDEN-015 | All-malformed OSV packages → `ENGINE_OUTPUT_UNPARSEABLE` |
| AUD-WARDEN-016 | Accept `CVSS:3.0` and `CVSS:3.1` prefixes for base scoring |
| AUD-WARDEN-020 | Waivers load via `_UniqueKeySafeLoader` (same as baseline) |

Also fixed AUD-ATLAS-033 (`_SAFE_NAME_RE` `$` → `\Z`) while touching emitter.

**Verified:** `pyforge-warden-test` → **1947 passed**; `kedro-test` → **805 passed**, 19 skipped.
W7c closed the P2 code cluster (below); W7d closed process/test-quality (030–031).
Still deferred (DW): atlas 032/046/049.

### W7c — Round-3 P2 code (2026-07-27)

| ID | Fix |
|----|-----|
| AUD-WARDEN-017 | Cap OSV zip entries (5 MiB) + engine output (20 MiB) |
| AUD-WARDEN-018 | Hygiene no-identity → excluded + finding |
| AUD-WARDEN-019 | License/Currency `deps_assessed` = `*_covered` count |
| AUD-WARDEN-021 | Indeterminate ids `name@version` / `@unspecified` (+ dogfood baseline) |
| AUD-WARDEN-022 | License findings dedupe by id |
| AUD-WARDEN-024 | Actuator PR body: `Subject:` only (no paths) |
| AUD-WARDEN-025 | Config double-fail keeps argparse-validated gates |
| AUD-ATLAS-026 | BSL loader: bare `TypeError` re-raises |
| AUD-ATLAS-027 | Dashboard data-root resolve + confinement |
| AUD-ATLAS-028 | Enrich: collect + one concat |
| AUD-ATLAS-029 | Unique `mkstemp` atomic writes |
| AUD-ATLAS-030 | `summarize_vdb_vulns` vectorized groupby |
| AUD-ATLAS-031 | `ttl_seconds=None` → all-stale |
| AUD-ATLAS-033 | Emitter `\Z` (already done; status closed) |
| AUD-ATLAS-034 | RAG store closes owned conn on init failure |
| AUD-ATLAS-035 | `parse_retry_after` NaN/Inf → 0.0 |
| AUD-ATLAS-037 | Pandera non-DataFrame → halt |
| AUD-ATLAS-038 | SBOM intake 10 MiB size cap |
| AUD-ATLAS-040 | LaSuite `doc_id` URL slug gate |

**Originally deferred in W7c (later closed in W7e):** AUD-WARDEN-023, AUD-ATLAS-036, AUD-ATLAS-039 implemented or demoted; AUD-ATLAS-032 remains KEEP_DEFER (DW-B7-4).

**Verified (W7c tip):** `pyforge-warden-test` → **1947 passed**; `kedro-test` → **809 passed**, 19 skipped.

### W7d — Round-3 process + test-quality (2026-07-27)

| ID | Fix |
|----|-----|
| AUD-WARDEN-030 | All 31 story specs `status: shipped`; Gap A / FR40 / epic 6.6 AC doc sync |
| AUD-WARDEN-031 | Feed-absence + real-metadata smokes; exit matrix from `_LEGAL_EXITS_BY_STATUS` |

**Verified:** `pyforge-warden-test` → **1961 passed**; `kedro-test` → **809 passed**, 19 skipped.

### W7e — Deferred closeout (2026-07-27)

| ID | Disposition |
|----|-------------|
| AUD-WARDEN-023 | **IMPLEMENT** — `_scan_osv_zip` + mtime cache |
| AUD-WARDEN-028 | **DEMOTE_DOC** — finding-only `!python-runtime` accepted |
| AUD-ATLAS-032 | **KEEP_DEFER** — DW-B7-4 streaming BOM |
| AUD-ATLAS-036 | **DEMOTE_DOC** — intentional cursor; DW-G3 note |
| AUD-ATLAS-039 | **IMPLEMENT** — downloads `groupby.max` |
| AUD-ATLAS-046 | ~~**KEEP_DEFER** — DW-AD23-1~~ → **FIXED 2026-07-29** by atlas Story 10.6; DW-AD23-1 closed, AD-23 re-promoted on a two-process gate |
| AUD-ATLAS-049 | **KEEP_DEFER** — DW-F1-1 (docs already closed) |

**Verified:** `pyforge-warden-test` → **1962 passed**; `kedro-test` → **809 passed**, 19 skipped.

## Verification

### Canonical test commands (use these — not a bare `python -m pytest`)

| Package | Command | Notes |
|---|---|---|
| pyforge-warden | `pixi run -e pyforge-warden pyforge-warden-test` | Fast loop, `-m "not slow"`. **Requires** `osv-scanner` + `deptry` on `PATH`; the suite deliberately *errors* (never skips) when they are absent, so a bare `python -m pytest` in another env produces ~21F/17E of pure environment noise. |
| pyforge-warden (slow) | `pixi run -e pyforge-warden pyforge-warden-test-corpus-oracle` | The `slow`-marked corpus/differential oracles. See AUD-WARDEN-009 — one of these effectively hangs. |
| pyforge-atlas | `pixi run -e pyforge-atlas kedro-test` | Self-contained since AUD-ATLAS-010. |
| sentinel (repo-level) | `pixi run -e local-recipes wiki-test` | Covers `sentinel.*`, not atlas (AUD-ATLAS-013). |

Since `AUD-ATLAS-010`, **the pixi tasks are sufficient** — no manual `PYTHONPATH`/`PATH` wrangling.
Running atlas by hand with a bare interpreter still works but needs all three of the following, and
each one silently *inflates* the failure count if forgotten (this is what made round 1 misread its
own baseline):

```bash
PYTHONPATH=src/shared/packages/pyforge-atlas/src:src/shared/packages/pyforge-warden/src \
PATH="$PWD/.pixi/envs/local-recipes/bin:$PATH" \
  .pixi/envs/local-recipes/bin/python -m pytest src/shared/packages/pyforge-atlas/tests -q
```

1. **Env** — `local-recipes` (or now `pyforge-atlas`, which is dependency-complete).
2. **`PYTHONPATH`** — `pyforge-warden` must be importable, or the 15 F4 policy-gate tests error
   with `ModuleNotFoundError: No module named 'pyforge.warden'` (by design, per AD-12: the
   `ComplianceReport` schema is imported, never vendored).
3. **`PATH`** — the pixi `bin` must be on `PATH` or
   `test_policy_gate.py::test_unused_dep_fixture_yields_hygiene_finding_in_report` fails looking
   for the `deptry` binary. This is the difference between an 8-failure and a 7-failure run.

One environment precondition remains for a fully green atlas run — the Playwright browser binary,
which is not a conda artifact:

```bash
pixi run -e pyforge-atlas python -m playwright install chromium-headless-shell
```

### Measured baseline (2026-07-26, round-2 re-audit — final)

| Suite | Before round 2 | After round 2 |
|---|---|---|
| pyforge-warden (fast) | 1935 passed, **1 failed** | **1936 passed, 0 failed** |
| pyforge-atlas | 780 passed, **7 failed**, 19 skipped | **787 passed, 0 failed**, 19 skipped |

How each delta was closed:
- **Warden's 1 failure** was self-inflicted by round 1 (`AUD-WARDEN-004`) and is gone after the
  revert.
- **6 of atlas's 7** were the pandas 3.0 `None`→`NaN` cluster, fixed under `AUD-ATLAS-011`
  (3 production sites + 3 test oracles) and `AUD-ATLAS-012` (`ci_red` null-coalesce).
  All 6 were first confirmed **pre-existing** by stashing every branch edit and re-running against
  the pristine tree, so none was a regression from this branch.
- **The 7th**, `test_dashboard_e2e_navigation_and_rendering`, needed the Playwright browser binary:
  `python -m playwright install chromium-headless-shell`. Environmental, not a code defect.

A one-time environment provisioning step is therefore required for a green atlas run:

```bash
PATH="$PWD/.pixi/envs/local-recipes/bin:$PATH" \
  .pixi/envs/local-recipes/bin/python -m playwright install chromium-headless-shell
```

---

## Spec closure stamp (2026-07-27)

| Check | State |
|---|---|
| Round-3 P0–P2 + product + process waves (W7–W7e) | **Complete** on reference branch |
| Residual KEEP_DEFER | AUD-ATLAS-032, 046, 049 (DW-bound) |
| Residual open | AUD-WARDEN-009 only |
| Residual CFE deferred (pre-R3) | AUD-CFE-003, 004 (+ older atlas/warden deferred per finding bodies) |
| This Spec usable without merging the PR | **Yes** — dispositions, BMAD seeds, file map, and suite oracles above |
| Next human action if shipping the branch | Commit → regenerate `environment.yaml` → PR + `maintenance` label → optional CFE Rule-2 retro |

**Do not** mark residual DWs as fixed in project story specs until their SEED stories close the named DW entries.

---

# Incorporation record — 2026-07-27

> **Added by a separate effort, after the fact. Everything above this line is the
> independent auditor's own work and is left exactly as written. Everything below is
> disposition: what was verified, what was incorporated, and what remains open.**

## 1. The branch is abandoned — read every `Status:` above as branch-scoped

`fix/code-audit-remediation-2026-07-26` (PR #131) **will never be merged.** That single fact
invalidates the status line on almost every finding above.

Those `Status: fixed` lines mean *fixed on the reference branch*. They were accurate when
written. They are **not** statements about `main`. With the branch abandoned, the remediation
described in waves W1–W7e **does not exist in the shipped tree**, and this document is the only
surviving record that the findings were ever made.

**Nothing above should be read as "already handled" without checking the table in § 3.**

## 2. How status-on-main was determined

Two independent methods, both mechanical:

1. **File cross-reference (covers 29 findings).** Every remediation on that branch necessarily
   modified a file. If a finding's `Files:` appear in PR #131's changed-file list, its fix is
   branch-only and the finding is therefore **OPEN on `main`**. This is a proof, not a heuristic.
2. **Direct inspection on `main` (covers the remainder).** Targeted checks against the live
   tree.

Confirmed open by direct inspection, with evidence:

| ID | Evidence gathered on `main` |
|---|---|
| `AUD-ATLAS-010` | `kedro-test` fails with **17 collection errors** — `duckdb`, `ibis`, `openlineage`, `pandera`, `playwright`, `vizro` all unimportable |
| `AUD-ATLAS-013` | `tests/factory/test_sentinel_knowledge.py` still inside the package; it is the `No module named 'sentinel'` collection error |
| `AUD-ATLAS-014` | no traversal guard in `datasets/migration_status.py` |
| `AUD-ATLAS-029` | fixed `.tmp` still present in `migration_status.py`, `refresh.py`, `basilisk.py` — the three datasets the finding names |
| `AUD-ATLAS-033` | `publish/emitter.py:62` — `_SAFE_NAME_RE = re.compile(r"^[^/\\]+$")`; `$` matches before a trailing newline, so `"foo\n"` slips |
| `AUD-ATLAS-030` | Python `groupby` loop still in `pipelines/vulnerability/nodes.py` |
| `AUD-ATLAS-032` | `iterrows()` still in `pipelines/universal_sbom/nodes.py` |
| `AUD-ATLAS-046` | `conf/base/dagster.yml` declares only the `in_process` executor; no lock or queue anywhere in the package |

## 3. Disposition of the 49 `AUD-ATLAS-*` findings

Scope note: **pyforge-atlas only.** The `AUD-CFE-*` and `AUD-WARDEN-*` findings were out of
scope for this effort and carry **no** disposition here — they remain as the auditor left them,
and are equally branch-abandoned.

| Status on `main` | Count | Meaning |
|---|---|---|
| **INCORPORATED** | 5 | Landed on `main` by this effort |
| **REFUTED** | 1 | Re-verified and found not to be a defect as stated |
| **OPEN** | 43 | Real, unlanded; becomes backlog |

### 3.1 Incorporated (landed on `main`, 2026-07-27)

| ID | What landed |
|---|---|
| `AUD-ATLAS-010` | **The blocker — resolved.** The package declared 3 run-deps while `pyforge.atlas` hard-imports **19** third-party modules at module level (derived by AST scan, not from this document's list). Declared the real set in the member `pixi.toml` run-dependencies + `pyproject.toml`, floors pinned to the versions resolved in the working env. Result: `kedro-test` went from **17 collection errors / 0 tests runnable** to **781 passed, 6 failed, 19 skipped**. `kedro-catalog-check` 47/47. |
| `AUD-ATLAS-013` | The misfiled `test_sentinel_knowledge.py` imported `sentinel.knowledge.*` — a different project entirely (`src/sentinel`), almost certainly copy-misfiled during H3, which shares the `LaSuiteClient`/`WikiSyncer` names. `git mv`'d to `src/sentinel/tests/test_knowledge.py`, history preserved. |
| `AUD-ATLAS-046` | The severe one. SPEC § Constraints, `ARCHITECTURE-SPINE` AD-23, `epics.md`, `spec-c1` (×2) and `orchestration/definitions.py:26` **all asserted run admission that was never implemented**. Every occurrence retracted; AD-23 demoted with re-promotion gated on a passing gate; tracked `DW-AD23-1`. |
| `AUD-ATLAS-041` | SPEC CAP-8 corrected: 8 pages ship + factory-status; full 28-CLI inventory deferred (`DW-D2-1`). |
| `AUD-ATLAS-047` | SPEC § Success signal corrected — parity **harness** delivered, but the credentialed run, sign-off and legacy retirement have **not** happened; `conda_forge_atlas.py` still live. |
| `AUD-ATLAS-049` | `shipped_scope_note` added to SPEC frontmatter + `gate-contract.md` marked all three attended events outstanding. |
| `AUD-ATLAS-048` | Live catalog count (86) is authoritative in `catalog-contract.md`; the historical 73 in `spec-a2`/`spec-b6` is labelled historical. |

**Where these landed is not where the audit looked.** The pyforge-atlas **Spec kernel**
(`specs/spec-pyforge-atlas/SPEC.md`) and its four peer companions were authored on 2026-07-27 —
*after* this audit ran. PR #131 touches none of them. The kernel had inherited the same
overclaims from the same sources, and in the AD-23 case stated the false safety property **more
confidently** than the spine did. That is why these five were re-fixed at a location the audit
could not have covered.

### 3.2 Refuted

| ID | Why |
|---|---|
| `AUD-ATLAS-042` | `validation.py:45–49` **already documents** the empty `DEFAULT_CONTRACTS` registry as deliberate ("F2 delivers the machinery + seam, not speculative contracts"). The registry being empty is the design, not drift. Any real drift is confined to `ARCHITECTURE-SPINE` AD-9 wording. No code defect. |

### 3.3 Operator decision recorded

| ID | Decision |
|---|---|
| `AUD-ATLAS-045` | The audit proposed uniform `status: shipped` YAML on all 32 story specs. 12 are **verbatim recovered originals with no frontmatter by design**. Operator chose **uniform frontmatter on all 32** (2026-07-27), accepting that the 12 are no longer byte-faithful; each will note that frontmatter was added post-recovery and the body below is verbatim. Scheduled as story I2. |

### 3.4 Open — the backlog

All 43 remaining atlas findings are **open on `main`** and are being re-derived as BMAD stories
rather than recovered from the dead branch. Sequencing:

- **`AUD-ATLAS-010` / `AUD-ATLAS-013` are the blocker and run first.** `kedro-test` cannot
  collect its own suite on `main`, so the bmad-loop `[verify]` gate cannot pass for *any* atlas
  story until dependency-completeness is restored. No other code story can be verified before
  this lands.
- `AUD-ATLAS-043` / `-044` (AD-17 envelope + per-page build stamps) and `AUD-ATLAS-046`'s
  implementation half (`DW-AD23-1` run admission) follow.
- The remaining ~38 are triaged into subsequent epics, each verified against `main` at story
  authoring time — **not** trusted from the status lines above.

## 4. Standing instruction for future readers

1. **Never trust a `Status:` line above** without re-checking `main`. They describe a branch
   that no longer exists.
2. **Re-verify before implementing.** Some findings may have been independently fixed since
   2026-07-26; others may have drifted further.
3. This effort verified 8 findings by direct inspection and 29 by file cross-reference. The
   rest are inferred open by the same branch-abandonment logic and are marked for
   verification at story-authoring time.

## 5. Findings surfaced *by* the remediation (not in the original audit)

Two defects found while fixing `AUD-ATLAS-010`. Neither appears above; both are recorded here
because this document is the durable record.

### AUD-ATLAS-050 — `semantic/models.py` hard-imports a PyPI-only package (Medium)

`boring_semantic_layer` is one of the Spec's **two recorded PyPI-only exceptions** (with
`kedro-mcp`) and has no conda-forge candidate — declaring it as a conda run-dep fails the solve
outright on `osx-arm64-min`. But `semantic/models.py` imports it at **module level**, so
**a pure-conda install of `pyforge-atlas` cannot import that module.** Supplying it to the env
(`[feature.pyforge-atlas.pypi-dependencies]`) unblocks the gate but does not close this: a
dependency line cannot fix it. The real fix is a lazy or guarded import. **Status: OPEN.**

### AUD-ATLAS-051 — conda `playwright` ships no Python module (Low, but a live trap)

conda-forge `playwright` is the **CLI/browser driver only** (`bin/playwright`, nothing in
`site-packages`); the `import playwright` bindings are the separate **`playwright-python`**
package. Declaring only the former **resolves cleanly and still fails at import** — which is
precisely how it stayed hidden. Both are now declared. This is the repo's known
PyPI↔conda mapping trap (try bare / hyphen↔underscore / `-py` / `-python` before concluding a
package is missing). **Status: FIXED.**

### Empirical confirmation of `AUD-ATLAS-011`

Fixing the collection blocker made this finding **directly observable for the first time**. Of
the 6 remaining test failures, the representative one is exact:

```
src = pd.DataFrame({"conda_name": ["a","b"], "feedstocks": [["a"], np.nan]})
>       assert m["b"] is None   # NaN cell -> None, no crash
E       assert nan is None
```

That is `AUD-ATLAS-011` (pandas 3.0 `str` dtype coercing `None` → `NaN`, breaking
None-identity contracts) reproducing on `main`. It is **confirmed OPEN**, is not fixed here —
that is its own story — and the 6 failures are the ready-made regression set for it.
