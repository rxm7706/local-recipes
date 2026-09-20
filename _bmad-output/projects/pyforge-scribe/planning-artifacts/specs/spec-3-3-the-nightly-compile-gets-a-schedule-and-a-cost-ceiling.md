---
title: "Story 3-3: The nightly compile gets a schedule and a cost ceiling"
type: "feature"
created: "2026-08-27"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-09-18"
---

<!-- RECOVERED 2026-09-18 Tier 3 (epics.md-derived Intent + ACs). No session
     transcript or bmad-loop worktree snapshot survived as a tracked story spec
     — regenerated from epics.md per CLAUDE.md's recovery priority order. -->

## Intent

The nightly compile existed as a verb but nothing scheduled it, and the Epic 3
transcript surface made an unattended run cost-unbounded. The CLI verb is the
schedulable unit; an opt-in, operator-installed local `crontab` entry is the
trigger. GitHub Actions is disqualified: the transcript root, `.claude/memory/`,
and the `.claude/data/` graph store are all operator-local.

## Acceptance Criteria

- **Given** a transcript root of any size, **When** `scribe graph compile` (any
  mode) reaches the transcript surface, **Then** the scan is bounded as a
  precondition of unattended scheduling: a file-count cap and a total-byte
  budget (newest files first) select what is read, a per-file timeout abandons
  a pathological file with a warning instead of hanging the run, and an
  mtime+size-keyed scan cache under the graph store's own directory makes a
  re-run over an unchanged surface skip re-reading unchanged files — all bounds
  defaulting high enough to cover the live 27-file/631MB surface without
  dropping data (closes DW-FU-3-2-2).
- **Given** an operator who wants the compile nightly, **When** they follow
  `src/shared/packages/pyforge-scribe/docs/cli-runbooks.md` (herald
  `docs/cli-runbooks.md` format), **Then** a documented, opt-in `crontab -e`
  entry — path-parameterized per checkout, `cd` to the repo root,
  `flock -n`-wrapped, appending to a stated log destination
  (`~/.cache/scribe-nightly-compile.log`) — is the trigger; no GitHub Actions
  workflow is added.
- **Given** a `scribe graph compile` already running against the same graph
  store, **When** a second invocation starts (an overlapping cron firing, or an
  operator running it by hand), **Then** the second run skips cleanly — a
  non-blocking lock keyed to the store path (mirroring `capture.py::_locked`'s
  stdlib flock pattern) makes it exit 0 with a "skipped" message, never a
  corrupted double-write and never a red cron mail — and FR-11's byte-identical
  idempotent rerun still holds with the scan cache in play.
- **Given** the runbook and the bounded, guarded verb exist, **When** this
  story completes, **Then** PRD SM-4 flips to met with the runbook as evidence
  (dated notes in §7 and § Currency reconciliation), and the deferred-work
  ledger's DW-FU-3-2-2 is closed with the same date.

## Delivery Record

Merged via PR #881 (`Frontier reconcile: 4 specs truth-checked, 15 stories
minted, scribe SM-4 shipped`), merge commit `cc8b3b2b1c`, 2026-08-27T09:41:20Z.
https://github.com/rxm7706/local-recipes/pull/881

Implementation commit: `f0267f5c03` (`feat(scribe): story 3.3 -- nightly compile
bounded, locked, scheduled`). Close notes (deferred-work ledger): file-count
cap 256, total-byte budget 1 GiB newest-first, 30s per-file timeout, mtime+size
scan cache `transcript-scan-cache.json`; live re-measure 25 files / 651MB in
2.2s cold, 0.3s cached.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass
  (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `6e8cf8d258` (2026-09-18, "Recover tracked story spec for scribe 3.3"); also `f0267f5c03` (2026-08-27, "feat(scribe): story 3.3 -- nightly compile bounded, locked, scheduled (SM-4 met; DW-FU-3-2"); also `39ab78ca2b` (2026-08-07, "steward: Story 3.3 — the operator can see every environment that exists, before picking on"). Ledger row `3-3-the-nightly-compile-gets-a-schedule-and-a-cost-ceiling: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-3-3-the-nightly-compile-gets-a-schedule-and-a-cost-ceiling.md`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
