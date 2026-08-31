---
title: "CycloneDX out, the corpus in"
type: 'feature'
created: '2026-08-22'
status: 'done'
baseline_revision: ''
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Eligibility-union results (7.2) have no CycloneDX projection, and adapters
lack a FABRIC-shaped multi-format corpus to exercise ingest without live inventory.

**Approach:** Add `render_eligibility_cyclonedx` reusing sbom.py's CycloneDX 1.6 + purl
discipline (deterministic when serial_number + timestamp are fixed), and land the
13-archetype × 6-format corpus under tests/fixtures/eligibility_corpus with NOTICE.

## Boundaries & Constraints

**Always:**
- Reuse packageurl.PackageURL; never PEP-503 dot-collapsing in purls.
- Keep FABRIC Apache-2.0 NOTICE.
- Adapters must ingest corpus without crashing.

**Never:**
- Mutate eligibility inputs during render.
- Reimplement discovery/extract for the corpus (ManifestSourceAdapter wraps existing pipeline).

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Error Handling |
|----------|-------|----------|----------------|
| Fixed serial+ts | same results twice | byte-identical JSON | N/A |
| Schema invalid | library bug | SbomValidationError | fail loud |
| Corpus matrix | MATRIX.txt | 78 files present | assert is_file |

</intent-contract>

## Code Map

- `eligibility_sbom.py` — renderer
- `tests/fixtures/eligibility_corpus/` — FABRIC-shaped stubs
- `tests/unit/test_eligibility_sbom.py`

## Tasks

- [x] Renderer
- [x] Corpus + NOTICE
- [x] Unit tests

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).
