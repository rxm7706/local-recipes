---
title: Herald's Proclamation Surfaces (Moments 2–4) — Product Requirements
slug: herald-moments-2-4
status: draft
created: 2026-08-02
updated: 2026-08-02
prd_version: 1.0
sources:
  - ../../../specs/spec-herald-moments-2-4/SPEC.md
  - ../../../specs/spec-herald-moments-2-4/epic-structure.md
---

# Herald's Proclamation Surfaces — Product Requirements Document

---

## Executive Summary

Herald's Four Moments of Proclamation framework guides all factory communications. Moment 1 (Pitch) is production-ready with the deck family specification. **This PRD delivers Moments 2–4** — three missing surfaces that complete the proclamation cycle:

- **Moment 2 (Progress)**: Make shipping motion visible + explainable (cost transparency, unblock narratives)
- **Moment 3 (Success)**: Claim project completion with retrievable evidence (tests, metrics, adoption)
- **Moment 4 (Operations)**: Announce deprecations, fixes, end-of-life notices proactively

Implementation is a **coordinated epic** (7 stories, 12–18 story-points) with shared CLI/web/automation infrastructure, prioritizing **integration correctness** over velocity-to-first-value.

---

## Product Vision & Strategy

### Vision Statement

Herald is the factory's unified voice. The Four Moments ensure every idea is argued (Pitch), every shipping is visible (Progress), every completion is claimed (Success), and every sunset is announced (Operations). This PRD completes Moments 2–4 so no work ships silently and every claim carries proof.

### Strategic Priority

**High** — Herald is infrastructure. Silent shipping creates downstream confusion (what changed? what cost? what unblocked?). Proclamation surfaces are the trust layer for the entire factory.

### Audience

- **Primary**: Factory operators, team leads, project stakeholders (who need visibility into shipping motion)
- **Secondary**: CI/CD systems, dashboard readers (automated evidence sources)
- **Tertiary**: Public-facing systems consuming notices (Moment 4 archive)

---

## Product Scope

### In Scope

**Moment 2 (Progress Visibility)**
- Weekly progress summaries + on-shipping-event updates
- Cost transparency (compute, tokens, wall-clock time)
- Unblock narratives (what downstream work did this unlock?)
- Automation: on-ship webhook + Thursday 2300 UTC weekly fallback
- CLI interface: `herald progress <station> [--update]`
- Web widget: Progress tab with station filter + date range

**Moment 3 (Success Proclamation)**
- Auto-extract success claims on PR-close + passing gates
- Claim structure: project, thesis, proof (tests, metrics, adoption)
- Evidence linking framework (link-to-evidence protocol)
- Operator review gate before publish (quality gate)
- Automation: on-PR-close + passing gates (auto-extract); operator-triggered publish
- CLI interface: `herald success [review <claim-id> | publish <claim-id>]`
- Web archive: Success tab with chronological claims + evidence badges

**Moment 4 (Operations Notices)**
- Manual notice authoring (deprecation, fix, end-of-life)
- Notice template with: what changed, why, migration path, deadline, proof/reason link
- Simple archive indexing (YYYY-MM folders + category tags)
- Permanent URLs + redirect rules for deprecated surfaces
- CLI interface: `herald notice [author | list | archive]`
- Web notice board: Operations tab with category filter + search

**Shared Infrastructure**
- Unified Herald CLI dispatcher (all three Moments under one command)
- Unified Herald web surface (4 tabs: Pitch, Progress, Success, Operations)
- Evidence-linking framework (shared across Moment 3 & 4)
- Automation orchestration (webhooks, cron, gate-based triggers)

### Out of Scope

- **Moment 1 improvements** — Pitch/deck family is complete and separate
- **Video pipeline integration** — Moment 4 feeds narration to bmad-manticore, but video rendering is upstream
- **Marketing/external proclamation** — Moments 2–4 are internal visibility; Moment 1 handles external
- **Full-text search backend** — Simple date/category indexing for Moment 4 archive (full-text addable later)
- **Multi-region Herald surfaces** — Single unified Herald service assumed
- **Real-time collaboration** — No live sync between operators; pull model is explicit

---

## Requirements by Feature

### Feature Group 1: Herald CLI Architecture

**FR-1.1: Unified Command Dispatcher**
- Single entry point: `herald <subcommand> [--help | --json | --date-range <start>..<end>]`
- Subcommands: `progress`, `success`, `notice`
- Help text comprehensive and discoverable (`herald --help`, `herald <subcommand> --help`)
- Argument parsing handles: JSON output mode, date filtering, station/project filtering
- Extensible for future Moments (not hardcoded to 3)

