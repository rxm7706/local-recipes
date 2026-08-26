---
title: "PRD: the Canopy mounts the eight stations"
status: "in-progress"
created: "2026-08-24"
updated: "2026-08-26"
chain: "pyforge-unifying-strategy"
owner: "steward"
extends: "spec-python-agent-platform"
inputs:
  - "../../specs/spec-pyforge-unifying-strategy/SPEC.md"
  - "../../specs/spec-pyforge-unifying-strategy/convergence.md"
  - "../../specs/spec-pyforge-unifying-strategy/resilience-invariants.md"
  - "../../specs/spec-pyforge-unifying-strategy/stack.md"
  - "../../briefs/brief-pyforge-unifying-strategy-2026-08-24/brief.md"
  - "../../research/technical-pyforge-unifying-strategy-research-2026-08-24.md"
  - "../../research/technical-pyforge-unifying-strategy-airgap-delivery-2026-08-24.md"
---

# PRD: the Canopy mounts the eight stations

## 0. Document Purpose

This PRD decomposes `spec-pyforge-unifying-strategy` into functional requirements an epic pass can
group and a dev session can implement. **The SPEC is the contract; this document is its
decomposition.** Where they disagree, the SPEC wins and this document is wrong.

Every FR carries the capability ID it realizes. Nothing here floats: an FR with no CAP is scope
creep, and a CAP with no FR is an unmet contract. The traceability check at §12 is mechanical for
exactly that reason.

Two things this PRD deliberately does not do. It does not restate what `spec-python-agent-platform`
already shipped — `convergence.md` is the authority on that boundary, and re-specifying a `done`
surface is how an extension quietly becomes a rewrite. And it does not choose mechanisms; those
live in `addendum.md` and the architecture pass, except where a mechanism was already decided and
recorded, in which case the FR names it as a constraint rather than pretending it is open.

## 1. Vision

An operator signs in once and the whole estate is in front of them: a published front page, eight
station portals, an analytical board that shows them only their own rows. An agent addresses the
same eight stations through one grammar and one service shape, and survives the connection dropping
mid-build. A station's action becomes an event another station acts on. All of it inside an
egress-blocked namespace where the application cannot alter its own schema.

The Canopy already proved this is reachable. **The 2026-08-25 drain landed the eight portals,
chrome, host MCP faces, dispatch, events, and the governed-DDL path in code.** Closeout
**2026-08-26:** Lane 1 `/` **200**, CAP-9 `platform_app` DML-only proven, Liquibase
`:17`–`:19` executed. Isolated `mfa` sqlmigrate stays fake. Not a `services/` rewrite.
**2026-08-26 evergreen:** CAP-19 (query plane) reopens this PRD. CAP-1..18 stay shipped
slices. Rebuild of private analytical stores is in scope.

## 2. Target User

Four users, and the fourth is not a person. That is load-bearing rather than cute: several of the
nineteen capabilities exist mainly to make the estate legible to something that is not a human, and
a requirement written only for the human reader will under-specify them. CAP-19 adds the
**query** as a shared job — dashboards and agents must share one plane.

### 2.1 Jobs To Be Done

