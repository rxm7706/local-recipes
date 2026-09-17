# Keep one chain on a PyForge station

Use the one-chain workflow to keep a PyForge station at one Dream, one Spec, one PRD, one spine, one epic chain. Operators and coding agents (Claude, Cursor, Copilot, or any other tool) run the same sequence. The policy page is [`CHAIN-STANDARD.md`](../governance/spec-one-chain-per-station/CHAIN-STANDARD.md); this guide is the operator path through it. Why the lock is minting, not a fold campaign, is in [`one-chain-lock-and-mop.md`](../explanation/one-chain-lock-and-mop.md).

## When to Use This

- Day-to-day work: append a dated section on the living station Dream and mint one CAP, one FR, and one Story.
- A still-open PR added an unexempted satellite `docs/dreams/<slug>.md` or `specs/spec-*/` folder that you must rewrite before merge.
- Unexempted satellites already reached `main` and you need a mop PR for one station.
- Several stations are in flight at once and you need the parallel-work rules.
- Do not use this guide to reset a fold, un-archive a Dream, or flip an operator `blocked` ledger key.

:::note[Prerequisites]
A worktree cut from `origin/main` (prefer `pixi run -e pyforge-steward pyforge steward workspace start <slug>`; hand-cut the tree if the default dest is unwritable). Never commit on the shared checkout that already holds `main`. From the repo root, `pixi run -e pyforge-guild` is available. You know the station short name `<s>` and the project slug `pyforge-<s>`. You have read CHAIN-STANDARD §3 (lock sequence), §7 (fold checklist), and §9 (when a fold PR is allowed), plus the closed `fold_exemptions` list in [`docs/governance/guild-roster.json`](../governance/guild-roster.json). You will not hand-edit a `SPEC.md` or `sprint-status-ledger.yaml`.
:::

Dispatch of stories that already exist is a different job: [`driving-a-pyforge-station-backlog.md`](driving-a-pyforge-station-backlog.md).

## Steps

### 1. Seed the ledger feed

Write or refresh the gitignored Tier-3 sprint feed under `_bmad-output/projects/pyforge-<s>/implementation-artifacts/` so it lists every ledger key the tracked twin should carry, at the status that key should keep, then regenerate the tracked ledger from the repo root:

```bash
pixi run -e pyforge-guild sprint-ledger-sync -- --project pyforge-<s>
pixi run -e pyforge-guild story-status-check
```

Never hand-edit `sprint-status-ledger.yaml`. Use `--repair-feed` only when you mean to pull a stale feed toward the tracked twin. A bare sync refuses when the feed would drop twin-only keys or overwrite `done` or `blocked` rows.

On a mop, the re-key map (`planning-artifacts/rekey-<date>.md`) and the feed use the same keys. If the map says `3-1-foo` became `1-1-foo`, the feed row is the new key at the old status. That is how a `done` row moves as `done` instead of drop-plus-add.

### 2. Lock new work on the living chain

Day-to-day after the station is folded is CHAIN-STANDARD §3. Append; do not mint a second Dream file or a second Spec folder.

1. Add a dated `## YYYY-MM-DD` section to `docs/dreams/pyforge-<s>.md` (why). A dated section is a Dream seed.
2. Append the station Spec memlog with `uv run _bmad/scripts/memlog.py`, then re-derive with `bmad-spec`. The new `CAP-n` lands in `SPEC.md`. Never edit `SPEC.md` by hand.
3. Re-derive the PRD so the new `FR-n` cites its source as `FR-n ← CAP-m`. Steps 3 and 4 of §3 may be recorded no-ops in the memlog; they are never silent skips.
4. Mint the Story through **one** `mint_slug`: the `### Story E.S` heading, the ledger key `<E>-<S>-<slug>`, and `spec-<E>-<S>-<slug>.md` are the same slug. Do not invent a second spelling.
5. Build in the worktree. Open a PR to `rxm7706/local-recipes`. Land with `gh pr merge --merge`. Paths outside `recipes/` take the `maintenance` label.

