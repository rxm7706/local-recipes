---
id: SPEC-code-audit-remediation-2026-07-26
spec: code-audit-remediation
status: in-progress
owner-dream: n/a
program: regenerable-factory
surface:
  - .claude/skills/conda-forge-expert/**
  - .claude/tools/**
  - .claude/hooks/**
  - src/shared/packages/pyforge-atlas/**
  - src/shared/packages/pyforge-warden/**
  - .gitignore
sources:
  - Cursor codebase audit session 2026-07-26 (conda-forge-expert MCP layer, pyforge-atlas, pyforge-warden)
---

# Code audit remediation — consolidated findings & fix map

Traceability contract: every implementation commit references one or more **Finding IDs**
(`AUD-<area>-<nnn>`). Status values: `open` | `in-progress` | `fixed` | `deferred` | `wont-fix`.

## Summary

| Area | High | Medium | Low | Fixed (this branch) |
|------|------|--------|-----|---------------------|
| CFE / MCP (`.claude/`) | 4 | 6 | 5 | 7 |
| pyforge-atlas | 2 | 6 | 4 | 5 |
| pyforge-warden | 4 | 6 | 4 | 3 |
| Cross-cutting | 0 | 2 | 1 | TBD |

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
- **Status:** deferred

### AUD-CFE-004 — SSRF via recipe hash/download URLs (High)
- **Severity:** High
- **Category:** Security
- **Files:** `recipe_editor.py`, `recipe-generator.py`
- **Finding:** `requests.get(url)` with no host/scheme allowlist.
- **Fix:** **Deferred** — needs enterprise URL policy module shared with `_http.py`.
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

### AUD-WARDEN-004 — `OsvEngine` clears `vuln_data` on version-check failure (Medium)
- **Severity:** Medium
- **Category:** Logic
- **Files:** `engines.py`
- **Fix:** Preserve `vuln_data` when DB was already read pre-flight.
- **Status:** fixed

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

---

## Implementation waves (this branch)

| Wave | Finding IDs | Scope |
|------|-------------|-------|
| W1 | AUD-CFE-001, 002, 006, AUD-CFE-008, 009, 010, AUD-CFE-005 | CFE path guards, gitignore, hooks, gemini |
| W2 | AUD-ATLAS-002, 006, 007, 008, AUD-ATLAS-001 | Atlas dashboard + datasets + perf |
| W3 | AUD-WARDEN-002, 003, 004, AUD-CFE-007 | Warden engines + scan_project batch |
| W4 | AUD-CFE-005 | query_atlas hardening |

Deferred items remain tracked above for follow-up branches.

## Verification

- CFE: existing skill tests + manual MCP path rejection
- Atlas: `pytest tests/dashboard/test_dashboard_dryrun.py`
- Warden: `pytest tests/unit/test_osv_engine*.py tests/unit/test_engine_env_deptry.py`
