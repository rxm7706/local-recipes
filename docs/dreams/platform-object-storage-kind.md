---
title: The estate gets an S3-compatible object store, without becoming its operator
type: dream
owner: steward
status: realized
---

# The estate gets an S3-compatible object store, without becoming its operator

## The Dream

The air-gap deployment target will have **NetApp StorageGRID** — S3-compatible
object storage — as infrastructure the operations team already runs, the same
way it already runs the Kubernetes cluster and the identity provider. Nothing in
the estate can point at it today, because `spec-pyforge-unifying-strategy`'s own
Constraint reads: *"infrastructure is exactly PostgreSQL + Redis + Kubernetes. A
component demanding a fourth backing service has failed its design review."*
`stack.md` names the obvious wrong answer explicitly: *"Never: a fourth backing
service (Vault-in-pod, MinIO, extra bus)."*

That line was written, and re-affirmed once already
(`sprint-change-proposal-2026-09-05-ad-1-reopen.md`, for Lane 1 media
specifically — a Kubernetes RWX PVC covered that case, no exception needed), to
stop the estate from becoming the **operator** of a fourth kind of
infrastructure it would have to run, patch, and reason about itself. Both
examples it names — Vault-in-pod, self-hosted MinIO — are things pyforge would
deploy and manage inside its own Helm chart.

StorageGRID isn't that. It's **ops-provided and externally operated** — pyforge
would only ever hold an S3 endpoint URL and credentials, the same shape the
estate already trusts for the identity provider (`canopy:AD-19`: *"pod specs
carry secret references only; no Vault HTTP from the platform image. Cluster
ESO/Vault stays outside the image"*). Consuming an externally-operated service
via a client library was never what the "fourth kind" rule was written to
forbid — self-hosting one was.

**What this Dream asks for:** a bounded, dated exception under AD-1 — object
storage specifically, consumed via an S3 client only, credentials and endpoint
taken as configuration never hard-coded, never a service pyforge deploys inside
its own platform image or Helm chart. Not a reopening of Lane 1 media's own
settled RWX-PVC answer, and not a licence for any other new backing service —
this is scoped to exactly the one kind, exactly the one consumption pattern.

**The local-dev half.** Nobody develops or tests against production
StorageGRID. This session verified, live, two real pixi-installable
candidates for a local equivalent:

- **Silo** (`pgsty/silo`) — a maintained fork of the actual MinIO codebase
  (same S3/IAM API surface, same on-disk format, same `MINIO_*` env vars),
  born because upstream MinIO gutted its own community edition in 2026.
  Real release binaries for Linux, macOS, **and Windows** (confirmed against
  live GitHub release assets: `darwin_amd64`/`darwin_arm64`,
  `linux_amd64`/`linux_arm64`, `windows_amd64`/`windows_arm64`). No
  conda-forge feedstock exists for it yet — this repo, being a conda-forge
  recipe factory, is positioned to author one.
- **Garage** — a real, from-scratch S3-compatible object store, already on
  conda-forge today (confirmed via live feedstock lookup), but Linux/macOS
  only (no Windows build, upstream or packaged) and a deliberately narrower
  S3 API surface than Silo/MinIO's.

Silo is the better long-term fit — full three-OS coverage, closer API fidelity
to what real StorageGRID behavior looks like — at the cost of needing a recipe
authored first. Garage works today with zero extra packaging work, at the cost
of no Windows story and a narrower feature set. The Dream asks for **both**,
pluggable, Silo as default once its recipe exists — the same default-plus-
alternatives shape this session already built for scribe's nightly-trigger
installer (`PYFORGE_SCRIBE_TRIGGER_BACKEND`), reused here rather than invented
fresh.

## Non-goals

- Not migrating Lane 1 media, or any other feature, onto object storage in
  this pass. That stays on its own settled RWX-PVC answer unless a separate,
  later Dream/story reopens that specific question with its own justification.
- Not self-hosting MinIO, Silo, or Garage inside the deployed platform image
  or Helm chart, in production. Production consumes StorageGRID as an
  external endpoint only.
- Not a general-purpose "add any infra we feel like" precedent. This Dream is
  scoped to object storage specifically, with its own stated justification
  (ops-provided, externally operated, consumed via client) — it does not
  loosen AD-1 for anything else.

## Realization log

- **2026-09-10** — Dream seeded from a live conversation investigating where
  media and CycloneDX SBOMs are stored under the current infra-kinds lock.
  Both turned out to already have working, non-object-storage answers (Lane 1
  media: RWX PVC, re-affirmed 2026-09-05; CycloneDX SBOMs: warden emits them
  as a plain `--sbom-output` file artifact, never touching the platform's own
  storage boundary) — but the real driver surfaced during that same
  conversation: NetApp StorageGRID will exist as ops-provided air-gap
  infrastructure, and nothing in the estate can consume it yet. Garage and
  Silo were both verified live (conda-forge feedstock lookup for Garage; real
  GitHub release assets for Silo) as the two pixi-installable local-dev
  candidates, with Silo chosen as the intended default given its fuller
  three-OS coverage and closer MinIO/StorageGRID API fidelity, Garage kept as
  the pluggable alternative. Next: `bmad-correct-course` against this Dream to
  process the AD-1 exception formally, matching the 2026-09-05 precedent's own
  procedure exactly, then decompose the implementation (Silo conda-forge
  recipe, local pixi tooling, a minimal S3-client seam) into stories.
- **2026-09-10 (later, same session)** — processed via `bmad-correct-course`
  (`sprint-change-proposal-2026-09-10-ad-1-object-storage-exception.md`). AD-1
  gained the dated consumed-not-self-hosted exception in
  `spec-pyforge-unifying-strategy/SPEC.md` (and `stack.md`'s own "Never" line
  qualified to match); decomposed into steward **Epic 50** (Stories 50.1-50.3):
  the Silo conda-forge recipe, local-dev pixi tooling (Silo default / Garage
  alternative), and a minimal S3-client seam. Status: `pitched` → `specified`.
- **2026-09-10 (later still, same session)** — Epic 50 drained 3/3. Story 50.1:
  `recipes/silo/recipe.yaml` authored, all four CFE gates green locally,
  published to `https://anaconda.org/SelfExplainML/silo` (`local-recipes#1183`).
  Story 50.2: the standalone `platform-object-storage` pixi feature +
  `scripts/platform_object_storage.py`, both backends' up/down/status verified
  live (idempotent, real S3 traffic, Garage's clean Windows refusal exercised)
  (`local-recipes#1184`). Story 50.3: `src/platform/config/object_storage.py` +
  a real round-trip test against an ephemeral local Silo, `platform-ci-local
  -- --test` full green (`local-recipes#1185`). All four capabilities in
  `spec-platform-object-storage-kind/SPEC.md` carry `verified:` lines; the
  Spec and this Dream both close as `shipped`/`realized`. Status: `specified`
  → `realized`.
