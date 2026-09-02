---
title: "Convergence — pyforge-unifying-strategy"
chain: "pyforge-unifying-strategy"
created: "2026-08-24"
updated: "2026-08-26"
status: "shipped"
---

# Convergence — what is already covered, and by what

Companion to `SPEC.md` (spec-pyforge-unifying-strategy). Computed against `main` @ `73291bd299`,
2026-08-24, per the repo's standing check-convergence-before-new-FR rule. Downstream reads this
to know which capabilities NOT to re-mint, which of the Dream's factual premises are wrong, and
which adjacent items this Spec deliberately does not absorb.

**This pass is also the chain's scoping instrument.** The Dream was written as though the Canopy
were greenfield; the audit found the host shipped. Per the operator decisions of 2026-08-24
(Dream § Realization log), the chain is an **extension binding `spec-python-agent-platform` as
prior art** — it mints nothing that duplicates **`pap:CAP-1`..`pap:CAP-6`** (parent file
headings CAP-1..6) — and within that boundary decomposition
is exhaustive. Unifying Strategy `CAP-1`..`CAP-19` are a different set.

## Already covered — do not re-mint

| Dream surface | Covered by | Evidence |
|---|---|---|
| The Django host itself, rendered from the accelerator shape | `pap:CAP-1`; steward Story 10.1 (ledger `done`) | `src/platform/` is live: `manage.py`, `config/settings/base.py`, `platformapp/{users,templates,static,contrib}`. Import rule enforced — no `pyforge.*` under `src/platform/`. |
| Identity / OIDC SSO | `pap:CAP-1` + steward Story 16.5 (`done`) | `django-allauth` with `allauth.socialaccount.providers.openid_connect` in `INSTALLED_APPS`; no second auth framework, no local passwords. |
| Langflow as a pluggable app on an isolated schema | `pap:CAP-2`; Story 11.1 (`done`) | `src/platform/langflow_integration/` with `asgi.py` dispatcher; `RunSQL` migration provisions `langflow_schema`; `search_path` carried on the connection string. **See RFC-5 conflict below.** |
| DB-GPT as a pluggable app on an isolated schema | `pap:CAP-3` + `pap:AD-6`/`pap:AD-17` (Pattern B deviation, 2026-08-21); Story 11.2 (`done`) | `src/platform/dbgpt_integration/`; data migration provisions `dbgpt_schema`; Django ORM never crosses in. **See RFC-5 conflict below.** |
| Async work never blocking Django | `pap:CAP-4`; Story 11.3 (`done`) | Celery + Redis broker wired in `config/settings/base.py`. |
| One factory-sourced environment | `pap:CAP-5`; Story 10.2 (`done`) | `[feature.python-agent-platform]` pixi env pinning `python = "3.12.*"`, env-scoped. **Env id stays; not a Foundry rename.** |
| Air-gap parity as a failing check | `pap:CAP-6`; Story 12.3 (`done`) | Egress-blocked build+deploy is a CI gate, not a warning. |
| Vanilla Helm chart + OCP overlay, GKE portability, hardened Redis | `pap:CAP-1`/`pap:CAP-6`; Stories 12.1, 12.2, 12.6, 12.9 (all `done`) | `src/platform/deploy/charts/platform/`; image passes `restricted-v2` (arbitrary UID, no root). |
| The 15-factor baseline | `spec-platform-fifteen-factors` CAP-1..5; steward Epic 16 (`done`) | Pixi as sole dependency authority, two-stage startup validation, structlog + OTel, policy-as-test-suite. |
| Health probes for K8s | Story 10.1 + 11.1 (`done`) | `src/platform/config/fastapi_app.py` → `GET /api/health`; `/ht/` via `django-health-check`; probes wired in `deploy/charts/platform/templates/platform-deployment.yaml`. |
| Station portals | warden 8-1/8-2 then canopy Epic 19 (`done`) | Eight Lane-2 shells under `/stations/<name>/`; warden left `/compliance/` as a permanent redirect. |
| A role-isolated live-dashboard pattern | `spec-secure-live-dashboards`; steward Epic 9 (`9-1`..`9-7` all `done`) | `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/` — middleware, cache, filtering, export, audit trail. **Built, but never adopted — see residual.** |
| An MCP server, proving the pattern | atlas (shipped) | `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/server.py` `build_server()`. MCP is not greenfield; the residual is per-station reach, not the mechanism. |
| Shared stdlib primitives for the estate | `spec-pyforge-core` CAP-1..7; marshal Epic 14 (`done`); canopy 18.3 | `pyforge.core` ships `atomic_write`, `errors`, `verdict`, `report`, `process`, `landing_evidence`, hooks. Trusted client is CAP-6 / Story 18.3 — do not re-mint. |
| All-stations-in-one-image delivery | `unified-container` (dream `realized`); steward Epic 7 (`done`) | The Dream's "Mode A single all-in-one container" is this, already shipped. |

## Corrections — the Dream asserts things that are not true of this repo

Recorded here because acceptance criteria must not be written against a false premise.

