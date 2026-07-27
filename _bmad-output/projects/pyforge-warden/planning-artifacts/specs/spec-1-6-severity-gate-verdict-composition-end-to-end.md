---
title: 'Story 1.6: Severity gate + verdict composition end-to-end'
type: 'feature'
created: '2026-07-16'
status: shipped
updated: '2026-07-27 (AUD-WARDEN-030 status sync)'
baseline_revision: 'ce2ed97bc44fcd90d553077f6207fb4f50a5c5c7'
final_revision: 'b2a032c7dc53063aa8351617d4b60697babb4a25'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/implementation-artifacts/epic-1-context.md'
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** `DefaultPolicy.evaluate` routes every non-hygiene-axis engine finding through a conservative "false-green backstop" (`Status.INDETERMINATE`, unconditionally) — the 1.2 placeholder documented in `interfaces.py` as pending each axis's real severity mapping. A `vuln:` finding from `OsvEngine` (Story 1.5) already carries a populated `Finding.severity` (tier + raw CVSS), but nothing reads it: a CRITICAL CVE and a LOW one compose identically today, and neither can ever reach `policy-violation` — the gate cannot fail a build on real vulnerability severity.

**Approach:** Add a `vuln_rung` (mirrors `hygiene.hygiene_rung`) in `vuln.py`, keyed off `Finding.severity.tier` via a hardcoded `DEFAULT_VULN_SEVERITY_POLICY` table: `CRITICAL → policy-violation`, `HIGH/MEDIUM/LOW/NONE → warn`, unmapped/absent severity (incl. `UNKNOWN`) → `indeterminate` (stays at the backstop level — an unassessable severity is never treated as safely non-blocking). Wire it into `DefaultPolicy.evaluate` as the vulnerability-axis sibling of the existing hygiene branch — this correctly covers BOTH real `vuln:` findings (severity set) and the axis's own `indeterminate:` withhold findings (severity `None`, so they still fall through to `indeterminate`) with one function, exactly as `hygiene_rung` already covers both `hygiene:` and stray `indeterminate:` ids on that axis.

## Boundaries & Constraints

**Always:** `vuln_rung` is pure composition (no I/O) and lives in `vuln.py`, never in `verdict.py` (sole-ownership guard) or `interfaces.py` directly (mirrors `hygiene_rung`'s placement, lazy-imported inside `evaluate()` to break the `vuln.py`→`interfaces._sanitize_id_segment` cycle, same technique already used for `hygiene_rung`). The mapping may only ever tighten toward `policy-violation` or hold at `indeterminate` — never map a finding straight to `clean` (C0c: a finding-carrying report must never compose clean). DEP001–005 stay exactly as 1.3 shipped them (all `warn`; DEP001's block-on-high-confidence activation is Story 2.1 scope) — this story makes zero changes to `hygiene.py` or `DEFAULT_HYGIENE_POLICY`. No new CLI flag, config table, or override path (`--fail-on`/`--warn-is-error`/`ConfigLoader` are Epic 3 scope) — the policy is a hardcoded module-level dict exactly like `DEFAULT_HYGIENE_POLICY`.

