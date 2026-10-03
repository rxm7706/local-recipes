---
title: "41.3: The board, factory, hygiene and status-body sources read frontmatter one way, and the docs pages say what is true"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Doctor's board, factory, hygiene, status-body, sibling-dream and docs-shelf sources, and the docs pages they police, carry 31 open deferrals (10 medium, 21 low): frontmatter readers that disagree with CAP-81 and with each other, 34 Dreams refused as unparseable, substring and preamble leaks in INV-A, a module cache that leaks between targets, factory checks that skip, fabricate or silently degrade, hygiene checks that crash together or mask orphans, stale doc counts and admonitions, and four recommended follow-up reviews (Stories 12.3, 23.3, 30.2, 30.3) that never ran.

**Approach:** Fix each row where its behaviour lives (one line each below): one shared fence-bounded frontmatter reader for every doctor reader, the 34 openers split, whole-token and section-scoped INV-A, per-check isolation and named WARNs in the factory and hygiene sweeps, the docs pages corrected; then run the four follow-up reviews.

Ledger key: `41-3-the-board-factory-hygiene-and-status-body-sources-read-frontmatter-one-way`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- spec-pyforge-doctor CAP-10-CAP-12, CAP-42, CAP-43, CAP-50, CAP-52, CAP-57, CAP-71-CAP-75, CAP-81, CAP-83, CAP-84, CAP-86 (the capabilities that shipped each behaviour); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a document whose frontmatter holds an indented three-dash line inside a block scalar or an embedded three-dash run When any doctor reader parses it Then all read the same mapping, bounded by the column-0 fence
- Given the 34 repaired Dreams When `dream-chain` and `dreams-hygiene` run Then none is `unparseable-frontmatter`, and the live-tree count tests carry the re-measured numbers
- Given a Spec slug that prefixes another slug, a `## Changelog` section or a heading-less file naming a slug near a CAP id, or a `## Scope (capabilities)` heading When chain-completeness runs Then only real decomposition citations count
- Given an absent `CLAUDE.md`, a `blocked` spec with a matching retro, a `retro-.md` file, an unreadable count source or one raising hygiene check When the factory or hygiene sweep runs Then each yields one named WARN and every other check still runs
- Given two targets in one process When the dashboard-drift gather loads each Then each sees only its own tree's modules
- Given any code row above When its fix is reverted Then at least one test in the station suite fails
- Given each `DW-FRR-<story>` row this story lists When its follow-up review has run Then the reviewed story's spec reads `followup_review_recommended: false` with a dated Review Triage Log entry naming this story, every finding the review raised is fixed here (with a test) or recorded there with its reason, and the row closes citing that log line
- Given this story lands When its deferred-work rows are read Then each of `DW-CHAIN-COMPLETENESS-4`, `DW-FU-6-5-6`, `DW-FU-6-5-8`, `DW-FU-6-8-5`, `DW-FU-6-8-11`, `DW-FU-6-8-12`, `DW-FU-6-9`, `DW-FU-28-1`, `DW-FU-28-1-3`, `DW-FU-28-1-4`, `DW-6-11-1`, `DW-CHAIN-COMPLETENESS-3`, `DW-CHAIN-COMPLETENESS-5`, `DW-FU-6-8-2`, `DW-FU-6-8-6`, `DW-FU-6-8-7`, `DW-FU-6-8-8`, `DW-FU-6-8-9`, `DW-FU-9-2`, `DW-FU-9-2-2`, `DW-FU-9-2-3`, `DW-FU-9-3`, `DW-FU-28-1-2`, `DW-FU-28-1-5`, `DW-FU-23-5`, `DW-FU-30-1`, `DW-FU-30-1-2`, `DW-FRR-12-3`, `DW-FRR-23-3`, `DW-FRR-30-2`, `DW-FRR-30-3` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Split the Dream openers byte-minimally (a line break after the dashes, nothing else), and reconcile and scoped-stamp the two steward-governed Dreams and any other Spec the detector names. Re-measure every live-tree count test the repair moves and record the old and new numbers. Re-verify each row at HEAD before fixing it: a row whose defect a later landing already removed closes citing the `path:line` of that fix and the test that pins it (adding the test when none exists), never on prose alone. Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix. A governed file moves only with its owning Spec's memlog naming it, then a scoped stamp for exactly that Spec (AGENTS.md pre-PR item 5); `spec-pyforge-core` co-governs every station's `src/`. Implementation and the follow-up reviews stay separate personas (AGENTS.md guideline 8). If a marshal follow-up-review dispatch closes a `DW-FRR-*` row first, cite that closure instead of re-running the review.

