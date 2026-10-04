---
title: "87.2: The unpushed-work detector fails closed and never prints a tag-minting remedy"
type: 'fix'
created: '2026-10-04'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - scripts/unpushed_work_check.py
  - tests/scripts/test_unpushed_work_check_full_ref.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `scripts/unpushed_work_check.py` answers "is any work only on this disk?", and it has three defects.
- It fails open: its git helper returns `""` whenever git exits non-zero (`:65-71`). On 2026-10-04, while `git fsck` exited 1 on two empty loose objects, the detector reported 0 dangling commits while 20,135 existed.
- It reads only `refs/heads/*` for unpushed content. A local-only tag or a custom ref (`refs/attempt-preserve-dirty/*`, `refs/backup/*`) holding the only copy of a commit is never reported.
- Its remedy prints `git tag rescue/dangling-… && git push origin …` (`:153-170`). Sessions ran that by hand and minted 682 public lightweight tags. 23 of them re-preserved the history the 2026-07-24 purge removed; they were deleted from `origin` on 2026-10-04.

`fsck` is healthy again, so the risk has turned around. Marshal's merged check writes about 700–2,500 synthetic "marshal teardown merged-check (not a real commit)" objects a day. About 16,000 of them now pass the `--min-files` filter, so a full run would print 16,000 minting remedies.

**Approach:** Make the detector fail closed and report only. Any git call it depends on that exits non-zero makes the run exit 2 (could-not-observe), naming the command. A commit whose subject ends "(not a real commit)" is never a dangling finding. Local-only tags and custom refs whose commits are on no `origin` ref become `unpushed-ref` findings, named by full refname. "On `origin`" means reachable from a `refs/remotes/origin/*` ref, or from a tag `git ls-remote --tags origin` lists. No remedy mints anything: every remedy reads "report; do not tag", and names the operator's review and, once Story 87.3 ships it, `marshal preserve tag`. `rescued()` keeps counting the frozen legacy `rescue/dangling-*` tags, plus any `preserve/` or `archive/` tag, as holding a commit.

Ledger key: `87-2-the-unpushed-work-detector-fails-closed-and-never-prints-a-tag-minting-remedy`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` FR-62 / AD-48 (durability is a status dimension, read from this detector) and CAP-287 / AD-81 (the preserve standard). A defect of shipped tooling, so it is a `fix` and carries no flag (`spec-feature-flag-governance` Q1). The operator ruled on 2026-10-04 that this hotfix ships unflagged and first: architecture review M2 and Q3.

## Acceptance Criteria

- Given a repository where `git fsck --no-reflogs`, or any other git call the detector depends on, exits non-zero When the detector runs without `--branches-only` Then it exits 2 and names the failing command; it never reports 0 dangling commits.
- Given a dangling commit whose subject ends "(not a real commit)" When the detector runs Then it is not a finding, and a real dangling commit beside it still is.
- Given a local-only annotated tag, a lightweight tag and a `refs/<custom>/*` ref, each holding a commit on no `origin` ref, against a bare `origin` When the detector runs Then each is a finding of kind `unpushed-ref` with its full refname; the same refs on a commit that `origin/main` or a tag on `origin` reaches are not.
- Given any finding When its remedy prints Then it contains neither `git tag` nor `git push`; it says "report; do not tag" and names the operator's review.
- Given a commit held only by a legacy `rescue/dangling-*` tag, or by a `preserve/` or `archive/` tag When the dangling scan runs Then it is not reported as unpreserved.
- Given `--branches-only` (the mode `marshal status` runs) When the detector runs Then its existing `unpushed-branch` output is unchanged for passing input, and a failed git call still exits 2.
- Given each rule removed When the tests run Then they fail (mutation). Tests use real git repositories and a bare remote, never the network.

## Boundaries & Constraints

**Always:** Fail closed. Match full refnames (Story 61.1). Keep the JSON shape additive, because `marshal status` reads it.

**Never:** Never mint, push or delete a ref, and never print a command that would. Never treat a name as proof that work is durable. Never call GitHub in tests.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-287 (FR-234, AD-81); FR-62 / AD-48 (amended 2026-10-04).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (preserved-work refs) entry.
Research: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04.md` § 4 item 1, and the review's M2 and Q3.
Ledger key: `87-2-the-unpushed-work-detector-fails-closed-and-never-prints-a-tag-minting-remedy`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-04 under the operator's ruling of the same day (the review's recommended defaults).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_unpushed_work_check.py tests/scripts/test_unpushed_work_check_full_ref.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the CI `scripts-suite` twin).
- On the primary checkout, read-only: `python scripts/unpushed_work_check.py --json` — expected: no remedy contains `git tag`, and the synthetic merged-check commits are not listed.

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
