---
title: "16.9: A non-Python repo's license and currency rows report what ran"
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
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-4-non-python-lockfiles-scan-through-osv-scanner-s-own-parsers.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/report.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/native_lockfiles.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/interfaces.py
  - src/shared/packages/pyforge-warden/tests/unit/test_non_python_lockfiles.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-26 says a non-Python repo's other axes are "honestly not-applicable", but the code says otherwise,
and the report's rows disagree with the findings beside them (line numbers at `03a7aff5d9`):
- For an npm, Go or Cargo component, the license and currency engines resolve nothing and emit `license:unknown` and
  `currency:unknown` findings, which warn when the axis is ungated and route to `indeterminate` when it is gated (the
  audit cites `src/shared/packages/pyforge-warden/src/pyforge/warden/license.py` about :661-665 and :712, and `src/shared/packages/pyforge-warden/src/pyforge/warden/interfaces.py` about :375-400). There is no false
  green: an unknown never composes to clean.
- The same report's license and currency coverage rows read `deps_total=0` (`src/shared/packages/pyforge-warden/src/pyforge/warden/report.py` about :385-398, through
  `inventory_count_for_axis`, `src/shared/packages/pyforge-warden/src/pyforge/warden/native_lockfiles.py` about :353-358), and the comment at `interfaces.py` about
  :454-457 calls those axes not-applicable.
- Open probe (the refute lens's observation): `native_lockfiles.py` (about :248-259) runs osv-scanner without
  `--all-packages`, so a clean npm lock may inventory 0 components and hit the empty-extraction `indeterminate`
  (`src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` about :1482).

**Operator ruling 2026-11-01** (the `spec-pyforge-warden` memlog's decision of that date): state today's
unknown-then-warn behaviour, and fix the `deps_total=0` rows.

EGM audit 2026-11-01, cluster WAR-CL-5; findings WAR-M-D1 (contested; settled in cluster: severity Major,
false-green refuted) and WAR-M-C2, accepted by the operator on 2026-11-01; residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:**
- `report.py` and `inventory_count_for_axis` stop reporting `deps_total=0` on an axis that carries findings for
  native-lockfile components: the license and currency rows count the components those axes judged.
- The `interfaces.py` comment says what the code does.
- Probe the clean-lock case; if it inventories 0 components and hits the empty-extraction `indeterminate`, add
  `--all-packages` to the osv-scanner argv under the tested osv range.
- `src/shared/packages/pyforge-warden/tests/unit/test_non_python_lockfiles.py` pins the composed status of a clean-lock and a vulnerable-lock npm fixture.
- CAP-26 drops "the other axes honestly not-applicable" and states the unknown-then-warn behaviour through the
  `spec-pyforge-warden` `bmad-spec` re-derive (with WAR-CL-3's), never a hand edit.

Ledger key: `16-9-a-non-python-repo-s-license-and-currency-rows-report-what-ran`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-warden` CAP-26 (FR-43) — the non-Python lockfile ecosystems' reports. A `fix`, so no new CAP;
  `spec-feature-flag-governance` Q1: a `fix` needs no flag (`pyforge.warden.non_python_ecosystems` keeps gating
  discovery).

## Acceptance Criteria

- **AC1 — Rows count what ran.** Given an npm fixture whose `package-lock.json` holds N components and the npm offline
  database, When `warden scan` runs with `pyforge.warden.non_python_ecosystems` on, Then the license and currency
  coverage rows report the components those axes judged (N, or the count that drew findings), never `deps_total=0`
  beside `license:unknown` or `currency:unknown` findings.
- **AC2 — Composed statuses are pinned.** Given the clean-lock fixture and the vulnerable-lock fixture, When each is
  scanned ungated and gated on license and currency, Then the test asserts each composed status: ungated, the unknowns
  warn; gated, they route to `indeterminate`; the vulnerable lock reports its `vuln:` finding; neither is `clean` with
  an unknown present.
- **AC3 — The clean lock is inventoried.** Given the clean-lock fixture, When it is scanned, Then it inventories its
  components and does not hit the empty-extraction `indeterminate`; if the fix needs `--all-packages`, the argv carries
  it and the osv version-range test still passes.
- **AC4 — The comment is true.** The `interfaces.py` comment about native-lockfile components describes the findings
  the engines emit.
- **AC5 — The contract follows.** CAP-26 states today's unknown-then-warn behaviour through a `bmad-spec` re-derive; no
  `SPEC.md` hand edit.
- **AC6 — Green.** `pixi run --frozen -e pyforge-warden pyforge-warden-test` passes and the `ComplianceReport`
  validates at 1.1.0.

## Boundaries & Constraints

**Always:** never a false green: an axis with an unknown never composes to `clean`; the report schema stays 1.1.0
(additive only); the extractor imports no execution primitive.

**Never:** make the license or currency engines skip non-Python components (the ruling keeps them running); amend the
never-false-green Constraint; hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-warden` CAP-26 (FR-43) — the non-Python lockfile ecosystems' reports; a fix, no new
  CAP.

Parent: CAP-26

- EGM audit findings carried: WAR-M-D1 and WAR-M-C2 (cluster WAR-CL-5; accepted 2026-11-01; one memlog event each on
  `spec-pyforge-warden/.memlog.md`); operator ruling 2026-11-01 (the memlog decision of that date); residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 16 — a fix story joins its done epic (operator rule 2026-10-04; doctor Story 41.5 lets the epic key roll up
  to `in-progress`).
- Ledger key: `16-9-a-non-python-repo-s-license-and-currency-rows-report-what-ran`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-warden/src/pyforge/warden/report.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/native_lockfiles.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/interfaces.py`, `src/shared/packages/pyforge-warden/tests/unit/test_non_python_lockfiles.py`.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Minted 2026-11-01 by the EGM audit landing (marshal Story 113.7, spec-pyforge-marshal:CAP-302); mode in-PR: built in the audit's landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_non_python_lockfiles.py -q` — expected: pass, including both
  composed-status tests.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Auto Run Result

Status: backlog

Summary: not yet dispatched.

## Spec Change Log

- 2026-11-01: minted `backlog` from the EGM fleet audit (marshal Story 113.7): cluster WAR-CL-5, findings WAR-M-D1
  (contested, false-green refuted) and WAR-M-C2, accepted by the operator; operator ruling 2026-11-01 (state today's
  unknown-then-warn behaviour and fix the `deps_total=0` rows); mode in-PR.

## Review Triage Log

- (none yet)
