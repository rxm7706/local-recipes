---
title: "41.6: Chain-completeness counts the one-chain fold's citation window again"
type: 'fix'
created: '2026-10-04'
status: 'in-progress'
baseline_revision: 'd8bb280f2d26d9dc19260f371227827dac5dc81f'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/retros/retro-pyforge-doctor-2026-10-04.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_completeness.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_board.py
  - docs/governance/spec-one-chain-per-station/.memlog.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** since Story 41.3, chain-completeness INV-A no longer reads the one-chain fold's citation window. Six
station Specs read `spec-not-decomposed` FAIL on `main` as a result: atlas, doctor, marshal, scribe, steward and
warden. Warden's finding names CAP-2 and CAP-5..22.

- **The predicate.** `_check_project_chain_completeness` (`src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py`)
  builds INV-A's citation prose with `_extract_decomposition_prose` (about :393). That function keeps only the
  sections `_DECOMP_SECTION_OPEN_RE` (about :242) opens: `## Epic N`, `## Capabilities` / `## Scope (capabilities)`
  and `### Story N`.
- **Where it came from.** It was introduced in `26a298ed12` (`wip: 41.3 (auto-checkpoint)`) and landed with
  `bc562fc6b8` (`Merge pyforge-doctor/41-3 into main`). It fixed DW-CHAIN-COMPLETENESS-4: a `## Changelog`
  section could open a false citation window. Before it, each file's prose ran from its first `## ` heading.
- **What it dropped.** Each station's `epics.md` opens with `## Fold provenance (2026-09-17)` (mason's spells it
  `## Fold provenance — 2026-09-17`). That section cites `spec-pyforge-<station> CAP-1..N` and calls itself "the
  INV-A citation window". The one-chain pilot made that the remedy for a `ready` station Spec, whose reminted CAPs
  INV-A demands (`docs/governance/spec-one-chain-per-station/.memlog.md`, 2026-09-16 pilot lesson 11; there,
  `DEFERRED_SPECS` is the wrong hatch). The allowlist leaves the heading out, so those citations vanish.
- **Measured on `1d62151fe2`.** With `_extract_decomposition_prose` restored to the pre-41.3 slicing, INV-A reports
  zero `spec-not-decomposed` findings. With the 41.3 allowlist plus `## Fold provenance`, it also reports zero.
- **Not a shipped-CAP rule.** Whether a CAP shipped plays no part in either result. Warden's CAP-23..CAP-26 are
  `ready` and stay covered by the citations in Epics 13-16.
- **Why it hid.** The Detectors summary row names only the last output line (`scripts/detectors.py:346`), so the
  six FAILs read as warden's alone.

**Approach:** add the `## Fold provenance` heading to `_DECOMP_SECTION_OPEN_RE`, matching any trailing text and the
same case rule as its neighbours. Its section then counts as decomposition prose like an epic section. Nothing
else in INV-A changes:

- The citation window (`_cited_cap_ids_by_spec`) stays as it is.
- The per-Spec anchoring stays as it is.
- The zero-CAP fallback stays as it is.
- The delivered-Spec branch stays as it is.
- 41.3's exclusion of every other non-decomposition section stays as it is.

Pin the rule with a fixture and a live-tree test. Story 41.3 had neither, which is how the regression reached
`main`.

Ledger key: `41-6-chain-completeness-counts-the-fold-provenance-window-again`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** The chain-completeness verdict (FR-15, Story 6.6) and CAP-57 (INV-A parses capability
  ids, not a bare substring match; Story 12.3). This is a defect of shipped behaviour, so it mints no new CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.
- **Origin.** Found by the Epic 41 retrospective (`retro-pyforge-doctor-2026-10-04.md`, finding 1).

## Acceptance Criteria

- Given the live tree When `board.gather_chain_completeness(repo_root)` runs Then no `spec-not-decomposed` finding
  names `spec-pyforge-warden`, while warden's CAP-23..CAP-26 still read `ready` in its `SPEC.md`. None names
  `spec-pyforge-atlas`, `spec-pyforge-doctor`, `spec-pyforge-marshal`, `spec-pyforge-scribe` or
  `spec-pyforge-steward` either. A live-tree test in `tests/unit/test_sources_board.py` asserts it.
- Given a project whose Spec declares CAP-1..3 and whose `epics.md` `## Fold provenance (2026-09-17)` section cites
  that Spec's CAP-1..2, and no epic, story or capabilities section cites CAP-3 When INV-A runs Then one
  `spec-not-decomposed` FAIL names CAP-3 alone. A truly undecomposed open CAP still fails.
- Given the same Spec with a fold-provenance section citing CAP-1..3 When INV-A runs Then there is no
  `spec-not-decomposed` finding, and the em-dash spelling `## Fold provenance — 2026-09-17` behaves the same.
- Given a `## Changelog` section that names the Spec's slug near CAP-3 When INV-A runs Then CAP-3 is still
  reported uncovered. The DW-CHAIN-COMPLETENESS-4 fix holds.
- Given the `## Fold provenance` alternative removed from `_DECOMP_SECTION_OPEN_RE` When the station suite runs
  Then the fold-provenance fixture test and the live-tree test fail (mutation).

## Boundaries & Constraints

**Always:**
- Fix it where the shipped behaviour lives: `_DECOMP_SECTION_OPEN_RE`.
- Keep the heading match anchored at column 0, at `## ` level, tolerant of trailing text such as a date in
  parentheses or after an em dash.
- Measure the live tree before and after, and record both counts in the Auto Run Result.
- Reconcile the governed files on their owning Specs' memlogs and stamp them scoped. `spec-pyforge-doctor` owns
  `board.py`, and `spec-pyforge-core` co-governs every station's `src/` (AGENTS.md pre-PR item 5).

**Never:**
- Never exempt a CAP by its shipped, verified or retired status; the live tree shows the status plays no part.
- Never add a Spec to `DEFERRED_SPECS` to clear a finding.
- Never edit any station's `epics.md`, PRD or `SPEC.md` to make a finding pass.
- Never widen the allowlist to PRD requirement sections, a `## Changelog`, or "any `## ` heading". That is an open
  question for a ruling (retro § Open questions), not this fix.
- Never weaken or delete an existing INV-A test.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-04 (later) entry.
- Epic: Epic 41 (a fix joins its own epic, which reopens; Story 41.5).
- Ledger key: `41-6-chain-completeness-counts-the-fold-provenance-window-again`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Minted 2026-10-04 from the Epic 41 retrospective, alongside it, in one chain PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`: no `spec-not-decomposed` line for any of the six
  station Specs. Read the detail section, not the Detectors summary row.
- `pixi run --frozen -e pyforge-guild detectors-ci`: the `chain-completeness` row is no longer red on
  `spec-not-decomposed`.
- Mutation: delete the `## Fold provenance` alternative and re-run the station suite. Both new tests fail. Restore
  it.
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 after the memlog reconciles and scoped stamps.

## Review Triage Log

- No review has run yet.
