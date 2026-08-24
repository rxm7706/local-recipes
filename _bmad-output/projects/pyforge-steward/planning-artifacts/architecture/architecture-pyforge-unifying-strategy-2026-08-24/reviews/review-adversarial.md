---
title: "Adversarial review — architecture spine: pyforge-unifying-strategy"
target: ../ARCHITECTURE-SPINE.md
parent: ../../../specs/spec-python-agent-platform/ARCHITECTURE-SPINE.md
reviewed: "2026-08-24"
reviewer: adversarial architecture pass
lens: adversarial
verdict: FAIL — the spine is not a closed substrate; two station-sized units can obey every adopted AD and still ship incompatible shared-data shapes, dual owners of one entity, and conflicting mutation paths
---

# Adversarial review — Canopy architecture spine (2026-08-24)

**Content class.** Architecture spine (docs / behavioral contract).

**Attack.** For each hole: construct two units one level down (a pair of station portals, a pair of service faces, or portal vs service of the same station) that follow every adopted AD in this spine and every inherited parent AD to the letter, then show the clash. Each pair is a missing or under-specified AD.

**Parent (cannot be weakened).** `specs/spec-python-agent-platform/ARCHITECTURE-SPINE.md` (AD-1..AD-17, original IDs, read-only). This review does not propose relaxing parent isolation, the `src/platform/` import ban, one-ASGI-process, three-schema *isolation*, Celery-only async, or secrets-at-boundary.

**Companions read (non-normative for this attack except where the spine itself defers to them).** `resilience-invariants.md`, `architecture-diagrams.md`, `spec-pyforge-unifying-strategy/SPEC.md`. Several companion diagrams still describe a `services/` FastAPI topology and `tasks/get` that this spine already forbids — those are consistency bugs, not licenses to violate the spine. The attack uses only what the spine *allows*.

**Verdict.** **FAIL.** Adopted ADs bind placement, prefixes, chrome, process count, DDL *mechanism*, Redis *kinds*, and “one assertion format” at slogan altitude. They do not bind: shared record shapes, single-writer rules, Redis *assignment* of Streams, assertion *claim set*, handle-row schema, changelog identity, or the conjunction of capability-handles with IdP re-read. Two teams can merge independently green stories and fail at first cross-station event, first portal→MCP call, and first Liquibase Job that includes two packages.

---

## Method notes

- “Obeys every AD” means the unit does not violate a stated rule. Using a deferred item as a story-local choice is allowed by this spine (Deferred table: CloudEvents extension names, supervisor ingest wire, Scribe dual-driver internals).
- Parent AD-5 isolation (`search_path`, ORM never crosses schemas) still binds; only the SQL *producer* is this spine’s AD-9. Extra schemas in the structural seed (`liquibase`, `run_state`, `mcp_handles`) are drawn but have no owner AD.
- Proposed closures are **new or tightened child ADs**. None weakens the parent.

---

## Incompatible pairs (constructed units)

### Pair 1 — `django-warden` portal vs `django-warden` MCP sibling: two owners of Finding, two stores, two writers

**Units.**

| Unit | What it builds |
|---|---|
| **Portal A** | `django-warden` / `django_warden_fabric` / `warden_fabric` (AD-4 rename of `compliance_face`). HTMX lists and forms persist `warden_fabric.Finding` in `public` via Django ORM. Registration via `AppConfig` (AD-1), mount `/stations/warden/` (AD-2), no chrome copy (AD-3). Calls MCP only through `django-pyforge`’s client for *actions that are “services”* (AD-7); list/detail stay on local models because AD-4 forbids moving existing models and the shipped portal already has them. |
| **Service B** | Sibling app `django_warden_mcp` / `warden_mcp` in the same distribution (AD-4: “one or more apps”). MCP on official `mcp` SDK, `POST /stations/warden/mcp` (AD-5). Long work is `start_audit` / `get_audit` over PostgreSQL `mcp_handles` (AD-6). Domain work delegated to `pyforge.warden` (legal: import ban is `src/platform/` only — parent AD-2). CLI path remains `pyforge warden …` → existing binary (AD-14), which writes the factory’s own store, not Django. |

**ADs both followed.** Child AD-1, AD-2, AD-3, AD-4, AD-5, AD-6, AD-7, AD-9 (portal DML in `public`; MCP DML in `mcp_handles`; ORM never crosses — inherited isolation); parent AD-2, AD-4, AD-5 isolation, AD-9 consume-not-fork.

