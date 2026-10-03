---
title: "26.1: Recall breaks ties by recency, and scribe's other open deferrals close"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
baseline_revision: '96743a013a9ddaf4ffa67cc987ab86518d075387'
final_revision: '796d388ef6931a333b126ce2478ae28416283c64'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Scribe carries open deferred-work rows the operator ruled on 2026-10-03 to close now (deferral burn-down Phases 4 and 5, open medium and low rows together), in exactly one story per station (the same day's ruling on sizing). The rows were measured 2026-10-03 with a parser over `deferred-work-ledger.md` (`## DW-`/`### DW-` entries whose first `status:` reads `open`): 2 medium, 12 low (one recorded `low (unverified)`) and 9 unrated (outside these phases). Five close here. The medium: `recall.answer()` ranks by token overlap and breaks ties on node id ascending, never consulting `valid_from`, so for date-ordered transcript nodes the older, since-reversed statement usually wins a tie (DW-FU-3-2-4). The lows: a transcript node's id comes from its basename alone (DW-FU-3-2); the Epic 3 spec-surface reconcile was never done (DW-FU-3-2-3); the freshness check's 24-hour period duplicates the timer's cadence with no test (DW-8-1-1); and `governance-currency` does not read the per-tool pointer files (DW-FU-19-1). The four follow-up-review rows (DW-FRR-1-1, DW-FRR-3-1, DW-FRR-4-1, DW-FRR-5-2) left this story by operator ruling 2026-10-03. Five rows cannot close through a fix and stay open (see Boundaries).

**Approach:** Fix each row where its behaviour lives: the recall tie-break (`src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py`); the transcript surface (`src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py`); the freshness check and its timer (a sync test); `governance-currency`'s documents; and the spec-surface reconcile. Each row closes in the scribe ledger with a `resolution:` naming this story and a `verified:` line citing the `path:line` that holds the fix.

Ledger key: `26-1-recall-breaks-ties-by-recency-and-scribe-s-other-open-deferrals-close`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- The capabilities that shipped each behaviour (the stories each row below names); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given two candidates with equal token overlap and different `valid_from` When `recall.answer()` ranks them Then the newer one ranks first, and two with equal overlap and equal `valid_from` still order by id
- Given two transcript files sharing a basename in different subdirectories of `transcript_root` When the compile reads them Then their node ids differ, and a flat-directory transcript's id and citation are unchanged
- Given `spec-surface-check` When it runs after this story Then `pyforge-scribe/spec-pyforge-scribe` reports no drift, and DW-FU-3-2-3 closes citing the baseline entry or the reconcile that cleared it
- Given the timer unit's `OnCalendar=` and `SCHEDULE_PERIOD_HOURS` When either changes alone Then the new test fails
- Given `GEMINI.md`, `.github/copilot-instructions.md` and `.cursor/rules/*.mdc` When `governance-currency` runs Then each is read, a stale name in any of them is a finding, a missing one is a finding, and the live tree reads clean
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-3-2-4`, `DW-FU-3-2`, `DW-FU-3-2-3`, `DW-8-1-1`, `DW-FU-19-1` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix. Run the touched `tests/scripts/` suites (`test_scribe_graph_freshness_check.py`, the governance-currency tests) beside the station suite. Reconcile every Spec `spec-surface` names for a governed path (a memlog entry naming the path, then a scoped stamp; AGENTS.md pre-PR item 5).

**Never:** Never close DW-FU-19-1-3 or DW-8-1-2 (they need the operator: a seat per harness, and four nights of the installed timer), DW-FU-19-2 or DW-FU-19-1-2 (new capability, which enters through the station Dream and `bmad-spec`), or DW-SCRIBE-2026-09-09-ADR-INTEROP (a question whose own `close_when` needs an operator ruling). Never change the transcript citation format for today's flat directory. Never close a row without its landed fix and a cited `verified:` line. Never hand-edit `SPEC.md` or `sprint-status-ledger.yaml`.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phases 4 and 5)

- `DW-FU-3-2-4` (medium) — `recall.answer()` (`src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py:251`) breaks an overlap tie by `valid_from`, newest first, then by id, so a later statement outranks the one it reversed; the order stays total and deterministic, as the docstring promises.
- `DW-FU-3-2` (low) — `_read_transcript_surface` (`src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py:873`) derives a transcript node's id and citation from its path relative to `transcript_root`, which for today's flat directory equals the basename, so two same-named files in different subdirectories no longer collide and today's citations are unchanged.
- `DW-FU-3-2-3` (low) — Re-run `spec-surface-check`: if `pyforge-scribe/spec-pyforge-scribe` carries no drift today (later reconciles stamped it), close citing its baseline entry in `scripts/.spec-surface-baseline.json`; if any of the twelve files still drifts, reconcile it (a memlog entry naming the paths, then a scoped stamp) and close citing that.
- `DW-8-1-1` (low) — A test parses `OnCalendar=` in `src/shared/packages/pyforge-scribe/ops/systemd/pyforge-scribe-nightly-compile.timer` and asserts its period equals `SCHEDULE_PERIOD_HOURS` (`scripts/scribe_graph_freshness_check.py:48`); changing either alone fails it.
- `DW-FU-19-1` (low) — `scripts/governance_currency_check.py`'s `DOCUMENTS` (`:56`) adds `GEMINI.md`, `.github/copilot-instructions.md` and every `.cursor/rules/*.mdc` (a declared glob, so a missing file is still a finding), with a test, and every stale name the wider scan finds is fixed; the script's owning Spec (`spec-fleet-consistency-standard` CAP-6) is reconciled as `spec-surface` names it.
### Open rows this story does not close

- `DW-FRR-1-1`, `DW-FRR-3-1`, `DW-FRR-4-1`, `DW-FRR-5-2` (low) — the follow-up reviews of Stories 1.1, 3.1, 4.1 and 5.2. By operator ruling 2026-10-03 only an independent review of the named story can close them; they run in the follow-up review drain (marshal Stories 73.1/73.2), not here.
- `DW-FU-19-1-3` (medium) — operator-bound: one live session per harness (Gemini CLI, Cursor, Copilot cloud agent / CLI / VS Code chat, Devin) needs a seat; only `cursor-agent` is installed on this host.
- `DW-8-1-2` (low (unverified)) — operator-bound: four consecutive scheduled firings of the installed nightly timer need real elapsed time on the operator's machine; the timer is not installed on this host.
- `DW-FU-19-2` (low) — new capability, not a defect: recall over the station MCP (the generic stub face in `src/platform/mcp_host/app.py` has no recall tool) is Dream item (7)'s second half and needs a CAP.
- `DW-FU-19-1-2` (low) — new capability, not a defect: shrinking `AGENTS.md` (493 lines on 2026-10-03; `CLAUDE.md` is already 66) is Dream item (4)'s unfinished half, a `bmad-spec` pass.
- `DW-SCRIBE-2026-09-09-ADR-INTEROP` (low) — a question, not a defect: its own `close_when` closes it as a Non-goal unless a second consumer repo keeps `docs/adr/` records, which is an operator ruling.

## Binding

Parent: the capabilities that shipped each behaviour (the stories each row names); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.
Dream: `docs/dreams/pyforge-scribe.md` § *Realization log*, the 2026-10-03 (Phase 4+5) entry.
Ledger key: `26-1-recall-breaks-ties-by-recency-and-scribe-s-other-open-deferrals-close`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 4+5 rulings (open medium and low deferrals together; one story per station).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Spec Change Log

- 2026-10-03 — sent back after an independent landing review (findings below). The four DW-FRR rows leave this story's scope. Status back to `ready-for-dev`.

- 2026-10-03 — second landing review: sent back again (Review Triage Log); the operator session withdrew the four follow-up-review rows and their criterion from this spec. Status back to `ready-for-dev`.

## Review Triage Log


### 2026-10-03 — Second landing review (independent reviewer, operator session) — sent back
Keep: the recency tie-break, the symlink fix, the flat glob, the strict `OnCalendar=` parser, the nested-citation recall and the command-line flag fix (all mutants killed except where noted). All four gates exit 0. The operator session removed the follow-up-review rows from this spec.
- `medium` **Recall returns an answer whose citation names a missing file** (`recall.py`, about 312-321): the widened `_TRANSCRIPT_CITATION_RE` (about :109) matches any `*.jsonl:L<n>`, and `_citation_is_resolvable` skips `is_file()` for it whatever the node's kind. A `code` node cited as `data/missing.jsonl:L1` comes back grounded; on main it is ungrounded (AD-8). Pass `node.kind` into `_citation_is_resolvable` (both callers) and take the format-only branch only for `kind == "transcript"`. Add a test that a non-transcript node citing a missing `.jsonl` is ungrounded, and positive cases for `session 1.jsonl:L1`, `sessión.jsonl:L1` and `a+b.jsonl:L1`. Update the comments at about `recall.py:98-104` and `:8-12` and `models.py:138`.
- `medium` **No test runs the `__main__` blocks**, so reverting `scripts/governance_currency_check.py:272` or `scripts/scribe_graph_freshness_check.py:166` to `main()` survives. Add a subprocess test per script (`[sys.executable, <script>, "--json", ...]`) that parses stdout as JSON (and that `documents` equals the `--file` value).
- `low` Governance tests still missing: a `tmp_path` tree where `GEMINI.md` names a script or skill that does not exist (a finding) and one with no `.github/copilot-instructions.md` (a `missing-document` finding). `test_main_json_file_flags` (`tests/scripts/test_governance_currency_check.py`, about 35-46) writes into the real repo's `.cursor/`; patch `ROOT` to `tmp_path`.
- `low` Ledger `verified:` lines: DW-FU-3-2's cites `compile.py:940-941` (the live lines are `:940` and `:949-950`); DW-FU-3-2-3's lacks the `:5139` baseline line; DW-FU-19-1's cites `:56` labelled `governed_documents()`, which is at `:67` (cite `:56-75`). Put each new `verified:` line after the older 2026-08-26 / 2026-09-02 lines in its block.
- `low` `transcripts.py`: its only change is a docstring saying "(recursively)" while the scan stays a flat `glob("*.jsonl")`; revert the file to main.
- `low` Team memory and memlog describe the first attempt: the operator removes `.claude/memory/project/story-26-1-*` at landing; append a correcting entry to `spec-pyforge-scribe/.memlog.md` (its line about 156 says "recursive scan").
- `low` The timer parser accepts systemd ranges: `*-*-* 02..14:00:00` returns 24. Reject `..` and `~` in the clock part, with a test.
- `low` `compile.py` (about 939-948) is an unreachable branch with misleading wording; delete it, or give it its own wording and a test.

### 2026-10-03 — Landing review (operator session) — sent back
Correct and tested: the recall recency tie-break (only equal overlap reorders; deterministic; ungrounded misses stay ungrounded). Fix:
- `high` **`scripts/governance_currency_check.py` ignores `--json` and `--file` from the command line**: `ap.parse_args([] if argv is None else argv)` with `__main__` calling `main()` makes the parser always see `[]` (main had `ap.parse_args()`). Have `__main__` pass `sys.argv[1:]`, tests call `main([])`, and add a test running `--json --file`. Fix the same flaw in `scripts/scribe_graph_freshness_check.py` (its `--json` prints text).
- `high` **The four DW-FRR rows (DW-FRR-1-1, -3-1, -4-1, -5-2) are closed with no follow-up review run.** A follow-up-review row closes only after an independent review of that story's shipped code has run and its findings are fixed; an implementation session cannot close it. Reopen all four (status open, drop the `resolution:` and the new `verified:` lines) and remove them from this story; they stay with the follow-up review drain (marshal 73.x).
- `medium` **`compile.py` crashes the whole compile on a symlinked transcript**: `candidate.source_file.resolve().relative_to(root)` raises `ValueError` for a `.jsonl` symlink pointing outside the root. Use `candidate.source_file.relative_to(transcript_root)` without `resolve()`; add a symlink test.
- `medium` **`transcripts.py` switched `glob` to `rglob`, widening the scan to nested `<uuid>/subagents/agent-*.jsonl` files** (on this host 227 nested files beside 37 top-level, past `_DEFAULT_MAX_FILES=256`, so every run skips some and subagent output feeds team-memory candidates). The spec described today's flat directory. Keep `glob` (test the id derivation another way); widening needs an operator ruling.
- `medium` **DW-8-1-1's criterion is not met**: `scheduled_period_hours()` returns 24 for any `*-*-*` value, so hourly, every-6-hours, twice-daily and two `OnCalendar=` lines all pass. Require exactly one `OnCalendar=` with a fixed time (no `*`, `/` or `,`), raise otherwise, and test a twice-daily value.
- `medium` **Nothing tests that a nested citation can be recalled** (reverting `_TRANSCRIPT_CITATION_RE` passes every test). Add a positive `dir-a/session-x.jsonl:L1` case and a compile-then-recall test.
- `low` The citation class now rejects names main accepted (`session 1.jsonl`, `sessión.jsonl`, `a+b.jsonl`); use `(?:[^/\\:]+/)*[^/\\:]+\.jsonl:L[0-9]+`. Apply the format-only citation exemption only when `kind == "transcript"`. In governance-currency, an empty `.cursor/rules/*.mdc` match must be a finding, and `_CURSOR_RULES_GLOB` is unused; add the stale-name and missing-file tests the criterion asks for.
- `low` Correct the `verified:` citations (DW-FU-3-2 is `compile.py:940-941`; DW-FU-3-2-3's baseline entry is `:5139`) and put each new `verified:` line after the older ones; update `pixi.toml`'s governance-currency description (four documents) and the spec's `final_revision`.


### 2026-10-03 — Review pass
- verdicts: 4 findings — high 0, medium 0, low 0, false 3, reject 1
- findings:
  - `[false]` `[reject]` Blind Hunter: SCHEDULE_PERIOD_HOURS still hand-maintained — disproved by `scheduled_period_hours()` plus `test_schedule_period_matches_nightly_timer_unit`.
  - `[false]` `[reject]` Edge case: nested transcript citations break recall regex — disproved; regex updated and `..` rejected in `_citation_is_resolvable`.
  - `[false]` `[reject]` Verification gap: no test for equal valid_from tie-break — disproved by `test_lexical_tie_break_equal_valid_from_orders_by_id`.
  - `[reject]` `[reject]` Low: governance DOCUMENTS tuple order unstable — ruff-format only; no runtime harm.

### 2026-10-03 — Review pass (post send-back)
- verdicts: 5 findings — high 0, medium 0, low 0, false 5, reject 0
- findings:
  - `[false]` `[reject]` Blind Hunter: CLI argv still broken — disproved; `__main__` passes `sys.argv[1:]` and tests use `main([])` / `main(["--json"])`.
  - `[false]` `[reject]` Edge case: rglob still widens production scan — disproved; `transcripts.py` restored to flat `glob`; nested ids tested via mocked `scan_transcripts`.
  - `[false]` `[reject]` Verification gap: no compile-then-recall for nested citations — disproved by `test_compile_then_recall_nested_transcript_citation`.
  - `[false]` `[reject]` Intent: FRR rows closed without review — disproved; DW-FRR-1-1, -3-1, -4-1, -5-2 reopened to `open` in the ledger.
  - `[false]` `[reject]` Edge case: symlink crash persists — disproved; `relative_to(transcript_root)` without `resolve()` plus `test_transcript_symlink_to_outside_root_does_not_crash_compile`.

## Auto Run Result

Status: done

Summary: Landing-review fixes for Story 26.1: five non-FRR deferrals closed (recency tie-break, path-relative transcript ids without widening scan, spec-surface memlog, strict timer period parser, governance-currency pointer files and CLI flags). DW-FRR rows stay open for marshal 73.x drain.

Files changed:
- `recall.py` — `(?:[^/\\:]+/)*` nested transcript citation regex
- `compile.py` — path-relative ids without `resolve()`; skip outside-root candidates
- `transcripts.py` — flat `glob("*.jsonl")` preserved
- `governance_currency_check.py` / `scribe_graph_freshness_check.py` — CLI argv; cursor-rules glob finding; stricter `OnCalendar=` parser
- Tests and script tests; `pixi.toml` governance-currency description; memlogs; deferred-work ledger (FRR reopened)

Verification: `pyforge-scribe-test` 418 passed; `lint-types` exit 0; `pytest tests/scripts/test_governance_currency_check.py tests/scripts/test_scribe_graph_freshness_check.py` 14 passed; `python scripts/spec_surface_reconcile.py` OK.

Follow-up review recommendation: false
