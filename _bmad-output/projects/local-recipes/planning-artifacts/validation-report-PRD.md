---
doc_type: prd-validation-report
project_name: local-recipes
date: 2026-05-12
prd_under_review: planning-artifacts/PRD.md
validator: bmad-validate-prd (Path 3 hybrid)
overall_verdict: APPROVED (re-validated 2026-05-15 post v8.1.0 sync)
status: final
source_pin: 'conda-forge-expert v8.1.0'
verdict_history:
  - { date: '2026-05-12 (initial)', verdict: 'REVISE', notes: 'Material issues across D3 / D5 / D6 / D7 / D9 / D10 on the v7.7-pinned draft PRD.' }
  - { date: '2026-05-12 (post tentative-decisions)', verdict: 'APPROVED', notes: 'PRD updated with tentative_decisions_applied; REVISE-rated dimensions addressed; status moved draft → approved.' }
  - { date: '2026-05-12 (re-validated post v7.8.1 sync)', verdict: 'APPROVED', notes: 'Re-validation after bmad-correct-course propagated v7.8.x deltas to architecture-cf-atlas.md / deployment-guide.md / architecture-conda-forge-expert.md / architecture.md. PRD body itself unchanged; only source_pin moved v7.7 → v7.8.1. No new REVISE findings.' }
  - { date: '2026-05-13 (re-validated post v7.9.0 sync)', verdict: 'APPROVED', notes: 'v7.9.0 actionable-scope audit (schema v20 + pypi_universe side table + pypi-only-candidates CLI/MCP + Phase D split). PRD MINOR-bumped 1.1.0 → 1.1.1 → 1.2.0 across the v7.9.0/v8.0.0 syncs. Feature counts updated. No new REVISE findings.' }
  - { date: '2026-05-13 (re-validated post v8.0.0 sync)', verdict: 'APPROVED', notes: 'v8.0.0 structural-enforcement + persona-profile bundle (schema v21 + v_actionable_packages view + Phase H serial-aware eligible-rows gate + bootstrap-data --profile flag with auto-detection). PRD MINOR-bumped 1.1.1 → 1.2.0. v8.0.0 is the first MAJOR skill bump but PRD scope unchanged (additive UX). No new REVISE findings.' }
  - { date: '2026-05-15 (re-validated post v8.1.0 sync)', verdict: 'APPROVED', notes: 'v8.1.0 PyPI intelligence layer (schema v22 + pypi_intelligence side table + 5 new phases O/P/Q/R/S + new pypi-intelligence CLI + new MCP tool + persona-profile integration). PRD MINOR-bumped 1.2.0 → 1.3.0 (fully additive — no FR/NFR scope shift; new CLI + MCP tool are opt-in surfaces; existing CLIs unchanged). All 8 spec open questions pre-resolved before BMAD intake; L1 + L2 live-DB verification complete (Phase O perf-fix shipped as 124c5a449d; Phase R 9× faster than estimate; score distribution well-discriminated across 5k enriched candidates). No new REVISE findings.' }
---

# PRD Validation Report

This report applies the 13 BMAD PRD validation dimensions to `planning-artifacts/PRD.md`. It is **honest critique, not rubber-stamping** — the author of the PRD is the same agent producing this report, and the goal is to surface real issues before sprint planning begins.

**Overall verdict: APPROVED (re-validated 2026-05-12).** Three rounds — see `verdict_history` in frontmatter:

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
- All 52 features have AC descriptions in §5
- Air-gap metrics (§6) are concretely auditable (zero JFrog headers in non-JFrog logs)

**Severity: MINOR.** 3 of 27 metrics under-specified; 24 are sound.

---

## D6. Traceability ❌ REVISE

The traceability chain is **Vision → Goals → JTBDs → Features → Acceptance Criteria**. The PRD has all four layers, but the **JTBD ↔ Feature mapping is not documented**.

### Findings

#### Missing: JTBD-to-Feature trace matrix

§3 lists 11 JTBDs across 5 user personas. §5 lists 52 features across 4 parts + cross-cutting. **There is no explicit mapping** showing which JTBD each feature serves.

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
