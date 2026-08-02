# Herald Dashboard Snapshot — BEFORE Fleet Chain Completeness Regeneration

**Timestamp:** 2026-08-01 (pre-commit state)

## Dashboard Status (from docs/dashboard/data.js)

**Project:** Herald  
**Label:** Herald  
**Branch:** loop/pyforge-herald  
**Current Contract:** SPEC-design-code-bridge CAP-1..5 · FR-01–FR-26 · AD-1–AD-8 · deterministic no-LLM core  
**Line State:** paused at 1.3

### Story Completion (E1 only, others shown for context)
- Total Stories: 17 (not counting epics/retrospectives)
- **Done:** 4/17
  - 1.1: Package scaffold ✅
  - 1.2: Transport port + MCP adapter ✅
  - 1.4: Bridge-core skeleton ✅
  - 1.5: Registry module ✅
- **Pending:** 13/17
  - 1.3: Fallback transport adapter ⏳
  - 1.6 through 5.2: All remaining ⏳

### Velocity (measured agent-compute time)
- Median: ~98 min/story
- Range: 29–417 min
- Total E1: ~11.9 h active compute
- Measured: 5/17 stories

---

## Sprint Status (from sprint-status-ledger.yaml)

**Project:** herald  
**Total Stories Tracked:** 27 (including 5 epics + 5 optional retrospectives)

### Breakdown by Status
- **done:** 4 stories
  - 1-1-package-scaffold-for-pyforge-herald
  - 1-2-transport-port-primary-mcp-client-adapter-the-transport-spike
  - 1-4-bridge-core-skeleton-state-errors-determinism-boundary
  - 1-5-registry-module-readme-design-project
- **backlog:** 23 stories (all remaining work)

---

## Planning Chain Status (BEFORE Regeneration)

| Layer | Source | Status |
|-------|--------|--------|
| Dream | docs/dreams/herald-pitch.md (NEW, consolidated) | ✅ ready |
| Spec | **FRAGMENTED**: 5 separate specs (now archived) | ❌ orphaned |
| |  - spec-design-code-bridge | → archived |
| | - spec-deckcraft | → archived |
| | - spec-video-scripts | → archived |
| | - spec-modernist-identity | → archived |
| | - spec-pyforge-herald (old) | → archived |
| PRD | 2 old versions (archived) | ❌ disconnected |
| Architecture | 2 old versions (archived) | ❌ disconnected |
| Epics | epics.md (old) | ⚠️ stale |
| Code | Herald v0.1.0 (shipped) | ✅ stable |

---

## Changes Made (Staged, Not Committed)

1. **Specs Consolidated:** 5 separate specs → 1 unified spec-herald-pitch
2. **Bridge Protocol Preserved:** Copied to spec-herald-pitch/bridge-protocol.md
3. **New Artifacts Generated:**
   - ✨ spec-herald-pitch/ (7 companions)
   - ✨ prd-pyforge-herald-2026-08-01/
   - ✨ architecture-herald-pitch-2026-08-01/
   - ✨ research/market-and-requirements-analysis.md
4. **Epics Regenerated:** epics.md updated from new spec
5. **Old Artifacts Archived:** 26 files → archive/ with full path preservation

---

## What Needs Updating After Commit

1. **Dashboard Contract:** Update from "SPEC-design-code-bridge" → "spec-herald-pitch"
2. **Sprint Status:** May need regeneration if epic structure changed
3. **Story Specs:** Review if new epics.md affected story IDs or status
4. **Dashboard Data:** Run `pixi run -e local-recipes dashboard-gen` to sync
