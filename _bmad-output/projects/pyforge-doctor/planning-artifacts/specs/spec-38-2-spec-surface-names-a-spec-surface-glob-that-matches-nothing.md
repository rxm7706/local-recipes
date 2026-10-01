---
title: "38.2: `spec-surface` names a Spec surface glob that matches nothing"
type: 'feature'
created: '2026-10-01'
status: 'done'
baseline_revision: '5b6a82b4c7a038dbcef39d8592bb08d20719e8d1'
warnings: [oversized]
review_loop_iteration: 0
followup_review_recommended: false
flag-exempt: detector-or-gate   # a gated gate reports a silent green (spec-feature-flag-governance Q2)
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - docs/dreams/pyforge-doctor.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - scripts/spec_surface_allowlist.txt
deferred:
  - summary: >-
      `_tracked_files` reads `git ls-files` with git's default path quoting, so a tracked path with non-ASCII bytes arrives
      quoted and octal-escaped and no literal glob can match it.
    evidence: |-
      Reproduced 2026-10-01 in a tmp repo: `git ls-files` printed `"docs/caf\303\251.md"`, and a Spec surface listing
      `docs/café.md` got a `stale-surface` WARN although the file is tracked. The cause predates this story: the same quoted
      string reaches `ungoverned` and drift matching, so such a file is not governed by that glob today either. One tracked
      path in this tree has non-ASCII bytes (the Story 22.4 spec file) and none of the 25 live `stale-surface` rows names a
      non-ASCII path. Fixing it means reading the listing with `core.quotepath=off` or `-z`, which changes how existing
      coverage and drift findings read paths; the intent's Never list forbids changing those here.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py:1822
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-surface` (`sources/chain.py::_check_spec_surface`, in `detectors-ci`) reports an allowlist entry that matches no
tracked file (`stale-allowlist`) but not a Spec `surface:` glob that matches nothing, so a retired or misspelt glob stops
governing anything without a word: the asymmetry `spec-regenerable-factory`'s memlog and doctor Story 6.9 recorded. On
2026-10-01, 25 such globs sat in 7 Specs while the check reported ok (DW-OPS-2026-10-01-2).

**Approach:**

- For every Spec whose surface was read, each `surface:` glob that matches no tracked file is one `stale-surface` WARN
  naming the Spec and the glob, beside the existing `stale-allowlist` rows. A WARN never changes the exit code, so the 25
  known globs do not red the gate; fixing them is the owning Specs' work.
- A Spec whose surface could not be read is not judged (the existing unevaluable path holds).

Ledger key: `38-2-spec-surface-names-a-spec-surface-glob-that-matches-nothing`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / S-38.1.

### Living CAP citations

- CAP-88 (FR-21; extends `spec-regenerable-factory` CAP-2). `type: feature`, `flag-exempt: detector-or-gate`
  (`spec-feature-flag-governance` Q2).

## Acceptance Criteria

- Given a Spec with one matching and one dead glob When `spec-surface` runs Then exactly one `stale-surface` WARN names that Spec and glob
- Given a trailing-slash directory glob and a brace glob When the check runs Then each is judged by what it actually matches
- Given a Spec whose surface cannot be read When the check runs Then no `stale-surface` row is reported for it
- Given `main` When `pixi run -e pyforge-guild spec-surface-check` runs Then it lists the dead globs and exits 0
- Given the new rule is removed When the new tests run Then they fail (mutation)

## Tasks

1. Read `_check_spec_surface` and `_parse_surface` in `sources/chain.py`, and how `stale-allowlist` is built.
2. Count matches per surface glob for every readable Spec; add `stale-surface` WARN rows.
3. Tests for each matrix row; run `spec-surface-check` on `main` and record the count in the triage log.

## Boundaries & Constraints

**Always:**
- The finding is a WARN.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not change any Spec's `surface:` list here.
- Do not change the existing drift, coverage or `stale-allowlist` findings.
- Do not hand-edit any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| live glob | matches tracked files | no row | — |
| dead glob | matches nothing | `stale-surface` WARN | exit code unchanged |
| unreadable surface | surface parse failed | no `stale-surface` row | existing unevaluable WARN |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- `_collect_surfaces` (l.2096) fills `specs[name]` with `globs` and a parallel compiled `res`; a Spec whose SPEC.md fails to parse never enters `specs`, so it is never judged. `_check_spec_surface` (l.2191) returns `(findings, presumed)`; `gather_spec_surface` emits `presumed` as WARN rows and still emits the OK verdict when `findings` is empty. `_glob_to_re` (l.1663) is the one governing matcher: no brace expansion, a trailing `/` matches no file.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py` -- real tmp-git-repo fixtures (`_write_spec`, `_write_allowlist`, `_add_commit`); `test_stale_allowlist_entry_reports_fail` (l.169) is the sibling to mirror.
- `pixi.toml` l.1357 -- `spec-surface-check` runs `python -m pyforge.doctor.sources spec-surface`, so AC 4 exercises this code. `scripts/spec_surface_check.py` is the mutation-only baseline script: out of scope.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- add `_stale_surface_findings(specs, files)`: per readable Spec, each distinct glob whose compiled regex matches no tracked file is one `stale-surface` item naming Spec and glob; call it from `_check_spec_surface` and append to `presumed` -- non-gating WARN, the OK verdict and every existing finding stay unchanged.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py` -- one test per matrix row and AC row (live and dead glob; trailing-slash and brace globs; unreadable SPEC.md; OK verdict kept); confirm they fail with the call removed.

**Acceptance Criteria:**
- Given the `## Acceptance Criteria` in the contract above, when the station suite and `spec-surface-check` run, then each holds and `spec-surface-check` exits 0 (read from `$?`, never a pipe).