**Never:** Never rewrite a Dream's content beyond its opener, and never parse an unbounded opener leniently. Never close a row without a landed fix, a `resolution:` naming this story and a `verified:` line citing what was read. Never edit `SPEC.md` by hand or stamp a bare `--write-baseline`. Never weaken or delete a test to make a row pass. Never turn a warn-only finding into a gate.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phases 4 and 5)

31 rows: 10 medium, 21 low.

- `DW-CHAIN-COMPLETENESS-4` (medium) — `board.py`'s per-file stripping keeps only decomposition-relevant sections (epic, story and capability headings) instead of everything after the first `## `, so a `## Changelog` mention of a slug near a CAP id opens no citation window.
- `DW-FU-6-5-6` (medium) — `_load_foreign_module` removes every `sys.modules` entry the executed file added (snapshot before, restore after), so a second target never reuses the first target's transitive imports.
- `DW-FU-6-5-8` (medium) — INV-A matches a Spec's slug and bare id as whole tokens, never substrings, so a slug that prefixes another slug is not read as decomposed.
- `DW-FU-6-8-5` (medium) — `check_spec_status` runs the stale-status check for every non-terminal status (`blocked`, `on-hold`, any unknown value), not only the two listed families.
- `DW-FU-6-8-11` (medium) — `check_spec_indexed` reports one `spec-index-unevaluable` WARN when `CLAUDE.md` is absent, never a `spec-unindexed` WARN per file.
- `DW-FU-6-8-12` (medium) — `check_spec_status` skips a retro whose slug reduces to empty, so a `retro-.md` file flags nothing.
- `DW-FU-6-9` (medium) — `scripts/fleet_scan.py::_task_cmd` treats a `python -m pyforge.doctor…` task as needing its pixi environment, and `_run_detector` reads a traceback exit as `unknown`, not `drift` (the file is governed by `spec-pyforge-marshal`: reconcile its memlog).
- `DW-FU-28-1` (medium) — `status_body_consistency._parse_frontmatter` reads through one fence-bounded frontmatter reader shared by every doctor reader (Story 28.1's rule, CAP-81), so CAP-3 and CAP-81 give one verdict per document.
- `DW-FU-28-1-3` (medium) — The glued opener on line 1 of the 34 `docs/dreams/*.md` files is split (a line break after the three dashes); the two steward-governed ones (`spec-mcp-era-isolation`, `spec-mcp-host-real-station-tools`) get a memlog entry and a scoped stamp each, and the live-tree counts the repair moves (`test_live_tree_kinship_wikilink_dead_count` and its siblings) are re-measured.
- `DW-FU-28-1-4` (medium) — `_unparseable_frontmatter_item` names the refusal cause (an unbounded opener, a glued opener, a non-mapping) and gives the remedy that matches it.
- `DW-6-11-1` (low) — `test_sources_factory.py` asserts `classify()`'s literal label for every rule, the spike-report rule included.
- `DW-CHAIN-COMPLETENESS-3` (low) — `_parse_declared_cap_ids` recognises a capabilities heading case-insensitively and with trailing text (`## Scope (capabilities)`); a SPEC carrying CAP ids under no recognised heading is a named WARN, not a silent fall-back to the substring check.
- `DW-CHAIN-COMPLETENESS-5` (low) — A source file with no `## ` heading goes through the same relevant-section rule, so it keeps nothing unless a decomposition heading is found and opens no false citation window.
- `DW-FU-6-8-2` (low) — `factory.gather` computes `_ground_truth()` and `_live_version()` once and threads them into each check.
- `DW-FU-6-8-6` (low) — `check_archive_hygiene` walks `implementation-artifacts/` recursively and `planning-artifacts/` for stray suffixes, so every stray file is reported once.
- `DW-FU-6-8-7` (low) — `check_dream_owners`'s `dream-unowned` message derives the station count from `docs/governance/guild-roster.json`.
- `DW-FU-6-8-8` (low) — `check_counts`'s four ground-truth probes report an unreadable source file as a named WARN instead of returning `0` or being skipped as `None`.
- `DW-FU-6-8-9` (low) — `check_coverage` carries its classification summary (files classified per bucket) as an OK Finding's evidence on every run, clean ones included.
- `DW-FU-9-2` (low) — `hygiene.gather` (and `board.gather_chain_completeness`'s same shape) degrades a `PermissionError` or a vanished directory in `projects_dir.iterdir()` or a per-project `is_dir()` to a WARN.
- `DW-FU-9-2-2` (low) — `_evaluate_station` isolates each of its five hygiene checks, so one that raises degrades to its own WARN and the rest still run.
- `DW-FU-9-2-3` (low) — `_has_inbound_references` matches the candidate's path or basename at a path or word boundary and also searches untracked, non-ignored files, so an incidental substring no longer masks an orphan.
- `DW-FU-9-3` (low) — Every hygiene class sets `evidence["path"]` against one base (repo-root-relative), `_check_stale_dream_status` included.
- `DW-FU-28-1-2` (low) — `factory.py::_doc_pin` takes the frontmatter through the shared fence-bounded reader, so a pin after an embedded three-dash run in a scalar is found.
- `DW-FU-28-1-5` (low) — The other readers the row names (`hygiene.py:252`, `board.py:430`, `sibling_dreams.py:120`, `status_body_consistency.py:512`) close the block only at a column-0 fence, through the shared reader.
- `DW-FU-23-5` (low) — A repeatable check (in `docs_shelf`) reds a live doc that cites the old `_bmad-output/` root path of the five archived files, with a test.
- `DW-FU-30-1` (low) — `docs/how-to/github-actions-recipe-ci.md:7` points at the generated workflow table (`docs/reference/github-workflows.md`) instead of a hand-typed count.
- `DW-FU-30-1-2` (low) — `docs/explanation/pyforge-estate-overview.md`'s `:::note` admonitions become GitHub's `> [!NOTE]` form, and `docs/_STYLE_GUIDE.md` names that one admonition syntax for `docs/`.
- `DW-FRR-12-3` (low) — Run the recommended independent follow-up review of Story 12.3's landed diff against its spec (a review persona that did not implement it); fix its findings in this story or record why each stands, write them to that spec's Review Triage Log, and set its `followup_review_recommended: false`.
- `DW-FRR-23-3` (low) — Run the recommended independent follow-up review of Story 23.3's landed diff against its spec (a review persona that did not implement it); fix its findings in this story or record why each stands, write them to that spec's Review Triage Log, and set its `followup_review_recommended: false`.
- `DW-FRR-30-2` (low) — Run the recommended independent follow-up review of Story 30.2's landed diff against its spec (a review persona that did not implement it); fix its findings in this story or record why each stands, write them to that spec's Review Triage Log, and set its `followup_review_recommended: false`.
- `DW-FRR-30-3` (low) — Run the recommended independent follow-up review of Story 30.3's landed diff against its spec (a review persona that did not implement it); fix its findings in this story or record why each stands, write them to that spec's Review Triage Log, and set its `followup_review_recommended: false`.

## Binding

Parent: spec-pyforge-doctor CAP-10-CAP-12, CAP-42, CAP-43, CAP-50, CAP-52, CAP-57, CAP-71-CAP-75, CAP-81, CAP-83, CAP-84, CAP-86 (the capabilities that shipped each behaviour); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.
Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-03 (Phase 4+5) entry.
Ledger key: `41-3-the-board-factory-hygiene-and-status-body-sources-read-frontmatter-one-way`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 4+5 rulings (fix every open medium deferral and the lows in the modules it touches, no blanket closure; sizing override the same day: fewer, larger stories split by package area, at most about 30 rows each).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
