---
title: '22.2: `scribe-pg-down` stops only this checkout''s cluster'
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-22-1-scribe-pg-up-succeeds-from-a-long-path-worktree.md
  - scripts/scribe_pg.py
  - tests/scripts/test_scribe_pg.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** One PostgreSQL server serves the whole host on 127.0.0.1:5433. Each checkout keeps its own data
directory under `var/scribe-pg/`, and `up()` reuses any server already listening on the port, this checkout's or
another's (Story 22.1 review item 8, deliberate). `down()` (`scripts/scribe_pg.py`:283-293) does not follow that
model. It runs `pg_ctl -D var/scribe-pg/data stop` whenever `PG_VERSION` exists. When this checkout's cluster is
initialised but stopped while another checkout's server answers on :5433, `pg_ctl` fails (no PID file) and
`_is_up()` is true, so `scribe-pg-down` writes `pg_ctl`'s error and exits 1. Nothing is wrong: this checkout's
cluster is already down.

EGM audit 2026-11-01 findings carried: SCR-M-Z1, SCR-M-D5, SCR-M-C4 (cluster SCR-1, the code half). Research:
`_bmad-output/projects/pyforge-scribe/planning-artifacts/research/egm-audit-2026-11-01.md`. The oracle-text half
(CAP-31's success graded only when no server listens on :5433; one data directory per checkout and one listening
server per host; the named length guard, 107 bytes on Linux and 103 on macOS; `status` exits 0 by design;
`SCRIBE_GRAPH_DSN` overrides the conftest default) is a `spec-pyforge-scribe` memlog event and a `bmad-spec`
re-derive in marshal Story 113.7's PR, which names this story for the `down()` edge.

**Approach:** In `down()`, after the `PG_VERSION` test and before `pg_ctl stop`, return early when
`var/scribe-pg/data/postmaster.pid` does not exist: print `[scribe-pg] not running` and exit 0. With the PID file
present, keep today's stop. With no `PG_VERSION`, keep today's `no cluster to stop`. Pin the new branch with one
offline test.

Ledger key: `22-2-scribe-pg-down-stops-only-this-checkout-s-cluster`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-scribe` CAP-31: the local Postgres cluster starts from any checkout; the data directory stays under
  the checkout's `var/scribe-pg/`. This story makes `down` act on that checkout's cluster only. No new CAP.
- `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- AC1: Given a data directory holding `PG_VERSION` and no `postmaster.pid`, and another checkout's server answering on
  :5433 When `scribe-pg-down` runs Then it prints `[scribe-pg] not running`, exits 0, and never calls `pg_ctl`.
- AC2: Given a data directory holding `PG_VERSION` and `postmaster.pid` When `scribe-pg-down` runs Then it runs
  `pg_ctl … stop` as today, prints `[scribe-pg] stopped` on success, and exits 1 only when the stop fails and a
  server still answers.
- AC3: Given no `PG_VERSION` When `scribe-pg-down` runs Then it prints `[scribe-pg] no cluster to stop` and exits 0,
  as today.
- AC4: Given the new branch is removed When the AC1 test runs Then it fails (mutation).
- AC5: Given this story lands When `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_scribe_pg.py`
  and `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` run Then both exit 0.

## Boundaries & Constraints

**Always:**
- Keep the test offline: build the data directory under `tmp_path`, patch `CLUSTER`, `_run` and `_is_up`, and start
  no server.
- Reconcile every Spec `spec-surface-check` names for `scripts/scribe_pg.py` and `tests/scripts/test_scribe_pg.py`:
  the memlog entry first, then `git add`, then one scoped `--write-baseline --spec <project>/<spec>` per Spec.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Never change port 5433, the DSN `src/shared/packages/pyforge-scribe/tests/unit/conftest.py` defaults to, the
  socket-directory rules or `up()`'s reuse of another checkout's listener (Epic 22's HARD boundaries).
- Never stop, signal or touch another checkout's server or data directory.
- Never start a container.
- Never hand-edit `SPEC.md`; CAP-31's text moves only through marshal Story 113.7's memlog event and re-derive.
- Never hand-edit `sprint-status-ledger.yaml`, and never run a bare `spec_surface_check.py --write-baseline`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| never initialised | no `PG_VERSION` | `no cluster to stop`, exit 0 | — |
| initialised, stopped, another server on :5433 | `PG_VERSION`, no `postmaster.pid` | `not running`, exit 0, no `pg_ctl` | — |
| initialised, stopped, port free | `PG_VERSION`, no `postmaster.pid` | `not running`, exit 0, no `pg_ctl` | — |
| running | `PG_VERSION` and `postmaster.pid` | `pg_ctl stop`, `stopped`, exit 0 | stop fails and a server answers: exit 1 |

</intent-contract>

## Binding

Parent: `spec-pyforge-scribe` CAP-31; a `fix`, so no new CAP; no FR (CAP-31 states no requirement of Scribe's users).
Parent capability:
- `spec-pyforge-scribe` CAP-31 — the local Postgres cluster starts from any checkout.
Dream: `docs/dreams/pyforge-scribe.md` (the 2026-09-25 entry; the 2026-11-01 EGM audit residue).
Ledger key: `22-2-scribe-pg-down-stops-only-this-checkout-s-cluster`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none. This is a `fix` (`spec-feature-flag-governance` Q1).
EGM audit findings: SCR-M-Z1, SCR-M-D5, SCR-M-C4 (cluster SCR-1, the code half).
Surface: `scripts/scribe_pg.py` (`down()`), `tests/scripts/test_scribe_pg.py` (one offline case).

## Epic excerpt

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-scribe CAP-31 (no FR); a fix, no new CAP.
See `epics.md` § Story 22.2 for the full Given / When / Then / And.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_scribe_pg.py` — expected: pass (the
  `scripts-suite` leg that `pr-preflight` runs).
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (the station's `verify_commands`).
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

**Manual checks:**
- With this checkout's cluster stopped and another checkout's server up on :5433:
  `pixi run -e pyforge-scribe-pg scribe-pg-down` — expected: `[scribe-pg] not running`, exit 0.

## Spec Change Log

- 2026-11-01 — minted `backlog` from the EGM fleet audit (marshal Story 113.7; operator triage 2026-11-01).

## Auto Run Result

Status: backlog
