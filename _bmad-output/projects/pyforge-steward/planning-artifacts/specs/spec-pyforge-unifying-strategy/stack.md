---
title: "Stack and the conda-forge gate"
chain: "pyforge-unifying-strategy"
created: "2026-08-24"
updated: "2026-08-26"
---

# Stack — and the conda-forge gate

Companion to `SPEC.md`. Every dependency this chain needs, checked against conda-forge on
2026-08-24. **This table is a scheduling instrument, not a shopping list:** a package in the
"absent" section is feedstock work that must land as its own story *before* the capability
depending on it can be built, and per repo Rule 1 each of those stories invokes
`conda-forge-expert`.

## Fixed floor

Django `>=5.2.15,<6` and Python `3.12.*`, inherited from `spec-python-agent-platform` CAP-5. Django
6 is unavailable to this chain.

**A live packaging risk sits underneath that pin.** conda-forge's Django 5.2 line **stopped at
5.2.15 (2026-06-06)** while upstream shipped 5.2.16 (2026-07-07) and 5.2.17 (2026-08-04).
conda-forge's autotick bot follows newest-upstream, so it advanced the 6.x line and left 5.2
behind — but a `5.x` maintenance branch **does** exist (`abi_migration_branches`); catching up is
a one-file PR. **Audited 2026-08-24:** those releases carry seven CVEs, one high, and every
affected path is unreachable in `src/platform/`. Currency gap, not a live exposure. Recommend
moving the pin to `>=5.2.17,<6` once the feedstock publishes it (scanners key on version strings).

## Available — no work required

| Package | conda-forge | Serves | Note |
|---|---|---|---|
| `wagtail` | 7.4.3 | CAP-2 | Landed ~4h after upstream; full transitive closure present. Supports Django 5.2 + Python 3.12. No Wagtail version requires Django 6 — 5.2 is the only Django supported across the entire 7.0→8.0 range. |
| `django` | 5.2.15 | all | See risk above. |
| `mcp` (official SDK) | 2.0.0 | CAP-4 | `2026-07-28`-capable. The only conda-forge path to the current MCP spec. |
| `django-lasuite` | 0.0.28 | packaging only | **Not a Canopy dep.** Host OIDC is allauth. Feedstock + `suite-*` recipes stay. Sole listed maintainer `rxm7706`. |
| `pybreaker` | 1.4.1 | CAP-10 | Sync paths only — see `resilience-invariants.md` BS-4. |
| `django-storages` | 1.14.6 | CAP-2 | Library present. **Backend is filesystem on a ReadWriteMany PVC** (parent AD-1 forbids MinIO/S3 as a fourth kind). Multi-replica media leaves ephemeral pod disk without a new infra kind. |
| `django-redis` | 7.0.0 | CAP-11 | Also what PyBreaker's own Redis-storage docs use. |
| `openjdk` | 25.0.2 | CAP-9 | Satisfies Liquibase's Java 17+ floor — but Liquibase itself is absent. |
| `celery`, `redis-py`, `grpcio`, `protobuf`, `pyyaml`, `pydantic` | current | CAP-8, CAP-11, CAP-13 | No work. |
| `python-duckdb` | current (pixi / atlas) | CAP-19 | Library, not a fourth infra kind. **Single writer on RWO** — one process owns ``atlas.duckdb``; Parquet is the cross-pod shared artifact (Story 41.2 / BS-5). `vss` / `postgres` extensions: LOAD-only consumer (AD-13). |
| `duckdb-server` | reciped (`recipes/duckdb-server`) | CAP-19 face | Optional HTTP/Arrow face. Not in `pixi.toml` until `query-plane-face` is answered. Not a Helm backing store. |
| `kedro`, `kedro-datasets`, `kedro-dagster` | current (atlas env) | CAP-19, atlas | One Kedro *home* (atlas). Not eight projects (AD-21). |
| `kedro-mcp`, `kedro-skills` | current | authoring | Skills: 34.2 catalog shipped. MCP: wrapped, never load-bearing (atlas FR-7). |
| `kedro-viz` | current | atlas 12.2 | Pipeline DAG publish. Not Lane 3. |
| `vizro` | `>=0.1.60` | Lane 3, CAP-7 | Runtime boards over BSL + plane. Not imported into Django. |
| `vizro-mcp`, `vizro-e2e-flow` | current | Lane 3 authoring | Replaces Vizro-AI. 36.2 is a grounded page; MCP authoring is still a later story. |
| `vizro-ai` | `0.4.2` **final / deprecated** | legacy `query_vizro_ai` | No new features. |
| `boring-semantic-layer` | `>=0.3.18` (SelfExplainML) | CAP-19 / UJ-6 | Certified metrics. Agents and Vizro do not invent raw SQL. |

