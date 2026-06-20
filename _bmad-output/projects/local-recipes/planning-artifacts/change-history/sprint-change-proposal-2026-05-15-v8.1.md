---
doc_type: sprint-change-proposal
project_name: local-recipes
date: 2026-05-15
author: rxm7706
trigger_type: release-driven
trigger_release: conda-forge-expert v8.1.0
scope: documentation-sync
classification: Minor (additive — no FR/NFR scope shift)
mode: Batch
status: approved
approved_by: rxm7706
approved_date: 2026-05-15
input_docs:
  - _bmad-output/projects/local-recipes/planning-artifacts/PRD.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-cf-atlas.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-conda-forge-expert.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-mcp-server.md
  - _bmad-output/projects/local-recipes/planning-artifacts/epics.md
  - _bmad-output/projects/local-recipes/planning-artifacts/index.md
  - _bmad-output/projects/local-recipes/planning-artifacts/project-parts.json
  - _bmad-output/projects/local-recipes/implementation-artifacts/spec-atlas-pypi-intelligence.md
  - _bmad-output/projects/local-recipes/implementation-artifacts/retro-atlas-pypi-intelligence-2026-05-15.md
  - .claude/skills/conda-forge-expert/CHANGELOG.md
ground_truth:
  - .claude/skills/conda-forge-expert/CHANGELOG.md
  - .claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py
  - .claude/skills/conda-forge-expert/scripts/bootstrap_data.py
  - .claude/skills/conda-forge-expert/scripts/pypi_intelligence.py
  - .claude/skills/conda-forge-expert/scripts/_http.py
  - .claude/tools/conda_forge_server.py
  - .claude/skills/conda-forge-expert/config/skill-config.yaml
prior_proposal: sprint-change-proposal-2026-05-13-v8.0.md
---

# Sprint Change Proposal: v8.1.0 PyPI Intelligence Layer Sync

## 1. Issue Summary

The `conda-forge-expert` skill shipped **v8.1.0** on 2026-05-15 via `bmad-quick-dev` against `docs/specs/atlas-pypi-intelligence.md`. All 8 spec open questions pre-resolved before BMAD intake; all 5 waves landed in 4 wave-commits + 1 closeout commit.

**MINOR bump trigger**: fully additive. No schema deletions, no existing-CLI changes, no breaking FR/NFR. New `pypi-intelligence` CLI and `pypi_intelligence` MCP tool are opt-in surfaces; existing `pypi-only-candidates` and all other CLIs continue to work unchanged.

Architecture lock (carried from spec frontmatter): **`pypi_universe` stays reference-data-only forever (3 cols)**. All enrichment lands in a new `pypi_intelligence` side table joined on `pypi_name`. Clean separation, no working-set contamination.

Substantive deltas:

- **Wave A — Schema v22 foundation + Phase O** — `pypi_intelligence` (35 cols across 5 tiers), `pypi_universe_serial_snapshots` (90-day rolling history), `v_pypi_candidates` view. Phase O writes daily snapshots (no HTTP) and computes activity_band (hot/warm/cold/dormant) from rolling serial deltas.
- **Wave B — Phase P + Phase Q** — Phase P lazy-imports `google-cloud-bigquery` (opt-in admin-tier; ~30 GB BQ scan per run, free-tier safe at monthly cadence) to populate downloads_30d/90d on all 806k rows. Phase Q bulk-fetches `current_repodata.json` from bioconda/pytorch/nvidia/robostack-staging via the new `resolve_anaconda_channel_urls` resolver to populate `in_<channel>` BOOLs. PEP 503 canonicalization on both join sides via the new `_pep503_canonical` helper.
- **Wave C — Phase R + classifier + SPDX** — Bounded per-project JSON enrichment for the top-N (default 5000) candidate slice. New `_classify_packaging_shape` deterministic classifier (pure-python/cython/c-extension/rust-pyo3/unknown). New `_normalize_license_to_spdx` covering the OSI-approved subset.
- **Wave D — Phase S + CLI + MCP + profiles** — Phase S computes `conda_forge_readiness` (0-100 composite via 6-component weighted formula) + `recommended_template` (full template path). New `pypi-intelligence` CLI with rich filters (`--score-min`, `--activity`, `--license-ok`, `--in-bioconda`, `--sort-by score|downloads|serial|name`). New `pypi_intelligence` MCP tool wrapping the CLI's read path. Profile integration: maintainer enables O+Q only; admin enables all 5; consumer enables O only.
- **Wave E — Closeout** — this proposal + retro + skill-side doc updates (CHANGELOG v8.1.0, SKILL.md heading, skill-config 8.0.2 → 8.1.0).

