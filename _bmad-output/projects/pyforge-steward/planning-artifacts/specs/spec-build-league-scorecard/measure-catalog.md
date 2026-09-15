# Measure catalog (companion)

Load-bearing tables for `spec-build-league-scorecard`. The kernel cites this
file; do not invent a ninth steering number here.

## Registry

Config names every measure. A new source is a new row. A dead source is
**archived** (id kept; never reused). States:

| State | Steers work? |
|---|---|
| `on` | yes |
| `off` | no (still a named published row) |
| `archived` | no (retired) |

A new row starts `off` until the operator flips it `on`. Consumers may cite
only `on` rows. They must not invent a substitute for `off` or `archived`.

## First cut (all `on`, 2026-09-15)

| id | Dimension | Source (already counted) | Notes |
|---|---|---|---|
| `warden-verdict` | human | Warden verdict rungs | Q8 remains the PR gate |
| `owner-work-class` | human | steward discovery `owner` / `work_class` | 03 work only |
| `gate-record-outcomes` | agent | `gate-record.json` per-story commands | pass/fail, not a new score |
| `journal-timing` | agent | `journal.json` run/phase timing | |
| `run-cost-usd` | agent | `driver.py` per-run `total_cost_usd` | |
| `ledger-throughput` | team | sprint ledger stories → `done` | |
| `detector-pass-fail` | team | detector / `detectors-ci` vector | |
| `five-tier-completeness` | team | five-tier 8×5 ladder | **never** score 01/02 work |

## Out of this catalog

- Weights, composites, or a single league total.
- Jira keys as quality.
- A dashboard UI (later empty slot on the Spec).
- Hub Outcome Guards (they read `on` rows later).
