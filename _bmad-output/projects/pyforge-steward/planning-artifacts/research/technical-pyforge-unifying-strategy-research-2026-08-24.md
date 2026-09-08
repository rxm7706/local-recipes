---
title: "Technical research — pyforge-unifying-strategy"
chain: "pyforge-unifying-strategy"
type: "technical"
created: "2026-08-24"
updated: "2026-08-24"
status: "ready"
decision: "Which of the Dream's RFC/BS directives can become machine-checkable acceptance criteria, and at what cost"
---

# Technical research — pyforge-unifying-strategy

Five questions, run 2026-08-24 through parallel web fan-out. Constraints held fixed throughout,
taken from the live repo: Django `>=5.2.15,<6`, Python `3.12.*`, and **every dependency must
resolve from conda-forge** because CAP-5 sources the environment from the factory and CAP-6 gates
an egress-blocked build. A PyPI-only package is not a preference problem, it is new feedstock work.

**Headline: four of the Dream's directives are not implementable as written.** Two are stale
against upstream (BS-2's transport, BS-4's library), one is blocked on packaging (OpenFeature),
and one rests on a false premise about what a library does (`django-lasuite`). RFC-5 is
achievable only in a modified form that the operator's "as written" ruling does not survive
contact with. Details and citations below; every claim traces to a source dated on or before
2026-08-24.

**Later the same day — binds this research does not reopen.** The five investigations below stay
the evidence record. After they landed, Dream Grounding Q1–Q8 and canopy:AD-21 bound the
*operating model*. They do not reverse MCP/Liquibase/Wagtail/PyBreaker/`django-pyforge`
verdicts. They do change how a later reader must use this file:

- Five-tier completeness is the **03** shape of the eight stations, not “any work missing a
  tier is unfinished.”
- Packaging (OpenFeature four + `cachebox` 5.x + Liquibase ≥5.0.4) is **operator-owned**.
  Stories 26.3 / 27.1 do not author recipes (canopy:AD-16).
- The claim that `django-feedstock` has no 5.2 maintenance branch was **wrong** — it has a
  `5.x` branch (see `technical-pyforge-unifying-strategy-dependency-currency-2026-08-24.md`
  and SPEC). Currency gap, not a missing branch.
- **Hooks and plugins (AD-21)** are an architecture principle (replaceable layers). Kedro
  names the spec-vs-plugin split. Q8 is the PR-gate instance (Warden owns those specs).
- WFT-named tools and Tachyon are **plugins / adapters**, not a rewrite of this research's
  stack table.

---

## 1. BS-2 — MCP over SSE through OpenShift. **Superseded twice over.**

**The transport is deprecated.** The current MCP specification revision is `2026-07-28`. HTTP+SSE
(the two-endpoint `/sse` + POST shape the Dream describes) has been deprecated since `2025-03-26`
and is now formally classified *Deprecated* under the lifecycle policy: "New implementations
**SHOULD NOT** adopt it" (MCP specification 2026-07-28, Streamable HTTP transport page).

**Worse, the modern replacement removed the thing the Dream depends on.** `2026-07-28` removed the
standalone GET stream *and* protocol-level sessions from Streamable HTTP itself. A compliant
server exposes a single POST endpoint (conventionally `/mcp`) and answers GET or DELETE on it with
`405 Method Not Allowed`. `Mcp-Session-Id` is gone; `Last-Event-ID` resumability is gone. SSE
survives only as the wire format of a *response to one POST*, scoped to that request.

**And the timeout annotation does not do what the Dream claims.**
`haproxy.router.openshift.io/timeout: 30m` is valid syntax and does raise HAProxy's
`timeout server` per route. But it leaves **`timeout client` at the cluster-wide 30-second
default, and OpenShift exposes no per-route annotation to change it** — confirmed in the
`openshift/router` HAProxy template, where `timeout client` appears only in `defaults` from
`ROUTER_DEFAULT_CLIENT_TIMEOUT`. HAProxy upstream is explicit that SSE is governed by
`timeout client`/`timeout server`, not `timeout tunnel`. So the keep-alive interval must sit
comfortably under 30 seconds no matter what the annotation says; a documented OpenShift case
shows a 30-second heartbeat failing with HTTP 504 and 15 seconds fixing it.

