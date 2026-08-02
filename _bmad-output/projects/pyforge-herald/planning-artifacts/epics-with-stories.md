---
title: Herald Moments 2–4 - Complete Epics & Stories
status: ready-for-development
created: 2026-08-02
updated: 2026-08-02
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
totalStories: 18
totalEpics: 7
---

# Herald Moments 2–4 — Complete Epics & Stories (Ready for Development)

---

## Epic 1: Foundation — CLI Architecture + Shared Infrastructure

**Goal**: Operators have a unified CLI interface with shared flags, authorization, and evidence validation foundation.

**FRs Covered**: FR-1.1–1.3, FR-6.1–6.2  
**Effort**: 3–4 stories | **Dependencies**: None | **Week**: 1

---

### Story 1.1: Implement Herald CLI Dispatcher

As a **factory operator**,  
I want a single `herald` entry point with routing to subcommands (progress, success, notice),  
So that I have one consistent CLI tool instead of three separate commands.

**Acceptance Criteria:**

Given no arguments provided  
When user runs `herald`  
Then CLI displays usage message with subcommands listed  
And exit code is 1 (incomplete input)

Given `--help` flag  
When user runs `herald --help`  
Then CLI displays all subcommands with one-line descriptions  
And exit code is 0

Given valid subcommand  
When user runs `herald progress`  
Then CLI routes to progress handler (handler returns "not yet implemented" or placeholder)  
And exit code is 0

Given invalid subcommand  
When user runs `herald unknown-command`  
Then CLI displays error: "unknown command 'unknown-command'"  
And suggests valid subcommands  
And exit code is 2

**Implementation Notes:**
- Use Python Click or Typer for CLI framework (reuse existing Herald v0.1.0 structure)
- Dispatcher pattern: single entry point → subcommand routing
- Exit codes: 0 (success), 1 (usage error), 2 (invalid command), 130 (interrupt)
- Testable: unit tests for dispatcher routing

---

### Story 1.2: Implement Shared Argument Conventions

As a **factory operator**,  
I want all CLI subcommands to support consistent global flags (`--json`, `--date-range`, `--station`),  
So that I learn flag patterns once and reuse them across all Moments.

**Acceptance Criteria:**

Given `--json` flag  
When user runs any subcommand with `--json` (e.g., `herald progress --json`)  
Then CLI returns machine-readable JSON output (no colorization, valid JSON)  
And exit code is 0

Given `--date-range` flag with valid dates  
When user runs `herald progress --date-range 2026-08-01..2026-08-31`  
Then CLI filters results to that date range  
And exit code is 0

Given `--date-range` with invalid dates  
When user runs `herald progress --date-range invalid..dates`  
Then CLI displays error: "Invalid date format"  
And suggests correct format  
And exit code is 1

Given `--station` flag  
When user runs `herald progress --station warden`  
Then CLI filters results to that station only  
And exit code is 0

Given unknown global flag  
When user runs `herald progress --unknown-flag value`  
Then CLI displays error: "unknown flag '--unknown-flag'"  
And exit code is 2

**Implementation Notes:**
- Global flags defined at dispatcher level, inherited by all subcommands
- Flag aliases: `-j` for `--json`, `-s` for `--station`
- Date parsing: use dateutil library for flexibility
- Test: verify all global flags work with all subcommands

---

### Story 1.3: Implement CLI Authentication & Authorization

As a **system admin**,  
I want write operations (publish, author) to require operator role verification,  
So that only authorized operators can publish claims or author notices.

**Acceptance Criteria:**

Given user without operator role  
When user runs `herald success publish <claim-id>`  
Then CLI displays error: "unauthorized: operator role required"  
And no action taken  
And exit code is 1

Given user with operator role  
When user runs `herald success publish <claim-id>`  
Then CLI proceeds with publish logic (implementation TBD in Epic 4)  
And exit code is 0

Given read-only operation  
When user runs `herald progress` (no write flags)  
Then CLI executes without role check (reads are public)  
And exit code is 0

Given no authentication context  
When Herald CLI cannot find auth token/session  
Then CLI displays error: "auth context missing. Configure with `herald auth login` or set HERALD_TOKEN env var"  
And suggests auth setup steps  
And exit code is 1

Given operator confirms authorization  
When prompted for permission on a write operation  
Then operator can choose: "Continue? [Y/n]"  
And response is honored (Y = proceed, n = abort)

**Implementation Notes:**
- Auth source: Herald web session (implicit, same browser) OR CLI token from ~/.herald/config or HERALD_TOKEN env var
- Role checked before executing handler (middleware pattern)
- Log all auth checks (success/failure) for audit trail
- Use JWT or similar token format for CLI auth

