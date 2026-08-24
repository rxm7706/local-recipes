---
reviewer: architecture-spine-rubric
artifact: ARCHITECTURE-SPINE.md
chain: pyforge-unifying-strategy
altitude: feature (epics/stories below)
parent: specs/spec-python-agent-platform/ARCHITECTURE-SPINE.md
driving-spec: specs/spec-pyforge-unifying-strategy/SPEC.md
date: 2026-08-24
verdict: PASS-WITH-FLAGS
---

# Rubric review — Architecture Spine (pyforge-unifying-strategy) — rescore

**Gate verdict: PASS-WITH-FLAGS.** Previous highs H1–H5 are closed in the current files (not comment-only). Previous mediums M1–M6 are closed as ADs, Stack pins, citation convention, or Deferred-with-revisit. Remaining issues will not split the epic set; they are polish or one-capability ops detail. Safe to send to `bmad-create-epics-and-stories` after treating flags as story-entry constraints (especially CAP-13 refresh).

Scope notes honored: packaging/feedstock work is operator-owned — `canopy AD-16` remains the correct gate. No packaging ADs demanded.

---

## Re-verdict of previous highs

### H1 — Object storage vs parent AD-1 — **closed**

Verified in current spine, not assumed:

- Inherited parent AD-1 row: Lane 1 media is a Kubernetes RWX volume (canopy AD-13), not MinIO/S3; two Redis Deployments still Redis.
- **Conflict, not override — parent AD-1:** MinIO/S3 would be a fourth *kind*; compatible path is `ReadWriteMany` PVC; in-cluster object-store Deployment is review-blocking until parent AD-1 is formally excepted.
- Canopy **AD-13** Rule: media on RWX at a fixed path; Django filesystem storage (default or `django-storages` FileSystemStorage); MinIO/S3 / cloud object-store backend is review-blocking.
- Stack: `django-storages` `1.14.6` pinned as library; backend called out as filesystem on RWX, not S3.
- Structural seed: `wagtail-media ReadWriteMany PVC`.
- Deferred **BS-8**: MinIO blocked; Mason re-index against PG + RWX until parent AD-1 excepted.
- Resilience companion **BS-8** row matches (REVISED — object store blocked).

`django-storages` is no longer smuggling an infra kind. Two portal/Lane-1 stories cannot pick MinIO vs RWX without hitting the Rule.

### H2 — Extra PostgreSQL schemas vs parent AD-5 cardinality — **closed**

- Inherited parent AD-5: isolation still binds; **schema count amended** to four (canopy AD-9).
- Conflict note: CAP-4 / CAP-17 stores are **tables in `public`**, not extra schemas; fourth schema is tracking `liquibase` only.
- Canopy **AD-9**: exactly `{public, langflow_schema, dbgpt_schema, liquibase}`; `run_state` and `mcp_handles` are tables in `public`; fifth schema or promoting those tables to schemas is review-blocking.
- Structural mermaid: `PostgreSQL — four schemas` with `public — Django + run_state + mcp_handles`. Diagram and Rule agree.

DDL-producer conflict (Liquibase vs Django `RunSQL`) remains the model write-up; cardinality is no longer mermaid-only.

### H3 — RFC-1 two HTTP pools vs parent AD-4 — **closed**

- Inherited parent AD-4: CAP-11 independent scale is Celery workers, not a second web Deployment (canopy AD-10).
- **Conflict, not override — RFC-1:** two HTTP *process* pools would violate parent AD-4; bound by canopy AD-10.
- Canopy **AD-10**: one public ASGI Deployment; work scales as a Celery worker Deployment on redis-broker; no second web Deployment, FastAPI process, or extra public port; HTMX and MCP share the one ASGI process; work over ~30s uses canopy AD-6 `start`/`get`.
- Resilience **RFC-1** row REVISED to the same topology; FastAPI seam stays in-host.
- CAP-4 and CAP-11 map rows cite canopy AD-10.

One epic cannot add a streaming HTTP pool while another stays parent-shaped.

### H4 — CAP-7 Vizro vs secure-dashboard pattern — **closed**

- New canopy **AD-20**: boards go through `pyforge.steward.dashboard` (`filter_by_role` / `AccessDeclaration`); isolation is that library's; a second stack including Vizro/Dash that filters rows itself is review-blocking; pattern binds at ASGI (secure-dashboard parent AD-8); atlas's own Vizro CLI pages stay outside the host (non-goal).
- Capability map: CAP-7 governed by canopy AD-20.

Map-only coverage is gone. Mechanism is not re-derived per story.

### H5 — CAP-12 secrets vs parent AD-12 — **closed**

