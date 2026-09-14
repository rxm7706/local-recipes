---
id: SPEC-design-sync-loop
spec: design-sync-loop
status: ready   # 2026-09-14 — derived by bmad-spec (headless, express) from the Dream the same day it
                # was seeded; the operator answered all four open questions before derivation, so
                # the contract is complete and downstream may bind. Decompose into herald stories
                # before any code moves (Spec → Story before code).
owner-dream: docs/dreams/design-sync-loop.md
companions: []
surface: []     # Deliberately empty until the first story lands: the loop's own module, the
                # registry's exclusion/design-system entries, the family-page templates and the
                # new twins do not exist yet, and every surface the loop CALLS is already governed
                # by the Spec that owns it (currency, lockstep, pages, the herald kernel). The
                # story that mints a file declares it here.
sources:
  - ../../../../../../docs/dreams/design-sync-loop.md
open_questions: []
---

> **Canonical contract.** This SPEC is the complete contract for what to build, test and validate.
> `docs/dreams/design-sync-loop.md` is listed in `sources:` for narrative rationale and for the
> operator's four rulings in their own words.
>
> **Binds, never re-mints.** The refresh and the mirror are `spec-deck-family-currency` CAP-2/4/5/6;
> the trio and export-set derivations are `spec-deck-family-lockstep` (Epic 21.1–21.5, 21.10); the
> bridge verbs are the herald kernel (`seed` / `pull` / `push` / `status` / `watch`); the gallery is
> `spec-pyforge-pages` CAP-1. This Spec sequences them into one idempotent loop and extends them
> where the operator's rulings require — Design-wins pull, the account-wide registry, the family
> page — minting nothing they already cover.

# The Design sync loop

## Why

A pain to solve, stated by the operator on 2026-09-14 the afternoon the second manual poster sweep
landed. Keeping the deck family true is a hand-driven act an agent performs from memory of a runbook,
one deck at a time: the 2026-09-14 sweep moved nine posters and left the Infographic heads, the
Infographic Decks, the executive summaries, the Marp sources and the PowerPoints exactly as stale as
they were, because no shipped capability moves them. The Design account holds more projects than
`presentations/` has twins, the bridge sees 10 of 15, currency runs repo-side-first while the
operator wants Design's edits to win, and Pages publishes the posters and nothing else. The Dream is
one command that enumerates the account, pulls what Design changed, refreshes every fact-bearing
surface from one ledger, re-derives the family, pushes, proves, publishes — and does nothing the
second time it runs.

## Capabilities

- **CAP-1 — The account is enumerated and reconciled.**
  - **intent:** Every Design project the operator's login can see is classified — presentation,
    design system, or excluded by name — and mapped to a local twin and a registry section, or
    listed as excluded with its reason.
  - **success:** `herald deck status` lists every project the account returns (paging past the
    first 20): presentations report `linked`, design systems `mirrored`, `REMOVED-PyForge Unifying
    Strategy` and `Local recipes repository connection` `excluded` with the recorded reason; no
    project is absent from the report.
- **CAP-2 — Every presentation has a local twin.**
  - **intent:** A Design project that is a presentation exists under `presentations/<slug>/` with
    its prototype pulled and a machine-owned registry section; the three design systems are
    mirrored as libraries.
  - **success:** The fourteen decks, `agentic-sdlc`, `six-quarter-roadmap` and
    `llm-knowledge-bases` each resolve through `registry.read`; `Modernist`, `Broadsheet` and
    `Nocturne` are pulled byte-exact to the design-system home (see Assumptions); a second run
    pulls nothing.
- **CAP-3 — Pull, with Design winning.**
  - **intent:** For every twin whose Design etag moved since the last recorded pull, the loop takes
    Design's bytes wholesale.
  - **success:** After a human edit in Design, one run leaves the repo copy byte-identical to
    Design (harness stripped) and records the new etag; a repo-side edit Design has not seen is
    overwritten and named in the report, never merged.
- **CAP-4 — The ledger re-applies over what was pulled.**
  - **intent:** After the pull, every marked literal on every fact-bearing surface — the standalone
    poster first; the trio, executive summary and Marp as Epic 21.3/21.5 make them markable — is
    rewritten from a `facts.yaml` re-derived at the current tree.
  - **success:** `deck-facts <slug> --check` reads `0 drifted, 0 mismatch` for every deck after a
    run, and the report lists each literal the ledger overrode together with the value Design had.
