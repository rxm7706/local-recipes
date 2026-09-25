---
name: Herald Pitch Orchestration Architecture
slug: herald-pitch
status: final
created: 2026-08-01
updated: "2026-09-25"   # RE-STAMPED 2026-09-25: chain-currency cascade (prd -> spine) after the 2026-09-25 PRD re-stamp; no AD change. Prior 2026-09-20
altitude: feature
---

> **Consolidated 2026-08-02.** This spine is now the single canonical Architecture for the
> `pyforge-herald` station (explicit, same-day user override of the keep-chains-separate
> convention). AD-1..AD-10 below are unchanged from the original 2026-08-01 authoring.
> Herald's other live Architecture — **Moments 2–4**
> (`architecture-herald-moments-2-4-2026-08-02`) — is folded in as
> `## Satellite: Herald Moments 2–4 Architecture` with its own AD-1..AD-10 renumbered to
> AD-11..AD-20 to continue this document's sequence. Its `.memlog.md` had only one decision
> with real content (AD-1); the rest were literal `placeholder` stubs, a pre-existing defect
> in that document — the satellite section below is reconstructed from its
> `ARCHITECTURE-SPINE.md` prose, not from those placeholders (see this document's own
> `.memlog.md` for the note). The original folder is archived, unmodified, at
> `archive/_bmad-output/projects/pyforge-herald/planning-artifacts/architecture/architecture-herald-moments-2-4-2026-08-02/`.

# Herald Pitch Orchestration Architecture

**Feature**: Herald's Pitch Deck orchestration across 9 PyForge stations, producing 6 artifact formats per station from a single Design source with etagged safety and zero manual file transfers.

---

## Paradigm: Design-Code-Bridge with Etagged Pull Model

**Core insight**: One immutable Design prototype per station → Etagged pull into Code → Multi-format pipeline → Tracked finals + regenerable intermediates.

**Design Source of Truth**: Single `.dc.html` file per station is the immutable design prototype, tracked in git at `project/{station}.dc.html`. All code-side artifacts derive from it via an explicit pull model. Design edits happen in Claude Design cloud; Code never pushes back.

**Etagged Pull Model**: Every Design ↔ Code transfer validates etags. Write operations fail if etags mismatch, preventing silent overwrites. The protocol is deterministic and safe across concurrent edits.

**Multi-Format Export Pipeline**: Pull (etagged) → Markdown (marp) → PPTX (deckcraft) + Narration extraction → HTML deck engine + Video scripts. Each format has explicit ownership and regenerability status.

---

## Architecture Decision Records

### AD-1 — Single Immutable Design Prototype per Station

**Binds**: Each of the 9 stations (Marshal, Warden, Atlas, Mason, Steward, Scribe, Genesis, Doctor, Herald) has exactly one Design prototype file (`.dc.html`) as the source of truth.

**Prevents**: 
- Design drift between multiple design sources
- Silent overwrites when pulling updated designs
- Ambiguity about which version is current

**Rule**: All markdown, PPTX, narration, SVG, and video scripts derive from the single `.dc.html`. Code-side edits to any derived artifact do not flow back to Design.

**[ADOPTED]** — Proven on 7 existing decks; Design-Code-Bridge framework established.

---

### AD-2 — Etagged Safety on All Design ↔ Code Transfers

**Binds**: Every pull operation includes etag validation. Write operations require matching etag or fail explicitly.

**Prevents**:
- Mid-flight Design edits overwriting Code-side pulls
- Silent data loss during concurrent updates
- Ambiguous conflict states

**Rule**: 
- Read: Include `etag` in response metadata.
- Write: Require matching `etag` in request; reject if mismatch.
- On conflict: Fail loudly; never silently merge or prefer one side.

**[ADOPTED]** — Proven in Design-Code-Bridge protocol on 7 decks.

---

### AD-3 — Multi-Format Export Pipeline with Explicit Ownership

**Binds**: Artifact derivation follows a single pipeline: Design (source) → Markdown → PPTX, Narration, SVG → HTML deck engine, Video scripts (finals). Each format has a clear owner and regenerability status.

**Prevents**:
- Ambiguity about which format is authoritative
- Multiple code paths producing the same artifact
- Stale intermediate artifacts blocking shipping

**Rule**:
1. **Design protos** (`.dc.html`): Source of truth, tracked, etagged.
2. **Markdown** (marp): Extracted from Design protos, tracked, regenerable.
3. **PPTX** (deckcraft): Generated from Markdown + design tokens, tracked for deliverable readiness.
4. **Narration scripts** (`.md`): Extracted from Design speaker notes, tracked for video pipeline.
5. **SVG infographics**: Extracted as inline assets, tracked, never raster.
6. **HTML decks** (Vite): Built from Markdown, gitignored, regenerable in <5s.
7. **Video scripts** (`.mp4` via manticore): Rendered downstream, gitignored, regenerable in <60s.

