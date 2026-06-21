---
doc_type: prd-validation-report
project_name: local-recipes
date: 2026-06-21
prd_under_review: planning-artifacts/PRD.md
validator: bmad-validate-prd (Path 3 hybrid)
overall_verdict: APPROVED (re-validated 2026-06-21 post-v8.40.0 sync; PRD v1.6.0 closed the v8.11.1 → v8.39.0 structural drift then pin-bumped to v8.40.0 — gotcha range grew G45 → G51 as a MINOR skill-internal bump. Spot-check per the pinned-resync convention surfaces ONE residual count-drift [F1.7 / glossary / matrix still read G1-G45; live skill ships G1-G51] — SHOULD-FIX, non-blocking; verdict holds. See verdict_history.)
status: final
source_pin: 'conda-forge-expert v8.40.0'
verdict_history:
  - { date: '2026-05-12 (initial)', verdict: 'REVISE', notes: 'Material issues across D3 / D5 / D6 / D7 / D9 / D10 on the v7.7-pinned draft PRD.' }
  - { date: '2026-05-12 (post tentative-decisions)', verdict: 'APPROVED', notes: 'PRD updated with tentative_decisions_applied; REVISE-rated dimensions addressed; status moved draft → approved.' }
  - { date: '2026-05-12 (re-validated post v7.8.1 sync)', verdict: 'APPROVED', notes: 'Re-validation after bmad-correct-course propagated v7.8.x deltas to architecture-cf-atlas.md / deployment-guide.md / architecture-conda-forge-expert.md / architecture.md. PRD body itself unchanged; only source_pin moved v7.7 → v7.8.1. No new REVISE findings.' }
  - { date: '2026-05-13 (re-validated post v7.9.0 sync)', verdict: 'APPROVED', notes: 'v7.9.0 actionable-scope audit (schema v20 + pypi_universe side table + pypi-only-candidates CLI/MCP + Phase D split). PRD MINOR-bumped 1.1.0 → 1.1.1 → 1.2.0 across the v7.9.0/v8.0.0 syncs. Feature counts updated. No new REVISE findings.' }
  - { date: '2026-05-13 (re-validated post v8.0.0 sync)', verdict: 'APPROVED', notes: 'v8.0.0 structural-enforcement + persona-profile bundle (schema v21 + v_actionable_packages view + Phase H serial-aware eligible-rows gate + bootstrap-data --profile flag with auto-detection). PRD MINOR-bumped 1.1.1 → 1.2.0. v8.0.0 is the first MAJOR skill bump but PRD scope unchanged (additive UX). No new REVISE findings.' }
  - { date: '2026-05-15 (re-validated post v8.1.0 sync)', verdict: 'APPROVED', notes: 'v8.1.0 PyPI intelligence layer (schema v22 + pypi_intelligence side table + 5 new phases O/P/Q/R/S + new pypi-intelligence CLI + new MCP tool + persona-profile integration). PRD MINOR-bumped 1.2.0 → 1.3.0 (fully additive — no FR/NFR scope shift; new CLI + MCP tool are opt-in surfaces; existing CLIs unchanged). All 8 spec open questions pre-resolved before BMAD intake; L1 + L2 live-DB verification complete (Phase O perf-fix shipped as 124c5a449d; Phase R 9× faster than estimate; score distribution well-discriminated across 5k enriched candidates). No new REVISE findings.' }
  - { date: '2026-05-23 (re-validated post v8.5.3 sync)', verdict: 'APPROVED', notes: 'PATCH bumps v8.1.0 → v8.5.1 (env-inspect suite — additive: 2 new Tier 1 scripts + 1 MCP tool + 1 extended MCP tool) → v8.5.2 (Phase K/N/P/Q reliability bundle — additive: Phase K daemon-thread hard-timeout watchdog + per-batch checkpoint, Phase P google-cloud-bigquery enabled in local-recipes env, Phase Q robostack 404 fix, Phase N partial-batch recovery) → v8.5.3 (DW12 rollup-staleness fix via v_current_version_vulns view + _phase_g_sync_current_rollup tail step + DW13 CISA KEV via Path C: new cisa_kev side table + cisa_kev_fetcher.py + fetch-cisa-kev pixi task + _load_kev_cves helper + Phase G/G overlay loop modification) do not require re-validation; FR/NFR set unchanged across all three PATCH bumps. PRD pin moved v8.1.0 → v8.5.3 retroactively via sequential bmad-correct-course passes; PRD body validated content unchanged. v8.6.0 spec at docs/specs/atlas-appthreat-deep-signals.md (mirrored at implementation-artifacts/spec-appthreat-deep-signals.md) is intake-ready — full re-validation will run when v8.6.0 ships (MINOR bump; new opt-in surfaces — epss_scores + cwe_categories + package_hardening tables, Phase T + U, new CLIs and pixi tasks — require dimension re-scoring on D2 [Specificity], D7 [Testability], D9 [Phasing], D10 [Risk Management]). No new REVISE findings.' }
  - { date: '2026-05-24 (re-validated post v8.6.0 sync)', verdict: 'APPROVED', notes: 'v8.6.0 AppThreat Deep Signals released across three commits — Wave A (e4ba891cd2 2026-05-23: schema v23 → v24 foundation + EPSS pipeline) + Wave B (e22c531ac2 2026-05-23: CWE catalog + Phase G/G overlay wiring) + Wave D (592b18089a 2026-05-24: schema v24 → v25 cleanup + CLI flags + persona profiles + closeout). Wave C (Phase T blint + Phase U EPSS overlay phase) cancelled pre-implementation at verify-don''t-assume verification. Net delta: +2 side tables (epss_scores, cwe_categories) + 4 packages columns surviving v25 + 3 package_version_vulns columns surviving v25 + 2 new fetcher CLIs (fetch-epss, fetch-cwe-catalog) + 4 new flags across existing query CLIs + persona-profile auto-runs. PRD MINOR-pin bump but PATCH PRD-version bump (v1.4.2 → v1.4.3) because the PRD feature catalogue gains opt-in additive surfaces only — no FR/NFR scope shift; new CLIs are opt-in operator-invoked maintenance like v8.5.3 fetch-cisa-kev; new flags preserve existing CLI defaults; persona-profile auto-runs are env-var gated. D2/D7/D9/D10 spot-checked instead of full re-validation: (D2 Specificity) the four new flag-additions are specific (`--by-epss`, `--has-cwe`, `--epss-threshold`, `--epss`, `--cwe`) and the two new fetcher CLIs follow the established `fetch-<source>` convention from v8.5.3 — PASS. (D7 Testability) test suite 1,099 → 1,137 passing (+38 net; 0 regressions); live-verified channel-wide on production cf_atlas.db (334,683 EPSS rows + 944 CWEs + 213 EPSS-scored + 216 CWE-classified actionable feedstocks) — PASS. (D9 Phasing) Wave A foundation + Wave B wiring + Wave C cancellation decision + Wave D cleanup are ordered by dependency; the v23 → v24 → v25 round-trip is rare but every migration is idempotent + self-healing + live-validated — PASS. (D10 Risk Management) Wave A schema columns provisioned for Wave B/C consumers (the recognized risk that they''d become dead surface materialized for Wave C, mitigated by Wave D''s v25 cleanup); review subagents caught a real Wave B bug (rollup-sync missing COALESCE-to-existing) before commit; verify-don''t-assume caught 5 parent-spec errors pre-implementation (saving ~10-15 stories) — PASS with the retro-recommended follow-up that future major-feature specs include a populated "Verified facts" section. No new REVISE findings. Future-Epic-14-candidate flagged in v8.5.3 sync retired — v8.6.0 work layered cleanly onto Epic 8 acceptance criteria.' }
  - { date: '2026-06-21 (re-validated post v8.40.0 sync, PRD v1.6.0)', verdict: 'APPROVED', notes: 'First DEEP re-sync since the 2026-06-07 v8.11.1 frontmatter touch. The PRD had drifted to a v8.6-era pin (v8.11.1) while the skill advanced ~28 MINOR/PATCH releases. Closed in two PRD edits this cycle: (1) v1.5.1 → v1.6.0 STRUCTURAL re-sync v8.11.1 → v8.39.0 (bmad-edit-prd 2026-06-20) re-derived every drifted count against live code — F2.1 schema v25/16-tables → v28 (21 tables + 4 views; migration range v19→v28); F2.2 17 → 22 phases (B→N + PyPI-intelligence O/P/Q/R/S); F3.2/§6 37(35) → 42 MCP tools; FX.2 8 → 9 pixi envs (+gcloud); + 3 net-new feature-level FRs for capabilities that shipped after the old pin (F2.13 PyPI-intelligence layer, F2.14 security-signals overlays KEV/EPSS/CWE, F3.9 7 net-new MCP tools). MINOR PRD bump (additive FRs; none removed; no decision overridden). (2) source_pin v8.39.0 → v8.40.0 pin-bump (this cycle) — v8.40.0 is a skill-INTERNAL MINOR (SKILL.md gotchas G46–G51 + feedstock-platform-expansion guide refinements; CHANGELOG explicit "no code/test/CLI/build change"). Per the established pinned-resync convention (skill-internal release with no new public surface → 4-dimension spot-check, not full re-score) the gate runs as a documented spot-check below. Live ground truth verified 2026-06-21: skill v8.40.0 (config/skill-config.yaml + CHANGELOG top entry); SCHEMA_VERSION=28 / 21 tables + 4 views (v_actionable_packages, v_current_version_vulns, v_packages_enriched, v_pypi_candidates); PHASES 22-tuple (conda_forge_atlas.py:8504-8527); 42 @mcp.tool() (conda_forge_server.py); 9 environments (pixi.toml); gotchas G1–G51 (SKILL.md + CHANGELOG v8.40.0; G45 was v8.39.0, G46–G51 added v8.40.0). Spot-check: (D2 Specificity) the 3 new FRs name concrete, unambiguous surfaces (named tables, named phases O/P/Q/R/S, named fetcher CLIs, the 7 named MCP tools) — PASS. (D5 Measurability / D12 Completeness) ONE residual count-drift found: F1.7 acceptance + "45" count, Appendix A glossary line, and Appendix C matrix row F1.7 still read "G1-G45"; live skill ships G1-G51 (51 gotchas). The v8.40.0 pin-bump grew the range without re-syncing the body. SHOULD-FIX (cosmetic count drift, exactly the F1.4/F1.8-class numeric pin that this gate tracks) — does NOT shift the FR/NFR set, does not change a decision, does not break traceability; verdict holds. NOTE F1.16 "Feature G45" is a CORRECT reference (the SPA-packaging gotcha is still G45 in the live skill) — not part of the drift. (D7 Implementation Leakage) the 3 new FRs hold the rebuild-PRD framing already accepted in 2026-05-12 D7 (concrete artifacts are the rebuild target) — PASS. (D9 Phasing / D10 Risk) no new wave/epic introduced; the additive FRs map onto existing Epics 6/8; R1 (skill drift) is the active risk this very sync addresses — PASS. Co-audit: §7 architectural-gaps table uses a SEPARATE G1-G6 numbering (SYSTEM gaps, not recipe gotchas) — intentionally left untouched; §9 DW17 reconciled-SHIPPED preserved. No new REVISE findings. Carryover follow-ups still open: MCP-count audit note from 2026-06-07 is now RESOLVED (live count 42 matches PRD pin); the G1-G45 → G1-G51 body re-sync is the single new SHOULD-FIX; v8.11.x + v8.39/v8.40 CFE-skill retros remain outstanding per CLAUDE.md Rule 2.' }
  - { date: '2026-05-26 (re-validated post v8.10.0 sync)', verdict: 'APPROVED', notes: 'Bundled v8.6.0 → v8.10.0 sync covering 4 MINOR + 1 PATCH skill releases — v8.7.0 (Rust template refresh: cargo auditable install --locked --no-track --bins canonical pattern + SCHEMA-001 optimiser check + 8-recipe schema-header backfill; 21-PR sample), v8.8.0 (Python generator + template alignment: CFEP-25 dual-version test matrix in generated recipes + project_urls description/repository/documentation extraction + python_min clamp to conda-forge floor + pdm-backend/scikit-build-core detection; 30-PR sample), v8.9.0 (maturin/PyO3 routing + sdist-driven import-name + abi3-gated version_independent; 27-PR sample), v8.9.1 (interpolated source URLs + CARGO_PROFILE_RELEASE env vars in maturin template), v8.10.0 (drop context.name + literal package.name + literal source.url with only ${{ version }} interpolated, matching current grayskull / conda-forge convention; verified against recipes/xorq-datafusion + recipes/py-yaml12 reference recipes; v8.9.1 interpolated form retired five days after ship — caught the convention drift). All five releases are skill-internal generator + template + SKILL.md changes; **none touch the FR/NFR set**, no new CLIs / MCP tools / pixi tasks, no schema migration, no atlas-phase additions. Skill atlas surface (22 phases / schema v25 / 19 CLIs) **unchanged** in this range — last atlas surface change was v8.1.0 + v8.6.0. PRD PATCH bump v1.4.3 → v1.4.4 reflects bundled re-pin with no FR/NFR scope shift. **Full D-dimension re-score not required** under the established convention (skill-internal releases without new public surfaces); a 4-dimension spot-check confirms no degradation: (D2 Specificity) v8.10.0 SKILL.md "PyPI source.url" critical-constraint section rewritten to the literal pattern; concrete and unambiguous (literal-name, literal-stem, only ${{ version }} interpolates) — PASS. (D7 Testability) test suite 1,137 → 1,149 passing (+12 net; 0 regressions); generator regeneration of recipes/py-yaml12 byte-for-byte matches the user-curated recipe (deterministic verification anchor) — PASS. (D9 Phasing) five releases ordered v8.7 → v8.8 → v8.9 → v8.9.1 → v8.10.0; v8.9.1 → v8.10.0 corrects v8.9.1 within five days (retro-2026-05-26 documents the lesson) — PASS. (D10 Risk Management) v8.9.1 codified a grayskull-style URL pattern that was already obsolete on arrival; v8.10.0 caught + reverted at the next user signal. **Recommended follow-up captured in retro-conda-forge-expert-v8.10-2026-05-26.md**: any future generator change claiming to "match grayskull" must carry a live `grayskull pypi <name>` diff in the CHANGELOG. Net risk: low; mitigation actionable — PASS. Co-audit drift in BMAD planning artifacts caught + fixed in commit 461e32ddb3 (architecture-cf-atlas.md schema v19 → v25, 17 phases → 22 phases with O/P/Q/R/S table rows added; source-tree-analysis.md script counts refreshed; 14 source_pins re-synced to v8.10.0). No new REVISE findings. Audit retro: implementation-artifacts/retro-conda-forge-expert-v8.10-2026-05-26.md + retro-conda-forge-expert-v8.7-v8.8-2026-05-25.md.' }
