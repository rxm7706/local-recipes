---
title: "Convergence — pyforge-unifying-strategy"
chain: "pyforge-unifying-strategy"
created: "2026-08-24"
updated: "2026-08-24"
status: "ready"
---

# Convergence — what is already covered, and by what

Companion to `SPEC.md` (spec-pyforge-unifying-strategy). Computed against `main` @ `73291bd299`,
2026-08-24, per the repo's standing check-convergence-before-new-FR rule. Downstream reads this
to know which capabilities NOT to re-mint, which of the Dream's factual premises are wrong, and
which adjacent items this Spec deliberately does not absorb.

**This pass is also the chain's scoping instrument.** The Dream was written as though the Canopy
were greenfield; the audit found the host shipped. Per the operator decisions of 2026-08-24
(Dream § Realization log), the chain is an **extension binding `spec-python-agent-platform` as
prior art** — it mints nothing that duplicates CAP-1..6 — and within that boundary decomposition
is exhaustive.

## Already covered — do not re-mint

| Dream surface | Covered by | Evidence |
|---|---|---|
| The Django host itself, rendered from the accelerator shape | `spec-python-agent-platform` CAP-1; steward Story 10.1 (ledger `done`) | `src/platform/` is live: `manage.py`, `config/settings/base.py`, `platformapp/{users,templates,static,contrib}`. Import rule enforced — no `pyforge.*` under `src/platform/`. |
| Identity / OIDC SSO | CAP-1 + steward Story 16.5 (`done`) | `django-allauth` with `allauth.socialaccount.providers.openid_connect` in `INSTALLED_APPS`; no second auth framework, no local passwords. |
| Langflow as a pluggable app on an isolated schema | CAP-2; Story 11.1 (`done`) | `src/platform/langflow_integration/` with `asgi.py` dispatcher; `RunSQL` migration provisions `langflow_schema`; `search_path` carried on the connection string. **See RFC-5 conflict below.** |
| DB-GPT as a pluggable app on an isolated schema | CAP-3 + AD-6/AD-17 (Pattern B deviation, 2026-08-21); Story 11.2 (`done`) | `src/platform/dbgpt_integration/`; data migration provisions `dbgpt_schema`; Django ORM never crosses in. **See RFC-5 conflict below.** |
| Async work never blocking Django | CAP-4; Story 11.3 (`done`) | Celery + Redis broker wired in `config/settings/base.py`. |
| One factory-sourced environment | CAP-5; Story 10.2 (`done`) | `[feature.python-agent-platform]` pixi env pinning `python = "3.12.*"`, env-scoped. |
| Air-gap parity as a failing check | CAP-6; Story 12.3 (`done`) | Egress-blocked build+deploy is a CI gate, not a warning. |
| Vanilla Helm chart + OCP overlay, GKE portability, hardened Redis | CAP-1/CAP-6; Stories 12.1, 12.2, 12.6, 12.9 (all `done`) | `src/platform/deploy/charts/platform/`; image passes `restricted-v2` (arbitrary UID, no root). |
| The 15-factor baseline | `spec-platform-fifteen-factors` CAP-1..5; steward Epic 16 (`done`) | Pixi as sole dependency authority, two-stage startup validation, structlog + OTel, policy-as-test-suite. |
| Health probes for K8s | Story 10.1 + 11.1 (`done`) | `src/platform/config/fastapi_app.py` → `GET /api/health`; `/ht/` via `django-health-check`; probes wired in `deploy/charts/platform/templates/platform-deployment.yaml`. |
| One station portal, mounted and working | warden Stories 8-1, 8-2 (`done`) | `src/platform/compliance_face/` — async upload → warden engines via Celery → JSON report; mounted in `INSTALLED_APPS` and at `/compliance/` in `config/urls.py`. **This is the pattern the other seven portals follow.** |
| A role-isolated live-dashboard pattern | `spec-secure-live-dashboards`; steward Epic 9 (`9-1`..`9-7` all `done`) | `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/` — middleware, cache, filtering, export, audit trail. **Built, but never adopted — see residual.** |
| An MCP server, proving the pattern | atlas (shipped) | `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/server.py` `build_server()`. MCP is not greenfield; the residual is per-station reach, not the mechanism. |
| Shared stdlib primitives for the estate | `spec-pyforge-core` CAP-1..7; marshal Epic 14 (`done`) | `pyforge.core` ships `atomic_write`, `errors`, `verdict`, `report`, `process`, `landing_evidence`. **`client` is NOT among them — see residual.** |
| All-stations-in-one-image delivery | `unified-container` (dream `realized`); steward Epic 7 (`done`) | The Dream's "Mode A single all-in-one container" is this, already shipped. |

## Corrections — the Dream asserts things that are not true of this repo

Recorded here because acceptance criteria must not be written against a false premise.