**What still clashed.**

- **Shared-data shape.** Portal `Finding` is a Django model (status enum, FK to `auth.User`, `created_at`). MCP `get_audit` row is whatever the MCP story invented (`handle`, `tool`, `blob jsonb`, `ttl_at`). Factory CLI writes a third shape (warden’s existing on-disk/report artifacts). No AD names a canonical Finding/AuditResult schema or a mapping.
- **Two owners of one entity.** “An audit finding” is owned by `warden_fabric` (existing models must not move), by `mcp_handles` (AD-6 store), and by `pyforge-warden` (AD-14 must not reimplement the binary). Three sources of truth, all legal.
- **Conflicting mutation paths.** Operator marks a finding accepted in the portal → ORM `UPDATE` on `public`. Agent calls `start_audit` → insert/update `mcp_handles` then factory logic. Operator runs `pyforge warden …` → factory store, no Django row. Supervisor (AD-12) is *not* this entity’s publisher, so the front door cannot reconcile them.

**Hole to close.** New AD: **one canonical write path per station noun.** Portal DML is projection-only (or is the sole writer for that noun — pick one). MCP `start`/`get` rows are handles to work, not a second Finding table. CLI mutations must publish the same projection the portal reads (event or supervisor), or the portal must not persist domain entities. Bind this *before* CAP-9 freezes table names into Liquibase.

---

### Pair 2 — Mason producer vs Atlas consumer: CloudEvents 1.0 on “one stream family” with incompatible envelopes and Redis homes

**Units.**

| Unit | What it builds |
|---|---|
| **Mason service face** | `XADD` CloudEvents 1.0 (AD-8). Stream key `events:mason` on **redis-broker** (AD-10: broker does not evict; Celery already lives here; Streams are durable work-adjacent). Loop-depth extension attribute `loopDepth` (integer), ceiling 8. Poison → stream `events:mason:dlq`. Consumer group `mason`. Event `type`: `recipe.audit.failed` (convention example). `data` is Mason’s pydantic dump (`recipe_name`, `sha`, `exit`). |
| **Atlas service face** | Same AD-8 rules. Stream key `pyforge:events` (RFC-4-shaped, but the spine deferred field names and did not adopt RFC-4 identifiers). Lives on **redis-cache** because AD-10 only assigns Celery/Channels → broker and Django/Wagtail → cache; Streams are unassigned, and cache is “the other Redis.” Loop-depth header `X-PyForge-Loop-Depth` (RFC-4 string in companion; spine says only “extension attribute”). Ceiling 5. DLQ `pyforge:events:dlq`. Consumer group `atlas`. Expects `data.package` + `data.reason`. |

**ADs both followed.** Child AD-8, AD-10; parent AD-1 (still only Redis, two Deployments); inherited “two Redis still count as Redis.” Deferred table explicitly leaves “exact CloudEvents extension attribute names” to the first producer story.

**What still clashed.**

- **Shared-data shape.** Envelope class is “CloudEvents 1.0” only. Extension names, `type` vocabulary beyond one example, and `data` schemas are story-local. Atlas never sees Mason’s events (wrong key, wrong Redis, wrong attribute, wrong payload).
- **Two owners of the backbone.** “The” stream family is unspecified (per-station streams vs one estate stream). Each service face owns a family that the other does not read.
- **Conflicting mutation / consumption paths.** Mason mutates broker streams; Atlas mutates cache streams. Cache eviction (AD-10’s purpose) can drop Atlas’s “durable” events while Mason’s survive — both still satisfy AD-8’s DLQ/ceiling tests *inside their own family*.

**Hole to close.** Tighten AD-8 + AD-10 together: **Streams are a named keyspace on redis-broker only** (never cache). **One estate stream family** (name, maxlen policy, DLQ name). **One loop-depth extension name and ceiling.** **`type` registry** (or “payload schema id in `dataschema`”) so `data` is not a per-station private struct. Do not leave these to the first producer.

---

### Pair 3 — `django-pyforge` portal client vs `pyforge.core` CLI client: “one assertion format” with two claim dialects

**Units.**

