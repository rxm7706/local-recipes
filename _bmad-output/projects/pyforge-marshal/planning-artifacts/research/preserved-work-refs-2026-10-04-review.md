---
chain: pyforge-marshal
created: 2026-10-04
updated: 2026-10-04
status: final
type: architecture-review
title: "Preserved-work refs: independent architecture review"
companion: preserved-work-refs-2026-10-04.md
ruling: "2026-10-04 operator ruling: accept this review's recommended default for every open question (.claude/memory/project/2026-10-04-operator-ruling-preserved-work-refs-adopt-the-arc.md)"
---

# Architecture review: preserved-work refs (research and drafts, 2026-10-04)

> **Redacted in this tracked copy (2026-10-04).** The repository is public and the GitHub cache purge
> request is still the operator's step, so the three purged commit ids and the leaked-key file path
> are replaced by `<purged-1..3>` and `<leaked-key-file>`. The operator holds the originals
> (team memory, the 2026-07-24 history purge). Nothing else is changed.

- **Reviewer:** independent architecture reviewer (AGENTS.md guideline 8). I did not write the research.
- **Reviewed:**
  - `.worktrees/research-preserved-work-refs/_bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04.md` (the research, "R" below)
  - `…/preserved-work-refs-2026-10-04-drafts.md` (the drafts, "D" below)
  - Story specs 87.1 and 85.1 from `chain-sweeper-protected-refs`.
- **Read against:**
  - AGENTS.md;
  - marshal `ARCHITECTURE-SPINE.md`: AD-2, 9, 11, 12, 13, 17, 23, 24, 27, 29, 40, 46, 47, 48, 59, 73, 74;
  - `spec-pyforge-marshal/SPEC.md` (highest CAP is 286);
  - `spec-pyforge-steward/SPEC.md`: CAP-5, CAP-155, CAP-157 (highest CAP is 164);
  - `docs/governance/spec-one-chain-per-station/SPEC.md` CAP-11 and CHAIN-STANDARD §11;
  - the marshal PRD (`FR-234 = next free id`, `prd.md:3124`).
- **Method:** I ran read-only git and gh commands only. I edited nothing in the worktree or the primary checkout.

> **The state moved during the review.**
> - `main` advanced to `6e466546cf` ("Merge pull request #1816 from rxm7706/chain-sweeper-protected-refs"). **Stories 87.1 and 85.1 are now merged.** Both sit at ledger `backlog` with specs `ready-for-dev`, and no dispatch branch exists for either.
> - The research's "required changes before it lands" are now **amendments to merged, dispatchable specs**.
> - The two empty loose objects the research cites are **gone**: `.git/objects/73/` and `6d/` were modified at 05:17 local today. `git fsck --no-reflogs` now exits **0** in 30 s and lists 20,136 dangling commits.

---

## Verdict: adopt with changes

Candidate B's core is sound and I recommend keeping it:
- one durable, server-protected, annotated tag namespace on `origin`;
- upstream names left alone, with promotion plus `preserve_keep = 0`;
- legacy tags frozen;
- one declared protected list.

The research is unusually well evidenced. I re-derived 25+ of its numbers and they hold, with the drift noted below.

As drafted, though, the package has three blocking problems:
1. It would **cement already-purged secret content on the public `origin`** and push more unreviewed content into tags that cannot be deleted (B1).
2. Its central rule **contradicts AD-29's offline-durability amendment** (B2).
3. Its enforcement is still **keyed on names**, so the incident class that motivated it (hand deletion of *working* branches) stays open (B3).

The repo is **public** (`gh api repos/rxm7706/local-recipes` → `"visibility":"public"`), which makes B1 and the volume risk (M7) much sharper than the research assumes.

---

## Findings

### BLOCKER

**B1. Purged secret content is reachable from 23 public `rescue/*` tags. The plan freezes it, and the snapshot and migration path would publish more into tags that cannot be deleted.**

- **Evidence:**
  - `git for-each-ref --contains <purged-1>` returns 23 refs, all `refs/tags/rescue/dangling-20260723-*` and `-20260724-*`, and all 23 are on `origin` (checked against `git ls-remote origin`).
  - `git cat-file -e <purged-1>:<leaked-key-file>` succeeds. That commit holds the file that carried the leaked `sk-ant-` key. The key was reportedly rotated. The history rewrite purged commits `<purged-1>` / `<purged-2>` / `<purged-3>`, and all three are reachable from the same 23 tags. I did not print the file's contents.
  - These tags are the unpushed-work detector's printed remedy, run by hand the day after the purge. It re-preserved exactly the history the purge removed.
- **What the drafts would do:**
  - R §7.3 and D 85.1 put `refs/tags/rescue/**` under a deletion + update rule with `bypass_actors: []`.
  - D 87.3 / AC-2 snapshots *untracked* files and pushes them.
  - D 87.12 pushes 17 local-only `refs/attempt-preserve-dirty/*` snapshots, 3 local tags, `refs/backup/*` and `refs/bundle/*`.
  - Secret scanning push protection is on, but non-provider patterns are **disabled** (`security_and_analysis`).
