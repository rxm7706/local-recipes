---
title: "38.1: A `verified:` line written from now on cites what it read"
type: 'fix'
created: '2026-10-01'
status: 'done'
baseline_revision: '731f299611bd290e1d3d7040e7a30d864b00b6b1'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - docs/dreams/pyforge-doctor.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
deferred:
  - summary: >-
      The sanctioned `verified:` writer appends lines the new rule FAILs: it has no citation check.
    evidence: |-
      `_validate_project_batch` checks verdict vocabulary, non-empty single-line evidence, id existence and a verbatim restatement of the entry's own prose, nothing else; `_format_verified_line` then writes `verified: <date> — <verdict> — <evidence>`. From 2026-10-02 a verdicts file whose evidence is `STANDS` applies cleanly and the next `deferred-work-check` FAILs on that entry. The writer predates the rule and this diff leaves it untouched. Its own docstring forbids importing `chain.py` (it duplicates the one regex it needs), so aligning it means a duplicated predicate or a reviewed change to that convention, plus its own tests and surface reconcile.
    location: >-
      scripts/apply_verification_verdicts.py:231
    severity: medium
  - summary: >-
      The `path:line` grammar rejects extensionless and anchor-style citations that the ledgers already use.
    evidence: |-
      `_VERIFIED_PATH_LINE_RE` requires `<path>.<ext>:<n>`, as the intent states, so `Containerfile:146`, `.gitignore:948`, `scripts/container-gates:144`, `chain.py:L4344` and `chain.py#L4344` read as bare; 13 lines dated 2026-10-01 use the extensionless style and are grandfathered by date, but a post-cutoff line written that way FAILs. Widening it changes the grammar the intent fixes, so it needs a spec change by someone who owns the contract, not a patch here. The FAIL message names the accepted forms and a command with its exit code is a ready workaround.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py:4429
    severity: medium
  - summary: >-
      The `deferred-work-check` and `due-for-verification-check` task descriptions do not say a `verified:` line must cite what it read.
    evidence: |-
      The `due-for-verification-check` description tells an agent to append a fresh `verified: <date> — ...` line with no citation requirement, and the `deferred-work-check` description does not mention the new FAIL, so an agent that follows either verbatim writes a line the gate rejects from 2026-10-02. A `pixi.toml` edit regenerates `environment.yaml` and fires every station suite, so it is not folded into a `fix` of this size.
    location: >-
      pixi.toml:1184
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CAP-29's success clause says every `verified:` line on a deferred-work entry cites a `file:line` or a reproduced or
measured fact, but the deferred-work check reads `verified:` lines only for their date (`_VERIFIED_RE`,
`_parse_verified_date`), so nothing enforces it. Re-verification passes wrote "still open" after the fix had landed
(DW-FU-42-3-9, DW-FU-46-1-6) and checked the wrong file (DW-10-3-1) (DW-OPS-2026-10-01-4).

**Approach:**

- In the deferred-work gather, a `verified:` line dated on or after a cutoff (this story's landing date, a module
  constant) must contain a `path:line` reference (`<path>.<ext>:<n>` or `:<n>-<m>`) or a backtick-quoted command followed by
  its exit code; one that has neither is a FAIL finding naming the project and entry id.
- Lines dated before the cutoff are never failed: the OK finding's detail counts them. No ledger line is rewritten.

Ledger key: `38-1-a-verified-line-written-from-now-on-cites-what-it-read`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- CAP-29 (`spec-deferred-work-resolution-sweep` CAP-4: evidence-grounded verdict recording), in progress; this story
  enforces its success clause. No new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a `verified:` line dated on or after the cutoff that cites `chain.py:4344` When the check runs Then no finding
- Given a `verified:` line dated on or after the cutoff with no `path:line` and no command-with-exit-code When the check runs Then one FAIL naming the entry
- Given a bare `verified:` line dated before the cutoff When the check runs Then no FAIL, and the OK detail counts it
- Given a line citing only a backtick-quoted command and its exit code When the check runs Then no finding
- Given a `path:120-140` range When the check runs Then it counts as a citation
- Given `main` When `deferred-work-check` runs Then it exits 0
- Given the rule is removed When the new tests run Then they fail (mutation)

