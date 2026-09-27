---
title: '69.1: `workspace clean` keeps a note, not a tarball, for a worktree already on its source'
type: 'fix'
created: '2026-09-27'
status: 'in-progress'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 68.1 took the reinstallable environments out of `workspace clean`'s archives. `_archive_worktree` still tars every worktree it removes, though, at ~120 MB each, even when every file is already on `main`.

On 2026-09-27 a deep audit covered the 25 archives left after that cleanup (3.1 GB) and found none holding work that `main` lacks:
- 19 were byte-identical to a `main` commit.
- The rest were earlier drafts of work `main` carries in a later form.
- Two held stray copies of local secrets: a platform dev key and atlas's local credentials.

The operator deleted all 25 and asked for `clean` to prove a worktree against `main` first.

**Approach:** a new `_landed_proof(record, *, root)` returns `(head_sha, source_sha)` only when git itself proves the worktree holds nothing unlanded. Otherwise it returns `None`, and it never raises. The proof has two parts:
- `git status --porcelain` in the worktree is empty. That covers tracked changes and untracked non-ignored files.
- The worktree's HEAD is an ancestor of the record's `source`, with both resolved to commits via `rev-parse --verify --end-of-options <ref>^{commit}`.

When the proof holds, `_archive_worktree` writes `<slug>-<stamp>.landed.txt` instead of a tarball (`_landed_note`). The note records:
- slug, branch and path;
- the HEAD sha;
- the source and its sha;
- every git-ignored path not kept, from `git status --ignored --porcelain`.

The worktree is then removed exactly as before. Anything unproven archives exactly as CAP-155 does.

Ledger key: `69-1-workspace-clean-keeps-a-note-not-a-tarball-for-a-worktree-already-on-its-source`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-157 (extends CAP-155, Story 68.1; CAP-107, archive-not-delete).

## Acceptance Criteria

- Given a clean worktree whose HEAD is on its source and which holds one git-ignored file When `workspace clean` removes it Then it leaves a `.landed.txt` note naming the HEAD sha, the source and that ignored file, and no tarball
- Given a worktree with an unlanded commit When it is cleaned Then it archives to a tarball
- Given a worktree with an uncommitted edit When it is cleaned Then it archives to a tarball
- Given a worktree with an untracked file When it is cleaned Then it archives to a tarball
- Given a worktree whose recorded source git cannot resolve When it is cleaned Then it archives to a tarball (never dropped)
- Given `status.showUntrackedFiles=no` in config and an untracked file When it is cleaned Then it archives to a tarball
- Given a skip-worktree or an assume-unchanged edit When it is cleaned Then it archives to a tarball
- Given a branch commit behind a HEAD detached on `origin/main` When it is cleaned Then it archives to a tarball and the unmerged branch is kept
- Given a local branch named like the source When it is cleaned Then the proof fails and it archives
- Given ignored Tier-3 drafts under `_bmad-output/` that are not a backlink When it is cleaned Then it archives; a backlink symlink alone does not block the note

## Boundaries & Constraints

**Always:**
- The proof is git's own, never a guess.
- Anything unproven archives (archive-not-delete).
- The note names every git-ignored path it does not keep.

**Never:**
- Do not change `--merged-only` semantics, the confirm prompt, or the `.missing.txt` path.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| landed | clean tree, HEAD on `origin/main` | `.landed.txt` note; no tarball; worktree removed | a note write that fails → `could not archive …` row, record kept (CAP-155) |
| ignored local file | `dev-secret.local` ignored | named in the note's ignored list | — |
| unlanded commit | HEAD not on source | tarball | — |
| uncommitted edit | tracked file modified | tarball | — |
| untracked file | a new non-ignored file | tarball | — |
| unresolvable source | record's source ref gone | tarball | — |
| path gone | worktree missing | `.missing.txt` (unchanged) | — |
| config hides untracked | `status.showUntrackedFiles=no` | pinned `normal`: tarball | — |
| hidden index entry | skip-worktree / assume-unchanged edit | tarball | — |
| detached HEAD | branch commit not on source | tarball; branch kept | — |
| shadowing ref | local `origin/main` branch | ambiguous → no proof → tarball | — |
| submodule `ignore=all` | a submodule commit | pinned `--ignore-submodules=none`: tarball | — |
| ignored listing fails | `status --ignored` exits non-zero | tarball | — |
| ignored Tier-3 | a real `implementation-artifacts/` dir | tarball (a backlink symlink is fine) | — |
| many ignored paths | 250 ignored files | note lists 200, counts 50 | — |
| unmerged branch, tar path | any tarred worktree | the branch is kept, not `-D`'d | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-157.
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-27 (evening) — Proposed: an archive only for work that has not landed*.
Ledger key: `69-1-workspace-clean-keeps-a-note-not-a-tarball-for-a-worktree-already-on-its-source`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

### Review 1 — 2026-09-27, independent adversarial reviewer, working tree on `workspace-clean-proves-against-main` — FAIL (1 high, 2 medium)

Verified clean: stashes live in the common dir and survive; commits on another local branch survive; a note write that fails is an error row with the record kept; a proven but locked worktree is moved into the archive folder; an unresolvable source, an unlanded commit, an uncommitted edit and an untracked file (default config) tar; `--merged-only`, the confirm prompt and `.missing.txt` unchanged; planning text agrees.

- `[high]` `[patch]` **`status.showUntrackedFiles=no` blinded the proof and the note** — an untracked file was deleted unnamed. **Fix:** `_worktree_dirty` pins `-c status.showUntrackedFiles=normal` (fixing `status` and the repo-set dirty gate too); the note's listing pins it as well; `test_an_untracked_file_archives_even_when_config_hides_untracked_files`.
- `[medium]` `[patch]` **skip-worktree / assume-unchanged edits were invisible to `status`.** **Fix:** `ls-files -v` — any lowercase or `S` tag is no proof; two tests.
- `[medium]` `[patch]` **The proof checked HEAD, but cleanup deletes the recorded branch** — a detached HEAD over a branch commit was certified and the commit lost (the loss predated 69.1: a tarball holds files, never history). **Fix:** the branch tip must be on the source too; and in every clean the branch is deleted only when it is on the source; `test_a_detached_head_on_main_does_not_prove_the_branch_and_the_branch_is_kept`.
- `[low]` `[patch]` A submodule with `ignore=all` hid a submodule commit — `--ignore-submodules=none` pinned (no dedicated test; the flag is on the one status call).
- `[low]` `[patch]` A failed ignored listing wrote "(0)" — now no proof; `test_a_failed_ignored_listing_archives_instead_of_writing_an_empty_note`.
- `[low]` `[patch]` A local ref shadowing `origin/main` resolved with only a warning — an ambiguous resolution is no proof; `test_a_local_ref_shadowing_the_source_is_no_proof`.
- `[low]` `[patch]` Ignored work-bearing paths (a scratch worktree's own Tier-3 drafts) were dropped — a real file or directory under `_bmad-output/` forces a tarball, a backlink symlink does not; two tests. Other ignored local files (a dev key, a local credential) are dropped by design and named in the note.
- `[low]` `[patch]` Note size — at most 200 ignored paths listed, the rest counted; `core.quotePath=false`.
- `[nit]` `[patch]` "Never raises" was inexact — the docstring says git-launch failures raise and become an error row. "every file it drops" (Dream, epics) → "the git-ignored paths".
