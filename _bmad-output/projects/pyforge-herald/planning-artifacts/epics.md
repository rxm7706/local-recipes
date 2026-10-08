---
epics_role: canonical
# The single canonical story source for this station: every `### Story` heading here maps
# 1:1 to a sprint-status-ledger.yaml story key. Exactly one `canonical` per station (marshal:AD-72).
project_name: pyforge-herald
epicCount: 35  # 2026-10-07: re-measured, 35 epic keys in the ledger (fleet_scan.parse_sprint_status); Epics 33-35 had been minted 2026-09-29..10-03 without a bump. 2026-09-28 (night): Epics 29-32 appended (spec-pyforge-herald CAP-54..CAP-57); 32 epic keys in the ledger (measured with fleet_scan.parse_sprint_status; 28 before this mint). 2026-09-28: Epic 28 appended (spec-pyforge-herald CAP-53); 28 epic keys in the ledger (measured with fleet_scan.parse_sprint_status; 27 before this mint). 2026-09-27: Epic 27 appended (spec-pyforge-herald CAP-52); 27 epic keys in the ledger (measured with fleet_scan.parse_sprint_status; 26 before this mint). Prior 2026-09-13: Epic 22 added (spec-pyforge-pages) — the 22 had gone stale by four epics (23-26 never bumped it). Dated snapshot; the ledger enumerates.
storyCount: 125  # 2026-10-08: +1 for Story 27.6 (fix, no CAP); 125 story keys in the ledger, 116 done once Stories 30.2, 33.1 and 34.1 landed (fleet_scan.parse_sprint_status). 2026-10-07: re-measured, 124 story keys in the ledger (fleet_scan.parse_sprint_status), 108 done; Stories 33.1, 34.1, 35.1 and 35.2 had been minted without a bump. 2026-09-28 (night): +7 for Epics 29-32 / Stories 29.1-29.2, 30.1-30.2, 31.1-31.2, 32.1 (120 story keys in the ledger, measured; 113 before this mint; 29.1 and 29.2 are minted blocked on steward 74.1). 2026-09-28: +2 for Epic 28 / Stories 28.1-28.2 (113 story keys in the ledger, measured; 111 before this mint). 2026-09-27 (later): +1 for Story 27.5 (operator ruling D8; its ledger key is minted blocked on steward 71.2), 111 story keys in the ledger, measured. 2026-09-27: +4 for Epic 27 / Stories 27.1-27.4 (110 story keys in the ledger, measured; 106 before this mint). Prior 2026-09-13: + Story 22.1 — the 55 had gone stale (Epics 13-26 never bumped it). Dated snapshot; the ledger enumerates.
status: in-progress  # 2026-09-28 (night): Epics 29-32 (7 stories) backlog; 29.1 and 29.2 blocked on steward Story 74.1, the rest backlog behind station-local Deps. 2026-09-28: Epic 28 (2 stories, both backlog; 28.2 on S-28.1) backlog. 2026-09-27: Epic 27 (5 stories; 27.1-27.4 backlog, 27.5 blocked on steward 71.2) backlog; Epic 19 in-progress with 19.2 blocked on DW-13-6-1. Prior 2026-09-13: Epic 22 opens Story 22.1; Epics 19 and 21 still have unstarted work.
updated: "2026-10-08"   # AMENDED 2026-10-08 (docs-site helper): Story 27.6 minted (fix, no CAP, no flag) in Epic 27: the docs site builds from a clean checkout. The Epic List table re-measured from the ledger (E27 6/1; E28, E29 and E30 2/2, E33 and E34 1/1 after their landings; 125 stories, 116 done). Prior: RE-STAMPED 2026-10-07: chain-currency cascade (arch -> epics) validated against the spine's § Currency reconciliation — 2026-10-07 (no AD amended); no epic or story added or changed; the Epic List table and epicCount/storyCount re-measured from the ledger (35 epics, 124 stories, 108 done). See § Currency reconciliation — 2026-10-07. Prior: RE-STAMPED 2026-10-03 (night): Story 35.2 added to Epic 35 (fix: Story 35.1's post-landing follow-ups). Prior: RE-STAMPED 2026-10-03 (Phase 4+5): Epic 35 / Story 35.1 minted (fix, no CAP): herald's 21 open medium and low deferrals, operator rulings of 2026-10-03. Prior: RE-STAMPED 2026-09-29 (evening): Epic 34 / Story 34.1 minted (spec-one-chain-per-station CAP-11 relay; no herald CAP or FR). Prior 2026-09-29   # RE-STAMPED 2026-09-29: Epic 33 / Story 33.1 minted (spec-one-chain-per-station CAP-11 relay; no herald CAP or FR). Prior 2026-09-28 (night): chain-currency cascade (spec -> PRD -> arch -> epics) for FR-10.1..FR-10.6 / CAP-54..CAP-57; Epics 29-32 / Stories 29.1-29.2, 30.1-30.2, 31.1-31.2, 32.1 minted; amended the same night: every flagged story names its reader (pyforge.core.flags.read_boolean, steward 75.1's contract; django_pyforge.flags on portal paths). Prior 2026-09-28
# 2026-09-28  # RE-STAMPED: chain-currency cascade (spec -> PRD -> arch -> epics) for FR-9.1..FR-9.2 / CAP-53; Epic 28 / Stories 28.1-28.2 minted. Prior 2026-09-27
# 2026-09-27  # RE-STAMPED: chain-currency cascade (spec -> PRD -> arch -> epics) for FR-8.1..FR-8.5 / CAP-52; Epic 27 / Stories 27.1-27.5 minted (27.5 and the 27.2 rewrite follow the operator rulings of 2026-09-27, D7/D8). Prior 2026-09-25
# 2026-09-25  # RE-STAMPED 2026-09-25: chain-currency cascade (arch -> epics); Epic 26 minted (26.1, spec-python-foundry-cutover fnd:CAP-14). Prior 2026-09-20
---

# pyforge-herald — Epic Breakdown

## Fold provenance (2026-09-17)

Station Spec spec-pyforge-herald reminted absorbed capabilities as CAP-1..47. Historical stories keep sequential epic numbers 1..23; Epic 23 story gaps closed (23.5–23.8 → 23.3–23.6). This heading is the INV-A citation window for the folded set (`spec-pyforge-herald` CAP-1..47).

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
| **E13** | The live backend — a ship records itself | 6 | 6 |
| **E14** | A deck is proven to look right | 3 | 3 |
| **E15** | Editable decks — the PowerPoint-native pipeline | 2 | 2 |
| **E16** | Exporter hook spec | 1 | 1 |
| **E17** | Herald owns its skill, persona, and one portal job | 2 | 2 |
| **E18** | Herald renders, announces and slides with the suite | 3 | 3 |
| **E19** | Herald in effect (fleet readiness 2026-09-09) | 4 | 3 |
| **E20** | The deck family stays current (spec-deck-family-currency) | 14 | 14 |
| **E21** | The whole deck family moves together (spec-deck-family-lockstep) | 12 | 12 |
| **E22** | The public Pages root is one dossier (spec-pyforge-pages) | 1 | 1 |
| **E23** | The Design sync loop — one command keeps every twin and its family true (spec-design-sync-loop) | 6 | 6 |
| **E24** | What Epic 23's four landings deferred (spec-pyforge-herald CAP-48..50) | 3 | 3 |
| **E25** | Herald runs from the Guild env (spec-pyforge-herald CAP-51) | 1 | 1 |
| **E26** | The dossier states the cutover's control plane (spec-python-foundry-cutover fnd:CAP-14) | 1 | 1 |
| **E27** | The docs site matches BMAD-METHOD's pattern (spec-pyforge-herald CAP-52) | 6 | 1 |
| **E28** | Each deck keeps one current version of each export (spec-pyforge-herald CAP-53) | 2 | 2 |
| **E29** | Each current export is also kept in object storage (spec-pyforge-herald CAP-54) | 2 | 2 |
| **E30** | A deck is readable in the browser from its HTML twin (spec-pyforge-herald CAP-55) | 2 | 2 |
| **E31** | The docs site deploys to a second host from the same artifact (spec-pyforge-herald CAP-56) | 2 | 0 |
| **E32** | A deck exports as a native, editable .pptx through pptxgenjs-plus (spec-pyforge-herald CAP-57) | 1 | 0 |
| **E33** | The genesis deck counts archived Dreams where they now live (spec-one-chain-per-station CAP-11) | 1 | 1 |
| **E34** | Herald cites the deck how-to, not the retiring intake stub (spec-one-chain-per-station CAP-11) | 1 | 1 |
| **E35** | Phase 4+5 of the deferral burn-down: herald's open medium and low deferrals | 2 | 2 |
| **Total** | | **125** | **116** |


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
**Surface:** `docsite/content/dossier.yml` (Estate, Foundation, Synthesis and Verified sections), `docsite/` templates only if a new section needs one, `src/shared/packages/pyforge-herald/tests/unit/test_dossier_structure.py` (new — the structural oracle: every item under the Verified section carries a non-empty `source` naming a `docs/foundry/capability-ledger.yaml` id, a `case-list.md` case id or a CI run URL; no Estate text calls `local-recipes` archived or read-only).
**Given** the dossier (re-verified 2026-09-13) is a forensic inventory of A's stations, and the cutover's state — A/B roles, modes, `pyforge.cutover_root`, the four campaign verbs — lives in the Spec, the capability ledger and B's `PIN.md`
**When** this story lands
**Then** the Estate section states A (`local-recipes`: control plane, oracle, root of record until the flip, never archived) and B (`python-foundry`: lasting root, engines rebuilt from Frame + Spec), the modes with "never `move`", and the four campaign verbs each with a done / not-done line; SBOM claims are labelled A-side; the Verified section cites, per claim, `docs/foundry/capability-ledger.yaml`, B's `case-list.md`, or a named CI run
**And** `pixi run -e site site-check` is green; `test_dossier_structure.py` passes in `pyforge-herald-test` and reds on a planted Verified item without a `source`; no claim reads the cutover as flipped or B as a mirror of A; co-governor reconcile: a memlog entry on every Spec `spec-surface-check` names, then a scoped stamp per Spec, never a bare `--write-baseline`
**Status:** done
**Outcome (2026-09-26):** landed as `df7a651aa9` (Merge pyforge-herald/26-1 into main); tracked spec `specs/spec-26-1-the-dossier-reads-the-a-b-cutover-as-control-plane-fact.md` carries the review triage. (Inline status corrected 2026-09-27; it had read `backlog` since the mint.)

