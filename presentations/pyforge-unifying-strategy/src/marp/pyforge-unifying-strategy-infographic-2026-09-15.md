---
marp: true
paginate: true
size: 16:9
title: PyForge Unifying Strategy — Infographic
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:24px; }
  h1 { letter-spacing:-0.02em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.01em; color:#201e1d; }
  strong { color:#c22a10; }
  a { color:#c22a10; }
  code { background:#eae9e9; color:#c22a10; padding:0 .3em; }
  section.lead { background:#ec3013; color:#f3f2f2; }
  section.lead h1, section.lead h2, section.lead h3, section.lead strong, section.lead code { color:#f3f2f2; }
  section.lead code { background:rgba(255,255,255,.15); }
  section.part { background:#201e1d; color:#f3f2f2; }
  section.part h1, section.part h2, section.part strong { color:#f3f2f2; }
  hr { border:none; border-top:3px solid #201e1d; margin:.3em 0; }
  table { font-size:.62em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:5px 9px; }
  ul { font-size:.86em; }
---

<!-- _class: lead -->

PYFORGE ESTATE DREAM · STEWARD CHAIN · Status — Evergreen · CAP-1..18 closed 2026-08-26 · CAP-19 live

# The Canopy

`pyforge-unifying-strategy` · the 8-station hub-and-spoke enterprise architecture

Eight capability stations that each shipped as an **excellent CLI** — and stopped there. The Canopy (`src/platform/`) mounts all eight under **one chrome, one session, one grammar, one event backbone and one query plane**, and carries the governance mandate: schema change auditable, identity revocable, failure contained.

`pyforge <station> <noun> <verb>` · hub-and-spoke · modular monolith · air-gap first · 19 capabilities

---

## At a glance

| Owner | Host | Scope | Infra — exactly | Live proof (CRC) |
| --- | --- | --- | --- | --- |
| Steward | Django 5.2 · Python 3.12 | 19 CAPs · Epics 18–37 | PostgreSQL · Redis · K8s | `/` 200 · 40/40 tiers |

### Why the Canopy — eight stations, one canopy, sign in once, never leave the origin

**01** Warden · **02** Atlas · **03** Mason · **04** Marshal · **05** Doctor · **06** Herald · **07** Scribe · **08** Steward

---

<!-- _class: part -->

## ACT I — Eight terminals

The friction

---

## 01 · The problem

Each station shipped as a **genuinely good CLI and stopped there**. An operator holding compliance findings, package health, fleet status and build queues gets **no help from the estate in relating them**.

- **8** terminals and mental models per operator — no shared identity or vocabulary
- **1/8** portals mounted before the drain — warden's, at `/compliance/`; the pattern was never repeated
- **0** ways for one station to tell another that something happened

**The mandate is governance:** auditable schema change, revocable identity, contained failure — five RFCs + eight blind-spot directives. Never merely a UI project.

---

## 02 · Four users, four broken paths

| Who | Reached the estate through | What was broken |
| --- | --- | --- |
| Platform engineer | eight separate CLIs | no shared grammar; every station its own verbs and output shape |
| Compliance auditor | warden's portal — the one that existed | compliance and nothing else; no path to context |
| Platform operator | `kubectl`, Helm, the chart | the app's own database role could alter its own schema |
| **Autonomous agent** | atlas's MCP server — the only one | seven stations had no service face; long ops died with the connection |

The agent is a **first-class user**: five of the nineteen capabilities exist mainly to make the estate legible to something that is not a human.

---

<!-- _class: part -->

## ACT II — One canopy

The insight — hub and spoke

---

## 03 · The hub-and-spoke topology

**The Canopy** — `src/platform/`, one ASGI process: `django-pyforge` chrome · allauth OIDC · Wagtail `/` · 8 portals · 8 MCP faces · `pyforge` dispatch · CloudEvents. **Never imports `pyforge.*`** — stations arrive as packages; their binaries stay first-class.

Spokes: Warden (sole PR-gate verdict) · Atlas (graph, Kedro home, plane writer) · Mason (recipes) · Marshal (loop cockpit) · Doctor (advisory diagnostics) · Herald (decks) · Scribe (memory) · Steward (custody — owns this chain).

Rail: **exactly** PostgreSQL 17 + Redis 7 (broker/cache split) + Kubernetes (`restricted-v2`). A fourth backing kind fails design review; DuckDB is a query face.

---

## 04 · Three lanes, one session — two agent doors

- **ONE SESSION** — `django-allauth` OIDC; roles from the IdP; a revoked role is gone on the next request (CAP-12).
- **Lane 1 · CAP-2** — Wagtail at `/`; pages published with no deploy; `/cms/` answers 302 to OIDC; supersedes the static console.
- **Lane 2 · CAP-1+3** — `/stations/<name>/`, HTMX, zero domain models, chrome from `django-pyforge`.
- **Lane 3 · CAP-7** — Vizro over BSL over the plane; same board URL, provably different row sets per role.
- **Agent doors · CAP-4+5** — `POST /stations/<name>/mcp` (dual-era, start/get) and `pyforge <station> <noun> <verb>` (CI parity).
- **Below:** Celery on `redis-broker` (noeviction) — cache pressure provably loses no task (CAP-11).

---

## 05 · Nineteen capabilities at a glance

| | | |
| --- | --- | --- |
| CAP-1 chrome | CAP-2 CMS front door | CAP-3 eight portals |
| CAP-4 MCP faces | CAP-5 one grammar | CAP-6 identity client |
| CAP-7 Lane 3 isolation | CAP-8 event backbone | **CAP-9 governed DDL — proven live** |
| CAP-10 containment | CAP-11 queue ≠ cache | CAP-12 revocable access |
| CAP-13 offline flags | CAP-14 Scribe store | CAP-15 domain skills 40/40 |
| CAP-16 personas 40/40 | CAP-17 run-state service | CAP-18 hook-spec contract |
| **CAP-19 query plane — first slice shipped · evergreen** | | |

Extends `spec-python-agent-platform` CAP-1..6 (shipped prior art) — re-mints nothing; `convergence.md` is the authority.

---

<!-- _class: part -->

## ACT III — How the mounting works

The mechanics

---

## 06 · One chrome — `django-pyforge` · CAP-1

- **App switcher** from each portal's registration seam (`AppConfig`): owner, backup, `work_class`, promotion date — the Guildhall refuses to tile 01/02 work.
- **Base layout + theme** — OIDC-aware `pyforge/base.html`, Modernist, WhiteNoise, zero CDNs.
- **Proof, not promise** — identical chrome, zero duplicated files; **a test fails if a portal ships its own copy**.
- Research killed the shortcut: `django-lasuite` has **no app switcher and no theme** — the chrome was ours to build.
- Reusable-app convention: `django-<station>` / `django_<station>_<app>` / compound label; models never move between apps.

---

## 07 · The front door displaces something that worked · CAP-2 + CAP-17

Wagtail Lane 1 **supersedes** Marshal's static console — parity proven **before** removal.

- **23 surfaces**: 14 runtime-reproducible · **7 build-time-only** · 3 mixed — the seven collapsed to **four decisions**.
- The retired path had **100+ inbound references** (its own story); the Kedro-Viz tree (~195 files) is **not** a parity obligation.
- **CAP-17** — the one place the chain grew: a supervisor **publishes** live run state; it never reads an operator's home directory. *The replacement is held to a higher bar than the thing it replaces — deliberately.*
- **Live proof (2026-08-26):** `GET /` **200** — "published from PostgreSQL." · `/cms/` **302** to the IdP · page edits deploy nothing.

---

## 08 · Eight portals, one identity path · CAP-3 + CAP-6

PORTAL (HTMX, zero models) → **CLIENT** (`pyforge.core`: signed **RS256**, `sub`=`idp_subject`, `aud=mcp:<station>`, `delegated_by=pyforge-host`, `exp ≤ 5 min`) → SERVICE (verifies independently — a forwarded header is never trusted) → CELERY (captures `idp_subject`, mints scoped execution tokens).

Uniform `/stations/<name>/`; warden's `/compliance/` lives on as a **permanent redirect**. Adding or removing a portal changes **no host code** outside its own registration.

---

## 09 · Every station has a service face · CAP-4

- **Wire rules:** accept `2025-03-26` → `2026-07-28` · **echo the client's revision, never assert your own newest** · never branch on a client's name.
- **Disconnect survival:** `start`/`get` over a durable store (SEP-2663's lifecycle; Tasks has no SDK runtime anywhere) · the handle is a capability — opaque, high-entropy, TTL'd · **never** progress notifications, sticky sessions, or stream replay · keep-alives well under 30 s.
- **Success:** a multi-minute operation across a simulated ingress disconnect — result retrieved from a **different replica**.

`POST /stations/<name>/mcp` · official `mcp` 2.0.0 · `GET` answers 405.

---

## 10 · The estate teaches agents its own work · CAP-15 + CAP-16

- **Domain skills** — each 03 station encodes how its work is actually done; mason's cell is `conda-forge-expert`, the original exemplar.
- **Personas** — addressable and disciplined: act **only** through CAP-5's grammar and CAP-4's face; no ad-hoc filesystem or raw HTTP.
- **Promotion classes** — 01: spec + script · 02: spec + skill · **03: the full five tiers** + owner + SLA. Build only what value and ownership justify.

---

<!-- _class: part -->

## ACT IV — The governance mandate

Auditable · revocable · contained

---

## 11 · Schema change is governed, not incidental · CAP-9

AUTHOR (Django migration) → EXTRACT (`sqlmigrate`) → CHANGESET (`db/changelog/`) → **CI GATE** (stale extraction fails the build — no prior art; built here) → **HELM HOOK JOB, weight −1** (`liquibase update`, migration role, platform image — never an init container) → `migrate --fake` (`post_migrate` still fires) → RUN as **`platform_app`, DML-only**. Test databases carved out.

**Live proof (CRC 2026-08-26):** `CREATE` on `public` **refused** · `/api/health` 200 as that role · schema `liquibase` + contrib/auth/Wagtail changesets `:15`–`:19` executed.

**Traps, named:** never `preserveSchemaCase` (issue 7624 — DDL silently in `public`) · the Job **creates** schema `liquibase` · feedstock targets **5.0.4+** · no Agent-Canopy engine `CREATE TABLE` on import.

---

## 12 · Thirteen directives — four rewritten by research · CAP-10

| # | Status | Bound form |
| --- | --- | --- |
| RFC-1 | revised | one ASGI Deployment; Celery is the independently-scaling pool |
| RFC-2 | as written | `redis-broker` (noeviction) split from `redis-cache` (allkeys-lru) |
| RFC-3 | revised | RS256, not HMAC; audience-bound; exp ≤ 5 min |
| RFC-4 | revised | `pyforge.events(.dlq)` · XAUTOCLAIM · `pyforgeloopdepth` ≤ 8 |
| RFC-5 | revised | role-based least-bad (§ 11); zero prior art existed |
| BS-1 | premise false | Scribe was one JSON file, not SQLite; flat-file → pgvector behind the port |
| BS-2 | revised | `/mcp/sse` deprecated twice over; the 30 m annotation never raises `timeout client` |
| BS-3 | as written | delegation context + scoped tokens; Keycloak caveat pinned |
| BS-4 | revised | PyBreaker's async circuit **never trips**; our ~40-line wrapper |
| BS-5 | as written | single writer; every other handle `read_only=True` → CAP-19 |
| BS-6 | as written | schema-versioned CloudEvents; validation in domain adapters |
| BS-7 | as written | `PydanticFormErrorBridge` in `django-pyforge` |
| BS-8 | revised | reconcile on restart, yes; MinIO, no — RWX, not a fourth kind |

**An invariant with no test that fails in its absence is not implemented.**

---

## 13 · Stations can tell each other things · CAP-8

PUBLISH (CloudEvents `schema_version 2.x` · `spec_id` + git sha + SBOM purl; Jira is an adapter — never required) → STREAM (`pyforge.events`, consumer groups per station) → UNACKED (PEL → `XAUTOCLAIM` harvest) → QUARANTINE (`pyforge.events.dlq`; cycles halt at depth 8).

A poisoned event lands in the DLQ instead of retrying forever. OpenLineage rides **this** fabric — a face on CAP-8, never a fourth bus.

---

## 14 · Revocable, delivered, flippable — and the price · CAP-12 + CAP-13

- **Identity** — IdP roles; revoke → gone next request.
- **Secrets** — pod specs carry references only; `go-sops` + `age` in estate; Vault outside the image, never `hvac` in-process.
- **Flags** — OpenFeature flagd FILE resolver: in-process, full targeting engine, zero egress, no redeploy.
- **The price: 6 conda-forge builds** — 4 OpenFeature feedstocks (anaconda.org: zero results) + `cachebox` 5.x + `liquibase` 5.0.4+ (JDBC vendored; `apache-tika` shape; `openjdk` 25 clears Java 17+).

---

<!-- _class: part -->

## ACT V — The proof

Dreamt → drained → proven → reopened

---

## 15 · Dream to live cluster in four days — dated

- **08-23 · Dreamt** — hub-and-spoke blueprint, adversarial reviews, 5 RFCs + 8 blind spots.
- **08-24 · Grounded** — the audit found **the host already built**; owner herald → steward; ten rulings; four directives rewritten; spec → brief → PRD → spine → Epics 18–30, one day.
- **08-24→25 · Drained** — Epics 18–32 + eight peer hook stories; worktree `bmad-build-auto`; one story in flight per station; merge never squash.
- **08-25 · Deployed** — 12-7 on attended CRC: Helm deployed, Liquibase + `migrate --fake`, `/ht/` **200**.
- **08-26 · Closed out** — `/` **200** from PostgreSQL; CAP-9 DML-only **proven**; `:17`–`:19` executed.
- **08-26 · Reopened** — CAP-19 minted **and first slice shipped the same day**; the Dream ruled **evergreen**.

---

## 16 · One HTAP query plane; stations are clients · CAP-19

Before: **five answers** — atlas in-memory DuckDB · scribe pgvector · Langflow Chroma · DB-GPT any DSN · Vizro/BSL — and a hallucinated join could land on OLTP.

**One DuckDB engine, one writer.** Mode A — live **read-only ATTACH** of Postgres (declared views for humans) · Mode B — **Kedro-written Parquet cache** on a *named* pipeline (the sealed seven stay untouched) · Mode C — **vss / HNSW** vectors. Consumers `LOAD`, never `INSTALL`.

Clients: Vizro/BSL (Lane 3) · station library face · agents via the **Mosaic HTTP face** (no OLTP DSN) · Scribe store-port driver (34.5).

**OQ rulings 2026-08-26:** both faces, one boot script · a named new pipeline · dual-write for now. **Tests fail** if a second writable engine or an agent OLTP DSN reappears.

---

## 17 · Five-tier symmetry — declared complete, 40/40

| Station | CLI | Portal | Service | Skill | Persona |
| --- | --- | --- | --- | --- | --- |
| Warden | ✓ | ✓ | ✓ | ✓ | ✓ |
| Atlas | ✓ | ✓ | ✓ | ✓ | ✓ |
| Mason | ✓ | ✓ | ✓ | **CFE** | ✓ |
| Marshal | ✓ | ✓ | ✓ | ✓ | ✓ |
| Doctor | ✓ | ✓ | ✓ | ✓ | ✓ |
| Herald | ✓ | ✓ | ✓ | ✓ | ✓ |
| Scribe | ✓ | ✓ | ✓ | ✓ | ✓ |
| Steward | ✓ | ✓ | ✓ | ✓ | ✓ |

Declared 2026-08-26 (Epic 37.1). A missing cell **fails CI**. Mason's skill cell is `conda-forge-expert`. 01/02 work is never scored against this matrix.

---

<!-- _class: part -->

## ACT VI — Held lines & the road

Honesty · doctrine · on-ramp

---

## 18 · What the chain refuses to build — and what it honestly left

**Held lines:** no ninth station · no `services/` farm · no fourth backing kind · no CodeRed, no `django-lasuite` on the host · no second PR-gate verdict (Warden sole; scanners are Warden plugins on CAP-18 hooks) · no agent on the OLTP DSN · no CLI absorbed.

**Honest leftover:** `mfa` — the one sqlmigrate that stays fake · `12.9 CI` — optional, awaiting Actions minutes · `MCP slice 3` — parked with the sibling isolation spec · `Q5 scorecard` — sibling Dream; unpublished metrics must not steer · `vizro-ai` — deprecated.

**Recommended:** Django pin → `>=5.2.17,<6` when the feedstock's `5.x` branch publishes it.

---

## 19 · Which surface, when

| You are… | Reach for |
| --- | --- |
| Browsing the estate | Lane 1 — the front door at `/` |
| Working one station | its portal at `/stations/<name>/` |
| An analytical question | a Lane 3 board — only the rows your role allows |
| Scripting or CI | `pyforge <station> <noun> <verb>` — or the station binary |
| Driving it as an agent | `POST /stations/<name>/mcp` + skill + persona |
| Changing the schema | the governed changeset path — by construction |

---

## → Start here — the on-ramp

1. **Sign in once** — the front door at `/`; all eight portals and the boards on one session.
2. **Speak one grammar** — `pyforge <station> <noun> <verb>`; station binaries still first-class.
3. **Point your agent at it** — `POST /stations/<name>/mcp`; start the build, lose the connection, come back and `get` the result.

---

<!-- _class: lead -->

The Dream is evergreen — closeout is a dated slice, not the end of the contract

# An estate, not eight tools.

An operator signs in once and moves from a published page to eight portals to a board that shows only their rows. An agent drives the same stations over MCP and survives the disconnect. The whole estate deploys egress-blocked on PostgreSQL, Redis and Kubernetes — with a database role that provably cannot alter its own schema.

**PyForge Unifying Strategy** · steward chain · `spec-pyforge-unifying-strategy` · CAP-1..19 · docs/dreams/pyforge-unifying-strategy.md

<!-- herald-ledger-band -->

---

## Ledger

<span data-fact="tree_commit_date">2026-09-15</span> · <span data-fact="cfe_skill_version">8.90.5</span> · <span data-fact="bmad_core_version">6.12.0</span> · <span data-fact="fleet_epics_done_total">207/219</span> · <span data-fact="fleet_stories_done_total">926/972</span>
