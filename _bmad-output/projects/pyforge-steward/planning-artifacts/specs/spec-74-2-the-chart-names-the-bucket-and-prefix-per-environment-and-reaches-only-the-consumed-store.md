---
title: "74.2: The chart names the bucket and prefix per environment and reaches only the consumed store"
type: 'feature'
created: '2026-09-28'
status: 'done'
baseline_revision: a16ab7f7e2a65d81814987c7698ace76d65ad16e
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.steward.object_store_consumer    # the same key as Story 74.1 (one flag per CAP)
  provider: openfeature-file                   # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: on, dev: on}   # per-env values need Guild CAP-5 (steward Epic 76); until then the tree default is off
  scope: global                                # v1 is global only (Q5)
  fallback: nothing calls the seam, so the bucket and prefix values are inert; objectStorage.enabled false renders today's chart byte for byte
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
  - src/platform/deploy/charts/platform/values.yaml
  - src/platform/deploy/charts/platform/templates/_helpers.tpl
  - src/platform/deploy/charts/platform/templates/networkpolicy-egress.yaml
  - src/platform/tests/test_chart_invariants.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the chart wires `OBJECT_STORAGE_ENDPOINT_URL` / `OBJECT_STORAGE_ACCESS_KEY` / `OBJECT_STORAGE_SECRET_KEY` as
optional `secretKeyRef`s (`templates/_helpers.tpl`, Story 50.3) and names no bucket or prefix, so every environment would
share one namespace in the store. With `networkPolicy.enabled`, the web and worker egress policies
(`templates/networkpolicy-egress.yaml`, Story 48.3) list exactly their in-cluster peers, so a pod could not reach a store
outside the cluster at all. Story 74.1 reads `OBJECT_STORAGE_BUCKET` and `OBJECT_STORAGE_PREFIX` from the environment.

**Approach:**

- `values.yaml` gains `objectStorage.enabled` (default `false`), `objectStorage.bucket` and `objectStorage.prefix`, with a
  comment naming the rule: one bucket per environment, or one bucket and a prefix per environment; the store is consumed,
  never deployed by this chart.
- `_helpers.tpl` renders `OBJECT_STORAGE_BUCKET` and `OBJECT_STORAGE_PREFIX` as plain `value:` env on the web and worker
  workloads when enabled, each through `required` so an empty value fails the render naming it. Credentials stay the three
  existing `secretKeyRef`s (canopy:AD-19).
- `networkPolicy.objectStorage` (a CIDR list and a port) adds one egress rule to the web and worker policies only, rendered
  only when both `networkPolicy.enabled` and `objectStorage.enabled` are set.
- `test_chart_invariants.py` pins: the enabled render carries both values and no credential value; the disabled render is
  byte-identical to today's; no rendered manifest names an object-store image (`silo`, `garage`, `minio`); the egress rule
  appears on web and worker and on no other workload.

Ledger key: `74-2-the-chart-names-the-bucket-and-prefix-per-environment-and-reaches-only-the-consumed-store`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / S-74.1.

### Living CAP citations