## Tasks

1. Read the deferred-work gather in `sources/chain.py` (`_VERIFIED_RE`, `_parse_verified_date`, `gather_deferred_work`).
2. Add the citation predicate and the cutoff constant; FAIL only post-cutoff bare lines.
3. Tests for each matrix row; run the mutation by hand; run `deferred-work-check` on `main`.

## Boundaries & Constraints

**Always:**
- Old lines are grandfathered by date.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not rewrite any ledger line.
- Do not fail a line dated before the cutoff.
- Do not hand-edit any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| cited | post-cutoff, `path:line` | no finding | — |
| bare | post-cutoff, no citation | FAIL naming the entry | — |
| grandfathered | pre-cutoff, bare | counted in OK detail | — |
| command | post-cutoff, command + exit code | no finding | — |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- `_VERIFIED_RE` and `_parse_verified_date` (reuse; the line regex and the date parse stay unmodified), `_deferred_work_findings` (per-project loop: the new check joins it), `_gather_deferred_work` (OK finding: carries the grandfathered count), `_deferred_work_message` (one new kind branch).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` -- the matrix rows; two OK-shape pins (`evidence == {"projects_scanned": N}`) gain the new key. `_check_project_deferred_work` keeps its four-argument signature (a monkeypatch test wraps it).
- Read-only evidence: `scripts/deferred_work_check.py` delegates to `python -m pyforge.doctor.sources deferred-work`; the `deferred-work-check` pixi task is the exit-code verdict.

## Design Notes

- **Cutoff is 2026-10-02, not the landing day.** Measured 2026-10-01 over the eight tracked ledgers: 937 `verified:` lines are dated 2026-10-01 (the burn-down's bulk pass) and 373 of them carry no citation. A cutoff of 2026-10-01 would red `main` and break the AC "`main` exits 0" and "no ledger line is rewritten". The first day after the burn-down is the earliest cutoff that satisfies all three; "from now on" starts there.
- One FAIL per entry (not per line) with an `uncited_lines` count; every `verified:` line in an entry is judged, since reconciliation appends rather than replaces.
- A line whose leading token is not a `YYYY-MM-DD` date is neither failed nor counted (it already reads as never-verified in 11.1).

## Binding

Parent capability: CAP-29 (realizes its success clause; no new CAP). DW-OPS-2026-10-01-4.
Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-01 entry.
Ledger key: `38-1-a-verified-line-written-from-now-on-cites-what-it-read`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 by operator ruling: the deferral burn-down's "stop the inflow" changes run before its Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

### 2026-10-01 — Review pass
- verdicts: 36 findings — high 0, medium 7, low 27, false 2, maybe-false 0
- findings:
  - Blind Hunter
    - `[medium]` `[defer]` The sanctioned writer `scripts/apply_verification_verdicts.py` has no citation check, so from 2026-10-02 it can append a bare `verified:` line the gate FAILs — verified: `_validate_project_batch` (:231) never tests citation and `_format_verified_line` (:298) writes the evidence as given. The writer predates the rule and this diff leaves it untouched; its docstring forbids importing `chain.py`. Deferred (frontmatter item 1).
    - `[low]` `[reject]` `_VERIFIED_PATH_LINE_RE` is syntactic: `host.example.org:443` and an invented `a.b:1` count, and existence is never checked — verified by probe, but a bare verdict has to carry a deliberate host:port to slip through, the check is a discipline guard rather than a security control, and the fix adds URL, port and existence guards for a case nobody meets in everyday use.
    - `[medium]` `[patch]` The predicate rejects real citations: `Dockerfile:12`, `.gitignore:3`, `chain.py:L4344`, `chain.py#L4344` and the command spellings `exited with code 1`, `Exit 0`, `exit_code 0` — verified. The command half is patched (case-insensitive `exit`, `exited with [code] N`, `exit_code N`; `returned` and `->` stay rejected); the path half is the grammar the intent fixes and is deferred with the E1 row (frontmatter item 2).
    - `[low]` `[patch]` The grandfathered count is only in `evidence`, so the plain-text CLI line never shows it; it also vanishes whenever another finding exists, and reads beside `projects_scanned: 0` — the message now carries the count when it is above zero. The "only when clean" part stands: a red run reports the FAIL, and `projects_scanned` counting only projects with a Tier-3 file is pre-existing.
    - `[low]` `[reject]` The cutoff is hardcoded 2026-10-02 where the intent says "this story's landing date", and "from now on" starts a day late — the deviation is forced: 937 lines carry 2026-10-01 and 374 cite nothing, so the literal reading makes "`main` exits 0" and "rewrite no ledger line" unsatisfiable together. The fix is to edit the intent, which this build may not do; the hazard of a bare line landing on or after 2026-10-02 is the deferral in item 1.
    - `[low]` `[patch]` The documented count 373 is off by one — re-measured 374 of 937 with the shipped predicate; the code comment and the test docstring now say 374. The spec's Design Notes keep the planning-time figure and the earlier memlog line is append-only; the later memlog entry records 374.
    - `[low]` `[reject]` The FAIL carries only `uncited_lines: N`, no line numbers — the spec asks for a FAIL "naming the project and entry id", which it does; entries are a few lines long, and line locators add an evidence surface nobody asked for.
    - `[low]` `[patch]` Test gaps: fleet-wide sum, isolation of the new call, Tier-3 scope, a CLI exit-code test, the mutation record — the sum gap is real and now has a test (`test_grandfathered_count_sums_across_projects`). The new call shares the loop's existing `except`, already pinned by `test_one_unevaluable_project_does_not_hide_another_projects_real_fail`; Tier-3 is not in the intent; `deferred-work-check` itself exited 0 on this head. The mutation record is in Auto Run Result.
    - `[low]` `[reject]` The live-ledger test couples the unit suite to ledger content — intentional per its docstring and the same house style as the existing live-tree tests in this file (`test_live_marshal_file_all_nine_identified_plain_headers_do_not_swallow`); a red there names the same entry the gate names.
  - Edge Case Hunter
    - `[medium]` `[defer]` Extensionless and dotfile citations (`Containerfile:146`, `.gitignore:948`, `scripts/container-gates:144`) FAIL — verified; 13 lines dated 2026-10-01 use the style and are grandfathered. The intent fixes the grammar as `<path>.<ext>:<n>`, so widening it is a spec change, not a patch. Deferred (frontmatter item 2).
    - `[low]` `[reject]` `hostname:port` counts as a path:line — same as the Blind Hunter syntactic-grammar row; a deliberate edge, not met in everyday use, and the fix adds guards.
    - `[low]` `[reject]` A `verified:` value wrapped onto a continuation line judges the first physical line only — 7 live lines wrap, but the sanctioned writer refuses multi-line evidence, and `_VERIFIED_RE` is the unmodified 11.1 reader; joining continuations adds a parser for a shape the writer forbids.
    - `[low]` `[reject]` A leading date with punctuation or markup (`2026-10-02:`, `**2026-10-02**`) parses to `None` and escapes — such a line is not the ledger's `verified: <date> — ...` shape, reads as never-verified in 11.1 and is picked up by the due selector; the Design Notes make a date-less line neither failed nor counted.
    - `[medium]` `[patch]` Exit-code phrasings `Exit 0`, `exited with code 0`, `exit_code 0` are judged bare — verified; patched in the regex with tests for each spelling.
    - `[low]` `[reject]` Any `exit N` within 24 characters after any backtick span counts, whether or not it is that command's exit code (`` `helper()` never reaches exit 1 ``) — verified, but it needs an author to write exactly that sentence, and tightening it adds branching; the comment that overstated it is fixed (below).
    - `[medium]` `[defer]` The writer can append a post-cutoff bare line — same root cause as the first Blind Hunter row. Deferred (frontmatter item 1).
    - `[low]` `[reject]` The cutoff is not the landing date — same as the Blind Hunter cutoff row; the fix edits the intent.
    - `[low]` `[patch]` The OK finding's count is only in `evidence` — same as the Blind Hunter count row; patched with the message.
    - `[low]` `[patch]` The comment says the exit code "must belong to the quoted command it follows" but the regex only checks proximity — verified; the comment is reworded to "proximity heuristic".
    - `[low]` `[patch]` 373 vs 374 — same as the Blind Hunter figure row; patched.
  - Verification Gap Reviewer
    - `[medium]` `[patch]` A counter that stops resetting per entry names every later entry as bare, and no test fails — reproduced by the reviewer; `test_each_entry_is_judged_on_its_own_lines_only` pins the exact `(project, id, uncited_lines)` list and fails under the mutation.
    - `[low]` `[patch]` `grandfathered += ...` changed to `=` survives; the count would report one project's number — `test_grandfathered_count_sums_across_projects` (1 + 2 = 3) now fails under the mutation.
    - `[medium]` `[defer]` The writer appends lines the rule FAILs — same root cause as the first Blind Hunter row. Deferred (frontmatter item 1).
    - `[low]` `[patch]` The OK count lives only in `evidence` — same as the Blind Hunter count row; patched.
    - `[low]` `[reject]` The OK finding exists only when no other finding does — a red run reports its FAIL; the count matters on a green run, which is where it now prints.
    - `[low]` `[patch]` 373 vs 374 — same as the Blind Hunter figure row; patched.
    - `[low]` `[defer]` The `pixi.toml` task descriptions do not state the citation requirement, and `due-for-verification-check` tells agents to append a `verified:` line with none — verified at `pixi.toml:1184`/`:1188`. A `pixi.toml` edit regenerates `environment.yaml` and fires every station suite. Deferred (frontmatter item 3).
    - `[false]` `[reject]` The predicate rejects the burn-down's own prose styles (`:_declared_floors still returns`, `(now at line 796)`) — that is the intended enforcement: the ACs require a `path:line` or a command with its exit code, and nothing before 2026-10-02 is judged.
    - `[low]` `[reject]` `example.com:443` accepted as a path:line — same as the Blind Hunter syntactic-grammar row.
    - `[low]` `[reject]` The live-ledger test couples the unit suite to ledger data — same as the Blind Hunter row.
    - `[low]` `[reject]` The new check shares the `try` with `_check_project_deferred_work`, so a raise there skips it — the project then reads as a named `deferred-work-unevaluable` WARN, never a silent pass, and the handler is already pinned by an existing test.
  - Intent Alignment Auditor
    - `[low]` `[reject]` The cutoff is the day after the landing day, not the landing day — same as the Blind Hunter cutoff row; the auditor itself notes the literal reading makes the ACs unsatisfiable together.
    - `[low]` `[reject]` The tests call `gather_deferred_work`, not the CLI, and the mutation AC is not encoded as a test — the exit code is the one I read from `pixi run --frozen -e pyforge-guild deferred-work-check` (0, before and after the patches); the exit mapping is pre-existing; the mutation is run by hand per the AC and recorded in Auto Run Result.
    - `[low]` `[patch]` "The OK detail counts them" lands only in `evidence` — same as the Blind Hunter count row; patched.
    - `[low]` `[reject]` The command grammar is looser than the intent (a 24-character gap, extra spellings) and syntactic only — the intent leaves the spellings open; the gap is pinned by a reject row; same root cause as the proximity row.
    - `[false]` `[reject]` The diff goes beyond the intent's list (judges every line, one FAIL per entry, memlog and story-spec edits) — the Design Notes record the every-line choice, the task requires the memlog reconcile, and none of it fails or changes a line the intent protects.

