---
title: "pyforge-herald — Retrospective, Epics 13-17"
slug: retro-pyforge-herald-2026-08-26
status: final
created: 2026-08-26
updated: "2026-08-26"
project: pyforge-herald
scope: "Epics 13-17 (14 stories), 2026-08-10 through 2026-08-26; everything since retro-herald-2026-08-08.md"
---

# pyforge-herald — Retrospective (Epics 13–17)

**Date:** 2026-08-26 · **Facilitator:** chain-currency sweep agent (headless) · **Project Lead:** rxm7706
**Scope:** the 14 stories landed since the 2026-08-08 whole-build retro — Epic 13 (live
backend, 6), Epic 14 (deck visual QA, 3), Epic 15 (PPTX-native pipeline, 2), Epic 16
(exporter hook spec, 1), Epic 17 (skill/persona + portal slice, 2). All `done` in
`sprint-status-ledger.yaml`; Herald now stands at 61/61 stories across 17 epics.

**Evidence base:** `git log --since=2026-08-08 -- src/shared/packages/pyforge-herald`
(landings `cfc951aac9`/`488105bdc1`/`828a89fadd`/`8ba853c78a` for Epic 13;
`c47a46d1b7`/`9de381a01e`/`ef0b9482d2`/`3ab6509823` for Epic 14, 2026-08-14;
`788423fc56`/`0888084eff`+two review passes for Epic 15, 2026-08-22; `a6288ed157` for
16.1, 2026-08-24; `dbf53e2d75`/`a1d0609c4f` for Epic 17, 2026-08-25/26), the per-story
specs (`spec-13-1` … `spec-17-2`), and the 2026-08-08 research triple these epics were
executed against.

## 1. What shipped since 2026-08-08

