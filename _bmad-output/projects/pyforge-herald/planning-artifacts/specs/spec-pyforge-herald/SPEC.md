---
id: SPEC-pyforge-herald
spec: pyforge-herald
status: ready
updated: '2026-09-20'
owner-dream: docs/dreams/pyforge-herald.md
covers-dreams:
  - docs/dreams/deck-family-currency.md
  - docs/dreams/deck-family-lockstep.md
  - docs/dreams/deck-visual-qa.md
  - docs/dreams/design-sync-loop.md
  - docs/dreams/herald-moments-2-4-live-backend.md
  - docs/dreams/herald-moments-2-4-missing-surface.md
  - docs/dreams/herald-pitch.md
  - docs/dreams/pptx-custom-shapes.md
  - docs/dreams/pptx-deck-generation.md
  - docs/dreams/pyforge-herald.md
  - docs/dreams/pyforge-pages.md
surface:
  - src/shared/packages/pyforge-herald/**
  - presentations/**
  - presentations/pyforge-*/project/* Infographic standalone.html
  - presentations/pyforge-*/facts.yaml
  - presentations/pyforge-*/README.md
  - presentations/README.md
  - scripts/deck_facts.py
  - docs/specs/presentation-deck.md
  - presentations/pyforge-*/project/*.dc.html
  - presentations/pyforge-*/src/marp/**
  - presentations/pyforge-*/src/pptx/**
  - presentations/{unity-data-stack,wasm-analytics-stack,deckcraft,presenton-pixi-image}/**
  - scripts/deck_trio.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/transport/mcp_transport.py
  - src/shared/packages/pyforge-herald/pyproject.toml
  - src/shared/packages/pyforge-herald/
  - src/shared/packages/pyforge-herald/src/pyforge/herald/**
  - docsite/**
  - .github/workflows/dashboard.yml
  - docs/dashboard/index.html
surface-drift-exclude:
  - src/shared/packages/pyforge-herald/src/pyforge/herald/station_api.py
  - presentations/pyforge-atlas/facts.yaml
  - presentations/pyforge-atlas/project/PyForge Atlas Infographic standalone.html
  - presentations/pyforge-atlas/README.md
  - presentations/pyforge-doctor/facts.yaml
  - presentations/pyforge-doctor/project/PyForge Doctor Infographic standalone.html
  - presentations/pyforge-doctor/README.md
  - presentations/pyforge-herald/facts.yaml
  - presentations/pyforge-herald/project/PyForge Herald Infographic standalone.html
  - presentations/pyforge-herald/README.md
  - presentations/pyforge-marshal/facts.yaml
  - presentations/pyforge-marshal/project/PyForge Marshal Infographic standalone.html
  - presentations/pyforge-marshal/README.md
  - presentations/pyforge-mason/facts.yaml
  - presentations/pyforge-mason/project/PyForge Mason Infographic standalone.html
  - presentations/pyforge-mason/README.md
  - presentations/pyforge-scribe/facts.yaml
  - presentations/pyforge-scribe/project/PyForge Scribe Infographic standalone.html
  - presentations/pyforge-scribe/README.md
  - presentations/pyforge-steward/facts.yaml
  - presentations/pyforge-steward/project/PyForge Steward Infographic standalone.html
  - presentations/pyforge-steward/README.md
  - presentations/pyforge-warden/facts.yaml
  - presentations/pyforge-warden/project/Warden Infographic standalone.html
  - presentations/pyforge-warden/README.md
  - presentations/pyforge-genesis/facts.yaml
  - presentations/pyforge-genesis/project/PyForge Genesis Infographic standalone.html
  - presentations/pyforge-genesis/README.md
  - presentations/pyforge-unifying-strategy/facts.yaml
  - presentations/pyforge-unifying-strategy/project/PyForge Unifying Strategy Infographic standalone.html
  - presentations/pyforge-unifying-strategy/README.md
  - presentations/README.md
companions:
  - artifact-tracking-matrix.md
  - workflow-stages.md
  - six-act-framework.md
  - station-roster.md
  - bridge-protocol.md
  - epic-structure.md
sources:
  - ../../../../../../docs/dreams/pyforge-herald.md
open_questions: []
---

> **Canonical contract.** Derived from `.memlog.md` (herald one-chain fold 2026-09-17) and the Dream in `sources:`. Do not hand-edit — append the memlog and re-derive.


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

**Current state (re-grounded 2026-09-09; the 2026-08-02 text below it was written while the
station was still mid-build and no longer matched this Spec's own `status: ready`).** The deck
family (Moment 1
content) is production-ready. HER-1's CLI mechanization shipped: Epics 1–5 are `done` and
`seed`/`pull`/`status`/`watch` are wired (`cli.py:226-318`); `cli.py` is 1764 lines wiring 26
subparsers. Moments 2–4 shipped too — Epics 8–10 landed 47 stories on 2026-08-08 — as the
CLI-triggered/local-storage v1, not the live-service version (that contract is
`spec-herald-moments-2-4-live-backend`, `in-progress`). The detailed capability breakdown for
both Moment 1's deck-family orchestration (HER-4..HER-10) and Moments 2–4's proclamation
surfaces (HER-11..HER-13) lives inline below, folded in from their own formerly-separate Specs
on 2026-08-02.

Herald's Four Moments of Proclamation, in full: **Pitch** (HER-4..HER-10 — a Dream must be
argued, not merely filed), **Progress** (HER-11 — a build in flight is not self-explaining),
**Success** (HER-12 — shipping is not the same as being known to have shipped), **Operations**
(HER-13 — the long tail nobody announces).

## Capabilities

- **CAP-1 — a Dream becomes a deck.** ← spec-pyforge-herald HER-1 (shipped 2026-09-17)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** `herald seed` renders a Dream into a deck and `herald pull` brings the designed result back; the round trip is the realized [[design-code-bridge]] (elaborated in HER-4 below). *Shipped* (re-grounded 2026-09-09): the CLI foundation and the `seed`/`pull`/`status`/`watch` subcommands are all wired and tested (`cli.py:226-318`).

- **CAP-2 — releases are proclaimed from the ledger.** ← spec-pyforge-herald HER-2 (shipped 2026-09-17)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** release notables compile from pipeline data, never hand-written. *Status* (re-grounded 2026-09-09): the detailed breakdown that used to live in a separate `spec-herald-moments-2-4` document is inline as HER-11 (Progress), HER-12 (Success) and HER-13 (Operations) below, and shipped as the CLI-triggered v1 in Epics 8–10 (47 stories, 2026-08-08). The automatic, ledger-triggered version is `spec-herald-moments-2-4-live-backend`'s contract and has never run.

- **CAP-3 — the visual identity is one system.** ← spec-pyforge-herald HER-3 (shipped 2026-09-17)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** decks, infographics and the Guildhall share [[modernist-identity]]'s vocabulary (elaborated in HER-7 below).

- **CAP-4 — Design-Code-Bridge Framework.** ← spec-pyforge-herald HER-4 (shipped 2026-09-17)
  - **intent:** Automate the round-trip between Claude Design (visual authoring) and Code (repository).
  - **success:** prototype round-trips seamlessly between Design and Code; etagged safety prevents overwrites; zero manual file transfers; 7 decks proven. This is the realized mechanism behind HER-1's `seed`/`pull`.

- **CAP-5 — Deckcraft Framework.** ← spec-pyforge-herald HER-5 (shipped 2026-09-17)
  - **intent:** Generate editable PowerPoint from Markdown sources without sacrificing manual refinement.
  - **success:** PPTX files are editable in PowerPoint; formatting and layout choices preserved; regenerable from markdown in 5–10s. *Scope note:* this is the narrow "render markdown to PPTX" slice of the broader standalone `deckcraft` AI-pipeline product (prompt/document → deck via local LLMs) — that broader product's own PRD/Architecture/Spec were archived in the 2026-08-01 consolidation (commit `409b3357bd`); only this reused rendering capability survived into Herald's own chain.

- **CAP-6 — Video-Scripts Framework.** ← spec-pyforge-herald HER-6 (shipped 2026-09-17)
  - **intent:** Extract narration scripts from decks and feed them into video production pipelines (bmad-manticore).
  - **success:** narration scripts extracted and available; video production ready; no fabricated demos; all b-roll is real.

- **CAP-7 — Modernist-Identity Framework.** ← spec-pyforge-herald HER-7 (shipped 2026-09-17)
  - **intent:** One visual language across all PyForge surfaces (decks, dashboards, docs, exports, videos) — the mechanism behind HER-3.
  - **success:** Modernist design system adopted across all Herald family decks; 7 decks bound; tokens ready for PPTX ↔ Figma ↔ video round-trip.

- **CAP-8 — Six-Act Deck Framework.** ← spec-pyforge-herald HER-8 (shipped 2026-09-17)
  - **intent:** Canonical structure for all pitch decks to ensure consistency and narrative clarity.
  - **success:** all 9 decks follow six-act structure; all contain persona appendices; all render full depth; all use L.A.T.C.H. visual principles consistently. Full structure detail in companion `six-act-framework.md`.

- **CAP-9 — Multi-Format Export.** ← spec-pyforge-herald HER-9 (shipped 2026-09-17)
  - **intent:** Deliver 6 artifact formats per station from a single Design prototype.
  - **success:** all 6 formats available per station; tracked/gitignored split correct; regeneration strategy reduces footprint by 62%; no manual file copies. Full tracking rationale in companion `artifact-tracking-matrix.md`.

- **CAP-10 — Station-Specific Customization.** ← spec-pyforge-herald HER-10 (shipped 2026-09-17)
  - **intent:** Apply the framework consistently across 9 pyforge stations with domain-appropriate content.
  - **success:** 9 Design projects seeded; 9 prototypes authored per six-act framework; 9 × 6 artifact sets committed; zero manual re-engineering per station. Full roster in companion `station-roster.md`; workflow detail in companion `workflow-stages.md`; implementation-critical bridge details in companion `bridge-protocol.md`.

- **CAP-11 — Progress Visibility Surface (Moment 2).** ← spec-pyforge-herald HER-11 (shipped 2026-09-17)
  - **intent:** Make factory motion visible — what shipped, what it cost, what it unblocked.
  - **success:** progress surface renders weekly; cost data is accurate (derived from sprint-status + bmad-loop journals); every shipped effort has an unblock narrative.

- **CAP-12 — Success Proclamation Surface (Moment 3).** ← spec-pyforge-herald HER-12 (shipped 2026-09-17)
  - **intent:** Shipping ≠ being known to ship — create a public claim backed by retrievable evidence.
  - **success:** every closed project has a success claim with ≥1 evidence link; claims are retrievable and dated; no claims exist without proof.

- **CAP-13 — Operations Proclamation Surface (Moment 4).** ← spec-pyforge-herald HER-13 (shipped 2026-09-17)
  - **intent:** Deprecations, security fixes, end-of-life notices — the unglamorous tail that protects users but nobody announces.
  - **success:** every deprecated feature has a notice; every notice links to proof/reason; archive is indexed and searchable; all links are permanent. Story breakdown (7 epics, 12–19 stories) in companion `epic-structure.md`.

- **CAP-14 — from spec-deck-family-currency** ← spec-deck-family-currency CAP-1 (shipped 2026-09-17)
  - **intent:** One codified infographic standard exists that any author or reviewer can check a poster against — the six-act arc with act bands, the full-depth section set adapted per subject, the inline-diagram floor, the length class and the source-cited-facts rule — with Unifying Strategy as the structure, acts and length reference and Warden as the density and visual-form reference.
  - **success:** `infographic-standard.md` is the standard's single home and `docs/specs/presentation-deck.md`'s verify checklist points to it; each rebuilt poster's README ledger records its measured values (sections, act bands, inline SVGs, bytes, cited facts) against the floors; a poster below any floor is not marked current.

- **CAP-15 — from spec-deck-family-currency** ← spec-deck-family-currency CAP-2 (shipped 2026-09-17)
  - **intent:** Every count, version, status and date a poster shows is traceable to a live source through a per-deck fact ledger, `presentations/<slug>/facts.yaml`, re-derivable on demand from the tracked ledgers and manifests — never from a prior poster or from memory.
  - **success:** Each of the ten decks has a `facts.yaml` whose rows carry `id`, `value`, `source`, `method` and `shown_as`, under a document header naming the `tree` (HEAD sha) and `derived_at` (HEAD commit date); every swept token (`n/n`, `x.y.z`, `YYYY-MM-DD`) and every `data-fact` mark the poster shows resolves to a row; re-deriving on an unchanged tree reproduces the file byte-identically; re-deriving after a tracked source changes reports the changed rows.

- **CAP-16 — from spec-deck-family-currency** ← spec-deck-family-currency CAP-3 (shipped 2026-09-17)
  - **intent:** Each PyForge-branded poster is rebuilt to the standard from its fact ledger, repo-side and at full depth.
  - **success:** All ten `presentations/pyforge-*/project/<Name> Infographic standalone.html` meet CAP-1's floors and cite CAP-2's rows; each renders headless to a full-page PNG with no clipped or blank region, and the README ledger records the render date and page height; each lands through its own PR.

- **CAP-17 — from spec-deck-family-currency** ← spec-deck-family-currency CAP-4 (shipped 2026-09-17)
  - **intent:** The Design mirror carries the same bytes as git for every rebuilt poster, and the bridge knows about it.
  - **success:** Each poster is pushed to its Design project through the DesignSync local-path pipeline; the README ledger records the returned etag and byte count; a read-back is byte-identical (content-identical after the harness strip above 256 KiB); `herald deck status` reports the deck linked; `pyforge-unifying-strategy` has a Modernist-bound Design project holding its poster.

- **CAP-18 — from spec-deck-family-currency** ← spec-deck-family-currency CAP-5 (shipped 2026-09-17)
  - **intent:** Poster staleness is detectable — an advisory check compares each poster's fact tokens against a fresh derivation and names the stale posters and rows.
  - **success:** After a tracked ledger changes a value a poster shows, the check names that poster and row; on an unchanged tree it reports clean; it always exits 0 and is invocable as a pixi task.

- **CAP-19 — from spec-deck-family-currency** ← spec-deck-family-currency CAP-6 (shipped 2026-09-17)
  - **intent:** A stale marked literal is refreshed mechanically from the ledger — `deck-facts <slug> --refresh` re-derives the ledger and rewrites every `data-fact` mark whose text no longer equals its row, preserving the literal's shape (`N/M` vs `N of M`, a leading `v`), so a poster follows its ledger without hand edits.
  - **success:** After a tracked ledger moves, `--refresh` leaves `--check` at 0 `mismatch` on the marks it rewrote, reports each rewrite (`id`, old → new), leaves the file byte-identical outside the rewritten text spans, exits 0, and reports nested or unresolvable marks instead of rewriting them.

- **CAP-20 — from spec-deck-family-lockstep** ← spec-deck-family-lockstep CAP-1 (ready 2026-09-17)
  - **intent:** The trio derives from the standalone — a verb turns a current standalone into its Infographic head (`.dc.html`, `x-dc` wrapper, styles in the helmet) and its Infographic Deck (the same sections re-laid as 1920×1080 slides), so the three can no longer disagree.
  - **success:** Run over a rebuilt deck, the head's body matches the standalone's exactly modulo the wrapper and style placement, the Infographic Deck carries one slide per numbered section, both render without error, and a second run changes nothing.

- **CAP-21 — from spec-deck-family-lockstep** ← spec-deck-family-lockstep CAP-2 (ready 2026-09-17)
  - **intent:** Every marked surface of a deck refreshes together — `deck-facts <slug> --refresh` walks the poster, head, Infographic Deck, exec summary and marp sources, so one ledger move updates all of them.
  - **success:** After a tracked ledger changes, one `--refresh` leaves every surface of that deck at 0 `mismatch`, and `--check` reports per surface.

- **CAP-22 — from spec-deck-family-lockstep** ← spec-deck-family-lockstep CAP-3 (ready 2026-09-17)
  - **intent:** The Standard export set is current in every format — the exec summary and marp sources carry marked facts, and `deck-export` regenerates both PPTX from them.
  - **success:** For every deck the six companions are regenerated from current sources and dated the rebuild day; no README still reads "standalone ahead".

- **CAP-23 — from spec-deck-family-lockstep** ← spec-deck-family-lockstep CAP-4 (ready 2026-09-17)
  - **intent:** Fourteen decks, not ten — the four chain decks are rebuilt to the standard from their own fact ledgers, registered and linked.
  - **success:** `herald deck status` reports every deck in `presentations/` linked with its project id, and each of the four meets the `infographic-standard.md` floors at 0 unmarked / 0 mismatch.

- **CAP-24 — from spec-deck-family-lockstep** ← spec-deck-family-lockstep CAP-5 (ready 2026-09-17)
  - **intent:** The Design side is used as a design surface — at least one deck goes through a real visual pass in Claude Design and returns through a byte-exact pull.
  - **success:** A dated Design-side edit is pulled to git, the read-back is byte-identical after the harness strip, the deck README records the etag, and the pull discipline is demonstrated end to end.

- **CAP-25 — from spec-deck-family-lockstep** ← spec-deck-family-lockstep CAP-6 (ready 2026-09-17)
  - **intent:** The transport speaks the `mcp` SDK it actually has pinned — `pyforge.herald. transport.mcp_transport` imports whichever streamable-HTTP client symbol the pinned `mcp` SDK actually exports, and `pyforge-herald`'s own `pyproject.toml` floor is reconciled with `pixi.toml`'s environment pin so the two agree.
  - **success:** A real `herald deck push` against a live Design project round-trips (push, then read back byte-identical) through the fixed transport, and `deck-facts <slug> --check` reports 0 `mismatch` afterward.

- **CAP-26 — from spec-deck-visual-qa** ← spec-deck-visual-qa CAP-1 (ready 2026-09-17)
  - **intent:** A headless-render-to-PNG step callable after any deck build: drive the deck engine's existing per-slide `#/<n>` URL-hash routes with headless Chromium (playwright-python, already pinned in the pixi envs per `docs/reference/library-llms-full.md` — no new dependency), screenshot every slide `manifest.json` names at the native 1920×1080 frame, and emit one PNG per slide plus a contact sheet — an artifact a human or LLM reviewer actually looks at instead of trusting "the build didn't crash."
  - **success:** Run against the worked-example deck (`presentations/agentic-sdlc/`, 45 slides, PR #50), it emits exactly one PNG per manifest entry (named by slide index/id) plus one contact sheet, and a reviewer can spot a visually broken slide from the sheet alone. A slide that renders badly still yields its PNG — the run reports, it never aborts on ugliness.

- **CAP-27 — from spec-deck-visual-qa** ← spec-deck-visual-qa CAP-2 (ready 2026-09-17)
  - **intent:** A format-agnostic unedited-placeholder scan reframed for Herald's own convention: flag slides shipping with unfilled image slots, catching BOTH spellings — `<image-slot placeholder="…">` in prototype/fragment sources AND the dashed `.image-slot` placeholder `<div>` the extractor converts them to (`presentation-deck.md` § extraction). Explicitly NOT the source org's PowerPoint-specific "Click to add"/Lorem-ipsum regex.
  - **success:** Run against `presentations/agentic-sdlc/` today, it flags exactly slide 40 ("In action"), whose three `<image-slot>` panels are documented in `presentation-deck.md`'s own placeholder table as deliberately left for real screenshots — a live true positive. A deck with every slot filled reports clean.

- **CAP-28 — from spec-deck-visual-qa** ← spec-deck-visual-qa CAP-3 (ready 2026-09-17)
  - **intent:** Both gates emit into one machine-readable report keyed by gate id (gate → status → per-slide findings → paths to reviewer-facing artifacts), designed so the three parked `.pptx`-contingent gates — `check_xml` OOXML ordering, `check_typst_safety`, `audit_overflow` — can register as new gate ids later without reworking the report shape, the entrypoint, or any consumer.
  - **success:** Adding a stub third gate id requires no change to the report schema or to the two v1 gates' output; the report round-trips (parse it back, address each gate's findings by id).