**The spec's own answer for multi-minute work is a job handle, not a held stream.** The Tasks
extension (`io.modelcontextprotocol/tasks`, SEP-2663, promoted to an official extension in
`2026-07-28`) returns a durable `taskId` with `ttlMs` and `pollIntervalMs`; the client polls
`tasks/get` and can resume after disconnect. This matters because `2026-07-28` also made stream
closure *mean cancellation* — so with a held-open stream, any transient ingress hiccup silently
cancels the build.

**Packaging.** conda-forge has `mcp` 2.0.0 (the official SDK, `2026-07-28`-capable, updated
2026-07-30) and `fastmcp` 3.4.4. FastMCP only speaks `2026-07-28` from version 4, which is still
beta — so **the official `mcp` SDK is currently the only conda-forge path to the current spec.**

> **Verdict.** Do not write `/mcp/sse` or the 30-minute route timeout into acceptance criteria.
> Write: one POST `/mcp` endpoint on `mcp` 2.0.0; operations over ~30s return a Task handle or
> emit `notifications/progress` on the request's own stream; SSE keep-alive comment frames at a
> measured interval well under 30 seconds plus `X-Accel-Buffering: no`; the route annotation kept
> as defence-in-depth, not as the mechanism.

**Open:** which MCP revision our agent clients actually speak; whether the official Python SDK yet
ships a server-side Tasks *runtime* (FastMCP's own PR notes no SDK shipped one at time of writing).

---

## 2. RFC-5 — Liquibase as sole DDL authority. **Achievable only in modified form.**

The operator accepted RFC-5 as written on 2026-08-24. Research says the literal reading cannot
hold, for one documented reason.

**Django's `migrate` is not only a DDL mechanism.** `post_migrate` fires "at the end of the
`migrate` command (even if no migrations are run)" and is the only supported mechanism populating
`django_content_type`, `auth_permission`, and `django_site`. Those handlers do DML, not DDL — the
signal docs state they "must not perform database schema alterations." So a schema that Liquibase
built perfectly, with `migrate` never run, boots with empty permission and content-type tables:
the admin fails, every `has_perm` fails, and allauth's `SITE_ID` lookup fails.

**The test runner cannot use Liquibase at all.** `create_test_db()` "creates a new test database
and runs `migrate` against it." Test DDL is always Django-generated, in-process, against ephemeral
`test_*` databases. If the directive covers test databases, the Django test runner does not
survive in any documented configuration.

**Prior art is absent.** No documented case of any team running Liquibase or Flyway as schema
authority for a Django app was found — no blog post, talk, or maintained repo. The only bridge
package, `liquimigrate`, last released 2016 and predates Django 2.0. A 2026 empirical survey of
schema-migration practice found every Django project using Django migrations and every Liquibase
project on the JVM; no cell combines them. **This is the largest risk in the proposal.**

**Django has no `ddl-auto: validate`.** The Liquibase+Hibernate pattern works because Hibernate
refuses to start on model/schema drift. Django has no equivalent: `migrate --check` and
`makemigrations --check` compare models to *migration files*, never to the live schema. Drift is
therefore invisible until a runtime `ProgrammingError`.

**Packaging is a hard blocker.** Liquibase is **not on conda-forge**. The only anaconda.org hit is
a third-party `maize-genetics/liquibase` 4.21.0 with zero recorded downloads, two major versions
behind current Community (5.0.4, 2026-08-20). It needs Java 17+ (`openjdk` *is* on conda-forge),
and since 5.0 the Community container **no longer bundles the PostgreSQL JDBC driver** — LPM
fetches drivers over the network, so an air-gapped build must bake the JAR into a derived image.

> **Verdict — the least-bad implementation.** (1) Revoke DDL at the **database role**: the app role
> gets DML only, a separate migration role holds `CREATE`/`ALTER`/`DROP`. This is the only control
> an auditor can verify and it makes every other failure loud. (2) Liquibase owns production DDL
> via a Helm `pre-upgrade` hook Job — **not** an init container, which on N replicas means N
> concurrent runs contending for `DATABASECHANGELOGLOCK` whose default wait is 5 minutes.
> (3) Keep Django migrations as the *authoring* surface, extract with `sqlmigrate`, land as
> Liquibase changesets, and gate staleness in CI — **this gate has no prior art; we build it.**
> (4) Run Liquibase first, then `migrate --fake`, so no Django DDL is emitted, history stays
> consistent, and `post_migrate` still populates content types and permissions. (5) **Carve test
> databases out of the directive explicitly.**
>
> If the estate's real goal is auditable, DBA-gated DDL rather than Liquibase specifically, step 1
> alone delivers most of it at a fraction of the cost.

**Open:** whether air-gap policy accepts a container as the delivery vehicle for a non-conda tool;
Liquibase issue #7791 (multi-schema `default-schema-name` regression on 5.0.3) fixed in 5.0.4 or
not; whether Secure-tier drift detection — arguably the feature justifying the directive — is in
scope and whether its licensing telemetry works air-gapped.

---

## 3. Lane 1 CMS — Wagtail is a clean fit, **CodeRed CMS is not.**

**Wagtail: adopt.** 7.4.3 LTS, released 2026-08-20, supports Django 5.2 and Python 3.12. **No
Wagtail version requires Django 6** — 5.2 is in fact the only Django supported across the entire
current 7.0→8.0 range. conda-forge carries 7.4.3, uploaded about four hours after PyPI, with the
full transitive closure already present. **No new feedstock work.** PostgreSQL FTS is a supported
search backend, so no Elasticsearch service is needed — a real win air-gapped. And
`WAGTAILADMIN_LOGIN_URL` (added 6.0, extended 7.1 to cover logout) is a first-class hook for
putting the admin behind allauth's OIDC flow.

**CodeRed CMS: do not adopt.** `coderedcms` 6.0.0 shipped 2025-09-12 and **nothing has landed on
`main` since that same day** — eleven months. No push to any branch since 2025-12-16. It declares
support only for Wagtail 7.0–7.1 while the current LTS is 7.4.3. It carries an open, unfixed
functional break *inside its own support window*: issue #710, form submissions 404 in the Wagtail
admin because `CoderedFormMixin` doesn't inherit Wagtail's `FormMixin`; community fix PR #717
unmerged since 2026-07-17. An outside PR to support Wagtail 7.3 has sat unanswered since
2026-04-28. It is on conda-forge at 6.0.0 — the feedstock is current; it is upstream that stopped.

**Separate packaging finding, and it affects everything.** conda-forge's Django 5.2 line **stopped
at 5.2.15 (2026-06-06)** while upstream shipped 5.2.16 (2026-07-07) and 5.2.17 (2026-08-04).
conda-forge's autotick bot follows newest-upstream, so it moved to the 6.x line and left 5.2
behind. Under our pin `>=5.2.15,<6` **exactly one conda-forge build qualifies, with zero
resolution headroom, two patch releases behind upstream.** Closing that needs a 5.2 maintenance
branch on `django-feedstock` that does not exist today.

**Multi-replica caveats for Wagtail** (documented, all solvable): media must move off the pod
filesystem to object storage via `django-storages` (on conda-forge); cache must be shared (Redis,
already present); and since 6.4 Wagtail routes indexing through `django-tasks`, which ships
database and RQ backends but **no Celery backend** — so either accept in-request execution or
write a `BaseTaskBackend`.

> **Verdict.** Wagtail yes, CodeRed no. Build the Lane 1 CMS on Wagtail directly, or evaluate an
> alternative page-builder. The Dream's "Wagtail + CodeRed CRX" pairing should be reduced to
> Wagtail alone.

---

## 4. BS-4 — PyBreaker. **Cannot circuit-break the async path.**

`pybreaker` 1.4.1 is on conda-forge, dependency-free, BSD-3. Its `CircuitRedisStorage` works
across replicas and its docs literally use `from django_redis import get_redis_connection` — a
good fit for the sync Django side.

**But its async support is Tornado, not asyncio.** The source imports `from tornado import gen`
and wraps `call_async` in `@gen.coroutine`. There is no `async def` and no `await` anywhere in the
module. **Consequence: passing an `httpx.AsyncClient` coroutine to `breaker.call()` returns the
un-awaited coroutine object, the breaker records an immediate success, and the circuit never
trips.** A native `acall` exists only as an unmerged PR from 2026-03-21.

Upstream is low-activity: no functional code change merged in ~11 months, three asyncio PRs open
since March 2026. Not abandoned, but assume no upstream fix on our timeline.

**The alternatives are worse.** `aiocircuitbreaker` is the only async breaker already on
conda-forge — and upstream has been dormant since January 2022 with 5 stars. `purgatory` is
maintained into 2025 but is not on conda-forge and has 4 stars. `aiobreaker` is five years stale.
The whole Python circuit-breaker landscape is low-activity; PyBreaker is perversely among the
healthier options.

> **Verdict.** Use PyBreaker for sync Django→service calls where it genuinely works, and
> hand-write the ~40-line async wrapper against PyBreaker's own state storage for
> `httpx.AsyncClient` paths — which is what the unmerged `acall` PR does. Avoids both a new
> feedstock and an unmaintained dependency. Note also that its Redis state transitions use plain
> `setnx`/`set`/`incr` with no Lua or `WATCH`, so cross-replica transitions are not atomic; treat
> `fail_max` as coarse protection, not exact-count semantics.

---

## 5. OpenFeature and `django-lasuite` — one blocked, one mis-premised.

**OpenFeature: hard packaging blocker.** A global anaconda.org search for `openfeature` across
**all channels returns zero results.** Not conda-forge, not anywhere. Adoption costs new feedstock
work in every variant: 1 minimum (`openfeature-sdk`, which has zero runtime deps and is about as
simple as a `noarch` recipe gets), 2 for the env-var provider, **4 for the flagd FILE resolver**,
5 including `django-openfeature`. Additionally `wasmtime` is not on conda-forge, which kills GO
Feature Flag's in-process WASM mode outright, and conda-forge's `cachebox` is 6.2.5 while the
flagd provider pins `<6`.

Status correction: OpenFeature is CNCF **Incubating**, not graduated — the graduation issue has
been open since 2024. A CloudBees blog claiming "graduated" is wrong.

If we do adopt it, the flagd **FILE resolver** is the strongest air-gap answer (in-process, local
JSON, full targeting engine, no daemon). But note the SDK's async methods only help if the
*provider* implements them, and **none of the shipped providers do** — `_async` appears zero times
in the flagd, OFREP and env-var providers. For an in-memory/file lookup that's negligible; for any
network-backed provider it blocks the event loop.

**`django-lasuite`: the Dream's premise is wrong.** It is real, healthy (0.0.28, MIT, DINUM,
roughly monthly releases), Django 5.2-compatible, and on conda-forge. But it is **not a UI layer,
not a theme, and contains no app switcher**. Its modules are OIDC login, OIDC resource server,
malware detection, marketing backends, DRF throttling, admin colour customisation, and
secret-from-file config. The six shipped how-tos are all OIDC, malware, or marketing.

