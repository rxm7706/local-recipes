---
doc_type: sprint-change-proposal
project_name: local-recipes
date: 2026-05-13
author: rxm7706
trigger_type: release-driven
trigger_release: conda-forge-expert v8.0.0
scope: documentation-sync
classification: Minor (Wave A+B+D shipped; Wave C deferred)
mode: Batch
status: approved
approved_by: rxm7706
approved_date: 2026-05-13
input_docs:
  - _bmad-output/projects/local-recipes/planning-artifacts/PRD.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-cf-atlas.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-conda-forge-expert.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-mcp-server.md
  - _bmad-output/projects/local-recipes/planning-artifacts/epics.md
  - _bmad-output/projects/local-recipes/planning-artifacts/source-tree-analysis.md
  - _bmad-output/projects/local-recipes/planning-artifacts/project-parts.json
  - _bmad-output/projects/local-recipes/implementation-artifacts/spec-conda-forge-expert-v8.0.md
  - _bmad-output/projects/local-recipes/implementation-artifacts/retro-conda-forge-expert-v8.0-2026-05-13.md
  - _bmad-output/projects/local-recipes/implementation-artifacts/retro-atlas-pypi-universe-split-2026-05-13.md
  - .claude/skills/conda-forge-expert/CHANGELOG.md
ground_truth:
  - .claude/skills/conda-forge-expert/CHANGELOG.md
  - .claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py
  - .claude/skills/conda-forge-expert/scripts/bootstrap_data.py
  - .claude/skills/conda-forge-expert/reference/atlas-phases-overview.md
  - .claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md
  - .claude/skills/conda-forge-expert/guides/atlas-operations.md
  - .claude/skills/conda-forge-expert/config/skill-config.yaml
prior_proposal: sprint-change-proposal-2026-05-13.md
---

# Sprint Change Proposal: v8.0.0 Structural Enforcement + Persona Profiles Sync

## 1. Issue Summary

The `conda-forge-expert` skill shipped **v8.0.0** on 2026-05-13, closing 3 of the 4 deferred v7.9.0 follow-ups via `docs/specs/conda-forge-expert-v8.0.md` (driven by `bmad-quick-dev`). Wave C (drop `vuln_total`) was deferred mid-implementation after consumer audit found 4 actual consumers; the original v7.9.0 retro has been corrected.

**MAJOR bump trigger**: `bootstrap-data --profile maintainer` is the new documented default. No invocations break (legacy no-flag runs print an end-of-run advisory recommending the profile flag; suppress via `BUILD_CF_ATLAS_QUIET=1`).

Substantive deltas:

- **Wave A — `v_actionable_packages` view + structural enforcement** — Schema v21 ships a SQL view encoding the canonical persona-filter triplet (`conda_name IS NOT NULL AND latest_status='active' AND COALESCE(feedstock_archived,0)=0`). 7 phase selectors refactor to `FROM v_actionable_packages`. New `tests/meta/test_actionable_scope.py` parses `conda_forge_atlas.py` and asserts every `SELECT ... FROM packages WHERE ...` either reads the view OR has a `# scope:` justification comment. Prevents drift like the v7.9.0 audit had to fix by hand.
- **Wave B — Phase H serial-aware eligible-rows gate** — Schema v21 adds `pypi_version_serial_at_fetch INTEGER` column + index on `packages`. Phase H's pypi-json worker stamps the serial on every successful fetch; eligible-rows SELECT becomes a 3-condition OR (never-fetched OR serial-moved OR 30 d safety re-check). **Warm-daily Phase H drops ~5 min → ~30 s** on a typical day (~30-100 packages whose serial moved).
- **Wave C DEFERRED** — `vuln_total` drop was specced on v7.9.0 audit's "0 consumers" claim, which was wrong. The v8.0.0 audit found 4 consumers: `detail_cf_atlas:827`, `cve_watcher:71`, `staleness_report:110/182`, `scan_project:1408/2672/2690/3293/3311`. Column stays. v7.9.0 retro corrected with consumer list. Future spec should consolidate consumers behind a single accessor before deciding drop-vs-keep.
- **Wave D — Persona profiles + auto-detection** — `bootstrap_data.py` ships `PROFILES` dict + `--profile {maintainer,admin,consumer}` argparse flag + `_auto_detect_gh_user(timeout=5)` (5 s; graceful degradation) + `_auto_detect_phase_l_sources(maintainer, db_path)` (queries `v_actionable_packages JOIN package_maintainers` for populated registries in scope) + `_print_no_profile_advisory(profile)`. Profile resolution merges via `os.environ.setdefault` so explicit user env vars and CLI flags always win. Maintainer profile auto-derives `PHASE_N_MAINTAINER` from `gh api user --jq .login` and auto-restricts `PHASE_L_SOURCES`; admin runs channel-wide Phase N; consumer pins F=s3-parquet, H=cf-graph, skips Phase N + Phase D universe upsert.
- **Catalog flips** — `atlas-actionable-intelligence.md` flips 5 previously 📋-open Phase-N-gated rows to ✅ shipped (open human PRs, open issues, ci-red filter, abandonment composite, maintainer last-active). Status Summary updated: ~65 shipped (up from ~60), ~6 open (added vuln_total-consumer-consolidation + per-user contributionsCollection items), 0 gaps.