**[ADOPTED]** — Workflow stages defined in spec companions; proven on deckcraft (PPTX) and existing deck engines (HTML).

---

### AD-4 — Aggressive Artifact Tracking Strategy (62% Footprint Reduction)

**Binds**: Track source + final deliverables; gitignore regenerable intermediates. Total tracked footprint: ~144 files (9 stations × ~16 files) vs. ~270 unoptimized.

**Prevents**:
- Repository bloat from storing regenerable artifacts
- Confusion about what lives where and why
- Wasted storage on build fragments

**Rule**:
- **Tracked**: Design protos (1 each), Markdown (5–8 each), PPTX (2–4 each), Narration (1–2 each), SVG infographics (0–1 each) = ~144 total.
- **Gitignored**: fragments.json, dist/, assets/, .mp4, node_modules, build caches (all regenerable in <15s for HTML, <60s for video).
- **Verification**: `retired-console-check` validates all tracked artifacts render correctly. Build pipeline proves all gitignored artifacts regenerate deterministically.

**[ADOPTED]** — Optimization strategy verified in spec appendix; no new infrastructure required.

---

### AD-5 — Modernist Design Tokens as Single Authority

**Binds**: One source of truth for design tokens (Figma variables). Tokens round-trip through: Figma → design-tokens.json → PPTX templates → deck engine → video production bibles.

**Prevents**:
- Token drift across surfaces (PPTX vs. HTML vs. Video)
- Hardcoded colors/fonts in templates
- Inconsistent visual identity across all 9 stations

**Rule**:
- Figma is the authority for all design tokens (colors, fonts, spacing, grid).
- Token changes flow: Figma → design-tokens.json (automated export) → templates (updated on next build).
- Templates consume tokens declaratively, never hardcode values.
- All 9 stations inherit tokens from the same source; per-station visuals vary (diagrams, photos), not fundamentals.

**[ADOPTED]** — Modernist-Identity framework CAP-4 defines tokens; round-trip proven on existing work.

---

### AD-6 — Nine-Station Replication with Identical Framework

**Binds**: Framework (Design-Code-Bridge, Deckcraft, Video-Scripts, Modernist-Identity) is identical across all 9 stations. Per-station content varies: thesis, pain point, solution pillars, ecosystem vision, personas.

**Prevents**:
- Re-engineering the framework for each station
- Inconsistency in narrative structure (six-act framework)
- Manual coordination between station teams

**Rule**:
- One deck workflow applies to all 9 stations: Seed → Design → Pull → Build → Extract → Ship.
- Content customization happens in Design (speaker notes, visuals, personas); Framework never changes.
- Tooling abstractions (deckcraft, video-scripts, design-code-bridge) are station-agnostic.

**[ADOPTED]** — Seven-station consolidation proven in spec; station roster confirms 9 domains ready for content authoring.

---

### AD-7 — Narration Script Extraction from Design Speaker Notes

**Binds**: Narration scripts are extracted mechanically from Design speaker notes, generating `{station}-narration-YYYY-MM-DD.md` per deck. Extraction is deterministic and tracked.

**Prevents**:
- Manual narration authoring (error-prone, not reproducible)
- Narration drift from visual story (speaker notes stay in sync)
- Ambiguity about what video pipeline consumes

**Rule**:
- Speaker notes in Design proto → Extracted to narration.md via mechanical extraction.
- Narration enforced linter: WPM, speech patterns, tone markers validated against voice bible.
- Narration blacklist (fabricated claims, misleading language) applied before any video render.
- Tracked in git for source auditability and video pipeline readiness.

**[ADOPTED]** — Mechanical extraction avoids authoring; linter enforced by Video-Scripts framework (CAP-3).

---

### AD-8 — Video Pipeline Boundary — Herald Orchestrates, Manticore Renders

**Binds**: Herald orchestrates narration extraction and real screen-recording sourcing. BMad-Manticore is downstream, consuming narration + real footage to render video.

