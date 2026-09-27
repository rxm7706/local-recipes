---
title: '61.1: Every local-branch read names the full ref'
type: 'fix'
created: '2026-09-27'
status: 'done'
review_loop_iteration: 3
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
- marshal's repo-root scripts (found by reviews 1 and 3): `scripts/fleet_scan.py`'s landing history and `scripts/bmad-loop-worktree`'s branch check and mint (both on this Spec's surface), and the operator tooling marshal runs, allowlisted rather than governed (`scripts/spec_surface_allowlist.txt`): `scripts/fleet_picture.py`'s fetch and behind-count, `scripts/unpushed_work_check.py`'s branch listing, reads and remedy, `scripts/worktree_sweep.py`'s merged checks (its interim home until it folds into `marshal retire`).

And `core/policy._valid_landing_base_branch` accepts any non-empty string, so `landing_base_branch = "origin/main"` would reach every read above.

**Approach:** `core/refs.py` gains `local_branch_ref(branch) -> "refs/heads/<branch>"`. Every call site above wraps the branch it reads in it, at the call — the branch *name* stays a name wherever it is also used as one (`merge_branch(into=)`, `resolve_ref`, `is_branch_merged`, the forge's PR base, messages). `GitVcs.push` names both sides `refs/heads/<branch>`; `<branch>@{upstream}` stays bare (the full form fails there). The scripts spell `refs/heads/<branch>` (or `HEAD`) themselves. `_valid_landing_base_branch` refuses a full refname, a ref namespace (`heads/`, `tags/`, `remotes/`), a remote's branch (`origin/…`), and any value git's branch-name rules refuse; `land` and `batch-pr` refuse to run on a refused value (MRS-LAND-002 / MRS-DEPLOY-015, widened from `landing_rules`) rather than fall back to `main`. A meta test classifies every `str` parameter of every `VcsPort` method and flags a bare local branch name reaching a revision argument, or a full ref reaching a name-taking one.

Ledger key: `61-1-every-local-branch-read-names-the-full-ref`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-271 (FR-217); CAP-270 (60.1).

## Acceptance Criteria

- Given a tag named `main` on an older commit than the branch `main` When status, deploy, retire or dispatch land read the landing subjects Then they read the branch's history
- Given the same tag When deploy or land compute the merge base, the wave range and the changed-files base Then each reads the branch
- Given the same tag When init or the loop-home adapter mints a branch from `main` Then the new branch starts at the branch's tip (today: the mint refuses as ambiguous)
- Given a tag named like the dispatch branch When the landing heal probes, reads and merges the dispatch branch Then it reads the branch, and the local-`main` advance's push succeeds with a tag named `main` present, locally or on the remote
- Given a tag named `main` on the remote When marshal fetches `main` (the behind-count, the heal, the ledger publish, land, refresh, `fleet_picture`) Then `refs/remotes/origin/main` moves to the remote's branch, and the publish lands
- Given the same tag, or a stray tag `main` on a feature commit When `fleet_scan`, `bmad-loop-worktree`, `fleet_picture`, `unpushed_work_check` and `worktree_sweep` read `main` or a branch Then each reads the branch (the sweep never reads the feature as merged)
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
| fetch with a tag `main` on the remote | remote's `main` moved on | `refs/remotes/origin/main` updated (source `refs/heads/main`) | a missing branch fails as before |
| push beside a local `origin/<b>` shadow | upstream configured | upstream read by full name; push succeeds | — |
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

- `[medium]` `[patch]` **Marshal's repo-root scripts still read local branches by short name** — `scripts/fleet_scan.py` (landing history: landed stories dropped out), `scripts/bmad-loop-worktree` (a same-named tag attached the home detached; the mint from `main` refused), `scripts/fleet_picture.py` (the primary checkout counted behind), `scripts/unpushed_work_check.py` (`refname:short` printed `heads/<b>`, so a pushed branch read as absent). Two are on this Spec's surface; two are allowlisted operator tooling marshal runs (corrected by review 3). **Fix:** full refs (`HEAD` in `fleet_picture`), `refname:lstrip=2`; `tests/scripts/test_local_branch_full_ref_scripts.py` — all six cases fail on the old scripts.
- `[medium]` `[patch]` **A refused `landing_base_branch` silently retargeted `main`** — `batch-pr` opened and `land` merged against the default with only an MRS-POLICY-002 ERROR. **Fix:** both hard-refuse, as for a malformed `landing_rules` (MRS-DEPLOY-015 / MRS-LAND-002 widened); AC amended; tests for both. `retire` keeps its fallback: it only deletes a branch proven merged into what it read, so a `main` fallback can make it refuse, never lose work.
- `[medium]` `[patch]` **`spec-surface-check` red** — reconcile events on both Specs and scoped stamps, at landing.
- `[low]` `[patch]` **The push destination was bare** — a same-named tag on the remote made it ambiguous. **Fix:** `refs/heads/<branch>:refs/heads/<remote_branch>`; a test with and without an upstream.
- `[low]` `[patch]` **The meta test had no completeness guard** — it now classifies every `str` parameter of every `VcsPort` method (`worktree_unified_patch`, `fetch`, `commit_paths_onto_remote_tip` added).
- `[low]` `[patch]` **The scan missed spellings** — it now renders f-strings, `+`, `%`, `format`, `join` and conditionals, resolves function-local and imported literal bindings, spares a hand-built `refs/heads/…`, and flags a `*_ref` name or `refs/` template reaching a name-taking parameter; the self-test pins each. Not scanned, by design: direct git argv outside the adapter (AD-4), method aliases, `functools.partial`.
- `[low]` `[note]` Four call sites (`cli/gate`, `cli/adapters`, `dispatch_land`, `dispatch_supervisor`) are pinned by the meta test alone, not by a fake — accepted: the meta test's literal/constant rule catches each.
- `[nit]` `[patch]` The chain said `dispatch` mints from local `main` (it mints from `refs/remotes/origin/main` since 60.1) — corrected in this spec, CAP-271, the Dream entry. The validator refuses ref namespaces (`heads/`, `tags/`, `remotes/`) and judges only an ASCII space; `schemas/policy.json` describes the rule. `epics.md` counts bumped; the DW entry closes at landing.

### Review 2 — 2026-09-27, independent adversarial reviewer, commits through `eacafa23d5` — FAIL (1 medium, 4 low)

Verified clean: all six script cases fail on the `origin/main` scripts and pass on HEAD; the `land` / `batch-pr` refusal fires only on ERROR findings, before any forge call, and nothing outside the tests parses MRS-DEPLOY-015 / MRS-LAND-002 text; `bmad-loop-worktree`'s mint from `refs/heads/main` writes the same branch config under every `autoSetupMerge`, steward only locates the script, seed copies it with no byte pin; `fleet_picture` from `HEAD` equals the branch (detached is skipped first); `lstrip=2` is right for nested names and now matches `cli/status.py`'s `by_ref`; a push to a non-`origin` upstream with a different remote-side name works; the validator matches git plus the documented refusals; the meta guard fails on a new `str` port parameter; marshal 8823, steward 1745, scripts green.

- `[medium]` `[patch]` **`fetch` named the remote's branch by short name** — a tag `main` on the remote made the fetch of `main` land the tag in `FETCH_HEAD` only, exit 0, and leave `refs/remotes/origin/main` stale: a false 0-behind that skipped the MRS-DISP-044 merge preview, the heal probing an old tip, every ledger / blocked-twin / deferred-work publish rejected as non-fast-forward, `land`'s and `refresh`'s fast-forward short, `fleet_picture` under-reporting. **Fix:** `GitVcs.fetch` names `refs/heads/<ref>` itself (the parameter stays a name, like `resolve_ref`'s); `fleet_picture` fetches `refs/heads/main`. Tests: the fetch, the publish, `fleet_picture` — each fails on the prior code.
- `[low]` `[patch]` **The unpushed-work remedy printed a bare `<b>` push**, which fails beside a same-named tag. **Fix:** `refs/heads/<b>:refs/heads/<b>` in the script and both fallback texts (`core/status.py`, `fleet_picture.py`); the script test asserts it.
- `[low]` `[patch]` **The meta scan missed a branch through one more name** (`ref = head_branch`, `_A = _B`, the pre-61.1 heal's `probe = … else base`) and skipped non-`str` parameter types. **Fix:** names are rendered through what is assigned to them (three deep) and through literal parameter defaults; every parameter whose type mentions `str` is classified. A new self-test pins the spellings.
- `[low]` `[patch]` **`push` parsed its upstream from `--abbrev-ref`**, which answers `remotes/origin/<b>` beside a local `origin/<b>` shadow (a push to a remote called `remotes`). Pre-existing and loud, but the rewritten docstring claimed otherwise. **Fix:** `--symbolic-full-name`, stripped of `refs/remotes/`; a test with the shadow.
- `[low]` `[note]` `spec-surface-check` red until the landing reconcile — done at landing.
- `[nit]` `[patch]` The refusal names what it would have fallen back to (a lower layer can hold a valid base) and matches the policy's `policy key '<key>'` wording; `core/findings.py`'s comment block and the Story's When clause (`retire`, fetch/push) updated.
- `[nit]` `[note]` Under an operator's `merge.log=true` the heal's local-advance merge body names `refs/heads/<b>`; the subject is unchanged and landing evidence reads subjects only — accepted. `fleet_scan.py`'s shipped-history read (`build_status`) has no direct test; the same one-line change is tested through `done_ids_from_git`.
- `[nit]` `[→ DW-marshal-doctor-route3-short-main-2026-09-27]` doctor's `sources/marshal.py` route 3 and `scripts/worktree_sweep.py` still read `main` bare (review 3 corrected "conservative only": a stray tag on a feature commit made the sweep delete that feature; the sweep is fixed in this story, doctor's route stays a deferred-work row).