- **CAP-29 — The account is enumerated and reconciled.** ← spec-design-sync-loop CAP-1 (ready 2026-09-17)
  - **intent:** Every Design project the operator's login can see is classified — presentation, design system, or excluded by name — and mapped to a local twin and a registry section, or listed as excluded with its reason.
  - **success:** `herald deck status` lists every project the account returns (paging past the first 20): presentations report `linked`, design systems `mirrored`, `REMOVED-PyForge Unifying Strategy` and `Local recipes repository connection` `excluded` with the recorded reason; no project is absent from the report.

- **CAP-30 — Every presentation has a local twin.** ← spec-design-sync-loop CAP-2 (ready 2026-09-17)
  - **intent:** A Design project that is a presentation exists under `presentations/<slug>/` with its prototype pulled and a machine-owned registry section; the three design systems are mirrored as libraries.
  - **success:** The fourteen decks, `agentic-sdlc`, `six-quarter-roadmap` and `llm-knowledge-bases` each resolve through `registry.read`; `Modernist`, `Broadsheet` and `Nocturne` are pulled byte-exact to the design-system home (see Assumptions); a second run pulls nothing.

- **CAP-31 — The sweep pulls every twin Design changed.** ← spec-design-sync-loop CAP-3 (ready 2026-09-17)
  - **intent:** Bound to the kernel's `herald deck pull` / `deck watch` — Design's bytes win wholesale whenever the etag moved, never a merge. This Spec adds the sweep over *every* twin and the report line that names a repo-side edit Design had not seen and was overwritten.
  - **success:** One `sync-all` run pulls every twin whose Design etag moved since the last recorded pull, each byte-identical to Design (harness stripped), and the report names each overwrite; a twin whose etag did not move is not touched.