La Suite's app switcher is **"La Gaufre"**, and it has no Python packaging path — it ships as
`@gouvfr-lasuite/ui-kit` (npm/React) or a vanilla-JS widget, and its dynamic service-list endpoint
`integration.lasuite.numerique.gouv.fr/api/v1/gaufre` **is unreachable from an air-gapped
deployment**. Only the static-JSON variant is offline-viable, and it would surface a French
government service catalogue rather than our own navigation.

**And there is no documented La Suite "reusable-app pattern" at all.** Their `dev-handbook`'s
`python.md` is a PEP 8 style guide. The observable practice is ~20 independent Django repos
converging on one shared PyPI library and one shared npm library — a two-package convergence along
the language boundary, not a framework, and not written down as guidance.

Worth knowing: the conda-forge `django-lasuite` feedstock's sole listed maintainer is **`rxm7706`**
— our own account. "It's on conda-forge" is self-supplied here, with no bus-factor cover.

> **Verdict.** Adopt `django-lasuite` for what it actually is — OIDC plumbing — and build
> `django-pyforge` as our own shared-chrome package rather than expecting La Suite to supply one.
> Defer OpenFeature until someone owns the feedstock work, or start with a custom `AbstractProvider`
> over Django settings, which needs only `openfeature-sdk` itself.