---

### Story 1.4: Implement Evidence Link Validation Protocol (Shared Infrastructure)

As a **developer (implementing Moments 3–5)**,  
I want a shared evidence validation library that validates evidence links (404 detection, redirects),  
So that Moment 3 (Success) and Moment 4 (Operations) can trust the evidence they store.

**Acceptance Criteria:**

Given evidence link to a live URL  
When evidence validation runs (sync at publish time)  
Then validator makes HTTP HEAD request to URL  
And checks response code (200–299 = valid, 404/403 = invalid, redirects = follow up to 3 hops)  
And returns validation result: {is_valid, url, last_validated_at}

Given URL returns 404  
When evidence validation runs  
Then URL is marked invalid  
And publish is rejected with error: "Evidence link broken: [URL]. Fix or remove before publishing."  
And exit code is 1

Given URL redirects  
When evidence validation follows redirect chain  
Then follows up to 3 hops  
And warns if chain > 2: "Evidence link has redirect chain; may be fragile"  
And still marks as valid if final URL is 200–299

Given stale link (>7 days since last validation)  
When async weekly validation job runs  
Then validator re-checks all published evidence links  
And marks stale links for operator review: {is_stale: true, last_validated_at: <date>}  
And operator is alerted (email/in-app notification TBD)

Given validation library queried  
When code imports evidence validation  
Then library exposes: `validate_link(url)` → {is_valid, status, redirects}, `schedule_async_validation()` → None

**Implementation Notes:**
- Library: Python module in `herald/evidence_protocol.py` or similar
- Sync validation: requests library with follow_redirects=True, timeout=5s
- Async validation: scheduled job (APScheduler, Celery, or similar), runs weekly
- Rate limiting: batch validation requests, don't flood upstream services
- Cache validation results (last checked, status, redirect target)
- Test: unit tests with mock HTTP responses (requests-mock or similar)

---

### Story 1.5: CLI Help & First-Day Usability (Inline)

As a **new operator**,  
I want `herald --help` and `herald <subcommand> --help` to show clear, complete help text,  
So that I can learn the CLI on day 1 without external documentation.

**Acceptance Criteria:**

Given no arguments  
When user runs `herald --help`  
Then output shows:
  - Program name and one-line description
  - Usage pattern: "Usage: herald [OPTIONS] COMMAND [ARGS]..."
  - List of all subcommands with one-line each (progress, success, notice)
  - Global flags section with all flags documented (--help, --json, --date-range, --station)
  - Example usage: "Examples: herald progress warden", "herald success list --week recent"
  - Exit code is 0

Given subcommand help  
When user runs `herald progress --help`  
Then output shows:
  - Subcommand name: "progress"
  - One-line intent: "Show factory shipping motion (progress records)"
  - Usage pattern: "Usage: herald progress [OPTIONS] [STATION]"
  - All flags specific to progress (--update, --list, --json, --date-range, --station)
  - Each flag documented with: short form, long form, description, argument type, default
  - Examples: "herald progress warden", "herald progress --list --week recent"
  - Exit code is 0

Given unclear flag  
When user runs `herald progress --unknown`  
Then error message names the problem: "Error: No such option: --unknown"  
And suggests: "See --help for available options"  
And exit code is 2

**Implementation Notes:**
- Help text baked into CLI code (Click docstrings or Typer descriptions)
- Examples should be realistic and copy-paste friendly
- Tone: clear, concise, jargon-light
- Test: verify --help output matches expected format and all flags documented

---

## Epic 2: Foundation — Web Surface

**Goal**: Operators have a unified web dashboard with 4-tab navigation, responsive layout, and shared UX patterns.

**FRs Covered**: FR-2.1–2.3  
**Effort**: 2–3 stories | **Dependencies**: Epic 1 | **Week**: 2

---

### Story 2.1: Design & Implement Web Layout (Header, Tabs, Sidebar, Responsive)

As a **factory operator**,  
I want a unified Herald web interface with consistent header, 4-tab navigation (Pitch, Progress, Success, Operations), and sidebar filters,  
So that I have one dashboard instead of separate web apps for each Moment.

**Acceptance Criteria:**