- **CAP-32 — The ledger re-applies, and says what it overrode.** ← spec-design-sync-loop CAP-4 (ready 2026-09-17)
  - **intent:** Bound to `deck-facts --refresh` over every marked surface after the pull (lockstep CAP-2 / Story 21.3, currency CAP-6). This Spec adds only the report of each overridden literal together with the value it replaced.
  - **success:** `deck-facts <slug> --check` reads `0 drifted, 0 mismatch` for every deck after a run, and the report lists each literal the ledger overrode with the value Design had.

- **CAP-33 — The `.potx` path, and every derived file stamped.** ← spec-design-sync-loop CAP-5 (ready 2026-09-17)
  - **intent:** The Marp path is lockstep CAP-3 (Story 21.5). This Spec owns the second path the operator ruled — a deck whose registry section declares a `.potx` is filled through `pptx-spec`/`pptx-fill` — the per-deck choice recorded in the registry, and a stamp (tree + etag) on every derived trio/export artifact.
  - **success:** A `.potx` deck yields a genuinely editable PPTX from its template, a Marp deck yields exactly what 21.5 yields, every derived file's stamp names the tree and etag it derived at, and a host without Chrome reports `derive-skipped: no chrome` rather than failing the run.

- **CAP-34 — PowerPoints push back, and every push proves itself.** ← spec-design-sync-loop CAP-6 (ready 2026-09-17)
  - **intent:** Changed-only, etag-guarded poster push is the kernel's `herald deck push`. This Spec owns what it lacks: the binary PPTX push Story 5.1 deferred, and the read-back proof as a verb rather than a curl recipe.
  - **success:** A binary push is proven live on one PPTX and adopted for the pair; every pushed file is read back through the serve URL with the harness stripped and is byte-identical; the etag is recorded in the README ledger and bridge state; a read-back mismatch is a refusal that names the file; a second push pushes nothing.