## 2. Impact Analysis

| Aspect | Pre-v8.0.0 (v7.9.0) | Post-v8.0.0 | Delta |
|---|---|---|---|
| Schema version | 20 | 21 | +1 (view + serial column added; vuln_total column kept) |
| Phase selectors using canonical triplet | 9 (via explicit clauses) | 9 (via view; explicit clauses dropped) | Structural enforcement landed |
| Meta-tests | 4 (test_actionable_scope NEW) | 5 | +1 (drift gate) |
| Phase H warm-daily wall-clock | ~5 min (TTL-only) | ~30 s (serial-aware gate) | -90% on typical days |
| `bootstrap-data` CLI surface | 13 flags | 14 flags (`--profile`) | +1 |
| Documented default invocation | `bootstrap-data` (no flag) | `bootstrap-data --profile maintainer` | UX shift; no break |
| Backward-compat invocations | — | All invocations work; advisory print for no-flag | Soft launch |
| New persona profiles | 0 | 3 (maintainer, admin, consumer) | New UX surface |
| Auto-detection helpers | 0 | 2 (`_auto_detect_gh_user`, `_auto_detect_phase_l_sources`) | New |
| Catalog ✅ shipped count | ~60 | ~65 | +5 (all Phase-N-gated) |
| Catalog 📋 open count | ~5 | ~6 | +1 (vuln_total consolidation; -5 from flips, +6 net additions including per-user activity API) |
| Skill MCP tool count | 36 | 36 | Unchanged (profiles are CLI-only; MCP exposure deferred) |
| Skill test count | 432 | 989 passing (incl. unrelated tests; +24 new in v8.0.0) | +24 (19 persona + 5 serial-gate) |
| `cf_atlas.db` size delta | — | Adds ~96 KB (12k INTEGER `pypi_version_serial_at_fetch` rows); view is zero-storage | +96 KB (vuln_total NOT dropped, so no ~10 MB savings as originally planned) |

## 3. Affected Artifacts (sync targets)

- ✅ `PRD.md` — v1.1.1 → v1.2.0; source_pin → `conda-forge-expert v8.0.0`; edit-history line; R1 updated.
- ✅ `architecture-cf-atlas.md` — schema v21 documented; Phase H serial-gate behavior; `v_actionable_packages` view; vuln_total Wave C deferral note.
- ✅ `architecture-conda-forge-expert.md` — skill version pin v7.9.0 → v8.0.0; `bootstrap-data --profile` flag noted.
- ✅ `epics.md` — release ticker; sprint history entry.
- ✅ `project-parts.json` — skill version pin v7.9.0 → v8.0.0.
- ✅ `index.md` — release pointer (if present).
- ⚪ `architecture.md` — incidental v7.x mentions left; the architecture itself is unchanged at the doc level.
- ⚪ `architecture-bmad-infra.md`, `architecture-mcp-server.md`, `source-tree-analysis.md`, `validation-report-PRD.md`, `deployment-guide.md`, `development-guide.md`, `integration-architecture.md`, `project-overview.md` — incidental mentions left (no semantic content changes per v8.0.0).
- ✅ `implementation-artifacts/spec-conda-forge-expert-v8.0.md` — status flipped in-progress → done with Wave C noted deferred; Wave A+B+D checkboxes flipped.
- ✅ `implementation-artifacts/retro-atlas-pypi-universe-split-2026-05-13.md` — A6 corrected with consumer list.
- ✅ `implementation-artifacts/retro-conda-forge-expert-v8.0-2026-05-13.md` — NEW v8.0.0 retro per CLAUDE.md Rule 2.

## 4. Decision

**Approved**. Pin-only updates across listed planning artifacts. PRD MINOR bump (no FR/NFR scope shift; persona profiles are backward-compatible UX addition + Phase H performance improvement + structural-enforcement test; Wave C deferral does not regress any prior FR). No re-validation required — existing PRD validation report at `validation-report-PRD.md` remains current at the FR level.

## 5. Outcome

- PRD v1.2.0 pinned to `conda-forge-expert v8.0.0` with edit-history note.
- Architecture docs reflect schema v21 + persona profiles.
- Retro at `retro-conda-forge-expert-v8.0-2026-05-13.md` carries action items D1 / D2 (live-DB verification next session) + F1 / F2 / F3 (follow-up specs).
- Predecessor retro corrected for `vuln_total` consumer claim.

## 6. Trigger conditions for next bump

- Live-DB verification of `--profile maintainer` + Phase H serial-gate against the real 32k-row v21 atlas (retro action items D1 / D2). When complete, this proposal's readiness flips to "fully verified" and the next planning-artifact pass can drop the "pending live verification" qualifier.
- Wave C re-attempt after `vuln_total` consumer-consolidation spec (retro action item F1) → schema-bump trigger.
- Per-user `contributionsCollection` Phase N work (retro action item F2) → catalog row "maintainer last-active" enhancement; minor catalog update.
- Channel-wide Phase H/N cron operationalization (retro action item F3) → architecture doc update for cron strategy.