| Unit | What it builds |
|---|---|
| **Portal client (chrome package)** | AD-7: portals call services only through `django-pyforge`’s client. Mints a short-lived **JWT** (asymmetric), `aud` = `https://{host}/stations/{name}/mcp`, subject claim `sub` = OIDC `sub`, roles from session. TTL 60s. Key: platform K8s secret mounted as env (parent AD-12). |
| **CLI client (`pyforge.core`)** | AD-7: CLI/agent callers use `pyforge.core`’s client. Mints **HMAC-SHA256** compact token (companion RFC-3 is not an AD here), `aud` = `mcp://{station}`, claims `idp_subject`, `roles`, `delegated_by: "pyforge-host"`. TTL 5m. Key: operator env `PYFORGE_INTERNAL_HS256` on the laptop (CLI is not the pod). |

**ADs both followed.** Child AD-7 (“same audience-bound signed short-lived assertion”); parent AD-2 (no `pyforge.*` under `src/platform/` — chrome client lives in `django-pyforge`); parent AD-12 (pod secrets via env/mounts). AD-7 never names JOSE vs HMAC, claim names, audience URI, TTL, or key distribution to out-of-cluster CLI.

**What still clashed.**

- **Shared-data shape.** The assertion *is* the shared identity document. Two byte-incompatible tokens. Warden MCP verifies JWT+`sub`; Herald MCP verifies HMAC+`idp_subject`. Each is independently “audience-bound” and “signed.”
- **Two owners of identity-at-the-service.** Chrome team owns portal minting; core team owns CLI minting. “Same format” is untestable (no golden vector, no shared library requirement). AD-7 forbids raw HTTP and trusted headers — both teams still comply.
- **Conflicting mutation paths.** A portal-originated MCP call and a persona/CLI-originated MCP call to the same `start_*` carry different identity documents. Authorization (AD-15: re-read roles “from the token on the request”) keys off different claim names; revocation (SPEC CAP-12) is next-request on IdP for portals and next-mint on CLI keys.

**Hole to close.** Tighten AD-7: **one library, one algorithm, one claim set, one audience URI pattern, one TTL bound, one test vector** that both clients must emit. Name how the CLI obtains the minting key without becoming a fourth backing service and without weakening parent AD-12. Companion RFC-3 is not inherited until it is an AD.

---

### Pair 4 — CAP-17 supervisor vs CAP-4 handle store: two owners of “in-flight work,” two mutation paths to completed

**Units.**

| Unit | What it builds |
|---|---|
| **Supervisor (host Django app)** | AD-12: only publisher of live run state and completed-run timing; PostgreSQL `run_state`; front door queries through the host; no filesystem fallback. Ingest at run completion (loop-side hook deferred — so this story defines a row: `run_id`, `station`, `started_at`, `heartbeat_at`, `status`). |
| **Warden (or Mason) MCP** | AD-6: `start_*` returns opaque TTL’d handle; `get_*` reads a PostgreSQL row in `mcp_handles` (structural seed); any replica. Handle treated as a capability. Does **not** write `run_state` because AD-12 says the supervisor is the *only* publisher — MCP must not publish run state. Does **not** skip PG because AD-6 requires a row. |

**ADs both followed.** Child AD-6, AD-12, AD-14 (persona may start work via CLI *or* MCP); structural seed draws both schemas; Deferred: “supervisor ingest wire from bmad-loop” and MCP Tasks swap.

**What still clashed.**

- **Shared-data shape.** “A run” vs “a task handle” are unspecified relative to each other. Front door shows supervisor rows. Agent polls `get_*`. Same human work item has two ids, two status enums (`running|done` vs `pending|completed|failed`), two clocks (heartbeat vs TTL).
- **Two owners of one entity.** In-flight execution is owned by the supervisor *and* by every station’s handle table. AD-12’s “only publisher” is vacuously true if MCP claims handles are not “run state.”
- **Conflicting mutation paths.** CLI/persona → binary → (deferred) loop hook → supervisor `INSERT`. MCP `start_*` → `mcp_handles` `INSERT`, completion on `get_*` / worker, **never** supervisor. Unreachable-supervisor UX (AD-12) vs expired-handle UX (AD-6) for the same disconnect. Capability handle (AD-6: presenter may read) vs IdP re-read on every request (AD-15) vs revocation (CAP-12): Warden `get_*` authorizes on handle possession; Atlas `get_*` requires a fresh assertion and re-reads roles. Both conjunctions are legal.