- **CAP-35 — The family is browsable and downloadable on Pages.** ← spec-design-sync-loop CAP-7 (ready 2026-09-17)
  - **intent:** The dossier site gains one family page per registered deck and an index across the family.
  - **success:** Each family page shows the poster, the Infographic Deck and the Executive Summary in view, offers the PPTX(s) and Marp sources as downloads, stamps each with its etag and tree, and is built by `docsite/build.py` inside the one existing Pages deployment; `site-check` passes.

- **CAP-36 — One command, idempotent, reported.** ← spec-design-sync-loop CAP-8 (ready 2026-09-17)
  - **intent:** `herald deck sync-all` runs CAP-1..7 in order for every deck (or one `--slug`) and prints a per-deck report — pulled / overrode / derived / pushed / published / unchanged.
  - **success:** Two consecutive runs: the second reports every deck `unchanged` with zero writes to git or Design; `--dry-run` prints the same report without writing.

- **CAP-37 — DB-backed storage layer.** ← spec-herald-moments-2-4-live-backend LB-1 (in-progress 2026-09-17)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** two writers hitting the same store concurrently never lose an update, and the CLI verbs behave identically across the swap.

- **CAP-38 — Webhook endpoint.** ← spec-herald-moments-2-4-live-backend LB-2 (in-progress 2026-09-17)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** a merged PR produces a progress record with zero operator action.