1. **Epic 13 — the live backend (2026-08-10 → 08-13, bmad-loop).** The full-spec Moments
   2–4 substrate the 2026-08-08 pivot had deferred into
   `docs/dreams/herald-moments-2-4-live-backend.md`, built in the Dream's own intended
   order: locking first (13.1 — stdlib `fcntl`/`msvcrt` advisory lock, `locking.py`,
   closing DW-1-4-2 *before* any second writer existed), the serverless-intermediate
   decision recorded per-item with individual verdicts (13.2, a code-free decision story),
   then SQLite behind the untouched function seam with a versioned migration runner (13.3,
   `db.py`, `.herald/herald.db`, WAL; notices markdown stays the durable copy), the
   HMAC-verified webhook module CI calls (13.4, `webhook.py`/`webhook_host.py`, GitHub
   Actions, riding Steward's secure-live-dashboards trust boundary), the scheduler that
   enforces the displayed 7-day evidence window (13.5, `scheduler.py` + the fifth
   top-level CLI verb `herald scheduler`), and the composed live proof (13.6): **a real
   merge produced a progress record and a success-claim draft with no human action** —
   the "an unrecorded ship is indistinguishable from no ship" risk (2026-08-08 technical
   research, risk #2) is structurally closed, CI-contained.
2. **Epic 14 — a deck is proven to look right (2026-08-14).** `deck_qa.py`: gate-registry +
   gate-id-keyed machine-readable report under `herald deck qa <slug>` (14.1, entrypoint
   decision recorded); headless-Chromium render gate — playwright-python already pinned,
   throwaway loopback static server rather than `file://` (recorded decision), one PNG per
   manifest slide + a contact sheet, report-only (14.2, incl. a review-pass fix for a
   render-gate path-traversal bypass); image-slot scan gate flagging both placeholder
   spellings, with the known slide-40 true positive in `presentations/agentic-sdlc/`
   (14.3). Closes the recorded "render gates prove the page RUNS, never that it LOOKS
   right" gap for the deck pipeline.
3. **Epic 15 — the PowerPoint-native pipeline (2026-08-22).** Unparked the same day Marp
   inadequacy was proven (shipped PPTX exports were background-image slides with **zero
   editable text runs**) and the operator named the editing audience. 15.1:
   template-parse-then-fill (`spec.json` + `content_plan.json`, raw OOXML never
   hand-written) → every text run edits cleanly in PowerPoint, round-trip proven. 15.2:
   dense content renders as editable card/metric-box/table/section-label shapes with
   Pillow real-font-measured autofit — the densest six-act appendix slide fits, measured
   not guessed. Two adversarial review passes landed 16 patch findings same-day.
4. **Epic 16 — exporter hook spec (2026-08-24).** Marp, PPTX and `.dc.html` export
   re-registered as default plugins on the shared `pyforge.core.hooks` contract (canopy:AD-21); no station-local plugin loader, and export success can never publish a PR
   quality-gate verdict (`SecondVerdictError`) — the never-a-second-verdict invariant
   held in code, not just prose.
5. **Epic 17 — the station owns its skill, persona, and one portal job (2026-08-25/26).**
   17.1: SKF domain skill compiled from the package (`.claude/skills/pyforge-herald/`,
   v0.1.0) + `bmad-agent-herald` persona that acts only through `pyforge herald …` grammar
   and `POST /stations/herald/mcp`. 17.2: first `/stations/herald/` portal slice — one
   slug's `deck status` rendered via PortalClient only, HTMX under the Canopy host, no raw
   HTTP, no chrome copy, no second public port.

## 2. What held

- **The seam claim was real.** The 2026-08-08 technical research (§4.1) asserted the
  pivot's key asset — pure `(path, **fields) → record` functions with no CLI coupling —
  would make a live backend "a genuinely small delta." Epic 13 cashed that in: the DB swap
  (13.3) and both automation triggers (13.4/13.5) landed behind the unchanged CLI/web-tab
  contract, exactly as the Dream's constraint demanded. Planning honesty at pivot time
  (preserve as a Dream, don't delete) paid out three weeks later.
- **The concurrency prediction was honored, not rediscovered.** The research's risk #4
  ("*the live-backend Dream itself trips this first*") was encoded as Epic 13's hard
  Constraint 1, and 13.1 shipped first with a concurrency test that failed against the old
  code. A ledgered risk became sequenced work instead of an incident.
- **The 2026-08-08 retro's process lessons visibly carried.** Recorded first-AC decisions
  (13.1 lock-vs-SQLite, 13.4 which-CI, 14.1 entrypoint, 14.2 serve-mode, 15.1
  own-template) appear in every epic — the "resolve the spec's open question as the first
  AC, dated" pattern is now habitual. Adversarial review kept earning: 14.2's
  path-traversal bypass and 15.2's 16 findings were caught in-pass, not post-ship.
- **Report-only / never-mutate constraints held** across Epic 14 (QA never rebuilds or
  edits deck sources) and Epic 16 (no competing verdict), matching each spec's Never list.

## 3. What changed course

- **Deckcraft's markdown→PPTX slice (HER-5) is no longer the editable-deliverable path.**
  The 2026-08-22 proof that its output carried zero editable text runs demoted it;
  the template-parse-then-fill pipeline (Epic 15) is now how an editable deck is made.
  The HTML/Marp path coexists; nothing was deleted. The architecture spine's AD-3 PPTX row
  is amended by the same-day arch reconciliation rather than rewritten.
- **The Moments automation shipped in a different shape than the 2026-08-02 satellite PRD
  specced:** GitHub Actions webhooks + CI-scheduled `herald scheduler run` instead of a
  resident cron daemon; stdlib SQLite instead of PostgreSQL/SQLAlchemy/Celery; Steward's
  trust boundary instead of Herald-owned auth. All three deviations are recorded decisions
  in the story specs and reconciled into the PRD/arch on this date.
- **Epic minting stopped at the Canopy boundary.** The 2026-08-24 obligations in
  `epics.md` bind Herald to *not* duplicate steward Epics 18–30; Epics 16–17 were scoped
  as exactly the two station-local jobs (exporter hooks; skill/persona + one portal
  slice) and nothing more.

## 4. Strategy convergence (Unifying Strategy / Canopy)

Against `spec-pyforge-unifying-strategy` (steward-owned), Herald's contracted roles are now
materially converged: **outward voice/decks** (Epics 1–5, 14, 15, 16 — the deck program's
QA and editable-deliverable machinery); **portal + MCP face client on the Canopy host**
(17.2 portal slice at `/stations/herald/`; service face `POST /stations/herald/mcp`; no
standalone origin or port); **persona/grammar discipline** (17.1 — Path B via
`pyforge herald …` + MCP only); **Lane 1 comms adjacency respected** — the Guildhall/CMS
remains steward's (Herald's own non-goal since 2026-08-02; reaffirmed when steward 30.2
deleted the retired Guildhall generator on 2026-08-25 and Herald's SPEC re-pointed its one
check reference the same day). The **Dream→spec handoff portability** role (AGENTS.md) is
untouched by these epics. Stack bindings (markitdown, graphviz2drawio, playwright dual
pins) remain as listed in the strategy `stack.md`; playwright's "extend" row is now
partially realized by Epic 14's render gate.

## 5. Open items (carried forward, none gating)

1. **Retro A5 (2026-08-08) still open:** the four Epic-2 live Design proofs
   (`deck pull` against real projects, `--commit`, `--target marp-deck`/`standalone`)
   remain blocked on a live `/design-login` credential; the bridge's remote-behavior
   DW-1-2-* tail (timeouts, 429/5xx discrimination, unobserved conflict wire shape) is
   still the most likely source of the next real defect.
2. **Telemetry-derived defaults for `herald progress`** (13.2's tracked BUILD verdict for
   the `herald snapshot` family's siblings) — the 2026-08-08 market research's
   differentiator remains only partially closed: automation now creates records, but
   cost/shipped fields are not yet telemetry-derived.
3. **Persistent, always-on hosting** of the webhook/scheduler surface is a Steward-owned
   deployment concern; 13.6's proof is CI-contained by recorded decision.
4. **Moment-1 deferred decisions** (family review cadence, extraction automation, video
   render scheduling) and the Manticore video path remain unexercised.
5. **Adoption/engagement metrics** from the satellite PRD remain unmeasured — near-zero
   production usage time; targets, not results.

## 6. Rule-2 applicability

Per CLAUDE.md's BMAD ↔ conda-forge-expert Rule 2: Epics 13–17 touched no `recipes/` work
and no conda-forge surface (pure Python/CLI/web/portal work under
`src/shared/packages/pyforge-herald/` and `src/platform/`), so the mandatory CFE-skill
retro does not apply — same non-applicability the 2026-08-08 retro recorded for Epics 1–12.