1. **Lane 1 / the Guildhall is Marshal's, not Herald's.** Herald's own Spec makes this an explicit
   non-goal: *"Owning the console. The Guildhall is Marshal's ([[factory-console]]); Herald
   supplies its conviction and its look, not its machinery"*
   (`specs/spec-pyforge-herald/SPEC.md:137`). The live Guildhall is Marshal's static
   `docs/dashboard/` (`spec-factory-console`, `shipped`). Herald's own web surface is a shipped
   **React + Vite** app at `src/shared/packages/pyforge-herald/web/` (Epic 7 `done`) — not a CMS.
   Any Wagtail Lane 1 work therefore lands against **Marshal's** console ownership.
   **Resolved 2026-08-24: supersede.** CAP-2 retires the console rather than coexisting with it, so
   the handoff is a migration with a parity gate, and `spec-factory-console` is corrected in this
   chain's Phase 5. Herald's non-goal is unaffected — it never owned the console — and Herald's
   React web surface is out of scope entirely, being the Moments UI rather than Lane 1.
2. **Scribe is not SQLite.** BS-1 mandates a dual-driver engine on the premise that "local
   development uses SQLite". Scribe actually ships `FlatFileGraphStore` — a single JSON file at
   `.claude/data/pyforge-scribe/graph.json` (`graph_store.py`, Story 2-1 `done`). There is no
   SQLite driver to keep and no B-tree to corrupt; BS-1's remediation must be rewritten as
   "flat-file → PostgreSQL/pgvector", and its stated failure mode re-derived.
3. **Scribe's `recall` is lexical, not semantic.** `recall.py` is deterministic token overlap.
   The Dream's "semantic search" is a new capability, not a backend swap.
4. **FastAPI is not absent, it is in-host.** `src/platform/config/fastapi_app.py` is a real
   mounted sub-app. RFC-1's worker-pool split therefore modifies an existing seam rather than
   introducing FastAPI.
5. **`pyforge-atlas` already has MCP.** The Dream treats the MCP tier as uniformly unbuilt; atlas
   ships `build_server()`. The residual is the other seven stations plus the SSE transport.

## The RFC-5 conflict (operator-accepted, recorded here in full)

RFC-5 requires that Liquibase govern all PostgreSQL DDL estate-wide and that application
frameworks be *"strictly prohibited from generating runtime DDL alterations."*

Two **shipped, `done`** stories do exactly what it prohibits:

- **Story 11.1** provisions `langflow_schema` with a Django `RunSQL` migration.
- **Story 11.2** provisions `dbgpt_schema` with a Django data migration.

RFC-5 was accepted **as written** on 2026-08-24 and then **revised the same day**, once Phase-2
research established the literal directive is not implementable: `post_migrate` is the only
supported mechanism populating `django_content_type`, `auth_permission` and `django_site`, and
`create_test_db` builds every test database by running `migrate`. Either reopens both stories
regardless. `bmad-correct-course` decides the ledger shape (new superseding epic vs. reopening
Epic 11). `resilience-invariants.md` carries the binding form; the two questions below are settled
there rather than left to inherit:

- **Django's own built-in apps** (`auth`, `sessions`, `contenttypes`, `admin`, `allauth`) generate
  DDL through `django_migrations`. The revision resolves this by moving enforcement off the
  framework and onto the **database role** — the app role is DML-only and a separate migration role
  holds DDL — so the question stops being "which apps are carved out" and becomes "which role runs
  what", which an auditor can actually verify. **Test databases are carved out entirely.**
- **Ordering.** The revision puts `liquibase update` in a Helm **pre-upgrade Job**, explicitly *not*
  an init container: N replicas each running an init container contend on `DATABASECHANGELOGLOCK`,
  whose default wait is 5 minutes. Django's `migrate --fake` still runs afterwards so `post_migrate`
  fires. Story 12.1's chart contract is `done` and AD-4/AD-17 topology is HARD per
  `spec-platform-fifteen-factors`; the hook lands as a seam, not a chart rewrite.
- **Delivery vehicle is unresolved.** Liquibase is not on conda-forge. Whether it arrives as a
  feedstock or as the Job's container image turns on whether this repo's air-gap policy governs
  images at all — under research as of 2026-08-24, and CAP-9 cannot be scheduled until it lands.

## Adjacent-not-absorbed

- **Ledger rollup drift** — warden `epic-8` and `epic-7` read `backlog` while all their stories
  read `done`; mason epics 2–3 show the same shape. Pre-existing, cross-station, and not this
  chain's to fix; flagged so nobody mistakes a `backlog` rollup for remaining scope.
- **Atlas never adopted `spec-secure-live-dashboards`** despite being named its first adopter.
  `pyforge-atlas` imports nothing from `pyforge.steward.dashboard`. This chain's Lane 3 work
  *consumes* that pattern; making atlas adopt it is atlas's own story.