| User | Job | Blocked today by |
|---|---|---|
| **Platform operator** (steward's own audience) | Deploy, upgrade and audit the estate in a regulated namespace | Schema change is whatever the migration graph did; the app's role can alter its own schema |
| **Compliance auditor** | Move from a finding to the package, build and fleet context around it | Warden's portal exists and shows compliance; nothing else has a portal |
| **Packaging / platform engineer** | Drive any station without learning eight tools | Eight CLIs, eight verb vocabularies, eight output shapes |
| **Autonomous agent** | Perform a station's work programmatically and reliably | One station of eight has a service face; long operations die with the connection |
| **Dashboard / agent query** | Ask the estate a question (metric, SQL, neighbor) | Five private stores; Text-to-SQL can still hit OLTP |

### 2.2 Non-Users

- **The public.** Lane 1 is a front door for the estate's own operators, reachable only behind the
  identity provider. "Public" in CAP-2 means "not gated per-page", not "unauthenticated".
- **External API consumers.** CAP-4's service face is for estate callers and estate agents. No
  external contract, no versioning promise to third parties.
- **Multi-tenant customers.** CAP-7's row isolation is per-user row filtering on analytical boards,
  not a tenancy layer, and nothing here makes the estate multi-tenant.

### 2.3 Key User Journeys

**UJ-1 — One session, four surfaces.** An operator opens the estate root, reads a runbook page an
editor published this morning without a deploy, uses the app switcher to jump to the packaging
station's portal, follows a link into an analytical board, and sees only rows their role permits.
They authenticate once, at the start, and never change origin.

**UJ-2 — The agent that survives the proxy.** An agent connects to a station's service face,
starts an operation that takes several minutes, and loses its connection to a router that closes
idle streams at thirty seconds. It reconnects, re-attaches to the same operation, and collects the
result. Nothing is recomputed and nothing is lost.

**UJ-3 — The event that crosses stations.** A build completes. The event is published once and a
different station consumes it and acts. A malformed event published by a buggy producer lands in a
dead-letter queue after its retry budget rather than blocking the group forever, and an operator
can see it there.

**UJ-4 — The audited upgrade.** An operator runs a chart upgrade. A governed changeset applies the
schema change under a role that holds DDL rights; the application's own role does not and provably
cannot. The application then starts and its framework bookkeeping still runs. The change is
attributable to a reviewed changeset, not to whatever an ORM decided to emit.

**UJ-5 — The flag flip.** An operator changes one flag value. Web, service and CLI surfaces all
observe the new behaviour, with no redeploy and no outbound network call.

**UJ-6 — The query that misses OLTP.** A Vizro board and a DB-GPT Text-to-SQL ask the same
estate question. Both read the query plane (live attach for a declared view, Parquet for a
scan, `vss` for a neighbor). Neither opens a private DuckDB or Chroma, and neither is
given the OLTP DSN. A guessed `SELECT` against the system of record is a refused
configuration, not a hot table.

## 3. Glossary

Defined once. The rest of the document uses these exactly, and no synonyms.

- **Canopy** — the Django host at `src/platform/`. Live today. Not renamed by this chain.
- **Station** — one of the eight PyForge capability domains: warden, atlas, mason, marshal, doctor,
  herald, scribe, steward. The roster is fixed at eight.
- **Lane 1** — the CMS-managed front door mounted at `/`.
- **Lane 2** — a station's server-rendered portal, mounted under the Canopy as a Django app.
- **Lane 3** — an analytical board surface, reached through the Canopy, isolated per user.
- **Service face** — a station's programmatic endpoint, spoken over the current MCP specification.
- **Five-tier symmetry** — an **03** station capability is complete when it has all five of: CLI,
  portal, service face, domain skill, persona. The eight stations are 03. 01/02 work is complete
  at spec + script/analysis or spec + skill and is not measured on this matrix.
- **work_class** — 01 one-off, 02 short-term (spec + skill), 03 long-term (capability + owner +
  SLA). Estate operating model (Dream Grounding Q1–Q2).
- **Path A / Path B** — 03 is deterministic code (Path A) or agentic work through the Agent
  Canopy and a station persona (Path B). **Tachyon** is a production LLM provider adapter, not
  Path B and not a product.
- **Domain skill** — an agent-loadable document encoding how a station's work is actually done.
- **Persona** — an autonomous agent bound to one station, acting only through that station's
  command grammar and service face.
- **Chrome** — the app switcher, base layout and theme assets shared by every portal. Owned by one
  package; never by a portal.
- **Governed changeset** — a reviewed, versioned schema-change unit applied by an authority holding
  DDL privilege, distinct from the application's own migration bookkeeping.
- **Feedstock** — a conda-forge recipe. Six are new work in this chain.
- **Hooks and plugins** — architecture principle (canopy AD-21): a process owns
  hook specifications; a plugin replaces or extends a layer without a fork.
  Kedro names the split; it does not require a Kedro project. **CAP-18** is the
  shared contract (not a scorecard). Q8 is the PR-gate instance (Warden owns
  those specs; scanners are plugins).
- **Query plane** — the one DuckDB analytical engine (live read-only Postgres
  attach, Kedro Parquet cache, `vss` vectors). Stations and agents are clients.
  Platform Postgres stays OLTP / app state. **CAP-19**, canopy AD-22.

## 4. Features

Sixteen features over nineteen capabilities (CAP-1..19). Grouped by delivery seam, which is also
how the epic pass groups them. Canopy Epics 18–30 do **not** implement CAP-18; that is Epic 32
plus Warden Epic 9 plus per-station process-hook stories. **CAP-19 is Epic 34.**

---

### 4.1 Shared chrome

**Description.** One installable Django app supplies everything a portal needs to look and behave
like part of the estate: the app switcher, an OIDC-aware base layout, the Modernist theme assets,
and the seam by which a portal registers itself with the host. It is built first because
everything visual depends on it, and a portal built before it exists will grow its own chrome that
nobody removes later. Realizes UJ-1.

Nothing off-the-shelf supplies this. `django-lasuite` — which the Dream named — is OIDC, DRF and
malware-scanning plumbing with no switcher and no theme, and La Suite's own switcher ships as
npm/React against a service-list endpoint unreachable in an air gap. This package is ours.

**Functional Requirements:**

#### FR-1: Chrome is installable, and singular

A portal author installs one package and receives the estate's chrome. Realizes UJ-1. **CAP-1.**

**Consequences (testable):**
- Two portals render byte-identical chrome markup sourced from the package.
- A test enumerates portal template and static directories and **fails** if any portal ships its
  own copy of a base layout, app-switcher template, or theme asset.
- Removing the package from `INSTALLED_APPS` breaks both portals identically.
- Registration carries owner station slug, backup, `work_class`, and promotion date. The SLA
  body is not a chrome / AppConfig field (it stays in the 03 BMAD spec).

#### FR-2: A portal registers itself without host edits

Adding or removing a station portal changes no host code outside that portal's own registration.
**CAP-1, CAP-3.**

**Consequences (testable):**
- Adding a portal requires no edit to the host's root URLconf or settings beyond an entry the
  portal itself supplies.
- Removing a portal leaves the host booting and the remaining portals rendering.
- The app switcher's entries derive from what is registered, not from a hand-maintained list.
- A portal registering outside the `/stations/<name>/` prefix fails a check.
- The switcher and Guildhall do **not** tile a registration with `work_class` 01 or 02 as a
  first-class station surface.

#### FR-3: The switcher shows only what the user may reach

The app switcher renders the stations the signed-in user is authorized for. **CAP-1, CAP-12.**

**Consequences (testable):**
- A user lacking a station's role does not see it in the switcher.
- The switcher is not the enforcement point — requesting a hidden station's URL directly is still
  refused by that station's own authorization.

**Notes:** The estate's existing portal (`compliance_face`) mounts at `/compliance/`, not under a
`/stations/` prefix. **Decided 2026-08-24: uniform prefix, and `compliance_face` moves** — see
FR-9a. The pre-audit draft asserted `/stations/{station}/` as an inherited convention; it was not,
and choosing it now is a decision with a migration attached rather than a free default.

---

### 4.2 Lane 1, the front door that replaces a console

**Description.** A CMS-managed front door at `/` whose pages are edited and published without a
code deploy, with its admin reachable only through the identity provider. It **supersedes** the
estate's existing statically-built console rather than sitting beside it — so this feature carries
a migration obligation, and the ordering inside it is the whole point: parity is proven before the
old build path is removed. Realizes UJ-1.

Wagtail carries it alone. CodeRed CMS was ruled out on maintenance evidence.

**Functional Requirements:**

#### FR-4: Content publishes without a deploy

An editor changes a page and the change is live with no code deploy and no pod restart.
Realizes UJ-1. **CAP-2.**

**Consequences (testable):**
- A page edit is visible to an anonymous-within-estate request without a new image or a rollout.
- Content survives a pod restart and is visible identically from every replica.

#### FR-5: The CMS admin is behind the estate identity provider

An unauthenticated request to the CMS admin is redirected to the identity provider, not to a local
login form. **CAP-2, CAP-12.**

**Consequences (testable):**
- The admin login URL resolves to the IdP; no local password form is reachable.
- Local password management and email-management surfaces are disabled.
- A user who authenticates but holds no group granting CMS admin access is refused **with a
  comprehensible error**, not an unexplained bounce.

**Notes:** The last consequence is the one that bites. CMS admin access gates on a specific
permission rather than a generic staff flag, and OIDC users arrive with no groups — so a correctly
authenticated user is refused by default until claim-to-group mapping exists. There is no
first-party guidance for this; treat it as real work, not configuration.

#### FR-6: Console parity is inventoried before anything is removed

Every view the retired console offers is enumerated and classified as runtime-reproducible or
build-time-only **before** the cutover. **CAP-2. Satisfied 2026-08-24** by
`specs/spec-pyforge-unifying-strategy/console-parity-inventory.md`.

**Consequences (testable):**
- An inventory artifact exists listing every console view with its data source and classification.
  **Done:** 23 surfaces — 14 runtime-reproducible, 7 build-time-only, 3 mixed.
- Any view classified build-time-only is escalated as a scope decision rather than silently
  dropped. **Done:** the seven reduce to four decisions, recorded in the inventory.
- The inventory is the cutover's precondition: FR-7 cannot start until it is complete.

**Notes:** The four decisions are live run state (three surfaces, one decision), detector verdicts,
curated editorial content, and journal-derived timing. The fifth build-time-only item — the
committed-snapshot delivery model — is not a loss to mitigate; removing it is the point of CAP-2.

#### FR-7: The old build path is removed, not unlinked

After parity, the console's generation pipeline is deleted — not merely delisted from navigation.
**CAP-2.**

**Consequences (testable):**
- The generator, its four pixi tasks, its scheduled workflow trigger, and the committed data blob
  are gone.
- No inbound reference to the retired path remains in docs, workflows, specs, presentations,
  scripts or tests.
- The co-published Kedro-Viz tree **survives** — it has its own workflow and no inbound link from
  the console, so it is not part of this obligation and must not be deleted with it.
- Downstream parsers of the committed data blob are identified and migrated first.
- `spec-factory-console` is marked superseded in the same chain — a superseded spec still claiming
  ownership is a worse outcome than two consoles.

**Notes:** `[NOTE FOR PM]` the inventory found **over 100 inbound references** to the console path
across dreams, specs, presentations, pixi tasks, workflows, tests and scripts — including the
Charter's own accountability gate. The reference sweep is its own story, not cleanup at the end of
another one. The inventory recommends splitting this feature's retirement into three stories:
inventory (done), parity build, removal.

#### FR-8: Media and cache survive multiple replicas

Lane 1 operates correctly with more than one replica. **CAP-2.**

**Consequences (testable):**
- Uploaded media is retrievable from a replica that did not receive the upload.
- An image rendition generated by one replica is served by another without regeneration.
- No Lane 1 state depends on pod-local disk.

**Feature-specific NFRs:**
- Search uses the database backend (PostgreSQL full-text). No fourth backing service.
- Background task routing is an explicit decision, not a default — the CMS's task layer ships
  database and RQ backends and **no Celery backend**, so inheriting the default silently splits the
  estate's task story. See `addendum.md`.

---

### 4.3 Eight portals, one session

**Description.** Every station becomes reachable as a Lane 2 application under the one host, so an
operator moves between stations without re-authenticating or changing origin. One of eight exists
today. Realizes UJ-1.

**Functional Requirements:**

#### FR-9: All eight stations resolve behind one session

Eight portal URLs resolve, and a single authentication covers all of them. **CAP-3.**

**Consequences (testable):**
- Requesting each of the eight portals in one session triggers no re-authentication.
- All eight are same-origin with Lane 1.
- All eight mount under `/stations/<name>/`.
- The existing compliance portal is one of the eight and is not re-implemented.

#### FR-9a: The moved portal does not break its old URL

`compliance_face` relocates from `/compliance/` to `/stations/warden/` and the old path keeps
working. **CAP-3.**

**Consequences (testable):**
- `/compliance/` returns a permanent redirect to `/stations/warden/`, preserving path and query
  beneath it.
- The redirect survives as a supported route, not a temporary shim — it is not scheduled for
  removal in this chain.
- No inbound reference to `/compliance/` anywhere in the repo is left pointing at a 404.

#### FR-9b: Station portals are reusable Django apps under one naming scheme

`compliance_face` is repackaged as a reusable Django app following
[Django's reusable-app convention](https://docs.djangoproject.com/en/6.0/intro/reusable-apps/), and
that convention becomes the scheme every station's portal follows. **CAP-3.**

The triple, for warden:

| | Name |
|---|---|
| Distribution | `django-warden`, at `src/shared/packages/django-warden/` |
| Module | `django_warden_fabric` |
| App label | `warden_fabric` |

**Consequences (testable):**
- No identifier spelled `compliance_face` survives anywhere in `src/`.
- **One distribution per station, holding one or more apps** — the `django-allauth` shape. A second
  warden surface becomes a sibling app inside `django-warden`, not a second distribution.
- Every station portal's app label is `<station>_<app>`, so labels are unique across
  `INSTALLED_APPS` for any number of stations and apps, and no label collides with a Django contrib
  app.
- It installs as an in-repo path dependency — **not** a conda-forge feedstock, since it is
  first-party and never leaves the repo.
- A migration carries the app-label change: the model's table, its `django_migrations` rows and its
  `django_content_type` row all move, and applying it to a populated database preserves every
  existing job row.
- Warden's two shipped specs that name the old app still resolve — no dangling reference is left in
  `_bmad-output/projects/pyforge-warden/`.

**Notes:** Ruled 2026-08-24. **Sequencing is the whole point of putting this here.** The app carries
`label = "compliance_face"`, so renaming it is a table rename plus content-type and
migration-history updates. Today that is an ordinary Django migration. Once CAP-9 lands the
application role loses DDL rights and the same rename becomes a governed Liquibase changeset — so
this must precede §4.9, and folding it into FR-9a's move costs one disruption instead of two.

Two properties of the scheme are load-bearing and should not be simplified away later:

- **The label is `warden_fabric`, not `warden`.** A per-station label cannot survive a station
  owning a second app, and Django requires labels to be unique in `INSTALLED_APPS`. The compound
  form reserves room for `warden_baseline` beside it at no cost.
- **New concerns get new sibling apps; existing models never move between apps.** Moving a model
  later costs exactly what this FR is paying now. Adding a sibling app costs nothing. So the estate
  starts at one app per station without ever having to pay a split.

`[NOTE FOR PM]` this is the only requirement in the PRD that renames shipped, working code. It earns
its place by riding along with a move that was happening anyway; it would be hard to justify alone.

This also settles a question the PRD had left implicit: `src/shared/packages/` holds **two families
under two conventions** — station CLI/library packages (`pyforge-warden` → `pyforge.warden`, entry
point `warden = "pyforge.warden.cli:main"`) and Django reusable apps (`django-*` → `django_*`).
`django-pyforge` is correct as it stands; it is a reusable app, not a CLI package.

One editorial change followed: CAP-8's backbone was called the "event fabric" in four places, which
would have read confusingly beside `warden_fabric` in the same architecture diagram. It is now
uniformly the **event backbone**, which was already the dominant term.

#### FR-10: A portal holds no station logic

A portal renders and dispatches; the station's behaviour stays in the station. **CAP-3, CAP-6.**

**Consequences (testable):**
- A portal reaches its station only through the shared client (FR-14).
- No portal imports station internals directly.
- A test asserts no portal constructs a raw HTTP request to a service.

---

### 4.4 Service faces for agents

**Description.** Each station exposes its capabilities to programmatic and agent callers over a
current-specification MCP endpoint, with long operations surviving connection loss. One station
(atlas) has a server today; seven do not. Realizes UJ-2.

The transport question is settled and it is not what the Dream said: the SSE transport it named is
deprecated twice over, and a compliant current server answers a GET to its endpoint with `405`.
A single POST endpoint on the official SDK is the target.

**Functional Requirements:**

#### FR-11: Eight stations answer on a current-specification endpoint

Each station exposes a service face implementing the current MCP specification. **CAP-4.**

**Consequences (testable):**
- A conformance check passes against each of the eight endpoints.
- Each endpoint accepts **`2025-03-26` through `2026-07-28`** — the four handshake revisions and
  the modern one — served from one deployment.
- An `initialize` request is answered with **the revision the client asked for**, never the
  server's own newest.
- A request declaring an unsupported revision returns `-32022` with the supported list attached,
  rather than failing opaquely.
- No code path selects behavior from the client's name or user-agent.
- The deprecated dual-endpoint SSE shape is not served.
- Atlas's existing server is brought to the same specification rather than duplicated.

**Notes:** The revision range is not a compatibility nicety — the client fleet is genuinely split.
Copilot and Zed sit at `2025-11-25`, Gemini CLI at `2025-06-18`, and Codex already sends
`2026-07-28`. Pinning either end alone rejects real traffic. Cursor's revision is unpublished, which
is itself an argument for accepting the range rather than enumerating known clients.

The echo rule earns its own consequence because the failure it prevents is counter-intuitive: a
client receiving a revision it does not recognize aborts **even when that revision is newer**.
Asserting the newest is a self-inflicted rejection, not a forward-compatible default.

#### FR-12: A long operation survives a disconnect

An operation exceeding the ingress idle timeout completes and its result is retrievable after the
client reconnects. Realizes UJ-2. **CAP-4.**

**Consequences (testable):**
- A multi-minute operation run across a simulated ingress disconnect yields its result on
  reconnection.
- The operation is not recomputed on reconnect.
- The starting call **returns without holding the connection**, proven by the response arriving well
  before the operation completes.
- The result is retrievable **from a different replica** than the one that started the work, so no
  session affinity is required.
- A handle is opaque and high-entropy, and expires — it is not a guessable or permanent identifier.
- Keep-alive interval is under 30 seconds where any stream exists at all, verified by inspecting
  emitted traffic — not by a route annotation, which is defence-in-depth only.

**Notes:** **OQ-3 is answered, and the answer removes the mechanism this FR was expected to use.**
There is no server-side Tasks runtime in the official SDK — it is listed under *Known gaps*, and the
only implementation in any language is a beta on an unreleased FastMCP 4 that conda-forge cannot
accept. So the requirement is delivered as a **`start`/`get` tool pair over a durable store**.

This is why the FR is worded as an outcome rather than a mechanism. The pair implements the same
lifecycle SEP-2663 standardizes, so adopting Tasks later is a wire-layer swap over the same store —
the durable store is the hard part, and the extension only replaces the layer above it.

Three things that look like they satisfy this FR and do not: progress notifications travel down the
live connection and die with it (they solve the spinner, not the disconnect); sticky-session
affinity is ruled out because the modern protocol revision deliberately removed sessions; and
home-grown stream replay reimplements the hard part badly. The "different replica" consequence
exists specifically to make the affinity shortcut fail its test.

`[NOTE FOR PM]` Tasks is worth a **scheduled re-check** rather than treating this as settled
forever. SEP-2663 is Final, the SDK's pluggable extension API has landed, and the tracking issue is
open to bring the extension in-repo — this could plausibly resolve during the chain.

---

### 4.5 One command grammar

**Description.** A single entry point dispatches `pyforge <station> <noun> <verb>` to the eight
existing station CLIs without reimplementing their logic. The station binaries remain first-class;
this is a front door, not an absorption.

**Functional Requirements:**

#### FR-13: Every station verb is reachable through one entry point

`pyforge <station> <noun> <verb>` reaches the same behaviour as the station's own binary.
**CAP-5.**

**Consequences (testable):**
- A generated parity matrix lists every station verb and shows it reachable through both paths.
- The build **fails** when the two diverge — a verb added to a station CLI and not reachable
  through the unified entry point breaks CI.
- No station CLI's logic is reimplemented; dispatch only.

**Notes:** `[ASSUMPTION: the eight station CLIs expose a surface stable enough to dispatch to
without modification.]` Unverified per-station. If a station's CLI cannot be introspected for the
parity matrix, that station needs a preparatory story.

---

### 4.6 One client, carrying identity

**Description.** Portals reach station services through a shared client that carries the end user's
identity as a signed, audience-bound assertion — not a trusted header a compromised caller could
forge. This is the seam that decides whether the estate's internal traffic is auditable, so it
lands before the portals that will use it.

**Functional Requirements:**

#### FR-14: A service can verify on whose behalf it was called

A station service independently verifies the end-user identity behind a portal call. **CAP-6.**

**Consequences (testable):**
- A service rejects a call whose assertion fails signature or audience validation.
- A service rejects an assertion minted for a different audience.
- An expired assertion is refused.
- No portal-to-service path exists that does not carry one.

#### FR-15: The trusted-header path does not exist

Identity is never asserted by an unverified header. **CAP-6.**

**Consequences (testable):**
- A request bearing an identity header but no valid assertion is refused.
- A test asserts no portal code constructs a raw request to a service.

---

### 4.7 Analytics behind the front door

**Description.** Atlas's analytical boards become reachable through the host, with per-user row
isolation enforced at the identity boundary, adopting the estate's existing secure-dashboard
pattern rather than inventing a second one. Realizes UJ-1.

**Functional Requirements:**

#### FR-16: Two roles, same URL, different rows

Users with different roles requesting the same board receive provably different row sets.
**CAP-7.**

**Consequences (testable):**
- Two authenticated users of differing roles request one board URL; returned rows differ as their
  roles dictate.
- Isolation is enforced server-side at the identity boundary — not by client-side filtering, and
  not by serving different URLs.
- The board is reached through the Canopy, same-origin and same-session.

**Notes:** This consumes the estate's existing secure-dashboard pattern. Making atlas's own
dashboard adopt that pattern is atlas's story and explicitly out of scope here.

---

### 4.8 Stations can tell each other things

**Description.** A durable event backbone carries structured events between stations, with consumer
groups, poison-message quarantine, and a ceiling on how deep a cascade may run. Realizes UJ-3.

**Functional Requirements:**

#### FR-17: Events are durable and consumed in groups

A published event reaches its consumers and survives a consumer restart. **CAP-8.**

**Consequences (testable):**
- An event published while a consumer is down is delivered when it returns.
- A restart reconciles rather than duplicating — reprocessing does not double-apply effects.
- The envelope carries `spec_id`, git sha, and SBOM purl, plus an optional work-item id. A
  missing Jira key does **not** fail publish or drop the event (Dream Grounding Q4).

#### FR-18: A poisoned event is quarantined, not retried forever

A message that cannot be processed lands in a dead-letter queue after its retry budget.
Realizes UJ-3. **CAP-8, CAP-10.**

**Consequences (testable):**
- A deliberately malformed event ends in the dead-letter queue.
- It does not block the consumer group.
- An operator can enumerate quarantined messages.

#### FR-19: Cascades halt at a declared depth

A cyclic publish chain stops at the declared ceiling. **CAP-8.**

**Consequences (testable):**
- A deliberately cyclic chain halts at the configured depth rather than running away.
- The halt is observable, not silent.

#### FR-20: Validation happens in the domain adapter

Event payload validation occurs in the consuming domain adapter, not at the stream boundary.
**CAP-8.**

**Consequences (testable):**
- A schema-invalid payload is rejected by the consuming adapter with a domain error.
- The stream boundary does not reject on payload shape — it is a transport, not a validator.

---

### 4.9 Governed schema change

**Description.** Production schema change flows through one auditable authority, enforced by
**database privilege** rather than by convention, while the application's own tooling remains where
a developer authors a change. Realizes UJ-4.

This feature reopens shipped work and its literal directive turned out to be unimplementable, so
the shape below is the revised one. The framework's own bookkeeping — content types, permissions,
sites — has exactly one supported population mechanism, and the test runner builds every test
database by running migrations. So migrations keep running; what changes is who is allowed to
execute DDL. That is also the only version of this an auditor can verify, which is the point.

**Functional Requirements:**

#### FR-21: Liquibase is available inside the boundary

The governed-changeset tool resolves from conda-forge like every other Python/pixi dependency.
**CAP-9.**

**Consequences (testable):**
- A recipe exists and builds at **5.0.4 or later**; the tool is available in the platform
  environment.
- The PostgreSQL JDBC driver is **vendored into the recipe** — recent Community releases stopped
  bundling it and the package manager fetches it over the network, which an air gap forbids.
- No new container image is introduced.
- A `runInTransaction="false"` changeset applied against a non-default schema lands in that schema,
  demonstrated against a live PostgreSQL instance.

**Notes:** Per repo Rule 1, this story's dev session invokes `conda-forge-expert`. This FR **gates
the rest of §4.9** — the epic opens with packaging work, not platform work.

The version floor is not arbitrary. 5.0.2 and 5.0.3 carry a defect where `SET LOCAL SEARCH_PATH`
is a no-op outside a transaction, so non-transactional changesets silently resolved in the wrong
schema; it is fixed in 5.0.4. Separately, 5.0.4 is the **first release whose GPG signature verifies
against the rotated signing key**, which decides the recipe's verification step. The last
consequence exists because the fix is currently verified by a reviewer's report rather than by our
own observation — cheap to close, and CAP-9 rests on it.

#### FR-21a: Schema resolution cannot fail silently

Schema targeting is configured so that a misresolution is impossible rather than merely unlikely.
**CAP-9.**

**Consequences (testable):**
- `preserveSchemaCase` is disabled and no schema name is mixed-case — a check fails if either
  changes.
- The connection carries its own schema targeting rather than relying on the tool's search-path
  manipulation.
- The pre-upgrade Job connects directly to PostgreSQL, not through a transaction-pooling proxy.

**Notes:** `[NOTE FOR PM]` this FR exists because of an **open, unfixed** upstream issue: with
`preserveSchemaCase` enabled the schema name is double-quoted into one that does not exist, and DDL
then applies silently to `public`. Silent wrong-schema DDL is the worst available failure mode for
this feature, and the mitigation costs nothing because Django's naming conventions already produce
lowercase. Do not let a later story turn this flag on for a formatting reason.

#### FR-22: The application role cannot alter its own schema

The role the application connects with holds no DDL privilege. Realizes UJ-4. **CAP-9.**

**Consequences (testable):**
- `CREATE`, `ALTER` and `DROP` attempted as the application role are refused **by the database**.
- A separate migration role holds DDL and is used only by the governed step.
- The refusal is a privilege error from PostgreSQL, not an application-level guard.

#### FR-23: A schema change without a governed changeset fails the build

Authoring a model change without its corresponding changeset breaks CI. **CAP-9.**

**Consequences (testable):**
- A model change with no matching changeset fails a check.
- The check names the missing changeset.

**Notes:** `[NOTE FOR PM]` No prior art exists for this — no team is documented running Liquibase as
schema authority for a Django application. Size this as invention, not integration.

#### FR-24: The deploy sequence keeps framework bookkeeping working

The governed step runs before the application's migration step, and the latter still fires
framework post-migration hooks. **CAP-9.**

**Consequences (testable):**
- The governed changeset applies as a pre-upgrade hook Job at a lower hook-weight than the existing
  migration Job, on the same platform image.
- The existing migration Job still runs, so content types, permissions and sites are populated.
- **No init container is introduced** — replicas would contend on the changelog lock, and the
  shipped Job's own documentation records that waiting on hooks deadlocks migration-gated
  readiness.
- The chart contract from the shipped story is not rewritten; this is a seam beside it.

#### FR-25: Test databases are carved out

The governed authority does not apply to test databases. **CAP-9.**

**Consequences (testable):**
- The test runner continues to build databases by running migrations, unchanged.
- No test-suite change is required by this feature.

---

### 4.10 Containment

**Description.** A failing dependency degrades its caller instead of cascading; concurrent writers
cannot corrupt shared analytical state; validation errors reach the user inline; a restart
reconciles rather than duplicates. And the queue and the cache stop being able to evict each other.

Each invariant is demonstrated **individually** — a test that fails with the invariant absent and
passes with it present. A suite that goes green proves nothing about any one of them.

**Functional Requirements:**

#### FR-26: A failing dependency degrades its caller

A dependency failing repeatedly opens a circuit and the caller degrades rather than hanging.
**CAP-10.**

**Consequences (testable):**
- Repeated failures open the circuit; the caller returns a degraded response within its budget.
- **The async path trips correctly** — a failing asynchronous call registers as a failure, not a
  success.
- Removing the containment makes the test fail.

**Notes:** The chosen library's async support targets a different coroutine model; an asynchronous
client call passed to it registers a false success and the circuit never trips. A thin wrapper is
required and is a known, sized piece of work — see `addendum.md`. `[ASSUMPTION: its cross-replica
state transitions are not atomic]`, read from source rather than documentation, so the failure
threshold is coarse protection and not exact-count semantics. Do not write an FR that depends on an
exact count.

#### FR-27: Concurrent writers cannot corrupt shared analytical state

A single-writer boundary is enforced for the columnar analytical store. **CAP-10.**
CAP-19 names that store as the **query plane** (FR-27 *intent* survives if the
file is no longer literally `atlas.duckdb`).

**Consequences (testable):**
- A second concurrent writer is refused or serialized; no corruption occurs.
- The test fails if the boundary is removed.

#### FR-28: Validation errors reach the user inline

A validation failure is rendered in place rather than lost or thrown as an opaque error.
**CAP-10.**

**Consequences (testable):**
- A rejected submission renders its errors inline in the originating surface.
- The test fails if the inline path is removed.

#### FR-29: A restart reconciles rather than duplicates

Work interrupted by a restart is reconciled, not re-applied. **CAP-10, CAP-8.**

**Consequences (testable):**
- An operation interrupted mid-flight and resumed produces one effect, not two.
- The test fails if reconciliation is removed.

#### FR-30: Queue and cache cannot evict each other

Broker and cache are separate resources with separate eviction policies. **CAP-11.**

**Consequences (testable):**
- Filling the cache to its eviction limit **provably loses no queued task**.
- The broker's eviction policy refuses to evict; the cache's evicts by recency.
- Web and worker pools scale independently.

---

### 4.11 Access, secrets, and flags

**Description.** Authorization derives from identity-provider roles rather than locally-managed
state; runtime secrets arrive from a secret manager rather than the pod environment; and behaviour
flips without a redeploy through one vendor-neutral flag interface evaluated entirely offline.
Realizes UJ-5.

**Functional Requirements:**

#### FR-31: Revoking a role at the IdP removes access

A role revoked centrally takes effect on the user's next request. **CAP-12.**

**Consequences (testable):**
- Revoking the role at the IdP denies portal access on the next request — not at next login, and
  not after a cache expiry.
- Local group state is not the authority.

#### FR-32: No long-lived secret appears in a pod specification

Runtime secrets are delivered by a secret manager. **CAP-12.**

**Consequences (testable):**
- No secret value appears in any pod specification or chart value.
- A check over rendered manifests fails if one does.

#### FR-33: Flag packages are available inside the boundary

The flag interface and its provider resolve from conda-forge. **CAP-13.**

**Consequences (testable):**
- Four new feedstocks exist and build: `openfeature-sdk`, `openfeature-flagd-api`,
  `openfeature-flagd-core`, `openfeature-provider-flagd`.
- A `cachebox` 5.x build exists — conda-forge ships 6.2.5 and the provider pins `<6`.
- The version conflict is resolved by that build rather than pinned around silently.

**Notes:** The four OpenFeature packages are absent from anaconda.org **entirely** — a global
search returns zero results. `cachebox` is a different task: the feedstock exists at the wrong
version, so it is a **downgrade build, not a new recipe**, and sizing it as a fifth new recipe
overstates it. Per repo Rule 1 each of these stories invokes `conda-forge-expert`. Like FR-21, this
FR **gates the rest of its feature**.

#### FR-34: One flag flips three surfaces, offline

A single flag change alters behaviour across web, service and CLI. Realizes UJ-5. **CAP-13.**

**Consequences (testable):**
- One flag change is observed by all three surfaces.
- No egress occurs during evaluation — evaluation is in-process from a local source.
- No redeploy and no restart is required.

---

### 4.12 Scribe's graph outlives one file

**Description.** The knowledge graph gains a durable, concurrent-safe backing store behind its
existing port, keeps a local-development path, and gains semantic recall. Today it is one flat JSON
file — the Dream's premise of an existing dual-driver engine was simply wrong, so this is a first
driver, not a second.

**Functional Requirements:**

#### FR-35: The same operations pass against both drivers

Graph operations behave identically against the durable store and the local path. **CAP-14.**

**Consequences (testable):**
- One operation suite passes against both drivers.
- The existing port is unchanged — callers are unaware which driver is active.
- Concurrent writers do not corrupt the durable store.

#### FR-36: Semantic recall returns what lexical recall cannot

Recall finds a semantically relevant result that token-overlap search misses. **CAP-14.**

**Consequences (testable):**
- A query with no lexical overlap with its target returns that target.
- The same query under the lexical path does not.

---

### 4.13 The agent-facing tiers

**Description.** The Dream promises five-tier symmetry — CLI, portal, service, domain skill,
persona — as the **03 shape of each of the eight stations**. The estate has one domain skill of
eight and zero station personas, so two full tiers are missing and an 03 station cannot be called
complete without them. 01/02 work does not owe this matrix. These are the capabilities most
easily dropped as "documentation", which is exactly why the SPEC makes fewer-than-five on an
**03 capability** a contract violation.

**Functional Requirements:**

#### FR-37: Each station carries a domain skill

Every **03** station has an agent-loadable skill encoding how its work is actually done. **CAP-15.**

**Consequences (testable):**
- An agent asked to perform a station's core task loads that station's skill and follows it.
- Demonstrated for a station that has **no** skill today — not for the one that already does.
- Each skill follows the shape the existing one proves.

#### FR-38: Each station is addressable as a persona

Every **03** station exposes a persona that acts only through that station's grammar and service
face. **CAP-16.** 01/02 work does not mint a persona.

**Consequences (testable):**
- A persona completes a station task end to end.
- Its transcript shows **no** direct filesystem access and **no** ad-hoc HTTP calls — only FR-13's
  grammar and FR-11's service face.

#### FR-39: Five-tier completeness is checkable

**03** station completeness is mechanically verifiable, not asserted. **CAP-15, CAP-16.**

**Consequences (testable):**
- A check enumerates all eight **03** stations across all five tiers and reports which are missing.
  Denominator remains 8 × 5 = 40.
- The check fails when an **03** station is declared complete with fewer than five.
- The check does **not** fail 01/02 work for lacking a portal, service, skill, or persona.

---

### 4.14 Run state is a service

**Description.** In-flight execution state — which runs are live, how long they have been going,
and the timing history behind them — is published by a supervisor the front door can query, rather
than read off an operator's local disk when a static page is generated.

This feature exists because of a decision, not a discovery. The parity inventory found that three
of the retired console's surfaces read `~/.bmad-loops`, tmux sessions and journal files directly,
which is why the published board showed `unavailable` for all of them. The inventory recommended
dropping those surfaces; the operator chose on 2026-08-24 to keep them and pay for the service that
makes them deployable. **The replacement is therefore held to a higher bar than the thing it
replaces**, and that is deliberate.

**Functional Requirements:**

#### FR-40: Live run state is queryable, not scraped

The front door obtains run state from a service. **CAP-17.**

**Consequences (testable):**
- Live run state renders in a deployed namespace with **no access to any operator home directory**
  — the deciding test, because it is exactly what fails today.
- No front-door code path reads a filesystem for run state, and no fallback to scraping exists.
- A run started on one machine is visible to a front door running on another.

#### FR-41: A run's timing survives the workstation that produced it

Completed-run timing is ingested into durable storage rather than left in a local journal.
**CAP-17.**

**Consequences (testable):**
- A run's timing is retrievable after its originating workstation is unavailable.
- Ingestion happens at run completion, not at page-generation time.
- Timing history is queryable across runs, not only for the most recent.

#### FR-42: The supervisor degrades honestly

When the supervisor is unreachable, the surface says so rather than implying staleness is
liveness. **CAP-17, CAP-10.**

**Consequences (testable):**
- An unreachable supervisor renders an explicit unavailable state, not an empty list and not stale
  data presented as current.
- Any displayed run state carries its age.
- The front door does not hang waiting on the supervisor — it degrades within its budget, per
  FR-26.

**Notes:** `[NOTE FOR PM]` this feature was added after the capability set was otherwise settled,
and it is the one place this chain grew rather than converged. It is worth a deliberate look during
the readiness gate: it is genuinely useful, and it is also the kind of scope that arrives late and
is not sized with the same rigor as the rest.

---

### 4.15 One plugin API, then Warden, then station processes

**Description.** Canopy Epics 18–30 mount chrome, portals, MCP, events, and DDL. They do not
extract replaceable layers. **CAP-18** is the missing story: one hook-spec plus plugin-registration
shape in `pyforge-core` so eight stations do not invent eight APIs. Warden is the first concrete
retrofit (PR-gate hook specs; current scanners become optional plugins; default Warden stays green
with no Checkmarx). Each station's package then extracts its process layer (build engine, runner,
store, exporter, deploy profile, LLM provider); today's backend is the default plugin.

**Functional Requirements:**

#### FR-43: Shared hook-spec and plugin registration

`pyforge-core` publishes one registration API and one documentation shape for hook
specifications. Station packages consume it; they do not ship a second plugin loader.
**CAP-18.**

**Consequences (testable):**
- A dummy plugin loads through the shared API.
- A conformance check **fails** if a station package introduces a parallel registration
  mechanism for the same class of extension.
- Named hook points are before / after / around (or an equivalent documented set). A plugin
  must not publish a second verdict for a process another owner specified.

#### FR-44: Warden owns PR-gate hooks; scanners are optional plugins

Warden owns the PR-gate hook specifications on the FR-43 contract. Existing scanners become
plugins. A missing named scanner (including Checkmarx) is not a failed Warden run.
**CAP-18.** Q8.

**Consequences (testable):**
- Default Warden / CI invocation is green with no named commercial scanner plugin installed.
- Enabling an optional scanner plugin can change findings; it cannot replace the Warden verdict
  with a second pass/fail published beside it.

#### FR-45: Each 03 station extracts one process hook spec

Each 03 station identifies a replaceable process layer, publishes a hook spec on the FR-43
contract, and registers today's backend as the default plugin. Atlas **audits** existing Kedro
hooks against the contract; it does not rebuild the pipeline or grow a pipeline PR-gate.
**CAP-18.**

**Consequences (testable):**
- Swapping the vendor/backend for that layer does not require forking the station process.
- Steward deploy-profile adapters (Harness, Splunk, StorageGRID, EPLX GHA, Tachyon, Jira) are
  plugins on this FR, not core stack.

**Notes:** Order is FR-43, then FR-44, then FR-45 on the next process change (Warden first).
Epics 18–30 must not violate CAP-18; they are not its implementation.

---

### 4.16 The query plane (CAP-19)

Stations stop inventing stores. One DuckDB engine federates live Postgres (read-only),
serves Kedro Parquet, and ranks vectors. Agents do not get the OLTP DSN. Rebuild of
Atlas RAG defaults, Scribe semantic recall, and Langflow/DB-GPT estate reads is
authorized. Realizes UJ-6.

#### FR-46: Live federation is read-only attach

DuckDB attaches a multi-schema Postgres as `READ_ONLY`. No `pgvector` is required on
that database. **CAP-19.**

**Consequences (testable):**
- A fixture with two schemas answers a federated `SELECT` through the plane.
- A write against the attach is refused.
- The test fails if the path goes through pandas SQL or a writable attach.

#### FR-47: Analytical scans hit the Parquet cache

Kedro writes compressed Parquet on a named catalog pipeline. Dashboards and
autonomous SQL read the cache, not OLTP. **CAP-19.**

**Consequences (testable):**
- After `kedro run` of the named pipeline, the cache file exists and a query
  against it does not open the OLTP writer role.
- The test fails if Airflow or an `01_raw` tree is the refresh mechanism.

#### FR-48: Vectors live on the plane

`REAL[]` (or equivalent) casts to `FLOAT[N]` and HNSW / `vss` ranking runs in
DuckDB SQL. Dimension is a parameter. Consumer `LOAD`s `vss`. **CAP-19.**

**Consequences (testable):**
- Nearest-neighbor returns the planted row without lexical overlap.
- The consumer path does not `INSTALL` on the network.
- The test fails if a second writable `.duckdb` file is the index home.

#### FR-49: Agents cannot use the OLTP DSN

DB-GPT Text-to-SQL and Langflow estate RAG are configured at the plane (cache,
declared views, or the HTTP/Arrow face). **CAP-19.**

**Consequences (testable):**
- Config/tests show the estate read DSN is the plane, not `langflow_schema` /
  enterprise OLTP.
- A mis-aimed OLTP DSN for Text-to-SQL fails the gate.

#### FR-50: Stations reimplement onto the plane

Scribe semantic recall uses `GraphStore.query_similar` backed by the plane (or a
driver that is the plane). Atlas RAG persist uses the plane writer. BSL remains
the dashboard contract. **CAP-19.** Rebuild of 28.2 / in-memory RAG is in scope.

**Consequences (testable):**
- FR-36 still holds after the Scribe path moves.
- Callers do not `isinstance` the driver.
- The test fails if semantic recall is aliased back to lexical or to a private
  Chroma / in-memory DuckDB.

---

## 5. Non-Goals (Explicit)

- **Not a rewrite of the host.** `src/platform/` stands. No rename, no relocation of `config/` or
  `platformapp/`.
- **Not a ninth station or a ninth project.** The roster stays at eight.
- **Not a re-decision of the monolith-versus-microservices topology.** That trail is closed
  elsewhere and reopening it is out of scope.
- **Not a replacement for any station CLI.** FR-13 dispatches; station binaries remain first-class.
- **Not atlas's own Wagtail Spec.** CAP-2 may end up serving one of its waiting consumers (OQ-5),
  but does not absorb, re-mint or supersede it.
- **Not CodeRed CMS.** Ruled out on maintenance evidence.
- **Not a general-purpose multi-tenancy model.** FR-16 is row isolation for boards, nothing more.
- **Not atlas's adoption of the secure-dashboard pattern.** Consumed here; adopting it in atlas's
  own board is atlas's story.
- **Not an external API contract.** The service faces are for estate callers; no third-party
  versioning promise.

## 6. MVP Scope

MVP here means "the smallest cut where the estate behaves as one system", not "the first
demonstrable slice". Two features are excluded from it for opposite reasons — one because it is
gated on external packaging, one because it is a migration that should not be rushed.

### 6.1 In Scope

- Shared chrome (FR-1..FR-3) — everything visual depends on it.
- Eight portals behind one session (FR-9, FR-10).
- The identity-carrying client (FR-14, FR-15) — before its consumers, or the first integration
  becomes a trusted header nobody removes.
- Service faces on a current specification (FR-11), with resumability (FR-12) as the risk item.
- One command grammar (FR-13).
- Queue/cache separation (FR-30) — cheap, and it prevents a whole class of production surprise.
- IdP-derived authorization and delivered secrets (FR-31, FR-32).

### 6.2 Out of Scope for MVP

- **Governed schema change (§4.9)** — gated on a feedstock, reopens shipped stories, and has no
  prior art. Deferring it does not weaken the MVP's demonstration; rushing it risks the estate's
  database.
- **Flags (§4.11 FR-33, FR-34)** — gated on four absent feedstocks plus a downgrade build.
  `[NOTE FOR PM]` this is the one deferral most likely to be regretted, because flags would
  de-risk every other rollout in the chain. If packaging lands early, pull it forward.
- **Lane 1 supersession (§4.2)** — the front door itself is MVP-adjacent, but retiring the console
  is a migration with a parity precondition. The build may land in MVP; **the removal may not**.
- **Semantic recall (FR-36)** — durability (FR-35) is the urgent half of CAP-14.
- **Personas (FR-38)** — depend on FR-13 and FR-11 both existing first.

## 7. Success Metrics

**These are stated as binary gates, not as targets, and that is deliberate.** No baseline
measurement exists for this estate — no current-state latency, adoption or incident numbers — so a
percentage target here would be invented, and an invented target propagates into an acceptance
criterion nobody can evaluate. Where a number appears below it is a threshold already fixed by an
external constraint, not a goal we chose.

**Primary**

- **SM-1 — One session spans the estate.** An operator traverses Lane 1 → a station portal → an
  analytical board with a single authentication and no origin change. Binary. Validates FR-4, FR-9,
  FR-16.
- **SM-2 — An agent survives the proxy.** A multi-minute operation completes across a simulated
  ingress disconnect and its result is retrieved. Binary. Validates FR-11, FR-12.
- **SM-3 — The application cannot alter its own schema.** `CREATE`/`ALTER`/`DROP` as the
  application role are refused by PostgreSQL. Binary, and verifiable by an auditor without reading
  application code. Validates FR-22.
- **SM-4 — The egress-blocked deploy succeeds.** A build and deploy with external egress blocked
  completes end to end, carrying only PostgreSQL, Redis and the platform images. Binary; already
  the estate's existing gate. Validates FR-21, FR-33, and the air-gap constraint generally.
- **SM-5 — Five tiers, eight 03 stations.** The completeness check reports all eight **03**
  stations with all five tiers present. Countable, with a known denominator: 8 × 5 = 40.
  01/02 work is outside the denominator. Validates FR-37, FR-38, FR-39.

**Secondary**

- **SM-6 — Each containment invariant fails without itself.** Each of the four invariants has a
  test demonstrated individually to fail when the invariant is removed. Count: 4 of 4. Validates
  FR-26..FR-29.
- **SM-7 — Chrome is not duplicated.** The duplication check finds zero portal-local copies of
  chrome. Count: 0. Validates FR-1.
- **SM-8 — CLI parity holds.** The generated matrix shows every station verb reachable both ways,
  and CI fails on divergence. Validates FR-13.
- **SM-9 — One plugin API.** A dummy plugin loads through `pyforge-core`; a station-local second
  registration API fails the check; default Warden is green with no named commercial scanner.
  Validates FR-43, FR-44, FR-45.

**Counter-metrics (do not optimize)**

- **SM-C1 — Do not optimize portal count.** Eight portals that render but hold station logic is a
  worse outcome than six that are properly thin. Counterbalances SM-1; enforced by FR-10.
- **SM-C2 — Do not optimize event throughput.** The backbone's value is durability, ordering and
  quarantine. A faster backbone that drops or double-applies has failed. Counterbalances the CAP-8
  work; enforced by FR-17, FR-18, FR-29.
- **SM-C3 — Do not optimize for the skill/persona count.** Eight shallow skills that no agent
  actually follows satisfies SM-5 and delivers nothing. Counterbalances SM-5; enforced by FR-37's
  "demonstrated for a station that has no skill today".
- **SM-C4 — Do not optimize migration speed.** FR-23's build gate will slow schema authoring. That
  cost is the feature. Counterbalances SM-3.

## 8. Cross-Cutting NFRs

- **Air-gap.** Every Python/pixi dependency resolves from conda-forge; the egress-blocked build is
  a gate, not a warning. Container images are governed separately by the platform Spec's
  internal-registry rule. Both boundaries bind; neither substitutes for the other.
- **Backing services.** Exactly PostgreSQL, Redis and Kubernetes. A component demanding a fourth
  has failed design review. DuckDB is a library / optional query face on the platform image,
  not a fourth Helm kind (CAP-19).
- **Statelessness.** Replicas are capacity; any pod is disposable. This rules out pod-local media
  (FR-8) and per-process caches.
- **Runtime floor.** Django `>=5.2.15,<6` and Python `3.12.*`. Zero headroom — conda-forge ships
  exactly one qualifying build, two **security** patch releases behind upstream. Audited
  2026-08-24: seven CVEs across 5.2.16 and 5.2.17, one rated high, and **every affected path is
  unreachable here**. A currency gap rather than a live exposure — but the pin should still move to
  `>=5.2.17,<6`, because scanners key on version strings rather than reachability and an SBOM
  declaring seven unremediated CVEs is a finding whatever the analysis says. The feedstock's `5.x`
  maintenance branch exists and this repo's maintainer has bumped it before, so this is a one-file
  PR, not chain scope.
- **Import boundary.** `src/platform/` consumes the factory's published conda packages and never
  imports factory source.
- **Ingress timing.** Any long-lived response keeps alive well under 30 seconds. The platform's
  router timeout is cluster-wide with no per-route override; a route annotation is
  defence-in-depth, never the mechanism.

## 9. Constraints and Guardrails

**Sequencing constraints** — facts about the work, not preferences. Each dictates ordering, and the
epic pass must honour rather than rediscover them.

1. **Packaging precedes platform in two features.** FR-21 gates §4.9; FR-33 gates FR-34. Both
   epics open with `conda-forge-expert` sessions.
2. **FR-1 precedes FR-4 and FR-9.** Chrome first, or portals grow their own.
3. **FR-14 precedes FR-9's integrations.** The client before its consumers.
4. **FR-6 precedes FR-7.** Inventory before removal, unconditionally.
5. **FR-13 and FR-11 precede FR-38.** A persona has nothing to act through otherwise.

6. **The inventory (FR-6) precedes the parity build, which precedes the removal (FR-7).** Three
   stories, in that order. The inventory is done; the removal carries the 100+ reference sweep and
   the spec correction, and must not start until the parity build proves the reproducible surfaces.
7. **Phase 5 is eight `bmad-correct-course` runs, not one** — one per station, recording each
   station's Canopy obligations, with Marshal's additionally retiring `spec-factory-console`. That
   skill, not the epic pass, also decides the ledger shape for reopening the two `done` stories
   FR-22 contradicts: a new superseding epic, or a reopened Epic 11.

**Change-management guardrail.** §4.2 removes something that works today. The guardrail is FR-6's
inventory as a hard precondition and FR-7's requirement that removal be real. A "temporarily keep
both" outcome is the failure mode to guard against — it is how a supersession becomes a permanent
second console.

**Audit guardrail.** FR-22 is deliberately enforced at the database rather than in application
code, because a control an auditor can verify without reading source is worth more than a stricter
control they cannot.

## 10. Integration and Dependencies

- **Identity provider** — OIDC, already live. FR-5, FR-31 and the CAP-6 assertion chain all depend
  on it. Group/claim mapping for CMS admin (FR-5) is **new work with no first-party guidance**.
- **The shipped chart** — FR-24 adds a Job beside the existing migration hook, on the same image.
  The existing chart contract is not rewritten.
- **The existing compliance portal** — becomes one of the eight (FR-9). URL scheme is bound:
  `/stations/<name>/` with `/compliance/` redirect (FR-9a). OQ-4 is answered.
- **Atlas's MCP server** — brought to the current specification by FR-11 rather than duplicated.
- **Atlas's waiting CMS consumer** — OQ-5 / `lane1-serves-dw-h3` **answered 2026-08-25: no.**
  Host Wagtail `/cms/` does not satisfy `LaSuiteClient` Docs REST. DW-H3 stays atlas.
- **Packaging (FR-21, FR-33)** — operator-owned conda-forge recipes (canopy AD-16; Stories 26.3
  and 27.1 stay blocked). Not in-chain CFE sessions for Canopy implementation.

## 11. Open Questions

**Still open:** none.

**Answered 2026-08-25:**

1. ~~**Can Lane 1 serve atlas's waiting consumer?** (`lane1-serves-dw-h3`)~~ — **no.** Atlas's
   shipped `LaSuiteClient` froze La Suite Docs REST (`POST /api/v1/documents/` etc.), which is
   *not* host Wagtail `/cms/`. Epic 20 (Lane 1 exists) is independent. This chain does not
   absorb `spec-wagtail-corporate-brain`. DW-H3 stays atlas attended bring-up.

**Answered 2026-08-24:**

-3. ~~**MCP runtime base (FastMCP vs official `mcp` SDK)**~~ — **hybrid, canopy AD-5.** Service
   faces on the host are the official `mcp` SDK (`>=2.0.0`) on the one ASGI process. Stopgap in
   `local-recipes` only: `fastmcp >=3.4.7,<4` + `mcp >=1.24,<2.0` until those faces land; lift the
   `mcp` ceiling in the FR-11 story. The pairing outage is contained, not reopened.
-4. ~~**One Liquibase tracking schema or one per application?**~~ — **one tracking schema**,
   canopy AD-9: `liquibaseSchemaName=liquibase`. Four PostgreSQL schemas in this instance
   (`public`, `langflow_schema`, `dbgpt_schema`, `liquibase`). A fifth schema is a review-blocking
   finding. Concurrent migrate of two applications shares that global changelog lock; that is
   the bound cost.

-2. ~~**MCP client revision**~~ — **accept `2025-03-26` through `2026-07-28`**, which `mcp` 2.0.0
   already serves dual-era with no configuration. The fleet is split (Copilot and Zed at
   `2025-11-25`, Gemini CLI at `2025-06-18`, Codex already at `2026-07-28`), so both ends are load
   bearing. Bound into FR-11, along with two invariants the research surfaced: echo the client's
   requested revision, and never branch on client name.
-1. ~~**MCP resumable-operation runtime**~~ — **no, and blocked upstream.** The Tasks extension is
   listed under the SDK's *Known gaps*; the only runtime in any language is a beta on an unreleased
   FastMCP 4, absent from conda-forge along with its own dependency. FR-12 ships a `start`/`get`
   pair over a durable store instead — the same lifecycle SEP-2663 standardizes, so adopting it
   later is a wire-layer swap. Worth a scheduled re-check rather than treating as closed.
0. ~~**Liquibase multi-schema regression**~~ — **fixed in 5.0.4**, corroborated by both the merged
   PR and the release notes. The question was framed too broadly: the defect only affected
   `runInTransaction="false"` changesets, never in-transaction ones. It surfaced a worse hazard in
   its place — an **open** issue where `preserveSchemaCase` causes DDL to land silently in
   `public` — now bound as FR-21a.

5. ~~**Portal URL scheme**~~ — **uniform `/stations/<name>/` for all eight**, with
   `compliance_face` moving from `/compliance/` behind a permanent redirect. One rule beats eight
   exceptions, and the registration seam enforces it (FR-2, FR-9, FR-9a). The cost is a migration
   of a shipped URL, which the redirect absorbs.
6. ~~**Django patch-level exposure**~~ — **audited 2026-08-24: a currency gap, not an exposure.**
   5.2.16 and 5.2.17 are both security releases carrying seven CVEs, one rated high — and every
   affected path is unreachable here. The premise underneath the question was also wrong: the
   feedstock's `5.x` maintenance branch **does** exist and this repo's maintainer has already
   bumped it, so moving the pin to `>=5.2.17,<6` is a one-file PR rather than the seventh packaging
   item it was sized as. Recommended, not required: scanners read version strings, not
   reachability.
7. ~~**Console parity classification**~~ — answered by the FR-6 inventory, and the question it
   raised in turn is **also** answered: live run state and journal-derived timing **stay on the
   front door**, which means building the supervisor that makes them deployable. That is
   **CAP-17 / §4.14**, new scope taken deliberately.

8. **Query plane face / catalog / Scribe cutover** — open on the SPEC as
   `query-plane-face`, `query-plane-catalog`, `query-plane-scribe-cutover`.
   Defaults: in-process first; named new Atlas pipeline; GraphStore driver on
   the plane. Epic 34 may proceed on those defaults.

## 12. Traceability

Every capability has at least one FR; every FR names a capability.

| CAP | FRs | CAP | FRs |
|---|---|---|---|
| CAP-1 | FR-1, FR-2, FR-3 | CAP-10 | FR-18, FR-26..FR-29, FR-42 |
| CAP-2 | FR-4..FR-8 | CAP-11 | FR-30 |
| CAP-3 | FR-2, FR-9, FR-9a, FR-9b, FR-10 | CAP-12 | FR-3, FR-5, FR-31, FR-32 |
| CAP-4 | FR-11, FR-12 | CAP-13 | FR-33, FR-34 |
| CAP-5 | FR-13 | CAP-14 | FR-35, FR-36 |
| CAP-6 | FR-10, FR-14, FR-15 | CAP-15 | FR-37, FR-39 |
| CAP-7 | FR-16 | CAP-16 | FR-38, FR-39 |
| CAP-8 | FR-17..FR-20, FR-29 | CAP-17 | FR-40, FR-41, FR-42 |
| CAP-9 | FR-21, FR-21a, FR-22..FR-25 | CAP-18 | FR-43, FR-44, FR-45 |
| CAP-19 | FR-46, FR-47, FR-48, FR-49, FR-50 | | |

## 13. Assumptions Index

- **§4.5 FR-13** — the eight station CLIs expose a surface stable enough to dispatch to without
  modification. Unverified per-station; a station that cannot be introspected needs a preparatory
  story.
- **§4.10 FR-26** — the circuit breaker's cross-replica state transitions are not atomic. Read from
  source, not documentation. Consequence: no FR may depend on an exact failure count.
- **§4.2** — Marshal's console views are re-creatable as CMS pages plus portal routes. Under test
  by the FR-6 inventory; a build-time-only view forces a scope conversation.
- **§2** — the agent is a first-class user, weighted equally with the three human roles. Derived
  from the capability set rather than from a stated requirement.

## 14. What Comes Next

Architecture spine and Canopy Epics **18–30** already exist. First Canopy dispatch remains
**S-18.1** (chrome). **CAP-18** is a later-day bind: steward **Epic 32** (shared contract in
`pyforge-core`, then steward deploy-profile plugins), **Warden Epic 9** (PR-gate retrofit),
then each station's process-hook story. Do not regenerate the whole steward sprint feed
(slug truncation). Packaging stays operator-owned (S-26.3, S-27.1). Scorecard remains a
sibling Dream — CAP-18 is **not** that board.

**2026-08-26 ready-to-implement:** SPEC `ready`. CAP-19 / Epic 34 is the live
residual. Do not re-dispatch 18–32. First dispatch **S-34.1**
(`specs/spec-34-1-read-only-live-attach.md`). `django-lasuite` is not a Canopy
FR. OQs have defaults; do not block 34.1 on them.