## Estate leverage — installed, bind now

Pins already in `pixi.toml`. This is **not** a shopping list and **not** eight new stations.
It is the 2026-08-26 schedule for using what we already lock. Kedro/Vizro rules: option
for pipelines, Vizro for Lane 3, one Atlas Kedro home (see AD-21 / AD-22).

| Pin | Station | Bind | Status |
|---|---|---|---|
| `kedro` + `kedro-datasets` + `kedro-dagster` | atlas (home); optional extract nodes | Named CAP-19 pipeline; Dagster refreshes cache | **shipped 34.2** |
| `kedro-skills` / `kedro-mcp` | atlas | `catalog-config` already in atlas `AGENTS.md`; MCP inspect after 34.2 | **use now** / wrap |
| `vizro` + BSL | atlas, steward Lane 3 | Boards over plane metrics; CAP-7 isolation | **shipped 36.1–36.2 (`estate-cache`)** |
| `vizro-mcp` + `vizro-e2e-flow` | herald/atlas authoring | Replace Vizro-AI for new boards | **still later** (not 36.2) |
| `cocoindex` + `graphifyy` | scribe | `scribe index`: AST graph + incremental index; link functions to Dream/PRD/spec_id | **bind** (not Epic 34) |
| `openlineage-python` | marshal, steward | CloudEvents already CAP-8; emit OpenLineage on Dream→Spec→Mason→Warden→Steward | **bind** (CAP-8 face, not a fourth bus) |
| `boring-semantic-layer` | atlas | Metrics on the plane (`package_download_velocity`, `ecosystem_cve_risk_score`, new CAP-19 relations) | **36.1 reads estate cache** |
| `markitdown` | herald, scribe | docx/xlsx/pptx/pdf → markdown for Wagtail / Scribe memory | **bind** |
| `graphviz2drawio` | herald | Kedro/Graphviz `.dot` → `.drawio` for architect review / decks | **bind** |
| `filelock` | marshal, scribe; **atlas already** | Atlas `duckdb_writer` (FR-27). Same primitive for worktrees / scribe files | **extend** |
| `go-sops` + `age` | steward | Offline X25519 vaulting — in-estate path | **landed / keep** |
| HashiCorp Vault / `hvac` | steward **profile adapter** | **Not** CAP-12 in-app. canopy:AD-19: pod specs carry secret *references* only; no Vault HTTP from the platform image. Cluster ESO/Vault stays outside the image. | **do not bind in-app** |
| `pandera` | warden, mason | Schema contracts on lockfiles / CycloneDX feeds | **bind** |
| `taplo`, `sqlfluff`, `yamllint` | doctor, warden | `pixi.toml` / `recipe.yaml` / DuckDB SQL preflight (`doctor check --syntax`) | **bind** (sqlfluff also lints CAP-19 SQL) |
| `playwright` + `playwright-python` | herald, testing-kit | `.dc.html` + Vizro board PNG/PDF; both pins required (CLI ≠ Python module) | **extend** (herald already; Vizro thumbs after Lane 3 plane board) |

