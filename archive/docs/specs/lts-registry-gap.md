---
doc_type: spec
part_id: lts-registry-gap
display_name: lts-registry-gap suggester
project_type_id: tooling
date: 2026-07-06
status: shipped
implemented_by: conda-forge-expert v8.74.0
shipped_ref: c428c5849aa88abccc170582c222babc6f6b1260
spec_updated: 2026-07-06
---

# Spec: `lts-registry-gap` — propose lts-registry.yaml entries (mapping-gap sibling)

## Goal

`data/lts-registry.yaml` is deliberately hand-curated (every entry encodes a
verified conda-name → endoflife.date-slug decision or a manual LTS line), so
the pipeline never writes it. The automation gap is **discovery**: nobody
systematically diffs endoflife.date's product list against the atlas to find
packages the registry *could* cover. `lts-registry-gap` closes that gap in
the `mapping-gap` mold — a read-only suggester that **proposes** entries with
confidence tiers; accept/reject stays with git review. The registry keeps the
property that every entry was verified by a human.

## Design

- **Inputs**: `cf_atlas.db` (`v_actionable_packages` — the canonical
  persona-filter view), endoflife.date's all-products list
  (`/api/all.json` via `_http.resolve_endoflife_urls("all")`, mirror-routable
  per `ENDOFLIFE_BASE_URL`; TTL-7d cache `eol_products.json` in the runtime
  data dir, offline-stale fallback — the `EolClient` cache pattern), and the
  current registry via `library_futures.load_lts_registry` (already-covered
  names are excluded, aliases included).
- **Matching tiers** (conservative; no fuzzy matching):
  - `exact` — `conda_name` or `pypi_name` lowercase-equals a product slug.
  - `likely` — equality after `_`→`-` normalization, or after stripping a
    `python-` / `py-` conda-name prefix.
- **Output**: ready-to-paste YAML entry snippets grouped by tier (stdout or
  `--out FILE`), each stamped `source: endoflife` + a `note:` naming the
  match basis; `--json` machine summary; `--limit` per tier;
  `--products-file` for offline/test injection. **Never writes
  `lts-registry.yaml`**; exit code 0 always (report tool).

## Acceptance criteria

- Three-place rule: canonical script + wrapper + pixi task + SCRIPTS meta
  entry; `--help` clean.
- Fixture tests: exact + likely tiers, registry-covered exclusion,
  no-match exclusion, stale-cache fallback, `--json` shape, `--limit`.
- Registry file provably untouched by any code path (no write call sites).
- Docs: SKILL.md atlas CLI table row + Version History, CHANGELOG v8.74.0
  (MINOR — new tool), commands-cheatsheet row. CLI/pixi-only (no MCP tool),
  matching `library-futures`/`add-handoff`.
