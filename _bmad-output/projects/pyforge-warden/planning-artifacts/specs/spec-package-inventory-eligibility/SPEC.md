---
spec: package-inventory-eligibility
status: in-progress
owner-dream: docs/dreams/package-inventory-eligibility.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/package-inventory-eligibility.md
open_questions: []   # the required-authority question was answered in code at Story 7.2; its config half is a named residual
---

# SPEC — Every package has one provenance trail and one eligibility answer

## Why
"Can I use this package" has no single auditable answer when evidence is
scattered (allow-lists, SBOMs, manifests, telemetry) under divergent
identities. Warden answers the narrower per-project gate; this is the
estate-wide union with provenance, in the CycloneDX shape warden already
speaks.

## Capabilities
- **CAP-1 — SourceContract + identity API.** Pluggable
  fetch/parse/validate/ingest adapters (generalizing `feeds.py`'s
  fetch/cache/provenance shape) and `inventory.py`'s Component identity
  exposed as a standalone adapter-facing API (PEP-503-canonical,
  purl-derived). *Success:* two heterogeneous sources ingest without
  touching the union core; `scikit_learn`/`sklearn` collapse to one identity.
- **CAP-2 — eligibility-union + provenance.** Union over required-authority
  sources; every result carries ProvenanceEntry trails (source + timestamp);
  the new vocabulary (`eligible-union`/`observed-in-use`/
  `flagged-for-review`) stays distinct from `models.py`'s Status rungs.
  *Success:* an answer is reproducible from its own provenance alone.
- **CAP-3 — CycloneDX out + the corpus in.** Output through `sbom.py`'s
  renderer + purl discipline; FABRIC's 13-archetype × 6-format manifest
  corpus adopted as fixtures (Apache-2.0, notices kept). *Success:*
  deterministic CycloneDX; the corpus exercises every adapter.

## Constraints
Never dot-collapse purls; the per-project gate's verdicts unchanged; sibling
same-name dream is pattern reference only (unlicensed).

## Non-goals
A web face (spec-compliance-factory-web-face); auto-remediation; replacing
the curated allow-lists (they become one source class).

## Success signal
One CLI question, one CycloneDX answer, full provenance — across at least
three real source classes, fixture-proven on the corpus.

## Assumptions
- **Required-authority policy is answered in code.** `eligibility.py:113-121` defaults
  `required_authority_sources=None` to "every source name present in the full evidence
  tuple" — unanimous consensus — and the docstring at `:128-131` records the omission of a
  config surface as deliberate.
- CAP-1..3 landed as real library modules — `sources.py` (SourceContract + registry),
  `eligibility.py` (the union with ProvenanceEntry trails and the separate
  `eligible-union`/`observed-in-use`/`flagged-for-review` vocabulary) and
  `eligibility_sbom.py` (CycloneDX through the existing renderer) — with Stories 7.1–7.3
  `done` and unit-tested. The Dream's constraint that this vocabulary stay separate from
  `models.py`'s Status rungs holds, verified by reading.

## Residuals
- **There is no CLI question.** This Spec's Success signal is "One CLI question, one
  CycloneDX answer", and `grep eligib src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py`
  returns zero hits. The Spec is not shipped until warden grows the eligibility verb its
  Success signal describes.
- **The required-authority config surface is deferred, deliberately.** It is minted **only
  together with the missing CLI front door** — a settable policy no user can reach is
  unreachable, so the two belong in one story. *Rejected alternative:* mint the config story
  now, separately.
