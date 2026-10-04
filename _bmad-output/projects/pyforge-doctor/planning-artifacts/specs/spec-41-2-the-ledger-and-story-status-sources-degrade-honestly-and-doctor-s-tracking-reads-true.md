---
title: "41.2: The ledger, story-status and capability-effect sources degrade honestly, the source dispatch passes its scope through, and doctor's own tracking reads true"
type: 'fix'
created: '2026-10-03'
status: 'blocked'
baseline_revision: 'dfe4007e46d463427406b4ab022cc94760e0bc63'
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

**Problem:** Doctor's ledger-regression, story-status, frozen-path and capability-effect sources, its source dispatch and registry, and doctor's own tracking surfaces carry 24 open deferrals (11 medium, 13 low): parsers that truncate, mis-read quoting or skip alias and duplicate keys, reads that call an empty or failed measurement clean, a dispatcher that drops scoping flags, a capability join that resolves 7% of CAP rows, a registered Source nothing emits, and epics Status lines and SPEC text that lag the ledger.

**Approach:** Fix each row where its behaviour lives (one line each below): one status parser and one terminal test for both modules, NUL-split git reads, WARNs for every cannot-evaluate case, flag pass-through in the dispatcher, a wider capability join with the flag inventory re-run, and the SPEC changes through a memlog entry and the `bmad-spec` re-derive.

