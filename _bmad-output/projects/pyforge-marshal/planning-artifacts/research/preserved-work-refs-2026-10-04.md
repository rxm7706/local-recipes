---
chain: pyforge-marshal
created: 2026-10-04
updated: 2026-10-04
status: draft
type: technical-research
title: "Preserved-work refs: inventory, root cause, and one standard"
companion: preserved-work-refs-2026-10-04-drafts.md
measured_at: "origin/main 33a7af0cb5 (2026-10-04), live `git ls-remote origin`, live GitHub ruleset and activity API"
---

# Preserved-work refs: inventory, root cause, and one standard

> **Operator ask (2026-10-04).** The repo keeps work under many ref names, made by different
> processes at different times. Standardize them correctly. Cover every execution mode: the
> bmad-loop engine, `marshal factory spin`, `marshal factory dispatch` on every harness,
> `marshal factory drain`, `bmad-build`, `bmad-build-auto` (bare and dispatched), and hand-driven
> sessions (`land/*` rebuilds, `steward workspace`, Claude Code and Cursor agent worktrees).
>
> **Status: research draft.** Nothing here is decided. No tracked file changed outside this folder.
> The Dream entry, Spec delta, AD amendment and stories are drafted in the companion
> `preserved-work-refs-2026-10-04-drafts.md`.

## 0. Verdict up front

1. **Names are not durability.** Every protection in the repo is keyed on a branch prefix:
   - `PROTECTED_BRANCH_PREFIXES` (`scripts/worktree_sweep.py:65`);
   - the GitHub ruleset `protected-refs-no-deletion`;
   - AD-47's structural exclusions;
   - the hook rule steward Story 85.1 is about to add.

   Whether work survives depends on two other facts: whether some ref still reaches the commit, and
   whether that ref exists on `origin`. Measured today, much of what the repo calls "preserved" is
   **local-only or unreachable**:
   - 16 of 17 `refs/attempt-preserve-dirty/*` refs hold commits that are on no `origin` ref.
   - 3 local-only tags (`archive/recover-scribe-1-3`, `archive/scribe-1-3-dangling-91d3571f`,
     `bmad-loop-preserve/5-9-intent-gap-2026-08-12`) hold commits that are on no `origin` ref.
   - 120 dispatch `failed/<story>/changes.patch` files sit in gitignored Tier-3 directories.
   - 98 branch tips deleted on 2026-10-04 are now reachable from no `origin` ref, no tag and no
     local branch.
2. **One namespace has two owners with opposite intents.** Upstream bmad-loop owns `attempt-preserve/*`
   as *bounded scratch*. At every run start it deletes all but the newest `scm.preserve_keep`
   (default 20) of these branches, and it says so: *"the prefix itself is owned by the pruner:
   anything parked under it, however it got there, is subject to deletion"*
   (`bmad_loop/verify.py:5805-5826`).

   This repo treats the same prefix as a *protected permanent record*. Marshal's intent-gap
   preserve (`supervisor/intent_gap_preserve.py:139`) and operators' hand-named branches
   (`attempt-preserve/47.1-dispatch-…`, `attempt-preserve/doctor-11-4-…`) put durable work under
   the pruner's prefix.
3. **Tags carry most of the preserved state, and they are unprotected server-side.**
   - The only ruleset targets branches. Its `refs/heads/rescue/**` and `refs/heads/recover/**`
     patterns match nothing that exists.
   - 698 `rescue/*` tags and 45 `archive/*` tags have no server protection.
   - 85.1's draft matcher does not cover tag deletion.
4. **Retirement has no defined path, so it destroys reachability.**
   - The 30 `attempt-preserve/*` branches retired on 2026-10-04 were deleted. 8 of their tips are
     now reachable from nothing.
   - The earlier "retire to `archive/`" moves produced local-only tags.
   - Spec CAP-11's "one archive strategy" (`archive/<original path>`) governs *files*. It says
     nothing about refs.
5. **The detector that asks "is any work only on this disk?" is blind.**
   - `scripts/unpushed_work_check.py:65-71` returns `""` whenever git exits non-zero.
   - `git fsck` here exits 1, because of two empty loose objects. So the dangling scan reports 0
     findings while 20,135 dangling commits exist.
   - 19,412 of those are marshal's own synthetic `"marshal teardown merged-check (not a real
     commit)"` objects (`adapters/vcs_git.py:490-512`).
6. **Three shipped rules contradict the new protection:**
   - `marshal land` deletes `loop/<slug>` on `origin` by default (`cli/land.py:438,507`;
     `core/policy.py:611`).
   - `marshal teardown` deletes it locally with `-D` (`cli/init.py:2682`).
   - Story 87.1's `--retire` deletes `attempt-preserve/*` on `origin`. Ruleset 24451573 forbids
     that, with no bypass.

**Recommendation (candidate B, § 7).** One rule for every mode:

> *Work outlives its working copy only as a commit reachable from an annotated tag under
> `refs/tags/preserve/` on `origin`.*
>
> - Nothing may remove a working copy whose unique content has no such tag. A working copy is a
>   branch, a worktree, a run directory or a patch file.
> - `preserve/` tags are append-only.
> - Retirement adds an annotated twin under `refs/tags/archive/<retired ref path>`, and never
>   removes reachability.
> - Deleting either namespace is a *purge*: an operator act, by explicit name, after a committed
>   manifest.
>
> Upstream names stay as they are. Marshal promotes them into `preserve/` at the moment they are
> written, and renders `preserve_keep = 0`.

---

## 1. Method and evidence base

All counts were measured on 2026-10-04 from the primary clone at `main = 33a7af0cb5`, with the
commands below. Nothing was pushed, deleted or rewritten.

| What | Command (abridged) | Result |
|---|---|---|
| Remote refs | `git ls-remote origin` | 2,590 lines. Excluding `refs/pull/*`: 19 heads, 749 tags (5 peeled entries are the annotated `checkpoint/*` tags) |
| Local refs | `git for-each-ref` | 878 refs: 29 heads, 752 tags, 78 remote-tracking, 17 `refs/attempt-preserve-dirty/*`, 1 `refs/backup/*`, 1 `refs/bundle/*` |
| Ruleset | `gh api repos/rxm7706/local-recipes/rulesets[/24451573]` | One ruleset, `target: branch`, rules `[deletion]`, include `refs/heads/{loop,attempt-preserve,recover,rescue}/**`, `bypass_actors: []`, created `2026-10-04T04:29:07-05:00` |
| `main` protection | `gh api …/branches/main/protection` | `404 Branch not protected`. No ruleset covers `main` either (`…/rules/branches/main` returns `[]`) |
| Repo merge settings | `gh api repos/rxm7706/local-recipes` | `delete_branch_on_merge: false`, `allow_squash_merge: false` |
| Incident | `gh api …/activity -f activity_type=branch_deletion -f time_period=day` | 494 deletion events on 2026-10-04, covering 464 unique branches |
| Dangling objects | `git fsck --no-reflogs` | 20,135 dangling commits; exit 1 (two empty loose objects); 46 s |
| Detectors (read-only runs) | `missing_preserve_check.py --json`; `bmad_loop_baseline_drift_check.py`; `unpushed_work_check.py --json` | exit 1 (1 finding); exit 0 (`loop-home runs=0, dispatch-runs=756`); exit 1 (8 unpushed branches, **0 dangling**) |
| Upstream contract | read `bmad_loop` 0.12.0 under `.pixi/envs/pyforge-guild/lib/python3.14/site-packages/bmad_loop/` | cited below as `BL/<file>:<line>` |

Two read-only subagent sweeps covered marshal code and the skills and docs. Every claim taken
from them was re-checked at its cited line before use here. Path abbreviations:
- `M/` = `src/shared/packages/pyforge-marshal/src/pyforge/marshal/`
- `C/` = `src/shared/packages/pyforge-core/src/pyforge/core/`
- `BL/` = the installed `bmad_loop` package

---

## 2. Inventory

### 2.1 Live ref counts