- **Changes:**
  1. New **step 0, operator-gated, before any tag ruleset exists:** a purge audit of every legacy tag against the purged SHAs and paths. Purge the 23 tags with a committed manifest. Decide on a GitHub support request for cached objects.
  2. Add a **content gate** to the preserve verb (87.3) and to every promotion (87.4, 87.5, 87.12). Before any push it must:
     - refuse a commit that descends from a purge-listed SHA or carries a purge-listed path (the list is a tracked governance file);
     - run a secret scan over the snapshot's added blobs;
     - apply a per-file size cap, on bmad-loop's `failed_diff_max_mb = 5` precedent;
     - on a hit: keep the tag local (`pending`), never push it.
  3. 87.12 pushes previously local-only content only after the operator reviews the manifest row by row.
  4. Add a purge runbook with a **secret-incident fast path**: a temporary ruleset edit, delete, request a GitHub cache purge. R5's "purge is deliberately heavy" must not slow down a leak response.

**B2. AD-81, AC-7 and Story 87.7 contradict AD-29 F-14 (durability must not require the network).**

- **Evidence:**
  - AD-29 (spine:317-323) says: "That ref may be **local** — durability is a reachability property, not a network one". It also names the failure: "an offline operator's every teardown refuses and must be forced … That is precisely how a destructive-refusal gate gets trained away … it now fires only on work that is genuinely unreachable, not on work that is merely unpushed."
  - D's AD-81 says: "No process removes a working copy whose unique content no `preserve/` or `archive/` tag **on `origin`** holds". 87.7 refuses teardown on "a `loop/<slug>` ahead of `origin`". Both are the "merely unpushed" refusal AD-29 removed.
  - AD-81's own last bullet ("An offline preserve is a local tag reported pending") contradicts its earlier bullet.
- **Change:** split the predicate in AD-81, CAP-287 and AC-7:
  - **(a) Removing a local working copy** (a worktree, run dir, patch, local branch) requires the content to be reachable from a `refs/tags/preserve/` or `refs/tags/archive/` tag. A **local tag suffices**: refs are shared across worktrees and survive home removal.
  - **(b) An unpushed preserve** is reported preserve debt (AD-48), never a refusal.
  - **(c) Deleting a ref on `origin`** requires the tag on `origin`, confirmed by `ls-remote`.
  - Then declare `refs/tags/preserve/` as AD-29's "declared durable local ref". That realizes AD-29's third route, which is unimplemented today (`M/cli/deploy.py:15-25`: "no code anywhere in this package names a real mechanism for it yet"), and removes the conflict. Move it out of D's Out of scope.

**B3. The incident class is not closed. Enforcement stays keyed on names, and the losses were working branches.**

- **Evidence:** I re-derived R §2.8 from `gh api repos/…/activity?activity_type=branch_deletion&time_period=day`: 494 events, 464 names, 454 tips; 327 are ancestors of `main`, 29 reachable elsewhere, 98 reachable from nothing. The 98 by family: `bmad-loop/` 37, `attempt-preserve/` 15, `copilot/` 10, top-level 8, `marshal/` 5, `docs/` 5, `dispatch/` 5, `fix/` 4, `feat/` 3, `claude/` 2, `fleet/` 2, and five others. **83 of the 98 are not under any protected prefix.**
- **What enforces what, as drafted:**
  - the rulesets protect `loop/**`, `attempt-preserve/**`, `preserve/**`, `archive/**`, `rescue/**`;
  - 85.1 (amended) denies by those names;
  - the in-code guards cover only marshal and steward deleters.
- **What still passes:** a repeat of the 2026-10-04 cleanup (`git push --delete origin fix/x bmad-loop/…`) passes every layer. R2 ("No operation may make a commit unreachable") and R8 ("one rule for every mode … hand-driven sessions") are claimed but not delivered.
- **Modes missing from the R §2.6 table:**
  - cloud agents (Copilot cloud agent, Claude Code web, Devin), which produce remote-only `copilot/*` and `claude/*` branches (12 of the 98);
  - harnesses with no hook deny surface (Gemini CLI, Copilot CLI, Devin; AGENTS.md § Session guardrails). For those, the server ruleset is the only guard.
- **Change:** add a **reachability-guarded deletion rule**, separate from the name list:
  - Any branch or tag deletion through `git push --delete`, a `:refs/…` refspec, `git branch -D`, `gh api -X DELETE …/git/refs/…` or `update-ref -d` is denied when the ref's tip is not an ancestor of `refs/remotes/origin/main` and no `preserve/` or `archive/` tag contains it.
  - The denial names `marshal preserve tag` and the sweeper's `--retire` as the sanctioned forms.
  - The hook already shells out to git (`.claude/hooks/pre-shell.py:240-298`), so this is feasible.
  - It needs its own `session_denials` governance ruling (see M6).
- **Add to R §2.6 and AD-81:** the server ruleset cannot tell an agent from the operator (AD-27's trust model: agents hold the operator's credentials). So protecting every branch server-side is only possible with no bypass, and that would also block legitimate merged-branch cleanup. The guarded hook plus the guarded tools is the realistic ceiling, and AD-81 should say so.

### MAJOR

**M1. The pre-push hook runs `pr-preflight` on tag pushes. Preserve pushes will be slow, or refused when the tree is red.**

