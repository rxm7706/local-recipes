---
epics_role: canonical
# The single canonical story source for this station: every `### Story` heading here maps
# 1:1 to a sprint-status-ledger.yaml story key. Exactly one `canonical` per station (marshal:AD-72).
project_name: pyforge-herald
epicCount: 22  # 2026-09-13: Epic 22 added (spec-pyforge-pages). Dated snapshot; the ledger enumerates.
storyCount: 55  # 2026-09-13: + Story 22.1. Dated snapshot; the ledger enumerates.
status: in-progress  # 2026-09-13: Epic 22 opens Story 22.1; Epics 19 and 21 still have unstarted work.
updated: "2026-09-25"   # RE-STAMPED 2026-09-25: chain-currency cascade (arch -> epics); Epic 26 minted (26.1, spec-python-foundry-cutover fnd:CAP-14). Prior 2026-09-20
---

## Fold provenance (2026-09-17)

Station Spec spec-pyforge-herald reminted absorbed capabilities as CAP-1..47. Historical stories keep sequential epic numbers 1..23; Epic 23 story gaps closed (23.5–23.8 → 23.3–23.6). This heading is the INV-A citation window for the folded set (`spec-pyforge-herald` CAP-1..47).

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
| **E20** | The deck family stays current (spec-deck-family-currency) | 14 | 14 |
| **E21** | The whole deck family moves together (spec-deck-family-lockstep) | 11 | 0 |
| **E22** | The public Pages root is one dossier (spec-pyforge-pages) | 1 | 0 |
| **Total** | | **48** | **47** |


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
**Status:** done  ·  **Ledger key:** `6-3-implement-cli-authentication-authorization`

### Story 6.4: Implement Evidence Link Validation Protocol (Shared Infrastructure)
**Status:** done  ·  **Ledger key:** `6-4-implement-evidence-link-validation-protocol-shared-infrastructure`

### Story 6.5: CLI Help & First-Day Usability (Inline)
**Status:** done  ·  **Ledger key:** `6-5-cli-help-first-day-usability-inline`


---

## Epic 7: Foundation — web surface

### Story 7.1: Design & Implement Web Layout (Header, Tabs, Sidebar, Responsive)
**Status:** done  ·  **Ledger key:** `7-1-design-implement-web-layout-header-tabs-sidebar-responsive`

### Story 7.2: Implement Web Tooltips & Inline Help
**Status:** done  ·  **Ledger key:** `7-2-implement-web-tooltips-inline-help`


---

## Epic 8: Moment 2 — progress visibility

### Story 8.1: Implement Progress Data Model & Database Schema
**Status:** done  ·  **Ledger key:** `8-1-implement-progress-data-model-database-schema`

### Story 8.2: Implement On-Ship Webhook & Weekly Cron Automation
**Status:** done  ·  **Ledger key:** `8-2-implement-on-ship-webhook-weekly-cron-automation`

### Story 8.3: Implement Progress CLI (`herald progress` subcommand)
**Status:** done  ·  **Ledger key:** `8-3-implement-progress-cli-herald-progress-subcommand`

### Story 8.4: Implement Progress Web Tab
**Status:** done  ·  **Ledger key:** `8-4-implement-progress-web-tab`


---

## Epic 9: Moment 3 — success proclamation

### Story 9.1: Implement Claim Data Model & Database Schema
**Status:** done  ·  **Ledger key:** `9-1-implement-claim-data-model-database-schema`

### Story 9.2: Implement Auto-Extract & Operator Review Gate
**Status:** done  ·  **Ledger key:** `9-2-implement-auto-extract-operator-review-gate`

### Story 9.3: Implement Success CLI
**Status:** done  ·  **Ledger key:** `9-3-implement-success-cli`

### Story 9.4: Implement Success Web Archive
**Status:** done  ·  **Ledger key:** `9-4-implement-success-web-archive`

### Story 9.5: Implement Evidence Validation (Sync + Async)
**Status:** done  ·  **Ledger key:** `9-5-implement-evidence-validation-sync-async`


---

## Epic 10: Moment 4 — operations notices

### Story 10.1: Notice Data Model & Archive Storage
**Status:** done  ·  **Ledger key:** `10-1-notice-data-model-archive-storage`

### Story 10.2: Notice Authoring Workflow (CLI)
**Status:** done  ·  **Ledger key:** `10-2-notice-authoring-workflow-cli`

### Story 10.3: Notice Archive & Redirects
**Status:** done  ·  **Ledger key:** `10-3-notice-archive-redirects`

### Story 10.4: Notice CLI
**Status:** done  ·  **Ledger key:** `10-4-notice-cli`

### Story 10.5: Operations Web Tab
**Status:** done  ·  **Ledger key:** `10-5-operations-web-tab`

### Story 10.6: Notice Lifecycle
**Status:** done  ·  **Ledger key:** `10-6-notice-lifecycle`


---

## Epic 11: Integration testing & automation reliability

### Story 11.1: Integration Testing (CLI + Web + Automation)
**Status:** done  ·  **Ledger key:** `11-1-integration-testing-cli-web-automation`

### Story 11.2: Automation Reliability
**Status:** done  ·  **Ledger key:** `11-2-automation-reliability`

### Story 11.3: Evidence Linking (Cross-Moment)
**Status:** done  ·  **Ledger key:** `11-3-evidence-linking-cross-moment`

### Story 11.4: Performance Testing
**Status:** done  ·  **Ledger key:** `11-4-performance-testing`


---

## Epic 12: Documentation & operator experience

### Story 12.1: CLI Runbooks & Troubleshooting
**Status:** done  ·  **Ledger key:** `12-1-cli-runbooks-troubleshooting`

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
**Type:** feature • **Effort:** M • **Deps:** S-15.1 • **FR/AD:** spec-pptx-custom-shapes CAP-1, spec-pptx-deck-generation CAP-2 (owned-by cross-reference per that Spec's own CAP-2 declaration)
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
**Hooks and plugins (canopy:AD-21):** as far as possible every layer is replaceable —
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
- Design station processes as hook specs + plugins (canopy:AD-21). Do not fork a process to swap a vendor.
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

**Type:** feature • **Effort:** M • **Deps:** steward S-32.1 • **FR/AD:** FR-45 • canopy:AD-21
**Given** today's exporters **When** the hook spec lands **Then** they are the default plugins
**And** export success is not published as a PR quality-gate verdict

## Epic 17: Herald owns its skill, persona, and one portal job

Does **not** copy Canopy 18–30. Lane 1 CMS remains steward.

### Story 17.1: SKF domain skill and BMAD persona for herald
As an autonomous agent,
I want a herald SKF skill from `pyforge-herald/` and a `bmad-agent-herald` persona,
So that Path B uses CAP-5 grammar and CAP-4 MCP only.

**Type:** feature • **Effort:** L • **Deps:** S-16.1 • **FR/AD:** canopy FR-37, FR-38 • canopy:AD-17
**Given** steward 29 proved the shape **When** this story completes **Then** SKF compiles from `src/shared/packages/pyforge-herald/` if missing
**And** the persona uses only `pyforge herald …` and `POST /stations/herald/mcp`

### Story 17.2: First portal slice — deck status for one slug
As a herald operator,
I want `/stations/herald/` to show `herald deck status` for one slug,
So that stale-mirror state is visible in HTMX without leaving the host.

**Type:** feature • **Effort:** M • **Deps:** S-17.1 • **FR/AD:** canopy FR-10 • canopy:AD-7
**Given** an authenticated herald-role session **When** the operator opens `/stations/herald/` **Then** one slug's status renders via PortalClient only
**And** no raw HTTP, no `pyforge.*` under `src/platform/`, no chrome copy

## Epic 18: Herald renders, announces and slides with the suite

**Spec binding.** The herald-side relays of `spec-bmad-suite-lifecycle` (Dream
`docs/dreams/bmad-suite-lifecycle.md`, 2026-09-06): the manticore studio (CAP-5), the
`bmad-os-changelog` / `-social` release comms and labs' `slides-generator` (CAP-3, CAP-6).
**HARD boundaries:** the studio is a separate root — this repo's `_bmad/` is never touched by a
render (lifecycle spine AD-3); `.mp4` and render intermediates are gitignored build artifacts;
steward 46.6 / 46.2 / 46.5 provision first; Path B grammar stays `pyforge herald …`.

### Story 18.1: The first station video renders from Herald's studio
**Type:** feature • **Effort:** M • **Deps:** — (after steward 46.6 — cross-station: ledger `blocked`, AD-10) • **FR/AD:** spec-bmad-suite-lifecycle CAP-5 • AD-3 • `docs/dreams/herald-pitch.md` (narration scenes)
**Surface:** the studio root read from `PYFORGE_STUDIO_ROOT` (default `~/pyforge-studio/`, AD-3 — the register cell cites it), `presentations/<station>/` speaker notes (read), `bmad-agent-herald` (a hand-off note: "open a session in `$PYFORGE_STUDIO_ROOT`; run `mc-*` there" — never a route, `mc-*` never live in the repo tree), a `herald deck …` verb or documented studio invocation
**Given** the provisioned studio **When** one station deck's speaker notes are handed to `mc-braindump → mc-script → mc-cut → mc-package` **Then** one `<station>.mp4` renders in the studio, is gitignored, this repo's `_bmad/` checksum is unchanged, and the register row records the render date and the four approval gates walked

### Story 18.2: Release comms go through `bmad-os-changelog` and `-social`
**Type:** feature • **Effort:** S • **Deps:** — (after steward 46.2 — cross-station: ledger `blocked`, AD-10) • **FR/AD:** spec-bmad-suite-lifecycle CAP-3 • AD-2
**Surface:** `.claude/skills/bmad-agent-herald/SKILL.md` (routing), the register § 2 row (one AGENTS.md pointer line only, AD-2/AD-11), `herald notice` / `success` inputs, `adoption-register.md` § 2 rows
**Given** the two skills installed **When** the herald persona routes release notes to `bmad-os-changelog` and the social variant to `bmad-os-changelog-social` feeding `herald notice` **Then** one release (the next suite refresh) has its note produced through them, the register names herald as sole wielder, and CLAUDE.md is untouched

### Story 18.3: `slides-generator` is herald-wielded
**Type:** docs • **Effort:** XS • **Deps:** — (after steward 46.5 — cross-station: ledger `blocked`, AD-10) • **FR/AD:** spec-bmad-suite-lifecycle CAP-6 • AD-2 • `docs/specs/presentation-deck.md` (the deck pipeline it must not fork)
**Surface:** `.claude/skills/bmad-agent-herald/SKILL.md`, `adoption-register.md` § 2 row, `AGENTS.md` block
**Given** the labs skill installed by name **When** the herald persona routes quick slide drafts to `slides-generator` while the Claude-Design deck pipeline stays the deck source of record **Then** the register names herald as sole wielder and the routing line states the boundary (draft only; never a deck head)


## Epic 19: Herald in effect (fleet readiness 2026-09-09)

**Spec binding.** The herald satellites of the **realization gate** — a capability is in effect
when its named success criterion is exercised in the running estate, not when its story merges
(`spec-pyforge-unifying-strategy`; fleet-readiness decision batch 2026-09-09, row **C6**). The
2026-09-09 readiness pass found three of Herald's five Dreams `done` in the ledger and never
exercised: Epic 13's live backend has never run green, Epic 14's deck-QA gate is called by
nothing, and Epic 15's pptx pipeline has never rendered a real station deck. This epic is their
single vessel; steward **Epic 49** carries one index row pointing here, and nothing in this epic
is re-implemented under steward. **HARD boundaries:** no new capability is built — every story
turns on something that already ships; the effect test is Story 49.2's, *"has a caller outside
its own test file"*; `herald-live-demo.yml` stays disabled (a green run against a
`runner.temp` store is not the success signal); no second console, no extra public port.