## Spec Change Log

## Design Notes

A glob is dead exactly when `_glob_to_re` rejects every tracked path: the same regex governance uses, so the WARN never disagrees with what a Spec actually governs. A trailing-slash or brace glob therefore reports dead (it governs nothing); judging it live by directory-existence or brace expansion would be a lie.

`presumed`, not `findings`: a WARN in `findings` makes `gather_spec_surface` drop the OK row, changing an existing finding.

## Binding

Parent capability: CAP-88 (FR-21). DW-OPS-2026-10-01-2.
Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-01 entry.
Ledger key: `38-2-spec-surface-names-a-spec-surface-glob-that-matches-nothing`.
Ledger status at mint: `backlog`.
Deps: S-38.1.
Minted 2026-10-01 by operator ruling: the deferral burn-down's "stop the inflow" changes run before its Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
- Implementation 2026-10-01: `pixi run -e pyforge-guild spec-surface-check` (run from this worktree, whose tracked tree equals
  `main` plus this change) lists 25 `stale-surface` WARN rows across 7 Specs (atlas, doctor, herald, marshal, pyforge-testing-charter,
  scribe, steward) beside the OK verdict and exits 0 (read from `$?`, no pipe) - the 25 globs in 7 Specs DW-OPS-2026-10-01-2 recorded.
  No Spec `surface:` list was edited. The existing `test_spec_governing_no_files_is_not_drift_blind` fixture glob is itself dead, so
  its exact check set now includes `stale-surface`; no other existing test moved. Removing the `presumed.extend(...)` call fails
  8 of the spec-surface tests (mutation confirmed).

