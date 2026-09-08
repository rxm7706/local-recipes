---
title: "Addendum — depth for the PRD and architecture passes"
status: "ready"
chain: "pyforge-unifying-strategy"
parent: "brief.md"
created: "2026-08-24"
updated: "2026-08-24"
inputs:
  - "docs/dreams/pyforge-unifying-strategy.md"
  - "../../specs/spec-pyforge-unifying-strategy/SPEC.md"
  - "../../specs/spec-pyforge-unifying-strategy/convergence.md"
  - "../../research/technical-pyforge-unifying-strategy-research-2026-08-24.md"
  - "../../research/technical-pyforge-unifying-strategy-airgap-delivery-2026-08-24.md"
---

# Addendum

Material that earned a place in the chain but not in a two-page brief. Downstream passes (PRD,
architecture, epics) read this; the brief does not repeat it.

## Corrections carried forward from the pre-audit draft

The 2026-08-23 draft is superseded, but it is worth recording *what* it got wrong, because several
errors are the kind a downstream pass would reintroduce from the Dream's own prose.

| Draft claimed | Actual | Consequence |
|---|---|---|
| Greenfield platform to be built | `src/platform/` is live; steward epics 10/11/12/16 `done` | The chain is an extension binding `spec-python-agent-platform`, minting nothing that duplicates CAP-1..6 |
| `pyforge_host` / `pyforge-agent-platform` are the artifacts | Role names only; the artifact is `src/platform/` | No rename story is minted |
| Lane 2 portals at `/stations/{station}/` | Warden's mounts at `/compliance/` | Asserted as inherited convention; it never was. **Decided 2026-08-24:** uniform `/stations/<name>/`, and the shipped portal moves behind a permanent redirect (FR-9a) and is repackaged as a reusable app (FR-9b) |
| Eight FastAPI services on ports `:8001–:8008` | No port assignments exist anywhere in `src/platform/` | Invented. Port/binding topology is an architecture decision, not an inherited fact |
| Wagtail CRX (CodeRed) carries Lane 1 | CodeRed dropped 2026-08-24 on maintenance evidence | Wagtail alone |
| MCP over `/mcp/sse` | Deprecated twice over; a compliant server answers GET with `405` | Single POST `/mcp` on the official SDK; long work is `start`/`get` over PostgreSQL until Tasks ships in the SDK |
| Scribe has a SQLite/PostgreSQL dual driver | Scribe ships `FlatFileGraphStore` — one JSON file | BS-1's remediation is "flat-file → PostgreSQL/pgvector"; its stated failure mode had to be re-derived |
| RFC-5: zero runtime ORM DDL, as written | Not implementable — `post_migrate` and `create_test_db` both require `migrate` | Enforcement moved to the database role; test databases carved out |
| "80% reduction", "sub-500ms", "100% deterministic" | No baseline exists for any of them | Removed. Fabricated metrics survive into a PRD as requirements and then into acceptance criteria nobody can evaluate |
| A dated Gantt through 2026-11 | No such schedule was ever agreed | Removed. Sequencing is expressed as dependency, not calendar |
| Five-tier completeness for any work | **03 only** (Q2). 01/02 stay spec+script or spec+skill | canopy:AD-14; Epic 29. Do not fail 01/02 for missing a portal. |
| Packaging stories in this chain author OpenFeature/Liquibase recipes | Operator-owned. S-26.3 / S-27.1 do not author recipes | canopy:AD-16 |
| No `django-feedstock` 5.x branch | Branch exists. Pin catch-up is a version+sha256 PR | Currency gap, not chain packaging |

## Operating model (bound 2026-08-24, after first ready)

Dream Grounding is authoritative. This table is the brief's copy so a PRD/architecture reader
does not re-derive pre-OM five-tier from this addendum's older sequencing list.

| Bind | Brief consequence |
|---|---|
| Q1 Golden Path; WFT names as adapters | Same Pixi task. Harness / Splunk / Jira / Tachyon / named scanners are **plugins**. |
| Q2 five-tier = 03 | The eight stations still owe five tiers. New work does not. |
| Q3 owner vs SLA | Registration: owner, backup, `work_class`, promotion date. SLA body in the 03 spec. |
| Q4 traceability | `spec_id` + git sha + SBOM purl; Jira optional. |
| Q5 measurement | Rules in the Dream. Board = sibling Dream. No CAP-18. No unpublished metrics. |
| Q6 Path B ≠ Tachyon | Path B = Agent Canopy + persona. Tachyon = production LLM adapter. |
| Q7 Lane 2 is HTMX | FastAPI = compute. DRF on Atlas / data-models only. |
| AD-21 hooks/plugins | Process owns hook specs; plugin replaces a layer without a fork. Kedro *names* the split. |
| Q8 Warden sole PR verdict | Warden **owns** PR-gate hook specs; plugins implement. Missing scanner ≠ failed run. |

## Sequencing constraints the epic pass must honour

These are facts about the work, not preferences, and each one dictates ordering.

1. **Packaging precedes platform in two epics — six builds, not six new recipes.** CAP-13 needs
   four new OpenFeature feedstocks (`openfeature-sdk`, `openfeature-flagd-api`,
   `openfeature-flagd-core`, `openfeature-provider-flagd`) plus a `cachebox` 5.x build — conda-forge
   ships 6.2.5 and the provider pins `<6`, so that fifth one is a **downgrade build on an existing
   feedstock**. CAP-9 needs `liquibase` ≥5.0.4 with PostgreSQL JDBC vendored. **S-26.3 and S-27.1
   are operator gates** (canopy:AD-16): they do not author recipes. Downstream stories wait on the
   channel. Rule 1 still applies if the *operator* authors those recipes elsewhere.
