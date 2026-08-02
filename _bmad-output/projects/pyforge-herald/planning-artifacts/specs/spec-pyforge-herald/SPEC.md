---
id: SPEC-pyforge-herald
spec: pyforge-herald
status: specified
owner-dream: docs/dreams/pyforge-herald.md
surface:
  - src/shared/packages/pyforge-herald/**
  - presentations/**
companions:
  - artifact-tracking-matrix.md
  - workflow-stages.md
  - six-act-framework.md
  - station-roster.md
  - bridge-protocol.md
  - epic-structure.md
sources:
  - ../../../../../../docs/dreams/pyforge-herald.md
  - ../../../../../../docs/dreams/herald-pitch.md (archived/absorbed; source of HER-4..HER-10)
  - ../../../../../../docs/dreams/herald-moments-2-4-missing-surface.md (archived/absorbed; source of HER-11..HER-13)
open_questions: []
---

> **Canonical contract.** This SPEC is the complete contract for what to build, test and
> validate. Source documents in frontmatter are traceability only.

> **Consolidated 2026-08-02 (later same day).** This is now the single canonical Spec for
> the `pyforge-herald` station — explicit user override of the same-day
> keep-chains-separate convention this repo otherwise follows (see the Realization log in
> `docs/dreams/pyforge-herald.md`). HER-1, HER-2, HER-3 and both Constraints/two of the
> Non-goals below are unchanged from the pre-consolidation version of this document.
> **HER-4 through HER-10** are folded in from `spec-herald-pitch/SPEC.md` (its own
> CAP-1..CAP-7, renumbered). **HER-11 through HER-13** are folded in from
> `spec-herald-moments-2-4/SPEC.md` (its own CAP-1..CAP-3, renumbered). Both source
> folders — `SPEC.md` + `.memlog.md`, companions already relocated here — are archived,
> unmodified, at
> `archive/_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-herald-pitch/`
> and
> `archive/_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-herald-moments-2-4/`
> respectively. Their memlog entries are replayed, in original order, into this document's
> own `.memlog.md` before this hand-produced merge, per this repo's re-distillation-safety
> convention for Spec kernels.

# pyforge-herald

## Why

Herald is the factory's **voice and visual surface**. *Invisible engineering is failed
engineering* — Herald exists so nothing the factory does stays invisible. Re-scoped by the
2026-07-23 ownership review (infrastructure moved to Marshal; Herald keeps communication).

**Herald's work is continuous, not a bookend** — corrected 2026-07-25, when this Dream said
"first to touch a Dream and last to touch a release". Communication runs throughout, not at
the ends.

**Current state (2026-08-02):** the deck family (Moment 1 content) is production-ready. HER-1's
CLI mechanization of it is in progress — 4 of 17 foundation stories done (package scaffold,
MCP-transport spike, bridge-core skeleton, registry module); `seed`/`pull`/`status`/`watch`
are not wired into the CLI yet, and the loop is paused mid-story on the fallback transport
adapter. Moments 2–4 (progress/success/operations proclamation) are Herald's active next
frontier, planned end-to-end but not yet implemented — the detailed capability breakdown for
both Moment 1's deck-family orchestration (HER-4..HER-10) and Moments 2–4's proclamation
surfaces (HER-11..HER-13) now lives inline below, folded in from their own formerly-separate
Specs on 2026-08-02.

Herald's Four Moments of Proclamation, in full: **Pitch** (HER-4..HER-10 — a Dream must be
argued, not merely filed), **Progress** (HER-11 — a build in flight is not self-explaining),
**Success** (HER-12 — shipping is not the same as being known to have shipped), **Operations**
(HER-13 — the long tail nobody announces).

## Capabilities

### Station-level (unchanged, 2026-08-01/02)

- **HER-1 — a Dream becomes a deck.** *Success:* `herald seed` renders a Dream into a deck and `herald pull` brings the designed result back; the round trip is the realized [[design-code-bridge]] (elaborated in HER-4 below). *In progress:* the CLI foundation (package scaffold, transport port, bridge-core, registry) is built and tested; the `seed`/`pull`/`status`/`watch` subcommands themselves are not yet wired up.
- **HER-2 — releases are proclaimed from the ledger.** *Success:* release notables compile from pipeline data, never hand-written. *Status:* fully specced — the detailed breakdown that used to live in a separate `spec-herald-moments-2-4` document is now inline as HER-11 (Progress), HER-12 (Success) and HER-13 (Operations) below — but not yet implemented.
- **HER-3 — the visual identity is one system.** *Success:* decks, infographics and the Guildhall share [[modernist-identity]]'s vocabulary (elaborated in HER-7 below).

### HER-4..HER-10 — Moment 1 (Pitch): deck-family orchestration (folded in 2026-08-02 from `spec-herald-pitch`, was CAP-1..CAP-7)

Herald's Four Moments of Proclamation guide all work: **Pitch** (a dream must be argued, not
merely filed — this group), **Progress**, **Success**, **Operations** (HER-11..13 below). This
group orchestrates Moment 1 across **9 pyforge stations** using four reusable Tier 1
capabilities, producing 6 artifact formats per station from a single Design source, tracked
and regenerable per an aggressive optimization strategy. Core insight: **one source of truth
(Design prototype) → multiple deliverable formats → zero manual file transfers.**

- **HER-4 — Design-Code-Bridge Framework.** *Intent:* Automate the round-trip between Claude Design (visual authoring) and Code (repository). *What it does:* **Seed** — Claude Code creates Design projects per deck, seeded with a contract-compliant prototype (1920×1080, Archivo, family palette). **Design** — user iterates visually at claude.ai/design; edits tracked by etagged protocol. **Pull** — `herald deck pull <slug>` reads the Design prototype into Code, extracts to markdown, auto-commits; zero downloads, zero copy-paste. **Discipline** — etags on every transfer; mid-edit conflicts surface instead of silently overwriting. *Success:* prototype round-trips seamlessly between Design and Code; etagged safety prevents overwrites; zero manual file transfers; 7 decks proven. This is the realized mechanism behind HER-1's `seed`/`pull`.
- **HER-5 — Deckcraft Framework.** *Intent:* Generate editable PowerPoint from Markdown sources without sacrificing manual refinement. *What it does:* input is a Markdown source (`{station}.md`) + Modernist design tokens; `pixi run deck-export` runs the deckcraft pipeline → python-pptx → editable PPTX at `src/pptx/{station}.pptx`. *Success:* PPTX files are editable in PowerPoint; formatting and layout choices preserved; regenerable from markdown in 5–10s. *Scope note:* this is the narrow "render markdown to PPTX" slice of the broader standalone `deckcraft` AI-pipeline product (prompt/document → deck via local LLMs) — that broader product's own PRD/Architecture/Spec were archived in the 2026-08-01 consolidation (commit `409b3357bd`); only this reused rendering capability survived into Herald's own chain.
- **HER-6 — Video-Scripts Framework.** *Intent:* Extract narration scripts from decks and feed them into video production pipelines (bmad-manticore). *What it does:* mechanical narration extraction from Design speaker notes → `{station}-narration-YYYY-MM-DD.md`; Herald feeds the narration corpus to manticore (322 scenes, 27 files mechanically extracted; first master script authored as exemplar); manticore orchestrates voice (Kokoro-82M), graphics (HyperFrames), b-roll (real screen recordings, never fabricated UI), SFX (AudioLDM2) → `.mp4`. Four hard gates: Outline → Cut Plan → Graphics Beats → Final Render; no fabricated product demos. *Success:* narration scripts extracted and available; video production ready; no fabricated demos; all b-roll is real.
- **HER-7 — Modernist-Identity Framework.** *Intent:* One visual language across all PyForge surfaces (decks, dashboards, docs, exports, videos) — the mechanism behind HER-3. *What it does:* flat, architectural, Archivo typography throughout; light palette (#f3f2f2), ink (#201e1d), red accent (#ec3013/#c22a10); visible grid, 2px rules, zero corner radius, flush-left labels, black-and-white photography. Tokens round-trip through Figma variables, design-tokens JSON, PPTX templates, deck engine, video production bibles. *Success:* Modernist design system adopted across all Herald family decks; 7 decks bound; tokens ready for PPTX ↔ Figma ↔ video round-trip.
- **HER-8 — Six-Act Deck Framework.** *Intent:* Canonical structure for all pitch decks to ensure consistency and narrative clarity. *What it does:* 8 sections — Cover (hook), Act I (friction), Act II (insight), Act III (solution/mechanics, L.A.T.C.H. Time), Act IV (real-world application, L.A.T.C.H. Location), Act V (future/vision, L.A.T.C.H. Category), Act VI (action/CTA), Appendix (personas). ~28 slides per deck, 90KB+ class, inline SVGs, full depth (no size-restricted authoring). Visual principles: L.A.T.C.H. (Location, Analogy, Time, Color, Hierarchy). *Success:* all 9 decks follow six-act structure; all contain persona appendices; all render full depth; all use L.A.T.C.H. visual principles consistently. Full structure detail in companion `six-act-framework.md`.
- **HER-9 — Multi-Format Export.** *Intent:* Deliver 6 artifact formats per station from a single Design prototype. *What it does:* (1) Design protos (.dc.html) — source of truth, tracked, etagged; (2) Markdown sources (marp) — version-controlled content extracted from Design; (3) PPTX exports (editable) — deckcraft output, tracked for deliverable readiness; (4) Narration scripts (.md) — video production input, tracked for pipeline readiness; (5) Infographics (SVG) — inline static images, tracked, never raster; (6) HTML decks (interactive) — Vite bundle, gitignored (regenerable <5s). Optimization: aggressive strategy tracking ~144 files (source + final deliverables), gitignoring intermediate builds (fragments.json, dist/, assets/, .mp4, ~62% reduction). *Success:* all 6 formats available per station; tracked/gitignored split correct; regeneration strategy reduces footprint by 62%; no manual file copies. Full tracking rationale in companion `artifact-tracking-matrix.md`.
- **HER-10 — Station-Specific Customization.** *Intent:* Apply the framework consistently across 9 pyforge stations with domain-appropriate content. *What it does:* 9 stations (Marshal, Warden, Atlas, Mason, Steward, Scribe, Genesis, Doctor, Herald), each with its own thesis, pain point, solution pillars, ecosystem vision, personas, and domain-appropriate diagrams (warden: lattices/gates; marshal: policy composition; atlas: pipeline stages); framework (six-act structure, Modernist identity, design bridge, deckcraft pipeline) stays constant across all 9. *Success:* 9 Design projects seeded; 9 prototypes authored per six-act framework; 9 × 6 artifact sets committed; zero manual re-engineering per station. Full roster in companion `station-roster.md`; workflow detail in companion `workflow-stages.md`; implementation-critical bridge details in companion `bridge-protocol.md`.

### HER-11..HER-13 — Moments 2–4 (Progress, Success, Operations): proclamation surfaces (folded in 2026-08-02 from `spec-herald-moments-2-4`, was CAP-1..CAP-3)

Moment 1 (Pitch, HER-4..10 above) is production-ready. This group covers the three missing
surfaces that close the proclamation cycle and ensure no work ships silently.

- **HER-11 — Progress Visibility Surface (Moment 2).** *Intent:* Make factory motion visible — what shipped, what it cost, what it unblocked. *What it does:* weekly/milestone summary showing station updates, new capabilities, closed gates; cost transparency (compute hours, token spend, wall-clock time per effort); unblock narrative (what downstream work did this unlock); automation trigger — weekly schedule OR manual on shipping milestone; integration — Herald CLI `herald progress <station>`, Herald web surface widget. *Success:* progress surface renders weekly; cost data is accurate (derived from sprint-status + bmad-loop journals); every shipped effort has an unblock narrative.
- **HER-12 — Success Proclamation Surface (Moment 3).** *Intent:* Shipping ≠ being known to ship — create a public claim backed by retrievable evidence. *What it does:* release claim — structured statement ("Project X shipped. Thesis: [what we proved]. Proof: [links to tests, metrics, adoption data]"); evidence integration — automatic link to CI test results, dashboard metrics, user adoption counts, upstream PRs merged; automation trigger — on PR close to main + passing gate-suite; integration — Herald CLI `herald success <project>`, Herald web release archive. *Success:* every closed project has a success claim with ≥1 evidence link; claims are retrievable and dated; no claims exist without proof.
- **HER-13 — Operations Proclamation Surface (Moment 4).** *Intent:* Deprecations, security fixes, end-of-life notices — the unglamorous tail that protects users but nobody announces. *What it does:* notice authoring — structured template for deprecation/fix/EOL notices (what changed, why, migration path, deadline); archive & redirect — notices are permanent and indexed by date/category, old URLs redirect to archive; automation trigger — manual on notice author, no auto-generation; integration — Herald CLI `herald notice author|list|archive`, Herald web notice board. *Success:* every deprecated feature has a notice; every notice links to proof/reason; archive is indexed and searchable; all links are permanent. Story breakdown (7 epics, 12–19 stories) in companion `epic-structure.md`.

## Constraints

### Station-level (unchanged)

- **The Dream is Tier 0 and this Spec is Tier 2.** Where they differ, the Dream is the
  intent and this contract is what was agreed to build from it.
- **Ownership does not move with the work.** Chains stay filed with the owning station
  (Charter §5), whatever surface the work touches.

### From HER-4..HER-10 (deck-family product constraints, folded in 2026-08-02)

- **Design source of truth.** Single Design prototype per station is immutable, etagged, tracked as `.dc.html`. All code-side artifacts derive from it; no direct editing of code-side copies.
- **Tracked vs. gitignored.** Aggressive optimization: track design protos (3–4 files), markdown (5–8), PPTX (2–4), narration (1–2), infographics (0–1). Gitignore fragments (.json), dist/ (HTML), assets/ (JS/CSS), videos (.mp4) — all regenerable.
- **Etagged safety.** All Design ↔ Code transfers use etags. Conflicts detected, never silent overwrites. Protocol: read-file includes etag; write-file requires matching etag or fails explicitly.
- **No fabricated demos.** All screen recordings in video output are real. Never use AI-generated UI or synthetic mockups. Manticore receives real footage + real narration only.
- **Narration identity.** Voice bible derived from published transcripts (WPM, speech patterns, tone markers). Blacklist enforced by script linter; all narration passes linter before video render.
- **Multi-surface readiness.** Decks ship as interactive HTML (Vite), editable PPTX (python-pptx), static SVG infographics (inline), and video scripts (text). Every format must be production-ready; no "preview" or "draft" states in shipping.

### From HER-11..HER-13 (proclamation-surface automation constraints, folded in 2026-08-02)

- **Integration.** All three Moments must integrate with Herald CLI and Herald web surface. No separate platforms; unified UI surface.
- **Automation triggers.** Moment 2 weekly/on-ship, Moment 3 on-PR-close, Moment 4 on-notice-author. Each must have an explicit automation rule.
- **Evidence requirement.** Moment 3 and 4 claims must be backed by retrievable evidence. No claims without proof links.
- **No silent shipping.** Every completed project must have a Moment 3 claim. Enforced by a pre-ship gate.

No contradictions were found across these three groups — they are disjoint domains (station
governance, deck-family product rules, proclamation-surface automation rules) and are kept as
complementary, non-overlapping constraints.

## Non-goals

- **Owning the console.** The Guildhall is Marshal's ([[factory-console]]); Herald supplies its conviction and its look, not its machinery.
- **Infrastructure.** Moved to Marshal in the 2026-07-23 re-scope.
- **~~Re-specifying Moments 2–4 as a separate spec~~ — AMENDED 2026-08-02.** This non-goal previously said Moments 2–4's capability breakdown lived in a separate `spec-herald-moments-2-4` document that this Spec referenced without duplicating. Per the explicit 2026-08-02 user override, that breakdown is now folded in directly as HER-11..HER-13 above; the separate file is archived (not deleted — see the banner note at the top of this document).
- **New deck-authoring infrastructure** (from HER-4..10). Design-code-bridge is already proven on 7 decks; this Spec reuses it, does not rebuild it.
- **New export backends** (from HER-4..10). Deckcraft handles PPTX generation; `deck-export` CLI handles HTML, SVG, others. This Spec composes existing tools, does not invent new ones.
- **New video pipeline** (from HER-4..10). bmad-manticore is upstream. HER-6 feeds it narration scripts and real screen recordings; does not implement the renderer.
- **Real-time collaboration** (from HER-4..10). Design cloud iterates in real-time; pull model is explicit. Not a goal to sync live or merge-edit on the Code side.
- **Replacing Moment 1** (from HER-11..13). Pitch/deck-family (HER-4..10) is complete and separate; HER-11..13 complete the remaining Moments, not reimplement the existing one.
- **Implementing automation yet** (from HER-11..13). This Spec designs the surfaces and automation triggers; implementation (CI hooks, scheduler rules, CLI commands) happens in downstream PRD/Architecture/Epics, not here.
- **Marketing proclamation** (from HER-11..13). Moments 2–4 are internal visibility (what we shipped, what changed, what's deprecated), not external marketing content — HER-4..10 (Pitch) handles that.

## Success signal

A release goes out with a deck, an infographic and notables that no one hand-assembled. **Not
yet true end to end** (2026-08-02): the deck (HER-3 / HER-4..10) is production-ready and
hand-operated; the CLI that mechanizes seed/pull (HER-1 / HER-4) is mid-build; the notables
(HER-2 / HER-11..13) have a full planning chain but no code. Open drift: the bridge's design
intent runs on `claude-design`, an MCP outside the governed tool surface — recorded in
[[agent-tool-surface]]'s coverage table.

**Detailed signals inherited from the folded-in specs** (all still open as of 2026-08-02):

*HER-4..HER-10 (Moment 1 deck family):*
- 9 Design projects seeded (one per pyforge station), all bound to Modernist design system; 9 prototypes authored and iterated per six-act framework.
- 9 × 6 artifact sets (54 total) exported and tracked: `.dc.html`, marp `.md`, `.pptx`, narration `.md`, infographics `.svg`, built outputs (gitignored).
- All 9 HTML decks render without error (`pixi run dashboard-check` passes); all 9 PPTX files open and edit in Microsoft PowerPoint; all infographics render as inline SVG (zero raster).
- All 9 narration scripts extracted and available for manticore; zero manual file transfers (design-code-bridge automation end-to-end); all etagged transfers validated.
- Total tracked footprint: ~144 files (9 stations × ~16 files) vs. ~270 unoptimized (62% reduction).

*HER-11..HER-13 (Moments 2–4 proclamation surfaces):*
- Herald CLI supports `herald progress`, `herald success`, `herald notice`; Herald web surface unifies all three Moments in nav + layout.
- Evidence linking works bidirectionally across Moment 3 (success) and Moment 4 (operations); no claim or notice exists without ≥1 evidence link.
- Automation framework (weekly, on-event, on-manual) executes without errors; all three Moments tested together (integration suite passes).

## Open Questions (carried from HER-4..HER-10, `spec-herald-pitch`, informational — not blocking)

1. **Station-by-station review cadence** — family batch after all 9 are drafted (catches narrative/visual inconsistencies) vs. isolated review. Suggested: family batch.
2. **Video render priority** — all 9 station videos at completion, or pilot subset (Marshal, Warden, Atlas) first? Suggested: pilot subset, full batch on second pass.
3. **Narration extraction tooling** — automated pixi task vs. manual per-station via Claude Design UI. Suggested: automated pixi task with manual review of extraction quality.
