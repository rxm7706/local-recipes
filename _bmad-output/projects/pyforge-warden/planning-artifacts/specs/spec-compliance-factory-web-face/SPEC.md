---
spec: compliance-factory-web-face
status: in-progress
owner-dream: docs/dreams/compliance-factory-web-face.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/compliance-factory-web-face.md
  - ../../../../../../docs/intake/external-repos-analysis-2026-08-22/report.md
open_questions: []   # the host question was ANSWERED BY DELIVERY at Story 8.1: a platform-mounted Django app
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

## Assumptions
- The host question is answered by delivery: `django_warden_fabric` is a
  platform-mounted Django app (registered through `_STATION_PORTAL_PACKAGES` in
  `src/platform/config/settings/base.py`; `/compliance/` 308-redirects to
  `/stations/warden/`), relocated out of `src/platform/compliance_face/` in
  `2394d850db`.

## Residuals
Stories 8.1/8.2 are `done` against their tests; **CAP-1 and CAP-2 are not yet true in the
running estate**, for two named reasons. Recorded as residuals rather than reopened stories:

- **The deployed image cannot import the engines it calls.** `tasks.py:97-102` lazy-imports
  `pyforge.warden.cli` to keep the platform host importable without `pyforge` installed
  (Story 10.1's boundary), but `pyforge-warden` is absent from
  `[feature.python-agent-platform.dependencies]` — its sole path dep is `pyforge-steward` —
  and `src/platform/Containerfile` installs that environment alone, so every uploaded
  manifest lands `FAILED` via `tasks.py:89-94`. The fix is **steward Story 48.11** (add the
  path dep, add an import test, regenerate `environment.yaml` — that sync check is ungated by
  the `maintenance` label): steward's surface, warden's capability. Until it merges, CAP-1's
  "completes against the real engines" is unmet. *Rejected alternative:* re-scope CAP-1 to
  shell out to a warden binary in a sidecar — it preserves the boundary but is a real
  architecture change for a Spec whose stories are already done, and the precedent for the
  chosen fix is already in the file.
- **The SBOM half of CAP-2 is a stub.** `_run_warden_engines` returns `sbom_json`
  unconditionally as the literal `"{}"` (`tasks.py:110-111`), persisted to
  `ComplianceJob.sbom_json` by `tasks.py:80-82`, so the field is always empty. Only the report
  half of CAP-2 is rendered. The derived-progress half *is* real and correct: `phases.py`
  computes `progress = phase_index / len(PHASES)` and callers advance only through `advance()`.
