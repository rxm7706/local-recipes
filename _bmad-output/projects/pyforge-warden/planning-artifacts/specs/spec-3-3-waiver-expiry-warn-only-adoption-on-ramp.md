<!-- RECOVERED 2026-07-25 from Claude Code session transcript 12db9514-1d7c-46c7-98ea-bd92bc2108f6.jsonl (~/.claude/projects); this is the ORIGINAL spec incl. its dev/review narrative, not an epics.md regeneration. -->
---
title: 'Waiver expiry + warn-only adoption on-ramp'
type: 'feature'
created: '2026-07-17'
status: shipped
updated: '2026-07-27 (AUD-WARDEN-030 status sync)'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Today an expired waiver already re-blocks correctly (`waiver.apply_waivers` leaves the rung untouched, so the original severity-driven status/exit code survives) but this happens with zero visibility — an expired match is silently indistinguishable from "no waiver ever existed." Separately, a repo adopting the gate over pre-existing findings has no non-blocking mode, so day-one is always a red wall (FR23/FR25), which discourages adoption.

**Approach:** Extend `apply_waivers` to also emit review-visible notices for expired (not just applied) waiver matches, surfaced in the text report. Add a `--warn-only` CLI flag that downgrades any still-blocking rung (`policy-violation`/`indeterminate`, never `error`) to `warn` before verdict composition, plus a graduate-to-enforcing nudge in the text report.

## Boundaries & Constraints

