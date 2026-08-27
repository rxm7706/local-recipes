# PyForge fleet drain — repeatable hand-driven `bmad-build-auto` playbook

> **SUPERSEDED (2026-08-27, Story 22.7 / FR-193 CAP-7).** Phases 0–5 below are
> productized end to end as `marshal factory drain` (`--mode` is required and
> never defaulted). Queue state is the tracked `sprint-status-ledger.yaml` files themselves,
> plus an OPTIONAL (absent by default) `planning-artifacts/fleet-drain-queue.yaml` under
> `pyforge-marshal` carrying only order overrides + skip policies; campaign journals live in
> that project's `implementation-artifacts/fleet-drain-runs/`.
> Kept as the historical record — **do not replay this hand ritual.**

**Scope:** all eight active PyForge BMAD stations (`pyforge-{atlas,doctor,herald,marshal,mason,scribe,steward,warden}`).

**Purpose:** drain each station's story backlog using the **single-story, worktree-isolated, non-fork** `bmad-build-auto` pattern — **not** `bmad-loop`, **not** marshal factory spin. One story in flight per station; stations run in parallel with each other.

**Marshal home (Tier 2):** `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/` — `SPEC.md` (CAP-1..CAP-7) + `fleet-drain-playbook.md`. This folder is the **interim runner** until Epic 22 Stories 22.1–22.6 land as `marshal factory dispatch` / `marshal drain` verbs.

**This campaign's station order:** [SEQUENCING.md](./SEQUENCING.md) (Canopy: 18-1 → 32-1 unlock → eight-station Wave 2 → steward serial).

**Merge policy (fleet-wide, since 2026-08-23):** dispatch agents **merge their own PR** when CI is green, then **finalize** (ledger sync, spec promotion, queue regen). The coordinating session preflights and monitors; it only intervenes on blocked/failed runs. Supersedes the 2026-08-22 "never merge" split documented in the pause handoff.

---

## When to use this vs other paths

| Path | Use when |
|------|----------|
| **This playbook (`bmad-build-auto`, worktree, merge-in-agent)** | Interim runner until `marshal factory dispatch` / `marshal drain` (Epic 22, CAP-7) ships — see `spec-marshal-single-story-dispatch/fleet-drain-playbook.md` |
| `bmad-build` (quick-dev) | Single story, interactive, no review loop |
| `bmad-loop` / marshal factory | Unattended multi-story runs with marshal run state — **explicitly out of scope here** |

Marshal story `22-1`…`22-6` + **CAP-7** productize this playbook as marshal verbs. Until then, this folder is the interim runner (companion: `spec-marshal-single-story-dispatch/fleet-drain-playbook.md`).

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
3. Invoke bmad-build-auto skill; dev + review + open PR.
4. Branch: <s>/<epic>-<story>-<short-slug>
5. Non-recipes/ changes → gh pr edit --add-label maintenance
6. pixi.toml changed → regenerate environment.yaml and commit on the PR branch before merge
7. When CI is green: gh pr merge <n> --merge (NEVER --squash). git pull origin main in worktree.
8. Finalize THIS STATION ONLY (see Phase 3 below) — then report PR URL + merge commit.
9. On blocked: push branch, HALT blocked with reason, do not restart from scratch.
10. Verify implementation-artifacts is a SYMLINK not a directory before spec promotion.
```

**AD-16 / config:** ensure worktree has `_bmad/custom/config.toml` with `[core] communication_language` + `user_skill_level` (only one definition fleet-wide — see pause memory).

### Phase 3 — Merge + finalize (dispatch agent, **after CI green**)

The dispatch agent owns merge-through-finalize for its station. Parallel stations are safe because each agent only mutates **its own project's** Tier-2/Tier-3 paths plus the **tracked ledger row for that project** — never another station's `_bmad-output/projects/<other>/`.

```bash
# 1. Merge (agent)
gh pr checks <n> --repo rxm7706/local-recipes   # all required green
gh pr merge <n> --merge --repo rxm7706/local-recipes   # NEVER --squash
git pull origin main

# 2. Mark story done in Tier-3 feed (gitignored — local to worktree/main checkout)
#    Edit _bmad-output/projects/pyforge-<s>/implementation-artifacts/sprint-status.yaml
#    Set development_status[<story-key>]: done

# 3. Promote tracked ledger (agent — this station only)
pixi run -e local-recipes sprint-ledger-sync --project <s>
git add _bmad-output/projects/pyforge-<s>/planning-artifacts/sprint-status-ledger.yaml
# Also commit promoted story spec under planning-artifacts/specs/ if bmad-build-auto wrote scratch

# 4. Regenerate fleet queues (read-only merge of all ledgers — safe concurrently)
python3 .cursor/pyforge-fleet-drain/generate-queues.py
git add .cursor/pyforge-fleet-drain/queues.yaml .cursor/pyforge-fleet-drain/STATUS.md  # if updated

# 5. Push finalize commit(s) directly to main ONLY if policy allows; otherwise open a tiny
#    maintenance PR for ledger/spec promotion. Prefer: merge story PR first, then a second
#    commit on main from a fast-forwarded worktree for ledger+spec (same agent session).
```

**Parallel finalize rules (HARD):**

| OK | NOT OK |
|----|--------|
| `sprint-ledger-sync --project marshal` while steward syncs `--project steward` | Two agents both editing `_bmad/custom/config.toml` on main without rebasing |
| Each agent promotes spec under its own `planning-artifacts/specs/` | Agent A running `sprint-ledger-sync` without `--project` (all stations) |
| `generate-queues.py` after merge (regenerates whole file; last writer wins — re-run if conflict) | Force-pushing main |

**Shared-root files** (`pixi.toml`, `environment.yaml`, `_bmad/custom/config.toml`, `.github/workflows/`): if the story PR touches them, merge that PR before any other agent rebases onto main. If CI missed `environment.yaml` after `pixi.toml` change: export and push a follow-up commit before merge.

**Spec promotion:** if `implementation-artifacts/` became a real directory, `diff -rq` against main before copying the story spec into `planning-artifacts/specs/`.

### Phase 4 — Coordinating session (monitor + rescue only)

Use when the dispatch agent HALTs, CI stays red, or finalize push fails:

1. Review open PR / worktree diff manually.
2. Merge with `gh pr merge --merge` if agent did not.
3. Run Phase 3 finalize commands for the affected `<s>`.
4. Nudge/resume stuck agents (see Recovery playbooks).

Update `.cursor/pyforge-fleet-drain/STATUS.md` when intervening.

### Phase 5 — Chain next story

If station queue non-empty and mode is `drain_to_zero`, return to Phase 0 for next story. **Max one in-flight agent per station.**

---

## Parallelism matrix

| Parallel OK | Parallel NOT OK |
|-------------|-----------------|
| Different stations at the same time (marshal + steward + …) | Two stories same station |
| Preflight on station B while station A agent runs | `scripts/bmad-switch` from two agents on same worktree |
| Finalize station A while station B agent runs | Two stories same station |
| Coordinator merges when agent already did | Merging without CI green |
| `generate-queues.py` last-writer without re-run after conflict | Force-pushing main |

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