- **CAP-39 — Cron scheduler.** ← spec-herald-moments-2-4-live-backend LB-3 (in-progress 2026-09-17)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** the weekly aggregation and the 7-day re-validation both run without anyone remembering them.

- **CAP-40 — the shape API + autofit engine (→ 15.2).** ← spec-pptx-custom-shapes CAP-1 (ready 2026-09-17)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** See absorbed Spec memlog and git history.

- **CAP-41 — template-parse-then-fill (→ 15.1).** ← spec-pptx-deck-generation CAP-1 (ready 2026-09-17)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** See absorbed Spec memlog and git history.

- **CAP-42 — custom shapes + real autofit (→ 15.2, downstream).** ← spec-pptx-deck-generation CAP-2 (ready 2026-09-17)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** See absorbed Spec memlog and git history.

- **CAP-43 — from spec-pyforge-pages** ← spec-pyforge-pages CAP-1 (ready 2026-09-17)
  - **intent:** The dossier YAML is the only source of truth; the Pages site, the infographic gallery, and the Claude Artifact build are renders of it.
  - **success:** Changing a sentence in `docsite/content/dossier.yml` and running `pixi run -e site site-check` rebuilds every page from that file; no second hand-edited HTML copy of the dossier exists in git.

- **CAP-44 — from spec-pyforge-pages** ← spec-pyforge-pages CAP-2 (ready 2026-09-17)
  - **intent:** The Pages root is the dossier landing page; Kedro-Viz stays at `/kedro-viz/` and is linked from it; the repository still has one Pages deployment.
  - **success:** `dashboard.yml` builds the site into `docs/dashboard/` and remains the only workflow that calls `deploy-pages`; Kedro-Viz is still served at `/kedro-viz/`.

