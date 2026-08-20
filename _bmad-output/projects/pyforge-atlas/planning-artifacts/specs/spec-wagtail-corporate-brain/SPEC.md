---
spec: wagtail-corporate-brain
status: ready
owner-dream: docs/dreams/wagtail-corporate-brain.md
surface:
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/lasuite.py
  - src/shared/packages/pyforge-atlas/tests/factory/test_lasuite.py
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-atlas/tools/lasuite_bringup.py
  - src/shared/packages/pyforge-atlas/tests/factory/test_lasuite_live_rehearsal.py
sources:
  - ../../../../../../docs/dreams/wagtail-corporate-brain.md
# Verification-home question RESOLVED 2026-08-15 (Story 16.2): the rehearsal lives in the
# DEFAULT `kedro-test` gate, not a network-marked pytest outside it — a real httpx opener
# (`tools/lasuite_bringup.py`) driven over a loopback-only stdlib `http.server` stub stays fully
# offline, so no new pytest marker was needed. See
# `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-16-2-httpx-opener-and-rehearsal.md`.
open_questions:
  - deployment substrate — conda-forge Wagtail + django-lasuite (DW-H3's own text) vs a container
  - is DW-H1's PostgreSQL/MinIO required, or does a SQLite-backed minimal instance satisfy the contract?
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/wagtail-corporate-brain.md` is listed in
> `sources:` for narrative rationale this contract intentionally omits.

# A live server for the WikiSyncer that has been waiting to push to it — the narrow DW-H3 contract

## Why

Atlas's CMS sync is half-real. Story H3 (FR-22(c), AD-22) shipped the buildable half —
`src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/lasuite.py`: `LaSuiteClient`
(create/update/get/list over the Wagtail REST shape) + `WikiSyncer` (idempotent,
content-digest-keyed push of the Karpathy-wiki's `outputs/` report pages) — proven end-to-end
against an in-memory `MockWagtail` in `tests/factory/test_lasuite.py` with zero network.
`resolve_lasuite_config` already freezes the live contract: `LASUITE_BASE_URL` +
`LASUITE_API_TOKEN`, BOTH required, or the client degrades to unconfigured rather than push at a
half-configured endpoint. The missing half is entirely the SERVER, which the deferred-work ledger
already names: DW-H3 — "the live La Suite/Wagtail SERVER + credential + httpx opener bring-up
(ATTENDED) — DEFERRED".

Operator decision (2026-08-14, binding): **spec-first, bring-up later.** This SPEC authors the
narrow-scope contract now; the attended live bring-up is scheduled separately. Executing the
bring-up is NOT this SPEC's gate — defining what "brought up correctly" means IS, so the attended
session runs against a contract instead of improvising one. Per Charter §5's outcome/mechanism
rule, atlas owns the outcome ("the wiki reaches the Brain") and consumes Steward's
deploy/credential verbs as the mechanism.

## Capabilities

- **CAP-1**
  - **intent:** a minimal live Wagtail/La Suite instance satisfies `LaSuiteClient`'s
    already-defined REST contract — Bearer-token auth plus the four routes the client calls:
    `POST /api/v1/documents/` (a 2xx body MUST carry `id`; `WikiSyncer._created_id` hard-fails
    otherwise), `PATCH /api/v1/documents/{id}/`, `GET /api/v1/documents/{id}/`,
    `GET /api/v1/documents/all/`.
  - **success:** with `LASUITE_BASE_URL` + `LASUITE_API_TOKEN` exported, `resolve_lasuite_config()`
    returns a config and every route answers per the shapes `MockWagtail` encodes — zero
    client-side change is needed to talk to the live instance.
- **CAP-2**
  - **intent:** a real httpx-backed `Opener` replaces the mock at the module's sole network seam —
    constructed OUTSIDE package code (a bring-up script / the C1 Dagster resource), injected in
    place of `_unconfigured_opener` exactly as the seam was designed.
  - **success:** `WikiSyncer.sync_all()` runs live through that opener with ZERO edits to
    `factory/lasuite.py`; the no-inline-IO gate (`tests/catalog/test_no_inline_io.py`) stays
    green — no HTTP client entered package code (AC-2).
- **CAP-3**
  - **intent:** the round-trip + idempotency semantics `test_lasuite.py` already proves against
    the mock are defined as the live acceptance: first push CREATEs every `outputs/` page; an
    unchanged re-push makes NO remote call (all-skipped `SyncReport`); a changed page yields
    exactly ONE update and no duplicate create; a fresh syncer resumes from the persisted
    `.lasuite_sync.json` mapping without re-creating.
  - **success:** the attended session runs that four-step sequence against the real CMS and each
    step's report matches the mock-proven expectation; the ledger's DW-H3 entry flips to closed
    citing this SPEC.

## Constraints

- **Always:** endpoint + token resolve ONLY from env (AD-2) — never a hardcoded host, never a
  committed credential; a partial config still degrades to `None`.
- **Always:** package code holds no HTTP client (AC-2). `factory/lasuite.py` is a read-only
  contract surface for this work — the httpx opener, the credential, and the server all live
  outside it.
- **Always:** the outcome/mechanism split (Charter §5) — server provisioning and credential
  minting go through Steward's deploy/credential verbs; atlas grows no deploy code of its own.
- **Always:** the bring-up itself stays ATTENDED, exactly as DW-H3 frames it. This SPEC does not
  decide or schedule the bring-up date.
- **Always:** the live instance is deployable air-gapped — substrate installs resolve from
  mirrored indexes only (an Artifactory-mirrored conda channel or an internal-registry image,
  whichever way the substrate open question resolves), admin/site static assets serve locally
  with zero CDN references, and endpoint + token reach the process via env/secret-mount through
  the existing config seam (`resolve_lasuite_config`) — never a committed credential.

## Non-goals

- **Not** the broad CMS scope — the dream's second Constraint FORBIDS this SPEC silently absorbing
  it: no `wagtailsite`, no `wagtailtables`, no `wagtailcharts`, no `wagtailcolorpicker`, no
  OIDC/django-allauth RBAC, no DRF APIs. Each would need its own separate, explicit decision.
- **Not** `BokehPanelPage` — doubly contingent (the broad CMS scope AND [[atlas-query-dashboards]],
  neither decided).
- **Not** headless/API-only mode, not multi-site/multi-tenant, not a content-authoring platform
  for non-developer humans — no such audience is named in this repo.
- **Not** an execution of the bring-up — this SPEC ships as the contract the attended DW-H3
  session will later be run against.

## Success signal

This SPEC is done when it stands as the accepted contract: the attended session's definition of
"brought up correctly" is CAP-1..CAP-3's success lines, verbatim — a live instance answering the
four routes under Bearer auth, a real httpx opener injected from outside package code, and the
create / no-op re-push / single-update / mapping-resume sequence observed against the real CMS
with `factory/lasuite.py` unchanged and the no-inline-IO gate green. When that attended session
later runs and passes, DW-H3 closes citing this SPEC; until then the SPEC holds at
`draft`/`ready` — never `shipped` on paper alone.

## Open Questions

- **Deployment substrate:** DW-H3's own text names conda-forge Wagtail + django-lasuite; whether
  the minimal instance is that stack or a container is Steward's mechanism call at bring-up.
- **DW-H1 dependency:** does the minimal instance need DW-H1's PostgreSQL/MinIO, or does a
  SQLite-backed Wagtail satisfy the four-route contract for a first bring-up?

**Resolved:**

- **Verification home** (Story 16.2, 2026-08-15): the rehearsal lives in the DEFAULT `kedro-test`
  gate — a real httpx-backed opener (`src/shared/packages/pyforge-atlas/tools/lasuite_bringup.py`)
  driven over a loopback-only stdlib `http.server` stub
  (`src/shared/packages/pyforge-atlas/tests/factory/test_lasuite_live_rehearsal.py`) reproduces the
  mock-proven create / no-op re-push / single-update / mapping-resume sequence over REAL HTTP while
  staying fully offline (127.0.0.1 ephemeral port, started and torn down inside the test, no
  external network, no credentials), so no network-marked pytest outside the default gate was
  needed. DW-H3's own "Do NOT weaken the gate to import httpx into package code or bind a socket
  (AC-2 / NFR-12)" clause is not contradicted by this: it bars making the offline gate depend on a
  real network or a live CMS, `httpx` still enters no package file (the import lives under
  `tools/`, outside the no-inline-IO scan root), and this repo already binds loopback stub servers
  inside the same default gate (`tests/publish/test_emit_range.py`, `tests/wasm/test_wasm_smoke.py`)
  — recorded here so a future reader does not re-litigate the apparent contradiction. The attended
  DW-H3 checklist (Design Notes of
  `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-16-2-httpx-opener-and-rehearsal.md`)
  is additional, not a substitute — it still runs the same script against a real Wagtail/La Suite
  instance.
