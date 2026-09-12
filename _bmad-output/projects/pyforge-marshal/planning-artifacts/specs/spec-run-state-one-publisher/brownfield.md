---
companion-of: SPEC-run-state-one-publisher
content: brownfield notes — live-code evidence (2026-09-12) and the residual reader inventory
---

# Brownfield — what is live on 2026-09-12

Every line below was re-verified against the working tree on 2026-09-12, not recalled.

## Evidence behind the Why

| Finding | Where it is visible |
|---|---|
| Marshal imports `django_pyforge` zero times | `grep -r django_pyforge src/shared/packages/pyforge-marshal/src/` returns no files |
| The loop home resolves to the operator's home | `pyforge-marshal/src/pyforge/marshal/cli/init.py:336` — `BMAD_LOOP_HOME_ROOT` override, else `Path.home() / ".bmad-loops"` |
| Doctor scrapes the same home | `pyforge-doctor/src/pyforge/doctor/sources/marshal.py:544`; the registration comment at `sources/__init__.py:223` reads "preserve, don't redesign" |
| The only writer of `run_state` is the MCP path | `django-pyforge/src/django_pyforge/supervisor.py:435` `publish_start` — verifies an assertion, mints a handle, enqueues a Celery task |
| The sweep assumes a Celery task | `supervisor.py:681` `sweep_lost_runs` — a live row whose task id no worker reports is marked `worker_lost` |
| The front door already forbids scraping | `src/platform/tests/test_front_door_queries_supervisor.py:235` |
| Both stories block each other by design | steward `sprint-status-ledger.yaml` row `49-8` and marshal row `33-4` both `blocked`; 33.4 says "joint landing with 49.8", 49.8 says "until marshal's Track story exists" |
| The contract's own verdict | Unifying `SPEC.md` CAP-17 `verified:` — "marshal loop homes still filesystem-backed; deployed egress-blocked proof unexercised" |
| Preconditions already met | steward 49.1 `done`; marshal 33.1 `done` with the savings fields at `adapters/harness_bmadloop.py:743-768`; doctor's incoming surface claim for 49.8 in its memlog 2026-09-09 |

## The host API the publisher binds to (steward surface, CAP-1 / CAP-2)

`django_pyforge/supervisor.py`: `publish_start` (:435, assertion-verified, Celery-bound),
`begin_attempt` (:566), `complete_run` (:519), `sweep_lost_runs` (:681, judges by
`live_task_ids`). `RunState` (`models.py:15`) carries `station`, `status`, `subject`, `tenant`,
`celery_task_id`, `result`, `started_at`, `heartbeat_at`, `completed_at`, `duration_ms`. The
front door reads it at `platformapp/front_door/views.py:53` `runs_board`.

## Residual `~/.bmad-loops` readers — the CAP-4 inventory, classified 2026-09-12

Non-test Python sites mentioning `.bmad-loops`: 14 sites, 4 code reads.
Classification per OQ-4 (decision of record in `.memlog.md`). RUN-STATE = `runs/<id>/state.json`,
`journal.jsonl`, `engine.pid`; LOOP-HOME FILE = install tree (`.bmad-loop/bmad_loop_hook.py`,
`policy.toml`), worktrees, git state.

| Station | Site | Kind | Class / disposition |
|---|---|---|---|
| steward | `pyforge-steward/src/pyforge/steward/upgrade.py:3222` | **code read** | LOOP-HOME FILE — hook-relay byte-compare (core-upgrade CAP-4); keep, tag |
| steward | `pyforge-steward/src/pyforge/steward/upgrade.py:4025` | **code read** | LOOP-HOME FILE — prove-landed `bmad-loop validate` over install files + worktree git state (core-upgrade CAP-5); keep, tag |
| steward | `pyforge-steward/src/pyforge/steward/cli.py:772` | argparse help | not a read — `--loops-home` override for the two steward sites |
| steward | `pyforge-steward/src/pyforge/steward/cli.py:798` | argparse help | not a read — `--loops-home` override for the two steward sites |
| steward | `pyforge-steward/src/pyforge/steward/cli.py:830` | argparse help | not a read — `--loops-home` override for the two steward sites |
| doctor | `pyforge-doctor/src/pyforge/doctor/sources/__init__.py:55` | comment / docstring | not a read |
| doctor | `pyforge-doctor/src/pyforge/doctor/sources/__init__.py:147` | comment / docstring | not a read |
| doctor | `pyforge-doctor/src/pyforge/doctor/sources/__init__.py:223` | comment / docstring | not a read |
| doctor | `pyforge-doctor/src/pyforge/doctor/sources/__init__.py:523` | comment / docstring | not a read |
| doctor | `pyforge-doctor/src/pyforge/doctor/sources/marshal.py:519` | comment / docstring | not a read |
| doctor | `pyforge-doctor/src/pyforge/doctor/sources/marshal.py:544` | **code read** | RUN-STATE — `gather_story_status` reads `runs/*/state.json` phase + commit; moves when the payload carries them; CAP-17 debt until then |
| marshal | `pyforge-marshal/src/pyforge/marshal/cli/init.py:336` | **code read** | root resolver (`_loop_home_root`, `BMAD_LOOP_HOME_ROOT` else home) — Story 33.4; consumers move, the root stays |
| scribe | `pyforge-scribe/src/pyforge/scribe/promote.py:124` | comment / docstring | not a read |
| scribe | `pyforge-scribe/src/pyforge/scribe/promote.py:125` | comment / docstring | not a read |

### Run-state reads the literal grep misses (reached through `_loop_home_root()`)

| Site | What it reads | Class / disposition |
|---|---|---|
| marshal `cli/spin.py:395` | globs `.bmad-loop/runs/*/state.json` for `tasks[*].attempt` / `phase` | RUN-STATE — Story 33.4's inventory; reads the plane |
| marshal `cli/status.py` `_gather_home_facts` / `_latest_run_dir` | run journals (the `unknown`-from-landing-journal defect, FR-196) | RUN-STATE — Story 33.4's inventory; reads the plane |
| marshal `supervisor/__main__.py:2729` | appends and reads the run journal | RUN-STATE, writer side — feeds the publisher; the journal itself stays (loop-home file) |

What `bmad-loop` writes under a loop home (`bmad_loop/install.py`, `journal.py`, `runs.py`):
install tree `.bmad-loop/bmad_loop_hook.py` + `policy.toml` + skills; engine state
`.bmad-loop/runs/<id>/{state.json, journal.jsonl, engine.pid, tasks/, logs/}`; worktrees
`.bmad-loop/runs/<id>/worktrees/<story-key>`; the home itself is a full repo checkout.
