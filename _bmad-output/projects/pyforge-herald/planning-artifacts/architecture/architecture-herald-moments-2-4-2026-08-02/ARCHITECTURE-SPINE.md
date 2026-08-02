---
title: Herald Moments 2–4 Architecture Spine
slug: herald-moments-2-4-arch
status: draft
created: 2026-08-02
updated: 2026-08-02
altitude: epic
sources:
  - ../../prds/prd-herald-moments-2-4-2026-08-02/prd.md
---

# Herald Moments 2–4 Architecture Spine

**Altitude**: Epic — fixes the invariants that the 7 coordinated stories must share (CLI dispatcher, web layout, automation framework, evidence protocol).

---

## Paradigm: Unified Surfaces, Distributed Automation

Herald Moments 2–4 share a **single paradigm**: one CLI, one web surface, many independent automation triggers (webhooks, cron, gate checks). No separate tools per Moment; no per-story re-architecture. The stories implement Moment logic *within* this unified shell.

**Data plane**: Records (progress, claims, notices) owned by their Moment; cross-linked by evidence protocol.  
**Control plane**: Automation rules (webhooks, cron, gates) dispatch to Moment-specific handlers; operators author/approve.  
**UI plane**: One web layout (4 tabs + unified nav); each tab shows Moment-specific content.

---

## Architectural Decisions (ADs)

### AD-1: CLI — Single Dispatcher with Subcommands

**Rule**: One `herald` entry point; subcommands `progress`, `success`, `notice` dispatch to Moment logic. Shared global flags: `--help`, `--json`, `--date-range <start>..<end>`, `--station <name>`.

**Binds**: 
- CLI structure recognizable across all three Moments (operators learn once)
- Subcommand routing clean and extensible (add Moment 5 later as `herald future-moment`)

**Prevents**:
- Separate CLIs per Moment (tool fatigue, maintenance burden)
- Loose argument conventions (silent incompatibilities between Moments)

**[ADOPTED]** — Herald v0.1.0 uses this pattern; extend it.

---

### AD-2: Web Surface — Unified 4-Tab Navigation

**Rule**: Single Herald web app; header nav with 4 tabs: **Pitch** (Moment 1, external link), **Progress**, **Success**, **Operations**. Unified sidebar: station filter, date range selector, search box. Responsive layout (desktop ≥ tablet ≥ mobile support).

**Binds**:
- Users see a coherent Herald, not disconnected surfaces
- Navigation conventions shared across all Moments (consistency)
- Filtering (station, date) applies uniformly

**Prevents**:
- Separate web apps per Moment (fragmented UX, feature duplication)
- Inconsistent tab naming or layout (user confusion)

**[ADOPTED]** — Herald v0.1.0 web surface integrates existing Pitch tab; extend with Progress, Success, Operations tabs.

---

### AD-3: Data Model — Moment-Owned Records with Evidence Links

**Rule**: Each Moment owns its record type — Progress (Moment 2), Claim (Moment 3), Notice (Moment 4) — with fields per its PRD. Cross-linking via evidence protocol (URL + type pairs). No shared database schema across Moments; each owns its schema.

