---
stepsCompleted:
  - step-01-validate-prerequisites
inputDocuments:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/prds/prd-herald-moments-2-4-2026-08-02/prd.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/architecture/architecture-herald-moments-2-4-2026-08-02/ARCHITECTURE-SPINE.md
---

# Herald Moments 2–4 - Epics & Stories

## ✅ REQUIREMENTS EXTRACTED & VERIFIED

**Functional Requirements**: 24 FRs extracted  
**Non-Functional Requirements**: 6 NFRs extracted  
**Architecture Requirements**: 10 ADs (decisions) mapped to implementation  
**Total Coverage**: 100% of PRD + Architecture + Spec captured

---

## EPIC BREAKDOWN

### Epic 1: Foundation — CLI Architecture (2–3 stories)
- Story 1.1: CLI Dispatcher (subcommands, routing)
- Story 1.2: Shared Argument Conventions (--json, --date-range, --station)
- Story 1.3: CLI Authentication & Authorization (role gates)

**Blocks**: All downstream stories (foundation required)

---

### Epic 2: Foundation — Web Surface (2–3 stories)
- Story 2.1: Web Layout Design (nav, sidebar, responsive)
- Story 2.2: Header, Tabs, Sidebar Implementation (4 Moments)
- Story 2.3: Responsive Design & Mobile Support

**Blocks**: Stories 3.4, 4.4, 5.5 (web foundation needed)  
**Depends On**: Epic 1

---

### Epic 3: Moment 2 — Progress Visibility (2–3 stories)
- Story 3.1: Progress Data Model & DB Schema
- Story 3.2: On-Ship Webhook + Weekly Cron Automation
- Story 3.3: Progress CLI (herald progress subcommand)
- Story 3.4: Progress Web Tab (cards, filters, detail)

**Depends On**: Epics 1, 2

---

### Epic 4: Moment 3 — Success Proclamation (2–3 stories)
- Story 4.1: Claim Data Model & DB Schema
- Story 4.2: Auto-Extract + Operator Review Gate
- Story 4.3: Success CLI (review, publish, list, get)
- Story 4.4: Success Web Archive (chronological, evidence badges)
- Story 4.5: Evidence Validation (sync + async stale-link checks)

**Depends On**: Epics 1, 2

---

### Epic 5: Moment 4 — Operations Notices (2–3 stories)
- Story 5.1: Notice Data Model & Archive Storage
- Story 5.2: Notice Authoring Workflow (CLI + form)
- Story 5.3: Notice Archive (YYYY-MM folders, redirects)
- Story 5.4: Notice CLI (author, list, archive, get)
- Story 5.5: Operations Web Tab (notice board, filters)
- Story 5.6: Notice Lifecycle (Draft → Published → Closed)

**Depends On**: Epics 1, 2

---

### Epic 6: Integration Testing & Automation (1–2 stories)
- Story 6.1: Integration Testing (CLI + web + automation together)
- Story 6.2: Automation Reliability (webhook retries, cron, gates)
- Story 6.3: Evidence Linking (cross-Moment: claim ↔ notice)
- Story 6.4: Performance Testing (latency, scalability)

**Depends On**: Epics 3, 4, 5

---

### Epic 7: Documentation & Operator Experience (0.5–1 story)
- Story 7.1: Comprehensive CLI Help
- Story 7.2: Web Surface UX Guide (inline help, tooltips)
- Story 7.3: Operator Runbook (how-to guides)
- Story 7.4: Automation Troubleshooting Guide

**Depends On**: All other epics

---

## READY FOR NEXT STEP

✅ All requirements extracted and organized into 7 epics  
✅ 24+ individual stories identified  
✅ Dependencies mapped (critical path: 1 → 2 → {3,4,5} → 6 → 7)  
✅ Effort estimates provided (12–18 stories total)

**Current Status**: Step 1 complete. Ready to proceed to Step 2 (Design Epics with detailed acceptance criteria).

**[C] Continue to Story Design** — Press C to move to Step 2 and develop detailed ACs for each story.


---

## APPROVED EPIC STRUCTURE (Step 2 Complete)

### Epic 1: Foundation — CLI Architecture
**Outcome**: Unified CLI interface for all three Moments (consistent flags, extensible routing).  
**FRs**: FR-1.1–1.3 | **Dependencies**: None

### Epic 2: Foundation — Web Surface  
**Outcome**: Unified web dashboard (4-tab nav, responsive layout, shared UX patterns).  
**FRs**: FR-2.1–2.3 | **Dependencies**: Epic 1