- **CAP-5 — The family derives and the PowerPoints regenerate.**
  - **intent:** Each deck's Infographic head, Infographic Deck, Executive Summary, Marp sources and
    PPTX are re-derived from the refreshed standalone and ledger.
  - **success:** The trio derives via `deck-trio` (21.1/21.2); the export set via `deck-export`
    (Marp path, the default) or `pptx-spec`/`pptx-fill` (a deck whose registry section declares a
    `.potx`); every derived file's stamp names the tree and etag it derived at; a deck whose host
    lacks Chrome reports `derive-skipped: no chrome` rather than failing the run.
- **CAP-6 — Push what changed; prove the mirror.**
  - **intent:** Only artifacts whose bytes changed are pushed to their Design project, and every
    pushed artifact is read back.
  - **success:** Read-back is byte-identical for 100% of pushed files; the Design etag is recorded
    in the deck README ledger and in bridge state; a second run pushes nothing.
- **CAP-7 — The family is browsable and downloadable on Pages.**
  - **intent:** The dossier site gains one family page per registered deck and an index across the
    family.
  - **success:** Each family page shows the poster, the Infographic Deck and the Executive Summary
    in view, offers the PPTX(s) and Marp sources as downloads, stamps each with its etag and tree,
    and is built by `docsite/build.py` inside the one existing Pages deployment; `site-check`
    passes.
- **CAP-8 — One command, idempotent, reported.**
  - **intent:** `herald deck sync-all` runs CAP-1..7 in order for every deck (or one `--slug`) and
    prints a per-deck report — pulled / overrode / derived / pushed / published / unchanged.
  - **success:** Two consecutive runs: the second reports every deck `unchanged` with zero writes to
    git or Design; `--dry-run` prints the same report without writing.

## Constraints

- **Git is the archive of record and the source of facts; Design is the editing surface.** "Design
  wins" governs prototype content only — `facts.yaml` is derived from the tree and is never pulled.
- **Binds, never re-mints.** The loop sequences shipped mechanics — `deck-facts` (currency
  CAP-2/5/6), `deck-export`, the kernel's `seed`/`pull`/`push`/`status`/`watch`, DesignSync
  `finalize_plan` → `write_files` (`localPath`), the CAP-4 read-back recipe, `docsite/build.py`
  (pages CAP-1) — and calls Epic 21's derivations (21.1–21.5, 21.10) where they exist.
- **One Pages deployment** (`dashboard.yml`); Kedro-Viz stays at `/kedro-viz/` (pgs:CAP-2).
- **Session-run.** Every Design read and write rides the operator's claude.ai login and no runner
  credential exists, so the loop is invoked from a session and must be idempotent because it will
  be re-run by hand.
- **Measure the artifact, never the container.** Byte comparisons strip the injected serve harness;
  a Design bundle with fonts and runtime is not the poster.
- **Excluded projects are excluded by name, with a reason, in the registry** — never by a
  heuristic, never silently.

## Non-goals

- Authoring new decks, changing the infographic standard, or redesigning any poster.
- Unattended or CI-scheduled runs (until a runner can hold a Design credential).
- A second Pages site or deployment.
- Three-way merging of Design and repo edits — ruled out: Design wins, the ledger re-applies.
- Giving design-system mirrors a poster, a fact ledger or a Pages page.

## Success signal

An operator runs `herald deck sync-all` after a week in which humans edited three decks in Design
and the fleet landed forty stories: the run pulls the three, overrides the fleet counts a human had
retyped, re-derives every trio and export, pushes only what changed, proves every push byte-identical,
and the Pages family index shows every deck with its downloads stamped at today's tree. The operator
runs it again immediately and every deck reports `unchanged`.

## Assumptions

- The design-system mirrors live at `presentations/_design-systems/<name>/` — a sibling no deck glob
  matches, so no currency or Pages surface picks them up; moving them to a top-level sibling is a
  one-line surface edit if downstream prefers.
- "Every project the account returns" means paging past `list_projects`' 20-item first page (Scribe
  and Steward were absent from that page on 2026-09-14).
- PPTX regeneration needs Chrome on the loop's host (marp CLI); absence degrades to a named skip,
  not a failed run.
