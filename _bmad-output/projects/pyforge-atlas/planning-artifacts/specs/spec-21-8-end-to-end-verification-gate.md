---
title: 'End-to-end verification gate (Story 21.8, Epic 21)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/verification-matrix.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/identity-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/operator-surfaces.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/implementation-artifacts/epic-21-context.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-21-1-relocate-atlas-data-defaults-and-bootstrap.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-21-2-remove-cf-atlas-db-seeds-from-production-datasets.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** Epic 21's own success signal (`SPEC.md` § Success signal) is never proven by any
single upstream story — Stories 21.1-21.7 each verify only their own local slice (bootstrap
smoke on an empty root, SQLite-seed removal, Tier 0/1/2 catalog completeness, the identity
join, quartet thin-out) but nothing runs the FULL chain end-to-end on a genuinely fresh clone
and checks that the whole self-contained data plane (CAP-1 through CAP-4 together) actually
holds: no `CF_ATLAS_DB` anywhere, `--live-catalog` reproducing every `verification-matrix.md`
field from Parquet alone, `parity-diff` and `bsl-metric-check` staying green against the fully
populated catalog (not the partial fixture states those gates saw story-by-story), and the
operator env block documenting every variable an operator needs across the whole bootstrap —
not only Story 21.1's CAP-1 subset.

**Approach:** No new data sources, pipelines, datasets, or catalog entries. This story is pure
verification plus documentation: (1) run `pyforge-atlas-bootstrap` on a genuinely empty data
root with no `CF_ATLAS_DB` set and confirm exit 0 across all seven pipelines the task names
(including `seed_gaps` — this story cannot carve it out as Story 21.2 did, see Design Notes);
(2) run the inventory metrics CLI's `--live-catalog` mode (Story 21.3's CLI contract, per
`verification-matrix.md`) against the bootstrapped root and diff every listed field against the
legacy/Excel-mode value on a fixed corpus; (3) re-run `parity-diff` and `bsl-metric-check`
against the now-fully-populated catalog and confirm both green; (4) extend the README's
Operator env block table (Story 21.1's table) to cover every variable introduced by
Stories 21.3-21.7 (Tier 1/2 credentials, identity-join credentials, the `--live-catalog`
flag itself), so it is complete for the whole epic rather than only the CAP-1 bootstrap.

## Boundaries & Constraints

**Always:**
- No dataset, pipeline, node, or catalog entry is added or modified by this story — CAP-1
  through CAP-4 are proven read-only here, never extended.
- The bootstrap run uses a genuinely empty `PYFORGE_ATLAS_DATA_ROOT` (never an already-populated
  local dev data dir) with `CF_ATLAS_DB` unset.
- `--live-catalog` output is diffed field-by-field against the same fixed corpus's legacy-mode
  output per `verification-matrix.md`'s table — a "looks plausible" spot check does not satisfy
  this story; every listed field must match or the story is not done.
- `pixi run -e pyforge-atlas parity-diff` and `pixi run -e pyforge-atlas bsl-metric-check` are
  RE-RUN after the full bootstrap (not merely cited as "was green once" from an earlier story's
  narrower state).
- `src/shared/packages/pyforge-atlas/README.md`'s Operator env block table (added Story 21.1) is
  extended to list every environment variable needed across the full Epic 21 bootstrap +
  `--live-catalog` chain, not only the CAP-1 subset.

**Block If:** Stories 21.3, 21.4, 21.5, 21.6, and 21.7 are not all `status: done`. This spec may
be authored and reviewed ahead of that (as this document is), but implementation must not be
dispatched until all five are done — see Design Notes.

**Never:**
- Do not add a new pipeline, dataset, or catalog entry — CAP-1-4 are proven here, not extended
  (that is 21.3-21.7's, or Epic 22/23's, territory).
- Do not silently narrow the `verification-matrix.md` field list the way Story 21.2 narrowed its
  bootstrap-chain AC around the pre-existing `seed_gaps` bug. If a field genuinely cannot be
  reproduced from Parquet at dispatch time, that is either a real blocker for this story (fix the
  upstream gap) or a Spec Change Log amendment with the same rigor Story 21.2 used — a cited,
  reproduces-on-baseline, pre-existing-and-unrelated bug — never a silent skip.
- Do not modify `tests/parity/parity_runner.py`'s credentialed legacy-comparison mode (same
  constraint as Story 21.2).