### Story 19.1: The webhook routes move onto the station API seam
**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** `spec-herald-moments-2-4-live-backend` LB-2 • `spec-pyforge-unifying-strategy` SPEC.md:497 (Always: station routes are `/stations/<name>/api/v<N>/`) • batch row C11
**Surface:** `src/shared/packages/pyforge-herald/src/pyforge/herald/webhook.py` (`ON_SHIP_PATH` / `ON_PR_CLOSE_PATH`, `:183-184`), `src/shared/packages/pyforge-herald/src/pyforge/herald/webhook_host.py`, `src/platform/config/station_api.py` (herald v1 registration beside warden, `:146`), `.github/workflows/herald-live-demo.yml` (caller paths only), herald's CI-caller documentation
**Given** `webhook.ON_SHIP_PATH = "/api/herald/webhooks/on-ship"` and `ON_PR_CLOSE_PATH = "/api/herald/webhooks/on-pr-close"`, which sit on the bare `/api/` namespace the platform FastAPI seam owns — `config/asgi.py:149-150` routes every `/api/*` path to `fastapi_application`, and only `_STATION_API_RE` paths are diverted to a station sub-app (`config/asgi.py:132-144`, `config/station_api.py:24-32`) — **When** the literals are re-pointed onto `/stations/herald/api/v1/webhooks/{on-ship,on-pr-close}` and herald v1 is registered on the seam beside warden **Then** a request to the new path reaches `webhook_host:application` rather than the platform stub, the HMAC verification path is unchanged, every caller (workflow, runbook, CLI doc) names the new path, and a test asserts the bare `/api/herald/...` form is no longer served
**And** the change is contract-visible: the Spec's `surface:` block and `docs/` callers move in the same PR, because fixing this later means changing a documented CI-caller contract

### Story 19.2: One real ship records itself against a persistent store
**Type:** feature • **Effort:** M • **Deps:** S-19.1 • **FR/AD:** `spec-herald-moments-2-4-live-backend` LB-2 / LB-3 • Epic 13's success signal • batch rows C6, C11
**Surface:** `src/shared/packages/pyforge-herald/src/pyforge/herald/{webhook.py,webhook_host.py,scheduler.py,db.py,locking.py}`, the store location (a persistent path or a provisioned DB — **never** `${{ runner.temp }}`), `HERALD_WEBHOOK_SECRET` provisioning, whatever host actually runs the listener
**Given** Epic 13 closed 6/6 `done` while `herald-live-demo.yml` is `disabled_manually` with 100 failed runs and zero successes (last run 2026-08-24), its own header declaring it "never a persistent, publicly-reachable deployment" writing to a `runner.temp` DB "discarded when the job ends" — so a ship has never recorded itself — **When** one real ship event is delivered to the webhook against a store that survives the process **Then** the progress record exists in that store after the process exits, is readable by `herald progress`, and the run is cited by evidence (run id or store path) in this story's completion note
**And** the hosting half is honest about its blocker: `DW-13-6-1` records that `steward deploy perimeter` renders only a hardcoded `myproject.asgi:application` (`steward/deploy.py:484`) with no `--asgi-application` flag, so this story either names the host it used or is **explicitly `foundry-side`** and blocked on the cutover giving Herald a perimeter — it never closes on a throwaway store

### Story 19.3: The deck-QA gate gets a caller
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** `spec-deck-visual-qa` CAP-1..3 (Epic 14: 14.1/14.2/14.3, all `done`) • batch row C6
**Surface:** `pixi.toml` (a `deck-qa` task in the `local-recipes` or `pyforge-herald` feature), `docs/specs/presentation-deck.md` § verify checklist, optionally `.github/workflows/` (a deck lane), `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_qa.py` (unchanged — this story adds no gate)
**Given** `herald deck qa <slug>` works (`cli.py:331-341` / `:764-765` / `:982-995`; `deck_qa.py`, 665 lines) and nothing calls it — no pixi task (`pixi.toml` names `deck_qa` only in a playwright dependency comment), no CI job, and `docs/specs/presentation-deck.md`'s verify checklist is still entirely run-shaped, which is the exact gap the Spec was written to close — **When** a pixi task invokes the gate and `presentation-deck.md`'s verify checklist names it as a step **Then** one existing deck (`presentations/agentic-sdlc/`) is run through the gate, its report is produced under `.herald/deck-qa/<slug>/`, and the gate has at least one caller outside its own test file
**And** the gate's verdict is advisory or blocking by explicit choice recorded in the story — never blocking by accident, and never a second PR gate

### Story 19.4: One real station deck renders through the pptx pipeline
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** `spec-pptx-deck-generation` CAP-1 • `spec-pptx-custom-shapes` CAP-1 (Epic 15: 15.1/15.2, both `done`) • batch row C6
**Surface:** a first real `content_plan.json` (none exists anywhere in the tree today), `src/shared/packages/pyforge-herald/src/pyforge/herald/pptx_pipeline.py` (unchanged — this story adds no pipeline), `presentations/<station>/src/pptx/`, `docs/specs/presentation-deck.md` (the pptx step, if it earns one)
**Given** `pptx_pipeline.py` (1057 lines) ships `extract_spec` / `fill_template` and the shape API (`add_card` / `add_metric_box` / `add_table` / `add_section_label` + Pillow `fit_text` autofit) behind `herald deck pptx-spec` / `pptx-fill` (`cli.py:342-386`), while every `.pptx` under `presentations/*/src/pptx/` is a dated Marp export from 2026-07/08 and no `content_plan.json` exists — **When** one station deck is authored as a `content_plan.json` and filled through the pipeline against the committed interim template (`templates/pyforge-deck-template.pptx`) **Then** the resulting `.pptx` opens with real, editable text runs (not background-image slides), at least one dense slide exercises the shape API, and the file is the pipeline's output rather than a Marp export
**And** the deck follows the canonical six-act framework with the Warden standalone deck as the shape exemplar; a PyForge-branded `.potx` stays deferred work reachable by a `--template` flag, not a blocker for this story

