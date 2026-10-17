---
title: '32.1: The DAG export builds in CI, and a failed build fails its task'
type: 'fix'
created: '2026-10-17'
status: 'in-review'
baseline_revision: '17670a0580df2e84d19f9b5ca679f395818951a3'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-30-1-the-dag-export-reaches-pages-as-a-workflow-artifact.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - .github/workflows/kedro-viz-publish.yml
  - src/shared/packages/pyforge-atlas/tools/bootstrap.py
  - src/shared/packages/pyforge-atlas/conf/base/catalog.yml
  - pixi.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `kedro-viz-publish.yml`'s `publish` job cannot build the DAG export on a runner, and `viz-build` reports
the failed build as a success. Line numbers below are at `17670a0580`.

- **What happened.** The operator lifted every CI pause on 2026-10-16 (PR #2247), which re-enabled the workflow after
  two months disabled by hand. Story 30.1 names the step after that: dispatch the workflow once and confirm the
  `kedro-viz-export` artifact. Run `39002722593` (`workflow_dispatch`, `990d796c7f`, 2026-10-17T04:28Z) failed in its
  `publish` job and uploaded only `vizro-static-export` (the `vizro` job passed). Its log, in the step `Build +
  normalize + stage the real DAG's kedro-viz export`:
  - `ERROR: Failed to build/deploy Kedro-Viz : "Unable to find credentials 'gitlab_token': check your data catalog
    and credentials configuration. ..."`
  - then `RuntimeError: normalize_viz_build: .../src/shared/packages/pyforge-atlas/build does not exist -- run the
    viz-build pixi task first.` and `Process completed with exit code 1`.
- **Cause 1: the workflow carries its own stub, and it drifted.** The step `Materialize stub credentials for offline
  catalog resolution` (`kedro-viz-publish.yml:122`-`:141`, written 2026-08-09 in `c08a0a4a7a`) writes
  `conf/local/credentials.yml` with two keys, `bigquery_adc` and `github_token`, as fake auth pairs. Its comment
  (`:103`-`:121`) says two entries declare `credentials:` and that the shapes mirror
  `tests/catalog/conftest.py::STUB_CREDENTIALS`; that file moved to `tests/unit/catalog/conftest.py` on 2026-09-07
  (`aec4c74f6e`). `conf/base/catalog.yml` now names eight keys on ten entries: `github_token` (three entries, :573,
  :1234, :1246), `bigquery_adc` (:249), `gitlab_token` (:586), `codeberg_token` (:595), `npm_token` (:608),
  `crates_token` (:641), `rubygems_token` (:650) and `nuget_token` (:667). Story 27.2 (`99af53f690`, 2026-10-04) added
  the last six while the workflow was disabled.
- **Cause 2: a second source.** `tools/bootstrap.py`'s `_CREDENTIALS_STUB` (:53-:70) lists all eight keys as `{}`;
  Story 27.2 updated it and not the workflow. `_ensure_credentials_stub` (:92-:98) writes it only when the file is
  absent or empty. Its docstring and its printed message still say two keys.
- **Cause 3: `kedro viz build` exits 0 when it fails.** kedro-viz 12.5.0's `create_shareableviz_process`
  (`kedro_viz/launchers/cli/utils.py`) catches every exception, prints `ERROR: Failed to build/deploy Kedro-Viz :
  <exc>` at :97-:98 and returns normally. `viz-build` (`pixi.toml:2858`-`:2862`, `rm -rf build && kedro viz build`)
  therefore exits 0 on a failed build, and `viz-publish-stage`'s `depends-on = ["viz-build"]` (:2870), whose
  description says it exists "so a failed build never stages stale/partial output", never stops anything. The failure
  surfaces one command later, in `normalize_viz_build.py:158`, with a message that names the wrong step.
- **Cause 4, found by the independent review (2026-10-17, of `f52936ff75`): the flag step runs in an env without
  `pyforge.atlas`.** The `publish` job's step `Resolve viz export artifact flag` (`kedro-viz-publish.yml:130`-`:134`
  at `f52936ff75`, unchanged since Story 30.1) runs `print_viz_export_flag.py` in `-e pyforge-guild`. That script
  imports `pyforge.atlas.viz_export_artifact` (line 6), and `pyforge-guild` deliberately does not carry
  `pyforge-atlas`. Measured by the reviewer from a clone root: `ModuleNotFoundError: No module named 'pyforge.atlas'`,
  exit 1, in the guild env; `enabled=true`, exit 0, in the atlas env. Under `bash -e` the job would fail at that step
  once the build passes, before the upload. No run had reached the step (the workflow was disabled until 2026-10-16,
  and run `39002722593` died earlier), and no test pinned its environment. The `vizro` job's flag step already runs
  in `-e pyforge-atlas`.

