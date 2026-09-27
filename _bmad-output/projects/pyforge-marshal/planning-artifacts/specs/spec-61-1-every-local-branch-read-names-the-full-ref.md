---
title: '61.1: Every local-branch read names the full ref'
type: 'fix'
created: '2026-09-27'
status: 'in-progress'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - docs/dreams/pyforge-marshal.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-60-1-every-remote-tracking-read-names-the-full-ref.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** git resolves a short name through `refs/<n>`, `refs/tags/<n>`, `refs/heads/<n>` in that order, so a tag named `main` stands in for the local branch `main`. A probe on 2026-09-27 showed what that does to marshal's reads: `log main`, `show main:<path>` and `merge main` read the tag's commit with only a warning on stderr; `push origin main:main` and `worktree add -b <b> <path> main` refuse as ambiguous. Story 60.1 closed this for remote-tracking refs. Marshal still hands git its local branches by short name in:
- the landing subjects `status`, `deploy` (merge route and `batch-pr`), `retire` and `dispatch land` read (`commit_subjects(root, "main")` and the policy's base);
- `deploy land-story`'s `--since` default (`merge_base(branch, "main")`);
- `deploy batch-pr`'s and `land`'s merge base, wave range (`<sha>..<head_branch>`), base subjects and changed-files base;
- the gate's `--scope-check` diff base;
- the start point `init` and the loop-home adapter mint a branch from (`add_worktree(base="main")`) — `dispatch` mints from `refs/remotes/origin/main` since 60.1;
- the dispatch supervisor's landing subjects;
- the stage-push supervisor's retired-branch check, `merge_base(commit, <station branch>)`;
- the landing heal: its probe default (the local base), and its reads of the dispatch branch — the merge-tree probe, the merge base, the ledger text, and the local-`main` advance's merge;
- `GitVcs.push`'s refspec;
- marshal's repo-root scripts (on this Spec's surface, found by review 1): `scripts/fleet_scan.py`'s landing history, `scripts/bmad-loop-worktree`'s branch check and mint, `scripts/fleet_picture.py`'s behind-count, `scripts/unpushed_work_check.py`'s branch listing and reads.

And `core/policy._valid_landing_base_branch` accepts any non-empty string, so `landing_base_branch = "origin/main"` would reach every read above.