## Epic 20: The deck family stays current (spec-deck-family-currency)

**Spec binding.** `spec-deck-family-currency` CAP-1..5 (herald; Dream `docs/dreams/deck-family-currency.md`,
`specified` 2026-09-13). Every `presentations/pyforge-*/project/<Persona> Infographic standalone.html` is
re-derived to one codified standard from a per-deck fact ledger, pushed byte-exact to its Design project, and
made checkable for staleness. Measured 2026-09-13: eleven of fourteen posters are the 2026-07-24/25
six-section stubs; the deep ones quote July's tooling and fleet (marshal: `bmad-method 6.10.0`, "128/333
fleet-wide"). **HARD boundaries (Spec constraints):** facts come from tracked ledgers and manifests, never a
prior poster or memory — no number ships without a `facts.yaml` row; never restrict size at authoring; the
standalone leads this epic (dated exception to trio lockstep — head and Infographic Deck marked "standalone
ahead"); repo-side authoring with a DesignSync `localPath` push, no Design-chat authoring or polish; one PR
per deck with the `maintenance` label; four worktree agents per wave, physical paths, never `bmad-switch`;
the facts check is advisory (exit 0), never a second gate. **Standard:** the Spec companion
`infographic-standard.md` — Unifying Strategy is the structure/acts/length reference, Warden the
density/visual-form reference. Wave A = 20.3–20.10; Wave B = 20.11–20.12; 20.13 closes the bridge view.

### Story 20.1: The standard has one home and the deck spec points to it
**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** `spec-deck-family-currency` CAP-1
**Surface:** `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-currency/infographic-standard.md` (the home — unchanged by this story), `docs/specs/presentation-deck.md` (§ *Artifact dependency tree* "Exemplar for form" sentence; the verify checklist), `presentations/README.md` (pointer line)
**Given** the standard lives in `infographic-standard.md` while `presentation-deck.md` still names "the warden family" as the sole form exemplar and its verify checklist is run-shaped and never names a floor — **When** the deck spec's editing-surfaces section and verify checklist point at the standard and name its floors (six act bands, ≥ 18 sections, ≥ 3 inline SVGs, ≥ 90 KB, every fact a ledger row, full-page PNG reviewed) — **Then** a reader of `presentation-deck.md` reaches the standard in one hop and no second copy of the floors exists anywhere in the tree
**And** the legacy `docs/specs/` tier gains a pointer only — never a second standard

### Story 20.2: `deck-facts` derives a per-deck fact ledger and checks a poster against it
**Type:** feature • **Effort:** M • **Deps:** S-20.1 • **FR/AD:** `spec-deck-family-currency` CAP-2, CAP-5 • companion `facts-ledger.md`
**Surface:** `scripts/deck_facts.py` (new; the `scripts/deck_export.py` precedent — one script, one pixi task), `pixi.toml` (`[feature.local-recipes.tasks.deck-facts]`), `presentations/pyforge-*/facts.yaml` (first derivations for the ten decks), `docs/specs/presentation-deck.md` (one line naming the task)
**Given** no poster cites a source for any number it shows and nothing detects poster staleness — **When** `pixi run -e local-recipes deck-facts <slug>` emits `presentations/<slug>/facts.yaml` per `facts-ledger.md` (sprint ledgers through the real `parse_sprint_status`, versions from `pyproject.toml` and `_bmad/_config/manifest.yaml`, CAP counts from `SPEC.md`, counts from `bmad-groundtruth`, CLI verbs from the station's subparsers, test counts from `pytest --collect-only` in the station's own env) and `deck-facts <slug> --check` tokenizes the poster and reports unresolved tokens, drifted rows and unshown rows — **Then** re-deriving on an unchanged tree is byte-identical, a mutated ledger value is named by `--check`, and the marshal poster's known-stale claims (`6.10.0`, `0.9.0`, `128/333`, `4/27`) are each reported on the first run
**And** the check always exits 0 and never joins `detectors` / `detectors-ci` as a gate — advisory by construction

### Story 20.3: PyForge Atlas poster rebuilt to the standard from its ledger
**Type:** feature • **Effort:** M • **Deps:** S-20.1, S-20.2 • **FR/AD:** `spec-deck-family-currency` CAP-3, CAP-4 • Wave A
**Surface:** `presentations/pyforge-atlas/project/PyForge Atlas Infographic standalone.html`, `presentations/pyforge-atlas/facts.yaml`, `presentations/pyforge-atlas/README.md` (sync ledger) • Design project `2acb0575-9997-442b-bb0e-6207d78f6648`
**Given** the poster is a 2026-07-24 stub (15,678 B / 6 sections / 0 acts / 0 SVG) — **When** it is authored repo-side to `infographic-standard.md` from `facts.yaml` (six act bands, ≥ 18 sections, ≥ 3 inline SVGs, ≥ 90 KB, every count/version/status/date a ledger row), rendered headless to a full-page PNG and reviewed, pushed to the Design project through DesignSync `finalize_plan` → `write_files` (`localPath`), and read back — **Then** the README ledger carries the measured values against the floors, the Design etag and byte count, the render date and page height, and "standalone ahead" for the head and Infographic Deck; `deck-facts pyforge-atlas --check` reports every token resolved
**And** the PR carries the `maintenance` label, touches only this deck's folder, and is one of at most four in flight for the wave
### Story 20.4: PyForge Doctor poster rebuilt to the standard from its ledger
**Type:** feature • **Effort:** M • **Deps:** S-20.1, S-20.2 • **FR/AD:** `spec-deck-family-currency` CAP-3, CAP-4 • Wave A
**Surface:** `presentations/pyforge-doctor/project/PyForge Doctor Infographic standalone.html`, `presentations/pyforge-doctor/facts.yaml`, `presentations/pyforge-doctor/README.md` • Design project `46dbbdea-6f8d-45c6-9309-15d1f297beeb`
**Given** the poster today measures 14,419 B / 5 / 0 / 0 — **When / Then / And** exactly as Story 20.3, for PyForge Doctor
### Story 20.5: PyForge Herald poster rebuilt to the standard from its ledger
**Type:** feature • **Effort:** M • **Deps:** S-20.1, S-20.2 • **FR/AD:** `spec-deck-family-currency` CAP-3, CAP-4 • Wave A
**Surface:** `presentations/pyforge-herald/project/PyForge Herald Infographic standalone.html`, `presentations/pyforge-herald/facts.yaml`, `presentations/pyforge-herald/README.md` • Design project `ff879a32-9741-4cf5-948f-d67040481d24`
**Given** the poster today measures 16,720 B / 6 / 0 / 0 — **When / Then / And** exactly as Story 20.3, for PyForge Herald
### Story 20.6: PyForge Marshal poster rebuilt to the standard from its ledger
**Type:** feature • **Effort:** M • **Deps:** S-20.1, S-20.2 • **FR/AD:** `spec-deck-family-currency` CAP-3, CAP-4 • Wave A
**Surface:** `presentations/pyforge-marshal/project/PyForge Marshal Infographic standalone.html`, `presentations/pyforge-marshal/facts.yaml`, `presentations/pyforge-marshal/README.md` • Design project `ad84d4f6-c292-42c8-98bf-ede78a567773`
**Given** the poster today measures 91,340 B / 19 / 6 / 3 — six-act already; every stat is a July 2026 claim — **When / Then / And** exactly as Story 20.3, for PyForge Marshal
### Story 20.7: PyForge Mason poster rebuilt to the standard from its ledger
**Type:** feature • **Effort:** M • **Deps:** S-20.1, S-20.2 • **FR/AD:** `spec-deck-family-currency` CAP-3, CAP-4 • Wave A
**Surface:** `presentations/pyforge-mason/project/PyForge Mason Infographic standalone.html`, `presentations/pyforge-mason/facts.yaml`, `presentations/pyforge-mason/README.md` • Design project `a7a2c3b1-5718-49fa-8c90-71d44d57eae9`
**Given** the poster today measures 14,404 B / 6 / 0 / 0 — **When / Then / And** exactly as Story 20.3, for PyForge Mason
### Story 20.8: PyForge Scribe poster rebuilt to the standard from its ledger
**Type:** feature • **Effort:** M • **Deps:** S-20.1, S-20.2 • **FR/AD:** `spec-deck-family-currency` CAP-3, CAP-4 • Wave A
**Surface:** `presentations/pyforge-scribe/project/PyForge Scribe Infographic standalone.html`, `presentations/pyforge-scribe/facts.yaml`, `presentations/pyforge-scribe/README.md` • Design project `a1e42dac-7cee-438b-9acc-2523985b5253`
**Given** the poster today measures 15,978 B / 6 / 0 / 0 — **When / Then / And** exactly as Story 20.3, for PyForge Scribe
### Story 20.9: PyForge Steward poster rebuilt to the standard from its ledger
**Type:** feature • **Effort:** M • **Deps:** S-20.1, S-20.2 • **FR/AD:** `spec-deck-family-currency` CAP-3, CAP-4 • Wave A
**Surface:** `presentations/pyforge-steward/project/PyForge Steward Infographic standalone.html`, `presentations/pyforge-steward/facts.yaml`, `presentations/pyforge-steward/README.md` • Design project `573d6554-0095-4126-b13f-cd537279ff8a`
**Given** the poster today measures 14,475 B / 6 / 0 / 0 — **When / Then / And** exactly as Story 20.3, for PyForge Steward
### Story 20.10: Warden poster rebuilt to the standard from its ledger
**Type:** feature • **Effort:** M • **Deps:** S-20.1, S-20.2 • **FR/AD:** `spec-deck-family-currency` CAP-3, CAP-4 • Wave A
**Surface:** `presentations/pyforge-warden/project/Warden Infographic standalone.html`, `presentations/pyforge-warden/facts.yaml`, `presentations/pyforge-warden/README.md` • Design project `100ca8cc-8daa-409a-8564-1f8d79c579d2`
**Given** the poster today measures 411,764 B / 18 / 0 acts / 15 SVG — the visual reference: keep its form, add the six-act arc, re-derive every stat — **When / Then / And** exactly as Story 20.3, for Warden
### Story 20.11: PyForge Genesis poster rebuilt to the standard from its ledger
**Type:** feature • **Effort:** M • **Deps:** S-20.1, S-20.2 • **FR/AD:** `spec-deck-family-currency` CAP-3, CAP-4 • Wave B
**Surface:** `presentations/pyforge-genesis/project/PyForge Genesis Infographic standalone.html`, `presentations/pyforge-genesis/facts.yaml`, `presentations/pyforge-genesis/README.md` • Design project `6af4c28d-d510-4e9b-b788-6c0e5d651183`
**Given** the poster today measures 47,877 B / 9 sections / 0 acts / 0 SVG and carries the Charter's guild-wide facts (eight Smiths, the Dream count, fleet totals) — **When / Then / And** exactly as Story 20.3, for the Genesis (Charter) deck; guild-wide facts come from `docs/governance/guild-roster.json`, `docs/dreams/*.md` frontmatter and `fleet-picture`

### Story 20.12: The Canopy poster re-derived and its Design project created
**Type:** feature • **Effort:** M • **Deps:** S-20.1, S-20.2 • **FR/AD:** `spec-deck-family-currency` CAP-3, CAP-4 • Wave B • requires the claude-design MCP connected
**Surface:** `presentations/pyforge-unifying-strategy/project/PyForge Unifying Strategy Infographic standalone.html`, `presentations/pyforge-unifying-strategy/facts.yaml`, `presentations/pyforge-unifying-strategy/README.md` (`## Design project` section written in the canonical two-line shape via `registry.register`)
**Given** the poster is the structure reference (128,783 B / 21 sections / 6 acts / 9 SVG) yet quotes 2026-08-26 facts ("CAP-1..18 closed", "40/40 five-tier") and has no Design project — **When** its facts are re-derived from `spec-pyforge-unifying-strategy/SPEC.md` and steward's ledger, a Design project "PyForge Unifying Strategy deck" is created through the claude-design MCP `create_project` bound to Modernist `fbc1d6c8-b35f-4df6-9044-a64d2675427b` per the bridge seed protocol (`finalize_plan`, `create_support_js`, `copy_files` `deck-stage.js` from the marshal pilot), and the poster is pushed and read back — **Then** the README carries the project id, etag and measured values, and `herald deck status pyforge-unifying-strategy` reports it linked
**And** the structure reference's arc and section order are preserved — this story changes facts and the mirror, not the shape

### Story 20.13: The bridge sees the family — `herald deck status` reports all ten linked
**Type:** fix • **Effort:** S • **Deps:** S-20.3–S-20.12 • **FR/AD:** `spec-deck-family-currency` CAP-4 • `spec-pyforge-herald` HER-3 (status)
**Surface:** `presentations/pyforge-*/README.md` (`## Design project` sections normalized to the canonical two-line shape through `registry.register`), the `.herald/bridge-state.json` bootstrap (gitignored — its derivation documented in `docs/specs/presentation-deck.md`), and `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` only if `_status_for_slug` is found not to read the README registry fallback
**Given** `herald deck status --repo-root .` reported all fifteen decks `linked: false` on 2026-09-13 because no bridge state exists and every README section predates the canonical shape (DW-1-5-1) — **When** the ten README sections are registered canonically and the state is bootstrapped from them — **Then** `herald deck status` lists the ten PyForge-branded decks `linked: true` with their project ids, and a fresh clone reproduces that answer from the READMEs alone
**And** no second registry is invented — the README section stays the human-readable record and `bridge-state.json` the operational one, exactly as `registry.py` and `state.py` already divide them

### Story 20.14: `deck-facts --refresh` rewrites stale marked literals from the ledger
**Type:** feature • **Effort:** S • **Deps:** S-20.2 • **FR/AD:** `spec-deck-family-currency` CAP-6 (minted 2026-09-13 from the Wave A round-1 landing)
**Surface:** `scripts/deck_facts.py` (`--refresh`), `tests/scripts/test_deck_facts.py`, `docs/specs/presentation-deck.md` (one line in the poster sub-step)
**Given** the four round-1 posters landed and their own landings moved the fleet and station counts they print (`848/878` → `852/878`, herald `69/81` → `73/81`), so `deck-facts <slug> --check` reads `mismatch` on those marks the moment the reconcile merged — detected by CAP-5, repairable only by hand — **When** `deck-facts <slug> --refresh` re-derives the ledger and rewrites each `data-fact` mark whose text differs from its row, choosing the replacement by the old literal's shape (the row's `value`, or the `shown_as` variant at the same index, keeping a leading `v`) — **Then** the poster is byte-identical outside the rewritten spans, `--check` reports 0 `mismatch` for every rewritten mark, each rewrite is printed as `refreshed  <id>  "<old>" -> "<new>"`, nested marks and marks with no row are printed as `skipped` with the reason, and the exit code is 0
**And** the verb never touches prose, unmarked tokens, `facts.yaml` rows it did not derive, or any other file; a `--with-tests` flag combines as for derive so a poster that prints `tests_collected` keeps its row