**Measured on a scratch copy of `17670a0580`** (`git archive HEAD`, its own `pyforge-atlas` env, kedro-viz 12.5.0,
kedro 1.6.0, kedro-datasets 9.6.0), `pixi run --frozen -e pyforge-atlas viz-build` from the copy's root, each with only
`conf/local/credentials.yml` changed:

| `conf/local/credentials.yml` | Exit | `build/` | First error |
|---|---|---|---|
| absent | 0 | not written | `Unable to find credentials 'bigquery_adc'` |
| the workflow's two-key stub (`bigquery_adc`, `github_token` as pairs) | 0 | not written | `Unable to find credentials 'gitlab_token'` (the CI run's error) |
| `tools/bootstrap.py`'s stub (eight keys, each `{}`) | 0 | 293 files, 12 MB, in 8.7 s | none: `Success! Kedro-Viz build files have been added` |
| all eight keys as auth pairs | 0 | written, in 8.3 s | none |

- **The shape.** `{}` works for every key, and so does a pair. The workflow comment's claim that the
  `APIDataset`-family entries need an auth pair does not hold: viz only introspects the DAG and loads through no
  credential. This story writes `{}` for every key, which is `tools/bootstrap.py`'s shape and the one `kedro run`
  already uses on a fresh clone. No stub value appears in the build output (`grep -rl stub- build/` is empty for the
  pair run).
- **The operator's local file.** The operator's `conf/local/credentials.yml` in the primary checkout carries the same
  two top-level keys, `bigquery_adc` and `github_token` (key names read; its values were not read or copied). Kedro
  fails on the missing key name before it reads any value, so a local `viz-build` or `pyforge-atlas-bootstrap` there
  fails the same way as the two-key row above. Copying the file into the scratch tree was refused by the session's
  permission classifier as credential handling; the key-name read is the measurement.
- **What a real build writes.** The kedro-viz deployer (`kedro_viz/integrations/deployment/base_deployer.py`,
  `deploy`) writes the API responses first (`api/main`, `api/nodes/*`, `api/pipelines/*`), then the static files
  (`index.html`), then `api/deploy-viz-metadata` last. A complete build has all three of `index.html`, `api/main` and
  `api/deploy-viz-metadata`; a failed one, after `rm -rf build`, has none.

**Approach:**
1. **One source.** `tools/bootstrap.py` holds `CREDENTIAL_KEYS`, the one list of the keys the catalog names, and renders
   the stub from it (every key `{}`). A `--credentials-only` flag writes only the stub, through the same
   `_ensure_credentials_stub` guard (absent or empty file only), and makes no store directory. The workflow's stub step
   runs `pixi run --frozen -e pyforge-atlas python src/shared/packages/pyforge-atlas/tools/bootstrap.py
   --credentials-only` and carries no key list of its own; its comment is corrected (every key the catalog names, with
   no count that can go stale; the moved conftest; the measured shape). The step keeps its name and its place before `viz-publish-stage`. The stale docstring and
   printed message in `bootstrap.py` are corrected in the same edit.
2. **A test keeps the stub complete.** A new `tests/unit/test_viz_publish_build.py` reads every `credentials:` value in
   every catalog file under `conf/base` (`**/catalog*.y*ml`, the files Kedro's default catalog patterns load; a YAML
   walk, cross-checked against a raw-text scan so the walk cannot go blind) and fails when `CREDENTIAL_KEYS` lacks one
   or names one the catalog does not. It also fails when any string in the workflow (a `run:`, an `env:`, a `with:`,
   a key) names a catalog credential key or `credentials.yml`.
3. **`viz-build` fails when the build fails.** A new `tools/viz_build_check.py` exits 1 naming each of `api/main`,
   `index.html` and `api/deploy-viz-metadata` missing under `build/`, and 0 when all three are there. `viz-build`
   becomes `rm -rf build && kedro viz build && python tools/viz_build_check.py`. The test pins that command and the
   checker's verdicts.
4. **Story 30.1's byte pin hands over.** `test_viz_export_artifact.py::test_ac4_kedro_viz_publish_workflow_shape`
   pinned the old stub step's `run:` by sha256 and asserted its two key names (Story 30.1 AC4: the stub step
   "unchanged"). That pin now asserts the step runs `tools/bootstrap.py --credentials-only`; the new test pins the
   source. Every other assertion in that test stays.