| Family | Kind | On `origin` | Local | Notes |
|---|---|---|---|---|
| `loop/pyforge-<station>` | branch | 8 | 8 | All 8 sit at `71c3747e91`, local = origin, an ancestor of `main`. **They hold no unique content today.** |
| `attempt-preserve/*` | branch | 3 | 0 | The three the operator kept. Two are hand-named and do not match bmad-loop's `<run>-<sha8>` shape. They hold 1,014 / 1 / 17 commits not in `main` |
| `refs/attempt-preserve-dirty/*` | custom ref | 0 | 17 | bmad-loop snapshots. 16 of 17 hold a commit on no `origin` ref |
| `rescue/dangling-<YYYYMMDD>-<sha8>` | lightweight tag | 682 | 682 | Every one is the **only** reachability for its commit: none is reachable from `origin/main` or any other `origin` branch |
| `rescue/<story…>` (hand-named) | lightweight tag | 16 | 16 | 4 are ancestors of `main`; 12 hold 1–4 commits not in `main` |
| `archive/*` | lightweight tag | 45 | 47 | 2 are local-only (`archive/recover-scribe-1-3`, `archive/scribe-1-3-dangling-91d3571f`). None of the 47 is an ancestor of `main` |
| `bmad-loop-preserve/*` | lightweight tag | 0 | 1 | `bmad-loop-preserve/5-9-intent-gap-2026-08-12` holds 2 commits on no `origin` ref |
| `archive/crewai-toolkit-wip-2026` | **branch** | 1 | 1 | `archive/` used as a branch prefix. 400 commits not in `main`. Unprotected |
| `backup/*` | branch | 1 (`steward-11-2-blocked-adf57ec5`) | 1 (`bmad-suite-updates-2026-09-26`, unpushed, 3 files) | Unprotected |
| `refs/backup/pre-split-1787762347`, `refs/bundle/pyforge-pages` | custom ref | 0 | 1 + 1 | Each holds 2 commits on no `origin` ref. Producer unknown |
| `recover/*`, `rescue/*` branches | branch | 0 | 0 | Protected by name in the sweeper and the ruleset; none exist |
| `dispatch/<slug>/<N.M>` | branch | 3 | 4 | Working refs. ≥ 300 merged dispatch PRs, and only 3 branches remain on origin |
| `land/pyforge-<station>-<e>-<s>` | branch | 0 | 5 | Hand rebuilds. All 5 are flagged unpushed (7–18 files) |
| `worktree-agent-<hex17>`, `chain-*`, `*-phase45-*` | branch | 0 | 6 | Claude Code agent worktrees. All merged into `main`, all local-only |
| `checkpoint/*`, `substrate-nightly` | annotated / lightweight tag | 5 + 1 | 5 + 1 | Milestone tags, not preserved work. Out of scope |
| `refs/remotes/{marshal,mason}-home/*` | remote-tracking | — | 31 + 31 | Two loop homes registered as git *remotes* of their own repo. These are stale mirrors of shared refs |

### 2.2 Producers

