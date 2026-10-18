---
title: "34.10: Phase H covers every mapped PyPI project, gated by its serial"
type: 'feature'
created: '2026-10-18'
status: 'in-review'
baseline_revision: 'bde97f7f80'
flag:
  key: pyforge.atlas.live_public_sources          # shared with Stories 34.4 (registered it) to 34.9
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: on, dev: on}   # unchanged from 34.4
  scope: global                                   # v1 is global only
  fallback: 'the fan-out keeps today''s bounded behaviour: PYPI_JSON_FANOUT_LIMIT names (default 200) per run from a rotating offset, behind the store''s weekly cadence'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-34-2-the-phase-c-mapping-fills-from-the-conda-forge-bot-s-name-mapping.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/request_datasets.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/refresh.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py
deferred: ['DW-atlas-34-10-1']
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pypi_current_versions` and everything after it covered a few hundred projects.

- `PYPI_JSON_FANOUT_LIMIT` capped the fan-out at 200 names a run, from a rotating offset behind the store's weekly
  cadence. The ~11,000 mapped names took about 55 runs to cover once (Story 34.2).
- Legacy Phase H (`_phase_h_eligible_pypi_names`, CFA:4174) fetches every row of its universe that is eligible:
  - never fetched;
  - its serial moved (NULL-safe `IS NOT` against the serial stamped at fetch);
  - or fetched more than 30 days ago.
  It retries 429 and 503 after `Retry-After`, with three attempts (CFA:4073).
- **Found while wiring the gate: `fetch_pypi_current_versions` re-applied the gate to the stored rows** and emitted
  only the eligible ones. `pypi_current_versions` is overwritten each run, never merged. A run that stamps the
  serial at fetch would therefore shrink it to the few projects whose serial moved. Nothing stamped a serial
  before, so every row looked never-fetched, and that hid the problem. The first live run of this story, still on
  the old node, wrote 34 rows from a 10,875-row store.
- The store merged rows on `conda_name`, so a second PyPI project mapped to the same conda package replaced the
  first.

**Approach:**
1. **The trigger carries the serials.** `refresh_pypi_json_store` takes the same run's
   `pypi_universe_serial_snapshots` as an input (so Kedro runs it after Phase D). It passes each candidate's
   current serial on the `RefreshRequest` (`pypi_serials`), matched under PEP 503.
2. **The fan-out fetches the eligible set while live public sources are on.**
   - `PyPIJsonFanOutDataset._eligible` orders candidates never fetched first, then serial moved, then the 30-day
     re-check, oldest first.
   - The batch is uncapped. `PYPI_JSON_FANOUT_LIMIT` stays an explicit cap; `0` skips the cycle under a marker.
   - The store's weekly cadence no longer holds a moved serial back.
   - Each row stamps the serial it was fetched at: the snapshot's when known (legacy stamps Phase D's), else the
     payload's own `last_serial`.
   - A project that fails is not stored, so it stays eligible.
   - Nothing eligible is a clean run.
   - Flag off: today's bounded rotation, unchanged.
3. **Retries.** `load_many` retries 429 and 503 up to three attempts. It waits the server's `Retry-After`
   (capped at 60 s, `parse_retry_after`), else 1 s then 2 s. Other failures stay one per-project miss.
4. **Public GETs.** With no credentials, every request carries a 30 s timeout and a no-op auth, so requests never
   reads `~/.netrc` (`public_sources.request_args`).
5. **The node keeps every fetched project's version.** `fetch_pypi_current_versions` emits every stored row:
   - `pypi_last_serial` comes from the universe join;
   - `pypi_version_serial_at_fetch` is the row's stamp, else the current serial.
   The gate now lives in the fetch, as legacy's does; `phase_h_eligibility_stats` still reports its split.
6. **One row per PyPI project.** The store merges on `pypi_name`.
7. **Rate.** The catalog raises the fan-out's rate to 10 requests a second. pypi.org allows about 30 per IP
   (CFA:4197), and legacy ran 3 workers.

Ledger key: `34-10-phase-h-covers-every-mapped-pypi-project-gated-by-its-serial`.
Type / Effort / Deps: feature / M / Story 34.2 (the Phase C candidates), Story 34.4 (`public_sources`).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-64** (`live-sources.md`, the pypi.org row): a feature behind
  `pyforge.atlas.live_public_sources`.
- **AD-2** (dataset-owned IO), **AD-5** (incremental: fetch only what moved), **AD-13**, **AD-11** (every test's
  responses are built in memory; the suite pins the flag off).
- **Origin.** Dream entry 2026-10-18 (atlas fills its own data), R3/R4.

## Acceptance Criteria

- **AC1 — The eligible set.**
  - Live, the fan-out fetches exactly the never-fetched, serial-moved and 30-day-old candidates, in that order. A
    known serial against a missing stamp counts as moved; with no serial known, only the 30-day check applies.
  - A cold run fetches every candidate, past the old 200 cap.
  - A warm run with no serial movement fetches only the 30-day re-checks, and the store's cadence never holds a
    moved serial back.
  - An explicit limit caps the set; `0` skips the cycle under a marker.
- **AC2 — The stamp.** Each row stamps the snapshot's serial when known, else the payload's.
- **AC3 — The trigger.** It carries each candidate's serial matched under PEP 503, and runs after Phase D.
- **AC4 — Retries.**
  - 429 and 503 are retried after `Retry-After`, else back off.
  - A throttle that outlasts three attempts is a miss.
  - A 404 is never retried.
  - Each GET carries a timeout and no credential.
- **AC5 — Coverage.** `pypi_current_versions` holds every fetched project, whatever the gate says, and the store
  keeps one row per PyPI project.
- **AC6 — The flag.** On: the eligible set. Off: today's bounded rotation. Tested with `flag_states`.
- **AC7 — Live.** See Verification. Tolerance against legacy Phase H, measured the same day:
  - **(a)** atlas fetches at least 99% of its candidates;
  - **(b)** on the shared names, at least 99% of current versions are equal;
  - **(c)** its candidates cover legacy's parselmouth-mapped names to within 1%.
- **AC8 — Gates.** `pyforge-atlas-test`, `kedro-test`, `kedro-catalog-check`, the coverage gate, `lint-types`
  (and mypy in `pyforge-foundry-full`), `flag-gate-check`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, each named from the repo root:
  - `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_pypi_json_phase_h.py`: the eligible set, the
    stamp, retries, request args, the store key, the trigger, and the two-state test spelled with
    `@flag_states("pyforge.atlas.live_public_sources")`.
  - `src/shared/packages/pyforge-atlas/tests/unit/pipelines/pypi_intelligence/test_serial_gate.py`: the node keeps
    every fetched row.
  - `src/shared/packages/pyforge-atlas/tests/unit/pipelines/pypi_intelligence/test_nodes.py`: the trigger runs
    after Phase D.
- **Live, recorded 2026-10-18.** A scratch copy of the 2026-10-17 data root, flag on (dev),
  `--pipelines pypi_intelligence --nodes snapshot_pypi_serials,map_pypi_conda,refresh_pypi_json_store,fetch_pypi_current_versions`.
  - **Cold:** exit 0, 19.7 min, peak RSS 2.8 GB (the simple index).
    - 10,955 of 10,955 candidates were eligible; 10,875 were stored.
    - The 80 misses failed again on the warm run. The one the log names is a hash-like name in the bot's
      mapping that PyPI answers 404.
    - This run predates the node fix: `pypi_current_versions` held 34 rows.
  - **Warm, one hour later, with the node fixed:** exit 0, 57 s.
    - 84 eligible: the 80 misses, never stored, plus 4 serials that moved.
    - `pypi_current_versions` holds 10,875 rows, 10,874 with an upload time.
  - **Against legacy `cf_atlas.db`** (`v_actionable_packages`, PEP 503 keys):
    - (a) 10,875 of 10,955 candidates are fetched: 99.3%.
    - (b) Of the 10,873 shared names, 10,827 have equal versions: 99.58%. The rest released since legacy's fetch.
    - (c) Legacy's parselmouth-mapped set is 10,965 names, of which 81 are not in atlas's candidates: 0.74%.
  - **Legacy's universe is 20,938 names.** The other 10,565 carry `match_source = 'none'`: recipe-source-URL
    matches (legacy's Phase C.5, folded into Phase E) kept from earlier runs. Atlas has no such match; it is
    `DW-atlas-34-10-1`, and outside this story, which fetches what the mapping names.

## Boundaries & Constraints

**Never:** a credential on pypi.org; an HTTP client import in the package; a test that touches the network; a
fetch of a PyPI-only project (the candidates are the mapping's, never `pypi_universe`).

**Residual risk:**
- **The 80 misses are requested on every run** (about 10 s). Legacy stamps a 404 to stop that; here a miss is
  never stored, so it stays eligible.
- **A cold run takes about 20 minutes** at 10 requests a second, sequentially; warm runs take about a minute.
- **The serial snapshot comes from the simple index**, about 2.8 GB of peak memory in the same run.
- **netrc on a redirect:** a redirect to another host still consults `~/.netrc` for that host. pypi.org does not
  redirect the JSON API today.

## I/O & Edge-Case Matrix

| Situation | Before | After |
|---|---|---|
| Cold live run | 200 names a run, rotating | every candidate; 10,875 stored |
| Warm run, nothing moved | weekly cadence: nothing, or 200 names | only the 30-day re-checks and misses |
| A serial moved | wait for the cadence and the rotation | fetched this run |
| 429 / 503 | a per-project miss | retried after `Retry-After`, three attempts |
| Flag off | bounded rotation | unchanged |
| A run that stamps serials | — | `pypi_current_versions` keeps every fetched project (it would have shrunk) |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-64 (FR-72), a feature.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data).
- Epic 34 / Story 34.10 in `planning-artifacts/epics.md`.
- Flag: `pyforge.atlas.live_public_sources` (`feature-flag-governance:CAP-1`), registered by Story 34.4.

## Spec Change Log

- 2026-10-18: written with the implementation (branch `atlas-34-10-phase-h-coverage`, cut from `main` at
  `bde97f7f80`). The node's re-applied gate was found by the first live run; `DW-atlas-34-10-1` records the
  Phase C.5 gap the parity check exposed.
