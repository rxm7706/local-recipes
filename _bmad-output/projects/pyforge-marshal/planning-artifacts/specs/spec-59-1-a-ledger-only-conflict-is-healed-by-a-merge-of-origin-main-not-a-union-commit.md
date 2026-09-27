---
title: '59.1: A ledger-only conflict is healed by a merge of `origin/main`, not a union commit'
type: 'fix'
created: '2026-09-27'
status: 'done'
review_loop_iteration: 2
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - docs/dreams/pyforge-marshal.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 58.1 made merge conflicts visible to the landing heal (Story 28.20), which made its ledger-union branch reachable for the first time, and Story 58.1's review found three faults in it:
- **The union is a single-parent commit, so it rarely clears the conflict.** `_try_ledger_union_heal` writes the union of `main`'s and the branch's ledger maps into the dispatch worktree, commits it as an ordinary single-parent commit, pushes it to the PR branch and retries the forge merge. Git's three-way merge still sees both sides changing the same lines. A same-row status conflict clears. The common case does not: two landings each add a story row next to each other. The landing then fails MRS-DISP-020, with a useless commit already pushed.
- **The probe reads local `main`.** The heal checks `main`, not `origin/main`, although GitHub merges against `origin/main` and `dispatch land` has just fetched it.
- **Every project's ledger counts as mechanical.** Any path ending `sprint-status-ledger.yaml` passes, so a conflict in another project's ledger is neither healed nor escalated.

**Approach:**
- **Probe `origin/main`.** `dispatch land` fetches `origin/main` when the forge merge fails, then calls the heal with a new `probe_ref="refs/remotes/origin/main"`, the full refname. The heal uses `probe_ref` for `merge_tree_conflict_paths` and for the union's base text. `base` keeps its one other job: `_try_local_main_advance` still merges into and pushes the local `main`, unchanged.
- **A new port method.** `VcsPort.merge_ref_resolving(worktree_path, ref, *, resolutions, message) -> str` (additive), implemented by `GitVcs`:
  1. Refuse a merge already in progress; run `git merge --no-ff --no-commit <ref's commit>` in the worktree, inside the abort guard, and require `MERGE_HEAD` to be that commit.
  2. Read the conflicted paths from `git diff --name-only --diff-filter=U -z`.
  3. If any conflicted path is not a key of `resolutions`, run `git merge --abort` and raise `VcsCommandError`.
  4. Otherwise write each resolution's text, `git add -- <path>`, and `git commit -m <message>`. The result is a two-parent merge commit.
  5. Return the new HEAD sha.
  6. Any failure or interrupt after the merge started aborts it before raising.
- **Build the union text purely.** A new pure `core/chain_regen.render_ledger_statuses(template_text, statuses) -> str` produces the template's header plus a sorted `development_status:` body, which is the generator's own layout. `write_ledger_statuses` now uses it, with unchanged behaviour. The heal resolves the ledger three-way against the merge base (`core/dispatch_landing.three_way_ledger_statuses`: a row only one side changed takes that side, deletions hold, precedence settles only a row both sides changed, where `done` never regresses and `blocked` beats every other status), renders it under `origin/main`'s header (the branch's when `origin/main` has no ledger) and passes it as the resolution of `sprint_ledger_rel_path(project_slug)`. Once that merge is committed, a refused retry or a rejected push ends the attempt `healed=False` — never the local-`main` advance.
- **Mechanical means this project's ledger only.** `is_mechanical_conflict_path` and `unknown_conflict_paths` take an optional `ledger_rel`. When it is given, only that exact path is mechanical, and the heal always passes it.

Ledger key: `59-1-a-ledger-only-conflict-is-healed-by-a-merge-of-origin-main-not-a-union-commit`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: fix / M / 58.1.

### Living CAP citations

- `spec-pyforge-marshal` CAP-269 (FR-215); Story 28.20 (`spec-marshal-drain-self-resolution` CAP-3, folded into `spec-pyforge-marshal`); CAP-268 (58.1).

## Acceptance Criteria

All of these run against a bare remote, the real `GitVcs`, and a forge fake that merges only when a real `git merge-tree --write-tree origin/main origin/<head>` is clean.

