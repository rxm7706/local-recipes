---
title: "41.1: The chain sources measure what they claim: spec-surface, dream-chain, the deferred-work checks and the verification sweep"
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

**Problem:** Doctor's chain gathers (`sources/chain.py`) and the scripts that write their baselines and verdicts carry 29 open deferrals (12 medium, 17 low): surface globs that can never match or parse to nothing, git output read quoted or split on the wrong byte, a future `verified:` date read as fresh forever, a Tier-3 bullet swallowed, a subdirectory target answered with false FAILs, a verdict writer with no citation, duplicate or collision check, baseline scripts that crash or wipe, and two recommended follow-up reviews (Stories 12.5, 38.1) that never ran.

**Approach:** Fix each row where its behaviour lives (one line each below), keep `chain.py` and its script twin `scripts/spec_surface_check.py` reading the contract identically, wire the dreams-hygiene classes warn-only, and run the two follow-up reviews.

Ledger key: `41-1-the-chain-sources-measure-what-they-claim`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- spec-pyforge-doctor CAP-24, CAP-26-CAP-29, CAP-36, CAP-41, CAP-59, CAP-86, CAP-88 (the capabilities that shipped each behaviour); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a Spec whose `surface:` uses a quoted glob, a flow sequence, another indent or a glob-less `dir/` entry When `spec-surface` runs, through the chain source or the stamp script Then both read the same globs, and `dir/` governs the directory's subtree
- Given a tracked path with a non-ASCII byte or a colon When `spec-surface`, the call-site count or the ledger reads git Then the path arrives literal and its fields are split on NUL
- Given a `verified:` line dated after today, a project's live anonymous count below its stamp, or a target that is a repository subdirectory When the deferred-work, due-for-verification or spec-surface gather runs Then each is one named WARN, never an OK or a FAIL storm
- Given an uncited verdict, a verdict already on the entry, or a ledger with two entries sharing an id When `apply_verification_verdicts.py` runs Then it refuses, skips and reports, and refuses naming both lines, respectively
- Given a corrupt `scripts/.spec-surface-baseline.json`, or a full stamp that discovers zero Specs over a non-empty baseline When the stamp script runs Then it exits non-zero with a diagnostic and writes nothing
- Given `detectors-ci` When it runs Then `dream-chain --dreams` reports warn-only beside the other Doctor sources
- Given any code row above When its fix is reverted Then at least one test in the station suite fails
- Given each `DW-FRR-<story>` row this story lists When its follow-up review has run Then the reviewed story's spec reads `followup_review_recommended: false` with a dated Review Triage Log entry naming this story, every finding the review raised is fixed here (with a test) or recorded there with its reason, and the row closes citing that log line
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-12-4`, `DW-12-5-3`, `DW-FU-6-6-6`, `DW-FU-6-6-7`, `DW-FU-6-6-9`, `DW-FU-8-1`, `DW-FU-11-1`, `DW-OPS-2026-10-01-2`, `DW-OPS-2026-10-01-4`, `DW-doctor-38-1`, `DW-doctor-38-1-2`, `DW-FU-7-2-2`, `DW-7-3-1`, `DW-doctor-38-1-3`, `DW-doctor-38-2`, `DW-FU-11-2`, `DW-FU-11-2-2`, `DW-FU-11-3`, `DW-FU-11-3-2`, `DW-FU-11-3-3`, `DW-FU-11-4`, `DW-FU-11-4-2`, `DW-FU-12-5`, `DW-FU-12-5-2`, `DW-FU-6-6-4`, `DW-FU-21-6`, `DW-FU-21-6-2`, `DW-FRR-12-5`, `DW-FRR-38-1` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Keep `chain.py` and `scripts/spec_surface_check.py` agreeing on the surface contract. A Spec whose governed set grows under the `dir/` rule is reconciled and scoped-stamped in this change (one memlog line each). A change under `.claude/skills/conda-forge-expert/` invokes the conda-forge-expert skill first and lands as one `retro(cfe):` commit with a CHANGELOG entry and semver bump. Re-verify each row at HEAD before fixing it: a row whose defect a later landing already removed closes citing the `path:line` of that fix and the test that pins it (adding the test when none exists), never on prose alone. Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix. A governed file moves only with its owning Spec's memlog naming it, then a scoped stamp for exactly that Spec (AGENTS.md pre-PR item 5); `spec-pyforge-core` co-governs every station's `src/`. Implementation and the follow-up reviews stay separate personas (AGENTS.md guideline 8). If a marshal follow-up-review dispatch closes a `DW-FRR-*` row first, cite that closure instead of re-running the review.

**Never:** Never let the stamp script fall back to `{}` on a corrupt baseline. Never close a row without a landed fix, a `resolution:` naming this story and a `verified:` line citing what was read. Never edit `SPEC.md` by hand or stamp a bare `--write-baseline`. Never weaken or delete a test to make a row pass. Never turn a warn-only finding into a gate.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phases 4 and 5)

29 rows: 12 medium, 17 low.

- `DW-FU-12-4` (medium) — Both surface matchers (`chain.py::_glob_to_re` and `scripts/spec_surface_check.py::glob_to_re`) read a glob-less trailing-slash entry (`dir/`) as that directory's subtree, so `spec-pyforge-marshal/SPEC.md:106`'s `.claude/skills/conda-forge-expert/tests/meta/` governs what it names; every Spec whose governed set grows is reconciled (memlog) and scoped-stamped in the same change.
- `DW-12-5-3` (medium) — Every baseline write path (scoped and full stamp) holds the sidecar flock across read, merge and atomic replace, pinned by a two-process test that neither drops the other's entries; two worktrees write two files that git merges, which no lock spans, and the module docstring says so.
- `DW-FU-6-6-6` (medium) — `_spec_entry` reads a scalar `covers-dreams:` as a one-item list and reports any other non-list value as a named WARN, never iterating a string character by character.
- `DW-FU-6-6-7` (medium) — `gather_spec_surface` resolves the repository top level and, when `target` is a subdirectory, emits one `spec-surface-unevaluable` WARN naming both paths instead of a storm of `ungoverned` FAILs.
- `DW-FU-6-6-9` (medium) — `_parse_surface` and its script twin `parse_surface` read `surface:` with a YAML frontmatter reader (quoted globs, flow sequences, any indent); a `surface:` key that yields no globs emits `spec-surface-unevaluable`.
- `DW-FU-8-1` (medium) — `_anonymous()` no longer swallows the headerless bullet after an `IDENTIFIED_PLAIN` `### DW-<n>:` header, so `tier3-entry-unidentified` counts it.
- `DW-FU-11-1` (medium) — `_parse_verified_date` refuses a date after today: a future `verified:` line is a named WARN and is never read as permanently fresh.
- `DW-OPS-2026-10-01-2` (medium) — Story 38.2 shipped the dead-surface-glob WARN (CAP-88) and left this row open: re-verify at HEAD that the remaining dead globs are named, pin it with a test if none does, and close citing the line.
- `DW-OPS-2026-10-01-4` (medium) — Story 38.1 shipped the `verified:`-line citation rule (CAP-29) and left this row open: re-verify at HEAD, pin it with a test if none does, and close citing the line.
- `DW-doctor-38-1` (medium) — `scripts/apply_verification_verdicts.py` refuses a verdict whose evidence fails the citation predicate the deferred-work check applies (one definition, never a copy), so the sanctioned writer cannot append a line the rule FAILs.
- `DW-doctor-38-1-2` (medium) — The `path:line` citation grammar (`chain.py:4429`) accepts extensionless paths (`.gitignore:3`, `Makefile:12`) and anchor-style cites (`module.py::symbol`) that the ledgers already use.
- `DW-FU-7-2-2` (medium) — `scripts/deferred_work_baseline.py` validates `--project` against the union of the committed baseline and the discoverable projects, so a project whose Tier-3 file is gone can be lowered or zeroed.
- `DW-7-3-1` (low) — The deferred-work source WARNs when a project's live anonymous-Tier-3 count falls below its stamped baseline (a stale-high stamp would grandfather new entries), so baseline freshness is checked on every run.
- `DW-doctor-38-1-3` (low) — The `deferred-work-check` and `due-for-verification-check` task descriptions in `pixi.toml` say a `verified:` line must cite what it read (a task-text change; `environment.yaml` unchanged).
- `DW-doctor-38-2` (low) — `_tracked_files` (`chain.py:1822`) reads `git -c core.quotePath=false ls-files -z` and splits on NUL, so a non-ASCII path arrives literal and matches its glob.
- `DW-FU-11-2` (low) — `_churn_since` and `_authored_date` memoize per (path, since) within one sweep, so a path cited by many due entries spawns one `git log`.
- `DW-FU-11-2-2` (low) — `_churn_since` and `_authored_date` read history from an explicit ref (`refs/remotes/origin/main` when it exists, else `HEAD`), so a change landed on main counts as churn from any worktree.
- `DW-FU-11-3` (low) — `_call_site_count` scopes its grep to the package of the entry's cited paths and skips comment and docstring lines, so a generic short name or a prose mention no longer inflates the count.
- `DW-FU-11-3-2` (low) — `_entry_unused_symbol_claims` binds each "unused"-family phrase to its nearest backticked identifier over all matches, so the claim names the intended subject.
- `DW-FU-11-3-3` (low) — `_call_site_count` splits `git grep` output on NUL (`-z`), so a colon in a matched path no longer shifts the line number and content fields.
- `DW-FU-11-4` (low) — `apply_verification_verdicts.py`'s `_entry_spans` refuses a ledger holding two entries with one `DW-` id, naming both lines, instead of letting the second overwrite the first.
- `DW-FU-11-4-2` (low) — `apply_verification_verdicts.py` skips and reports a verdict whose exact `verified:` line already sits on the entry, so a re-run is idempotent.
- `DW-FU-12-5` (low) — `scripts/spec_surface_check.py::_read_baseline` turns a corrupt baseline into a diagnostic naming the file and the re-stamp recovery path, exit non-zero, never an `except -> {}` fallback.
- `DW-FU-12-5-2` (low) — The `--spec`-less full stamp refuses to write when discovery returns zero Specs and the committed baseline is not empty.
- `DW-FU-6-6-4` (low) — `scripts/spec_surface_check.py`'s tracked-file read uses `-c core.quotePath=false` and NUL splitting, as `chain.py` does (the script twin of DW-doctor-38-2).
- `DW-FU-21-6` (low) — `docs/dreams/README.md`'s Phase-2b prose describes file-driven reconciliation and the three dreams-hygiene finding classes (the file is governed by `spec-pyforge-genesis`: reconcile its memlog).
- `DW-FU-21-6-2` (low) — `scripts/detectors.py` runs `dream-chain --dreams` warn-only beside the other Doctor sources, so the three dreams-hygiene classes report in `detectors-ci` without a live-volume red (CAP-43's warn-only shape, as Story 38.3 did for the hygiene sweep).
- `DW-FRR-12-5` (low) — Run the recommended independent follow-up review of Story 12.5's landed diff against its spec (a review persona that did not implement it); fix its findings in this story or record why each stands, write them to that spec's Review Triage Log, and set its `followup_review_recommended: false`.
- `DW-FRR-38-1` (low) — Run the recommended independent follow-up review of Story 38.1's landed diff against its spec (a review persona that did not implement it); fix its findings in this story or record why each stands, write them to that spec's Review Triage Log, and set its `followup_review_recommended: false`.

## Binding

Parent: spec-pyforge-doctor CAP-24, CAP-26-CAP-29, CAP-36, CAP-41, CAP-59, CAP-86, CAP-88 (the capabilities that shipped each behaviour); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.
Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-03 (Phase 4+5) entry.
Ledger key: `41-1-the-chain-sources-measure-what-they-claim`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 4+5 rulings (fix every open medium deferral and the lows in the modules it touches, no blanket closure; sizing override the same day: fewer, larger stories split by package area, at most about 30 rows each).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