`chain-sprawl-check` fails an unexempted new Dream or Spec folder. A small fix is not an exemption from this sequence (AGENTS.md Dream-first §5).

### 3. Rewrite a satellite still on a PR

If the PR adds `docs/dreams/<slug>.md` or a `specs/spec-*/` folder and that file has no valid `fold-exemption:`, rewrite the work as a dated section on the owning station Dream plus a `CAP-n` on that station Spec, then drop the extra file. Keep a new folder only when frontmatter `fold-exemption:` is one of the closed roster values: `different-owner`, `different-lifecycle`, `cross-station-seam`, `governance`. A fifth reason is a governance edit to `guild-roster.json`, not an ad-hoc string.

### 4. Mop unexempted satellites already on main

Open a fold PR only when unexempted satellites already reached `main`. One station, one PR, branch `fold/<s>`. The fold mops what leaked past the lock; it is not the weekly rhythm, and it does not reset the chain.

The checklist the operator does not rewrite lives in CHAIN-STANDARD §7. Carry these lessons from the 2026-09-17 folds into that checklist:

- Absorbed Spec folders keep the pointer header, the memlog, and **every companion** they already had (inventories, whitepapers, playbooks). Companions move only with a memlog line that names the new path.
- The re-key map is the feed's key list. Ledger regeneration runs through that map so `done` stays `done`.
- Re-point deferred-work `source_spec:` and `location:` through the map. Never re-ingest with `deferred_work_intake.py --fix`; that appends a duplicate row per fingerprint.
- Stamp surfaces scoped after `git add`, from a tree that holds only this fold: `python scripts/spec_surface_check.py --write-baseline --spec pyforge-<s>/<dir>`. A bare `--write-baseline` is forbidden.
- Prove the head with a local `pixi run -e pyforge-guild detectors-ci` run. The GitHub Actions `Detectors` check is advisory (findings print, the step exits 0), so its green is not evidence.
- Leave `pixi.lock` (and usually `pixi.toml`) on doctor. Do not union them onto the station Spec you are folding.
- Never flip an operator `blocked` key. Archived Dreams stay `archived`. Absorbed Spec folders stay pointers. Station Dreams stay `specified`; station Specs stay `ready`.

### 5. Serialize parallel station work

One agent, one worktree, one Story (or one fold). Parallel means two worktrees, not two writers on one tree. Prefer `pyforge steward workspace start <slug>` from `origin/main`; if that dest is unwritable, `git worktree add` a path you can write. The branch for a mop is `fold/<s>`.

Do not run `scripts/bmad-switch` from a parallel agent. Set `BMAD_ACTIVE_PROJECT=pyforge-<s>` on the invocation and write physical `_bmad-output/projects/pyforge-<s>/` paths only. The shared marker and the planning-artifact symlinks are per-working-tree global state; a switch retargets every other writer.

Serialize writes to shared memlogs, `docs/governance/fr-baseline.json`, and `docs/foundry/capability-ledger.yaml`. Merge with `gh pr merge --merge`, one PR at a time. Wait for GitHub's mergeability bit if a sibling just landed.

### 6. Pin the guild environment

Run every detector, ledger sync, surface stamp, and this Spec's derive path as `pixi run -e pyforge-guild …` from the **repository root**. `uv run` from a package directory creates a stray `.venv` there. Load `local-recipes` only when the change actually needs Mason's recipe factory. When rendering BMAD skills, set `PYTHONPATH="$PWD/_bmad/scripts:$PYTHONPATH"`.

Station code is the station CLI (`pyforge <s> …`), not `import pyforge.<s>`. Scribe recall for a team decision or an active Spec is `pixi run -e pyforge-scribe scribe recall "…" --mode planning`.

## What You Get

The station stays one living Dream and one living Spec. New work is a dated section, a CAP, an FR that cites that CAP, and a Story minted through one slug. A satellite on a PR is rewritten or exempted from the roster list. A mop PR, when one is needed, is green on local `detectors-ci` with companions and deferred-work rows intact and with `blocked` rows untouched. Parallel agents do not retarget each other's BMAD writes.