**Hole to close.** New AD: **handle rows are not a second run ledger** — either (a) `start_*` *is* a supervisor publish (MCP writes through the supervisor API, one schema), or (b) handles are capabilities *to a supervisor run_id* with a single status machine. Bind handle TTL vs run heartbeat. Bind AD-6 capability vs AD-15 token re-read (possession-only `get` is a durable grant by another name). Do not defer the ingest wire if CAP-4 and CAP-17 can both mark work complete.

---

### Pair 5 — Two station Liquibase packs + two MCP apps: colliding changelog identity and two `mcp_handles` table shapes in one schema

**Units.**

| Unit | What it builds |
|---|---|
| **django-warden CAP-9 pack** | Django authors migrations (convention); `sqlmigrate` CI gate (AD-9). Changeset ids `001-initial`, `002-finding`. Tables in `public` (`warden_fabric_*`). Also authors `mcp_handles.task` (`id uuid`, `payload jsonb`) for AD-6 because the seed drew `mcp_handles` and no owner is named. |
| **django-atlas CAP-9 pack** | Same AD-9. Changeset ids `001-initial`, `002-board-row`. Tables in `public`. Authors `mcp_handles.handle` (`handle text pk`, `result bytea`, `expires timestamptz`) for *its* AD-6 store. |

**ADs both followed.** Child AD-4 (models stay in their apps; new MCP concern is a sibling app, not a moved model), AD-6, AD-9 (one tracking schema `liquibase`, one sequential Helm Job, lowercase schemas, app role DML-only, Job `currentSchema` set, tests still `migrate`); parent AD-5 isolation (neither ORM crosses into `langflow_schema` / `dbgpt_schema`).

**What still clashed.**

- **Shared-data shape.** `mcp_handles` is one schema in the seed and two incompatible table designs. `get_*` “reads a PostgreSQL row” is satisfied by both. Liquibase changeset id `001-initial` collides in the **one** `DATABASECHANGELOG` (AD-9: one tracking schema, one sequential migrator). Job `currentSchema` is a single setting; multi-schema changesets rely on per-changeset schema names the spine does not require.
- **Two owners of one entity.** `mcp_handles` (and the master changelog include order on the platform image) have no owning package. Each station reasonably owns “its” handle store. `public` is shared Django; app labels prefix tables (good) but **do not** prefix Liquibase ids.
- **Conflicting mutation paths.** Production DDL: whichever package’s changelog the Job runs first wins the schema; the second fails or silently targets `public` (the failure mode AD-9 cites from Liquibase 7624 — `preserveSchemaCase` off helps names, not ownership). Test path: Django `migrate` applies both apps’ migrations in `INSTALLED_APPS` order, which need not match Liquibase order — CI `sqlmigrate` gate can be green per-package and still produce a Job that cannot apply.

**Hole to close.** Tighten AD-9: **changeset id namespace** (`<station>:<app>:<seq>` or includeAll with unique file paths and unique ids). **One owner of `mcp_handles` DDL** (host `platformapp` or `django-pyforge`, not per-station). **Handle table schema** as an AD (columns, TTL, capability entropy). **Master changelog composition** on the platform image. **`currentSchema` vs per-changeset schema** for `public` + `run_state` + `mcp_handles` + engine schemas in one Job. Extra schemas beyond parent’s three must be named as an additive isolation AD (search_path entries, ORM still cannot cross), not only a mermaid node.

---

## Further holes (same attack class; not the return set)

These also admit AD-compliant incompatible pairs; they are recorded so they are not lost.

### F-1 — MCP mount seam: Django `urls.py` include vs ASGI dispatcher branch

**Units.** Warden registers `path("mcp", …)` inside the portal URLconf discovered by AD-1. Atlas mounts the MCP Starlette app in the host ASGI wrapper next to parent AD-4’s `/langflow/` and `/api/dbgpt/` forwards, claiming AD-5 “mounted on the host ASGI app.”

**ADs followed.** AD-1 (Warden: host still has no station path list; Atlas: MCP is not a “portal” so AD-1’s AppConfig protocol need not list it — AD-1 never says MCP is a registrable). AD-5 both. Parent AD-4 dispatch order names only Django default + three forwards; `/stations/*/mcp` is unnamed.

**Clash.** Session middleware, CSRF, OIDC, and assertion checks apply on one path and not the other. Adding Atlas’s mount is a host ASGI edit (AD-1’s spirit: host does not list portals; letter: MCP is not a portal).

