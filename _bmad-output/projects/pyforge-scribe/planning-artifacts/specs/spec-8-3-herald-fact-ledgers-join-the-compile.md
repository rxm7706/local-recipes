---
title: 'Herald fact ledgers join the compile'
type: 'feature'
created: '2026-09-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Herald derives `presentations/<slug>/facts.yaml` as the
currency ledger for each persona deck. The Scribe compile never reads those
files. Agents recalling fleet numbers get CHANGELOG/retro prose (or nothing)
while posters can already show a dated, sourced number.

**Approach:** Add a named compile surface that writes one `kind=doc` node
per `presentations/<slug>/facts.yaml` through `_node_from_text_file` and the
same persist port. Do not parse YAML as a new dependency. Do not ingest the
presentations export tree.

## Boundaries & Constraints

**Always:**
- Citation is the repo-relative `presentations/<slug>/facts.yaml`.
- Kind is `doc` (text surface), never `code`.
- A missing `presentations/` directory is zero nodes and no warning.
- The glob is one slug deep (`presentations/*/facts.yaml`).

**Never:**
- Never `project/*.dc.html`, `src/slides/fragments/`, dated Marp sources, or
  copied `src/deck/` engines as compile sources.
- Never graphify this surface.
- Never require a PyYAML (or other) dependency on the lean scribe env.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| One ledger present | `presentations/pyforge-scribe/facts.yaml` | One `doc:` node; title from `deck:` | Unreadable file uses the existing text-file path (`errors=replace`) |
| No presentations/ | tmp fixture / sparse checkout | Zero fact-ledger nodes | No warning |
| Export tree siblings | `.dc.html`, fragments, `src/deck/` | Not compiled | Ignored by glob |
| Nested or repo-root `facts.yaml` | `presentations/<slug>/nested/facts.yaml` or `./facts.yaml` | Not this surface | Ignored |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` —
  `_read_facts_ledger_surface` after retros, before git
- `src/shared/packages/pyforge-scribe/tests/unit/test_compile.py` —
  ledger present / presentations missing

## Tasks & Acceptance

**Execution:**
- feature: compile one `doc` node per `presentations/*/facts.yaml`
- test: present ledger + ignore export siblings; missing dir is silent
- docs: compile module docstring names the seventh surface

**Acceptance Criteria:**
- Given `presentations/<slug>/facts.yaml` files exist, when
  `scribe graph compile` runs, then each file is one `kind=doc` `GraphNode`
  written through `open_graph_store`, citation
  `presentations/<slug>/facts.yaml`.
- And a repo with no `presentations/` directory compiles with zero
  fact-ledger nodes and no warning.
- And `project/*.dc.html`, `src/slides/fragments/`, dated Marp sources, and
  copied `src/deck/` engines are not compile sources.
- And the ingest is the existing text-file `doc` path, not the graphify extra.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/unit/test_compile.py -k 'facts_ledger or missing_presentations' -q` — expected: green
- Next `SCRIBE_GRAPHIFY_EXTRA=1 scribe graph compile --nightly` (or the 02:30 trigger) — expected: one `doc:` node per live `presentations/*/facts.yaml` without dropping `code:` nodes

## Spec Change Log

- **2026-09-13:** minted from `spec-scribe-graphify-nightly-currency` CAP-3
  and `epics.md` Story 8.3, kinship `spec-deck-family-currency`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `f71a381c3c` (2026-08-15, "doctor: land Story 8.3 -- sprint ledger, dashboard, epics outcome, spec promotion"); also `d2617c4036` (2026-08-15, "doctor: Story 8.3 -- deferred_work_promote.py, the --fix mode"). Ledger row `8-3-herald-fact-ledgers-join-the-compile: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-8-3-the-fix-mode-promotes-the-backlog-and-refuses-on-collision.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`, `docs/dashboard/data.js`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `8-3-herald-fact-ledgers-join-the-compile: done`).
- `## Auto Run Result` reconstructed from git (none survived).
