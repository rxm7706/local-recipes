---
title: "87.17: The legacy promoter reads every commit's bytes"
type: 'fix'
created: '2026-10-22'
status: 'done'
baseline_revision: 'ab50b079a8c8d68d364570b96e01cdd788885ac6'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-87-12-legacy-refs-are-promoted-and-attempt-preserve-leaves-the-protected-list.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/preserve-manifests/README.md
  - docs/dreams/pyforge-marshal.md
  - scripts/legacy_preserve_promote.py
  - tests/scripts/test_legacy_preserve_promote.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** on 2026-10-22 the operator ruled to promote the 17 `refs/attempt-preserve-dirty/*` refs ("go ahead").
`scripts/legacy_preserve_promote.py` (Story 87.12) is the promoter, and it had never written a manifest:
`preserve-manifests/` held only its README. Its first run, dry, crashed with `UnicodeDecodeError: 'utf-8' codec can't
decode bytes` before writing anything. To classify the `rescue/dangling-*` tags, `_origin_main_patch_ids_since` runs
`git show --format=email --no-prefix --binary` and `git patch-id` over each `origin/main` commit since 2026-06-01. That is
13,145 commits, and `_git` decoded each output as UTF-8 text. One commit's `git show` output is not UTF-8:
`e09f50352d`, a 2026-09-10 merge of `origin/main` into `dispatch/pyforge-doctor/21.13`. Its blobs and both parent diffs
are valid UTF-8; the combined diff `git show` prints for a merge cuts an em-dash in a hunk header (`\xe2\x80` at byte
785). Any hunk header that cuts a multi-byte character does the same. Story 87.12's tests never fed the script a
non-UTF-8 byte.

**Approach:**
1. `_patch_id` runs `git show` and `git patch-id` on bytes. A decoded and re-encoded diff would hash differently, so the
   output is never decoded before `git patch-id` reads it; only the patch id (ASCII hex) is decoded.
2. `_git` reads git's text output with `encoding="utf-8", errors="replace"`, so a non-UTF-8 subject cannot raise either.
3. Tests in `tests/scripts/test_legacy_preserve_promote.py` build a commit whose diff carries `\xe9` (`git commit`
   re-encodes the message to UTF-8, so its subject does not), and a raw commit object whose subject keeps `\xe9`.
4. The dry run writes `preserve-manifests/legacy-preserve-promote-2026-10-22.json`, and `--execute` writes the local
   twins. Nothing is pushed.

Ledger key: `87-17-the-legacy-promoter-reads-every-commit-s-bytes`.
Type / Effort / Deps: fix / XS / S-87.12.

### Living CAP citations

- `spec-pyforge-marshal` CAP-287 (FR-234; AD-81): preserved work is a protected tag. Story 87.12 delivered this
  promoter; this is a defect in it, so no new CAP. The script is a one-off, dry-run-default tool that
  `pyforge.marshal.preserve_refs` does not gate, so the fix carries no flag.

## Acceptance Criteria

- **AC1 — Patch id.** For a commit whose diff is not UTF-8, `_patch_id` returns the same id `git show | git patch-id`
  gives on bytes.
- **AC2 — Dry run.** A dry run over an `origin/main` that carries such a commit writes the manifest, with the dirty ref's
  promotion row and a classification row; classifying a raw commit whose subject is not UTF-8 does not raise.
- **AC3 — Mutation.** The three tests fail on the old script.
- **AC4 — Live.** On this repository the dry run writes `legacy-preserve-promote-2026-10-22.json` with a promotion row for
  each of the 17 dirty refs, and `--execute` writes local annotated twins only.

## Boundaries & Constraints

**Always:** Keep the script dry-run by default. Read every verdict from the exit code.

**Never:** Push a tag or delete a ref. Change GitHub settings, the ruleset or `guild-roster.json` (Story 87.12's
operator-gated rows stay rows). Turn on `pyforge.marshal.preserve_refs` here.

**Residual risk:**
- `errors="replace"` turns a non-UTF-8 subject into U+FFFD in the manifest's evidence text. It cannot change a verdict:
  the synthetic and stash patterns are ASCII, and twin names come from commit SHAs.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected |
|----------|-------|----------|
| commit with a non-UTF-8 diff | `_patch_id` | git's own patch id, computed on bytes |
| raw commit object with a non-UTF-8 subject | `classify_rescue_dangling` | `unresolved`; no raise |
| `origin/main` carries such a commit | dry run | manifest written |
| `--execute` | promotion rows | local annotated twins; nothing pushed |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-marshal` CAP-287 (FR-234). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-22 entry (the legacy promoter dies on one
  commit's bytes).
- Epic: Epic 87 (done). Story 87.17 is minted `done`, so `epic-87` stays `done` (operator rule 2026-10-04: a fix story
  goes into its done epic).
- Ledger key: `87-17-the-legacy-promoter-reads-every-commit-s-bytes`; status at mint `done`.

## Verification

**Commands:**
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_legacy_preserve_promote.py -q` — expected: 6 passed
  (AC1, AC2).