- Given `main` and the dispatch branch each added a ledger row next to each other When the heal runs Then the pushed head is a merge commit whose second parent is `origin/main`, its ledger holds both rows, the forge merge is retried once and succeeds, and the result is `healed=True, retried_forge_merge=True`
- Given both sides changed one row's status When the heal runs Then it heals, and the row holds the precedence winner
- Given the ledger and `README.md` both conflict When the heal runs Then it returns `escalated_paths=("README.md",)`, and nothing is committed, pushed or merged
- Given only another project's ledger conflicts When the heal runs Then that path is escalated by name, and nothing is pushed
- Given a worktree When `merge_ref_resolving` meets a conflicted path it has no resolution for Then the merge is aborted, the worktree is clean at its previous HEAD, and `VcsCommandError` is raised
- Given the union merge is pushed but the forge refuses the retry, or the push is rejected When the heal ends Then remote `main` is untouched and the PR is open (`healed=False`)
- Given `main` flipped a row the branch never touched to `blocked`, and retired another When the heal resolves the ledger Then the flip and the retirement survive
- Given a merge already in progress in the worktree When `merge_ref_resolving` runs Then it refuses and leaves that merge as it was

## Boundaries & Constraints

**Always:**
- A conflicted merge never lands. Only the landing project's own ledger is ever resolved mechanically.
- A merge is committed only when every conflicted path has a resolution.

**Never:**
- Do not change `_try_local_main_advance`.
- Do not force-push anything.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.
- Do not start a commit subject with `Story N.M:`, or with anything a landing-evidence parser reads as `Merge … into main`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| adjacent rows | each side adds a row | two-parent merge pushed; union ledger; retry succeeds | push or forge failure → `healed=False`, as before |
| same row | `backlog` vs `done` | union holds `done`; heals | — |
| ledger + other | `README.md` conflicts too | `escalated_paths=("README.md",)`; no commit, no push | — |
| foreign ledger | only another project's ledger | escalated by name | — |
| unresolvable conflict in `merge_ref_resolving` | a conflicted path without a resolution | `git merge --abort`; HEAD and tree unchanged | `VcsCommandError` |
| fetch fails | no network | the whole heal skipped, the local-`main` advance included (fail closed) | MRS-DISP-020 naming the skipped heal |
| retry refused after the union merge | a red required check | `healed=False`; `main` untouched; PR open | MRS-DISP-020; the next attempt reads a fresh state |
| push rejected | someone pushed to the PR branch | `healed=False`; `main` untouched; the merge stays local | MRS-DISP-020 |
| main's own ledger change | `blocked` flip / retired row on `main` | kept (three-way against the merge base) | — |
| both sides re-status one row | `blocked` vs `done` | `done` (never regresses; `ledger-regression` would red) | — |
| both sides re-status one row | `blocked` vs `review` | `blocked` (never undone mechanically) | — |
| unwritable resolution | an `OSError` writing the ledger | merge aborted; `healed=False` | `VcsCommandError` |
| merge in progress | an operator's pending merge in the worktree | refused, left as it was | `VcsCommandError` |

**Known sibling, outside this story:** `dispatch_land.py`'s merge-preview gate counts behind with the short name `origin/main` (`_ORIGIN_MAIN`). A local branch or tag of that name would shadow it, the same trap Story 57.1's review found in `refresh`.

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-269 (FR-215).
Dream: `docs/dreams/pyforge-marshal.md` § Realization log → *2026-09-27 (evening)* → *Follow-up, same evening (Story 58.1 review)*.
Ledger key: `59-1-a-ledger-only-conflict-is-healed-by-a-merge-of-origin-main-not-a-union-commit`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

### Review 1 — 2026-09-27, independent adversarial reviewer, working tree on `ledger-union-heal-merges-base` — FAIL (1 high, 3 medium)

Verified clean: `merge_ref_resolving` over a conflict plus clean changes elsewhere, an unconflicted resolution key (ignored), modify/delete both ways, add/add, unstaged unrelated changes, staged/dirty/untracked refusals, refusing hooks (aborted, HEAD unchanged), per-worktree MERGE_HEAD, already-merged and fast-forwardable refs, spaced/unicode paths; adjacent/same-row/ledger-plus-other/foreign-ledger heals when the retry succeeds; the commit subject matches no landing-evidence shape; `dispatch_land` is the heal's only caller; the adjacent-row and foreign-ledger tests fail on the old code.

