---
title: One flag flips three surfaces without a redeploy
type: feature
created: '2026-08-25'
status: done
shipped_ref: '61b31b3f29c978ffe2492f51923f7ab4e8ed6197'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Flag behaviour is not yet evaluated in-process from one JSON tree, so Django, MCP, and CLI cannot observe the same flip without a Deployment rollout (canopy:FR-34, canopy:AD-11).

**Approach:** Ship one flagd-schema JSON tree at `src/platform/config/flags.json`. The Helm ConfigMap is built from that file and mounted read-only. The OpenFeature flagd FILE provider (0.5.0) watches/polls the mount in-process. Django, MCP, and the steward CLI evaluate those same bytes with no egress.

## Acceptance Criteria

- Given one JSON tree (ConfigMap from `src/platform/config/flags.json`), when a flag value changes on disk, then Django, MCP, and CLI all observe it with no egress.
- The in-process FILE provider watches the mount — no Deployment rollout, no Reloader, no flagd sidecar.
- Two trees is a review-blocking finding (tests fail).
- CLI uses the same bytes (host fetch or local-dev file).
- Platform CI pytest.

## Boundaries & Constraints

**Always:** flagd JSON schema (`flags` object). `FlagdProvider(resolver_type=ResolverType.FILE, offline_flag_source_path=…)`. Polling is 5s and unconfigurable. In-cluster path `/etc/pyforge/flags.json`. Physical spec path under `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/`. `BMAD_ACTIVE_PROJECT=pyforge-steward`.

**Block If:** Reloader, flagd daemon, or any flags sidecar (parent canopy:AD-14). A second JSON tree. Loosening `openfeature-provider-flagd` off `>=0.5.0,<0.5.1`. Recipe authoring. Story 27.x or 12-7.

**Never:** `import pyforge` under `src/platform/`. WASM/`wasmtime`. Per-surface homemade flag formats. Env promotion overlays (Deferred).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| One tree | Repo + rendered ConfigMap | Exactly one flags.json tree; ConfigMap bytes parse equal to the file | Fail if two files/trees |
| Three surfaces | Same FILE provider path | Django, MCP `get_flag`, `steward flags get` return the same boolean | Mismatch fails the test |
| No egress | Eval with HTTP/socket blocked | Evaluation still returns the file value | Any network during eval fails |
| Live file change | Rewrite flags.json; no process restart | New variant observed within FILE poll (~5s) | Timeout fails the test |
| Chart | `helm template` | ConfigMap + read-only mount + FLAGD_* env; no Reloader/flagd sidecar | Review-blocking |
| CLI local-dev | No host URL | Reads `src/platform/config/flags.json` | Missing file is a named failure |
| CLI host | Authenticated fetch | Evaluates the fetched bytes, not a second tree | Unauthenticated fetch is refused |
| Migrate Job | No flags volume | Django boots; FILE configure skipped if file absent | Must not fail migrate |

</intent-contract>

## Code Map

- `src/platform/config/flags.json` -- the only flag tree (flagd schema)
- `src/shared/packages/django-pyforge/src/django_pyforge/flags.py` -- FILE provider, eval, Django views, MCP app, CLI (`python -m django_pyforge.flags`)
- `src/platform/deploy/charts/platform/templates/flags-configmap.yaml` -- ConfigMap from `--set-file flags.tree=`
- `src/platform/deploy/charts/platform/templates/{platform,worker}-deployment.yaml` -- read-only `/etc/pyforge` mount
- `src/platform/deploy/charts/platform/templates/_helpers.tpl` -- FLAGD env + volume helpers
- `src/platform/tests/test_openfeature_file_flags.py` -- one tree, three surfaces, no egress, watch/poll, chart
- `src/platform/tests/test_chart_invariants.py` -- ConfigMap is a vanilla kind; `_helm` injects the one tree
- `pixi.toml` `[feature.platform-ci-test.pypi-dependencies]` -- OpenFeature 0.5.0 pin for Platform CI

## Tasks & Acceptance

**Execution:**
- One flags.json; Helm ConfigMap + mount + env
- FILE provider shared by Django, MCP, CLI
- Tests as in Verification

**Acceptance Criteria:**
- Given one JSON tree, when a flag changes on disk, then all three surfaces observe it with no egress.
- Given rendered manifests, when inspected, then there is no Reloader or flagd sidecar and no second tree.

## Design Notes

OpenFeature `set_provider` is process-global. Django and MCP share the ASGI process. CLI is a separate process against the same bytes. FILE poll is 5s. ConfigMap is directory-mounted (not `subPath`) so kubelet updates are visible to poll. `FLAGD_OFFLINE_FLAG_SOURCE_PATH` matches the mount file. Helm never duplicates the tree in `values.yaml`; tests and README pass `--set-file flags.tree=src/platform/config/flags.json`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/815
Merge SHA: 61b31b3f29c978ffe2492f51923f7ab4e8ed6197
Verification: `pixi run -e platform-ci-test pytest src/platform/tests/test_openfeature_file_flags.py src/platform/tests/meta/test_no_pyforge_import.py` — 8 passed, 1 skipped (helm not on PATH locally)

