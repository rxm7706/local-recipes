---
title: Foundry BaaS-Inspired Capability Gaps
type: dream
owner: steward
status: draft
---

# Foundry BaaS-Inspired Capability Gaps

## The aspiration

Build in the open, and make the result easy to deploy and reuse anywhere. That aspiration was
checked against two concrete tools — [InsForge](https://github.com/InsForge/InsForge) (a
self-hostable, Apache-2.0, agent-centric backend-as-a-service) and
[Vercel](https://github.com/vercel)'s open-source tooling — asking specifically whether either
belongs inside `pyforge`/Foundry Platform. It does not, for reasons this Dream documents in full. But
the exercise surfaced real value along the way: five end-user capability gaps worth closing with
Foundry-native tools, and one finding that an existing, operator-ratified architecture rule
(`pap:AD-1`'s infra-kinds cap, and this chain's own canopy `AD-13`) was asserted with a weaker
justification than its own documentation claims — a finding worth a formal second look, not a silent
correction.

This is a **seed Dream**. It is intended to be folded into
[`pyforge-unifying-strategy`](pyforge-unifying-strategy.md) — the 8-Station Hub-and-Spoke Foundry Dream
this whole analysis is checked against — the same way `pyforge-target-monorepo`,
`pyforge-foundry-unifying-architecture`, and `fleet-convention-consistency` were each seeded standalone
and later absorbed (see that Dream's Realization log). The fold is a deliberate next step, not done
here.

## What InsForge and Vercel's OSS actually are (verified against their repos, not memory)

**InsForge** (`github.com/InsForge/InsForge`, Apache 2.0): a bundled backend-as-a-service — Postgres,
Auth, S3-compatible storage, Realtime, edge functions, a model gateway, and site deployment — built on
TypeScript/Deno + PostgreSQL (+ pgvector). It's explicitly **agent-centric**: its primary interface is
an MCP server exposing backend operations (create a bucket, run a migration, deploy a function, read
schema/logs) as tools an AI coding agent calls directly, plus a CLI. Deployment: managed cloud
(insforge.dev), self-hosted via Docker Compose, or one-click (Railway/Zeabur/Sealos/RepoCloud).
Positioned as the open-source, self-hostable answer to Supabase/Firebase, for agent-built apps
specifically.

**Vercel's OSS** (`github.com/vercel`): almost entirely JS/TS-specific — Next.js, Turborepo, the AI
SDK, SWR, Svelte/Nuxt/Nitro, shadcn/ui, a Workflow SDK, newer agent-tooling (agent-browser, `skills`,
`fx`). None of it is Python-oriented. Vercel's hosting platform itself is proprietary commercial SaaS,
not open source — free hobby tier, paid at scale, git-push deploys with preview URLs. It supports
Python only as narrow serverless functions (no persistent processes, no long-running workers, ephemeral
filesystem, execution-time limits) — there is no path to running Django + ASGI + Celery + Postgres +
Redis on it.

## The constraints this was checked against

`pyforge-unifying-strategy.md`'s Grounding locks in several dated, operator-ratified decisions that
bear directly on this question:

- **Infra kinds: PostgreSQL + Redis + Kubernetes, no fourth kind** (`pap:AD-1`, inherited from the
  parent `spec-python-agent-platform`) — "No Elasticsearch, no Vault-as-app-dep, no RQ, no fourth
  *kind*." InsForge is exactly the shape this rejects: a new, separate Postgres+Auth+Storage+Realtime
  service.
- **Single identity engine** — `django-allauth` (OIDC/SSO) is the one auth system. InsForge ships its
  own; no bridge is documented, and two identity systems contradicts "one Foundry."
- **Not a fragile monolithic SPA** — "Server-driven Django + HTMX + Wagtail... Lane 3 is
  reverse-proxied Vizro, not a React analytics SPA" is a direct, named rejection of the Next.js/React
  shape Vercel's tooling is built around.
- **Self-hosted Kubernetes/OpenShift deployment, air-gap parity as a failing check** (`pap:CAP-6`) —
  Vercel's hosting model (outbound build pipeline, hosted edge network) cannot satisfy an air-gapped,
  on-prem target at all; there is no self-host option for the *platform* itself (only for its OSS
  libraries).
- **MCP is already solved in-tree, if not yet fully populated** — every station mounts
  `POST /stations/<name>/mcp` on the host ASGI via the official MCP SDK, isolated in its own
  `mcp-host` sidecar. InsForge's MCP gateway would duplicate hosting mechanics that already exist.
- **Cost posture** — Foundry is private, self-hosted, and meters its own Actions-minutes budget
  (Story 44.15) by deliberate choice; a commercial SaaS dependency cuts against that posture
  independent of the technical mismatch above.

## Scope-by-scope verdict

**A — Core Foundry Platform (`src/platform/`): not recommended.** Every constraint above applies
directly, and the Dream literally names "no MinIO as a fourth core kind" as the pattern it rejects.
InsForge/Vercel don't fill a gap here — Postgres, Auth, and MCP hosting are already shipped — they'd
duplicate all three while breaking the infra-kinds lock, the single-identity rule, the no-SPA rule, and
the air-gap requirement at once. Pursuing this needs an explicit `bmad-correct-course` naming which
rulings it reverses and why, not a silent bolt-on.

**B — A standalone station spinoff (a small companion app for one `pyforge-<station>`): viable as a
bounded pilot.** The constraints above are scoped to `src/platform/` specifically; a station package
already runs standalone (its own pixi env, its own CLI). A small externally-facing demo — "ask scribe,"
"warden scan results" — that a stranger can `docker compose up` and get Postgres+Auth+Storage for free
is a genuine, narrow fit, and InsForge's MCP-native design matches if the demo's point is "let an agent
build/extend this app." Keep it entirely outside `src/platform/`; it should never appear in the Foundry
image, Helm chart, or infra-kinds list. **PocketBase** (single Go binary, ~20 dependencies, zero
payment/telemetry/AI-SDK baggage) is worth naming as a lower-footprint alternative here, at the cost of
a materially weaker MCP story (community-only, no official server) — pick InsForge if the demo's point
is agent-nativeness, PocketBase if it's minimum footprint.

**C — A brand-new separate open-source project, loosely interoperating via MCP: strongest fit of the
three, if genuinely decoupled.** Next.js + Vercel hosting + InsForge (self-hosted or cloud) + the
Vercel AI SDK is a coherent, zero-lock-in "deploy anywhere" stack that satisfies the aspiration
literally, without touching Foundry at all. The clean interop path: the new project's agent features
call *out* to pyforge's existing `/stations/<name>/mcp` endpoints as tools. pyforge stays untouched — a
service the new project consumes, not a merge.

## Capability comparison — InsForge (fresh) vs. pyforge/Foundry (today)

| Capability | InsForge gives you out-of-the-box | pyforge/Foundry gives you today | Verdict |
|---|---|---|---|
| Relational DB + migrations | Bundled custom Postgres image, `node-pg-migrate` | Self-managed Postgres 17 (Helm StatefulSet, backup CronJob), Liquibase-governed schema, isolated per-app schemas | Redundant — pyforge is more production-hardened |
| Auto-generated REST API from schema | PostgREST exposes full CRUD on any table automatically | Hand-written, versioned station contract (`/stations/<name>/api/v<N>/` via `pyforge.core.client`) | Deliberate tradeoff, not a gap — pyforge traded raw-schema exposure for a curated, versioned contract |
| Auth / Identity | Bundled JWT + OAuth (Google/GitHub/Discord/MS/LinkedIn/X/Apple) | `django-allauth` OIDC/SSO, single identity engine, mature | Redundant — pyforge already ahead |
| Object storage (S3-compatible) | AWS SDK v3 + presigned URLs, swappable backend (S3/MinIO/RustFS) | Media has nowhere to go on ephemeral pod disk; the estate's own answer to this is under active re-examination — see § *Reopening AD-1* below | Real, live question — see below, not a closed gap |
| Realtime (DB-change push to browser) | socket.io-based subscriptions | None as a base dependency — HTMX is server-driven by design, but a full Channels/Daphne architecture already exists as an optional extra (see § *Recommendations*, item 2) | Largely already answered, not a gap |
| Edge functions (arbitrary user code) | Deno runtime, deploy-on-demand | None — async work is Celery tasks inside station packages | Different paradigm — pyforge isn't a multi-tenant platform for third-party function deploys |
| MCP / agent-tool surface | Auto-generates CRUD MCP tools straight from DB schema (core value prop) | Official-SDK hosting exists and is proven (Atlas: 13 tools, shipped); most other stations' host-mounted face is still a placeholder | Interesting, not redundant — see § *Recommendations*, item 3 |
| Admin/dashboard UI (generic table browser, SQL editor, schema graph) | Full React dashboard, CodeMirror SQL editor, schema visualizer | Hand-built Django/HTMX portals per station + Wagtail CMS + Vizro/BSL | Redundant for existing stations — this is the "instant scaffold" value InsForge sells before domain UI exists |
| Payments (Stripe/Razorpay) | Bundled, unconditional | None | Dead weight — pyforge isn't a billed SaaS product |
| Deployment model | Docker Compose / one-click PaaS / managed cloud | Helm on Kubernetes/OpenShift, CRC-attended, digest-pinned CD, air-gap parity as a failing check | Different tier — InsForge optimizes for 5-minute self-host; pyforge is already committed to enterprise cluster ops |
| Language/runtime footprint | TypeScript/Node/Deno + a custom Postgres image | 100% Python (Django/Celery/pixi) | Real ongoing cost — a second language ecosystem to secure/maintain (see footprint note below) |
| Governance/maturity | Apache 2.0, single-vendor-led, young project | Fully in-house, shaped by a dated red-team architecture review | Adds third-party dependency risk for capability pyforge mostly already has |

**InsForge's dependency footprint**, verified against its live manifests (not marketing copy): four
containers (a custom `ghcr.io/insforge/postgres` image, PostgREST, a Node/Deno app image, a Deno
functions runtime — with MinIO and RustFS as swappable alternate storage backends), and an npm
dependency tree that unconditionally bundles Stripe *and* Razorpay, a hardcoded OpenAI SDK (not
provider-agnostic), and `posthog-js` telemetry in the dashboard — real attack-surface/license/phone-home
considerations for a dependency-hygiene-conscious adopter, independent of whether the capabilities
themselves are wanted.

**Sanity check — is InsForge even the right reference point?** Compared against Supabase (self-hosted,
11 containers, polyglot Elixir/Go/Haskell/Node), PocketBase (single Go binary, ~20 deps, no official MCP
server), and Appwrite (30+ containers, three simultaneous database engines, its own bundled AI-assistant
services) — the comparison doesn't change the conclusion, it reinforces it: all four would fail
Foundry's locked rules the same way InsForge does, Appwrite far more so. InsForge is, if anything, a
fair-to-favorable choice specifically on "self-hostable + genuinely agent-native," since Supabase and
Appwrite both bolted MCP onto older, heavier products rather than building around it.

## Recommendations

Rather than adopting InsForge/Vercel wholesale, the more valuable move is to treat InsForge as a
**capability checklist**: take the end-user-facing gaps it exposes and check them against what Foundry
has already decided or shipped before proposing anything new.

1. **Object storage for media.** This looked like a closed gap (Epic 20 already implements a
   `ReadWriteMany`-PVC-only answer per canopy `AD-13`) until direct scrutiny of that decision's own
   justification surfaced two real gaps — see § *Reopening AD-1*, immediately below. Status: open, not
   closed.
2. **Realtime push.** Already specced and partially shipped, more mature than a first read suggests: a
   full architecture spine (`architecture-secure-live-dashboards-2026-08-09`) gives Django + Channels +
   Daphne + `channels_redis`, shipped as the optional extra `pyforge-steward[dashboard]` — Redis is
   already split into `redis-broker` and `redis-cache` specifically to support it (Epic 20 / Story 9.5),
   with per-message auth and protocol-specific identity resolution designed in. Open question: whether
   it's wired to live station data yet, or still just the plumbing.
3. **Baseline MCP tools per station.** InsForge's "auto-generate tools from a schema" premise doesn't
   transfer here — per the Dream's own "zero domain models on portals" rule, `django-<station>` apps
   carry no domain data at all (one station's only model is thin Celery-job metadata; the rest have no
   `models.py`). Real domain data lives inside each `pyforge-<station>` package in heterogeneous stores
   (DuckDB/SQLite/JSON/dataclasses) — there's no single schema to introspect the way InsForge
   introspects one Postgres database. What's actually true and cheaper: the wiring pattern is already
   proven for Atlas (a real 13-tool official-SDK server, ~30 lines of wiring code, shipped as Story
   21.2). Marshal has its own 7-tool server, but built on FastMCP — forbidden in the `mcp-host`
   sidecar's isolation boundary — so **porting Marshal to the official SDK is the actual smallest next
   slice**, not schema introspection. The other six stations have no tool server at all; authoring their
   first tools is real per-station engineering work, the same effort class as originally building
   Atlas's or Marshal's tools, and isn't something a generator shrinks.
   Security note, flagged rather than silently resolved: one research pass read the 2026-09-02 red-team
   review as leaving two HIGH findings open on this surface (anonymous `tools/list`/`initialize`; no
   rate limiting). A second, code-level pass found both already shipped (per-station audience scoping
   in the auth layer; per-request rate limiting in the dispatch path). The two passes disagree — trust
   the more specific, file-grounded one, but this is worth a human double-check before treating the
   gating concern as fully resolved.
4. **Lean on Django Admin as the generic "browse any table" console**, instead of hand-building one.
   Confirmed genuinely open — nothing in the estate uses Admin as a designed data-browsing capability
   today, only as access-controlled plumbing. A mature, native, zero-new-dependency answer to the same
   problem InsForge's React dashboard solves.
5. **A read-only, human-operator SQL console over the DuckDB query plane.** The estate's "no raw SQL"
   rule restricts *agent* access to the OLTP DSN, not a human operator's ad-hoc query need. The
   `query-plane-face` decision (an in-process library face plus an optional HTTP/Arrow face) was about
   programmatic/agent access parity, not a human console — but a future console could sit on that
   HTTP/Arrow face once built, rather than needing its own plumbing.
6. **Formally reopen `pap:AD-1` and canopy `AD-13` via `bmad-correct-course`.** Not a capability
   addition — a process recommendation, and the strongest finding of this whole pass. Detail below.

**Deliberately excluded**, to keep this list honest rather than reflexively additive: an
auto-generated raw-schema REST API (conflicts with the curated-contract principle), payments, arbitrary
third-party edge-function deploy (not a multi-tenant platform), and any new self-run storage *server*
running inside the cluster as its own workload — all rejected for the reasons Scope A is rejected
above.

## Reopening AD-1: is "no object storage, ever" actually justified?

> **Correction (2026-09-05, `bmad-correct-course` — `pyforge-steward`
> `sprint-change-proposal-2026-09-05-ad-1-reopen.md`).** Both legs below were re-read against
> primary sources and corrected; the operator ruled **re-affirm, not except** (Option A).
> (1) Parent `AD-1` never invokes air-gap — its full text is design-review discipline ("a
> component that demands a fourth piece of infrastructure has failed its design review"); the
> air-gap decision is parent `AD-13`, which no canopy artifact cites as AD-1's reason. (2) The
> RWX claim **did** bind on the target — `platform-media` Bound on CRC 2026-08-25
> (`crc-csi-hostpath-provisioner`, Story 12.7 verification record) — and RWO cannot substitute
> at `replicaCount: 1`, because five Deployments (web, worker, worker-builds, beat,
> consume-events) mount the media volume. **What survives:** CRC is single-node hostpath, no
> multi-node target exists yet, `storageClassName: ""` defers to a default class that is often
> RWO-only, and no artifact named that prerequisite — now recorded in canopy `AD-13`, with the
> "formally excepted" procedure defined in the canopy spine. Read the section below as the
> pre-correction argument; the fold into `pyforge-unifying-strategy` carries the corrected text.

This started as a routine "confirm the gap is already closed" check and became the most consequential
finding here — not that a new kind should be added, but that the rule as currently justified has two
real gaps, found by reading the primary architecture sources directly rather than trusting a summary of
them.

**1. The air-gap argument doesn't distinguish self-hosted object storage from self-hosted
Postgres/Redis.** Air-gap parity rules out *depending on a public-internet endpoint* — it does not rule
out a self-hosted, internal-only S3-compatible store (MinIO, Ceph RGW). That's exactly as
air-gap-compatible as self-hosted Postgres/Redis already are; none of the three approved kinds are
approved because of cloud-vs-self-hosted, they're approved because they run inside the cluster with no
outbound dependency. This estate already trusts the identical substitution pattern elsewhere:
`docs/reference/enterprise-deployment.md` documents JFrog Artifactory as the sanctioned air-gapped
stand-in for public conda-forge/PyPI — an internal service speaking the same protocol as the public one
it replaces. There is no principled reason object storage is different, and the InsForge-shaped
proposal on the table was always self-hosted MinIO, never literal AWS S3.

**2. The "compatible" `ReadWriteMany`-PVC alternative was asserted, not verified, and may not even be
needed yet.** Checked directly against the Helm chart and its test suite, not the review's prose:

- `src/platform/deploy/charts/platform/values.yaml:11` sets `replicaCount: 1`. The platform Deployment
  runs a single web replica. The cross-replica consistency problem RWX exists to solve — "replica A
  writes, replica B must see it" — isn't live infrastructure today.
- `src/platform/tests/test_chart_invariants.py:1999`
  (`test_media_pvc_is_readwritemany_and_mounted_on_web_and_worker`) is a **Helm-template rendering
  assertion** — it checks the rendered YAML declares `accessModes == ["ReadWriteMany"]` and mounts on
  the right containers. It does not deploy anything or prove a PVC actually binds. Story 20.2's
  `status: done` reflects "the manifest is shaped correctly," not "this was proven to work on real
  infrastructure."
- `values.yaml:256` sets `storageClassName: ""` for the media PVC — "use whatever the cluster's default
  storage class is." Most default provisioners, including the typical OpenShift-Local/CRC hostpath
  provisioner, **do not support `ReadWriteMany` at all** — RWX generally requires NFS, CephFS/ODF, or
  similar, specifically provisioned. The CRC bring-up record documents PVC binding only for the earlier
  Postgres/Redis (RWO) work, which predates Wagtail — nothing found confirms an RWX-capable storage
  class exists on the actual target cluster.
- Consequence: at `replicaCount: 1`, an ordinary `ReadWriteOnce` PVC — supported by virtually every
  storage class, no special provisioner needed — already solves the actual current problem (surviving
  pod restarts) with zero unverified assumptions. RWX only becomes necessary if a second replica is
  ever added, and at that point the storage class needs to be confirmed before being called
  "compatible," not assumed. If RWX genuinely requires standing up NFS/CephFS where neither exists
  today, the "stay within three kinds" answer may cost comparable or greater operational surface than
  the self-hosted-MinIO option it was written to reject — undermining the rule's own stated purpose.

**Bottom line.** The "no fourth kind, ever" rule's air-gap leg doesn't survive scrutiny for the
self-hosted case, leaving only an operational-surface-minimization preference — legitimate, but a
judgment call, not a hard wall — and its own chosen implementation hasn't been checked against whether
it's actually cheaper than the thing it rejected. This is **not** a claim that self-hosted MinIO is
definitely the right answer — the second-language/footprint concerns noted above would still apply to
adopting InsForge's MinIO specifically — only that the current rule was asserted with weaker
justification than its documentation presents, and the review's own process explicitly allows reopening
it ("review-blocking until parent AD-1 is formally excepted"). That reopening hasn't happened. Formally
running `bmad-correct-course` against this evidence, with an operator ruling recorded the same way every
other decision in the parent Dream is recorded, is the next step — not something this seed Dream
resolves on its own.

## Kinships

[[pyforge-unifying-strategy]] (fold target — this Dream's findings belong in that Dream's Grounding and
recommendation surface once reviewed) · [[secure-live-dashboards]] (item 2, realtime push, is that
Dream's architecture, not a new one) · [[pyforge-atlas]] (item 3's proven MCP wiring pattern lives
there) · [[pyforge-scribe]] / [[pyforge-warden]] (item 6's dependency-hygiene lens on InsForge's
footprint is exactly warden's domain)

## Realization log

- **2026-09-05** — Seeded from a plan-mode research conversation evaluating whether InsForge and
  Vercel's tooling should be adopted into pyforge/Foundry. Verdict: no, at the Foundry Platform layer
  (Scope A); a bounded pilot only outside it (Scope B); genuinely useful only as a fully separate,
  loosely-MCP-coupled project (Scope C). Along the way: five Foundry-native capability additions
  identified, two of which turned out to already be decided/shipped on closer check (realtime; and
  object storage — see next point); and one finding that AD-1/canopy AD-13's own justification has two
  unaddressed gaps (an over-broad air-gap argument, and an unverified RWX-storage-class assumption at
  `replicaCount: 1`), recommended for formal reopening via `bmad-correct-course`. **Not yet done**:
  folding this into `pyforge-unifying-strategy.md`; running `bmad-correct-course` on the AD-1 finding.
- **2026-09-05 (later)** — `bmad-correct-course` ran on the AD-1 finding
  (`pyforge-steward` `sprint-change-proposal-2026-09-05-ad-1-reopen.md`). Both legs corrected
  against primary sources (see the dated block at the top of § *Reopening AD-1*); operator
  ruling: AD-1 / canopy AD-13 **re-affirmed**, RWX storage-class prerequisite recorded, exception
  procedure defined. Recommendation 6 is closed. **Still not done:** the fold into
  `pyforge-unifying-strategy.md`.