**Never:** a fourth backing service (Vault-in-pod, MinIO, extra bus). OpenLineage events ride
the existing Redis CloudEvents fabric or a documented emit from the same process — they do
not mint a lineage server. cocoindex/graphifyy stay behind Scribe `GraphStore`; they do not
become a second vector store beside CAP-19.

## Absent — feedstock work, blocking

| Package | Serves | Consequence |
|---|---|---|
| `openfeature-sdk` | CAP-13 | **Zero runtime dependencies** — as simple as a `noarch: python` recipe gets. Start here. |
| `openfeature-flagd-api` | CAP-13 | Transitive, via flagd-core. |
| `openfeature-flagd-core` | CAP-13 | Carries the targeting engine. |
| `openfeature-provider-flagd` | CAP-13 | The FILE resolver itself. |
| `cachebox` 5.x | CAP-13 | conda-forge ships **6.2.5**; the flagd provider pins `>=5.1,<6`. A 5.x build is required alongside the four above. |
| `liquibase` | CAP-9 | **Not on conda-forge** — sole anaconda.org hit is third-party `maize-genetics/liquibase` 4.21.0, 0 downloads, two majors behind Community 5.0.4. **Feedstock committed 2026-08-24.** Shape precedent: `apache-tika` (Maven jars into `$PREFIX/share/java/…`, `openjdk` run-dep, CLI wrapper), one of ~12 JVM recipes already here. `openjdk` 25.0.2 clears the Java 17+ floor. **Vendor the PostgreSQL JDBC driver** — 5.0 Community stopped bundling it and LPM fetches over the network. |

Nothing OpenFeature-related exists anywhere on anaconda.org: a global search returns zero results.
Five *builds* are the committed cost of CAP-13, ruled 2026-08-24 — four new feedstocks plus the
`cachebox` 5.x downgrade on an existing one, which is a different size of task and should not be
scheduled as a fifth new recipe. `liquibase` is a sixth build for CAP-9,
committed the same day. **Stories 26.3 and 27.1 are ledger-`done` (2026-08-25).** Do not
re-open those epics as “start with packaging.” CRC did not close live CAP-9 (`/ht/` after
Liquibase).

## Two supply boundaries, not one

The "absent" table above governs the **Python/pixi dependency graph**. Container images are a
separate boundary governed by `spec-python-agent-platform` CAP-6 — internal-registry images,
external references failing rather than warning — and third-party images are already consumed
under it (`postgres:17`, `redis:7`, and `quay.io/keycloak/keycloak:26.4.0` in compose), none with a
feedstock. `docs/reference/enterprise-deployment.md` is silent on images entirely; it documents
conda/PyPI mirrors only.

This mattered for exactly one row. **Liquibase was the only dependency in this chain that could
legitimately arrive either way**, and the deciding fact turned out not to be policy but the chart:
the shipped `migrate-job.yaml` hook runs the **platform image** and passes its command as `args`, so
a conda-packaged Liquibase requires no new image, while the container route pays a third-party-image
supply path the repo has never documented *and* still builds a derived image for the JDBC driver.
**Resolved to the feedstock, 2026-08-24.** Full evidence in
`research/technical-pyforge-unifying-strategy-airgap-delivery-2026-08-24.md`.

## Ruled out, with reasons

| Candidate | Why not |
|---|---|
| **CodeRed CMS** (`coderedcms` 6.0.0) | On conda-forge, but upstream is dead: no `main` commit since 2025-09-12, no push to any branch since 2025-12-16, declared support stops at Wagtail 7.0–7.1 against a 7.4.3 LTS, and open issue #710 breaks admin form submissions inside its own support window with fix PR #717 unmerged since 2026-07-17. Lane 1 is Wagtail alone. |
| **`wasmtime`** | Not on conda-forge — kills GO Feature Flag's in-process WASM mode outright. Reinforces the flagd FILE-resolver choice. |
| **`aiocircuitbreaker`** 2.0.0 | On conda-forge and genuinely async, but upstream dormant since January 2022 with 5 stars. Adopting it means adopting unmaintained code. |
| **`purgatory`** 3.0.1 | Purpose-built for asyncio and maintained into 2025-07, but not on conda-forge and 4 stars. Not worth a feedstock for a 40-line wrapper. |
| **`django-openfeature`** 0.2.0 | Third-party, single-maintainer, pre-1.0, and unreleased since the SDK 0.10.0 `set_provider` breaking change. Not required — CAP-13 needs the SDK plus a provider, not this shim. |

