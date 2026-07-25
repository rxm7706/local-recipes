---
title: 'Story 6.5: Two-mode policy integration (unconfigured visibility + flag-activated gating)'
type: 'feature'
created: '2026-07-24'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'c3c0e817f6fe2ae8ef1b5f41688427557a1c876b'
final_revision: '627624fca12bc60ea1e60b26f6d7c153e36fbf7a'
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** The license (6.2) and currency (6.3) axis producers are hard-capped at `Status.WARN`: `license_rung`/`currency_rung` ignore their `*_policy` tables and never escalate, and the `--allow/--deny-licenses` / `--max-lag/--require-lts/--fail-on-eol` flags only flip a transparency `gating` bool on the coverage row. So a configured policy does not actually block (FR33/FR35/FR37) — `gating:false` is honest but a configured axis is invisible-as-enforcement. The `warn_is_error` exit knob exists in `verdict.py` but has no CLI flag.

**Approach:** Story 6.5 solely owns the axes-3/4 escalation mapping. Make `config.license_policy`/`config.currency_policy` **gating-aware** (the single writer of the two-mode semantics per F7): when the axis's `gating` bool is false they map every verdict to `WARN`; when true they escalate (`denied`/`eol` → `policy-violation`, `unknown` → `indeterminate`). Thread those tables into `license_rung`/`currency_rung` in `DefaultPolicy.evaluate` exactly as `vuln_rung(finding, policy=…)` is already threaded — a policy-table change, no producer (finding-generation) change. Add currency's numeric over-lag check (`lag > --max-lag` → `policy-violation`) and its freshness precondition by **mirroring 6.4's KEV mechanism**: `CurrencyEngine` emits a whole-axis `indeterminate:currency-registry-{unavailable,stale}` provenance finding when the gate is active and the bundled LTS registry is absent/stale. Finally wire the `--warn-as-error` flag through config into `exit_code_for(warn_is_error=…)`.

## Boundaries & Constraints

**Always:**
- The escalation mapping is 6.5's SOLE ownership; producers (`license_findings`/`currency_findings`) stay byte-identical — the two-mode diff test runs the identical fixture set unconfigured vs configured and diffs only rungs/exit (AC2).
- `config.py` is the single writer of the per-axis `gating` bool AND of the gating-aware `*_policy` tables (F7); `DefaultPolicy`, the rungs, and the report only READ them. The escalation table lives on `EffectiveConfig.{license,currency}_policy`; the module-level `DEFAULT_{LICENSE,CURRENCY}_POLICY` stay the all-`WARN` fallback used when `policy is None` (unconfigured / the ceiling meta-test), mirroring `vuln.DEFAULT_VULN_SEVERITY_POLICY` vs `config.vuln_severity_policy`.
- Verdict discrimination: license reads `Finding.license.verdict` (`DENIED`/`UNKNOWN`); currency reads `Finding.currency.verdict` + `.lag` — `over-lag` ⟺ `CurrencyVerdict.SUPPORTED` with truthy `lag` (there is no `OVER_LAG` enum member), so `over-lag` escalation is the numeric `lag > max_lag` check, not a table key. Reason precedence `eol > over-lag > unknown` is already pinned in the producer's `_classify`; 6.5 does not re-derive it.
- Currency freshness precondition (NFR-S9): under an active currency gate, an absent/stale bundled LTS registry (report-level `currency_data is None` or `currency_data.max_age_ok is False`) forces a whole-axis `indeterminate` — never a pass — via an engine-emitted provenance finding (`severity=None`, `axis=currency`, no `CurrencyInfo`) that the rung maps to `indeterminate`. Gated on `currency_gating`, exactly as `_kev_enrichment` gates on `fail_on_kev`. Staleness is computed by `feeds.py`/`_registry_feed_provenance` (F5 — the axis never computes staleness itself); the engine only READS `max_age_ok`.
- The C0 bound is the invariant: escalation only ever moves a rung toward a stronger (non-`clean`) status; the shipped 1.2 `indeterminate` backstop is a placeholder these axes' defined mappings supersede, not a floor (architecture F4, 2026-07-16). `verdict.py` is untouched — 6.5 feeds rungs, never projects.
- `--warn-as-error` is a pure exit-projection knob: it sets `exit_code_for(warn_is_error=True)` so a `warn` STATUS exits non-zero; it never changes the composed status or any rung. Threads config → `assemble_report` → `exit_code_for`, orthogonal to the existing `--warn-only`.
- Standing cross-cutting gates hold: zero false-green on fixtures (C0), the ceiling meta-test stays green (default/unconfigured rung call returns `WARN`), deny-by-default socket harness (no new egress — all inputs are cached/bundled), twice-run byte-identical determinism (NFR-R3b).

