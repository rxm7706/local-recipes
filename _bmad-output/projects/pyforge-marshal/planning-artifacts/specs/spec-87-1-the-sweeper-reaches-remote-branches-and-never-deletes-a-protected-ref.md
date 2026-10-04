---
title: "87.1: The sweeper reaches remote branches and never deletes a protected ref"
type: 'fix'
created: '2026-10-04'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - scripts/worktree_sweep.py
  - tests/scripts/test_worktree_sweep.py
  - docs/how-to/manage-worktrees-with-bmad.md
  - docs/governance/guild-roster.json
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-10-04 an operator session cleaned up branches with a hand-rolled script instead of `scripts/worktree_sweep.py`. It removed every worktree whose `git status --porcelain` was empty, which included the eight station loop homes `~/.bmad-loops/pyforge-<station>`: porcelain hides gitignored files, so the loop homes' runtime state went with them. It also deleted the eight `loop/pyforge-<station>` branches, because their tips were ancestors of main, and 41 `attempt-preserve/*` branches, local and remote. The operator had approved the deletion by tier. The refs were restored from GitHub's branch-deletion activity log (`before` sha) through `gh api -X POST …/git/refs`, and the loop homes with `marshal init`. The gitignored run history was lost. `scripts/worktree_sweep.py` would have kept every one of them: its verdicts keep loop homes, and it never deletes a `loop/*`, `attempt-preserve/*`, `recover/*` or `rescue/*` branch. But it only sweeps worktrees and local merged branches, so remote branches still need a hand-written script. It also has no way to retire a protected `attempt-preserve/*` branch once its story has landed: 30 were retired by hand on 2026-10-04 (manifest below).

**Approach:** Add a remote mode and an explicit-name retirement to the one sweeper:
- `--remote` (dry run by default; `--execute` applies) gives every `origin` branch a verdict:
  - KEEP: `main`, a protected prefix, an open PR's head, a branch checked out in any worktree, or a live dispatch run's branch.
  - DELETE: the tip is an ancestor of `origin/main`; or the PR merged; or the PR closed and the story's ledger row is `done`.
  - INSPECT: everything else.
- `--execute` writes a JSON manifest (branch, sha, verdict, reason) under `--preserve-dir` before it deletes anything, and deletes in batches.
- `--retire <branch>...` deletes only the protected branches named on the command line, never a pattern, after writing the same manifest.
- The protected prefixes are read from `docs/governance/guild-roster.json` `protected_ref_prefixes` when that key exists (steward Story 85.1 adds it), else from the script's own `PROTECTED_BRANCH_PREFIXES`.

Ledger key: `87-1-the-sweeper-reaches-remote-branches-and-never-deletes-a-protected-ref`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- The worktree/branch hygiene tool `scripts/worktree_sweep.py`, kept as the permanent home by the Phase 3 ruling on DW-HYGIENE-2026-09-05-1 (2026-10-03). A defect of shipped tooling, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a real repository with a bare `origin` holding branches of every kind (merged, PR merged, PR closed with a done or a not-done story, open PR, protected prefixes, checked out in a worktree, no PR and unmerged) When `worktree_sweep.py --remote` runs Then each gets the verdict above with its reason, and nothing is deleted
- Given the same repository When `--remote --execute` runs Then only DELETE branches leave `origin`, and the manifest names each with its sha before the first delete
- Given `--retire attempt-preserve/x loop/y` When it runs Then the named branches are deleted after the manifest is written; a pattern or a name that does not exist is refused; without `--retire` no protected branch is ever deleted
- Given a loop home `~/.bmad-loops/<station>` whose `git status --porcelain` is empty but which holds gitignored files When the worktree sweep runs with `--execute` Then it stays KEEP with the reason "loop home"
- Given `docs/governance/guild-roster.json` with `protected_ref_prefixes` When the sweep runs Then it uses that list; given no such key Then it uses `PROTECTED_BRANCH_PREFIXES`
- Given each rule removed When the new tests run Then they fail (mutation); PR state comes from an injectable reader, never the network

## Boundaries & Constraints

**Always:** Dry run by default; write the manifest before any delete; test with a real git repository and a bare remote.

**Never:** Never delete a protected branch except by explicit `--retire` name. Never remove a loop home. Never call GitHub in tests.

</intent-contract>

## Context: the attempt-preserve branches retired on 2026-10-04

