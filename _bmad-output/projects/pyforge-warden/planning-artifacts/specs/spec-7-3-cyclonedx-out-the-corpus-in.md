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

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `990e9ae48f` (2026-08-22, "Merge pull request #635 from rxm7706/warden/7-3-cyclonedx-out-the-corpus-in"). Ledger row `7-3-cyclonedx-out-the-corpus-in: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `src/shared/packages/pyforge-warden/src/pyforge/warden/eligibility_sbom.py`, `src/shared/packages/pyforge-warden/tests/fixtures/eligibility_corpus/MATRIX.txt`, `src/shared/packages/pyforge-warden/tests/fixtures/eligibility_corpus/NOTICE`, `src/shared/packages/pyforge-warden/tests/fixtures/eligibility_corpus/cli-tool/bom.cdx.json`, `src/shared/packages/pyforge-warden/tests/fixtures/eligibility_corpus/cli-tool/conda-lock.yml`, `src/shared/packages/pyforge-warden/tests/fixtures/eligibility_corpus/cli-tool/environment.yaml`, `src/shared/packages/pyforge-warden/tests/fixtures/eligibility_corpus/cli-tool/pixi.toml`, `src/shared/packages/pyforge-warden/tests/fixtures/eligibility_corpus/cli-tool/pyproject.toml`, `src/shared/packages/pyforge-warden/tests/fixtures/eligibility_corpus/cli-tool/requirements.txt`, `src/shared/packages/pyforge-warden/tests/fixtures/eligibility_corpus/conda-hybrid/bom.cdx.json`, `src/shared/packages/pyforge-warden/tests/fixtures/eligibility_corpus/conda-hybrid/conda-lock.yml`, `src/shared/packages/pyforge-warden/tests/fixtures/eligibility_corpus/conda-hybrid/environment.yaml` (+70 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
