---
title: "35.1: The deck transport, sync-all, deck tooling and docs site close their open deferrals"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Herald carries open deferred-work rows the operator ruled on 2026-10-03 to close now (deferral burn-down Phases 4 and 5, open medium and low rows together), in exactly one story per station (the same day's ruling on sizing). The rows were measured 2026-10-03 with a parser over `deferred-work-ledger.md` (`## DW-`/`### DW-` entries whose first `status:` reads `open`): 6 medium, 15 low, 1 high (DW-21-7-1, outside Phases 4 and 5) and 49 unrated (outside them too). The mediums: `McpTransport.list_files` raises `TransportCallError` on every live call, because the live `claude-design` server answers with a bare JSON array (DW-21-7-2); `deck sync-all` refuses every standalone HTML poster push, because its byte-equality read-back never matches what Claude Design stores (DW-FU-23-6-1); `deck-trio --deck` refuses four of the ten PyForge posters (DW-FU-21-2); `docsite/build.py` has no unit tests (DW-FU-24-2-1); and two rows whose fix landed on 2026-09-08 but whose status was never closed (DW-FU-18-1, DW-FU-18-3). The lows: an ambiguous layout name resolves to the first match (DW-FU-15-1-2); a garbled README sentence (DW-FU-21-10); an untested stderr note (DW-FU-21-3); a chain-currency row a later cascade cured (DW-herald-59-6); and eleven recommended follow-up reviews of ten landed stories that never ran (DW-1-4-1 with its duplicate DW-1, DW-2, DW-3, DW-FRR-1-2, DW-FRR-15-1, DW-FRR-20-2, DW-FRR-23-1, DW-FRR-23-2, DW-FRR-23-5, DW-FRR-23-6).

**Approach:** Fix each row where its behaviour lives, cluster by cluster: the transport and push path (`transport/mcp_transport.py`, `transport/agent_sdk_transport.py`, `deck_pipeline.py`, `sync_all.py`, with the follow-up reviews of Stories 1.2, 23.1, 23.2 and 23.6); the deck tooling (`scripts/deck_trio.py`, `scripts/deck_facts.py`, the posters' markup, with the review of Story 20.2); the docs site (`docsite/build.py` tests, with the review of Story 23.5); the template pipeline (`pptx_pipeline.py`, with the review of Story 15.1); the bridge core and state layer (the reviews of Stories 1.4, 13.1 and 13.3); and the three rows whose fix already landed (re-read, pin, close). Each row closes in the herald ledger with a `resolution:` naming this story and a `verified:` line citing the `path:line` that holds the fix.

Ledger key: `35-1-the-deck-transport-sync-all-deck-tooling-and-docs-site-close-their-open-deferrals`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- The capabilities that shipped each behaviour (the stories each row below names); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given the live server's bare JSON array answer to `list_files` (directories included) When `McpTransport.list_files` and `AgentSdkTransport.list_files` parse it Then each returns one `ListedFile` per `type == "file"` entry, and the `{"files": [...]}` object still parses
- Given a standalone infographic HTML pushed by `deck sync-all` When the read-back returns the body Claude Design stored Then the push is proven by a comparison that tolerates the server's normalisation (or by the server's content hash) and recorded, and a truly different body is still refused
- Given the ten `presentations/pyforge-*/project/*Infographic standalone.html` posters When `deck-trio --deck` runs on each Then each derives acts and numbered sections with non-empty labels and exits 0, with no poster's visible text changed; a fixture with no act or section structure still exits 2
- Given `docsite/build.py` When `pixi run --frozen -e pyforge-herald pyforge-herald-test` runs Then unit tests exercise `collect_infographics`, `collect_families` and each `check()` predicate, and breaking any one of them fails a test
- Given a template with two layouts sharing one name When a slide references that name Then `_resolve_layout` refuses naming both layout indices, and a unique name still resolves
- Given an ambiguous multi-file surface When `scripts/deck_facts.py --check` runs alone Then its discovery note reaches stderr, and a test pins it (replacing the print with `pass` fails it)
- Given `presentations/presenton-pixi-image/README.md` When it is read Then its Provenance sentence is whole, restored from its last whole revision
- Given DW-FU-18-1, DW-FU-18-3 and DW-herald-59-6, whose fixes already landed When this story re-reads the cited code and re-runs the check Then each row closes citing the line that holds the fix, and a test pins the fix where none does
- Given each recommended follow-up review (Stories 1.2, 1.4, 13.1, 13.3, 15.1, 20.2, 23.1, 23.2, 23.5, 23.6) When it runs as an independent adversarial pass reading the story's shipped code against its spec Then every finding is fixed here with a test, and the row closes naming the review's result
- Given this story lands When its deferred-work rows are read Then each of `DW-21-7-2`, `DW-FU-23-6-1`, `DW-FU-21-2`, `DW-FU-24-2-1`, `DW-FU-18-1`, `DW-FU-18-3`, `DW-FU-15-1-2`, `DW-FU-21-10`, `DW-FU-21-3`, `DW-herald-59-6`, `DW-1-4-1`, `DW-1`, `DW-2`, `DW-3`, `DW-FRR-1-2`, `DW-FRR-15-1`, `DW-FRR-20-2`, `DW-FRR-23-1`, `DW-FRR-23-2`, `DW-FRR-23-5`, `DW-FRR-23-6` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix. Run the touched `tests/scripts/` suites (`test_deck_trio.py`, `test_deck_facts.py`) beside the station suite. Reconcile every Spec `spec-surface` names for a governed path (a memlog entry naming the path, then a scoped stamp; AGENTS.md pre-PR item 5).

**Never:** Never re-push a poster to Claude Design from this story: DW-21-7-1 (the corrupted standalone poster on the live Design project) is the one open high row and is outside Phases 4 and 5. Never change a poster's visible text to make `deck-trio` pass. Never close a row without its landed fix and a cited `verified:` line. Never hand-edit `SPEC.md` or `sprint-status-ledger.yaml`.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phases 4 and 5)

- `DW-21-7-2` (medium) — `McpTransport.list_files` (`src/shared/packages/pyforge-herald/src/pyforge/herald/transport/mcp_transport.py:497`) and `AgentSdkTransport.list_files` (`transport/agent_sdk_transport.py:424`) accept the live server's bare JSON array, keeping the `type == "file"` entries, as well as the `{"files": [...]}` object, and the unit tests assert the live shape.
- `DW-FU-23-6-1` (medium) — The push read-back (`src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py:2076`, reached by `sync_all.py`) proves an HTML artifact with a comparison that tolerates Claude Design's normalisation, or the server's content hash, instead of byte equality, so `deck sync-all` publishes the standalone poster and can reach `unchanged`; a truly different body is still refused.
- `DW-FU-21-2` (medium) — `scripts/deck_trio.py`'s `_DeckStructure` reads the act and section label vocabularies the refused posters carry (`.n`/`.t`, `.act-num`/`.act-title`), and a poster with no act or section markup (herald; marshal's inline-styled sections) gains the standard's `.act`/`.sec`/`.lbl` markup with its visible text unchanged, so `deck-trio --deck` derives all ten PyForge posters.
- `DW-FU-24-2-1` (medium) — Unit tests under `src/shared/packages/pyforge-herald/tests/` exercise `docsite/build.py`'s `collect_infographics`, `collect_families` and each `check()` predicate, each failing when its function is broken.
- `DW-FU-18-1` (medium) — Fixed 2026-09-08 and never closed: `ledger-direction` is in `_DOCTOR_SOURCE_TASKS` (`scripts/detectors.py:213`) with its `ledger-direction-check` task. Confirm it, pin the wiring with a test if none does, and close citing the line.
- `DW-FU-18-3` (medium) — Resolved 2026-09-08 and never closed: Story 18.2's numbered procedure and 18.3's `slides-generator` paragraph both stand in `.claude/skills/bmad-agent-herald/SKILL.md` (`:12`, `:40`), pinned by `tests/meta/test_slides_generator_routing.py`. Confirm and close citing the lines.
- `DW-FU-15-1-2` (low) — `_resolve_layout` (`src/shared/packages/pyforge-herald/src/pyforge/herald/pptx_pipeline.py:179`) refuses a layout name that matches two layouts, naming both indices, instead of taking the first; a unique name still resolves.
- `DW-FU-21-10` (low) — The garbled Provenance sentence at `presentations/presenton-pixi-image/README.md:71` is restored from its last whole revision in git history.
- `DW-FU-21-3` (low) — A `--check`-only test in `tests/scripts/test_deck_facts.py` with an ambiguous multi-file surface asserts `check()`'s stderr discovery note; replacing the print with `pass` fails it.
- `DW-herald-59-6` (low) — Cured by a later cascade: `scripts/chain_currency_sweep_check.py --project pyforge-herald` reads current (measured 2026-10-03). Re-run it and close citing the newest currency-reconciliation section of the herald PRD.
- `DW-1-4-1` (low) — The follow-up review of Story 1.4 (the bridge-core skeleton: state, errors, determinism boundary) against `spec-1-4-bridge-core-skeleton-state-errors-determinism-boundary.md`.
- `DW-1` (low) — The same recommendation as DW-1-4-1, under bmad-loop's generic id; it closes with DW-1-4-1, citing the same review.
- `DW-2` (low) — The follow-up review of Story 13.1 (the state layer survives a second writer).
- `DW-3` (low) — The follow-up review of Story 13.3 (DB-backed storage behind the existing seam, with migrations).
- `DW-FRR-1-2` (low) — The follow-up review of Story 1.2 (the transport port and primary MCP client adapter); it sits on DW-21-7-2's module.
- `DW-FRR-15-1` (low) — The follow-up review of Story 15.1 (template parse-then-fill); it sits on DW-FU-15-1-2's module.
- `DW-FRR-20-2` (low) — The follow-up review of Story 20.2 (deck-facts' per-deck fact ledger); it sits on DW-FU-21-3's module.
- `DW-FRR-23-1` (low) — The follow-up review of Story 23.1 (the account is enumerated and reconciled against the registry).
- `DW-FRR-23-2` (low) — The follow-up review of Story 23.2 (every presentation has a local twin; design systems are mirrored as libraries).
- `DW-FRR-23-5` (low) — The follow-up review of Story 23.5 (the family is browsable and downloadable on Pages); it sits on DW-FU-24-2-1's module.
- `DW-FRR-23-6` (low) — The follow-up review of Story 23.6 (sync-all: one command, idempotent, reported); it sits on DW-FU-23-6-1's module.

A follow-up review row closes when that review has run as an independent adversarial pass (the reviewer reads the story's shipped code against its spec, never the implementer's summary) and every finding is fixed here with a test; if a drain-scheduled follow-up review (marshal Stories 73.1/73.2) closed the row first, this story cites that closure instead of repeating the review.

## Binding

Parent: the capabilities that shipped each behaviour (the stories each row names); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.
Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-10-03 (Phase 4+5) entry.
Ledger key: `35-1-the-deck-transport-sync-all-deck-tooling-and-docs-site-close-their-open-deferrals`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 4+5 rulings (open medium and low deferrals together; one story per station).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
