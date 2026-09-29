---
sources:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - scripts/promote_sprint_status.py
  - scripts/loop_stall_check.py
  - scripts/bmad_loop_baseline_drift_check.py
  - .claude/memory/reference/bmad-loop-escalation-and-landing-traps.md
  - .claude/memory/reference/fleet-landing-pass-liveness.md
  - docs/how-to/driving-a-pyforge-station-backlog.md
verified: 2026-09-19
---

# Troubleshoot BMAD Agent Loops

This playbook is designed for Station Operators to diagnose and unblock automated agents that are stuck in continuous loops, failing to advance the ledger, or causing state regressions.

## Symptoms of a Stuck Agent
- A continuous cycle of identical tool calls and errors.
- A run that reads `dev-running` forever: `bmad-loop status` reports the last phase the engine *wrote*, so a session blocked on an interactive dialog in its tmux pane never advances and its log stops growing (`loop-stall-check`).
- A story re-dispatched on every drain because its merged work never reached the tracked ledger (a `done` story whose ledger row still says `backlog`).
- The agent creates new branches but never pushes or raises a PR.

## Step 1: Find the run and decide whether it is alive
Start from Marshal, which derives everything from journals and run state:
```bash
pixi run -e pyforge-guild marshal status --project <slug>
pixi run -e pyforge-guild marshal watch --project <slug>            # ground-truth + delta + next-check delay
pixi run -e pyforge-guild marshal status --project <slug> --run <run_id>
```
`UNSUPERVISED` means no Marshal supervisor sidecar, not a dead engine. Before killing or re-spinning anything, confirm liveness in the loop home with `bmad-loop status <run_id> --json` and `bmad-loop list --json`; a dispatch session's log can be followed with `marshal factory dispatch-attach`.

## Step 2: Halt a runaway loop
Stop a live bmad-loop run (engine plus agent session) from its loop home:
```bash
bmad-loop stop <run_id>
```
For a paused-on-escalation run, do not re-arm blindly — the re-arm default re-implements the story from scratch. Preserve first, then restore-patch (`.claude/memory/reference/bmad-loop-escalation-and-landing-traps.md`).

## Step 3: Read what the agent recorded
1. **The Spec's memlog:** `_bmad-output/projects/<slug>/planning-artifacts/specs/spec-<slug>/.memlog.md` is the Spec's append-only, chronological log. Did the dev or review session record a blocker, a deviation, or an escalation there?
2. **The run journal:** each run's `journal.jsonl` under `~/.bmad-loops/<station>/` is what `marshal status` and the watchdogs read.
3. **Team memory:** `scribe recall` answers from the compiled knowledge graph with a citation, or says it has no grounded coverage — useful for "has this trap been seen before?", not for the run's own state:
   ```bash
   pixi run -e pyforge-guild scribe recall "<what you are seeing>" --mode memory
   ```

## Step 4: Inspect the Ledger Drift
A common failure mode is an agent operating against a stale `sprint-status-ledger.yaml`. For example, a merged story whose tracked row was left at `backlog` respawns on every drain until the row is corrected.

1. **Check the story status:**
   ```bash
   pixi run -e pyforge-guild story-status-check
   ```
   This reports a story that reads `done` in a sprint feed without having landed, so the board never over-reports and the next run never skips a story that still needs doing.

2. **Sync the Ledger:**
   When a story has landed and the Tier-3 feed is ahead of the tracked twin, promote it — and scope the sync to the project you mean (an unscoped run once destroyed 96 `done` markers across four other stations):
   ```bash
   pixi run -e pyforge-guild sprint-ledger-sync -- --project <station>
   ```
   Then commit the twin and run `story-status-check` again.
   > [!WARNING]
   > A plain sync refuses to move any key *out of* `done` or drop it (`--allow-regression` overrides, naming every affected key). `--repair-feed` runs the other direction — it writes `done` rows the tracked twin holds *back into* a truncated Tier-3 feed. Use it only when you are deliberately converging a stale feed toward the twin.

## Step 5: Validate the "One Chain" Governance
Check that the station still has one active Dream, one Spec, one PRD, one spine, and one epic chain. A second Dream file or Spec folder minted without a `fold-exemption:` is what `chain-sprawl-check` reports; agents do not refuse to run on it, so it surfaces as a detector finding, not a stall:
```bash
pixi run -e pyforge-guild chain-sprawl-check
```
See [One-Chain Station Ops](one-chain-station-ops.md) for the fold.

## Step 6: Re-dispatch on a clean worktree
If the session's worktree is hopelessly broken but the planning artifacts (Tier 2) are intact:
1. Do **not** modify files in `implementation-artifacts/` by hand.
2. Stop the run (Step 2) and let `marshal retire --project <slug>` (dry-run first, `--execute` to delete) or `python scripts/worktree_sweep.py` clear what is provably safe — both preserve unmerged work rather than deleting it.
3. Dispatch a fresh, isolated session for the story; every dispatch provisions its own worktree from `origin/main`:
   ```bash
   pixi run -e pyforge-guild marshal factory dispatch <slug> <story-key>
   ```
   The wider dispatch/land workflow is in [Driving a PyForge station backlog](driving-a-pyforge-station-backlog.md).
