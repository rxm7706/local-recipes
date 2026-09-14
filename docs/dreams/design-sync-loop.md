---
title: The Design sync loop — every Design project has a local twin, and one command keeps the whole family true
type: dream
owner: herald
status: specified   # 2026-09-14 — seeded, answered and specified the same afternoon: the operator's
                    # four requirements (verbatim under § The Dream), the four open questions ruled
                    # the same hour, and spec-design-sync-loop derived `ready` by bmad-spec (CAP-1..8,
                    # open_questions []). Herald Epic 23 carries the eight stories. Every fact under
                    # § What is real was measured on main at 168bbedb13.
---

# The Design sync loop — every Design project has a local twin, and one command keeps the whole family true

## The Dream

The operator's ask, 2026-09-14, in their own words:

> We want the repeatable DesignSync to do 3 things — 1) Every design project should be available
> locally in `presentations/`. 2) Standalone HTML posters need to be synced (**Claude Design edits
> win over local copies**) and refreshed to the latest facts and state of the repo. 3) The remaining
> PowerPoint decks, Marp content (called *deck family*) in each Design project needs to be
> refreshed. 4) The synced posters and PowerPoints should be available on GitHub Pages for users to
> browse and download.

Today each of those is a hand-driven act, done by an agent in a session, one deck at a time, from
memory of a runbook. The second sweep (2026-09-14) took nine `finalize_plan` prompts, nine
`write_files`, nine `render_preview` read-backs and a hand-written ledger row per deck to move nine
posters — and it deliberately left the Infographic heads, the Infographic Decks, the executive
summaries, the Marp sources and the PowerPoints exactly as stale as they were, because no shipped
capability moves them. The Dream is that **the loop is one command**: it enumerates the Design
account, pulls what Design changed, refreshes every fact-bearing surface from the same ledger,
re-derives the family, pushes the result back, proves the mirror, and publishes — and that running
it twice in a row is a no-op.

> A deck family that is current only on the day an agent remembered the runbook is not current.

## What is real (measured 2026-09-14 on `main` at `168bbedb13`)

- **The Design account holds more projects than `presentations/` has twins.** `list_projects`
  returns 20+ (the tool pages at 20; `PyForge Scribe deck` and `PyForge Steward deck` exist and
  were not in the first page). Fourteen are deck projects with a local twin. Beside them:
  `Agentic AI SLDC deck` (twin: `presentations/agentic-sdlc/`, **unregistered** with herald's
  registry); `PyForge six-quarter roadmap` and `LLM Knowledge Bases` (**no local twin at all**);
  `REMOVED-PyForge Unifying Strategy` (the ad-hoc duplicate Story 21.11 found, renamed to mark it
  retired); `Local recipes repository connection` (the retired mirrored-app-tree project the deck
  spec names as the cautionary tale); and three **design systems** — `Modernist`, `Broadsheet`,
  `Nocturne` — which are libraries the decks bind to, not decks.
- **`herald deck status` reports 10 of 15 linked.** The registry (each README's machine-owned
  *Design project* section) and the gitignored `.herald/bridge-state.json` are the bridge's two
  halves; the four chain decks and `agentic-sdlc` have no registry section, so the bridge cannot
  see them (Story 21.10 is the backlog row for the fourteen).
- **Poster currency is solved repo-side-first, and only for the standalone.**
  `spec-deck-family-currency` CAP-6 is `deck-facts <slug> --refresh --check` → DesignSync push →
  read-back; git is the source and Design the mirror. The operator's rule for the loop inverts the
  direction — **Design edits win** — so the loop must *pull first*, then refresh, then push. The
  2026-09-14 sweep proved the push and read-back mechanics 9/9 byte-identical.
- **The rest of the family has no refresh path.** The `- Infographic.dc.html` head, the
  `- Infographic Deck.dc.html`, the `- Executive Summary.dc.html`, `src/marp/*.md` and
  `src/pptx/*.pptx` carry the literals of the day they were authored (July–September). Epic 21
  (`deck-family-lockstep`) owns deriving the trio from the standalone (21.1–21.4) and the exec
  summaries + export set (21.5); `deck-export` regenerates standalone HTML + PPTX from Marp via the
  marp CLI (PPTX needs Chrome); `herald deck push` (kernel CAP-5) pushes regenerated derived
  exports back into Design; `herald deck pptx-spec` / `pptx-fill` (Story 15.1) fill a template
  into a genuinely editable deck. The pieces exist; nothing sequences them.
- **Pages publishes the posters and nothing else.** `docsite/build.py` (`spec-pyforge-pages`,
  live at `rxm7706.github.io/local-recipes/infographics/`) renders the standalone infographics
  into a gallery from configured globs. No PPTX, Marp, executive summary or per-deck family page
  is published or downloadable; `dashboard.yml` is the one Pages deployment and must stay so
  (pgs:CAP-2).
- **The loop cannot run unattended today.** Every Design read and write goes through the
  operator's claude.ai login (the `claude-design` MCP server and `DesignSync` in a Claude Code
  session; herald's `McpTransport` needs a resolved credential). A GitHub Actions runner has none of
  that. `herald deck watch` polls for Design-side edits from a session.

## What it looks like when real

- `pixi run -e pyforge-herald herald deck sync-all` (name provisional) enumerates the account,
  reconciles the registry against it, and for every registered deck runs: **pull** (Design wins
  for every prototype and poster whose Design etag moved since the last pull) → **refresh**
  (`deck-facts --refresh` over every marked surface, so the human's visual edits survive and the
  numbers come from the ledger) → **derive** (trio, executive summary, Marp, PPTX from the
  refreshed standalone) → **push** (only what changed) → **prove** (read-back byte-identical, etag
  recorded) → **publish** (the Pages family page picks up the new artifacts). A second run reports
  every deck `unchanged` and writes nothing.