1. **Lane 1 / the Guildhall is Marshal's, not Herald's.** Herald's own Spec makes this an explicit
   non-goal: *"Owning the console. The Guildhall is Marshal's ([[factory-console]]); Herald
   supplies its conviction and its look, not its machinery"*
   (`specs/spec-pyforge-herald/SPEC.md:137`). The live Guildhall is Marshal's static
   `docs/dashboard/` (`spec-factory-console`, `shipped`). Herald's own web surface is a shipped
   **React + Vite** app at `src/shared/packages/pyforge-herald/web/` (Epic 7 `done`) — not a CMS.
   Any Wagtail Lane 1 work therefore lands against **Marshal's** console ownership.
   **Resolved 2026-08-24: supersede.** CAP-2 retires the console rather than coexisting with it, so
   the handoff is a migration with a parity gate, and `spec-factory-console` is corrected in this
   chain's Phase 5. Herald's non-goal is unaffected — it never owned the console — and Herald's
   React web surface is out of scope entirely, being the Moments UI rather than Lane 1.
2. **Scribe is not SQLite.** BS-1 mandates a dual-driver engine on the premise that "local
   development uses SQLite". Scribe actually ships `FlatFileGraphStore` — a single JSON file at
   `.claude/data/pyforge-scribe/graph.json` (`graph_store.py`, Story 2-1 `done`). There is no
   SQLite driver to keep and no B-tree to corrupt; BS-1's remediation must be rewritten as
   "flat-file → PostgreSQL/pgvector", and its stated failure mode re-derived.
3. **Scribe's `recall` is lexical, not semantic.** `recall.py` is deterministic token overlap.
   The Dream's "semantic search" is a new capability, not a backend swap.
4. **FastAPI is not absent, it is in-host.** `src/platform/config/fastapi_app.py` is a real
   mounted sub-app. RFC-1's worker-pool split therefore modifies an existing seam rather than
   introducing FastAPI.
5. **`pyforge-atlas` already has MCP.** The Dream treats the MCP tier as uniformly unbuilt; atlas
   ships `build_server()`. The residual is the other seven stations plus the SSE transport.
6. **Wagtail is not absent from the estate — and this pass said it was.** Correction to this
   file's own residual item 1, found 2026-08-24. Atlas owns the Dream
   `docs/dreams/wagtail-corporate-brain.md` (`status: specified`) and the Spec
   `spec-wagtail-corporate-brain` (CAP-1..3), and Epic 16 stories 16.1/16.2 are **`done`**:
   `pyforge/atlas/factory/lasuite.py` ships `LaSuiteConfig`, `resolve_lasuite_config`,
   `LaSuiteClient` (create/update/get/list over a Wagtail REST shape) and `WikiSyncer`, plus
   `tools/lasuite_bringup.py`. The original claim was true of `src/platform/` and was wrongly
   generalised to the repo; the grep that produced it dismissed every `wagtail` hit outside
   `src/platform/` as warden test-corpus fixtures, and atlas's client did not match on that term.
   **2026-08-25:** CAP-2 Wagtail *is* mounted on the host (Epic 20). **`lane1-serves-dw-h3` is
   answered no:** host `/cms/` is not `LaSuiteClient`'s `/api/v1/documents/` contract. DW-H3
   remains atlas attended bring-up. This chain does not absorb `spec-wagtail-corporate-brain`.

## The RFC-5 conflict (operator-accepted, recorded here in full)

RFC-5 requires that Liquibase govern all PostgreSQL DDL estate-wide and that application
frameworks be *"strictly prohibited from generating runtime DDL alterations."*

Two **shipped, `done`** stories do exactly what it prohibits:

- **Story 11.1** provisions `langflow_schema` with a Django `RunSQL` migration.
- **Story 11.2** provisions `dbgpt_schema` with a Django data migration.

RFC-5 was accepted **as written** on 2026-08-24 and then **revised the same day**, once Phase-2
research established the literal directive is not implementable: `post_migrate` is the only
supported mechanism populating `django_content_type`, `auth_permission` and `django_site`, and
`create_test_db` builds every test database by running `migrate`. Either reopens both stories
regardless. `bmad-correct-course` decides the ledger shape (new superseding epic vs. reopening
Epic 11). `resilience-invariants.md` carries the binding form; the two questions below are settled
there rather than left to inherit:

- **Django's own built-in apps** (`auth`, `sessions`, `contenttypes`, `admin`, `allauth`) generate
  DDL through `django_migrations`. The revision resolves this by moving enforcement off the
  framework and onto the **database role** — the app role is DML-only and a separate migration role
  holds DDL — so the question stops being "which apps are carved out" and becomes "which role runs
  what", which an auditor can actually verify. **Test databases are carved out entirely.**
- **Ordering — and the seam already exists.** The revision puts `liquibase update` in a Helm
  **pre-upgrade Job**, explicitly *not* an init container. `migrate-job.yaml` is shipped and is
  exactly that hook (`helm.sh/hook: post-install,pre-upgrade`, `hook-weight: "0"`), so CAP-9 adds a
  Job at weight `-1` and changes this one's args from `migrate --noinput` to `migrate --fake`.
  Story 12.1's chart contract stays intact; the risk that this was a chart rewrite is retired.
  Its header independently rejects init containers for a *different* reason than Phase-2 research
  did — `helm install --wait` deadlocks migration-gated readiness, versus N replicas contending on
  `DATABASECHANGELOGLOCK` — two unrelated arguments reaching the same answer.
