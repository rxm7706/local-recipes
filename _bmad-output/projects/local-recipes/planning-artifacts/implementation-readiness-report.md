---
doc_type: implementation-readiness-report
project_name: local-recipes
date: 2026-05-12
artifacts_under_review:
  - planning-artifacts/PRD.md
  - planning-artifacts/architecture.md
  - planning-artifacts/epics.md
validator: bmad-check-implementation-readiness (Path 3 hybrid)
overall_verdict: READY — all 5 must-fix items resolved 2026-05-12
status: final
verdict_history:
  - initial: 'CONDITIONAL_READY (2026-05-12)'
  - after_must_fix: 'READY (2026-05-12 — MF1 confirmed, MF2-MF5 applied)'
---

# Implementation Readiness Assessment

This report validates that `PRD.md`, `architecture.md`, and `epics.md` form a **consistent, implementable triple**. The PRD says WHAT to build; the architecture says HOW; the epics break the HOW into actionable stories. Each must align with the others or sprint planning will plan against contradictions.

## VERDICT UPDATE (2026-05-12)

**Initial verdict: CONDITIONAL_READY** — 5 must-fix items identified.

**Updated verdict: READY** — all 5 must-fix items resolved on the same day:

- ✅ **MF1**: All 7 open questions (Q-PRD-01 through Q-PRD-07) confirmed by operator — see PRD §8 Decision summary
- ✅ **MF2**: JTBD↔Feature traceability matrix added to PRD as Appendix C
- ✅ **MF3**: Timeline section added to PRD as §11.5 (with aspirational, no-deadline framing)
- ✅ **MF4**: All 6 XL stories split into right-sized sub-stories (193 total stories, 0 XL remaining)
- ✅ **MF5**: `test-skill.py` covered by new E12.S10

**Sprint planning is unblocked across all 5 waves.** The original report body below is preserved as a historical record of the initial assessment.

---

## Original Report (2026-05-12 initial assessment)

**Overall verdict: CONDITIONAL_READY.** The triple is largely consistent and implementable. **5 must-fix items** need resolution before sprint planning starts. **7 should-fix items** improve quality but don't block. **3 informational findings** flag structural patterns worth noting.

---

## Methodology

This report applies the BMAD `bmad-check-implementation-readiness` 6-step framework:

1. **Document discovery** — all 3 artifacts present and frontmatter-aligned
2. **PRD analysis** — PRD section coverage and quality
3. **Epic coverage validation** — every PRD feature maps to ≥1 story
4. **UX alignment** — N/A for this rebuild (no UX design doc; infrastructure rebuild)
5. **Epic quality review** — story granularity, AC clarity, dependency soundness
6. **Final assessment** — readiness verdict + must-fix list

Where the BMAD skill would HALT for user input, this Path 3 hybrid produces direct findings.

---

## Step 1: Document Discovery ✅

| Artifact | Path | Frontmatter | Size |
|---|---|---|---|
| PRD | `planning-artifacts/PRD.md` | ✅ aligned (v1.0.0, draft, v7.7 pin) | 472 lines |
| Architecture | `planning-artifacts/architecture.md` | ✅ aligned (v1.0.0, draft, v7.7 pin) | 564 lines |
| Epics & Stories | `planning-artifacts/epics.md` | ✅ aligned (v1.0.0, draft, v7.7 pin; 13 epics, ~176 stories) | 557 lines |
| Project context | `_bmad-output/projects/local-recipes/project-context.md` | ✅ aligned (v7.7 pinned, 63 rules) | 176 lines |