### 2026-10-01 — Review pass
- verdicts: 20 findings — high 0, medium 0, low 13, false 7, maybe-false 0
- findings:
  - `[low]` `[reject]` Blind Hunter: the dead glob is only in the message, `evidence` carries just the Spec name — no consumer of `stale-surface` keys on `evidence` (the doctor package has no dedup, and the live JSON run gave 25 distinct rows); the message names Spec and glob as AC 1 asks, and every other path-only kind here (`drift-blind`, `spec-surface-unevaluable`) does the same; a new evidence key changes an externally consumed, frozen report shape, more than a direct correction.
  - `[low]` `[patch]` Blind Hunter: the message said "remove or fix it in the Spec's surface: list" (invites hand-editing SPEC.md, AGENTS.md § Policy) and did not explain the shapes the live run produced — patched: the one static detail string in `_stale_surface_findings` now says a trailing '/' and a '{a,b}' brace are not expanded (write `dir/**`, one glob per name) and that the owning Spec is re-derived with bmad-spec, never hand-edited; no new branch or key.
  - `[low]` `[reject]` Blind Hunter: nothing stops the inflow and nothing tracks the 25 — the intent fixes the finding at WARN ("The finding is a WARN") and hands the 25 to the owning Specs; a FAIL promotion or acknowledgement path is new surface the intent excludes; Task 3 asked for the count in this log, and the listing is reproducible with the command.
  - `[false]` `[reject]` Blind Hunter: `surface-drift-exclude` entries are not judged — a dead exclude names a path that is not a governed file, so it cannot hide drift (`chain.py:1902` skips only governed files that exist); a renamed file shows as loud `drift`, not silence; the intent covers `surface:` globs only.
  - `[low]` `[reject]` Blind Hunter: a Spec with an empty `surface:` yields no row — measured 2026-10-01: 149 of 171 Specs have no surface globs (the shape `test_spec_governing_no_files_is_not_drift_blind` pins), so a row each would be 149 WARNs; there is no glob to judge, which is the intent's unit.
  - `[low]` `[patch]` Blind Hunter: AC 4's "lists the dead globs" half had no durable assertion — patched: `test_dead_glob_keeps_the_ok_verdict_and_the_exit_code` takes `capsys` and asserts the CLI listing contains `stale-surface` and `retired/**`; the exit-code assertion stays.
  - `[false]` `[reject]` Blind Hunter: the unreadable-surface test covers only the non-UTF-8 branch — `_stale_surface_findings` iterates `specs`, which `_collect_surfaces` never fills for an unreadable SPEC.md or an unlistable directory (`chain.py:2137-2180`), so both branches are excluded by construction; `test_unreadable_spec_directory_names_what_went_dark` already pins the listing branch.
  - `[low]` `[reject]` Blind Hunter: Code Map line numbers went stale after the change — the fix edits this build's spec; cosmetic.
  - `[low]` `[reject]` Blind Hunter: `warnings: [oversized]` is unexplained — the fix edits this build's spec; the template defines the flag with no explanation field and the spec is about 6.6 kB, over the 1600-token line.
  - `[low]` `[defer]` Edge Case Hunter: a tracked non-ASCII path arrives quoted from `git ls-files`, so a glob naming it is reported dead — reproduced in a scratch repo (`"docs/caf\303\251.md"`); the cause is the existing `_tracked_files` (`chain.py:1822`), the same string governs `ungoverned` and drift matching today, one non-ASCII path is tracked and no live row names one; the fix changes existing coverage and drift reading, which the Never list forbids here — deferred in frontmatter.
  - `[low]` `[reject]` Edge Case Hunter: `evidence` shape, two dead globs in one Spec share `evidence` — same claim and same refutation as the first row.
  - `[false]` `[reject]` Edge Case Hunter: a glob naming a deliberately gitignored path (`.steward/budget.yaml`) warns every run and has no exemption — the glob matches no tracked file, which is exactly what the WARN states and what AC 1 specifies; the fix belongs in the owning Spec, and an exemption mechanism is new surface.
  - `[low]` `[defer]` Edge Case Hunter: the non-ASCII claim, reproduced with `docs/café.md` — same root cause and deferral as the earlier non-ASCII row.
  - `[low]` `[reject]` Verification Gap, other findings: `stale-surface` rows carry only the Spec name in `evidence` — same claim and same refutation as the first row.
  - `[low]` `[patch]` Intent Alignment: a trailing-slash or brace glob is judged dead by `_glob_to_re` although its directory is populated (10 trailing-slash rows and 1 brace row of the 25) — A1 is the literal reading of AC 2 ("judged by what it actually matches"); the confusion for owners is the message, patched with the row above.
  - `[false]` `[reject]` Intent Alignment: rows ride `presumed`, not `findings`, so they print first and not beside `stale-allowlist` — deliberate and commented (a row in `findings` drops the OK verdict); consumers filter `drift`/`drift-presumed` names; output order is irrelevant to AC 4.
  - `[false]` `[reject]` Intent Alignment: `test_spec_governing_no_files_is_not_drift_blind` had its exact check set widened — the fixture's one glob matches nothing by construction, so the specified WARN must appear; the test still pins no `drift-blind`; the Never list binds findings, not that literal.
  - `[false]` `[reject]` Intent Alignment: unlike `ungoverned`, an unknown surface does not suppress `stale-surface` — a glob's match depends only on the tracked files, never on another Spec's surface, so a dark sibling cannot make a dead glob live.
  - `[low]` `[patch]` Intent Alignment: AC 4's listing is covered by no test — same defect as the capsys row; fixed by the same patch. The "on `main`, 25 rows across 7 Specs" half is verified by the command (recorded in the implementation note above); a unit test pinning 25 would break as owners fix their globs.
  - `[false]` `[reject]` Intent Alignment: the `detectors-ci` aggregator path has no test of its own — no code changed there; it calls `DISPATCH["spec-surface"]` and `exit_code_for`, which the exit-code test drives.

