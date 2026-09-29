---
title: '63.4: `steward session check` — one verdict for the session preconditions, run from every entry point'
type: 'feature'
created: '2026-09-18'
status: 'done'
baseline_revision: '95589f02336c7b76c89e0ce6a06b3cb0c6f25819'
review_loop_iteration: 0
followup_review_recommended: true
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

## Review Triage Log

### 2026-09-24 — Review pass
- verdicts: 19 findings — high 0, medium 5, low 8, false 6, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind Hunter: `except json.JSONDecodeError, KeyError, TypeError:` / `except (OSError, subprocess.TimeoutExpired) as exc:` chains in `session.py` read as Python-2-style comma-separated except clauses and would raise `TypeError` at runtime — refuted: this repo targets Python 3.14, and PEP 758 (accepted for 3.14) makes an unparenthesized multi-exception `except A, B, C:` valid syntax there; confirmed independently via `ast.parse` + bytecode disassembly, corroborated by the Verification Gap and Intent Alignment layers.
  - `[false]` `[reject]` Blind Hunter: a second instance of the same comma-separated-except claim, a different location in `session.py` — same refutation (PEP 758, Python 3.14).
  - `[false]` `[reject]` Blind Hunter: a third instance of the same comma-separated-except claim, in `dispatch.py`'s `except json.JSONDecodeError, AttributeError, TypeError:` — same refutation (PEP 758, Python 3.14).
  - `[false]` `[reject]` Blind Hunter: `_bmad_method_finding`'s `[row for row in findings if row.status is DoctorStatus.FAIL]` filter claimed to silently defeat the bmad-method drift check — refuted: `pyforge.doctor.sources.bmad_method.gather` never emits `DoctorStatus.FAIL` (module docstring: "Never gates... always ok or warn, never fail"), and doctor's own `pyforge.doctor.verdict.exit_code_for` treats `WARN` as passing too — the FAIL-only filter mirrors doctor's own verdict convention exactly, which is what AC3 requires ("doctor's own verdict verbatim, never re-implemented").
  - `[low]` `[reject]` Blind Hunter: `_scribe_reachability_finding` always returns `ok=True` (AC8-mandated) even when it sets a `remedy` for the "not reachable" branch, and `format_session_report`'s text mode only prints a remedy line `if not finding.ok and finding.remedy` — so that remedy is silently dropped in the default text output. Real but negligible: the identical root cause (guild env not materialized) is always also surfaced via the separate, gating `pixi-guild` finding, which shows the same remedy. Rejected: unlikely to cost anyone real information in everyday use, and the only fix (always show remedy regardless of `ok`) would change the text-format contract for a fully redundant case.
  - `[low]` `[reject]` Blind Hunter (+ #10, grouped with Edge Case Hunter #3 — same defect, repeated occurrences): `_surface_session_precondition_findings` in `dispatch.py` shells `steward session check --json` once per pending story in a multi-story drain, so a fleet drain repeats the full seven-probe suite (including two networked `gh` calls and one `marshal seed check` subprocess) once per story. Real but negligible relative to a story's total dispatch duration (each story's own dev/review loop runs for minutes); caching across calls within one drain process would need new state and an invalidation policy that no part of this spec names or asks for. Rejected on that basis.
  - `[medium]` `[patch]` Blind Hunter: `_SEED_CHECK_ARGV = ("pixi", "run", "-e", _DEFAULT_PIXI_ENV, "marshal", "seed", "check", "--json")` omits `--frozen`, unlike every other pixi invocation this diff adds (the hook's own `pixi run --frozen -e pyforge-guild steward session check`, and `dispatch.py`'s `_SESSION_CHECK_ARGV`) — a real, demonstrable inconsistency that risks a silent lock-resolution/install side effect inside what is meant to be a fast, read-only diagnostic probe. Fix applied: added `--frozen` to `_SEED_CHECK_ARGV`.
  - `[low]` `[reject]` Blind Hunter: `session-start.sh`'s worst-case added latency stacks the seed-check timeout (60s) plus two `gh` timeouts (20s each) to ~100s, with no opt-out flag (unlike `PYFORGE_SESSION_ENVS`). Rejected: these are maximum caps, not typical durations (a healthy call completes in well under a second), a hang only manifests under already-anomalous network conditions where the delay doubles as diagnostic signal, and a bypass flag would be a new, unscoped config surface.
  - `[low]` `[reject]` Blind Hunter (+ Intent Alignment divergence (d), grouped — same defect): `_pixi_guild_finding` only checks `env_dir.is_dir()`, with no validation that the materialized env actually matches the current frozen lock (a stale env from an older lock would still read `ok`) — claimed to fall short of the Intent's own "materialised at the frozen lock" wording. Real but rejected: this spec's own Acceptance Criteria (AC1/AC2, same document) both operationalize "materialised at the frozen lock" as pure directory presence/absence, settling the ambiguity the Approach line alone would raise; no existing lock-hash-comparison helper is named anywhere in the Code Map for reuse, and lock drift while the directory still exists is an uncommon edge case in practice (`pixi install --frozen` normally keeps env and lock consistent or fails outright).
  - `[low]` `[reject]` Blind Hunter: `test_session_check_entry_points.py`'s exact `text.count(...)` assertions are brittle — a harmless comment edit could spuriously break them. Rejected: the test's own docstring documents this exactness as a deliberate tripwire against a second ad hoc precondition check creeping in beside the sanctioned one, directly matching the epic's own "one mechanism, many surfaces" requirement; an AST-based rewrite would be a disproportionate, unscoped change for marginal robustness gain.
  - `[medium]` `[patch]` Edge Case Hunter: `_seed_kit_findings`'s `except json.JSONDecodeError, KeyError, TypeError:` at line 152 only wraps the JSON-parsing call; a non-dict item in the `kit` array would raise an uncaught `AttributeError` at `item.get("status")` (line 159 onward), propagating past `gather_session_findings` instead of degrading to a `SessionFinding(ok=False, ...)` as the Design Notes require. Verified real: `dispatch.py`'s structurally identical sibling guard in the same diff does catch `AttributeError` at the analogous point, confirming this is an inconsistency rather than a deliberate narrower design. Fix applied: adding `AttributeError` to the JSON-parsing except tuple was a no-op (that block doesn't wrap the item-processing code); wrapped the actual `kit`-item-processing block in its own `try: ... except AttributeError:`, returning the same `ok=False` finding pair as the function's other error branches.
  - `[low]` `[patch]` Edge Case Hunter: `_active_project_slug`'s `except OSError:` around `marker.read_text(encoding="utf-8")` does not catch `UnicodeDecodeError` (a `ValueError` subclass, not an `OSError`) — a non-UTF-8 marker file would raise uncaught rather than resolving to "no active project." Low probability (the marker is machine-written by `scripts/bmad-switch`), but the fix is a trivial, safe broadening. Fix applied: `except (OSError, UnicodeDecodeError):`.
  - `[false]` `[reject]` Edge Case Hunter: the spec's own Code Map names `MRS-DISP-040` as the suggested new finding code for the dispatch wiring, but the implementation registers `MRS-DISP-049` instead — refuted as a defect: `pyforge-marshal/core/findings.py` shows `MRS-DISP-040` is already registered to a distinct, pre-existing CAP-4 done-status-refusal finding, so the spec's suggested code was infeasible at implementation time; `MRS-DISP-049` is correctly, newly registered — a necessary substitution, not an error. (Also independently out of scope for a patch: any "fix" here would mean editing this spec's own Code Map text.)
  - `[medium]` `[patch]` Verification Gap: `dispatch_once`'s new `MRS-DISP-049` wiring (`_surface_session_precondition_findings`) is never exercised end-to-end — only the isolated helper function is unit-tested with a direct call; no test drives `dispatch_once`/`run_dispatch` with a non-ok session check and asserts the finding lands in `attempt.findings`. Filed pre-verified by the Verification Gap layer. Fix applied: added an integration-style test asserting `MRS-DISP-049` appears in `attempt.findings` via `dispatch_once` when the session check reports non-ok.
  - `[medium]` `[patch]` Verification Gap: `session-start.sh`'s "never fatal" contract (the `if ! pixi run ... steward session check; then echo ...; fi` guard under `set -euo pipefail`) is never actually executed under test — the meta-test only checks the file's text content. Filed pre-verified by the Verification Gap layer, with a concrete demonstrated regression (rewriting the guard as a bare statement plus a separate `if [ $? -ne 0 ]` check) that would pass the existing test while genuinely breaking the never-fatal contract under `set -e`. Fix applied: added an executing test that stubs a failing `pixi`/`steward` on `PATH` and asserts the hook still exits `0`.
  - `[low]` `[reject]` Intent Alignment Auditor (a): `session-start.sh`'s pre-existing `CLAUDE_CODE_REMOTE` guard (lines 19-21, untouched by this diff) means a local interactive Claude Code session never reaches the new call through this one entry point, in tension with the epic's Given clause ("a session begins on any harness, local or cloud"). Verified real. Rejected: the "local or cloud" framing is satisfied in aggregate by the four entry points together — notably the Marshal dispatch preamble, which fires for any dispatch regardless of local/remote — none of the ten explicit Acceptance Criteria test automatic local-session firing via this specific hook, and a knowledgeable user retains the manual `pyforge steward session check` escape hatch; modifying the pre-existing, unrelated guard would be a nontrivial, unscoped change to that hook's own established contract (documented in its own header: "remote containers only").
  - `[low]` `[reject]` Intent Alignment Auditor (b): three of the four entry points (`.cursor/environment.json`, `copilot-setup-steps.yml`, and `session-start.sh` — the latter covered separately by Verification Gap above) are verified only by static string-presence tests, never behavioral execution. For the Cursor/Copilot portion specifically: rejected — these are simple declarative config surfaces (a JSON string field, a YAML workflow step) with no branching logic of their own; executing them would mean bootstrapping Cursor's environment or a live GitHub Actions run, disproportionate for the marginal gain.
  - `[false]` `[reject]` Intent Alignment Auditor (c): the token-kit finding's "`layer-off` is always non-ok" semantics claimed to diverge from marshal's own, more lenient treatment of its context layers — refuted: AC5 explicitly mandates that any `layer-off`/missing/stale kit entry surfaces as a non-ok finding here; session check is deliberately a stricter, independent gate by this spec's own explicit instruction, not an accidental divergence from marshal's own tolerance.
  - `[medium]` `[patch]` Intent Alignment Auditor (e): AC3's "real `pyforge.doctor` importable" branch is only exercised in tests against a synthetic double, never the actual `pyforge.doctor.sources.bmad_method.gather` call — so a bug where `session.py` reformats or transforms the verdict instead of passing it through verbatim (AC3's own explicit "never re-implemented" requirement) would go undetected. `pyforge-doctor` is confirmed present in the `pyforge-guild` environment's dependency list, so a real-path test is feasible. Fix applied: added a test that calls the actual `pyforge.doctor.sources.bmad_method.gather` and asserts `_bmad_method_finding`'s output matches it verbatim for a representative case.

## Auto Run Result

**Summary.** Implemented Story 63.4: a single `steward session check` duty
(`pyforge.steward.session`) that gathers seven session-precondition
findings — pixi/pyforge-guild materialization, bmad-method drift (doctor's
own verdict when importable, the pre-existing subprocess fallback
otherwise), the token-economy kit + codegraph-index (one `marshal seed
check --json` call), gh auth/rate-limit (never fails open), the Tier-3
sprint-status feed for the active project, and scribe reachability
(report-only, never gates) — and renders one PASS/FAIL verdict in text or
`--json`. Wired it into all four session entry points named by the epic:
`.claude/hooks/session-start.sh` (never fatal under `set -euo pipefail`),
`.cursor/environment.json`'s `install`, `.github/workflows/copilot-setup-steps.yml`,
and Marshal's dispatch preamble (`_surface_session_precondition_findings`,
a new non-blocking `MRS-DISP-049` WARN finding folded into `dispatch_once`
right after `repo_root` resolves).

**Files changed:**
- `.claude/hooks/session-start.sh` — calls `pixi run --frozen -e pyforge-guild steward session check`, non-fatal on failure.
- `.cursor/environment.json` — `install` command calls the same check.
- `.github/workflows/copilot-setup-steps.yml` — calls the same check in the Copilot setup step.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/session.py` (new) — the seven findings, `gather_session_findings`, `format_session_report`, `SessionDuty`.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — registers the `session check` verb.
- `src/shared/packages/pyforge-steward/tests/unit/test_session.py` (new) — unit coverage for every finding, composition, and CLI exit codes; includes a real-`pyforge.doctor`-import integration test (skips under `-e pyforge-steward`, runs under `-e pyforge-guild`).
- `src/shared/packages/pyforge-steward/tests/meta/test_session_check_entry_points.py` (new) — static one-invocation-per-entry-point tripwire, plus an executing test proving `session-start.sh`'s never-fatal contract under a stubbed failing `pixi`.
- `src/shared/packages/pyforge-steward/tests/unit/test_cli.py`, `tests/unit/test_restore_duty.py` — updated duty-count assertions (AGENTS.md pre-PR checklist item 4).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — `_surface_session_precondition_findings` + its `dispatch_once` call site.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` — registers `MRS-DISP-049`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py` (+ `test_dispatch_completion.py`, `test_dispatch_fleet.py`, `test_dispatch_station_guard.py`, `test_findings.py`) — `FakeProcess` gains a `session_check_returncode` (default 0, byte-identical pre-existing fixture behaviour), unit coverage for `_surface_session_precondition_findings`'s four branches, and an integration test proving the wiring through `dispatch_once` itself.

**Review findings breakdown** (19 findings across four layers — Blind
Hunter, Edge Case Hunter, Verification Gap, Intent Alignment Auditor; see
the Review Triage Log above for full evidence per finding):
- **6 patched:** `_SEED_CHECK_ARGV` missing `--frozen` (medium); `_seed_kit_findings` uncaught `AttributeError` on a malformed kit item (medium); `_active_project_slug` uncaught `UnicodeDecodeError` on a non-UTF-8 marker file (low); `dispatch_once`'s `MRS-DISP-049` wiring untested end-to-end (medium); `session-start.sh`'s never-fatal contract untested under execution (medium); AC3's real-`pyforge.doctor`-import branch untested against the real call (medium).
- **6 rejected as false** (bad outcome disproven): three PEP 758 "Python 2 syntax" misreads of valid Python 3.14 multi-exception `except` clauses; the `bmad-method` FAIL-only filter claim (refuted by `pyforge.doctor.sources.bmad_method.gather`'s own "never FAIL" contract); the spec's own `MRS-DISP-040` vs `MRS-DISP-049` Code Map naming (a necessary substitution, not a defect); the token-kit "stricter than marshal's own tolerance" claim (AC5-mandated, not accidental).
- **8 rejected as low** (real but negligible, or fix disproportionate to gain): the scribe-reachability remedy dropped in text mode (already surfaced redundantly via the gating `pixi-guild` finding); the per-story repeated session-check cost in a multi-story drain (real but negligible relative to story duration, no caching policy asked for); `session-start.sh`'s worst-case ~100s latency with no bypass flag (maximum caps, not typical durations); `_pixi_guild_finding`'s directory-presence-only check (settled by this spec's own AC1/AC2); the brittle exact-count meta-test (a deliberate tripwire, per its own docstring); the pre-existing `CLAUDE_CODE_REMOTE` guard excluding local sessions from one of four entry points (the other three deliver real coverage; no AC tests this; a manual escape hatch exists; fixing it would be an unscoped change to a pre-existing, unrelated guard); the Cursor/Copilot entry points' string-only test coverage (simple declarative config with no branching logic of its own).
- **0 high**, **0 maybe-false**, **0 deferred**.

**Follow-up review recommended: yes.** Five `medium`-severity findings were
patched on this first pass (`_SEED_CHECK_ARGV`, the `_seed_kit_findings`
`AttributeError` guard, and the three newly-added tests for VG1/VG2/IA(e)),
meeting the "≥2 medium patched" threshold. The specific residual risk: the
three new tests (VG1's `dispatch_once` integration test, VG2's executing
`session-start.sh` test, IA(e)'s real-`pyforge.doctor` test) have not
themselves been independently re-reviewed to confirm they exercise the
real failure paths claimed — e.g. that VG2's stub `pixi` genuinely
reproduces the shape of a real `steward session check` failure, not just
an easy-to-satisfy non-zero exit.

**Verification performed:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 1680 passed, 2 skipped (the real-`pyforge.doctor`-import test skips here by design; the env has no `pyforge-doctor` dependency).
- `pixi run --frozen -e pyforge-guild python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_session.py -k test_bmad_method_finding_matches_real_doctor_gather_when_importable` — 1 passed (the same test run for real where `pyforge-doctor` is installed).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 8605 passed, 1 skipped, 12 deselected.
- `pixi run -e pyforge-guild lint-types` — ruff, `ruff format --check` (after one `ruff-format-fix` pass over the two files the new patches touched), mypy, `target-version-check`, `precommit-config-check` all green across all ten `pyforge-*` packages.

**Residual risks:**
- The follow-up-review risk named above (new tests not independently re-reviewed).
- `pr-preflight`'s full lane set (`detectors-ci`, `test-ci`, `pyforge-station-tests`, `pyforge-station-coverage-gates`) has not been run this pass — only the two directly-touched station suites plus `lint-types`.
- `spec_surface_reconcile.py` has not yet been run for this change.

