---
title: Sprint Change Proposal — stamp the Canopy SPEC shipped
date: 2026-08-26
project: pyforge-steward
chain: pyforge-unifying-strategy
status: approved
trigger: operator closeout — CAP-2 live at /, CAP-9 role proof, drain leftovers already landed
mode: batch
scope: minor
operator: Rxm7706 directed implementation (seed Lane 1 + bind leftovers + stamp shipped)
---

# Sprint Change Proposal — Canopy closeout bind

## 1. Issue summary

The Unifying Strategy SPEC stayed `in-progress` after the 2026-08-25 drain-bind because
Dream Grounding and the kernel still named **open** leftovers that had since landed
(`:17`/`:18`, sidecar image, mcp dual-era / sidecar host, one-pixi-env, `platform_app`).
CAP-2's success signal still required a **published Lane 1 page** at `/`; CRC had schema
(`:19`) but no Site/HomePage, so `/` was 404 while `/cms/` already 302'd to OIDC.

Type: **implementation overtook the residual list** — not a new product, not a rollback.

Evidence: CRC 2026-08-26 proofs below; PRs #856, #858, #859, #861; steward ledger 18–32
`done`; `spec-platform-image-one-pixi-env` `shipped`.

## 2. Impact analysis

### Checklist (batch)

| ID | Status | Finding |
|---|---|---|
| 1.1 | Done | Trigger is leftover bind + CAP-2 seed, not a new epic. |
| 1.2 | Done | Type: residual list stale vs live CRC. |
| 1.3 | Done | Route proofs + Liquibase `:17`–`:19` + role grants. |
| 2.1 | Done | No new epic or story. |
| 2.2 | Done | No story rewrite. |
| 2.3 | Done | Isolated `mfa` sqlmigrate stays fake (only RFC-5 leftover). |
| 2.4 | Done | Do not mint query-plane / HTAP CAP (correct-course later if wanted). |
| 2.5 | Done | 12.9 `ocp-portability-smoke` is an honesty gap, **not** a stamp gate. |
| 3.1–3.4 | Done | SPEC + Dream + companions + PRD status. |
| 4.1 | Viable | Direct Adjustment. Effort: S. Risk: Low. |
| 4.4 | Done | **Option 1 — Direct Adjustment.** Operator directed apply. |

### Epic / story impact

None. Story 12.9 remains the optional pap:AD-11 CI job (ledger already `done` without the
job — do not flip it here). Actions minutes are a **gate**, not a story.

### Artifact conflicts

- `docs/dreams/pyforge-unifying-strategy.md` Grounding + `status`
- `spec-pyforge-unifying-strategy` SPEC / companions / memlog
- PRD status
- 12.1 verification addendum (`/` 200)

### Technical impact

Idempotent `seed_lane1_homepage` on `front_door` `post_migrate`. CRC already seeded
Root + published HomePage + default Site (`platform.apps-crc.testing:443`).

## 3. Recommended approach

**Direct Adjustment.** Classify **Minor**. Apply in this session.

## 4. Detailed change proposals (applied)

### CAP-2 live (CRC 2026-08-26)

| Check | Result |
|---|---|
| `GET https://platform.apps-crc.testing/` | **200**, body contains `PyForge Lane 1 — published from PostgreSQL.` |
| `GET /cms/` (unauthenticated) | **302** `Location: /accounts/oidc/oidc/login/?next=/cms/` |
| `GET /ht/` | **200** |

### CAP-9 live role proof (CRC 2026-08-26; not “CRC holes”)

- Role `platform_app` exists; Liquibase `:2` **EXECUTED**.
- Web `DATABASE_URL` uses `platform_app`.
- `GET /api/health` **200** as that role.
- `CREATE` on schema `public` as `platform_app` **refused** (DML-only).
- Governed DDL path: Liquibase Job / host `liquibase update`; app role does not own schema.

### Drain leftovers now landed (do not re-open)

- `:17` django_celery_beat, `:18` third-party/allauth 0001, `:19` Wagtail 7.4 catch-up
  (`site_name` + locale/collection/page columns).
- `spec-platform-image-one-pixi-env` shipped; no `pip install --no-deps` in the Containerfile.
- Story 10.5 sidecar Ready (`NOTE_BOOK_ENABLE=false`).
- MCP host sidecar (slice 1, PR #858) + factory stdio translator (slice 2, PR #859).
  Slice 3 (retire ImportError skip) stays parked until FastMCP 4 or Langflow drops `mcp<2`.

### Still not this stamp

- Isolated `mfa` sqlmigrate — fake only.
- Query plane / HTAP — no CAP; sibling capture absorbed; mint only via later correct-course.
- Q5 scorecard — parked sibling.
- Platform CI air-gap + `platform-mcp-host` bake — when Actions minutes return.
- Story 12.9 `ocp-portability-smoke` — pap:AD-11 honesty, optional for this SPEC.

Kernel moves:

- SPEC `status: shipped`; Dream `status: realized`; PRD `status: shipped`.
- Why / CAP-9 residual / Grounding lists match the table above.
- Architecture leftover subgraph is closeout, not “12-7 holes.”

## 5. Implementation handoff

**Scope:** Minor — Developer (this session).

**Success:** `/` 200 through the CRC Route; `/cms/` 302 to IdP; SPEC and Dream stamped;
CAP-9 recorded as proven; 12.9 named as optional honesty work.

**Routed to:** applied below.
