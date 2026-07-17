---
skill_name: cf-atlas-legacy
generated: 2026-07-17
forge_tier: Quick
t2_future_count: 0
---

# Evidence Report: cf-atlas-legacy

**Generated:** 2026-07-17
**Forge Tier:** Quick
**Source:** /home/user/local-recipes @ b18cbb5e1bfd1e7111d89dff0a4b7e47875f965c (HEAD, 2026-07-17)

## Grounding Stamp (AD-17)

- Generation date: 2026-07-17
- Grounding commit: `b18cbb5` (`b18cbb5e1bfd1e7111d89dff0a4b7e47875f965c`)
- Legacy CFE skill pin: v8.78.0
- cf_atlas.db schema: v29 (`SCHEMA_VERSION = 29` at conda_forge_atlas.py:139)
- Phase T conditional (D-15): re-checked NOT shipped — surface stays 23 phases / v29
- Live anchors verified against spec § 3.3 snapshot (grounded `58a6dcc`, re-verified
  `4cf1b74` at intake, re-verified `b18cbb5` this run): 8,902-line orchestrator,
  PHASES @ :8679, bootstrap 1,094 lines, atlas_phase._TTL_GATED @ :44, 19
  resolve_*_urls, 46 @mcp.tool() (23 atlas-relevant). ALL MATCH — no divergence.

## Tool Versions
- ast-grep: unavailable (Quick tier)
- QMD: unavailable (Quick tier)
- SKF: 2.0.1 (bmad-module-skill-forge)

## Extraction Summary
- Files scanned: 13 in-scope sources (9 code + 3 reference docs + 1 spec)
- Exports (modeled surface entries) found: 130
- Confidence: T1=0, T1-low=130, T2=0, T3=0
- Method: Quick-tier source reading — 4 parallel extraction subagents (each invoking
  the conda-forge-expert skill per CLAUDE.md Rule 1) + orchestrator-level grep -n
  cross-verification of every load-bearing line anchor
- Coverage floor (story 0.1 AC-1): 23/23 phases; TTL/checkpoint machinery; bootstrap
  driver (profiles + 1800 s cap); 6/6 write paths; per-phase engineering contracts
  (spec:250-286); § 3.4 boundary (3 in-scope stores + 5 out-of-scope classes)

## Source-vs-Spec Divergences (recorded, code authoritative)
- D1: spec:253-261 says Phase P uses `_PARTITIONDATE` literal bounds; code REJECTS
  `_PARTITIONDATE` (conda_forge_atlas.py:7690-7697) and uses literal TIMESTAMP bounds
  on `timestamp` (:7704-7705).
- D2: "AD-10" is an architecture-SPINE label; zero matches in the spec — the contract
  list is spec:250-286 (unlabeled).
- D3: `_parse_retry_after` is in conda_forge_atlas.py:2668, not _http.py (story
  prompt's placement corrected).
- D4: `_coerce_cvss_score` is in detail_cf_atlas.py:295 (outside the include set;
  recorded as a boundary pointer).

## Validation Results
- Schema: PASS (quality score: 100/100; skill-check 1.2.0, 0 errors, 0 warnings, fixed[] empty)
- Frontmatter: PASS (skf-validate-frontmatter clean after description restore)
- Body: PASS (165 lines, under 400 budget; auto-shard skipped; Tier-1 preserved)
- Security: skipped — snyk agent-scan requires SNYK_TOKEN (mcp-scan renamed to snyk-agent-scan); advisory only
- Content Quality (tessl): skipped — tessl 0.91.0 requires login (skill review deprecated upstream); no novel suggestions to triage
- Metadata: PASS (skf-render-metadata-stats --check: coherence ok, 0 violations; spec_version 1.3; scope_type verbatim)

## Quality Score Breakdown
- Frontmatter (30%): 30 | Description (30%): 30 | Body (20%): 20 | Links (10%): 10 | File (10%): 10

## Description Guard
- Restored: true
- Triggering tool: skf-description-guard verify-restore (operator mis-invocation — empty --captured-description argument)
- Original description preserved: true
- Notes: an empty captured-description argument caused the guard to "restore" the description to the empty string; the original was re-applied byte-identically (schema_hash re-verified sha256:5856f5d6...) and skill-check re-scored 100/100. skill-check --fix itself changed nothing.

## Auto-Decisions

| Step | Gate | Decision | Rationale | Timestamp |
|------|------|----------|-----------|-----------|
| extract | authoritative-files | skip-all (21) | headless: all candidates are vendored .pixi site-packages noise or repo-level agent-config files; outside the spec 3.3 legacy surface (AD-19 fixed universe) | 2026-07-17 |
| extract | scripts-assets-detect | skip | brief scripts_intent=none and assets_intent=none — detector no-op by contract | 2026-07-17 |
| extract | extraction-summary | continue | headless: auto-approve extraction summary (130 modeled entries, zero-exports check N/A) | 2026-07-17 |
| validate | tessl-suggestions | skip | tessl unavailable (login required) — no novel suggestions to triage | 2026-07-17 |

## Auto-Fixed Issues
- skill-check --fix: none (fixed[] empty; score 100/100 on first pass)
- Frontmatter description restored after guard mis-invocation (see Description Guard)

## Remaining Warnings
- Doc-source detection (step 5a) skipped — gh CLI unavailable; no doc_sources[] recorded.
- Doc-rot scan (step 5c): 0 matches across evidence-report/provenance-map/SKILL.md.
- Quick tier: all provenance is T1-low (source reading, grep-verified line anchors);
  no AST verification available (ast-grep not installed).
- Extraction subagent for conda_forge_atlas.py exhausted its budget before emitting a
  final report on first pass; its scope was re-verified by orchestrator greps and the
  agent's completed report arrived afterward — both sources agree on every anchor.
- provenance-map.json is copied into the skill package (in addition to its canonical
  forge-data workspace location) so the skill is self-contained for Wave-B consumers.