| Family | Producer (process) | Where it is written | When | Local / origin |
|---|---|---|---|---|
| `attempt-preserve/<run>-<sha8>` | upstream bmad-loop | `BL/recovery_flow.py:56-58` (name), `:1522-1593` (`preserve_attempt_commits`), `BL/workspace.py:410-420` (re-mount reclaim) | Before an auto-rollback's `reset --hard` (`rollback_on_failure`), and when an abandoned story branch is re-mounted | local only |
| `refs/attempt-preserve-dirty/<run>-<base8>-<n>[-rN]`, `…-<head8>-orphan` | upstream bmad-loop | `BL/recovery_flow.py:1673-1738`, `BL/workspace.py:104-114, 253` | Uncommitted state before a rollback reset; an orphaned mount before reclaim | local only |
| `bmad-loop/<run>/<story>` | upstream bmad-loop | `BL/workspace.py:87-101` | Each story under `isolation = "worktree"` | local; **pushed by marshal's stage pusher** (`M/supervisor/__main__.py:1803-1813`) |
| `<run_dir>/failed/<story>/changes.patch` (spin) | upstream bmad-loop | `BL/workspace.py:529-590` | Failed unit (with `keep_failed`, the worktree and branch also stay) | gitignored file in the loop home (`.gitignore:812`) |
| `attempt-preserve/<run>-<head8>` (marshal) | marshal spin supervisor, Story 20.4 | `M/supervisor/intent_gap_preserve.py:136-139`, with `git branch -f` at `:291-295`; called from `M/supervisor/__main__.py:3137-3158` | Intent-gap escalation where bmad-loop left `preserve_ref` empty | local only. **Not pushed**: the stage push covers only `loop/<slug>` and `task.branch` (`:1798-1813`) |
| `<bmad_run_dir>/failed/<story>/changes.patch` (marshal) | marshal spin supervisor | `M/supervisor/intent_gap_preserve.py:160-169` | Same, uncommitted-only or as an overlay | gitignored file |
| `<dispatch-runs>/<run>/failed/<story>/changes.patch` | marshal dispatch supervisor | `M/core/dispatch_preserve.py:19-21`; writer `M/dispatch_supervisor/__main__.py:287-347` | **Only** when the verdict is `FAILED` and there is git progress (`:2735-2746`). Untracked files are not captured (`M/adapters/vcs_git.py:815-848`) | gitignored Tier-3 (`.gitignore:798`). 120 such files on disk today |
| `wip: <story> (auto-checkpoint)` commits | marshal | `M/core/worktree_checkpoint.py:11-66`; dispatch tick `M/dispatch_supervisor/__main__.py:2340-2355`; spin `M/supervisor/__main__.py:2652-2665` | Dirty and idle ≥ 60 s | on the working branch (dispatch pushes pre-verify, `:1898-1980`) |
| synthetic `…(not a real commit)` objects | marshal `VcsPort` | `M/adapters/vcs_git.py:490-512` (merged-check), `:1347-1375` (merge-tree preview) | Every `is_branch_merged` call, including the dispatch supervisor tick (`M/dispatch_supervisor/__main__.py:443`) | dangling local objects. **19,412 today** |
| `loop/<slug>` | `marshal init` | `M/cli/init.py:697, 738` | Provisioning a loop home | local, then pushed by the stage pusher, `marshal refresh` (fast-forward only, `M/cli/refresh.py:367-375`) and `scripts/fleet-poll-hourly.sh:20` |
| `dispatch/<slug>/<N.M>` | `marshal factory dispatch` | `M/core/dispatch.py:441`; `M/cli/dispatch.py:1256-1283` | First dispatch of a story; re-dispatch reuses it | pushed pre-verify (`M/core/dispatch_push.py`; `M/dispatch_supervisor/__main__.py:1898-1980`) |
| `rescue/dangling-<YYYYMMDD>-<sha8>` | **a detector's printed remedy, run by hand** | `scripts/unpushed_work_check.py:166-169` prints `git tag … && git push origin …` | Operator sessions ran it by hand, in bulk. A lightweight tag has no creation date. The tagged commits are dated 2023-04 to 2026-08, and 669 of the 682 fall in July–August 2026 | origin |
| `rescue/<story…>`, `recover/*`, `bmad-loop-preserve/*`, `backup/*`, `archive/<…>` tags and branch | operator/agent sessions, by hand | no code; records exist, e.g. `spec-2-4-mason-recipe-new.md:182` (`rescue/mason-2-4-attempt-snapshot`), `spec-5-9-…md:13` (`preserved_at_tag`) | Ad hoc recoveries and cleanups | mixed |
| `land/<station>-<epic>-<seq>` | hand recovery recipe | `C/landing_evidence.py:172-181` (grammar); `scripts/bmad_loop_baseline_drift_check.py:28-31, 309-313`; `docs/how-to/pixi-tasks.md:64` | Rebuilding a stranded or wip-laden story for a clean landing | local; pushed when a PR is opened |
| `<slug>` scratch branch + `<repo>-wt-<slug>` worktree | `pyforge steward workspace start` | `src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py:534-573` | Operator/agent landing worktrees | local |
| `.steward/workspace-archive/<slug>-<stamp>.tar.gz` | `steward workspace clean` | `workspace.py:866-945` | Before removing an unlanded scratch worktree | gitignored (`.gitignore:951`). 26 on disk |
| `~/.local/state/pyforge-marshal/worktree-preserve/<branch>/` | `scripts/worktree_sweep.py` PRESERVE-THEN-DELETE | `scripts/worktree_sweep.py:63, 244-261` (`git format-patch`) | Before removing a worktree with unmerged commits | host-local. 6 on disk |
| `worktree-agent-<hex17>` + `.claude/worktrees/agent-<hex17>` | Claude Code subagent isolation (`isolation: "worktree"`; Claude Code's own Agent-tool documentation says "auto-cleaned if unchanged"; no repo file configures it) | Claude Code itself; the lock text is `claude agent agent-<id> (pid N start T)` (`git worktree list --porcelain`) | A subagent that runs in its own worktree | local; locked to the parent process |
| `.claude/worktrees/<adjective>-<name>-<hex6>` (e.g. `nervous-jemison-4f6c71`, detached HEAD) | Claude Code desktop session worktrees | Claude Code itself | A session that runs in a worktree | local |
| `~/.cursor/worktrees/<name>/`, `.cursor/worktrees/<name>/` | Cursor parallel/background agents | Cursor itself | Cursor agent sessions | local. **All 6 present today are empty, unregistered directories dated 2026-09-05** |
| unnamed intent-gap patch | `bmad-build-auto` skill text | `.claude/skills/bmad-build-auto/step-04-review.md:71` ("Save the attempted change as a patch file in `{{.implementation_artifacts}}`… then revert") | Intent gap | gitignored Tier-3 file |
| *(nothing; revert)* | `bmad-build-auto` and `bmad-build` skill text | `bmad-build-auto/step-04-review.md:72` (bad_spec: "Revert code changes"); `bmad-build/step-04-review.md:63-64` (intent_gap and bad_spec revert with no patch) | Intent gap or bad spec | **the attempt is discarded** unless an auto-checkpoint commit happened to capture it |

### 2.3 Consumers, detectors and protections

| Consumer | What it reads or protects | path:line | Depends on the name? |
|---|---|---|---|
| `scripts/worktree_sweep.py` | Branch prefix list. `attempt-preserve` worktree: delete the worktree only once the branch is on origin. KEEP every locked worktree | `:65`, `:197-200`, `:191` | yes |
| `marshal retire` (Story 4.10, AD-47) | Candidates are only the `TaskPhaseSnapshot.branch` values from each home's latest run. Structural exclusion `loop/` only; **`rescue/*` is not excluded** in code | `M/cli/retire.py:274-280, 314-322`; `M/core/retire.py:53, 97-105` | yes (`loop/`) |
| `marshal init` / `homes` / fleet scan | Fleet membership is "a worktree whose branch starts with `loop/`" | `M/cli/init.py:958, 1070`; `M/cli/retire.py:275`; `M/core/context.py:39`; `M/core/status.py:85` | **yes, load-bearing** |
| `marshal land` | PR head is `loop/<slug>`; `gh pr merge --delete-branch` when `landing_branch_retirement` (default `True`) | `M/cli/land.py:438, 507, 979-1050`; `M/adapters/forge_gh.py:375-376`; `M/core/policy.py:611` | yes |
| `marshal teardown` | Removes the home, then `git branch -D loop/<slug>`. Refuses only on dirt, unmerged `loop/<slug>`, or unreachable *spec promotions*. **Does not check** failed patches, kept-failed unit branches, scratch preserve refs, or whether `loop/<slug>` is pushed | `M/cli/init.py:2292-2702`, `:2662`, `:2682` | yes |
| dispatch landing / heal | `--delete-branch` on the dispatch PR; local `git branch -D` of the dispatch branch | `M/dispatch_land.py:993, 1379-1386`; `M/dispatch_land_heal.py:373-377` | yes (`dispatch/`) |
| marshal status (AD-48) | Runs `unpushed_work_check.py --json --branches-only` and keeps only `unpushed-branch` rows matched to `loop/<slug>` or the row's dispatch branch. **Every other unpushed ref is discarded**. Shows `failed_patches` and `dispatch_preserve_ref` | `M/cli/status.py:1198, 1226-1251, 1867-1870`; `M/core/status.py:1110-1128, 1241-1242`; FR-176 glob `M/cli/status.py:1255` | partly |
| `scripts/unpushed_work_check.py` | `refs/heads/*` ahead of origin, plus dangling commits. `rescued()` reads `refs/tags/rescue/dangling-*`. **Does not read tags or custom refs** for unpushed content; **swallows a non-zero git exit** | `:65-71`, `:105-109`, `:111-150`, `:153-170` | yes (`rescue/dangling-`) |
| `scripts/missing_preserve_check.py` | `preserve_ref` must name a **local** `refs/heads/attempt-preserve/*` branch, or `failed/<story>/changes.patch` must exist | `:78`, `:146-160`, `:163-224` | yes |
| `scripts/bmad_loop_baseline_drift_check.py` | `for-each-ref refs/heads/attempt-preserve/<run>-*`, **local only** | `:111-118` | yes |
| `scripts/fleet_picture.py` | Prints the hint `no attempt-preserve/<run>-* branch -- check failed/<story>/changes.patch` | `:790-795` | yes |
| upstream bmad-loop | `task.preserve_ref` in `state.json` (`BL/model.py:428, 572, 815`); defer notice (`BL/engine.py:7633-7700`); prunes both families at run start (`BL/engine.py:944`; `BL/recovery_flow.py:1484-1513`; `BL/verify.py:5805-5857`) | — | owns them |
| bmad-loop-resolve skill | `restore_patch` path; **refuses it for worktree-isolation runs** | `.claude/skills/bmad-loop-resolve/SKILL.md:200-206` | file path |
| session hook (85.1, chained, not merged) | Planned matcher: deleting `main`, `loop/`, `attempt-preserve/`, `recover/`, `rescue/` branches via `git push --delete`, `-d`, `:refs/heads/…`, `git branch -d/-D`, `gh api -X DELETE …/git/refs/heads/…`, and `git worktree remove` of `~/.bmad-loops/*` | branch `chain-sweeper-protected-refs`, spec `spec-85-1-…md` | yes |
| GitHub ruleset 24451573 | Branch deletion blocked for `refs/heads/{loop,attempt-preserve,recover,rescue}/**`. No tag ruleset, no update or force-push rule, no `main` | live API | yes |

### 2.4 Planning artifacts that name these families

| Artifact | What it says | Status vs code |
|---|---|---|
| AD-29 (`ARCHITECTURE-SPINE.md:317-323`) | Promotion durability accepts "the declared durable local ref" | **Unimplemented**: `M/cli/deploy.py:15-25`, "no code anywhere in this package names a real mechanism for it yet" |
| AD-40 (`:430-434`) / FR-59 | Landing retires the branch it merged | Ships as `--delete-branch` on `loop/<slug>` |
| AD-46 (`:470-474`) / FR-61 | Stage-bound push of station and per-story branches | Ships. Does not push marshal's own `attempt-preserve/*` |
| AD-47 (`:476-480`) / FR-63 / Story 4.10 | Retirement is proof-gated; `loop/*` and "`rescue/*` tags" are structural exclusions | `loop/` only (`M/core/retire.py:53`). spec-4-10 line 43 says no code mints rescue tags, but the detector prints a mint command |
| AD-48 (`:482-486`) / FR-62 | Durability is a fleet-status dimension, read from the unpushed-work detector | Ships. Inherits the detector's blind spots |
| AD-74 (`:1430-1445`) / FR-189 / Stories 20.4–20.5 | Detect, then preserve (`attempt-preserve/*` or `changes.patch`), then defer loudly | Ships. The preserve is local-only and sits under the pruned prefix |
| FR-170, FR-171, FR-176, FR-177, FR-178 (`prd.md:377-445`) | Retired-merged classification; tip-based unpushed check; failed-patch reporting; one pusher; shared git state | Ship |
| `spec-durable-runs` memlog `:12, :15, :19` | CAP-6 retirement; `loop/*` and `rescue/*` tags permanently excluded; rescue-tag lifecycle is a non-goal | — |
| `architecture-bmad-infra.md:842-849` | Branch table lists `attempt-preserve-dirty/*` (it is really `refs/attempt-preserve-dirty/*`) and "retain 20" | stale shape |
| `spec-one-chain-per-station` CAP-11 (`docs/governance/spec-one-chain-per-station/SPEC.md:192-205`; CHAIN-STANDARD §11) | `archive/<original path>`, nothing deleted | **Files only**; refs not covered |
| marshal Story 87.1 (chained, `chain-sweeper-protected-refs`) | Remote sweep with KEEP/DELETE/INSPECT; `--retire <branch>` deletes named protected branches; reads `protected_ref_prefixes` | `--retire` conflicts with the ruleset's no-bypass deletion rule (§ 4, item 4) |
| steward Story 85.1 (chained) | `session_denials` entry `protected-ref-deletion`; roster key `protected_ref_prefixes` | Branches only; no tags (§ 4, item 5) |
| Team memory `reference/bmad-loop-escalation-and-landing-traps.md:10-14`; `docs/how-to/troubleshoot-bmad-agent-loops.md:38` | Use `--restore-patch` on re-arm | Contradicts the resolve skill's worktree-isolation refusal |

### 2.5 Upstream bmad-loop contract (0.12.0)

- **What it writes.**
  - `attempt-preserve/{safe(run_id)}-{tip[:8]}` with `git branch` (`BL/recovery_flow.py:56-58, 1574-1590`).
  - `refs/attempt-preserve-dirty/{slug}-{baseline[:8]}-{attempt}`, probing `-r2…-r100` when the name
    is taken (`:1673-1700`), and `…-{head[:8]}-orphan` for orphaned mounts (`BL/workspace.py:104-114`).
  - Unit branches `bmad-loop/{run}/{story}` (`BL/workspace.py:87-101`).
  - `run_dir/failed/<unit>/changes.patch` (`BL/workspace.py:529-590`).
- **What it reads back.** `task.preserve_ref`, which persists in `state.json` (`BL/model.py:428, 572,
  815`), is printed in the defer notice (`BL/engine.py:7663-7685`) and journaled on `story-deferred`
  (`:7692-7697`). The notice says *"The pointer is a name, not a promise: `scm.preserve_keep` prunes
  the oldest refs at a later run's start"* (`:7650-7652`).
- **What it deletes.**
  - At every run start, both families down to the newest `preserve_keep` by committer date
    (`BL/engine.py:944`; `BL/verify.py:5739-5857`). The deleter is
    `delete_branch(force=True)` / `update-ref -d`, **local refs only**. Because every loop home is a
    worktree of the same repository, and git shares all `refs/` except `refs/bisect`, `refs/worktree`
    and `refs/rewritten` across worktrees (`man git-worktree`), the prune runs against the
    **primary clone's** refs.
  - Unit branches after a successful merge (`delete_branch = true`).
  - On resume, a crashed unit's branch, with `force=True` (`BL/workspace.py:649-670`).
- **Policy knobs marshal renders** (`M/adapters/harness_bmadloop.py:376-399`): `isolation = "worktree"`,
  `merge_strategy = "squash"`, `delete_branch = true`, `keep_failed = true`,
  `rollback_on_failure = true`, `preserve_keep = 20`, `run_retention = 10`, `archive_old = true`
  (old runs are tarred into `.bmad-loop/archive/`, which is gitignored), `auto_clean_on_finish = true`.
  The upstream policy comment says `0 = never prune (maximum safety)` (`BL/policy.py:543-549, 1433`).
- **Restore.** `--restore-patch` re-applies a patch on re-drive (`BL/cli.py:3175-3260`). The resolve
  skill forbids it for worktree-isolation runs, which is the mode marshal renders.
- **Journal events marshal can key on.**
  - `attempt-commits-preserved` (`BL/recovery_flow.py:1592`)
  - `attempt-worktree-preserved` (`:1738`)
  - `attempt-preserve-failed` (`:1584`)
  - `worktree-kept` (`BL/worktree_flow.py:4023`)
  - `story-deferred` (`BL/engine.py:2305`)
  - `<family>-pruned` (`BL/recovery_flow.py:1504-1512`)

### 2.6 Lifecycle by execution mode

"Durable?" means: reachable from a ref on `origin` that the server forbids deleting.

| Mode | Failure | Abandon / stop | Re-arm / re-drive | Send-back | Success | Read back by | Retired by | Durable? |
|---|---|---|---|---|---|---|---|---|
| **bmad-loop engine** (bare, or under spin) | `attempt-preserve/*` + `refs/attempt-preserve-dirty/*` before the reset; kept-failed unit worktree + `bmad-loop/<run>/<story>` + `failed/…/changes.patch` under the run dir | `discard_worktree` force-deletes the unit branch on resume (preceded by the reclaim park) | Re-mount parks the old tip under `attempt-preserve/*`; the resolve re-drive restores only in-place runs | n/a | Squash-merge into `loop/<slug>`; unit branch deleted | `state.json` `preserve_ref`; defer notice | **bmad-loop prune at the next run start**; `run_retention` tarring | **No**. Local refs and gitignored files |
| **`marshal factory spin`** | Adds the intent-gap `attempt-preserve/*` (`git branch -f`) or a patch; stage pushes `loop/<slug>` and `bmad-loop/<run>/<story>` | `marshal teardown` removes the home (and every gitignored run artifact), then `-D loop/<slug>` | as engine | n/a | `marshal land` merges the `loop/<slug>` PR and deletes `loop/<slug>` on origin by default | status `failed_patches`, `escalated_preserve_ref`; `missing-preserve-check`; `baseline-drift-check` | teardown, land, bmad-loop prune; `marshal retire` for unit branches | **Partly**: pushed unit branches until someone deletes them; the intent-gap ref and the patches are not |
| **`marshal factory dispatch`** (same on `claude`, `cursor`, `copilot`, `gemini`, `devin`; no harness branching in preserve code, `M/data/harness_profiles/*.toml`, default preference `M/core/policy.py:639`) | `FAILED` + progress writes `dispatch-runs/<run>/failed/<story>/changes.patch` and a `dispatch-preserve` journal pair. The branch is already pushed pre-verify | `stopped_externally` / `blocked`: **nothing preserved** beyond what the branch already holds (no writer, `M/dispatch_supervisor/__main__.py:2735`) | Re-dispatch reuses the worktree and branch; new baseline = HEAD; `MRS-DISP-036` warns (`M/cli/dispatch.py:441-479, 2912-2945`) | New session on the same worktree and branch (`M/core/dispatch_harness_done.py:140-200`) | PR merged with `--delete-branch`; local `-D` in heal | status `dispatch_preserve_ref` (`M/cli/dispatch.py:1437-1441`); `missing-preserve-check` dispatch plane | **Worktree never removed by marshal**; the patch is never retired | **Partly**: committed work pushed pre-verify; uncommitted work only in the local patch |
| **`marshal factory drain`** (`--stories`, `--campaign`, `--max-in-flight`; `M/cli/dispatch.py:3727, 3766, 3791`) | Per story, as dispatch (`run_fleet_drain` `M/cli/dispatch.py:5572` → `dispatch_once` `:2480`) | Campaign journals only (`fleet-drain-runs/<run>`, `M/core/dispatch_fleet.py:35, 52-53`; wave journals) | as dispatch | as dispatch | as dispatch | campaign journal | n/a | as dispatch; **the campaign records no preserve fact** |
| **`bmad-build-auto` bare** | intent_gap: unnamed patch in `implementation-artifacts`, then revert (`step-04-review.md:71`) | — | bad_spec: revert, keeping only notes (`:72`) | — | Local commit, "Do not push" (`:115-116`) | `bmad-loop-resolve` `restore_patch` | never | **No** |
| **`bmad-build-auto` under dispatch** | as dispatch, plus the skill's own patch | as dispatch | as dispatch | as dispatch | as dispatch | as dispatch | as dispatch | as dispatch |
| **`bmad-build`** (interactive) | intent_gap and bad_spec **revert with no patch** (`bmad-build/step-04-review.md:63-64`) | — | — | — | Local commit, "NEVER auto-push" (`step-05-present.md:9`) | — | — | **No** |
| **hand `land/*` rebuild** | — | — | — | — | Rebuilt branch lands via PR; the *source* (wip-laden dispatch branch or preserve ref) is not preserved by any step | `landing_evidence` grammar | nothing retires `land/*` (not protected; INSPECT in the sweeper) | **Source: no** |
| **`steward workspace`** | — | `clean`: tarball of unlanded work (or a `.landed.txt` note), `worktree remove --force`, `branch -D` only if merged (`workspace.py:866-945`) | — | — | — | own `.steward/workspaces.yaml` | `clean` | **No**: tarball is host-local |
| **Claude Code agent worktree** | — | Agent ends: worktree and branch removed if unchanged; else kept, **locked to the parent pid**. The lock outlives the process | — | — | branch merges via its parent's PR | — | sweeper KEEPs locked worktrees forever (`scripts/worktree_sweep.py:191`) | **No**: local-only branch |
| **Cursor agent worktree** | — | Directory left behind; today 6 empty, unregistered dirs (`~/.cursor/worktrees/*`, `.cursor/worktrees/steward-29-2-personas`) | — | — | — | — | **nothing**: the sweeper reads only registered worktrees | n/a (empty) |

### 2.7 Git and GitHub semantics that matter

1. **gc reachability.** A commit survives `git gc` only while some ref, reflog entry, index or
   worktree HEAD reaches it. Unreachable loose objects are pruned after `gc.pruneExpire` (default 2
   weeks). Reflog entries expire after 90 days (reachable) or 30 days (unreachable)
   (`man git-gc`). Three operations here remove reflog protection at once:
   - `git branch -d/-D` deletes the branch's reflog (`man git-branch`, "the reflog will also be
     deleted");
   - removing a worktree drops its per-worktree `HEAD` reflog;
   - `update-ref -d` drops the ref's reflog.
2. **Refs are shared across worktrees.** All `refs/` except `refs/bisect`, `refs/worktree` and
   `refs/rewritten` are shared (`man git-worktree`). A loop home or a dispatch worktree that creates,
   or *prunes*, `refs/heads/attempt-preserve/*` does so for the whole clone.
3. **Tags vs branches.**
   - Tags are the git-native immutable label. Lightweight tags carry no metadata; annotated tags
     carry tagger, date and message (provenance in-band).
   - A tag and a branch with the same short name make short-name resolution ambiguous. The repo
     already hit this with a stray tag `main` (Story 61.1, `scripts/worktree_sweep.py:58-60`).
   - `git fetch --prune --prune-tags` deletes **local tags absent from the remote**, so local-only
     preserve tags are one fetch flag from deletion.
4. **GitHub rulesets.** Branch and tag rulesets support the same four ref rules: restrict creations,
   restrict updates, restrict deletions, and block force pushes, each "only users with bypass
   permissions can …" (GitHub docs, *Available rules for rulesets*, read 2026-10-04). The live
   ruleset has only `deletion`, branches only, no bypass, so:
   - no tag is protected;
   - `loop/**` can still be force-pushed;
   - **nobody, not even the admin, can delete a protected branch through the API until the ruleset
     changes**.
5. **Deletion and recreation.**
   - GitHub's activity API records each branch deletion with its `before` sha, and a branch can be
     recreated at that sha while GitHub still holds the object. That is how the incident was undone.
   - No documented retention period for unreferenced objects was found. Recreation is a race, not a
     guarantee.
   - `gh pr merge --delete-branch` treats an HTTP 422 or 404 from the remote delete as "already
     deleted" and exits 0 (`cli/cli` `pkg/cmd/pr/merge/merge.go`, read 2026-10-04).
6. **Squash merges hide landed content from ancestry.** Marshal renders `merge_strategy = "squash"`
   for unit branches into `loop/<slug>`. A squashed unit branch's tip is never an ancestor of
   `main`, so ancestry checks call landed work "unmerged", and deleting the branch leaves its commits
   unreachable even though the content landed. Only patch-id or tree equivalence can tell the two
   apart. AD-47 already requires this ("by patch-id").

### 2.8 The 2026-10-04 incident, measured

- GitHub recorded **494 branch deletions (464 unique names)** on 2026-10-04, 487 of them in the 09:00
  UTC hour:
  - 33 unique `attempt-preserve/*` and 8 `loop/*` deleted at 09:11 UTC;
  - the same 30 `attempt-preserve/*` deleted again at 09:23 UTC (the operator's retirement);
  - ruleset 24451573 created at 09:29 UTC.
- Families among the 464: `bmad-loop/` 62, `fix/` 56, `dispatch/` 38, `docs/` 26, `bmad/` 16, and
  others.
- Of the **454 unique deleted tips**:
  - 327 are ancestors of `origin/main`;
  - 29 are reachable from another `origin` ref or tag;
  - **98 are reachable from no `origin` ref, no tag and no local branch.** Their objects are still in
    this clone (454 of 454 present), so they are gc-eligible here and retained on GitHub only at
    GitHub's discretion.
- By name, those 98 tips break down as: `bmad-loop/` 37, `attempt-preserve/` 15, `copilot/` 10,
  top-level 8, `marshal/` 5, `docs/` 5, `dispatch/` 5, `fix/` 4, `feat/` 3, `fleet/` 2, `claude/` 2,
  and one each of `warden/`, `steward/`, `scribe/`, `sbom/`.
- **The 37 `bmad-loop/` tips are inconclusive.** Only 5 match a `main` commit by whole-branch
  patch-id; the other 32 cannot be called lost or landed this way, because their merge-base with
  `main` predates the loop branch's own history.
- **The 30 retired tips (29 unique):** 14 are ancestors of `main`; **8 are now reachable from no ref
  at all** (`e63ea1e7`, `6725b773`, `137d3f9c`, `4edeb666`, `85a60d06`, `066d3633`, `1f526046`,
  `46cf7ae6`).
- **The loop homes' gitignored run history was lost.** `bmad_loop_baseline_drift_check.py` now
  reports `loop-home runs=0`.

---

## 3. Root cause

1. **No owner of the vocabulary.** Each process named a ref the moment it needed one:
   - upstream (`attempt-preserve/`, `refs/attempt-preserve-dirty/`);
   - marshal Story 20.4 copied upstream's name on purpose: *"Park `snapshot` under bmad-loop's
     deferred naming convention"* (`intent_gap_preserve.py:129`);
   - a detector's printed remedy (`rescue/dangling-`);
   - operator sessions (`recover/`, `rescue/<story>`, `bmad-loop-preserve/`, `backup/`, `archive/`
     as both tag and branch, `land/`);
   - three tools wrote non-git preserves (sweeper patches, steward tarballs, dispatch patches).

   No AD, FR or CAP defines what a *preserved-work ref* is. AD-47 names `rescue/*` only to exclude
   it, and spec-durable-runs declares the rescue-tag lifecycle a non-goal.
2. **Durability was encoded as "protected names", not as "reachable from a durable ref".** The
   protections (sweeper prefixes, AD-47, ruleset, 85.1) all ask "is this name protected?". None asks
   "would deleting this make a commit unreachable from `origin`?". That is the property every loss
   in the record shares: scribe 1.3's dangling commit, the 2026-07-31 unpushed estate, the 30
   retirements, the 98 tips.
3. **Upstream scratch was adopted as a permanent archive.** bmad-loop documents `attempt-preserve/*`
   as a bounded safety net that it prunes. The repo protects the prefix in four places and parks
   durable work in it. Nothing reconciles the two: marshal renders `preserve_keep = 20` and never
   pushes its own intent-gap refs.
4. **Tags are where most preserved state lives, and the protection model covers only branches.**
   The ruleset and 85.1 are branch-only. The `rescue/**` branch pattern protects an empty set, and
   AD-47's "`rescue/*` tags" exclusion is not in code (`M/core/retire.py:53`).
5. **Retirement was never specified.** CAP-11's `archive/<original path>` is a files rule. The ref
   retirements actually done (delete; or "archive tag kept locally") each removed reachability from
   `origin`.
6. **Operational branches are conflated with preserved work.** `loop/<slug>` is load-bearing for
   fleet membership, landing and pushes, and today it carries no unique content. It needs
   *operational* protection with explicit teardown and land rules. Treating it as preserved work put
   it in the same deletion ruleset that now contradicts `marshal land`'s default.
7. **Detectors can be silently blind.**
   - `unpushed_work_check.py` turns a failed `fsck` into "no dangling commits". It reads only
     `refs/heads/*` for unpushed content. Its remedy creates more lightweight tags.
   - Marshal's synthetic merged-check commits flood the object store (19,412 objects; 149 of the 682
     rescue tags preserve such synthetic commits).
   - Every preserve reader (`missing_preserve_check`, `baseline-drift-check`, `fleet_picture`) checks
     **local** `refs/heads` only, so a preserve restored only on `origin` (the three kept branches
     today) reads as missing.
8. **Hand-rolled cleanup filled the gap left by a local-only sweeper.** Remote branches had no
   sweeper (87.1 fixes that), and the hook had no deny (85.1 fixes that). The deeper gap is that
   **tool-internal deleters** never pass through a shell hook:
   - bmad-loop's prune;
   - `marshal teardown` / `land` / heal;
   - `steward workspace clean`;
   - `gh pr merge --delete-branch`.

   Only the server ruleset and in-code checks reach them.

**Live producers today:**
- upstream bmad-loop (both families, unit branches, failed patches) on every spin run;
- marshal spin (intent-gap `attempt-preserve/*`, patches);
- marshal dispatch (dispatch patches, synthetic objects every 60 s);
- the unpushed-work remedy (whenever a session follows it);
- `bmad-build-auto` (unnamed patch);
- steward workspace (tarballs);
- the sweeper (format-patch dirs);
- Claude Code and Cursor (agent worktrees and branches).

`recover/*`, `rescue/<story>`, `bmad-loop-preserve/*` and `backup/*` have no live producer; they are
historical.

**Names that carry meaning a consumer depends on:**

| Name | Consumers |
|---|---|
| `loop/` | fleet membership, landing, pushes, watch |
| `attempt-preserve/` | upstream prune, `missing_preserve_check`, baseline drift, `fleet_picture`, sweeper |
| `refs/attempt-preserve-dirty/` | upstream |
| `bmad-loop/<run>/<story>` | upstream, `landing_evidence`, `retire` |
| `dispatch/<slug>/<N.M>` | worktree resolution by branch name (`M/core/dispatch.py:74-88`), `landing_evidence`, status |
| `land/<station>-<epic>-<seq>` | `landing_evidence` |
| `failed/<story>/changes.patch` | `missing_preserve_check`, status, resolve |
| `rescue/dangling-` | `unpushed_work_check.rescued()` only |

`rescue/<story>`, `recover/`, `archive/`, `bmad-loop-preserve/` and `backup/` carry **no** code
meaning; only protection lists name them.

---

## 4. Live defects found (ranked by blast radius)

1. **The durability detector false-greens.**
   - `scripts/unpushed_work_check.py:65-71` returns `""` on any non-zero exit. `git fsck --no-reflogs`
     exits 1 here (empty loose objects `73fab1dc…` and `6d4b7abe…`), so `find_dangling` sees nothing.
     The detector exits 1 for 8 unpushed branches and reports 0 dangling commits; `fsck` lists
     20,135.
   - AD-48's status dimension inherits this. Marshal status runs `--branches-only`, so it never
     reaches the dangling scan anyway.
2. **8 retired tips and 98 deleted tips are reachable from nothing.** They are gc-eligible in the
   only clone that holds them. This is recoverable today and not after the next gc past the 2-week
   window.
3. **bmad-loop's prune can delete protected work.** Any local `refs/heads/attempt-preserve/*` beyond
   the newest 20 is deleted at the next spin run start, whatever its name. That includes marshal's
   intent-gap refs and hand-named ones. No local `attempt-preserve/*` exist today only because the
   incident removed them.
4. **Story 87.1's `--retire` cannot pass on GitHub.** Ruleset 24451573 blocks deleting
   `attempt-preserve/**` and `loop/**` with `bypass_actors: []`. Its AC only passes against the
   bare-remote test fixture.
5. **85.1's protection list is branch-only.** None of these is covered:
   - `git tag -d`, `git push origin :refs/tags/…`, `git push --delete origin <tag>`,
     `gh api -X DELETE …/git/refs/tags/…`;
   - `git update-ref -d`;
   - `git push --mirror` / `--prune`, `git fetch --prune-tags`;
   - `rm -rf ~/.bmad-loops/<station>`;
   - `gh pr merge --delete-branch` on a `loop/` head.

   It also lists `recover/` and `rescue/`, which match nothing.
6. **`marshal land` vs the ruleset.** The default `landing_branch_retirement = true` sends
   `--delete-branch` for the `loop/<slug>` head. The ruleset now refuses that delete. GitHub's status
   code for a ruleset-refused ref delete was not verified here:
   - If it is 422, `gh` exits 0 and marshal journals `branch_retired: true` for a branch that still
     exists (`M/cli/land.py:1050, 1088`).
   - Otherwise `gh` exits non-zero *after* the merge, and marshal raises `ForgeCommandError` on a
     merged PR (`M/adapters/forge_gh.py:378-387`).
7. **Preserve readers are local-only.** Today the three kept `attempt-preserve/*` exist only on
   `origin`. `missing_preserve_check._branch_exists` (`:146-160`) and
   `baseline_drift.preserve_refs` (`:111-118`) would report them missing.
   `missing_preserve_check` currently reports one live finding: herald run
   `pyforge-herald-20260915T011759678Z-ecad0a63`, an intent-gap with `preserve_ref: null`.
8. **Agent worktrees never retire.** The five `.claude/worktrees/agent-*` worktrees are locked by
   pid 9993 (alive, this session's desktop process). All are merged and local-only. Once the process
   exits, the locks stay, and the sweeper KEEPs them forever. The six Cursor directories are empty
   and unregistered, and invisible to the sweeper.
9. **Skill text discards attempts.** `bmad-build` reverts on intent_gap and bad_spec with no patch;
   `bmad-build-auto` reverts on bad_spec. The resolve skill and the troubleshooting docs disagree on
   `--restore-patch` for worktree-isolation runs.
10. **Synthetic objects pollute the store.** 19,412 dangling synthetic commits slow `fsck` (46 s)
    and inflate the dangling population that drove 682 rescue tags. 149 of those tags preserve
    synthetic commits, and 146 of those point at a tree that a reachable commit already has.

---

## 5. Requirements for a correct standard

Each requirement is stated so a test or a detector can check it.

- **R1 Durability.** Preserved work is a commit reachable from a ref on `origin` whose deletion and
  update the server forbids. A preserve that exists only locally is *pending*. It is reported until
  it is pushed, never reported as clean.
- **R2 Nothing gc-able.** No operation may make a commit unreachable unless the commit is reachable
  from `origin/main`, or a durable preserve or archive ref on `origin` reaches it. This covers:
  - deleting a branch, tag or custom ref;
  - removing a worktree or a run or home directory;
  - pruning;
  - retiring.
- **R3 Discoverability.** One name grammar with one parser, the AD-73 precedent (one grammar, many
  consumers). A single command lists preserved work by station, story, producer and state
  (open/retired). Consumers never regex ref names.
- **R4 Provenance.** Every preserve records in-band:
  - producer (closed vocabulary);
  - machine or human;
  - reason;
  - source ref or path;
  - run id;
  - journal entry;
  - the full commit sha.
- **R5 Retirement.** There is one retirement path. It keeps reachability, records its evidence
  (ruling or done story with merge sha), is idempotent, and is reversible by reading. Purge is a
  separate, operator-only act by explicit name, after a manifest is committed to git.
- **R6 Protection.**
  - One declared list of protected ref prefixes, as full refnames, covering both branches and tags.
  - The same list drives three things: the server rulesets (deletion + update + force-push for
    preserve and archive tags; deletion for operational branches); the session hook (branch, tag,
    custom-ref, prune/mirror and home-removal forms); and every tool-internal deleter.
  - A runtime check proves the live rulesets equal the declared list.
- **R7 Upstream compatibility.** No upstream name changes. Marshal adapts by promotion and by the
  knobs it already renders (`preserve_keep`). An upstream PR is only an option, and only on an
  explicit operator ask.
- **R8 One rule for every mode.** spin, dispatch (every harness profile), drain, bare bmad-loop,
  `bmad-build`, `bmad-build-auto` (bare and dispatched), hand `land/*`, `steward workspace`, and
  Claude Code and Cursor agent worktrees each meet R1–R5 at their failure, abandon, re-arm,
  send-back and teardown events.
- **R9 Fail closed.** A detector that cannot observe returns could-not-observe, never 0 findings.
- **R10 Offline.** Preserving works offline (local tag) with the push pending and reported, per
  AD-29's F-14 principle.
- **R11 Operational ≠ preserved.** `loop/*` is protected as an operational branch. Its deletion
  paths (teardown, land) are explicit, refuse while it holds unpreserved content, and never run
  server-side under a ruleset that forbids them.
- **R12 Name hygiene.**
  - Dates are `YYYY-MM-DD` (AGENTS.md § Dates); the existing `YYYYMMDD` segments are legacy.
  - Matching uses full refnames (Story 61.1).
  - No short name exists as both a branch and a tag.

---

## 6. Candidate standards

### Candidate A — Protect what exists

Keep every name. Add:
- a tag ruleset over `refs/tags/rescue/**` and `refs/tags/archive/**`;
- tag forms in 85.1;
- `preserve_keep = 0`;
- a push of marshal's intent-gap `attempt-preserve/*`;
- detector fixes.

Retirement stays "delete with a manifest".

- **For:** the smallest change; no migration.
- **Against:**
  - Keeps 9+ families with overlapping meaning.
  - Hand-named work keeps landing under the upstream-pruned prefix.
  - Retirement still destroys reachability (the 8 orphaned tips are the proof).
  - No provenance: lightweight tags carry none.
  - `archive/` stays ambiguous: a branch prefix, a tag prefix, a CAP-11 files rule, and sometimes
    local-only.
  - The protected list grows with every new family.

### Candidate B — One durable tag namespace; archive as the retirement state (recommended)

Three ref classes:

1. **Working refs.** Mutable, owned by one producer, retired freely once proven:
   - `dispatch/…`, `bmad-loop/…`, `land/…`, steward `<slug>`, `worktree-agent-…`, ordinary branches;
   - `loop/<station>`: operational, never retired by a sweep, removed only by `marshal teardown`
     under R11;
   - upstream scratch: `attempt-preserve/*`, `refs/attempt-preserve-dirty/*`, kept local, never
     pushed, promoted on sight.
2. **Preserved work.** `refs/tags/preserve/…` annotated tags. Append-only. Protected by a tag
   ruleset (deletion, update, force-push; no bypass).
3. **Retired.** `refs/tags/archive/<original ref path>` annotated tags. Same protection. All 45
   `archive/*` tags on `origin` already have this `archive/<branch path>` shape, e.g.
   `archive/claude/pdos-1-2-…`, `archive/bmad-loop/<run>/<story>`, `archive/attempt-preserve/<…>`.
   Only the 2 local-only extras flatten the path. Each original branch name was not verified
   one by one.

- **For:**
  - One rule, which meets R1–R12.
  - Upstream untouched.
  - Provenance in the tag object.
  - Retirement keeps bytes; purge is deliberately heavy (it needs a ruleset change).
  - The protected list collapses to four entries (§ 7.3).
  - Mirrors CAP-11's structure-preserving `archive/<original path>` for refs.
- **Against:**
  - New code in spin and dispatch (promotion) and a preserve verb.
  - The tag count only grows until a purge.
  - The legacy 698 + 45 tags stay lightweight (no in-band provenance) unless re-tagged.

### Candidate C — Durable branches

One protected branch prefix (e.g. `preserve/**` branches) with deletion and force-push rules; tags
migrated into branches.

- **For:** reuses the existing branch ruleset type and the sweeper's branch logic.
- **Against:**
  - Branches are mutable by design.
  - Provenance needs a sidecar manifest.
  - Hundreds of branches flood the branch, PR-head and `gh` listings.
  - Migrating 698 tags into branches runs against git's own model.
  - `delete_branch_on_merge`-style tooling and `--merged` sweeps target branches.

### Option D — Upstream change (only on an explicit operator ask)

A bmad-loop PR could add three things:
1. a prune that never deletes refs it did not mint (match only `<run_id>-<sha8>` names of known runs), or a configurable preserve prefix;
2. a plugin or hook event when a preserve ref is written, so marshal promotes event-driven;
3. `--restore-patch` support for worktree-isolation runs.

Each is an outward PR. Per AGENTS.md § Policy, it needs operator confirmation. B does not depend on
any of it.

| Requirement | A | B | C |
|---|---|---|---|
| R1 durability (origin + server protection) | partial (tags protected; intent-gap pushed) | yes | yes |
| R2 nothing gc-able on delete or retire | no (retire deletes) | yes | yes |
| R3 one grammar | no | yes | yes |
| R4 provenance in-band | no | yes (annotated) | sidecar only |
| R5 reachability-keeping retirement | no | yes | yes |
| R6 one list, both kinds | long list | 4 entries | 2 entries |
| R7 upstream untouched | yes | yes | yes |
| R11 operational separated | no | yes | yes |
| Migration cost | none | promote local-only items; legacy tags stay | high |

---

## 7. Recommendation — candidate B

### 7.1 The one rule

> **Work outlives its working copy only as a commit reachable from an annotated tag under
> `refs/tags/preserve/` on `origin`.**
>
> - A working copy is a branch, worktree, run directory, patch file or tarball. No process removes
>   one whose unique content no such tag holds.
> - `preserve/` tags are never moved or deleted. A preserve retires by gaining an annotated twin at
>   `refs/tags/archive/<its ref path>`.
> - Deleting a `preserve/` or `archive/` tag is a purge: an operator act, by explicit name, after a
>   manifest is committed.

### 7.2 Grammar (one owner, one parser)

```
refs/tags/preserve/<project-slug>/<story-key>/<producer>-<YYYY-MM-DD>-<sha8>   (story-bound)
refs/tags/preserve/unbound/<producer>-<YYYY-MM-DD>-<sha8>                      (no story)
refs/tags/archive/<original ref path without refs/heads/ or refs/tags/>        (retired)
```

- `<project-slug>` is the BMAD project slug (`pyforge-marshal`), as in `dispatch/<slug>/<N.M>`.
- `<story-key>` is AD-23's canonical `N.M`.
- `<sha8>` is the preserved commit. The tag message carries the full sha.
- The date is the preserve date (UTC).
- `<producer>` is a closed vocabulary:

| Producer | Meaning |
|---|---|
| `bmad-loop` | promoted upstream scratch: rollback, re-mount, orphan, kept-failed unit |
| `intent-gap` | marshal spin Story 20.4 |
| `dispatch` | dispatch supervisor |
| `build` | `bmad-build` / `bmad-build-auto` before a revert |
| `sweep` | `worktree_sweep.py` |
| `workspace` | `steward workspace clean` |
| `dangling` | the unpushed-work remedy |
| `hand` | an operator or agent by hand |

Annotated message trailers (all required):
- `Preserve-Producer`
- `Preserve-Provenance: machine|human`
- `Preserve-Reason`, from `rollback|redrive|orphan|kept-failed|intent-gap|failed-verify|stopped|blocked|revert|sweep|dangling|hand`
- `Preserve-Source` (full refname or path)
- `Preserve-Run`
- `Preserve-Journal`
- `Preserve-Commit`

Archive twins carry `Archive-From`, `Archive-Reason` and `Archive-Evidence`. The evidence is a ruling
date and text, or `story <slug> <N.M> done <merge-sha>`.

A dirty working tree is first captured as a snapshot commit, without moving any branch, the same way
`BL/verify.py` `snapshot_worktree` does it, including untracked files. A collision on the same
name and same object is a no-op; a collision on the same name and a different object is refused.

### 7.3 Protection (one declared list)

```
refs/heads/loop/              operational: deletion blocked (branch ruleset, existing)
refs/heads/attempt-preserve/  legacy: deletion blocked until the operator rules on the 3 left
refs/tags/preserve/           deletion + update + force-push blocked (new tag ruleset)
refs/tags/archive/            deletion + update + force-push blocked (new tag ruleset)
refs/tags/rescue/             legacy, frozen: deletion + update + force-push blocked (new tag ruleset)
```

- Drop `refs/heads/recover/**` and `refs/heads/rescue/**`: no producer, no instance. This is open
  question Q6.
- The roster key (85.1) holds exactly this list as full refnames. The hook, the sweeper and the
  in-code deleters read it, and a runtime parity check compares it with the live rulesets.

### 7.4 What changes, by mode (the file that has to change)

| Mode | Change | Where |
|---|---|---|
| bmad-loop engine (spin and bare) | Render `preserve_keep = 0`, so upstream never prunes. The supervisor promotes on `attempt-commits-preserved` / `attempt-worktree-preserved` / `worktree-kept` / `story-deferred` and pushes the tag at the next stage boundary. A sweep retires local scratch only once promoted | `M/adapters/harness_bmadloop.py:392`; `M/supervisor/__main__.py:1798-1813` (stage loop); `M/supervisor/durability.py:73-77` |
| spin intent gap | Mint a `preserve/…/intent-gap-…` tag instead of `attempt-preserve/*` (no `git branch -f`). Keep the patch as a convenience | `M/supervisor/intent_gap_preserve.py:123-169, 291-295`; `M/supervisor/__main__.py:3137-3215` |
| spin teardown | Refuse while the home holds unpromoted work: `failed/*/changes.patch`, kept-failed unit branches, local scratch refs, an unpushed `loop/<slug>`. `--abandon` names it | `M/cli/init.py:2292-2702` |
| spin landing | Never send `--delete-branch` for a `loop/*` head. Journal `branch_retired` from an `ls-remote` fact, not intent | `M/cli/land.py:438, 507, 979-1088`; `M/adapters/forge_gh.py:375-376` |
| dispatch (every harness) | On `FAILED`, `stopped_externally` or `blocked` with progress: snapshot (including untracked) and push a `preserve/…/dispatch-…` tag. Journal it in the `dispatch-preserve` payload; status shows it | `M/dispatch_supervisor/__main__.py:287-347, 2735-2746`; `M/core/dispatch_preserve.py`; `M/adapters/vcs_git.py:815-848`; `M/cli/dispatch.py:1437-1441`; `M/core/status.py:1241-1242` |
| drain | A campaign cycle that stops, holds or blocks a story records that story's preserve tag, or a finding that none exists | `M/cli/dispatch.py:5572` (`run_fleet_drain`), `:2480` (`dispatch_once`); `M/core/dispatch_fleet.py:35, 52-53` |
| `bmad-build-auto` (bare or dispatched) | Before any revert (intent_gap, bad_spec): `marshal preserve tag --producer build`. Delivered as a persistent fact in the installer-safe customization, never by editing installed step files | `_bmad/custom/bmad-build-auto.toml` (`persistent_facts`); behaviour at `.claude/skills/bmad-build-auto/step-04-review.md:71-72` |
| `bmad-build` | Same, via a new `_bmad/custom/bmad-build.toml` | behaviour at `.claude/skills/bmad-build/step-04-review.md:63-64` |
| resolve / re-arm docs | Align `--restore-patch` advice with the worktree-isolation refusal | `docs/how-to/troubleshoot-bmad-agent-loops.md:38`; `.claude/memory/reference/bmad-loop-escalation-and-landing-traps.md:10-14`; `.claude/skills/bmad-loop-resolve/SKILL.md:200-206` (unchanged) |
| hand `land/*` rebuild | The recipe's first step preserves the source (`--producer hand`) before rebuilding | `C/landing_evidence.py:172-181` (convention text); `scripts/bmad_loop_baseline_drift_check.py:28-31, 309-313`; `docs/how-to/pixi-tasks.md:64` |
| `steward workspace clean` | Unlanded commits go to a `preserve/…/workspace-…` tag before `worktree remove`. The tarball stays only for gitignored bytes | `src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py:866-945, 929-940` |
| sweeper | PRESERVE-THEN-DELETE writes a `sweep` preserve tag (not `~/.local/state`). The protected list comes from the roster. `--retire` = archive twin, and refuses a delete the ruleset forbids. Stale-lock detection (pid + start time) for agent worktrees. Unregistered directories under `.claude/worktrees/`, `.cursor/worktrees/` and `~/.cursor/worktrees/` (never `~/.bmad-loops/`) are reported. Never touches `refs/tags/**` | `scripts/worktree_sweep.py:63, 65, 113-133, 191, 244-261, 276-288` |
| Claude Code / Cursor agent worktrees | No harness change. They are working copies under the sweeper's rules above | — |
| detectors | `unpushed_work_check`: fail closed on git error; scan local-only tags and custom refs; remedy = `marshal preserve tag --producer dangling`. `missing_preserve_check`, baseline drift, `fleet_picture`: accept `preserve/` tags and `origin` refs | `scripts/unpushed_work_check.py:65-71, 105-170`; `scripts/missing_preserve_check.py:78, 146-224`; `scripts/bmad_loop_baseline_drift_check.py:111-118`; `scripts/fleet_picture.py:790-795` |
| status (AD-48) | Report preserve debt: local-only preserve tags, unpromoted scratch, patches with no tag. Stop discarding unmatched unpushed refs | `M/cli/status.py:1198, 1226-1251`; `M/core/status.py:1110-1128` |
| retire (AD-47) | Structural exclusion of `refs/tags/**` and of every protected prefix. Candidates stay working branches | `M/core/retire.py:53, 97-105` |
| synthetic objects | Build merged-check and preview commits in a temporary object directory (alternates), so they never enter the repository's store | `M/adapters/vcs_git.py:490-512, 1347-1375` |
| hook + roster | Branch, tag, `update-ref`, prune/mirror, `rm` of homes, `gh pr merge --delete-branch` on a protected head | `.claude/hooks/pre-shell.py` (`MATCHERS` at `:616-…`); `docs/governance/guild-roster.json` |
| server | New tag ruleset; branch ruleset trimmed per § 7.3 | GitHub settings (operator act) |

### 7.5 Migration (no deletion anywhere)

| Item | Count | Action |
|---|---|---|
| 8 retired tips and the 98 deleted tips reachable from nothing | 8 / 98 (overlapping) | **First, before any gc:** create `archive/<original branch path>` annotated tags at each `before` sha and push them. This needs operator confirmation (Q1) |
| `refs/attempt-preserve-dirty/*` | 17 (16 with local-only commits) | Promote to `preserve/<slug>/<key>/bmad-loop-…` where the run's story is known, else `preserve/unbound/bmad-loop-…`. Push. Leave the originals to the sweeper |
| Local-only tags | 3 | `bmad-loop-preserve/5-9-…` → `preserve/pyforge-marshal/5.9/hand-2026-08-12-77bb757a`. The two flattened `archive/` tags → push as-is (open question Q4) or re-create as `archive/recover/scribe-1-3`, `archive/rescue/scribe-1-3-dangling-91d3571f` |
| `attempt-preserve/*` on origin | 3 | Create `preserve/…/hand-…` twins: `pyforge-marshal/47.1`, `pyforge-mason/6.3`, `unbound` for the 2026-07-12 pilot. The branches stay until the operator drops `attempt-preserve/**` from the ruleset (Q3) |
| `backup/*` branches, `archive/crewai-toolkit-wip-2026` branch | 2 + 1 | `preserve/…/hand-…` or `archive/<path>` tag twins. The branches can then be deleted (unprotected), which removes the `archive/` branch-vs-tag ambiguity |
| `rescue/dangling-*` | 682 | **Leave as frozen legacy under the tag ruleset.** No new ones are minted (the remedy changes). Classification for a later operator purge decision: 149 synthetic merged-check objects (146 with a tree already on a reachable commit, 3 unique); 212 git-stash commits (`WIP on …` / `On …:` / `index on …`); 8 merges; 313 content commits, of which 153 have a patch-id equal to an `origin/main` commit since 2026-06-01, 148 match none, and 12 have no patch-id |
| `rescue/<story>` | 16 | Legacy, frozen. 4 are already ancestors of `main` |
| `archive/*` | 45 on origin | Legacy-conforming: all 45 have the `archive/<branch path>` shape. The 2 flattened ones are local-only extras, handled in the row above. They stay lightweight; new archive twins are annotated |
| `refs/backup/pre-split-*`, `refs/bundle/pyforge-pages` | 2 | Unknown producer; each holds 2 local-only commits. Operator decides (Q5) |
| Orphan agent directories | 6 Cursor + 1 `.claude/worktrees/.retired-worktrees-20260822` | All empty. The sweeper deletes empty, unregistered directories |
| `.git` object health | 2 empty loose objects | Repair before any gc (§ 9) |

**Is `archive/` the retirement state?** Yes. It is the ref analogue of CAP-11's
`archive/<original path>`: structure-preserving, reachability-keeping, nothing deleted. It differs
from CAP-11 in one way: a retired *branch* is deleted after its archive twin exists on `origin`, and
a retired *preserve tag* is not deleted (append-only). `archive/` is never a branch prefix.

### 7.6 Ownership and co-governance

- **Marshal** owns the standard: the producers, the preserve verb, retire, status, the sweeper and
  the detectors (scripts it already owns per DW-HYGIENE-2026-09-05-1's ruling).
- **Steward** co-governs: hook, roster key, workspace clean, and the declared ruleset plus its parity
  check.
- **`spec-pyforge-core`** co-governs only if the name grammar becomes a kernel module
  (`pyforge.core.preserve_refs`, on the AD-73 `landing_evidence` precedent). That would let steward's
  workspace clean and the scripts parse names without importing marshal.
- **Doctor** is not a co-governor unless the operator wants the ruleset parity check under
  `pyforge.doctor.sources` (Q8). No existing detector moves to doctor.

---

## 8. Open questions only the operator can decide

1. **Re-preserve the 8 + 98 unreachable tips now?** This creates and pushes `archive/` tags at their
   `before` shas. It is an outward write, and it should happen before any gc.
2. **Is retirement reachability-keeping (`archive/` twin, recommended), or deleting (status quo)?**
   If keeping, is purge ever allowed? A purge needs a temporary ruleset change, by design.
3. **The 3 remaining `attempt-preserve/*` branches on `origin`.** Keep them forever, or drop
   `refs/heads/attempt-preserve/**` from ruleset 24451573 once their `preserve/` twins exist?
4. **The two flattened local `archive/` tags.** Push them as-is, or re-create them structure-preserving?
5. **`refs/backup/pre-split-1787762347` and `refs/bundle/pyforge-pages`.** What are they, and should
   they be preserved?
6. **Drop the `recover/**` and `rescue/**` branch patterns** from the ruleset and the roster? They
   match nothing.
7. **`preserve_keep = 0` (recommended) or keep 20?** With 20, an unpromoted ref, for example from a
   bare bmad-loop run with no supervisor, can be pruned before promotion.
8. **Home of the ruleset parity check:** steward (with the roster) or doctor (sources)?
9. **Server-side tag ruleset:** confirm creating it (a settings change, outward). Confirm
   `bypass_actors: []` for `preserve/**` and `archive/**`.
10. **Option D upstream PR to bmad-loop:** ask for it or not.
11. **Rescue-tag purge.** Once classified, may the 146 synthetic-duplicate-tree tags and the 212 stash
    commits be purged with a manifest, or does `rescue/*` stay frozen forever?
12. **`main` has no server protection at all.** This is out of this standard's scope, but 85.1
    protects it locally only. Add `main` to a ruleset?
13. **Where the name grammar lives.**
    - In `pyforge.core.preserve_refs`, a kernel seam on the AD-73 `landing_evidence` precedent. That
      makes `spec-pyforge-core` a co-governor, and steward and the scripts can import it.
    - Or in `M/core/preserve_refs.py`, reached by others only through `marshal preserve`.
14. **Flagging.** May the CAP-287 producer stories ship behind the flag `pyforge.marshal.preserve_refs`,
    while the detector and conflict fixes (87.2, 87.6, 87.10) ship unflagged as `fix` stories, per
    `spec-feature-flag-governance` Q1/Q2?

---

## 9. Noticed in passing (out of scope; flag only)

- **Object store damage.** `.git/objects/73/fab1dc5a061a0bcbf000b35dcd034d83b20048` and `…/6d/4b7abee7186dc8f56d90f7601c8bb5e97849c2`
  are empty files, so `git fsck` reports them as corrupt. Repair them (re-fetch, or remove after
  checking reachability) before any `git gc`.
- **fleet-poll pushes `main`.** `scripts/fleet-poll-hourly.sh:21` runs `git -C <home> push origin
  main` from every loop home, with errors swallowed (`|| true`). It pushes the shared local `main` to
  `origin` on every tick.
- **Stale docstring.** `scripts/worktree_sweep.py`'s docstring still names `marshal retire` as "the
  marshal-native home for this logic". 87.1 records that the 2026-10-03 ruling made the sweeper the
  permanent home. The docstring and the how-to (`docs/how-to/manage-worktrees-with-bmad.md:46`) also
  understate the protected list (two prefixes vs four).
- **Loop homes registered as remotes.** `marshal-home` and `mason-home` are git remotes pointing at
  worktrees of the same repository, so 62 stale remote-tracking refs mirror shared refs.
