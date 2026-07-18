# BSL metric-parity — provenance & scope (Story D1, FR-8)

The `bsl-metric-check` gate is the AD-7 metric-semantics handover anchor. It proves the
Boring Semantic Layer (`pyforge.atlas.semantic`) answers the CORE atlas metrics with the
SAME value as the legacy read CLIs, via Ibis → DuckDB ONLY (AD-4), through the single
translation interface (AD-8).

## The DW-B1-1 discipline (why these fixtures are real anchors)

The trap D1 must avoid is a parity fixture that "proves" parity by having both sides
compute the same thing. Every assertion in `test_bsl_metric_parity.py` computes its
expected value from an **independent re-implementation of the legacy formula** — a
verbatim copy of the legacy Python function (`_legacy_classify`, copied from
`adoption_stage.py::_classify`) or the legacy SQL predicate translated to pandas
(`_legacy_is_actionable` ← `v_actionable_packages` DDL; `_legacy_staleness_age_days` ←
`staleness_report.py`). The BSL side is the Ibis port under test. A divergence between
the two fails the gate.

## Metric provenance (mirrors `metrics.METRIC_PROVENANCE`)

| Metric | Legacy source | Provenance | Data wiring |
|---|---|---|---|
| `staleness_age_days` | `staleness_report.py` age_days | legacy-formula | deferred (latest_conda_upload not yet migrated) |
| `adoption_stage` | `adoption_stage.py::_classify` | legacy-formula (verbatim) | deferred (per-version upload times not migrated) |
| `is_actionable` | `v_actionable_packages` view DDL | legacy-formula | migrated-column |
| `downloads_total` | `compute_downloads` | legacy-formula | migrated-column (`core_downloads`) |
| `downloads_30d` | `compute_downloads` (latest month) | legacy-formula | migrated-column (`core_downloads`) |
| `ci_red` | `feedstock_health.py --filter ci-red` | migrated-node-derived-flag-recapture | migrated-column (`core_feedstock_health.ci_status`) |
| `has_open_prs` | `feedstock_health.py --filter open-pr / open-prs-human` | migrated-node-derived-flag-recapture | migrated-column |
| `has_open_issues` | `feedstock_health.py --filter open-issues` | migrated-node-derived-flag-recapture | migrated-column |
| `maintainer` | `package_maintainers ⋈ maintainers` JOINs | legacy-formula | migrated-column (`vcs_package_maintainers` ⋈ `vcs_maintainers`) |

### `legacy-formula` vs `migrated-node-derived-flag-recapture`

- **legacy-formula** — a faithful port of an explicit legacy CLI formula, anchored by an
  independent re-implementation in the parity test.
- **migrated-node-derived-flag-recapture** — the migrated `core_feedstock_health` shape
  (a B-wave shape port) renamed/collapsed the legacy Phase M/N columns, so the expression
  is declared over the migrated column and FLAGGED (exactly the B2 shape-only-seed
  discipline). All three feedstock-health filters are flagged: `ci_red` assumes
  `ci_status`'s value domain equals the legacy `gh_default_branch_status`
  ({failure, error, …}); `has_open_prs` loses the bot(Phase M) vs human(Phase N) split;
  `has_open_issues` rides the unverified `gh_open_issues_count → open_issues` rename. A
  green gate proves the Ibis expression is self-consistent, NOT that it reproduces the
  credentialed legacy value — B4-style recapture confirms that.

## Deferred (NOT declared in D1 — no fabricated legacy signal)

- **feedstock-health `--filter stuck`** (`bot_version_errors_count > 0`) and **`--filter bad`**
  (`feedstock_bad = 1`) — Phase M columns absent from the migrated `core_feedstock_health`
  shape. Documented in `metrics.DEFERRED_FEEDSTOCK_HEALTH_FILTERS`; recapture with D2.
- **Data wiring** for `staleness_age_days` / `adoption_stage` — the FORMULA + its legacy
  anchor land in D1; the live catalog column (`latest_conda_upload`, per-version upload
  times) is wired when D2 ports the pages.
- **The full 28-CLI metric surface** — D1 lands the CORE set the AC names + the framework
  + the gate. D2 ports each page and completes the remaining metrics through this same
  interface.
