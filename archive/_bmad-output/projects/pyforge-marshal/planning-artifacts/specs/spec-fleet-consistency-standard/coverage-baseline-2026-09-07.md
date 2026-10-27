# Fleet coverage baseline — 2026-09-07

**The first coverage measurement ever taken across all eight stations.** Companion of
`spec-fleet-consistency-standard` (Story 32.7; amends `spec-pyforge-testing-charter` CAP-4,
whose own Assumptions said out loud that this had never been measured).

Produced by `scripts/run_station_coverage_gate.py --station <s>` per station, on the
converged test trees (Story 32.5), immediately after `pytest-cov` reached the seven station
environments that had never had it. Every number below is a full-package evaluate — every
measured module, not just touched ones.

## Why this file exists

`spec-pyforge-testing-charter` CAP-4 states a fleet target of unit >80% / integration >70%
and assumed nothing about whether the fleet met it. The operator decision on 2026-09-07 was
**measure first, ratchet from the measured baseline** — never assert a floor nobody had
checked. This is that measurement, recorded so the ratchet has something to ratchet *from*.

## The result

| station | package total | unit modules under 80% | integration modules under 70% |
|---|---|---|---|
| `pyforge-atlas` | **86%** | 13 | — (no integration suite) |
| `pyforge-doctor` | **88%** | 2 | — (no integration suite) |
| `pyforge-herald` | **94%** | 1 | — (no integration suite) |
| `pyforge-marshal` | **86%** | 24 | 116 |
| `pyforge-mason` | **98%** | 2 | 21 |
| `pyforge-scribe` | **84%** | 4 | — (no integration suite) |
| `pyforge-steward` | **87%** | 7 | — (no integration suite) |
| `pyforge-warden` | **91%** | 1 | 7 |

## What the numbers actually say

**The fleet is well tested.** Package totals run 84–98%. The charter's worry — that coverage
was unknown and possibly poor — is answered: it is high.

**But no single per-station floor can express it.** Every station carries a short tail of
genuinely uncovered modules — CLI entrypoint shims (`__main__` at 0.0%), MCP servers,
harness adapters — beside a well-covered core. Setting a station's floor at its worst module
would produce floors of 0.0% for four stations, a gate that cannot fail; keeping 80/70 as a
*full-package* gate would red the fleet on day one. Both were rejected: the first is a fake
pass, the second is the flat-floor outcome the operator decision explicitly ruled out.

**The ratchet already existed, in the right place.** `scripts/coverage_gates_ci.py` gates only
the modules a PR *touches* (`touched_source_modules`). New and changed code must meet 80/70;
untouched legacy debt is reported and not weaponised. So CI enforcement expanded to all eight
stations with no grandfathering mechanism invented and no floor fabricated — the thresholds
TOML keeps its 80/70 defaults, because against touched modules that is the correct number.

The full-package `pyforge-<station>-test-coverage` pixi tasks below will therefore FAIL today
on several stations. That is intended: they are operator reports naming the debt, not gates.

## Per-station detail — modules under floor at baseline

### `pyforge-atlas` — package total 86%

Unit suite, under 80%:

- `pyforge.atlas.publish.__main__` — 0.0%
- `pyforge.atlas.datasets.vulnerability_feeds` — 26.6%
- `pyforge.atlas.query_plane_vectors` — 34.5%
- `pyforge.atlas.rag.store` — 35.1%
- `pyforge.atlas.datasets.sbom_intake` — 58.3%
- `pyforge.atlas.datasets.core_sources` — 66.4%
- `pyforge.atlas.parity.legacy_surface` — 72.4%
- `pyforge.atlas.query_plane_boot` — 74.2%
- `pyforge.atlas.mcp.session` — 75.0%
- `pyforge.atlas.pipelines.query_plane_cache.nodes` — 75.0%
- `pyforge.atlas.trending_candidates.handoff_main` — 76.0%
- `pyforge/atlas/views/render.py` — 76.9% (module retired Story 25.1)
- `pyforge.atlas.datasets.tier3_sources` — 78.5%

Integration suite: none under floor, or no integration suite at this station.

### `pyforge-doctor` — package total 88%

Unit suite, under 80%:

- `pyforge.doctor.sources.sibling_dreams` — 56.7%
- `pyforge.doctor.sources.board` — 67.3%

Integration suite: none under floor, or no integration suite at this station.

### `pyforge-herald` — package total 94%

Unit suite, under 80%:

- `pyforge.herald.locking` — 71.0%

Integration suite: none under floor, or no integration suite at this station.

### `pyforge-marshal` — package total 86%

Unit suite, under 80%:

- `pyforge.marshal.mcp.__main__` — 0.0%
- `pyforge.marshal.mcp.server` — 0.0%
- `pyforge.marshal.dispatch_supervisor.__main__` — 21.8%
- `pyforge.marshal.cli.chain` — 41.2%
- `pyforge.marshal.cli.refresh` — 60.7%
- `pyforge.marshal.cli.planning` — 61.0%
- `pyforge.marshal.dispatch_land_finalize.__main__` — 61.2%
- `pyforge.marshal.dispatch_fleet_supervisor.__main__` — 67.0%
- `pyforge.marshal.seed.detect.referenced_deps` — 68.2%
- `pyforge.marshal.core.dispatch_harness_done` — 69.0%
- `pyforge.marshal.dispatch_verify` — 69.0%
- `pyforge.marshal.core.model_cost` — 69.9%
- `pyforge.marshal.dispatch_land` — 72.7%
- `pyforge.marshal.cli.dispatch` — 76.0%
- `pyforge.marshal.dispatch_land_heal` — 76.2%
- `pyforge.marshal.cli.benchmark` — 76.6%
- `pyforge.marshal.cli.retire` — 77.0%
- `pyforge.marshal.cli.deploy` — 77.2%
- `pyforge.marshal.adapters.vcs_git` — 77.5%
- `pyforge.marshal.core.dispatch_survival` — 77.8%
- `pyforge.marshal.ports.forge` — 78.3%
- `pyforge.marshal.core.dispatch_verification` — 79.1%
- `pyforge.marshal.adapters.skill_invoke_harness` — 79.3%
- `pyforge.marshal.core.spec_deps` — 79.6%

Integration suite, under 70%:

- `pyforge.marshal.adapters.harness_bmadbuild` — 0.0%
- `pyforge.marshal.adapters.notify_file_desktop` — 0.0%
- `pyforge.marshal.adapters.observer_mux` — 0.0%
- `pyforge.marshal.cli.benchmark` — 0.0%
- `pyforge.marshal.cli.dispatch` — 0.0%
- `pyforge.marshal.core.dispatch_harness_done` — 0.0%
- `pyforge.marshal.core.dispatch_landing` — 0.0%
- `pyforge.marshal.core.dispatch_preserve` — 0.0%
- `pyforge.marshal.core.dispatch_push` — 0.0%
- `pyforge.marshal.core.dispatch_re_preflight` — 0.0%
- `pyforge.marshal.core.dispatch_retry` — 0.0%
- `pyforge.marshal.core.dispatch_supervisor_finalize` — 0.0%
- …and 104 more

### `pyforge-mason` — package total 98%

Unit suite, under 80%:

- `pyforge.mason.__main__` — 0.0%
- `pyforge.mason.__init__` — 77.8%

Integration suite, under 70%:

- `pyforge.mason.__main__` — 0.0%
- `pyforge.mason.airgap_contract` — 0.0%
- `pyforge.mason.boot` — 0.0%
- `pyforge.mason.cli` — 0.0%
- `pyforge.mason.doctor` — 0.0%
- `pyforge.mason.engines.condalock` — 0.0%
- `pyforge.mason.engines.gh` — 0.0%
- `pyforge.mason.environment` — 0.0%
- `pyforge.mason.exit_codes` — 0.0%
- `pyforge.mason.render` — 0.0%
- `pyforge.mason.package` — 10.7%
- `pyforge.mason.recipe` — 18.8%
- …and 9 more

### `pyforge-scribe` — package total 84%

Unit suite, under 80%:

- `pyforge.scribe.graph_store_plane` — 32.1%
- `pyforge.scribe.embeddings` — 37.5%
- `pyforge.scribe.graph_store_pg` — 39.4%
- `pyforge.scribe.graph_store` — 75.9%

Integration suite: none under floor, or no integration suite at this station.

### `pyforge-steward` — package total 87%

Unit suite, under 80%:

- `pyforge.steward.__main__` — 0.0%
- `pyforge.steward.suite_advance` — 57.4%
- `pyforge.steward.restore` — 62.9%
- `pyforge.steward.workspace` — 72.1%
- `pyforge.steward.suite` — 77.4%
- `pyforge.steward.__init__` — 77.8%
- `pyforge.steward.bootstrap` — 79.8%

Integration suite: none under floor, or no integration suite at this station.

### `pyforge-warden` — package total 91%

Unit suite, under 80%:

- `pyforge.warden.actuator` — 67.1%

Integration suite, under 70%:

- `pyforge.warden.eligibility` — 0.0%
- `pyforge.warden.eligibility_sbom` — 0.0%
- `pyforge.warden.sources` — 0.0%
- `pyforge.warden.tea_advisory` — 26.6%
- `pyforge.warden.extract.pixi` — 53.7%
- `pyforge.warden.extract.environment_yml` — 64.0%
- `pyforge.warden.scanner_plugins` — 67.2%

## Provenance

Measured 2026-09-07 on branch `chore/fleet-consistency-standard-2026-09-07`, after the
Story 32.5 tree convergence and before any CI change. `pyforge-scribe`'s run additionally
reported 18 errors from `psycopg` connection-refused on port 5433 — no local Postgres — which
is environmental and pre-existing; its coverage numbers are otherwise valid.

Derived, not restated: re-running the per-station tasks regenerates every figure here.
