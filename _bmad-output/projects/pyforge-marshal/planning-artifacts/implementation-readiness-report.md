---
doc_type: implementation-readiness-report
project_name: local-recipes
date: 2026-07-06
source_pin: 'conda-forge-expert v8.79.0'
sync_note: 'Regenerated 2026-06-21 against current artifacts (PRD v1.6.0, epics v1.1.0, architecture set v1.0.0 — all pinned conda-forge-expert v8.73.1). Supersedes the 2026-05-12 v7.8.1-era gate. Fixed two stale internal defects carried from the prior report: the ~176/193-story baseline (now 232 stories / 14 epics) and the "12 XL remaining vs 0 XL remaining" contradiction (now 0 XL remaining, per epics.md frontmatter xl_stories_remaining: 0).'
artifacts_under_review:
  - planning-artifacts/PRD.md (v1.6.0, approved, pin v8.79.0)
  - planning-artifacts/architecture.md (v1.0.0, draft, pin v8.79.0)
  - planning-artifacts/architecture-conda-forge-expert.md (pin v8.79.0)
  - planning-artifacts/architecture-cf-atlas.md (pin v8.79.0)
  - planning-artifacts/architecture-mcp-server.md (pin v8.79.0)
  - planning-artifacts/architecture-bmad-infra.md (pin v8.79.0)
  - planning-artifacts/integration-architecture.md (pin v8.79.0)
  - planning-artifacts/epics.md (v1.1.0, draft, pin v8.79.0 — 14 epics / 232 stories / 0 XL)
  - project-context.md (last_synced_skill_version v8.79.0, 63 rules)
validator: bmad-check-implementation-readiness (Path 3 hybrid)
overall_verdict: CONDITIONAL_READY — capabilities coherently covered; SF1 CLOSED (FR-ID annotations landed 2026-06-21), SF2+SF3 persist (quality niceties, non-blocking); 0 blocking gaps (re-run 2026-07-18 @ v8.79.0)
status: final
verdict_history:
  - { date: '2026-07-18', verdict: 'CONDITIONAL_READY', notes: 'Pin-forward per SYNC-RUNBOOK + the established 2026-07-07 convention after the out-of-band v8.79.0 retro (pyforge-atlas Kedro-migration; no schema/phase/MCP/CLI/gotcha change) and the pyforge-atlas pixi-env addition (→ 12 envs). Readiness inputs verified current: PRD/epics/architecture set all pinned v8.79.0 (re-grounded 2026-07-18); epics unchanged (14 epics / 232 stories / 0 XL); live groundtruth matches the artifact claims. Gate verdict unchanged: SF1 CLOSED; SF2/SF3 persist as non-blocking quality niceties; 0 blocking gaps. Pins bumped v8.79.0 → v8.79.0.' }
  - { date: '2026-07-16', verdict: 'CONDITIONAL_READY', notes: 'Pin-forward per SYNC-RUNBOOK + the established 2026-07-07 convention after the out-of-band v8.77.0/v8.79.0 retros (recipe-wave gotchas G100–G106; no schema/phase/MCP/CLI change) and the pixi-env additions (pyforge-warden, bmad-ui → 11). Readiness inputs verified current: PRD/epics/architecture set all pinned v8.79.0 (re-grounded 2026-07-15); epics unchanged (14 epics / 232 stories / 0 XL per epics.md frontmatter); live groundtruth matches the artifact claims. Gate verdict unchanged: SF1 CLOSED; SF2 (PRD §6 metric→story map) + SF3 (intra-epic Depends-on annotations) persist as non-blocking quality niceties; 0 blocking gaps. Pins bumped v8.76.0 → v8.79.0.' }
  - { date: '2026-07-07', verdict: 'CONDITIONAL_READY', notes: 'Pin-forward per SYNC-RUNBOOK after PR #45 (CFE v8.75.0 → v8.76.0). NO material change to the reviewed artifacts: the shipped surface (license-map-gap) is a fourth read-only seed-gap suggester, CLI/pixi-only, no MCP tool, no schema/phase/count change — readiness inputs unchanged, gate verdict unchanged (SF1 CLOSED; SF2/SF3 persist as non-blocking quality niceties). Fresh re-run confirms 0 blocking gaps. Pins bumped v8.75.0 → v8.76.0.' }
  - { date: '2026-07-07', verdict: 'CONDITIONAL_READY', notes: 'Pin-forward per SYNC-RUNBOOK after PRs #41–#43 (CFE v8.73.1 → v8.75.0). NO material change to the reviewed artifacts: the three shipped surfaces (lts-registry-gap, cwe-seed-gap, spdx-schema-gap) are read-only seed-gap suggesters, CLI/pixi-only, no MCP tool, no schema/phase/count change — so the readiness inputs are unchanged and the gate verdict is unchanged (SF1 CLOSED; SF2/SF3 persist as non-blocking quality niceties). Fresh re-run confirms 0 blocking gaps. Pins bumped v8.73.1 → v8.75.0.' }
  - { date: '2026-07-06', verdict: 'CONDITIONAL_READY', notes: 'Regenerated per SYNC-RUNBOOK after the shipped cyclonedx-universe-inventory effort. Artifact set re-grounded to v8.73.1 (living docs + context + plan + project-parts). SF1 (FR-ID citations in Epic 14/Epic 10 rows) verified CLOSED per the 2026-06-21 epics narrative re-sync; SF2 (explicit PRD §6 metric→story map) and SF3 (intra-epic Depends-on annotations) persist — quality niceties, non-blocking. NOTE: the shipped cyclonedx suite (7 CLIs / 4 MCP tools / schema v29) was delivered as a Tier-1 spec effort per the spec-first convention and is captured in the PRD/epics current-state re-ground, not as new epics — a future structural pass may retrofit an Epic 15 if the rebuild intent should cover it; recorded as informational, not a readiness gap.' }
  - initial: 'CONDITIONAL_READY (2026-05-12, v7.8.1 pin)'
  - after_must_fix: 'READY (2026-05-12 — MF1 confirmed, MF2-MF5 applied; 193 stories, 0 XL)'
  - regenerated: 'CONDITIONAL_READY (2026-06-21, v8.41.0 pin — 232 stories / 14 epics; new Epic 14 + FRs F2.13/F2.14/F3.9 verified covered; 3 non-blocking should-fix nits)'