**Binds**:
- Each Moment can evolve independently (Moment 4 archives don't affect Moment 3 claim evolution)
- Evidence links are durable (URL is immutable proof reference)

**Prevents**:
- Monolithic schema (tight coupling between Moments)
- Lossy evidence (claims without links enforced at publish time)

**[ADOPTED]** — Spec defines three record types; stories implement independently.

---

### AD-4: Automation — Webhook + Cron + Gate Dispatch

**Rule**: Automation rules are **data**, not code. Stored in Herald config: per-Moment trigger rules (event type + handler name). Moment 2: on-ship webhook + Thursday 2300 UTC cron. Moment 3: on-PR-close webhook (extract) + operator gate (publish). Moment 4: manual author (no auto-trigger).

**Binds**:
- Operators can modify automation rules without recompiling
- Retries, rate limits, error handling centralized in dispatcher
- Easy to audit (config is version-controlled)

**Prevents**:
- Automation buried in story code (invisible to ops)
- Incidental consistency between webhook and cron handlers (both go through dispatcher)

**Implementation layers**:
- Dispatcher: webhook receiver + cron executor (shared)
- Handlers: Moment-specific logic (progress-extract, success-extract, notice-author)
- Config: Herald config file (trigger rules + event-to-handler mappings)

---

### AD-5: Evidence Protocol — Shared Link Schema & Validation

**Rule**: Evidence links follow schema: `{ type: "test_results|metrics|adoption|other", url: "https://...", label: "short description" }`. Validation: sync (404 on publish) + async (weekly stale-link check). No evidence ↔ claims allowed (enforced at publish gate).

**Binds**:
- Moment 3 claims and Moment 4 notices can link to each other (bidirectional)
- Evidence validation is consistent (one library, shared rules)
- Link audit trail (who added, when) is centralized

**Prevents**:
- Dead links in claims (404 detection at publish)
- Ambiguous link types (schema is strict)

**Storage**: Evidence links stored inline (claim/notice fields), not as separate records. Versioning: immutable published claims; editable drafts.

---

### AD-6: Operator Authorization — Role-Based Write Gates

**Rule**: Write operations require `operator` role (publish claim, author notice, update progress). Read operations are public (no auth). Role verified at CLI + web layer (same auth source: Herald app session or CLI token).

**Binds**:
- Consistent auth across CLI and web (same role model)
- Operators can't accidentally publish unreviewed claims (gate is enforced)

**Prevents**:
- Asymmetry (CLI allows unvetted publishes but web doesn't)
- Silent auth failures (role check happens before business logic)

**[ASSUMPTION]**: Herald app has existing session/auth model; CLI uses implicit auth (from machine identity or user session). Confirm with ops team.

---

### AD-7: Storage Strategy — Database-Backed, Archive-Friendly

**Rule**: Progress records and Success claims stored in database (queryable, indexed). Moment 4 notices stored as markdown files in archive folder structure (YYYY-MM/category/name.md), with database index for quick discovery. Redirects stored in database.

**Binds**:
- Fast queries for Moment 2 & 3 (database index)
- Durable archive for Moment 4 (files are permanent; can export/backup easily)
- Simple `ls` inspection of archive (operator doesn't need DB access to audit)

**Prevents**:
- Pure-file storage for Progress/Claims (slow filtering by date)
- Pure-database archive (hard to inspect, backup, or understand structure)

**Backup strategy**: Database nightly, archive files tracked in git (or synced to S3).

---

### AD-8: State Machine — Claim/Notice Lifecycle

**Rule**: Progress records are **immutable** (once published, not edited — new record for next update). Success claims: Draft → Published → Closed (optionally versioned if thesis is edited). Notices: Draft → Published → Closed (with edit history preserved).

**Binds**:
- Progress audit trail is clean (no confusion about what was claimed when)
- Operators can retract unpublished claims (draft-only delete allowed)
- Closed notices stay visible (no surprise removals)

**Prevents**:
- Retroactive edits confusing readers (mutable records)
- Loss of notices post-deadline (closed state preserves data)

---

### AD-9: Resilience — Automation Reliability & Fallback

**Rule**: Webhook failures trigger exponential backoff + max 3 retries (configurable). If exhausted, logged to operator dashboard + alert sent. Cron jobs run in dedicated queue (no blocking web requests). If automation fails, operator can manually trigger via CLI (`herald progress --update`, `herald success publish`).

**Binds**:
- Transient failures don't lose work (retries)
- Operators have fallback path (manual CLI)
- Clear visibility into automation failures (dashboard + alerts)

**Prevents**:
- Silent lost data (all failures logged)
- Timeout cascades (cron is isolated from web)

**[ASSUMPTION]**: Herald has existing queue/job infrastructure (from Moment 1 or v0.1.0). Reuse it; don't build new.

---

### AD-10: Extensibility — Future Moments

**Rule**: Paradigm and dispatcher are extensible: new Moments add a new subcommand + handler without touching existing Moment logic or CLI structure. Evidence protocol and automation framework designed for 10+ Moments without rearchitecture.

**Binds**:
- Moment 5+ can be added as stories in future epics
- CLI remains stable (existing scripts don't break)

**Prevents**:
- Revisiting dispatcher logic per new Moment (waste)

---

## Constraints (Load-Bearing Invariants)

**Integration constraint**: All three Moments must appear in a single CLI and single web surface. No separate platforms, no workarounds.

**Automation constraint**: Each Moment has explicit automation rule (schedule, event, gate). Rules are data (config), not code.

**Evidence constraint**: All Moment 3 claims and Moment 4 notices require ≥1 evidence link at publish time. Validation enforced.

**No silent shipping**: Pre-ship gate ensures every closed project has a Moment 3 claim authored (auto-extract + operator publish, or manual author).

---

## Inherited Constraints (from Herald v0.1.0 & Moment 1 Pitch spec)

- **Herald CLI structure**: Existing v0.1.0 entry point; extend with new subcommands (don't rebuild)
- **Herald web foundation**: Existing web app; add tabs + nav integration (don't rebuild)
- **Modernist design system**: Use design tokens from Moment 1 (colors, typography, grid)
- **Evidence linking**: Design system aligns with Pitch spec's design-code-bridge evidence protocol

---

## Deferred (Not Decided, Not Blocking)

1. **Database choice**: PostgreSQL, SQLite, or other? Defer to implementation story (Story 2 or first database story).
2. **Queue/job infrastructure**: Assume Herald has existing; if not, evaluate Celery, APScheduler, native async.
3. **Evidence extraction**: Auto-query dashboard API or parse public URLs? Defer to Moment 3 story.
4. **Notice versioning**: Full edit history stored as separate versions or single "current" + audit log? Defer to Moment 4 story.
5. **Authentication model**: Herald's auth mechanism (session, JWT, API key)? Assume existing; confirm with ops.
6. **Internationalization**: Do any surfaces need i18n? Defer; assume English-first for now.

---

## Diagrams

### CLI Structure

```
herald
├─ progress <station> [--update | --list --week recent|<N>]
├─ success [review <claim-id> | publish <claim-id> | list | get <claim-id>]
└─ notice [author --type <type> | list --month YYYY-MM | archive]

Global flags: --help, --json, --date-range <start>..<end>, --station <name>
```

### Web Surface Layout

```
┌─────────────────────────────────────────────────┐
│ Herald                [Pitch][Progress][Success][Operations] │
├─────────────────────────────────────────────────┤
│ ┌──────────────┐ ┌──────────────────────────────┐ │
│ │ Sidebar      │ │ Tab Content                  │ │
│ │ • Filter     │ │ (Progress: cards, Success:   │ │
│ │ • Station    │ │  timeline, Operations:       │ │
│ │ • Date range │ │  archive list)               │ │
│ │ • Search     │ │                              │ │
│ └──────────────┘ └──────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### Automation Dispatcher

```
Webhook Events (on-ship, on-PR-close)
         ↓
    Dispatcher
         ↓
    Config Lookup (trigger → handler)
         ↓
    Handler (moment-specific logic)
         ↓
    Store (database or archive)

Cron Events (weekly Thursday)
         ↓
    Queue (isolated, no blocking)
         ↓
    Handler
         ↓
    Store
```

### Evidence Protocol

```
Claim/Notice
├─ ID
├─ Date
├─ Content
└─ Evidence
   ├─ { type: "test_results", url: "...", label: "..." }
   ├─ { type: "metrics", url: "...", label: "..." }
   └─ { type: "adoption", url: "...", label: "..." }
```

---

## Cross-Story Invariants (What Stories Must Agree On)

1. **CLI argument parsing**: All stories use the same flag conventions (`--json`, `--date-range`, `--station`)
2. **Error messages**: All stories use consistent error formatting (template defined in shared utility)
3. **Database schema**: Progress/Claim tables defined in Story 2 (DB layer); Moment stories use them as-is
4. **Authorization**: All stories use the same role check (operator role required for writes)
5. **Evidence links**: All stories validate links using the shared protocol library
6. **Automation config**: All stories read their trigger rules from the same config structure

---

## Next Steps (Handoff to Stories)

1. **Story 1** (CLI Architecture) — Implement dispatcher, subcommand routing, flag parsing. Proof: `herald --help` shows all 3 subcommands; `herald progress --help` is clear.
2. **Story 2** (Web Layout) — Design nav, responsive layout, sidebar filters. Share new layout with Story 3–5 (they fill tabs). Proof: all 4 tabs present + navigable; sidebar filters work.
3. **Stories 3–5** (Moments 2, 3, 4) — In parallel. Each implements Moment logic + stores using architecture defined here. CLI + web integration tested per AD-1, AD-2.
4. **Story 6** (Integration Testing) — Verify all three Moments work together; automation triggers execute correctly; evidence links resolve.
5. **Story 7** (Documentation) — Document CLI and web surface for operators using this spine as reference.

---

## References

- **PRD**: `../prds/prd-herald-moments-2-4-2026-08-02/prd.md` (feature requirements)
- **Spec**: `../../specs/spec-herald-moments-2-4/SPEC.md` (five-field kernel, decisions)
- **Epic structure**: `../../specs/spec-herald-moments-2-4/epic-structure.md` (story breakdown, dependencies)
- **Herald v0.1.0**: Existing CLI and web surface (integration points)
- **Moment 1 Pitch spec**: `../../specs/spec-herald-pitch/SPEC.md` (design system, patterns to reuse)