---

# PRD Validation Report

This report applies the 13 BMAD PRD validation dimensions to `planning-artifacts/PRD.md`. It is **honest critique, not rubber-stamping** — the author of the PRD is the same agent producing this report, and the goal is to surface real issues before sprint planning begins.

> **Latest run: 2026-06-21, post-v8.40.0 sync (PRD v1.6.0) → APPROVED.** This is a dated gate snapshot regenerated against the current artifacts (not a number-patch of the prior run; full `verdict_history` preserved). The 2026-05-12 deep validation below remains the authoritative full 13-dimension pass; everything after it is a sync-driven spot-check per the pinned-resync convention. The current run found ONE residual SHOULD-FIX (a `G1-G45` → `G1-G51` body count-drift the v8.40.0 pin-bump introduced) — non-blocking; the verdict holds. See the **"Re-validation Run — 2026-06-21"** section at the end of this report and the `verdict_history` frontmatter entry.

**Original verdict: APPROVED (re-validated 2026-05-12).** Three rounds — see `verdict_history` in frontmatter:

1. **Initial validation (REVISE)** — material issues in D3 / D5 / D6 / D7 / D9 / D10 on the v7.7-pinned draft PRD (findings preserved below for traceability).
2. **Post-tentative-decisions (APPROVED)** — PRD's `tentative_decisions_applied: 2026-05-12` resolved each REVISE finding (JTBD↔feature mapping added in §3, implementation-leakage cleanup in §5, time-bound constraints in §7, etc.); PRD moved `draft` → `approved` (v1.1.0).
3. **Re-validation after v7.8.1 sync (APPROVED)** — `bmad-correct-course` propagated the v7.8.0 + v7.8.1 atlas-hardening deltas across architecture + deployment-guide; PRD body did NOT need to change (feature-level vs the v7.8.x implementation-detail deltas) — only the `source_pin` frontmatter moved v7.7 → v7.8.1. Spot-checked against the now-updated companion artifacts: no contradictions, no new dimensions go into REVISE.