The operator ruled on 2026-10-04: "retire the 30, keep the 3". Kept: `attempt-preserve/47.1-dispatch-20260920-80e85c57` (Story 47.1 is blocked; this is its only preserved work), `attempt-preserve/20260821-082415-mason-6-3-github-version-checker-gap` (blocked mason 6.3 attempt), and `attempt-preserve/20260712-125315-0aaa-c2605ff1` (the bmad-loop pilot's history). Retired, with their tip shas. A restore is `gh api -X POST repos/rxm7706/local-recipes/git/refs -f ref=refs/heads/<branch> -f sha=<sha>` while GitHub still holds the commit.

| Branch | Tip sha |
|---|---|
| `attempt-preserve/20260809-114839-7af9-e63ea1e7` | `e63ea1e7dcf504d16cf8497929d52d82a20d4726` |
| `attempt-preserve/20260812-191714-167d-6725b773` | `6725b773fd251bc62b6f562e5c61b2f2e6a23aa8` |
| `attempt-preserve/20260813-094917-9bba-c9e59028` | `c9e59028ffad5ed42adf0cf8816add80a4cae0db` |
| `attempt-preserve/20260813-094919-bfcb-1f6320dc` | `1f6320dc4c54329a56e1da6187d55a8a33b167ae` |
| `attempt-preserve/20260813-094919-bfcb-523e938c` | `523e938c79783d06d72030afdb92932d3d02f62f` |
| `attempt-preserve/20260813-094919-bfcb-95ea70c9` | `95ea70c9e374c74b5ed7994b81878e89975141fb` |
| `attempt-preserve/20260813-094919-bfcb-a71b81c4` | `a71b81c4cfeb3ce2d9fcc4e3b8e63527e6c9e661` |
| `attempt-preserve/20260813-094919-bfcb-accc097e` | `accc097e6ab585d0398a4e66bb1c7365ee1ba960` |
| `attempt-preserve/20260813-094919-bfcb-bf979ece` | `bf979ece863e872102b1d332e60b2d68a3139bf6` |
| `attempt-preserve/20260813-094919-bfcb-e5c52f83` | `e5c52f83c072b80e07e17194839f76a0c7792449` |
| `attempt-preserve/20260813-094919-bfcb-edd3a0ef` | `edd3a0ef9890dfedff95ecaa2922e722dc75a997` |
| `attempt-preserve/20260813-145934-3eb0-4edeb666` | `4edeb666fceadd614836a1802085d5ff139cf7a5` |
| `attempt-preserve/20260813-145934-3eb0-855522fe` | `855522fe024b2460b0d19652cf2863a47422e6a5` |
| `attempt-preserve/20260813-160412-936a-137d3f9c` | `137d3f9c5b944fa2a479f169ad50c8cccf7d3294` |
| `attempt-preserve/20260813-160412-936a-85a60d06` | `85a60d06e673b50ee9553fcd9d369fc1f3273f2a` |
| `attempt-preserve/20260814-202328-e168-01027a26` | `01027a26ec95369152f04aa5aab081cc0f79a3ed` |
| `attempt-preserve/20260814-202328-e168-4bc53701` | `4bc5370124f19efa806105a85c160930cef95ed5` |
| `attempt-preserve/20260814-202329-6e05-3ab65098` | `3ab650982398e8944d250b8c234a0cbc9ed42165` |
| `attempt-preserve/20260814-202329-6e05-9de381a0` | `9de381a01e279385e778dedffe7cbf7ec54cc0b8` |
| `attempt-preserve/20260815-112702-c77e-1f526046` | `1f5260468e17565dd5d27940bcf28076e542fa80` |
| `attempt-preserve/20260815-115702-0501-066d3633` | `066d3633d996953e91167daf6ce8ebab9749090b` |
| `attempt-preserve/20260815-115702-0501-34fcec5c` | `34fcec5c6dd6d0099aec548858f397fbb60efdba` |
| `attempt-preserve/20260815-115702-0501-46cf7ae6` | `46cf7ae664f09d9bdcafd859d91c9dffe46c800a` |
| `attempt-preserve/20260910-100021-1dbc-b9f867c9` | `b9f867c912a06dbe6c3990a6fbcda3e83fdf433e` |
| `attempt-preserve/20260910-100021-1dbc-de30608a` | `de30608a1f84a71525f66dd5a1e22f79c3c0879c` |
| `attempt-preserve/20260910-100021-1dbc-e6827596` | `e6827596cd5a42bd36245776aa12130033d6842a` |
| `attempt-preserve/20260914-201759-bd47-1a029b86` | `1a029b86a0ab720b262c7ee031b11e278ff1d522` |
| `attempt-preserve/20260914-201759-bd47-f909c5d7` | `f909c5d726d81419ac753d0f30d5282765a5be86` |
| `attempt-preserve/20260918-011855-dc48-54b60530` | `54b60530294390044bc3c64353d729eaed41aba9` |
| `attempt-preserve/doctor-11-4-46cf7ae664` | `46cf7ae664f09d9bdcafd859d91c9dffe46c800a` |

## Binding

Parent: DW-HYGIENE-2026-09-05-1 (closed 2026-10-03: `scripts/worktree_sweep.py` is the permanent home).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (later) entry.
Ledger key: `87-1-the-sweeper-reaches-remote-branches-and-never-deletes-a-protected-ref`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-04 at the operator's request ("retire the 30, keep the 3, and chain the sweeper fixes").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_worktree_sweep.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-guild scripts-suite` — expected: pass.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

- No review has run yet.
