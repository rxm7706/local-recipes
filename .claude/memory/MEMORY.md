# Team Memory Index

Checked-in index of `.claude/memory/` — decisions, project state, and
reference material that are relevant to every contributor to this repo
(human or agent), captured with the `scribe` CLI
(`src/shared/packages/pyforge-scribe/`). See `README.md` in this directory
for the schema, the team-relevance test, and the promotion workflow.

This layer is additive to, not a replacement for, per-user auto-memory
(`~/.claude/projects/<encoded-path>/memory/`) — only entries that pass the
team-relevance test below live here.

Keep this file under 200 lines (Claude Code truncates context past that
length) — prune stale entries under standard git review rather than
letting the index grow unbounded.

## Feedback

- [bmad-runs-cfe-retro](feedback/bmad-runs-cfe-retro.md) — Always-on rule — at closeout of any BMAD-driven conda-forge effort, run bmad-retrospective focused on conda-forge-exper…
- [spec-surface-check-py-s-write-baseline-reads-git-ls-files-so](feedback/spec-surface-check-py-s-write-baseline-reads-git-ls-files-so.md) — spec_surface_check.py's --write-baseline reads git ls-files, so new files must be git add'ed BEFORE stamping or the bas…
- [pre-existing-findings-fix-now-is-the-default](feedback/pre-existing-findings-fix-now-is-the-default.md) — "Pre-existing" says why a finding is not yours, never why it stays; defer only for a Dream-sized effort or a named blocker; a DW entry is never closure
- [a-pr-from-a-parallel-agent-that-adds-a-station-capability-mu](feedback/a-pr-from-a-parallel-agent-that-adds-a-station-capability-mu.md) — A PR from a parallel agent that adds a station capability must carry the whole Dream-to-code chain before it merges: a…
- [coverage-gates-run-per-station-in-that-station-s-own-pixi-en](feedback/coverage-gates-run-per-station-in-that-station-s-own-pixi-en.md) — Coverage gates run per station in that station's OWN pixi environment: scripts/coverage_gates_ci.py evaluates only the…
- [before-pushing-a-non-recipe-branch-replicate-every-ci-lane-t](feedback/before-pushing-a-non-recipe-branch-replicate-every-ci-lane-t.md) — Before pushing a non-recipe branch, replicate every CI lane the diff will trigger, locally, and read each verdict from…

## Project

- [fleet-inbox-is-not-a-second-decompose-wave](project/fleet-inbox-is-not-a-second-decompose-wave.md) — 2026-09-16: leftover intake/Dreams/deferred are not a second story-mint wave; dispatch 59–62 then doctor 23–24; next decompose is status-body-consistency only. Charter CAP-3 is doctor 21.4 (do not remint); 59.4 teaching-only; Dream stays specified.
- [the-stuck-orchestrator-baseline-bug-bmad-loop-s-task-baselin](project/the-stuck-orchestrator-baseline-bug-bmad-loop-s-task-baselin.md) — The stuck-orchestrator-baseline bug: bmad-loop's task.baseline_commit can drift to a later commit while a dev session i…
- [operator-inbox-as-of-2026-09-19-the-asks-a-session-cannot-cl](project/operator-inbox-as-of-2026-09-19-the-asks-a-session-cannot-cl.md) — Operator inbox as of 2026-09-19 (the asks a session cannot close itself; tracked here so every harness and session sees…
- [2026-09-25-operator-stopped-both-fleet-drains-by-explicit-de](project/2026-09-25-operator-stopped-both-fleet-drains-by-explicit-de.md) — 2026-09-25: operator stopped both fleet drains by explicit decision after landing steward 59.6/59.7 and marshal 46.6 (n…

## Reference

- [fleet landing-pass liveness](reference/fleet-landing-pass-liveness.md) — STEP 2 primary check is `bmad-loop status <run_id> --json` + `list --json`; UNSUPERVISED rows use the same check before re-spin; never `cat engine.pid` / bare `grep 'bmad-loop run'`
- [bmad-loop escalation & landing traps](reference/bmad-loop-escalation-and-landing-traps.md) — re-arm defaults to re-implementing from scratch; `--no-interactive` is NOT the safe flag; diff the restore patch against current main; `dashboard-gen` defaults to the intent feed
- [pyforge-scribe-story-7-1-cap-3-bmad-os-audit-file-refs-adapt](reference/pyforge-scribe-story-7-1-cap-3-bmad-os-audit-file-refs-adapt.md) — pyforge-scribe Story 7.1 (CAP-3): bmad-os-audit-file-refs adapted pass over docs/reference/ -- 13 files audited, 7 stal…
- [bmad-skill-customization-mechanics-verified-live-2026-09-10](reference/bmad-skill-customization-mechanics-verified-live-2026-09-10.md) — BMAD skill customization mechanics (verified live 2026-09-10 against docs.bmad-method.org/customize/customize-bmad, doc…