## Epic 21: The whole deck family moves together (spec-deck-family-lockstep)

**Spec binding.** `spec-deck-family-lockstep` CAP-1..6 (herald; Dream `docs/dreams/deck-family-lockstep.md`). CAP-6 added 2026-09-16, found live dispatching Story 21.4 (Story 21.12).
Epic 20 made one surface of ten decks true; this epic finishes the rest. Measured on main at Epic 20's
closeout (2026-09-13): every deck README says its head and Infographic Deck are **"standalone ahead"**;
the heads are 14–48 KB against posters of 112–295 KB; every marp source and both PPTX per deck are
dated 2026-07/08; four chain decks never entered the wave (15–19 KB stubs, no `facts.yaml`, registry
sections `registry.read` cannot parse); `herald deck status` sees 10 of 15. **HARD boundaries (Spec
constraints):** derive, never re-author — the head's body *is* the standalone's body, so a transform
replaces the divergence rather than re-checking it; the marked-fact contract and the three hazards
`--refresh` cannot cover stay in force; never restrict size at authoring; one PR per deck with the
`maintenance` label; worktrees and physical paths, never `bmad-switch` in a parallel agent; checks stay
advisory; no new engine and no change to `deck_export.py`'s semantics. **Order:** 21.1–21.3 are tooling
every later story leans on; 21.4–21.5 sweep the ten; 21.6–21.9 are the four chain decks (independent,
four agents); 21.10–21.11 close the registry and the Design proof.

### Story 21.1: `deck-trio` derives the Infographic head from the standalone
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** `spec-deck-family-lockstep` CAP-1
**Surface:** `scripts/deck_trio.py` (new), `pixi.toml` (a `deck-trio` task), `tests/scripts/test_deck_trio.py`, `docs/specs/presentation-deck.md` (§ *Artifact dependency tree* — the head becomes derived)
**Given** the trio's own definition says the standalone is the head's body with no `x-dc` wrapper and its styles moved into `<head>` (`presentation-deck.md` § *Artifact dependency tree*), while on main the two have diverged by 100 KB and a README flag ("standalone ahead") tracks the fact by hand — **When** `deck-trio <slug> --head` transforms the current standalone into `project/<Persona> - Infographic.dc.html` (wrap the body in `<x-dc>`, move the `<style>` block into `<helmet>`, add the `support.js` script tag and the `data-dc-script` block with a `$preview` sized to the measured page) — **Then** the head's body is byte-identical to the standalone's modulo those three mechanical differences, it renders, and a second run changes nothing
**And** the verb refuses rather than guesses when the standalone is missing or its `<head>` style block cannot be located, and it never edits the standalone