Ledger key: `41-2-the-ledger-and-story-status-sources-degrade-honestly-and-doctor-s-tracking-reads-true`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- spec-pyforge-doctor CAP-9, CAP-17-CAP-19, CAP-53, CAP-77, CAP-84, CAP-86 (the capabilities that shipped each behaviour); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a feed with a column-0 comment, a quoted or commented `done`, an alias-form key, a duplicate key and `epic-N` rows When the ledger and story-status gathers run Then every story key is read, each once, and epic rows are not counted as stories
- Given a failed `git ls-tree`, a subdirectory target, zero tracked ledgers at both revisions or a non-UTF-8 ledger byte When the ledger or durability gather runs Then each is one named WARN, never an OK and never a traceback
- Given `python -m pyforge.doctor.sources ledger-regression --base <rev> --head <rev>` or an `--inv` filter on dream-chain or chain-completeness When it runs Then the gather receives the scope
- Given the live tree When `flag-inventory` is re-run Then the `unresolved` CAP count is lower than 722 and the row's `verified:` line records the new count
- Given doctor's `epics.md` and tracked ledger When the live-tree test compares them Then every story's `**Status:**` line matches its ledger status
- Given any code row above When its fix is reverted Then at least one test in the station suite fails
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-6-4-4`, `DW-FU-6-4-7`, `DW-FU-6-4-9`, `DW-FU-6-4-15`, `DW-FU-6-4-16`, `DW-FU-6-4-17`, `DW-FU-6-4-19`, `DW-FU-6-4-23`, `DW-FU-6-4-24`, `DW-FU-6-4-25`, `DW-doctor-34-4`, `DW-FU-6-4-5`, `DW-FU-6-4-6`, `DW-FU-6-4-10`, `DW-FU-6-4-18`, `DW-FU-6-4-21`, `DW-FU-20-3`, `DW-FU-6-9-3`, `DW-FU-6-9-4`, `DW-FU-6-2`, `DW-FU-10-1-5`, `DW-FU-23-6`, `DW-FU-23-6-2`, `DW-FU-30-3` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Make the SPEC.md changes only through a memlog entry and the `bmad-spec` re-derive; if the render is refused, record that in the story and leave the two rows open for the operator's render. Keep the frozen report schema additive-only. Re-verify each row at HEAD before fixing it: a row whose defect a later landing already removed closes citing the `path:line` of that fix and the test that pins it (adding the test when none exists), never on prose alone. Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix. A governed file moves only with its owning Spec's memlog naming it, then a scoped stamp for exactly that Spec (AGENTS.md pre-PR item 5); `spec-pyforge-core` co-governs every station's `src/`.

**Never:** Never rename or remove a `Source` member, and never re-key a check other consumers read without updating them in this change. Never close a row without a landed fix, a `resolution:` naming this story and a `verified:` line citing what was read. Never edit `SPEC.md` by hand or stamp a bare `--write-baseline`. Never weaken or delete a test to make a row pass. Never turn a warn-only finding into a gate.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phases 4 and 5)

24 rows: 11 medium, 13 low.

- `DW-FU-6-4-4` (medium) — `_ledger_paths` tells a failed `git ls-tree` (one `ledger-regression` WARN naming the error) from a ref that genuinely holds no ledgers.
- `DW-FU-6-4-7` (medium) — The `_git` wrappers in `sources/ledger.py` and `sources/marshal.py` degrade a `UnicodeDecodeError` from `cli_bridge.run_git` to a WARN, keeping both modules' "never raises" contract.
- `DW-FU-6-4-9` (medium) — `gather_story_status`'s Route 3 recognises alias-form story keys with the same prefix rule as `ledger.py`'s `_ID_PREFIX_RE`, so a legacy `a1-…` key gets its hand-landed commit evaluated.
- `DW-FU-6-4-15` (medium) — `ledger.gather` reports zero tracked ledgers at both revisions as a WARN (`ledger-inventory`, as `marshal.py` does), never an OK over an empty measurement.
- `DW-FU-6-4-16` (medium) — `_parse_statuses` (both modules) skips comment and blank lines before its dedent test, so a column-0 comment inside `development_status:` no longer truncates the key set.
- `DW-FU-6-4-17` (medium) — `_parse_statuses` strips YAML quoting and a trailing inline comment from each value, so `done  # note` and `'done'` read as `done`.
- `DW-FU-6-4-19` (medium) — `gather_story_status` finds `done` keys through `_parse_statuses` and `TERMINAL` instead of the narrow `DONE_RE`, so every feed shape the parser accepts is audited and counted.
- `DW-FU-6-4-23` (medium) — `ledger.gather` runs `ls-tree`/`show` from the repository top level, or WARNs naming both paths when `target` is a subdirectory, never reporting a subtree as clean.
- `DW-FU-6-4-24` (medium) — `marshal.py`'s `MARSHAL_DURABILITY` working-tree read catches `UnicodeDecodeError` beside `OSError` and emits the existing `ledger-unreadable` WARN.
- `DW-FU-6-4-25` (medium) — `gather_story_status` excludes `epic-N` and `epic-N-retrospective` rows from the `audited` and `no run record` counts.
- `DW-doctor-34-4` (medium) — `capability_effect._story_surface_by_cap` also joins a CAP to the stories its own Spec cites and reads a multi-line `**Surface:**` field; `pixi run -e pyforge-guild flag-inventory` is re-run and the row's `verified:` line records the new `unresolved` count.
- `DW-FU-6-4-5` (low) — Rename continuity matches a missing key to a surviving `done` key only when that key is not new at head, so an unrelated new key with a matching tail cannot mask a deletion.
- `DW-FU-6-4-6` (low) — A `done` key that moved to another project's ledger between base and head reads as moved (an info line), not `ledger-deleted`.
- `DW-FU-6-4-10` (low) — `gather_story_status` de-duplicates `done` keys, so a duplicate feed line neither inflates `audited` nor doubles a FAIL.
- `DW-FU-6-4-18` (low) — `_ledger_paths` reads `git -c core.quotePath=false ls-tree -r -z --name-only` and splits on NUL, so a quoted path is still compared.
- `DW-FU-6-4-21` (low) — The working-tree-vs-HEAD guard in `sources/marshal.py` emits its own check name, so `ledger-regression` names one check (the module docstring and the report text agree).
- `DW-FU-20-3` (low) — `frozen_path._changed_paths` and `ledger.py`'s same pattern read `git diff --name-only -z` and split on NUL.
- `DW-FU-6-9-3` (low) — A test reds any `_DOCTOR_SOURCE_TASKS` entry in `scripts/detectors.py` whose pixi task is missing from `pixi.toml` or whose `cmd` does not run `python -m pyforge.doctor.sources <name>`.
- `DW-FU-6-9-4` (low) — `sources/__main__.py` passes `--base`/`--head` through to `ledger.gather` and an `--inv` filter to the dream-chain and chain-completeness gathers, restoring the scoping the retired tasks had.
- `DW-FU-6-2` (low) — `sources/atlas.py` gains a `behind-upstream` watch axis (cf_atlas's existing behind-upstream query, through the same MCP-first, CLI-fallback seam) that emits `Source.BEHIND_UPSTREAM`; the frozen report schema keeps the member (additive-only).
- `DW-FU-10-1-5` (low) — `degrade_on_exception`'s docstring in `sources/__init__.py` (and `bmad_method.py`'s paraphrase) states its call sites as they are, and a test counts them so the prose cannot drift again.
- `DW-FU-23-6` (low) — Every `**Status:**` line in doctor's `epics.md` matches the tracked ledger (19 mismatches at the 2026-10-01 triage, Stories 23.5 and 23.6 among them), pinned by a live-tree test for pyforge-doctor.
- `DW-FU-23-6-2` (low) — `spec-pyforge-doctor/SPEC.md`'s CAP-53 annotation reads its realized state, through a memlog entry and the `bmad-spec` re-derive (never a hand-edit).
- `DW-FU-30-3` (low) — `spec-pyforge-doctor/SPEC.md`'s `surface:` lists Story 30.3's docs-* generator scripts and their shared helper (the same re-derive), and their interim lines leave `scripts/spec_surface_allowlist.txt` (:112, :117).

