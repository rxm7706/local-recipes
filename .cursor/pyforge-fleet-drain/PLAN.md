# PyForge fleet drain — repeatable hand-driven `bmad-build-auto` playbook

**Scope:** all eight active PyForge BMAD stations (`pyforge-{atlas,doctor,herald,marshal,mason,scribe,steward,warden}`).

**Purpose:** drain each station's story backlog using the **single-story, worktree-isolated, non-fork** `bmad-build-auto` pattern — **not** `bmad-loop`, **not** marshal factory spin. One story in flight per station; stations run in parallel with each other.

**Canonical prior art:** Claude session pause [`project_session_pause_2026-08-22_fleet_queue_restart.md`](file:///home/rxm7706/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/memory/project_session_pause_2026-08-22_fleet_queue_restart.md) (2026-08-22 eight-station wave). This document generalizes that handoff into a **repeatable operator playbook** stored in-repo under `.cursor/` (Tier-3 working output — not a BMAD spec).

---

## When to use this vs other paths

| Path | Use when |
|------|----------|
| **This playbook (`bmad-build-auto`, worktree, coordinating session merges)** | Hand-driven fleet drain; one story per station; you want PR review between merges; marshal Epic 22 dispatch verb does not exist yet |
| `bmad-build` (quick-dev) | Single story, interactive, no review loop |
| `bmad-loop` / marshal factory | Unattended multi-story runs with marshal run state — **explicitly out of scope here** |

Marshal story `22-1`…`22-6` will eventually **productize** this playbook. Until then, this folder is the manual implementation of `22-5` ("one story in flight per station").

---

## Operating modes

### `drain_to_zero` (current campaign default)

Dispatch the next backlog story for a station, merge + finalize, repeat until `development_status` has **zero** non-`done` story keys. No reserved leftover.

### `leave_one` (2026-08-22 pause policy — optional)

Stop when exactly one story remains in backlog (`leave_remaining` in `queues.yaml`). Used during graceful shutdown before a Claude restart. Switch mode in `queues.yaml` → `campaign.mode`.

### `skip_on_blocked` (steward 12-7)

If a story HALTs `blocked` (needs live OCP cluster, missing secret, etc.): **do not** force; **skip to next queue entry**; **report skip to operator**; leave the story in backlog. Policy block in `queues.yaml` under `skip_policies`.

---

## The eight stations

| Slug | BMAD project | Package / surface | Ledger |
|------|--------------|-------------------|--------|
| `atlas` | `pyforge-atlas` | `src/` atlas/Kedro pipeline | `…/pyforge-atlas/planning-artifacts/sprint-status-ledger.yaml` |
| `doctor` | `pyforge-doctor` | `src/shared/packages/pyforge-doctor/` | `…/pyforge-doctor/…` |
| `herald` | `pyforge-herald` | `src/shared/packages/pyforge-herald/` | `…/pyforge-herald/…` |
| `marshal` | `pyforge-marshal` | `src/shared/packages/pyforge-marshal/` | `…/pyforge-marshal/…` |
| `mason` | `pyforge-mason` | `src/shared/packages/pyforge-mason/` | `…/pyforge-mason/…` |
| `scribe` | `pyforge-scribe` | `src/shared/packages/pyforge-scribe/` | `…/pyforge-scribe/…` |
| `steward` | `pyforge-steward` | `src/shared/packages/pyforge-steward/`, `src/platform/` | `…/pyforge-steward/…` |
| `warden` | `pyforge-warden` | `src/shared/packages/pyforge-warden/` | `…/pyforge-warden/…` |

**Active project rule:** never `scripts/bmad-switch` from parallel agents on the shared repo. Each dispatch worktree sets `BMAD_ACTIVE_PROJECT=pyforge-<station>` per invocation and writes specs to `_bmad-output/projects/<slug>/planning-artifacts/…` **literally** (CLAUDE.md parallel-agent rule).

---

## One dispatch cycle (repeat per story)

### Phase 0 — Preflight (coordinating session, **before** launching agent)

For station `<s>` and story `<id>` (e.g. `marshal` / `11-5`):

1. **Ledger truth:** read `sprint-status-ledger.yaml` — skip if story already `done`.
2. **Remote branch:** `git ls-remote --heads origin '<s>/*'` — look for `<s>/<epic>-<story>-*`.
3. **Open PR:** `gh pr list --repo rxm7706/local-recipes --search "head:<branch-prefix>"`.
4. **Live agent:** if a prior dispatch may still be running, check worktree under `.claude/worktrees/agent-*` before duplicating.

Do **not** dispatch if an open PR or in-progress branch already covers the story.

### Phase 1 — Spec readiness

- **Preferred:** tracked spec at `_bmad-output/projects/pyforge-<s>/planning-artifacts/specs/spec-<epic>-<story>-*.md` with `status: ready` (or `done` for re-runs).
- **If missing:** coordinating session drafts spec from `epics.md` story block (intent contract shape per sibling specs), commits to a prep branch or passes spec path in agent prompt — **do not** let `bmad-build-auto` invent scope silently.

### Phase 2 — Launch agent (worktree-isolated)

Plain background agent (Cursor `Task` or Claude Code `Agent`), **`run_in_background: true`**, **`subagent_type: generalPurpose`** (must **not** be a fork of parent — see auto-memory `feedback_bmad_dev_auto_needs_non_fork_agent`).

**Prompt skeleton:**

```
Full Repository Path: /home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes
Station: pyforge-<s>
Story: <epic>-<story> — <title slug>
Spec: _bmad-output/projects/pyforge-<s>/planning-artifacts/specs/spec-<epic>-<story>-<slug>.md

Run bmad-build-auto for this single story only:
1. Work in an isolated git worktree (fresh checkout from origin/main).
2. export BMAD_ACTIVE_PROJECT=pyforge-<s> — do NOT run scripts/bmad-switch on shared repo.
3. Invoke bmad-build-auto skill; dev + review + open PR. Never merge.
4. Branch: <s>/<epic>-<story>-<short-slug>
5. Non-recipes/ changes → gh pr edit --add-label maintenance
6. pixi.toml changed → regenerate environment.yaml and commit
7. Do NOT edit sprint-status-ledger.yaml — coordinating session finalizes after merge.
8. On blocked: push branch, HALT blocked with reason, do not restart from scratch.
9. Verify implementation-artifacts is a SYMLINK not a directory before spec promotion.
```

**AD-16 / config:** ensure worktree has `_bmad/custom/config.toml` with `[core] communication_language` + `user_skill_level` (only one definition fleet-wide — see pause memory).

### Phase 3 — Coordinating session: merge gate

When agent reports PR URL (trust only explicit PR URL or "Clean HALT, status done" — not interim task notifications):

1. Review diff + CI (`gh pr checks`, Platform CI / detectors as applicable).
2. Confirm `maintenance` label if needed.
3. Merge: `gh pr merge <n> --merge` (**never `--squash`** — breaks subject-based merge detection).
4. If `pixi.toml` changed on main and agent missed export: `pixi project export conda-environment -e build > environment.yaml` + commit.

### Phase 4 — Finalize (coordinating session, **after every merge**)

```bash
# Flip Tier-3 sprint-status + regenerate tracked ledger + dashboard inputs
pixi run -e local-recipes sprint-ledger-sync --project <s>

# Promote story spec from implementation-artifacts scratch → planning-artifacts/specs/ if needed
# (bmad-build-auto may write scratch first; promotion is post-merge convention)

# Close deferred-work ledger entries referenced in spec/PR if applicable
# Regenerate dashboard if your closeout includes it:
# pixi run -e local-recipes dashboard-gen  # when station closeout requires it
```

Update `.cursor/pyforge-fleet-drain/STATUS.md` and re-run `generate-queues.py`.

### Phase 5 — Chain next story

If station queue non-empty and mode is `drain_to_zero`, return to Phase 0 for next story. **Max one in-flight agent per station.**

---

## Parallelism matrix

| Parallel OK | Parallel NOT OK |
|-------------|-----------------|
| Different stations at the same time (marshal + steward + …) | Two stories same station |
| Preflight on station B while station A agent runs | `scripts/bmad-switch` from two agents on same worktree |
| Finalize station A while station B agent runs | Merging without CI green |

**Suggested wave sizing:** 2–4 stations concurrently on a coordinating session with enough context budget; 8-station fan-out only when operators can monitor nudges/recoveries.

---

## Recovery playbooks (from 2026-08-22 live incidents)

### SendMessage / subagent orphan

Implementation subagent fails to report to parent. **Fix:** paste orphaned result to **stuck top-level task id** via resume/nudge; instruct parent to **independently re-verify** before commit.

### Agent "silent" mid-review

`TaskOutput` may say "no task found" while agent waits on nested reviewer. **Fix:** wait for natural completion OR `SendMessage` nudge with worktree uncommitted state description; after ~20 min no progress, rescue worktree manually (review diff, commit, push, open PR).

### `implementation-artifacts` symlink → directory

Before spec promotion: `readlink -f _bmad-output/projects/<slug>/implementation-artifacts` must be symlink. If directory: `diff -rq` against main checkout, copy diverged spec files only.

### Config ambiguity HALT

`user_skill_level` / `communication_language` must exist in **exactly one** of the six config layers. Never merge duplicate keys under `[core]` and `[modules.bmm]`.

### Steward 12-7 skip

Live OCP cluster required — skip under `skip_on_blocked`, dispatch 12-8, tell operator.

---

## Queue maintenance

| File | Role |
|------|------|
| `queues.yaml` | Machine-readable per-station ordered queues + campaign mode + skip policies |
| `generate-queues.py` | Regenerate `queues.yaml` backlog sections from ledgers (+ manual order overrides) |
| `STATUS.md` | Human snapshot: last merge, in-flight, drained stations |

Regenerate after every finalize:

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py
```

Manual order overrides (marshal Epic 22 insert, steward skip) live in `queues.yaml` `order_overrides` — generator preserves them.

---

## Verification commands

```bash
# Fleet backlog counts
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary

# Ledger vs dashboard
pixi run -e local-recipes fleet-picture

# Drift / tier hygiene (optional between waves)
pixi run -e local-recipes bmad-drift-check
```

---

## Exit criteria

**Campaign complete** when every station in `queues.yaml` → `stations.<s>.drained: true` (zero backlog stories per ledger), or `leave_one` mode leaves exactly the configured `leave_remaining` story per station.

**Post-drain:** run station epics retrospective stories if any; consider archiving this campaign folder or resetting for the next epic tranche.