5. **The flag step runs in the atlas env** (Cause 4; folded into this story by orchestrator ruling, 2026-10-17, "fold it
   into 32.1. Do not mint 32.2"). The step's `-e pyforge-guild` becomes `-e pyforge-atlas`, the env the job's
   `setup-pixi` already installs; nothing else in the gate changes, and nothing in the job needs `pyforge-guild` any
   more. A test fails when any `pixi run … python …/pyforge-atlas/tools/*.py` step in the workflow names another env.

Ledger key: `32-1-the-dag-export-builds-in-ci-and-a-failed-build-fails-its-task`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-62** (FR-70; the DAG export reaches Pages as a workflow artifact): its intent
  "materializes the stub `conf/local/credentials.yml` as today" still holds, and its success clause "the
  stub-credentials step unchanged" is the clause this fix moves: the step stays, named and placed as before, and its
  content now comes from `tools/bootstrap.py`. Recorded as a decision on the Spec's memlog; `SPEC.md` is not
  hand-edited, and the next `bmad-spec` re-derive of CAP-62 takes the wording. A `fix`, so no CAP is minted.
- **AD-11** (gates are never weakened; no credential enters the workflow): the stub carries no value at all, and no
  test loses an assertion it had except the byte pin the new test replaces with a stronger one.
- **AD-21** (every static surface atlas publishes reaches Pages as a workflow artifact): unchanged; this story makes the
  producer able to produce.
- **No flag.** `spec-feature-flag-governance` Q1: a `fix` needs no flag. Like the other atlas fix specs (28.1, 29.1,
  31.1), this spec carries neither a `flag:` block nor a `flag-exempt:` value; the flag rule reads only `type: feature`.
- **Origin.** `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-17 entry (kedro-viz-publish's stub
  credentials drifted); run `39002722593`.

## Acceptance Criteria

- **AC1 — One source.** `tools/bootstrap.py` defines `CREDENTIAL_KEYS` (no duplicates) and renders its stub from it,
  every key `{}`. `python tools/bootstrap.py --credentials-only` writes that stub to `conf/local/credentials.yml` when
  the file is absent or empty, leaves a non-empty file byte-for-byte untouched, creates no store directory, and exits
  0. A bare `python tools/bootstrap.py` behaves as before (store dirs, then the stub).
- **AC2 — The workflow reads it.** In `.github/workflows/kedro-viz-publish.yml`'s `publish` job, the step `Materialize
  stub credentials for offline catalog resolution` runs `tools/bootstrap.py --credentials-only` and comes before the
  `viz-publish-stage` step. No string in the workflow (any `run:`, `env:`, `with:` value or key) names a credential
  key the catalog names, and none contains `credentials.yml`. The comment above the step says every key
  `conf/base/catalog.yml` names (no count), `tests/unit/catalog/conftest.py` is no longer cited for shapes, and the
  measured shape is stated. *(Amended 2026-10-17 after review: was "no `run:`" and "names eight keys".)*
- **AC3 — Complete, and kept so.** `tests/unit/test_viz_publish_build.py` asserts `set(CREDENTIAL_KEYS)` equals the set
  of `credentials:` values in every `conf/base/**/catalog*.y*ml`, read two ways that must agree. Mutations, each on a
  scratch edit and undone: dropping one key from `CREDENTIAL_KEYS` fails the test naming that key; a second catalog
  file naming a new key fails it; restoring a key list (the old heredoc) in the workflow's stub step, or putting one
  in a step's `env:`, fails the workflow test.
- **AC4 — `viz-build` fails when the build fails.** `tools/viz_build_check.py --build-dir <dir>` exits 1 naming each
  missing file of `api/main`, `index.html`, `api/deploy-viz-metadata`, and exits 0 when all three exist. `pixi.toml`'s
  `viz-build` `cmd` is `rm -rf build && kedro viz build && python tools/viz_build_check.py`, with `cwd` unchanged. The
  test pins the command and the verdicts, and reads kedro-viz's own deployer for the three files (`_METADATA_PATH`,
  `_HTML_DIR/index.html`, the `api/main` write, metadata written last); a plain pin of the tuple stands beside it.
  Mutations: dropping the check from the `cmd` fails the pin; a checker that always returns 0 fails the verdict tests;
  a metadata path the deployer does not write fails the deployer test.
- **AC5 — The real build.** On a scratch copy of this tree with no `conf/local/credentials.yml`, `python
  src/shared/packages/pyforge-atlas/tools/bootstrap.py --credentials-only` then `pixi run --frozen -e pyforge-atlas
  viz-build` exits 0 and writes the build; `pixi run --frozen -e pyforge-atlas viz-publish-stage` exits 0 and fills
  `docs/dashboard/kedro-viz/`. With the old two-key stub in place, `viz-build` exits 1 and the checker names the
  missing files after kedro-viz's `Unable to find credentials 'gitlab_token'` line.
- **AC6 — Nothing else moves.** The `vizro` job, the upload step, the artifact's name (`kedro-viz-export`) and
  retention (90), the flag gate (`viz_export_flag`) byte-identical except its environment, `on.push.paths`, the
  `changes` job's pathspecs and every CI-pause `if:` fragment are byte-identical to `17670a0580`. The flag step runs
  `print_viz_export_flag.py` in `-e pyforge-atlas` (was `-e pyforge-guild`, which cannot import `pyforge.atlas`), and
  a test fails when any `pixi run … python …/pyforge-atlas/tools/*.py` step in the workflow names another env
  (mutation: `pyforge-guild` back on the flag step). A scratch run of the step in `-e pyforge-atlas` prints
  `enabled=true`. `pixi run --frozen -e pyforge-guild python scripts/ci_surface_gates.py --check` exits 0.
  `test_viz_export_artifact.py` changes only in AC4's stub pin. *(Amended 2026-10-17 after review: was "the flag gate
  byte-identical".)*
- **AC7 — Gates.** `pixi run --frozen -e pyforge-atlas pyforge-atlas-test`, `kedro-test` and `kedro-catalog-check`
  exit 0; the atlas coverage gate (`scripts/coverage_gates_ci.py --suites unit`, atlas's env) exits 0;
  `pixi run --frozen -e pyforge-guild lint-types` exits 0; steward's `tests/meta/test_station_tests_trigger_map.py`
  passes with every path the new test reads (`pyforge-station-tests.yml`'s `atlas_paths` already carries
  `.github/workflows` and `src/shared/packages`; `pixi.toml` is shared surface). The planning detectors and
  `detectors-ci` exit 0.
- **AC8 — Reconciled.** Every Spec `spec-surface-check` names gets a memlog surface-reconcile entry naming its paths and
  this story and is stamped scoped, one `--spec` each; `spec-surface-check` then exits 0, re-run after the last edit.

## Boundaries & Constraints

**Always:**
- The stub carries key names only, every value `{}`. The writer never overwrites a file that holds anything.
- One list: `CREDENTIAL_KEYS` in `tools/bootstrap.py`. The workflow and the bootstrap task both write through it.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never write a credential, token, secret or fake auth pair into the workflow or the stub.
- Never change the `vizro` job, the upload step, the artifact's name or retention, the flag gate (beyond its step's
  environment, AC6), `on.push.paths`, the `changes` job or a CI-pause `if:` fragment.
- Never edit an operator's `conf/local/credentials.yml`; the measurement reads key names only.
- Never hand-edit `SPEC.md` or `sprint-status-ledger.yaml`.
- Never import `pyforge.atlas` internals, Dagster or `kedro-mcp` from the tools; both stay stdlib-only (AD-1).

**Deviation recorded from the orchestrator's design:**
- The guard is `_ensure_credentials_stub`'s (absent **or zero-byte** file), not the old workflow step's
  `[ -e "$CRED" ]` (absent only). One function serves both writers, and a zero-byte file holds no value to lose; Kedro
  fails on it exactly as on an absent one.
- The optional repair (bootstrap adding missing keys to an existing, non-empty `credentials.yml`) is not done; it is
  residual risk below. Editing an operator's credential file in place is the riskier path, and the build now fails
  loudly with the remedy instead of silently.

**Co-governor memlogs the implementer appends** (read from `scripts/.spec-surface-baseline.json` at `17670a0580`; each
was reconciled and stamped scoped, one `--spec` each):
- `.github/workflows/kedro-viz-publish.yml`: `pyforge-atlas/spec-pyforge-atlas`.
- `tools/bootstrap.py`, `tests/unit/test_viz_export_artifact.py` and the two new atlas files:
  `pyforge-atlas/spec-pyforge-atlas` and `pyforge-steward/spec-pyforge-unifying-strategy`.
- `pixi.toml`: `pyforge-doctor/spec-pixi-candidate-currency`, `pyforge-herald/spec-deck-family-currency`,
  `pyforge-herald/spec-deck-family-lockstep`, `pyforge-herald/spec-pyforge-pages`, `pyforge-marshal/spec-pyforge-core`,
  `pyforge-marshal/spec-pyforge-marshal`, `pyforge-steward/spec-pyforge-steward` and
  `pyforge-steward/spec-pyforge-unifying-strategy`.
- `docs/how-to/pixi-tasks.md` and `docs/map.yaml` (regenerated by `docs-pixi-tasks`): `pyforge-doctor/spec-pyforge-doctor`.
- `spec-surface-check` names one governor per changed path per run, so the full list comes from the baseline, not from
  one run of the detector. Every co-governor entry cites `pyforge-atlas:CAP-62`, qualified: a bare `CAP-62` in another
  project's memlog reads as that project's own id (`ad_citation_check`).

**Residual risk:**
- **Operators' existing local files.** A `conf/local/credentials.yml` written before 2026-10-04 lacks six keys (the
  operator's does). `pyforge-atlas-bootstrap` and `viz-build` still fail there; `viz-build` now exits 1 with the
  checker's message, which names the remedy: add each missing key as `<key>: {}`. Not auto-repaired (see the
  deviation). **Operator step:** in the primary checkout's `conf/local/credentials.yml`, add `<key>: {}` for each key
  `viz-build` names (kedro-viz's `Unable to find credentials '<key>'` line; at this mint the six are `gitlab_token`,
  `codeberg_token`, `npm_token`, `crates_token`, `rubygems_token` and `nuget_token`). Only the operator edits that file;
  the orchestrator captures this at session close.
- **The producer re-runs only on a DAG change.** `on.push.paths` does not carry `tools/bootstrap.py`,
  `tools/viz_build_check.py` or `pixi.toml`, so a change there is proven by this test on the PR and by the next
  dispatched or DAG-triggered run, not by a run of its own. Adding paths would change Story 30.1's pinned trigger; left
  as it is.
- **A later kedro-viz that writes different files** fails the checker on a good build, loudly, naming the file; the
  fix is the `REQUIRED_OUTPUTS` tuple, read against the deployer.
- **The flag.** The upload still depends on `pyforge.atlas.viz_export_artifact` resolving on in CI (dev, the default
  when `PYFORGE_ENVIRONMENT` is unset). Its step now runs in the atlas env, where a scratch run prints `enabled=true`;
  run `39002722593` uploaded `vizro-static-export` through the same kind of gate in that env.

## I/O & Edge-Case Matrix

| Situation | Today (`17670a0580`) | After |
|---|---|---|
| Runner, no `conf/local/credentials.yml` | stub with 2 of 8 keys; `viz-build` exit 0, no build; job fails at normalize | stub with 8 of 8; build, stage, upload |
| A non-empty `credentials.yml` already present | left untouched | left untouched |
| A zero-byte `credentials.yml` present | workflow: left untouched (build fails); bootstrap: filled | filled, by both writers |
| `credentials.yml` lacks a catalog key | `viz-build` exit 0, no build | `viz-build` exit 1, checker names the missing files and the remedy |
| The catalog gains a credential key | nothing notices until a run fails | `test_viz_publish_build.py` fails naming the key |
| The workflow gains a key list again (in a `run:`, `env:` or `with:`) | nothing notices | `test_viz_publish_build.py` fails |
| A second `conf/base/catalog*.yml` names a new key | nothing notices | `test_viz_publish_build.py` fails naming the key |
| The flag step runs | `-e pyforge-guild`: `ModuleNotFoundError`, exit 1, no upload | `-e pyforge-atlas`: `enabled=true`, upload |
| An atlas tool step names another env | nothing notices | `test_viz_publish_build.py` fails naming the step |
| `kedro viz build` succeeds | exit 0 | exit 0, checker prints the three files |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-62 (FR-70), a `fix`, so no CAP is minted and no `SPEC.md` text
  changes by hand.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-17 entry (kedro-viz-publish's stub credentials
  drifted).
- Epic: Epic 32 (new). Epic 30, which shipped the producer, is done, and Epic 31 is the foundry-full type gate. `epic-32`
  and `epic-32-retrospective` are minted with it.
- Ledger key: `32-1-the-dag-export-builds-in-ci-and-a-failed-build-fails-its-task`.
- Ledger status at mint: `backlog` (the orchestrator promotes it at landing).
- Deps: none. Cross-station, prose: steward's `DW-steward-102-4-1` (Story 102.4 AC7, the `present` record) waits on
  the first `kedro-viz-export` this fix makes possible; no blocked row.
- Surface: `marshal-policy.toml` `[epic_surfaces]."32"`, added with this mint.
- Minted 2026-10-17 in one chain commit with its implementation (the brief's builder session).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`).

**Run before the push (not dispatch gates):**
- AC1-AC4: `pixi run --frozen -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/unit/test_viz_publish_build.py src/shared/packages/pyforge-atlas/tests/unit/test_viz_export_artifact.py -q -p no:cacheprovider` — expected: pass.
- AC1/AC3/AC4/AC6 mutations, each on a scratch edit and undone: drop `"nuget_token"` from `CREDENTIAL_KEYS`; add a `conf/base/catalog_extra.yml` naming `extra_token`; restore the old heredoc in the stub step; put a key list in a step's `env:`; drop `&& python tools/viz_build_check.py` from `viz-build`; make `viz_build_check.main` return 0; name a metadata file the deployer does not write; make `--credentials-only` also call `_ensure_store_dirs`; put `-e pyforge-guild` back on the flag step — expected: the named test fails each time.
- AC6, the flag step, from the root of a scratch copy: `pixi run --frozen -e pyforge-atlas python src/shared/packages/pyforge-atlas/tools/print_viz_export_flag.py` — expected: `enabled=true`, exit 0.
- AC5, on `git archive` of this tree into a scratch dir with no `conf/local/credentials.yml`: `pixi run --frozen -e pyforge-atlas python src/shared/packages/pyforge-atlas/tools/bootstrap.py --credentials-only`, `pixi run --frozen -e pyforge-atlas viz-build`, `pixi run --frozen -e pyforge-atlas viz-publish-stage` — expected: exit 0 each, `docs/dashboard/kedro-viz/index.html` present. With the old two-key stub: `viz-build` — expected: exit 1.
- AC6: `pixi run --frozen -e pyforge-guild python scripts/ci_surface_gates.py --check` — expected: exit 0.
- AC7: `pixi run --frozen -e pyforge-atlas pyforge-atlas-test`; `COVERAGE_GATES_STATIONS=atlas pixi run --frozen -e pyforge-atlas python scripts/coverage_gates_ci.py --suites unit --paths-file <changed paths>`; `pixi run --frozen -e pyforge-guild lint-types`; `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q -p no:cacheprovider` — expected: exit 0 each.
- Planning: `chain-completeness-check`, `dream-chain-check`, `dreams-hygiene-check`, `deferred-work-check`, `ledger-regression-check`, `story-status-check`, `flag-gate-check`, `chain-currency-sweep-check`, `detectors-ci` (each `pixi run --frozen -e pyforge-guild <task>`) — expected: exit 0.
- AC8: `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and scoped stamps.

**Operator, after landing (an outward act a session never performs):**
- `gh workflow run kedro-viz-publish.yml --repo rxm7706/local-recipes`, then confirm the run's `publish` job passes
  and the run lists the `kedro-viz-export` artifact (`gh api repos/rxm7706/local-recipes/actions/runs/<id>/artifacts`).
  That run is the producer half of steward's `DW-steward-102-4-1` (Story 102.4 AC7): a `pages.yml` run after it records
  `KEDRO_VIZ_EXPORT=present`.
- In the primary checkout's own `conf/local/credentials.yml`, add `<key>: {}` for each key `viz-build` names (Residual
  risk, the operator step); until then a local `viz-build` or `pyforge-atlas-bootstrap` there exits 1 naming them.

## Spec Change Log

- 2026-10-17: minted from the Dream entry of that date and run `39002722593`; `type: fix`, no flag, no CAP; bound to
  `spec-pyforge-atlas` CAP-62. The credential shape (`{}` against an auth pair) was measured by real builds on a
  scratch copy before the design was fixed.
- 2026-10-17 (implementation): landed as specced. Four recorded choices:
  - AC5's scratch copy is `git archive` of the staged tree (`git write-tree`), not of `HEAD`: the builder session
    cannot commit, and `HEAD` is the baseline. Same mechanism, same isolation; the baseline rows in the Intent are an
    archive of `HEAD`.
  - The scratch `viz-publish-stage` ran with `GIT_DIR` set to this worktree's git dir and `GITHUB_SHA` set to the
    baseline, because a `git archive` copy is not a repository and `viz_manifest.py` reads the commit's date through
    `git show` (the flag is on in `dev`). Read-only; the manifest's three fields came out as AC2 of Story 30.1 says.
  - `pyforge-station-tests.yml` and `on.push.paths` of `kedro-viz-publish.yml` are unchanged: `atlas_paths` already
    carries `.github/workflows` and `src/shared/packages`, `pixi.toml` is shared surface, and steward's trigger-map
    meta-test passes with the new test's reads (AC7).
  - The atlas coverage gate measured no touched module: `tools/` sits outside `src/pyforge/atlas`, the package the gate
    maps changed files to. Measured by hand instead (`pytest tests/unit/test_viz_publish_build.py
    --cov=src/shared/packages/pyforge-atlas/tools --cov-branch`): `viz_build_check.py` 92% and `bootstrap.py` 93%. The
    misses are the two `__main__` lines (the script test runs `viz_build_check.py` in a subprocess) and the
    stores-already-present path (`_ensure_store_dirs` and its message in `main`), which predates this story.
- 2026-10-17 (implementation, `detectors-ci`): two findings on the first run, both this story's, both fixed before the
  stamps were final. `tea_playwright_check` found Story 32.1 missing from atlas's Story Coverage Matrix, so
  `planning-artifacts/test-architecture.md` is regenerated with `_bmad/scripts/bmad_tea_playwright.py --project
  pyforge-atlas` (its inventory also catches up on the test files Stories 30.x and 31.1 added). `ad_citation_check`
  found the three herald co-governor memlog lines citing a bare `CAP-62`; those unlanded lines, in all nine
  co-governor memlogs, now cite `pyforge-atlas:CAP-62`.
- 2026-10-17 (review fixes, on `f52936ff75`): the independent review failed the story (2 should-fix, 6 nits; see the
  Review Triage Log). **Deviation from the spec as minted:** AC6 said the flag gate stays byte-identical; its step's
  environment now moves from `-e pyforge-guild` to `-e pyforge-atlas` (Cause 4, Approach 5), by orchestrator ruling
  ("fold it into 32.1. Do not mint 32.2"): the story's goal is that the next dispatch uploads `kedro-viz-export`, and
  the flag step blocked that. AC6 now reads "byte-identical except its environment". Nothing else in the gate moves:
  the step's `id`, its script, the `>> "$GITHUB_OUTPUT"` and the upload step's `if:` are as they were, and the job's
  `setup-pixi` already installs only `pyforge-atlas`, so no step in the job needs `pyforge-guild` any more. AC2, AC3 and
  AC4 are amended for the nits (every string of the workflow, every catalog file, the deployer binding, no key counts
  in prose). The Dream entry and the Epic 32 / Story 32.1 block record the same.

## Review Triage Log

### 2026-10-17 — Independent review of `f52936ff75` (FAIL)
- verdicts: 8 findings — should-fix 2, nit 6; all 8 accepted and fixed in the follow-up commit, none deferred.
- findings:
  - `[should-fix]` `[fixed]` F1 — the flag step ran `print_viz_export_flag.py` in `-e pyforge-guild`
    (`ModuleNotFoundError`, exit 1), so the upload would never run. Now `-e pyforge-atlas`; new test
    `test_every_atlas_tool_step_runs_in_the_atlas_env`. Folded into 32.1 by orchestrator ruling; AC6 amended.
  - `[should-fix]` `[fixed]` F2 — AC1's "creates no store directory" was untested (the test listed regular files only).
    The test now lists every path under `tmp_path` and asserts `not (tmp_path / "data").exists()`.
  - `[nit]` `[fixed]` N1 — the key walk read only `catalog.yml`; it now reads every `conf/base/**/catalog*.y*ml`, both
    the YAML walk and the raw scan.
  - `[nit]` `[fixed]` N2 — the no-list guard read only `run:`; it now reads every string key and value of the parsed
    workflow.
  - `[nit]` `[fixed]` N3 — the deployer test compared the tuple with itself. Now `test_required_outputs_pin` (a pin,
    named so) and `test_required_outputs_match_the_kedro_viz_deployer` (kedro-viz's `_METADATA_PATH`,
    `_HTML_DIR/index.html`, the `api/main` write in `save_api_responses_to_fs`, and the order of `deploy()`).
  - `[nit]` `[fixed]` N4 — `bootstrap.py`'s docstring cited `tests/catalog/test_no_inline_io.py`; now
    `tests/unit/catalog/test_no_inline_io.py`.
  - `[nit]` `[fixed]` N5 — "the eight keys" in the workflow comment and `pyforge-atlas-bootstrap`'s description is now
    "every key `conf/base/catalog.yml` names"; `pixi-tasks.md` and `map.yaml` regenerated. (`viz-build`'s
    description never named a count.)
  - `[nit]` `[recorded]` N6 — the operator's own `conf/local/credentials.yml` lacks six keys: Residual risk and the
    operator step now say "add `<key>: {}` for each key `viz-build` names". The orchestrator captures it at session
    close; the file is not touched.

## Auto Run Result

Status: in-review (the orchestrator promotes the spec and the ledger at landing)

Measured on this branch's staged tree (`git archive` into a scratch dir, its own `pyforge-atlas` env, no
`conf/local/credentials.yml`):
- `python src/shared/packages/pyforge-atlas/tools/bootstrap.py --credentials-only` — exit 0; wrote the eight-key stub,
  created no `data/` directory.
- `pixi run --frozen -e pyforge-atlas viz-build` — exit 0 in 8.8 s; `viz-build: build complete`; 293 files, 12 MB
  (`index.html`, `api/main`, `api/deploy-viz-metadata`, `api/nodes/*`, `api/pipelines/*`, `assets/*`).
- `pixi run --frozen -e pyforge-atlas viz-publish-stage` — exit 0 in 9.4 s (it rebuilds through `depends-on`);
  `docs/dashboard/kedro-viz/` holds 294 files with `manifest.json` (`export_commit` the baseline sha,
  `kedro_viz_version` 12.5.0) and `api/deploy-viz-metadata` reading `{"timestamp": "unset", "version": "12.5.0"}`; no
  scratch path in the staged tree.
- With the workflow's old two-key stub: `viz-build` — exit 1 (kedro-viz's `Unable to find credentials 'gitlab_token'`,
  then the checker naming `api/main`, `index.html`, `api/deploy-viz-metadata`); `viz-publish-stage` — exit 1, before
  `normalize_viz_build.py` starts.

Mutations, each on a scratch edit, undone and `cmp`-checked against the saved file:
- `"nuget_token"` dropped from `CREDENTIAL_KEYS` — 1 failed (`test_stub_names_every_catalog_credential_key`, naming
  `['nuget_token']`).
- the `17670a0580` workflow restored — 2 failed (`test_workflow_writes_the_stub_through_bootstrap_before_the_build`,
  `test_workflow_carries_no_credentials_list_of_its_own`, naming `bigquery_adc` and `github_token`).
- one extra step appending `gitlab_token: {}` to the file — 1 failed (`test_workflow_carries_no_credentials_list_of_its_own`).
- `&& python tools/viz_build_check.py` dropped from `viz-build` — 1 failed (`test_viz_build_task_checks_its_output_after_the_build`).
- `viz_build_check.main` returning 0 on a missing file — 6 failed (every failure-verdict test, the script-exit test included).

Review fixes, measured on the revised staged tree (`git archive` of `git write-tree` into a fresh scratch dir, its own
`pyforge-atlas` env, no `conf/local/credentials.yml`):
- `bootstrap.py --credentials-only` — exit 0; `conf/local/credentials.yml` written, no `data/` directory.
- `viz-build` — exit 0 in 11.8 s (the atlas suite ran alongside), 293 files; `viz-publish-stage` — exit 0 in 9.1 s,
  294 files in `docs/dashboard/kedro-viz/`, `manifest.json` with `export_commit` `f52936ff75…`.
- The flag step's command from the copy's root: `-e pyforge-atlas` — `enabled=true`, exit 0; `-e pyforge-guild` —
  `ModuleNotFoundError: No module named 'pyforge.atlas'`, exit 1.

Review-fix mutations, each on a scratch edit, undone and `cmp`-checked:
- `-e pyforge-guild` back on the flag step — 1 failed (`test_every_atlas_tool_step_runs_in_the_atlas_env`).
- `--credentials-only` also calling `_ensure_store_dirs(_resolve_data_root())` — 1 failed
  (`test_credentials_only_writes_the_stub_and_nothing_else`).
- a `conf/base/catalog_extra.yml` naming `credentials: extra_token` — 1 failed (`test_stub_names_every_catalog_credential_key`).
- a step whose `env:` carries `STUB: "gitlab_token: {}"` — 1 failed (`test_workflow_carries_no_credentials_list_of_its_own`).
- `REQUIRED_OUTPUTS` naming `api/viz-metadata` — 3 failed (the pin, the deployer test, one partial-build case).
- `"nuget_token"` dropped again, after the glob change — 1 failed (`test_stub_names_every_catalog_credential_key`).
