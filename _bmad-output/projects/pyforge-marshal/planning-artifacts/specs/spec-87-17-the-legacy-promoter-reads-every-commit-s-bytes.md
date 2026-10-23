---
title: "87.17: The legacy promoter reads every commit's bytes"
type: 'fix'
created: '2026-10-23'
status: 'done'
baseline_revision: 'ab50b079a8c8d68d364570b96e01cdd788885ac6'
review_loop_iteration: 0
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

**Problem:** on 2026-10-23 the operator ruled to promote the 17 `refs/attempt-preserve-dirty/*` refs ("go ahead").
`scripts/legacy_preserve_promote.py` (Story 87.12) is the promoter, and it had never written a manifest:
`preserve-manifests/` held only its README. Its first run, dry, crashed with `UnicodeDecodeError: 'utf-8' codec can't
decode bytes` before writing anything. To classify the `rescue/dangling-*` tags, `_origin_main_patch_ids_since` runs
`git show --format=email --no-prefix --binary` and `git patch-id` over each `origin/main` commit since 2026-06-01. That is
13,145 commits, and `_git` decoded each output as UTF-8 text. One commit's diff is not UTF-8: `e09f50352d`, a 2026-09-10
merge of `origin/main` into `dispatch/pyforge-doctor/21.13`. Story 87.12's tests never fed the script a non-UTF-8 byte.

**Approach:**
1. `_patch_id` runs `git show` and `git patch-id` on bytes. A decoded and re-encoded diff would hash differently, so the
   output is never decoded before `git patch-id` reads it; only the patch id (ASCII hex) is decoded.
2. `_git` reads git's text output with `encoding="utf-8", errors="replace"`, so a non-UTF-8 subject cannot raise either.
3. Two tests in `tests/scripts/test_legacy_preserve_promote.py` build a commit whose diff and subject carry `\xe9`.
4. The dry run writes `preserve-manifests/legacy-preserve-promote-2026-10-23.json`, and `--execute` writes the local
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
  promotion row and a classification row.
- **AC3 — Mutation.** Both tests fail on the old script.
- **AC4 — Live.** On this repository the dry run writes `legacy-preserve-promote-2026-10-23.json` with a promotion row for
  each of the 17 dirty refs, and `--execute` writes local annotated twins only.

## Boundaries & Constraints

**Always:** Keep the script dry-run by default. Read every verdict from the exit code.

**Never:** Push a tag or delete a ref. Change GitHub settings, the ruleset or `guild-roster.json` (Story 87.12's
operator-gated rows stay rows). Turn on `pyforge.marshal.preserve_refs` here.

**Residual risk:**
- `errors="replace"` turns a non-UTF-8 subject into U+FFFD in the manifest's evidence text and in the synthetic and
  stash checks. A subject that matched only through those bytes would classify as `unresolved`. No such subject exists
  today.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected |
|----------|-------|----------|
| commit with a non-UTF-8 diff | `_patch_id` | git's own patch id, computed on bytes |
| commit with a non-UTF-8 subject | `_git log -1 --format=%s` | text with U+FFFD; no raise |
| `origin/main` carries such a commit | dry run | manifest written |
| `--execute` | promotion rows | local annotated twins; nothing pushed |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-marshal` CAP-287 (FR-234). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-23 entry (the legacy promoter dies on one
  commit's bytes).
- Epic: Epic 87 (done). Story 87.17 is minted `done`, so `epic-87` stays `done` (operator rule 2026-10-04: a fix story
  goes into its done epic).
- Ledger key: `87-17-the-legacy-promoter-reads-every-commit-s-bytes`; status at mint `done`.

## Verification

**Commands:**
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_legacy_preserve_promote.py -q` — expected: 6 passed
  (AC1, AC2).
- `pixi run -e pyforge-guild python scripts/legacy_preserve_promote.py --manifest-date 2026-10-23` — expected: exit 0,
  the manifest written (AC4).

**Run before the push (not dispatch gates):**
- Both new tests against the old script — expected: both fail (AC3).
- `pixi run -e pyforge-marshal pyforge-marshal-test` — expected: pass.

## Run results

Run 2026-10-23 in the landing worktree on `ab50b079a8`, every verdict read from its exit code.

- **Before the fix:** the dry run exited 1 with `UnicodeDecodeError` in `_patch_id` (`_origin_main_patch_ids_since`),
  and no manifest was written. Of the 13,145 `origin/main` commits since 2026-06-01, one `git show` output is not UTF-8:
  `e09f50352d`.
- **AC1–AC3:** `tests/scripts/test_legacy_preserve_promote.py` gives 6 passed (exit 0). With the old script restored,
  `test_patch_id_reads_a_non_utf8_diff` and `test_dry_run_survives_a_non_utf8_commit_on_origin_main` fail and the other
  four pass.
- **AC4, dry run:** exit 0 in 159 s. `legacy-preserve-promote-2026-10-23.json` holds 680 rows: 19 promotion rows (the 17
  `refs/attempt-preserve-dirty/*`, plus `refs/backup/pre-split-1787762347` and `refs/bundle/pyforge-pages`), 659
  `rescue/dangling-*` classifications (204 stash, 185 patch-equivalent, 149 synthetic, 103 unresolved, 18 merge), and
  Story 87.12's two operator-gate rows. All 17 dirty refs read `unbound` (the 87.12 deferral: no story inference).
- **AC4, `--execute`:** exit 0. 19 local annotated tags under `refs/tags/preserve/unbound/` (`bmad-loop-<sha8>` for the
  17, `hand-<sha8>` for the 2). Each of the 17 peels to its dirty ref's commit (0 mismatches), with the `Preserve-*`
  trailers. Nothing was pushed: `origin` still carries only its two earlier mason `preserve/` tags. No ref was deleted.

## Spec Change Log

- 2026-10-23: minted `done`, implemented and verified in the same change.

## Review Triage Log

- 2026-10-23: the independent review runs as a separate pass and records its findings here.