- Do not touch Epic 22/23 surfaces (Vizro pages, `identity_complete_export.parquet`, ranking) —
  out of Epic 21's core scope per `SPEC.md` § Non-goals.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh clone, no `CF_ATLAS_DB`, empty data root | `PYFORGE_ATLAS_DATA_ROOT` unset or an empty dir; `CF_ATLAS_DB` unset | `pixi run -e pyforge-atlas pyforge-atlas-bootstrap` exits 0 across all seven pipelines named in the task (`core`, `pypi_intelligence`, `vulnerability`, `vcs_health`, `upstream_discovery`, `derived_artifacts`, `seed_gaps`) | Any non-zero exit is a story blocker, not a deferred finding |
| `--live-catalog` against the bootstrapped root | Bootstrap complete; metrics CLI invoked with `--live-catalog` (Story 21.3 contract) | Every `verification-matrix.md` field (`PyPI_Verified`, `CondaForge_Verified`, `Source_Repository_URL`, Basilisk/AOSS/Anaconda membership, cross-channel BOOLs, `identity_source`/`primary_purl`/`conda_purl`) matches the legacy/Excel-mode value on the same fixed corpus | A mismatched field fails the story; a still-missing field (dataset not actually wired despite the upstream story claiming done) is a real gap, escalate, do not paper over |
| `--live-catalog-only` strict mode | A required dataset is deliberately made missing/stale | Command fails loudly, non-zero exit | Never a silent pass |
| Re-run `parity-diff` / `bsl-metric-check` post-bootstrap | Full catalog populated (not the earlier per-story fixture-only state) | Both pixi tasks green | A regression here means an earlier 21.x story broke semantic parity — fix upstream, do not weaken this story's AC to route around it |
| Operator reads the extended env block | `README.md` § Operator env block table | Every variable touched across 21.1-21.7 (Tier 1/2 credentials, identity-join credentials, any `--live-catalog`-related override) is listed with Required/Effect columns | A missing variable is a documentation gap this story must close |

</intent-contract>

## Code Map

- `pixi.toml` `[feature.pyforge-atlas.tasks.pyforge-atlas-bootstrap]` (~L2014-2018, Story 21.1) —
  the bootstrap entrypoint this story runs end-to-end; `cmd = "python tools/bootstrap.py &&
  kedro run --pipelines core,pypi_intelligence,vulnerability,vcs_health,upstream_discovery,
  derived_artifacts,seed_gaps"` — no command change expected, verification only.
- `pixi.toml` `[feature.pyforge-atlas.tasks.parity-diff]` (~L2027-2029) and
  `[feature.pyforge-atlas.tasks.bsl-metric-check]` (~L2031-2033) — the two semantic gates this
  story re-runs against the fully bootstrapped catalog; both currently target
  `tests/parity` / `tests/semantic` via plain `pytest -q`, unchanged by this story.
- `src/shared/packages/pyforge-atlas/README.md` § "Operator env block" (~L81-93, Story 21.1) —
  today's table covers only `PYFORGE_ATLAS_DATA_ROOT`, `GITHUB_TOKEN`/`GH_TOKEN`, and
  `GOOGLE_APPLICATION_CREDENTIALS`; extend it with every variable Stories 21.3-21.7 introduce.
  This table is the story's one documentation deliverable (`invoke_dev_with`).
- `src/shared/packages/pyforge-atlas/tests/semantic/test_bsl_metric_parity.py` (+
  `test_maintainer_dimension.py`, `test_metric_provenance.py`) — the existing BSL metric-parity
  suite `bsl-metric-check` runs; re-verify green against the fully populated catalog, do not add
  new metric anchors here (a new metric needing a parity anchor is 21.3-21.7's territory).
- `src/shared/packages/pyforge-atlas/tests/parity/` — `parity-diff`'s pytest target (fixture-mode
  node-output-vs-legacy-snapshot); re-verify green.
- `scripts/conda-forge-packaging-inventory-operations_metrics.py` (repo-root inventory metrics
  CLI) — Story 21.3 adds the `--live-catalog` / `--live-catalog-only` flags here per
  `verification-matrix.md`'s CLI contract. Confirmed via `grep -n "live.catalog"` against this
  file (and the whole `src/` tree) returning zero hits as of this spec's drafting — the flag does
  not exist yet; this story's verification depends on Story 21.3 landing it first.
- `_bmad-output/.../specs/spec-atlas-kedro-catalog-expansion/verification-matrix.md` — the
  field-to-Parquet-path mapping this story's `--live-catalog` diff is graded against; also
  documents the proposed `--live-catalog` / `--live-catalog-only` CLI contract.