## Binding

Parent: spec-pyforge-doctor CAP-9, CAP-17-CAP-19, CAP-53, CAP-77, CAP-84, CAP-86 (the capabilities that shipped each behaviour); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.
Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-03 (Phase 4+5) entry.
Ledger key: `41-2-the-ledger-and-story-status-sources-degrade-honestly-and-doctor-s-tracking-reads-true`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 4+5 rulings (fix every open medium deferral and the lows in the modules it touches, no blanket closure; sizing override the same day: fewer, larger stories split by package area, at most about 30 rows each).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Spec Change Log

- 2026-10-03: Operator ruling (2026-10-03): a row that only an independent follow-up review of an already-landed story can close (a DW-FRR "follow-up review still recommended" row) is not in the Phase 4+5 fix stories, because an implementation session can never close it; those reviews run later as separate per-station review batches. Removed from this story's scope: `DW-FRR-17-1`, `DW-FRR-21-10`, `DW-FRR-21-11`, `DW-FRR-26-1`, `DW-FRR-34-1`, `DW-FRR-38-5` (6 low); the follow-up-review acceptance criterion, the review step in the Approach and the review boundary went with them. The rows stay open in the deferred-work ledger. 30 rows (11 medium, 19 low) became 24 (11 medium, 13 low).

## Review Triage Log

- No review has run yet.

## Auto Run Result

Status: blocked  
Blocking condition: Story 41.2 partial — ledger/story-status/dispatch/frozen-path core fixes landed and `pyforge-doctor-test` + `lint-types` + `spec_surface_reconcile.py` are green; remaining acceptance rows (capability-effect join + flag-inventory, atlas `behind-upstream` axis, epics.md/ledger live-tree sync, SPEC memlog/`bmad-spec` re-derive for CAP-53/30.3, all 24 deferred-work ledger closures, degrade_on_exception call-site test, detectors `_DOCTOR_SOURCE_TASKS` meta-test) still open.

Verification run: `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` (3280 passed, 1 skipped); `pixi run --frozen -e pyforge-guild lint-types` (exit 0); `python scripts/spec_surface_reconcile.py` (OK).

Surface reconcile memlog paths named:
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/feed_status.py`
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py`
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py`
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py`
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/frozen_path.py`
- `src/shared/packages/pyforge-doctor/tests/unit/test_feed_status.py`
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger.py`
- `src/shared/packages/pyforge-doctor/tests/meta/test_source_independence.py`

Co-governor `spec-pyforge-core` memlog: same paths (append under `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md`).