2. **CAP-1 precedes CAP-2 and CAP-3.** Chrome lives in the shared package; a portal built before it
   exists will grow its own and violate the contract.
3. **CAP-6 precedes CAP-4's consumers.** Portals must not reach services before the identity-carrying
   client exists, or the first integration will be a trusted header nobody removes later.
4. **CAP-2's parity inventory precedes CAP-2's cutover.** Enumerate Marshal's console views and
   confirm a runtime equivalent for each *before* removing the old build path. A view depending on
   build-time data with no runtime equivalent forces a scope conversation rather than a silent gap.
5. **CAP-9's changeset extraction gate has no prior art.** No team is documented running Liquibase
   as schema authority for a Django app; the `sqlmigrate` extraction check is ours to build, and
   should be sized as invention rather than integration.
6. **Phase 5 is eight correct-course runs, not one — and they landed.** Canopy obligations plus
   operating-model obligations (`DW-CANOPY-2026-08-24`, `DW-OM-2026-08-24`) are on every station.
   Marshal's Canopy run retires `spec-factory-console`. Each run pinned `BMAD_ACTIVE_PROJECT` and
   wrote a physical `projects/<slug>/` path. Ledger shape for reopening 11.1/11.2 remains
   `bmad-correct-course`, not a new Canopy epic.
7. **Django 5.2.16/5.2.17 are security releases; every affected path is unreachable here.** The
   claim that no `5.x` branch exists was wrong. Catch-up is a feedstock PR, not Canopy scope.

## Design decisions already made, with their reasons

Sourced from the two 2026-08-24 research files in `inputs:`. Recorded so the architecture pass
confirms them rather than relitigating them.

- **Pre-upgrade Job, never an init container.** Two independent arguments: N replicas each running
  an init container contend on `DATABASECHANGELOGLOCK` (default wait 5 minutes), and the shipped
  `migrate-job.yaml` header documents that `helm install --wait` deadlocks migration-gated
  readiness. The hook already exists at weight `0` and runs the platform image with its command as
  `args`, so CAP-9 adds a Job at weight `-1` and flips the existing one to `migrate --fake`.
- **flagd FILE resolver, not a daemon.** Evaluates in-process from local JSON with the full
  targeting engine — no sidecar, no egress. `wasmtime` is not on conda-forge, which independently
  rules out GO Feature Flag's in-process WASM mode.
- **Keep-alive well under 30 seconds.** OpenShift's `timeout client` is cluster-wide with no
  per-route override, and HAProxy governs streaming by `timeout client`/`timeout server`, not
  `timeout tunnel`. A route annotation is defence-in-depth, never the mechanism.
- **PyBreaker plus a ~40-line async wrapper.** Its async support is Tornado-coroutine, not asyncio:
  an `httpx.AsyncClient` coroutine passed to `breaker.call()` records a false success and the
  circuit never trips. The alternatives were `aiocircuitbreaker` (packaged, dormant since 2022) and
  `purgatory` (maintained, unpackaged) — neither worth it for forty lines. Note also that its Redis
  state transitions use plain `setnx`/`set`/`incr` with no Lua and no `WATCH`, so cross-replica
  transitions are **not atomic**: treat `fail_max` as coarse protection, never as exact-count
  semantics, and do not specify a test that asserts an exact failure count.
- **`django-lasuite` for OIDC only.** It is OIDC/DRF/malware plumbing with no app switcher and no
  theme. La Suite's own switcher ships as npm/React with a service-list endpoint unreachable
  air-gapped. `django-pyforge` is ours to build.

## Deployment constraints CAP-2 inherits

Documented Wagtail requirements for multi-replica operation. All solvable, none optional, and the
OIDC group-mapping one is the one that bites.

- Media must leave the pod filesystem (object storage or RWX). Remote storage does not fully
  offload it — originals are re-read whenever a rendition is generated.
- Cache must be shared. Wagtail uses a dedicated `"renditions"` alias falling back to `default`; a
  per-process cache leaves each replica with a divergent rendition cache.
- Search needs no new service: the database backend uses PostgreSQL full-text search and is
  documented as production-adequate. Requires `django.contrib.postgres` in `INSTALLED_APPS`.
- Background tasks: **Celery `BaseTaskBackend`** (canopy:AD-10). Do not inherit django-tasks'
  database or RQ backends. PyPI `django-tasks-celery` is Django 6-only and out of pin.
- **OIDC users land with no groups**, and Wagtail's admin gates on `wagtailadmin.access_admin`
  rather than `is_staff` — so a user authenticates successfully and is still bounced. Mapping IdP
  claims onto a group holding that permission is required work with no first-party guidance. Pair
  with `WAGTAILUSERS_PASSWORD_ENABLED = False` and `WAGTAIL_EMAIL_MANAGEMENT_ENABLED = False`.
- `WAGTAILADMIN_LOGIN_URL` (6.0, extended in 7.1 to cover logout) is the supported allauth hook.
  Most community material predates it and describes URLconf-override workarounds — do not follow
  those.

## Adjacent, deliberately not absorbed

- Ledger rollup drift: warden `epic-7`/`epic-8` and mason epics 2–3 read `backlog` while their
  stories read `done`. Flagged so nobody mistakes a `backlog` rollup for remaining scope.
  Pre-existing, cross-station.
- Atlas never adopted `spec-secure-live-dashboards` despite being named its first adopter. CAP-7
  consumes that pattern; making atlas adopt it is atlas's story.
- Story 12-7 is permanently `skip_on_blocked` pending a live cluster.
- Two steward Dreams (`bmad-suite-install-class-wiring`, `ocp-as-a-portability-profile`) fail
  `dream-chain-check` today. Same station, unrelated chains.