- `_bmad-output/.../specs/spec-atlas-kedro-catalog-expansion/identity-contract.md` — the
  `lookup_assoc` / `from_inventory` / `from_board_only` parity semantics this story restates as a
  cross-CAP proof point (Story 21.6 owns deriving them; this story re-confirms them as part of
  the whole-epic gate).
- `_bmad-output/.../specs/spec-atlas-kedro-catalog-expansion/SPEC.md` § "Success signal"
  (~L169-177) — the literal target this story's Acceptance Criteria restate as verifiable checks.
- `spec-21-2-remove-cf-atlas-db-seeds-from-production-datasets.md` frontmatter `deferred` — the
  `seed_gaps` `seed_root` path-resolution bug (resolves relative to the Kedro member dir instead
  of `REPO_ROOT`); this story's bootstrap AC requires it resolved (or re-verified resolved) since
  21.8 runs the LITERAL `pyforge-atlas-bootstrap` task (all seven pipelines), not the
  21.2-narrowed six-pipeline chain that story's own AC settled for.

## Tasks & Acceptance

**Execution:**
- Pre-flight: confirm Stories 21.3, 21.4, 21.5, 21.6, and 21.7 are `status: done` (check each
  spec's frontmatter or `fleet-picture`) before dispatching this story's implementation.
- Run `pixi run -e pyforge-atlas pyforge-atlas-bootstrap` on a genuinely empty
  `PYFORGE_ATLAS_DATA_ROOT` (a fresh temp dir or clean worktree) with `CF_ATLAS_DB` unset; capture
  the exit code and per-pipeline pass/fail, including `seed_gaps`.
- If `seed_gaps` still fails on the Story 21.2 `seed_root` bug, this story cannot claim the
  bootstrap AC as-is: either an upstream 21.x story already fixed it (re-verify against live code,
  do not assume from this spec's drafting-time snapshot), or this story's own execution fixes the
  narrow `seed_root` path-resolution bug itself (minimal, surgical — that one bug only; Epic 21
  owns no other `seed_gaps` changes). Do not narrow this story's AC to exclude `seed_gaps` the way
  21.2 did — that carve-out was scoped to 21.2's 3-file surface, not a standing exemption.
- Run the inventory metrics CLI's `--live-catalog` mode (Story 21.3's landed flag/shape) against
  the bootstrapped root, and run the existing legacy/Excel-mode path against a comparable fixed
  corpus; diff every `verification-matrix.md` field between the two runs.
- Run `--live-catalog-only` against a deliberately incomplete root (one required dataset missing
  or forced stale) and confirm a loud, non-zero-exit failure.
- Run `pixi run -e pyforge-atlas parity-diff` and `pixi run -e pyforge-atlas bsl-metric-check`
  against the fully bootstrapped catalog; confirm both green.
- Extend `src/shared/packages/pyforge-atlas/README.md`'s Operator env block table with every
  variable introduced across 21.3-21.7 (grep each landed story's own Code Map / Design Notes for
  new `credentials.yml` keys and `*_BASE_URL` overrides once merged).
- Record the diff results (fields matched, any residual gaps with citation) in this story's own
  Verification / Auto Run Result section when dispatched.

**Acceptance Criteria:**
- Given a fresh clone with `PYFORGE_ATLAS_DATA_ROOT` pointed at an empty directory and no
  `CF_ATLAS_DB` set, when `pixi run -e pyforge-atlas pyforge-atlas-bootstrap` runs, then it exits
  0 across all seven pipelines named in the task's `cmd` — no pipeline-specific carve-out.
- Given the bootstrapped data root, when the inventory metrics CLI runs with `--live-catalog`,
  then every field in `verification-matrix.md`'s table matches the legacy-mode value on the same
  fixed corpus.
- Given `--live-catalog-only` with a deliberately missing/stale required dataset, when the CLI
  runs, then it fails loudly (non-zero exit) — never a silent pass.
- Given the fully bootstrapped catalog, when `pixi run -e pyforge-atlas parity-diff` and
  `pixi run -e pyforge-atlas bsl-metric-check` run, then both are green.
- Given the README's Operator env block after this story, when read by a human, then every
  environment variable touched by the full Epic 21 bootstrap + `--live-catalog` chain (not only
  Story 21.1's CAP-1 subset) is listed with Required/Effect columns.
- Given `identity_export_parquet` (Story 21.6's output), when its `lookup_assoc` /
  `from_inventory` / `from_board_only` parity is checked against the fixed fixture corpus (per
  `identity-contract.md`), then it matches — restated here as this story's cross-CAP proof point,
  not a re-derivation of Story 21.6's own acceptance criteria.

## Spec Change Log

- 2026-08-30: Initial draft. Epic 21's own closing verification story — adds no new data sources
  or pipelines; proves Stories 21.1-21.7 hold together end-to-end per `SPEC.md`'s Success signal.
  Written ahead of Stories 21.3-21.7's implementation (only 21.1 and 21.2 are `status: done` as of
  this drafting) — see Design Notes for the resulting dispatch-timing consequence.

## Design Notes

**This story cannot be dispatched yet.** As of this spec's drafting (2026-08-30), only Stories
21.1 and 21.2 are `status: done`; Stories 21.3 (`--live-catalog` contract), 21.4/21.5 (Tier 1/2
catalog sources), 21.6 (identity join), and 21.7 (quartet thin-out) are not yet implemented. This
spec describes the FINAL state those five stories collectively produce — the
`verification-matrix.md` field list, the `--live-catalog` / `--live-catalog-only` CLI contract,
and the identity-export parity checks all reference capabilities that do not exist in the
codebase today (confirmed: zero `live-catalog` / `live_catalog` hits anywhere under `src/` or
`scripts/` as of this drafting). Do not dispatch `bmad-build` / `bmad-loop` against this spec
until `stories.yaml`'s 21.3-21.7 rows are all `status: done` — dispatching early would either
stall immediately (the CLI flag this story verifies does not exist to run) or produce a
false-green verification against a partial catalog, exactly the failure mode Story 21.2's own
Spec Change Log records correcting for its dormant-trigger-node gap (10 of 12 new catalog entries
built and unit-tested but never reachable from a real `kedro run`).

**`seed_gaps`'s pre-existing bug is this story's problem to close out, not carve around.** Story
21.2's `deferred` entry documents a `seed_root` path-resolution bug in the `seed_gaps` pipeline
that predates 21.2 and was explicitly out of that story's 3-file scope; Story 21.1's own
Verification section likewise narrowed its bootstrap-chain AC to exclude `seed_gaps`. This story
runs the LITERAL `pyforge-atlas-bootstrap` pixi task (all seven pipelines, `seed_gaps` included,
per its exact `cmd` in `pixi.toml`) — by the time 21.8 dispatches, either an earlier story has
fixed the bug as a side effect of touching that pipeline, or this story's own execution must fix
the narrow `seed_root` resolution bug itself before it can honestly claim the bootstrap AC.
Re-verify the bug's live status at dispatch time rather than trusting this spec's drafting-time
snapshot either way.

**Why `status: ready-for-dev` despite the hard dependency.** The spec itself — Intent,
Boundaries, I/O matrix, Code Map, Tasks & Acceptance — is complete and actionable; what is
missing is not spec clarity but upstream code that has not landed yet. That is a
dispatch-ordering constraint, not an ambiguity in what this story must prove, and it is recorded
both here and in the `Block If` boundary above. `epic-21-context.md` § Cross-Story Dependencies
already documents the roughly-linear 21.1 → 21.2 → ... → 21.8 chain this story's dispatch order
follows; whoever picks this story up is responsible for checking `stories.yaml` / `fleet-picture`
for 21.3-21.7's live status first, the same way any dependent story in this file
(21.9/21.10/22.x/23.x, which carry explicit `depends_on` rows) would be checked.

## Verification

**Commands (run once Stories 21.3-21.7 are done and this story dispatches):**
- `pixi run -e pyforge-atlas pyforge-atlas-bootstrap` — expected: exit 0, all seven pipelines
  complete, on an empty `PYFORGE_ATLAS_DATA_ROOT` with no `CF_ATLAS_DB` set.
- Inventory metrics CLI with `--live-catalog <bootstrapped-root>` (flag name/shape per Story
  21.3's landed contract) — expected: every `verification-matrix.md` field matches legacy-mode
  output on the fixed corpus.
- Inventory metrics CLI with `--live-catalog-only` against a deliberately incomplete root —
  expected: loud, non-zero-exit failure.
- `pixi run -e pyforge-atlas parity-diff` — expected: green.
- `pixi run -e pyforge-atlas bsl-metric-check` — expected: green.
- Manual read-through of `src/shared/packages/pyforge-atlas/README.md`'s Operator env block table
  against a fresh grep of every `credentials:` / `${env_or:...}` reference added by 21.3-21.7's
  catalog entries — expected: complete coverage, no missing variable.
