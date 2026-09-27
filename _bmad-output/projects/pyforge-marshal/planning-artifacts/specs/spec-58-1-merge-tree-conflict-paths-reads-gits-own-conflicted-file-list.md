---
title: '58.1: `merge_tree_conflict_paths` reads git''s own conflicted-file list'
type: 'fix'
created: '2026-09-27'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - docs/dreams/pyforge-marshal.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 28.20's landing heal unions a PR whose only conflict is the sprint ledger and escalates any other conflict by name. It has never seen a conflict. `GitVcs.merge_tree_conflict_paths` runs the legacy three-arg `git merge-tree <merge-base> <base> <branch>` and collects lines containing `Merge conflict in `. That form prints `changed in both`, the three blob lines and conflict markers — never that line (probed on git 2.43; only `--write-tree` prints `CONFLICT (content): Merge conflict in <path>`). So every real conflict returns `()`: the ledger union never fires, a conflict outside the ledger is never escalated with its paths, and the heal falls through to the local-merge fallback, which refuses the conflicted merge. Nothing lands wrongly; the heal simply never acts.

**Approach:** `merge_tree_conflict_paths` runs `git merge-tree --write-tree --name-only -z --no-messages <base> <branch>` (git computes the merge base itself, as `merge_tree_write` already does). Exit 0 is a clean merge: return `()`. Exit 1 whose first NUL-separated field is a tree oid is a conflicted merge: return the remaining non-empty fields, sorted and de-duplicated — git's own conflicted-file list, so modify/delete and add/add conflicts are included, not only content conflicts. A conflicted merge that names no file, and any other outcome — an unknown ref also exits 1, with empty stdout — raises `VcsCommandError`, never an empty list. `dispatch_land_heal.py` and the pure classifiers in `core/dispatch_landing.py` do not change. The port docstring states the contract.

Ledger key: `58-1-merge-tree-conflict-paths-reads-gits-own-conflicted-file-list`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-268 (FR-214); Story 28.20 (`spec-marshal-drain-self-resolution` CAP-3, folded into `spec-pyforge-marshal`).

## Acceptance Criteria

- Given a real repository where `main` and a branch both edit two files When `merge_tree_conflict_paths(repo, "main", branch)` runs Then it returns both paths, sorted
- Given one side deletes a file the other modifies When it runs Then that path is returned too
- Given a clean merge When it runs Then it returns `()`
- Given an unknown branch When it runs Then it raises `VcsCommandError`
- Given a conflicted merge that names no file (a directory-rename split) When it runs Then it raises `VcsCommandError`
- Given a real conflict outside the sprint ledger When `try_heal_dispatch_land_merge` runs with the real `GitVcs` Then it returns `healed=False` with that path in `escalated_paths`, before touching the forge

## Boundaries & Constraints

**Always:** the heal's decisions are unchanged — only what it sees; a merge-tree failure is an error, never an empty list.

**Never:**
- Do not change `dispatch_land_heal.py`'s orchestration or `core/dispatch_landing.py`'s classifiers.
- Do not let a conflicted merge land.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| content conflicts | both sides edit `a.txt` and `b c.txt` | `("a.txt", "b c.txt")` — a space in a name survives (`-z`) | — |
| modify/delete | one side deletes `d.txt`, the other edits it | `"d.txt"` included | — |
| clean merge | disjoint edits | `()` | — |
| unknown ref | branch does not exist | — | `VcsCommandError` naming the command |
| add/add | both sides add `e.txt` | `"e.txt"` included | — |
| no-file conflict | a directory-rename split | — | `VcsCommandError` ("names no file") |
| ledger-only conflict, same row | both sides change one row's status | its path — the union heal clears it and retries | unchanged heal behaviour |
| ledger-only conflict, adjacent rows | both sides add a row next to each other | its path — the union commit is pushed but the merge still conflicts; MRS-DISP-020 as before | a follow-up story |
| other conflict | `README.md` conflicts | the heal escalates `("README.md",)` | unchanged heal behaviour |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-268 (FR-214).
Dream: `docs/dreams/pyforge-marshal.md` § Realization log → *2026-09-27 (evening) — Proposed: the landing heal sees the conflicts it was built to heal*.
Ledger key: `58-1-merge-tree-conflict-paths-reads-gits-own-conflicted-file-list`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

### Review 1 — 2026-09-27, independent adversarial reviewer, working tree on `merge-tree-conflict-paths` — PASS with lows

Verified clean: the `-z --name-only --no-messages` format lists each conflicted path once across content, add/add, binary, modify/delete, rename/delete, rename/rename, directory/file, submodule-gitlink, non-ASCII and newline-bearing names; `--no-messages` keeps the messages section out of the list; an unknown ref (exit 1, no stdout) and unrelated histories (exit 128) raise, and the heal turns that into a refusal; SHA-256 oids match; git 2.43 has every flag; no heal path lands a conflicted merge; three of the new tests fail against the old implementation.

- `[medium]` `[→ follow-up story]` **The union heal, now reachable, does not clear the common ledger conflict.** Probe (bare remote, clone, dispatch worktree, real `GitVcs`): when both sides add adjacent rows, the heal writes the union, commits it as an ordinary single-parent commit, pushes it to the PR branch and retries — the three-way merge still conflicts and the landing reports MRS-DISP-020 without naming the ledger. A same-row status conflict does heal. Before this story the heal never pushed. **Decision:** narrow CAP-268 / FR-214 / this spec to what holds, and fix the union in a follow-up story on its own epic (a two-parent merge of the base with the ledger resolved by union), implemented next. No landing is exposed meanwhile: both fleet drains are stopped (2026-09-25) and a conflicted merge still never lands.
- `[low]` `[patch]` **A conflict that names no file read as clean.** git's manual: "Do NOT interpret an empty Conflicted file info list as a clean merge" — a directory-rename split exits 1 with only a tree. **Fix:** raise `VcsCommandError` ("names no file"); `test_merge_tree_conflict_paths_refuses_a_conflict_that_names_no_file`.
- `[low]` `[→ follow-up story]` **The heal probes local `main`, not `refs/remotes/origin/main`** (`dispatch_land.py` passes `_MERGE_BASE="main"`) — harmless while every conflict read as clean; now the paths and the union's `main_text` can come from a stale local `main`. Reasoning only, no stale-main repro.
- `[nit]` `[patch]` `merge_tree_write`'s docstring still described the old sibling; rewritten.
- `[nit]` `[patch]` add/add was claimed, not tested — added to `_conflicting_branch`.
- `[nit]` `[→ follow-up story]` Another project's sprint ledger is classed as mechanical (`is_mechanical_conflict_path` matches the basename), so its conflict is neither healed nor escalated. A directory/file conflict is reported under git's renamed-away name (`dir~branch`) — an escalation still names it; noted.
