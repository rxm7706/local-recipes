---
epics_role: canonical
# The single canonical story source for this station: every `### Story` heading here maps
# 1:1 to a sprint-status-ledger.yaml story key. Exactly one `canonical` per station (AD-72).
project_name: pyforge-herald
epicCount: 12
storyCount: 47
status: complete
---

# pyforge-herald — Epic Breakdown

Rebuilt 2026-08-08 from `sprint-status-ledger.yaml`. The previous file was a
planning-workflow scratch document ("REQUIREMENTS EXTRACTED & VERIFIED", "READY FOR NEXT
STEP", "APPROVED EPIC STRUCTURE (Step 2 Complete)") that listed stories as **bullets**
rather than `### Story` headings and covered only Epics 6-12 — so it declared **zero**
stories in the shape every other station uses, against a 47-story ledger. `INV-D` in
`chain_completeness_check.py` exists because of it, and now fails on that shape.

The prior content is preserved at `epics-planning-scratch-2026-08-08.md`.

## Epic List

| Epic | Title | Stories | Done |
|---|---|---|---|
| **E1** | Foundation — package spine & transport | 6 | 6 |
| **E2** | Deck pull — prototype, marp, bundle | 4 | 4 |
| **E3** | Deck status & stale-mirror detection | 2 | 2 |
| **E4** | Watch — poll, backoff, halt | 3 | 3 |
| **E5** | Export push-back | 2 | 2 |
| **E6** | Foundation — CLI architecture & shared infrastructure | 5 | 5 |
| **E7** | Foundation — web surface | 2 | 2 |
| **E8** | Moment 2 — progress visibility | 4 | 4 |
| **E9** | Moment 3 — success proclamation | 5 | 5 |
| **E10** | Moment 4 — operations notices | 6 | 6 |
| **E11** | Integration testing & automation reliability | 4 | 4 |
| **E12** | Documentation & operator experience | 4 | 4 |
| **Total** | | **47** | **47** |


---

## Epic 1: Foundation — package spine & transport

### Story 1.1: Package scaffold for pyforge herald

**Status:** done  ·  **Ledger key:** `1-1-package-scaffold-for-pyforge-herald`

### Story 1.2: Transport port primary mcp client adapter the transport spike

**Status:** done  ·  **Ledger key:** `1-2-transport-port-primary-mcp-client-adapter-the-transport-spike`

### Story 1.3: Fallback transport adapter

**Status:** done  ·  **Ledger key:** `1-3-fallback-transport-adapter`

### Story 1.4: Bridge core skeleton state errors determinism boundary

**Status:** done  ·  **Ledger key:** `1-4-bridge-core-skeleton-state-errors-determinism-boundary`

### Story 1.5: Registry module readme design project

**Status:** done  ·  **Ledger key:** `1-5-registry-module-readme-design-project`

### Story 1.6: Herald deck seed slug

**Status:** done  ·  **Ledger key:** `1-6-herald-deck-seed-slug`


---

## Epic 2: Deck pull — prototype, marp, bundle

### Story 2.1: Herald deck pull slug prototype pull with etag short circuit

**Status:** done  ·  **Ledger key:** `2-1-herald-deck-pull-slug-prototype-pull-with-etag-short-circuit`

### Story 2.2: Commit opt in

**Status:** done  ·  **Ledger key:** `2-2-commit-opt-in`

### Story 2.3: Marp source pull

**Status:** done  ·  **Ledger key:** `2-3-marp-source-pull`

### Story 2.4: Standalone bundle pull

**Status:** done  ·  **Ledger key:** `2-4-standalone-bundle-pull`


---

## Epic 3: Deck status & stale-mirror detection

### Story 3.1: Herald deck status slug

**Status:** done  ·  **Ledger key:** `3-1-herald-deck-status-slug`

### Story 3.2: Stale hand mirror detection

**Status:** done  ·  **Ledger key:** `3-2-stale-hand-mirror-detection`


---

## Epic 4: Watch — poll, backoff, halt

### Story 4.1: Poll loop with quiescence debounce

**Status:** done  ·  **Ledger key:** `4-1-poll-loop-with-quiescence-debounce`

### Story 4.2: Idle backoff

**Status:** done  ·  **Ledger key:** `4-2-idle-backoff`

### Story 4.3: Halt on auth error

**Status:** done  ·  **Ledger key:** `4-3-halt-on-auth-error`


---

## Epic 5: Export push-back

### Story 5.1: Push regenerated exports with etag guard

**Status:** done  ·  **Ledger key:** `5-1-push-regenerated-exports-with-etag-guard`

### Story 5.2: Conflict refusal on export push

**Status:** done  ·  **Ledger key:** `5-2-conflict-refusal-on-export-push`


---

## Epic 6: Foundation — CLI architecture & shared infrastructure

### Story 6.1: Implement Herald CLI Dispatcher

**Status:** done  ·  **Ledger key:** `6-1-implement-herald-cli-dispatcher`

### Story 6.2: Implement Shared Argument Conventions

**Status:** done  ·  **Ledger key:** `6-2-implement-shared-argument-conventions`

### Story 6.3: Implement CLI Authentication & Authorization

**Status:** done  ·  **Ledger key:** `6-3-implement-cli-authentication-and-authorization`

### Story 6.4: Implement Evidence Link Validation Protocol (Shared Infrastructure)

**Status:** done  ·  **Ledger key:** `6-4-implement-evidence-link-validation-protocol-shared-infrastructure`

### Story 6.5: CLI Help & First-Day Usability (Inline)

**Status:** done  ·  **Ledger key:** `6-5-cli-help-and-first-day-usability`


---

## Epic 7: Foundation — web surface

### Story 7.1: Design & Implement Web Layout (Header, Tabs, Sidebar, Responsive)

**Status:** done  ·  **Ledger key:** `7-1-design-and-implement-web-layout-header-tabs-sidebar-responsive`

### Story 7.2: Implement Web Tooltips & Inline Help

**Status:** done  ·  **Ledger key:** `7-2-implement-web-tooltips-and-inline-help`


---

## Epic 8: Moment 2 — progress visibility

### Story 8.1: Implement Progress Data Model & Database Schema

**Status:** done  ·  **Ledger key:** `8-1-implement-progress-data-model-and-database-schema`

### Story 8.2: Implement On-Ship Webhook & Weekly Cron Automation

**Status:** done  ·  **Ledger key:** `8-2-implement-on-ship-webhook-and-weekly-cron-automation`

### Story 8.3: Implement Progress CLI (`herald progress` subcommand)

**Status:** done  ·  **Ledger key:** `8-3-implement-progress-cli`

### Story 8.4: Implement Progress Web Tab

**Status:** done  ·  **Ledger key:** `8-4-implement-progress-web-tab`


---

## Epic 9: Moment 3 — success proclamation

### Story 9.1: Implement Claim Data Model & Database Schema

**Status:** done  ·  **Ledger key:** `9-1-implement-claim-data-model-and-database-schema`

### Story 9.2: Implement Auto-Extract & Operator Review Gate

**Status:** done  ·  **Ledger key:** `9-2-implement-auto-extract-and-operator-review-gate`

### Story 9.3: Implement Success CLI

**Status:** done  ·  **Ledger key:** `9-3-implement-success-cli`

### Story 9.4: Implement Success Web Archive

**Status:** done  ·  **Ledger key:** `9-4-implement-success-web-archive`

### Story 9.5: Implement Evidence Validation (Sync + Async)

**Status:** done  ·  **Ledger key:** `9-5-implement-evidence-validation-sync-and-async`


---

## Epic 10: Moment 4 — operations notices

### Story 10.1: Notice Data Model & Archive Storage

**Status:** done  ·  **Ledger key:** `10-1-notice-data-model-and-archive-storage`

### Story 10.2: Notice Authoring Workflow (CLI)

**Status:** done  ·  **Ledger key:** `10-2-notice-authoring-workflow-cli`

### Story 10.3: Notice Archive & Redirects

**Status:** done  ·  **Ledger key:** `10-3-notice-archive-and-redirects`

### Story 10.4: Notice CLI

**Status:** done  ·  **Ledger key:** `10-4-notice-cli`

### Story 10.5: Operations Web Tab

**Status:** done  ·  **Ledger key:** `10-5-operations-web-tab`

### Story 10.6: Notice Lifecycle

**Status:** done  ·  **Ledger key:** `10-6-notice-lifecycle`


---

## Epic 11: Integration testing & automation reliability

### Story 11.1: Integration Testing (CLI + Web + Automation)

**Status:** done  ·  **Ledger key:** `11-1-integration-testing-cli-web-and-automation`

### Story 11.2: Automation Reliability

**Status:** done  ·  **Ledger key:** `11-2-automation-reliability`

### Story 11.3: Evidence Linking (Cross-Moment)

**Status:** done  ·  **Ledger key:** `11-3-evidence-linking-cross-moment`

### Story 11.4: Performance Testing

**Status:** done  ·  **Ledger key:** `11-4-performance-testing`


---

## Epic 12: Documentation & operator experience

### Story 12.1: CLI Runbooks & Troubleshooting

**Status:** done  ·  **Ledger key:** `12-1-cli-runbooks-and-troubleshooting`

### Story 12.2: Web Surface UX Guide

**Status:** done  ·  **Ledger key:** `12-2-web-surface-ux-guide`

### Story 12.3: Operator Runbook

**Status:** done  ·  **Ledger key:** `12-3-operator-runbook`

### Story 12.4: Automation Troubleshooting Guide

**Status:** done  ·  **Ledger key:** `12-4-automation-troubleshooting-guide`

## Epic 13: The live backend — a ship records itself

**Value delivered.** The full-spec version of Moments 2-4 the 2026-08-08 pivot deferred: a
real database, a webhook endpoint CI calls, and scheduled jobs — so an unrecorded ship stops
being indistinguishable from no ship. Decomposes `spec-herald-moments-2-4-live-backend`.
**Operator go: 2026-08-10, in-session** ("herald live-backend"), answering the Spec's own
leading question (is there real pull?) — the prior session's queue record is corroborating,
not load-bearing.

**Two Spec constraints this epic must not lose** (both dropped by an earlier draft and
restored on blind review):
1. **The concurrency prerequisite is real and first.** Every shipped storage module inherits
   `state.py`'s unlocked whole-file read-modify-write (DW-1-4-2): two writers silently drop
   an update. That is a live bug the moment ANY second writer exists — including this epic's
   own webhook. S-13.1 is a hard prerequisite, not a nicety.
2. **The serverless intermediates come first, or their skip is justified in writing.** The
   Spec names cheaper steps (`herald snapshot`, telemetry-derived defaults, locking +
   hook-triggered CLI) and says the full backend "should not be built ahead of them without
   new justification". S-13.2 carries that decision as its first AC.

**Cross-station dependency:** hosting adopts Steward's pattern (decided 2026-08-09) —
`spec-secure-live-dashboards`, decomposed as steward Epic 9. S-13.4's webhook rides that
pattern's trust boundary; it depends on `steward:S-9.1`.

### Story 13.1: The state layer survives a second writer
**Type:** foundation • **Effort:** M • **Deps:** none • **FR/AD:** LB-prereq (Spec Constraint 1)
**Surface:** `src/pyforge/herald/state.py`, `progress.py`, `claims.py`, `notices.py`, tests
**Given** two concurrent writers **Then** no update is silently lost — the unlocked
whole-file read-modify-write is replaced by a real locking/transactional layer, proven by a
concurrency test that fails against today's code. **First AC: the recorded SQLite-vs-per-file
`fcntl` decision** (the Spec's open question, resolved here). **PREREQUISITE for 13.2-13.5.**

### Story 13.2: The serverless-intermediate decision, recorded
**Type:** decision • **Effort:** S • **Deps:** S-13.1 • **FR/AD:** Spec Constraint 2
**Surface:** the Spec's memlog + this epic
**Given** the Spec's named cheaper steps (`herald snapshot`, telemetry-derived defaults,
hook-triggered CLI) **Then** each is either built here or its skip carries written
justification measured against the full backend's cost — the Spec forbids building ahead of
them silently. No further story dispatches until this decision is recorded.

### Story 13.3: DB-backed storage behind the existing seam, with migrations
**Type:** feature • **Effort:** L • **Deps:** S-13.2 • **FR/AD:** LB-1
**Surface:** `src/pyforge/herald/{progress,claims,notices}.py`, new storage module, migrations
**Given** the three local file stores **Then** the database carries the same
Progress/Claims/Notice schemas behind the existing pure function seam — CLI/web-tab contract
unchanged in shape, notices' git-tracked markdown stays the durable copy, **and migrations
ship with it** (LB-1's clause an earlier draft dropped).

### Story 13.4: The webhook endpoint CI calls
**Type:** feature • **Effort:** L • **Deps:** S-13.3, steward:S-9.1 • **FR/AD:** LB-2
**Surface:** new endpoint module, HMAC verification, retry/backoff, operator alerts
**Given** a merge or PR-close **Then** `/api/herald/webhooks/on-ship` and `on-pr-close`
create the records the CLI verbs create today, with HMAC verification, retry/backoff and
operator-alert delivery. **First AC records WHICH CI system and events trigger it** (the
Spec's second open question). Rides Steward's identity/trust boundary — never a bespoke one.

### Story 13.5: The scheduler enforces what was displayed
**Type:** feature • **Effort:** M • **Deps:** S-13.3 • **FR/AD:** LB-3
**Surface:** scheduled-job module + config
**Given** the 7-day evidence-staleness window **Then** the weekly aggregation and evidence
revalidation actually run on schedule rather than being operator-remembered.

### Story 13.6: A ship records itself, end to end
**Type:** feature • **Effort:** M • **Deps:** S-13.4, S-13.5 • **FR/AD:** LB-2 + LB-3 composed
**Given** a real merge on a station **Then** progress and a success-claim draft exist with no
human action, demonstrated live — the Dream's whole point, proven rather than asserted.

---

## Epic 14: A deck is proven to look right

**Value delivered.** Closes the recorded "render gates prove the page RUNS, never that it
LOOKS right" gap for Herald's entire deck pipeline: after this epic, one command against any
built deck yields a PNG per slide, a contact sheet, and a gate-id-keyed machine-readable
report — evidence a human or LLM reviewer actually looks at instead of trusting "the build
didn't crash." Decomposes `spec-deck-visual-qa`
(`planning-artifacts/specs/spec-deck-visual-qa/SPEC.md`).

**Decomposition choice: CAP-3 stays its own story, first — not folded into CAP-1.** The
report interface is the seam BOTH v1 gates and the three parked `.pptx`-contingent gates
(`check_xml`, `check_typst_safety`, `audit_overflow`) register into; folding it into the
render gate's story would make the placeholder scan (and every later gate) depend on that
gate's internals instead of an interface, and would leave CAP-3's own success criterion — a
stub gate id added with zero schema change — unverifiable until story two. It is also where
the Spec's entrypoint-placement open question must be resolved before either gate has
anywhere to register. With the seam first, the two gate stories are independent (both dep
only S-14.1) and one-story-per-CAP holds cleanly.

**Spec constraints this epic must not lose:** report-only — the QA step never mutates deck
sources and never rebuilds; runs against Herald's EXISTING HTML/React pipeline with zero
dependency on the pptx Dreams (CAP-3 only reserves the parked gates' slot in the report);
headless-only default; no new headless-browser dependency — playwright-python is already
pinned in the pixi envs.

### Story 14.1: Gate report interface
**Type:** foundation • **Effort:** S • **Deps:** none • **FR/AD:** CAP-3
**Surface:** new `src/pyforge/herald/deck_qa.py` (report schema + gate registry + entrypoint), `cli.py`, tests
**Given** N registered gates **Then** one machine-readable report keyed by gate id (gate →
status → per-slide findings → paths to reviewer-facing artifacts) that round-trips — parse it
back, address each gate's findings by id — and a stub third gate id registers with no change
to the report schema, the entrypoint, or any consumer: the slot the three parked
`.pptx`-contingent gates fill later. **First AC: the recorded entrypoint-placement decision**
(`herald deck qa <slug>` on the Epic-6 CLI dispatcher vs a standalone per-deck `scripts/`
step alongside `extract-slides.mjs` — the Spec's first open question, resolved here).

### Story 14.2: Headless render gate
**Type:** feature • **Effort:** M • **Deps:** S-14.1 • **FR/AD:** CAP-1
**Surface:** render gate in `src/pyforge/herald/deck_qa.py`, tests; verification target `presentations/agentic-sdlc/`
**Given** any built deck **Then** headless Chromium (playwright-python, already in the pixi
envs — no new dependency) drives every per-slide `#/<n>` URL-hash route `manifest.json`
names, screenshots the native 1920×1080 frame, and emits one PNG per slide (named by slide
index/id) plus one contact sheet into the S-14.1 report. Against
`presentations/agentic-sdlc/` (45 slides): exactly one PNG per manifest entry plus the sheet,
and a reviewer can spot a broken slide from the sheet alone; a slide that renders badly still
yields its PNG — the run reports, never aborts, never mutates deck sources. **First AC: the
recorded serve-mode decision** (built `dist/` opened as `file://` vs a throwaway local static
server — the Spec's second open question, resolved by spiking hash-routing under headless
Chromium against the real deck).

### Story 14.3: Image slot scan
**Type:** feature • **Effort:** S • **Deps:** S-14.1 • **FR/AD:** CAP-2
**Surface:** placeholder gate in `src/pyforge/herald/deck_qa.py`, tests; verification target `presentations/agentic-sdlc/`
**Given** a deck's sources and extracted slides **Then** slides shipping with unfilled image
slots are flagged in BOTH spellings — `<image-slot placeholder="…">` in prototype/fragment
sources AND the dashed `.image-slot` placeholder `<div>` the extractor converts them to —
registered as a second real gate id in the S-14.1 report, proving the multi-gate report shape
with more than a stub. Against `presentations/agentic-sdlc/` today it flags exactly slide 40
("In action"), whose three `<image-slot>` panels are documented as deliberately unfilled — a
live true positive; a deck with every slot filled reports clean. Explicitly NOT the source
org's PowerPoint-specific "Click to add"/Lorem-ipsum regex.

## Epic 15: Editable decks — the PowerPoint-native pipeline

**Spec binding.** Decomposes `spec-pptx-deck-generation` CAP-1 + `spec-pptx-custom-shapes`
CAP-1 — UNPARKED 2026-08-22: Marp inadequacy proven (shipped exports are background-image
slides, zero text runs) AND the operator named the audience (the 21-station deck program
delivered to stakeholders who edit). Sibling-org blueprint = pattern only, unlicensed.
Coexists with the HTML/Marp pipeline; never replaces it.

### Story 15.1: Template-parse-then-fill produces a genuinely editable deck
**Type:** feature • **Effort:** L • **Deps:** — • **FR/AD:** spec-pptx-deck-generation CAP-1
**Given** a .potx/.pptx template (own-template question resolved here with a dated entry)
**Then** it parses once into a `spec.json` machine contract, an agent's
`content_plan.json` fills placeholders mechanically — raw OOXML never hand-written — and
an existing station deck renders to a .pptx whose every text run edits cleanly in
PowerPoint (round-trip proven).

### Story 15.2: Dense content renders as shapes that fit
**Type:** feature • **Effort:** M • **Deps:** S-15.1 • **FR/AD:** spec-pptx-custom-shapes CAP-1
**Given** content no placeholder anticipates **Then** card/metric-box/table/section-label
calls render editable objects into 15.1's decks with Pillow real-font-measured autofit
(wrap, shrink, orphan rebalancing) — the densest six-act appendix slide fits, measured
not guessed.

---

## Canopy obligations (2026-08-24)

Herald station boundaries under the Canopy (`spec-pyforge-unifying-strategy`, steward-owned).
Epics 1–15 are **complete**. Do **not** mint herald Epics 16+ that duplicate steward Epics
18–30.

**Five-tier symmetry.** Herald's CLI tier is shipped (`pyforge-herald` / `herald` verbs).
Remaining tiers are steward-owned: **Epic 19** (portal), **Epic 21** (service face / MCP +
supervisor), **Epic 22** (`pyforge herald …` dispatch), **Epic 29** (SKF domain skill +
Agent-Herald persona). Herald integrates at hooks — it does not re-spec those tiers here.

**Uniform URL.** Herald's Lane 2 portal mounts at **`/stations/herald/`** under the single host
session — no station-specific origin, no extra public port.

**Naming triple.** Distribution **`django-herald`**, module **`django_herald_<app>`**, app label
**`herald_<app>`** (reusable-app convention; additional apps are siblings; existing models never
move between apps).

**Chrome.** Portals mount **`django-pyforge`** shared chrome only — no second app switcher, no
duplicated Modernist shell, no herald-only header fork.

**Service face.** Herald capabilities surface through **`POST /stations/herald/mcp`** on the host
ASGI (steward **Epic 21.4**) — **no** standalone `:8006` FastAPI, **no** `services/` microservice,
**no** second public port. Existing transport/MCP bridge code migrates to the Canopy pattern; it
is not duplicated.

**CLI.** The **`herald`** entry point remains authoritative; **`pyforge herald …`** dispatch is
steward **Epic 22** — herald does not fork a second grammar.

**Domain skill & persona.** SKF compiles the domain skill from **`pyforge-herald`** (steward
**Epic 29.1**); **Agent-Herald** consults that skill and acts only through FR-13 grammar + FR-11
MCP (steward **Epic 29.2**).

**Web surfaces — two lanes, not confused.** Herald's Moments UI (Epics 7–10, static JSON
snapshot) is the **framework-neutral secure-dashboard adopter** that motivated
`spec-secure-live-dashboards` — role isolation and audit ride **`pyforge.steward.dashboard`**
(CAP-7). Herald **does not** adopt Vizro (Lane 3). Lane 1 Guildhall/Wagtail is **not** Herald's
(`spec-pyforge-herald/SPEC.md` non-goal: owning the console); steward **Epic 20** owns the front
door. Portal projection of Moments data is steward **Epic 19**, not a herald Epic 16+.

**Shipped work stands.** Epics 1–15 (deck bridge, CLI, Moments 2–4, live backend, deck QA, PPTX
pipeline) remain **done**. Canopy integration is additive — no rollback of shipped herald stories.

## Operating-model obligations (2026-08-24)

Estate-wide bind from Unifying Strategy Grounding (hooks/plugins principle + Q1–Q8)
and steward `sprint-change-proposal-2026-08-24-operating-model.md` (**§6 revisited**).
**Hooks and plugins (canopy AD-21):** as far as possible every layer is replaceable —
the process owns hook specifications; a plugin implements or replaces a layer without
a fork. Kedro
[architecture overview](https://docs.kedro.org/en/stable/getting-started/architecture_overview/)
*names* the split; it does not require this station to be a Kedro project. Warden owns
PR-gate hook specs (Q8). This station owns its process hooks.

**Always / Never (every station):**
- Five-tier completeness is the **03** shape. 01/02 stay spec+script or spec+skill.
- Guildhall / switcher must not tile `work_class` 01 or 02 as a station.
- Golden Path: humans, CI, and agents invoke the same Pixi task names.
- CloudEvents: `spec_id` + git sha + SBOM purl; Jira optional; never fail for a missing key.
- Path B = Agent Canopy + this station's persona. Tachyon = production LLM provider adapter.
- Lane 2 = HTMX; station compute = FastAPI. No station-local DRF JSON:API on the portal.
- Design station processes as hook specs + plugins (AD-21). Do not fork a process to swap a vendor.
- **Never** a competing PR quality-gate verdict. Quality scanners register as **Warden plugins**.
- Scorecard measures are unpublished (human + agent + team; draft later). Do not optimize to invented metrics.

**Herald-local:** Deck/export format plugins (Marp, PPTX, .dc.html) are station hooks (Story **16.1**). Publish/export success is not a Warden verdict. Lane 1 CMS remains steward-owned.

**Pointers:** `change-history/sprint-change-proposal-2026-08-24-operating-model.md`;
`change-history/sprint-change-proposal-2026-08-24-hook-specs.md`;
steward `sprint-change-proposal-2026-08-24-hook-specs.md`; `DW-OM-2026-08-24`.

## Epic 16: Exporter hook spec

**FR-45.** Deps: steward S-32.1.

### Story 16.1: Extract deck/export format plugins

As a herald operator,
I want Marp, PPTX, and `.dc.html` as exporter plugins on the shared contract,
So that adding an export format does not fork herald.

**Type:** feature • **Effort:** M • **Deps:** steward S-32.1 • **FR/AD:** FR-45 • canopy AD-21
**Given** today's exporters **When** the hook spec lands **Then** they are the default plugins
**And** export success is not published as a PR quality-gate verdict

## Epic 17: Herald owns its skill, persona, and one portal job

Does **not** copy Canopy 18–30. Lane 1 CMS remains steward.

### Story 17.1: SKF domain skill and BMAD persona for herald

As an autonomous agent,
I want a herald SKF skill from `pyforge-herald/` and a `bmad-agent-herald` persona,
So that Path B uses CAP-5 grammar and CAP-4 MCP only.

**Type:** feature • **Effort:** L • **Deps:** S-16.1 • **FR/AD:** canopy FR-37, FR-38 • canopy AD-17
**Given** steward 29 proved the shape **When** this story completes **Then** SKF compiles from `src/shared/packages/pyforge-herald/` if missing
**And** the persona uses only `pyforge herald …` and `POST /stations/herald/mcp`

### Story 17.2: First portal slice — deck status for one slug

As a herald operator,
I want `/stations/herald/` to show `herald deck status` for one slug,
So that stale-mirror state is visible in HTMX without leaving the host.

**Type:** feature • **Effort:** M • **Deps:** S-17.1 • **FR/AD:** canopy FR-10 • canopy AD-7
**Given** an authenticated herald-role session **When** the operator opens `/stations/herald/` **Then** one slug's status renders via PortalClient only
**And** no raw HTTP, no `pyforge.*` under `src/platform/`, no chrome copy
