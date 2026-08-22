---
spec: compliance-factory-web-face
status: ready
owner-dream: docs/dreams/compliance-factory-web-face.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/compliance-factory-web-face.md
  - ../../../../../../docs/intake/external-repos-analysis-2026-08-22/report.md
open_questions:
  - "Host: a src/platform app (reusing its Celery/auth once 15-factors lands) vs standalone — decide at 8.1; platform-app is the default lean answer."
---

# SPEC — A web face for the compliance factory

## Why
The engines exist (warden's six axes, the CycloneDX machinery, atlas
intelligence) but are CLI-only. FABRIC (Apache-2.0) proves the service
shape in production; only the face is missing here.

## Capabilities
- **CAP-1 — the service skeleton.** Manifest upload (safe-loader-only
  validation, the supported-format matrix), async Celery execution that
  CALLS warden/atlas engines, blobs kept out of brokers (keys-not-blobs).
  *Success:* an uploaded pixi.lock returns a job id and completes against
  the real engines.
- **CAP-2 — results + derived progress.** SBOM + vulnerability/license/
  currency reports rendered from engine output; progress derived from
  phase position (`_phase_guard` pattern — no phase chooses its own
  number). *Success:* progress is monotonic by construction; reports match
  the CLI engines byte-for-byte on the same input.

## Constraints
Engines stay canonical — the face never reimplements an analyzer; FABRIC
notices kept on any borrowed code; herald adjacency for UI polish, not
ownership.

## Non-goals
Multi-tenant/API-key SaaS on day one; new analysis capability; replacing
the CLI surfaces.

## Success signal
Upload → analyzed by the same engines the CLI runs → reports downloadable,
with the corpus as the demo set.