**Approach:** `core/refs.py` gains `local_branch_ref(branch) -> "refs/heads/<branch>"`. Every call site above wraps the branch it reads in it, at the call — the branch *name* stays a name wherever it is also used as one (`merge_branch(into=)`, `resolve_ref`, `is_branch_merged`, the forge's PR base, messages). `GitVcs.push` names both sides `refs/heads/<branch>`; `<branch>@{upstream}` stays bare (the full form fails there). The scripts spell `refs/heads/<branch>` (or `HEAD`) themselves. `_valid_landing_base_branch` refuses a full refname, a ref namespace (`heads/`, `tags/`, `remotes/`), a remote's branch (`origin/…`), and any value git's branch-name rules refuse; `land` and `batch-pr` refuse to run on a refused value (MRS-LAND-002 / MRS-DEPLOY-015, widened from `landing_rules`) rather than fall back to `main`. A meta test classifies every `str` parameter of every `VcsPort` method and flags a bare local branch name reaching a revision argument, or a full ref reaching a name-taking one.

Ledger key: `61-1-every-local-branch-read-names-the-full-ref`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-271 (FR-217); CAP-270 (60.1).

## Acceptance Criteria

- Given a tag named `main` on an older commit than the branch `main` When status, deploy, retire or dispatch land read the landing subjects Then they read the branch's history
- Given the same tag When deploy or land compute the merge base, the wave range and the changed-files base Then each reads the branch
- Given the same tag When init or the loop-home adapter mints a branch from `main` Then the new branch starts at the branch's tip (today: the mint refuses as ambiguous)
- Given a tag named like the dispatch branch When the landing heal probes, reads and merges the dispatch branch Then it reads the branch, and the local-`main` advance's push succeeds with a tag named `main` present, locally or on the remote
- Given the same tag When `fleet_scan`, `bmad-loop-worktree`, `fleet_picture` and `unpushed_work_check` read `main` or a branch Then each reads the branch
- Given `landing_base_branch = "origin/main"`, `"refs/heads/main"`, `"heads/main"` or `"bad..name"` When the policy composes Then the value is refused with MRS-POLICY-002, and `land` / `batch-pr` refuse to run on it (never fall back to `main`); `"release/2026"` is accepted
- Given the package source When scanned Then no revision argument of a `VcsPort` read receives a bare local branch name (a meta test, every known spelling in its self-test)
- Given no tag shadowing a branch When any of these runs Then its behaviour is unchanged

## Boundaries & Constraints

**Always:** the helper lives in `core/refs.py`; the wrap is at the read, so a name used as a name elsewhere stays one; `core/` stays pure (AD-4).

**Ask First:** widening scope to another station's scripts.

**Never:**
- Do not qualify an argument git reads as a branch name: `branch -D`, attaching an existing branch to a worktree (`add_worktree`'s attach path is bare on purpose), `<branch>@{upstream}`.
- Do not change what is fetched, pushed or merged when no tag shadows a branch.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| no shadow | ordinary repo | identical results | — |
| tag `main` on an older commit | branch `main` ahead | every read uses the branch | — |
| tag named like a dispatch branch | heal probe and merge | reads and merges the branch | — |
| push with tag `main` present | local-main advance | push succeeds (`refs/heads/main:refs/heads/main`) | a rejected push fails as before |
| push with a same-named tag on the remote | with or without an upstream | push succeeds; the remote tag untouched | — |
| `landing_base_branch = "origin/main"` | project policy | MRS-POLICY-002; `land` / `batch-pr` refuse (MRS-LAND-002 / MRS-DEPLOY-015) | — |
| `landing_base_branch = "release/2026"` | project policy | accepted; reads `refs/heads/release/2026` | a missing branch fails as before |
| `deploy land-story --since <rev>` | operator-typed revision | passed through untouched | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-271 (FR-217).
Dream: `docs/dreams/pyforge-marshal.md` § Realization log → *2026-09-27 (late) — Proposed: marshal names its own branches too, never a name a tag can wear*.
Deferred-work: closes `DW-marshal-local-branch-short-names-2026-09-27`.
Ledger key: `61-1-every-local-branch-read-names-the-full-ref`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

### Review 1 — 2026-09-27, independent adversarial reviewer, commit `c9b543e69f` — FAIL (3 medium, 3 low)

Verified clean: every call site of all 30 `VcsPort` methods — local-branch revision positions wrapped, name positions bare, nothing builds `refs/heads/refs/heads/…`; the direct git shell-outs outside the adapter carry no branch names; no-tag behaviour unchanged (same commits read, diffed, merged, pushed; `merge_branch` passes `-m`; no ref reaches a journal); `<branch>@{upstream}` works bare beside a same-named tag; the validator matches `git check-ref-format --branch` on 54 names; `init`'s `base` → `main_sha` rename is neutral; suites and planning detectors green.

- `[medium]` `[patch]` **Marshal's repo-root scripts still read local branches by short name** — `scripts/fleet_scan.py` (landing history: landed stories dropped out), `scripts/bmad-loop-worktree` (a same-named tag attached the home detached; the mint from `main` refused), `scripts/fleet_picture.py` (the primary checkout counted behind), `scripts/unpushed_work_check.py` (`refname:short` printed `heads/<b>`, so a pushed branch read as absent). All four are on this Spec's surface. **Fix:** full refs (`HEAD` in `fleet_picture`), `refname:lstrip=2`; `tests/scripts/test_local_branch_full_ref_scripts.py` — all six cases fail on the old scripts.
- `[medium]` `[patch]` **A refused `landing_base_branch` silently retargeted `main`** — `batch-pr` opened and `land` merged against the default with only an MRS-POLICY-002 ERROR. **Fix:** both hard-refuse, as for a malformed `landing_rules` (MRS-DEPLOY-015 / MRS-LAND-002 widened); AC amended; tests for both. `retire` keeps its fallback: it only deletes a branch proven merged into what it read, so a `main` fallback can make it refuse, never lose work.
- `[medium]` `[patch]` **`spec-surface-check` red** — reconcile events on both Specs and scoped stamps, at landing.
- `[low]` `[patch]` **The push destination was bare** — a same-named tag on the remote made it ambiguous. **Fix:** `refs/heads/<branch>:refs/heads/<remote_branch>`; a test with and without an upstream.
- `[low]` `[patch]` **The meta test had no completeness guard** — it now classifies every `str` parameter of every `VcsPort` method (`worktree_unified_patch`, `fetch`, `commit_paths_onto_remote_tip` added).
- `[low]` `[patch]` **The scan missed spellings** — it now renders f-strings, `+`, `%`, `format`, `join` and conditionals, resolves function-local and imported literal bindings, spares a hand-built `refs/heads/…`, and flags a `*_ref` name or `refs/` template reaching a name-taking parameter; the self-test pins each. Not scanned, by design: direct git argv outside the adapter (AD-4), method aliases, `functools.partial`.
- `[low]` `[note]` Four call sites (`cli/gate`, `cli/adapters`, `dispatch_land`, `dispatch_supervisor`) are pinned by the meta test alone, not by a fake — accepted: the meta test's literal/constant rule catches each.
- `[nit]` `[patch]` The chain said `dispatch` mints from local `main` (it mints from `refs/remotes/origin/main` since 60.1) — corrected in this spec, CAP-271, the Dream entry. The validator refuses ref namespaces (`heads/`, `tags/`, `remotes/`) and judges only an ASCII space; `schemas/policy.json` describes the rule. `epics.md` counts bumped; the DW entry closes at landing.