**Close.** AD-1 protocol **must** include the MCP mount token. Parent AD-4 dispatch table **gains** `/stations/<name>/mcp` without becoming a hardcoded station list (pattern match, not roster).

### F-2 — OpenFeature FILE: one JSON tree, two files

**Units.** In-cluster Django+MCP evaluate `/etc/pyforge/flags.json` (ConfigMap; “local disk”; no sidecar — AD-11). CLI on the operator workstation evaluates `~/.config/pyforge/flags.json` (also local disk, also in-process FILE provider, also no egress).

**ADs followed.** AD-11, AD-16 (CLI is local-first). Parent AD-6 (pods disposable — ConfigMap is not pod-local *state*). CAP-13 success (“one flag change alters all three surfaces”) is a SPEC criterion, not an AD.

**Clash.** Same flag key, different trees. Stories that import OpenFeature still block on feedstocks (AD-16) while this split ships.

**Close.** AD-11: **one feed, one evaluation context schema, how CLI receives the same bytes as the pod** (without a flagd daemon and without a fourth infra kind).

### F-3 — SPEC CAP-12 success vs parent AD-12 (surfaced, not decided)

**Units.** Warden: long-lived K8s Secret → env (parent AD-12; this spine’s inherited note: “manager sits outside the app”). Herald: CSI / external manager so “no long-lived secret value appears in any pod specification” (SPEC CAP-12 success). Spine treats this like AD-5 DDL (conflict surfaced) but **did not mint a child AD**.

**Clash.** Two secret-delivery faces. Herald’s reading may imply a Vault-class app dependency (parent AD-1 forbids Vault-as-app-dep). Warden’s reading fails SPEC CAP-12 success.

**Close.** Child AD that **restates parent AD-12 as the in-process contract** and maps CAP-12’s manager to an out-of-pod provisioner whose outputs still enter as env/secret mounts — or explicitly reopen parent AD-12 (not allowed here). Do not leave SPEC success and parent AD in unresolved conflict.

### F-4 — RFC-1 dual HTTP pools vs one ASGI process (companion bound to CAP-11, absent from AD-10)

**Units.** Doctor: gunicorn sync workers for HTMX. Herald: a second in-container process bound to loopback for streaming MCP (not a *public* port — parent AD-4 forbids extra public ports).

**ADs followed.** Parent AD-4 letter (public edge). Child AD-10 only splits Redis. RFC-1 lives in the companion, CAP-11 map row does not mention pools.

**Clash.** One station is one process; the other is two. Load-shedding and keep-alive (AD-6’s 30s rule) differ.

**Close.** AD on **in-process pool split only** (or named worker Deployment that is still not a public edge), so RFC-1 cannot mint a second server.

### F-5 — Redis keyspace on redis-broker: Celery + Channels + Streams, no prefix AD

**Units.** Mason Streams `celery` (human-named “task events”). Atlas Channels default prefix. Celery default keys.

**ADs followed.** AD-8, AD-10.

**Clash.** Key collision mutates the wrong consumer (Celery eats a CloudEvent; Stream group sees a task payload).

**Close.** AD: **mandatory prefixes** (`{celery,asgi,ce}` or equivalent) on redis-broker.

### F-6 — Scribe portal vs Scribe MCP (deferred dual-driver)

**Units.** Portal in local-first (parent AD-16) uses the file driver behind `GraphStore`. MCP in cluster uses PostgreSQL/pgvector. Same port, different recall (`recall.py` token overlap vs semantic — SPEC CAP-14).

**ADs followed.** AD-14 five tiers; parent AD-1 (pgvector in the instance); Deferred: dual-driver internals.

**Clash.** Persona via CLI vs persona via MCP (AD-14 both required) return different graph shapes/ids for the same recall. Local file vs PG is two owners of the graph entity.

**Close.** AD: **identity of a graph node is driver-stable**; CLI and MCP must not diverge on which driver they use in a given environment; projection of semantic vs lexical recall is named.

### F-7 — Wagtail Lane 1 vs Doctor portal: two owners of “fleet picture”

**Units.** Editors publish a Wagtail page with a JSON block of fleet stats (AD-13, CAP-2 only front door). Doctor portal live-queries supervisor/PG at `/stations/doctor/` (AD-2, AD-12).