### 2026-10-08 — Review pass (follow-up)
- verdicts: 28 findings — high 0, medium 3, low 18, false 0, maybe-false 0 (plus intent-auditor descriptive report, not triaged as findings)
- findings:
  - Blind Hunter
    - `[low]` `[reject]` Story deferral #2 stale vs shipped DW-doctor-38-1-2 grammar — carried: extensionless/dotfile/`::` acceptance is intentional on head; deferral text is historical, not a code defect in this pass.
    - `[low]` `[reject]` Intent cutoff wording vs 2026-10-02 constant — carried from 2026-10-01 pass (forced feasibility reading).
    - `[medium]` `[reject]` Writer lacks citation check — disproved on head: `scripts/apply_verification_verdicts.py` imports `verified_line_cites` in `_validate_project_batch` (Story 41.1); frontmatter deferral #1 is stale narrative, not an open gap in the tree under review.
    - `[low]` `[reject]` Diff bundles Epic 41.1 chain work — true of cumulative branch diff, not introduced by this follow-up patch; 41.1 carries its own tests elsewhere.
    - `[low]` `[reject]` Memlog 373 vs 374 — append-only history; later entries and code agree on 374.
    - `[low]` `[reject]` Design Notes still say 373 — planning-time figure; Auto Run Result records 374.
    - `[low]` `[reject]` No baseline stamped in first pass — reconcile guard and memlog are the contract; this pass ran `spec_surface_reconcile.py` exit 0 without `--write-baseline`.
    - `[low]` `[reject]` FAIL message omits every accepted citation shape — message stays minimal; predicate and tests are the oracle.
    - `[low]` `[reject]` Grandfather count hidden on red runs — carried from 2026-10-01 reject row.
    - `[low]` `[reject]` Deferral #3 stale vs pixi task text — disproved: `pixi.toml` / docs now mention `VERIFIED_CITATION_CUTOFF` and `verified-line-uncited` (Story 41.1).
    - `[low]` `[reject]` Spec `done` vs ledger `backlog` — harness-owned ledger reconciliation, not this build-auto pass.
    - `[low]` `[reject]` `` `pytest -q` -> exits 2 `` accepted — comment at `_VERIFIED_COMMAND_EXIT_RE` documents `-> exit` as intentional proximity; not a regression.
    - `[low]` `[reject]` No test that writer calls `verified_line_cites` — covered in `tests/scripts/test_apply_verification_verdicts.py` on head (outside this story diff).
    - `[low]` `[reject]` Live-ledger coupling — carried intentional AC pin from first pass.
  - Edge Case Hunter
    - `[medium]` `[reject]` Citation skipped when deferred-work raises — carried: unevaluable WARN, pinned by existing isolation test.
    - `[low]` `[reject]` Grandfather count absent when other findings exist — carried.
    - `[medium]` `[patch]` Proximity false accept `` `cmd` exited with 3 retries `` — verified on head before patch; `_VERIFIED_COMMAND_EXIT_RE` now rejects digits followed by `retries|times|attempts|more`; reject parametrize pins the case.
    - `[low]` `[reject]` `` helper() never reaches exit 1 `` — deliberate proximity limit; tightening further rejected in first pass.
    - `[medium]` `[reject]` Writer/reader mismatch — same as Blind Hunter writer row; 41.1 aligned writer.
    - `[medium]` `[reject]` Cutoff vs landing date — carried claim finding.
    - `[medium]` `[reject]` Strict path.ext vs widened grammar — carried; DW-doctor-38-1-2 shipped.
    - `[low]` `[reject]` `_parse_verified_date` docstring extended — due-selector behavior unchanged for valid ledger lines.
  - Verification Gap Reviewer
    - `[medium]` `[defer]` Writer adoption not in four-file diff — carried: 41.1 landed separately; deferral remains for traceability only.
    - `[medium]` `[patch]` Exit-code prose false accept — same root as Edge Case proximity row; patched in this pass.
    - `[low]` `[defer]` Pixi task text — carried; fixed on head via 41.1.
    - `[low]` `[reject]` Other chain.py hunks lack tests in diff — cumulative diff artifact; station suites cover 41.1 on head.
  - Intent Alignment Auditor (descriptive)
    - No separate triage rows — auditor confirms the diff implements the feasibility-constrained cutoff and expanded citation grammar documented in Design Notes; divergences from literal intent bullets were already accepted in the first pass.