**FR-1.2: Shared Argument Conventions**
- All subcommands support `--json` (machine-readable output)
- All subcommands support `--date-range YYYY-MM-DD..YYYY-MM-DD` or `--week recent|last-N` patterns
- All subcommands support station/project filtering where applicable
- Error messages consistent and actionable

**FR-1.3: CLI Authentication & Authorization**
- [ASSUMPTION: Herald CLI reads from Herald web service with implicit auth (same session)] Confirm with ops team
- Write operations (publish, author) require operator role confirmation
- Read operations (progress, list, archive) are public

---

### Feature Group 2: Herald Web Surface

**FR-2.1: Unified Navigation & Layout**
- Header nav with 4 tabs: **Pitch** (link to Moment 1 deck family), **Progress**, **Success**, **Operations**
- Unified color scheme and typography (Modernist design system from Moment 1)
- Sidebar: station filter (Warden, Atlas, Marshal, etc.), date range selector, search box
- Responsive (desktop, tablet, mobile)

**FR-2.2: Header & Footer**
- Header: Herald branding, Moment tab nav, user profile (if applicable)
- Footer: snapshot timestamp, last-updated indicators per section

**FR-2.3: Surface Integration**
- All three Moments visible in unified web surface (no separate apps or domains)
- Consistent pagination, sorting, and filtering across all tabs
- Cross-moment linking: Moment 3 success claim can link to Moment 4 notice (bidirectional)

---

### Feature Group 3: Moment 2 — Progress Visibility

**FR-3.1: Progress Data Model**
- **Record structure**: station name, date, shipped capabilities (list), cost (compute hours, token spend, wall-clock), unblock narrative (text)
- **Cost metrics**: derived from sprint-status ledger + bmad-loop journal timestamps
- **Unblock narrative**: operator-authored (auto-suggested from downstream PRs if available)

**FR-3.2: Progress Automation**
- **Trigger 1**: On-ship event (webhook from CI when PR merges to main)
  - Auto-creates progress record with cost + shipped capabilities extracted from journal
  - Operator authors unblock narrative (prompted)
- **Trigger 2**: Weekly cron Thursday 2300 UTC
  - Collects all shipping events from past week, aggregates into one record
  - Falls back to this when no on-ship events in the week

**FR-3.3: Progress CLI**
- `herald progress <station>` — show latest progress record for station (JSON or formatted)
- `herald progress <station> --update` — manually trigger progress update (operator only)
- `herald progress --list [--station <name> --week recent|<N>]` — list progress records by filter

**FR-3.4: Progress Web Tab**
- Latest progress per station (card view or table)
- Sidebar filters: station, date range
- Expandable detail: full cost breakdown, unblock narrative, shipped capabilities list
- Sorting: by date, by cost, by station

---

### Feature Group 4: Moment 3 — Success Proclamation

**FR-4.1: Success Claim Data Model**
- **Record structure**: project name, shipped date, thesis (one-liner, what we proved), evidence list (URL + type pairs: test_results | metrics | adoption | other)
- **Evidence types**: 
  - `test_results`: CI job URL (links to passing tests)
  - `metrics`: dashboard metric URL (proves real-world impact)
  - `adoption`: downstream PR URL (proves dependent projects use it)
  - `other`: freeform URL (any supporting proof)

**FR-4.2: Success Auto-Extract**
- **Trigger**: On PR close to main + passing gate-suite
  - Herald webhook receives: PR URL, commit SHA, test job URL, merged-at timestamp
  - Herald auto-extracts: project name (from PR title/labels), test results (CI job)
  - Herald queries dashboard for metrics (if configured) + searches for downstream adoption PRs
  - Generates structured claim with thesis-placeholder ("shipped on [date]")
- **Operator review**: Operator edits thesis (what we proved) and approves/publishes
  - CLI: `herald success review <claim-id>` (shows extracted claim + evidence)
  - Web: review form with editable thesis + evidence list
  - Operator clicks publish → claim becomes public + indexed

**FR-4.3: Success CLI**
- `herald success review <claim-id>` — show claim under review (JSON or formatted)
- `herald success publish <claim-id> --thesis "<one-liner>"` — publish with operator-authored thesis
- `herald success list [--status draft|published --date-range <start>..<end>]` — list claims by filter
- `herald success get <claim-id>` — retrieve published claim

**FR-4.4: Success Web Archive**
- Published claims listed chronologically (newest first)
- Claim card: project, thesis, shipped date, evidence badges (green=linked, yellow=pending)
- Click to expand: full evidence list with live links
- Sidebar filters: date range, evidence status
- Search box: project name, thesis keyword

**FR-4.5: Evidence Integrity**
- All evidence links validated at publish time (404 detection, redirect resolution)
- Dead links surface error before publish (operator fixes or removes)
- Evidence links re-validated weekly (stale links flagged in operator dashboard)

---