**Block If:**
- The gating-aware policy tables cannot be expressed because a producer emits a verdict/`CurrencyInfo` shape incompatible with `denied`/`eol`/`over-lag`/`unknown` discrimination as documented here (would indicate a real 6.1/6.2/6.3 contract gap, not something to patch around).

**Never:**
- No schema widening (post-6.1 rule): do NOT add an `is_lts` field or a `runtime_python` report slot. `--require-lts` therefore activates the currency gate (unknown→indeterminate, eol→policy-violation apply) but adds NO non-LTS-specific block — the dropped `lts` boolean makes that unexpressible from emitted data; this is a carried limitation (see `deferred-work.md`), not this story's fix. The Python runtime's currency stays a `!python-runtime` finding, never a report field.
- No change to `license_findings`/`currency_findings` output, to `verdict.py`, to the verdict lattice/exit projection, or to any other axis's mapping (hygiene/vulnerability unchanged). No new network access. No producer-side escalation (escalation must not leak back into the producers — F2).
- No boolean-`eol` schema fix: dateless-EOL upstream shapes still surface as `currency:unknown` (→ `indeterminate` under an active gate), never invented as `eol` — schema-blocked, ledgered.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| License unconfigured | denied/unknown license finding, no `--allow/--deny-licenses` | each feeds a `warn` rung (driver names axis+finding); status `warn`, exit 0 | No error |
| License gated — denied | `--deny-licenses GPL-3.0-only`, a `denied` finding | rung `policy-violation`, exit 1; driver = that finding | No error |
| License gated — unknown | any license flag set, an `unknown` finding | rung `indeterminate`, exit 1 | No error |
| Currency unconfigured | eol/over-lag/unknown finding, no currency flag | each `warn`, exit 0; `currency.gating=false` | No error |
| Currency gated — eol | any currency flag set, an `eol` finding | `policy-violation`, exit 1 | No error |
| Currency gated — over-lag over threshold | `--max-lag 3`, over-lag finding `lag=5` | `policy-violation`, exit 1 | No error |
| Currency gated — over-lag under threshold | `--max-lag 3`, over-lag finding `lag=2` | `warn`, exit 0 (visible, not blocking) | No error |
| Currency gated, no `--max-lag` | `--fail-on-eol` only, an over-lag finding | `warn` (no threshold configured); eol/unknown still escalate | No error |
| Currency gated — unknown | any currency flag set, an `unknown` finding | `indeterminate`, exit 1 | No error |
| Currency gated — stale bundled registry | currency flag set, `currency_data.max_age_ok=False` | whole-axis `indeterminate:currency-registry-stale:*` finding + rung; status `indeterminate`, exit 1 — never a pass | No error |
| Currency gated — absent bundled registry | currency flag set, `currency_data is None` | whole-axis `indeterminate:currency-registry-unavailable:*`; `indeterminate`, exit 1 | No error |
| `--warn-as-error`, warn-only scan | unconfigured axis warn findings, `--warn-as-error` | status stays `warn`, exit 1 | No error |
| Two-mode diff | identical fixtures unconfigured vs configured | findings (ids/verdicts/tiers) identical; only rungs/exit + `coverage.gating` differ | No error |
| Ceiling meta-test | `license_rung(finding)` / `currency_rung(finding)` (no policy arg) | `Status.WARN`, `driver.axis`==axis, `driver.finding_id`==id — unchanged | No error |
| Currency rung on provenance finding | finding with `currency=None` (freshness finding) | `indeterminate` (never toward clean) | No error |

</intent-contract>

## Code Map

