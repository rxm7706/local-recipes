---
title: '69.1: `workspace clean` keeps a note, not a tarball, for a worktree already on its source'
type: 'fix'
created: '2026-09-27'
status: 'done'
review_loop_iteration: 2
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

**Approach (as landed, after reviews 1 and 2):** `_landed_note_text(record, *, root, stamp)` returns the note text only when git itself proves the worktree holds nothing unlanded, else `None` (the worktree then archives exactly as CAP-155 does). The proof, all of it:
- `git status --porcelain` empty, with `status.showUntrackedFiles=normal` and `--ignore-submodules=none` pinned in `_worktree_dirty`;
- no skip-worktree or assume-unchanged index entry (`ls-files -v`), no gitlink (`ls-files --stage`), no per-worktree ref (`refs/worktree/`, `refs/bisect/`);
- HEAD and the recorded branch (when it exists) both ancestors of the source, which must resolve to a remote-tracking ref (`_source_commit`: `rev-parse --symbolic-full-name`);
- the git-ignored listing (`status --ignored --porcelain -z`, read as bytes by `_git_bytes`) succeeds and holds no real file or directory under `_bmad-output/`.

Anything that fails, is ambiguous, or cannot be decoded is no proof. The note records slug, branch, path, the HEAD sha, the source and its sha, up to 200 git-ignored paths (the rest counted), and the worktree's pre-push skip journal. After removal, the recorded branch is deleted only when it is on the source; an unmerged branch is kept and reported (`branch_kept`, and `format_clean` says so).

Ledger key: `69-1-workspace-clean-keeps-a-note-not-a-tarball-for-a-worktree-already-on-its-source`.
Ledger status (do not edit the ledger): `done`.
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
- Given an ignored file whose name is not valid UTF-8 When it is cleaned Then the sweep does not crash and the note names it
- Given a gitlink or a per-worktree ref When it is cleaned Then it archives
- Given a worktree with a pre-push skip journal When it is cleaned with a note Then the journal's lines are copied into the note
- Given an unmerged branch When its worktree is cleaned Then the branch is kept and the clean output names it

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
| unmerged branch, tar path | any tarred worktree | the branch is kept, not `-D`'d; the row says `branch_kept` | — |
| non-UTF-8 ignored name | `caf\xe9.local` | named in the note (backslash-escaped); no crash | — |
| quiet shadow | `core.warnAmbiguousRefs=false` + local `origin/main` | not a remote-tracking ref → tarball | — |
| quoted Tier-3 path | `we"ird/implementation-artifacts/` | tarball | — |
| gitlink / per-worktree ref | `160000` entry / `refs/worktree/keep` | tarball | — |
| skip journal | `.steward/preflight-skips.log` | lines copied into the note | — |

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

### Review 2 — 2026-09-27, independent adversarial reviewer, commit `7c2cc5e08b` — FAIL (1 medium) → fixed

Verified closed by re-running review 1's probes: `showUntrackedFiles=no` (repo and global), skip-worktree, assume-unchanged, a detached HEAD over a branch commit (branch kept), a shadowing branch or tag or `refs/origin/main`, a submodule `ignore=all`, a failed listing, Tier-3 real dir vs backlink, truncation; a deleted branch with HEAD on source notes; an unborn HEAD tars; a missing path with an unmerged branch keeps the branch.

- `[medium]` `[patch]` **A non-UTF-8 ignored name crashed the whole sweep** (`UnicodeDecodeError` is a `ValueError`, not caught) — every later sweep would abort at that record, breaking CAP-155. **Fix:** the listing is `-z` bytes via `_git_bytes`, displayed with `backslashreplace`; any `ValueError` in the proof is no proof; `test_a_non_utf8_ignored_name_neither_crashes_the_sweep_nor_goes_unnamed`.
- `[low]` `[patch]` **`core.warnAmbiguousRefs=false` silenced the shadow warning** the first fix relied on. **Fix:** `_source_commit` asks `--symbolic-full-name` which ref won and accepts only `refs/remotes/`; `test_a_shadowing_ref_is_no_proof_even_with_ambiguity_warnings_off`.
- `[low]` `[patch]` **A C-quoted path bypassed the Tier-3 guard** — fixed by `-z`; `test_quoted_tier3_paths_still_force_a_tarball`.
- `[low]` `[patch]` **The kept branch was invisible**, and a later `start` of the slug then failed. **Fix:** `branch_kept` in the row, `format_clean` names it, the docstring says a later `start` needs it deleted; `test_an_unmerged_branch_is_kept_and_the_clean_output_says_so`, `test_a_merged_branch_is_still_deleted`.
- `[low]` `[patch]` **The pre-push skip journal was dropped** — its lines are copied into the note; `test_the_skip_journal_is_copied_into_the_note`.
- `[nit]` `[patch]` A submodule's ignored files went unnamed — a gitlink is no proof; `test_a_gitlink_is_no_proof`. `[nit]` `[patch]` A per-worktree ref could hold the only copy of a commit — no proof; `test_a_per_worktree_ref_is_no_proof`. `[nit]` `[patch]` Stale names in the epics Surface and this spec's Approach — rewritten.
- `[nit]` `[note]` `--ignore-submodules=none` makes `workspace status` and the repo-set dirty gate count submodule changes as dirty — conservative, no repo here has submodules; recorded on CAP-157's memlog. Sparse-checkout worktrees always tar (`S` entries) — acceptable; `start` never makes one.