**Always:**
- The exit-code re-block mechanism ITSELF already works today (`apply_waivers` leaves an expired match's rung untouched) — do not change that fall-through behavior, only add visibility around it.
- `--warn-only` downgrades rung STATUS (`policy-violation`/`indeterminate` → `warn`) BEFORE `verdict.compose`/`assemble_report`, mirroring `waiver.bypass_blocking`'s existing shape exactly — never widen `models._LEGAL_EXITS_BY_STATUS`, never touch `verdict.py`, never let a non-`verdict.py` module compute or literal-guard an exit code (`tests/meta/test_verdict_sole_ownership.py` enforces this for every module except `verdict.py`).
- `Status.ERROR` rungs are NEVER downgraded by `--warn-only` — a tool malfunction must always surface honestly regardless of adoption mode.
- Expired-waiver visibility and the warn-only nudge are `render_text`-only (non-contract) additions, matching Story 3.2's own precedent that waiver notices are not part of the `--format json` schema — no `report-schema.json`/`schema_version` change in this story.
- Keep `WaiverNotice`'s shape unchanged; return expired matches as a separate list from `apply_waivers` rather than adding a field to the existing frozen dataclass.

**Block If:** none — this is a bounded, resolvable design; no unresolved human decision remains.

**Never:**
- Do not implement `--require-full-coverage` (a related-but-separate future flag the PRD only mentions in passing) or a `[tool.pyforge-warden]` `warn-only` TOML config key — epics.md's AC text spells `--warn-only` as CLI-only, matching the existing precedent that some knobs are CLI-only (`--fail-on`) and some are TOML-only (`dep001-block-confidence`, `waiver-default-expiry-days`).
- Do not implement the `review_required: true` machine field mentioned in planning docs for a bypassed/waived report — that is unshipped Story-3.2-adjacent scope, not named by this story's own ACs; leave it as a known gap, not this story's problem.
- Do not add a "scan the waiver file for orphaned/unused entries not matching any current finding" feature — expired-waiver flagging is scoped to waivers that match a rung in THIS scan, exactly mirroring `apply_waivers`'s existing per-rung match loop.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Expired waiver on a real policy-violation | `.warden-waivers.yaml` waives `vuln:PDOS-FIXTURE-0001:pdos-vuln-fixture@1.0.0` with `expires_at` in the past; `pyproject.toml` pins `pdos-vuln-fixture==1.0.0` (seeded CRITICAL OSV advisory, ambient test DB) | `status=policy-violation`, `exit_code=1` (unchanged from today); text output gains a new, distinct line for that waiver id flagging it expired/re-blocked (reason, authorized_by, expires_at) | No error expected |
| Same, `--format json` | Same as above, `--format json` | `status.value == "policy-violation"`, `exit_code == 1`, document still schema-valid (waiver notices stay text-only) | No error expected |
| Active (non-expired) waiver | Same fixture, `expires_at` in the future | Byte-for-byte unchanged from today: `bypassed`/exit 0, existing `[waiver]` line, no expired-notice line | No error expected |
| `--warn-only` on a repo with a real policy-violation | Same critical-vuln fixture, `--warn-only`, no waiver file | `status=warn`, `exit_code=0`; text output includes a nudge naming the finding count and how to enforce (e.g. via `--fail-on`) | No error expected |
| `--warn-only` with a malformed committed waiver file | Malformed `.warden-waivers.yaml`, `--warn-only` | `status=error`, `exit_code=2` — `--warn-only` never downgrades `Status.ERROR` | Existing `WaiverParseError`/`WaiverValidationError` → `ErrorKind` path, untouched |
| `--warn-only` on an already-clean repo | No findings, `--warn-only` | `status=clean`, `exit_code=0`, no nudge line (nothing to graduate from) | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-warden/src/pyforge/warden/waiver.py` -- `apply_waivers` (L307-340) gains an expired-notice return value; new `bypass_blocking`-shaped (L343-361) downgrade function for `--warn-only`
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` -- new `--warn-only` flag (near `--bypass`, ~L311-320); wiring at the waiver-application block (~L740-779) to unpack the new return value, call the downgrade function, and thread `expired_waivers`/`warn_only` into `render_text` (~L825)
- `src/shared/packages/pyforge-warden/src/pyforge/warden/report.py` -- `render_text` (L314-357) gains `expired_waivers`/`warn_only` params and new output lines
- `src/shared/packages/pyforge-warden/tests/unit/test_waiver.py` -- update `test_expired_match_leaves_the_rung_untouched` (L385, currently asserts the notices list is empty) for the new 3-tuple return + populated expired-notice; add coverage for the new downgrade function
- `src/shared/packages/pyforge-warden/tests/unit/test_cli_bypass.py` -- update/rename `test_expired_waiver_is_not_echoed_in_text_format` (L247); add a real policy-violation expiry scan (critical-vuln fixture + waiver file in `tmp_path`, mirroring `tests/conformance/test_scan_harness.py:867`'s `pdos-vuln-fixture==1.0.0` technique) and new `--warn-only` scans
- `src/shared/packages/pyforge-warden/tests/meta/test_verdict_sole_ownership.py` -- regression gate only, no edits expected; confirms the new `waiver.py` function stays guard-safe (never enumerate the full 7-status lattice order, never call an exit primitive)

## Tasks & Acceptance

**Execution:**
- [ ] `waiver.py` -- change `apply_waivers` to return `(rungs, applied_notices, expired_notices)`: an expired match now also produces a `WaiverNotice` added to `expired_notices` (rung left untouched, exactly as today) — makes the already-correct re-block visible for review
- [ ] `waiver.py` -- add a `bypass_blocking`-shaped function rewriting every `POLICY_VIOLATION`/`INDETERMINATE` rung to `WARN` (leaving `ERROR` and every already-non-blocking/`WARN` rung untouched) — the `--warn-only` mechanism; must not enumerate the full 7-status lattice order
- [ ] `cli.py` -- add `--warn-only` (`store_true`, default `False`) next to `--bypass`; after the existing waiver/`--bypass` block, when `args.warn_only` is set, call the new downgrade function on `rungs` before `assemble_report`
- [ ] `cli.py` -- unpack `apply_waivers`'s new 3-tuple; pass `expired_waivers` and `warn_only=args.warn_only` into `render_text`
- [ ] `report.py` -- `render_text` renders one line per `expired_waivers` entry (id/reason/authorized_by/expires_at + a marker distinct from `[waiver]`, e.g. `[waiver-expired]`, indicating re-block/needs-review) and, when `warn_only` is true and the report is non-clean/non-not-applicable, one nudge line naming the finding count and how to graduate (mention `--fail-on`)
- [ ] `tests/unit/test_waiver.py` -- update the expired-match test for the new return arity and populated `expired_notices`; add a test for the new downgrade function (policy-violation/indeterminate → warn; error and already-bypassed/clean untouched)
- [ ] `tests/unit/test_cli_bypass.py` -- add a real critical-vuln + expired-waiver scan asserting `status=policy-violation`/`exit_code=1` (both text and json format) with the new expired-notice line present; add `--warn-only` scans covering the downgrade, the nudge text, and the malformed-waiver-file-still-errors case

**Acceptance Criteria:**
- Given a `.warden-waivers.yaml` entry matching a real critical-vuln finding with `expires_at` in the past, when scanned, then `status=policy-violation`/`exit_code=1` (both text and json) and the text report includes a distinct, review-visible line for that expired waiver (id, reason, authorized_by, expires_at)
- Given `--warn-only` on a repo whose only finding would otherwise compose `policy-violation` or `indeterminate`, when scanned, then `status=warn`/`exit_code=0` and the text report includes a nudge naming how many findings and how to enforce
- Given `--warn-only` with a malformed committed waiver file, when scanned, then `status=error`/`exit_code=2` unchanged — `--warn-only` never downgrades a tool error
- Given a still-active (non-expired) committed waiver, when scanned, then behavior is byte-for-byte unchanged from pre-3.3 (`bypassed`/exit 0, `[waiver]` line, no expired-notice line)

## Design Notes

`models._LEGAL_EXITS_BY_STATUS[Status.POLICY_VIOLATION] == frozenset({1, 130})` unconditionally — unlike `--allow-empty`'s narrow, driver-scoped widening of `INDETERMINATE`'s legal exits, there is no equivalent per-driver exception for `POLICY_VIOLATION`. This is why `--warn-only` MUST rewrite the rung's `Status` to `WARN` (already legal at exit 0) rather than attempt an exit-code-only downgrade while status stays `policy-violation` — that combination raises in `ComplianceReport.__post_init__` today. `bypass_blocking`'s existing shape is the template:

```python
def bypass_blocking(rungs):
    return [
        (Status.BYPASSED if driver is not None and status not in _NON_BLOCKING_STATUSES
         and _is_finding_family_id(driver.finding_id) else status, driver)
        for status, driver in rungs
    ]
```

The `--warn-only` downgrade is the same shape, targeting `{POLICY_VIOLATION, INDETERMINATE}` → `WARN` instead of `{everything non-blocking}` → `BYPASSED`. Apply it AFTER the existing `apply_waivers`/`--bypass` block in `cli.py`, so a waiver still shows as `bypassed` distinctly and warn-only only mops up whatever is still blocking.

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `pixi run -e pyforge-warden --frozen pyforge-warden-test` -- expect all pass (1169 baseline + new tests; `--frozen` avoids an unrelated `bmad-ui` environment solve failure in this worktree)
- `pixi run -e pyforge-warden --frozen pytest src/shared/packages/pyforge-warden/tests/meta/test_verdict_sole_ownership.py -q` -- expect all pass (no sole-ownership violation from the new `waiver.py` function)