## Epic 27: The docs site matches BMAD-METHOD's pattern (spec-pyforge-herald CAP-52)

Minted 2026-09-27 from the station Dream's 2026-09-20 entry. The operator's ask (09:55Z) was to *"design our docs and docs deployment to GitHub Pages to match what BMAD-METHOD itself does, so that we can reuse their patterns, skills and workflows"*. The research is `research/docs-site-bmad-method-pattern-2026-09-20.md`, and its six decisions are D1–D6 on the Spec memlog; the operator's 2026-09-27 rulings on Pages URLs and `pr-preflight` cost are D7 and D8. A new epic, because Epic 26 is `done`. Epic 22 (CAP-43..47, `done`) made the dossier the Pages root. This epic puts the docs shelf at the root and moves docsite's whole output under `/herald/`, with a redirect page at each HTML path it served at the root before (`/` excepted), which supersedes CAP-44's root and path clauses. **Cross-station gate:** Story 27.5 is minted `blocked` until steward Story 71.2 (`spec-pyforge-steward:CAP-159`, "run the lanes CI would run, read from the workflow files") has landed; the operator flips it. It is a ledger gate because marshal's `Deps:` parser is station-local. **HARD boundaries:** no page under `docs/` moves or is renamed. A vendored upstream file is byte-identical to the recorded `bmad-code-org/BMAD-METHOD` commit or it is not vendored (re-vendor, never fork). `dashboard.yml` stays the only `actions/deploy-pages` caller and keeps its path, because steward's `tests/meta/test_invariants.py` and `src/platform/tests/test_console_parity_homes.py` read it. Nothing under `src/shared/packages/pyforge-doctor/` or another station's tree is edited: `docs/map.yaml` is doctor's registry, read and never written. A `pixi.toml` change is a hand edit, then `pixi lock` and the `environment.yaml` regeneration in the same PR, because the pre-shell hook refuses a live `pixi add`. Every PR carries the `maintenance` label.

### Story 27.1: The docs shelf builds as a Starlight site in place

As an operator who wants to read the docs shelf outside the repo,
I want `docs/` to build as a BMAD-METHOD-shaped Astro + Starlight site without moving or editing a page,
So that upstream's docs tooling applies here and the shelf is readable somewhere other than the repo.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-herald CAP-52 (FR-8.1; D3, D4, D6); AD-21, AD-4
**Surface:** `docs-site/` (new, vendored from `bmad-code-org/BMAD-METHOD` `docs-site/` at one recorded commit, MIT): `package.json` and `package-lock.json` (upstream's `astro` / `@astrojs/starlight` ranges; the scripts for content this repo does not have are dropped), `.nvmrc`, `astro.config.mjs` (`site`/`base` from `SITE_URL`, unset meaning `/`; no locales; one sidebar group per quadrant, autogenerated until 27.3), `src/content.config.ts` (local: the collection is `docs/{tutorials,how-to,reference,explanation}/**` plus `index.md` and `404.md`; the title comes from frontmatter, else from the page's first `# ` heading, and that heading is not rendered twice; `<quadrant>/README.md` routes to the quadrant index), `src/content/docs` (a symlink to `../../../docs`), `scripts/validate-doc-links.js`, `scripts/validate-sidebar-order.js` and `scripts/fix-doc-links.js` (byte-identical to upstream), and `README.md` (the upstream SHA, the sha256 of each vendored file, the MIT notice, and what is local). Also `docs/index.md` (new landing page: what the shelf is, the four quadrants, links to `/herald/` (the dossier, infographics and deck families) and `/dashboard/kedro-viz/`) and `docs/404.md` (new). In `pixi.toml`, `[feature.site.dependencies]` gains `nodejs` at `[feature.python]`'s pin (`>=24.19.0,<27.0,!=25.*`), plus the tasks `docs-site-install` (`npm ci`, `cwd = "docs-site"`) and `docs-site-build` (the Astro build to `docs-site/build/site/`, depending on `docs-site-install`). Then `pixi.lock` (`pixi lock` after the hand edit), `environment.yaml` (regenerated, expected byte-identical), `.gitignore` (`docs-site/node_modules/`, `docs-site/build/`, `docs-site/.astro/`), and `src/shared/packages/pyforge-herald/tests/meta/test_docs_site.py` (new; a structural oracle that needs no Node: the symlink target, the pin equal to `[feature.python]`'s, both tasks with their `cwd`, the `.nvmrc` major inside the pin, `docs/index.md` and `docs/404.md` present, each vendored file's sha256 equal to the value `docs-site/README.md` records, the three ignores).
**Given** `docs/` holds the Diátaxis shelf — 60 `docs/map.yaml` pages, none with a `title:` key, each opening with a `# ` heading, quadrant indexes named `README.md` — and nothing publishes it
**When** `pixi run -e site docs-site-build` runs on a clean checkout
**Then** it exits 0 and `docs-site/build/site/` holds `index.html`, `404.html`, and one page per `docs/map.yaml` entry, each titled from its heading with that heading rendered once; the quadrant indexes are served at `/tutorials/`, `/how-to/`, `/reference/` and `/explanation/`; no page from `docs/{dreams,specs,governance,intake,foundry,dashboard}/` is built
**And** `git diff --stat origin/main -- docs/` lists only `docs/index.md` and `docs/404.md` as added; `pixi project export conda-environment -e build` leaves `environment.yaml` byte-identical; `test_docs_site.py` passes in `pyforge-herald-test`
**Status:** done

### Story 27.2: One Pages artifact carries the docs site, the dossier and the dashboard

As an operator publishing the estate's pages,
I want one Pages artifact with the Starlight site at the root, docsite's whole output under `/herald/` with every old root URL redirected there, and the dashboard tree under `/dashboard/`, deployed by the one workflow that already deploys Pages,
So that the docs, the dossier and Kedro-Viz share one site, no existing public URL silently changes meaning, and no second `deploy-pages` caller races the first.