- New canopy **AD-19**: CAP-12 authorization is IdP-on-request (canopy AD-15); delivery is parent AD-12 env/`secretKeyRef`/secret volume; success test is rendered Helm/Kustomize contains names and keys, never secret *values*; cluster manager may materialize K8s Secrets *outside* the platform image and is out of this chain; Vault-in-app / injector / CSI / extra secrets sidecar requires a dated Dream entry first.
- Inherited parent AD-12 row points at canopy AD-19.
- Map: CAP-12 → canopy AD-19, AD-15.

Comment-only interpretation is now a Rule with Prevents. Spec *intent* still says “from a secret manager rather than the pod environment”; the spine binds the spec *success* criterion (no long-lived **value** in the pod spec) to parent AD-12. That is an explicit ratification, not a silent override. Spec-intent wording is hygiene for a SPEC reconcile, not an epic fork.

---

## Re-verdict of previous mediums

| ID | Previous | Now | Verdict |
|---|---|---|---|
| M1 | AD-7 “same assertion” unsigned | RS256 JWT; claim set (`sub`/`roles`/`aud`/`exp`/`delegated_by`); HMAC rejected; golden test vector; Keycloak Token Exchange Deferred; Keycloak `26.4.0` in Stack; RFC-3 companion REVISED | **closed** |
| M2 | CloudEvents names Deferred while RFC-4 bound | AD-8 binds `pyforge.events` / `pyforge.events.dlq` / `XAUTOCLAIM` / `pyforgeloopdepth` ceiling **8**; RFC-4 colon form and HTTP header superseded in companion; Deferred is *additional* extensions only | **closed** |
| M3 | Child AD-1..17 collide with parent IDs | Consistency Conventions + Inherited intro: cite `parent AD-n` vs `canopy AD-n`; bare `AD-n` is review-blocking | **closed** (see L3 duplicate table) |
| M4 | Celery/Channels/allauth/storage unpinned | Celery `==5.5.3`, Channels `>=4.3.2,<5.0`, allauth `==65.10.0`, gunicorn, django-celery-beat, Keycloak, django-storages with filesystem backend called out | **closed**; HTMX 2.x still “pin at the story” (L4) |
| M5 | CAP-10 tests without BS-5/7/8 mechanisms | Map: AD-15 + BS-5/BS-7/BS-8 Deferred with first-story revisits; BS-8 blocked off MinIO | **closed** |
| M6 | FILE mount + Liquibase lock silent | AD-11: ConfigMap read-only; CLI same bytes; local-dev `src/platform/config/flags.json`; Deferred: env promotion overlays + `DATABASECHANGELOGLOCK` runbook with revisits | **closed** |

---

## Checklist score (this pass)

| Check | Result |
|---|---|
| Fixes real divergence points for epics/stories; misses none | **Pass with flag** — H1–H5 forks are bound. Remaining miss is CAP-13 *refresh without redeploy* (M7), not a whole-spine hole |
| Every AD Rule is enforceable and prevents its stated divergence | **Pass** — AD-7/8/9/10/13/19/20 are now testable. AD-11 enforces one tree + ConfigMap + no sidecar; it does not yet enforce “no redeploy” |
| Nothing under Deferred lets two units diverge without revisit | **Pass** — every row has a revisit. Parallel first-stories on BS-5/7/8 still need the revisit to serialize; that is the Deferred contract |
| Named tech version-pinned in Stack | **Pass with flag** — core runtime pinned; OpenFeature absent-until-feedstocks OK; HTMX 2.x story-level (L4) |
| Ratifies brownfield (`src/platform/` Django host; parent AD-1..17) | **Pass** — paradigm, import rule, one ASGI, Celery-only async, conda consume, Liquibase same image, RWX instead of object store, secrets-at-boundary. Conflicts for parent AD-1, AD-4/RFC-1, AD-5 (producer *and* cardinality), RFC-3 HMAC are written. Parent AD-6 PVC-for-media is in the inherited row + AD-13, not a full conflict paragraph (L5) |
| Covers spec CAP-1..17 | **Pass** — every CAP has governing canopy AD(s) or named Deferred. CAP-13 success “no redeploy” is the weak Rule (M7) |
| No new AD weakens/contradicts an inherited parent AD without a conflict record | **Pass** — four-schema amendment, RFC-1 topology, object-store refusal, secrets delivery all surfaced. AD-8 ceiling 8 vs original RFC-4 5 is companion-revised, not a parent-AD clash |
| Every dimension this feature owns is decided, deferred, or an open question — especially deploy/env/ops | **Pass with flag** — Helm Job, Redis split, RWX PVC, flag ConfigMap, lock runbook Deferred, env overlays Deferred. Flag *hot-reload vs rollout* is the leftover ops fork (M7) |

