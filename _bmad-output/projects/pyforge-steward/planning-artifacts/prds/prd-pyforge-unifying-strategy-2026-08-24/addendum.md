---
title: "PRD Addendum — mechanisms, and why they were chosen"
chain: "pyforge-unifying-strategy"
created: "2026-08-24"
updated: "2026-08-24"
---

# PRD Addendum

The PRD states capabilities. This states mechanisms — the technical-how it deliberately keeps out,
plus the rationale behind decisions already made so the architecture pass **confirms** them rather
than reopening them.

**Operating-model bind (2026-08-24, after this addendum's first ready).** Dream Grounding Q1–Q8
and canopy AD-21 do not reopen the mechanism choices below (MCP `start`/`get`, Liquibase Job,
FILE flags, PyBreaker wrapper, `django-pyforge` chrome). They **scope** five-tier completeness
to 03, bind hooks/plugins as replaceable layers, and adapterize WFT tool names. See § Operating
model, added the same day.

Three of these were not choices between good options. They were forced by research that
invalidated what the Dream assumed, and the reasoning is recorded because a future reader who only
sees the outcome would reasonably wonder why the obvious thing was not done.

## Operating model (bound 2026-08-24)

These are estate rules, not a second mechanism hunt. Full text: Dream Grounding; canopy AD-14
(03-only five tiers), AD-21 (hooks/plugins).

| Bind | Consequence for this chain |
|---|---|
| Q1 Golden Path; WFT tools as adapters | Same Pixi task contract. Harness / Splunk / Jira / Tachyon / named scanners are **plugins**, not core stack. |
| Q2 five-tier = 03 only | FR-37/38/39 and SM-5 denominator stay 8×5 for the eight stations. 01/02 must not fail that check. |
| Q3 owner vs SLA | Registration carries owner, backup, `work_class`, promotion date. SLA body stays in the 03 spec. |
| Q4 generic traceability | CloudEvents: `spec_id` + git sha + SBOM purl; Jira optional. Never fail for a missing key. |
| Q5 measurement | Scorecard / Build League rules live in the Dream; board is a sibling Dream; **no CAP-18**. Measures unpublished (human + agent + team). |
| Q6 Path B ≠ Tachyon | Path B = Agent Canopy + CAP-16 persona. Tachyon = production LLM provider adapter. |
| Q7 Lane 2 is HTMX | FastAPI = station compute. DRF JSON:API on Atlas / `enterprise-data-models-and-apis` only. |
| AD-21 hooks/plugins | Process owns hook specs; plugin replaces a layer without a fork. Kedro *names* the split. |
| Q8 Warden sole PR verdict | Warden **owns** PR-gate hook specs; scanner plugins implement them. Missing named scanner ≠ failed run. |

Lane 2 URL scheme is **no longer open**: uniform `/stations/<name>/`, permanent `/compliance/`
redirect (FR-9a). The corrections table below is updated.

## Mechanism decisions already made

### FR-11/FR-12 — MCP transport and resumability

The Dream specified SSE at a `/mcp/sse` endpoint. That is deprecated twice over: HTTP+SSE as a
dual-endpoint transport was superseded by Streamable HTTP, and a compliant current server answers a
GET to its endpoint with `405`. **A single POST endpoint on the official SDK is the target.**
Resumability comes from the Tasks extension rather than from stream reconnection logic of our own.

The unresolved half (OQ-3) is whether the SDK ships a *server-side* Tasks runtime yet. Client-side
support landing first is the normal order, so the story must be written to survive the SDK catching
up: an interim mechanism behind the same FR, replaced without changing the requirement.

**Keep-alive under 30 seconds is not tunable.** The router's `timeout client` is cluster-wide with
no per-route override, and HAProxy governs streaming by `timeout client`/`timeout server` — *not*
`timeout tunnel`, which is the setting most community advice reaches for and which does not apply.
A route annotation is defence-in-depth. The keep-alive is the mechanism.

### FR-21/FR-24 — Liquibase delivery and deploy ordering

**Feedstock, not container image.** The deciding fact was not policy but the chart. The shipped
`migrate-job.yaml` is a `post-install,pre-upgrade` hook at weight `0` that runs the platform image
and passes its command as `args` — so anything on the platform environment's PATH is runnable in
that Job with no new image at all. FR-24 therefore adds a Job at weight `-1` on that same image and
flips the existing one to a fake-apply.

The container route would have paid for a third-party image class the repo has no documented
mirroring pattern for, *and* still built a derived image, because recent Community releases stopped
bundling the PostgreSQL JDBC driver and the package manager fetches it over the network. So the
JDBC driver is vendored into the recipe either way; the feedstock is strictly cheaper.

Recipe shape precedent: the estate already has roughly a dozen JVM recipes, and `apache-tika` is
the exact shape — Maven jars into the prefix's shared Java directory, a JDK run-dependency, a CLI
wrapper. `openjdk` 25.0.2 clears the Java 17+ floor.

**Never an init container**, for two independent reasons that happen to agree — the strongest form
of corroboration available. N replicas each running one contend on the changelog lock, whose
default wait is five minutes. And the shipped Job's own header documents that with `helm install
--wait`, post-install hooks fire only after resources are Ready, so migration-gated readiness
deadlocks.

### FR-22 — why privilege, not convention

The literal directive ("zero runtime ORM DDL") is not implementable. `post_migrate` is the only
supported mechanism populating content types, permissions and sites, and the test runner builds
every test database by running migrations. Both would break.

The revision moves enforcement off the framework and onto the **database role**, which changes the
question from "which apps are carved out" — unanswerable without reproducing the framework's entire
built-in migration graph in changesets — to "which role runs what". That second question an auditor
can verify from outside the application entirely. Test databases are carved out completely.

### FR-33/FR-34 — flag provider

**File-resolver mode, evaluated in-process from local JSON, with the full targeting engine.** No
sidecar, no daemon, no egress.

The in-process WASM alternative is independently ruled out: its runtime dependency is not on
conda-forge, so it could not enter the boundary regardless of preference.

The five builds are not five new recipes. Four are — `openfeature-sdk`, `openfeature-flagd-api`,
`openfeature-flagd-core`, `openfeature-provider-flagd`, none of which exists anywhere on
anaconda.org. The fifth, `cachebox`, already has a feedstock at 6.2.5 while the provider pins
`<6`, so it is a deliberate **downgrade build on an existing feedstock**. Different task, different
size; do not schedule it as a fifth new recipe.

### FR-26 — the circuit breaker wrapper

The chosen library's asynchronous support targets Tornado coroutines, not asyncio. An
`httpx.AsyncClient` coroutine passed to its call path **records a false success and the circuit
never trips** — a silent failure of exactly the invariant the FR exists to guarantee. A wrapper of
roughly forty lines fixes it.

The alternatives were weighed and rejected: one is packaged but dormant since 2022; the other is
maintained but unpackaged, which means a feedstock for forty lines' worth of benefit.

Its cross-replica Redis state transitions use plain `setnx`/`set`/`incr` with no Lua script and no
`WATCH` — read from source, since upstream does not document it. So the threshold is coarse
protection. **Do not write a test that asserts an exact failure count**; it will be flaky for a
reason that looks like a bug in our code.

### FR-1 — why the chrome package is ours

`django-lasuite`, which the Dream named as the source, is OIDC/DRF/malware-scanning plumbing. It
contains no app switcher and no theme. La Suite's own switcher is npm/React and reads a service-list
endpoint that is unreachable in an air gap. Adopted for OIDC only; the chrome is ours to build.

## Deployment constraints §4.2 inherits

All solvable, none optional, and the last is the one that bites.

- **Media must leave the pod filesystem** — object storage or RWX. Note that remote storage does not
  fully offload it: originals are read back whenever a new rendition is generated.
- **Cache must be shared.** A dedicated renditions cache alias falls back to the default; a
  per-process cache leaves every replica with a divergent rendition cache.
- **Search needs no new service.** The database backend uses PostgreSQL full-text search and is
  documented as production-adequate — which is what keeps the three-backing-service constraint
  intact. Requires the framework's PostgreSQL contrib app installed.
- **Background tasks are an open decision.** Recent versions route indexing and image work through a
  task abstraction shipping database and RQ backends and **no Celery backend**. Inheriting the
  default silently splits the estate's task story in two. Decompose it explicitly.
- **OIDC users land with no groups**, and admin access gates on a specific permission rather than a
  generic staff flag — so a correctly authenticated user is bounced with no useful error. Mapping
  IdP claims onto a group holding that permission is required work with no first-party guidance.
  Pair with password-management and email-management disabled.
- Use the supported admin-login-URL setting for the allauth hook. Most community material predates
  it and describes URLconf-override workarounds; do not follow that advice.

## Rejected alternatives

| Rejected | For | Why |
|---|---|---|
| CodeRed CMS | Lane 1 | Upstream dormant since 2025; supports Wagtail only through 7.1 against a current 7.4.3 LTS — three minor releases behind. Adopting it would import an unmaintained dependency into a regulated estate. |
| SSE dual-endpoint transport | Service faces | Deprecated twice over; a current compliant server rejects the GET half with `405`. |
| Init container for governed DDL | Deploy ordering | Changelog-lock contention across replicas, *and* readiness deadlock with `--wait`. |
| Upstream Liquibase container image | FR-21 | New third-party image class with no mirroring precedent here, and still requires a derived image for the JDBC driver. |
| Self-built Liquibase image | FR-21 | Requires the conda package first, then adds an image that package does not need. |
| In-process WASM flag evaluation | FR-34 | Runtime dependency absent from conda-forge. |
| `aiocircuitbreaker` | FR-26 | Packaged, but dormant since 2022. |
| `purgatory` | FR-26 | Maintained, but unpackaged — a feedstock to replace forty lines. |
| `django-lasuite` as chrome source | FR-1 | Contains no switcher and no theme; its own switcher is npm/React against an unreachable endpoint. |

## Corrections the downstream passes must not reintroduce

These were all asserted by the Dream or its pre-audit brief and disproved. They are listed because
a pass reading the Dream directly would re-derive them in good faith.

| Asserted | Actual |
|---|---|
| Greenfield platform | `src/platform/` is live; four steward epics `done` |
| `pyforge_host` / `pyforge-agent-platform` are artifacts | Role names; the artifact is `src/platform/` |
| Lane 2 at `/stations/{station}/` (pre-audit, as if already live) | One portal was at `/compliance/`. **Closed:** uniform `/stations/<name>/` + permanent `/compliance/` redirect (FR-9a). OQ-4 is not open. |
| Eight services on ports `:8001–:8008` | No port assignment exists anywhere in `src/platform/` |
| Scribe has a SQLite/PostgreSQL dual driver | One flat JSON file; FR-35 builds the *first* durable driver |
| Wagtail CRX carries Lane 1 | CodeRed dropped; Wagtail alone |
| No Wagtail anywhere in the estate | Atlas ships a client and a syncer against a **La Suite Docs** REST contract — which is not the CMS's own API, hence OQ-5 |
| Zero runtime ORM DDL | Unimplementable; enforcement moved to the database role |
| Five-tier completeness for any work / any station | **03 only** (Q2). 01/02 stay spec+script or spec+skill. canopy AD-14. |
| Warden re-templated as a Kedro project so scanners can plug in | Kedro *names* the spec-vs-plugin split (AD-21). Warden owns PR-gate hook **specs**; plugins implement. Atlas already *is* Kedro. |
| Tachyon is Path B / the Agent Canopy | Tachyon is a production LLM adapter (Q6). |

## Adjacent, deliberately not absorbed

- Ledger rollup drift: warden `epic-7`/`epic-8` and mason epics 2–3 read `backlog` while their
  stories read `done`. Pre-existing, cross-station.
- Atlas never adopted the secure-dashboard pattern despite being named its first adopter. FR-16
  consumes the pattern; atlas adopting it is atlas's story.
- Story 12-7 is permanently `skip_on_blocked` pending a live cluster.
- Two steward Dreams (`bmad-suite-install-class-wiring`, `ocp-as-a-portability-profile`) fail
  `dream-chain-check`. Same station, unrelated chains.