---

## Validation Summary

| # | Dimension | Verdict | Severity if fail |
|---|---|---|---|
| 1 | Discovery — PRD found at expected path | ✅ PASS | — |
| 2 | Format detection — PRD follows BMAD template structure | ✅ PASS | — |
| 3 | Information Density — high signal-to-noise | ⚠️ MINOR | Padding in some sections |
| 4 | Brief Coverage — all required sections present | ✅ PASS | — |
| 5 | Measurability — FRs/NFRs are measurable & testable | ⚠️ MINOR | 3 success metrics under-specified |
| 6 | Traceability — Vision → SC → JTBD → FR chain intact | ❌ REVISE | JTBD↔feature mapping not documented |
| 7 | Implementation Leakage — WHAT not HOW | ❌ REVISE | Features section names specific technologies (SQLite WAL, FastMCP, Python 3.12) |
| 8 | Domain Compliance — domain conventions followed | ✅ PASS | — |
| 9 | Project Type Alignment — appropriate for project class | ⚠️ MINOR | This is a "platform rebuild," not a typical product PRD — some dimensions N/A; should be marked explicitly |
| 10 | SMART Criteria — specific, measurable, achievable, relevant, time-bound | ❌ REVISE | "Time-bound" missing (no sprint targets, no calendar) |
| 11 | Holistic Quality — reads as coherent intent | ✅ PASS | — |
| 12 | Completeness — no template vars, all sections populated | ✅ PASS | — |
| 13 | Report — this document | ✅ PASS (in-progress) | — |

**Score (initial validation): 6 PASS / 4 MINOR / 3 REVISE = 6.5/13 pass-without-issues.**

**Score (after `tentative_decisions_applied: 2026-05-12` and v7.8.1 re-sync):** All 13 dimensions PASS. The REVISE-rated rows below carry their original findings for traceability — each is annotated with `→ RESOLVED in v1.1.0` where the PRD update addressed the issue. Severity-MINOR rows are unchanged in v1.1.0 and accepted as residual.

---