---

## What holds (do not reopen)

- Paradigm: one Django/ASGI process at `src/platform/`; factory packages consumed; `pyforge.*` never imported under the host. Canopy AD-5 still forbids Dream `services/` + eight FastAPI ports.
- Parent AD-5 isolation / `search_path` / ORM-never-crosses; only SQL producer + tracking-schema count change, both conflict-recorded.
- Parent AD-1 Redis kind-count: two Deployments, still Redis; cache≠broker is canopy AD-10 with a testable eviction Rule.
- Canopy AD-16: CAP-9/13 block on channel packages; recipe authoring out of spine.
- `mcp` SDK + dual-era + `start`/`get` over PostgreSQL; Wagtail Celery `BaseTaskBackend`.
- `lane1-serves-dw-h3` Deferred jointly with atlas — matches SPEC’s remaining open question.
- New canopy AD-18 (portal projections vs station-package writer) is a real CAP-3/4/5 fork-stopper; keep it.
- Citation prefix `parent` vs `canopy` is load-bearing for epics — keep enforcing it.

---

## Findings (this pass)

### H1–H5 — **closed** (see re-verdict). No new high that would split epics.

### M7 — CAP-13 “no redeploy” is not in canopy AD-11

- **Severity:** medium
- **Location:** SPEC CAP-13 success; canopy AD-11; Deferred “FILE flag env promotion overlays”
- **Trigger:** Spec success is one flag change across Django / service / CLI with **no egress and no redeploy**. AD-11 binds one JSON tree, ConfigMap mount, in-process FILE, no flagd sidecar. Overlay *values* per env are Deferred. How a ConfigMap update becomes live in the process (FILE provider watch vs Deployment rollout vs Reloader) is unbound.
- **Why it matters:** two CAP-13 stories can still ship “edit ConfigMap and roll pods” (contradicts success) vs inotify/watch vs a Reloader sidecar (parent AD-14). Env-promotion Deferred does not cover this.
- **Disposition:** defer with revisit = first CAP-13 import story: “in-process FILE provider observes the mounted file (or equivalent) without a new process; Reloader/flagd sidecar is parent AD-14.” Do not invent a daemon.

### L3 — Consistency Conventions table is duplicated

- **Severity:** low
- **Location:** Consistency Conventions — identical rows appear twice with a stray `\|---\|---\|` mid-table
- **Disposition:** autofix — one table. Citation Rule above the table is fine.

### L4 — HTMX still “pin at the story”

- **Severity:** low
- **Location:** Stack — HTMX **2.x** via `django-htmx`, not 4 (beta); “Pin at the story; not in pixi today”
- **Disposition:** ignore for packaging; first chrome/HTMX story pins `django-htmx`. Naming 2.x vs 4 already prevents the real fork.

### L5 — Parent AD-6 media PVC is ratified in the inherited row, not a full conflict block

- **Severity:** low
- **Location:** Inherited AD-6 (“Wagtail media leaves ephemeral pod disk (RWX)”); conflict blocks exist for AD-1/AD-4/AD-5/RFC-3 only
- **Note:** Parent AD-6’s letter is “all state in PostgreSQL or Redis.” RWX is the same *kind* of exception as the dated dbgpt SQLite PVC. Canopy AD-13 + parent AD-1 conflict already prevent the dangerous reading (pod-local disk or MinIO). Optional: add a one-line “Conflict, not override — parent AD-6” that disposable pods still hold; shared RWX is the replica-safe store. Not required before epics.

### L6 — SPEC CAP-12 intent vs success (spec hygiene)

- **Severity:** low (spec, not spine)
- **Note:** Intent still says secrets from a manager rather than the pod environment; success and canopy AD-19 bind values-vs-refs. Same class as previous L2. Flag for SPEC reconcile; do not reopen H5.

---

## Capability coverage (CAP-1..17)

