---
title: "16.9: A non-Python repo's license and currency rows report what ran"
type: 'fix'
created: '2026-11-01'
status: 'done'
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

Status: done

Summary: implemented 2026-11-01 in the EGM audit landing worktree (branch `egm-audit-2026-11`); not committed.

**Probe (AC3) — it held.** osv-scanner 2.4.0 without `--all-packages`, run on a two-package npm lock that matches no
advisory, wrote `"results": []` (0 components); with `--all-packages` it listed both packages. So a clean npm lock
inventoried 0 components and composed the empty-extraction `indeterminate`, and a mixed lock listed only its
vulnerable packages.

**What changed:**
- `src/shared/packages/pyforge-warden/src/pyforge/warden/native_lockfiles.py` — `inventory_count_for_axis` counts every
  component on the vulnerability, license and currency axes and leaves native components out on hygiene only, so the
  license and currency rows report the N components their engines judged (AC1). `scan_native_lockfile` passes
  `--all-packages` (2.4.0, inside the tested `>=2.4.0,<2.5`; the version-range meta-test still passes) (AC3). The
  `is_non_python_native_ecosystem` docstring no longer calls license and currency N/A.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/interfaces.py` — the native-component comment in
  `DefaultPolicy.evaluate` describes what runs: osv-scanner's vuln scan, hygiene out of scope, and the license and
  currency engines emitting `license:unknown` / `currency:unknown` (warn ungated, indeterminate gated, never clean) (AC4).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/report.py` — a comment at the per-axis total; no code change
  (the row fix flows through `inventory_count_for_axis`). Schema stays 1.1.0; no engine skips a native component.
- `src/shared/packages/pyforge-warden/tests/unit/test_non_python_lockfiles.py` — the old `license deps_total == 0`
  assertion now reads `== inventory_count == 1`; `inventory_count_for_axis` asserts license/currency counts; new
  `test_scan_native_lockfile_inventories_a_clean_lock` (AC3), `test_npm_license_and_currency_rows_count_what_ran`
  (clean N=2, vulnerable N=1; AC1/AC3) and `test_npm_lock_composed_status_is_pinned` (clean and vulnerable lock ×
  ungated / `--deny-licenses GPL-3.0-only` / `--fail-on-eol`: ungated `warn` exit 0, gated `indeterminate` exit 1
  driven by the gated axis with its row `gating: true`, the vulnerable lock carries
  `vuln:PDOS-NPM-FIXTURE-0001:pdos-npm-vuln-fixture@1.0.0`, `schema_version` 1.1.0; AC2/AC6). The clean lock is
  written into `tmp_path`, so no new fixture file.
- Mutation check: dropping `--all-packages` fails 5 tests (every clean-lock case); restoring the old
  `inventory_count_for_axis` fails 8 (the counting test, both row tests, the vuln-lock row assertion, the four gated
  cases). The file was restored byte-identical (`cmp`).
- AC5: two events appended to `spec-pyforge-warden/.memlog.md` (the surface reconcile and the CAP-26 behaviour line);
  the CAP-26 text itself changes only through the session's `bmad-spec` re-derive (with WAR-CL-3's), never by hand.

**Commands run (exit codes):**
- `pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_non_python_lockfiles.py -q` — 0 (28 passed).
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — 0 (2238 unit + 265 meta/integration passed).
- `ruff check` / `ruff format --check` (pyforge-guild's ruff, run from the package directory as `lint-types` does)
  over the four changed files and over the whole package's `src tests` — 0 / 0.
- `mypy -p pyforge.warden` from the package directory (pyforge-guild env, scratch cache dir) — 0 (44 source files).
- `pixi run --frozen -e pyforge-guild lint-types` — 1, not from this story: its ruff leg reds on
  `src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py` (I001), another station's in-flight
  edit in this shared worktree; `pyforge-warden` and `django-warden` report `ok`, and the chain stops before the
  format and mypy legs (warden's slices of both are green above).

## Spec Change Log

- 2026-11-01: minted `backlog` from the EGM fleet audit (marshal Story 113.7): cluster WAR-CL-5, findings WAR-M-D1
  (contested, false-green refuted) and WAR-M-C2, accepted by the operator; operator ruling 2026-11-01 (state today's
  unknown-then-warn behaviour and fix the `deps_total=0` rows); mode in-PR.
- 2026-11-01: implemented; the AC3 probe held (`--all-packages` added); status `in-review`.

## Review Triage Log

- **Review 1 (2026-11-01, reviewer: independent session) — PASS.**
  - Checked: the `native_lockfiles.py`, `interfaces.py` and `report.py` diffs and the tests against AC1-AC6 and the Boundaries; the osv version-range meta test passes with `--all-packages`; no engine skips a native component.
  - Common evidence (one run for all eight stories, exit codes read from `$?`): `pixi run --frozen -e pyforge-warden pyforge-warden-test` exit 0 (2255 unit+meta, 265 other); the twelve touched warden unit/meta test files together exit 0 (290 passed, 0 skipped; opengrep 1.30.2 and osv-scanner present); `ruff check` and `ruff format --check` over every changed warden, django-warden and platform test file exit 0; `python scripts/lint_types.py ruff-format` exit 0 and `python scripts/lint_types.py mypy` exit 0 (`pyforge-warden ok`); `pixi run --frozen -e pyforge-guild lint-types` exit 1 only from `pyforge-doctor`'s I001 in `tests/unit/test_sources_pages_liveness.py`, another station's in-flight file (`pyforge-warden` and `django-warden` ruff legs ok); `pixi run -e pyforge-guild platform-ci-local -- --test` (private ports) exit 0, RESULT: PASS, 1377 passed / 14 skipped; touched warden modules' unit coverage all at or above 81%. Mutations ran on scratch copies only (warden via `PYTHONPATH`, django-warden via `pytest -o pythonpath=`), never on the worktree.
  - Reviewer probe: four npm reports (clean lock, vulnerable lock, clean lock gated on license, mixed dry-run) validate against `report-schema.json` at 1.1.0; the license and currency rows read N=2 (clean) and N=1 (vulnerable); ungated `warn`, gated `indeterminate`.
  - Mutations: dropping `--all-packages` turns 5 red (every clean-lock case); the old `inventory_count_for_axis` turns 8 red.
  - Carried forward, not held against the story: the CAP success-line change is recorded on `spec-pyforge-warden/.memlog.md`; `SPEC.md` is unchanged, as required, and the line waits for the session owner's `bmad-spec` re-derive.
  - Failures: none.
