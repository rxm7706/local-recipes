# Driving a PyForge station backlog forward

Use this workflow to move a PyForge Guild station's BMAD backlog forward: checking what's ready, dispatching the right stories through the right mechanism, and landing the result without trusting a green check you haven't looked behind.

## When to use this

- You're asking "what's next" for a station (herald, doctor, marshal, mason, scribe, steward, warden, atlas) and want to know what's actually ready to dispatch.
- You're about to hand a story or a batch of stories to a background agent.
- A background agent just reported success and you need to decide whether to believe it.
- A PR you're merging touches `sprint-status-ledger.yaml` alongside other open PRs.

:::note[Prerequisites]
An active BMAD project (`scripts/bmad-switch --current`) and familiarity with this repo's Dream → Spec → Story chain (see `AGENTS.md` and the `CLAUDE.md` § Dream-first section). This guide assumes stories already exist in `epics.md`; it doesn't cover minting them.
:::

## How do I check status without spending anything?

Run `pixi run -e pyforge-guild fleet-picture`. It's read-only and never gates anything, so there's no cost to checking before you decide whether a task is even worth dispatching. Cross-reference against the station's own `sprint-status-ledger.yaml` for exact story keys and current status (`backlog`, `in-progress`, `blocked`, `in-review`, `done`).

Don't assume a story marked `backlog` still needs full work, and don't assume one marked `done` is trustworthy without checking what actually landed. Both directions bite: content can be further along than the ledger admits (local work merged but never pushed to an external system), or a "done" can be a false self-report from an abandoned session that never produced a merged PR.

## How do I choose a dispatch mechanism?

Three options, picked by story size and blast radius:

| Mechanism | Use when |
|---|---|
| `bmad-build` (quick-dev) | One hand-picked, low-risk story. No external side effects, nothing you'd regret if it landed wrong. |
| `bmad-build-auto` | One story with real external blast radius: pushes to a live third-party system, opens PRs against production content, touches something you can't easily undo. Its mandatory adversarial review earns its overhead here. |
| `bmad-loop` | A genuine unattended multi-story run, when you want a whole epic drained without checking in after each story. |

Defaulting to `bmad-build-auto` for anything that writes outside the repo isn't overcaution. A single-line code fix that also proves itself against a live Design project, for instance, still deserves the review pass, because the risk lives in the external write, not the line count.

## How do I dispatch a story safely?

One story per agent, even when several stories in a wave are independent and could theoretically run under one supervisor. A background agent that owns an entire backlog has no reliable way to signal when a nested review subagent is still working, and a stalled top-level agent can get killed by a watchdog while its work is still landing underneath it, which leaves you unsure whether to redispatch or wait.

Give each agent full context in the prompt: what's already done and verified (don't make it re-derive facts you already know), the exact mechanism for anything non-obvious (how to push through a transport the CLI doesn't fully cover, known gotchas from a prior attempt), and what "done" means for that specific story. A fresh agent has no memory of your investigation; a terse prompt produces shallow work.

## How do I verify a background agent's report before trusting it?

A green check proves what it checks, nothing more. `deck-facts --check` validates that marked facts match a ledger; it says nothing about whether the surrounding prose is real content or a corrupted repeat of one boilerplate sentence. A byte-identical read-back proves the push was faithful, not that what got pushed was correct. Verify every self-reported "0 mismatch" or "verified" claim yourself instead of recording it as fact.

Three checks catch most of what a summary hides:

- Re-read the actual file yourself. Grep for a suspicious repeated pattern, check the byte count against the floor the story specifies, spot-check a paragraph for real prose.
- Check the live external state independently: pull the file back from the third-party system yourself rather than trusting the agent's own read-back claim.
- Diff what actually landed (`gh pr diff`) against what the report claims landed. File scope should match exactly; nothing stray.

This discipline mirrors what you'd apply to your own work before calling it done, and it catches real defects: this pattern found corrupted content that had already been pushed to two live external projects, sitting behind a fully green `deck-facts --check`.

## How do I resolve a `ledger-regression-check` false positive?

The detector walks every commit between `origin/main` and your branch's head, checking each one's ledger diff for a `done → not-done` transition on any key. It doesn't just compare the two endpoints. So a two-commit sequence (one commit that accidentally introduces a regression, a second that fixes it) trips the check even though the net result matches main exactly, because the *first* commit's diff still shows the bad transition.

Fix it by removing the bad transition from history rather than papering over it with a corrective commit:

```bash
git reset --soft origin/main
# working tree now holds every real change from both commits; recommit as one
git commit -m "..."
git push --force-with-lease
```

This is safe on a single-purpose, not-yet-merged feature branch that only you are working on. Never do it on `main` or a branch someone else depends on.

## How do I land several PRs that all touch the same tracked ledger file?

Expect merge conflicts once the first sibling PR lands: they'll usually collide on adjacent lines in `sprint-status-ledger.yaml`. Resolve additively: both sides' changes are almost always real and both belong, so keep both rather than picking one. Watch for `main` having moved further than you expect between checks; another concurrent session (a different agent, a teammate, an automated fold) can land a change to the exact key you're touching, and the right move is usually to accept it and rebase rather than fight it.

`gh pr merge` can report "not mergeable" for a few seconds right after a sibling PR merges, even when the branch is genuinely conflict-free, because GitHub's mergeable-status computation lags the merge itself. Wait a few seconds and retry before assuming there's a real conflict to resolve.

## What you get

A station backlog driven forward with verified, not assumed, results: stories dispatched through the mechanism their risk profile actually calls for, self-reports checked against live state before anything gets merged, and ledger conflicts resolved without losing real progress on either side.
