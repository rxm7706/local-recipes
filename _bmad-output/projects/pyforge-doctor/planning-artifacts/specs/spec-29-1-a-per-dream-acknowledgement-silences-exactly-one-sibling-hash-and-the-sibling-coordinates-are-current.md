---
title: '29.1: A per-Dream acknowledgement silences exactly one sibling hash, and the sibling coordinates are current'
type: 'feature'
created: '2026-09-19'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the first live run of CAP-71 with an operator token (`DW-OPS-2026-09-19-6`) reports six locally `archived`
Dreams diverging from their pre-fold sibling copies on every run — expected fold fallout the check cannot be told about, so
the six re-fire forever and will drown a genuine later change. Separately, `_SIBLING_OWNER` names
`OpenTeams-WFT-CDO`, an org GitHub now only redirects to `openteams-ai`.

**Approach:** honour a `sibling-acknowledged: <sibling content_hash>` line on the local Dream's frontmatter (silent while
the sibling's hash equals it; re-fires naming both hashes otherwise; an archived Dream without one is reported with its
status), and read the sibling from `openteams-ai/mgmt-wf-python-modernization` directly.

## Boundaries & Constraints

**Always:** read-only toward the sibling; the acknowledgement lives on the LOCAL Dream only and records a hash, never
content; unreachable / unauthenticated stay `warn` + fail-open (exit 0).
**Never:** write to the sibling; copy sibling prose; downgrade a mismatched hash to silence.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| local Dream `sibling-acknowledged:` == sibling `content_hash` | no finding for that Dream |
| acknowledged hash ≠ sibling hash | `sibling-dreams-drift: warn` naming the Dream, the acknowledged hash and the current one |
| local Dream `archived`, no acknowledgement, diverging | finding message carries `archived` so the operator sees the fold |
| no token | `sibling-dreams-unreachable`, warn, exit 0 (unchanged) |
| sibling path 404 under the new owner | `sibling-dreams-unreachable` with the HTTP status (unchanged shape) |
| the six DW-OPS-2026-09-19-6 Dreams acknowledged at their landing-day hashes | zero findings on a live run |

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-82` (extends CAP-71).
Surface: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py`, the six local Dreams named in `DW-OPS-2026-09-19-6` (`docs/dreams/{django-accelerator-framework,enterprise-data-models-and-apis,miniforge-installer,package-inventory-eligibility,pixi-container-image,reusable-cicd-workflows}.md`: one frontmatter line each), `planning-artifacts/deferred-work-ledger.md` (`DW-OPS-2026-09-19-6` closed with the live zero).
Ledger key: `29-1-a-per-dream-acknowledgement-silences-exactly-one-sibling-hash-and-the-sibling-coordinates-are-current`.
Ledger status at mint (unchanged): `backlog`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` can resolve this file. The landing-day sibling hashes are read live (`GH_TOKEN` from the operator's shell) — never guessed.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks (live, operator token):**
- `GH_TOKEN="$(gh auth token)" pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources sibling-dreams-drift` → exit 0 and no `sibling-dreams-drift` row for the six.

</intent-contract>
