# Detecting concurrent agent activity

Use this check to tell whether another agent or session is already working on the same files you're about to touch, before you duplicate work, race a shared file, or dispatch a background agent that collides with one already running.

## When to use this

- You're about to dispatch a background agent against a station's backlog.
- A tracked file changed on disk since you last read it and you're not sure why.
- You're planning a broad `git add` or a push to a shared branch.
- Work in this repo has felt slower or stranger than expected and you suspect you're not the only one touching it.

This repo runs heavy concurrent automation by design: multiple BMAD loop supervisors, dispatched background agents, and separate human-driven sessions (including non-Claude tooling) can all be active in the same checkout at once, which is expected here, so don't assume you're working alone.

## How do I check for other active work?

Three checks, in order of how fast they answer the question:

```bash
git worktree list
```

Shows every checked-out branch, including ones set up by a background agent's isolated worktree. A branch name matching a story or task you're about to dispatch is a strong signal someone else already owns it.

```bash
ps aux | grep -i "bmad-loop\|marshal.supervisor\|bmad-build-auto"
```

Lists live orchestrator and dev-session processes. An empty result means nothing is currently running, but check the worktree's git log too, since a process can finish and leave a clean, committed worktree behind with no PR yet opened.

```bash
gh pr list --repo rxm7706/local-recipes --search "<story-or-topic> in:title" --state all
```

Catches work that already landed, or is mid-review, under a title you might not have guessed.

## How do I read a "file changed on disk" notification?

When a tool result reports that a file changed since you last read it, that's the harness telling you something else wrote to it while you were working, not an error to dismiss. Read the new content before acting on stale assumptions about what it contains. Most of the time it's legitimate concurrent progress (a sibling agent, a supervisor syncing a shared ledger); occasionally it's a signal that your own in-flight edit is about to conflict with someone else's.

Don't revert a change you didn't make just because it's unexpected; check whether it's deliberate (a commit message, a PR, a process still running) before deciding it's wrong.

## What you get

This check gives you enough visibility to dispatch with confidence. You'll know whether a story is genuinely free to pick up, and whether a stalled-looking agent is actually dead or just quiet. An unexpected file change on disk will read clearly too, as someone else's real progress or as a genuine conflict headed your way.
