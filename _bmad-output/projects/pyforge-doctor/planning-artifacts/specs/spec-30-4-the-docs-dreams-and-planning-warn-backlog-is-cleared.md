---
title: '30.4: The docs, Dream and planning warn backlog is cleared'
type: 'fix'
created: '2026-10-24'
status: 'in-progress'
baseline_revision: '9ab7ef1cf1'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_currency.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/hygiene.py
  - docs/dreams/README.md
  - docs/map.yaml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** three warn-only detectors carry 146 standing warnings on `main`, and a full-scope `pr-preflight` shows
each detector as one summary line, so the backlog is read as three findings and rides every run unread.

- **`dreams-hygiene` (121).** 64 `dream-readme-missing` (a Dream file with no `docs/dreams/README.md` row), 23
  `dream-status-trailing-comment` (a `status:` line ending in a `#` comment), 32 `kinship-wikilink-dead` (a Kinship
  `[[slug]]` that resolves to no file under `docs/dreams/`), 2 `realization-log-missing` (an archived Dream with no
  `## Realization log`). The README says the 64 are a backlog whose rows are not added by hand.
- **`docs-currency` (20).** `docs/reference/bmad-estate-llms-full.md` is `kind: generated` with no `generator:` in
  `docs/map.yaml` (its generator is scribe's CLI, and `docs-currency` runs only a `scripts/docs_*.py`); 19 authored
  pages name `sources:` that moved past their `verified:` date, and four of them hold dead references (five in all).
  (A preflight run in another worktree also showed `docs/reference/skills-catalog.md` stale; at this branch's base
  its `--check` is current, so it is not part of the 20.)
- **`bmad-output-hygiene` (5).** Orphan planning files: herald
  `deckcraft-board-epics-displaced-2026-08-08.json`; marshal `change-history/sprint-change-proposal-2026-08-12.md` and
  `change-history/sprint-change-proposal-2026-09-01-drain-self-resolution.md`; steward
  `sprint-change-proposal-2026-08-21.md` and `sprint-change-proposal-2026-08-26-mcp-host-cluster.md`.
- **Origin.** Atlas Story 27.6's session listed the three preflight lines as a follow-up; the operator asked for it in
  session and, shown the 146, chose to clear them all ("All 146").

**Approach:**
1. Give `bmad-estate-llms-full.md` a generator `docs-currency` will run: `scripts/docs_bmad_estate.py`, a door that
   hands both modes to `scribe catalog bmad-estate` (`--check` / `--write`) through the same interpreter, with unit
   tests in `tests/scripts/test_docs_bmad_estate.py`; name it in `docs/map.yaml`. `bmad-estate-check` stays the
   detector of record.
2. For each authored-stale page: read each stale source's history since the page's `verified:` date, check every
   claim the page makes that the source backs, correct what changed, fix each dead reference (or mark a deliberate
   historical citation with the `governance-currency:ignore` markers), then set `verified: 2026-10-24`.
3. For each Dream class: move the `status:` comment to the next line; retarget each dead Kinship link to the Dream that
   absorbed its target (a fold's "Consolidated into" banner, a rename) or drop it where none did; add a
   `## Realization log` to each archived Dream without one, from its own history.
4. Add one `docs/dreams/README.md` row per missing Dream, derived from its own frontmatter (`title:`, `status:`), in
   a table for the backlog; replace the README's sentence that rows are not added by hand with the ruling.
5. Cite each orphan planning file from the record it belongs to (its companion readiness report, its Spec memlog, or
   its epic).
6. Reconcile every Spec governing a changed file (memlog event naming the paths), stamp each, and re-stamp any
   station chain the 2-day chain-currency gate then reds.

Ledger key: `30-4-the-docs-dreams-and-planning-warn-backlog-is-cleared`.
Type / Effort / Deps: fix / L / S-30.3.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-84** (documentation currency) and **CAP-42** (the fleet hygiene sweep): the detectors
  whose backlog this clears. A `fix`, so no CAP, no FR and no flag (`spec-feature-flag-governance` Q1).
- **Origin.** `docs/dreams/pyforge-doctor.md` Realization log, 2026-10-24 (the warn backlog behind three preflight
  lines); the operator's ruling on the `spec-pyforge-doctor` memlog.

## Acceptance Criteria

- **AC1 — Zero warnings.** `python -m pyforge.doctor.sources dreams-hygiene`, `docs-currency` and
  `bmad-output-hygiene` each report no `warn` finding.
- **AC2 — Re-verified, not re-stamped.** Each of the 19 pages' `verified:` moves only with a recorded review of each
  stale source (Auto Run Result lists, per page, what changed and what was corrected).
- **AC3 — Detectors untouched.** No file under `src/shared/packages/pyforge-doctor/src/` changes; under `scripts/`
  only the new `docs_bmad_estate.py` door is added; no check, threshold or severity changes.
- **AC4 — README policy.** The README carries a row for every Dream file, and its backlog sentence states the ruling.
- **AC5 — Suites and gates.** `pixi run -e pyforge-doctor pyforge-doctor-test` green; full-scope `pr-preflight` exit 0.

## Boundaries & Constraints

- Docs, Dreams and planning records, plus the one generator door and its tests; no detector code.
- A generated page is changed only by its generator.
- A Dream's narrative is not rewritten; only the named lines and sections change.

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-doctor` CAP-84, CAP-42 (a `fix`; no CAP minted).
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-24 entry.
- Epic: Epic 30, which reopens until this story is promoted (doctor Story 41.5 lets `ledger-regression` accept it).
- Ledger key: `30-4-the-docs-dreams-and-planning-warn-backlog-is-cleared`; status at mint `backlog`.
- Minted and implemented 2026-10-24 in one session; reviewed by an independent reviewer before landing.

## Verification

- `pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources dreams-hygiene` (and `docs-currency`,
  `bmad-output-hygiene`) — expected: no `warn` line.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the reconcile and stamps.
- `TMPDIR=$HOME/.cache/pyforge-preflight-tmp PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` —
  expected: exit 0.

## Spec Change Log

- 2026-10-24: minted with Story 30.4 under Epic 30 from the Dream entry of that date.

## Auto Run Result

- Worktree `.claude/worktrees/exciting-faraday-1e4549-wt-preflight-warn-hygiene-2026-10-24`, branch
  `preflight-warn-hygiene-2026-10-24`, from `9ab7ef1cf1`. Three workers took disjoint file sets (11 how-to pages; 8
  tutorial, reference and explanation pages; the Dream files); the README rows, the orphans, the generator door, the
  MAP.md row and the reconcile were done by the session that owns the story.
- Evidence for AC2 and the Dream classes, per page and per finding:
  `spec-30-4-the-docs-dreams-and-planning-warn-backlog-is-cleared-evidence.md` (beside this spec).
- `dreams-hygiene` 121 → 0: 23 status comments moved verbatim to their own lines; 32 dead Kinship links in 14 files
  retargeted (`deckcraft`, `design-code-bridge`, `modernist-identity`, `video-scripts` → `[[pyforge-herald|…]]`;
  `pyforge-genesis` → `[[pyforge-charter|pyforge-genesis]]`), turned into a relative link (`presentation-deck` →
  `docs/how-to/presentation-deck.md`), backticked (two sibling-org Dreams that never existed here) or dropped
  (`intelligence-before-foundry`, never a Dream); 2 archived Dreams gained a Realization log from their history; 64
  README rows derived from frontmatter (63 with a verified fold target), the count paragraph and the backlog sentence
  rewritten. Found and fixed on the way: commit `1e845b55fc` had cut the first line of the status comment in
  `marshal-run-watch.md`, `library-catalog-manifest-sync.md` and `run-state-one-publisher.md`; restored from
  `1e845b55fc^`.
- `docs-currency` 20 → 0: 19 pages re-verified (corrections in 17, none needed in 2), five dead references fixed or
  marked historical, and the generator door named in `docs/map.yaml`. Found and fixed on the way: `docs/MAP.md`
  still listed the retired Tier 1 `docs/specs/` folder as live.
- `bmad-output-hygiene` 5 → 0: steward Epic 11 names `sprint-change-proposal-2026-08-21.md` by file; the mcp-host
  readiness report names its proposal; marshal Story 5.10 and the Epic 28 lead-in to 28.18 name theirs; marshal's
  `DW-BOARD-2026-08-08-1` names where the displaced herald epics array is kept.
- Also clean after the change: `docs-map-hygiene`, `general-docs-consistency`, `governance-currency`,
  `dream-chain-check` (exit 0 each); `scripts-lib-test` 985 passed, 3 skipped (with the 9 new door tests).
- Outside these three detectors and not changed: `status-body-consistency` warns on 12 `SPEC.md` files' open
  questions, none of them touched here.