| CAP | Governing AD(s) | Rubric |
|---|---|---|
| CAP-1 chrome | canopy 1, 3 | Covered |
| CAP-2 Lane 1 | canopy 13, 10; Deferred `lane1-serves-dw-h3` | Covered (H1 closed) |
| CAP-3 portals | canopy 1, 2, 4, 18 | Covered |
| CAP-4 MCP | canopy 5, 6, 12, 10 | Covered (H3 closed) |
| CAP-5 CLI | canopy 14, 18 | Covered |
| CAP-6 identity client | canopy 7; Keycloak TE Deferred | Covered (M1 closed) |
| CAP-7 boards | canopy 20 | Covered (H4 closed) |
| CAP-8 events | canopy 8, 10 | Covered (M2 closed) |
| CAP-9 DDL | canopy 9, 16; lock runbook Deferred | Covered (H2 closed) |
| CAP-10 containment | canopy 15; BS-5/7/8 Deferred | Covered (M5 closed) |
| CAP-11 cache≠broker | canopy 10 | Covered (H3 closed) |
| CAP-12 IdP + secrets | canopy 19, 15 | Covered (H5 closed) |
| CAP-13 flags | canopy 11, 16; overlays Deferred | Partial — **M7** refresh |
| CAP-14 Scribe | parent AD-1, parent AD-5 isolation | Adequate + Deferred internals |
| CAP-15 / CAP-16 | canopy 14, 17 | Covered |
| CAP-17 run state | canopy 12, 6; ingest Deferred | Covered |

---

## Inherited parent AD interaction (no silent override)

| Parent | This spine | Rubric |
|---|---|---|
| AD-1 PG+Redis+K8s only | Redis split OK; object store refused; RWX classified as Kubernetes | **H1 closed** |
| AD-2 no `pyforge.*` in host | Clients in `django-pyforge` / `pyforge.core` | Holds |
| AD-3 apps not services | Wagtail + portals as apps | Holds |
| AD-4 one ASGI, fixed dispatch | MCP pattern added; RFC-1 = Celery, not second web | **H3 closed** |
| AD-5 three schemas + search_path | Isolation holds; four schemas + Liquibase producer conflict-recorded; CAP-4/17 in `public` | **H2 closed** |
| AD-6 stateless | Media on RWX, not pod disk; dbgpt PVC untouched | Holds; **L5** optional conflict sentence |
| AD-7 Celery only | Explicit; django-tasks RQ forbidden | Holds |
| AD-8 py3.12 conda-space | Unchanged; Liquibase via same image | Holds |
| AD-9 consume, don’t fork | django-* / pyforge-* as conda packages | Holds |
| AD-10..17 image/chart/secrets/air-gap/sidecars/CI/local-first/engine switch | Claimed unchanged; CAP-12 delivery = parent AD-12 via canopy AD-19 | **H5 closed** |

---

## Deferred table audit

| Item | Revisit present? | Can two units still diverge? |
|---|---|---|
| `lane1-serves-dw-h3` | Yes — Phase 5 atlas + steward | No (joint course-correct) |
| Per-schema Liquibase tracking | Yes — second Job proposed | No |
| MCP Tasks | Yes — official SDK Tasks | No (wire swap) |
| FastMCP 4 | Yes — after CAP-4 mcp faces | No |
| Django 5.2.17 pin | Yes — feedstock 5.x | No; not chain scope |
| OF/Liquibase/cachebox recipes | Yes — packages on channel | No; operator-owned |
| Scribe dual-driver internals | Yes — CAP-14 story | OK if parent AD-1 holds |
| Keycloak Token Exchange | Yes — first CAP-6 delegated-token story | Acceptable |
| Additional CloudEvents extensions | Yes — first producer that needs one | No — names/ceiling bound in AD-8 |
| Supervisor ingest wire | Yes — Marshal + CAP-17 | Acceptable |
| Ledger 11.1 / 11.2 | Yes — Phase 5 steward | Acceptable |
| FILE flag env promotion overlays | Yes — first CAP-13 import | Weakly related to **M7** (overlays ≠ refresh) |
| Liquibase stuck-lock runbook | Yes — before first prod CAP-9 Job | No |
| BS-5 / BS-7 / BS-8 | Yes — first CAP-10 story per surface | OK if those first stories are not parallelized blindly |

**Missing Deferred (should exist until decided):** FILE-provider refresh without redeploy / without Reloader sidecar (**M7**).

---

## Recommended gate actions

1. **Ignore for this altitude (do not reopen):** H1–H5, M1–M6, packaging ADs, OpenFeature version until channel packages exist, L4 HTMX pin, L6 SPEC CAP-12 intent wording.
2. **Defer with revisit (one row):** M7 flag-file refresh vs rollout — first CAP-13 import story.
3. **Autofix (optional, non-blocking):** L3 duplicate conventions table; L5 one-line parent AD-6 conflict.
4. **Epics may proceed.** Cite `parent AD-n` / `canopy AD-n` in every story. Treat M7 as an AC on the first CAP-13 story if the Deferred row is not added before planning.

---

## Compact summary

**PASS-WITH-FLAGS.** **H1–H5 closed.** Leftover: **M7** CAP-13 ConfigMap/FILE refresh vs “no redeploy”; L3 duplicate conventions table. File: `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/reviews/review-rubric.md`