**Cross-references**:
- PRD references architecture (§11 Dependencies, §1 Vision, glossary)
- Architecture references PRD (§11 References) and consolidates 4 architecture-*.md files
- Epics references PRD (§ each epic's "Source: PRD F#") and architecture (§ build order)

All three artifacts cite each other appropriately. ✅

---

## Step 2: PRD Analysis ⚠️

The companion `validation-report-PRD.md` covers PRD-internal quality. **Implementation-readiness adds these checks**:

### Findings

| Finding | Severity |
|---|---|
| PRD §5 has **52 features** with priority + AC. Epics need to cover all 52. | (verified in Step 3) |
| PRD §6 Success Metrics has **27 measures**. Each should map to a verification story in Epic 12 or Epic 13. | (gap — see below) |
| PRD §8 Open Questions has **7 items**. Of these, Q-PRD-01, Q-PRD-03, Q-PRD-04, Q-PRD-05, Q-PRD-07 may **block specific stories**. | (gap — see below) |
| PRD §10 has **7 risks** with mitigations. Mitigations should map to specific stories or be documented in architecture. | (verified — most map; one gap) |

### Gap 1: Success metrics → verification stories

PRD §6 has 27 measures. `epics.md` Epic 12 has 9 test stories and Epic 13 has 13 docs/validation stories — but **the mapping is not explicit**. For example:

- PRD G2: "First-pass conda-forge PR acceptance ≥90%" — no specific story measures this post-rebuild
- PRD G3: "Atlas refresh resilient to interrupts" — partly covered by E7.S14 (checkpoint resume test); but cross-phase resilience isn't a single story
- PRD G4 air-gap metrics — covered by E13.S8 (air-gap deployment dry-run), but the specific measures (zero JFrog headers in non-JFrog logs) aren't explicit AC

**Required**: Epic 13 should add a "Measure PRD success metrics" story (or augment E13.S10 with explicit per-metric AC).

### Gap 2: Open questions blocking stories

PRD §8 Q-PRD-01 ("Should the rebuild include `.mcp.json` registration?") — recommendation says "include in v1 rebuild." If accepted, story E10.S9 stands as written. If deferred, E10.S9 should be moved to deferred work.

Similar:
- Q-PRD-03 (G6 promotion) — if accepted, augments E6.S1's SKILL.md authoring scope; if deferred, no story
- Q-PRD-04 (Phase K rate-limit backoff) — if accepted, adds a story to Epic 8; if deferred, captured in DW3
- Q-PRD-05 (sibling project stubs) — affects E2.S7
- Q-PRD-07 (macOS SDK inclusion) — affects deployment-guide.md content (E13.S2)

**Required**: PRD owner (rxm7706) resolves Q-PRD-01, 03, 04, 05, 07 (and 02 already deferred per ADR-010). Each resolution either confirms an existing story OR adds/removes a story.

### Gap 3: Risk mitigation traceability

PRD §10 R6: "conda-forge changes Python floor before rebuild ships" — mitigation says "Floor is documented in SKILL.md + project-context.md + python-min-policy.md; update in same retro." This is documentation, not a story. ✅ acceptable.

PRD §10 R7: "New conda-forge lint code added post-rebuild" — mitigation says "Run `optimize_recipe.py` against the upstream conda-forge linter periodically; add the code to the 17." This implies a periodic verification story that doesn't exist in epics. **Gap.**

**Recommended**: add a Wave 5 story (Epic 12 or 13) that periodically diffs `recipe_optimizer.py` lint codes against upstream conda-forge linter (`conda-smithy recipe-lint`) and reconciles new codes.

---

## Step 3: Epic Coverage Validation ❌ MUST FIX

**The big question**: do the 13 epics cover all 52 PRD features?

### Coverage matrix (52 features → 13 epics)

| PRD Feature | Priority | Covered by epic(s) | Verdict |
|---|---|---|---|
| **Part 1 (15 features)** | | | |
| F1.1 (3-tier architecture) | P0 | E5 (wrapper layer) + E4 (Tier 1 scripts) + E1.S9 (scaffolding) | ✅ |
| F1.2 (10-step autonomous loop in SKILL.md) | P0 | E6.S1 (SKILL.md) | ✅ |
| F1.3 (5 Critical Constraints) | P0 | E6.S1 | ✅ |
| F1.4 (42 Tier 1 scripts) | P0 | E4 (20 stories cover ~20 scripts) | ⚠️ **GAP** — Epic 4 covers 20 of 42 scripts; the other 22 are atlas scripts (Epics 7/8/9) — verify cross-coverage |
| F1.5 (34 Tier 2 wrappers + pixi tasks) | P0 | E5 (8 stories cover all 34) | ✅ |
| F1.6 (17-lint-code optimizer) | P0 | E4.S7 | ✅ |
| F1.7 (G1-G6 gotchas) | P0 | E6.S1 — but G6 promotion is Q-PRD-03 dependent | ⚠️ blocked by Q-PRD-03 |
| F1.8 (41 templates / 13 ecosystems) | P0 | E6.S19 | ✅ |
| F1.9 (11 reference + 8 guides + 2 quickrefs) | P0 | E6.S5-S18 (14 doc stories) | ✅ |
| F1.10 (MANIFEST.yaml + install.py) | P1 | E6.S4 | ✅ |
| F1.11 (Build failure protocol) | P0 | E6.S1 (in SKILL.md) | ✅ |
| F1.12 (Migration protocol) | P0 | E6.S1 + E4.S15 (feedstock-migrator) | ✅ |
| F1.13 (Mapping subsystem) | P0 | E4.S1 (name_resolver) + E4.S2 (mapping_manager) | ✅ |
| F1.14 (41 tests) | P0 | E6.S23-S26 (4 test-setup stories) + E12 (test completeness) | ✅ |
| F1.15 (CHANGELOG with TL;DR) | P0 | E6.S3 | ✅ |
| **Part 2 (12 features)** | | | |
| F2.1 (SQLite schema v19) | P0 | E7.S1-S2 | ✅ |
| F2.2 (17 phases via PHASES registry) | P0 | E7.S4-S11 (Phase B-E.5) + E8 (Phase F-N) + E9.S1 (atlas_phase.py with PHASES dispatch) | ✅ |
| F2.3 (`bootstrap-data` orchestrator) | P0 | E9.S2 | ✅ |
| F2.4 (`atlas-phase <ID>` CLI) | P0 | E9.S1 | ✅ |
| F2.5 (TTL gates on F/G/H/K) | P0 | E8.S4, S16 + E12.S5 (meta-test) | ✅ |
| F2.6 (`phase_state` checkpointing on B/D/N) | P0 | E7.S3 + E7.S14 (test) | ✅ |
| F2.7 (Phase F S3 backend) | P0 | E8.S2, S3 | ✅ |
| F2.8 (Phase H cf-graph backend) | P0 | E8.S8, S9 | ✅ |
| F2.9 (60s heartbeat + capped cadence) | P0 | E8.S15 | ✅ |
| F2.10 (17 public CLIs) | P0 | E9 (20 stories) | ✅ |
| F2.11 (Phase G/G' require vuln-db) | P0 | E8.S5-S6 | ✅ |
| F2.12 (Idempotent additive schema migrations) | P0 | E7.S2 + E12.S3 (migration test) | ✅ |
| **Part 3 (8 features)** | | | |
| F3.1 (`conda_forge_server.py` + FastMCP) | P0 | E10.S1 | ✅ |
| F3.2 (35 `@mcp.tool()` registrations) | P0 | E10.S3-S5 | ✅ |
| F3.3 (Thin subprocess wrapper pattern) | P0 | E10.S1 + S3 + S4 | ✅ |
| F3.4 (`_run_script` 3-tier error handling) | P0 | E10.S2 | ✅ |
| F3.5 (2 async tools) | P0 | E10.S3 (trigger_build) + E10.S4 (update_cve_database) | ✅ |
| F3.6 (Out-of-band state files) | P0 | E10.S6 | ✅ |
| F3.7 (`mcp_call.py` JSON-RPC client) | P1 | E10.S7 | ✅ |
| F3.8 (`gemini_server.py` auxiliary) | P2 | E10.S8 | ✅ |
| **Part 4 (10 features)** | | | |
| F4.1 (BMAD installer) | P0 | E2.S1 | ✅ |
| F4.2 (6-layer config merge) | P0 | E2.S2 + E2.S11 (round-trip test) | ✅ |
| F4.3 (Active-project resolution) | P0 | E2.S2 + E2.S11 | ✅ |
| F4.4 (`scripts/bmad-switch`) | P0 | E2.S5 | ✅ |
| F4.5 (65 installed skills) | P0 | E2.S1 + E2.S9 | ✅ |
| F4.6 (`conda-forge-expert` skill) | P0 | Wave 2 (Epics 4-6) | ✅ |
| F4.7 (Per-skill customization) | P1 | E2.S3 | ✅ |
| F4.8 (Multi-project layout) | P0 | E2.S6, S7, S8 | ✅ |
| F4.9 (CLAUDE.md BMAD↔CFE integration rules) | P0 | E11.S1 | ✅ |
| F4.10 (project-context.md + drift contract) | P0 | E11.S2 | ✅ |
| **Cross-cutting (7 features)** | | | |
| FX.1 (`_http.py` auth chain) | P0 | E3.S1-S3 | ✅ |
| FX.2 (8 pixi envs) | P0 | E1.S2-S7 | ✅ |
| FX.3 (JFROG_API_KEY leak docs) | P0 | E3.S4-S6 | ✅ |
| FX.4 (vuln-db env separation) | P0 | E1.S6 | ✅ |
| FX.5 (`docs/pixi-config-jfrog.example.toml`) | P1 | E13.S6 | ✅ |
| FX.6 (`.claude/settings.json`) | P0 | E3.S7 | ✅ |
| FX.7 (`build-locally.py` Docker wrapper) | P0 | E4.S9 | ✅ |

### Coverage summary

- **51 of 52 features ✅ covered** with explicit story(ies)
- **1 feature ⚠️ with verification gap** (F1.4 — verify 42 scripts split across Epic 4 + Epic 7-9)
- **2 features ⚠️ blocked by open questions** (F1.7 G6 promotion blocked by Q-PRD-03; F3.7 P1 priority depends on Q-PRD-01)

### Verification of F1.4 (42 Tier 1 scripts)

`source-tree-analysis.md` lists the 42 scripts grouped by function. Cross-referencing:

- **Recipe lifecycle (18 scripts)**: covered by Epic 4 (20 stories — extra coverage for some) ✅
- **cf_atlas orchestration (7 scripts)**: covered by Epic 7 (`conda_forge_atlas.py`, `_cf_graph_versions.py`, `_parquet_cache.py`, `atlas_phase.py`, `bootstrap_data.py`, `detail_cf_atlas.py`, `inventory_channel.py` — all referenced) ✅
- **Atlas query CLIs (11 scripts)**: covered by Epic 9 ✅
- **Project-scanning + health (3 scripts)**: covered by E9.S14, S15, _sbom helper inside scan_project ✅
- **Shared infrastructure (3 scripts: `_http.py`, `mapping_manager.py`, `test-skill.py`)**: E3.S1-S3 (_http.py), E4.S2 (mapping_manager), E12 (test-skill.py as test harness) — **`test-skill.py` not explicitly covered** ⚠️

**Gap**: `test-skill.py` (skill-internal smoke test runner) is not covered by any story. Either add a story to Epic 12 or note it as out of scope.

---

## Step 4: UX Alignment ✅ N/A

The BMAD `bmad-check-implementation-readiness` skill expects a UX design doc to align against. **This rebuild has no UX design doc** because it's an infrastructure rebuild — there's no user-facing UI.

### N/A justification

- No web app, no mobile app, no native GUI
- User surfaces are: CLI (pixi tasks), MCP tools (Claude Code), markdown documentation, skill activation
- No visual design, no information architecture beyond markdown structure, no accessibility requirements beyond "readable in a terminal/Claude Code"

**Verdict: SKIP this step**. Document explicitly in §0 of this report (already done above).

---

## Step 5: Epic Quality Review ⚠️

Each epic should have:
- Clear goal
- Defined owner (which part)
- Acceptance criteria
- Stories with: title, scope, AC, complexity, dependencies

### Findings

#### Strengths

- ✅ Each epic has a Goal + Owner part + Acceptance
- ✅ All 176 stories have ID + title + scope + AC + complexity
- ✅ Stories are organized into 5 dependency-ordered waves
- ✅ Build order traces back to `project-parts.json` and `architecture.md` §9
- ✅ Risk concentration is called out (7 highest-risk stories flagged for extra review)

#### Issues

##### Story granularity skew

| Complexity | Count | % of total |
|---|---|---|
| S (small) | ~36 | 20% |
| M (medium) | ~78 | 44% |
| L (large) | ~50 | 28% |
| XL (extra large) | ~12 | 7% |
| **Total** | **~176** | **100%** |

**Issue**: 12 XL stories. Per BMAD planning conventions, XL stories should be split — they're hard to estimate and produce risk concentration.

XL stories identified:
1. E4.S7 (recipe_optimizer.py — 17 lint codes) — could split into 17 lint-code stories or 3-5 by family
2. E6.S1 (SKILL.md) — could split by section (Operating Principles + Constraints + Loop + ... = 4-6 sub-stories)
3. E6.S25 (unit tests for each Tier 1 module) — should split into per-module test stories
4. E7.S2 (schema v1-v19 migrations) — could split into per-version migration stories
5. E9.S14 (scan_project.py with ~28 input formats) — could split by format family (manifest / lock file / SBOM / container / OCI)
6. E13.S8 (air-gap deployment dry-run) — could split into setup + atlas + recipe-authoring + validation phases

**Recommended**: split 3-6 of the XL stories before sprint planning. Some may legitimately remain XL (E4.S7 lint codes might fit one sprint).

##### Inter-story dependencies not fully documented

Some stories list deps ("Epic X must complete first") but **within an epic**, story-level deps are often implicit. Example: in Epic 4 (recipe lifecycle), E4.S1 (name_resolver) precedes E4.S5 (dependency-checker) because the latter imports the former — but the dep isn't stated.

**Recommended**: add a "Depends on" column to each epic's story table.

##### Acceptance criteria are uneven

Some stories have testable AC ("`atlas-phase F` populates `total_downloads` column"). Others are softer ("Cheatsheet complete"). Soft AC make sprint completion ambiguous.

Spot-checked weak AC:
- E5.S8 "Each task listed in quickref" — what's the verification? Manual count?
- E6.S17 "Cheatsheet complete" — by whose judgment?
- E13.S9 "Documentation reviewed by operator" — N/A unless operator signs off
- E13.S12 "All PRD open questions resolved" — needs each Q-PRD-N status

**Recommended**: tighten weak AC to objective + verifiable criteria.

---

## Step 6: Final Assessment

### Verdict: CONDITIONAL_READY

The triple (PRD + architecture + epics) is **largely consistent and implementable**, but **5 must-fix items** need resolution before sprint planning starts. Sprint planning against the current triple risks committing to ambiguous scope (open questions), under-specified AC, or unsplit XL stories.

### Must-fix before sprint planning (5 items)

| ID | Action | Source | Effort |
|---|---|---|---|
| MF1 | **Resolve PRD §8 open questions** (Q-PRD-01, 03, 04, 05, 07) — each resolution either confirms a story stands or alters it | Step 2 gap 2 | M (~1-2 hr per operator's decision pace) |
| MF2 | **Add JTBD↔Feature traceability matrix** to PRD (Appendix C) | validation-report-PRD.md D6 | M (~30 min) |
| MF3 | **Add §12.5 Timeline to PRD** with milestone targets or explicit open-ended note | validation-report-PRD.md D10 | S (~10 min) |
| MF4 | **Split XL stories** (E4.S7, E6.S1, E6.S25, E7.S2, E9.S14, E13.S8) into sized stories | Step 5 | M (~45 min — author 3-5 new story rows per XL) |
| MF5 | **Cover `test-skill.py` script** with a story OR document as out-of-scope | Step 3 F1.4 gap | S (~5 min) |

### Should-fix before sprint planning (7 items)

| ID | Action | Source | Effort |
|---|---|---|---|
| SF1 | **Add success-metric → verification-story map** to Epic 13 (or augment E13.S10) | Step 2 gap 1 | M (~30 min) |
| SF2 | **Add risk R7 mitigation story** (periodic lint-code reconciliation with upstream conda-smithy) | Step 2 gap 3 | S (~10 min) |
| SF3 | **Add story-level dependency column** to each epic's story table | Step 5 | L (~1 hr — go through all 176 stories) |
| SF4 | **Tighten weak AC** in 5-8 stories (E5.S8, E6.S17, E13.S9, E13.S12, …) | Step 5 | S (~20 min) |
| SF5 | **Address PRD validation MINOR items** (density, measurability for 3 metrics, project-type note) | validation-report-PRD.md | S-M (~30 min) |
| SF6 | **Frame implementation leakage** with PRD §5 introductory note | validation-report-PRD.md D7 | S (~10 min) |
| SF7 | **Promote G6 gotcha to SKILL.md** per Q-PRD-03 (assumes accept) | open questions | S (~10 min during E6.S1 authoring) |

### Informational (no action required)

| Note | Finding |
|---|---|
| I1 | UX alignment step is N/A — infrastructure rebuild has no UX design doc. Acknowledged. |
| I2 | The 176-story count exceeds initial 142 estimate. Reasonable expansion during detailed authoring. |
| I3 | Story complexity skew (44% M) is healthy; the 7% XL is the only concern (see MF4). |

### Total effort to reach `READY_FOR_SPRINT_PLANNING`

- **Must-fix**: ~3-4 hours focused work (most is operator resolving open questions)
- **Should-fix**: ~2-3 hours focused work
- **Combined**: ~5-7 hours

After these revisions, re-run this report (Step 6 only); expect verdict to flip to `READY`.

---

## What Sprint Planning Can Begin Now

Some work doesn't need the must-fix items resolved. **Wave 1 (Foundation) Epics 1-3 can begin immediately:**

- Epic 1 (Pixi Monorepo Bootstrap) — 10 stories, no open-question dependencies
- Epic 2 (BMAD Installer + Multi-Project) — 11 stories; only E2.S7 is mildly affected by Q-PRD-05 (sibling project stubs)
- Epic 3 (Cross-Cutting Auth Chain + Permission Gates) — 8 stories, no open-question dependencies

**Wave 1 = 29 stories, 0-1 dependencies on open questions.** Start here while the operator resolves Q-PRD-01 through Q-PRD-07 in parallel.

Waves 2-5 should wait until must-fix items are resolved.

---

## Risk Assessment

### High-risk concentration confirmed

`epics.md` § Risk Concentration flags 7 stories for extra review:
1. E4.S7 (recipe_optimizer 17 codes) — also flagged as XL split candidate
2. E7.S2 (schema migrations) — also flagged as XL split candidate
3. E8.S2 (Phase F S3 path) — appropriate flag
4. E8.S8 (Phase H cf-graph) — appropriate flag
5. E10.S3+S4 (35 MCP tools) — could be more granular per-tool reviews
6. E11.S1+S2 (CLAUDE.md + project-context.md) — appropriate flag
7. E13.S8 (air-gap validation) — also flagged as XL split candidate

This is solid risk identification. Each should get `bmad-code-review` + `bmad-review-adversarial-general` before close.

### Additional risks surfaced by this report

- **R8 (new)**: open questions Q-PRD-01-07 are blocked on operator availability; sprint planning can't commit to certain stories until resolved. **Mitigation**: Wave 1 has no open-question dependencies; start there.
- **R9 (new)**: XL story under-estimation. 12 XL stories may consume more sprint budget than estimated. **Mitigation**: split before sprint planning (MF4).
- **R10 (new)**: weak AC in 5-8 stories may produce ambiguous sprint completion. **Mitigation**: tighten AC (SF4) before sprint planning.

---

## Recommended Sprint Planning Sequence

When MF1-MF5 are resolved:

```
Sprint 1: Epic 1 (Pixi monorepo bootstrap, 10 stories)
Sprint 2: Epic 2 (BMAD installer, 11 stories)
Sprint 3: Epic 3 (Cross-cutting auth chain, 8 stories)
                    ─── End of Wave 1 ───

Sprint 4-5: Epic 4 (Tier 1 recipe lifecycle scripts, 20 stories)
Sprint 6: Epic 5 (Tier 2 wrappers + meta-test, 8 stories)
Sprint 7-8: Epic 6 (Part 1 docs + templates + tests, 26 stories)
                    ─── End of Wave 2 ───

Sprint 9-10: Epic 7 (cf_atlas schema + Phase B-E, 14 stories)
Sprint 11-12: Epic 8 (Phase F-N + backends + TTL, 16 stories)
Sprint 13-14: Epic 9 (cf_atlas CLIs + bootstrap-data, 20 stories)
                    ─── End of Wave 3 ───

Sprint 15: Epic 10 (MCP server + 35 tools, 11 stories)
Sprint 16: Epic 11 (BMAD↔CFE integration, 10 stories)
                    ─── End of Wave 4 ───

Sprint 17: Epic 12 (test suite completeness, 9 stories)
Sprint 18-19: Epic 13 (docs + deployment validation, 13 stories)
                    ─── End of Wave 5 ───
                    ─── REBUILD COMPLETE ───
```

**~19 sprints** (vs. epic-level estimate of 16-20). Aligns with the epics.md estimate.

---

## References

- [PRD.md](./PRD.md) — product requirements (validated separately in `validation-report-PRD.md`)
- [architecture.md](./architecture.md) — unified architecture
- [epics.md](./epics.md) — 13 epics, 176 stories, 5 waves
- [validation-report-PRD.md](./validation-report-PRD.md) — PRD-internal validation
- [project-parts.json](./project-parts.json) — machine-readable part inventory
- [index.md](./index.md) — navigator