**ADs followed.** AD-13, AD-2, AD-12, AD-1.

**Clash.** Same operator-facing entity, CMS snapshot vs live service, no AD saying Lane 1 may embed live partials vs must link to Lane 2.

**Close.** AD: **live operational entities are not CMS fields**; Lane 1 embeds via chrome/HTMX from the owning station or supervisor, or is explicitly a dated snapshot.

### F-8 — Architecture-diagram companion vs this spine (self-hostility)

`architecture-diagrams.md` still draws `services/` FastAPI + MCP, portal → `pyforge.core.client`, and `tasks/get` Task handles. The spine’s AD-5, AD-7 (two clients), and AD-6 (`start`/`get` tools, not Tasks) contradict it.

Two teams can follow the **diagram** or the **spine** and both believe they have architecture cover. That is an incompatible-pair generator *outside* AD text.

**Close.** Diagrams must match ADs in the same change, or the spine must mark diagrams non-authoritative (they already are Spec Law rule 2 — then delete residual `services/` from the residual subgraph so it cannot be followed).

### F-9 — Parent AD-4 dispatch vs eight MCP apps vs “never branch on client name” (AD-5)

AD-5: echo requested revision; never branch on client name. Two MCP apps can still branch on **protocol revision** differently (subset of tools advertised per revision). Warden’s `2025-03-26` initialize omits `start`/`get`; Atlas’s `2026-07-28` requires them. Both accept the revision range.

**Close.** AD: **tool surface is revision-stable** for the CAP-4 pair (or a published per-revision matrix).

### F-10 — `fail_max` coarse PyBreaker (AD-15) vs per-station outbound wrappers

Each station implements “~40 lines” asyncio wrapper over PyBreaker. Warden trips on timeout; Mason trips on HTTP 5xx only. Both have a test that fails without *a* wrapper (AD-15). Shared HTTP to IdP or MCP from chrome vs from a station uses different breakers → different degradation.

**Close.** AD: **one wrapper in `django-pyforge` / `pyforge.core`**, stations may not ship a second; trip conditions named.

### F-11 — Station token convention vs MCP tool names

Convention table: token `warden` in CLI, URL, distribution, skill, persona. No AD that MCP tools are `pyforge_<station>_<noun>_<verb>` matching CAP-5 grammar. Warden exposes `start_audit`; CLI is `pyforge warden finding list`. Persona (AD-14) must use both CAP-5 and CAP-4 and cannot map them.

**Close.** AD: **tool names ↔ CLI grammar bijection** (the parity matrix already required for CAP-5 binaries).

---

## Parent-spine interactions (must not weaken)

| Parent AD | How a child “fix” could accidentally weaken it | Allowed closure |
|---|---|---|
| AD-1 (PG+Redis+K8s only) | Putting Streams on a third Redis Deployment; MinIO for Mason BS-8; Vault sidecar for CAP-12 | Streams on existing broker; object store decision stays out unless parent is formally extended |
| AD-2 (no `pyforge.*` in `src/platform/`) | Moving the portal client into `config/` to “unify” assertions | Keep clients in `django-pyforge` and `pyforge.core`; unify *format* via a third tiny package both depend on, imported only outside `src/platform/` |
| AD-4 (one ASGI, fixed dispatch) | Second public MCP port to “split pools” | In-process mount; extend the dispatch *pattern*, not the process count |
| AD-5 (three schemas, isolation) | Collapsing `langflow_schema` into `public` for Liquibase simplicity | Additive named schemas + search_path; ORM still never crosses |
| AD-6 (stateless pods) | Flags or media or handles on emptyDir | Flags as ConfigMap; handles in PG; media object storage (already AD-13) |
| AD-7 (Celery only async) | RQ / django-tasks DB backend for Wagtail or MCP | Forbidden; already child AD-10 |
| AD-12 (secrets env/mounts) | App that pulls from Vault at runtime | Manager outside; in-app still env/mount |

The child spine already does the right *shape* of conflict handling for DDL (parent AD-5 mechanism vs child AD-9). It must repeat that pattern for: Streams Redis assignment, assertion bytes, handle vs run_state, changelog identity, CAP-12 vs parent AD-12, and MCP dispatch.

---

## Proposed AD backlog (closures)