---

## Consolidated conda-forge gate

| Package | On conda-forge | Consequence |
|---|---|---|
| `wagtail` 7.4.3 | yes, same-day, full closure | adopt freely |
| `coderedcms` 6.0.0 | yes, but upstream dead 11 months | do not adopt |
| `django` 5.2.15 | yes — **and only 5.2.15** | zero headroom, 2 patches behind upstream |
| `mcp` 2.0.0 | yes, `2026-07-28`-capable | the only current-spec path |
| `fastmcp` 3.4.4 | yes, but pre-`2026-07-28` | v4 is beta; not yet viable |
| `django-lasuite` 0.0.28 | yes (sole maintainer `rxm7706`) | adopt as OIDC plumbing only |
| `pybreaker` 1.4.1 | yes | sync only; async needs our wrapper |
| `aiocircuitbreaker` 2.0.0 | yes | only async breaker, dormant since 2022 |
| `django-storages`, `django-redis`, `openjdk`, `celery` | yes | no work |
| **`openfeature-sdk` + all providers** | **no — zero results anywhere** | 1–5 new feedstocks |
| **`wasmtime`** | **no** | kills GOFF in-process mode |
| **`liquibase`** | **no** (third-party 4.21.0, 0 downloads) | feedstock or container decision needed |
| `purgatory`, `aiobreaker` | no | not worth feedstock work |

## What this changes for the Spec

1. **BS-2 must be rewritten** — `/mcp/sse` and the 30m timeout are stale. Target: POST `/mcp`,
   Tasks extension, sub-30s keep-alives.
2. **RFC-5's "as written" ruling needs revisiting** — the literal form is not implementable; the
   role-revocation + `migrate --fake` + test-DB-carve-out form is.
3. **CodeRed CMS drops out** of the Lane 1 stack; Wagtail alone stands.
4. **BS-4 gains a build task** — the async breaker wrapper — rather than a dependency.
5. **OpenFeature and Liquibase each need a packaging decision** before either can be an acceptance
   criterion.
6. **`django-pyforge` is ours to build** — `django-lasuite` supplies OIDC, not chrome.

## What the later-day operating-model bind adds (does not replace §1–5)

7. **Q2 / AD-14** — do not write “a station is unfinished on fewer than five tiers” into
   acceptance criteria for 01/02 work. The eight stations remain 03 and still owe all five.
8. **AD-21 + Q8** — design processes as hook specifications + plugins. Do not require Warden
   (or every station) to become a Kedro project. Do not let a plugin publish a second PR
   verdict.
9. **Q5** — do not invent scorecard metrics in this chain. No CAP-18.