### Story 21.2: `deck-trio` derives the Infographic Deck from the standalone
**Type:** feature • **Effort:** M • **Deps:** S-21.1 • **FR/AD:** `spec-deck-family-lockstep` CAP-1
**Surface:** `scripts/deck_trio.py` (`--deck`), `tests/scripts/test_deck_trio.py`, `docs/specs/presentation-deck.md`
**Given** the Infographic Deck is defined as "the same sections re-laid as 1920×1080 slides" and today's copies are the July stubs — **When** `deck-trio <slug> --deck` emits `project/<Persona> - Infographic Deck.dc.html` with one `<section data-label>` per numbered section of the standalone plus the act bands as section dividers, honouring the prototype contract the extractor reads — **Then** the slide count equals the standalone's numbered-section count plus its act bands, every slide carries a `data-label`, the file renders, and a second run changes nothing
**And** no content is invented: a section that will not fit a slide is split mechanically, never summarised

### Story 21.3: `deck-facts` refreshes every marked surface, not just the poster
**Type:** feature • **Effort:** M • **Deps:** S-21.1, S-21.2 • **FR/AD:** `spec-deck-family-lockstep` CAP-2
**Surface:** `scripts/deck_facts.py` (surface discovery for `--check` / `--refresh`), `tests/scripts/test_deck_facts.py`, `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-currency/facts-ledger.md` (the sweep's definition)
**Given** `--refresh` walks only `project/<Persona> Infographic standalone.html`, so a ledger move leaves the head, Infographic Deck, exec summary and marp sources stale and unreported — **When** both verbs walk every marked surface of the deck and report per surface — **Then** one `--refresh` after a tracked ledger changes leaves every surface at 0 `mismatch`, `--check` names the surface on every finding, and a deck whose extra surfaces carry no marks behaves exactly as today
**And** the `unvisited` cross-check and every skip reason apply per surface, so no surface can be silently missed
**And** *(absorbed 2026-09-14 from the folded Story 23.4 — `spec-design-sync-loop` CAP-4)* `--refresh` reports each literal it overrode **together with the value it replaced**, so a number a human retyped in Design and then lost to the ledger is visible in the run output, never silent

### Story 21.4: The ten decks' trios re-derived, refreshed and pushed
**Type:** feature • **Effort:** L • **Deps:** S-21.1, S-21.2, S-21.3 • **FR/AD:** CAP-1, CAP-2
**Surface:** `presentations/pyforge-*/project/*- Infographic.dc.html`, `*- Infographic Deck.dc.html`, `presentations/pyforge-*/README.md` (the "standalone ahead" note retires)
**Given** ten READMEs carry a "standalone ahead" flag that exists only because the surfaces diverged — **When** `deck-trio` re-derives both surfaces for each of the ten and `deck-facts --refresh` brings their marks current, each pushed to its Design project and read back — **Then** every head and Infographic Deck matches its standalone, every surface reports 0 `mismatch`, each README records the new etags, and **no README says "standalone ahead"**
**And** each deck lands as its own PR with the `maintenance` label, at most four in flight
**Note (2026-09-14):** this is a one-time sweep of the ten using 21.1–21.3 plus `herald deck push` and the CAP-4 read-back. If `spec-design-sync-loop` Story 23.8 (`herald deck sync-all`) lands first, this story is satisfied by the loop's first real run over the ten — the acceptance criteria stand either way; only the hands change.
**Outcome (2026-09-17):** Push + read-back leg complete, resuming after Story 21.12 fixed the `mcp` 2.2.0 transport symbol drift that had blocked it (verified live: `resolve_design_credential()` now succeeds). `herald deck push`'s own CLI verb only covers the CAP-5 marp-regenerated export, not these `project/` trio files, so the push used `pyforge.herald.transport.mcp_transport.McpTransport` directly (`finalize_plan` → `write_files`, inline `data` — `local_path` is not implemented server-side today). Pushed the Infographic head for all ten decks, and the Infographic Deck for the six where `deck-trio --deck` succeeds (doctor, genesis, mason, scribe, steward, warden); read every pushed file back and proved it byte-identical (SHA-256 compare for the nine decks under the 256 KiB `read_file` cap; `render_preview` → curl → strip-harness for pyforge-warden, whose files exceed it — this also surfaced a new SDK finding: `read_file` offset/limit paging silently corrupts a file when a very long single line straddles a page boundary, recorded in pyforge-warden's README). All ten READMEs got a new dated Ledger entry with the new etags, and no README says "standalone ahead" any more (verified by grep across all ten). **Partial by design, not a gap:** DW-4 (`_bmad-output/implementation-artifacts/deferred-work.md`, still `open`, re-verified live for all four) blocks `deck-trio --deck` for atlas/herald/marshal/unifying-strategy — their pre-existing, stale Infographic Deck stubs were left untouched (not pushed, not regressed); this is pre-existing poster non-conformance, out of this story's own Code Map, unchanged by this session. Landed as ten separate PRs (one per deck, `maintenance`-labeled), all left open for operator review — not merged by the agent: #1394 (atlas), #1395 (doctor), #1396 (genesis), #1397 (herald), #1398 (marshal), #1399 (mason), #1400 (scribe), #1401 (steward), #1402 (unifying-strategy), #1403 (warden). Story status set to `in-review` (Tier-3 `implementation-artifacts/sprint-status.yaml` is a shared symlink outside this worktree and could not be edited directly; the tracked `sprint-status-ledger.yaml` twin was hand-set to match instead).

### Story 21.5: The exec summaries and the export set follow the same ledger
**Type:** feature • **Effort:** L • **Deps:** S-21.3 • **FR/AD:** CAP-3
**Surface:** `presentations/pyforge-*/project/*- Executive Summary.dc.html`, `presentations/pyforge-*/src/marp/*`, `presentations/pyforge-*/src/pptx/*`
**Given** every exec summary and marp source is dated 2026-07/08 and both PPTX derive from them, so the Standard export set is stale in every format — **When** the exec summary and marp sources are brought to the current ledger with marked facts and `deck-export <slug>` regenerates the standalone HTML and both PPTX — **Then** all six companions per deck are current and dated the rebuild day, and `deck-facts <slug> --check` reports the exec summary and marp surfaces clean
**And** the derived artifacts are regenerated, never hand-edited — the rule `deck_export.py`'s own docstring states