- `spec-pyforge-steward` CAP-163 (FR-36); canopy:AD-19; CAP-94's dated 2026-09-10 exception (consumed, never self-hosted).
- `spec-feature-flag-governance` CAP-1 (the flag block; this story shares Story 74.1's key).

## Acceptance Criteria

- Given `objectStorage.enabled: true` with a bucket and a prefix When the chart renders Then web and worker pods carry `OBJECT_STORAGE_BUCKET` and `OBJECT_STORAGE_PREFIX` as plain values and the three credentials only as `secretKeyRef`
- Given `objectStorage.enabled: true` with an empty bucket or prefix When the chart renders Then the render fails naming the missing value
- Given `objectStorage.enabled: false` When the chart renders Then the output is byte-identical to the render before this story
- Given `networkPolicy.enabled: true`, `objectStorage.enabled: true` and `networkPolicy.objectStorage` set When the chart renders Then the web and worker egress policies allow that CIDR and port and no other workload's policy does
- Given any values When the chart renders Then no manifest runs an object-store image (`silo`, `garage`, `minio`)
- Given the change When `pixi run --frozen -e pyforge-steward pyforge-steward-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- Keep credentials as references; the rendered chart names secret keys, never values (canopy:AD-19).
- Keep `objectStorage.enabled: false` the default, so an existing release renders unchanged.
- Reconcile every Spec `spec-surface-check` names for the chart paths, then stamp each scoped with `--spec`.

**Never:**
- Do not render an object-store Deployment, StatefulSet or sidecar, in any overlay.
- Do not open egress for any workload other than web and worker, or to anything but the configured endpoint.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| enabled | bucket + prefix set | two plain env values on web and worker | — |
| missing value | enabled, empty prefix | — | render fails naming `objectStorage.prefix` |
| disabled | default values | byte-identical to today | — |
| egress | networkPolicy + objectStorage enabled | web and worker allow the endpoint | — |
| egress, store disabled | networkPolicy enabled only | no new egress rule | — |
| self-hosting | any overlay | no object-store image rendered | invariant test reds |

</intent-contract>

## Source

Contract authored from `docs/dreams/pyforge-steward.md`'s 2026-09-28 (night) Realization-log entry *Proposed: the
object-storage seam gets its first consumer, Herald's deck exports* ("The Helm chart names the bucket and prefix per
environment"; "consumed and never self-hosted in production") and `spec-pyforge-steward` CAP-163.

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-163 (FR-36).
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-28 (night) — Proposed: the object-storage seam gets its first consumer, Herald's deck exports*.
Ledger key: `74-2-the-chart-names-the-bucket-and-prefix-per-environment-and-reaches-only-the-consumed-store`.
Ledger status at mint: `backlog`.
Deps: S-74.1 (the settings the chart feeds).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- ON/OFF: render the chart with `objectStorage.enabled` true and false (the flag's two deployment states) and compare
  against two flagd trees (key on, key off), the way `src/platform/tests/test_openfeature_file_flags.py` does, until the
  testing-kit fixture of `spec-feature-flag-governance` CAP-4 lands.
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: `test_chart_invariants.py` passes with `helm` on `PATH`.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new findings.

## Spec Change Log (amendment)

- 2026-10-03 — operator ruling (deferral burn-down Phase 3, DW-steward-74-1-2): the mounted S3 credential must allow
  `s3:ListBucket` on the bucket (conditioned to the prefix) as well as `s3:GetObject` and `s3:PutObject` on the prefix.
  On real S3 a `head_object` on an absent key answers 403 instead of 404 without ListBucket, which the store would read
  as a failure rather than "absent". State it in the chart values docs and in this story's acceptance criteria when it is
  dispatched.

## Review Triage Log

### 2026-10-07 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings:
  - (implementer self-check against diff and AC matrix; no separate reviewer subagent findings recorded this pass)

## Auto Run Result

Status: done

Summary: Helm chart gains optional consumed object storage: `objectStorage.enabled` wires plain `OBJECT_STORAGE_BUCKET` / `OBJECT_STORAGE_PREFIX` on web and worker only; optional store egress on those two NetworkPolicies; default-off render stays byte-identical.

Files changed:
- `src/platform/deploy/charts/platform/values.yaml` — objectStorage defaults and ListBucket IAM note; networkPolicy.objectStorage
- `src/platform/deploy/charts/platform/templates/_helpers.tpl` — objectStorageEnv + egressToObjectStorage helpers
- `src/platform/deploy/charts/platform/templates/platform-deployment.yaml` — objectStorageEnv on web
- `src/platform/deploy/charts/platform/templates/worker-deployment.yaml` — objectStorageEnv on worker
- `src/platform/deploy/charts/platform/templates/networkpolicy-egress.yaml` — store egress on web/worker only
- `src/platform/tests/test_chart_invariants.py` — Story 74.2 I/O matrix tests

Review: no patch/defer entries; self-check only.

Follow-up review recommended: false

Verification:
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — pass (2028 passed, 3 skipped)
- `tests/test_chart_invariants.py -k test_story_74_2` — 6 passed (platform-ci-test env)
- `python scripts/spec_surface_reconcile.py` (pyforge-doctor env) — OK after memlog reconcile on spec-pyforge-steward and spec-pyforge-unifying-strategy
- `bash scripts/platform-ci-local.sh --test` — chart/ruff/mypy/policy pass; full Django suite had pre-existing ERRORs on unrelated warden/supervisor tests in this local run

Residual risks: operators must set `networkPolicy.objectStorage.cidrs` when enabling object storage with default-deny policies; per-env flag overlay (Epic 76) still pending for production ON.