## Premise corrections that change the stack

**`django-lasuite` is not a UI layer.** Its modules are OIDC login, OIDC resource server, malware
detection, marketing backends, DRF throttling, admin colours, and secret-from-file config. All six
shipped how-tos are OIDC, malware, or marketing. It contains **no app switcher and no theme**.

**La Suite's switcher has no Python path.** "La Gaufre" ships as `@gouvfr-lasuite/ui-kit`
(npm/React) or a vanilla-JS widget, and its dynamic service-list endpoint is unreachable
air-gapped; only the static-JSON variant works offline, and it would surface a French government
service catalogue rather than our navigation. **No documented La Suite reusable-app pattern exists**
— their `dev-handbook`'s `python.md` is a PEP 8 style guide.

Consequence: **CAP-1's `django-pyforge` is ours to build.** Host OIDC is
`django-allauth` (shipped). **`django-lasuite` is not a Canopy dependency** —
Phase-2 “adopt for OIDC only” is retracted. Keep the conda-forge feedstock
and `suite-*` recipes as packaging; do not add the package to host
`INSTALLED_APPS`.

**Lane 2 is not a DRF surface (operating-model Q7).** `django-lasuite`'s DRF throttling is not a
reason to put JSON:API on Guildhall or station portals. HTMX is the portal contract; FastAPI is
the station compute API; DRF JSON:API stays on the Atlas / enterprise-data-models kinship. Do not
add `djangorestframework` as a Canopy/Lane-2 feedstock item in this chain.

## Deployment constraints CAP-2 inherits

Documented Wagtail requirements for multi-replica operation, all solvable, none optional:

- **Media must leave the pod filesystem** — object storage via `django-storages`, or RWX. Note that
  remote storage does not fully offload file handling: original images are read back whenever a new
  rendition is generated, so pods need reach to the store.
- **Cache must be shared** — Redis via `django-redis`. Wagtail also uses a dedicated `"renditions"`
  cache alias, falling back to `default`; a per-process cache would leave each replica with a
  divergent rendition cache.
- **Search needs no new service** — the database backend uses PostgreSQL FTS and is documented as
  production-adequate absent Elasticsearch-specific features. A real air-gap win; requires
  `django.contrib.postgres` in `INSTALLED_APPS`.
- **Background tasks are an open design decision** — since 6.4 Wagtail routes indexing and image
  work through `django-tasks`, which ships database and RQ backends but **no Celery backend**.
  Either accept in-request execution or write a `BaseTaskBackend`. Decompose explicitly; do not
  inherit the default by accident.
- **`ManifestStaticFilesStorage`** is recommended because admin assets change between releases —
  more than cosmetic under rolling updates.
- **`WAGTAILADMIN_LOGIN_URL`** (added 6.0, extended in 7.1 to cover logout) is the supported hook
  for putting the admin behind allauth's OIDC flow. Most community material on this predates the
  setting and describes URLconf-override workarounds — do not follow it.
- **OIDC users land with no groups**, and Wagtail's admin is gated on the `wagtailadmin.access_admin`
  permission rather than `is_staff`. A user will authenticate successfully and still be bounced.
  Mapping IdP claims onto a Django group holding that permission is required work with **no
  first-party guidance** — expect to write it. Pair with `WAGTAILUSERS_PASSWORD_ENABLED = False`
  and `WAGTAIL_EMAIL_MANAGEMENT_ENABLED = False` for an SSO-only estate.