### Story 21.6: unity-data-stack rebuilt to the standard
**Type:** feature • **Effort:** M • **Deps:** S-21.3 • **FR/AD:** CAP-4 • Wave C
**Surface:** `presentations/unity-data-stack/project/Unity Data Stack Infographic standalone.html`, `presentations/unity-data-stack/facts.yaml`, `presentations/unity-data-stack/README.md` • Design project `0494e2b0-7132-43b7-8ff2-4b4b42fa8384`
**Given** an 18,588 B July stub with 7 sections, no act bands, no inline diagram and no fact ledger, for a chain whose Spec lives under `pyforge-atlas` — **When** it is rebuilt to `infographic-standard.md` from a derived `facts.yaml` (the chain's own Spec, Dream and the tracked ledgers; a chain deck has no station package, so package and CLI rows are absent by design) — **Then** it meets every floor, reports 0 unmarked / 0 mismatch, renders clean at 1240 px, and is pushed and read back byte-identical
**And** facts with no derivable row are enumerated by name rather than guessed

### Story 21.7: wasm-analytics-stack rebuilt to the standard
**Type:** feature • **Effort:** M • **Deps:** S-21.3 • **FR/AD:** CAP-4 • Wave C
**Surface:** `presentations/wasm-analytics-stack/{project/Wasm Analytics Stack Infographic standalone.html,facts.yaml,README.md}` • Design project `45c841c6-e807-4fee-a92a-f8e89cb890b4`
**Given** an 18,713 B July stub (6 sections, 0 acts, 0 SVG, no ledger) — **When / Then / And** exactly as Story 21.6, for the Wasm analytics chain

### Story 21.8: deckcraft rebuilt to the standard
**Type:** feature • **Effort:** M • **Deps:** S-21.3 • **FR/AD:** CAP-4 • Wave C
**Surface:** `presentations/deckcraft/{project/Deckcraft Infographic standalone.html,facts.yaml,README.md}` • Design project `59c42e9c-7c90-431d-adae-b0021dd3f727`
**Given** a 15,774 B July stub (6 sections, 0 acts, 0 SVG, no ledger) for the chain that is Herald's own editable-PPTX engine — **When / Then / And** exactly as Story 21.6, for deckcraft

### Story 21.9: presenton-pixi-image rebuilt to the standard
**Type:** feature • **Effort:** M • **Deps:** S-21.3 • **FR/AD:** CAP-4 • Wave C
**Surface:** `presentations/presenton-pixi-image/{project/Presenton Conda-Native Infographic standalone.html,facts.yaml,README.md}` • Design project `c824a332-8e43-4b17-bf84-f38307085289`
**Given** a 19,028 B July stub (7 sections, 0 acts, 0 SVG, no ledger) for Mason's air-gapped Presenton chain — **When / Then / And** exactly as Story 21.6, for presenton-pixi-image

### Story 21.10: The registry sees all fourteen decks
**Type:** fix • **Effort:** S • **Deps:** S-21.6, S-21.7, S-21.8, S-21.9 • **FR/AD:** CAP-4
**Surface:** `presentations/{unity-data-stack,wasm-analytics-stack,deckcraft,presenton-pixi-image}/README.md`, the `.herald/bridge-state.json` bootstrap documented in `docs/specs/presentation-deck.md`
**Given** Story 20.13 registered the ten PyForge decks and left the four chain decks unlinked with sections `registry.read` cannot parse (it raises on deckcraft's 24-line body) — **When** each is re-registered through `registry.register` with history preserved under `### Provenance`, and the bootstrap is re-run — **Then** `herald deck status --repo-root .` reports **all fourteen** decks linked with their project ids, and a fresh clone reproduces it from the READMEs alone
**And** ~~`agentic-sdlc` stays unlinked by design (BMAD-branded, no poster in `project/`)~~ — **superseded 2026-09-14** by the operator's `design-sync-loop` scope ruling (*every* presentation project gets a twin and a registry section): `agentic-sdlc` is registered by `spec-design-sync-loop` Story 23.2, so this story leaves it untouched rather than declaring it unlinked by design

### Story 21.11: One deck proves the Design loop end to end
**Type:** feature • **Effort:** M • **Deps:** S-21.4 • **FR/AD:** CAP-5
**Surface:** one deck's `project/` artifacts, its `README.md` ledger, `docs/specs/presentation-deck.md` (§ *The MCP bridge* — the worked pull)
**Given** every push this far has been repo→Design, so the bridge's editing half is unexercised on current content and no rebuilt deck carries a Design-side improvement — **When** one deck is opened in Claude Design, visually improved there by a human, and pulled back byte-exact (`render_preview` → curl → strip the `data-omelette-injected` harness and the blank line the serve layer inserts after `<head>`) — **Then** git holds the improved bytes, the read-back is byte-identical, the README records the etag and the date, and `deck-facts <slug> --check` still reports 0 `mismatch` (the visual pass must not break a mark)
**And** the pull is the closing act: no Design-side edit is complete until git holds it

### Story 21.12: The transport speaks the `mcp` SDK it actually has pinned
**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** CAP-6
**Surface:** `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/mcp_transport.py`, `src/shared/packages/pyforge-herald/pyproject.toml`, `pixi.toml`
**Given** `pyforge-herald`'s pixi environment resolves `mcp==2.2.0`, which renamed `mcp.client.streamable_http.streamablehttp_client` to `streamable_http_client`, while `mcp_transport.py:641` (Story 1.2, 2026-08-07) still imports the retired name and `pyproject.toml`'s own floor (`mcp>=1.28.1`) never anticipated the rename — so `herald deck push`/`pull`/`watch` die on `ImportError` before any credential or network check, blocking Story 21.4's and 21.6–21.9's push+read-back leg and all of `spec-design-sync-loop`'s Epic 23 — **When** the transport imports whichever streamable-HTTP client symbol the pinned `mcp` SDK actually exports, and `pyproject.toml`'s floor is bumped to agree with `pixi.toml`'s environment pin — **Then** the reproducer import no longer fails, a real `herald deck push` against a live Design project round-trips (push, then read back byte-identical), and `deck-facts <slug> --check` reports 0 `mismatch` afterward
**And** confined to this module — atlas's parallel `mcp` 2.x usage is untouched (verified no shared symbol use), no change to `resolve_design_credential` or the fallback transport (FR-22/Story 1.3) unless the fix's own shape requires it

## Platform floor addendum — 2026-09-07

Every story in this epic set builds and tests against **Python 3.14 only**.
`pyforge-herald`'s `requires-python` was raised `>=3.12` -> `>=3.14` by marshal Story 32.2
(`spec-fleet-consistency-standard` CAP-5) to match the interpreter the workspace actually
installs. No story's acceptance criteria change; recorded here so a future story is not
written against a 3.12 assumption the estate cannot produce.

## Epic 22: The public Pages root is one dossier (spec-pyforge-pages)

**Spec binding.** `spec-pyforge-pages` CAP-1..5 (herald; Dream `docs/dreams/pyforge-pages.md`,
`specified` 2026-09-13). The PyForge dossier lives in `docsite/content/dossier.yml`; Pages,
the gallery, and the Claude Artifact build are renders. Kedro-Viz stays at `/kedro-viz/`.
One `deploy-pages` caller. After steward 54.5, python-foundry re-derives this surface —
it is kernel cargo, not a 44.4 fold. **HARD boundaries:** never a second Pages deploy;
`build.py` never blanket-`rmtree`s `docs/dashboard/`; `environment.yaml` stays
byte-identical; verify is advisory in CI; `maintenance` label; not Lane 1.

### Story 22.1: The dossier is the source and Pages is a render
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** `spec-pyforge-pages` CAP-1..5
**Surface:** `docsite/**` (new), `pixi.toml` (`[feature.site]` + `site` environment), `.github/workflows/dashboard.yml` (build into `docs/dashboard/`), `.gitignore` (owned outputs), `docs/dashboard/index.html` (replaced by the landing render)
**Given** Pages publishes `docs/dashboard/` as Kedro-Viz plus a retired Guildhall landing, and the dossier exists only as a published artifact — **When** the rebased `pyforge-pages` bundle lands (`docsite/` + `feature.site` + `dashboard.yml` build step) — **Then** `pixi run -e site site-check` is green, `pixi project export conda-environment -e build` leaves `environment.yaml` unchanged, Kedro-Viz remains at `/kedro-viz/`, and `dashboard.yml` is still the only `deploy-pages` caller
**And** the PR carries the `maintenance` label; `verify_claims.py` is advisory in CI (`continue-on-error`); foundry lists this surface as rebuild cargo after 54.5 with the same CAP-N


## Epic 23: The Design sync loop — one command keeps every twin and its family true (spec-design-sync-loop)

**Spec binding.** `spec-design-sync-loop` CAP-1..8 (herald; Dream `docs/dreams/design-sync-loop.md`,
`specified` 2026-09-14). Minted the afternoon the second manual CAP-6 sweep landed (PR #1361) from the
operator's four requirements and four rulings, all recorded on the Dream: presentations *and* design
systems in scope, two retired projects excluded by name; **Design wins, then the ledger re-applies**;
PowerPoints both ways per deck (Marp-derived default, `.potx`-filled where declared); the dossier site
extended with a family page per deck, run on demand from a session.

**Re-scoped the same evening (operator, "duplicate functionality between Herald's epics and stories")
from eight stories to six.** Read against the code, four of the first eight re-described verbs the
kernel already ships or stories Epic 21 already holds: `herald deck pull` *is* Design-wins (etag
short-circuit, otherwise Design's bytes overwrite local, never a merge) and `herald deck watch` is its
continuous form; `herald deck push` already pushes the standalone poster changed-only by content hash;
`deck-facts --refresh` over every marked surface is Story 21.3. So: **23.3 and 23.4 are folded** (holes
kept, not renumbered — the repo's "reserved hole" precedent) — 23.3's `--all` sweep and overwritten-edit
report live in 23.8, 23.4's override report is an AC on 21.3; **23.5 narrows** to the `.potx` path and
the derived-file stamps (the Marp path is 21.5); **23.6 narrows** to what `deck push` lacks — the binary
PPTX push Story 5.1 deferred and the read-back proof as a verb. Every remaining story is a delta over
something that exists, named in its Given. **HARD boundaries (Spec constraints):** git is the archive
of record and the source of facts — `facts.yaml` is never pulled; binds-never-re-mints — the loop
*calls* `deck-facts`, `deck-export`, `deck-trio`, the kernel's bridge verbs, DesignSync and
`docsite/build.py`; one Pages deployment; session-run and therefore idempotent; measure the artifact,
never the container; exclusions by name with a reason, never by heuristic. **Order:** 21.1 → 21.2 →
21.3 first (tooling, serial); then 23.1 ∥ 23.2 beside 21.5; then 23.5 / 23.6 / 23.7; 23.8 last — its
first real run over the ten *is* Story 21.4.

### Story 23.1: The account is enumerated and reconciled against the registry
**Type:** feature • **Effort:** M • **Deps:** S-21.10 • **FR/AD:** `spec-design-sync-loop` CAP-1
**Surface:** `src/shared/packages/pyforge-herald/src/pyforge/herald/registry.py` (exclusion + design-system entries), `.../herald/state.py`, `.../herald/cli.py` (`deck status` gains the account view), `presentations/README.md` (the registry's exclusion list), tests.
**Given** `list_projects` returns the account in pages of 20 and `herald deck status` only knows what a README registry section names, so `PyForge six-quarter roadmap`, `LLM Knowledge Bases`, `Agentic AI SLDC deck`, the two retired projects and the three design systems are invisible to the bridge **When** the loop enumerates every project the login returns (paging), classifies each as presentation / design system / excluded-by-name, and reconciles the set against the registry **Then** `herald deck status` lists every project the account returns with `linked` / `mirrored` / `excluded (<reason>)` / `untwinned`, and no project is absent from the report
**And** `REMOVED-PyForge Unifying Strategy` and `Local recipes repository connection` are excluded by name in `presentations/README.md` with their recorded reasons — never by a name heuristic

### Story 23.2: Every presentation has a local twin; design systems are mirrored as libraries
**Type:** feature • **Effort:** M • **Deps:** S-23.1 • **FR/AD:** `spec-design-sync-loop` CAP-2
**Surface:** `presentations/agentic-sdlc/README.md` (registry section), `presentations/six-quarter-roadmap/**` (new twin), `presentations/llm-knowledge-bases/**` (new twin), `presentations/_design-systems/{modernist,broadsheet,nocturne}/**` (new mirrors), `herald deck seed`/`pull` as needed, tests.
**Given** `agentic-sdlc` has a Design project but no registry section, two presentation projects have no twin at all, and the three design systems the decks bind to exist only in Design **When** each presentation gets a `presentations/<slug>/` twin with its prototype pulled byte-exact and a machine-owned registry section, and each design system is pulled byte-exact to `presentations/_design-systems/<name>/` **Then** the fourteen decks, `agentic-sdlc`, `six-quarter-roadmap` and `llm-knowledge-bases` all resolve through `registry.read`, the three mirrors match Design byte-for-byte, and a second pull writes nothing
**And** no deck glob (`presentations/pyforge-*/…`, the four chain decks) matches the design-system home, so no currency check, trio derivation or Pages page picks them up

**Story 23.3 — folded 2026-09-14 (reserved hole; do not renumber).**
`herald deck pull` already takes Design's bytes wholesale when the etag moved and `herald deck watch`
does it continuously; what this story would have added — the `--all` sweep over every twin and the
report line naming a repo-side edit that Design had not seen and was overwritten — lives in Story 23.8.
CAP-3 in the Spec is narrowed to that delta.

**Story 23.4 — folded 2026-09-14 (reserved hole; do not renumber).**
Re-deriving `facts.yaml` at the current tree and running `deck-facts --refresh` over every marked
surface after a pull is Story 21.3 plus currency CAP-6; the one new requirement — report each overridden
literal with the value it replaced — is now an acceptance criterion on 21.3. CAP-4 in the Spec is
narrowed to that delta.

> **Re-keyed 2026-09-17** (`rekey-2026-09-17.md`): the four surviving stories were renumbered
> 23.5→23.3, 23.6→23.4, 23.7→23.5, 23.8→23.6 so the feed keys are contiguous. The fold notes above
> and the epic's *Order* line keep their pre-rekey numbers as historical prose; every `Deps:` field
> and in-story pointer below was repointed to the live numbers on 2026-09-18 (the stale `S-23.5`
> self-dependency on 23.5 and the phantom `S-23.7` on 23.6 had made both stories permanently
> not-ready to `marshal factory drain`'s dependency graph).

### Story 23.3: The `.potx` path — template-filled PowerPoints, and every derived file stamped
**Type:** feature • **Effort:** M • **Deps:** S-21.5 • **FR/AD:** `spec-design-sync-loop` CAP-5 • binds `spec-deck-family-lockstep` CAP-3 (the Marp path)
**Surface:** each deck README's registry section (a declared `.potx`, the chosen path), the derive stage calling `pptx-spec`/`pptx-fill` (Story 15.1) for a `.potx` deck and `deck-export` otherwise, derived-file stamps (tree + etag) on every trio/export artifact, tests.
**Given** Story 21.5 regenerates the export set from the refreshed Marp sources for every deck, and the operator ruled PowerPoints come **both ways per deck** — Marp-derived by default, template-filled where a deck declares a `.potx` — while no derived file today records which tree or Design etag it was derived at **When** a registry section may declare a `.potx`, the derive stage routes that deck through `pptx-spec`/`pptx-fill` and every other deck through `deck-export`, and every derived artifact carries a stamp naming the tree and etag it derived at **Then** a `.potx` deck yields a genuinely editable PPTX from its template, a Marp deck yields exactly what 21.5 yields, and the stamps make a stale derived file detectable without opening it
**And** a host without Chrome reports `derive-skipped: no chrome` for the Marp-PPTX step and the run continues

### Story 23.4: PowerPoints push back, and every push proves itself
**Type:** feature • **Effort:** M • **Deps:** S-23.3 • **FR/AD:** `spec-design-sync-loop` CAP-6 • closes Story 5.1's deferred binary-push follow-up
**Surface:** `.../herald/deck_pipeline.py` (`push_exports` gains the PPTX pair once a binary `write_files` shape is proven live; a `--prove` read-back), `.../herald/state.py`, each deck README's ledger section (etag row), tests.
**Given** `herald deck push` already pushes the standalone poster changed-only by content hash and etag-guarded per file, but skips both PPTX because no binary `write_files` wire shape has ever been proven (Story 5.1's recorded deferral), and the read-back proof the 2026-09-14 sweep used is a curl-and-strip recipe an agent runs by hand **When** a binary push is proven live on one PPTX and adopted for the pair, and the push verb reads every pushed file back through the serve URL with the harness stripped **Then** read-back is byte-identical for 100% of pushed files, the etag is recorded in the README ledger and bridge state, and a second push pushes nothing
**And** a read-back mismatch is a refusal that names the file, never a warning

### Story 23.5: The family is browsable and downloadable on Pages
**Type:** feature • **Effort:** M • **Deps:** S-23.3 • **FR/AD:** `spec-design-sync-loop` CAP-7 • `spec-pyforge-pages` CAP-1/CAP-2 (bound, not re-minted)
**Surface:** `docsite/build.py`, `docsite/templates/**` (family page + index), `docsite/content/**` (deck family config), `docs/dashboard/**` (render), tests / `site-check`.
**Given** `docsite/build.py` publishes the standalone infographics into a gallery and nothing else — no PPTX, Marp, executive summary or per-deck page is published or downloadable **When** the site gains one family page per registered deck and an index **Then** each family page shows the poster, the Infographic Deck and the Executive Summary in view, offers the PPTX(s) and Marp sources as downloads, stamps each with its etag and tree, and `site-check` passes
**And** `dashboard.yml` is still the only `deploy-pages` caller and Kedro-Viz is still at `/kedro-viz/`

### Story 23.6: One command, idempotent, reported
**Type:** feature • **Effort:** M • **Deps:** S-21.3, S-21.5, S-23.1, S-23.2, S-23.3, S-23.4, S-23.5 • **FR/AD:** `spec-design-sync-loop` CAP-8, CAP-3 (the sweep half)
**Surface:** `.../herald/cli.py` (`deck sync-all`, `--slug`, `--dry-run`), `pixi.toml` (a `deck-sync-all` task), the run report, `docs/specs/presentation-deck.md` § *The MCP bridge* (the loop replaces the runbook), tests.
**Given** every stage exists as its own verb — `status` (23.1), the adopt path (23.2), `pull`/`watch` (kernel), `deck-facts --refresh` over every surface (21.3), `deck-trio` (21.1/21.2), `deck-export`/`pptx-fill` (21.5/23.3), `push` with proof (23.4), the family page (23.5) — and an agent runs them from memory **When** `herald deck sync-all` runs them in that order for every registered deck (or one `--slug`): enumerate → pull every twin whose etag moved → refresh → derive → push → prove → publish, and prints a per-deck report — pulled / **overwrote-local** (a repo-side edit Design had not seen, named) / overrode / derived / pushed / published / unchanged **Then** two consecutive runs leave the second reporting every deck `unchanged` with zero writes to git or Design
**And** `--dry-run` prints the same report without writing, and the README/spec runbook points at the command rather than the steps

## Epic 24: What Epic 23's four landings deferred (spec-pyforge-herald CAP-48..50)

Minted 2026-09-18 from the station Dream's same-day Realization-log entry (Dream-append-first). Epic 23
drained to zero today — 23.1 (#1459), 23.2 (#1461), 23.5 (#1463), 23.6 (#1465), all landed by
`marshal factory dispatch` on the Claude harness — and each dispatched session deferred exactly one thing
it could not settle from inside its worktree, twinned as DW-FU-23-2 / DW-FU-23-5 / DW-FU-23-6 in
`deferred-work-ledger.md`. One story per deferral; each closes its DW row with named evidence. **HARD
boundaries:** binds-never-re-mints (24.1 guards a verb that exists, 24.2 gates a build that exists, 24.3
proves a command that exists); one Pages deployment; a live proof is opt-in and operator-run, never a
default gate and never a second PR gate.

### Story 24.1: The windowed Design read never loops on a stalled window
**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** `spec-pyforge-herald` CAP-48 • closes DW-FU-23-2
**Surface:** `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` (`_windowed_read`), a typed error in the pipeline's error module, `tests/unit/test_deck_pipeline.py`, `planning-artifacts/deferred-work-ledger.md` (DW-FU-23-2 → done with the test as evidence).
**Given** `_windowed_read` breaks only when `window.last_line >= window.total_lines` and never checks that `last_line` advanced between calls, so a server that repeatedly returns the same window loops forever (Story 23.2's Edge Case Hunter finding; every live call paged forward, so reachability is unproven) **When** a window whose `last_line` did not advance past the previous window's raises a typed pagination error naming the file and the stalled line **Then** a fake transport returning the same `(last_line, total_lines)` pair twice raises that error on the second window, and every existing live-shaped fixture (the 3377-line and 136,293-byte pulls) still pages to completion byte-exact
**And** the error is a refusal that names the file, never a warning or a silent truncation

### Story 24.2: The docsite has a PR gate
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** `spec-pyforge-herald` CAP-49 • closes DW-FU-23-5 • `spec-pyforge-pages` CAP-1 (bound, not re-minted)
**Surface:** `.github/workflows/` (one new `pull_request` lane, path-filtered to `docsite/**`, `docs/dashboard/**` render inputs and the workflow itself, running `docsite/build.py --check` and `site-check`), `pixi.toml` (`pr-preflight` gains the same leg; `site-check` task reused, not re-minted), `docs/how-to/presentation-deck.md` § verify checklist (names the lane), `planning-artifacts/deferred-work-ledger.md` (DW-FU-23-5 → done citing the lane's first green run).
**Given** no `pull_request`-triggered workflow and no `pr-preflight` leg references `docsite` or `site-check` (verified 2026-09-18: `dashboard.yml` runs the build on `push: branches: [main]` only, and `pyforge-herald-test` has zero coverage of `docsite/`), so 23.5's 296-line family-page change merged with every gate green **When** a PR that touches the docsite runs `build.py --check` + `site-check` before merge, locally and in CI **Then** a fixture regression (a family-page template with an unrendered Jinja tag) reds the lane and `main` is green, `pr-preflight` predicts the lane, and `dashboard.yml` is still the only `deploy-pages` caller
**And** the lane is path-filtered so a `recipes/`-only or station-only PR never runs it, and Kedro-Viz stays at `/kedro-viz/`

### Story 24.3: The second `sync-all` run is proven unchanged on a real deck
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** `spec-pyforge-herald` CAP-50 • closes DW-FU-23-6 • listed in `spec-pyforge-doctor:CAP-77`'s `live-proof-surfaces.md` (bound, not re-minted)
**Surface:** `pixi.toml` (an opt-in `deck-sync-proof` task gated on `HERALD_LIVE_SYNC_PROOF=1`), `src/shared/packages/pyforge-herald/src/pyforge/herald/sync_all.py` (a `--proof-dir` that writes both reports and the etag/tree stamps; no new stage), `.herald/sync-proof/<slug>/` (gitignored runtime output; the operator commits the two reports as the story's evidence under `planning-artifacts/specs/spec-pyforge-herald/sync-proof-2026-09-1x.md`), `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/live-proof-surfaces.md` (one new row: herald `sync-all` idempotency), `planning-artifacts/deferred-work-ledger.md` (DW-FU-23-6 → done citing the run).
**Given** 23.6's idempotency AC is proven over hand-written fakes and one live smoke that exercised only the skipped path, because no dispatch environment has live Claude Design credentials — the proof needs a person **When** one opt-in command runs `sync-all --slug <seeded deck>` twice against live Design and writes both per-deck reports plus the stamps to a proof dir **Then** the second report is all-`unchanged` with zero git writes and zero Design writes, the artifacts are recorded, and the surface is catalogued as live-proof-only so a static pass never claims it
**And** the task is never in the default gate or any CI lane, and the operator-run half is stated as such in the story's completion note — this story is `done` when the recorded run exists, not when the task does

## Epic 25: Herald runs from the Guild env (spec-pyforge-herald CAP-51)

Minted 2026-09-20 from the station Dream's entry of the same date (operator ruling: only `pyforge-guild` exists at runtime). A new epic because Epic 24 is `done`. One story; the env side is steward 63.6.

### Story 25.1: The deck pipeline runs from the Guild env

As a fleet operator running herald where only `pyforge-guild` exists,
I want `deck_pipeline.py` and `sync_all.py` to shell `deck-export`, `deck-facts` and `deck-trio` through `-e pyforge-guild`,
So that a deck sync never depends on the recipe factory's environment.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-herald CAP-51 • cross-project gate: the three tasks must be in `guild-tasks` first (steward 63.6) — a ledger `blocked`/`backlog` flip the operator makes, per AGENTS.md
**Surface:** `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py:497-527` (`DeckExporter` argv), `sync_all.py:348-401` (`FactsRefresher`, the trio step), `tests/unit/test_deck_pipeline.py:2465` and the sync-all tests (argv assertions).
**Given** three shell-outs name `-e local-recipes` for tasks that are herald's own
**When** they name `-e pyforge-guild` and the tasks live in `guild-tasks`
**Then** the argv assertions read the Guild env; `deck-sync-proof`'s opt-in live run still passes; steward 63.6's guard lists no herald offender
**And** `pyforge-herald-test` green
**Outcome (2026-09-20):** done, hand-driven in PR #1551 with steward 63.6 (the gate resolved in one landing) — see the tracked spec's Auto Run Result.

## Epic 26: The dossier states the cutover's control plane (spec-python-foundry-cutover fnd:CAP-14)

Minted 2026-09-25 from steward's `docs/dreams/pyforge-unifying-strategy.md` § *Consolidation —
2026-09-25* (Input 2, folded from PR #1576). A new epic because Epic 22 is `done`. The capability
is steward's (`spec-python-foundry-cutover` fnd:CAP-14); the surface is herald's `docsite/`, so the
story lives here and steward carries index row 67.6. One story; PR #1576's `dossier.yml` diff is
reference only, never merged.

### Story 26.1: The dossier reads the A→B cutover as control-plane fact

As an operator or Smith running the strangler,
I want the dossier's Estate, Foundation, Synthesis and Verified sections to state where the cutover stands, each claim tied to evidence,
So that I read the cutover's state in one place instead of reconstructing it from ledgers, PIN files and chat.

**Type:** docs • **Effort:** M • **Deps:** — • **FR/AD:** fnd:CAP-14 • cross-station: steward index 67.6 flips `done` when this closes; reference payload PR #1576 (branch `docs/pyforge-estate-whitepaper`, 118 insertions in `dossier.yml`)
**Surface:** `docsite/content/dossier.yml` (Estate, Foundation, Synthesis and Verified sections), `docsite/` templates only if a new section needs one, herald tests that assert dossier structure.
**Given** the dossier (re-verified 2026-09-13) is a forensic inventory of A's stations, and the cutover's state — A/B roles, modes, `pyforge.cutover_root`, the four campaign verbs — lives in the Spec, the capability ledger and B's `PIN.md`
**When** this story lands
**Then** the Estate section states A (`local-recipes`: control plane, oracle, root of record until the flip, never archived) and B (`python-foundry`: lasting root, engines rebuilt from Frame + Spec), the modes with "never `move`", and the four campaign verbs each with a done / not-done line; SBOM claims are labelled A-side; the Verified section cites, per claim, `docs/foundry/capability-ledger.yaml`, B's `case-list.md`, or a named CI run
**And** `pixi run -e site site-check` is green, and no claim reads the cutover as flipped or B as a mirror of A
**Status:** backlog

## Currency reconciliation — 2026-09-20 (fleet consistency pass)

*Operator ruling 2026-09-20: every station's PRD, spine and epics are re-stamped in the same pass,
grace period or not, so the whole chain reads current for the foundry cutover. Trigger: the
station Spec's `.memlog.md` gained a 2026-09-20 event — the fleet consistency pass reconciled every
tracked story spec's frontmatter against the sprint ledger, matched each "Ledger status" line,
reconstructed missing Auto Run Results from `main`'s landing commits, fixed invalid frontmatter,
and let `sprint-ledger-sync` roll the epic keys up (`spec→prd→arch→epics` cascade). Bookkeeping only:
no requirement, decision, story or AD changes in this epics. `updated:` bumped to record that the
check ran.*

## Currency reconciliation — 2026-09-25

`arch→epics` edge after the spine re-stamp of 2026-09-25. Epic 26 / Story 26.1 minted from
steward's 2026-09-25 consolidation (`spec-python-foundry-cutover` fnd:CAP-14 — the dossier as the
cutover's control plane; steward index row 67.6). Every Story heading still maps 1:1 to a
`sprint-status-ledger.yaml` key; the Tier-3 feed was repaired from the tracked twin first
(stale-slug orphans dropped). `updated:` bumped.