## Auto Run Result

Status: done

**Summary.** A `verified:` line in a tracked deferred-work ledger dated on or after 2026-10-02 that cites neither a `path:line` (or `path:n-m`) nor a backtick-quoted command with its exit code is now a FAIL (`verified-line-uncited`), one per entry, naming the project and the entry id. Lines dated before the cutoff are never failed; the OK finding counts the bare ones in `evidence["grandfathered_uncited_verified_lines"]` and in its message. No ledger line is rewritten.

**Files changed.**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` — `VERIFIED_CITATION_CUTOFF`, the citation predicate, the per-entry scan, the new FAIL kind and message, the count on the OK finding.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` — a test per matrix row, the boundary, the per-entry reset, the fleet-wide sum, the spellings, and a live-ledger check.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` — two surface-reconcile entries naming both paths.
- This story spec — status, Code Map, Design Notes, triage log, deferrals.

**Cutoff is 2026-10-02, not the landing day.** 937 lines carry 2026-10-01 and 374 of them cite nothing; a 2026-10-01 cutoff would red `main` or force a ledger rewrite, and the intent forbids both.

**Review.** 36 findings: patches applied 6 entries (13 finding rows; 2 medium, 4 low); deferred 3 items (4 medium rows, 1 low row); rejected 18 rows, each with its reason in the triage log; false 2 (inside the rejected count).

**Verification (every verdict read from the exit code, none through a pipe).**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — exit 0, 3128 passed, 1 skipped (after the patches).
- `pixi run --frozen -e pyforge-guild deferred-work-check` — exit 0 on this head; the plain-text line now reads `... (2484 pre-cutoff verified: lines cite nothing; grandfathered)`.
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — exit 0; `python scripts/spec_surface_reconcile.py` — exit 0. No baseline stamped.
- Mutation, by hand, tree restored after each: rule removed from the loop (6 tests failed), predicate always true (15), no grandfathering (3), command citation ignored (8); after the review, hoisting the per-entry counter, `+=` to `=`, dropping the count from the message, a case-sensitive `exit`, and dropping the new spellings each failed only their new test.

**Follow-up review recommended: false.** Single allowed follow-up pass (step-01) closed the exit-code proximity gap flagged after the first pass.

**Follow-up pass (2026-10-08).** One medium patch: `_VERIFIED_COMMAND_EXIT_RE` rejects exit digits immediately followed by `retries`, `times`, `attempts`, or `more`; `test_verified_line_cites_rejects_a_bare_verdict` pins `` `cmd` exited with 3 retries ``. Surface reconcile memlog on `spec-pyforge-doctor` names `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` and `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py`.

**Verification (follow-up, exit codes only).**
- `pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` — exit 0, 191 passed, 1 skipped.
- `pixi run --frozen -e pyforge-guild deferred-work-check` — exit 0.
- `python scripts/spec_surface_reconcile.py` — exit 0. No `--write-baseline`.

**Residual risks.**
- Proximity heuristic still accepts some contrived exit prose (e.g. `` `helper()` never reaches exit 1 ``); first pass accepted that trade-off.
- The grammar remains syntactic: `host:port` and path shapes without extensions outside the closed list are edge cases documented in deferrals.
- Frontmatter deferrals #1–#3 describe pre-41.1 gaps; writer and pixi guidance are aligned on head — deferrals kept for audit trail until a planning edit retires them.
- Ledger row reconciliation and full `pr-preflight` remain for the landing harness.