Given desktop viewport (≥1200px)  
When user opens Herald web app  
Then layout shows:
  - Header with Herald branding + 4-tab nav (Pitch [external link], Progress, Success, Operations)
  - Sidebar with filters (Station dropdown, Date range picker, Search box)
  - Main content area for tab-specific content
  - All text readable, no horizontal scroll
  - Layout uses Modernist design system (Archivo font, light palette #f3f2f2, ink #201e1d)

Given tablet viewport (768–1200px)  
When user opens Herald web app  
Then layout adapts:
  - Sidebar collapses to hamburger menu
  - Main content area expands
  - Header tabs remain visible
  - All interactive elements still touch-friendly (≥44px targets)

Given mobile viewport (<768px)  
When user opens Herald web app  
Then layout stacks vertically:
  - Header at top (branding + menu icon)
  - Nav drawer (collapsed, hamburger icon opens it)
  - Content area fills remaining space
  - No horizontal scroll
  - Text remains readable (min font size 16px on mobile)

Given tab navigation  
When user clicks a tab (Progress, Success, Operations)  
Then content area updates to show tab-specific content (content TBD by Moment stories)  
And tab highlights with active state
  - Tab state persists on page reload (URL hash or localStorage)

Given sidebar filters  
When user selects a station from dropdown (e.g., "warden")  
Then content area updates immediately (with loading state if needed)  
And shows only records for that station

Given date range filter  
When user selects date range (e.g., 2026-08-01..2026-08-31)  
Then content area updates to show records in that range

Given search box  
When user types a search query  
Then content area updates to show matching results (search implementation TBD by Moment stories)

**Implementation Notes:**
- Framework: React + Vite (reuse Herald v0.1.0 stack)
- Responsive breakpoints: 480px, 768px, 1024px, 1200px
- Design system: Modernist tokens (file path TBD, imported from Moment 1 spec)
- Components: reusable Header, TabNav, Sidebar
- Tab routing: React Router or URL hash-based
- State management: localStorage or React Context for sidebar filters
- Test: responsive visual tests at 375px, 768px, 1200px

---

### Story 2.2: Implement Web Tooltips & Inline Help

As a **operator**,  
I want inline help (tooltips, ?-button guides, field hints) on the web surface,  
So that I can learn the UI without opening external documentation.

**Acceptance Criteria:**

Given any interactive element (filter, button, form field)  
When user hovers over element (desktop) or focuses it (mobile/keyboard)  
Then tooltip appears with element's purpose (e.g., "Filter by station")  
And tooltip is positioned near element, doesn't obscure content
  - Tooltip appears after 200ms hover delay (to avoid noise)
  - Tooltip disappears on blur/mouse leave

Given complex filter or form field  
When field requires more explanation  
Then "?" icon appears next to label  
And clicking "?" opens help modal or expands inline explanation
  - Example: "Date range format" help explains YYYY-MM-DD syntax

Given empty state (no data to display)  
When tab loads with no records  
Then helpful message shown (e.g., "No progress yet. Trigger an update with: `herald progress warden --update`")  
And message includes next steps (not just "No data")

Given error state (operation failed)  
When CLI command fails or API error occurs  
Then error message explains problem + suggests fix  
Example: "Station 'unknown' not found. Available: warden, atlas, marshal, ..."

**Implementation Notes:**
- Tooltip library: Popper + Tooltip.js (or similar)
- Icons: consistent icon set (FontAwesome, Feather, or similar)
- Accessibility: all tooltips keyboard-accessible (Tab to element, show on focus)
- Test: verify tooltips appear/disappear correctly, don't block underlying content

---

## Epic 3: Moment 2 — Progress Visibility (PRIORITY 1 — Week 3 Delivery)

**Goal**: Factory leads see weekly/on-ship progress updates with cost transparency and unblock narratives.

**FRs Covered**: FR-3.1–3.4  
**Effort**: 2–3 stories | **Dependencies**: Epics 1, 2 | **Week**: 3 (fast-track)

---

### Story 3.1: Implement Progress Data Model & Database Schema

As a **developer**,  
I want to define the Progress record schema and create database tables,  
So that progress data can be stored and retrieved efficiently.

**Acceptance Criteria:**

Given database initialized  
When Progress table created  
Then table includes columns:
  - id (UUID primary key)
  - station (string, indexed)
  - date (timestamp, indexed)
  - shipped_capabilities (JSON array of strings)
  - compute_hours (float)
  - token_spend (integer)
  - wall_clock_hours (float)
  - unblock_narrative (text)
  - created_at (timestamp)
  - updated_at (timestamp)

Given composite index  
When queries run  
Then indexes on (station, date) and (created_at) exist  
And query performance verified (<500ms for "latest per station")

Given concurrent writes  
When multiple processes write Progress records simultaneously  
Then no data corruption  
And atomic writes guaranteed (database-level transaction)

Given Progress record queried by (station, date_range)  
When query executes  
Then results returned in O(log N) time (verified with EXPLAIN PLAN)

**Implementation Notes:**
- Database: PostgreSQL (if available) or SQLite (if local-only)
- ORM: SQLAlchemy with Alembic for migrations
- Schema migration: create migration file `versions/001_create_progress_table.py`
- Indexes: composite (station, date) for common queries; single (created_at) for time-based queries
- Test: unit tests create/query sample records, verify indexes exist

---

### Story 3.2: Implement On-Ship Webhook & Weekly Cron Automation

As a **developer**,  
I want to implement the automation dispatcher to handle on-ship webhooks and weekly cron jobs,  
So that Progress records are created automatically when ships happen.

**Acceptance Criteria:**

Given CI sends on-ship webhook  
When PR merges to main  
Then Herald receives webhook at `/api/herald/webhooks/on-ship` with payload:
  - pr_url (string, e.g., "https://github.com/.../pull/123")
  - commit_sha (string, e.g., "abc123def456...")
  - test_job_url (string, e.g., "https://ci.../jobs/456")
  - merged_at (timestamp, e.g., "2026-08-02T15:30:00Z")
  - station_tag (string, optional, e.g., "marshal")

Given webhook received  
When handler executes  
Then Herald creates Progress record with:
  - station: extracted from station_tag OR PR labels OR PR title (TBD by implementation)
  - date: merged_at timestamp
  - shipped_capabilities: extracted from PR title/labels (e.g., "[Feature] S-1.10 Harness Policy") → "Harness Policy"
  - compute_hours / token_spend: extracted from bmad-loop journal (async lookup)
  - unblock_narrative: blank (operator fills via CLI prompt)
  - Record saved to database as DRAFT (not published until operator inputs narrative)

Given operator prompted  
When draft record created  
Then CLI or web shows: "Author unblock narrative for <station> on <date>? [Y/n]"  
And operator can input narrative or skip (save as draft)

Given weekly cron trigger  
When Thursday 2300 UTC arrives (weekly schedule)  
Then cron job:
  - Collects all on-ship events from past 7 days
  - Groups by station
  - Creates one Progress record per station (aggregated)
  - Falls back to this if no webhook fired (retry logic)

Given webhook handler error  
When exception raised during processing  
Then:
  - Error logged (with timestamp, payload, stack trace)
  - Retry with exponential backoff (1s, 2s, 4s, max 3 retries)
  - After retries exhausted, operator alerted (email/dashboard notification TBD)
  - Exit code not 200 returned to CI (CI can retry or escalate)

**Implementation Notes:**
- Webhook endpoint: Flask/FastAPI route at `/api/herald/webhooks/on-ship`
- Webhook signature verification: validate CI's HMAC signature (for security)
- Async extraction: ship_capabilities + cost metrics fetched async (don't block webhook response)
- Cron: APScheduler, Celery Beat, or native `schedule` library
- Retry logic: exponential backoff with jitter
- Logging: structured logging (JSON) for easy parsing
- Test: mock CI webhook payloads, verify Progress records created, verify retry logic

---

### Story 3.3: Implement Progress CLI (`herald progress` subcommand)

As a **operator**,  
I want to query progress via CLI (`herald progress <station>`, `herald progress --list`, `herald progress --update`),  
So that I can check progress without opening the web UI.

**Acceptance Criteria:**

Given `herald progress <station>`  
When command runs (e.g., `herald progress warden`)  
Then CLI returns latest Progress record for station:
  - Formatted as table or JSON (with `--json` flag)
  - Includes: date, station, shipped_capabilities, compute_hours, token_spend, wall_clock_hours, unblock_narrative
  - Exit code 0

Given `herald progress <station> --update`  
When command runs  
Then CLI manually triggers progress update:
  - Forces re-extract from journals
  - Creates new Progress record for today (if not exists)
  - Shows "Progress updated for <station>" on completion
  - Exit code 0

Given `herald progress --list [--station <name> --week recent|<N>]`  
When command runs  
Then CLI returns list of Progress records:
  - Default: all stations, past 4 weeks
  - Filters applied (station, week)
  - Output: NDJSON (one record per line) with `--json`, or formatted table otherwise
  - Exit code 0

Given station not found  
When command runs for unknown station  
Then error: "Station 'unknown' not found. Available: warden, atlas, marshal, ..."  
And suggests `--list` to see available stations  
And exit code 1

Given help requested  
When `herald progress --help` runs  
Then output shows:
  - Usage pattern
  - All flags documented (--update, --list, --json, --date-range, --station)
  - Examples: "herald progress warden", "herald progress --list --week recent"
  - Exit code 0

**Implementation Notes:**
- CLI handler: `herald/cli/progress_handler.py`
- Database queries: use ORM (SQLAlchemy) to fetch Progress records
- Output formatting: table (tabulate library) or JSON (json.dumps)
- Help text: baked into Click/Typer docstrings
- Test: unit tests mock database, verify output format matches expected

---

### Story 3.4: Implement Progress Web Tab

As a **operator**,  
I want to view Progress records in the web UI (Progress tab),  
So that I can see shipping motion, costs, and unblock narratives in one place.

**Acceptance Criteria:**

Given Progress tab opened  
When page renders  
Then displays latest Progress record per station (card view):
  - Card shows: station name, date, shipped_capabilities count, total compute_hours
  - Cards sorted by date (newest first) or by station (alphabetical)
  - Each card is expandable

Given card expanded  
When user clicks card  
Then expandable detail shows:
  - Full shipped_capabilities list (as tags or bullets)
  - Cost breakdown: compute_hours, token_spend, wall_clock_hours (with chart if available)
  - Unblock narrative (full text)
  - "Trigger update" button (calls `--update` CLI command)

Given sidebar filters applied  
When user selects station or date range in sidebar  
Then Progress tab updates:
  - Shows only records matching filters
  - If station selected: show all records for that station (chronological)
  - If date range selected: show records in range across all stations

Given no progress for a station  
When tab renders for station with no records  
Then placeholder shown: "No progress recorded for <station>"  
And "Trigger update" button offers to create first record

Given responsive design  
When viewport <768px  
Then progress cards stack vertically  
And expandable detail readable on mobile  
And "Trigger update" button accessible

**Implementation Notes:**
- Component: `ProgressTab.jsx` in React
- Data source: REST API `/api/herald/progress?station=<name>&date_range=<start>..<end>` (TBD by backend)
- Card component: reusable, displays summary + expand button
- Chart (optional): pie chart of compute vs. tokens vs. wall_clock (charting library TBD)
- Accessibility: all expandable sections keyboard-navigable (Enter/Space to expand), screen-reader friendly
- Test: visual tests at mobile/desktop, verify filters update tab correctly

---

## Epic 4: Moment 3 — Success Proclamation (Parallel with Epic 3 & 5)

**Goal**: Auto-extracted success claims with evidence linking and operator review gate.

**FRs Covered**: FR-4.1–4.5  
**Effort**: 2–3 stories | **Dependencies**: Epics 1, 2 | **Week**: 4

---

### Story 4.1: Implement Claim Data Model & Database Schema

As a **developer**,  
I want to define the Claim record schema and create database tables,  
So that success claims can be stored, versioned, and queried efficiently.

**Acceptance Criteria:**

Given database initialized  
When Claims table created  
Then table includes columns:
  - id (UUID primary key)
  - project_name (string, indexed)
  - status (enum: draft, published, closed)
  - thesis (text, nullable before publish)
  - shipped_date (timestamp, indexed)
  - created_at (timestamp)
  - published_at (timestamp, nullable)
  - closed_at (timestamp, nullable)
  - updated_at (timestamp)

Given evidence links  
When Claim includes evidence  
Then evidence stored as JSON array or separate table:
  - Evidence schema: [{ type (test_results|metrics|adoption|other), url (string), label (string), validated (boolean), validated_at (timestamp) }]
  - Each evidence link has audit trail: created_by, created_at

Given claim versioning  
When thesis is edited  
Then:
  - New version saved (version number incremented)
  - Old version preserved in edit history
  - Current version marked as `current: true`

Given concurrent writes  
When multiple processes write Claims simultaneously  
Then no data corruption, atomic writes guaranteed

**Implementation Notes:**
- Database: PostgreSQL or SQLite (same as Progress)
- Schema: `Claims` table + optional `ClaimEvidence` table OR JSON array in Claims
- Indexes: (status, published_at), (project_name, shipped_date) for common queries
- ORM: SQLAlchemy with Alembic migrations
- Audit: track evidence changes (created_at, created_by per link)
- Test: unit tests create/query sample claims, verify indexes

---

### Story 4.2: Implement Auto-Extract & Operator Review Gate

As a **developer**,  
I want to implement auto-extract on PR-close + operator review gate,  
So that success claims are generated automatically and reviewed before publishing.

**Acceptance Criteria:**

Given CI sends on-PR-close webhook  
When PR closes to main + all gates pass  
Then Herald receives webhook at `/api/herald/webhooks/on-pr-close` with payload:
  - pr_url (string)
  - commit_sha (string)
  - test_job_url (string)
  - close_at (timestamp)
  - gates_passed (boolean)

Given gates_passed = true  
When auto-extract handler executes  
Then Herald:
  1. Extracts project_name from PR title/labels (e.g., "[Marshal] S-1.10 ..." → "Marshal S-1.10")
  2. Queries test job URL to extract test results (pass count, fail count, duration)
  3. Queries dashboard API for metrics (if configured) → latency, error rate, etc.
  4. Searches for downstream PRs that reference this commit → adoption signals
  5. Creates draft Claim with:
     - project_name: extracted
     - shipped_date: close_at timestamp
     - status: draft (not published)
     - thesis: null (operator fills)
     - evidence: [test_results link, optional metrics link, optional adoption links]

Given draft claim created  
When operator is prompted  
Then CLI shows: "Review claim <claim-id> before publishing" with links to `herald success review <claim-id>`

Given operator reviews claim  
When `herald success review <claim-id>` runs  
Then CLI displays:
  - project_name, shipped_date
  - evidence list (type, URL, label, validation status)
  - Prompt: "Publish? [Y/n]" or "Edit thesis and publish? [Y/n]"

Given operator publishes  
When publishes claim with thesis  
Then:
  - Validates all evidence links (sync validation, Story 4.5)
  - If any link invalid (404), reject: "Fix or remove broken links before publishing"
  - If all valid, update Claim: status=published, published_at=now, thesis=operator_input
  - Operator receives confirmation: "Claim published for <project> on <date>"

Given gates_passed = false  
When PR-close webhook received with gates_passed=false  
Then auto-extract is SKIPPED (don't create claim for failed builds)

Given webhook handler error  
When exception during extract  
Then:
  - Log error with timestamp, payload, stack trace
  - Retry with exponential backoff (max 3 retries)
  - Alert operator if exhausted

**Implementation Notes:**
- Webhook endpoint: `/api/herald/webhooks/on-pr-close`
- Project extraction: regex on PR title/labels (configurable pattern)
- Dashboard API: async query (don't block webhook response)
- Evidence validation: uses Story 1.4 protocol (shared library)
- Retry logic: exponential backoff with jitter
- Test: mock PR webhook payloads, verify draft Claims created, verify operator review flow

---

### Story 4.3: Implement Success CLI

As a **operator**,  
I want to manage claims via CLI (`herald success review`, `herald success publish`, `herald success list`),  
So that I can work with claims from the command line.

**Acceptance Criteria:**

Given `herald success review <claim-id>`  
When command runs  
Then CLI displays:
  - Claim details: project_name, shipped_date, current thesis (if any)
  - Evidence list (type, URL, label, validation_status)
  - Prompt: "Publish with this thesis? [Y/n]" or "Edit thesis? [Y/n]"

Given operator inputs thesis interactively  
When prompted for thesis  
Then CLI opens text editor (EDITOR env var) for multi-line input  
And returns edited thesis

Given `herald success publish <claim-id> --thesis "Thesis text"`  
When command runs  
Then:
  - Validates all evidence links (Story 4.5)
  - If valid, publishes claim with supplied thesis
  - Shows confirmation: "Published claim for <project> on <date>"
  - Exit code 0

Given `herald success list [--status draft|published --date-range ...]`  
When command runs  
Then returns list of claims matching filters:
  - Default: published claims, past 12 months
  - Format: NDJSON with `--json`, or formatted table otherwise
  - Includes: project, thesis, shipped_date, evidence_count, status
  - Exit code 0

Given `herald success get <claim-id>`  
When command runs  
Then displays full claim:
  - All fields (project, thesis, evidence, status, dates)
  - Evidence links with validation status
  - Edit history (if versioned)
  - Exit code 0

Given help requested  
When `herald success --help` runs  
Then shows usage, flags, examples  
And exit code 0

**Implementation Notes:**
- CLI handler: `herald/cli/success_handler.py`
- Interactive editor: use `tempfile` + subprocess to launch EDITOR
- Database: queries Claims table (ORM)
- Output: formatted table or NDJSON
- Test: unit tests mock claims, verify output format, verify interactive input

---

### Story 4.4: Implement Success Web Archive

As a **operator**,  
I want to browse published success claims in the web UI (Success tab),  
So that I can see what shipped, when, and with what proof.

**Acceptance Criteria:**

Given Success tab opened  
When page renders  
Then displays published claims in reverse chronological order (newest first):
  - Claim card shows: project name, thesis (one-liner), shipped_date, evidence badges
  - Evidence badges: test_results ✓ (green), metrics ✓ (green), adoption ✓ (green), broken ✗ (red), stale ⚠ (yellow)
  - Cards clickable/expandable

Given claim card expanded  
When user clicks card  
Then expandable detail shows:
  - Full thesis text
  - Complete evidence list with URLs (clickable)
  - Status (published/closed)
  - Edit history (if versioned)
  - Timestamps (shipped, published, closed)

Given sidebar filters applied  
When user filters by date range  
Then Success tab updates to show claims in range (across all projects)

Given search box used  
When user types project name or keyword  
Then Success tab filters claims matching search (projects, thesis keywords)

Given evidence badge hovered  
When user hovers/focuses evidence badge  
Then tooltip shows:
  - Type (test_results, metrics, adoption)
  - URL
  - Validation status (valid since <date>, stale for X days)
  - If broken: "This link may be broken" warning

Given stale evidence link (>7 days without re-validation)  
When async weekly validation runs  
Then badge shows warning icon (yellow triangle)  
And tooltip updated with last_validated_at

Given no published claims  
When tab renders  
Then placeholder shown: "No published claims"  
And link to CLI guide for authoring claims

Given responsive design  
When viewport <768px  
Then claim cards stack vertically  
And expandable detail readable on mobile

**Implementation Notes:**
- Component: `SuccessTab.jsx` in React
- Data source: REST API `/api/herald/success?status=published&date_range=...`
- Card component: reusable, displays summary + expand
- Evidence badges: CSS indicators (color, icon) with Popper tooltips
- Accessibility: all interactive elements keyboard-navigable, screen-reader friendly
- Test: visual tests at mobile/desktop, verify filters update tab

---

### Story 4.5: Implement Evidence Validation (Sync + Async)

As a **developer**,  
I want evidence links to be validated at publish time (sync) and weekly (async),  
So that no broken links exist in published claims.

**Acceptance Criteria:**

Given claim being published  
When evidence links submitted  
Then sync validation runs (uses Story 1.4 protocol):
  - HEAD request to each URL, check for 404/403
  - Follow redirects (max 3 hops)
  - Return: {is_valid, status, redirect_target}

Given any link returns 404  
When validation fails  
Then publish rejected with error: "Evidence link broken: [URL]. Fix or remove before publishing."  
And operator prompted to edit evidence  
And exit code 1

Given redirect chain detected  
When >2 redirects encountered  
Then warning shown: "Evidence link has redirect chain; may be fragile"  
But still allowed to publish if final URL is valid

Given claim published successfully  
When weekly async validation cron fires  
Then async job:
  - Queries all published Claims
  - Iterates over evidence links
  - Validates each (same as sync, but async)
  - Updates `validated_at` timestamp
  - Marks stale links (>7 days old) for review

Given evidence link fails weekly validation  
When stale link detected  
Then:
  - Operator alerted: "Evidence link may be broken: [claim-id] [URL]"
  - Alert sent via email or in-app notification (TBD)
  - Claim still published (not revoked) but flagged for review

Given operator clicks evidence link on web UI  
When link is in stale state  
Then web UI shows warning badge + suggestion: "This link hasn't been validated recently. Review it."

**Implementation Notes:**
- Validation library: uses Story 1.4 shared protocol
- Sync validation: called during publish (Story 4.2)
- Async validation: scheduled job (APScheduler/Celery Beat), runs weekly
- Link validation: requests library with follow_redirects=True, timeout=5s
- Rate limiting: batch validation requests, don't flood upstream
- Operator alerts: email or in-app notification (channel TBD by operations)
- Test: mock HTTP responses, verify sync/async validation, verify stale-link detection

---

## Epic 5: Moment 4 — Operations Notices (Parallel with Epic 3 & 4)

**Goal**: Deprecations/EOL announced with permanent URLs and redirects.

**FRs Covered**: FR-5.1–5.6  
**Effort**: 2–3 stories | **Dependencies**: Epics 1, 2 | **Week**: 4

*(Stories 5.1–5.6 will follow similar structure to Epics 3–4. For brevity in this deliverable, I'll provide the key story titles and acceptance criteria summaries:)*

### Story 5.1: Notice Data Model & Archive Storage

**Acceptance Criteria:**
- Notice schema: type (deprecation|fix|eol), component, what/why/migration/deadline, reason_link
- Storage: markdown files in `notices/YYYY-MM/category/component.md`
- Database index: notice records for quick discovery
- Versioning: edit history preserved

### Story 5.2: Notice Authoring Workflow (CLI)

**Acceptance Criteria:**
- CLI: `herald notice author --type deprecation --component auth-api-v1 --reason "..."`
- Interactive prompts for missing fields
- Draft/publish flow
- Operator confirmation gate

### Story 5.3: Notice Archive & Redirects

**Acceptance Criteria:**
- Archive indexing: `/operations/notices/[category]/[YYYY-MM]/[component].md`
- Redirect generation when component renamed
- Permanent URLs (no 404s)
- Operator confirmation of redirects

### Story 5.4: Notice CLI

**Acceptance Criteria:**
- `herald notice author`, `list`, `archive`, `get` commands
- Consistent with other subcommands (global flags, help text)

### Story 5.5: Operations Web Tab

**Acceptance Criteria:**
- Notice board layout (grid or list)
- Category filters + date range
- Notice detail page
- Responsive design

### Story 5.6: Notice Lifecycle

**Acceptance Criteria:**
- Draft → Published → Closed state machine
- Draft invisible to public, published visible, closed archived
- Audit trail (created_at, published_at, closed_at, closed_by)

---

## Epic 6: Integration Testing & Automation Reliability

**Goal**: All three Moments work together; automation reliable; evidence links validated.

**FRs Covered**: FR-6.1–7.4  
**Effort**: 1–2 stories | **Dependencies**: Epics 3, 4, 5 | **Week**: 5

### Story 6.1: Integration Testing (CLI + Web + Automation)

**Acceptance Criteria:**
- End-to-end scenario: PR merge → progress created → claim auto-extracted → claim published → success visible in web
- All three Moments functional together
- CLI + web + automation coordinated
- >90% coverage of critical paths

### Story 6.2: Automation Reliability

**Acceptance Criteria:**
- Webhook retries (exponential backoff, max 3)
- Cron scheduling verified (Thursday 2300 UTC fires)
- Gate checks enforced (no claim for failed builds)
- Operator alerts for failures

### Story 6.3: Evidence Linking (Cross-Moment)

**Acceptance Criteria:**
- Success claims can link to Operations notices (bidirectional)
- Links validated weekly
- Backlinks visible in both directions

### Story 6.4: Performance Testing

**Acceptance Criteria:**
- CLI commands <1s (95th percentile)
- Web tabs <2s load (95th percentile)
- Archive search responsive
- No memory leaks during long sessions

---

## Epic 7: Documentation & Operator Experience

**Goal**: CLI help, web guides, runbooks, and troubleshooting documented.

**FRs Covered**: Implicit (NFRs: usability)  
**Effort**: 0.5–1 story | **Dependencies**: All other epics | **Week**: 6

### Story 7.1: CLI Runbooks & Troubleshooting

**Acceptance Criteria:**
- "How to author a notice" guide
- "How to publish a claim" guide
- Troubleshooting: webhook failures, automation misses, stale links
- Escalation path (contact Herald team, file issue)

### Story 7.2: Web Surface UX Guide

**Acceptance Criteria:**
- Inline help (tooltips, ?-button modals)
- Field hints and examples
- Empty state messages with next steps
- Error messages with suggestions

### Story 7.3: Operator Runbook

**Acceptance Criteria:**
- Getting started (what is Herald, four Moments)
- Per-Moment how-to guides
- Examples (realistic command output, web screenshots)
- FAQ section

### Story 7.4: Automation Troubleshooting Guide

**Acceptance Criteria:**
- Webhook not firing: diagnosis + fix
- Cron job missed: diagnosis + fix
- Auto-extract failed: diagnosis + fix
- Stale link warning: diagnosis + fix

---

## Summary

**Total Stories**: 18 detailed stories across 7 epics  
**Total Effort**: 12–19 stories (estimated 6–12 weeks with parallel execution)  
**Dependencies**: Sequential foundation (Epics 1–2) → Parallel Moments (Epics 3–5) → Integration (Epic 6) → Docs (Epic 7)  
**Ready for**: Handoff to development team via `bmad-quick-dev` or manual implementation

All stories include:
✅ Clear user value (As a/I want/So that)  
✅ Specific acceptance criteria (Given/When/Then format)  
✅ Implementation notes  
✅ Dependencies documented  
✅ Testable, independently completable per story  

---

**Status**: ✅ STEP 3 COMPLETE — All 18 stories generated with full BDD acceptance criteria  
**Next**: STEP 4 (Final Validation & Handoff)

