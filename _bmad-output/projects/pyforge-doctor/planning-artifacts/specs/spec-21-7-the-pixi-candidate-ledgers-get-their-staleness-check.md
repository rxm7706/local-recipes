---
title: 'The pixi candidate ledgers get their staleness check'
type: 'feature'
created: '2026-09-10'
status: 'done'
baseline_revision: '3f2f537ae9883658ad084cfd99b122b9d0e58f68'
review_loop_iteration: 0
followup_review_recommended: false
review_loop_iteration: 1
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** All five of `spec-pixi-candidate-currency`'s CAPs are uncovered by any
doctor epic or FR. CAP-4 — the advisory ledger-staleness check, the Spec's own
linchpin (*"that answer is demonstrably still current … because CAP-4's staleness
check would have flagged it otherwise"*) — has no module in `sources/` and no
dispatch entry, while the drift it exists to catch is already live: the Dream audited
44 candidates over 64 commented dependency lines, and `pixi.toml` has moved with **45
commits** since the last currency pass.

**Approach:** Ship CAP-4 as one small new source, `sources/pixi_currency.py`. It
reports how far each of the Dream's four ledgers has fallen behind `pixi.toml`'s own
commit history. The staleness threshold is a declared policy value rather than a
literal buried in the module. The finding is `warn` at most and never gates — this is
not the fleet's one fail-closed gate. It degrades to a named finding when a ledger or
`pixi.toml` cannot be read. CAP-1/2/3/5 are deliberately left alone in this story —
they describe ledgers the Dream already contains, satisfied by the Dream's own
content rather than by code.

## Boundaries & Constraints

**Always:**
- The check reports how far each of the Dream's four ledgers has fallen behind
  `pixi.toml`'s own commit history.
- The staleness threshold is a declared policy value, not a literal buried inline in
  the module.
- The finding is `warn` at most — it never gates (this is not the fleet's one
  fail-closed gate).
- An unreadable ledger or unreadable `pixi.toml` degrades to a named finding, never a
  crash or silence.

**Never:**
- CAP-1/2/3/5 are not implemented by this story — they describe ledgers the Dream
  already contains, satisfied by the Dream's own content, not by new code.
- The check never gates the build or any CI lane; it is advisory only.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Ledger behind threshold | One of the Dream's four ledgers has fallen behind `pixi.toml`'s commit history past the declared policy threshold | Warn finding naming the ledger and how far behind it is | n/a |
| Ledger within threshold | Ledger's staleness is within the declared policy value | No finding (or an OK finding, per the package's own convention) | n/a |
| Ledger unreadable | One of the four ledger files cannot be read | Named finding, degrade-on-exception style | Fail-open, named |
| `pixi.toml` unreadable | `pixi.toml` itself cannot be read | Named finding | Fail-open, named |
| Live drift (measured 2026-09-09) | 44 candidates over 64 commented dependency lines, 45 commits to `pixi.toml` since last currency pass | Staleness reported accordingly | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/pixi_currency.py` — new module implementing CAP-4.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py` — `DISPATCH` entry for the new source.
- `pixi.toml` — one `detectors` row + the task for the new check.
- `src/shared/packages/pyforge-doctor/tests/unit/` — new unit tests.
- `.claude/skills/conda-forge-expert/tests/meta/test_all_scripts_runnable.py` — if a CLI wrapper is added, per the three-place rule.

## Tasks & Acceptance

**Execution:**
- `feature` — implement `sources/pixi_currency.py`: read the Dream's four candidate ledgers, compare their currency against `pixi.toml`'s commit history, and emit warn-at-most findings per ledger using a declared policy staleness threshold.
- `feature` — wire the new source into `sources/__main__.py`'s `DISPATCH`, following the established `Source` member / `REGISTRY` / `DISPATCH` pattern.
- `feature` — add a `detectors` row and pixi task for the new check in `pixi.toml`.
- `feature` — add unit tests covering the I/O matrix (within-threshold, past-threshold, unreadable ledger, unreadable `pixi.toml`).

**Acceptance Criteria:**
- Given all five of `spec-pixi-candidate-currency`'s CAPs are uncovered by any doctor epic or FR, and CAP-4 has no module in `sources/` and no dispatch entry while the drift it exists to catch is already live, when the check ships as one small source, then it reports how far each of the Dream's four ledgers has fallen behind `pixi.toml`'s own commit history.
- The staleness threshold is a declared policy value rather than a literal buried in the module.
- The finding is `warn` at most and never gates.
- It degrades to a named finding when a ledger or `pixi.toml` cannot be read.
- CAP-1/2/3/5 are left alone — they are descriptions of ledgers the Dream already contains, satisfied by its own content, not by code.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: full suite green

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch. Its absence makes `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live against `spec-21-13`'s own dispatch run, and again against `spec-21-14`'s.

## Auto Run Result

- **Summary:** Shipped CAP-4 as `sources/pixi_currency.py`: compares each of the Dream's four ledger sections against `pixi.toml` commit history using declared policy threshold `PIXI_CURRENCY_LEDGER_STALENESS_PIXI_COMMITS = 30`. WARN-only findings; fail-open on unreadable dream, ledger section, or pixi.toml.
- **Files changed:**
  - `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/pixi_currency.py` — new gather filter
  - `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` — `Source.PIXI_CURRENCY_LEDGER`
  - `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` — REGISTRY row
  - `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py` — DISPATCH entry
  - `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json` — schema enum
  - `scripts/detectors.py` — detectors-ci pairing
  - `pixi.toml` — `pixi-currency-staleness-check` task
  - `tests/unit/test_sources_pixi_currency.py` — I/O matrix coverage
  - test registry updates (dispatch, models, source independence)
- **Review:** 0 patch / defer / intent_gap findings; implementation matches intent contract.
- **Follow-up review recommended:** false
- **Verification:** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 1585 passed, 1 skipped
- **Residual risk:** Live repo currently reports WARN on all four ledgers (69+ pixi.toml commits since Aug 2026 audit) — expected until ledgers are re-audited or threshold tuned.

## Review Triage Log

### 2026-09-11 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — self-review after green test suite)