## Auto Run Result

Status: done

**Summary.** `spec-surface` now reports each `surface:` glob of a readable Spec that matches no tracked file as one non-gating `stale-surface` WARN naming the Spec and the glob. The new rows ride `presumed`, so the OK verdict, the exit code and every drift, coverage and `stale-allowlist` finding are unchanged. A glob is judged by `_glob_to_re`, the matcher governance itself uses, so trailing-slash and brace globs report dead. A Spec whose SPEC.md could not be read is never in `specs` and is not judged. `pixi run -e pyforge-guild spec-surface-check` lists 25 `stale-surface` rows across 7 Specs and exits 0.

**Files changed.**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` — `_stale_surface_findings` plus its one call in `_check_spec_surface`; docstring note on `gather_spec_surface`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py` — eight tests: seven new (live, dead, trailing-slash and brace, unreadable surface, duplicate glob, same glob in two Specs, OK verdict and CLI listing, `stale-allowlist` unchanged) and one existing expectation widened.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` — one "Surface reconcile 2026-10-01" entry naming `chain.py` and the test file.
- This story spec — Code Map, tasks, triage log, result.

**Review.** 20 findings across four layers: 2 patch entries (4 rows) applied, 1 deferred entry (2 rows), 13 rows rejected with the reasons logged above, none high or medium. Patched counts by verdict: high 0, medium 0, low 4.

**Follow-up review recommended:** `false` — no high or medium finding was patched.

**Verification** (every verdict from `$?`, no pipe):
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — exit 0, 3136 passed, 1 skipped, after the patches.
- `pixi run -e pyforge-guild spec-surface-check` — exit 0, 25 `stale-surface` rows, OK row kept.
- `python scripts/spec_surface_reconcile.py` — exit 0.
- `pixi run -e pyforge-guild lint-types` — exit 0.
- Mutation: commenting out the `presumed.extend(...)` call failed 8 of the 50 spec-surface tests (before the patches); the call was restored and the diff compared identical.

**Residual risks.** The deferred non-ASCII quoting (low). `pr-preflight` was not run in this session. `spec-pyforge-marshal` also lists `chain.py` and the test file in its surface; its memlog was not touched, as in Story 38.1, and the doctor memlog names both paths. The 25 dead globs stay for the owning Specs.