### Epic 3: Moment 2 — Progress Visibility
**Outcome**: Shipping motion visible (progress + costs + unblocks via webhook + cron automation).  
**FRs**: FR-3.1–3.4 | **Dependencies**: Epics 1, 2

### Epic 4: Moment 3 — Success Proclamation
**Outcome**: Auto-extracted claims backed by evidence (tests, metrics, adoption).  
**FRs**: FR-4.1–4.5 | **Dependencies**: Epics 1, 2

### Epic 5: Moment 4 — Operations Notices
**Outcome**: Deprecations/EOL announced with permanent URLs and redirects.  
**FRs**: FR-5.1–5.6 | **Dependencies**: Epics 1, 2

### Epic 6: Integration Testing & Automation
**Outcome**: All Moments work together; automation reliable; evidence links validated.  
**FRs**: FR-6.1–7.4 | **Dependencies**: Epics 3, 4, 5

### Epic 7: Documentation & Operator Experience
**Outcome**: CLI help, web guides, runbooks, troubleshooting documented.  
**FRs**: Implicit (NFRs) | **Dependencies**: All other epics

---

**Total Effort**: 12–18 stories | **Parallel Path**: Epics 1 → 2 → {3,4,5 parallel} → 6 → 7

**Status**: ✅ READY FOR STEP 3 (Story Creation with detailed acceptance criteria)


---

## REFINED STRUCTURE (Advanced Elicitation + Party Mode)

**Key Changes**:
1. Epic 1 expanded: Evidence Protocol added (Story 1.4 + CLI help inline)
2. Epic 3 prioritized first (week 3 delivery of real value)
3. Epic 6 simplified (cross-Moment focused, not foundational re-testing)
4. Sequencing: value-driven (1 → 2 → 3-fast → {4,5 parallel} → 6 → 7)

### FINAL EPIC BREAKDOWN

**Epic 1: Foundation — CLI + Shared Infrastructure** (3–4 stories)
- 1.1: CLI Dispatcher
- 1.2: Shared Argument Conventions
- 1.3: Authorization Layer
- **1.4: Evidence Protocol (NEW)** — Shared link validation framework for Moments 3–5
- CLI help inline (first-day usability)

**Epic 2: Foundation — Web Surface** (2–3 stories)
- 2.1: Web Layout Design
- 2.2: Header, Tabs, Sidebar
- 2.3: Responsive Design & Mobile
- Web tooltips/inline help

**Epic 3: Moment 2 — Progress Visibility** (2–3 stories) **[PRIORITY 1]**
- 3.1: Progress Data Model
- 3.2: Webhook + Cron Automation
- 3.3: Progress CLI
- 3.4: Progress Web Tab
- **Week 3 delivery: First real user value**

**Epic 4: Moment 3 — Success Proclamation** (2–3 stories) **[Parallel with 3 & 5]**
- 4.1: Claim Data Model
- 4.2: Auto-Extract + Review Gate
- 4.3: Success CLI
- 4.4: Success Web Archive
- 4.5: Evidence Validation (uses Epic 1.4 protocol)

**Epic 5: Moment 4 — Operations Notices** (2–3 stories) **[Parallel with 3 & 4]**
- 5.1: Notice Data Model
- 5.2: Notice Authoring
- 5.3: Notice Archive
- 5.4: Notice CLI
- 5.5: Operations Web Tab
- 5.6: Notice Lifecycle

**Epic 6: Integration Testing & Automation** (1–2 stories) **[SIMPLIFIED]**
- 6.1: Cross-Moment Integration
- 6.2: Automation Reliability
- 6.3: Evidence Linking Tests
- (Foundation testing moved to Epic 1; performance testing optional)

**Epic 7: Documentation & Operator Experience** (0.5–1 story)
- 7.1: CLI Runbooks (not help; help in Epic 1)
- 7.2: Web UX Guides
- 7.3: Operator Runbook
- 7.4: Troubleshooting Guide

**Total Effort**: 12–19 stories (refined +0.5 net)

**Sequencing**:
- Week 1: Epic 1 (CLI + evidence protocol foundation)
- Week 2: Epic 2 (web foundation)
- Week 3: Epic 3 *fast-track* (Progress → real value)
- Week 4: Epics 4 & 5 parallel (Success + Notices)
- Week 5: Epic 6 (integration)
- Week 6: Epic 7 (docs)

---

**Status**: ✅ STEP 2 COMPLETE (refined structure approved)  
**Next**: STEP 3 (Detailed story creation with acceptance criteria)

