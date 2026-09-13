---
id: SPEC-library-catalog-manifest-sync
spec: library-catalog-manifest-sync
status: shipped
created: "2026-09-12"
updated: "2026-09-12"
owner-dream: docs/dreams/library-catalog-manifest-sync.md
companions: []
surface:
  - pixi.toml
  - environment.yaml
  - docs/reference/library-llms-full.md
  - scripts/llms_full_check.py
sources:
  - ../../../../../../docs/dreams/library-catalog-manifest-sync.md
open_questions: []
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to
> build, test, and validate. `docs/dreams/library-catalog-manifest-sync.md` is listed in
> `sources:` for narrative rationale this contract intentionally omits.
>
> **Binds, never re-mints.** `spec-pyforge-unifying-strategy` (steward) is where the gap was
> found and recorded (Realization log, "Manifest-sync gap found," 2026-09-12); `regenerable-factory`
> is the two-layer detector/reconciler pattern this closes a blind spot in. This Spec mints only
> what neither covers: the concrete pixi.toml/catalog fix and the detector extension.

# The library catalog can't see a station's own build manifest

## Why

A pain to solve, found while auditing `library-llms-full.md`'s own scope (operator-directed,
2026-09-12): every `pyforge-*` station has a second dependency manifest — its own
`src/shared/packages/pyforge-<station>/pixi.toml` `[package.run-dependencies]` table, the one
`pixi-build-python` actually builds the station's conda package from — that root `pixi.toml`,
`docs/reference/library-llms-full.md`, and `scripts/llms_full_check.py` have zero visibility
into, since all three only ever read root `pixi.toml`. Cross-checking all ten stations' own
run-deps against root `pixi.toml`'s active-dependency set surfaced seven libraries that are
real, directly-imported, already-shipped station code — confirmed importable live in each
station's own pixi env today — yet undocumented and absent from root `pixi.toml` entirely. This
is the same "shipped but not in effect" pattern `spec-pyforge-unifying-strategy` already tracks
(§ *Where next* / Epic 49), applied to the dependency-truth surface itself.

## Capabilities

- **CAP-1**
  - **intent:** Root `pixi.toml` and `docs/reference/library-llms-full.md` document the seven
    libraries every affected station's own nested manifest already declares and its source
    already imports directly: `packaging` (marshal, mason, warden), `jsonschema` (doctor,
    marshal, warden), `psutil` (marshal), `attrs` (atlas), `packageurl-python` — imports as
    `packageurl` (warden), `license-expression` — imports as `license_expression` (warden).
  - **success:** `pixi run -e local-recipes llms-full-check` exits 0; each of the seven appears
    as a versioned floor (`>=` its conda-resolved version: `packaging` 26.3, `jsonschema` 4.26.0,
    `psutil` 7.2.2, `attrs` 26.1.0, `packageurl-python` 0.17.6, `license-expression` 30.4.4) in
    both root `pixi.toml` — `[feature.local-recipes.dependencies]` plus each owning station's own
    `[feature.pyforge-<station>.dependencies]` block — and the catalog; `environment.yaml`
    regenerated if the `build` env's closure changed; the catalog's existing `pydantic` note is
    sharpened to also name pyforge-atlas's and pyforge-scribe's direct declarations (not a new
    pin — `pydantic` already resolves and is already documented).

- **CAP-2**
  - **intent:** `scripts/llms_full_check.py`'s dependency walk also covers every
    `src/shared/packages/pyforge-*/pixi.toml`'s `[package.run-dependencies]` table, merged into
    the same active-dependency set the root-`pixi.toml` walk already builds, so a station
    declaring a real run-dep in its own manifest without mirroring or documenting it fails the
    check the same way an undocumented root-`pixi.toml` dep does today.
  - **success:** A synthetic station-manifest entry that is not mirrored in root `pixi.toml` or
    documented in the catalog is caught as `undocumented-dep` by `llms-full-check` (exercised by
    a unit/meta test covering the new code path); the existing exit-code contract (0 clean / 1
    drift / 2 missing input) and the "commented-out deps are out of scope" rule hold unchanged
    for both the pre-existing root-`pixi.toml`-only checks and the new station-manifest checks.

## Constraints

- Floors are the versions `pixi.lock` already resolves today (`packaging` 26.3, `jsonschema`
  4.26.0, `psutil` 7.2.2, `attrs` 26.1.0, `packageurl-python` 0.17.6, `license-expression`
  30.4.4) — never invented, never bumped to a newer upstream release as part of this fix.
- The detector's CLI contract is frozen: `pixi run -e local-recipes llms-full-check` invocation,
  the `--json` flag, and exit codes 0/1/2 do not change shape; only the manifests
  `manifest_deps()` reads grows.

## Non-goals

- Not a station library-adoption decision. The aspirational "should station X bind library Y"
  items in `spec-pyforge-unifying-strategy`'s "Estate leverage — installed, bind now" table
  (the kedro/vizro/openlineage/etc. matrix, and `filelock`'s marshal/scribe extension) are a
  separate, already-tracked, forward-looking question and stay untouched here.
- Not a new manifest or convention. The nested `pixi.toml [package.run-dependencies]` tables
  already exist and are already the real source of a station's conda run-deps
  (`tests/meta/test_manifest_sync.py` already enforces their sync with each station's own
  `pyproject.toml`); this Spec only teaches the detector to read what already exists.

## Success signal

A future station-manifest drift — a new run-dep declared in a station's own nested `pixi.toml`
but never mirrored in root `pixi.toml` or documented in the catalog — is caught by the very next
`llms-full-check` run, with no further manual cross-check audit required to find it.