- Every Design project that is a presentation has a `presentations/<slug>/` twin with a registry
  section; projects that are not presentations are listed once in the registry as *excluded*, with
  the reason, so the loop never silently skips them.
- Pages has one page per deck: the poster (view), the Infographic Deck and Executive Summary
  (view), the PowerPoints and Marp sources (download), each with the etag/tree the artifact was
  derived at — and an index across the family.

## Open questions for the Spec — asked and answered 2026-09-14 (operator)

1. **Scope of "every Design project."** **Ruled: presentations *and* design systems.** Every
   presentation project gets a `presentations/<slug>/` twin with a registry section — the 14 decks,
   `agentic-sdlc` (registered at last), and new twins for `PyForge six-quarter roadmap` and
   `LLM Knowledge Bases`. The three design systems (`Modernist`, `Broadsheet`, `Nocturne`) are
   mirrored too, so the styling libraries the decks bind to are versioned alongside them (home to
   be chosen by the Spec — `presentations/_design-systems/<name>/` or a sibling dir; they are not
   decks and get no poster, ledger or Pages page). `REMOVED-PyForge Unifying Strategy` and `Local
   recipes repository connection` are **excluded by name** in the registry, with the reason, so the
   loop lists them as skipped rather than silently ignoring them.
2. **The conflict rule.** **Ruled: Design wins, then the ledger re-applies.** The loop pulls Design
   wholesale for every prototype and poster whose etag moved — the human's visual and prose edits
   survive — and then `deck-facts --refresh` rewrites every *marked* literal from the ledger. A
   human who changed a fleet count in Design is overridden by the tree, and the loop's report names
   every literal it overrode so the override is visible, never silent.
3. **Where PowerPoints come from.** **Ruled: both, per deck.** Marp-derived is the default — the
   Marp sources are refreshed from the ledger and `deck-export` regenerates the PPTX in-repo (marp
   CLI + Chrome on the machine running the loop); a deck that declares a `.potx` template is
   filled through `pptx-spec` / `pptx-fill` (Story 15.1) instead. The registry section records
   which path a deck takes; both push to Design and both publish.
4. **Pages shape and cadence.** **Ruled: extend the dossier site, on demand.** One Pages
   deployment (`dashboard.yml`, pgs:CAP-2); a family page per deck — poster, Infographic Deck and
   Executive Summary to view, PowerPoints and Marp sources to download, each stamped with the etag
   and tree it was derived at — plus an index across the family. The loop runs from an operator
   session (`herald deck sync-all`, or `herald deck watch` for the pull half); unattended runs are
   out of scope until a Design credential exists that a runner can hold.

## Constraints / Non-goals

- Git stays the archive of record and the *source* for facts; Design is the editing surface. "Design
  wins" is a rule about *prototype content*, not about `facts.yaml`, which is derived from the tree.
- One Pages deployment (`dashboard.yml`), per `spec-pyforge-pages` CAP-2.
- The loop binds to the shipped mechanics — `deck-facts`, `deck-export`, `herald deck
  seed/pull/push/status/watch`, DesignSync `finalize_plan` → `write_files`, the read-back recipe —
  and does not re-mint them. Epic 21's stories are its inputs, not its competitors: where 21.x
  builds a derivation the loop calls it.
- Not in scope: authoring new decks; the infographic standard itself; redesigning any poster.

## Kinships

- [[deck-family-currency]] — realized; CAP-1..6 are the refresh, mirror and check the loop calls.
- [[deck-family-lockstep]] — specified; Epic 21 derives the trio and export set the loop sequences,
  and 21.10 makes the registry see all fourteen.
- [[pyforge-pages]] — specified; the one Pages deployment the family page extends.
- [[pyforge-herald]] — the station; its kernel Spec owns the bridge verbs.
- [[vocabulary-one-name-one-job]] — `DW-VOCAB-2026-09-14-3` carries the agentic-sdlc deck's
  Design-side edits the loop's pull direction would make routine.

## Realization log

- **2026-09-14 (later still)** — **Specified.** `bmad-spec` (headless, express) derived
  `spec-design-sync-loop` at `ready` from this file: CAP-1 enumerate + reconcile the account,
  CAP-2 every presentation has a twin (design systems mirrored as libraries), CAP-3 pull with Design
  winning, CAP-4 the ledger re-applies, CAP-5 the family derives and PPTX regenerates (both paths per
  deck), CAP-6 push-changed + prove, CAP-7 the Pages family page, CAP-8 one idempotent, reported
  command. Self-validate PASS on both passes. Decomposed the same day into herald Epic 23, Stories
  23.1–23.8, one per CAP, all `backlog`; 23.5 waits on Epic 21.1/21.2/21.5 for the derivations it
  calls.
- **2026-09-14 (later)** — The four questions answered by the operator: presentations *and* design
  systems in scope (two retired projects excluded by name); Design wins then the ledger re-applies;
  PowerPoints both ways per deck (Marp-derived default, template-filled where a `.potx` is declared);
  the dossier site extended with a family page per deck, run on demand from a session. `bmad-spec`
  derives the Spec from this file next.
- **2026-09-14** — Seeded from the operator's four-requirement ask, the afternoon PR #1361 landed
  the second manual sweep. Four open questions are the operator's; nothing downstream binds until
  they are answered and `bmad-spec` derives the Spec.