**Never:** Touch `verdict.py`'s lattice, ordering, or exit projection. Touch KEV/EPSS gating (Epic 6, unpopulated in v1). Add configurability. Change `DEFAULT_HYGIENE_POLICY`'s DEP001 warn default (2.1's job).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Critical CVE | `vuln:` finding, `severity.tier == CRITICAL` | Rung `(policy-violation, driver)`; composed exit 1 | No error |
| High/Medium/Low/None severity | `vuln:` finding, tier in `{HIGH,MEDIUM,LOW,NONE}` | Rung `(warn, driver)` | No error |
| Unknown/unmapped severity | `vuln:` finding, `tier == UNKNOWN` (or a future tier) | Rung `(indeterminate, driver)` — never silently downgraded | No error |
| Withheld / unsafe-identity finding | `indeterminate:*` finding on the vulnerability axis, `severity is None` | Rung `(indeterminate, driver)` — unchanged from today | No error |
| Indeterminate rides alongside a live warn | Inventory yields both a real hygiene `warn` rung and a real vulnerability-axis `indeterminate` rung in one scan | Composed status `indeterminate`, exit 1 (indeterminate outranks warn) | No error |
| Fully clean scan | No findings, all components `cve_match_level=EXACT`, hygiene-covered | Composed status `clean`, exit 0 | No error |

</intent-contract>

## Code Map

- `src/pyforge/warden/vuln.py` -- MODIFY: add `DEFAULT_VULN_SEVERITY_POLICY: dict[SeverityTier, Status]` (`CRITICAL→POLICY_VIOLATION`, `HIGH/MEDIUM/LOW/NONE→WARN`; `UNKNOWN` deliberately absent, mirroring `DEFAULT_HYGIENE_POLICY`'s unknown-code-degrades convention), `status_for_severity_tier(tier) -> Status`, and `vuln_rung(finding: Finding) -> tuple[Status, StatusDriver]` (reads `finding.severity.tier`; `None` severity → `Status.INDETERMINATE`).
- `src/pyforge/warden/interfaces.py` -- MODIFY: `DefaultPolicy.evaluate`'s per-finding loop gains an `elif finding.axis == AXIS_VULNERABILITY:` branch calling a lazily-imported `vuln_rung(finding)`, symmetric with the existing `AXIS_HYGIENE` → `hygiene_rung` branch; the `else` backstop remains only for any future/unrecognized axis. Update the module + `DefaultPolicy` docstrings (currently say "Story 1.3/1.6 scope by plan" / "Story 2.4 for vulnerability") to reflect that both v1 axes now have real mappings.
- `tests/unit/test_vuln.py` -- MODIFY: add unit tests for `DEFAULT_VULN_SEVERITY_POLICY`, `status_for_severity_tier`, and `vuln_rung` (parametrized over all 6 `SeverityTier` members + a `severity=None` case), mirroring `test_hygiene.py`'s coverage of `hygiene_rung`.
- `tests/unit/test_interfaces_and_null_engine.py` -- MODIFY: add `DefaultPolicy`-level tests proving a `vuln:` CRITICAL finding feeds `policy-violation`, non-critical tiers feed `warn`, and an unknown-tier/severity-less vuln-axis finding still feeds `indeterminate` (the backstop preserved for that case).
- `tests/fixtures/projects/vuln_critical/pyproject.toml` + `pkg/__init__.py` -- NEW: pins `pdos-vuln-fixture==1.0.0` (the Story 1.4/1.5 fixture-DB advisory `PDOS-FIXTURE-0001`, CVSS CRITICAL) so a real `cli.main()` scan produces a genuine `policy-violation` end-to-end (AC1).
- `tests/fixtures/projects/warn_and_indeterminate/pyproject.toml` + `pkg/__init__.py` -- NEW: `requests==2.31.0` declared-but-unused (real DEP002 `warn`) + `leftpad` with no version pin (real `indeterminate:no-version` withhold) in one project, proving `indeterminate` outranks a live `warn` end-to-end (AC2).
- `tests/conformance/test_scan_harness.py` -- MODIFY: add `test_critical_vuln_fixture_composes_policy_violation` (AC1) and `test_indeterminate_outranks_a_live_warn_end_to_end` (AC2), both driving `cli.main()` against the two new fixtures.

## Tasks & Acceptance

**Execution:**
- [x] `vuln.py` -- add `DEFAULT_VULN_SEVERITY_POLICY` + `status_for_severity_tier` + `vuln_rung` -- the severity→rung mapping AC1 requires.
- [x] `interfaces.py` -- wire `vuln_rung` into `DefaultPolicy.evaluate` as the vulnerability-axis sibling of `hygiene_rung`; refresh the stale "Story 1.6 scope by plan" docstrings -- closes the gate.
- [x] `tests/unit/test_vuln.py` -- unit-cover the new table/function over all 6 `SeverityTier` members + `severity=None`.
- [x] `tests/unit/test_interfaces_and_null_engine.py` -- `DefaultPolicy`-level coverage of critical/non-critical/unknown-severity vuln findings.
- [x] `tests/fixtures/projects/vuln_critical/` + `tests/fixtures/projects/warn_and_indeterminate/` -- new fixtures for the two end-to-end conformance tests.
- [x] `tests/conformance/test_scan_harness.py` -- the two new end-to-end tests (AC1, AC2).

**Acceptance Criteria** *(from `epics.md`, story 1.6):*
- Given the `Policy` interface with a hardcoded-sane default, when a critical CVE is present, then the vuln axis emits `policy-violation` and the verdict projects exit 1. (DEP001 blocking on high-confidence mapping is already satisfied by 1.3's shipped `DEFAULT_HYGIENE_POLICY` + documented as 2.1-gated — no change needed here.)
- Given a synthetic/real `indeterminate`-composing scan, when the verdict composes alongside a live `warn` rung, then `indeterminate` outranks `warn`/`clean` and projects non-zero. Given clean hygiene + no vulns, then status is `clean`, exit 0 (already proven by the existing `clean` fixture; re-confirmed unchanged by this story's test run). No module outside `verdict.py` computes the projection.

## Review Triage Log

### 2026-07-16 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8 (medium 4, low 4)
- defer: 2 (low 2)
- reject: 2
- addressed_findings:
  - `medium` `patch` The false-green backstop `else` branch in `DefaultPolicy.evaluate` (now reachable only by a hypothetical future axis, since both v1 axes have real mappings) had zero test coverage anywhere in the suite — a regression there would go undetected. Fixed: added `test_hypothetical_future_axis_still_hits_the_backstop` to `test_interfaces_and_null_engine.py`, constructing a `Finding` with a synthetic third axis (`"license"`) and asserting it still lands on `Status.INDETERMINATE`.
  - `medium` `patch` `DEFAULT_VULN_SEVERITY_POLICY`'s golden-equality unit test pinned today's literal dict via `==` but never structurally asserted the C0c "never maps to clean" invariant — a future edit mapping a tier to `clean` would just need the literal updated to stay green. Fixed: added `test_default_vuln_severity_policy_never_maps_to_clean` (`assert Status.CLEAN not in DEFAULT_VULN_SEVERITY_POLICY.values()`) to `test_vuln.py`.
  - `medium` `patch` No conformance test exercised a real (non-critical-severity) osv-scanner match end to end — HIGH/MEDIUM/LOW/NONE→`warn` was proven only via hand-built `Finding` objects in unit tests, never through the real `osv-scanner` subprocess → `parse_osv_output` → `_cvss_score_to_tier` → `vuln_rung` chain the way AC1's critical case was. This is a genuine new behavioral boundary (a real detected vulnerability can now exit 0, where the pre-1.6 backstop always exited 1) left unverified end-to-end. Fixed: added a new seeded HIGH-severity OSV advisory (`tests/fixtures/osv-db/pypi/PDOS-FIXTURE-0002.json`, CVSS vector empirically verified against the real osv-scanner binary to compute base score 8.8), a new `vuln_high` fixture project, and `test_high_severity_vuln_fixture_composes_warn` in `test_scan_harness.py` (also confirmed the new record doesn't collide with or break any of the other 572 pre-existing tests sharing the same ambient DB).
  - `medium` `patch` Determinism (NFR-I3, "twice-run byte-identical stdout") — a standard this module's own docstring states every fixture is held to — was never checked for the two new Story 1.6 fixtures (`vuln_critical`, `warn_and_indeterminate`). Fixed: added `test_severity_gate_fixture_twice_run_is_byte_identical`, parametrized over `vuln_critical`, `vuln_high`, and `warn_and_indeterminate`.
  - `low` `patch` A comment on `DEFAULT_VULN_SEVERITY_POLICY` claimed `UNKNOWN` is absent from the table "so the sole-ownership rung-ordering guard does not fire on this literal" — factually wrong (the guard only inspects dict-literal keys typed as `Status` members; this table's keys are `SeverityTier`, so the guard would never fire regardless of `UNKNOWN`'s presence). The precedent comment it was adapted from (`hygiene.py`) states the correct reason. Fixed: reworded to "Keys are SeverityTier members (NOT Status tokens), so the sole-ownership rung-ordering guard does not fire on this literal," matching `hygiene.py`'s correct phrasing.
  - `low` `patch` `status_for_severity_tier`'s docstring described the fallback as covering "`UNKNOWN`, or any future tier this table has not been updated for," implying `SeverityTier` is a growable enum — but `models.py`'s own module docstring states only `CveMatchLevel` and `WithholdReason` may widen additively; `SeverityTier` is closed. Fixed: reworded to name only `UNKNOWN` (the sole absent, real tier) without implying future growth.
  - `low` `patch` `test_critical_vuln_fixture_composes_policy_violation` never asserted the fixture's own documented side effect (`pdos-vuln-fixture` also gets flagged `DEP002` by deptry) — the outranking property the fixture comment claims was never directly verified, only the absence of a status regression. Fixed: added `_one_hygiene_finding(document, "hygiene:DEP002:pdos-vuln-fixture")`.
  - `low` `patch` `test_indeterminate_outranks_a_live_warn_end_to_end` under-asserted its own two-dependency fixture: `leftpad`'s own `hygiene:DEP002:leftpad` finding (independent of its vulnerability-axis withhold) and the total finding count were never checked. Fixed: added the `leftpad` DEP002 assertion and `assert len(document["findings"]) == 3`.
  - `reject`: `SeverityTier.NONE` collapsing into the same `warn` rung as HIGH/MEDIUM/LOW (Blind Hunter) — by design, already reasoned through in this spec's own Design Notes (matches hygiene's flat "everything non-blocking warns" ceiling; FR18 blocks on critical only); not a defect. A generic "no finding-count assertions" complaint on the two original conformance tests (Blind Hunter) — superseded by the specific concurrent-finding assertions added above, which already pin every finding the fixtures produce; a redundant bare count would add no real signal beyond those.
  - `defer`: `hygiene.py`'s analogous `DEFAULT_HYGIENE_POLICY` golden-equality test lacks the same structural "never clean" guard just added to `DEFAULT_VULN_SEVERITY_POLICY`'s — pre-existing since 1.3, out of this story's scope (`hygiene.py`/`test_hygiene.py` untouched by design). `DEFAULT_HYGIENE_POLICY` and `DEFAULT_VULN_SEVERITY_POLICY` are both unprotected mutable module-level dicts (no immutability guard) — same latent, low-risk pattern in both tables. Both appended to `deferred-work.md`.

## Design Notes

**Why `AXIS_VULNERABILITY` (not an id-prefix check like `finding.id.startswith("vuln:")`) is the branch discriminator:** every vulnerability-axis `indeterminate:` finding (withheld, unsafe-identity, offline-db-unavailable) carries `severity=None`, so routing it through `vuln_rung` yields `Status.INDETERMINATE` anyway — identical to today's backstop result, with zero special-casing. This mirrors `hygiene_rung`, which already handles a stray `indeterminate:` id on the hygiene axis the same way (unrecognized code segment → indeterminate). One function per axis, no id-family branching inside `DefaultPolicy`.

**Why HIGH/MEDIUM/LOW/NONE → `warn`, not `indeterminate`:** FR18's default gate is "block on critical CVEs" only; architecture.md's F4 ("tighten-only, redefined") states the 1.2 backstop is a placeholder superseded per-axis by the real mapping, with the sole invariant being "never toward clean" — `warn` satisfies that (it is not `clean`) and matches the precedent 1.3 already set by mapping ALL of DEP001–005 to `warn`. **Why `UNKNOWN` → `indeterminate` instead:** an out-of-range/unparseable CVSS score is "malformed data, not evidence of a low-severity vulnerability" (vuln.py's own `_cvss_score_to_tier` docstring) — treating it as safely `warn` would silently downgrade an unassessable finding, which the project's C0 "never false-green" principle forbids. This is the same shape as `status_for_code`'s unknown-DEP-code fallback.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: all prior suites unchanged + new `vuln_rung`/`DefaultPolicy`/conformance tests green; sole-ownership / no-execution / socket-deny meta-guards stay green.
- Manual: `git diff --stat` shows zero changes to `verdict.py`, `hygiene.py`, `models.py`, `report.py`, `cli.py`, `pixi.toml`/`pixi.lock`/`pyproject.toml`.

## Auto Run Result

**Summary of implemented change:** Added `DEFAULT_VULN_SEVERITY_POLICY` + `status_for_severity_tier` + `vuln_rung` (`vuln.py`), wired into `DefaultPolicy.evaluate` (`interfaces.py`) as the vulnerability-axis sibling of `hygiene_rung`. A real `vuln:` finding's `severity.tier` now composes `policy-violation` (CRITICAL, exit 1) or `warn` (HIGH/MEDIUM/LOW/NONE, exit 0 by default); an unassessable severity (`UNKNOWN`, or any `indeterminate:` withhold finding on the vulnerability axis, which carries no severity) still composes `indeterminate` — the pre-1.6 backstop's result, unchanged for that case. The backstop `else` branch in `DefaultPolicy.evaluate` now covers only a hypothetical future axis. Closes the pre-existing gap where a CRITICAL CVE and a LOW one composed identically (both `indeterminate`) and neither could ever block a build via `policy-violation`.

**Files changed:**
- `src/pyforge/warden/vuln.py` — `DEFAULT_VULN_SEVERITY_POLICY`, `status_for_severity_tier`, `vuln_rung` (new); imports `Status`/`StatusDriver`.
- `src/pyforge/warden/interfaces.py` — `DefaultPolicy.evaluate`'s per-finding loop gains an `AXIS_VULNERABILITY` branch calling `vuln_rung` (lazily imported, mirroring the existing `hygiene_rung` import); refreshed stale "Story 1.3/1.6 scope by plan" docstring language in both the module and `DefaultPolicy` docstrings.
- `tests/unit/test_vuln.py` — unit coverage for the new table/functions over all 6 `SeverityTier` members + `severity=None`, plus a structural `Status.CLEAN not in DEFAULT_VULN_SEVERITY_POLICY.values()` guard (review patch).
- `tests/unit/test_interfaces_and_null_engine.py` — `DefaultPolicy`-level coverage: critical→policy-violation, non-critical→warn, unknown-tier/severity-less→indeterminate, plus a hypothetical-future-axis test proving the narrowed backstop still fires (review patch).
- `tests/fixtures/projects/vuln_critical/`, `tests/fixtures/projects/vuln_high/` (new), `tests/fixtures/projects/warn_and_indeterminate/` (new) — end-to-end fixtures for AC1 (critical CVE), the review-added non-critical-severity case, and AC2 (indeterminate outranks a live warn) respectively.
- `tests/fixtures/osv-db/pypi/PDOS-FIXTURE-0002.json` (new, review patch) — a HIGH-severity seeded advisory (CVSS vector empirically verified against the real `osv-scanner` binary to compute base score 8.8) added to the shared ambient offline DB every test consumes; confirmed to collide with no existing fixture's dependency name/version.
- `tests/conformance/test_scan_harness.py` — `test_critical_vuln_fixture_composes_policy_violation` (AC1), `test_high_severity_vuln_fixture_composes_warn` (review patch), `test_indeterminate_outranks_a_live_warn_end_to_end` (AC2), `test_severity_gate_fixture_twice_run_is_byte_identical` (review patch, determinism parity with sibling fixtures).

**Review findings breakdown:** 0 intent_gap, 0 bad_spec, 8 patch (4 medium, 4 low — all applied), 2 defer (appended to `deferred-work.md`: `hygiene.py`'s analogous golden-test gap, and both default-policy tables' unprotected mutability), 2 reject (a by-design severity-collapsing choice already justified in this spec's Design Notes, and a generic finding-count complaint superseded by the specific assertions the patches added).

**Follow-up review recommendation:** `false` — all 8 patches are test/fixture additions or comment/docstring wording fixes; zero changes to `vuln_rung`'s or `DefaultPolicy.evaluate`'s actual logic beyond the original implementation, zero API/behavior changes introduced by the patch round itself, and the one shared-test-asset addition (the new OSV record) was verified against the full 573-test suite before and after.

**Verification performed:** `pixi run --frozen -e pyforge-warden pyforge-warden-test` — 573 passed, 0 failed (567 at implementation + 6 from the review-patch round: 1 backstop test, 1 structural clean-guard test, 1 high-severity conformance test, 3 parametrized determinism tests). `mypy` (`pixi run --frozen -e local-recipes mypy src/shared/packages/pyforge-warden/src/pyforge/warden`) — 2 errors, both pre-existing/unrelated (confirmed identical to the baseline recorded in story 1.5's own spec). `ruff check` — 2 pre-existing issues, same baseline, zero new. `git diff --stat` against baseline — zero changes to `verdict.py`, `hygiene.py`, `models.py`, `report.py`, `cli.py`, `pixi.toml`, `pixi.lock`, `pyproject.toml`. Empirically verified the new HIGH-severity CVSS vector's computed base score (8.8) against the real `osv-scanner` binary before writing the fixture, rather than relying on a memorized/assumed value.

**Residual risks:** The two deferred items in `deferred-work.md` (hygiene's golden test missing the same structural clean-guard; both default-policy tables being unprotected mutable module dicts) are both pre-existing-pattern, low-probability-of-exploitation observations, not regressions from this story. `DEFAULT_VULN_SEVERITY_POLICY` (like `DEFAULT_HYGIENE_POLICY`) remains hardcoded/non-overridable by design — Story 3.1's `ConfigLoader` is the intended lift point.