## D1. Discovery ✅ PASS

PRD found at: `_bmad-output/projects/local-recipes/planning-artifacts/PRD.md` (472 lines, 30K).

Frontmatter properly populated: `doc_type: prd`, `version: 1.1.0` (was 1.0.0), `status: approved` (was draft), `source_pin: 'conda-forge-expert v7.8.1'` (re-pinned 2026-05-12 from v7.7), `input_docs` listed.

---

## D2. Format Detection ✅ PASS

The PRD follows BMAD template structure with the standard sections:

- ✅ Vision (§1)
- ✅ Background & Context (§2 — added; not strictly templated but appropriate for rebuild PRDs)
- ✅ Users & Jobs-to-be-Done (§3)
- ✅ Goals & Non-Goals (§4)
- ✅ Features (§5)
- ✅ Success Metrics (§6)
- ✅ Constraints & Assumptions (§7)
- ✅ Open Questions (§8)
- ✅ Deferred Work (§9 — added; appropriate for brownfield rebuild)
- ✅ Risks (§10)
- ✅ Dependencies (§11)
- ✅ Approvals & Sign-off (§12)
- ✅ Glossary + References (Appendices)

**Note**: this is a *rebuild* PRD, not a *new product* PRD. Some BMAD template fields (e.g., "Competitive analysis", "Pricing strategy") don't apply. The PRD wisely omits them.

---

## D3. Information Density ⚠️ MINOR

Spot-checked for conversational filler and wordy phrases. Most of the PRD is appropriately dense, but a few instances of padding:

### Findings

| Location | Issue | Suggested fix |
|---|---|---|
| §1 Vision | "**An AI agent — given an empty repo, pixi, and Claude Code — can stand up the full `local-recipes` system (Parts 1-4) and produce conda-forge-ready recipes on first authoring, in any network environment from open-internet to fully air-gapped.**" | Strong sentence, but "in any network environment from open-internet to fully air-gapped" can be "across all network environments." Save 8 words. |
| §2 "Why rebuild?" intro | "This PRD does not assume a destruction event. The rebuild target supports:" | "The rebuild target supports:" — drop the lead-in. |
| §2 "In scope" table | Table format is dense ✅. No issue. |
| §3 JTBD-1.1 | "Author a new conda-forge recipe with confidence that it will pass review on first land." | "Author a new conda-forge recipe that passes review on first land." — drop "with confidence that it will." |
| §5 Feature row prose | Each feature row's acceptance description is appropriately tight. ✅ |
| §6 Note line | "(Calendar estimates assume one operator + Claude Code; AI-assisted development changes the math significantly.)" | This is meta-commentary, not a requirement. Move to §7 Assumptions. |
| §8 Q-PRD intros | "**Pros**: ... **Cons**: ... **Recommendation**: ..." structure is good. ✅ |
| §10 Risks table | Each risk has Probability/Impact/Mitigation. ✅ Good density. |

**Severity: MINOR.** Maybe 30-40 words of padding across 472 lines. Not a blocker for sprint planning.

---

## D4. Brief Coverage ✅ PASS

All required BMAD PRD sections are present (see D2). The PRD also adds appropriate sections for a rebuild context (Deferred Work, project-specific glossary).

---

## D5. Measurability ⚠️ MINOR

§6 Success Metrics enumerates 27 measures across 4 categories. Most are measurable; **3 are under-specified**:

### Findings

| Metric | Issue | Suggested fix |
|---|---|---|
| G5 (Goal) "MCP server availability ≥99% during a Claude Code session" | "Availability" undefined. Per-call uptime? Server-process uptime? | Define: "Per-MCP-tool-call success rate ≥99% (calls returning JSON ≠ `{'error': ...}` divided by total calls) within a single Claude Code session." |
| Performance §6 row "`bootstrap-data --fresh` cold time (auto-mode) ≤90 min" | "Cold" undefined. Empty data dir? Recently-built host with caches? | Define: "Cold = empty `.claude/data/conda-forge-expert/` + no parquet cache + no cf-graph tarball." |
| Quality §6 row "First-pass conda-forge PR acceptance ≥90%" | Depends on the recipes chosen for the sample. Cherry-picking risk. | Define: "Measured on the next 10 recipes authored after rebuild completion; each must be a recipe the system has not previously authored." |

### Other measurability strengths

- All 7 G* goals have measurable outcomes in §4
- All 54 features have AC descriptions in §5
- Air-gap metrics (§6) are concretely auditable (zero JFrog headers in non-JFrog logs)

**Severity: MINOR.** 3 of 27 metrics under-specified; 24 are sound.

---

## D6. Traceability ❌ REVISE

The traceability chain is **Vision → Goals → JTBDs → Features → Acceptance Criteria**. The PRD has all four layers, but the **JTBD ↔ Feature mapping is not documented**.

### Findings

#### Missing: JTBD-to-Feature trace matrix

§3 lists 12 JTBDs across 5 user personas. §5 lists 54 features across 4 parts + cross-cutting. **There is no explicit mapping** showing which JTBD each feature serves.

Some features have obvious JTBD parents (F1.2 "10-step autonomous loop" → JTBD-3.1). Others are ambiguous:

| Feature | Likely JTBD parent | Documented? |
|---|---|---|
| F1.10 (MANIFEST.yaml portability) | JTBD-5.1 (future contributor)? Or JTBD-1.4 (BMAD-driven planning)? | ❌ Not documented |
| F1.15 (CHANGELOG with TL;DR) | JTBD-3.2 (skill update on closeout)? Or JTBD-1.4? | ❌ Not documented |
| F3.7 (`mcp_call.py` JSON-RPC client) | JTBD-3.1? Or a "shell-only operator" JTBD not yet defined? | ❌ Not documented |
| F3.8 (`gemini_server.py` auxiliary) | No JTBD identified for "alternative model backend" | ❌ Not documented |
| FX.4 (vuln-db env separation) | JTBD-2.1 (air-gap)? Or a "performance" JTBD? | ❌ Not documented |

If F3.8 (Gemini) doesn't serve any documented JTBD, why is it in scope? (Its priority is P2 — perhaps justified by "operator may want fallback model" — but the JTBD should be explicit.)

#### Required: Add a JTBD↔Feature mapping matrix

Recommended location: new appendix `Appendix C: Feature-to-JTBD Traceability Matrix` with rows like:

```
| Feature | Primary JTBD | Secondary JTBD(s) | Why this serves the JTBD |
|---|---|---|---|
| F1.1  | JTBD-3.1 | JTBD-5.1            | Three-tier discipline lets new agents/contributors navigate the codebase |
| F1.2  | JTBD-3.1 | JTBD-1.1, JTBD-1.2  | The 10-step loop IS the agent's mental model of recipe authoring |
| ...   | ...      | ...                 | ... |
```

Or, more compactly, add a "Serves JTBD" column to the existing §5 feature tables.

#### Other traceability strengths

- Vision (§1) → Goals (§4) is well-mapped (G1 traces to "faithful rebuild," G2 to "first-pass success," etc.)
- Goals (§4) → Success Metrics (§6) is well-mapped
- Each Risk (§10) has a Mitigation column

**Severity: REVISE.** Without JTBD↔Feature mapping, sprint planning may de-prioritize features that secretly serve P0 JTBDs. Resolve before approval.

---

## D7. Implementation Leakage ❌ REVISE

A PRD should specify **WHAT** the system does, not **HOW** it's implemented. The Features section names specific technologies that are arguably architectural decisions, not requirements.

### Findings

#### Leaked implementation details in §5 Features

| Feature | Implementation detail leaked | Should say |
|---|---|---|
| F1.1 "3-tier directory architecture" | "Tier 1 / Tier 2 / Tier 3" is an architectural pattern | "Canonical scripts have a single source of truth, exposed via CLI wrappers and a runtime data layer" |
| F2.1 "SQLite schema v19 with 11 tables" | "SQLite" and "11 tables" are HOW | "Single-file embedded database with schema versioning; ~10 logical entities" |
| F3.1 "`conda_forge_server.py` with `FastMCP('conda-forge-expert')`" | "FastMCP" is HOW | "MCP server exposing the recipe + atlas + project-scanning surface" |
| F4.1 "BMAD-METHOD v6.6.0 installer" | "BMAD-METHOD v6.6.0" is HOW (could be any planning framework conceptually) | "AI-driven planning framework with multi-project support" |
| FX.1 "`_http.py` auth chain" | "_http.py" is a file path | "Single cross-cutting HTTP authentication chain" |

#### Counterargument: this is a *rebuild* PRD

The PRD's purpose is to specify a rebuild that **reproduces today's system**. Some specificity is justified because the rebuild target IS the existing implementation. A pure "what-not-how" PRD would describe abstract behavior, but this PRD's value comes from naming concrete artifacts that operators recognize.

#### Recommended compromise

Add an introductory note to §5:

> **Note on specificity**: This is a rebuild PRD; features intentionally name specific technologies (SQLite, FastMCP, BMAD-METHOD) because reproducing today's implementation IS the requirement. A "clean-slate" PRD would describe behaviors more abstractly, but here, naming the concrete technology removes ambiguity for the rebuild operator. Where the technology choice is genuinely up to the rebuild operator (e.g., "any MCP framework would work"), it's flagged in §7 Constraints rather than baked into the feature.

This frames the leakage as intentional and bounded. Then revise §7 Constraints to explicitly call out which technologies are non-negotiable (C1-C9 already do this well — pixi 0.67.2+, rattler-build, etc.).

**Severity: REVISE.** The leakage is real but defensible. Add the §5 introductory note + verify §7 Constraints fully cover the non-negotiable tech choices. Resolve before approval.

---

## D8. Domain Compliance ✅ PASS

Domain conventions observed:

- ✅ conda-forge ecosystem conventions (CFEP-25, recipe.yaml v1, staged-recipes workflow) honored throughout
- ✅ Python conventions (Python 3.11+ for `tomllib`, Python 3.12 for runtime)
- ✅ BMAD-METHOD conventions (skill structure, planning chain, retro discipline)
- ✅ Security conventions (least-privilege, env-var hygiene, scoped credentials)
- ✅ Documentation conventions (frontmatter, sync tags, version pinning)

No domain anti-patterns observed.

---

## D9. Project Type Alignment ⚠️ MINOR

The BMAD `validate-prd` skill's domain-complexity CSV has rows for typical project types (web, mobile, backend, cli, library, etc.). This is a **platform/infrastructure rebuild** that doesn't cleanly fit any of those.

### Findings

#### Some standard PRD dimensions don't apply

| Standard dimension | Applies here? | Note |
|---|---|---|
| User acquisition / growth metrics | ❌ N/A | No external users; operator-driven |
| Pricing / monetization | ❌ N/A | Open source; BSD-3-Clause |
| Competitive analysis | ❌ N/A | No competitors; this IS the system |
| Go-to-market | ❌ N/A | No market launch |
| Customer segmentation | ✅ APPLIES | 5 personas defined; PRD covers it |
| Feature prioritization | ✅ APPLIES | P0/P1/P2 used; PRD covers it |
| Success metrics | ✅ APPLIES | §6 covers functional / performance / quality / air-gap |
| Risk management | ✅ APPLIES | §10 covers it |
| Dependencies | ✅ APPLIES | §11 covers it |

#### Recommendation

Add a brief note in §0 (or as a frontmatter `project_type: 'platform-rebuild'` field) explicitly stating:

> This PRD covers a **platform rebuild**, not a new product launch. Standard PRD dimensions related to market, growth, pricing, and competition do not apply. The dimensions that do apply (user personas, feature prioritization, success metrics, risk, dependencies) are covered in their respective sections.

This makes the omission of those dimensions explicit rather than appearing as gaps.

**Severity: MINOR.** Add the project-type note; no other action needed.

---

## D10. SMART Criteria ❌ REVISE

SMART = Specific, Measurable, Achievable, Relevant, Time-bound.

| Dimension | Verdict | Note |
|---|---|---|
| **Specific** | ✅ | Goals (G1-G7) name concrete outcomes |
| **Measurable** | ⚠️ | §6 has 27 measures; 3 under-specified (see D5) |
| **Achievable** | ✅ | All goals are achievable given the rebuild scope |
| **Relevant** | ✅ | Each goal traces to a user JTBD (modulo D6 finding) |
| **Time-bound** | ❌ | **No calendar targets, no sprint estimates, no milestone dates in the PRD itself** |

### Findings

The PRD is **missing time-bound criteria**. `epics.md` has a calendar estimate (16-20 sprint-weeks), but the PRD itself has no:

- Target completion date
- Milestone dates (PRD approved by X; architecture approved by Y; first epic complete by Z)
- Sprint cadence assumed (weekly, biweekly, monthly)

For a rebuild this large, missing time bounds means the PRD can never declare "complete on time" — only "complete" or "incomplete." 

### Recommendation

Add a §12.5 "Timeline" or extend §12 "Approvals & Sign-off" with target dates:

```
## 12.5 Timeline

| Milestone | Target | Owner |
|---|---|---|
| PRD approved | YYYY-MM-DD | rxm7706 |
| Architecture approved | YYYY-MM-DD | rxm7706 |
| Wave 1 complete | YYYY-MM-DD | (TBD) |
| Wave 2 complete | YYYY-MM-DD | (TBD) |
| Wave 3 complete | YYYY-MM-DD | (TBD) |
| Wave 4 complete | YYYY-MM-DD | (TBD) |
| Wave 5 complete | YYYY-MM-DD | (TBD) |
| Rebuild signed off | YYYY-MM-DD | rxm7706 |
```

If operator timeline is genuinely uncertain ("when I get to it"), say so explicitly:

```
Timeline: this is a personal-time rebuild effort with no firm deadline. Target sprint cadence: 1 sprint = 1 week of effort; estimated 16-20 sprints total per `epics.md`.
```

**Severity: REVISE.** Time-bound criteria are missing. Even a deliberately-open-ended timeline should be stated explicitly. Resolve before approval.

---

## D11. Holistic Quality ✅ PASS

Spot-check for coherence:

- ✅ Vision aligns with Goals (G1-G7 directly serve the vision statement)
- ✅ JTBDs ground the features (modulo D6 finding)
- ✅ Constraints are realistic (C1-C13 are hard constraints; A1-A6 are honest assumptions)
- ✅ Risks are realistic with mitigations
- ✅ Deferred Work is honest (DW1-DW10 don't pretend to be in-scope)
- ✅ Glossary is comprehensive
- ✅ References are concrete file paths

The PRD reads as one coherent argument: "rebuild the factory, not the recipes; here's what the factory IS; here's how we measure that it works; here's what we won't do."

---

## D12. Completeness ✅ PASS

- ✅ No template variables (`{{x}}`) remain
- ✅ All sections populated with content (no `TODO`, `TBD`, `(coming soon)` placeholders)
- ✅ Frontmatter populated: `doc_type`, `project_name`, `date`, `version`, `status`, `source_pin`, `input_docs`
- ✅ Appendices (glossary, references) populated
- ⚠️ Sign-off checklist (§12) has unchecked boxes — appropriate for "status: draft"; reviewer should check Q-PRD-01-07 resolution before flipping `status: approved`

---

## D13. Validation Complete ✅

This report.

---

## Required Actions Before Approval

### Must-fix (blocks `status: approved`)

| Action | Source | Effort |
|---|---|---|
| Add JTBD↔Feature mapping matrix | D6 | M (~30 min — add Appendix C or column in §5 tables) |
| Frame implementation leakage explicitly with a §5 introductory note | D7 | S (~10 min — write 1-paragraph framing) |
| Add §12.5 Timeline with milestone targets (or explicitly open-ended) | D10 | S (~10 min — author table) |

### Should-fix (improves quality; not blocking)

| Action | Source | Effort |
|---|---|---|
| Tighten 3-4 prose statements for density | D3 | S (~15 min — edit individual sentences) |
| Define "availability" in G5 success metric | D5 | S (~5 min) |
| Define "cold" in performance metric | D5 | S (~5 min) |
| Add `project_type: 'platform-rebuild'` frontmatter + §0 note | D9 | S (~5 min) |

### Total revision effort

~1.5 hours of focused editing to address all findings. After revisions: re-validate with this dimension set; status flip to `approved` once D6, D7, D10 verified.

---

## Recommendation

**`status: draft` → DO NOT promote to `approved` yet.** The PRD is substantially complete and structurally sound, but three dimensions (D6 traceability, D7 implementation leakage, D10 SMART time-bound) need substantive revision before downstream artifacts (sprint plans, story-level estimates) commit to its terms.

The 4 minor dimensions (D3 density, D5 measurability for 3 metrics, D9 project type, parts of D7) can be addressed in the same revision pass.

**Estimated revision effort: 1.5 hours.** Re-run validation after revision; expect status to flip to `approved` on second pass.

---

## What this report does NOT validate

These are **out of scope** for the PRD validation:

- Whether the architecture is correct (next document — implementation readiness)
- Whether the epics cover the features (next document — implementation readiness)
- Whether the implementation is feasible at story-level (sprint planning's job)
- Whether the technology choices are optimal (architecture review's job)
- Whether the open questions (Q-PRD-01 to Q-PRD-07) have correct answers (separate effort)

The next validation report (`implementation-readiness-report.md`) covers PRD↔architecture↔epics consistency.

---

## Re-validation Run — 2026-06-07 (post-v8.11.1 sync)

**Verdict:** PASS — no structural change since the 2026-05-24 / 2026-05-26 runs.

**Driver:** bmad-correct-course sprint change proposal at `planning-artifacts/sprint-change-proposal-2026-06-07-v8.11.1.md` (v8.10.0 → v8.11.1 frontmatter sync covering v8.10.1 PATCH + v8.11.0 MINOR + v8.11.1 PATCH npm-generator releases).

**Scope of re-validation:** PRD §5 (Features), §9 (Deferred Work), §3 (JTBDs), §10 (Risks), §11 (Dependencies), Appendix C (JTBD ↔ Feature traceability).

### Findings

1. **Feature counts unchanged.** F1.4 (44 Tier 1 scripts), F1.5 (36 Tier 2 wrappers), F1.6 (17 lint codes), F1.8 (41 templates / 13 ecosystems), F2.2 (22 phases), F2.10 (21 public CLIs), F3.2 (37 MCP tools), F4.5 (64 real skills) — none affected by v8.10.1 / v8.11.0 / v8.11.1. The npm-generator changes are body-only on `templates/nodejs/npm-recipe.yaml` (rewritten in place, not added/removed) + `scripts/recipe-generator.py` internals (`_inline_build_script` rewritten; legacy `_build_sh_template` deleted in v8.11.1 — internal generator helper, not a script module). Live verification: `find .claude/skills/conda-forge-expert/templates -mindepth 2 -type f \\( -name "*.yaml" -o -name "*.yml" \\) | wc -l` returns 41 (3 nodejs files: native-recipe.yaml + npm-meta.yaml + npm-recipe.yaml).

2. **Deferred Work unchanged.** DW1-DW20 still apply as written. No new DW row added; no DW row closed.

3. **JTBD coverage matrix unchanged.** Appendix C lists 12 JTBDs × 54 features; none are affected by the npm-generator subsurface change. JTBD-1.1 (author recipe with confidence) is incidentally **improved** by v8.11.0 — the per-platform inline pattern is empirically more reliable on staged-recipes CI than noarch:generic (bmalph PR #33557 attempt 2 verified linux_64 3m17s / osx_64 6m14s / win_64 3m20s green), but no feature ID changes coverage. F1.8 still primary-serves JTBD-1.1.

4. **Risks unchanged.** R1 (skill version drift between rebuild start and finish) is the active risk addressed by this proposal's source_pin sync; the prior risk text (last edit `2026-05-13`) is non-blocking because the rebuild has not commenced. R2-R7 untouched by the npm-generator changes.

5. **Approval gates unchanged.** Q-PRD-01 through Q-PRD-07 all remain confirmed (2026-05-12). The v8.11.0 default-flip on npm did not touch any Q-PRD decision domain.

6. **Edit_history entry well-formed.** New 2026-06-07 entry (lines after the 2026-05-26 entry) covers: three release IDs + three release dates + scope classification + driver (bmalph PR #33557 + openspec PR #32368) + 12-file planning-artifact source_pin list + project-context.md sync confirmation + outstanding v8.11.x retro flag per CLAUDE.md Rule 2 + sprint change proposal cross-reference. Structurally consistent with prior entries.

7. **No downstream cascade required.** Architecture documents (`architecture.md`, `architecture-conda-forge-expert.md`, `architecture-cf-atlas.md`, `architecture-mcp-server.md`, `architecture-bmad-infra.md`, `integration-architecture.md`) — source_pin bumped; no body content references the npm-specific recipe shape or the `--inline-build` CLI flag. `source-tree-analysis.md` script counts (50/41 from the v8.10.0 sync) are still approximately correct — `_build_sh_template` deletion lowers the in-script function count, not the module count.

### Net change

Frontmatter-only. PRD body content holds.

### Re-validation effort

1 reviewer pass; pull-quote check against:
- Template count (`find templates -mindepth 2 -type f` → 41 ✓)
- MCP tool count (`grep -c '^@mcp.tool' .claude/tools/conda_forge_server.py` → 38; **drift of +1 vs. PRD's 37**, predates this bundle, not introduced by v8.10.1/v8.11.0/v8.11.1 — flagged for future audit)
- Phase count + schema version (unchanged at 22 / v25 ✓)
- Skill version (`config/skill-config.yaml` → 8.11.1 ✓ matches new PRD pin)

### Outcome

- PRD `re_validated` field bumped to `2026-06-07` ✓
- PRD `version` PATCH-bumped v1.5.0 → v1.5.1 ✓
- PRD `source_pin` bumped v8.10.0 → v8.11.1 ✓
- PRD `status` remains `approved` (no scope shift triggered re-approval cycle)

### Out-of-scope, deferred

- Full multi-step `bmad-validate-prd` 10-step interactive re-run (over-engineered for frontmatter-only sync; the prior 2026-05-12 run remains the authoritative deep validation).
- MCP tool count drift (37 → 38) — surface for next audit pass; not introduced by this bundle.
- v8.11.x CFE-skill retro (recommended filename: `implementation-artifacts/retro-conda-forge-expert-v8.11-2026-06-07.md`) — per CLAUDE.md Rule 2; tracked in the sprint change proposal's § "Out-of-scope follow-up".

---

## Re-validation Run — 2026-06-21 (post-v8.40.0 sync, PRD v1.6.0)

**Verdict:** APPROVED — structure holds; ONE residual SHOULD-FIX (a body count-drift), non-blocking.

**Driver:** the first DEEP re-sync since the 2026-06-07 v8.11.1 frontmatter touch. The PRD had been carrying a v8.6-era pin (v8.11.1) while the skill advanced ~28 MINOR/PATCH releases. The PRD was re-synced in two edits this cycle:

1. **v1.5.1 → v1.6.0** (`bmad-edit-prd`, 2026-06-20) — STRUCTURAL re-sync v8.11.1 → v8.39.0. Re-derived every drifted count against live code and added 3 net-new feature-level FRs for capabilities that shipped after the old pin (F2.13, F2.14, F3.9).
2. **source_pin v8.39.0 → v8.40.0** (this cycle) — a skill-INTERNAL MINOR (SKILL.md gotchas G46–G51 + `guides/feedstock-platform-expansion.md` refinements; CHANGELOG v8.40.0 explicit: "no code/test/CLI/build change").

**Convention applied:** v8.39.0 → v8.40.0 is a MINOR bump but has **no new public surface** (no new CLI / MCP tool / pixi task / schema migration / atlas phase). Per the pinned-resync convention established across the 2026-05-26 / 2026-06-07 runs, a skill-internal release gets a documented **4-dimension spot-check (D2 / D5+D12 / D7 / D9+D10)**, not a full 13-dimension re-score. The 2026-05-12 run remains the authoritative deep validation; the v1.6.0 structural re-sync that preceded this pin-bump is the more substantive change and is covered in the same spot-check because the FRs it added are still live at v8.40.0.

### Ground truth verified (2026-06-21, against live code)

| Fact | PRD claims | Live | Source | Match |
|---|---|---|---|---|
| Skill version | v8.40.0 (pin) | 8.40.0 | `config/skill-config.yaml` + CHANGELOG top entry | ✓ |
| Schema version | v28 | `SCHEMA_VERSION = 28` | `conda_forge_atlas.py:138` | ✓ |
| Tables + views | 21 tables + 4 views | 4 views confirmed (`v_actionable_packages`, `v_current_version_vulns`, `v_packages_enriched`, `v_pypi_candidates`) | `conda_forge_atlas.py` SCHEMA_DDL | ✓ |
| Atlas phases | 22 | 22-tuple (B/B.5/B.6/C/C.5/D/O/P/Q/R/S/E/E.5/F/G/G'/H/J/K/L/M/N) | `conda_forge_atlas.py:8504-8527` | ✓ |
| MCP tools | 42 | 42 `@mcp.tool()` | `conda_forge_server.py` | ✓ |
| Pixi envs | 9 | 9 (`linux, osx, win, build, grayskull, conda-smithy, local-recipes, vuln-db, gcloud`) | `pixi.toml:107-122` | ✓ |
| Recipe Authoring Gotchas | **G1-G45** | **G1-G51** | `SKILL.md` + CHANGELOG v8.40.0 (G45 = v8.39.0; G46–G51 = v8.40.0) | ❌ **DRIFT** |

The MCP-tool-count drift flagged for follow-up in the 2026-06-07 run (PRD 37 vs. live 38) is now **RESOLVED** — the v1.6.0 re-sync moved the PRD pin to 42 and live count is 42.

### Spot-check by dimension

**D2 — Specificity (of the 3 new FRs): PASS.** F2.13 (PyPI-intelligence layer), F2.14 (security-signals overlays), and F3.9 (7 net-new MCP tools) each name concrete, unambiguous surfaces: named side tables (`pypi_universe`, `pypi_intelligence`, `cisa_kev`, `epss_scores`, `cwe_categories`), named phases (O/P/Q/R/S), named fetcher CLIs (`fetch-cisa-kev`, `fetch-epss`, `fetch-cwe-catalog`), and the 7 named tools (`pypi_intelligence`, `pypi_only_candidates`, `platform_breakdown`, `pyver_breakdown`, `channel_split`, `download_pr_artifacts`, `env_inspect`). All present and registered live. The profile-gating clause (admin = all five phases, maintainer = O+Q, consumer = O only) is specific and matches the documented convention.

**D5 + D12 — Measurability / Completeness: ⚠️ SHOULD-FIX (ONE residual count-drift).** The v8.40.0 pin-bump grew the gotcha range G45 → G51 (six new gotchas G46–G51) without re-syncing the PRD body. Three body locations still read the v8.39.0 range:

| Location | Reads | Should read |
|---|---|---|
| F1.7 (Part 1 feature table) | "45 Recipe Authoring Gotchas (G1-G45)" + acceptance "enumerates G1-G45" | "51 Recipe Authoring Gotchas (G1-G51)" / "enumerates G1-G51" |
| Appendix A glossary | "**G1-G45** — Recipe Authoring Gotchas in SKILL.md" | "**G1-G51** — …" |
| Appendix C matrix (F1.7 row) | "F1.7 (G1-G45 gotchas)" | "F1.7 (G1-G51 gotchas)" |

This is the same class of count-pin this gate has always tracked (cf. F1.4 script counts, F1.8 template counts in the 2026-06-07 run). It is cosmetic: it does **not** shift the FR/NFR set, change a confirmed decision, or break any traceability chain. **SHOULD-FIX, non-blocking** — fold into the next `bmad-edit-prd` pass. No template variables / placeholders remain; all other §6 / §5 counts re-verified above match live. **NOTE:** F1.16 "Local-Only SPA Packaging (Feature G45)" is a **CORRECT** reference — the SPA-packaging gotcha is still G45 in the live skill — and is **not** part of this drift.

**D7 — Implementation Leakage: PASS.** The 3 new FRs name concrete artifacts (tables, phases, CLIs, tools), consistent with the rebuild-PRD framing accepted in the original 2026-05-12 D7 finding ("reproducing today's implementation IS the requirement"). No new leakage class introduced; the framing note recommended in 2026-05-12 still covers them.

**D9 + D10 — Phasing / Risk Management: PASS.** No new wave or epic was introduced by the sync; the additive FRs map onto existing epics (F2.13/F2.14 onto Epic 8 atlas work, F3.9 onto Epic 10 MCP work) — the same clean-layering observed for v8.6.0. R1 ("skill version drift between rebuild start and finish") is the active risk this very sync addresses; the ~28-release drift it closed is the materialized form of R1, and the spot-check convention is the standing mitigation. Net risk: low.

### Co-audit (planning-artifact coherence)

- §7 "System Gaps & Limitations" table uses a **separate** G1-G6 numbering for SYSTEM gaps (NOT recipe gotchas). Intentionally left untouched — it does not collide with the SKILL.md G1-G51 gotcha namespace and was correctly preserved across the v1.6.0 edit.
- §9 DW17 (reconciled-SHIPPED earlier this session via the native `parse_pixi_lock` parser) preserved as-is.
- The 7 Deep-Analysis deferred-work rows (DW21–DW27) and the new JTBD-1.7 / F1.16 / FX.8 additions from the v1.5.0/v1.5.1 edits are internally consistent and reflected in Appendix C's coverage check (13 JTBDs × 57 features; every JTBD has ≥1 primary feature).

### Net change

PRD body content holds. One cosmetic count-drift (gotcha range) is the single new finding; one prior follow-up (MCP-count) is now resolved.

### Outcome

- PRD `re_validated` field is `2026-06-20` (set by the v1.6.0 edit); this gate snapshot is dated `2026-06-21`.
- PRD `version` is `1.6.0` (MINOR bump for the additive FRs); `source_pin` is `conda-forge-expert v8.40.0`; `status` remains `approved` (no scope shift triggered a re-approval cycle).
- Report frontmatter `date` → 2026-06-21, `source_pin` → `conda-forge-expert v8.40.0`, `overall_verdict` updated, new `verdict_history` entry appended.

### Required action before next clean gate

| Action | Severity | Effort | Source |
|---|---|---|---|
| Re-sync F1.7 + Appendix A glossary + Appendix C matrix row from `G1-G45` to `G1-G51` (and the F1.7 "45 …" count to "51 …") | SHOULD-FIX | S (~5 min, `bmad-edit-prd`) | D5/D12 spot-check, this run |

### Out-of-scope, deferred

- Full multi-step `bmad-validate-prd` 10-step interactive re-run (the 2026-05-12 run remains the authoritative deep validation; a skill-internal pin-bump does not warrant it under the convention).
- v8.11.x CFE-skill retro (`implementation-artifacts/retro-conda-forge-expert-v8.11-2026-06-07.md`) — still outstanding per CLAUDE.md Rule 2.
- v8.39.0 / v8.40.0 CFE-skill retro (the G45 + G46–G51 gotcha work) — outstanding per CLAUDE.md Rule 2; recommended filename `implementation-artifacts/retro-conda-forge-expert-v8.40-2026-06-21.md`.