- **Evidence:** `scripts/pre_push_preflight.sh:46-58` skips only branch deletes (an all-zero sha) and `refs/heads/dispatch/*`. A `git push origin refs/tags/preserve/…` runs the full preflight on the cwd's tree and refuses on red (`:79-81`). A preserve is often taken *from a failing attempt's worktree*, so the push would be refused exactly when it matters.
- CAP-156 already says a tool that can prove a push is safe sets the journaled opt-out with that proof.
- **Change:** add a steward co-governed story, or amend 85.2: a tag-only push under `refs/tags/preserve/` or `refs/tags/archive/` is skipped and journaled, because it moves no branch. Alternatively, D must state that every producer sets `PYFORGE_PREFLIGHT_SKIP=1` with reason `preserve tag <name>`.
- Producers must push one explicit refspec per tag, and never use `git push --tags`, which would also push local-only junk such as `archive/recover-scribe-1-3`.

**M2. Live detector state changed. The detector now prints rescue-tag remedies for thousands of synthetic commits.**

- **Evidence:**
  - `fsck` is healthy: it exits 0, lists 20,136 dangling commits, and 19,412 of them are "marshal teardown merged-check (not a real commit)" (exact match with R).
  - `find_dangling` keeps commits whose diff against the parent touches more than `--min-files` (3) files. In a sample of 200 synthetic commits, 164 qualify. So a full `unpushed_work_check.py` run would now report **about 16,000** synthetic dangling commits, each with remedy `git tag rescue/dangling-… && git push origin …` (`scripts/unpushed_work_check.py:153-170`). That is the same remedy that minted the 682 tags and re-preserved the purged history.
  - The synthetic commits are still being created at 700–2,500 a day (committer dates 2026-09-30 to 10-04).
- **Changes:**
  1. Make 87.2 urgent. It should also exclude commits whose subject ends "(not a real commit)", and **stop printing any minting remedy** now ("report; do not tag"), not "until 87.3 lands". As written, 87.2 is `Deps: —`, yet its remedy AC names the 87.3 verb; that is a dependency mismatch.
  2. Land 87.10 with 87.2. A simpler 87.10 is worth considering: pin `GIT_AUTHOR_DATE` / `GIT_COMMITTER_DATE`, so repeated checks reuse one object per (tree, merge-base); or compute the patch-id from `git diff <merge-base> <tree> | git patch-id --stable`, with no commit object at all. Either is simpler than a temporary alternates directory.
  3. Correct R §0 item 5, R §4 item 1, R §9 and D's Dream text: the detector's code still fails open, but the live scan is no longer blind. The live risk is now the opposite one, a flood of remedies.

**M3. The protected list must be a union with the structural floor, and marshal must not hard-read the roster.**

- **Evidence:**
  - Merged 87.1 says: "The protected prefixes are read from `docs/governance/guild-roster.json` `protected_ref_prefixes` when that key exists … else from the script's own `PROTECTED_BRANCH_PREFIXES`". That is replacement.
  - D keeps the "fallback constant" semantics.
  - AD-47: "`loop/*` … are **structural** exclusions, never policy-configurable".
  - AD-27: an allowlist may only be narrowed.
  - Under replacement, a roster edit that drops `refs/heads/loop/` makes `loop/*` sweepable.
- **Changes:**
  - The effective list is the code-declared structural floor (`refs/heads/loop/`, `refs/heads/main`, all of `refs/tags/`) **plus** the roster entries. The roster can only add. A meta-test pins the floor.
  - Marshal is a portable product that also runs in other repos. Its in-code deleters should receive the list through a policy layer with provenance (AD-10, AD-16), not open `docs/governance/guild-roster.json`. The sweeper is a repo script and may read the roster directly.
  - Add a per-entry `scope` field (`origin`, `local` or `both`). `refs/heads/attempt-preserve/` differs between local and origin (see M4).

**M4. `refs/heads/attempt-preserve/` is classified inconsistently, and promoted local scratch is never retired.**

- AD-81 calls engine refs **scratch** ("promoted … never pushed"), and R §7.3 B says working refs are "retired freely once proven". Yet R §7.3 and D 85.1 keep `refs/heads/attempt-preserve/` protected. The hook would then deny the local `git branch -D attempt-preserve/x` that retirement needs.
- With `preserve_keep = 0` nothing ever removes these refs locally, and D has no story that retires them. 87.8 does not mention it.
- **Changes:**
  - 87.12 phase 0 converts the 3 kept `origin` branches to `preserve/` twins.
  - Then drop `refs/heads/attempt-preserve/**` from ruleset 24451573 (Q3) and from the hook list.
  - Add an 87.8 AC: retire local engine scratch in both families only when its `preserve/` tag exists, on `origin` or pending per B2.

**M5. The AD-47 amendment contradicts AD-81's own "unique" test.**

- AD-47 already allows retirement only when the content is reachable in the integration branch **by patch-id**. By AD-81's definition ("Unique is judged by ancestry, then patch-id, then tree"), such a branch has nothing unique. Yet the AD-47 amendment demands an unconditional `archive/` twin.
- **Change:** one criterion everywhere, in AD-47, AD-81, 87.1 change #5 and 87.6. Write an archive twin **iff deleting the ref would make commits unreachable**, that is, when the tip is not an ancestor of `refs/remotes/origin/main` and no other durable ref contains it. A squash-proven branch gets a twin, because its commits orphan. An ancestor branch does not.
- Keep D's 87.1 change #5. The merged 87.1's DELETE verdict "PR closed and the story's ledger row is `done`" can delete never-landed content, because the story may have landed through a different PR.