### Feature Group 5: Moment 4 — Operations Notices

**FR-5.1: Notice Data Model**
- **Record structure**: notice type (deprecation | fix | eol), component/feature name, what changed, why, migration path (if applicable), deadline (if applicable), reason link (URL to decision / ticket), notice URL (permanent archive path)
- **Versions**: notices support edit history (who, what, when); old versions remain in archive for audit

**FR-5.2: Notice Authoring**
- **CLI**: `herald notice author --type <deprecation|fix|eol> --component <name> --reason "<why>" --deadline <YYYY-MM-DD> [--migrate-to <new-component>]`
  - Interactive prompt for missing fields (what changed, why, migration path)
  - Outputs: draft notice (markdown format) + preview URL
  - Operator confirms + publishes (or exits to edit)
- **Web form** (optional, if UI bandwidth): author form with fields matching CLI interface

**FR-5.3: Notice Archive**
- **Storage**: notices organized by YYYY-MM folders + category tags (directory tree)
- **Indexing**: 
  - `/operations/notices/` lists categories (deprecation, fix, eol)
  - `/operations/notices/deprecation/` lists 2026-08, 2026-07, … (by month)
  - `/operations/notices/deprecation/2026-08/` lists individual notices
- **Permanent URLs**: `/operations/notices/deprecation/2026-08/component-name.md`
  - URL never changes; if component name changes, redirect rule created
- **Search**: Cmd+F in browser (manual search)

**FR-5.4: Notice Lifecycle**
- **Draft** → **Published** → **Closed** (after deadline or superseded)
- Draft: visible to authors only; editable
- Published: visible to all; read-only (new version can be created if needed)
- Closed: visible to all; archived; no further edits

**FR-5.5: Redirect Rules**
- When component name or URL structure changes, redirect rule auto-generated
- Operator confirms redirect → persisted
- Old URLs → new archive location (no 404s for historical notices)

**FR-5.6: Notice CLI**
- `herald notice author [...]` — create and publish notice
- `herald notice list [--type deprecation|fix|eol --month YYYY-MM]` — list by filter
- `herald notice archive` — show archive structure + counts
- `herald notice get <notice-url>` — retrieve notice by archive path

---

### Feature Group 6: Evidence-Linking Framework

**FR-6.1: Shared Evidence Link Protocol**
- All evidence links follow schema: `{ type: "test_results|metrics|adoption|other", url: "https://...", label: "CI job #123" }`
- Protocol supports: HTTP/HTTPS, link validation (404 detection), redirect resolution
- Links can be bidirectional: success claim links to notice, notice links back to success claim

**FR-6.2: Evidence Validation**
- Sync validation: test at publish time (404 → error)
- Async validation: weekly check of all links (stale links → operator alert)
- Redirect handling: follow redirects up to 3 hops; warn on redirect chains

**FR-6.3: Evidence Retrieval**
- Evidence links always retrievable by claim ID + link ID
- Evidence can be unlinked (operator removes broken link)
- Evidence link audit trail: who added, when, any edits

---

### Feature Group 7: Automation Orchestration

**FR-7.1: Webhook Integration**
- **Moment 2**: on-ship webhook (CI notifies Herald when PR merges to main)
  - Payload: PR URL, commit SHA, test job URL, merged-at timestamp, station tag (if available)
- **Moment 3**: on-PR-close webhook (CI notifies Herald when PR closes + gates pass)
  - Payload: PR URL, commit SHA, test job URL, close-at timestamp

**FR-7.2: Scheduler (Cron)**
- **Moment 2**: Thursday 2300 UTC weekly (fallback if no on-ship events)
  - Collects all shipping events from past week, generates aggregated record
- **Extensible**: Automation rules stored in Herald config (can be modified per Moment without code changes)

**FR-7.3: Gate-Based Triggers**
- **Moment 3**: auto-extract only if PR-close event INCLUDES "all gates passed" signal
  - No orphaned claims from incomplete shipping
- **Moment 4**: manual author only (no auto-trigger)

**FR-7.4: Operator Confirmation Gates**
- Moment 2 progress: operator authors unblock narrative (prompted after auto-extract)
- Moment 3 success: operator approves + authors thesis (required before publish)
- Moment 4 notice: operator authors full notice (required; no auto-generation)

---

## Non-Functional Requirements

**Performance**
- Herald CLI commands respond in <1s (local cache or fast API)
- Herald web tabs load in <2s (even with thousands of records)
- Progress widget (latest per station) renders in <500ms

**Availability**
- Herald web surface ≥99% uptime (SLA tbd with ops)
- Herald CLI works offline (cached data) with graceful degradation

**Security & Authorization**
- Write operations (publish, author) require operator role
- Read operations are public (no auth required for archive)
- Evidence links validated (no malicious URLs in proofs)
- Audit trail: all edits logged (who, what, when)

