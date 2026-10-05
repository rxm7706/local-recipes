---
skill_name: pyforge-mason
generated: 2026-10-05
forge_tier: Quick
t2_future_count: 0
---

# Evidence Report: pyforge-mason

**Generated:** 2026-10-05T17:19:19Z
**Forge Tier:** Quick
**Source:** src/shared/packages/pyforge-mason @ c9e07879721e5a23e74c054383668026f49b0dc7 (source_ref: local)
**Brief:** .claude/skills/pyforge-mason/skill-brief.yaml (Story 19.1, spec-pyforge-mason CAP-29)

## Tool Versions
- ast-grep: 0.45.3 (on PATH, not used — tier pinned to Quick by the brief)
- QMD: unknown (not installed)
- SKF: 2.1.0 (_bmad/skf/VERSION)

## Extraction Summary
- Files in scope: 3 (src/pyforge/mason/cli.py, src/pyforge/mason/__init__.py, README.md)
- Exports found: 3 (2 functions, 0 types, 1 constant) — skf-extract-public-api: build_parser, main; __init__.__all__: __version__
- CLI surface documented: doctor; recipe {new, validate, build, diagnose, optimize, scan, submit, update}; package {build, ship} + bare-noun --ship alias; environment {lock, check}
- Confidence: T1=0, T1-low=3, T2=0, T3=0
- Scripts/assets: 0/0 (skf-detect-scripts-assets, 81 files scanned)
- Authoritative files scan: no candidates
- Doc sources: detection partial — skf-detect-docs.py error (exit 2, local source is not a GitHub URL); README tracked (readme_always, sha256 recorded)
- Version reconciliation: brief target_version 0.1.0 authoritative (pyproject version 0.1.0 agrees)
- Description sanitizations: 0

## Validation Results
- Schema: manual fallback — skill-check unavailable (npx refused by the repo session guardrail); validation_status: manual-only
- Frontmatter: PASS — skf-validate-frontmatter.py --skill-dir-name pyforge-mason: status pass, 0 issues (high 0, medium 0, low 0); manual §3 checklist also passes (name matches dir, description 544 chars, only name + description fields)
- Body: PASS — 279 body lines (Tier 1: 215), under the 400-line shard budget; no split; tier1_preserved true
- Output: PASS — skf-validate-output.py --generated-by create-skill: 0 issues (first run flagged 3 medium missing sections Description / Key Exports / Usage; added from source and re-run clean)
- Citations: 81 [SRC:…] citations, every range inside its file under src/shared/packages/pyforge-mason/
- Security: skipped — skill-check unavailable; SNYK scan not run
- Content Quality (tessl): skipped — outward-facing review not authorized in a headless run
- Metadata: PASS — skf-render-metadata-stats.py --check: coherence ok, 0 violations; spec_version 1.3; scope_type specific-modules

## Quality Score Breakdown
- skipped — skill-check unavailable, no 0-100 score computed

## Description Guard
- Restored: false
- Triggering tool: —
- Original description preserved: —
- Notes: —

## Auto-Decisions

| Step | Gate | Decision | Rationale | Timestamp |
|---|---|---|---|---|
| load-brief | tier-resolution | apply-brief-tier | forge-tier.yaml tier is null (setup never set it) and tier_override is null; brief declares forge_tier: Quick; all tools null = Quick by definition | 2026-10-05T17:16:39Z |
| extract | authoritative-files | none | helper reported no-candidates | 2026-10-05T17:17:43Z |
| extract | extraction-summary | C | headless: auto-approve extraction summary (2 public exports, 17 CLI verbs/leaves, 0 scripts/assets) | 2026-10-05T17:17:43Z |
| validate | skill-check-availability | manual-fallback | npx skill-check refused by the repo session guardrail (.claude/hooks/pre-shell.py: no ad hoc npx); no pinned skill-check in pixi.toml; validation_status set to manual-only | 2026-10-05T17:22:13Z |
| validate | tessl-review | skip | tessl 0.98.0 is installed but its review sends SKILL.md to an external LLM judge; an outward-facing send needs operator confirmation, which a headless run cannot obtain | 2026-10-05T17:22:13Z |

## Auto-Fixed Issues
- Added ## Description, ## Key Exports and ## Usage sections (skf-validate-output medium findings), all source-cited

## Remaining Warnings
- forge-tier.yaml carries tier null and all tools null ([SF] Setup Forge never completed on this machine); the brief's forge_tier Quick was applied.
- QMD version unknown (qmd not installed) — expected at Quick tier.
- The pyforge mason front door and POST /stations/mason/mcp are cited from README.md:L22-L25 only; neither is defined in the in-scope Python sources (the front door is pyforge-core's dispatcher, the route is the platform's station MCP seam).
- Exit-code integer values beyond 2 and 3 live in exit_codes.py, outside the brief scope; SKILL.md names the constants and points there.

ref_count: 0  # Tier-2 kept inline in SKILL.md (no split performed in step 6)
