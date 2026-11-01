---
title: "15.2: Opengrep runs estate-authored rules, and its offline flags are pinned by test"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-15-1-opengrep-is-an-optional-sast-scanner-that-informs-never-publishes-the-verdict.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/sast.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py
  - src/shared/packages/pyforge-warden/tests/unit/test_sast_opengrep.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-25 ships the opengrep mechanism with no estate rules and an unpinned offline posture (line numbers at
`03a7aff5d9`):
- The package's `src/shared/packages/pyforge-warden/src/pyforge/warden/data/sast-rules/` holds one file, `planted-opengrep-match.yaml`, a test marker. A production run
  with opengrep enabled detects nothing the estate cares about (WAR-M-C4, WAR-D-C6).
- No test pins opengrep's telemetry-off invocation: `--disable-version-check` (`src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py` about :465) and the
  environment `SEMGREP_SEND_METRICS=off` and `OPENGREP_ENABLE_VERSION_CHECK=0` (about :502-503). The socket guard cannot
  see a subprocess's egress, so the argv and env are the only offline proof (WAR-M-C4, WAR-M-D6's CAP-25 half).
- With `WARDEN_OPTIONAL_SCANNERS=opengrep` and the flag `pyforge.warden.sast_opengrep` off, `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` (about
  :1334-1335) strips opengrep silently. Story 15.1's Flag line says "as today", which at mint meant a `PluginError`;
  `test_cli_filters_opengrep_when_flag_off` does not call the CLI, so the shipped behaviour is unpinned. The flip is
  already recorded in `epics.md` § Currency reconciliation — 2026-10-10; Story 15.1's text is not edited.

WAR-M-D6's CAP-23 half is rejected (Story 11.2 decided that runner errors fail open with no note; Story 13.2 narrows
that for a started run). EGM audit 2026-11-01, cluster WAR-CL-10; findings WAR-M-C4, WAR-D-C6, WAR-M-D6, accepted by
the operator on 2026-11-01; residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:**
- Move `planted-opengrep-match.yaml` to `src/shared/packages/pyforge-warden/tests/fixtures/` and make every test that used `bundled_sast_rules_dir()`
  for it pass `rules_dir` explicitly.
- Ship a few estate-authored rules in `data/sast-rules/`, drawn from the Spec's own constraints: `subprocess` with
  `shell=True`, unsafe `yaml.load`, `eval`/`exec`. Each rule has a fixture file that trips it, and a test runs the rule
  set over the fixtures (the real binary where present; the rule files parse as YAML with an `id`, `pattern(s)`,
  `message` and `severity` everywhere).
- Extend `test_opengrep_engine_argv_capture` to capture `kwargs["env"]` and assert the three telemetry-off settings.
- Make `test_cli_filters_opengrep_when_flag_off` drive `warden scan` and pin today's flag-off behaviour (stripped, no
  error).
- CAP-25 success names the telemetry-off argv and env through a `bmad-spec` re-derive.

Ledger key: `15-2-opengrep-runs-estate-authored-rules-and-its-offline-flags-are-pinned-by-test`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-warden` CAP-25 (FR-42) — SAST joins as an optional plugin: opengrep with estate-owned rules. A `fix`,
  so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag (`pyforge.warden.sast_opengrep` keeps gating
  the scanner).

## Acceptance Criteria

- **AC1 — Estate rules ship.** Given the built package, When `bundled_sast_rules_dir()` is listed, Then it holds the
  estate-authored rules (at least `shell=True`, unsafe `yaml.load` and `eval`/`exec`) and no file named
  `planted-opengrep-match.yaml`.
- **AC2 — Each rule trips.** Given each estate rule and its fixture, When opengrep runs (the test skips with a reason
  where the linux-64-only binary is absent), Then the report's `advisory` carries a note naming that rule id, the
  fixture path and line; the status and exit code equal the same run with the scanner disabled.
- **AC3 — The planted marker is a fixture.** Given `src/shared/packages/pyforge-warden/tests/fixtures/`, Then it holds the planted rule, and every
  test that runs it passes `rules_dir`.
- **AC4 — The offline posture is pinned.** Given `test_opengrep_engine_argv_capture`, When it captures the subprocess
  call, Then it asserts `--disable-version-check` in the argv and `SEMGREP_SEND_METRICS=off` and
  `OPENGREP_ENABLE_VERSION_CHECK=0` in `kwargs["env"]`; removing any one of them from `engines.py` turns it red
  (mutation, reverted).
- **AC5 — Flag-off is pinned through the CLI.** Given `WARDEN_OPTIONAL_SCANNERS=opengrep` and the flag off, When
  `warden scan` runs, Then opengrep does not run, no error is recorded, and the exit code equals a default run.
- **AC6 — The contract follows.** CAP-25 success names the telemetry-off argv and env through a `bmad-spec` re-derive,
  never a hand edit.
- **AC7 — Green.** `pixi run --frozen -e pyforge-warden pyforge-warden-test` passes.

## Boundaries & Constraints

**Always:** SAST results stay advisory notes, never a `Finding`, a rung, a status or an exit code; rules ship in the
package's data and are never fetched from a registry; an absent binary is omit-not-error (Story 9.3).

**Never:** add a registry `--config`; change the `ComplianceReport` version (1.1.0); edit Story 15.1's text in
`epics.md` (its Flag and Deps lines stay as the 2026-10-10 currency section records them); hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-warden` CAP-25 (FR-42) — SAST joins as an optional plugin: opengrep with
  estate-owned rules; a fix, no new CAP.

Parent: CAP-25

- EGM audit findings carried: WAR-M-C4, WAR-D-C6, WAR-M-D6 (its CAP-25 half; cluster WAR-CL-10; accepted 2026-11-01;
  one memlog event each on `spec-pyforge-warden/.memlog.md`); residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 15 — a fix story joins its done epic (operator rule 2026-10-04; doctor Story 41.5 lets the epic key roll up
  to `in-progress`).
- Ledger key: `15-2-opengrep-runs-estate-authored-rules-and-its-offline-flags-are-pinned-by-test`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-warden/src/pyforge/warden/data/sast-rules/`, `src/shared/packages/pyforge-warden/tests/fixtures/`, `src/shared/packages/pyforge-warden/src/pyforge/warden/sast.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py`,
  `src/shared/packages/pyforge-warden/tests/unit/test_sast_opengrep.py`.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Minted 2026-11-01 by the EGM audit landing (marshal Story 113.7, spec-pyforge-marshal:CAP-302); mode in-PR: built in the audit's landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_sast_opengrep.py -q` — expected: pass, including the env
  assertions and the CLI flag-off test.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Auto Run Result

Status: backlog

Summary: not yet dispatched.

## Spec Change Log

- 2026-11-01: minted `backlog` from the EGM fleet audit (marshal Story 113.7): cluster WAR-CL-10, findings WAR-M-C4,
  WAR-D-C6 and WAR-M-D6 (CAP-25 half), accepted by the operator; mode in-PR.

## Review Triage Log

- (none yet)