**Scalability**
- Support 100+ notices per month (Moment 4 archive)
- Support 1000+ success claims per year
- Support 10+ simultaneous operators (no lock contention)

**Data Integrity**
- No claims without evidence (enforced at publish)
- No dead links in evidence (validated at publish + weekly check)
- Archive URLs permanent (redirects for moved/renamed)
- Edit history preserved (no data loss on edit)

**Operator Experience**
- CLI help text clear and actionable
- Web forms simple (auto-filled where possible, dropdown defaults)
- Error messages name the problem + suggest fix
- Notifications/alerts for stale links, review-pending claims

---

## Success Metrics

### Adoption Metrics
- **Moment 2**: ≥80% of shipping events trigger progress update (automatic or manual)
- **Moment 3**: ≥90% of closed projects have published success claims within 7 days of close
- **Moment 4**: ≥70% of deprecations announced before deprecation date (not after)

### Quality Metrics
- **Evidence integrity**: ≤5% of evidence links are stale (404 or permanent redirect broken)
- **Claim completeness**: 100% of success claims have ≥1 evidence link (enforced)
- **Notice accuracy**: 0 operator-reported false/misleading notices

### Operational Metrics
- **CLI performance**: 95th percentile command latency <500ms (local cache)
- **Web performance**: 95th percentile tab load <2s (dashboard included)
- **Automation reliability**: ≥99% of automation triggers execute without error (retry logs)

### Engagement Metrics
- **Visibility**: ≥50% of factory participants read Herald web surface weekly
- **Participation**: ≥25% of operators author notices or approve claims (active, not passive)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Evidence links break (upstream URLs change/404) | Success claims lose proof | Weekly link validation; operator alert on stale link; allow unlinking |
| Operators forget to author unblock narratives (Moment 2) | Progress loses context | CLI prompts + web form; template suggestions from downstream PRs |
| Too many deprecation notices (Moment 4) overload readers | Operator fatigue; notices ignored | Simple archive indexing; category + date filters; encourage bundling related notices |
| Moment 3 auto-extract fails (CI doesn't send webhook) | Silent missing claims | Fallback: operator CLI publish; weekly audit report of unclaimed closes |
| Automation webhook floods Herald (runaway triggers) | Uptime risk | Rate limiting per CI job; queue + dedup; operator alert on anomalies |

---

## Dependencies & Blockers

### Internal Dependencies
- **Herald v0.1.0 CLI**: existing CLI structure extends (no rebuild)
- **Herald web prototype**: existing web surface integrates (add tabs, nav)
- **Sprint-status ledger**: data source for Moment 2 cost metrics (must be accessible)
- **bmad-loop journals**: data source for Moment 2 cost + unblock (must have read access)
- **CI webhook infrastructure**: must support webhook payloads (Moment 2 & 3 auto-triggers)
- **Dashboard infrastructure**: must expose metric URLs for Moment 3 evidence linking

### External Dependencies
- None identified (all infrastructure internal)

### Blockers
- None; all capabilities are foundational to Herald, not dependent on other projects

---

## Open Questions for Architecture Phase

1. **Evidence link storage**: Store links in database (queryable, editable) or as markdown frontmatter in archive files?
2. **Claim versioning**: Support multiple versions of a success claim (edited thesis), or immutable claims + new claims for edits?
3. **Notice edit history**: Preserve full edit history (who, what, when) or just current + audit log?
4. **Automation retry logic**: Exponential backoff for webhook retries, or fixed retry count? Max retry duration?
5. **Evidence extraction**: Query dashboard via API, or parse public metric URLs? Rate limits?

---

## Phasing & Sequencing

**Phase 1: Foundation (Stories 1–2)** — CLI architecture + web layout
- Enables all downstream work
- No visible features yet; foundation only
- 3–4 story-points

**Phase 2: Core Moments (Stories 3–5)** — Implement Moments 2, 3, 4 in parallel
- After Stories 1–2 ship
- 6–10 story-points (can parallelize)
- Each Moment can deploy independently

**Phase 3: Integration & Quality (Stories 6–7)** — Testing + documentation
- After Moments 2–5 feature-complete
- 2–4 story-points
- Ship as coordinated release (all three Moments + CLI + web together)

---

## Appendix: References

- **Spec source**: `../specs/spec-herald-moments-2-4/SPEC.md` (five-field kernel)
- **Epic breakdown**: `../specs/spec-herald-moments-2-4/epic-structure.md` (story dependencies, timeline)
- **Herald Pitch spec** (Moment 1): `../specs/spec-herald-pitch/SPEC.md` (design system, patterns)
- **Herald v0.1.0 CLI**: existing codebase (entry point for extension)

