---
title: '63.4: `steward session check` — one verdict for the session preconditions, run from every entry point'
type: 'feature'
created: '2026-09-18'
status: 'in-progress'
baseline_revision: '95589f02336c7b76c89e0ce6a06b3cb0c6f25819'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a session begins on any harness, local or cloud

**Approach:** it reports, as findings not prose: pixi present and `pyforge-guild` materialised at the frozen lock; `bmad-method` at the pinned version (reuse doctor's drift verdict, do not re-implement); the token kit — `headroom` on PATH, this harness's caveman skill installed, the three context layers not `layer-off` (reuse `marshal seed check`); `gh auth status` and `gh api rate_limit` (an unauthenticated s…

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-63-4-steward-session-check-one-verdict-for-the-session-preconditions-run-from-every-entry-point.md` (CHAIN-STANDARD §5).
- This file is the tracked dispatch target for `marshal factory dispatch` / `resolve_story_spec_path`.

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| a session begins on any harness, local or cloud | `pyforge steward session check` runs | it reports, as findings not prose: pixi present and `pyforge-guild` materialised at the frozen lock; `bmad-method` at the pinned version (reuse doctor's drift verdict, do not re-implement); the token… | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the four entry points call this one command and nothing else for preconditions (vocabulary-one-name-one-job: one mechanism, many surfaces); a cloud clone with no feed can land a ledger flip by follow… | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/interfaces.py` — `Duty` Protocol (`name`, `run(ns) -> DutyResult`) and frozen `DutyResult(ok, summary, details)`; the new `SessionDuty` must conform.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/bootstrap.py` (new sibling module `session.py` mirrors this shape) — `ValidateFastStep` frozen dataclass (line 455), `validate_fast_steps()` (line 470) gathering multiple sub-checks into a tuple, `format_validate_fast_report()` (line 543, text+JSON), `ValidateFastDuty` (line 653). `_DEFAULT_PIXI_ENV = "pyforge-guild"` (line 40) and `repo_root()` (line 84) are directly reusable.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `DUTIES` tuple (~line 47), `_HELP` dict, `build_parser()`'s shared elif branch for `("init", "shell-init", "setup", "initrepo", "validate-fast")` (line 221 — always adds `--json`; `initrepo`/`validate-fast` also add `--repo`/`--env` at line 246) is the pattern to extend with `"session"`; `resolve_duty()` (~line 1260) mirrors the `"validate-fast"` branch (`from .bootstrap import ValidateFastDuty`).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py::gather(target: Path) -> tuple[Finding, ...]` (line 1233) — the bmad-method pinned-version drift verdict; reuse verbatim, never re-implement. Doctor's `Finding` (`pyforge/doctor/models.py:375`: `source, check, status, message, evidence`) — read `status`, never re-derive.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py:3567-3603` (`_import_drift_factory` / `_run_bmad_drift_task`) — the exact try-import-else-subprocess-fallback shape to copy: direct `pyforge.doctor` import when available, else shell `pixi run -e pyforge-guild bmad-drift-check`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/check.py` — `CheckReport.kit` (`tuple[KitCheck, ...]`, always 3 entries in `KIT_ITEMS` order — `output`/`wire`/`structure-graph`) and `CheckReport.to_json_dict()`'s `"kit"` array. `run_check()` needs marshal's bundled `Manifest` + `resolve_context_layers` (loaded only by `cli/seed.py`, no one-call helper) — reuse instead via subprocess `pyforge marshal seed check --json`, parsed for the `kit` entries, covering both the token-kit finding (headroom/caveman/context-layers) and the codegraph-index finding (`structure-graph`'s `KitCheck`) from one call.
- No existing helper — new code: `gh auth status` / `gh api rate_limit` probes (JSON, non-zero/rate-limited is a finding, never silently ok — drift probes fail open per `feedback_unauthenticated_github_probes_fail_open`).
- No unifying helper — new code: Tier-3 feed path `_bmad-output/projects/<slug>/implementation-artifacts/sprint-status.yaml` vs. tracked twin `_bmad-output/projects/<slug>/planning-artifacts/sprint-status-ledger.yaml` (shape confirmed at `scripts/fleet_scan.py:1412`); `<slug>` from `BMAD_ACTIVE_PROJECT` env var or an optional `--project` flag. Missing feed's remedy is the exact command from this spec's own `Then`: `cp planning-artifacts/sprint-status-ledger.yaml implementation-artifacts/sprint-status.yaml`.
- No existing helper — new code: scribe reachability, report-only, never fails the run on its own (`shutil.which("scribe")` or equivalent probe; `pyforge-scribe/src/pyforge/scribe/cli.py:313` `recall_cmd` is the surface being probed, not called).
- Entry points (exact insertion points):
  - `.claude/hooks/session-start.sh` — after the per-env `pixi install --frozen -e "$env"` loop (line 46), before the `CLAUDE_ENV_FILE` persistence block (line 48).
  - `.cursor/environment.json` — append to the `"install"` string (line 3), after `pixi install -e pyforge-guild`.
  - `.github/workflows/copilot-setup-steps.yml` — new step after "Prove the Guild env" (lines 29-30).
  - `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py::dispatch_once` (line 1682, the dispatch preamble) — append a new pre-launch `Finding` the way `_surface_worktree_wip_before_dispatch` (line 372, invoked ~line 2087) already does: shell `pyforge steward session check --json`, fold a non-ok verdict into `findings` (new code `MRS-DISP-040`). Marshal calls the steward CLI, never imports `pyforge.steward` (this spec's own Binding line).
- `src/shared/packages/pyforge-steward/tests/unit/test_bootstrap.py:34-54,120` — the two-tier test pattern to mirror: monkeypatch `shutil.which`/subprocess seams and call the gather function directly per finding, plus one CLI-level exit-code test.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/session.py` -- new module: `SessionFinding` frozen dataclass (`name, ok, detail, remedy`), `gather_session_findings(*, root, project) -> tuple[SessionFinding, ...]` producing the seven findings, `format_session_report(...)` (text+JSON), `SessionDuty` -- mirror `bootstrap.py`'s `ValidateFastDuty` shape.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- add `"session"` to `DUTIES`, `_HELP["session"]`, extend the shared elif branch (`--json` always, `--repo`/`--project` optional), add the `resolve_duty` branch importing `SessionDuty`.
- `.claude/hooks/session-start.sh` -- call `pyforge steward session check` (via the materialized `pyforge-guild` env) at the pinned insertion point; a non-ok result is surfaced, never silently swallowed.
- `.cursor/environment.json` -- append the same call to `"install"`.
- `.github/workflows/copilot-setup-steps.yml` -- add a step running the same call after "Prove the Guild env".
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` -- `dispatch_once` shells `pyforge steward session check --json` and appends `MRS-DISP-040` on a non-ok verdict, mirroring `_surface_worktree_wip_before_dispatch`'s shape.
- `src/shared/packages/pyforge-steward/tests/unit/test_session.py` -- new: one unit test per finding (monkeypatched seams) plus one CLI-level exit-code test (`0`/`1`/`70`).

**Acceptance Criteria:**
- Given `pyforge-guild` is materialized at the frozen lock, when `pyforge steward session check` runs, then it reports an ok finding for pixi/`pyforge-guild` and, with every other finding ok, exits `0`.
- Given `pyforge-guild` is not materialized, when the command runs, then it reports a non-ok finding naming `pixi install --frozen -e pyforge-guild` as the remedy and exits `1`.
- Given `pyforge.doctor` is importable, when the command runs, then the bmad-method finding is `pyforge.doctor.sources.bmad_method.gather`'s own verdict verbatim, never re-implemented.
- Given `pyforge.doctor` is NOT importable, when the command runs, then it falls back to `pixi run -e pyforge-guild bmad-drift-check` exactly as `upgrade.py::run_bmad_drift_integrity` does, rather than raising.
- Given `marshal seed check --json`'s `kit` array reports any of the three context layers as `layer-off`/missing/stale, when the command runs, then the corresponding kit entry surfaces as a non-ok finding, and the same call's `structure-graph` entry also drives the codegraph-index finding.
- Given `gh auth status` or `gh api rate_limit` reports an unauthenticated or exhausted session, when the command runs, then that surfaces as a non-ok finding (never defaults to ok on a probe failure).
- Given the Tier-3 feed is absent for the project in hand, when the command runs, then it reports a non-ok finding whose remedy is exactly `cp planning-artifacts/sprint-status-ledger.yaml implementation-artifacts/sprint-status.yaml`.
- Given scribe recall is unreachable (the `pyforge-guild` default), when the command runs, then that finding is reported but never flips an otherwise-clean run's exit code.
- Given an uncaught exception during gathering, when the command runs, then `main()`'s existing handler exits `70`; `SessionDuty.run` itself never calls `sys.exit` (AD-8).
- Given all seven findings are ok, when the command runs, then it exits `0`; given any is non-ok, it exits `1`.

## Design Notes

`session.py` is a peer of `bootstrap.py`, not an extension of it -- `ValidateFastDuty` stays scoped to its own onboarding gate. Findings (b) and (c)/(e) delegate to another station's already-published verdict (doctor's `bmad_method.gather`, marshal's `seed check --json`) rather than re-deriving pin/kit logic; new code is confined to the three probes nothing already exposes (gh, Tier-3 feed presence, scribe reachability). Every finding degrades to a `SessionFinding(ok=False, ...)`, never an exception -- only a genuinely unexpected error (e.g. `pixi.toml` unreadable) should propagate to `main()`'s `70`.

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: `src/shared/packages/pyforge-steward/src/pyforge/steward/` (new `session` duty, `pyforge steward session check`, exit domain `0` ok / `1` findings / `70` crash), `.claude/hooks/session-start.sh`, `.cursor/environment.json` (`start`), `.github/workflows/copilot-setup-steps.yml`, the Marshal dispatch preamble (`pyforge-marshal` calls the steward CLI, never imports it), station tests.
Ledger key: `63-4-steward-session-check-one-verdict-for-the-session-preconditions-run-from-every-entry-point`.
Ledger status at mint (unchanged): `backlog`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-63-4-steward-session-check-one-verdict-for-the-session-preconditions-run-from-every-entry-point.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** S-63.1, S-63.3 • **FR/AD:** spec-pyforge-steward CAP-5; AD-8 (`DutyResult` is frozen evidence; duties never `sys.exit`)
**Surface:** `src/shared/packages/pyforge-steward/src/pyforge/steward/` (new `session` duty, `pyforge steward session check`, exit domain `0` ok / `1` findings / `70` crash), `.claude/hooks/session-start.sh`, `.cursor/environment.json` (`start`), `.github/workflows/copilot-setup-steps.yml`, the Marshal dispatch preamble (`pyforge-marshal` calls the steward CLI, never imports it), station tests.
**Given** a session begins on any harness, local or cloud
**When** `pyforge steward session check` runs
**Then** it reports, as findings not prose: pixi present and `pyforge-guild` materialised at the frozen lock; `bmad-method` at the pinned version (reuse doctor's drift verdict, do not re-implement); the token kit — `headroom` on PATH, this harness's caveman skill installed, the three context layers not `layer-off` (reuse `marshal seed check`); `gh auth status` and `gh api rate_limit` (an unauthenticated session is a finding, because drift probes fail open); the codegraph index present (absent in every fresh clone); **the Tier-3 feed present for the project in hand — and when absent, the one sanctioned remedy: seed it by copying the tracked twin (`cp planning-artifacts/sprint-status-ledger.yaml implementation-artifacts/sprint-status.yaml`; verified 2026-09-16 in a fresh clone: `sprint-ledger-sync` then reports `unchanged`, tree clean)**; scribe recall reachability (absent by design in `pyforge-guild` — reported, not failed)
**And** the four entry points call this one command and nothing else for preconditions (vocabulary-one-name-one-job: one mechanism, many surfaces); a cloud clone with no feed can land a ledger flip by following the printed remedy
**Status:** backlog