### Review 3 — 2026-09-27, independent adversarial reviewer, `eacafa23d5..059c1c7ba2` and the whole story — PASS with lows (4 low, 1 nit)

Verified clean: `GitVcs.fetch` from `refs/heads/<ref>` updates `refs/remotes/<remote>/<ref>` exactly as the short form did under the default refspec, a single-branch clone, a slash branch, a narrowed or non-pattern refspec and a URL remote; a missing branch still exits 128 and nobody parses its text; all nine fetch callers and the three publish callers pass branch names; nothing parses the old remedy text; the refusal helpers match both MRS-POLICY-002 wordings; the meta test terminates on cycles and its "type mentions str" guard is sound for today's port; every revision call site names `refs/heads/…`, `refs/remotes/…`, `HEAD` or a sha; the review-2 tests fail on `eacafa23d5` and pass now; marshal 8827, scripts 778, CFE 20.

- `[low]` `[patch]` **The review-2 meta rendering missed spellings the review-1 scan caught** — once a name was reassigned (`base = base or "main"` — `cli/refresh.py`'s own idiom — `head_branch = head_branch.strip()`, `branch = str(args.branch)`, `into = cfg["into"]`), only the assignment was rendered and the name rule dropped; and bindings were module-wide, so one function's `ref = "main"` flagged another's `ref="HEAD"`. **Fix:** a branch-like name stays a branch whatever it was reassigned; `or`/`and` render as their operands; bindings are the module's plus the enclosing functions'. A new self-test pins the six spellings and both false positives.
- `[low]` `[patch]` **`push` refused an upstream whose fetch refspec maps outside `refs/remotes/`** (`+refs/heads/*:refs/origin/*`), which `--abbrev-ref` had pushed — a no-tag behaviour change. **Fix:** the target comes from the branch config (`%(upstream:remotename)` / `%(upstream:remoteref)`), refusing remote `.`; a remote named `foo/bar` is no longer split at its slash. Tests for both layouts (each fails on the review-2 adapter).
- `[low]` `[patch]` **The deferral reason was wrong for a tag AHEAD of the branch** — a stray `git tag main` on a feature commit made `scripts/worktree_sweep.py` read the feature as merged, remove its worktree and delete its branch. **Fix:** the sweep reads `refs/heads/main` (and lists branches with `refname:lstrip=2`); a test with the stray tag (fails on the old script). Doctor's route 3 stays deferred, the row renamed `DW-marshal-doctor-route3-short-main-2026-09-27` with the corrected risk (advisory).
- `[low]` `[patch]` **The port docstrings of `push` and `fetch` were stale** — both now say they take a branch NAME the adapter qualifies; `fetch`'s error names the ref it ran.
- `[nit]` `[patch]` Only `fleet_scan.py` and `bmad-loop-worktree` are on this Spec's surface; `fleet_picture.py`, `unpushed_work_check.py` and `worktree_sweep.py` are allowlisted operator tooling marshal runs — corrected here, in the review-1 line, the Dream, FR-217 and the memlog. The Story's Surface names `core/status.py`, `fetch` and `worktree_sweep.py`; the closed DW says three reviews.