**Prevents**:
- Scope creep into video rendering (out of Herald's scope)
- Fabricated product demos (Herald enforces real footage only)
- Unclear handoff between Herald and Manticore

**Rule**:
- Herald responsibilities: Extract narration, source real screen recordings, validate blacklist.
- Manticore responsibilities: Voice synthesis (Kokoro-82M), graphics (HyperFrames), SFX (AudioLDM2), final video render.
- Handoff: narration.md + real screen recordings → Manticore → `.mp4` output (gitignored, regenerable).
- No fabricated demos: All b-roll is real; Herald enforces this boundary at extraction time.

**[ADOPTED]** — Video-Scripts framework (CAP-3) defines four hard gates: Outline → Cut Plan → Graphics Beats → Final Render. Herald operates gates 1–2; Manticore operates 3–4.

---

### AD-9 — No Fabricated Demos — Real Footage Only

**Binds**: All screen recordings fed to video pipeline are real, recorded from actual product or system behavior. No AI-generated mockups, synthetic UI, or fabricated product demos.

**Prevents**:
- False claims about product capabilities
- Liability from misrepresentation
- Loss of trust if synthetic footage is later discovered

**Rule**:
- Screen recording sourcing is explicit: Real product footage only, never synthetic.
- Herald enforces this at narration extraction and footage sourcing stages.
- Manticore enforces this at graphics beats; rejects any synthetic input.
- Video pipeline gate #2 (Graphics Beats) includes a fabrication check before gate #3 (Final Render).

**[ADOPTED]** — Constraint stated in spec CAP-3 and PRD; inherited from existing PyForge quality standards.

---

### AD-10 — Narration Voice Identity — Consistency Enforced by Linter

**Binds**: Narration must match a published voice character (WPM, speech patterns, tone markers). Linter enforces consistency; blacklist blocks non-matching narration.

**Prevents**:
- Tonal inconsistency across videos
- Narration that contradicts established voice
- Unauthorized claims or misleading language

**Rule**:
- Voice bible: WPM range, speech patterns, tone markers, blacklisted claims (defined upstream, not in this effort).
- Linter: Validates narration against voice bible before video render.
- Blacklist: If linter flags, narration revision required; video render blocked.

**[ADOPTED]** — Video-Scripts framework (CAP-3) enforces via script linter; voice bible is upstream (external source).

---

## System Boundaries & Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Design Cloud (Claude Design)                                 │
│ - 9 interactive prototypes (.dc.html)                       │
│ - Speaker notes (narration source)                          │
│ - Visual iteration (Modernist tokens applied)               │
└────────────────┬────────────────────────────────────────────┘
                 │ Pull (etagged)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Herald Orchestration Layer (Python/Node)                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Design-Code-Bridge                                   │   │
│  │ - Pull .dc.html (etagged)                           │   │
│  │ - Extract Markdown (marp)                           │   │
│  │ - Validate etags (conflict detection)               │   │
│  └──────────────────────────────────────────────────────┘   │
│                     │                                        │
│      ┌──────────────┴──────────────┬──────────────────┐     │
│      ▼                             ▼                  ▼     │
│  ┌────────────────┐          ┌──────────────┐  ┌──────────┐ │
│  │ Deckcraft      │          │Narration     │  │ SVG/     │ │
│  │ (Markdown→    │          │Extraction    │  │Infographic│ │
│  │  PPTX + tokens)│         │(Speaker notes│  │Extraction │ │
│  └────────────────┘          │ → .md)      │  └──────────┘ │
│                              └──────────────┘               │
│  (All tracked: .dc.html, .md, .pptx, narration.md, .svg)   │
└────────────────┬─────────────────────────────────────────────┘
                 │ narration.md + real footage
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ BMad-Manticore (Downstream)                                  │
│ - Voice synthesis (Kokoro-82M)                              │
│ - Graphics (HyperFrames)                                    │
│ - SFX (AudioLDM2)                                           │
│ - Final render (.mp4 gitignored, regenerable)              │
└─────────────────────────────────────────────────────────────┘

Build Layer (Vite):
  Markdown → HTML deck engine (dist/, gitignored, regenerable <5s)
  All 6 formats ready for shipping; retired-console-check validates.
```

---

## Invariants by Slice

### Design Authoring
- **Single source**: One `.dc.html` per station is immutable at Code side.
- **Etagged pulls**: Every pull validates etag; conflicts fail loudly.
- **Token consistency**: Figma tokens applied uniformly via Modernist system.

### Markdown Export
- **Mechanical extraction**: No hand-authoring; derived from Design protos.
- **Six-act structure**: All markdown follows canonical structure (CAP-5 spec).
- **Regenerable**: Markdown re-extracted deterministically from Design on demand.

### PPTX Generation
- **Token-driven**: All fonts, colors, spacing from design-tokens.json, never hardcoded.
- **Editable**: Output opens in PowerPoint; structure + formatting preserved.
- **Tracked**: PPTX files committed to git for deliverable readiness proof.

### Narration Extraction
- **Mechanical**: Speaker notes → narration.md, deterministic, no hand-authoring.
- **Linter-enforced**: Voice identity + blacklist validated before video render.
- **Real footage only**: Screen recordings sourced from actual product, never synthetic.

### HTML Deck Engine
- **Regenerable**: Built from Markdown + tokens in <5s; not committed to git.
- **Validation**: `retired-console-check` proves all 9 decks render without error.
- **Asset management**: Inline SVGs (no raster images); assets/ gitignored.

### Video Scripts
- **Downstream boundary**: Manticore consumes narration.md + real footage; Herald stops at extraction.
- **No fabrication**: Herald enforces real footage sourcing; Manticore validates at graphics beats.
- **Gitignored output**: .mp4 regenerable on demand; not committed to git.

---

## Deferred Decisions

1. **Station-by-station review cadence**: Should each station's deck be reviewed in isolation or as a family batch? (Deferred to story/sprint planning; spec suggests family batch to catch inconsistencies.)

2. **Narration extraction automation**: Should extraction be pixi-automated or manual per-station via Design UI? (Deferred to story planning; spec suggests automated pixi task with manual review.)

3. **Video render scheduling**: Should all 9 station videos render at completion or prioritize a pilot subset? (Deferred to operations; spec suggests pilot subset for proof-of-concept, then full batch.)

---

## Success Signals

- ✅ 9 Design projects seeded with Modernist tokens applied uniformly.
- ✅ 9 prototypes authored per six-act framework, etagged, tracked.
- ✅ 54 artifacts exported (9 stations × 6 formats) and tracked.
- ✅ All 9 PPTX files open in PowerPoint; fonts, colors, layouts preserved.
- ✅ All 9 HTML decks render; `retired-console-check` passes (renamed from `dashboard-check`; steward 30.2, 2026-08-25).
- ✅ All 9 narration scripts extracted and available for video pipeline.
- ✅ Zero manual file transfers; design-code-bridge automation end-to-end.
- ✅ Tracked footprint: ~144 files (62% reduction vs. unoptimized).

---

## Scope Note: Related Efforts

- **Herald Moments 2–4 (Progress, Success, Operations)**: **Folded in 2026-08-02** as
  `## Satellite: Herald Moments 2–4 Architecture` below (AD-11–AD-20). Previously tracked
  as a separate, not-in-scope architecture; the same-day user override merges it into this
  station's single spine.
- **BMad-Manticore video rendering**: Downstream; Herald feeds it, does not implement.
- **Figma variable management**: Upstream; Herald consumes, does not author tokens.

---

## Satellite: Herald Moments 2–4 Architecture

> Folded in 2026-08-02 from `architecture-herald-moments-2-4-2026-08-02/ARCHITECTURE-SPINE.md`
> (slug `herald-moments-2-4-arch`, status `draft`, altitude `epic`, created/updated
> 2026-08-02). AD-1–AD-10 in that document are renumbered AD-11–AD-20 here to continue this
> spine's sequence; content is otherwise verbatim. The original folder is archived,
> unmodified, at
> `archive/_bmad-output/projects/pyforge-herald/planning-artifacts/architecture/architecture-herald-moments-2-4-2026-08-02/`.

**Altitude**: Epic — fixes the invariants that the 7 coordinated Moments 2–4 stories must share (CLI dispatcher, web layout, automation framework, evidence protocol).

### Paradigm: Unified Surfaces, Distributed Automation

Herald Moments 2–4 share a single paradigm: one CLI, one web surface, many independent automation triggers (webhooks, cron, gate checks). No separate tools per Moment; no per-story re-architecture. The stories implement Moment logic *within* this unified shell.

**Data plane**: Records (progress, claims, notices) owned by their Moment; cross-linked by evidence protocol.
**Control plane**: Automation rules (webhooks, cron, gates) dispatch to Moment-specific handlers; operators author/approve.
**UI plane**: One web layout (4 tabs + unified nav); each tab shows Moment-specific content.

### AD-11 — CLI — Single Dispatcher with Subcommands (was AD-1)

**Rule**: One `herald` entry point; subcommands `progress`, `success`, `notice` dispatch to Moment logic. Shared global flags: `--help`, `--json`, `--date-range <start>..<end>`, `--station <name>`.

**Binds**: CLI structure recognizable across all three Moments (operators learn once); subcommand routing clean and extensible (add Moment 5 later as `herald future-moment`).

**Prevents**: Separate CLIs per Moment (tool fatigue, maintenance burden); loose argument conventions (silent incompatibilities between Moments).

**[ADOPTED]** — Herald v0.1.0 uses this pattern; extend it.

### AD-12 — Web Surface — Unified 4-Tab Navigation (was AD-2)

**Rule**: Single Herald web app; header nav with 4 tabs: **Pitch** (Moment 1, external link), **Progress**, **Success**, **Operations**. Unified sidebar: station filter, date range selector, search box. Responsive layout (desktop ≥ tablet ≥ mobile support).

**Binds**: Users see a coherent Herald, not disconnected surfaces; navigation conventions shared across all Moments; filtering (station, date) applies uniformly.

**Prevents**: Separate web apps per Moment (fragmented UX, feature duplication); inconsistent tab naming or layout (user confusion).

**[ADOPTED]** — Herald v0.1.0 web surface integrates existing Pitch tab; extend with Progress, Success, Operations tabs.

### AD-13 — Data Model — Moment-Owned Records with Evidence Links (was AD-3)

**Rule**: Each Moment owns its record type — Progress (Moment 2), Claim (Moment 3), Notice (Moment 4) — with fields per its PRD. Cross-linking via evidence protocol (URL + type pairs). No shared database schema across Moments; each owns its schema.

**Binds**: Each Moment can evolve independently (Moment 4 archives don't affect Moment 3 claim evolution); evidence links are durable (URL is immutable proof reference).

**Prevents**: Monolithic schema (tight coupling between Moments); lossy evidence (claims without links enforced at publish time).

**[ADOPTED]** — Spec defines three record types; stories implement independently.

### AD-14 — Automation — Webhook + Cron + Gate Dispatch (was AD-4)

**Rule**: Automation rules are **data**, not code. Stored in Herald config: per-Moment trigger rules (event type + handler name). Moment 2: on-ship webhook + Thursday 2300 UTC cron. Moment 3: on-PR-close webhook (extract) + operator gate (publish). Moment 4: manual author (no auto-trigger).

**Binds**: Operators can modify automation rules without recompiling; retries, rate limits, error handling centralized in dispatcher; easy to audit (config is version-controlled).

**Prevents**: Automation buried in story code (invisible to ops); incidental inconsistency between webhook and cron handlers (both go through dispatcher).

**Implementation layers**: Dispatcher (webhook receiver + cron executor, shared); Handlers (Moment-specific logic — progress-extract, success-extract, notice-author); Config (Herald config file — trigger rules + event-to-handler mappings).

### AD-15 — Evidence Protocol — Shared Link Schema & Validation (was AD-5)

**Rule**: Evidence links follow schema: `{ type: "test_results|metrics|adoption|other", url: "https://...", label: "short description" }`. Validation: sync (404 on publish) + async (weekly stale-link check). No evidence ↔ claims allowed (enforced at publish gate).

**Binds**: Moment 3 claims and Moment 4 notices can link to each other (bidirectional); evidence validation is consistent (one library, shared rules); link audit trail (who added, when) is centralized.

**Prevents**: Dead links in claims (404 detection at publish); ambiguous link types (schema is strict).

**Storage**: Evidence links stored inline (claim/notice fields), not as separate records. Versioning: immutable published claims; editable drafts.

### AD-16 — Operator Authorization — Role-Based Write Gates (was AD-6)

**Rule**: Write operations require `operator` role (publish claim, author notice, update progress). Read operations are public (no auth). Role verified at CLI + web layer (same auth source: Herald app session or CLI token).

**Binds**: Consistent auth across CLI and web (same role model); operators can't accidentally publish unreviewed claims (gate is enforced).

**Prevents**: Asymmetry (CLI allows unvetted publishes but web doesn't); silent auth failures (role check happens before business logic).

**[ASSUMPTION]**: Herald app has existing session/auth model; CLI uses implicit auth (from machine identity or user session). Confirm with ops team.

### AD-17 — Storage Strategy — Database-Backed, Archive-Friendly (was AD-7)

**Rule**: Progress records and Success claims stored in database (queryable, indexed). Moment 4 notices stored as markdown files in archive folder structure (YYYY-MM/category/name.md), with database index for quick discovery. Redirects stored in database.

**Binds**: Fast queries for Moment 2 & 3 (database index); durable archive for Moment 4 (files are permanent; can export/backup easily); simple `ls` inspection of archive (operator doesn't need DB access to audit).

**Prevents**: Pure-file storage for Progress/Claims (slow filtering by date); pure-database archive (hard to inspect, backup, or understand structure).

**Backup strategy**: Database nightly, archive files tracked in git (or synced to S3).

### AD-18 — State Machine — Claim/Notice Lifecycle (was AD-8)

**Rule**: Progress records are **immutable** (once published, not edited — new record for next update). Success claims: Draft → Published → Closed (optionally versioned if thesis is edited). Notices: Draft → Published → Closed (with edit history preserved).

**Binds**: Progress audit trail is clean (no confusion about what was claimed when); operators can retract unpublished claims (draft-only delete allowed); closed notices stay visible (no surprise removals).

**Prevents**: Retroactive edits confusing readers (mutable records); loss of notices post-deadline (closed state preserves data).

### AD-19 — Resilience — Automation Reliability & Fallback (was AD-9)

**Rule**: Webhook failures trigger exponential backoff + max 3 retries (configurable). If exhausted, logged to operator dashboard + alert sent. Cron jobs run in dedicated queue (no blocking web requests). If automation fails, operator can manually trigger via CLI (`herald progress --update`, `herald success publish`).

**Binds**: Transient failures don't lose work (retries); operators have fallback path (manual CLI); clear visibility into automation failures (dashboard + alerts).

**Prevents**: Silent lost data (all failures logged); timeout cascades (cron is isolated from web).

**[ASSUMPTION]**: Herald has existing queue/job infrastructure (from Moment 1 or v0.1.0). Reuse it; don't build new.

### AD-20 — Extensibility — Future Moments (was AD-10)

**Rule**: Paradigm and dispatcher are extensible: new Moments add a new subcommand + handler without touching existing Moment logic or CLI structure. Evidence protocol and automation framework designed for 10+ Moments without rearchitecture.

**Binds**: Moment 5+ can be added as stories in future epics; CLI remains stable (existing scripts don't break).

**Prevents**: Revisiting dispatcher logic per new Moment (waste).

### Satellite Constraints (Load-Bearing Invariants)

**Integration constraint**: All three Moments must appear in a single CLI and single web surface. No separate platforms, no workarounds.

**Automation constraint**: Each Moment has explicit automation rule (schedule, event, gate). Rules are data (config), not code.

**Evidence constraint**: All Moment 3 claims and Moment 4 notices require ≥1 evidence link at publish time. Validation enforced.

**No silent shipping**: Pre-ship gate ensures every closed project has a Moment 3 claim authored (auto-extract + operator publish, or manual author).

**Inherited from Herald v0.1.0 & this document's own AD-1..AD-10**: existing CLI structure extends (don't rebuild); existing web app adds tabs + nav (don't rebuild); Modernist design tokens (AD-5) apply to Progress/Success/Operations surfaces same as the deck family.

### Satellite Diagrams

```
CLI Structure:
herald
├─ progress <station> [--update | --list --week recent|<N>]
├─ success [review <claim-id> | publish <claim-id> | list | get <claim-id>]
└─ notice [author --type <type> | list --month YYYY-MM | archive]

Global flags: --help, --json, --date-range <start>..<end>, --station <name>

Web Surface Layout:
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

Automation Dispatcher:
Webhook Events (on-ship, on-PR-close) → Dispatcher → Config Lookup (trigger → handler)
  → Handler (moment-specific logic) → Store (database or archive)
Cron Events (weekly Thursday) → Queue (isolated, no blocking) → Handler → Store

Evidence Protocol:
Claim/Notice { ID, Date, Content, Evidence: [{type, url, label}, ...] }
```

### Satellite Deferred Decisions (Not Decided, Not Blocking)

1. Database choice: PostgreSQL, SQLite, or other? Deferred to implementation story.
2. Queue/job infrastructure: assume Herald has existing; if not, evaluate Celery, APScheduler, native async.
3. Evidence extraction: auto-query dashboard API or parse public URLs? Deferred to Moment 3 story.
4. Notice versioning: full edit history as separate versions, or single "current" + audit log? Deferred to Moment 4 story.
5. Authentication model: Herald's auth mechanism (session, JWT, API key)? Assume existing; confirm with ops.
6. Internationalization: do any surfaces need i18n? Deferred; assume English-first for now.

---

## Architecture Status

**Finalized**: 2026-08-01 (AD-1..AD-10); Moments 2–4 satellite folded in 2026-08-02 (AD-11..AD-20, drafted 2026-08-02, status `draft` in its own document).
**Altitude**: Feature-level (AD-1..AD-10); Epic-level (AD-11..AD-20).
**Next Steps**: `bmad-create-epics-and-stories` for implementation breakdown (Moment 1 side); Moments 2–4 epic breakdown already exists at `planning-artifacts/epics.md` / `epics-with-stories.md`.

---

*AD-1..AD-10 distilled from spec-pyforge-herald/SPEC.md (formerly spec-herald-pitch/SPEC.md) + prd-pyforge-herald-2026-08-01/prd.md. AD-11..AD-20 folded in 2026-08-02 from architecture-herald-moments-2-4-2026-08-02/ARCHITECTURE-SPINE.md (archived, unmodified, at archive/_bmad-output/projects/pyforge-herald/planning-artifacts/architecture/architecture-herald-moments-2-4-2026-08-02/). Decisions logged in .memlog.md.*

---

## Currency reconciliation — 2026-08-26

Reconciliation pass cascaded from the same-day brief/PRD re-dating; grounded in the as-built
package (`src/shared/packages/pyforge-herald/src/pyforge/herald/`), the Epic 13–17 story
specs, and the Canopy obligations recorded in `epics.md` (2026-08-24). AD-1..AD-20 above
stand as written **except** where marked below; the satellite's deferred decisions are now
mostly closed by shipped code.

**Satellite ADs vs. the as-built live backend (Epic 13, done 2026-08-13):**

- **AD-13/AD-17 (storage)** — resolved concretely: one stdlib **SQLite** database
  (`.herald/herald.db`, WAL, versioned migration runner in `db.py`) carries Progress/Claims/
  Notices behind the pre-existing pure-function seam; the CLI/web-tab contract kept its
  shape, and notices' git-tracked markdown archive stays the durable copy (AD-17's
  archive-friendly half held exactly as designed). Satellite Deferred Decision 1 (database
  choice) is closed: SQLite, not PostgreSQL; no SQLAlchemy/Alembic.
- **Concurrency prerequisite (implicit in AD-18/AD-19, never its own AD)** — before any
  second writer existed, story 13.1 replaced the unlocked whole-file read-modify-write with
  a stdlib cross-platform advisory lock (`locking.py`, `fcntl`/`msvcrt`); 13.3 then subsumed
  it under SQLite's transactional locking. DW-1-4-2 resolved.
- **AD-14 (webhook + cron dispatch)** — shipped, reshaped: `webhook.py` is a
  framework-agnostic module (HMAC-SHA256 verification, `on-ship`/`on-pr-close`), mounted via
  `webhook_host.py` onto the host ASGI inside **Steward's `spec-secure-live-dashboards`
  trust boundary** — no bespoke Herald perimeter, no Flask/FastAPI app of Herald's own. The
  triggering CI is GitHub Actions (recorded decision, spec-13-4). The cron half runs as
  `scheduler.py` behind a fifth top-level CLI verb (`herald scheduler run`, CI-scheduled)
  rather than a resident APScheduler/Celery daemon — Satellite Deferred Decision 2
  (queue/job infrastructure) closed as "none needed".
- **AD-16 (operator authorization)** — the `[ASSUMPTION]` is discharged: role isolation and
  audit for Herald's web/portal surfaces ride **`pyforge.steward.dashboard`** (CAP-7), per
  the Canopy obligations; Herald does not own an auth model. Satellite Deferred Decision 5
  closed the same way.
- **AD-19 (resilience)** — retry/backoff + operator-alert delivery shipped in `webhook.py`
  as specced; 13.6 proved the composed path live (a real merge creates progress + a
  success-claim draft with no human action, CI-contained).
- **AD-11 (single dispatcher)** — held and stretched exactly as designed:
  `TOP_LEVEL_COMMANDS` is now `("deck", "progress", "success", "notice", "scheduler")`; the
  extension cost was a subparser, not a rearchitecture (AD-20 vindicated).

**New architectural surface since this spine was cut (no AD renumbering; recorded here):**

- **Deck visual QA (Epic 14)** — `deck_qa.py`: a gate-registry + machine-readable report
  interface (gate-id-keyed, round-trippable) under `herald deck qa <slug>` (entrypoint
  decision, spec-14-1); a headless-Chromium render gate (playwright-python, already pinned —
  serves built `dist/` over a throwaway loopback static server, **not** `file://`, because
  Chromium blocks module imports cross-origin under `file://` — recorded decision,
  spec-14-2); an image-slot scan gate. Constraint held: report-only, never mutates deck
  sources, never rebuilds.
- **PPTX-native pipeline (Epic 15)** — `pptx_pipeline.py` + `templates/`:
  template-parse-then-fill (`spec.json` machine contract + `content_plan.json`; raw OOXML
  never hand-written) producing decks whose every text run edits in PowerPoint, plus
  Pillow real-font-measured autofit shapes for dense content. This **amends AD-3's PPTX
  row**: deckcraft's markdown→PPTX slice produced background-image slides with zero
  editable text runs (proven 2026-08-22, the unpark trigger); the editable-deliverable
  path is now the template pipeline. It coexists with, never replaces, the HTML/Marp path.
- **Exporters as hook plugins (Epic 16, canopy:AD-21)** — `exporters.py`: Marp, PPTX, and
  `.dc.html` export register as default plugins on the shared `pyforge.core.hooks`
  contract (HookSpec/HookPlugin/PluginRegistry); no station-local plugin loader; export
  success is a station result, never a PR quality-gate verdict (`SecondVerdictError`).
- **Canopy service face + portal (Epic 17)** — Herald capabilities surface through
  `POST /stations/herald/mcp` on the host ASGI and the `/stations/herald/` HTMX portal
  slice (deck status for one slug, rendered via PortalClient only — no raw HTTP, no
  `pyforge.*` imports under `src/platform/`, shared `django-pyforge` chrome only). No
  standalone port, no `services/` microservice. The station SKF skill
  (`.claude/skills/pyforge-herald/`, v0.1.0) and `bmad-agent-herald` persona act only
  through the `pyforge herald …` grammar + that MCP face.
- **Verification rename** — the Guildhall generator and its `dashboard-check` pixi task
  were deleted 2026-08-25 (steward 30.2); render verification references above now read
  `retired-console-check` (corrected in place at the two remaining occurrences).

**Deferred decisions still genuinely open:** Satellite items 3 (evidence auto-extraction
source), 4 (notice versioning depth) and 6 (i18n) remain open and non-blocking; Moment-1
deferred decisions 1–3 (review cadence, extraction automation, video render scheduling)
remain open — the video pipeline (AD-8/AD-9/AD-10 boundary with Manticore) is still
unexercised downstream.


## Runtime floor — reconciled 2026-09-07

**Python 3.14 is the only supported runtime.** `pyproject.toml` now declares
`requires-python = ">=3.14"` (marshal Story 32.2, `spec-fleet-consistency-standard` CAP-5),
matching `pixi.toml`'s `python = ">=3.14.7,3.14.*"` and every env-scoped `3.14.*` pin.

Consequence for this spine: no deployment target, container image or CI lane may assume a
3.12/3.13 interpreter for `pyforge-herald`, and none does today — this records the constraint
rather than changing it. The previous `>=3.12` declaration was never exercised by any
environment in the workspace.


## Currency reconciliation — 2026-09-14

*Chain-currency sweep cascade: the PRD re-dated 2026-09-14 after reconciling against
`spec-pyforge-herald`'s 2026-09-13 SPEC.md/memlog, which fires the `prd→arch` edge.
This section is the as-built check: does the spine above still describe the station.*

**No structural divergence, and two AD boundaries confirmed by the effect-gap
closures rather than contradicted by them.**

1. **The deck-QA gate landed as a pixi task, not as a new runtime surface.** Story
   19.3's gate is `[feature.pyforge-herald.tasks.deck-qa]` in `pixi.toml`, declared
   **advisory only — never a PR gate** (verified live this pass, in the task's own
   description). That is exactly the boundary this spine and Herald's Spec both hold:
   Herald proclaims, it does not gate. Nothing here needed to move for it.
2. **The `.pptx` pipeline's first real render exercised the existing AD boundary, not
   a new one.** Story 19.4 filled `presentations/pyforge-warden/src/content_plan.json`
   through `pptx_pipeline.py` against the committed template — the Deckcraft path this
   spine already draws. The artifact is data, not a new component.
3. **Story 20.2's per-deck fact ledgers are a new artifact *class*, and they belong to
   a different Spec.** Ten `presentations/<slug>/facts.yaml` files now exist (verified
   live: 10). They are owned and reconciled by `spec-deck-family-currency`, not by this
   station spine, which is why the kernel Spec excludes them from its own drift
   tracking rather than absorbing them. No AD here describes them and none should — a
   satellite Spec owning its own artifact family is the intended shape.

**The one thing this spine must not quietly resolve.** The live-backend triggers have
still never run green: Story 19.2 is `blocked` on `DW-13-6-1` — `steward deploy
perimeter` renders only a hardcoded `myproject.asgi:application` with no
`--asgi-application` flag. This is a **cross-station dependency on Steward's
deployment surface**, not a Herald architecture decision, and it is recorded here (and
in the PRD) rather than converted into a Herald AD. `spec-herald-moments-2-4-live-backend`
(LB-2/LB-3) remains the contract that will close it.

**Deferred decisions unchanged.** Satellite items 3, 4 and 6 and Moment-1 items 1–3
all remain open and non-blocking; the video pipeline (AD-8/AD-9/AD-10 boundary with
Manticore) is still unexercised downstream, unchanged by this window.

**No content change required beyond this note.** `updated:` bumped to record that the
cascade ran.

## Currency reconciliation — 2026-09-17

Reviewed after the one-chain herald fold remint. No AD added, changed, or removed. Steps 3–4 of CHAIN-STANDARD §3 recorded as no-op in the station Spec memlog.

## Currency reconciliation — 2026-09-20

*Chain-currency sweep: `research/docs-site-bmad-method-pattern-2026-09-20.md` (an operator-asked
seed, 09:55Z: the docs site matches BMAD-METHOD's Astro + Starlight + Pages pattern so upstream's
skills and workflows apply unchanged) post-dated the PRD (`prd→arch` cascade); no AD added, changed or removed. It is input for `bmad-spec`, not yet
a capability: no requirement, decision or story changes here until that pass mints the CAP.
`updated:` bumped to record that the check ran; the six decisions the research asks for are listed
in its § 3 and on the Dream's 2026-09-20 entry.*

## Currency reconciliation — 2026-09-20 (fleet consistency pass)

*Operator ruling 2026-09-20: every station's PRD, spine and epics are re-stamped in the same pass,
grace period or not, so the whole chain reads current for the foundry cutover. Trigger: the
station Spec's `.memlog.md` gained a 2026-09-20 event — the fleet consistency pass reconciled every
tracked story spec's frontmatter against the sprint ledger, matched each "Ledger status" line,
reconstructed missing Auto Run Results from `main`'s landing commits, fixed invalid frontmatter,
and let `sprint-ledger-sync` roll the epic keys up (`spec→prd→arch` cascade). Bookkeeping only:
no requirement, decision, story or AD changes in this spine. `updated:` bumped to record that the
check ran.*

## Currency reconciliation — 2026-09-25

`prd→arch` edge after the PRD re-stamp of 2026-09-25 (steward 59.6's roster re-export in
`progress.py`). The roster is read from `pyforge-core`, the shared leaf every station already
depends on — no new import boundary, no AD added, changed or removed. `updated:` bumped.
