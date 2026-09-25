---
title: '22.1: `scribe-pg-up` succeeds from a long-path worktree'
type: 'fix'
created: '2026-09-25'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/pyforge-scribe.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `scripts/scribe_pg.py` passes `-k <checkout>/var/scribe-pg` to `pg_ctl`; from a long-path worktree the Unix socket path exceeds PostgreSQL's ~107-byte limit and the server refuses to start ("could not create any Unix-domain sockets"). The 18 durable-GraphStore tests then fail loudly by design, so `pr-preflight` is red for a reason unrelated to the change (found 2026-09-25 landing PR #1605).

**Approach:** Put the socket directory somewhere short and per-user — `SCRIBE_PG_SOCKET_DIR` when set, else `$XDG_RUNTIME_DIR/scribe-pg`, else `/tmp/scribe-pg-<uid>` — created 0700; pass it as `-k`; have `status` report it. The data directory stays under the checkout's `var/scribe-pg/`.

## Boundaries & Constraints

**Always:**
- The data directory stays `var/scribe-pg/data` under the checkout (one cluster per checkout, as today).
- Port 5433, the DSN `tests/unit/conftest.py` hard-codes, and the no-container rule are unchanged.
- `up` stays idempotent: a cluster already listening on :5433 is reused, never re-initialised.
- Co-governor reconcile before landing: a memlog entry on every Spec `spec-surface-check` names, `git add`, then `python scripts/spec_surface_check.py --write-baseline --spec <project>/<spec>` per named Spec, re-run the check and read its exit code; never a bare stamp.

**Never:**
- Do not move the data directory out of the checkout.
- Do not flip any Epic 44 `blocked` key.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.
- Do not start a server inside the unit test.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| long-path worktree | `var/scribe-pg` path > 100 bytes | `scribe-pg-up` exits 0; `scribe-pg-status` reports listening on 127.0.0.1:5433 and the socket dir | fail loud |
| override set | `SCRIBE_PG_SOCKET_DIR=/x` | `-k /x`, created 0700 if absent | fail loud if not creatable |
| no override, no XDG_RUNTIME_DIR | env unset | `/tmp/scribe-pg-<uid>` | fail loud |
| cluster already up | :5433 listening | reused; no init, no second server | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-scribe CAP-31`.
Dream: `docs/dreams/pyforge-scribe.md` § *2026-09-25 — The local Postgres cluster starts from any worktree*.
Ledger key: `22-1-scribe-pg-up-succeeds-from-a-long-path-worktree`.
Ledger status at mint: `backlog`.
Minted 2026-09-25 from `epics.md` so `marshal factory dispatch` can resolve `spec-22-1-scribe-pg-up-succeeds-from-a-long-path-worktree.md`.

## Epic excerpt

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-scribe CAP-31 • Dream 2026-09-25
**Surface:** `scripts/scribe_pg.py` (socket dir: `SCRIBE_PG_SOCKET_DIR` → `$XDG_RUNTIME_DIR/scribe-pg` → `/tmp/scribe-pg-<uid>`, created 0700; `-k` and `status` follow it), `tests/scripts/test_scribe_pg.py` (new), `pixi.toml` (`scribe-pg-up` / `scribe-pg-status` descriptions name the socket dir).
**Given** `scripts/scribe_pg.py` passes `-k <checkout>/var/scribe-pg` and a worktree such as `local-recipes-wt-unifying-strategy-dream-seeds-2026-09-25` pushes that socket path past PostgreSQL's ~107-byte limit, so `pg_ctl start` fails with "could not create any Unix-domain sockets" (found 2026-09-25)
**When** this story lands
**Then** `pixi run -e pyforge-scribe-pg scribe-pg-up` exits 0 from such a worktree and `scribe-pg-status` reports the cluster listening on 127.0.0.1:5433 with the socket directory it used; the data directory is unchanged (`var/scribe-pg/data`); a cluster already listening is reused, not re-initialised
**And** `tests/scripts/test_scribe_pg.py` covers the directory choice, the override and the length guard without starting a server; `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` green with the cluster up; co-governor reconcile: a memlog entry on every Spec `spec-surface-check` names, then a scoped stamp per Spec, never a bare `--write-baseline`

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (the station's `verify_commands`; run with the cluster up).

**Manual checks:**
- From a worktree whose `var/scribe-pg` path exceeds 100 bytes: `pixi run -e pyforge-scribe-pg scribe-pg-up` — expected: exit 0; `pixi run -e pyforge-scribe-pg scribe-pg-status` — expected: "listening on 127.0.0.1:5433" and the socket directory.
- `tests/scripts/test_scribe_pg.py` — expected: pass in `pixi run -e pyforge-ci python -m pytest tests/scripts/test_scribe_pg.py` (the `scripts-suite` leg).
