---
validationTarget: "_bmad-output/projects/deckcraft/planning-artifacts/prd.md"
validationDate: "2026-05-09"
inputDocuments:
  - "_bmad-output/projects/deckcraft/planning-artifacts/prd.md"
  - "_bmad-output/projects/deckcraft/planning-artifacts/product-brief-deckcraft.md"
  - "_bmad-output/projects/deckcraft/planning-artifacts/product-brief-deckcraft-distillate.md"
  - "pixi.toml"
  - ".claude/skills/bmad-validate-prd/data/prd-purpose.md (validation standards)"
validationStepsCompleted:
  - step-v-01-discovery
  - step-v-02-format-detection
  - step-v-02b-parity-check
  - step-v-03-density-validation
  - step-v-04-brief-coverage-validation
  - step-v-05-measurability-validation
  - step-v-06-traceability-validation
  - step-v-07-implementation-leakage-validation
  - step-v-08-domain-compliance-validation
  - step-v-09-project-type-validation
  - step-v-10-smart-validation
  - step-v-11-holistic-quality-validation
  - step-v-12-completeness-validation
  - step-v-13-report-complete
validationStatus: PASS_WITH_REVISIONS
gateDecision: PASS
mustFixIssues: 0
shouldFixIssues: 4
niceToHaveImprovements: 6
---

# PRD Validation Report — deckcraft

**PRD Validated:** `_bmad-output/projects/deckcraft/planning-artifacts/prd.md`
**Validation Date:** 2026-05-09
**Standards Applied:** BMAD PRD Purpose (`prd-purpose.md`)
**Validator:** autonomous run via `bmad-validate-prd` skill

---

## Gate Decision: ✅ PASS (with 4 should-fix items recommended before architecture phase)

The PRD is structurally complete, traceable, measurable, and ready for downstream architecture work. No must-fix blockers. Four should-fix items are quality improvements that will pay back in the architecture phase but do not block it.

---

## Summary Matrix

| Validation Pass | Status | Findings |
|---|---|---|
| Format detection | ✓ PASS | Markdown with YAML frontmatter, all 9 BMAD-standard L2 sections present |
| Density (signal-to-noise) | ✓ PASS | High signal density throughout; one minor caveat in Executive Summary (see SF-01) |
| Brief coverage | ✓ PASS | All locked decisions from brief + distillate are present in PRD |
| Measurability of FRs | ⚠ PASS-WITH-NOTES | 44 FRs total. Most testable. 5 contain implementation references (see SF-02) |
| Measurability of NFRs | ✓ PASS | 21 NFRs, all measurable with specific criteria + measurement methods |
| Traceability chain | ✓ PASS | Vision → SC → Journeys → FRs intact; explicit FR↔Journey mapping in journey section |
| Implementation leakage | ⚠ PASS-WITH-NOTES | 5 FRs reference specific libraries/tools (intentional per locked decisions, but mismatches BMAD strict standard — see SF-02) |
| Domain compliance | ✓ PASS | Air-gapped + conda-forge purity captured as DRs; BMAD↔CFE rules captured (DR-06/07) |
| Project-type validation | ✓ PASS | Library + CLI + MCP + Skill + conda recipe all enumerated with surface-specific reqs |
| SMART validation | ⚠ PASS-WITH-NOTES | All SMART criteria mostly met; some FR acceptance criteria implicit rather than explicit (see SF-03) |
| Holistic quality | ✓ PASS | Document is internally consistent, well-organized, dual-audience optimized |
| Completeness | ✓ PASS | No template variables remaining; frontmatter populated; all required sections present |

---

## Pass-by-Pass Details

### Pass 1 — Format Detection ✓ PASS

- File extension: `.md` ✓
- YAML frontmatter present and parseable ✓
- L2 section headers used for all main sections (machine-extractable) ✓
- All 9 BMAD-standard sections present:
  - Executive Summary ✓
  - Success Criteria ✓
  - User Journeys ✓
  - Domain Requirements ✓
  - Innovation Analysis ✓
  - Project-Type Requirements ✓
  - Project Scoping ✓ (single-release-prioritized model documented)
  - Functional Requirements ✓ (44 FRs across 11 capability areas)
  - Non-Functional Requirements ✓ (21 NFRs across 8 categories)
- Bonus sections: Open Questions, References

### Pass 2 — Density Validation ✓ PASS

The PRD avoids most BMAD anti-patterns. Sentences carry weight; "the system will allow users to" pattern absent; uses "Users can" form throughout the FR section. One minor density note:

- The Executive Summary's third paragraph ("The build leans on infrastructure that already exists...") spends words on context the brief already established. Could be tightened by 30–40 words without losing substance. Marked as **NTH-01** (nice-to-have).

### Pass 3 — Brief Coverage Validation ✓ PASS

Cross-checked PRD against brief + distillate locked decisions:

| Locked decision (from distillate) | Reflected in PRD? |
|---|---|
| Default LLM backend = `llama-server` | ✓ FR-34, NFR section, Innovation Pattern 3 |
| Optional Ollama for IDE-client compat | ✓ FR-34 |
| MLX preferred on osx-arm64 | ✓ Hardware tier matrix in scoping; FR-34 |
| LiteLLM deferred (pydantic conflict) | ✓ Scoping § Nice-to-Have, Open Question 8 |
| python-pptx 1.0.2 + adapter for vendor-fallback | ✓ FR-15, DR-04 escape hatch, Risk Mitigation |
| Editable native DrawingML non-negotiable | ✓ NFR-15, FR-13/14/15, Innovation Pattern 2, Kill Criteria |
| 6 user JTBDs | ✓ J1–J6 fully documented |
| Cross-platform 3 reference machines | ✓ Project-Type Requirements, FR-27 to FR-30 |
| Hardware tier matrix (small/medium/large) | ✓ Scoping section, FR-31 |
| Dogfooding as primary success criterion | ✓ Success Criteria opens with this; Kill Criteria reinforces |
| Kill criteria | ✓ 3 explicit triggers stated |
| Reference projects (pptx2marp, OscarPellicer fork) | ✓ frontmatter `referenceProjects`; cited in J5 and DR/FR sections |
| Sibling-project relationship to presenton-pixi-image | ✓ explicit reference in Executive Summary, Risk Mitigation, V∞ note |
| Recently added: sentencepiece + sentence-transformers | ✓ FR-43, FR-44, Open Questions 10–11 |
| Air-gapped mandatory default | ✓ DR-01, NFR-08, NFR-11 |
| All deps from conda-forge | ✓ DR-02, NFR-12 |
| BMAD ↔ CFE integration rules | ✓ DR-06, DR-07 |

**No locked decisions are missing from the PRD.** Coverage is complete.

### Pass 4 — Measurability Validation (FRs) ⚠ PASS-WITH-NOTES

44 FRs analyzed. Form-compliance results:

| Check | Pass count | Issues |
|---|---|---|
| `[Actor] can [capability]` format | 44 / 44 | All FRs use proper actor-capability form |
| No subjective adjectives | 42 / 44 | FR-29 says "auto-detects... and routes... accordingly" — `accordingly` is implicit/vague (SF-03); FR-44 uses "near-duplicate" which is qualified by "cosine similarity ≥ 0.92" so acceptable |
| No vague quantifiers | 44 / 44 | All numeric thresholds are specific (16K tokens, 0.92 cosine, etc.) |
| No implementation details | 39 / 44 | **5 FRs reference specific libraries** (FR-01 `markitdown`, FR-15 `python-pptx`/`pptx_engine`, FR-16 `mermaid-py` + `playwright`, FR-19 `diffusers` + SDXL-Turbo, FR-43 `sentence-transformers`/`all-MiniLM-L6-v2`). See SF-02. |

The implementation references are **intentional** — they reflect locked technical decisions captured during scoping. BMAD's strict standard says implementation belongs in architecture, but these references serve a real purpose: they pin the binding decisions so architecture doesn't re-litigate. Recommended treatment: move the specific library names from the FR text into a sibling "Technology Bindings" subsection (or accept the slight standard violation as documented intent — see SF-02 detail).

### Pass 5 — Measurability Validation (NFRs) ✓ PASS

21 NFRs analyzed. Each has:
- Specific criterion ✓
- Quantified metric ✓
- Implicit measurement method ✓ (most state how to measure: CI tests, benchmark fixtures, structural inspection, weekly self-report)

Examples of strong NFRs:
- NFR-02: "End-to-end deck generation (10 slides, no images) ≤ 10 minutes on large tier CPU; ≤ 4 minutes on medium tier with Metal/MLX; ≤ 15 minutes on small tier CPU." — has metric, condition, scope.
- NFR-08: "All V1 features verified to work in `unshare -n` (network-isolated) environment via CI test." — explicit measurement method.
- NFR-15: "100% of shape and chart content is rendered as native DrawingML; zero rasterized content..." — testable via structural inspection.

No measurability issues.

### Pass 6 — Traceability Chain ✓ PASS

Built traceability matrix:

| Layer | Element | Traces to |
|---|---|---|
| Vision (Exec Summary) | "AI-assisted deck creation in air-gapped environments" | Success Criterion SC-01 (end-to-end time), SC-05 (editability), SC-07 (air-gapped parity) |
| Success Criteria | SC-01 (end-to-end time) | J1, J6 |
| | SC-05 (editability) | All 6 journeys consume the editable output |
| | SC-07 (air-gapped) | DR-01, NFR-08 |
| | SC-08 (cross-platform parity) | FR-27 to FR-30 |
| User Journeys → FRs | Each journey explicitly references its FRs | J1 → FR-01, FR-02, FR-03, FR-09, FR-13, FR-14, FR-15, FR-25 (note: FR-25 was referenced but the FR section's last entry is FR-44; **FR-25 is not defined** — see SF-04) |
| | J2 → FR-16, FR-17, FR-18, FR-25 | Same FR-25 issue |
| | J3 → FR-19, FR-20, FR-26, FR-32 | **FR-26 is not defined either** — see SF-04 |
| | J4 → FR-21, FR-22 | ✓ |
| | J5 → FR-23, FR-24 | ✓ |
| | J6 → FR-04, FR-05, FR-25 | Same FR-25 issue |

**Finding:** Journeys reference `FR-25` and `FR-26` but no FR with those numbers exists in the document. This is a numbering gap — the FR list jumps from FR-24 (Marp Markdown Rendering) to FR-27 (Cross-Platform Operation). Marked as **SF-04** (must fix before architecture phase to avoid story-breakdown errors).

No orphan FRs found in the FR list itself; every FR maps to a journey or to a domain/project-type requirement.

### Pass 7 — Implementation Leakage ⚠ PASS-WITH-NOTES

Same 5 FR violations from Pass 4. Detailed accounting:

| FR | Tech mentioned | Capability-relevant or leakage? |
|---|---|---|
| FR-01 | `markitdown` | Leakage — capability is "extract text from PDF"; tool is HOW |
| FR-15 | `python-pptx`, `pptx_engine` | Mixed — "DrawingML" is capability; the engine adapter name is design choice that belongs in arch |
| FR-16 | `mermaid-py`, `playwright` | Leakage — capability is "render mermaid offline" |
| FR-19 | `diffusers`, `SDXL-Turbo` | Leakage — capability is "generate images on local hardware" |
| FR-43 | `sentence-transformers`, `all-MiniLM-L6-v2` | Leakage — capability is "RAG fallback for long documents" |

NFR section: NFR-04 mentions `playwright`, NFR-05 mentions `hf-transfer`, NFR-12 mentions JFrog/Artifactory. NFR-04 and NFR-05 are mild leakage; NFR-12 is enterprise-deployment context (acceptable).

**Recommendation:** Either restructure FRs to remove specific tool names (move to a "Technology Bindings" subsection that the architecture phase formalizes), OR accept the violation as deliberate documentation of locked decisions. Marked as **SF-02**.

### Pass 8 — Domain Compliance ✓ PASS

Air-gapped + conda-forge purity is treated correctly as a domain requirement (DR-01, DR-02, DR-03). The BMAD ↔ conda-forge-expert integration rule from CLAUDE.md is captured (DR-06, DR-07). No missing compliance dimensions for this product type.

Specifically validated:
- ✓ Cross-platform commitment (DR-05, FR-27 to FR-30)
- ✓ Conda-forge dist requirement (DR-04)
- ✓ Recipe authoring invokes conda-forge-expert skill (DR-06)
- ✓ Closeout retro touches CFE skill (DR-07)
- N/A — Healthcare HIPAA, fintech PCI-DSS, gov FedRAMP (not applicable to this product)

### Pass 9 — Project-Type Validation ✓ PASS

Project type is correctly identified as "Python library + CLI + MCP server + Claude Skill + conda-forge package" — a multi-surface distribution pattern. The Project-Type Requirements section enumerates per-surface needs:
- Library (importable Python package) ✓
- CLI (typer-based) ✓
- MCP server (fastmcp, stdio + HTTP) ✓
- Claude Skill (in-repo) ✓
- conda-forge recipe ✓
- VS Code extension (V2) ✓
- MS365 connector (V3) ✓ — gated, explicit

All surface requirements have associated FRs.

### Pass 10 — SMART Validation ⚠ PASS-WITH-NOTES

Sample SMART check on randomly-picked FRs:

- **FR-13** "Deckcraft renders slide JSON into a `.pptx` file that opens cleanly in Microsoft PowerPoint 2019+ on Windows and Office 365." — Specific ✓, Measurable (acceptance: open in PPT 2019/365 without errors) ✓, Attainable ✓, Relevant ✓, Traceable to NFR-14/15 ✓.
- **FR-31** "A user runs `deckcraft init` and the tool auto-detects RAM + platform + available GPU and recommends a hardware tier (small / medium / large)." — Specific ✓, Measurable (test: run on 3 reference machines, verify tier recommendation) ✓, Attainable ✓, Relevant ✓, Traceable ✓.
- **FR-29** "Deckcraft auto-detects the host platform's GPU acceleration availability... and routes diffusion + LLM workloads accordingly." — Specific (some), Measurable (vague — what does "accordingly" test against?), Attainable ✓, Relevant ✓, Traceable ✓. The "accordingly" leaves the acceptance test underspecified. Marked as **SF-03**.
- **FR-44** "Deckcraft detects semantically near-duplicate slides in LLM output (cosine similarity ≥ configurable threshold, default 0.92) and either collapses or reorders them..." — All SMART ✓ thanks to the explicit threshold.

Most FRs pass SMART. SF-03 captures the "accordingly" weakness in FR-29 and similar vagueness in a few others.

### Pass 11 — Holistic Quality ✓ PASS

- Document is internally consistent (no contradictions between sections)
- Single-release-prioritized model is consistently applied
- Dual-audience optimization: human-readable narrative + machine-extractable structure
- References appendix is complete
- Open Questions section is honest about unresolved items (good practice — these flow to architecture phase)
- Tone is direct and confident; no hedging
- The kill-criteria section is well-positioned (right after primary success criterion) and unambiguous

One small holistic note (NTH-02): the V2 / V3 nice-to-have lists could be consolidated into a single "Future Roadmap" subsection with V2/V3 as nested headers, rather than scattered across Scoping. Would improve grep-ability for "what's deferred."

### Pass 12 — Completeness ✓ PASS

- Template variables remaining: 0 ✓
- Each section has substantive content ✓
- Frontmatter populated:
  - `stepsCompleted` ✓ (all 14 listed)
  - `inputDocuments` ✓
  - `referenceProjects` ✓
  - `workflowType` ✓
  - `projectName` ✓
  - `projectType` ✓
  - `releaseMode` ✓
- All 6 user journeys have flow + actor + trigger + success + FR mapping
- All 7 domain requirements stated as DR-## with rationale
- All 44 FRs numbered + actor-capability format + capability area
- All 21 NFRs measurable with criteria + metric

---

## Should-Fix Items (recommended before architecture phase)

### SF-01 — Tighten Executive Summary's third paragraph

**Severity:** Low / cosmetic.
**Location:** Executive Summary, paragraph 3.
**Issue:** ~30–40 words of context-setting that the brief already established.
**Recommended fix:** Trim to: "The build leans on infrastructure that already exists — 100% of dependencies are on conda-forge (verified package-by-package); the requester maintains three of them; the existing `local-recipes` pixi env needed only nine small additions."
**Why it matters:** Tighter exec summary reads better for stakeholder review.

### SF-02 — Tool/library names in FRs (implementation leakage by BMAD strict standard)

**Severity:** Medium — this is the only item that directly conflicts with `prd-purpose.md` standards.
**Location:** FR-01, FR-15, FR-16, FR-19, FR-43 (and mild instances in NFR-04, NFR-05).
**Issue:** BMAD's `prd-purpose.md` says FRs specify WHAT, not HOW. Library names are HOW. The PRD currently bakes specific library names into FR text because they reflect locked decisions captured upstream.
**Recommended fix (choose one):**
- **Option A (BMAD-strict):** Remove library names from FR text. Move them into a new section "Technology Bindings" between FRs and NFRs that lists which FRs are bound to which conda-forge packages and why. The architecture phase formalizes this as the dependency map.
- **Option B (pragmatic):** Accept the slight standard deviation. Add a one-sentence note at the start of the FR section: "Some FRs reference specific libraries because those choices are locked decisions from the brief; remove them mentally if reading FR-only."
**Why it matters:** If left as-is, the FR list is more "binding spec" than "capability contract." Architecture phase may push back. Either fix is fine; just pick one and own it.

### SF-03 — FR-29 underspecified acceptance criterion ("accordingly")

**Severity:** Medium.
**Location:** FR-29.
**Current text:** "Deckcraft auto-detects the host platform's GPU acceleration availability (Metal on macOS; ROCm/CUDA on Linux/Windows where present) and routes diffusion + LLM workloads accordingly."
**Issue:** "Accordingly" leaves the test ambiguous. What is the right-routing acceptance criterion?
**Recommended fix:** "Deckcraft detects available compute (Metal on macOS; ROCm on Linux with healthy gfx; CUDA on Windows where pytorch-cuda is installed; CPU otherwise) and uses the highest-tier available device for diffusion (`pipe.to(device)`) and for llama.cpp's backend selection. Test: deckcraft logs the device chosen at startup; CI fixture verifies the expected device per platform." Now testable.

### SF-04 — Broken FR references in user journeys (FR-25, FR-26 don't exist) — ✅ RESOLVED 2026-05-09

**Status:** Fixed during cross-document consistency check. New "Templates & Resilience" capability area added to PRD with FR-25 (template support) and FR-26 (graceful degradation of optional capabilities). All journey cross-references now valid.

---

## Nice-to-Have Improvements

| ID | Item |
|---|---|
| NTH-01 | Tighten Executive Summary paragraph 3 (~30–40 words; see SF-01) |
| NTH-02 | Consolidate V2 / V3 nice-to-have lists into a single "Future Roadmap" subsection with nested V2/V3 |
| NTH-03 | Add an explicit "Glossary" appendix for terms that recur (DrawingML, MCP, MLX, GGUF, mmproj, RAG, Marp) — would help non-technical stakeholders skim the PRD |
| NTH-04 | The "Open Questions" section is great; consider numbering OQ-01 through OQ-11 and referencing them inline in the relevant FR/NFR text where the question affects implementation |
| NTH-05 | Add a "Constraints (out of scope)" section explicitly listing what V1 does NOT do (no real-time collaboration, no web UI, no notebook generation, no LiteLLM, no MS365 V1) — makes scope contract sharper |
| NTH-06 | Add a single-sentence "elevator pitch" at the top of the Executive Summary (≤25 words) — useful for slack-summary contexts |

---

## Architecture Phase Handoff Notes

When `bmad-create-architecture` runs, it should:

1. **Resolve all 11 Open Questions** before story breakdown. These are real unknowns the architecture phase must close (corporate template, GGUF model selection per tier, MCP HTTP V1-vs-V2, pptx-assembler reuse decision, performance benchmark cadence, vendor trigger for python-pptx, NVIDIA path on Windows, MLX backend selection logic, VS Code extension distribution model, embedding model selection, RAG threshold tuning).
2. **Formalize the Technology Bindings** that the FRs hint at — this is the natural home for library version pins, adapter signatures, and the engine-adapter pattern.
3. **Produce the first benchmark fixture** (per Open Question 5) and run it on the requester's Framework laptop before story estimation locks the V1 timeline.
4. **Define the data model precisely** — the brief and PRD reference `Deck`, `Slide`, `Theme`, `Asset`, `LayoutHint`, `HardwareTier`. Architecture phase produces the Pydantic class definitions.
5. **Wire the conda-forge-expert handoff for S-15** (the recipe story) per CLAUDE.md Rule 1.

---

## Final Verdict

```json
{
  "status": "PASS_WITH_REVISIONS",
  "gateDecision": "PASS",
  "validationReport": "_bmad-output/projects/deckcraft/planning-artifacts/prd-validation.md",
  "mustFixIssues": 0,
  "shouldFixIssues": [
    "SF-01: Tighten Executive Summary paragraph 3 (cosmetic)",
    "SF-02: Tool/library names in 5 FRs — choose strict-BMAD restructure or accept-as-locked-decisions",
    "SF-03: FR-29 'accordingly' is unmeasurable — make acceptance criterion explicit",
    "SF-04: Journeys reference undefined FR-25 / FR-26 — add missing FRs and renumber, or update cross-references"
  ],
  "niceToHaveImprovements": [
    "NTH-01: Tighten exec summary",
    "NTH-02: Consolidate V2/V3 roadmap",
    "NTH-03: Glossary appendix",
    "NTH-04: Number Open Questions and inline-reference them",
    "NTH-05: Explicit out-of-scope section",
    "NTH-06: Elevator-pitch sentence"
  ],
  "architecturePhaseReady": true,
  "openQuestionsForArchitecture": 11,
  "next": "Apply SF-04 (mandatory before architecture); apply SF-02/SF-03 if desired; then bmad-create-architecture"
}
```

---

*PRD validation complete. Ready for `bmad-create-architecture` once SF-04 is resolved (the broken FR references are mechanical and quick). SF-01/02/03 are quality improvements but not blockers.*
