# RESUME — pyforge-atlas Epic 10 (post-audit remediation)

**Written 2026-07-29 13:35 CDT, on an unplanned shutdown, mid-story.**
Epic 10 is **5 of 6 done**. Story I5 (10.6) was interrupted during its review pass.

---

> ## ✅ CLOSED 2026-07-29 — Epic 10 is 6/6, all merged, gates green
>
> I5 (10.6) resumed after the shutdown and completed. `kedro-test` **901 passed / 0 failed**,
> `kedro-catalog-check` 47. D1–D6 verified in the code; AD-23 re-promoted **with four stated
> boundaries**. Merged into `fix/atlas-post-audit-epic-10`; tag `checkpoint/epic-10-complete`.
>
> **The resume instructions below are HISTORY.** What remains is closeout only:
> `DW-I4-1` + `DW-I5-1` (both stories finalized on a spent review budget — see the ledger),
> the CFE Rule-2 retro, and push + the `maintenance` label. Nothing is pushed.


## Start here

```bash
cd ~/.bmad-loops/pyforge-atlas
pixi run --frozen -e local-recipes bmad-loop status          # see the interrupted run
pixi run --frozen -e local-recipes bmad-loop resume 20260729-112237-3139
```

If `resume` refuses (the tmux session is gone after a reboot, which is expected),
the work is **not** lost — see § "If resume will not take" below.

## Where everything is

- **Branch:** `fix/atlas-post-audit-epic-10` — 23 commits ahead of `main`, **never pushed**.
- **Loop home:** `~/.bmad-loops/pyforge-atlas` (a git worktree on `loop/pyforge-atlas`).
- **Interrupted run:** `20260729-112237-3139`, story `10-6-make-run-admission-real-or-stop-claiming-it`.

### Checkpoint tags — the safety net

| Tag | Points at | What it holds |
|---|---|---|
| `checkpoint/i5-10-6-wip` | `10db136ad8` | **I5's in-flight work.** dev complete + review-1 partial |
| `checkpoint/epic-10-5of6` | `94ea044f14` | Epic 10 at 5/6, all gates green |
| `checkpoint/i4-10-5-done` | `ff6e481117` | I4 merged green |
| `checkpoint/i4-10-5-review-3` | `6696543a68` | I4's pre-merge history (its branch was auto-deleted — this tag is the only copy) |

**The tags matter.** bmad-loop runs with `delete_branch = true` and
`auto_clean_on_finish = true`: I4's story branch and worktree were both destroyed after
its merge, and only the tag preserved the intermediate commits. Do not prune these.

## Story status

| Story | Key | State |
|---|---|---|
| I0 | `10-1-restore-atlas-dependency-completeness` | done |
| I1 | `10-2-truth-up-the-spec-kernel-and-its-companions` | done |
| I2 | `10-3-uniform-story-spec-frontmatter-…` | done |
| I3 | `10-4-preserve-null-identity-under-pandas-3-0` | done, merged |
| I4 | `10-5-stamp-advisory-data-with-its-build-provenance` | done, merged |
| **I5** | `10-6-make-run-admission-real-or-stop-claiming-it` | **INTERRUPTED mid review-1** |

Last known green gates (before I5 started): `kedro-test` **803 passed / 0 failed**,
`kedro-catalog-check` **47 passed**.

## What I5 had already done when the machine went down

Two commits on `bmad-loop/20260729-112237-3139/10-6-…`, both captured by
`checkpoint/i5-10-6-wip`:

- `5ace46d901` — "atlas: make run admission real (AD-23, AUD-ATLAS-046)" (the dev pass, complete)
- `10db136ad8` — WIP: review-1's in-flight edits, committed by hand before shutdown

Files touched: `admission.py`, `settings.py`, `tests/test_admission.py`, plus
`ARCHITECTURE-SPINE.md`, `deferred-work-ledger.md` and `SPEC.md` — meaning **D6's AD-23
re-promotion was already underway**.

> **The WIP commit has NOT passed any gate.** No verify ran against it. Treat it as
> unproven until `kedro-test` and `kedro-catalog-check` are re-run.

## Verify I5 against D1–D6 before trusting it

D1–D6 are **binding ACs** in `planning-artifacts/epics.md` § Story I5, closed by
operator decision *before* the story was drafted. Check the code, not the loop's verdict —
I4's first drive shipped a faithful implementation of the wrong contract and had to be
reverted, and a "done" verdict did not catch it.

- **D1** file lock via `filelock` (already in-env). NOT a DB lock, NOT the Dagster run-queue.
- **D2** enforced in a Kedro hook in `settings.HOOKS`; acquire in `before_pipeline_run`,
  release in **both** `after_pipeline_run` **and** `on_pipeline_error`.
  Admission logic must NOT appear in `mcp/`, `orchestration/definitions.py`, or node bodies.
