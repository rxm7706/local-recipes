---
title: "15.1: Opengrep is an optional SAST scanner that informs, never publishes, the verdict"
type: 'feature'
created: '2026-09-28'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - docs/dreams/pyforge-warden.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/scanner_plugins.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py
flag:
  key: pyforge.warden.sast_opengrep
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "opengrep is not a selectable optional scanner and no SAST note is written, as today"
  cleanup: 90 days after ON in every environment (Q4)
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Blocked (cross-station):** this story needs the `opengrep` conda package, which mason Story 21.4 builds (the Dream's
constraint: engines arrive as conda packages with tested version ranges, never curl-fetched). The Deps parser is
station-local, so the ledger row is minted `blocked`; the operator flips it once mason 21.4 is `done` and the package
resolves in the `pyforge-warden` environment.

**Problem:** Warden has no SAST lens. The PR-gate hook book has optional scanner slots (`scanner_plugins.py`:
Checkmarx, Sonar, Black Duck, `ghas`, profile-local — all stubs) and one real advisory lens (`tea_advisory.py`). The
operator ruled on 2026-09-28 that opengrep (LGPL-2.1) takes the SAST slot with rules the estate owns; CodeQL is rejected
because its CLI licence covers private code only with a GitHub Code Security licence.

**Approach:** An `OpengrepScanPlugin` registers on `PR_GATE_SCAN` beside the stubs and is enabled like them through
`WARDEN_OPTIONAL_SCANNERS=opengrep`. A new `sast.py` builds the argv — the local rules directory shipped in the package
data (`data/sast-rules/`), JSON output to a system-temp file, metrics off, no registry config — and `engines.py` runs it
through `_engine_env()` under a declared tested version range. Each result becomes one non-`Finding` advisory note
(`tool: opengrep`, rule id, path, line, severity) appended to `context["advisory_notes"]`, the TEA lens's shape
(suite:AD-4), so it lands in the report's open `advisory` array and never in `plugin_findings`. An absent binary is
omit-not-error; an out-of-range version or unparseable output is an advisory note saying so, never a rung. The flag is
read through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract); with it OFF, `opengrep` is not selectable.

Ledger key: `15-1-opengrep-is-an-optional-sast-scanner-that-informs-never-publishes-the-verdict`.
Ledger status (do not edit the ledger): `blocked`.
Type / Effort / Deps: feature / M / — (cross-station: mason Story 21.4).

### Living CAP citations

- `spec-pyforge-warden` CAP-25 (FR-42); suite:AD-4 (an advisory never gates); Story 9.3 (omit-not-error).
- `spec-feature-flag-governance:CAP-1`.

## Acceptance Criteria

- Given `WARDEN_OPTIONAL_SCANNERS=opengrep`, the flag ON and a fixture repo that trips an estate rule, When `warden scan` runs, Then the report's `advisory` carries a note naming `opengrep`, the rule id, the path and the line
- Given the same repo, When it is scanned with the scanner enabled and disabled, Then the status and the exit code are equal
- Given the invocation, When its argv is captured, Then it names only the local rules path and no registry config, and the socket-guard stays green
- Given no `opengrep` binary on PATH, When a default run happens, Then it is green (the Story 9.3 test stays green) and no note is written
- Given the flag OFF, When `WARDEN_OPTIONAL_SCANNERS=opengrep` is set, Then the scanner is not selected and nothing changes

## Boundaries & Constraints

**Always:**
- Advisory notes only: never a `Finding`, a finding family, a rung, a status or an exit code; the `ComplianceReport` stays 1.1.0.
- Spawn opengrep only through `_engine_env()`, with a tested version range declared in the member `pixi.toml` and mirrored in code.
- Ship the rules in the package; keep them few, estate-authored and each with a fixture that trips it.
- A `pixi.toml` change regenerates `environment.yaml` in the same PR; run `pyforge-station-tests` when `pixi.lock` moves.
- Read the flag only through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract) over the one tree (canopy:AD-11). If 75.1 has not landed when this story runs, add it in `pyforge.core` in exactly 75.1's shape (`read_boolean(key, default=False)`, `cutover_root.py`'s tree resolution, False with a named WARN for a missing tree, key or non-bool value; a `spec-pyforge-core` co-governor reconcile) — never a station-local reader or a second tree. Add the key to `src/platform/config/flags.json` (default OFF).
- Reconcile `spec-pyforge-warden` and every co-governor `spec-surface-check` names; scoped stamps only.

**Never:**
- Use CodeQL, `--config auto`, a registry ruleset, or anything that phones home.
- Publish a verdict or call `publish_pr_gate_verdict` from the plugin.
- Build the opengrep package here (mason Story 21.4 owns it).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| rule tripped | fixture file matching an estate rule | one advisory note | — |
| no match | clean fixture | no note | — |
| binary absent | not on PATH | omit-not-error | default run green |
| out-of-range version | `opengrep --version` outside the range | an advisory note naming the range | never a rung |
| unparseable output | malformed JSON | an advisory note saying so | never a rung |
| flag OFF | key off | not selectable | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-warden` CAP-25 (FR-42).
Dream: `docs/dreams/pyforge-warden.md` § Realization log → *2026-09-28 (night) — Proposed: the fix-PR actuator finishes the fix, SAST joins as a plugin, and Warden scans the enterprise fleet*.
Ledger key: `15-1-opengrep-is-an-optional-sast-scanner-that-informs-never-publishes-the-verdict`.
Ledger status at mint: `blocked` — until mason Story 21.4 (the opengrep conda package) is `done`; the operator flips the row.
Deps: — (cross-station: mason Story 21.4).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- Flag ON/OFF: a test writes two flagd trees (`pyforge.warden.sast_opengrep` on, then off; the `src/platform/tests/test_openfeature_file_flags.py` shape until the `spec-feature-flag-governance:CAP-4` fixture lands): ON selects the scanner and writes the note, OFF leaves the report unchanged.
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (`pixi.lock` moved for the run-dependency).
- `pixi run -e pyforge-guild spec-surface-check` exits 0 after the scoped stamps.

## Review Triage Log

- No review yet (minted 2026-09-28, `blocked`). Implementation and review stay separate.