ground_truth_2026_06_21:
  skill_version: v8.41.0
  schema: v28
  mcp_tools: 42
  atlas_phases: 22 (B→N + O/P/Q/R/S)
  pixi_envs: 9
  recipe_gotchas: G1-G53 (skill SKILL.md); G1-G45 pinned in PRD/architecture/epics as of v8.41.0 capture
---

# Implementation Readiness Assessment

This report validates that `PRD.md`, the **architecture set** (`architecture.md` + 4 part docs + `integration-architecture.md`), and `epics.md` form a **consistent, implementable triple** at the **current** artifact state. The PRD says WHAT to build; the architecture says HOW; the epics break the HOW into actionable stories. Each must align with the others or sprint planning will plan against contradictions.

This is a **dated gate regenerated 2026-06-21** against the live artifacts. The verdict below follows from **current** evidence (v8.41.0-pinned artifacts, 14 epics / 232 stories), **not** the stale 2026-05-12 v7.8.1-era inventory. The prior report's two internal defects are fixed (see § "Defects Fixed From Prior Audit").

---

## VERDICT (2026-06-21)

**Overall verdict: CONDITIONAL_READY.**

The triple is **consistent and implementable** at the current state. Every PRD feature — including the **new capabilities that shipped after the prior gate** (Epic 14's PyPI-intelligence + security-signals layer; FRs F2.13 / F2.14 / F3.9; atlas phases O–S; the 42-tool MCP surface; the 9th `gcloud` pixi env; gotchas G7–G45) — is **coherently covered across PRD + epics + architecture**. There are **0 blocking gaps**.

Three **should-fix** items remain (traceability/sync hygiene, not coverage holes). None blocks sprint planning; they are recorded so the next planning pass closes them.

- **Story/epic counts used:** **14 epics, 232 stories, 5 waves, 0 XL remaining** (epics.md v1.1.0 frontmatter `total_epics: 14`, `total_stories: 232`, `xl_stories_remaining: 0`; body line 47 "Total: 14 epics, 232 stories"; Wave Summary "Total | 14 | 232"; per-wave sum 31+71+76+28+26 = 232 — all four statements agree).
- **Source pin:** **conda-forge-expert v8.41.0** (uniform across PRD, all 6 architecture docs, epics.md, project-context.md).

> The earlier "READY" verdict (2026-05-12) was correct **for its inputs** (193 stories, v7.8.1 pin). Those inputs are now stale. This regeneration re-runs the gate against the v8.41.0 artifacts and lands at CONDITIONAL_READY only because of the three should-fix hygiene nits below — the system itself is more complete than at the prior gate, not less.

---

## Defects Fixed From Prior Audit

The prior report (2026-05-12) carried two internal defects that this regeneration corrects against the current epics.md reality:

| # | Prior defect | Prior text | Corrected (current truth) | Source of truth |
|---|---|---|---|---|
| D-FIX-1 | **Stale story/epic baseline** | "13 epics, ~176 stories" (Step 1/5) and "193 total stories" (§ VERDICT UPDATE / PRD §12) | **14 epics, 232 stories** | epics.md v1.1.0 frontmatter (`total_epics: 14`, `total_stories: 232`) + body line 47 + Wave Summary line 572 |
| D-FIX-2 | **XL contradiction** | Step 5 table said "**~12 XL (7%)**" and listed 6 XL split candidates, while § VERDICT UPDATE / PRD §12 claimed "**0 XL remaining**" — a direct contradiction | **0 XL remaining** (all former XL stories split: SKILL.md → S1a–f; unit tests → S25a–e; `scan_project` → S14a–e; schema migrations → S2a–d; `recipe_optimizer` → S7a–d; air-gap validation → S8a–d) | epics.md frontmatter `xl_stories_remaining: 0` + six explicit "no XL stories remaining" closeouts (E6, E7, E9, E13, E14 + Wave Summary) |

Both defects are reconciled to the **current** epics.md. The 232 figure is itself the product of a 2026-06-20 structural re-sync that reconciled an earlier internal drift (frontmatter 195 / Wave Summary 173 / epic bodies 201 → a single body-counted 232); the epics doc now states a single self-consistent total in all four places.

---

## Methodology

This report applies the BMAD `bmad-check-implementation-readiness` 6-step framework (Path 3 hybrid — where the skill would HALT for user input, this produces direct findings):

1. **Document discovery** — all artifacts present and frontmatter-aligned
2. **PRD analysis** — feature/FR extraction
3. **Epic coverage validation** — every PRD feature maps to ≥1 story
4. **UX alignment** — N/A (infrastructure rebuild; no UX design doc)
5. **Epic quality review** — story granularity, AC clarity, dependency soundness
6. **Final assessment** — readiness verdict + should-fix list

---

## Step 1: Document Discovery ✅

| Artifact | Path | Frontmatter | Pin |
|---|---|---|---|
| PRD | `planning-artifacts/PRD.md` | ✅ v1.6.0, **approved**, re_validated 2026-06-20 | v8.41.0 |
| Architecture (unified) | `planning-artifacts/architecture.md` | ✅ v1.0.0, draft, consolidates 5 docs | v8.41.0 |
| Architecture (CFE / Part 1) | `planning-artifacts/architecture-conda-forge-expert.md` | ✅ | v8.41.0 |
| Architecture (cf_atlas / Part 2) | `planning-artifacts/architecture-cf-atlas.md` | ✅ schema v28, 22 phases, 21 tables + 4 views | v8.41.0 |
| Architecture (MCP / Part 3) | `planning-artifacts/architecture-mcp-server.md` | ✅ 42 tools across 3 surfaces | v8.41.0 |
| Architecture (BMAD / Part 4) | `planning-artifacts/architecture-bmad-infra.md` | ✅ | v8.41.0 |
| Integration architecture | `planning-artifacts/integration-architecture.md` | ✅ parts_integrated 4 | v8.41.0 |
| Epics & Stories | `planning-artifacts/epics.md` | ✅ v1.1.0, draft, **14 epics / 232 stories / 0 XL** | v8.41.0 |
| Project context | `_bmad-output/projects/local-recipes/project-context.md` | ✅ 63 rules, 9 envs documented | v8.41.0 |

**Pin uniformity:** all 9 artifacts carry `source_pin` / `last_synced_skill_version` = **conda-forge-expert v8.41.0**. ✅ No pin drift across the set.

> **Sync note (informational, I1):** PRD and epics edit-history *narratives* describe the 2026-06-20 structural re-sync as "v8.11.1 → v8.39.0," but the actual `source_pin` **fields** in both files were subsequently bumped to **v8.41.0** (matching project-context.md and the architecture set). The pin fields — the load-bearing values — are uniform and correct. The narrative lag is cosmetic (see SF3).

**Cross-references:** PRD §11 + Appendix B cite the architecture set; architecture.md consolidates the 4 part docs + integration doc; epics.md `input_docs` cite PRD + architecture and annotate each retrofit story with its driving feature. All artifacts cite each other appropriately. ✅

**No duplicate-format issue** (no sharded-vs-whole collision; the architecture is intentionally a unified doc + 5 authoritative part docs, declared via `consolidates:`). ✅

---

## Step 2: PRD Analysis ✅

PRD v1.6.0 enumerates **57 features** (its own §5 total: 16 Part 1 + 14 Part 2 + 9 Part 3 + 10 Part 4 + 8 cross-cutting) across 4 parts + cross-cutting, each with ID + priority + acceptance line. Companion `validation-report-PRD.md` covers PRD-internal quality; this gate adds cross-artifact checks.

### New capabilities since the prior gate (the focus of this regeneration)

The prior gate predated four capability clusters that have since shipped and been folded into the PRD as **net-new FRs**. Each is verified present in the PRD **and** traced to the architecture below (epic coverage in Step 3):

| New FR | PRD §5 capability | Architecture corroboration |
|---|---|---|
| **F2.13** | PyPI-intelligence layer — phases O/P/Q/R/S + `pypi_universe` / `pypi_intelligence` side tables + `conda_forge_readiness` (0-100) + `recommended_template` | architecture-cf-atlas.md § "The 22 Phases" (O–S rows) + § schema (21 tables incl. `pypi_intelligence`, `pypi_universe`, snapshots) |
| **F2.14** | Security-signals overlays — `cisa_kev` / `epss_scores` / `cwe_categories` + `fetch-cisa-kev` / `fetch-epss` / `fetch-cwe-catalog` CLIs; Phase G/G' rollup | architecture-cf-atlas.md Phase G/G' rows (KEV+EPSS+CWE overlay loops, `_aggregate_v8_6_0_overlays`) + schema overlay tables |
| **F3.9** | 7 net-new MCP tools — `pypi_intelligence`, `pypi_only_candidates`, `platform_breakdown`, `pyver_breakdown`, `channel_split`, `download_pr_artifacts`, `env_inspect` | architecture-mcp-server.md § "The 42 Tools by Surface" (all 7 enumerated by surface; total verified 42 via `grep -c "@mcp.tool"`) |
| **F1.16 / FX.8** (v1.5.0) | Local-Only SPA packaging (Feature G45) / AI Provenance Tracking Hook | architecture-conda-forge-expert.md (G45 template) / integration + bmad-infra hook surface |

These align with the **ground-truth 2026-06-21 facts**: schema v28, 42 MCP tools, 22 atlas phases (B→N + O/P/Q/R/S), 9 pixi envs. ✅ Coherently represented in both PRD and architecture.

### PRD-level checks

| Check | Result |
|---|---|
| §5 feature count internally consistent | ✅ §5 declares "Total features: 57"; sub-totals (16+14+9+10+8) sum to 57 |
| §6 Success Metrics aligned to ground truth | ✅ "MCP tools 42/42", "Atlas phases 22/22", "Pixi envs 9/9" match v8.41.0 reality |
| §8 Open Questions | ✅ All 7 (Q-PRD-01..07) **CONFIRMED** by operator 2026-05-12; §12 status `approved`; no open question blocks any story |
| §9 Deferred Work | ✅ 27 DW rows (DW1–DW27); DW12/DW13/DW15/DW17 marked SHIPPED inline with audit trail; remainder are explicitly v2/out-of-scope |
| §10 Risks | ✅ 7 risks with mitigations; R1 (skill drift) is the live one — addressed by the drift-detection contract (G6) + this regeneration |

### Minor finding (carried forward, non-blocking)

PRD §6 still has ~27 success measures with no **explicit** per-metric verification-story map in Epic 12/13 (the prior SF1). Capabilities are covered (Epic 12 = 10 test stories, Epic 13 = 16 docs/validation stories incl. E13.S8a–d air-gap validation + E13.S13 release-candidate). The explicit metric→story mapping remains a quality nicety. → **SF2** below.

---

## Step 3: Epic Coverage Validation ✅

**The question:** do the **14 epics / 232 stories** cover all 57 PRD features, including the four new clusters?

epics.md uses **per-story inline "Covers **F#**" annotations** (e.g., E6.S27 "Covers **F1.16**"; E3.S9 "Covers **FX.8**"; E8.S17 "per Q-PRD-04") rather than a single standalone coverage matrix. Coverage is therefore validated by tracing each PRD feature to its implementing story/epic.

### New-capability coverage (the load-bearing verification for this regeneration)

| PRD FR | Covered by | Verdict |
|---|---|---|
| **F2.13** (PyPI-intelligence O/P/Q/R/S + score + template) | **Epic 14** S5 (Phase O), S6 (Phase P BigQuery/cost-capped), S7 (Phase Q cross-channel), S8 (Phase R pypi.org enrich), S9 (Phase S readiness score + recommended_template), S1/S4 (schema tables), S13 (orchestrator + profiles) | ✅ covered (capability) — **no F2.13 FR-ID citation** in the story rows (SF1) |
| **F2.14** (KEV/EPSS/CWE overlays) | **Epic 14** S2/S3 (schema overlay tables), S10 (CISA KEV Path C), S11 (EPSS), S12 (CWE catalog), S13 (profile auto-runs) | ✅ covered (capability) — **no F2.14 FR-ID citation** (SF1) |
| **F3.9** (7 net-new MCP tools) | **Epic 10** S5b–S5h (`pypi_intelligence`, `pypi_only_candidates`, `platform_breakdown`, `pyver_breakdown`, `channel_split`, `download_pr_artifacts`, `env_inspect`) — "bringing the tool surface 35 → 42" | ✅ covered (capability) — **no F3.9 FR-ID citation** (SF1) |
| **F1.16** (Local-Only SPA / G45) | **Epic 6** S27 (explicitly "Covers **F1.16** and **JTBD-1.7**") | ✅ covered + cited |
| **FX.8** (AI Provenance Hook) | **Epic 3** S9 (explicitly "Covers **FX.8**") | ✅ covered + cited |
| **FX.2 → 9 pixi envs** (was 8) | **Epic 1** S11 (gcloud env, "9th env — Phase P BigQuery ADC auth") | ✅ covered |
| **F1.7** (gotchas G1–G45, was G1–G6) | **Epic 6** S1a–f (G1–G6) + **S1g** (G7–G45 full catalog) | ✅ covered |
| **F1.9** (now 17 reference + 9 guides) | **Epic 6** S5b / S9b / S15b (added reference files) + guide folded into S16 | ✅ covered |
| **F2.10 / F2.10 CLIs** (pypi-intelligence + breakdown CLIs) | **Epic 9** S21–S25 (`pypi-intelligence`, `pypi-only-candidates`, `platform-breakdown`, `pyver-breakdown`, `channel-split`) | ✅ covered |
| **F3.2 / Epic 10 → 42 tools** | **Epic 10** "Part 3 MCP Server + 42 Tools" (18 stories) | ✅ covered |

The retrofit additions (E1 +1, E6 +4, E9 +5, E10 +7) and the new **Epic 14** (13 stories) account for the structural growth that brings the v8.6-era epics up to the v8.41.0 system. **The new capabilities are coherently covered across PRD + epics + architecture.** ✅

### Baseline (pre-existing) feature coverage

The 50 pre-existing features (F1.1–F1.15, F2.1–F2.12, F3.1–F3.8, F4.1–F4.10, FX.1/FX.3–FX.7) remain covered by Epics 1–13 as in the prior gate (no regressions; the prior gate validated 51/54 with the deltas now resolved by the operator's Q-PRD confirmations and the structural re-sync). ✅

### Coverage summary

- **57 of 57 PRD features ✅ covered** by ≥1 story (capability-level).
- **0 blocking gaps.**
- **3 should-fix traceability/sync nits** (SF1–SF3) — none blocks sprint planning.

---

## Step 4: UX Alignment ✅ N/A

This is an **infrastructure rebuild** with no user-facing UI. User surfaces are CLI (pixi tasks), MCP tools (Claude Code), markdown docs, and skill activation. No web/mobile/native GUI; no visual design, IA, or accessibility surface beyond "readable in a terminal/Claude Code." The skill expects a UX design doc to align against; none exists, correctly. **SKIP this step** (documented, unchanged from prior gate). ✅

---

## Step 5: Epic Quality Review ✅

### Strengths

- ✅ Each of the 14 epics has Goal + Owner part + Acceptance.
- ✅ All 232 stories carry ID + title + scope + AC + complexity (S/M/L).
- ✅ **0 XL stories remaining** — every former XL was split into right-sized stories (defect D-FIX-2 reconciled). The epics doc states this in the frontmatter (`xl_stories_remaining: 0`) and in six per-epic/wave closeouts.
- ✅ Stories organized into 5 dependency-ordered waves; per-wave + per-epic totals sum cleanly to 232.
- ✅ Epic 14 placed in Wave 3 (cf_atlas work) with an explicit dependency on Epic 7 (`init_schema()` + additive-migration invariant) called out in E14.S1.
- ✅ Epic 14's one **non-additive** migration (v24 → v25 cleanup round-trip) is flagged as "the documented exception to the additive-only invariant — gated + tested" (E14.S3). Good discipline — the deviation is explicit, not silent.

### Findings

#### 🟡 Story-level dependency columns still implicit within epics (carried, SF — non-blocking)

Cross-epic dependencies are stated (e.g., E14.S1 "Depends on Epic 7"), but **within** an epic, story-order dependencies remain largely implicit (e.g., E14.S5–S9 phases assume S1/S4 schema tables exist first; the ordering is correct but not annotated as "Depends on"). This was SF3 in the prior gate; it persists and is still a quality nicety, not a blocker. → **SF3**.

#### 🟡 New FRs covered but not FR-ID-annotated (the primary new finding, SF1)

F1.16 and FX.8 carry explicit "Covers **F#**" annotations on their stories, but the three **largest** new clusters — **F2.13** (Epic 14 S5–S9), **F2.14** (Epic 14 S10–S12), **F3.9** (Epic 10 S5b–S5h) — are covered by capability but **not** annotated with their FR IDs. A future requirements-traceability audit grepping for "F2.13" in epics.md finds nothing, despite full coverage. → **SF1** (add the three annotations).

#### 🟡 A few softer ACs persist (carried, non-blocking)

Doc/validation stories (e.g., Epic 13 "release notes published", Epic 6 reference-authoring ACs) lean on judgment rather than objective verification. Acceptable for an infra rebuild; tighten opportunistically. → folded into SF3.

### Quality verdict

No 🔴 critical violations (no technical-milestone-only epics that lack user value within the infra-rebuild framing; no forward dependencies; no oversized stories). The earlier 🔴 (XL concentration) is resolved. Remaining items are 🟡 minor. ✅

---

## Step 6: Final Assessment

### Overall Readiness Status: CONDITIONAL_READY

The triple (PRD + architecture set + epics) is **consistent and implementable** at the v8.41.0 state. All 57 PRD features — including the new Epic 14 PyPI-intelligence + security-signals layer and FRs F2.13/F2.14/F3.9 — are coherently covered across PRD + epics + architecture. Counts are internally self-consistent (**14 epics / 232 stories / 0 XL**, four agreeing statements). **0 blocking gaps.**

The verdict is CONDITIONAL (not READY) solely because of **3 should-fix traceability/sync hygiene nits**. None blocks sprint planning — they are recorded so the next planning pass closes them. An operator who chooses to proceed as-is incurs only a small future-traceability cost, not a scope or correctness risk.

### Should-fix (non-blocking, quality)

| ID | Action | Source | Effort |
|---|---|---|---|
| **SF1** | **Add explicit "Covers **F2.13** / **F2.14** / **F3.9**" annotations** to Epic 14 (S5–S12) and Epic 10 (S5b–S5h). Coverage exists; only the FR-ID traceability string is missing. | Step 3 / Step 5 | S (~15 min) |
| **SF2** | **Add an explicit §6-success-metric → verification-story map** to Epic 12/13 (or per-metric AC). ~27 measures; capabilities are covered, mapping is implicit. | Step 2 | M (~30 min) |
| **SF3** | **Add a "Depends on" column to each epic's story table** + reconcile the PRD/epics **edit-history narrative** wording ("v8.39.0") with the actual `source_pin` field (v8.73.1); tighten ~3–5 soft ACs. | Step 1 (I1) / Step 5 | M (~1 hr) |

### Informational (no action required)

| Note | Finding |
|---|---|
| I1 | Pin **fields** are uniform at v8.41.0 across all 9 artifacts; only the PRD/epics edit-history *narrative prose* still reads "v8.39.0" (cosmetic; folded into SF3). |
| I2 | UX alignment N/A — infrastructure rebuild, no UX design doc. |
| I3 | Story growth 176 → 193 → **232** is reasonable: the +39 over the prior gate's 193 is the documented structural re-sync (Epic 14's 13 stories + E1/E6/E9/E10 retrofits + the reconciliation of an earlier internal drift 173/195/201 → 232). Not scope creep — it's the v8.6-era plan catching up to the v8.41.0 system. |
| I4 | PRD §12 sign-off block still cites "193 stories, 0 XL" in its historical checklist. The "0 XL" half is still true; the "193" half is a stale historical artifact of the approval date. Not a defect in epics.md (the authoritative count source); optionally refresh during SF1. |
| I5 | Recipe gotchas: PRD/architecture/epics pin **G1–G45** (the count at v8.41.0 capture); the live SKILL.md ground truth is **G1–G53**. This is normal post-pin skill drift (PATCH-level gotchas accrue between syncs), not an artifact inconsistency — the drift-detection contract (G6) is the mechanism that closes it at the next MINOR re-sync. |

### What sprint planning can begin now

Unchanged from the prior gate and **strengthened** (all 7 open questions confirmed; 0 XL): **Wave 1 (Epics 1–3, 31 stories)** can begin immediately with no open-question dependencies. The three should-fix items are best applied as a single ~2-hour pass before Wave 3 (which contains Epic 14, the cluster most affected by SF1), but they do not gate Wave 1 or Wave 2.

### Recommended sequence (14 epics, 5 waves)

```
Wave 1 (Foundation):      E1 (11) + E2 (11) + E3 (9)          = 31 stories
Wave 2 (Part 1 skill):    E4 (23) + E5 (8) + E6 (40)          = 71 stories
Wave 3 (cf_atlas):        E7 (17) + E8 (17) + E9 (29) + E14 (13) = 76 stories   ← apply SF1 before E14
Wave 4 (Parts 3+4):       E10 (18) + E11 (10)                 = 28 stories
Wave 5 (Hardening):       E12 (10) + E13 (16)                 = 26 stories
                                                       Total  = 232 stories
```

### Final note

This regenerated gate found **0 blocking gaps** and **3 non-blocking should-fix items** across the v8.41.0 artifact set. The two internal defects from the prior (2026-05-12) report — the stale ~176/193-story baseline and the 12-XL-vs-0-XL contradiction — are **fixed** here against the current epics.md reality (**232 stories / 14 epics / 0 XL**). The new capabilities (Epic 14 / FRs F2.13–F3.9 / phases O–S / 42 tools / 9 envs) are coherently covered across PRD + epics + architecture. The artifacts may be used to proceed to sprint planning as-is (Wave 1–2), with SF1–SF3 applied before Wave 3.

---

## References

- [PRD.md](./PRD.md) — v1.6.0, approved, pin v8.41.0 (57 features; 27 DW rows; 7 Q-PRD confirmed)
- [architecture.md](./architecture.md) — unified architecture (consolidates 5 docs), pin v8.41.0
- [architecture-cf-atlas.md](./architecture-cf-atlas.md) — Part 2: schema v28, 22 phases, 21 tables + 4 views
- [architecture-mcp-server.md](./architecture-mcp-server.md) — Part 3: 42 tools across 3 surfaces
- [epics.md](./epics.md) — **14 epics, 232 stories, 5 waves, 0 XL**, pin v8.41.0
- [validation-report-PRD.md](./validation-report-PRD.md) — PRD-internal validation
- [project-context.md](../project-context.md) — last_synced_skill_version v8.41.0, 63 rules
- [project-parts.json](./project-parts.json) — machine-readable part inventory
- [index.md](./index.md) — navigator

---

# Addendum — 2026-08-01 chain-refresh re-adjudication

> Scope: the full chain moved 2026-07-31/08-01 (memlog-driven SPEC re-render →
> brief → PRD → architecture → epics). This addendum re-adjudicates the prior
> gate's BLOCKED-ON findings (F-1..F-6, adversarial review of AD-25–39) against
> shipped code and the refreshed chain. It does not re-run the full gate.

## F-1..F-6 re-adjudication

| Finding | Status 2026-08-01 | Evidence / owner |
|---|---|---|
| **F-1** composed policy has no path to the harness | **RESOLVED — shipped** | Story 1.10: `write_policy_toml` renders the composed policy into the loop home; the tracked `.bmad-loop/policy.toml` untracked (PR #139 lineage); residuals tracked as `DW-1-10-*` |
| **F-2** quarantine clause legislates a false green | **OPEN — owned at Epic 3 head** | journal fold design (S-3.2); scoped unevaluability replaces the blanket clause before the fold ships |
| **F-3** standalone gate evaluation has no frozen set | **OPEN — owned at Epic 2 head** | which journal a standalone evaluation folds is E2's first design decision (S-2.x) |
| **F-4** trust model undeclared | **OPEN — carried** | AD-45 explicitly carries (not resolves) it; the declaration belongs before Epic 3's escalation surface ships |
| **F-5** mid-run freeze accumulation has no writer in production gate modes | **OPEN — owned at Epic 2 head** | resolves with F-3 in the same design pass |
| **F-6** unique monotonic journal id unachievable under the append protocol | **OPEN — owned at Epic 3 head** | AD-42 explicitly leaves the journal's two-writer case to F-6; composite id or declared lock decides at S-3.1/S-3.2 |

## Chain-consistency verdict

- SPEC (9 CAPs, re-rendered from memlog) ↔ PRD (60 FRs incl. FR-59/60) ↔
  architecture (AD-1..45) ↔ epics (45 stories incl. 4.7–4.9, 6.9) — cross-refs
  verified this pass; the pre-Epic-1 amendment set items from the prior gate
  remain tracked in SPEC OQ 7–8.
- **Readiness:** Epic 2 may start with F-3/F-5 resolutions at its head; Epic 3
  with F-2/F-6 (and the F-4 declaration). Epic 4's new stories (4.7–4.9)
  depend on S-1.3/S-4.4/S-4.5 only — no new blockers introduced. Story 6.9 is
  post-MVP by declaration.
- The five 2026-07-31 operator rulings are fully propagated; no artifact
  contradicts another on them (verified by the section cross-reads in this
  pass).