- **Delivery vehicle.** The Job runs the **platform image** and takes its command as `args`, so a
  conda-packaged Liquibase needs no new image at all. See
  `research/technical-pyforge-unifying-strategy-airgap-delivery-2026-08-24.md`; the policy question
  underneath it is answered, the scope commitment is not yet made.

**Also already covered, found 2026-08-24:** the **Helm pre-upgrade hook seam** itself
(`src/platform/deploy/charts/platform/templates/migrate-job.yaml`, Story 12.1 `done`) and the
**internal-registry image relocation seam** (`image.registry` + `imagePullSecrets` in
`values.yaml`, `spec-python-agent-platform` CAP-6). CAP-9 consumes both rather than minting either.

## Adjacent-not-absorbed

- **Ledger rollup drift** — warden `epic-8` and `epic-7` read `backlog` while all their stories
  read `done`; mason epics 2–3 show the same shape. Pre-existing, cross-station, and not this
  chain's to fix; flagged so nobody mistakes a `backlog` rollup for remaining scope.
- **Atlas never adopted `spec-secure-live-dashboards`** despite being named its first adopter.
  `pyforge-atlas` imports nothing from `pyforge.steward.dashboard`. This chain's Lane 3 work
  *consumes* that pattern; making atlas adopt it is atlas's own story.
- **Steward Dreams without Specs** — `bmad-suite-install-class-wiring` and
  `ocp-as-a-portability-profile` both fail `dream-chain-check` today. Same station, unrelated
  chains, not absorbed.
- **Story 12-7** (live-cluster verification) **closed 2026-08-25**. Route / SCC / official
  postgres:17+redis:7 UID, Liquibase + `migrate --fake`, `/ht/` 200. See
  `spec-12-1-the-vanilla-chart-with-an-ocp-overlay-verification-2026-08-25.md`.
- **`bmad-drift-check` `pin-missing`** and 41 warnings are the pre-2026-08-24 baseline.
- **Marshal's `spec-factory-console` is absorbed as a correction, not as scope.** CAP-2 supersedes
  the console it specifies, so that spec must be retired — but the *console's own* remaining
  backlog, if any, is Marshal's and is not pulled into this chain. The correction says "superseded
  by CAP-2"; it does not adopt Marshal's open work.

## The residual this Spec binds (for cross-check)

Each line was evidence-confirmed absent on **2026-08-24**. The **2026-08-25 canopy drain** landed
the code for items 1–20 except as noted. Do not re-mint them. Steward **12-7** closed 2026-08-25
(`/ht/` 200). CRC follow-through **closed 2026-08-26** — sidecar Ready, `platform_app`
DML-only, MCP host sidecar, published `/` **200**. Isolated `mfa` sqlmigrate is the only
RFC-5 leftover. Recorded on the 12.7 verification addendum and
`sprint-change-proposal-2026-08-26-canopy-closeout.md`.

1. **Wagtail Lane 1** — **landed** (Epic 20). CodeRed stayed dropped. `lane1-serves-dw-h3`
   **answered no** (2026-08-25): La Suite Docs REST ≠ host Wagtail `/cms/`.
2. **`django-pyforge`** — **landed** (Epic 18).
3. **Eight portals + warden rename / `/compliance/` redirect** — **landed** (Epic 19).
4. **MCP faces** — **landed on host ASGI** (`POST /stations/<name>/mcp`). **Never** a repo-root
   `services/` process farm (item 4's "no `services/`" observation stays true *and* is now a
   non-goal).
5. **Identity client** — **landed** (Story 18.3); lives with chrome/`django-pyforge` +
   `pyforge.core`, not a ninth package.
6. **`pyforge` dispatch** — **landed** (Epic 22).
7. **Lane 3 row isolation** — **landed** (Epic 23) as the secure-dashboard pattern through the
   host; atlas adopting Vizro as its own board remains atlas's story.
8. **Redis Streams / CloudEvents** — **landed** (Epic 24) on redis-broker.
9–18. **RFC-1..5 / BS-1..8 path** — **landed** as steward 21/25/27/28 (RFC-1 remains Celery, not
   two HTTP processes). **RFC-5 live Job** path is in the chart; CRC applied `:17`–`:19`
   via host `liquibase update`. Isolated **`mfa` sqlmigrate** stays fake.
19. **Revoke + secret references + FILE flags** — **landed** (Epic 26). Full Keycloak Token
    Exchange / Vault agent remain caveats on BS-3, not a reason to re-build chrome.
20. **CAP-15/16/29 five-tier check** — **landed** for the 03 stations (skills + personas + gate).

## Drain bind (2026-08-25)

Peer stations drained on **one CAP-18 process-hook story** each after steward 32-1. They do not
clone Epics 18–30. Campaign engine was worktree `bmad-build-auto` under a singleton coordinator;
marshal Epic 22 verbs exist as product. Host never imports `pyforge.*`.