- **Steward Dreams without Specs** — `bmad-suite-install-class-wiring` and
  `ocp-as-a-portability-profile` both fail `dream-chain-check` today. Same station, unrelated
  chains, not absorbed.
- **Story 12-7** (live-cluster verification) is permanently `skip_on_blocked` pending a cluster.
  It gates verification of the Tier-3 chart items, not this chain's scope.
- **`bmad-drift-check` `pin-missing`** and 41 warnings are the pre-2026-08-24 baseline.
- **Marshal's `spec-factory-console` is absorbed as a correction, not as scope.** CAP-2 supersedes
  the console it specifies, so that spec must be retired — but the *console's own* remaining
  backlog, if any, is Marshal's and is not pulled into this chain. The correction says "superseded
  by CAP-2"; it does not adopt Marshal's open work.

## The residual this Spec binds (for cross-check)

Each line is evidence-confirmed absent, not assumed.

1. **Wagtail + CodeRed CMS Lane 1** — absent from `src/platform/`: not in `INSTALLED_APPS`, not in
   `pyproject.toml`, not in `requirements/`, and no StreamField block anywhere in the repo.
   *(Wagtail does appear 158× under `src/`, but exclusively as warden's conda-recipe test-corpus
   fixtures — `tests/fixtures/corpus/recipes/wagtail-*` — plus 4 hits in atlas package metadata.
   That is inventory, not platform code; it does usefully confirm the `wagtail-*` conda-forge
   ecosystem is packaged, which Phase 2 research should exploit.)* CodeRed dropped and Lane 1 set
   to **supersede** Marshal's console, both ruled 2026-08-24 — so this line now carries a retirement
   obligation as well as a build one. See Correction 1 and `Adjacent-not-absorbed`.
2. **`django-pyforge` shared package** — absent from `src/shared/packages/`; the App Switcher,
   OIDC middleware and Modernist theme layout have no home.
3. **Seven remaining station portals** + the `compliance_face → warden_portal` rename. One of
   eight mounted today; no `src/platform/portals/` directory exists.
4. **`services/` FastAPI + MCP tier** — no repo-root `services/`, no standalone FastAPI app
   outside `src/platform/`, no SSE/MCP transport for seven of eight stations.
5. **`pyforge.core.client`** — the shared data-contract SDK RFC-3 standardizes on. Not in
   `pyforge.core`, not in `spec-pyforge-core`'s CAPs, not in its non-goals.
6. **Unified `pyforge <station> <noun> <verb>` CLI** — no `pyforge` entry point in any
   `pyproject.toml`; eight per-station scripts (`marshal`, `herald`, `warden`, …) exist instead.
7. **Vizro Lane 3 behind the host** — atlas's Vizro dashboard is a build-time object with no
   server task and no reverse proxy; `src/platform/config/urls.py` has no atlas route.
8. **Redis Streams event fabric** — Redis is present for Celery and cache only; no `XADD`/
   `XAUTOCLAIM`, no CloudEvents envelope, no DLQ, no loop-depth ceiling (RFC-4, BS-6).
9. **RFC-1** worker-pool separation over the existing in-host FastAPI seam.
10. **RFC-2** `redis-broker` (`noeviction`) split from `redis-cache` (`allkeys-lru`).
11. **RFC-3** signed internal JWT delegation with `delegated_by` claim (BS-3, RFC 8693).
12. **RFC-5** Liquibase DDL governance, including the Epic 11 retro-fit — see conflict above.
13. **BS-1** scribe flat-file → PostgreSQL/pgvector, premise corrected per Correction 2.
14. **BS-2** SSE keep-alive frames + 30m OCP route timeout.
15. **BS-4** PyBreaker circuit breaking — no `pybreaker` import anywhere in `src/`.
16. **BS-5** DuckDB single-writer discipline — production code calls bare `duckdb.connect()`;
    no `read_only=True` on any DuckDB file handle.
17. **BS-7** `PydanticFormErrorBridge` for inline HTMX 422 mapping.
18. **BS-8** idempotent startup reconciliation — no MinIO/S3 in `pyforge-mason` at all.
19. **Keycloak RBAC matrix**, **HashiCorp Vault**, and **OpenFeature canary delivery** — none
    present in `src/platform/` or any station package.
20. **Tiers 4 and 5 of the Dream's own 5-tier symmetry**, caught on the Spec's preservation pass
    rather than in the first sweep. **Domain skills: one of eight** — `conda-forge-expert` is
    mason's and proves the shape; the other seven stations have none, and no station package
    carries a `skills/` directory. **Agent personas: zero of eight** — the five `bmad-agent-*`
    skills are BMAD roles (analyst, architect, dev, pm, ux-designer), not station personas. Bound
    as CAP-15 and CAP-16.
