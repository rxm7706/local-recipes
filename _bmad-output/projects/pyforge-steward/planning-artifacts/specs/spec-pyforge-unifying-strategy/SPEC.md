---
spec: pyforge-unifying-strategy
status: draft
chain: pyforge-unifying-strategy
created: "2026-08-24"
updated: "2026-08-24"
companions:
  - convergence.md
  - resilience-invariants.md
  - stack.md
  - architecture-diagrams.md
  - ../../research/technical-pyforge-unifying-strategy-research-2026-08-24.md
  - ../../research/technical-pyforge-unifying-strategy-airgap-delivery-2026-08-24.md
owner-dream: docs/dreams/pyforge-unifying-strategy.md
extends: spec-python-agent-platform
surface:
  - src/platform/**
  - src/shared/packages/django-pyforge/**
  - src/shared/packages/pyforge-core/**
  - src/shared/packages/pyforge-scribe/**
  - services/**
  - .claude/skills/pyforge-*/**
  - recipes/openfeature-*/**
  - recipes/cachebox/**
  - recipes/liquibase/**
  - pixi.toml
  - environment.yaml
sources:
  - ../../../../../../docs/dreams/pyforge-unifying-strategy.md
open_questions:
  - liquibase-7791-fixed
  - mcp-client-revision
  - mcp-tasks-runtime
  - console-parity-inventory
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete,
> preservation-validated contract for what to build, test, and validate. The Dream in `sources:`
> carries the decision trail — ten operator rulings dated 2026-08-24, the RFC/blind-spot
> derivations, and the pre-audit architecture prose this contract deliberately compresses.

> **This SPEC extends `spec-python-agent-platform`, it does not replace it.** That Spec's CAP-1..6
> are shipped and binding; nothing here re-mints them. `convergence.md` is the authority on which
> side of the line any surface falls, and CAP-9 is the one place this SPEC reopens shipped work.

# pyforge-unifying-strategy — the Canopy mounts the eight stations

## Why

**A vision to realize, with a mandate riding on it.** PyForge is eight capability stations that
each shipped as an excellent command-line tool and stopped there. An operator who wants to see
compliance findings, package health, fleet status and build queues holds eight terminals and no
shared identity, no shared vocabulary, and no way for one station to tell another that something
happened. The Canopy — `src/platform/`, already live with OIDC SSO, two agentic engines mounted on
isolated schemas, and exactly one station portal — proved the shape works. This SPEC extends it
from one portal to eight, gives every station a web face, a service face and a shared command
grammar, and connects them with an event fabric so the estate behaves as one system.

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

- **CAP-2 — Lane 1 is CMS-managed, and it is the only front door.**
  - **intent:** A public front door at `/` whose pages are edited and published without a code
    deploy, with its admin reachable only through the estate's identity provider. It **supersedes**
    the estate's existing statically-built console, which is retired rather than kept alongside.
  - **success:** An editor publishes a page change with no deploy; an unauthenticated request to the
    CMS admin is redirected to the IdP rather than to a local login form; and every view the retired
    console offered is reachable from the new front door, with the old build path removed rather
    than merely unlinked.

- **CAP-3 — Eight portals, one session.**
  - **intent:** Every station is reachable as a Lane 2 application under the one host, so an
    operator moves between stations without re-authenticating or changing origin.
  - **success:** All eight portal URLs resolve behind a single session, and adding or removing a
    portal changes no host code outside that portal's own registration.

- **CAP-4 — Every station has a service face.**
  - **intent:** Each station exposes its capabilities to programmatic and agent callers over a
    current-specification MCP endpoint, with long operations surviving connection loss.
  - **success:** An agent completes a multi-minute station operation across a simulated ingress
    disconnect and still retrieves the result.

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

- **CAP-9 — Schema change is governed, not incidental.**
  - **intent:** Production schema change flows through one auditable authority, enforced by
    database privilege rather than by convention, while the application's own tooling remains the
    place a developer authors a change.
  - **success:** The application's database role provably cannot execute `CREATE`, `ALTER` or
    `DROP`, and a schema change authored without a corresponding governed changeset fails the
    build. *(Reopens shipped work — see Constraints and `convergence.md`.)*

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
  - **intent:** Each station carries an agent-loadable domain skill encoding how that station's work
    is actually done, following the shape one station already proves.
  - **success:** An agent asked to perform a station's core task loads that station's skill and
    follows it, demonstrated for a station that has no skill today.

- **CAP-16 — Every station can be addressed as a persona.**
  - **intent:** Each station exposes an autonomous persona that acts through that station's own
    command grammar and service face rather than through ad-hoc tool calls.
  - **success:** A persona completes a station task end to end using only CAP-5's grammar and
    CAP-4's service face, with no direct filesystem or ad-hoc HTTP access in the transcript.

## Constraints

- **Always:** `spec-python-agent-platform` CAP-1..6 are shipped and binding. This SPEC extends
  them; `convergence.md` decides which side of the line a surface falls on.
- **Always:** Django `>=5.2.15,<6` and Python `3.12.*`. Django 6 is unavailable. conda-forge ships
  exactly one qualifying Django build, two patch releases behind upstream, with zero headroom — a
  dependency that demands a newer 5.2 patch is blocked until a feedstock maintenance branch exists.
- **Always:** every **Python/pixi** dependency resolves from conda-forge. The egress-blocked build
  is a gate, not a warning; a PyPI-only package is new feedstock work and must be scheduled as such.
  This governs the dependency graph, not every artifact in the namespace — container images are
  governed separately by `spec-python-agent-platform` CAP-6, which already admits third-party
  images (`postgres:17`, `redis:7`) under the internal-registry rule. Neither boundary is optional
  and neither substitutes for the other.
- **Always:** infrastructure is exactly PostgreSQL + Redis + Kubernetes. A component demanding a
  fourth backing service has failed its design review.
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
- **Always:** CAP-13's packages do not exist on conda-forge today, and neither does Liquibase.
  **Six recipes must land first** — five OpenFeature-related plus `liquibase` — and per repo Rule 1
  every one of those stories invokes `conda-forge-expert`. CAP-9 and CAP-13 are each blocked on
  their own feedstocks, so both epics open with packaging work rather than platform work.
- **Always:** CAP-9 adds a Helm hook Job beside the shipped `migrate-job.yaml`, at a lower
  hook-weight, on the same platform image. It does not introduce a chart pattern, a second image,
  or an init container.
- **Never:** a station portal owns chrome. Chrome lives in CAP-1's package; a portal that ships its
  own app switcher or base layout has violated the contract.
- **Never:** a portal calls a service with a raw request or a trusted identity header. CAP-6's
  client is the only path.
- **Never:** a station is declared complete on fewer than five tiers. The Dream's symmetry is CLI
  (CAP-5), portal (CAP-3), service (CAP-4), domain skill (CAP-15) and persona (CAP-16); a station
  missing any of the five is unfinished, whatever its ledger says.

## Non-goals

- **Not** a rewrite of the host. `src/platform/` stands; this SPEC extends it. No rename of
  `pyforge_host`, no relocation of `config/` or `platformapp/`.
- **Not** a ninth station or a ninth BMAD project. The Canopy is steward's surface; the roster
  stays at eight and Charter §5 is not amended.
- **Not** a re-decision of the monolith-versus-microservices topology. That trail is closed in
  `enterprise-multi-agent-orchestration` and `asgi-multiplexer-monolith`.
- **Not** a replacement for any station's CLI. CAP-5 dispatches to them; it does not absorb them,
  and a station binary remains a first-class entry point.
- **Not** the adoption of CodeRed CMS. Ruled out 2026-08-24 on maintenance evidence; Lane 1 is
  Wagtail alone.
- **Not** a general-purpose multi-tenancy model. CAP-7's isolation is row-level for analytical
  boards, not a tenancy layer for the estate.
- **Not** atlas's adoption of the secure-dashboard pattern. CAP-7 consumes that pattern; making
  atlas's own board adopt it is atlas's story.

## Success signal

An operator signs in once at the estate's front door and moves from a published Lane 1 page, to
any of the eight station portals, to an analytical board that shows them only their own rows —
without re-authenticating or leaving the origin. An agent drives the same stations over MCP,
survives a proxy disconnect mid-build, and still collects its result. One station's action shows
up as an event another station consumes. And the whole thing deploys into an egress-blocked
namespace carrying only PostgreSQL, Redis and the platform images, where the application's
database role is provably incapable of altering its own schema.

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

## Open Questions

- **liquibase-7791-fixed** — is the multi-schema `default-schema-name` regression on 5.0.3 fixed in
  5.0.4? Must be verified before any multi-schema changeset lands.
- **mcp-client-revision** — which MCP protocol revision do our agent clients actually speak? A
  `2026-07-28`-only server rejects handshake-era clients and vice versa.
- **mcp-tasks-runtime** — does the official `mcp` Python SDK ship a server-side Tasks runtime yet?
  This is the largest gap between CAP-4's recommended pattern and shippable code.
- **console-parity-inventory** — which of Marshal's console views have no runtime equivalent under
  CAP-2? The supersede ruling of 2026-08-24 settled *that* it is retired; this settles *what has to
  exist first*. Answered by an inventory pass in Phase 4, not by research.
- ~~**liquibase-airgap-policy**~~ — **answered 2026-08-24.** Two boundaries, both binding:
  conda channels govern the Python/pixi graph, `spec-python-agent-platform` CAP-6 governs
  deployment images and already admits non-conda third-party images. See
  `research/technical-pyforge-unifying-strategy-airgap-delivery-2026-08-24.md`.