- **CAP-45 — from spec-pyforge-pages** ← spec-pyforge-pages CAP-3 (ready 2026-09-17)
  - **intent:** Operators have a local pixi loop — build, check, verify figures, serve — without growing the `build` environment export.
  - **success:** `site`, `site-check`, `site-verify`, and `site-serve` exist under `[feature.site]`; `pixi project export conda-environment -e build` leaves `environment.yaml` byte-identical.

- **CAP-46 — from spec-pyforge-pages** ← spec-pyforge-pages CAP-4 (ready 2026-09-17)
  - **intent:** Marked dossier figures are compared to the source tree so drift is visible; editorial judgment stays human.
  - **success:** `verify_claims.py` runs in CI as an annotation with `continue-on-error`; local `site-verify` may exit 1 on drift.

- **CAP-47 — from spec-pyforge-pages** ← spec-pyforge-pages CAP-5 (ready 2026-09-17)
  - **intent:** The Claude Artifact host receives a body-only render from the same templates as the site.
  - **success:** `build.py --check` asserts the artifact shell has no wrapping `<html>` / `<body>` that the host already supplies.
- **CAP-48 — the windowed Design read never loops on a stalled window** ← spec-pyforge-herald CAP-48 (in-progress 2026-09-18)
  - **intent:** `deck_pipeline._windowed_read` refuses, with a named error, a server that returns a window whose `last_line` did not advance, instead of looping forever.
  - **success:** A fake transport returning the same `(last_line, total_lines)` pair twice raises a typed pagination error naming the file and the stalled line; every existing live-shaped fixture (3377-line, 136,293-byte pulls) still pages to completion byte-exact; DW-FU-23-2 closes with the test as evidence.
