---
marp: true
paginate: true
size: 16:9
title: PyForge Unifying Strategy — eight stations, one canopy
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:26px; }
  h1 { letter-spacing:-0.03em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.02em; color:#201e1d; }
  strong { color:#c22a10; }
  a { color:#c22a10; }
  code { background:#eae9e9; color:#c22a10; padding:0 .3em; }
  section.lead { background:#ec3013; color:#f3f2f2; }
  section.lead h1, section.lead h2, section.lead h3, section.lead strong, section.lead code { color:#f3f2f2; }
  section.lead code { background:rgba(255,255,255,.15); }
  section.part { background:#201e1d; color:#f3f2f2; }
  section.part h1, section.part h2, section.part strong { color:#f3f2f2; }
  hr { border:none; border-top:3px solid #201e1d; margin:.35em 0; }
  table { font-size:.68em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
  ul { font-size:.9em; }
---

<!-- _class: lead -->

PYFORGE ESTATE DREAM · STEWARD CHAIN · `spec-pyforge-unifying-strategy` · 2026-08-23 → evergreen

# Eight stations. One canopy.

The PyForge Unifying Strategy — **The Canopy & 8-Station Hub-and-Spoke Enterprise Architecture**. How eight excellent command-line tools became one estate: one chrome, one session, one grammar, one event backbone, one query plane — with schema change auditable, identity revocable, and failure contained.

<!-- Everything in this deck is dated and shipped, not projected. -->

---

## The story, in six acts

- **ACT I — Eight terminals.** Excellent stations, no estate; a governance mandate riding on it.
- **ACT II — One canopy.** Hub-and-spoke on a host the audit found already built.
- **ACT III — The mounting.** Chrome, portals, identity, service faces, grammar, skills, personas.
- **ACT IV — The mandate.** Auditable DDL, contained failure, revocable identity, offline flags.
- **ACT V — The proof.** Four dated days; a live cluster; a query plane minted and shipped in one.
- **ACT VI — Evergreen.** Held lines, honest leftover, and the on-ramp.

---

<!-- _class: part -->

## ACT I

# Eight terminals

Every station shipped as a genuinely good command-line tool — and stopped there.

---

## The roster — eight excellent CLIs

| Station | What it does |
| --- | --- |
| **Warden** | multi-axis dependency compliance — the sole PR-gate verdict |
| **Atlas** | package-graph intelligence · the estate's one Kedro home |
| **Mason** | conda-forge recipe factory — skill: `conda-forge-expert` |
| **Marshal** | autonomous-loop cockpit · run verbs · escalations |
| **Doctor** | workspace health diagnostics — findings stay advisory |
| **Herald** | decks, proclamations, the presentation stage |
| **Scribe** | team memory · knowledge graph behind a store port |
| **Steward** | platform custody & deployment — **owns this chain** |

Eight spokes — the Canopy is **not** a ninth station.

---

## The operator's day, before

- **Eight terminals, eight mental models** — every station its own verbs and output shape.
- **No shared identity** — nothing to sign into across tools.
- **No shared vocabulary** — a finding, an alert and a failed run cannot be related.
- **No signals** — one station cannot tell another that something happened. The human is the message bus.

**1/8** stations had a web portal (warden's, at `/compliance/`) · **1/8** had a service face (atlas's MCP server). The pattern worked and was simply never repeated.

---

## The mandate riding on it

The deployment target is **air-gapped and regulated**:

- **Auditable** — schema change flows through one authority, enforced by **database privilege**, not convention.
- **Revocable** — identity derives from the IdP; a revoked role is gone **on the next request**; secrets arrive by reference.
- **Contained** — a failing dependency degrades its caller; a poisoned event quarantines; a restart reconciles.

Five RFCs + eight blind-spot directives carry this — and the **egress-blocked build is a failing CI check**, not a warning.

---

<!-- _class: part -->

## ACT II

# One canopy

Hub and spoke — one host process carrying chrome, identity, portals and service faces. And the audit's twist: **the host was already built**.

---

## The hub-and-spoke topology

**The Canopy** — `src/platform/`, one ASGI process: `django-pyforge` chrome · allauth OIDC · Wagtail `/` · 8 portals · 8 MCP faces · `pyforge` dispatch · CloudEvents backbone. **It never imports `pyforge.*`** — stations arrive as packages, and their binaries stay first-class.

Eight spokes: Warden · Atlas · Mason · Marshal · Doctor · Herald · Scribe · Steward.

Underneath, **exactly three backing kinds**: PostgreSQL 17 · Redis 7 (broker `noeviction` + cache `allkeys-lru`) · Kubernetes/OpenShift (`restricted-v2`). A component demanding a fourth has failed its design review. DuckDB is a **library / query face**, not a fourth kind.

A **modular monolith** — not nine `:800x` processes; heavy work is Celery.

---

## The audit's twist: the host already existed

Found shipped on 2026-08-24: `src/platform/` — a live Django host with an ASGI seam, `django-allauth` OIDC, Langflow + DB-GPT mounted on isolated schemas, warden's portal, Celery + Redis, the pixi env, the 15-factor baseline, a Helm chart with an OCP overlay.

- **Scope is the residual, not the estate.** The chain binds `spec-python-agent-platform` CAP-1..6 as **shipped prior art** and mints nothing that duplicates it.
- Ten operator rulings the same day — owner **herald → steward**; the Canopy is not a ninth station; naming follows reality.
- `convergence.md` decides which side of the line any surface falls.

---

## Three lanes, one session — two agent doors

| Lane | Surface | Contract |
| --- | --- | --- |
| **Lane 1** | Wagtail CMS at `/` | pages published with no deploy; admin behind the IdP; supersedes the static console (CAP-2) |
| **Lane 2** | `/stations/<name>/` ×8 | HTMX · zero domain models · chrome from `django-pyforge` (CAP-1+3) |
| **Lane 3** | Vizro over BSL over the plane | per-tenant row isolation at the identity boundary (CAP-7) |
| **Agents** | `POST /stations/<name>/mcp` + `pyforge <station> <noun> <verb>` | dual-era MCP; CI-enforced CLI parity (CAP-4+5) |

One OIDC session over all of it; heavy work on Celery over `redis-broker` — the cache can never evict a task (CAP-11). Lane 2 is **HTMX, not DRF**.

---

<!-- _class: part -->

## ACT III

# The mounting

One chrome, one URL scheme, one identity path, one service-face design, one grammar — and a skill and persona for the agents.

---

## One chrome, eight portals · CAP-1 + CAP-3

- **`django-pyforge`** — app switcher, OIDC-aware base layout, Modernist theme, zero CDNs. Portals render identical chrome from one package — **a test fails if one ships its own copy**.
- **Registration, not configuration** — switcher entries derive from each portal's `AppConfig` seam: owner station, backup, `work_class`, promotion date. The Guildhall refuses to tile 01/02 work.
- **`/stations/<name>/` — one rule beats eight exceptions.** Warden moved off `/compliance/` behind a **permanent** redirect. Adding a portal changes no host code outside its registration.
- **Reusable apps by convention** — `django-<station>` / `django_<station>_<app>` / compound label; a model **never** moves between apps.

---

## One client, carrying identity · CAP-6

**No portal ever constructs a raw request; no service ever trusts a forwarded header.**

1. Portal calls through the shared `pyforge.core` client — the only path.
2. The client mints a signed **RS256** assertion: `sub`=`idp_subject` · roles · `aud=mcp:<station>` · `delegated_by=pyforge-host` · `exp ≤ 5 min`. (HMAC rejected — a shared secret is not an identity.)
3. The service verifies signature + audience **independently** — provably which end user a call served.
4. Celery tasks capture `idp_subject` at invocation and mint scoped execution tokens (BS-3).

---

## Every station has a service face · CAP-4

Eight MCP faces on the **host ASGI** — `POST /stations/<name>/mcp`, official `mcp` 2.0.0 SDK. `GET` answers 405; the `/mcp/sse` era is closed.

**Era discipline:** accept `2025-03-26` → `2026-07-28` (the fleet is split; either end alone rejects real traffic) · **echo the client's revision, never assert your own newest** (a client aborts on an unknown revision *even when it is newer*) · never branch on a client's name.

**Disconnect survival:** a **`start`/`get` tool pair over a durable store** — SEP-2663's own lifecycle without waiting for an SDK runtime that doesn't exist. The handle is a capability — opaque, high-entropy, TTL'd. **Never:** progress notifications, sticky sessions, stream replay. Keep-alives well under 30 s.

**The test that matters:** a multi-minute operation across a simulated disconnect — result retrieved **from a different replica**.

---

## One grammar — and the agents learn it too · CAP-5 + 15 + 16

- **The grammar** — `pyforge <station> <noun> <verb>` dispatches to the eight CLIs without reimplementing them; a generated **parity matrix fails the build** when the unified entry and a station binary diverge.
- **The skills** — each 03 station carries an agent-loadable domain skill, following the shape mason proved with `conda-forge-expert`.
- **The personas** — every station answers as a persona that acts **only** through the grammar and the service face; no ad-hoc filesystem or raw HTTP in the transcript.
- **Scoped by promotion class** — 01 stops at spec + script; 02 at spec + skill; only **03** owes the full five tiers plus owner and SLA.

---

<!-- _class: part -->

## ACT IV

# The mandate, delivered

Enforced by database privilege, verified by tests that fail in the invariant's absence — never by convention.

---

## Schema change, governed by construction · CAP-9

The literal directive ("no framework emits DDL, ever") was **unimplementable** — `post_migrate` is the only mechanism populating content types, permissions and sites. So enforcement moved to the **database role**:

1. **Author** in Django (developers keep their tooling) → 2. **extract** with `sqlmigrate` → 3. **land** a Liquibase changeset → 4. **CI gate** — stale extraction fails the build (**no prior art; built here**) → 5. Helm **hook Job, weight −1**, platform image, `liquibase update` (migration role holds DDL) → 6. `migrate --fake` reconciles → 7. app pods run as **`platform_app`, DML-only**. Test databases carved out.

**Proven live (CRC 2026-08-26):** `CREATE` on `public` **refused** · `/api/health` 200 as that role · changesets `:15`–`:19` executed. **Traps:** never `preserveSchemaCase` (issue 7624 — DDL silently in `public`); the Job creates schema `liquibase`; never an init container; no engine `CREATE TABLE` on import. It **reopened two shipped stories** — the correction was not optional.

---

## Failure is contained; stations talk · CAP-8 + 10 + 11

**Thirteen directives — four rewritten by research:**

- **BS-4** — PyBreaker's async circuit **never trips** on an `httpx` coroutine; we wrote the ~40-line async wrapper.
- **BS-1** — premise false: Scribe was one JSON file, not SQLite; rewritten flat-file → pgvector behind the port.
- **BS-2** — the SSE design was deprecated twice over; the 30 m annotation never raises `timeout client`.
- **BS-8** — reconcile on restart, yes; MinIO, no — a fourth backing kind fails design review.

**The backbone (CAP-8):** CloudEvents on `pyforge.events` (redis-broker, never the cache) — consumer groups, `XAUTOCLAIM` harvest, `pyforge.events.dlq`, `pyforgeloopdepth` ≤ 8. Work identity = `spec_id` + git sha + SBOM purl; Jira is an adapter, never required.

**The rule:** an invariant with no test that fails in its absence **is not implemented**.

---

## Flags without redeploy — and the packaging price · CAP-13

- **OpenFeature flagd FILE resolver** — the full targeting engine, in-process from local JSON, **zero egress**. One flag change flips Django, service and CLI surfaces with no redeploy.
- **The committed price: six conda-forge builds.** Four OpenFeature feedstocks (absent from anaconda.org *entirely*) + a `cachebox` 5.x build (conda-forge ships 6.2.5; the provider pins `<6`) + `liquibase` 5.0.4+ with the PostgreSQL JDBC driver **vendored**.
- The air-gap gate is a gate — a PyPI-only package is feedstock work, scheduled as such; every packaging story's dev session invokes `conda-forge-expert`.

---

<!-- _class: part -->

## ACT V

# The proof

Every claim dated. Nothing projected. And the day the contract closed, it reopened — by design.

---

## Dream → live cluster: four dated days

| Date | What happened |
| --- | --- |
| **08-23** | **Dreamt** — blueprint, adversarial reviews, 5 RFCs + 8 blind spots |
| **08-24** | **Grounded** — audit: the host already built; 10 rulings; research rewrote 4 directives; Dream → spec → PRD → epics in one day |
| **08-24→25** | **Drained** — steward Epics 18–32 + eight peer hook stories; one story in flight per station |
| **08-25** | **Deployed** — 12-7 on attended CRC: Helm deployed, `/ht/` **200** |
| **08-26** | **Closed out** — `/` **200** published from PostgreSQL; CAP-9 proven; CAP-1..18 closed |
| **08-26** | **Reopened** — CAP-19 minted **and first slice shipped the same day**; the Dream ruled **evergreen** |

---

## What "live" means — CRC, dated

- `GET /` → **200** — *"PyForge Lane 1 — published from PostgreSQL."* (2026-08-26)
- `GET /cms/` unauthenticated → **302** to the IdP, never a local login form
- `/ht/` → **200** on the deployed chart (12-7, 2026-08-25); `/api/health` **200** as the DML-only role
- `CREATE` on `public` as `platform_app` → **refused**
- Eight portals behind one session · eight MCP faces · `pyforge` dispatch · CloudEvents flowing · five-tier matrix **40/40** (mason's skill cell = `conda-forge-expert`)

---

## The evergreen reopen — one query plane · CAP-19

The Canopy unified chrome, identity, grammar and events — **but not where a question goes.** Five stores gave five answers (atlas in-memory DuckDB, scribe pgvector, Langflow Chroma, DB-GPT any DSN, Vizro/BSL) — and an agent that hallucinates a join could land on OLTP.

**One DuckDB HTAP engine; stations are clients:** Mode A — live **read-only ATTACH** (declared views for humans) · Mode B — **Kedro-written Parquet cache** on a *named* pipeline (the sealed seven stay untouched) · Mode C — **vss / HNSW vectors**. One writer; consumers `LOAD`, never `INSTALL`. Faces: library (in-process) + Mosaic `duckdb-server` HTTP — **both, one boot script**. Scribe: **dual-write** — the plane primary, pgvector the safety net. **Tests fail if a second writable engine or an agent OLTP DSN reappears.**

Minted 2026-08-26; first slice (34.1–34.5 + `estate-cache`) shipped the same day.

---

<!-- _class: part -->

## ACT VI

# Evergreen

Closeout is a dated slice, not the end of the contract.

---

## Held lines — and the honest leftover

**Held:** no ninth station · no `services/` farm · no fourth backing kind · no CodeRed, no `django-lasuite` on the host · **one PR-gate verdict** (Warden's; scanners are Warden plugins on CAP-18 hooks) · no agent on the OLTP DSN · no CLI absorbed.

**Leftover, named:** the isolated `mfa` sqlmigrate stays fake · optional 12.9 portability-smoke CI (Actions minutes) · MCP slice 3 parked · Q5 scorecard is a **sibling** Dream · `vizro-ai` deprecated.

**Recommended:** Django pin → `>=5.2.17,<6` when the feedstock's `5.x` branch publishes it — seven CVEs are unreachable here, but scanners key on version strings.

---

## Which surface, when — and the on-ramp

| You are… | Reach for |
| --- | --- |
| Browsing the estate | Lane 1 — `/`, CMS-published |
| Working one station | `/stations/<name>/` — same session |
| An analytical question | a Lane 3 board — only your rows |
| Scripting or CI | `pyforge <station> <noun> <verb>` or the station binary |
| An agent | `POST /stations/<name>/mcp` + skill + persona |
| Changing the schema | the governed changeset path — the app role cannot do otherwise |

**Start here:** ① sign in once → ② speak one grammar → ③ point your agent at it — start the build, lose the connection, come back and `get` the result.

---

<!-- _class: lead -->

The Dream is evergreen — closeout is a dated slice, not the end of the contract

# Eight stations. One canopy.

One session, one grammar, one backbone, one plane — and a schema no application can quietly change.

**PyForge Unifying Strategy** · steward chain · `spec-pyforge-unifying-strategy` · docs/dreams/pyforge-unifying-strategy.md

<!-- herald-ledger-band -->

---

## Ledger

<span data-fact="tree_commit_date">2026-09-15</span> · <span data-fact="cfe_skill_version">8.90.5</span> · <span data-fact="bmad_core_version">6.12.0</span> · <span data-fact="fleet_epics_done_total">207/219</span> · <span data-fact="fleet_stories_done_total">926/972</span>