- `src/pyforge/warden/config.py` -- make `EffectiveConfig.license_policy`/`currency_policy` gating-aware (escalate when `license_gating`/`currency_gating`, else all-`WARN`); add `warn_as_error: bool = False` field + `cli_warn_as_error` in `ConfigLoader.load` (mirror `cli_fail_on_eol`). `max_lag`/gating properties already exist.
- `src/pyforge/warden/license.py` -- upgrade `license_rung(finding, *, policy=None)` to look up `finding.license.verdict` in `policy or DEFAULT_LICENSE_POLICY` (guard `finding.license is None → INDETERMINATE`). Producer/`license_findings` untouched.
- `src/pyforge/warden/currency.py` -- upgrade `currency_rung(finding, *, policy=None, max_lag=None)`: `finding.currency is None → INDETERMINATE`; `SUPPORTED` (over-lag) → `POLICY_VIOLATION` iff `max_lag is not None and lag > max_lag` else `WARN`; else `(policy or DEFAULT_CURRENCY_POLICY).get(verdict, INDETERMINATE)`. Add `currency_stale_finding(*, unavailable: bool)` factory (mirror `vuln.kev_stale_finding`): `indeterminate:currency-registry-{unavailable,stale}:lts-registry`, `axis=AXIS_CURRENCY`, `severity=None`. `currency_findings` untouched.
- `src/pyforge/warden/engines.py` -- `CurrencyEngine.__init__(self, *, gating: bool = False)`; in `run`, when `gating` and (`currency_data is None or not currency_data.max_age_ok`), append `currency_stale_finding(unavailable=currency_data is None)` to the result findings (mirror `OsvEngine`'s `_kev_enrichment` merge).
- `src/pyforge/warden/interfaces.py` -- in `DefaultPolicy.evaluate`, thread `license_rung(finding, policy=self._config.license_policy)` and `currency_rung(finding, policy=self._config.currency_policy, max_lag=self._config.max_lag)` (mirror the adjacent `vuln_rung(...)` call).
- `src/pyforge/warden/cli.py` -- construct `CurrencyEngine(gating=config.currency_gating)` (currently bare `factory()`); add `--warn-as-error` argparse flag → `cli_warn_as_error`; update `--max-lag` help (threshold is now enforced by the gate); thread `warn_as_error=config.warn_as_error` into `assemble_report(...)`.
- `src/pyforge/warden/report.py` -- add `warn_as_error: bool = False` param to `assemble_report`; pass `warn_is_error=warn_as_error` into the `exit_code_for(status, …)` call (report.py:391).
- `tests/unit/test_license.py`, `tests/unit/test_currency.py`, `tests/unit/test_config.py`, `tests/unit/test_interfaces_and_null_engine.py`, `tests/conformance/test_axis_producer_ceiling.py`, `tests/conformance/test_scan_harness.py` -- escalation + freshness + two-mode-diff + `--warn-as-error` coverage; verify the ceiling meta-test stays green.

(All paths above are relative to `src/shared/packages/pyforge-warden/`.)

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/warden/config.py` -- gating-aware `license_policy`/`currency_policy`; `warn_as_error` field + `cli_warn_as_error` loader param -- the single-writer two-mode tables + strict-shop knob
- [x] `src/pyforge/warden/license.py` -- `license_rung(finding, *, policy=None)` table lookup on `finding.license.verdict`; None-guard -- license escalation, ceiling-safe default
- [x] `src/pyforge/warden/currency.py` -- `currency_rung(finding, *, policy=None, max_lag=None)` (verdict table + over-lag numeric check + None-guard); `currency_stale_finding` factory -- currency escalation + freshness precondition finding
- [x] `src/pyforge/warden/engines.py` -- `CurrencyEngine(gating=…)`; emit `currency_stale_finding` when gated + registry absent/stale -- KEV-mirror freshness precondition (whole-axis indeterminate, incl. the zero-findings-stale case)
- [x] `src/pyforge/warden/interfaces.py` -- thread `license_policy`/`currency_policy`/`max_lag` into the two rung calls -- wires escalation through the existing seam (mirrors `vuln_rung`)
- [x] `src/pyforge/warden/cli.py` -- `CurrencyEngine(gating=config.currency_gating)`; `--warn-as-error` flag; `--max-lag` help update; thread `warn_as_error` -- gate activation + strict-shop exit
- [x] `src/pyforge/warden/report.py` -- `warn_as_error` param → `exit_code_for(warn_is_error=…)` -- projection knob wiring
- [x] `tests/unit/test_license.py` -- denied→policy-violation, unknown→indeterminate under a gating policy; warn under the default/None -- license escalation coverage
- [x] `tests/unit/test_currency.py` -- eol→policy-violation, unknown→indeterminate; over-lag→policy-violation iff `lag>max_lag` else warn; freshness finding→indeterminate; warn under default -- currency escalation + freshness coverage
- [x] `tests/unit/test_config.py` -- `license_policy`/`currency_policy` escalate iff the axis gates; `warn_as_error` parsing (CLI overrides TOML) -- single-writer + knob parsing
- [x] `tests/unit/test_interfaces_and_null_engine.py` -- `DefaultPolicy(EffectiveConfig(deny_licenses=…))` and `(fail_on_eol=True)` escalate end-to-end through `evaluate` -- config-threaded escalation
- [x] `tests/conformance/test_axis_producer_ceiling.py` -- confirm the parametrized ceiling still asserts `WARN` for the no-arg rung call (add a companion asserting a gating policy DOES escalate, proving the ceiling guards only the default) -- meta-test integrity
- [x] `tests/conformance/test_scan_harness.py` -- two-mode diff (same fixture unconfigured vs configured → identical findings, differing rungs/exit); `--warn-as-error` warn→exit 1; stale-registry-under-gate→indeterminate E2E (mirror `test_kev_feed_stale_*`) -- end-to-end proof of both modes

**Acceptance Criteria:**
- Given an unconfigured license/currency axis, when a component's verdict is `unknown`/`denied`/`eol`, then the policy feeds a `warn` rung whose driver names the axis+finding, status is `warn` (not `clean`), exit 0; and `--warn-as-error` makes the same run exit non-zero with status still `warn`.
- Given `--deny-licenses`/`--allow-licenses` set, when the identical license fixtures run, then `denied`→`policy-violation` and `unknown`→`indeterminate`, `license_findings()` output is unchanged from the unconfigured run, and only the rungs/exit differ.
- Given any of `--max-lag`/`--require-lts`/`--fail-on-eol` set, when the identical currency fixtures run, then `eol`→`policy-violation`, `unknown`→`indeterminate`, over-lag→`policy-violation` iff `lag>--max-lag`, `currency_findings()` output is unchanged, and only rungs/exit differ.
- Given an active currency gate and an absent or stale bundled LTS registry, when the scan runs, then a whole-axis `indeterminate:currency-registry-{unavailable,stale}` finding forces status `indeterminate` / exit 1 — never a pass — mirroring the KEV feed-absence rule; and with no currency flag set, a stale registry changes nothing (still warn).
- Given `tests/conformance/test_axis_producer_ceiling.py`, when it runs, then `license_rung(finding)`/`currency_rung(finding)` (no policy arg) still return `Status.WARN` for every fixture — the producer-never-exceeds-warn guard is intact.
- Given `--deterministic`, when the same fixtures run twice in either mode, then the report is byte-identical across both runs; and `verdict.py` and every non-license/currency axis are untouched.

## Design Notes

The escalation seam already exists and is proven for the vulnerability axis — copy it. In `DefaultPolicy.evaluate` the `AXIS_VULNERABILITY` branch calls `vuln_rung(finding, policy=self._config.vuln_severity_policy, fail_on_kev=self._config.fail_on_kev)`; the `AXIS_LICENSE`/`AXIS_CURRENCY` branches call the bare `license_rung(finding)`/`currency_rung(finding)`. 6.5 makes those two branches pass their policy tables, and makes the tables two-mode:

```python
# config.py — the single writer of the two-mode semantics (mirrors vuln_severity_policy)
@property
def currency_policy(self) -> dict[CurrencyVerdict, Status]:
    if self.currency_gating:
        return {CurrencyVerdict.EOL: Status.POLICY_VIOLATION,
                CurrencyVerdict.UNKNOWN: Status.INDETERMINATE}
    return {CurrencyVerdict.EOL: Status.WARN, CurrencyVerdict.UNKNOWN: Status.WARN}

# currency.py — rung defaults stay warn-capped (ceiling test), escalate only via the passed table
def currency_rung(finding, *, policy=None, max_lag=None):
    info = finding.currency
    if info is None:                      # provenance/freshness finding
        return (Status.INDETERMINATE, StatusDriver(axis=finding.axis, finding_id=finding.id))
    table = policy or DEFAULT_CURRENCY_POLICY
    if info.verdict is CurrencyVerdict.SUPPORTED:   # over-lag (lag truthy); clean-supported never mints a finding
        over = max_lag is not None and info.lag is not None and info.lag > max_lag
        status = Status.POLICY_VIOLATION if over else Status.WARN
    else:
        status = table.get(info.verdict, Status.INDETERMINATE)
    return (status, StatusDriver(axis=finding.axis, finding_id=finding.id))
```

The freshness precondition is 6.4's KEV pattern verbatim: `kev_stale_finding(unavailable=…)` (`vuln.py`) mints `indeterminate:kev-data-{unavailable,stale}:kev-feed` with `severity=None`; `OsvEngine._kev_enrichment` emits it only when `fail_on_kev`. Currency mirrors this — `currency_stale_finding` (subject a reserved feed name, `axis=AXIS_CURRENCY`), emitted by `CurrencyEngine` only when `gating` and the bundled registry (`currency_data`) is absent/stale — so even a scan that produced zero per-component currency findings (stale tier-1 but a clean tier-2) cannot pass under an active gate. `currency_rung` maps its `currency is None` shape to `indeterminate`, and `verdict.compose`'s lattice (`indeterminate > warn`) lets it win.

`--warn-as-error` is the strict-shop knob for mode 1: the `warn_is_error` param already lives on `verdict.exit_code_for` (tested) but no flag feeds it. Wire a `store_true` `--warn-as-error` → `EffectiveConfig.warn_as_error` → `assemble_report(warn_as_error=…)` → `exit_code_for(warn_is_error=…)`. It is orthogonal to `--warn-only` (which downgrades blocking rungs pre-compose); `--warn-as-error` only adjusts the post-compose exit projection of a `warn` status.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: full suite green, including the new license/currency escalation, freshness-precondition, two-mode-diff, and `--warn-as-error` coverage, with the ceiling meta-test still asserting `WARN`. (Canonical `--frozen` form per `deferred-work.md`'s worktree path-length note; unfrozen fails environmentally in bmad-loop worktrees, unrelated to correctness.)

## Spec Change Log

(No bad_spec loopback occurred during this story's review pass — empty.)

## Review Triage Log

### 2026-07-24 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 2 (medium 1, low 1)
- defer: 1 (medium 1)
- reject: 1 (low 1)
- addressed_findings:
  - `[medium]` `[patch]` Two producer-invariance comparison tests (`test_currency_gate_flags_never_change_the_findings_themselves`, `test_currency_two_mode_diff_escalates_status_and_exit`) compared currency findings against the *live* bundled LTS registry, so once it ages past its 180-day max-age (~2027-01-02) the gate-only `indeterminate:currency-registry-stale` provenance finding would appear under the gate and break the equality assertions on a wall-clock date with no code change. Fixed by excluding the gate-only `indeterminate:currency-registry-*` provenance id from the producer-invariance comparison (`_currency_findings`/`_currency_block` now keep only the `currency:` id family) — faithful (the provenance finding was never producer output) and time-robust, matching 6.3's time-coupling precedent.
  - `[low]` `[patch]` `license_rung`/`currency_rung` used `policy or DEFAULT_*_POLICY`, so an EMPTY (non-`None`) gating table would short-circuit back to the all-`WARN` module default instead of failing closed via the `.get(..., INDETERMINATE)` fallback (a latent false-green direction + a code/docstring mismatch, though unreachable through the shipped `config.*_policy` which always returns a non-empty table). Fixed to `policy if policy is not None else DEFAULT_*_POLICY` in both rungs; added an empty-dict fail-closed regression test per axis.
  - `[medium]` `[defer]` The bundled `data/lts-registry.yaml` has a fixed `updated:` date + 180-day max-age and no runtime refresh path; Story 6.5 makes it gate-consequential (a stale bundled registry self-degrades every gated scan to `indeterminate` — fail-closed, but a fleet-wide false-RED unless re-stamped). Pre-existing 6.3 property; logged to `deferred-work.md` for a release-time re-stamp / cross-axis staleness-defaults pass.
  - `[low]` `[reject]` `--warn-only` + `--warn-as-error` composes to exit 1 (`--warn-only` downgrades blocking rungs to `warn` pre-compose; `--warn-as-error` then projects `warn → exit 1`). This is the coherent composition of two orthogonal, documented knobs in the *safe* (false-RED) direction; "which wins" is a product decision, not a defect — noted as a residual risk, not patched.

All 2 patch fixes applied; full suite re-verified green (1649 passed, net +2 regression tests) after patching.

### 2026-07-24 — Follow-up review pass (bmad-dev-auto, fresh Blind Hunter + Edge Case Hunter)

- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 0, medium 2, low 7)
- defer: 2: (high 0, medium 2, low 0)
- reject: 1: (high 0, medium 0, low 1)
- addressed_findings:
  - `[medium]` `[patch]` `test_currency_engine_gated_fresh_registry_emits_no_stale_finding` trusted the LIVE bundled registry's fixed `updated:` date with real wall-clock `now`, so it would flip red ~2027-01-02 (180-day max-age) with no code change — the one time-coupling the prior pass's two-mode robustness patch missed. Fixed by monkeypatching a yesterday-dated registry (always fresh, never future-dated).
  - `[medium]` `[patch]` The `max_lag=self._config.max_lag` threading through `DefaultPolicy.evaluate` was completely unpinned — no test exercised over-lag escalation through `evaluate` or the CLI (unit rung tests pass `max_lag` directly), so dropping the threading would have left the whole suite green while `--max-lag` silently stopped enforcing (a false-green direction). Fixed with two `DefaultPolicy(EffectiveConfig(max_lag=…))` over/under-threshold tests plus a `--max-lag` two-mode E2E harness test (over threshold → policy-violation/exit 1, at threshold → warn/exit 0, identical producer findings; wall-clock-robust via a fresh empty monkeypatched registry).
  - `[low]` `[patch]` `currency_rung` failed OPEN for a `SUPPORTED`-verdict finding with `lag=None` under an active `max_lag` (un-evaluable threshold → warn), opposite to every other unrepresentable shape's fail-closed degrade. Unreachable from the shipped producer (models.py pins non-null lag on `currency:over-lag` ids) but reachable via the open `indeterminate:` id family from a third-party engine. Fixed: active-threshold + no-lag now fails closed to `indeterminate`; grammar-legal regression test added; docstrings updated.
  - `[low]` `[patch]` The `--warn-only` + `--warn-as-error` composition (exit 1) was unpinned by any test and documented only one-way. Pinned with an E2E test (RECIPE_COMMON: `--warn-only` alone exits 0; both knobs → status warn, exit 1) and a `--warn-only` help cross-reference — this PINS the prior pass's product-decision composition, it does not change it.
  - `[low]` `[patch]` `currency.py`'s module docstring overclaimed "a producer's rung never exceeds warn unless a gating policy is passed" — false for the `policy=None, max_lag=N` path. Corrected both the module and rung docstrings to name the numeric threshold as the one no-policy escalation path.
  - `[low]` `[patch]` `--require-lts` help was a garden-path double negative ("adds no non-LTS-specific block"). Reworded plainly: activates the generic gate, performs no LTS-specific enforcement (blocking on a non-LTS resolution is unexpressible — the documented carried limitation). The finding's per-flag-E2E sub-suggestion was declined as compositionally covered (flag→gating and gating→escalation are each tested).
  - `[low]` `[patch]` The currency ceiling companion asserted only `is not WARN` where its license sibling asserts exact statuses — a gated `eol`→`indeterminate` regression (wrong exit-adjacent semantics) would have passed. Added the exact-status half (eol/over-lag → policy-violation, unknown → indeterminate).
  - `[low]` `[patch]` The producer-invariance findings filter (the `currency:` id-family rule) was copy-pasted as a nested helper duplicating module-level `_currency_block`, comment included. Deduplicated: both two-mode tests now share `_currency_block`.
  - `[low]` `[patch]` `test_currency_engine_defaults_to_gating_off` peeked at the private `_gating` attribute (breaks on rename; proves nothing if `run` stops honoring it). Converted to a behavioral proof: a default-constructed engine over a stale registry emits no provenance finding.

Deferred (2, appended to `deferred-work.md` as NEW entries): the warn-as-error exit projection leaves no trace in report/render/stderr (both hunters independently; schema-widening barred, needs an exit-code-provenance design decision); `deps_assessed == deps_total` coverage reported for an axis simultaneously declared untrustworthy under a stale-feed gate (cross-axis — the 6.4 KEV mirror shares the shape by contract). Rejected (1): a runtime CLEAN-clamp on handed policy tables — requires a contract-violating caller, and the shipped vuln axis shares the read-verbatim shape by precedent; the single-writer rule plus tests guard it.

All 9 patch fixes applied; full suite re-verified green (1654 passed, net +5 tests) after patching. No correctness defect was found in the shipped escalation logic itself — the two-mode tables, threading, freshness precondition, tri-state precedence, and exit projection all held under both fresh adversarial passes.

## Auto Run Result

**Run:** 2026-07-24, bmad-dev-auto follow-up review pass (spec supplied at `status: done` → fresh step-04 review; no implementation phase). Baseline `c3c0e817f6` → final `627624fca12bc60ea1e60b26f6d7c153e36fbf7a`.

**Summary:** Two fresh adversarial reviewers (Blind Hunter, Edge Case Hunter) re-reviewed the full 6.5 diff (13 files, +1233/−163). They confirmed the shipped escalation logic correct and surfaced 12 deduplicated findings — triaged 9 patch / 2 defer / 1 reject, 0 intent_gap, 0 bad_spec. All 9 patches applied and committed.

**Files changed this pass** (all under `src/shared/packages/pyforge-warden/`):
- `src/pyforge/warden/currency.py` — fail-closed `indeterminate` for `SUPPORTED`+`lag=None` under an active `max_lag` (previously fail-open warn; unreachable from the shipped producer); module/rung docstrings corrected (the no-policy `max_lag` path CAN escalate).
- `src/pyforge/warden/cli.py` — `--require-lts` help reworded (double negative removed); `--warn-only` help now cross-references the `--warn-as-error` composition.
- `tests/unit/test_currency.py` — fresh-registry engine test made wall-clock-robust (yesterday-dated monkeypatched registry, was a ~2027-01-02 time-bomb); default-gating test made behavioral (was a private-attribute peek); new fail-closed no-lag rung regression test.
- `tests/unit/test_interfaces_and_null_engine.py` — two new tests pinning the `max_lag` threading through `DefaultPolicy.evaluate` (over/under threshold).
- `tests/conformance/test_axis_producer_ceiling.py` — currency escalation companion now asserts exact statuses (was only `is not WARN`).
- `tests/conformance/test_scan_harness.py` — new `--max-lag` two-mode E2E test (enforces the numeric threshold end-to-end, wall-clock-robust); new `--warn-only`+`--warn-as-error` composition pin (exit 1); duplicated producer-invariance filter deduplicated onto `_currency_block`.

**Review findings breakdown:** 9 patched (2 medium: test time-bomb, unpinned `--max-lag` threading; 7 low), 2 deferred as NEW `deferred-work.md` entries (warn-as-error leaves no trace in report/render — both hunters independently; coverage reports 100% assessed on an axis declared untrustworthy under a stale-feed gate — cross-axis KEV-mirror shape), 1 rejected (runtime CLEAN-clamp on handed tables — contract-violating-caller hypothetical, vuln-axis precedent). Existing ledger entries untouched per orchestrator instruction.

**Follow-up review recommendation:** false — this pass's changes are test hardening, docstring/help wording, and one unreachable-path fail-closed guard; no reachable behavior, API, or schema change.

**Verification:** `pixi run --frozen -e pyforge-warden pyforge-warden-test` → 1654 passed (was 1649; net +5), 0 failed, after all patches.

**Residual risks:** the two deferred items above; the `--warn-only`+`--warn-as-error` → exit 1 composition remains the pinned product decision (now regression-guarded); the bundled LTS registry re-stamp concern from the prior pass's defer stands (operational, not code).