- **CAP-49 — the docsite has a PR gate** ← spec-pyforge-herald CAP-49 (in-progress 2026-09-18)
  - **intent:** A change that touches `docsite/**` (or the templates/content it renders) cannot merge with every gate green while `docsite/build.py` or `site-check` would fail.
  - **success:** A `pull_request`-triggered lane, path-filtered to `docsite/**` and the dashboard render inputs, runs `docsite/build.py --check` and `site-check` and is red on a fixture regression (a broken family-page template) and green on `main`; `pr-preflight` gains the same leg so the local run predicts the lane; `dashboard.yml` stays the only `deploy-pages` caller; DW-FU-23-5 closes with the lane's first green run as evidence.
- **CAP-50 — the second `sync-all` run is proven unchanged on a real deck** ← spec-pyforge-herald CAP-50 (ready 2026-09-18)
  - **intent:** The idempotency promise of `herald deck sync-all` is a recorded, repeatable, one-command live proof against a seeded deck with real Design credentials and real tracked state — not a fake-only test plus a memory.
  - **success:** An opt-in task (`HERALD_LIVE_SYNC_PROOF=1`, never in the default gate, listed in doctor's `live-proof-surfaces.md`) runs `sync-all --slug <seeded deck>` twice against live Design and asserts the second report is all-`unchanged` with zero git and zero Design writes, writing the two reports and the etag/tree stamps to `.herald/sync-proof/<slug>/`; run once by the operator on 2026-09-1x with the artifacts committed as the story's evidence; DW-FU-23-6 closes citing that run.
- **CAP-51 — the deck pipeline runs from the Guild env** ← spec-pyforge-herald CAP-51 (ready 2026-09-20)
  - **intent:** `deck_pipeline.py`'s `DeckExporter` and `sync_all.py`'s `FactsRefresher` / trio step shell `pixi run -e pyforge-guild deck-export | deck-facts | deck-trio` (registered in `guild-tasks` with their deps in `pyforge-guild` — steward 63.6), never `-e local-recipes`; the pipeline's fakes and the live sync proof keep their shapes.
  - **success:** no `-e local-recipes` string remains in `pyforge-herald/src`; `test_deck_pipeline`'s argv assertions read the Guild env; `deck-sync-proof`'s opt-in live run still passes; steward 63.6's meta-test lists no herald offender; `pyforge-herald-test` green.

## Fold provenance

One-chain fold 2026-09-17: CAPs reminted sequentially from 1; absorbed folders keep pointer + memlog + companions. Station Spec stays `ready`.