## 2. Impact Analysis

| Aspect | Pre-v8.1.0 (v8.0.2) | Post-v8.1.0 | Delta |
|---|---|---|---|
| Schema version | 21 | 22 | +1 (additive — 2 new tables + 1 view; no column modifications to existing tables) |
| Total pipeline phases | 17 | 22 | +5 (O / P / Q / R / S) |
| `pypi_intelligence` column count | 0 | 35 | +35 (5 tiers + notes) |
| `pypi_universe` column count | 3 | 3 | 0 (locked at reference-data-only) |
| New atlas CLIs | 0 | 1 | +1 (`pypi-intelligence`) |
| New MCP tools | 0 | 1 | +1 (`pypi_intelligence`) |
| Skill test count | 989 (last fully-verified) | 1,064 | +75 (51 new v8.1.0 + 24 inherited that now run cleanly against v22) |
| Skill MCP tool count | 36 | 37 | +1 |
| `cf_atlas.db` size delta | — | ~25 MB | +25 MB (pypi_intelligence rows for top-5k candidates × 1KB; snapshot rows × 90d × 12B) |
| `bootstrap-data --profile maintainer` wall-clock delta | — | +5-30s | Phase O ~5s + Phase Q ~30s |
| `bootstrap-data --profile admin` wall-clock delta | — | +35 min cold / +5 min warm | Phase R top-5k JSON fetches (~28 min cold; TTL-gated warm); Phase P BQ ~30s (when creds available); Phase Q ~2 min; Phase S ~10s |

## 3. Affected Artifacts (sync targets)

- ✅ `PRD.md` — v1.2.0 → v1.3.0; source_pin → `conda-forge-expert v8.1.0`; edit-history entry for v8.1.0
- ✅ `architecture-cf-atlas.md` — source_pin → v8.1.0 (schema v22 + 5 new phases documented in deeper edits, but pin bump is the minimum)
- ✅ `architecture-conda-forge-expert.md` — skill version pin v8.0.0 → v8.1.0; Atlas Intelligence Layer heading; CHANGELOG release version reference
- ✅ `epics.md` — sync_lineage entry for v8.1.0; source_pin bump
- ✅ `project-parts.json` — skill version pin + cf-atlas description updated to mention schema v22 + 5 new phases + pypi-intelligence CLI
- ✅ `index.md` — source pin bump; re-sync lineage extended; release pointer
- ✅ `implementation-artifacts/spec-atlas-pypi-intelligence.md` — status `in-progress` → `done`
- ✅ `implementation-artifacts/retro-atlas-pypi-intelligence-2026-05-15.md` — NEW v8.1.0 retro per CLAUDE.md Rule 2
- ✅ `CLAUDE.md` — spec-list entry already added when intent doc was written; flip to mark v8.1.0 shipped
- ⚪ `architecture-mcp-server.md`, `source-tree-analysis.md`, `validation-report-PRD.md`, etc. — incidental pin mentions left; no semantic content changes per v8.1.0 (the new MCP tool count goes 36 → 37 but the broader architecture doc is unchanged at the doc-set level)

## 4. Decision

**Approved**. Pin-only updates across listed planning artifacts; substantive content updates concentrated in `architecture-cf-atlas.md` (the technical surface) and `project-parts.json` (the structured manifest). PRD MINOR bump (no FR/NFR scope shift; new pypi-intelligence CLI + MCP tool are backward-compatible UX additions; profile system extension is additive). No re-validation required — existing PRD validation report at `validation-report-PRD.md` remains current at the FR level.

## 5. Outcome

- PRD v1.3.0 pinned to `conda-forge-expert v8.1.0` with edit-history entry
- Architecture docs reflect schema v22 + 5 new phases + new CLI/MCP tool
- Retro at `retro-atlas-pypi-intelligence-2026-05-15.md` captures action items L1/L2/L3 (live-DB verification) + F1/F2/F3/F4 (follow-up specs)
- All 8 pre-resolved spec open questions documented in CHANGELOG v8.1.0 § "Open questions resolution" — operator-visible record of architecture decisions
- 4 wave commits + 1 closeout commit on origin/main

## 6. Trigger conditions for next bump

- Live-DB verification of `bootstrap-data --profile admin` end-to-end (retro action L1) — flips readiness from "implementation-verified" to "production-verified"
- v8.2.0 spec opens when any of the deferred follow-ups (F1 bulk-index ecosystems, F2 bus_factor / blast_radius population, F3 conda_forge_readiness_percentile, F4 per-version BQ granularity) accumulates operator demand
- Schema v23 bump trigger: any future column-modification to existing tables (not new tables/views; those go in MINOR bumps)
