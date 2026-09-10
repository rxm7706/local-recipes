---
id: SPEC-platform-object-storage-kind
spec: platform-object-storage-kind
status: ready
updated: "2026-09-10"
owner-dream: docs/dreams/platform-object-storage-kind.md
covers-dreams:
  - docs/dreams/platform-object-storage-kind.md
companions: []
sources:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/sprint-change-proposal-2026-09-10-ad-1-object-storage-exception.md
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to
> build, test, and validate. `sources:` is for traceability only — consult it for narrative
> rationale this contract intentionally omits.

# Object storage becomes consumable, without pyforge operating it

## Why

`spec-pyforge-unifying-strategy`'s own AD-1 read "infrastructure is exactly PostgreSQL + Redis +
Kubernetes" with no exception — a mandate this Spec must meet, not a pain being newly
discovered. NetApp StorageGRID (ops-provided, externally-operated S3-compatible object storage)
became real air-gap infrastructure, and nothing in the estate could point at it. AD-1's own rule
exists to stop pyforge from becoming the *operator* of a fourth infrastructure kind, not from
ever consuming one it doesn't run itself — the same distinction `canopy:AD-19` already draws for
the external IdP. Processed via `bmad-correct-course`
(`sprint-change-proposal-2026-09-10-ad-1-object-storage-exception.md`), applied 2026-09-10.

## Capabilities

- **CAP-1** — The AD-1 exception itself
  - **intent:** Object storage is permitted as a backing service when consumed via an S3 client
    only — endpoint/credentials as configuration, never a server pyforge deploys inside its own
    platform image or Helm chart.
  - **success:** `spec-pyforge-unifying-strategy/SPEC.md` carries the dated 2026-09-10 exception
    bullet under AD-1; `stack.md`'s own Never-list is qualified to match; Lane 1 media's
    2026-09-05 RWX-PVC answer is untouched. (Landed.)

- **CAP-2** — Silo is pixi-installable
  - **intent:** `pgsty/silo` (a maintained MinIO-codebase fork with real Linux/macOS/Windows
    release binaries but no conda-forge feedstock) becomes genuinely pixi-installable via a
    `conda-forge-expert`-authored recipe.
  - **success:** `recipes/silo/recipe.yaml` passes `validate_recipe` + `optimize_recipe` +
    `scan_for_vulnerabilities` + a green linux-64 `recipe-build`, and the built package is
    published to the `SelfExplainML` anaconda.org channel so `pixi install` resolves it without
    waiting on upstream `conda-forge/staged-recipes` acceptance. (Story 50.1.)

- **CAP-3** — Local-dev object storage is pixi-provisioned
  - **intent:** A real local S3-compatible server (never a mock, matching the `scripts/scribe_pg.py`
    precedent) is provisionable via pixi — Silo default, Garage alternative — selected via
    `PYFORGE_OBJECT_STORAGE_BACKEND`, mirroring `scribe_install_nightly_trigger.py`'s own
    pluggable-backend pattern.
  - **success:** A new, separate `platform-object-storage` pixi feature (not folded into
    `platform-dev`) resolves cleanly; `platform-object-storage-up`/`-down`/`-status` idempotently
    start/stop/report the selected backend; Garage on win-64 refuses cleanly rather than silently
    no-opping. (Story 50.2.)

- **CAP-4** — A proven, unconsumed client seam
  - **intent:** A minimal `src/platform/` module resolves an S3 endpoint + credentials from
    configuration only and proves a put/get round trip against the local Story-50.2 backend, so
    the exception is demonstrated end-to-end rather than only declared on paper.
  - **success:** The round-trip test passes against the local backend; no existing feature (Lane
    1 media, SBOM handling, or anything else) is wired to consume the seam in this chain.
    (Story 50.3.)

## Constraints

- Never self-host an object-store server (MinIO, Silo, Garage) inside the deployed platform
  image or Helm chart — the exception covers consumption only. A future in-cluster object-store
  deployment needs its own, separately-justified exception, not a reading of this one.
- Endpoint and credentials are configuration only, never hardcoded — mirrors `canopy:AD-19`'s
  reference-not-embed pattern. The same client code must work unmodified against the local dev
  backend or real StorageGRID.
- The local-dev pixi feature stays separate from `platform-dev`, never folded in — Garage has no
  win-64 build, and `platform-dev` inherits the full workspace platform list, so folding it in
  would break that solve outright (same reasoning as the `scribe-pg`/pgvector separation).

## Non-goals

- Migrating Lane 1 media, CycloneDX SBOM handling, or any other existing feature onto object
  storage in this chain. Lane 1 media's own RWX-PVC answer (2026-09-05) is not reopened; SBOM
  emission already has a working file-artifact answer (warden's `--sbom-output`) untouched here.
- Submitting the Silo recipe to upstream `conda-forge/staged-recipes` in this chain — the
  `SelfExplainML`-staged version satisfies this Spec's own success signal; upstream submission is
  a normal, separate follow-up.
- Provisioning real StorageGRID credentials or endpoints — an operator/ops action outside this
  repo's scope, the same boundary the IdP's own credentials already sit behind.

## Success signal

`spec-pyforge-unifying-strategy/SPEC.md` carries the dated AD-1 exception bullet (true today).
Silo resolves via `pixi install` from the `SelfExplainML` channel. `platform-object-storage-up`/
`-down`/`-status` round-trip against a real local Silo instance (and, separately, Garage). The
S3-client seam's round-trip test passes against that local backend, with no existing feature
wired to consume it.