- **D3** reject fast with a typed error naming the locked dataset(s), holder run id and hold
  start; blocking wait only via explicit opt-in with a finite timeout.
- **D4** lock the pipeline's **declared output dataset set**, one lock per dataset, acquired
  in **sorted name order** (deadlock avoidance). Disjoint pipelines must still run concurrently.
- **D5** stale locks record holder PID + start time and are **reclaimable when the PID is dead**.
- **D6** on green, re-promote AD-23 to its full form in `ARCHITECTURE-SPINE.md` and correct the
  retracted docstring in `orchestration/definitions.py`.

**Gate:** `kedro-test` + `kedro-catalog-check`, **plus a real TWO-PROCESS concurrency test**
— a second OS process, not a thread and not a mock. A threaded test passes against a lock
that provides no cross-process exclusion at all, which is the whole defect.

## If resume will not take

Nothing is lost; re-drive from the checkpoint.

```bash
cd /home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes
git log --oneline checkpoint/i5-10-6-wip          # the work is here
# option A: cherry-pick / merge the two commits onto fix/atlas-post-audit-epic-10, then
#           finish by hand against D1-D6 above
# option B: reset the story to backlog in the sprint feed and re-run the loop clean:
#           edit implementation-artifacts/sprint-status.yaml ->
#             10-6-make-run-admission-real-or-stop-claiming-it: backlog
cd ~/.bmad-loops/pyforge-atlas
pixi run --frozen -e local-recipes bmad-loop run --story 10-6 --max-stories 1
```

A stale worktree from the killed run may need reaping first:
`pixi run --frozen -e local-recipes bmad-loop clean` (and see the auto-memory note that a
failed `git worktree remove` still de-registers the worktree).

## Traps that already bit this effort — do not re-learn them

1. **The loop cannot see a session blocked on a PROMPT.** I4's review sat 2.5 h at a
   "Fable 5 limit reached / continue on credits?" dialog while `status` cheerfully read
   `review-running`. Both adapters are now pinned to `opus` (committed, with reasons).
   Diagnose a suspected stall with `tmux capture-pane`, not with `bmad-loop status`.
2. **`max_tokens_per_story = 2000000` does not bite.** I4 ran to 14.9 M weighted and was
   never cut off. Do not rely on it as a budget guard.
3. **Story keys must match `^(\d+)-(\d+)([a-z]?)-(.+)$`.** Atlas's original spec-ID keys
   (`i3-…`) were silently ignored — `validate` read "1 stories, 0 actionable". Only
   Epic 10's six keys were renamed; waves A–H still use spec IDs and are still ignored
   (harmless, they are all done).
4. **Tier-3 is gitignored and this project has already lost data there.**
   `implementation-artifacts/` holds story specs and `deferred-work.md`; promote anything
   new into `planning-artifacts/specs/` and `planning-artifacts/deferred-work-ledger.md`.
   Current state: **0 unpromoted specs**, ledger at **53 entries**.
5. **The offline gate needs a stub credentials file.** `tests/orchestration/conftest.py`
   seeds `conf/local/credentials.yml` if absent — without it `kedro-test` cannot COLLECT
   in a fresh clone or worktree. Do not "fix" this by putting stubs in `conf/base`.

## After I5 lands

1. Merge the loop branch back into `fix/atlas-post-audit-epic-10`, re-run both gates, tag.
2. Set `epic-10: done` in `implementation-artifacts/sprint-status.yaml`.
3. **`DW-I4-1`** (tracked ledger) — story 10.5 closed on a spent review budget, not on
   convergence; an independent follow-up review of `provenance.py` + the `read_dataset`
   envelope against C1–C6 is still owed.
4. **CFE Rule-2 retrospective** (CLAUDE.md) — the effort surfaced several reusable findings:
   a verify gate that could not run in the worktrees the loop itself creates; a spec
   asserting a safety property the code never had; a contract that made a timestamp
   meaningless; the prompt-blocked-session blind spot.
5. **Push + PR** — needs the `maintenance` label (nothing here touches `recipes/`):
   `gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance`.
6. Revert `[adapter.dev]` to `sonnet` for the next mechanical batch; restore
   `[adapter.review]` to `fable` when weekly headroom returns.

## Known-open, not caused by this effort

- `spec-surface-check`: `.vscode/settings.json` ungoverned (pre-existing).
- `bmad-drift-check`: 1 currency finding. `llms-full-check`: non-zero.
  The board reports "0/3 detectors green" — accurate, not a bug.
