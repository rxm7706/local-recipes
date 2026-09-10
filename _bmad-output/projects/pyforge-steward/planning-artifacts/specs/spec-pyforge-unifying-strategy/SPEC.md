---
spec: pyforge-unifying-strategy
status: ready
chain: pyforge-unifying-strategy
created: "2026-08-24"
updated: "2026-09-10"
companions:
  - convergence.md
  - resilience-invariants.md
  - stack.md
  - architecture-diagrams.md
  - console-parity-inventory.md
  - ../../research/technical-pyforge-unifying-strategy-research-2026-08-24.md
  - ../../research/technical-pyforge-unifying-strategy-airgap-delivery-2026-08-24.md
  - ../../research/technical-pyforge-unifying-strategy-dependency-currency-2026-08-24.md
  - ../../research/technical-pyforge-unifying-strategy-mcp-runtime-2026-08-24.md
  - ../../research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md
  - ../../research/currency-review-pyforge-unifying-strategy-2026-09-09.md
  - ../../research/fleet-readiness-decision-batch-2026-09-09.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
owner-dream: docs/dreams/pyforge-unifying-strategy.md
surface:
  - src/platform/**
  - src/shared/packages/django-pyforge/**
  - src/shared/packages/django-*/**
  - src/shared/packages/pyforge-core/**
  - src/shared/packages/pyforge-scribe/**
  - src/shared/packages/pyforge-atlas/**
  - .claude/skills/pyforge-*/**
  - recipes/openfeature-*/**
  - recipes/liquibase/**
  - pixi.toml
  - environment.yaml
sources:
  - ../../../../../../docs/dreams/pyforge-unifying-strategy.md
open_questions:
  - "realization-gate-home: Epic 49 binds on this chain today (operator 2026-09-09: 'Unifying now, re-home later'); it re-homes to hub:CAP-* on spec-intelligence-hub by memlog once the operator's reading of 'align' lands and that Spec reaches ready. Story text does not change."
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete,
> preservation-validated contract for what to build, test, and validate. The Dream in `sources:`
> carries the decision trail — ten operator rulings dated 2026-08-24, the RFC/blind-spot
> derivations, the pre-audit architecture prose this contract deliberately compresses, and
> Grounding dated 2026-08-25 (fleet drain + attended CRC) and closeout 2026-08-26
> (`/` 200, CAP-9 proven). Correct-course:
> `sprint-change-proposal-2026-08-25-drain-bind.md` then
> `sprint-change-proposal-2026-08-26-canopy-closeout.md`. Evergreen reopen:
> `sprint-change-proposal-2026-08-26-query-plane.md` (CAP-19) then
> `sprint-change-proposal-2026-08-26-evergreen-ready.md`. This Dream/SPEC
> pair is living; CAP-1..18 closeout is a dated slice, not the end of the contract.
> **2026-08-26 first slice shipped:** Epic 34.1–34.5, Lane 3 36.1–36.2
> (`estate-cache`), five-tier 37.1 (40/40; mason = `conda-forge-expert`).
> Sibling Epic 35.1 is `spec-mcp-era-isolation` CAP-4, not this CAP set.
> Residual: **see § Residual (2026-09-09)** — the three 2026-08-26 `open_questions` were answered
> (see § Open Questions); the currency review reopened the residual. Do not re-dispatch 18–37.

> **Host contract merged 2026-09-10 (Story 48.8).** Cite host capabilities as
> **`pap:CAP-1`..`pap:CAP-6`** and host spine as **`pap:AD-1`..`pap:AD-17`**
> (same fully-qualified grammar as `marshal:AD-8`). Bare `CAP-1`..`CAP-19` in *this* file are
> Unifying Strategy only. Do not re-mint `pap:CAP-*`. `convergence.md` is the split.
> Pixi feature/env id stays `[feature.python-agent-platform]` until a named rename story.
> CAP-9 reopened shipped DDL stories; CAP-19 reopens shipped analytical stores (Atlas RAG
> writer, Scribe 28.x, agent DSNs) by operator ruling 2026-08-26.
> **`pap:` stays a live id prefix** — the merge moved text here; the namespace is unchanged.
> `spec-python-agent-platform` is superseded; spine detail remains in its ARCHITECTURE-SPINE
> companion (`pap:AD-1`..`pap:AD-17`).

## Host platform (`pap:CAP-*`) — merged from spec-python-agent-platform

**Qualified ids (cite these from anywhere outside this section):** `pap:CAP-1` … `pap:CAP-6`.
Bare `CAP-n` below is the local heading in this file only. Unifying Strategy's `CAP-1` is
`django-pyforge`, not this CAP-1. Pixi env id stays `python-agent-platform`.

- **pap:CAP-1 — The host renders from the accelerator shape.**
  - **intent:** A cookiecutter-django service with FastAPI integration is the platform's one
    control plane: `env()`-split settings, health endpoints wired to K8s liveness/readiness
    probes, mirror endpoints (conda/pypi/registry) parameterized at render time per
    django-accelerator-framework's air-gap entry, vendored zero-CDN static assets.
  - **success:** The rendered host boots against PostgreSQL + Redis with no other
    infrastructure, passes its probes on K8s, and a render pointed at internal mirrors
    produces an image with zero external-network references.
- **pap:CAP-2 — Langflow joins as a pluggable Django application.**
  - **intent:** Pattern A of langflow-django-plugin: ASGI mount forwarding `/api/v1/`,
    `/health`, `/langflow/`; `langflow_schema` isolation made real via `RunSQL` migration +
    `LANGFLOW_DATABASE_URL` `search_path` suffix; no local-disk state.
  - **success:** Langflow flows execute through the mounted app with its tables confined to
    `langflow_schema` (verified by schema inspection), and killing/replacing the pod loses no
    state.
- **pap:CAP-3 — DB-GPT joins the platform through its configured integration pattern.**
  - **intent:** DB-GPT integrates via whichever pattern pap:AD-17's per-engine config switch
    selects — Pattern A of db-gpt-django-plugin (ASGI-mounted, in-process) by default, or
    Pattern B (Celery-dispatched sidecar, `docker-compose.yml`-managed) where Pattern A is
    demonstrably not pluggable (pap:AD-14). As of 2026-08-21, DB-GPT is configured to Pattern B —
    `dbgpt-app`'s `fastapi<0.113.0` ceiling is disjoint from `langflow-base`'s
    `fastapi>=0.135.0` floor in the shared environment, confirmed live. `dbgpt_schema` in the
    shared PostgreSQL is provisioned by Django data migration (Django ORM never crosses in;
    DB-GPT's Alembic never touches `public`) and pgvector lives there if a vector store is
    needed — that part of the storage rule holds regardless of pattern. **DB-GPT's own
    `service.web.database` metadata store (chat history, knowledge/RAG, flow/plugin configs)
    is the bounded AD-6 exception**, dated 2026-08-21: `dbgpt-app` structurally cannot use
    PostgreSQL for it (confirmed live: connector-type rejection, SQLite-only migration path,
    MySQL-only column DDL), so it stays on SQLite behind a dedicated Kubernetes
    `PersistentVolumeClaim` instead — never in `dbgpt_schema`, never on ephemeral local disk.
  - **success:** Text-to-SQL / data-chat round-trips succeed end-to-end through whichever
    pattern is configured; `dbgpt_schema` state (Django-provisioned, pgvector) loses nothing on
    pod/container replacement; DB-GPT's own metadata store survives a kill-and-restart via its
    PVC (Story 10.5's two-boot persistence test), not via PostgreSQL. Switching DB-GPT's
    configured pattern later requires no code change, only a registry update (pap:AD-17); the AD-6
    exception is independent of that switch and stays scoped to `dbgpt-app`'s own metadata
    store regardless of pattern.
- **pap:CAP-4 — Async work never blocks Django.**
  - **intent:** Celery over Redis carries LLM/AWEL work (the plugin dreams' Pattern B/D
    element); workers call the engines in-process or over the internal network, never through
    the public edge.
  - **success:** A long-running agent task completes via the worker path while the host stays
    responsive; the task's failure mode (timeout/partial result) is named and handled.
- **pap:CAP-5 — One environment, factory-sourced, 3.14-bound.**
  - **intent:** The platform's environment is a single conda-space solve from mirrored
    conda-forge (langflow, dbgpt, dbgpt-serve, django + host deps) — pinned, locked, and
    rendered into the container build; python 3.14 compatibility is a tracked gate with the
    bcrypt pin as its named prerequisite (open question 3 sequences it).
  - **success:** The lockfile solves reproducibly from a mirror-only channel config; the 3.14
    gate flips green the release after the bcrypt prerequisite clears.
- **pap:CAP-6 — Air-gap parity is a test, not a hope.**
  - **intent:** Every deployment artifact resolves inside the boundary: internal-registry
    images, mirrored indexes, zero-CDN assets, env/secret-mount credentials (BuildKit
    `--mount=type=secret` at build time; K8s secrets at run time), internal-CA trust.
  - **success:** A build + deploy executed with external egress blocked succeeds end-to-end;
    any external reference is a failing check, not a warning.

Spine: `pap:AD-1`..`pap:AD-17` = host ARCHITECTURE-SPINE companion (same as **parent AD-n**).
Unifying spine IDs are **canopy AD-n** (prefix only; the product is Foundry Platform).
Qualify every citation; bare `AD-n` in epics is a review fail.


## Absorbed (`daf:CAP-*`) — the Django accelerator contract

**Absorbed 2026-09-09** (fleet readiness § 2.3 **C3**, operator-approved) from
`_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-django-accelerator-framework/SPEC.md`
(`status: draft`, owner mason), whose frontmatter now reads
`absorbed-into: spec-pyforge-unifying-strategy` and whose owner Dream
`docs/dreams/django-accelerator-framework.md` is `archived` / `archived-reason: absorbed`.
Its ids are qualified **`daf:CAP-n`** on arrival — exactly as `pap:` is — so no bare `CAP-n`
collides with this file's own CAP-1..19 (the namespace rule Story 48.7 exists to enforce).

| Qualified id | Source CAP | Disposition |
|---|---|---|
| `daf:CAP-1` | DAF CAP-1 — the accelerator contract (REAL now) | **Absorbed, below.** Its first realization is `pap:CAP-1`'s `src/platform/` render (Story 10.1, on main 2026-08-14); its second reference shape is Steward's dashboard. |
| `daf:CAP-2` | DAF CAP-2 — the templating engine (CONTINGENT) | **Not absorbed — falsified and closed.** The counting trigger ("a third/fourth Django surface repeats the copy by hand") never fired the way it was written: the estate reached **nine** Django faces and factored `PortalConfig` instead (`django-pyforge`; eight portals with ~10 declarative fields, one `manage.py`). The engine is not parked here; it is not wanted. Its open question — repo-wide vs estate-wide counting — dies with it. |

### `daf:CAP-1` — the accelerator contract

*Intent.* A named, documented shape — **the accelerator contract** — that any PyForge Django
surface renders to. Its clauses:

- cookiecutter-django base **with FastAPI integration** (an ASGI seam owning the API namespace) —
  live at `src/platform/config/asgi.py`;
- `env()`-helper / **split settings** — `config/settings/{base,local,production,test}.py`;
- **`/ht/` django-health-check endpoints** wired to K8s liveness/readiness probes —
  live at `src/platform/config/urls.py:98`, mounted as
  `HealthCheckView.as_view(checks=["health_check.Database", "health_check.Cache"])`
  (import at `urls.py:11`). *(Citation corrected on absorption: the mason copy still cited
  `config/urls.py:26` `include("health_check.urls")`; `urls.py:50-55` records that
  `include(...)` form as **deprecated** — django-health-check 4.x has no `health_check.urls`
  module at all, and the `checks` list must be dotted strings, never imported classes.)*
- **mirror endpoints** (conda / pypi / registry) parameterized at render time;
- **vendored zero-CDN static assets** (Bootstrap 5.3 + HTMX shape);
- auth bound to an **internal OIDC IdP** — the provider is named by Story 48.9.

*Success.* The contract is documented here, and both existing surfaces verifiably conform to the
clauses applicable to each **or carry dated deviations**. One asymmetry is recorded rather than
papered over: Steward's dashboard predates the contract and embodies the identity-at-the-boundary
and adopter-declaration clauses (`middleware.py`, `declarations.py`), not the full render shape.

*Constraints carried in.* **Air-gap parity** (Artifactory coordinates are first-class render-time
substitutions across `pyproject.toml`, `pixi.toml`, Helm charts and CI workflows; every
pip/conda/pixi install resolves from mirrored indexes only; frontend assets vendored with zero CDN
`<script>`/`<link>` in base templates, applied at authoring time and never as a later patch; all
runtime config through env/secret mounts, never committed; no external identity callbacks) — this
is the same obligation as `pap:CAP-6`, and the two are one check, not two. **The platform is the
living exemplar:** the contract must never drift from what `src/platform/` actually ships — when
contract and render disagree, either the render gains a dated deviation or the contract is
amended, never silent divergence.

*Non-goals carried in.* Not an engine build. Not an import of the WF source's FreeMarker
templates, Jenkins wiring, or three-repo pipeline — if a stamping engine is ever wanted, its
templates are **extracted from the proven local shapes**, never imported. Not a new station.

*Note for Story 48.8.* This absorption **precedes** the Single-Spec merge and is independent of
it: DAF pointed at `spec-python-agent-platform` in its `sources:` and deferred the platform's own
build contract to it, so absorbing DAF here rather than into a Spec that 48.8 supersedes avoids a
two-hop pointer into a superseded parent.

# pyforge-unifying-strategy — Foundry Platform mounts the eight stations

## Why

**A vision to realize, with a mandate riding on it.** PyForge is eight capability stations that
each shipped as an excellent command-line tool and stopped there. An operator who wants to see
compliance findings, package health, fleet status and build queues holds eight terminals and no
shared identity, no shared vocabulary, and no way for one station to tell another that something
happened. Foundry Platform — `src/platform/` — proved the shape works. **The 2026-08-24–25 canopy drain
landed the extension in code** (chrome, eight portals, host MCP faces, CLI dispatch, events,
flags, governed-DDL *path*, five-tier check, CAP-18 hooks). Steward **12-7 `/ht/` 200** is
dated. Closeout 2026-08-26: Lane 1 `/` **200** on CRC, CAP-9 `platform_app` DML-only
proven, Liquibase `:17`–`:19` executed. Parked outside this CAP set: Q5 scorecard (sibling Dream), MCP slice 3,
optional 12.9 CI. MCP cluster fail-loud is **sibling** `spec-mcp-era-isolation`
CAP-4 / steward Epic 35 — not a unifying CAP. **CAP-19 (query plane) is in this chain** — minted 2026-08-26;
first slice **shipped 2026-08-26** (Epic 34 + Lane 3 `estate-cache`). All OQs answered 2026-08-26.
CAP-1..18 closeout stands. Not a `services/` rewrite.

The mandate riding on it is governance: an air-gapped, regulated deployment target needs schema
change to be auditable rather than incidental, identity to be revocable rather than cached, and
failure to be contained rather than cascading. Those are the RFC and blind-spot directives, and
they are why this is not merely a UI project.

## Capabilities

- **CAP-1 — `django-pyforge`, the shared chrome.**
  - **intent:** One installable Django app supplies the chrome every station portal mounts — the
    app switcher, an OIDC-aware base layout, the Modernist theme assets, and the registration seam
    a portal uses to join the host.
  - **success:** Two portals render identical chrome from that one package with zero duplicated
    template or static files, proven by a test that fails if either portal ships its own copy.
  - *(Correct-course 2026-08-24, operating-model Q3. The registration seam also carries owner
    station slug, backup, `work_class`, and promotion date so Guildhall can refuse to tile 01/02
    work. The SLA body is not a CAP-1 field — it stays in the 03 BMAD spec until Doctor or
    Guildhall evaluates it. Never: a Steward SLA microservice. Never: Marshal stores SLAs.)*

- **CAP-2 — Lane 1 is CMS-managed, and it is the only front door.**
  - **intent:** A public front door at `/` whose pages are edited and published without a code
    deploy, with its admin reachable only through the estate's identity provider. It **supersedes**
    the estate's existing statically-built console, which is retired rather than kept alongside.
  - **success:** An editor publishes a page change with no deploy; an unauthenticated request to the
    CMS admin is redirected to the IdP rather than to a local login form; and every view the retired
    console offered is reachable from the new front door, with the old build path removed rather
    than merely unlinked.
    **Live proof (CRC 2026-08-26):** default Site + published `HomePage`; `GET /` **200**
    (`PyForge Lane 1 — published from PostgreSQL.`); unauthenticated `GET /cms/` **302**
    to `/accounts/oidc/oidc/login/?next=/cms/`. Seed:
    `platformapp.front_door.lane1_seed.seed_lane1_homepage` on `post_migrate`.

- **CAP-3 — Eight portals, one session.**
  - **intent:** Every station is reachable as a Lane 2 application under the one host, so an
    operator moves between stations without re-authenticating or changing origin. Each portal is a
    **reusable Django app** in its station's own distribution, not an app in the host project.
  - **success:** All eight portal URLs resolve behind a single session, and adding or removing a
    portal changes no host code outside that portal's own registration.
  - *(Correct-course 2026-08-24, operating-model Q7. Lane 2 contract is HTMX. DRF JSON:API is
    not a portal face — it stays on the Atlas / enterprise-data-models kinship. Compute JSON
    is FastAPI via CAP-6's client.)*
  - *(Absorbed 2026-09-09, fleet readiness C3: the **shape** a Lane-2 surface renders to is now
    stated in this file as `daf:CAP-1` — see § Absorbed. `PortalConfig` in `django-pyforge` is
    what falsified DAF's CAP-2 counting trigger: nine Django faces were reached by factoring a
    declarative registration, not by repeating a hand-copy nine times, so no templating engine
    is wanted.)*

- **CAP-4 — Every station has a service face.**
  - **intent:** Each station exposes its capabilities to programmatic and agent callers over a
    current-specification MCP endpoint **on the host ASGI** (`POST /stations/<name>/mcp`), with
    long operations surviving connection loss. **Not** a `services/` process-per-station topology.
  - **success:** An agent completes a multi-minute station operation across a simulated ingress
    disconnect and still retrieves the result.
  - *(The criterion is deliberately stated as an outcome, not a mechanism. The MCP Tasks extension
    would be the natural vehicle and has no server-side runtime to build on — so binding the
    capability to Tasks would block it on upstream. See the `start`/`get` constraint below.
    Drain 2026-08-25: eight faces mounted; atlas-only `start`/`get` on 21.3 — do not re-mint the
    mounts.)*

- **CAP-5 — One command grammar.**
  - **intent:** A single entry point dispatches `pyforge <station> <noun> <verb>` to the eight
    existing station CLIs without reimplementing their logic.
  - **success:** A generated parity matrix shows every station verb reachable through both the
    unified entry point and its own binary, and the build fails when the two diverge.

- **CAP-6 — One client, carrying identity.**
  - **intent:** Portals reach their station services through a shared client that carries the end
    user's identity as a signed, audience-bound assertion rather than a trusted header.
  - **success:** A service can independently verify which end user a portal call was made on behalf
    of, and no portal constructs a raw HTTP request to a service.

  - *(Correct-course 2026-09-02, red-team X-1 / R-1 → Story 40.1: the host mint MUST
    verify the presented IdP bearer — signature via the configured JWKS, `iss`, `aud`,
    `exp` — before signing. Never: a decode-only bearer path, in any profile.)*

- **CAP-7 — Analytics behind the front door.**
  - **intent:** Atlas's analytical boards are reachable through the host with per-tenant row
    isolation enforced at the identity boundary, adopting the estate's existing secure-dashboard
    pattern rather than a second one.
  - **success:** Two users with different roles request the same board URL and provably receive
    different row sets.

- **CAP-8 — Stations can tell each other things.**
  - **intent:** A durable event backbone carries structured events between stations, with
    consumer groups, poison-message quarantine, and a ceiling on cascade depth.
  - **success:** A poisoned event lands in the dead-letter queue instead of retrying forever, and a
    cyclic publish chain halts at the declared depth rather than running away.
  - *(Correct-course 2026-08-24, operating-model Q4. Envelope fields for work
    identity are `spec_id`, git sha, SBOM purl, and optional work-item id. Jira
    is a steward-profile adapter, not a required CloudEvents field. Never:
    reject or drop an event for lack of a Jira key.)*

- **CAP-9 — Schema change is governed, not incidental.**
  - **intent:** Production schema change flows through one auditable authority, enforced by
    database privilege rather than by convention, while the application's own tooling remains the
    place a developer authors a change.
  - **success:** The application's database role provably cannot execute `CREATE`, `ALTER` or
    `DROP`, and a schema change authored without a corresponding governed changeset fails the
    build. *(Reopens shipped work — see Constraints and `convergence.md`.)*
    **Live proof (CRC 2026-08-26, not a new CAP):** `platform_app` exists; `:2` EXECUTED;
    `/api/health` **200** as that role; `CREATE` on `public` refused. Schema `liquibase` and
    contrib/auth/Wagtail `:15`–`:19` are in the changelog. Isolated `mfa` sqlmigrate stays
    fake. `/ht/` 200 is steward **12-7**. See
    `sprint-change-proposal-2026-08-26-canopy-closeout.md`.

- **CAP-10 — Failure is contained.**
  - **intent:** A failing dependency degrades its caller instead of cascading, concurrent writers
    cannot corrupt shared analytical state, validation errors reach the user inline, and a restart
    reconciles rather than duplicates.
  - **success:** Each of the four invariants in `resilience-invariants.md` has a test that fails
    with the invariant absent and passes with it present — demonstrated individually, not as a
    suite.

- **CAP-11 — Queue and cache cannot evict each other.**
  - **intent:** The task broker and the cache are separate resources with separate eviction
    policies, and the web and worker pools scale independently.
  - **success:** Filling the cache to its eviction limit provably loses no queued task.

  - *(Correct-course 2026-09-02, red-team S-1 / A-3 / R-2 → Story 40.2: the broker is
    durable (AOF on a PVC) and bounded (`maxmemory` below its memory limit, `noeviction`).
    A broker restart loses no queued task, stream entry, pending entry, DLQ entry or
    applied-id key. Never: `noeviction` without `maxmemory`; `emptyDir` for the broker.)*

- **CAP-12 — Access is revocable and secrets are delivered.**
  - **intent:** Portal authorization derives from identity-provider roles rather than
    locally-managed state, and runtime secrets arrive from a secret manager rather than the pod
    environment.
  - **success:** Revoking a role at the IdP removes portal access on the user's next request, and
    no long-lived secret value appears in any pod specification.

- **CAP-13 — Behaviour flips without a redeploy.**
  - **intent:** Django, service and CLI surfaces evaluate feature flags through one vendor-neutral
    interface, entirely offline.
  - **success:** One flag change alters behaviour across all three surfaces with no egress and no
    redeploy.

- **CAP-14 — Scribe's graph outlives one file.**
  - **intent:** The knowledge graph gains a durable, concurrent-safe backing store behind its
    existing port, keeping a local-development path, and gains semantic recall.
  - **success:** The same graph operations pass against both drivers, and semantic recall returns
    a relevant result that lexical token-overlap recall does not.

- **CAP-15 — Every station teaches an agent its own work.**
  - **intent:** Each **03** station capability carries an agent-loadable domain skill encoding how
    that station's work is actually done, following the shape one station already proves. 01/02
    work may stop at a spec + script or spec + skill and does not mint a station skill.
  - **success:** An agent asked to perform a station's core **03** task loads that station's skill
    and follows it, demonstrated for a station that has no skill today.
  - *(Correct-course 2026-08-24, operating-model Q2. Five-tier completeness is the 03 shape, not
    a mandate to build skill+persona+portal for every task.)*
  - *(Realization 2026-08-26, Epic 37.1. Roster declared complete — 40/40. Mason's
    skill cell is `conda-forge-expert`; there is no `pyforge-mason/` skill.)*

- **CAP-16 — Every station can be addressed as a persona.**
  - **intent:** Each **03** station capability exposes an autonomous persona that acts through that
    station's own command grammar and service face rather than through ad-hoc tool calls. 01/02
    work does not mint a persona.
  - **success:** A persona completes a station **03** task end to end using only CAP-5's grammar and
    CAP-4's service face, with no direct filesystem or ad-hoc HTTP access in the transcript.
  - *(Correct-course 2026-08-24, operating-model Q2. Same scoping as CAP-15.)*
  - *(Correct-course 2026-08-24, operating-model Q6. Path B is this persona + the Agent Canopy.
    Tachyon is a production LLM provider adapter, not a persona and not a rename of CAP-16.)*

- **CAP-17 — Run state is a service, not a local filesystem read.**
  - **intent:** In-flight execution state — which runs are live, how long they have been going, and
    the timing history behind them — is published by a supervisor the front door can query, rather
    than scraped from an operator's local disk at generation time.
  - **success:** The front door displays live run state in a deployed, egress-blocked namespace
    with no access to any operator's home directory, and a completed run's timing survives the
    workstation that produced it.
  - *(Added 2026-08-24 by operator ruling. The retired console read `~/.bmad-loops`, tmux sessions
    and journal files directly, so three of its surfaces degraded to `unavailable` when published.
    Choosing to keep those surfaces is what makes this a capability rather than an answered
    question — see `console-parity-inventory.md`.)*

- **CAP-18 — One hook-spec and plugin-registration shape.**
  - **intent:** Eight stations do not invent eight plugin APIs. A shared contract in
    `pyforge-core` names how a process publishes hook specifications and how a plugin
    registers to implement or replace a layer. Warden owns the PR-gate hook book on that
    contract; each station owns its process hooks (build engine, runner, store, exporter,
    deploy profile, LLM provider). Kedro names the spec-vs-plugin split; it does not
    require every station to be a Kedro project. **Not the scorecard** (no board, no
    unpublished measures).
  - **success:** A dummy plugin loads through the shared registration API; a station
    package that ships a second registration mechanism fails the check; today's backend
    is the default plugin for that process; a default Warden run stays green with no
    named commercial scanner plugin present.
  - *(Correct-course 2026-08-24, later the same day. Operator: this is the missing
    story — it does not exist in Canopy 18–30. Those epics stay chrome/portals/MCP/DDL;
    they must not violate this capability. Drain: Epic 32 + peer hook stories **landed**;
    do not re-mint a second plugin API.)*

- **CAP-19 — One HTAP query plane; stations are clients.**
  - **intent:** Analytics, vectors, and agent SQL share one DuckDB engine: live
    read-only Postgres attach, Kedro-written Parquet cache, `vss` / HNSW.
    Domain ports stay (Scribe store port, Atlas catalog prefixes, BSL
    metrics). Private stores (in-memory RAG, Chroma for estate knowledge,
    autonomous SQL on OLTP) are rebuilt onto the plane. canopy:FR-27's *writer*
    intent applies to the plane; the filename `atlas.duckdb` may be
    generalized. Rebuild of shipped 25.2 / 28.x / agent DSN wiring is in
    scope.
  - **success:** A fixture multi-schema Postgres with no `pgvector` is attached
    read-only; Kedro writes a Parquet cache on a *named* pipeline; HNSW
    ranking runs on the plane; DB-GPT / Langflow estate reads use the plane
    DSN or HTTP face, not the OLTP DSN; Scribe semantic recall hits the plane
    (or a store-port driver that is the plane) and still satisfies canopy:FR-36.
    Tests fail if a second writable analytical engine or an agent OLTP DSN
    is reintroduced.
  - *(Minted 2026-08-26, operator: evergreen Dream; SPEC may return
    in-progress; rebuild is allowed. First slice shipped the same day:
    34.1–34.5 + 36.1–36.2. OQs closed 2026-08-26: both faces, one boot
    script (Mosaic committed); named new pipeline; dual-write.
    Not a ninth station. Atlas owns the
    engine; steward owns the through-line.)*

## Constraints

- **Always:** `pap:CAP-1..6` (§ Host platform) are shipped and binding. `convergence.md` decides
  which side of the line a surface falls on.
- **Always:** Django `>=5.2.17,<6` and Python `3.14.*` (43.6, 2026-09-03; the Django bump `daa35ee171` 2026-08-29; both corrected here 2026-09-09). Django 6 is unavailable. conda-forge ships
  exactly one qualifying build, two security patch releases behind upstream. **Audited 2026-08-24:
  5.2.16 and 5.2.17 carry seven CVEs, one rated high — and every affected path is unreachable here
  (no `contrib.gis`, no cache middleware, no `URLField`, no `set_language` route). A currency gap,
  not a live exposure.** The earlier claim that no feedstock maintenance branch exists was **wrong**:
  `django-feedstock` carries a `5.x` branch registered in `abi_migration_branches`, and this repo's
  maintainer authored the 5.2.15 bump on it. Catching up is a one-file version+sha256 PR, so the pin
  should move to `>=5.2.17,<6` — scanners key on version strings, not reachability, and an SBOM
  declaring seven unremediated CVEs is a finding regardless.
- **Always:** every **Python/pixi** dependency resolves from conda-forge. The egress-blocked build
  is a gate, not a warning; a PyPI-only package is new feedstock work and must be scheduled as such.
  This governs the dependency graph, not every artifact in the namespace — container images are
  governed separately by `pap:CAP-6`, which already admits third-party
  images (`postgres:17`, `redis:7`) under the internal-registry rule. Neither boundary is optional
  and neither substitutes for the other.
- **Always:** infrastructure is exactly PostgreSQL + Redis + Kubernetes. A component demanding a
  fourth backing service has failed its design review. DuckDB is a **library / query face**
  (in-process or an optional `duckdb-server` process on the platform image), not a fourth
  Helm backing store.
- **Exception (dated 2026-09-10, AD-1 object storage).** An S3-compatible object store is
  permitted as a **consumed**, never **self-hosted**, backing service — the same shape
  `canopy:AD-19` already trusts for the identity provider (pod specs / application config carry
  an endpoint URL and credentials only; no object-storage server process ships inside the
  platform image or Helm chart). Production target: NetApp StorageGRID, ops-provided and
  externally operated. This does not reopen Lane 1 media's own 2026-09-05 re-affirmation (RWX
  PVC stands); it authorizes object-storage consumption for capability that specifically needs
  S3 API semantics, decided story-by-story, never assumed. Self-hosting MinIO, Silo, Garage, or
  any object-store server inside the deployed platform remains forbidden without a further,
  separately-justified exception. See
  `sprint-change-proposal-2026-09-10-ad-1-object-storage-exception.md`.
- **Always:** CAP-19 is one analytical engine and one writer (canopy:FR-27 intent). `ATTACH` joins
  sources; it does not mint a second writable `.duckdb`. Consumer paths `LOAD` `postgres`
  and `vss`; they never `INSTALL` on boot (AD-13). Autonomous SQL is cache-and-view only.
  Mode A is declared operational views for humans, not DB-GPT exploring OLTP.
- **Always:** CAP-19 extract/transform is Kedro on a **named** Atlas pipeline (or an
  explicit reopen of the closed set). Not a silent `01_raw` tree. Not Airflow.
  Federation does not pull OLTP through pandas. Kedro is **optional** for new
  extracts; Atlas is the one Kedro *home* (canopy:AD-21). Not eight Kedro projects.
- **Always:** Lane 3 is Vizro over BSL over the plane (after 34.2). `vizro-ai`
  is deprecated. Do not import Kedro or Vizro into Django views.
- **Never:** a station or agent opens a private DuckDB, Chroma, or the OLTP DSN for
  estate knowledge or Text-to-SQL after CAP-19 lands. Platform Postgres remains the
  OLTP / app-state store. Scribe's **store port** remains (*2026-09-09: a `GraphStore` Protocol
  now exists at `pyforge-scribe/.../graph_store.py:59` with three drivers — see § Residual*; as written 2026-08-24: no `GraphStore` class
  exists in `pyforge-scribe` today).
- **Never:** `django-lasuite` on the host (`INSTALLED_APPS` or OIDC). Identity is
  `django-allauth`. Chrome is `django-pyforge`. Feedstock / `suite-*` recipes are
  packaging only.
- **Always:** `src/platform/` consumes the factory's published conda packages and never imports
  `pyforge.*` source. The factory/platform boundary is an import rule.
- **Always:** statelessness holds — replicas are capacity, any pod is disposable. This rules out
  pod-local media storage for CAP-2 and per-process caches for CAP-3.
- **Always:** CAP-9 reopens shipped stories 11.1 and 11.2, which provisioned schemas through Django
  migrations. `bmad-correct-course` decides the ledger shape; the correction is not optional.
- **Always:** CAP-2 retires Marshal's shipped console. Feature parity is proven **before** the old
  build path is removed, and `spec-factory-console` is corrected in the same chain — a superseded
  spec left claiming ownership is a worse outcome than two consoles.
- **Always:** CAP-9 cannot remove Django's `migrate` from the deploy path. `post_migrate` is the
  only supported mechanism populating content types, permissions and sites, and the test runner
  builds every test database by running `migrate`. **Test databases are carved out of CAP-9
  entirely.**
- **Always:** CAP-4's keep-alive interval stays well under 30 seconds. OpenShift's `timeout client`
  is cluster-wide with no per-route override, and HAProxy governs streaming responses by
  `timeout client`/`timeout server`, not `timeout tunnel`. A route timeout annotation is
  defence-in-depth, never the mechanism.
- **Always:** service faces accept **`2025-03-26` through `2026-07-28`** — four handshake revisions
  plus the modern one. Pinning to the modern revision alone would reject most of the current client
  fleet; omitting it rejects Codex, which already sends it.
- **Never:** a server asserts its own newest revision in an `initialize` response. It **echoes the
  client's requested revision** whenever it can serve it. A client that receives a revision it has
  never heard of aborts — *even when that revision is newer* — so asserting the newest is a
  self-inflicted rejection.
- **Never:** behavior is selected from the client's name or user-agent. Only the declared protocol
  revision decides. Sniffing becomes tempting mid-migration and is always wrong.
- **Always:** CAP-4's disconnect-survival is delivered as a **`start`/`get` tool pair over a durable
  store**, not via the MCP Tasks extension. Tasks is Final as SEP-2663 but has **no server-side
  runtime in the official SDK**, and the only implementation anywhere is a beta on an unreleased
  FastMCP 4, absent from conda-forge. The pair implements SEP-2663's own lifecycle, so adopting the
  extension later is a wire-layer swap over the same store. `start` must not hold the connection —
  which also means no long-lived stream exists for the keep-alive constraint above to apply to.
- **Never:** disconnect-survival is claimed by progress notifications, sticky-session affinity, or
  home-grown stream replay. Progress notifications die with the connection they travel on; the
  `2026-07-28` core deliberately removed sessions.
- **Always:** a task handle is treated as a **capability** — opaque, high-entropy, TTL'd. Without
  sessions, anyone presenting the handle can read the task.
- **Always:** **six conda-forge builds were the packaging open of this chain.** Stories 26.3 and
  27.1 are ledger-`done` as operator-gate work. That does **not** claim CRC `/ht/` 200 or that
  every OpenFeature/Liquibase package is on conda-forge `main` for every consumer. Do not
  re-open Epics 26/27 as “start with packaging.” CAP-9 live proof is listed on CAP-9 success.
- **Always:** CAP-9 adds a Helm hook Job beside the shipped `migrate-job.yaml`, at a lower
  hook-weight, on the same platform image. It does not introduce a chart pattern, a second image,
  or an init container. The Job **creates schema `liquibase`** before Liquibase opens
  `databasechangelog` (`liquibaseSchemaName` does not create it). Django contrib tables required
  by first-party FKs are explicit changesets, not a silent `migrate` carve-out.
- **Never:** a Langflow/DB-GPT (or other Agent Canopy) process emits boot-time DDL. Governed
  schema is the Liquibase Job, not SQLAlchemy `create_all` on import.
- **Always:** the `liquibase` feedstock targets **5.0.4 or later**. 5.0.2 and 5.0.3 carry the
  `runInTransaction="false"` search-path defect (issue 7791, fixed in 5.0.4), and 5.0.4 is
  additionally the first release whose GPG signature verifies against the rotated signing key.
- **Never:** `preserveSchemaCase` is enabled, and schema names are never mixed-case. Liquibase
  issue **7624 is open**: with that flag on PostgreSQL, `defaultSchemaName` is double-quoted into a
  schema that does not exist, and DDL then lands **silently in `public`**. Django's naming
  conventions already give us lowercase, so this costs nothing and prevents the worst available
  failure mode — wrong-schema DDL that raises no error.
- **Never:** a station portal owns chrome. Chrome lives in CAP-1's package; a portal that ships its
  own app switcher or base layout has violated the contract.
- **Never:** a portal calls a service with a raw request or a trusted identity header. CAP-6's
  client is the only path.
- **Never:** an **03** capability is declared complete on fewer than five tiers. 01/02
  deliverables are complete at spec + script/analysis or spec + skill. The eight stations are
  03 and were **declared complete 2026-08-26** (Epic 37.1, 40/40; mason skill =
  `conda-forge-expert`). A missing cell fails CI. New work is not a station.
- **Always:** design processes as **hook specifications** plus **plugins**. As far as
  possible every layer is replaceable: the process owns named hook points; a plugin
  implements or replaces a layer without a fork (**CAP-18** is the shared contract).
  [Kedro's architecture](https://docs.kedro.org/en/stable/getting-started/architecture_overview/)
  names the spec-vs-plugin split; it does not require every package to be a Kedro
  project (canopy:AD-21). Contracts (Pixi task names, Golden Path artifact identity,
  parent infra kinds, host import boundary, Warden as the sole PR-gate verdict) are
  not plugin surfaces.
- **Always:** Warden is the only PR quality-gate verdict on the Golden Path. External scanners
  (SonarQube, Checkmarx, Black Duck, GHAS, profile-local tools) register as **Warden plugins**
  implementing Warden-owned **hook specifications**. Profile settings choose which plugins
  load. This is not a requirement to re-template Warden as a Kedro project.
- **Always:** parallel BMAD writes use `BMAD_ACTIVE_PROJECT` and physical
  `_bmad-output/projects/<slug>/` paths; **never** `scripts/bmad-switch` from a fan-out. Story
  specs are tracked in `planning-artifacts/specs/` after merge. One story in flight per station.
  Merge is `--merge` (never squash). `--admin` is a CI billing adapter when local tests are
  green, not a second quality verdict. Peer stations implement CAP-18 as **one process-hook
  story**; they do not copy steward Epics 18–30.
- **Never:** a scanner plugin publishes a competing pass/fail that bypasses Warden, and the core
  gate never fails solely because a named scanner plugin is absent.
- **Never:** fork a process to swap a vendor, or let a plugin publish a second verdict for a
  process another owner specified.
- **Always:** a station portal is a reusable Django app following
  [Django's convention](https://docs.djangoproject.com/en/6.0/intro/reusable-apps/) — distribution
  `django-<station>`, module `django_<station>_<app>`, app label `<station>_<app>`. **One
  distribution per station holding one or more apps** (the `django-allauth` shape), living beside
  `django-pyforge` in `src/shared/packages/`. The compound label is required, not stylistic:
  Django demands unique labels across `INSTALLED_APPS`, so a bare `<station>` label cannot survive
  that station owning a second app.
- **Never:** an existing model moves between apps. New concerns become sibling apps in the same
  distribution. Adding a sibling costs nothing; moving a model costs a table rename plus
  content-type and migration-history surgery — and after CAP-9 that becomes a governed changeset
  rather than a Django migration.
- Note that `src/shared/packages/` holds **two families under two conventions**, and they should not
  be reconciled: station CLI/library packages are `pyforge-<station>` over the `pyforge.<station>`
  namespace, while Django reusable apps are `django-*` over `django_*`. `django-pyforge` is correct
  as it stands. The Dream's **03** symmetry is CLI
  (CAP-5), portal (CAP-3), service (CAP-4), domain skill (CAP-15) and persona (CAP-16); an 03
  station missing any of the five is unfinished, whatever its ledger says. 01/02 work is not
  measured against this matrix. **2026-08-26:** the eight-station roster reports 40/40
  (Epic 37.1); mason's skill cell is `conda-forge-expert`.
- **Always:** the eight station portals mount under a uniform `/stations/<name>/` prefix, decided
  2026-08-24. `compliance_face` moves from its shipped `/compliance/` mount and leaves a permanent
  redirect; the app switcher derives its entries from the registration seam rather than from a
  path list. A portal that mounts outside the prefix has violated CAP-3.
- **Never:** CAP-17's supervisor reads an operator's home directory, and the front door never reads
  run state from a filesystem. The supervisor is the only publisher; a surface that falls back to
  scraping local paths has reintroduced exactly the coupling that made the retired console's live
  surfaces undeployable.

### Correct-course 2026-09-02 — red-team HIGH set (Epics 41–43)

Bound from `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md`
via `sprint-change-proposal-2026-09-02-red-team-high.md`. Constraints are appended, not rewritten.

- **Always:** a DR contract (RPO/RTO per store, drill cadence, reconciliation order) exists
  before any store is called canonical; PostgreSQL has a base backup + WAL archive (41.1).
- **Always:** the `.duckdb` file is one process on RWO; Parquet is the shared artifact; every
  non-writer connection is `read_only=True` (41.2). **Never:** the plane file on RWX.
- **Always:** station DDL lives in the changelog under a per-distribution id; runtime paths are
  assert-only (41.3). **Never:** `CREATE EXTENSION` from a station at runtime.
- **Always:** `rediss://` verifies the chain; `CERT_NONE` only under `COMPONENT_RUNTIME=local` (41.4).
- **Always:** the MCP transport verifies the assertion before routing, on every method, on both
  the in-process and sidecar paths; the proxy streams; only `web` reaches `mcp-host` (42.1).
  **Never:** an IdP bearer forwarded to the sidecar.
- **Always:** per-subject rate limits on MCP and `start`, a per-station queue ceiling, a
  concurrent-RUNNING ceiling and `RunState` retention (42.2). **Never:** an unbounded `start`.
- **Always:** a well-formed failing event reaches the DLQ after N attempts with backoff; at least
  one consumer Deployment exists per subscribing station; `traceparent` rides the envelope (42.3).
- **Always:** `acks_late` + `reject_on_worker_lost`, per-station queues, a `builds` pool with an
  hours-scale limit and its own Deployment (42.4). **Never:** a build on the 300 s queue.
- **Always:** prefixed roles (`pyforge:station:*`, `pyforge:tenant:*`, `pyforge:admin`); bare
  station names refused; `tenant` on `RunState` and the envelope (42.5).
- **Always:** every diagram in the living Dream is a build target (43.1). **Amended 2026-09-09
  (operator):** the line count is not a constraint on the living Dream — a detailed evergreen
  strategy outranks a short one; the archive holds historical topology only.
  `historical-section-too-long` keeps that meaning, never a length cap.
- **Always:** station routes are `/stations/<name>/api/v<N>/`; `/api/v1` is not Langflow's;
  `pyforge.core.client` is the one client with a contract test (43.2).
- **Always:** co-located portals reach station code in-process; HTTP only under
  `STATION_REMOTE=1` (43.3). **Never:** a portal view awaiting its own gunicorn pool.
- **Always:** deploys pin an image digest with a recorded Warden verdict (43.4). **Never:** `latest`.
- **Always:** the interpreter topology is one recorded AD with a measured per-env matrix (43.5).
  **Decision 2026-09-02 (hybrid a+c):** one interpreter `3.14.*` for every env once Mason 13.1 / 13.2
  loosen `onnxruntime <1.24` and `sqlalchemy <2.0.29` (43.6 flips the pins); `mcp-host` stays as
  MCP-SDK isolation (langflow pins `mcp <2`). **Never:** describe `mcp-host` as an interpreter shim.

### Correct-course 2026-09-09 — currency review (Epics 48–49)

Bound from `research/currency-review-pyforge-unifying-strategy-2026-09-09.md` and the Dream
§ *Where next* via `sprint-change-proposal-2026-09-09-currency-review.md`. Appended, not rewritten.

- **Always:** a ledger sync never moves a `blocked` story off `blocked` and never drops a key the
  tracked twin holds; the twin's `blocked` is sticky in both `sprint_plan.py` and
  `promote_sprint_status.py` (48.1). **Never:** `--repair-feed` as a pre-write ritual until 48.1
  lands.
- **Always:** every capability in this Spec carries a `**verified:**` line naming which clause of
  its success criterion has a live exercise and which is fixture-only (49.1). **Never:** a Dream
  flips to `realized` on ledger bookkeeping; it flips on effect (Dream § Where next).
- **Always:** cross-spine CAP citations are qualified (`fnd:`, `suite:`, `sld:`, `pap:`, `hub:`)
  exactly as ADs and FRs are; a bare `CAP-n` means Unifying (48.7).

## Non-goals

- **Not** a `services/` FastAPI farm or nine public `:800x` processes. CAP-4 mounts on the host
  ASGI. Celery + Redis is the out-of-request pool (RFC-1 revised).
- **Not** a rewrite of the host. `src/platform/` stands; this SPEC extends it. No rename of
  `pyforge_host`, no relocation of `config/` or `platformapp/`.
- **Not** a ninth station or a ninth BMAD project. The Canopy is steward's surface; the roster
  stays at eight and Charter §5 is not amended.
- **Not** a re-decision of the monolith-versus-microservices topology. That trail is closed in
  `enterprise-multi-agent-orchestration` and `asgi-multiplexer-monolith`.
- **Not** a replacement for any station's CLI. CAP-5 dispatches to them; it does not absorb them,
  and a station binary remains a first-class entry point.
- **Not** atlas's `spec-wagtail-corporate-brain`. That Spec is atlas's and its Epic 16 is `done`.
  **2026-08-25:** Lane 1 does **not** serve `DW-H3` (`lane1-serves-dw-h3` answered no). This chain
  does not absorb, re-mint or supersede that Spec.
- **Not** the adoption of CodeRed CMS. Ruled out 2026-08-24 on maintenance evidence; Lane 1 is
  Wagtail alone.
- **Not** a general-purpose multi-tenancy model. CAP-7's isolation is row-level for analytical
  boards, not a tenancy layer for the estate.
- **Not** atlas's adoption of the secure-dashboard pattern. CAP-7 consumes that pattern; making
  atlas's own board adopt it is atlas's story.
- **Not** a sibling `spec-htap-query-plane` or a ninth station. CAP-19 lives on this SPEC.
- **Not** installing extensions on a customer enterprise database that forbids them.
- **Not** JSON:API / DRF over the plane (`enterprise-data-models-and-apis`).
- **Not** a lakehouse product or Unity / Wasm satellite revival.

## Success signal

An operator signs in once at the estate's front door and moves from a published Lane 1 page, to
any of the eight station portals, to an analytical board that shows them only their own rows —
without re-authenticating or leaving the origin. An agent drives the same stations over MCP,
survives a proxy disconnect mid-build, and still collects its result. One station's action shows
up as an event another station consumes. And the whole thing deploys into an egress-blocked
namespace carrying only PostgreSQL, Redis and the platform images, where the application's
database role is provably incapable of altering its own schema. Dashboards and agents read
the query plane (live attach, Parquet cache, vectors) — not five private stores and not
OLTP.

## Assumptions

- Marshal's console is superseded, not co-owned — decided 2026-08-24, so CAP-2 carries a migration
  obligation and not merely a build obligation. The assumption underneath it is that the console's
  views are re-creatable as CMS-managed pages plus station-portal routes; if any view turns out to
  depend on build-time data with no runtime equivalent, that view forces a scope conversation
  rather than a silent parity gap.
- PyBreaker's Redis state transitions are not atomic across replicas — read from its source
  (`setnx`/`set`/`incr`, no Lua or `WATCH`), not documented upstream. CAP-10 treats its failure
  threshold as coarse protection, not exact-count semantics.
- The eight stations' existing CLIs expose a stable enough surface for CAP-5 to dispatch to
  without modification. Unverified per-station.

## Residual (2026-09-09)

Reopened by the currency review; each line names its vessel.

- **R-18..R-22** (`DW-RT-2026-09-02-2..6`) → Epic 48 Stories 48.2–48.6. Were "Epic 45
  candidate"; Epic 45 went to eval-quality on 2026-09-05.
- **Single-Spec merge** → **shipped 2026-09-10 (Story 48.8).** Full `pap:CAP-1..6` text merged
  inline; `extends:` retired; `spec-python-agent-platform` superseded. Renaming
  `[feature.python-agent-platform]` remains a separate named story if ever.
- **Story 43.7** `backlog` — sidecar runtime validation on Python 3.14 (added 2026-09-08).
- **Six capabilities with an unexercised named criterion** → Epic 49: CAP-4 (`start`/`get` on 2
  of 8, no disconnect test), CAP-7 (fixture board; real Vizro board asserted absent from the
  host), CAP-11 (no eviction test), CAP-12 (`IDP_USERINFO = None` → next-login revocation),
  CAP-14 (7-entry synonym map as "semantic"; no dual-write), CAP-17 (marshal never publishes to
  the supervisor). Eleven CAPs verify fully.
- **`realization-gate-home` precondition MET this pass (2026-09-09, fleet readiness C4).** The
  question binds Epic 49's re-home to `hub:CAP-*` on `spec-intelligence-hub` reaching `ready`;
  all nine of that Spec's open questions were answered as one operator-approved bundle and its
  status flips `draft` → `ready`. **The re-home itself is pending that Spec's `bmad-spec`
  re-derive** — until the re-derive lands, Epic 49 still binds on this chain and no story text
  changes.

- **Five currency-review findings had no vessel; each now names one (2026-09-09, fleet readiness
  stB-F2).** They are all the "document tier stale" class the review named, and four of the five
  sat behind `blocked` Epic 44 stories or behind no story at all:
  1. **§1.7 — the obsolete feedstock table.** `stack.md`'s `## Absent — feedstock work, blocking`
     heads a six-row table whose own closing prose says the stories are `done`; all six shipped in
     `ed41099205` (2026-08-25), including the `cachebox` row whose premise is wrong (conda-forge
     ships 5.2.3, pinned at `pixi.toml:240`). Knock-on: this file's own `surface:` glob
     `recipes/cachebox/**` points at a directory that does not exist. → **Story 48.7**, whose
     CAP-axis pass gains explicit **"document-tier residue"** scope.
  2. **§1.8 — the High-Leverage matrix.** Five aspirational rows and three wrong-station bindings
     survive in `stack.md` (e.g. `stack.md:68` binds `graphviz2drawio` to herald — zero hits in
     herald; it is an atlas prototype). The Dream got a measured-status note on 2026-09-09; no
     story corrected the matrix. → **Story 48.7** (same document-tier residue scope).
  3. **§1.12 — the Spec/epics half.** The Dream corrected its measured claims; the Spec and epics
     tiers did not. `spec-python-foundry-cutover/SPEC.md:34,:76` still say `7,855 recipe dirs`
     (live: **7,873**), `:172` + `cutover.md:58,:112` still say `the 268 registered worktrees`
     (swept 2026-09-05 — 10 remain, 8 KB, `DW-HYGIENE-2026-09-05-1`), and `epics.md:2664` /
     `:2688` carry both literals **inside Story 44.8's and 44.10's own acceptance criteria**. →
     **Stories 44.2 / 44.8 / 44.10 texts, all `blocked`** — recorded here as blocked-gated, with
     the standing rule the Dream already adopted: *measure at dispatch, never a frozen literal.*
  4. **§1.13 residue.** Three items with no vessel before this pass: the broken regeneration
     command hardcoded in `scripts/pixi_env_matrix.py::render_markdown` (re-stamped on every
     regeneration, so it self-heals into staleness); "16 of 18 living names bind to nothing"; and
     the `pyforge.*` import-rule violation on both sides (`spec-python-agent-platform`'s Non-goal
     is stated absolutely while `src/platform/ingest/github_projects/` imports
     `pyforge.steward.{keys,sync}` at 8 sites outside the import-linter's `root_packages`, and
     `django-atlas`'s portal imports `pyforge.steward.dashboard.*` under a test allow-list). →
     **Story 48.7** for the first two; the import rule is recorded on
     `spec-python-agent-platform`'s memlog and belongs to **Story 48.8**'s merge, so a merge that
     copies text forward does not carry a knowingly-false absolute into the surviving contract.
  5. **The four `blocked`-gated `DW-RT-2026-09-02-*` re-reads.** All nine still carry "agent
     judgment not applied — a re-read against live code is still owed where the claim is
     semantic" (`deferred-work-ledger.md:2487-2576`). Five (`-2..-6`) were promoted to Stories
     48.2–48.6, so their re-read happens at implementation; the other four — `-1` (R-17 → Story
     44.7) and `-7`/`-8`/`-9` (R-23/24/25 → Story 44.2) — are gated behind `blocked` Epic 44.
     **`-9` (R-25) is the sharpest:** it is the correction for a constraint this chain's own Dream
     already documents as knowingly wrong ("zero domain models on portals" vs
     `django_warden_fabric/models.py:11` `ComplianceJob`), so a known-false constraint sits behind
     a `blocked` gate with no interim annotation. → **blocked-gated; annotate at 44.2/44.7
     dispatch, not before.**
  *Not steward's to vessel:* §1.10's "no detector validates Kinship wikilinks" is relayed to
  **doctor** as a `dreams-hygiene-check` extension (fleet readiness Class D, D3).

- **Three statements in this chain were false against live code and are corrected 2026-09-09:**
  this file's "no `GraphStore` class exists in `pyforge-scribe`" (it exists —
  `graph_store.py:59`, with `_pg`, `_plane`, `_plugins` drivers; the two prose sites below are
  annotated, not deleted); `resilience-invariants.md:103` BS-5 (`read_only=True` appears twice,
  AST-enforced) and `:104` BS-6 (CloudEvents 1.0 ships at `events/constants.py`).

- **`pyforge.*` import carve-outs (2026-09-10, Story 48.7).** `pap:AD-2` / host Non-goals state
  the host never imports `pyforge.*`; two brownfield sites remain until their owning stories land:
  `src/platform/ingest/github_projects/*` (eight `pyforge.steward.*` imports — successor in
  `fnd:AD-7` / Story 44.4) and `django-atlas` portal tests (allow-listed `pyforge.steward.dashboard`
  imports). These are recorded exceptions, not a repeal of the rule; Story 48.8 merge must not
  copy the absolute Non-goal forward without this carve-out.

## Open Questions

- ~~**liquibase-7791-fixed**~~ — **answered 2026-08-24: yes, fixed in 5.0.4**, corroborated by both
  the merged PR (an ancestor of the `v5.0.4` tag) and the release notes. The question was also
  **framed too broadly**: the defect only ever affected changesets marked
  `runInTransaction="false"`, never in-transaction ones, so the gate covers the exception
  (`CREATE INDEX CONCURRENTLY`, `ALTER TYPE … ADD VALUE`) rather than multi-schema work generally.
  It surfaced a larger hazard in its place — open issue 7624, now a `Never:` constraint above.
- ~~**mcp-client-revision**~~ — **answered 2026-08-24: accept `2025-03-26` through `2026-07-28`**,
  four handshake revisions plus the modern one, which is what `mcp` 2.0.0 already serves dual-era
  with no configuration. The client fleet is mixed enough that a `2026-07-28`-only server would
  reject most of it, while Codex traffic already declares `2026-07-28` — so both ends are needed
  now. Cursor's revision is genuinely unpublished and is treated as unknown.
- ~~**mcp-tasks-runtime**~~ — **answered 2026-08-24: no, and blocked upstream.** `mcp` 2.0.0 lists
  the Tasks extension under *Known gaps*; the only working server-side runtime in any language is
  `fastmcp-tasks` at `4.0.0b3`, a beta on unreleased FastMCP 4, absent from conda-forge along with
  its `docket` dependency. CAP-4's success criterion is shippable **without** Tasks — see the
  constraint below. Recorded as a **scheduled re-check**, not a closed door: SEP-2663 is Final and
  the SDK's extension API has landed, so this may resolve within the chain's lifetime.
- ~~**mcp-runtime-base**~~ — **answered 2026-08-24: hybrid.** Stopgap now: `local-recipes` pins
  `fastmcp >=3.4.7,<4` and `mcp >=1.24,<2.0` so servers start. CAP-4 service faces are built on
  the official `mcp` SDK (`>=2.0.0`) on the one ASGI process; that story lifts the ceiling.
  Bound as architecture AD-5.
- ~~**lane1-serves-dw-h3**~~ — **answered 2026-08-25: no.** CAP-2 Wagtail is `/cms/` (admin,
  documents, images, pages) on the host ASGI process. Atlas `LaSuiteClient` is frozen to La Suite
  Docs REST: `POST /api/v1/documents/`, `PATCH`/`GET /api/v1/documents/{id}/`,
  `GET /api/v1/documents/all/`, Bearer token
  (`src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/lasuite.py`). Those routes are not
  Wagtail's API. Lane 1 does **not** satisfy `DW-H3`. DW-H3 stays atlas's attended bring-up of a
  server that speaks that contract (or a future adapter Dream). This chain does not absorb
  `spec-wagtail-corporate-brain`. Estate may run two CMS faces.
- ~~**Q5 measure set**~~ — **parked 2026-08-25**, not an unbounded Canopy OQ. Operating-model
  Q5 remains in force (optimize to **published** measures; never invent). The measure set and
  board live under sibling Dream `docs/dreams/build-league-scorecard.md` (`status: dreamt`) and
  `spec-build-league-scorecard` (`status: draft`). No CAP-18 board. Herald / Atlas / Marshal /
  Doctor consume later.
- ~~**12-7 live `/ht/`**~~ — **answered 2026-08-25:** attended CRC, Helm `platform` **deployed**,
  Liquibase + `migrate --fake` Complete, `https://platform.apps-crc.testing/ht/` **200**. Record:
  `spec-12-1-the-vanilla-chart-with-an-ocp-overlay-verification-2026-08-25.md`. CRC follow-through
  **closed 2026-08-26** (sidecar Ready, `platform_app`, MCP host sidecar, `/` **200**). PVC
  sizes stay hostpath-odd; isolated `mfa` stays fake. They do not reopen this question.
- ~~**console-parity-inventory**~~ — **answered 2026-08-24** by `console-parity-inventory.md`.
  Twenty-three surfaces: 14 runtime-reproducible, 7 build-time-only, 3 mixed. The seven reduce to
  **four decisions** — live run state (three surfaces, one decision), detector verdicts, curated
  editorial content, and journal-derived timing — plus the committed-snapshot model, which is not a
  loss to mitigate but the property CAP-2 exists to remove. Two findings change scope: the retired
  build path has **100+ inbound references** across the repo and needs its own story, and the
  co-published Kedro-Viz tree is **not** part of the parity obligation (no inbound link from the
  console, separate workflow) and must not be deleted with it.
- ~~**liquibase-airgap-policy**~~ — **answered 2026-08-24.** Two boundaries, both binding:
  conda channels govern the Python/pixi graph, `pap:CAP-6` governs
  deployment images and already admits non-conda third-party images. See
  `research/technical-pyforge-unifying-strategy-airgap-delivery-2026-08-24.md`.
- ~~**query-plane-face**~~ — **answered 2026-08-26 (operator): both, one boot script.**
  Library-first stands for every consumer that can reach the file (pap:AD-16 local-first;
  DuckDB stays a query face, never a fourth backing store), AND the Mosaic
  `duckdb-server` HTTP/Arrow face is committed now behind the same single boot
  script — raised only when the platform stack is up, pixi-sourced. The two faces
  serve the identical plane; parity between them is part of the face's definition of
  done. Consumers with no filesystem access (DB-GPT / Langflow estate reads, live
  console queries) bind to the HTTP face per CAP-19's success wording ("the plane DSN
  or HTTP face").
- ~~**query-plane-catalog**~~ — **answered 2026-08-26 (operator): named new pipeline**,
  explicitly framed as the opt-in optimization layer: the closed seven stay sealed and
  keep producing the canonical datasets untouched; the new named pipeline sits
  downstream, deriving the plane's Parquet cache from their outputs; consumers choose
  per call — canonical datasets direct, or the plane as the fast path. Reopening the
  seven was considered and declined: it would entangle plane-writing into
  regression-gated shipped pipelines for no functional gain, since a downstream
  pipeline reads their outputs without modifying them. No silent `01_raw`.
- ~~**query-plane-scribe-cutover**~~ — residual **answered 2026-08-26 (operator):
  dual-write for now.** The plane (via the 34.5 store-port driver) is primary and
  satisfies canopy:FR-36; `scribe_schema` pgvector stays written as the safety net until the
  plane has operating history, then retirement becomes its own explicit decision.
  Lexical recall may stay local. *(2026-09-09: superseded — `GraphStore` exists; § Residual.)* There is still no `GraphStore` class in
  `pyforge-scribe`.