- `pixi run -e pyforge-guild python scripts/legacy_preserve_promote.py --manifest-date 2026-10-22` — expected: exit 0,
  the manifest written (AC4).

**Run before the push (not dispatch gates):**
- Both new tests against the old script — expected: both fail (AC3).
- `pixi run -e pyforge-marshal pyforge-marshal-test` — expected: pass.

## Run results

Run 2026-10-22 (local date; the first run's manifest was named for UTC's 2026-10-23) in the landing worktree on
`ab50b079a8`, every verdict read from its exit code.

- **Before the fix:** the dry run exited 1 with `UnicodeDecodeError` in `_patch_id` (`_origin_main_patch_ids_since`),
  and no manifest was written. Of the 13,145 `origin/main` commits since 2026-06-01, one `git show` output is not UTF-8:
  `e09f50352d`.
- **AC1–AC3:** `tests/scripts/test_legacy_preserve_promote.py` gives 8 passed with Story 87.18's test (exit 0). With
  the script of `ab50b079a8` restored, the three tests of this story and 87.18's fail, and the other four pass.
- **AC4, first run** (before the review): the dry run exited 0 in 159 s and wrote 680 rows: 19 promotion rows (the 17
  `refs/attempt-preserve-dirty/*`, plus `refs/backup/pre-split-1787762347` and `refs/bundle/pyforge-pages`), 659
  `rescue/dangling-*` classifications (204 stash, 185 patch-equivalent, 149 synthetic, 103 unresolved, 18 merge), and
  Story 87.12's two operator-gate rows. All 17 dirty refs read `unbound` (the 87.12 deferral: no story inference).
  `--execute` exited 0 and wrote 19 local annotated tags under `refs/tags/preserve/unbound/` (`bmad-loop-<sha8>` for
  the 17, `hand-<sha8>` for the 2). Each of the 17 peels to its dirty ref's commit (0 mismatches), with the
  `Preserve-*` trailers. Nothing was pushed: `origin` still carries only its two earlier mason `preserve/` tags. No ref
  was deleted.
- **After the review:** the re-run under Story 87.18 wrote `legacy-preserve-promote-2026-10-22.json` (688 rows: 27
  promotion, 659 classifications, 2 operator gates); the 19 rows above are unchanged, and the 680-row file is removed.
  `--execute` was not re-run.

## Spec Change Log

- 2026-10-22, independent review (FAIL, 1 blocker), fixed on the same branch:
  - B1: the committed manifest left out 8 legacy refs Story 87.12 names. That is Story 87.18, minted in this change; the
    manifest is re-run as `legacy-preserve-promote-2026-10-22.json`.
  - S1: `git commit` re-encodes a non-UTF-8 message, so the first fixture's subject was UTF-8 and the `errors="replace"`
    change was untested. A raw commit object now keeps `\xe9` in its subject, and `classify_rescue_dangling` reads it.
  - S2: the cause was stated as "one commit's diff is not UTF-8". The bytes come from the combined diff of a merge,
    which cuts an em-dash in a hunk header; the Problem, the Dream, epics and the memlog now say so.
  - Nits: `git patch-id` runs with `-C repo`; ruff findings in the touched files fixed (F541, PIE810, PLW1510, RUF100,
    EXE001: the script is now executable); the residual risk no longer describes a case that cannot happen; the date
    base is the local date, 2026-10-22, not UTC's 2026-10-23; the two `hand-*` twins beyond the 17 are recorded below.

- 2026-10-22: minted `done`, implemented and verified in the same change.

## Review Triage Log

- 2026-10-22, review 1 (independent subagent, read the diff against this spec): FAIL. 1 blocker (B1, the manifest
  missed 8 legacy refs), 2 should-fix, 6 nits. All fixed on the branch (Spec Change Log; B1 as Story 87.18). On N5,
  the operator's ruling named the 17 dirty refs; `--execute` has no row filter and also wrote two local twins,
  `preserve/unbound/hand-26b32591` (`refs/backup/pre-split-1787762347`) and `preserve/unbound/hand-5b6a5404`
  (`refs/bundle/pyforge-pages`). Both are local only and are deleted with `git tag -d` if the operator does not want
  them.