**M6. The 85.1 amendment exceeds the operator's governance ruling, and both stories are now merged.**

- The `session_denials` list is closed and "adding to it is a governance act". The 2026-10-04 ruling (steward memlog on `main`) covers deleting `loop/`, `attempt-preserve/`, `recover/`, `rescue/` and `main` branches, and removing `~/.bmad-loops` homes.
- D widens it to tags, `update-ref -d`, `fetch --prune-tags`, `push --mirror`/`--prune`, `rm -rf` of homes, and `gh pr merge --delete-branch`. That needs a **new ruling**.
- **Changes:**
  - Land 85.1 as ruled (a fix, unflagged), changing only the roster key's shape, so 87.1 and the parity check read the M3 structure.
  - Put the widened forms and B3's reachability guard in a new steward story with its own ruling.
  - 87.1 and 85.1 are dispatchable now (ledger `backlog`), so **hold their dispatch** until the amendments land in their story specs' change logs. Otherwise a drain implements `--retire` as "delete", which ruleset 24451573 refuses.
- Two more corrections:
  - `git fetch --prune-tags` deletes tags only together with `--prune` or `fetch.prune`. A config value (`fetch.pruneTags=true`) bypasses any command matcher. Say so.
  - A hook matcher is a denylist (AD-17's caution applies). The server ruleset is the guarantee, and the hook is defence in depth.

**M7. Machine producers can mint tags that cannot be deleted, at runaway volume.**

- This repo's own marshal produced 19,412 synthetic objects in about five days.
- Once a preserve namespace is append-only, public and has no bypass, a looping producer can mint thousands of tags that only a ruleset change can remove.
- The normal rate is fine: 120 failed dispatch patches (97 in September, 23 on Oct 1–4) works out to about 1–2k tags a year.
- **Changes:**
  - Add to 87.3: dedup by tree. A preserve for the same story whose tree equals an existing preserve's tree is a no-op.
  - Add a per-run and per-story cap. Exceeding it is a HARD finding and the tag stays local.
  - Add to the 87.4 and 87.5 ACs: a re-run of the same terminal verdict adds no second tag.

**M8. Decide the grammar's home now: it belongs in `pyforge.core`.**

- **Evidence:**
  - The `pyforge-steward` env has `pyforge-core` but **not** `pyforge-marshal` (`pixi.toml` feature `pyforge-steward`). So 85.3, done "through the `marshal preserve` CLI", cannot run in steward's own env, and station code must not import marshal.
  - The scripts (`worktree_sweep.py`, `missing_preserve_check.py`, `unpushed_work_check.py`) are stdlib-only and tested in `pyforge-ci`, which has no `pyforge-core`. Precedent for reaching core from a script: `scripts/deferred_work_intake.py:32-35` inserts `src/shared/packages/pyforge-core/src` into `sys.path`.
  - AD-73 put the analogous grammar in core.
- **Changes:**
  - Resolve Q13 in favour of `pyforge.core.preserve_refs`. It must be stdlib-only and importable by path. It holds render/parse, the tag writer and the snapshot. Marshal keeps the verb.
  - `spec-pyforge-core` CAP-12 becomes a required co-governor, not an "only if". Add it to the Spec's co-governing list and to every story's surface reconcile.

**M9. The verification oracles name a pixi task that does not exist.**

- **Evidence:** `scripts-suite` is a CI **job** (`.github/workflows/detectors.yml:73`), not a pixi task. `grep -c scripts-suite pixi.toml` → 0 task definitions; the local twins are `pixi run -e pyforge-ci pyforge-doctor-scripts-test` and `pixi run -e pyforge-doctor pyforge-doctor-aggregate-scripts-test`.
- Both D's CAP-287 field 4 and the merged 87.1 spec (Verification) use `pixi run --frozen -e pyforge-guild scripts-suite`. A gate running that command is unevaluable (AD-8).
- **Change:** replace it with those two tasks in D and in 87.1's spec.

### MINOR

1. **Dated tag names vs AGENTS.md § Dates.** That section says "A git tag is a version alias, not a date". The preserve grammar puts `YYYY-MM-DD` in tag names, and R12 cites the same section without noting the tension.
   - Preferred: drop the date from the name. The tagger date is in the tag object: derive, don't declare. The name becomes `preserve/<slug>/<N.M>/<producer>-<sha8>`.
   - Otherwise, AGENTS.md needs a one-line scope note. That is a governance edit (parity and currency checks).

2. **The "on origin" check across clones.** A plain `git fetch` auto-follows only tags that point into fetched history. Preserve tags point at commits *off* the branches, so other clones never receive them.
   - 87.9 and AC-9 must define "on origin" as `git ls-remote --tags origin 'refs/tags/preserve/*'`, or an explicit fetch refspec, never local tag presence.
   - Note that `git clone` (not `--single-branch`, not `--no-tags`) downloads every tag and its objects. Document `--no-tags` for contributors who do not want them.
   - The `git describe` risk is low here: no repo-owned package uses scm versioning. Still, recommend `--exclude 'preserve/*' --exclude 'archive/*' --exclude 'rescue/*'` wherever describe is added.

3. **Archive paths are ambiguous.** "original ref path without `refs/heads/` or `refs/tags/`" maps a branch and a tag of the same short name to one twin. Today a branch `archive/crewai-toolkit-wip-2026` would map to `archive/archive/…`.
   - Use `refs/tags/archive/heads/<branch>` and `refs/tags/archive/tags/<tag>` for new twins; the legacy 45 stay as they are.
   - Restrict creation of `refs/heads/preserve/**` and `refs/heads/archive/**` with a ruleset, so R12 is enforced and not just stated.

4. **AC quality.**
   - AC-1's meta-test ("No module … matches the string `preserve/`") would fail on today's tree: 7 files and 22 lines already match `attempt-preserve/`. Scope it to `refs/tags/preserve/` or a leading-segment match.
   - AC-12 ("every new rule has a mutation test") has no oracle. Make it a review checklist item, or name a mutation tool and command.
   - Boundary "Never push a branch that the declared list forbids updating": the list forbids *deletion* of branches. Reword.
   - Give the preserve-debt findings codes (AD-15).

5. **Story sizing and order.**
   - 87.3 is L, not M (grammar, verb, port, adapter, MCP face, snapshot, flag). Split it: 87.3a is the core grammar and writer (M8); 87.3b is the CLI and MCP face.
   - 87.8 mixes CAP-287 work with hygiene fixes. Stale-lock detection and orphan directories should be an unflagged `fix`.
   - Split 87.12:
     - 87.12a: operator-gated, **no code dependency**, done now. Local annotated archive tags for the 98 + 8 tips (no outward write), pushed after the B1 content review.
     - 87.12b: legacy promotion, after 87.3.
     - Context: only 2 of the 98 tips are loose objects. But the loose-object count is 7,718, above `gc.auto`'s default of 6,700, so `git gc --auto` can fire on routine commands. Pausing auto-gc locally (`gc.auto=0`) until 87.12a is done is the operator's choice.

6. **`preserve_keep = 0` should ship now as an unflagged one-line render fix** (`M/adapters/harness_bmadloop.py:392`, plus the AD-78 pin tests). It should not wait behind the flag in 87.4. Verified upstream: `keep <= 0` means "never prune" (`BL/verify.py:5805-5826`, `BL/policy.py:543-549`).

7. **Promotion should reconcile, not only react to events.** 87.4 promotes on four journal events. Add a scan of `refs/heads/attempt-preserve/*` and `refs/attempt-preserve-dirty/*` that promotes anything unpromoted (AD-21). That covers bare bmad-loop runs, missed events and upstream event renames (AD-78). Resolve each tag's target with `git rev-parse` of the ref, never from the sha the journal line prints (AD-9).

8. **Steward corrections.**
   - CAP-157, not CAP-155, owns "the recorded branch is deleted only when it is on the source … the kept branch is reported". Amend CAP-157.
   - `.steward/workspace-archive/` holds **26 `.landed.txt` notes and 0 tarballs**, not 26 tarballs (R §2.2), so 85.3 is low priority.
   - 85.3 says the tarball keeps "gitignored or untracked bytes", while 87.3 snapshots untracked files. Pick one. Under B1's gate, untracked files go in the snapshot only after the scan passes.

9. **Citation completeness.**
   - AD-81 should cite AD-11, because tags under `refs/tags/preserve/` and `refs/tags/archive/` are a new marshal write target outside the four AD-11 lists.
   - The AD-40 one-liner also needs a PRD FR-59 consequence line.
   - The spine and PRD need their re-stamp currency sections (team memory: an old PRD or spine plus a new CAP turns pr-preflight red).
   - Say "mirrors CAP-11's shape" rather than "carries CAP-11 … to refs". CAP-11 belongs to a governance Spec that D does not amend.

10. **Not a defect.** "AD-47's `rescue/*` exclusion is not in code" (`M/core/retire.py:53`) is vacuously harmless: retire's candidates are only `TaskPhaseSnapshot.branch` values, never tags. Restate it in R §0 and R §3 as a documentation and code mismatch, not a gap.

11. **Candidate C critique.** "Branches are mutable by design" overstates it: branch rulesets support restrict-updates and block-force-pushes too. B still wins, on listing noise, PR-head pollution and branch-targeted tooling.

12. **Research drift and omissions to correct.**
    - The §2.8 family list omits the two largest families: top-level 144 and `attempt-preserve/` 33.
    - Local heads are now 30, remote-tracking refs 81, `--branches-only` unpushed findings 5 (not 8), dangling commits 20,136, and fsck takes 30 s.
    - 6 of the 8 attempt-preserve tips counted "reachable from no origin ref/tag/branch" survive only through local `refs/attempt-preserve-dirty/*`. bmad-loop's prune would delete those refs once a family exceeds 20, which strengthens M4 and minor 6.

13. **CI side effect (unverified).** `.github/workflows/copilot-setup-steps.yml` has a `push` trigger filtered only by `paths`, and GitHub says "Path filters are not evaluated for pushes of tags". Check whether each preserve tag push starts that workflow, and add `branches: ['**']` if it does.

14. **Missed producer.** `scripts/fleet-poll-hourly.sh:15-21` runs `pull --rebase --autostash origin main` inside each loop home. That rewrites `loop/<slug>`, which contradicts AD-46's "never a rewrite", and leaves pre-rebase commits dangling. Add it to R §3 and §9 next to the `push origin main` note.

15. **Retiring preserves.** Doubling tags (an `archive/preserve/…` twin per retired preserve) only labels state. Derive the state instead: `landed` when the commit is an ancestor of `origin/main`, `retired` when a tracked retirement ledger lists it. D 87.1 change #4 is self-contradictory ("becomes a tracked file. It stays under `--preserve-dir`", which is `~/.local/state`). The annotated archive tag is the record; only the *purge* manifest must be tracked.

16. **Ruleset hygiene.** Add `non_fast_forward` to `refs/heads/loop/**`; today a force-push can still rewrite `loop/*`. `marshal refresh` is fast-forward only, so this is compatible. Keep R's Q12 (`main` has no protection at all; `rules/branches/main` → `[]`).

---

## Answers to the review questions

### Tags vs protected branches

**Tags are the right primitive.**
- They are immutable by design and annotated in-band.
- GitHub rulesets apply creation, update, deletion and force-push rules to tags as well as branches. The docs' rule text says "branches or tags"; with an empty bypass list `current_user_can_bypass` is `never`, and only an admin editing the ruleset can lift it.
- They stay out of branch and PR-head listings and out of `--merged` sweeps.

**Costs, all acceptable once mitigated:**
- clone downloads every tag (minor 2);
- `git fetch` never auto-follows them, so readers must use `ls-remote` (minor 2);
- the tag list is noisy and the repo is public (B1, M7);
- pushes pass through the pre-push hook (M1).

Expected volume is about 1–2k tags a year, which git and GitHub handle comfortably.

### Does the rule hold in every mode?

| Mode | As drafted | Gap or fix |
|---|---|---|
| bmad-loop bare | Prune stopped by `preserve_keep = 0`. No promotion without a supervisor, so refs stay local | Reported as debt only when status runs on that home. Promotion by reconcile scan (minor 7) |
| spin | Yes, after 87.4 and 87.7 | B2: a local tag must suffice for teardown |
| dispatch, every harness profile | Yes for failed, stopped and blocked. Committed work is already pushed pre-verify | B1 content gate for untracked files. M1 for the push |
| drain | Records only | OK |
| bmad-build-auto bare, bmad-build | **Instruction only** (`persistent_facts`). bmad-build says "NEVER auto-push" (`step-05-present.md:9`) | The fact creates a *local* tag (pending). Pushing is the operator's step |
| bmad-build-auto under dispatch | Supervisor and auto-checkpoint already cover it | A governed session pushing to a no-delete namespace sits badly with AD-9 and AD-32. Let the supervisor push |
| hand `land/*` rebuild | Instruction only (convention text) | Covered by the B3 guard on deletion |
| steward workspace | CAP-157 already keeps unmerged branches locally | 85.3 adds `origin` durability; low urgency |
| Claude Code and Cursor agent worktrees | Harness-owned deleters bypass every check. The branches are local-only | Sweeper stale-lock handling (87.8) plus the B3 guard for git commands run inside sessions. State this limit |
| Cloud agents (Copilot cloud, Claude Code web, Devin) | **Missing from R** | Remote-only branches: only the B3 guard or the server ruleset protects them |
| Hand-rolled cleanup (the incident) | **Not closed** | B3 |

### Conflicts with existing ADs, FRs, CAPs and invariants

**Real conflicts:**
- AD-29 F-14 (B2);
- AD-47 "never policy-configurable" against replacement semantics (M3), and AD-47 against the AD-81 "unique" test (M5);
- AGENTS.md § Dates (minor 1);
- the 85.1 governance ruling's scope (M6);
- the CAP-156 pre-push contract (M1).

**No conflict:**
- AD-27: the list only narrows, once M3 makes it a union;
- AD-40: D amends it;
- AD-24 and AD-73: tags never appear in merge subjects, and `landing_evidence` enumerates no refs (verified: no `for-each-ref`, `--all` or `ls-remote` in `pyforge/core/landing_evidence.py`);
- AD-59: legacy frozen, not migrated;
- the Tier rules: patches remain Tier-3 conveniences, and the record moves to git.

### The one-list design and its owner

- **The design is right**, with three structural changes:
  1. a union with a code floor that the roster can only add to;
  2. a `scope` field per entry;
  3. a separate reachability rule for everything not on the list (B3).
- **Owner: steward's roster.** It already owns `session_denials`, and the list is a governance act.
- **How each consumer reads it:**
  - marshal's in-code deleters through a policy layer (M3);
  - the sweeper and the hook directly;
  - the derived ruleset JSON byte-checked against the roster (AD-12).
- Steward should own the runtime parity detector, keeping roster, hook and rulesets together.

### "Retire = archive twin, never delete" in the long term

- **Sound for branches**, when twins are written only where reachability would be lost (M5).
- **For preserves, derive the state** rather than doubling tags (minor 15).
- **Growth** is bounded by the failure rate and acceptable.
- **The purge path** is correctly heavy, but it needs a committed manifest format, the purge-list governance file (B1), and a secret-incident fast path.

---

## Open questions for the operator, deduplicated and ordered by urgency

1. **Security, now.** Purge the 23 `rescue/dangling-2026072{3,4}-*` tags on public `origin` that reach the purged commits `<purged-1>`, `<purged-2>` and `<purged-3>` (the leaked-key file and a second purged file), with a committed manifest, before any tag ruleset exists? Request a GitHub cache purge? Re-confirm the key rotation.
2. **Hold dispatch of 87.1 and 85.1** (merged at `6e466546cf`, ledger `backlog`) until their specs carry the amendments? (M3, M5, M6, M9)
3. **Stop the detector's minting remedy now**, as an unflagged hotfix in 87.2? fsck is healthy again, so it would print about 16,000 `git tag rescue/dangling-…` remedies for synthetic commits.
4. **Re-preserve the 98 + 8 orphaned tips:** approve local annotated `archive/…` tags now (no outward write), and pushing them only after the B1 content review? Optionally pause local auto-gc meanwhile (7,718 loose objects is above the 6,700 threshold).
5. **Content policy for preserves on a public repo.** Include untracked files at all? Which secret scan, what size cap, what purge-list file? May the local-only snapshots (17 `refs/attempt-preserve-dirty/*`, 3 local tags, `refs/backup/*`, `refs/bundle/*`) be pushed after row-by-row review, or only kept locally?
6. **Durability predicate.** A local preserve tag suffices to remove a working copy, with the push reported as debt (recommended, per AD-29). And make `refs/tags/preserve/` AD-29's declared durable local ref?
7. **New governance ruling A:** a reachability-guarded deletion denial for *every* branch and tag (B3).
8. **New governance ruling B:** widen the protected-ref denial to tags, `update-ref -d`, prune and mirror forms, and `rm` of homes (M6). 85.1 itself lands as already ruled.
9. **Server settings (outward):**
   - create the tag ruleset for `preserve/**` and `archive/**` (and `rescue/**` only after Q1) with `bypass_actors: []`;
   - add `non_fast_forward` to `loop/**`;
   - restrict creation of `refs/heads/preserve/**` and `refs/heads/archive/**`;
   - enable non-provider secret-scanning patterns?
10. **Retirement criterion.** Twin only when commits would become unreachable (recommended), or always? Retire preserves by derived state or a tracked ledger (recommended), or by `archive/` twins?
11. **The 3 `attempt-preserve/*` branches.** Create `preserve/` twins, then drop `refs/heads/attempt-preserve/**` from ruleset 24451573 and from the hook list?
12. **Grammar home.** `pyforge.core.preserve_refs`, stdlib-only, making `spec-pyforge-core` a co-governor (recommended), or marshal-only?
13. **Pre-push hook.** Skip `refs/tags/preserve/` and `refs/tags/archive/` pushes in steward's hook (recommended), or have every producer set `PYFORGE_PREFLIGHT_SKIP` with a reason?
14. **Dated tag names.** Drop the date from the name (recommended), or amend AGENTS.md § Dates?
15. **Ship `preserve_keep = 0` now** as an unflagged fix?
16. **Flag split.** CAP-287 producers behind `pyforge.marshal.preserve_refs`; 87.2, 87.6 and 87.10, plus the stale-lock/orphan-dir fix and `preserve_keep = 0`, unflagged?
17. **Home of the ruleset parity check:** steward (recommended) or doctor?
18. **Legacy details.** The two flattened local `archive/` tags (R Q4); `refs/backup/pre-split-1787762347` and `refs/bundle/pyforge-pages` (R Q5); drop the `recover/**` and `rescue/**` branch patterns (R Q6).
19. **Later decisions.** Purge classification for the rest of `rescue/*` (R Q11); protection for `main` (R Q12); an upstream bmad-loop PR (R Q10).

---

## Claims checked

### Verified (command → result)

| Claim (R/D) | Evidence |
|---|---|
| bmad-loop renders `preserve_keep = 20` | `M/adapters/harness_bmadloop.py:392` |
| Upstream prune owns the prefix; `keep<=0` never prunes; runs at run start | `BL/verify.py:5805-5826` (quote matches); `BL/policy.py:543-549, 1433`; `BL/engine.py:944` `_prune_preserve_refs()` |
| Upstream name and event names | `BL/recovery_flow.py:56-58`, `:1584`, `:1592`, `:1738`, `:1512/1520`; `BL/worktree_flow.py:4023`; defer notice "The pointer is a name, not a promise" `BL/engine.py:7650-7652` |
| The detector fails open | `scripts/unpushed_work_check.py:65-71` returns `""` on non-zero |
| Synthetic merged-check commits | `M/adapters/vcs_git.py:490-512`; 19,412 of 20,136 dangling (`git log --no-walk --stdin` subjects) plus 35 merge-tree previews |
| `marshal land` deletes `loop/<slug>` by default | `M/cli/land.py:438` head `loop/{slug}`, `:507` `delete_branch = landing_branch_retirement`; `M/core/policy.py:611` default `True`; `M/adapters/forge_gh.py:375-376` `--delete-branch`, `:378-387` raises after merge |
| Teardown force-deletes the branch | `M/cli/init.py` ~`:2680` `vcs.delete_branch(..., force=True)` after removing the worktree and nested worktrees |
| Readers check only local `refs/heads` | `scripts/missing_preserve_check.py:146-160`; `scripts/bmad_loop_baseline_drift_check.py:111-118`; `scripts/fleet_picture.py:790-795` |
| Sweeper protections | `scripts/worktree_sweep.py:65` prefixes, `:189` KEEP locked, `:197-200` attempt-preserve rule |
| Intent-gap preserve copies upstream naming and is local | `M/supervisor/intent_gap_preserve.py:129` docstring, `:139`, `:291-295` `branch -f`; stage push covers only the station branch and `task.branch` (`M/supervisor/__main__.py:1795-1815`) |
| Dispatch preserves only on FAILED | `M/dispatch_supervisor/__main__.py:2735` condition |
| retire excludes only `loop/` | `M/core/retire.py:53, 97-105` |
| Ruleset 24451573 | `gh api …/rulesets/24451573`: branch target, `[deletion]`, four `refs/heads/*/**` patterns, `bypass_actors: []`, `current_user_can_bypass: never`, created 04:29 −05:00 |
| `main` unprotected; merge settings | `branches/main/protection` 404; `rules/branches/main` `[]`; `delete_branch_on_merge: false`, `allow_squash_merge: false` |
| Remote ref counts | `git ls-remote origin`: 2,590 lines; 19 heads; 749 tags; 5 peeled; 698 `rescue/`; 682 `rescue/dangling-`; 45 `archive/` |
| All 8 `loop/*` at `71c3747e91`, an ancestor of `main` | ls-remote plus `merge-base --is-ancestor` |
| Kept `attempt-preserve` unique commits: 1,014 / 1 / 17 | `rev-list --count origin/main..<tip>` |
| Incident: 494 events / 464 names / 454 tips / 487 in hour 09; 33 attempt-preserve and 8 loop at 09:11; 30 at 09:23 | activity API, paginated |
| 454 tips → 327 ancestors / 29 elsewhere / **98 none**; family breakdown | rev-list reachability sets (origin refs, local branches and tags) |
| 30 retired (29 unique) → 14 ancestors / 8 reachable from no ref / 7 elsewhere; the 8 SHAs | `for-each-ref --contains` and `merge-base` |
| 17 dirty refs, 16 not on origin; 3 local-only tags unreachable; 745 legacy tags lightweight | for-each-ref and origin reach set |
| 149 rescue tags are synthetic; 212 are stash commits | subject classification |
| Agent worktrees locked by pid 9993 (alive, a claude-code process); 6 empty Cursor dirs; empty `.retired-worktrees-20260822` | `git worktree list --porcelain`; `find`; `ps` |
| Claude Agent worktree "auto-cleaned if unchanged" | this harness's Agent tool definition |
| bmad-build / bmad-build-auto revert and no-push text | `bmad-build-auto/step-04-review.md` ~`:71-72`, `:115`; `bmad-build/step-04-review.md:63-64`; `step-05-present.md:9`; both `customize.toml` have `persistent_facts` |
| `--restore-patch` contradiction | `bmad-loop-resolve/SKILL.md:200-207` vs `.claude/memory/reference/bmad-loop-escalation-and-landing-traps.md` (2) vs `docs/how-to/troubleshoot-bmad-agent-loops.md:38` |
| `gh pr merge --delete-branch` treats 422 or 404 as already deleted | `cli/cli` `pkg/cmd/pr/merge/merge.go` (`isAlreadyDeletedError`) |
| Tag rulesets support creation, update, deletion and force-push rules | GitHub docs, *Available rules for rulesets* |
| Numbering free | marshal CAP-286, FR-233 (`prd.md:3124` "FR-234 = next free id"), AD-80; steward CAP-164; core spec CAP-11 |
| fleet-poll pushes `main` from homes | `scripts/fleet-poll-hourly.sh:20-21` (and `:18` `pull --rebase`, which R does not mention) |

### Could not verify, or no longer true

- **No longer true:** "`git fsck` exits 1 on two empty loose objects". Now it exits 0 and both files are gone, modified at 05:17 local. Plausibly true when the research measured it.
- **No longer true:** "unpushed_work_check reports 8 unpushed branches". Now 5.
- **Not true:** "26 steward tarballs". They are 26 `.landed.txt` notes and 0 tarballs.
- **Not verified:** that a git worktree lock outlives the process. Pid 9993 is alive; this is git's documented behaviour, but I did not observe it.
- **Not verified:** the HTTP status GitHub returns when a ruleset refuses a REST ref delete. Likely 422, which `gh` would report as success; untested, because the call would be destructive if allowed.
- **Not verified:** GitHub's retention period for unreferenced objects.
- **Not verified:** that Cursor created the `~/.cursor/worktrees/*` directories (they are empty and the names look like story slugs).
- **Not verified:** whether tag pushes trigger `copilot-setup-steps.yml`.
- **Not re-derived:** the 37 inconclusive `bmad-loop/` patch-id result, the 153/148/12 rescue content split, "≥ 300 merged dispatch PRs", and "146 synthetic tags share a reachable tree".