1. **Canonical writer per station noun** (Pair 1) — portal projection vs factory/MCP write.
2. **Streams on redis-broker; one family; named extensions; payload schema id** (Pair 2) — fold RFC-4 identifiers or explicitly reject them.
3. **Assertion profile** (Pair 3) — algorithm, claims, aud, TTL, shared test vector, CLI key distribution.
4. **Single in-flight ledger** (Pair 4) — supervisor ∪ handles; capability vs IdP re-read.
5. **Changelog identity + owner of `mcp_handles` / `run_state` DDL + handle row schema** (Pair 5).
6. **MCP is part of AppConfig registration; ASGI dispatch pattern** (F-1).
7. **Flag byte identity across Django/MCP/CLI** (F-2).
8. **CAP-12 restated onto parent AD-12** (F-3).
9. **In-process only RFC-1 pools** (F-4); **broker key prefixes** (F-5).
10. **Diagrams synchronized or struck** (F-8); **tool↔CLI bijection** (F-11); **one breaker wrapper** (F-10).

---

## Adversarial lens findings (canonical fields)

| location | trigger_condition | guard_snippet | potential_consequence |
|---|---|---|---|
| AD-4 + AD-6 + AD-14 + inherited isolation | Existing portal models, MCP handle rows, and station binaries may all persist the same noun | One-writer AD; portal tables are projections | Split-brain findings; CAP-9 freezes the split |
| AD-8 + AD-10 + Deferred extension names | Streams unassigned to a Redis Deployment; envelope fields story-local | Broker-only stream family; named loop-depth; `dataschema` | Cross-station events never meet; cache evicts “durable” events |
| AD-7 | “Same assertion format” with no bytes, claims, aud, or TTL | One profile + golden vector both clients emit | Portal and CLI cannot call the same MCP |
| AD-6 + AD-12 + AD-15 | `mcp_handles` and `run_state` both exist; capability vs token re-read unconjuncted | One ledger; named authz for `get_*` | Two “running” UIs; revoked users still poll handles |
| AD-9 + structural seed schemas | One DATABASECHANGELOG; unowned `mcp_handles`; colliding changeset ids | Namespaced ids; single DDL owner for new schemas | First multi-station Job fails or DDLs into `public` |
| AD-1 + AD-5 + parent AD-4 | MCP mount not in registration protocol or dispatch table | AppConfig mount token + ASGI pattern | Host grows a station roster; auth middleware diverges |
| AD-11 | FILE provider + “one JSON tree” without feed identity for CLI vs pod | One distributed blob / evaluation context | Flags disagree across CAP-13 surfaces |
| Inherited AD-12 vs SPEC CAP-12 (Capability map) | Conflict surfaced in prose, no child AD | Restate manager-outside + env/mount in-app | Illegal Vault-in-app or CAP-12 success untestable |
| AD-10 vs RFC-1 (companion) | HTTP pool split not in spine; extra process tempting | In-process pools only | Second server process / port |
| AD-8 + AD-10 keyspace | No Redis key prefixes among Celery, Channels, Streams | Mandatory prefixes | Cross-mutation of broker keys |
| Deferred Scribe dual-driver + AD-14 | Two drivers, two recall modes, both “the” graph | Stable node ids; env-pinned driver | Persona CLI ≠ persona MCP |
| AD-13 + AD-12 + CAP-2 | CMS page vs live portal for the same operational entity | Live data not a Wagtail field | Stale Lane 1 vs live Lane 2 |
| companions/architecture-diagrams.md vs AD-5/6/7 | Diagrams still show `services/`, core client for portals, Tasks `get` | Sync or strike residual boxes | Teams implement the diagram, fail the spine |
| AD-5 revision echo | Tool surface may differ by echoed revision | Revision-stable CAP-4 tools | Dual-era clients cannot share `start`/`get` |
| AD-15 PyBreaker | Per-station ~40-line wrappers | One shared wrapper | Uneven containment, tests pass locally |
| Consistency: station token vs MCP tools | No bijection with CAP-5 grammar | Tool names = `station noun verb` | Five-tier station is not operable as one |

---

## What this review is not

- Not a request to weaken parent AD-5 isolation or to keep Django `migrate` as production DDL authority.
- Not a claim that Liquibase, MCP-on-ASGI, or two Redis Deployments are the wrong shape — they are under-specified, not wrong.
- Not an implementation plan. Closures belong in the spine as numbered ADs before epics/stories split across teams.
