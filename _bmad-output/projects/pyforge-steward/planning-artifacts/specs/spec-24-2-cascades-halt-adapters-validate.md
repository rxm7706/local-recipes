---
title: 'Cascades halt; adapters validate'
type: feature
created: '2026-08-25'
status: done
baseline_commit: 07a6c360edf
baseline_revision: 07a6c360edf
review_loop_iteration: 0
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-24-1-cloudevents-on-redis-broker.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** A buggy producer can fan out forever, event `type` can be a story-local string, and payload shape can be rejected at the stream (killing transport) instead of in the domain (FR-19, FR-20, canopy AD-8).

**Approach:** Enforce `pyforgeloopdepth` ceiling 8 on publish in `django-pyforge`, register event `type` as dotted verbs in that same chrome, and reject payload shape only in consuming domain adapters. Keep CloudEvents on redis-broker Streams from 24-1.

## Boundaries & Constraints

**Always:** Halt publish when `pyforgeloopdepth` reaches 8; the halt is observable (typed error, no `XADD`). Event `type` must be a dotted verb in the `django-pyforge` registry (adding a type is a chrome change). Stream boundary remains a transport: invalid `data` still `XADD`s and parses. Cite canopy AD-8 / AD-10. Specs under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward`. Physical writes only under that slug.

**Block If:** Implementation would re-split Redis (20-2 already split redis-broker vs redis-cache), move CloudEvents off redis-broker, start Epic 25, or require a live cluster Redis that tests cannot replace with the in-process stream backend.

**Never:** Start 24.3 or 25-x. Epic 30. `import pyforge` under `src/platform/`. MinIO. Colon stream keys. Writing events to redis-cache. `scripts/bmad-switch`. `bmad-loop`. Other stations' ledgers. Re-split Redis.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Depth ceiling | Deliberate cycle republishing with incremented `pyforgeloopdepth` | Publish of depth `0..7` `XADD`s; depth `8` does not | `LoopDepthExceededError`; stream unchanged at halt |
| Observable halt | Publish with `pyforgeloopdepth=8` | Caller sees typed error; no new stream entry | Must not silently drop |
| Registered type | `type` in chrome registry (dotted verb) | Publish succeeds | — |
| Unregistered type | Dotted string not in registry | No `XADD` | `UnregisteredEventTypeError` |
| Adapter rejects shape | Valid envelope, `data` missing required keys | Event is on `pyforge.events`; `parse_cloudevent` returns it | `PayloadShapeError` from adapter only |
| Stream is transport | Same invalid `data` | Fabric publish + consume handler still run | Stream boundary must not raise on payload shape |

</intent-contract>

## Code Map

- `src/shared/packages/django-pyforge/src/django_pyforge/events/constants.py` -- `EXT_LOOP_DEPTH=pyforgeloopdepth`, `LOOP_DEPTH_CEILING=8`, `EVENT_TYPES` chrome registry
- `src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py` -- publish checks type registry + depth ceiling; does **not** validate `data` shape
- `src/shared/packages/django-pyforge/src/django_pyforge/events/adapters.py` -- NEW: consuming domain adapter; `PayloadShapeError`
- `src/shared/packages/django-pyforge/src/django_pyforge/events/__init__.py` -- export new errors, constants, adapter
- `src/platform/tests/test_cascades_halt_adapters_validate.py` -- NEW: three ACs
- `src/platform/tests/test_cloudevents_redis_broker.py` -- 24.1; `recipe.audit.failed` must stay registered
- Never: `src/platform/**` importing `pyforge.*`; Epic 25 circuits / DuckDB / HTMX 422; re-split Redis

## Tasks & Acceptance

**Execution:**
- `django_pyforge/events/` -- loop-depth halt, type registry, domain adapter
- `src/platform/tests/test_cascades_halt_adapters_validate.py` -- three ACs

**Acceptance Criteria:**
- Given a deliberate cycle, when `pyforgeloopdepth` reaches 8, then publish halts observably.
- And event `type` is a dotted verb registered in `django-pyforge`.
- And payload shape is rejected in the consuming domain adapter, not at the stream boundary.

## Spec Change Log

## Design Notes

Depth is a CloudEvents extension (`pyforgeloopdepth`), not HTTP `X-PyForge-Loop-Depth`. Allowed published depths are `0` through `7`; `>= 8` raises and does not `XADD`. Default omitted depth is `0`. Event types are a frozenset in `django-pyforge`; `recipe.audit.failed` stays for 24.1. Adapter required keys for that type: `data.package` and `data.reason`. Stream field remains one JSON object from 24.1.

## Verification

**Commands:**
- `export BMAD_ACTIVE_PROJECT=pyforge-steward`
- `pixi run -e platform-ci-test pytest src/platform/tests/test_cascades_halt_adapters_validate.py src/platform/tests/test_cloudevents_redis_broker.py -q` -- expected: all pass
- `pixi run -e platform-ci-test pytest src/platform/tests/meta/test_no_pyforge_import.py -q` -- expected: pass

## Auto Run Result

Status: done

Summary: Loop-depth ceiling 8, chrome `EVENT_TYPES` registry, and consuming `RecipeAuditAdapter` in `django-pyforge`. CloudEvents remain on redis-broker Streams from 24-1.

Files changed:
- `django_pyforge/events/constants.py` -- `pyforgeloopdepth`, ceiling 8, `EVENT_TYPES`
- `django_pyforge/events/fabric.py` -- halt + type check on publish; still no payload-shape check
- `django_pyforge/events/adapters.py` -- `PayloadShapeError` / `RecipeAuditAdapter`
- `src/platform/tests/test_cascades_halt_adapters_validate.py` -- three ACs
- this spec

Verification: `pixi run -e platform-ci-test pytest src/platform/tests/test_cascades_halt_adapters_validate.py src/platform/tests/test_cloudevents_redis_broker.py src/platform/tests/meta/test_no_pyforge_import.py -q` → 11 passed.