**Type:** feature • **Effort:** M • **Deps:** S-27.1 • **FR/AD:** spec-pyforge-herald CAP-52 (FR-8.2; D2, D7, D8); AD-21; supersedes CAP-44's root and path clauses, keeps CAP-44/CAP-49's single-deployment rule
**Surface:** `docsite/tools/assemble_pages.py` (new; a pure `assemble(...)` and a `--check` mode). It mounts docsite's whole output under `docs-site/build/site/herald/` (`docsite/build.py --out … --check`) and copies the tracked `docs/dashboard/` tree, minus its `README.md`, under `docs-site/build/site/dashboard/`. It then writes one redirect page for every HTML file docsite wrote, except the root `index.html`, at that file's old root path (for example `dossier/index.html` → `herald/dossier/`, `decks/<slug>/infographic-deck.html` → `herald/decks/<slug>/infographic-deck.html`). The set is derived from the `herald/` tree, never a hand-kept list — 44 pages on 2026-09-27, out of 45 HTML files. Each target is relative, so it works under any Pages `base`. It refuses, with exit 1 and the path named, when a mount point or a redirect path already exists in Starlight's output. The root `index.html` is the single named exception: Starlight's landing (`docs/index.md`, Story 27.1) owns `/` and links to `/herald/`. Non-HTML files (`assets/site.css`, `.nojekyll`, and the 69 deck downloads under `decks/<slug>/downloads/`) cannot carry an HTML redirect on static Pages. They move to `herald/` with no redirect, so their old paths return 404 rather than serve different content. `--check` asserts `index.html`, `404.html`, `herald/index.html`, `herald/dossier/index.html`, `dashboard/kedro-viz/index.html`, the `kedro-viz/` redirect, and one redirect page per HTML file under `herald/` except its root index, each resolving to its target. It also asserts that every relative `href`/`src` in the `herald/` tree resolves inside the artifact. In `pixi.toml`, `[feature.site.tasks]` gains `pages-build` (`docs-site-build`, then the herald and dashboard mounts and the redirects) and `pages-check` (the assembler's `--check`, depending on `pages-build`). `pr-preflight` is not changed: its `{ task = "site-check", environment = "site" }` leg stays exactly as today, and Story 27.5 owns the `pr-preflight` lane. Also: `docs-site/astro.config.mjs` (`redirects`: `/kedro-viz/` → `/dashboard/kedro-viz/`); `docsite/content/site.yml` (the Kedro-Viz neighbour `href` becomes `../dashboard/kedro-viz/`, `rel`-prefixed so it resolves at every depth under `/herald/`, and its comment is updated); `docsite/README.md` and `docs/dashboard/README.md` (the new mount points and the redirects). `.github/workflows/dashboard.yml` is reshaped into upstream `docs.yaml`'s two jobs with its path kept: a build job (checkout; setup-pixi `environments: site`, one `pixi-version:` pin, registry site `dashboard.yml setup-pixi`; `configure-pages`, whose `base_url` feeds `SITE_URL`; `pixi run --frozen -e site pages-check`; the advisory `site-verify` step, kept `continue-on-error`; `upload-pages-artifact` of `docs-site/build/site`) and a deploy job (`needs: build`, `environment: github-pages`, `deploy-pages`). Its triggers, permissions and `concurrency: pages` stay as they are, and its header keeps the race note. `.github/workflows/docsite-check.yml` replaces its pip-installed `build.py --check` leg with `pixi run --frozen -e site pages-check`, so the PR lane predicts the reshaped deploy. Its `pull_request` and `push` path filters gain `docs/**` and `docs-site/**`, because the lane now builds `docs/`; this moved here from 27.4 (D8), and Story 27.5's selection keys on these paths. `.gitignore` drops the `docs/dashboard/{index.html,.nojekyll,assets/,dossier/,infographics/,decks/,artifact/}` block once nothing writes there. `src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py` is new: `dashboard.yml` is the only file under `.github/workflows/` that uses `actions/deploy-pages`; it uploads `docs-site/build/site`; its concurrency group is `pages`; it triggers on `push: main` and `workflow_dispatch`; `docsite-check.yml` runs `pages-check` and carries both new path filters; `pr-preflight`'s `site-check` leg is unchanged. Unit tests over a temp tree cover the happy path, a redirect written per HTML page, a refused collision (a mount or a redirect path already present in Starlight's output), the root exception, and a missing mount.
**Given** the Pages root is the dossier landing page that `dashboard.yml` builds into `docs/dashboard/` (CAP-44), serving `/`, `/dossier/`, `/infographics/…`, `/decks/…` and `/artifact/dossier.html`, with Kedro-Viz at `/kedro-viz/`, and Story 27.1's site builds to `docs-site/build/site/`
**When** `pixi run -e site pages-build` and then `pixi run -e site pages-check` run
**Then** both exit 0, and the artifact holds `index.html` (Starlight), `herald/index.html`, `herald/dossier/index.html`, `dashboard/kedro-viz/index.html`, a `kedro-viz/` page that redirects to `/dashboard/kedro-viz/`, and a redirect page at each former root HTML path (`dossier/index.html` → `/herald/dossier/`, and so on for the infographics, deck family pages and `artifact/dossier.html`) except `/`. A planted collision (a Starlight page at a redirect path or a mount point) or a removed mount makes `pages-check` exit 1 and name the path
**And** `dashboard.yml` is the only workflow using `actions/deploy-pages` and it uploads `docs-site/build/site`; `pr-preflight`'s `site-check` leg is unchanged; steward's `tests/meta/test_invariants.py` and `src/platform/tests/test_console_parity_homes.py` pass unedited; `pixi run -e pyforge-guild pixi-version-check` is green; `test_pages_artifact.py` passes in `pyforge-herald-test`
**Status:** done

### Story 27.3: The sidebar is generated from docs/map.yaml order

As a docs author,
I want the site's sidebar to follow `docs/map.yaml`'s page order, generated at build time,
So that the shelf keeps one registry, doctor's map, and reordering a page takes one edit there.

**Type:** feature • **Effort:** S • **Deps:** S-27.1 • **FR/AD:** spec-pyforge-herald CAP-52 (FR-8.3; D1); AD-21 • Kinship: doctor 30.2 owns `docs/map.yaml` and its schema; this story only reads it
**Surface:** `docs-site/scripts/sidebar_from_map.py` (new, local). It reads `docs/map.yaml` and writes `docs-site/src/sidebar.generated.json`: one group per quadrant in the order the quadrants first appear in `map.yaml`, each item a page slug in `map.yaml` order, and a quadrant's `README.md` as its group index. Its `--check` mode exits 1, naming the page, when a `map.yaml` path has no file, when a quadrant page is missing from `map.yaml`, or when a page is listed twice. Also: `docs-site/astro.config.mjs` (the sidebar is read from the generated JSON; the per-quadrant autogenerate from 27.1 is removed); `pixi.toml` (a `docs-site-sidebar` task in `[feature.site.tasks]`, which `docs-site-build` depends on); `.gitignore` (`docs-site/src/sidebar.generated.json`, generated and never tracked); and `src/shared/packages/pyforge-herald/tests/unit/test_docs_site_sidebar.py` (new; it imports the generator by path and checks that order is preserved, that swapping two fixture entries swaps the output, that a missing page, an unmapped page or a duplicate exits 1, and that the live `docs/map.yaml` generates with no finding).
**Given** 27.1's sidebar is autogenerated per quadrant (alphabetical), while `docs/map.yaml` is the shelf's registry with an explicit page order
**When** `pixi run -e site docs-site-build` runs (it regenerates the sidebar first)
**Then** the built sidebar lists every `map.yaml` page exactly once, grouped by quadrant, in `map.yaml` order; swapping two entries in `map.yaml` alone swaps them in the built sidebar; no page under `docs/` gains a `sidebar:` key
**And** `docs-currency-check` and `docs-map-hygiene-check` report no new finding; `test_docs_site_sidebar.py` passes in `pyforge-herald-test`
**Status:** done

### Story 27.4: The docs validators gate every PR

As a reviewer,
I want upstream's link and sidebar validators to run on every PR that touches the docs, and locally in `pr-preflight`,
So that a dead link or a broken sidebar order cannot merge while every gate is green.

**Type:** feature • **Effort:** M • **Deps:** S-27.2, S-27.3 • **FR/AD:** spec-pyforge-herald CAP-52 (FR-8.4; D5, D6); AD-21
**Surface:** In `pixi.toml`, `[feature.site.tasks]` gains `docs-site-validate-links` (`node docs-site/scripts/validate-doc-links.js`), `docs-site-validate-sidebar` (`node docs-site/scripts/validate-sidebar-order.js`, then `python docs-site/scripts/sidebar_from_map.py --check`) and `docs-site-validate` (both); `pr-preflight` gains `{ task = "docs-site-validate", environment = "site" }`, with its description saying why. In `.github/workflows/docsite-check.yml`, a step runs `pixi run --frozen -e site docs-site-validate`; the `docs/**` and `docs-site/**` path filters are already there from 27.2 (D8). `pr-preflight`'s `docs-site-validate` leg needs only node (no npm install, no build), so it runs unconditionally until steward Story 71.2 selects it by `docsite-check.yml`'s paths, like every other lane. The 16 link findings the vendored `validate-doc-links.js` reported on 2026-09-27 are fixed in their pages, never by editing the validator: `docs/dreams/README.md` (`../../AGENTS.md`, `../specs/`), `docs/dreams/archive/pyforge-unifying-strategy-2026-08-23-topology.md` (`marshal-token-economy.md`), `docs/how-to/antigravity-developer-startup.md` (a `file:///` path), `docs/how-to/disaster-recovery.md` (`restore.md`), `docs/how-to/feedstock-platform-expansion.md` (two `.claude/skills/…` links), `docs/how-to/ocp-cluster-bringup.md` (`../../../ingest/…`), `docs/how-to/restore-operations.md` (`DR.md` twice), `docs/reference/README.md` (three directory links), `docs/reference/conda-forge-packaging-inventory-operations_replay.md` (`scripts/` and `conf/` links) and `docs/tutorials/getting-started.md` (`../how-to/`). A dead link is repaired or removed, a directory link points at its index page, and a repo file outside `docs/` is linked by its `https://github.com/rxm7706/local-recipes/blob/main/<path>` URL. `src/shared/packages/pyforge-herald/tests/meta/test_docs_site_validators.py` is new: the three tasks are registered; `docsite-check.yml` carries the step; `pr-preflight` carries the leg; the vendored validators' sha256 still equals what `docs-site/README.md` records.
**Given** the vendored `validate-doc-links.js` exits 1 over `docs/` (268 files scanned, 16 findings in 10 files, measured 2026-09-27) and no lane runs it
**When** the findings are fixed in their pages and the validators are wired as pixi tasks, a `docsite-check.yml` step and a `pr-preflight` leg
**Then** `pixi run -e site docs-site-validate` exits 0 on the story's tree; a planted dead link in any quadrant page makes it exit 1 and name the page; two pages with the same `sidebar.order` in one directory make `docs-site-validate-sidebar` exit 1
**And** `docsite-check.yml` runs the validators on a PR that touches `docs/**`; `pr-preflight` carries the leg; the vendored validators are byte-identical to the recorded upstream commit; `test_docs_site_validators.py` passes in `pyforge-herald-test`; the fixed pages keep `docs-currency-check` and `docs-map-hygiene-check` free of new findings
**Status:** backlog

### Story 27.5: pr-preflight runs the Pages build check only when docsite-check.yml's paths change

As a contributor pushing a branch,
I want `pr-preflight` to run the Pages build check (`pages-check`: `npm ci`, the Astro build, the dossier mount) only when my diff touches the paths that trigger `docsite-check.yml` in CI,
So that a change far from the docs does not pay for a site build, and the local run still predicts the CI lane that would run.

**Type:** feature • **Effort:** S • **Deps:** S-27.2 • **FR/AD:** spec-pyforge-herald CAP-52 (FR-8.5; D8); AD-21 • cross-project gate: steward Story 71.2 (`spec-pyforge-steward:CAP-159`) must have landed first — the ledger key is minted `blocked` and the operator flips it, per AGENTS.md (marshal's `Deps:` parser is station-local)
**Surface:** `pixi.toml`, and only `pr-preflight`'s lane list: its `{ task = "site-check", environment = "site" }` leg is replaced by `{ task = "pages-check", environment = "site" }`, with its description saying why. It is a replacement, not an addition, because `pages-check` depends on `pages-build`, which already runs `docsite/build.py --check` (the whole of `site-check`). Keeping both would build the dossier twice per preflight. `site-check` stays a pixi task for the local docsite loop (`docsite/README.md`). The lane is selected by steward Story 71.2's workflow-derived filter, which reads `docsite-check.yml`'s own `paths` (set by 27.2) through the lane-to-workflow binding 71.2 defines. No second, hand-kept path list is written anywhere. `src/shared/packages/pyforge-herald/tests/meta/test_preflight_pages_lane.py` is new. It checks that `pr-preflight` carries `pages-check` in `site` and no `site-check` leg, that the lane is bound to `docsite-check.yml` the way 71.2 reads it, and, against `docsite-check.yml`'s `paths` under GitHub's glob semantics, that a diff touching only `src/shared/packages/pyforge-marshal/` matches no path while one touching `docs/how-to/x.md` matches.
**Given** steward Story 71.2 has landed (pr-preflight selects each lane by its CI workflow's `paths`), and Story 27.2 made `docsite-check.yml` run `pages-check` on `docs/**`, `docs-site/**`, `docsite/**`, `docs/dashboard/**`, `presentations/**`, `pixi.toml` and the workflow itself
**When** `pr-preflight` selects its lanes for a fixture diff
**Then** a diff touching only `src/shared/packages/pyforge-marshal/` leaves `pages-check` unselected, and a diff touching `docs/how-to/x.md` selects it, as shown by 71.2's own selection report
**And** `test_preflight_pages_lane.py` passes in `pyforge-herald-test`; `pr-preflight` never runs `site-check` and `pages-check` together
**Status:** blocked

### Story 27.6: The docs site builds from a clean checkout

As an operator who builds the docs site from a fresh clone or in CI,
I want every file the Starlight config loads to be tracked, the URL helper vendored byte-identical from upstream, and a test that fails when a docs-site import resolves to a file git does not track,
So that `docs-site-build` works on any checkout and Stories 27.2–27.4 build on a site that exists.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-herald CAP-52 (FR-8.1; D6); AD-21 rule 5 (re-vendor, never fork) and rule 4 (built outputs stay ignored); Story 27.1 shipped the site • repairs the divergence the PRD's and spine's § Currency reconciliation — 2026-10-07 recorded and did not repair • Dream 2026-10-08 (docs-site helper)
**Flag:** none (a fix, spec-feature-flag-governance Q1)
**Surface:** `docs-site/src/lib/site-url.mjs` (new and tracked: upstream `bmad-code-org/BMAD-METHOD` `docs-site/src/lib/site-url.mjs` at the recorded commit `561eeedf386bc7cb164c577c423dc4484056a759`, git blob `7bc47ba8b85f88ae009d6b322c730440c745a9da`, 1032 bytes, sha256 `734c233ba2d1e601771caf05b55a99d3db35576fe0305e8e341e5e18daeb3520`, byte-identical); `docs-site/README.md` (the helper joins the vendored sha256 table and leaves "Local-only files"); `.gitignore` (one negation, `!docs-site/src/lib/`, in the Story 27.1 docs-site block; the general `lib/` rule at `:40` stays); `src/shared/packages/pyforge-herald/tests/meta/test_docs_site_imports_tracked.py` (new); `.github/workflows/pyforge-station-tests.yml` (herald's job also runs on `docs-site/**`: both `paths:` lists and herald's `job_paths`, as Story 28.1 did for `presentations/**`)
**Spec:** `planning-artifacts/specs/spec-27-6-the-docs-site-builds-from-a-clean-checkout.md`
**Given** `docs-site/astro.config.mjs:4` importing `./src/lib/site-url.mjs`, a file the root `.gitignore` rule `lib/` (`:40`) ignores and git has never tracked, so a fresh clone's `pixi run -e site docs-site-build` exits 1 at "Unable to load your Astro config" (measured on `054bb4e795`), while `tests/meta/test_docs_site.py` never resolves the config's imports
**When** the upstream helper is vendored and tracked behind a narrow `.gitignore` exception, and a meta test resolves every relative import in the tracked docs-site sources against `git ls-files`
**Then** in a fresh `git clone` of the story's branch, with `SITE_URL` and `GITHUB_REPOSITORY` unset, `pixi run -e site docs-site-build` exits 0 and writes `docs-site/build/site/index.html` and `404.html` (64 HTML pages on 2026-10-08); `git check-ignore -q docs-site/src/lib/site-url.mjs` exits 1, and `git check-ignore --no-index -q` still exits 0 for `lib/probe.py` and `docs-site/lib/probe.mjs`
**And** the meta test passes on the fixed tree, fails naming the path when the helper is untracked (`git rm --cached`, the mutation), and fails on a synthetic tree whose config imports an untracked or a missing file; `test_vendored_files_match_readme_sha256` checks the helper's sha256; `pixi run --frozen -e pyforge-herald pyforge-herald-test` green
**Status:** done

## Epic 28: Each deck keeps one current version of each export (spec-pyforge-herald CAP-53)

Minted 2026-09-28 from the station Dream's entry of the same date. It takes up the steward Dream's
2026-09-25 repo-size seed (`docs/dreams/pyforge-unifying-strategy.md`), which found `presentations/`
at 47% of the tracked tree and parked a "latest deck per topic" working set in the cutover's Story
44.5. The operator ruled on 2026-09-28 to spec it now, independent of the cutover: *keep the latest
deck per topic in `presentations/`; older dated versions are pruned or moved, and git history keeps
them.* Decisions D1–D5 are on the Spec memlog. Epic 28 is new, because Epic 27 belongs to CAP-52.

**Measured 2026-09-28** (`c660efec81`):
- `presentations/` holds 944 tracked files and 134.69 MB.
- 118 dated export kinds; 62 carry more than one date.
- 74 superseded files (26 `.pptx`, 36 `.md`, 12 `.html`), 54.14 MB, across 11 topics.
- After the prune: 870 files and 80.55 MB, with the tracked tree at about 232 MB.

**The rule (D2):** a kind is one directory, the filename stem before `-YYYY-MM-DD`, and the
extension. The newest date is the current version, and a `.stamp.json` sidecar goes with its
file. This is the rule `docsite/build.py` `_listed_files`, `deck_pipeline._newest_dated_match`,
`deck_export.find_source` and `deck_facts._marp_source` already apply, so the prune changes no
published or pushed byte.

**HARD boundaries:**
- Superseded exports are deleted with `git rm`, never moved to an archive folder (D1).
- The rule has no exceptions (D4).
- No undated file under `presentations/` is touched: `project/*.dc.html`, the standalone posters,
  `facts.yaml`, `README.md`. The one exception is Story 28.1's correction of
  `pyforge-unifying-strategy/README.md`'s artifact tree (D5).
- No steward-owned text is edited: the Charter, steward's deferred-work ledger, and
  `.steward/deck-integrity-baseline.json`. That baseline is gitignored and exists on neither
  checkout. Steward Story 59.4's `deck-drift` fingerprints the one pulled Design artifact given as
  `--path`, so far only ever a `project/*.dc.html`, so there is nothing to re-stamp.
- Story 44.5's estate-move filter is not touched.
- The spec-surface reconcile is a memlog entry naming every removed path, followed by one scoped
  stamp per Spec the detector names, never a bare `--write-baseline`.
- Every PR carries the `maintenance` label.

### Story 28.1: Each deck keeps one current version of each export

As a maintainer who clones, copies or ships `local-recipes`,
I want `presentations/` to carry only the current version of each dated deck export, and a check that reds a superseded one,
So that 54 MB of superseded exports stop riding in every working tree and copy while git history keeps them, and they cannot quietly regrow.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-herald CAP-53 (FR-9.1; D1–D5); AD-4 (amended 2026-09-28) • co-governing Specs: `spec-pyforge-core` (`spec-pyforge-core:CAP-8`'s station-tests lane; every station's `src/`), `spec-pyforge-doctor` (governs `docs/how-to/presentation-deck.md`)
**Surface:**
- `presentations/<topic>/src/{pptx,marp}/`: `git rm` every superseded dated export, the 74 files
  measured on 2026-09-28, re-derived at landing by the new module's own report, with any
  `.stamp.json` sidecar of a removed file.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_versions.py` (new, stdlib-only).
  - The D2 rule: `superseded(root)` returns each superseded export with its current version.
  - `python -m pyforge.herald.deck_versions [--root presentations]` prints one line per superseded
    file and exits 1 if there is any, 0 otherwise.
- `src/shared/packages/pyforge-herald/tests/meta/test_deck_working_set.py` (new). The live
  `presentations/` tree has zero superseded exports. Over fixture trees:
  - a kind with two dates reports the older one and names the newer
  - `<slug>-infographic` and `<slug>-infographic-deck-narration` stay separate kinds
  - a sidecar follows its file
  - undated files and single-date kinds are never reported
  - the CLI exits 0 or 1 to match
- `src/shared/packages/pyforge-herald/tests/unit/test_story_19_4_warden_deck.py`. Its three
  real-tree tests stop opening `pyforge-warden-deck-2026-09-10.pptx` and `-2026-07-15.pptx` by
  path, because both are superseded (D4). They read a deck regenerated from the tracked
  `presentations/pyforge-warden/src/content_plan.json` with `pptx_pipeline.run_fill` into
  `tmp_path` (a module-scoped fixture), and compare provenance against the one current
  `pyforge-warden-deck-*.pptx`, resolved by the module, never a pinned date.
- `.github/workflows/pyforge-station-tests.yml`: `presentations/**` joins both `on.paths` lists,
  and the herald leg of the `changes` job diffs `presentations` as well as its package. The `core`
  output is unchanged, so a `presentations/**`-only diff runs `herald-test` and not `core-test`.
- `docsite/build.py`: the `_listed_files` docstring only. The behaviour is unchanged; the
  docstring stops saying superseded exports stay on disk.
- `presentations/pyforge-unifying-strategy/README.md:29-35`: the artifact tree names the
  2026-09-15 files.
- `docs/how-to/presentation-deck.md`:
  - § Standard export set gains the one-version rule.
  - The pptx-fill exemplar line (`:536`) points at the regeneration command instead of the 09-10
    file.
  - The `.pptx` gotcha (`:659-660`) says a new dated export replaces its predecessor.
  - The worked examples keep their filenames as history (D5).
- `_bmad-output/projects/*/planning-artifacts/specs/spec-*/.memlog.md` for the reconcile entries,
  and `scripts/.spec-surface-baseline.json` for the scoped stamps.

**Given** `presentations/` carries 74 superseded dated exports (54.14 MB) beside their current versions, no check notices, and a deck-only PR runs no herald test
**When** the superseded exports are pruned and the rule, its meta test and the CI trigger land
**Then** `python -m pyforge.herald.deck_versions` exits 0 on the story's tree and exits 1 naming each planted superseded file and its current version; `git ls-files presentations | wc -l` and the tree's bytes drop by the pruned count and size, both recorded before and after in the story's Verification notes (944 → 870 and 134.69 → 80.55 MB on the 2026-09-28 tree); `pixi run -e site site-check` exits 0 and publishes the same 69 family downloads; the Story 19.4 tests pass against the regenerated deck
**And** `pyforge-station-tests.yml` selects `herald-test` for a `presentations/**`-only diff and steward's `test_workflow_path_filters_match.py` stays green; `spec-surface-check` is green after the memlog reconcile and one scoped stamp per Spec it names; `pyforge-herald-test` is green
**Status:** done

### Story 28.2: A new export replaces the version it supersedes

As a maintainer running `herald deck sync-all` or `deck-export`,
I want each writer of a dated export to retire the older versions of the kind it just wrote,
So that the one-version rule Story 28.1 checks holds after every sync, without a hand prune.

**Type:** feature • **Effort:** S • **Deps:** S-28.1 • **FR/AD:** spec-pyforge-herald CAP-53 (FR-9.2; D3); AD-4 (amended 2026-09-28) • co-governing Spec: `spec-pyforge-core` (every station's `src/`)
**Surface:**
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_versions.py` gains
  `retire_superseded(written)`. It deletes the strictly older dated versions of the written file's
  kind, and their `.stamp.json` sidecars, and returns what it removed.
  - It never deletes the written file, a newer version, another kind or an undated file.
  - When a newer version already exists, it removes nothing and reports the written file as
    superseded.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py`: `pull_marp_source`
  (`:808-842`), `pull_standalone_bundle` (`:908-937`) and `PptxTemplateExporter.export`
  (`:583-600`) call it after a successful write only.
- `scripts/deck_export.py`: `stamp_marp_kinds` (`:199-205`) and the three dated outputs (`:283-309`: the standalone,
  the infographic PPTX and the deck PPTX) call it after each successful write. It already imports `pyforge.herald.stamps`.
- `src/shared/packages/pyforge-herald/tests/unit/test_deck_versions.py` (new) and the writer tests
  in `tests/unit/test_deck_pipeline.py`, `tests/unit/test_sync_all.py` and
  `tests/scripts/test_deck_export.py`.

**Given** every dated writer adds a new file and none removes the one it supersedes, so a `sync-all` after Story 28.1's prune would regrow the tree
**When** a writer writes `<stem>-<newer date>.<ext>` beside `<stem>-<older date>.<ext>`
**Then** only the newer file of that kind remains, its sidecar with it; a failed write retires nothing; a backdated write (`DECK_EXPORT_DATE` older than the current file) removes nothing and is reported; other kinds and undated files are untouched; `python -m pyforge.herald.deck_versions` exits 0 after a fixture `sync-all`
**And** a second `sync-all` run still reports every deck `unchanged` with zero writes (CAP-36/CAP-50); `test_deck_versions.py` and the writer tests pass in `pyforge-herald-test`
**Status:** done

## Epic 29: Each current export is also kept in object storage (spec-pyforge-herald CAP-54)

Minted 2026-09-28 (night) from the station Dream's entry of the same night, which triaged the
airgapped-decks intake (`archive/docs/intake/airgapped_pptx_architecture_specification.md`). The
operator ruled that decks stay tracked and that each current export is *also* published to the
object store with a metadata row; bytes in PostgreSQL were rejected. Decisions D1–D4 are on the
Spec memlog, and AD-22 is new on the spine.

**Cross-station gate:** both stories are minted `blocked` until steward Story 74.1 has landed.
74.1 is the object-storage seam's first-consumer contract: the configuration names, the bucket and
prefix, and the Helm values. The operator flips the two keys. It is a ledger gate because
marshal's `Deps:` parser is station-local.

**HARD boundaries:**
- Decks stay tracked. AD-4 and CAP-53's one-version rule do not change, and CAP-35's downloads
  still build from tracked files.
- No bytes in PostgreSQL: no `BinaryField` and no `BYTEA`.
- `src/platform/` never imports `pyforge.*`, and the base herald package imports neither `django`
  nor the host's `config` modules.
- No `django-cors-headers`, and no route sends `Access-Control-Allow-Origin`.
- No new package path: the new modules live in `pyforge-herald` and `django-herald`.
- No steward-owned file is edited. The chart's bucket and prefix values and the seam contract are
  Story 74.1's.
- PostgreSQL stays at 17 (fnd:CAP-12).
- Every story spec carries the `pyforge.herald.deck_publish` flag block, and every PR carries the
  `maintenance` label.

### Story 29.1: herald deck publish puts each current export in the object store

As an operator inside the enterprise network,
I want `herald deck publish <slug>` to put each current export of a deck in the object store, with its metadata,
So that git stops being the only place the exports live, and the portal has something to serve.

**Type:** feature • **Effort:** M • **Deps:** S-28.1 • **FR/AD:** spec-pyforge-herald CAP-54 (FR-10.1; D1, D2); AD-22 • cross-project gate: steward Story 74.1 must have landed first — the ledger key is minted `blocked` and the operator flips it, per AGENTS.md (marshal's `Deps:` parser is station-local) • flag: `pyforge.herald.deck_publish`
**Surface:**
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_store.py` (new): the store port
  (`put_if_absent`, `head`, `open_stream`), its S3 adapter configured from the environment under
  Story 74.1's contract, and an in-memory fake for the suite.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_publish.py` (new). It resolves each
  current export through `pyforge.herald.deck_versions` (Story 28.1), hashes it with sha256,
  streams it to `<prefix>/sha256/<hex>` when that key is absent, and writes the deck's manifest,
  `<prefix>/manifests/<slug>.json`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py`: `herald deck publish <slug>
  [--dry-run]` and `herald deck exports <slug> --json`. With the flag OFF, both stay listed as
  disabled and exit 2.
- `src/platform/config/flags.json`: the key `pyforge.herald.deck_publish`, `defaultVariant` off.
- The flag is read through `pyforge.core.flags.read_boolean`, steward Story 75.1's contract. If
  75.1 has not landed, the story adds `read_boolean` to `pyforge.core` in exactly 75.1's shape
  (`src/shared/packages/pyforge-core/src/pyforge/core/flags.py` and its test), never a station-local reader.
- If the adapter's S3 client library is not already in the `pyforge-herald` and `pyforge-guild`
  environments: `pixi.toml` (a hand edit, then `pixi lock`), `pixi.lock`, and `environment.yaml`
  regenerated in the same PR, with `pyforge-station-tests` run before the push.
- Tests in the herald package: `tests/unit/test_deck_store.py`, `tests/unit/test_deck_publish.py`,
  `tests/meta/test_deck_store_import_boundary.py`, and an ON/OFF flag test.
**Given** each current export lives only in git, and the platform's object-storage seam has no consumer
**When** `herald deck publish <slug>` runs with the flag ON against a local store (the `platform-object-storage` silo server)
**Then** it exits 0; each current export sits at `<prefix>/sha256/<hex>` and reads back byte-identical; the manifest carries topic, kind, date, size, content type, sha256 and source commit for each; a second run uploads nothing; `herald deck exports <slug> --json` prints the records
**And** with the flag OFF both verbs are listed as disabled and exit 2 with a "flag off" message; the boundary test finds no `django` or `config` import in the base package; `pyforge-herald-test` is green
**Status:** done

### Story 29.2: The published exports are listed and streamed behind the herald role

As a reader inside the enterprise network,
I want the platform to know which exports are published and to stream one to me only when I hold the herald role,
So that a deck can be downloaded from the platform with no CORS hole and no bytes in the database.

**Type:** feature • **Effort:** M • **Deps:** S-29.1 • **FR/AD:** spec-pyforge-herald CAP-54 (FR-10.2; D3, D4); AD-22 • cross-project gate: steward Story 74.1 must have landed first — the ledger key is minted `blocked` and the operator flips it • flag: `pyforge.herald.deck_publish`
**Surface:**
- `src/shared/packages/django-herald/src/django_herald_portal/models.py` (new): `DeckExport`, a
  projection with no binary field; `migrations/0001_initial.py`; a `refresh_deck_exports`
  management command that upserts from `herald deck exports --json` through the portal's
  `PortalClient`.
- `src/platform/db/changelog/changes/` and `db.changelog-master.yaml`: one namespaced changeset for
  that migration, at the id the sqlmigrate extraction map assigns
  (`src/platform/tests/policy/test_sqlmigrate_extraction.py`).
- `src/shared/packages/pyforge-herald/src/pyforge/herald/station_api.py`:
  `GET /stations/herald/api/v1/deck-exports` and `GET /stations/herald/api/v1/deck-exports/{sha256}`,
  registered through the entry point the host already loads by name
  (`src/platform/config/station_api.py:122`). The read gate accepts a portal browser session that
  carries the herald role, and the story records how.
- The route handlers read the flag through `pyforge.core.flags.read_boolean`, steward Story 75.1's
  contract; `refresh_deck_exports` reads it through `django_pyforge.flags`. If
  75.1 has not landed, the story adds `read_boolean` to `pyforge.core` in exactly 75.1's shape
  (`src/shared/packages/pyforge-core/src/pyforge/core/flags.py` and its test), never a station-local reader.
- Tests: `src/platform/tests/test_herald_deck_exports.py` (the list, a chunked stream, 401, 403,
  404, no CORS header, flag OFF 404, the projection and its refresh command) and herald-package
  unit tests for the handlers over the store fake.
**Given** Story 29.1 publishes exports and their manifest to the store, and nothing in the platform can list or serve them
**When** the projection, its changeset and the two routes land
**Then** `refresh_deck_exports` fills `DeckExport` from the manifest and the model has no binary field; the list route returns the records; the stream route streams the bytes in bounded chunks with the record's content type; an anonymous call gets 401, a caller without the herald role 403, and an unknown sha256 404; no response carries `Access-Control-Allow-Origin`
**And** `test_sqlmigrate_extraction.py` and `test_liquibase_ddl_governance.py` stay green; no `pyforge.*` import appears under `src/platform/`; with the flag OFF both routes answer 404; `platform-ci-local -- --test` and `pyforge-herald-test` are green
**Status:** done

## Epic 30: A deck is readable in the browser from its HTML twin (spec-pyforge-herald CAP-55)

Minted 2026-09-28 (night) from the same Dream entry. The operator ruled that the viewer shows
Herald's own decks through their HTML twins, the Marp HTML and the React bundle, and that no
`.pptx` parser runs in the browser (PPTXjs was rejected). Decision D5 is on the Spec memlog; the
twins are served under AD-22, and AD-12's Pitch tab is amended. Both stories follow Epic 29
through station-local `Deps:`, so they also wait on steward Story 74.1.

**Measured 2026-09-28** (`cfae04e14b`):
- 15 current standalone twins (`src/marp/<slug>-infographic-standalone-<date>.html`). 2 of them
  load from another origin: agentic-sdlc's (fonts.googleapis.com) and pyforge-warden's (twemoji
  SVGs from cdn.jsdelivr.net).
- 14 React/JSX decks. Every `index.html` loads Google Fonts from fonts.googleapis.com and
  fonts.gstatic.com, and their `dist/` bundles are gitignored.

**HARD boundaries:**
- No browser-side `.pptx` parser, and no PPTXjs, jQuery or JSZip anywhere.
- No twin is published or served while it references another origin.
- A twin is served under the portal's own origin, with no CORS header.
- `dist/` stays gitignored (AD-4). A bundle lives in the store, never in git.
- Vendored fonts come from npm font packages resolved at build time; no font binary is tracked.
- Warden scans the vendored JavaScript like any other dependency; this epic adds no second verdict.
- Every story spec carries the `pyforge.herald.deck_viewer` flag block, and every PR carries the
  `maintenance` label.

### Story 30.1: A deck's HTML twins are self-contained and published

As an operator publishing decks for readers inside the airgap,
I want every deck's HTML twin to load nothing from another origin, and `herald deck publish` to put the twins in the store,
So that the portal can show a deck where fonts.googleapis.com and jsDelivr are unreachable.

**Type:** feature • **Effort:** M • **Deps:** S-28.2, S-29.1 • **FR/AD:** spec-pyforge-herald CAP-55 (FR-10.3; D5); AD-22 • flag: `pyforge.herald.deck_viewer`
**Surface:**
- `presentations/<slug>/index.html`, `package.json` and `vite.config.js` for the 14 React decks:
  fonts come from npm font packages (for example `@fontsource/*`) instead of Google Fonts, and
  `base: './'` lets a bundle resolve under any prefix.
- The two standalone twins that load from another origin are re-exported through
  `deck-export <slug> html` with the reference vendored: agentic-sdlc's Google Fonts import, and
  pyforge-warden's twemoji images (inlined, or Marp's emoji image conversion turned off).
  `scripts/deck_export.py` gains that option if it needs one. Story 28.2's writer retires each
  predecessor.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/twins.py` (new): the zero-origin scan
  (`src`, `href`, `url()`, `@import`), the React build (`npm ci`, then `vite build` in the deck
  folder), and the bundle manifest.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_publish.py`: with the flag ON,
  publish also puts the twins in the store (a standalone as one object; a bundle as one object per
  file plus a path-to-key manifest), and refuses a twin that fails the scan, naming the file and
  the origin.
- `src/platform/config/flags.json`: `pyforge.herald.deck_viewer`, `defaultVariant` off.
- The flag is read through `pyforge.core.flags.read_boolean`, steward Story 75.1's contract. If
  75.1 has not landed, the story adds `read_boolean` to `pyforge.core` in exactly 75.1's shape
  (`src/shared/packages/pyforge-core/src/pyforge/core/flags.py` and its test), never a station-local reader.
- Tests: `tests/meta/test_twins_zero_origin.py` (the live tree's 15 current standalones and 14 deck
  `index.html` files), `tests/unit/test_twins.py`, the publish cases, and an ON/OFF flag test.
**Given** 2 of 15 current standalone twins and all 14 React decks load from another origin, and no bundle is ever built for a reader
**When** the fonts and images are vendored and the twin publisher lands
**Then** the zero-origin scan passes on every current standalone, every deck's source `index.html` and a built bundle; publish refuses a planted twin that names another origin, naming the file and the origin, and exits non-zero
**And** with the flag ON, `herald deck publish <slug>` puts the twins in the store and records them in the manifest; with it OFF, publish behaves exactly as Story 29.1 left it; `pyforge-herald-test` is green
**Status:** done

### Story 30.2: The herald portal shows a deck in the browser from its HTML twin

As a reader inside the enterprise network without PowerPoint,
I want to open a deck from the herald portal and read it in my browser,
So that I can see the current deck without a download or a desktop application.

**Type:** feature • **Effort:** M • **Deps:** S-29.2, S-30.1 • **FR/AD:** spec-pyforge-herald CAP-55 (FR-10.4; D5); AD-22, AD-12 (amended 2026-09-28 (night)) • flag: `pyforge.herald.deck_viewer`
**Surface:**
- `src/shared/packages/pyforge-herald/src/pyforge/herald/station_api.py`:
  `GET /stations/herald/api/v1/deck-twins/{slug}/{path}` resolves a path through the current
  twin's bundle manifest (or the standalone) and streams it from the store. It uses Story 29.2's
  herald-role read gate, and its responses carry a Content-Security-Policy that names no origin
  other than `'self'`.
- `src/shared/packages/django-herald/src/django_herald_portal/views.py`, `urls.py` and
  `templates/herald_portal/`: `decks/` lists the decks from `DeckExport`, and `decks/<slug>/view/`
  frames the twin route in a sandboxed iframe and offers the `.pptx` as a download. Both views use
  `require_station_role("herald")`. `home.html`'s Pitch tab links to the list.
- The twin route reads the flag through `pyforge.core.flags.read_boolean`, steward Story 75.1's
  contract; the django-herald views read it through `django_pyforge.flags`. If
  75.1 has not landed, the story adds `read_boolean` to `pyforge.core` in exactly 75.1's shape
  (`src/shared/packages/pyforge-core/src/pyforge/core/flags.py` and its test), never a station-local reader.
- Tests: `src/platform/tests/test_herald_portal_deck_viewer.py` (the list, the viewer, 403 without
  the role, the CSP header, flag OFF 404), and a Playwright check that opens one standalone and one
  bundle and records zero requests to any other origin.
**Given** Epic 29 serves published exports and Story 30.1 publishes self-contained twins, but the portal shows only one deck's status
**When** the deck list, the twin route and the viewer land
**Then** `/stations/herald/decks/` lists every published deck, and `/stations/herald/decks/<slug>/view/` renders its twin with every asset request answered by the portal's own origin, which the Playwright run proves by recording zero requests to another origin; a `.pptx` is offered only as a download
**And** an anonymous call is refused and a caller without the herald role gets 403; with the flag OFF the list and viewer answer 404 and the home page is unchanged; `platform-ci-local -- --test` and `pyforge-herald-test` are green
**Status:** done

## Epic 31: The docs site deploys to a second host from the same artifact (spec-pyforge-herald CAP-56)

Minted 2026-09-28 (night) from the same Dream entry. The operator rejected a second Pages artifact.
The need is a second host, an internal GitHub Enterprise Pages site, for the one artifact AD-21
defines. Decision D6 is on the Spec memlog, and AD-21 is amended to "one artifact, N hosts". Both
stories follow Story 27.2, which assembles the artifact (station-local `Deps:`).

**HARD boundaries:**
- One artifact and one deploy caller per repository: `dashboard.yml` stays the only
  `actions/deploy-pages` caller, and no second workflow, assembler or artifact definition appears.
- Nothing in the artifact calls another origin at runtime: no fetch, XHR, script, stylesheet,
  font or image from another origin. No page calls the platform, and no host gets a CORS rule.
- The public site's URLs do not change.
- A vendored upstream file stays byte-identical to its recorded commit (AD-21 rule 5).
- `docs/map.yaml` is doctor's registry. Story 31.2 adds one row for its page and reconciles it on
  `spec-pyforge-doctor`.
- No `pixi.toml` change is expected; if one is needed, `environment.yaml` regenerates in the same
  PR.
- Story 31.1 carries the `pyforge.herald.pages_second_host` flag block, Story 31.2 is
  `flag-exempt: docs-only`, and every PR carries the `maintenance` label.

### Story 31.1: The Pages artifact builds for the host that deploys it

As a maintainer who deploys the docs site to GitHub Enterprise Pages inside the enterprise,
I want the one Pages build to take the site URL and base path of the host that runs it,
So that the same artifact works on github.io and on the enterprise host, with nothing calling across origins.

**Type:** feature • **Effort:** S • **Deps:** S-27.2 • **FR/AD:** spec-pyforge-herald CAP-56 (FR-10.5; D6); AD-21 (amended 2026-09-28 (night): one artifact, N hosts) • flag: `pyforge.herald.pages_second_host`
**Surface:**
- The assembler and `pages-build` that Story 27.2 adds under `docs-site/`: take a site URL and a
  base path as inputs, feed them to Astro's `site` and `base` and to docsite's `/herald/` mount,
  and default to today's public values.
- `.github/workflows/dashboard.yml`: pass `actions/configure-pages`' `base_url` and `base_path`
  outputs to the build when the flag is ON.
- `pages-check`: exit 1 when a script, stylesheet, font, image, `fetch(` or XHR in the artifact
  names another origin, or when an internal link is absolute to a host other than the configured
  one. Plain navigation links pass.
- `src/platform/config/flags.json`: `pyforge.herald.pages_second_host`, `defaultVariant` off, and no
  second flag file.
- The build step that chooses the host inputs reads the flag through
  `pyforge.core.flags.read_boolean`, steward Story 75.1's contract, in an env that carries
  `pyforge-core` (the `site` env gains no pyforge dependency). If
  75.1 has not landed, the story adds `read_boolean` to `pyforge.core` in exactly 75.1's shape
  (`src/shared/packages/pyforge-core/src/pyforge/core/flags.py` and its test), never a station-local reader.
- Tests: `src/shared/packages/pyforge-herald/tests/meta/test_pages_second_host.py` (both inputs,
  the flag-OFF fallback, each planted cross-origin kind) and the `pages-check` fixtures.
**Given** Story 27.2's artifact is built for the public github.io root only
**When** the build takes the host's site URL and base path
**Then** `pixi run -e site pages-build` with a fixture enterprise URL and base path produces an artifact whose internal links and assets resolve under that base, and with the public values produces today's artifact; with the flag OFF the host inputs are ignored and the public build results
**And** `pages-check` exits 0 on both builds and exits 1 on each planted cross-origin kind and on an absolute link to the other host; exactly one workflow uses `actions/deploy-pages`; `pyforge-herald-test` is green
**Status:** backlog

### Story 31.2: How to deploy the docs site to GitHub Enterprise Pages

As an operator of the enterprise GitHub,
I want a how-to that takes the repository's Pages site from mirror to a working internal URL,
So that the enterprise deploy is repeatable and does not live in one person's head.

**Type:** docs • **Effort:** S • **Deps:** S-31.1 • **FR/AD:** spec-pyforge-herald CAP-56 (FR-10.5; D6); AD-21 • flag-exempt: docs-only
**Surface:**
- `docs/how-to/deploy-the-docs-site-to-github-enterprise-pages.md` (new). It covers keeping the
  enterprise copy of the repository in step with `main`; enabling Pages with GitHub Actions as its
  source; a runner that reaches the internal conda mirror (linking
  `docs/how-to/air-gapped-mirror-setup.md` rather than restating it); turning
  `pyforge.herald.pages_second_host` on; and checking the deployed site with `pages-check` and a
  browser that has no route to the internet.
- `docs/map.yaml`: one row for the page (owner herald, kind authored), reconciled on
  `spec-pyforge-doctor`; `docs/MAP.md` re-rendered with `docs-map-render`.
- `docs/how-to/README.md`: one link line.
**Given** Story 31.1 makes the build take the deploying host's URL, and no written procedure exists for the enterprise side
**When** the how-to lands
**Then** it names each enterprise-side step with its command or setting, links the air-gapped mirror how-to instead of restating it, and ends with the check that the deployed site makes no request to another origin
**And** `docs-map-hygiene-check` and `docs-currency-check` exit 0, and `pyforge-herald-test` is green
**Status:** backlog

## Epic 32: A deck exports as a native, editable .pptx through pptxgenjs-plus (spec-pyforge-herald CAP-57)

Minted 2026-09-28 (night) from the same Dream entry. The operator ruled that `pptxgenjs-plus`
becomes an *additional* export kind, native and editable, beside `marp --pptx` and the python-pptx
fill, and that neither of those retires. Decision D7 is on the Spec memlog, and AD-3 is amended.
Mason's `pptxgenjs-plus-jsx` recipe (mason Story 21.5) is a kinship, not a dependency: it matters
only for JSX-authored decks.

**HARD boundaries:**
- `marp --pptx` and the python-pptx fill do not change, and their outputs stay byte-identical.
- The new output is its own kind, `src/pptx/<slug>-deck-native-<date>.pptx`, and never supersedes
  the Marp export.
- It runs from the Guild env, never `-e local-recipes`.
- The `pixi.toml` change is a hand edit followed by `pixi lock`, because the pre-shell hook refuses
  a live `pixi add`. `environment.yaml` is regenerated in the same PR, and `pyforge-station-tests`
  runs before the push (AGENTS.md checklist item 7).
- No mason file changes.
- The story spec carries the `pyforge.herald.deck_export_native` flag block, and the PR carries
  the `maintenance` label.

### Story 32.1: A deck exports as a native, editable pptx through pptxgenjs-plus

As a presenter who needs to edit a deck in PowerPoint,
I want `herald deck pptx-native <slug>` to write a native `.pptx` whose slides are real text, tables and notes,
So that I can change a deck without rebuilding it from images, and without Chrome.

**Type:** feature • **Effort:** M • **Deps:** S-28.2 • **FR/AD:** spec-pyforge-herald CAP-57 (FR-10.6; D7); AD-3 (amended 2026-09-28 (night)) • flag: `pyforge.herald.deck_export_native`
**Surface:**
- `src/shared/packages/pyforge-herald/src/pyforge/herald/exporters.py`: `PptxgenjsExportPlugin`
  (format id `pptxgenjs`) on `DECK_EXPORT_HOOK_SPEC`, beside the three default plugins.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/pptx_native.py` (new): the slide model
  from the deck's current Marp source (per slide: title, bullets, tables, speaker notes), written
  as JSON; the Node call; and `retire_superseded` after a successful write (Story 28.2).
- `src/shared/packages/pyforge-herald/src/pyforge/herald/node/pptx_native.mjs` (new, package
  data): reads the JSON and writes the `.pptx` with `pptxgenjs-plus`, resolved through
  `NODE_PATH=$CONDA_PREFIX/lib/node_modules`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py`: `herald deck pptx-native <slug>`.
  With the flag OFF it stays listed as disabled and exits 2.
- `pixi.toml`: `pptxgenjs-plus = ">=4.2.1"` in `[feature.pyforge-guild.dependencies]`, and in
  `[feature.pyforge-herald.dependencies]` with `nodejs` at the `python` feature's spec, so
  `pyforge-herald-test` runs the Node driver; then `pixi.lock`, and `environment.yaml`
  regenerated.
- `src/platform/config/flags.json`: `pyforge.herald.deck_export_native`, `defaultVariant` off.
- The flag is read through `pyforge.core.flags.read_boolean`, steward Story 75.1's contract. If
  75.1 has not landed, the story adds `read_boolean` to `pyforge.core` in exactly 75.1's shape
  (`src/shared/packages/pyforge-core/src/pyforge/core/flags.py` and its test), never a station-local reader.
- Tests: `tests/unit/test_pptx_native.py` (the slide model), `tests/integration/test_pptx_native_render.py`
  (a fixture deck rendered and read back with python-pptx), and an ON/OFF flag test.
**Given** every standard `.pptx` comes from `marp --pptx` as image slides that need Chrome, and `pptxgenjs-plus` sits only in the `local-recipes` env
**When** the plugin, the Node driver, the verb and the environment change land
**Then** `pixi run -e pyforge-guild herald deck pptx-native <slug>` exits 0 on a fixture deck and writes `<slug>-deck-native-<date>.pptx`; python-pptx reads it back with one slide per Marp slide, titles and bullet text as text frames, tables as table graphic frames, speaker notes in each notes slide, and no picture shape standing in for a slide; a second run on a later date leaves one version of the kind; the Marp and pptx-fill exports are byte-unchanged
**And** with the flag OFF the verb is listed as disabled and exits 2 with a "flag off" message; `environment.yaml` is regenerated in the same PR; `pyforge-station-tests` and `pyforge-herald-test` are green
**Status:** backlog

## Epic 33: The genesis deck counts archived Dreams where they now live (spec-one-chain-per-station CAP-11)

Minted 2026-09-29 from `docs/governance/spec-one-chain-per-station/SPEC.md` CAP-11 (owner Dream
`docs/dreams/one-chain-per-station.md`, `owner: guild`): archived Dreams leave `docs/dreams/` for `archive/docs/dreams/`,
and CHAIN-STANDARD §11 requires every reader that lists Dreams to follow them before the first fold PR moves a file.
`scripts/deck_facts.py` is one such reader: for the `pyforge-genesis` deck it counts Dreams by status, and spec-surface
puts it on Herald. Herald mints no CAP and registers no FR for this story: the CAP is the Guild Spec's, enumerated here
and in that Spec's `.memlog.md`, as doctor's relay epics do. **HARD boundaries:** no file moves in this story; the deck's
poster is not edited; `deck-facts --check` stays advisory. Doctor Epic 36 and marshal Epic 75 carry the other readers. The
story is a `chore`.

### Story 33.1: deck-facts counts Dreams under the archive too

As the owner of the genesis deck's fact ledger,
I want the Dream counts to include `archive/docs/dreams/`,
So that moving archived Dreams to one archive home does not make the deck report fewer Dreams.

**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** spec-one-chain-per-station CAP-11 (CHAIN-STANDARD §11: readers follow the move); `spec-deck-family-currency` CAP-2 (the facts ledger)
**Surface:** `scripts/deck_facts.py` (the `pyforge-genesis` branch counts `archive/docs/dreams/*.md` that carry a frontmatter `status` alongside `docs/dreams/*.md`, and each fact's source names both globs), `tests/scripts/test_deck_facts.py`.
**Given** `dreams_total` and `dreams_<status>` count only `docs/dreams/*.md`
**When** a fixture archived Dream moves to `archive/docs/dreams/`
**Then** `dreams_total` and `dreams_archived` keep their values, and each fact's source names both globs
**And** on today's tree every count derived from `docs/dreams/` is unchanged and the six Dreams already under `archive/docs/dreams/` (`deckcraft`, `design-code-bridge`, `herald-pitch-deck-family-expansion`, `modernist-identity`, `pyforge-genesis`, `video-scripts`) are added to `dreams_total` and `dreams_archived`, counted as archived whatever their frontmatter `status` *(amended 2026-09-30, operator ruling: location is the archive signal, CHAIN-STANDARD §11)*; the test covers a moved Dream and an archive with no status; `pixi run --frozen -e pyforge-herald pyforge-herald-test` is green
**Status:** done

## Epic 34: Herald cites the deck how-to, not the retiring intake stub (spec-one-chain-per-station CAP-11)

Minted 2026-09-29 from `docs/governance/spec-one-chain-per-station/SPEC.md` CAP-11 (owner Dream
`docs/dreams/one-chain-per-station.md`, `owner: guild`). `docs/specs/` retires, and its `presentation-deck.md` is a stub
whose body already lives at `docs/how-to/presentation-deck.md`. CHAIN-STANDARD §11 requires every reader to follow before
the PR that moves the stub (doctor Story 37.1). Herald's code, skill, tests and deck READMEs still cite the stub. Herald
mints no CAP and registers no FR for this story: the CAP is the Guild Spec's, enumerated here and in that Spec's
`.memlog.md`, as doctor's relay epics do. **HARD boundaries:**
- No behaviour changes: every edit is a citation in a comment, docstring, help text, skill section, test constant, fixture
  text or README.
- The stub itself does not move in this story.
- No deck poster or export is re-rendered.

Atlas Epic 26, steward Epic 77 and marshal Epic 76 carry the other readers. The story is a `chore`.

### Story 34.1: Herald cites the deck how-to, not the intake stub

As the owner of the deck family,
I want every Herald citation of the deck contract to name `docs/how-to/presentation-deck.md`,
So that retiring `docs/specs/` leaves no Herald file pointing at an archived stub.

**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** `spec-one-chain-per-station:CAP-11` (CHAIN-STANDARD §11: readers follow the move)
**Surface:**
- Code: `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` (four citations), and
  `scripts/deck_export.py`, `scripts/deck_facts.py` and `scripts/deck_trio.py` (one each).
- `pixi.toml`: three task descriptions. `docs/how-to/pixi-tasks.md` is regenerated with `scripts/docs_pixi_tasks.py`.
- `.claude/skills/bmad-agent-herald/SKILL.md` (the AD-2 section), with the `DECK_PIPELINE_SPEC` constant in
  `tests/meta/test_slides_generator_routing.py`.
- Test text: the docstring in `tests/meta/test_deck_registry_sections.py`, and the README fixture text in
  `tests/unit/test_deck_pipeline.py`.
- The 15 `presentations/*/README.md` that cite the stub.
**Given** herald's code, skill, tests and deck READMEs cite `docs/specs/presentation-deck.md`, whose body lives at
`docs/how-to/presentation-deck.md`
**When** each citation names the how-to, keeping its section name
**Then** no herald-owned live file names `docs/specs/presentation-deck.md`, and every cited section exists in the how-to
(*The MCP bridge*, *Standard export set*, *Artifact dependency tree*, the large-file uploads note)
**And** `environment.yaml` regenerates unchanged; `spec-surface-check` exits 0 after a memlog entry and a scoped stamp for each
Spec it names (`spec-pyforge-herald`, `spec-design-code-bridge`, `spec-modernist-identity`); `pixi run --frozen -e
pyforge-herald pyforge-herald-test` green
**Status:** done

## Epic 35: Phase 4+5 of the deferral burn-down: herald's open medium and low deferrals

Minted 2026-10-03 from the station Dream's Realization log entry of the same date: the operator's Phase 4+5 rulings on the deferral burn-down (open medium and low rows close together through fix stories; then, the same day, exactly one story per station). One `fix` story, no CAP, no flag; it closes 10 open rows: 6 medium, 4 low (the eleven follow-up-review rows left it by operator ruling 2026-10-03 and run as review batches) (measured with a parser over the station's `deferred-work-ledger.md`), each with a `resolution:` and a cited `verified:` line. **HARD boundaries:** no blanket closure (a row closes only by a landed fix or the cited line that already holds it); each fix is pinned by a test that fails without it. The one open high row (DW-21-7-1) is outside Phases 4 and 5.

### Story 35.1: The deck transport, sync-all, deck tooling and docs site close their open deferrals

As the owner of the deck family,
I want herald's open medium and low deferred-work rows fixed where they live,
So that the deferral burn-down closes them with landed fixes and cited evidence, not a blanket close.

**Type:** fix • **Effort:** L • **Deps:** — • **FR/AD:** the capabilities that shipped each behaviour (the stories each row names); no new CAP, no flag (`spec-feature-flag-governance` Q1) • **Closes:** DW-21-7-2, DW-FU-23-6-1, DW-FU-21-2, DW-FU-24-2-1, DW-FU-18-1, DW-FU-18-3, DW-FU-15-1-2, DW-FU-21-10, DW-FU-21-3, DW-herald-59-6
**Surface:** `src/shared/packages/pyforge-herald/src/pyforge/herald/` (`transport/mcp_transport.py`, `transport/agent_sdk_transport.py`, `deck_pipeline.py`, `sync_all.py`, `pptx_pipeline.py`), the herald tests; `docsite/build.py`; `scripts/deck_trio.py`, `scripts/deck_facts.py`, `tests/scripts/test_deck_trio.py`, `tests/scripts/test_deck_facts.py`; `presentations/**` (the four posters' markup, the presenton README); `scripts/detectors.py` and `tests/scripts/` (a pin test only, if none exists); the herald `deferred-work-ledger.md`
**Given** herald's 10 open medium and low deferred-work rows in scope (measured 2026-10-03 with a parser over the ledger)
**When** each is fixed where its behaviour lives and the three whose fix already landed are re-read and pinned
**Then** `list_files` parses the live server's answer, `deck sync-all` publishes the standalone poster, `deck-trio --deck` derives all ten PyForge posters, `docsite/build.py` has unit tests, and an ambiguous layout name is refused
**And** each row is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed; no poster is re-pushed and no visible poster text changes; `pixi run --frozen -e pyforge-herald pyforge-herald-test` green
**Spec:** `planning-artifacts/specs/spec-35-1-the-deck-transport-sync-all-deck-tooling-and-docs-site-close-their-open-deferrals.md`
**Status:** done

### Story 35.2: The docs-site checks and the sync-proof row close on real evidence

As the owner of the deck family,
I want Story 35.1's unfinished items done and its records corrected,
So that every closed row rests on a test that can fail or a proof that exists.

**Type:** fix • **Effort:** M • **Deps:** — • **FR/AD:** the capabilities that shipped each behaviour (Story 35.1's rows); no new CAP, no flag •
**Surface:** `docsite/build.py` tests (`src/shared/packages/pyforge-herald/tests/unit/test_docsite_build.py`), `scripts/deck_trio.py` and `tests/scripts/test_deck_trio.py`, `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py`, `src/shared/packages/pyforge-herald/src/pyforge/herald/pptx_pipeline.py`, `presentations/presenton-pixi-image/README.md`; the herald `deferred-work-ledger.md` and memlog
**Spec:** `planning-artifacts/specs/spec-35-2-the-docs-site-checks-and-the-sync-proof-row-close-on-real-evidence.md`
**Given** Story 35.1's post-landing review
**When** each docs-site check gets a failing-case test, the act vocabulary and a unique layout name are pinned, and the tautological hash branch goes
**Then** DW-FU-24-2-1 closes on tests that fail without their check, and DW-FU-23-6-1 is reopened until a live proof exists
**And** the README, DW-FU-20-2's record and the herald memlog are corrected and stamped; `pixi run --frozen -e pyforge-herald pyforge-herald-test` green

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
(stale-slug orphans dropped). Frontmatter repaired: the Fold provenance block had sat inside the
YAML fence since the 2026-09-17 fold (unparseable); it now follows the H1, as in steward and
scribe. `updated:` bumped.

## Currency reconciliation — 2026-09-27

`arch→epics` edge after the spine re-stamp of 2026-09-27, which added AD-21. Epic 27 (Stories
27.1–27.4) was minted from `spec-pyforge-herald` CAP-52 — the docs site matches BMAD-METHOD's
pattern — which registers FR-8.1..FR-8.4 in the PRD. Every Story heading still maps 1:1 to a
`sprint-status-ledger.yaml` key: the four `27-N` keys, `epic-27` and `epic-27-retrospective` went
into the Tier-3 feed, and `sprint-ledger-sync` wrote the twin. The feed and the twin carried the
same 158 keys before the mint, so no repair was needed. Two stale records in this file were fixed
in the same pass. Story 26.1's inline status read `backlog` for a story that landed on 2026-09-26
(`df7a651aa9`). The Epic List table stopped at E22 with a 48-story total; it is regenerated from
the ledger (27 epics, 110 stories, 105 done), and `epicCount`/`storyCount` are re-measured.
`updated:` bumped.

**Amended the same day — two operator rulings on the first mint (`815132515c`; D7 and D8 on the
Spec memlog).** D7: docsite's whole output mounts under `/herald/` (the dossier page is
`/herald/dossier/`), and every HTML path it served at the Pages root gets a redirect page to its
`/herald/` home — 44 pages, derived from the `herald/` tree. `/` is the one named exception,
because Starlight's landing owns it and links to `/herald/`. Story 27.2 is rewritten to match. D8:
`pr-preflight` runs the Pages build check only when a diff touches `docsite-check.yml`'s paths, a
selection read from the workflow file by steward Story 71.2 (`spec-pyforge-steward:CAP-159`), so
there is no second path list. Story 27.2 therefore leaves `pr-preflight`'s `site-check` leg
alone, and new Story 27.5 (FR-8.5) swaps that leg for `pages-check`. 27.5's ledger key is minted
`blocked` until 71.2 lands, and the operator flips it. The `docs/**` and `docs-site/**` path
filters on `docsite-check.yml` move from 27.4 to 27.2, where the lane starts building `docs/`.
The Tier-3 feed took the one new key, and `sprint-ledger-sync` wrote only that key and the
`# stories:` header to the twin. The Epic List table and `storyCount` are re-measured: 111
stories, 105 done.

## Currency reconciliation — 2026-09-28

`arch→epics` edge after the spine re-stamp of 2026-09-28, which amended AD-4 (one dated version per
export kind). Epic 28 (Stories 28.1–28.2) was minted from `spec-pyforge-herald` CAP-53, *each deck
keeps one current version of each export*, which registers FR-9.1..FR-9.2 in the PRD. Every Story
heading still maps 1:1 to a `sprint-status-ledger.yaml` key: the two `28-N` keys, `epic-28` and
`epic-28-retrospective` went into the Tier-3 feed, and `sprint-ledger-sync` wrote the twin. The feed
and the twin carried the same 165 keys before the mint, so no repair was needed. The Epic List
table and `epicCount`/`storyCount` are re-measured: 28 epics, 113 stories, 105 done. `updated:` bumped.

## Currency reconciliation — 2026-09-28 (night)

`arch→epics` edge after the spine's second 2026-09-28 re-stamp (§ Currency reconciliation —
2026-09-28 (night)), which added AD-22 and amended AD-3, AD-12 and AD-21. Epics 29–32 decompose
`spec-pyforge-herald` CAP-54..CAP-57 (FR-10.1..FR-10.6), all from the Dream's 2026-09-28 (night)
entry: Epic 29 (Stories 29.1–29.2, CAP-54), Epic 30 (30.1–30.2, CAP-55), Epic 31 (31.1–31.2,
CAP-56) and Epic 32 (32.1, CAP-57). Stories 29.1 and 29.2 are minted `blocked` until steward
Story 74.1 lands; the operator flips them. Every other new story is `backlog` behind station-local
`Deps:` (S-27.2, S-28.1, S-28.2 and Epic 29's own). Each `type: feature` story carries a flag block
under `spec-feature-flag-governance`, and Story 31.2 carries `flag-exempt: docs-only`. Every Story
heading still maps 1:1 to a `sprint-status-ledger.yaml` key: the seven story keys, `epic-29` to
`epic-32` and their four retrospectives went into the Tier-3 feed, and `sprint-ledger-sync` wrote
the twin. The Epic List table and `epicCount`/`storyCount` are re-measured: 32 epics, 120 stories,
105 done. `updated:` bumped.

## Currency reconciliation — 2026-10-07

`arch→epics` edge after the spine re-stamp of 2026-10-07 (its § Currency reconciliation — 2026-10-07), which added and
amended no AD. Validated against that section: Story 27.1 still maps to FR-8.1 / AD-21, Story 28.1 to FR-9.1 / AD-4
(amended 2026-09-28), and Stories 35.1–35.2 to the FRs that shipped each deferred-work row, under AD-2 and AD-3 as
written. No epic or story is added, and no story's status or text changes. The spine's one recorded divergence, the
untracked `docs-site/src/lib/site-url.mjs` (FR-8.1, AD-21), is not decomposed here; it needs its own fix story. Every
Story heading still maps 1:1 to a `sprint-status-ledger.yaml` key (124 headings, 124 story keys). Two stale records were
fixed in the same pass. The Epic List table stopped at E32 and still showed E27 with no story done; it now matches the
ledger, measured with `fleet_scan.parse_sprint_status`: 35 epics, 124 stories, 108 done. `epicCount` and `storyCount`
are re-measured to match. `updated:` bumped.