- `[high]` `[patch]` **After the union merge was pushed, a failure fell through to the local-`main` advance.** The branch then probed clean while `merge_state` was the stale pre-heal read, so the heal merged into local `main`, pushed it and closed the PR — past a refused forge retry (probe A) or a rejected push that dropped another person's commit (probe F); `main` is unprotected. **Fix:** the union heal is the whole answer for the attempt — `healed=False` on any failure after it, never the fall-through; the #985 advance still runs on the next attempt with a fresh state. `test_real_heal_never_lands_on_main_when_the_retried_forge_merge_is_refused`, `..._when_its_push_is_rejected`; the fake-based fall-through test now asserts the opposite.
- `[medium]` `[patch]` **`lint-types` red** (`ruff format` on `vcs_git.py`). **Fix:** formatted.
- `[medium]` `[patch]` **`merge_ref_resolving` treated any MERGE_HEAD as its own** — an operator's pending merge was aborted (work lost), or a leftover merge of another ref was committed under the heal's message and pushed. **Fix:** refuse a merge already in progress; merge the ref's resolved commit and require MERGE_HEAD to equal it; `test_merge_ref_resolving_refuses_and_leaves_a_merge_already_in_progress`.
- `[medium]` `[patch]` **The union ignored the merge base** — `main`'s `blocked` flip came back as `backlog` (blocked ranks lowest) and a retired row was resurrected. **Fix:** `three_way_ledger_statuses`; `blocked` never loses a both-changed row; `test_real_heal_keeps_mains_own_changes_to_rows_the_branch_never_touched` and two pure tests.
- `[low]` `[patch]` The `git merge` and the MERGE_HEAD probe ran outside the abort guard — now inside it (an interrupt mid-merge aborts; no pre-existing merge can be mistaken for ours).
- `[low]` `[patch]` A failed fetch left no trace — MRS-DISP-020 now says the heal was skipped and why.
- `[nit]` `[patch]` An absent `origin/main` ledger dropped the GENERATED header — the branch's header is used. `[nit]` `[patch]` Story 59.1's Surface list omitted `test_dispatch_landing.py`. `[nit]` `[note]` The union keeps `origin/main`'s `# stories: N` comment (the next `sprint-ledger-sync` regenerates it); `_ORIGIN_MAIN_REF` is a private constant in two modules; the new real-git tests follow the file's existing convention of not isolating global git config.
- `[note]` After a rejected push the heal's merge commit stays on the local branch only (nothing pushed); the next landing attempt starts from it.

### Review 2 — 2026-09-27, independent adversarial reviewer, commit `18af4505fb` — PASS with lows

Verified closed by re-running review 1's probes: the fall-through (a refused retry, a rejected push and a `resolve_ref` failure all end `healed=False`, remote `main` untouched, the PR open); a union failing before its commit leaves a clean worktree and no local advance, and the next attempt's own push rejects a diverged local merge (MRS-DISP-017); the #985 advance still runs for a branch clean against `origin/main` while GitHub says DIRTY; `main`'s `blocked` flip and retired row survive; a stale MERGE_HEAD is refused and left. Parse/render round-trips all 8 tracked ledgers byte-for-byte. Tags, annotated tags and `-`-leading refs are handled; `heal_skipped` is set on every path; nothing parses the MRS-DISP-020 text.

- `[low]` `[patch]` **`blocked` beat `done` in a both-changed row**, un-finishing a `main` row — doctor's `ledger-regression` (`detectors-ci`) fails it, and `promote_sprint_status` ranks `done` strictly senior to `blocked`. **Fix:** `done` > `blocked` > precedence; the pure test's case `c` now asserts `done`, and case `e` pins `blocked` over a non-`done` status.
- `[low]` `[patch]` **An `OSError` writing the resolution escaped raw** and would crash `dispatch land`. **Fix:** wrapped as `VcsCommandError` (the merge is aborted); `test_merge_ref_resolving_reports_an_unwritable_resolution_as_a_vcs_error_and_aborts`.
- `[low]` `[patch]` **The guard aborted a foreign merge** started in the window after the pre-check. **Fix:** abort only when MERGE_HEAD is the ref's own commit.
- `[low]` `[patch]` FR-215 and Story 59.1's I-want line still said "resolved by union"; FR-215 omitted the no-fall-through rule. **Fix:** both amended.
- `[nit]` `[patch]` With `rerere.enabled` + `rerere.autoupdate` a recorded resolution staged itself past `resolutions`. **Fix:** `--no-rerere-autoupdate`.
- `[nit]` `[patch]` "landing refused as before" for a failed fetch was inexact: the #985 advance is skipped too (fail closed). **Fix:** the I/O row says so.
