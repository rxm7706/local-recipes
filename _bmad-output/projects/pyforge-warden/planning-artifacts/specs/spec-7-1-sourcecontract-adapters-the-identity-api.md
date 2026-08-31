---
title: 'SourceContract adapters + the identity API'
type: 'feature'
created: '2026-08-22'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: true
context: []
warnings: ['oversized']
deferred:
  - summary: >-
      SourceEvidence carries no de-duplication across multiple observations
      of the same PackageIdentity (e.g. a package seen both direct and
      transitive within one CycloneDX document, or across adapters).
    evidence: |-
      Story 7.2's union computation is the natural owner of duplicate-
      identity reconciliation (that is what a union does); Story 7.1's
      adapters intentionally emit one evidence record per observation. Flagged
      by the Blind Hunter review pass on the 2026-08-22 loopback.
    location: >-
      src/shared/packages/pyforge-warden/src/pyforge/warden/sources.py (CycloneDXSourceAdapter.ingest / ManifestSourceAdapter.ingest)
    severity: medium
  - summary: >-
      CycloneDXSourceAdapter.validate() never checks the document's
      specVersion, so an incompatible/very old CycloneDX schema version
      would be accepted and processed identically to 1.6.
    evidence: |-
      The specific fields this adapter reads (purl, name) are stable across
      CycloneDX versions in practice, so the practical risk is low; a
      stricter check needs a policy decision on which versions to accept,
      which is a value judgment beyond this story's scope. Flagged by the
      Blind Hunter review pass on the 2026-08-22 loopback.
    location: >-
      src/shared/packages/pyforge-warden/src/pyforge/warden/sources.py (CycloneDXSourceAdapter.validate)
    severity: low
baseline_revision: 'fd5c16c16aee5550fd9b18e06a64d6f127a279f1'
---

<intent-contract>

## Intent

**Problem:** Warden's per-project compliance gate has no way to ingest evidence about
package eligibility from OUTSIDE the scanned project (existing SBOMs, other manifests) —
and no standalone way to compute a canonical package identity without first constructing a
full 15-field `Component`. Epic 7 (estate-wide eligibility) needs both before its union
computation (Story 7.2) can exist.

**Approach:** Add a new `sources.py` module: a `SourceContract` Protocol
(`fetch`/`parse`/`validate`/`ingest`, mirroring `feeds.py`'s proven fetch/cache/provenance
shape) plus a registration registry (mirrors `engines.py`'s `register_engine`/
`registered_engines`), a lightweight standalone `resolve_identity()` function/`PackageIdentity`
value object (builds on `inventory.canonical_name`/`derive_purl`, adds a small curated
alias table for import-name-vs-distribution-name mismatches), and two concrete adapters:
`CycloneDXSourceAdapter` (reads an external CycloneDX JSON document) and
`ManifestSourceAdapter` (reuses `discovery.discover` + `extract.extractor_for` over a
local target — the existing per-project scan pipeline, wrapped as one evidence source).

## Boundaries & Constraints

**Always:**
- `resolve_identity` reuses `inventory.canonical_name`/`inventory.derive_purl` verbatim for
  PEP-503 normalization and purl derivation — never a second, divergent implementation.
- `ManifestSourceAdapter` reuses `discovery.discover` + `extract.extractor_for` +
  `routing.DefaultRouter` unchanged — no new manifest-parsing logic.
- Every adapter conforms to `SourceContract` (`@runtime_checkable Protocol`, matching the
  `Engine`/`Extractor`/`Router` precedent in `interfaces.py`).
- The alias table is small, curated, and documented inline (git-review-owned, mirrors
  `mapping.py`'s bundled-map discipline) — not a speculative general alias-resolution engine.
- No adapter opens a network socket (NFR-S2 precedent): both adapters in this story read
  only the local filesystem.
- `SourceEvidence`/`PackageIdentity` are new, standalone dataclasses — never fields bolted
  onto `Component` (that contract is frozen per `models.py`'s module docstring) and never a
  second identity type competing with `inventory.Component`'s own.

**Block If:** none identified — this story's scope (adapter interface + registry + identity
API + the two adapters the Dream marks "Included") is fully bounded by the epic AC and prior
art audited above.

**Never:**
- No union/eligibility computation (`eligible-union`/`observed-in-use`/`flagged-for-review`)
  — that is Story 7.2, which depends on this story's output shape but is out of scope here.
- No CycloneDX *output* — Story 7.3. This story only *reads* an external CycloneDX document.
- No `GistSourceAdapter`/`ArtifactorySourceAdapter` — the Dream marks both omitted (no
  PyForge target confirmed); only the interface must remain extensible to them later.
- Never dot-collapse a purl (G98) — `derive_purl`'s existing PEP-503 behavior is unchanged;
  this story never touches purl *rendering*, only reads/derives identity purls for evidence.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| PEP-503 variants | `resolve_identity(PYPI, "scikit_learn", "1.3.0")` and `resolve_identity(PYPI, "Scikit-Learn", "1.3.0")` | Both yield the same `PackageIdentity(canonical_name="scikit-learn", ...)` | No error |
| Curated alias | `resolve_identity(PYPI, "sklearn", "1.3.0")` | Same `PackageIdentity` as the PEP-503 variants above (alias table resolves `sklearn` -> `scikit-learn`) | No error |
| Conda name | `resolve_identity(CONDA, "typing_extensions", None)` | `canonical_name` unchanged (conda names are verbatim-canonical, per `inventory.canonical_name`); no alias lookup applied (alias table is pypi-only) | No error |
| Valid external CycloneDX doc | A JSON document with `bomFormat: "CycloneDX"` and a non-empty `components[]`, each carrying a `purl` | `CycloneDXSourceAdapter.ingest(...)` yields one `SourceEvidence` per component with a parseable purl | No error |
| Malformed CycloneDX doc | Not valid JSON, or top level not an object, or missing/non-list `components` | `validate()` returns `None`/raises a typed error; `ingest` is never called on it | Caller sees a clear validation failure, never a crash |
| Component missing a purl | A `components[]` entry with `name`/`version` but no `purl` | Skipped (tolerant-per-entry, mirrors `feeds.py`'s established convention) — never guessed | No error; entry silently excluded |
| Local manifest target | A directory with a `pyproject.toml` | `ManifestSourceAdapter.ingest(...)` yields one `SourceEvidence` per extracted `Component`, identity resolved via `resolve_identity` | No error |
| Empty/no-manifest target | A directory with nothing `discovery.discover` recognizes | `ingest` yields an empty tuple | No error (mirrors `discovery.discover`'s own empty-tuple contract) |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-warden/src/pyforge/warden/sources.py` -- NEW module: `PackageIdentity`, `resolve_identity`, `SourceEvidence`, `SourceContract` Protocol, `register_source`/`registered_sources`/`source_factories` registry, `CycloneDXSourceAdapter`, `ManifestSourceAdapter`.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/inventory.py` -- REUSE ONLY: `canonical_name(ecosystem, name)` (line ~140), `derive_purl(ecosystem, name, version)` (line ~170). Do not modify.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/models.py` -- REUSE ONLY: `Ecosystem` enum (line 119). Do not modify.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/interfaces.py` -- STYLE REFERENCE ONLY: `@runtime_checkable class Engine(Protocol)` (line 241-248) is the pattern `SourceContract` mirrors. Do not modify (Epic 7's new Protocol is scoped to `sources.py`, not the compliance-gate interface layer).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py` -- STYLE REFERENCE ONLY: `register_engine`/`registered_engines`/`engine_factories` (lines 184-215) is the registry pattern `sources.py`'s registry mirrors exactly. Do not modify.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/discovery.py` -- REUSE ONLY: `discover(target: Path) -> tuple[ScannedManifest, ...]`. Do not modify.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/extract/__init__.py` -- REUSE ONLY: `extractor_for(kind, router) -> Extractor`, `UnparsableManifestError`. Do not modify.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/routing.py` -- REUSE ONLY: `DefaultRouter` (the `Router` implementation `cli.py` constructs before extraction). Do not modify.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/sbom.py` -- PATTERN REFERENCE ONLY (lines 106-150): shows the existing CycloneDX *write* path (`render_cyclonedx`) and self-validation discipline; `CycloneDXSourceAdapter` is the mirror-image *read* path over an EXTERNAL document — no shared code, but the tolerant-JSON-load style in `feeds.py` (see below) is what `parse`/`validate` should mirror instead.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/feeds.py` -- PATTERN REFERENCE ONLY (`load_kev_catalog`, lines 194-231): the tolerant-per-entry JSON-load convention (`None` on untrustworthy read, skip malformed entries, never raise) `CycloneDXSourceAdapter.parse`/`.validate` should follow.
- `src/shared/packages/pyforge-warden/tests/unit/test_sources.py` -- NEW test file.
- `src/shared/packages/pyforge-warden/tests/conftest.py` -- REUSE ONLY: `component_factory` fixture, if useful for constructing expected `Component` shapes in adapter tests.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-warden/src/pyforge/warden/sources.py` -- create the module: `PackageIdentity` (frozen dataclass: `ecosystem`, `canonical_name`, `version`, `purl`); `_PYPI_ALIASES` (small curated dict, e.g. `sklearn -> scikit-learn`, documented as git-review-owned and extensible); `resolve_identity(ecosystem, name, version=None) -> PackageIdentity` (PEP-503-normalize via `inventory.canonical_name`, apply the alias table for pypi only, derive the purl via `inventory.derive_purl`; normalize an empty-string version to `None` in exactly ONE place -- inside this function -- rather than duplicating the check again in `PackageIdentity.__post_init__`); `SourceEvidence` (frozen dataclass: `identity`, `source_name`, `locator`, `raw_name`); `SourceContract` (`@runtime_checkable Protocol` with `name: str` + `fetch`/`parse`/`validate`/`ingest`, `ingest` taking no arguments and internally sequencing `fetch`/`parse`/`validate`); `register_source`/`source_factories`/`registered_sources` (mirrors `engines.py`'s registry exactly, including its same-factory-object idempotency guard -- document plainly, where the registry is defined, that this guard only de-dupes a reused factory REFERENCE, not a freshly-constructed closure/lambda passed on each call: a caller who wants idempotent registration must hold onto and reuse one factory object, never construct a new `lambda: Adapter(path)` per registration attempt); `CycloneDXSourceAdapter` (constructed with a `Path`; `fetch` reads the file text, returning `None` on `OSError`/`UnicodeDecodeError` (missing file, unreadable, non-utf-8); `parse` is a tolerant `json.loads` returning `None` on any untrustworthy read, mirroring `feeds.load_kev_catalog`; `validate` checks `bomFormat == "CycloneDX"` and a list `components` key, returning the component list or `None`; `ingest` builds one `SourceEvidence` per component carrying a parseable purl via `packageurl.PackageURL.from_string` -- skipping entries with no purl, an unparseable purl string, or an unrecognized purl `type`, all without ever raising); `ManifestSourceAdapter` (constructed with a target `Path`; `fetch` calls `discovery.discover`, catching `OSError` (`discovery.py`'s own documented fail-closed contract: a missing/inaccessible/replaced target, a symlinked subdirectory, or an entry-cap overrun) and degrading to an empty tuple -- mirroring `CycloneDXSourceAdapter.fetch()`'s own OSError-tolerant guard, so a bad scan target degrades to no evidence rather than crashing `ingest()`; `parse` runs `extract.extractor_for(kind, DefaultRouter()).extract(...)` per manifest, tolerating (skipping) any manifest whose extraction raises `UnparsableManifestError`, `OSError`, OR any other exception (mirror `cli.py`'s own broad `except (SystemExit, Exception)` backstop at this identical extraction call site -- one manifest's unexpected extractor bug must never crash evidence collection for the rest of the target, matching this adapter's own documented "tolerant-per-manifest" contract); `validate` is a pass-through identity check (returns the tuple of `Component`s unchanged -- always a valid, possibly-empty tuple); `ingest` wraps each `Component` via `resolve_identity` into a `SourceEvidence`).
  Build the `register_source`/`source_factories`/`registered_sources` registry mechanism fully, but do NOT self-register either shipped adapter at module import time: neither `CycloneDXSourceAdapter` nor `ManifestSourceAdapter` is zero-arg-constructible (both require a `Path` at construction, per this same paragraph), and this story names no legitimate default `Path` for either (no bundled default CycloneDX document, no default scan target) -- inventing one would be exactly the speculative behavior "Simplicity First" forbids, and would make a bare `registered_sources()` call silently inert or misleading. A later call site (Story 7.2's union computation, or CLI wiring) registers a concrete zero-arg closure once it actually knows the adapter's construction path -- e.g. `register_source(lambda: CycloneDXSourceAdapter(doc_path))` -- at THAT call site, not inside `sources.py` itself. Record this as a short "Design decision" note in the module docstring (not a footnote buried in one function) so a future reader sees it before wondering why the registry starts empty.
- `src/shared/packages/pyforge-warden/tests/unit/test_sources.py` -- unit-test the full I/O matrix above plus these review-driven additions: PEP-503 + alias collapsing to one `PackageIdentity`; conda names left verbatim; `CycloneDXSourceAdapter` over a valid fixture doc (inline JSON, `tmp_path`), asserting on every `SourceEvidence` field including `locator`; malformed-doc validation failure; a component missing a purl skipped; **a component whose `purl` value is present but fails `PackageURL.from_string` (e.g. `"not-a-purl"`) skipped, not raised**; **a component with no `name` field falling back to the purl's own name for `raw_name`**; **a component whose purl carries no version segment (e.g. `pkg:pypi/requests`, no `@version`) resolving to a `PackageIdentity` with `version=None`**; `ManifestSourceAdapter` over a `tmp_path` with a real `pyproject.toml` fixture, asserting on every `SourceEvidence` field including `locator` (parity with the CycloneDX adapter's own test); **a `tmp_path` with two manifests, one deliberately malformed (invalid TOML raising `UnparsableManifestError`) and one valid, asserting `ingest()` returns evidence for the valid manifest only and does not raise**; **a `tmp_path` whose target itself is unreadable/inaccessible (e.g. `chmod 000`, or a nonexistent path if permission tests are unreliable in CI) asserting `ingest()` degrades to `()` rather than raising**; empty-target `ManifestSourceAdapter` yields `()`; both adapters satisfy `isinstance(adapter, SourceContract)`; **a `SourceEvidence` immutability test, parity with `PackageIdentity`'s own frozen-dataclass test**; every registry test that mutates `_SOURCE_FACTORIES` -- including the one asserting the registry starts empty -- must snapshot/restore it via `monkeypatch`, matching the other registry tests' own isolation discipline (a test relying on `_SOURCE_FACTORIES` being untouched by test-execution order is not self-contained).

**Acceptance Criteria:**
- Given two heterogeneous evidence sources (an external CycloneDX document and a local manifest tree), when each is run through its adapter's `fetch`/`parse`/`validate`/`ingest` sequence, then both yield `SourceEvidence` tuples through the identical `SourceContract` interface, with no shared/union code touched by either adapter's implementation.
- Given `scikit_learn`, `Scikit-Learn`, and `sklearn` as three raw names for the same PyPI package, when each is passed to `resolve_identity`, then all three yield the same `PackageIdentity`.
- Given a new adapter is added later (e.g. an Artifactory adapter), when it implements `SourceContract` and calls `register_source`, then no change to `sources.py`'s existing adapters, `resolve_identity`, or any other module is required (structurally verified: the two shipped adapters do not reference each other, and the registry has no adapter-specific branching).

## Design Notes

`resolve_identity` deliberately does NOT construct a full `inventory.Component` — that type
carries 11 fields (`mapping_confidence`, `cve_match_level`, `provenance`, `hygiene_covered`,
...) that describe a per-project compliance SCAN, meaningless to an external evidence source
that only knows "this package, this version, from this place." `PackageIdentity` is the
Dream's `PackageIdentity` concept realized as the smallest value object that lets
`inventory.canonical_name`/`derive_purl` be reused without that unrelated baggage.

The alias table is intentionally tiny at this story's scope: it exists to satisfy the one
concrete cross-ecosystem-naming gap the epic AC names (`sklearn`/`scikit-learn`), documented
as an extensible, hand-curated seed (mirrors this codebase's existing precedent for
hand-curated tables — `mapping.py`, the LTS registry, the license map) — not a general
alias-mining engine, which is out of scope and unrequested.

## Spec Change Log

### 2026-08-22 — Review loopback 1 (bad_spec)

**Triggering finding:** The original Tasks & Acceptance text directed "Register both
adapters via `register_source` at module import time (module-level factory calls...)"
while, in the same sentence, also describing each factory as closing "over whatever
construction argument its call site supplies" — internally self-contradictory, since
neither adapter is zero-arg-constructible and this story names no legitimate default
`Path` for either. The first implementation pass caught this, built the registry
mechanism without self-registering either adapter, and recorded the deviation clearly
in the module docstring — but the spec of record still described behavior the code
didn't (and, per "Simplicity First," shouldn't) implement. Flagged independently by
the Blind Hunter and Intent Alignment Auditor review layers.

**What was amended:** The Tasks & Acceptance "Execution" bullet now states plainly
that the registry mechanism is built and fully tested WITHOUT self-registering either
shipped adapter, and explains why (no legitimate zero-arg default exists for either).
It also folds in fixes for review findings that land in this same section rather than
deferring them to a second loopback: `ManifestSourceAdapter.fetch()` must catch
`OSError` from `discovery.discover()` (mirroring `CycloneDXSourceAdapter.fetch()`'s own
guard) instead of crashing on a missing/inaccessible target; `ManifestSourceAdapter.
parse()`'s per-manifest tolerance must catch any exception, not just
`UnparsableManifestError`/`OSError` (mirroring `cli.py`'s own broad backstop at the
identical extraction call site); the version-blank-normalization duplication between
`resolve_identity` and `PackageIdentity.__post_init__` collapses to one site; the
`register_source` idempotency guard's real behavior (only de-dupes a reused factory
reference, never a fresh lambda) is now documented plainly instead of implied; and the
test list gains explicit coverage for the partial-manifest-failure path, the
malformed-purl-string skip, the `raw_name` fallback, a version-less purl, `locator`
assertions on both adapters' happy-path tests, `SourceEvidence` immutability, and
registry-test isolation via `monkeypatch`.

**Known-bad state avoided:** Inventing a fabricated default `Path` (or a bundled
default CycloneDX document) purely to satisfy a literal "self-register at import time"
reading — which would have been unrequested, speculative infrastructure with no real
target, and would have made `registered_sources()` either crash on first use or return
misleading placeholder instances.

**KEEP instructions (preserve on re-derivation):**
- The overall module shape: ONE new file, `sources.py`, housing the identity API,
  the `SourceContract` Protocol + registry, and both concrete adapters together (CAP-1
  groups these as one capability; the `warnings: [oversized]` frontmatter flag already
  acknowledges and accepts the resulting file size — do not split into multiple files).
- `PackageIdentity` (frozen dataclass: `ecosystem`, `canonical_name`, `version`, `purl`)
  as a deliberately standalone value object, NOT `inventory.Component` — see the
  existing Design Notes section for the full rationale; keep that rationale intact.
- `resolve_identity(ecosystem, name, version=None) -> PackageIdentity`: PEP-503-normalize
  via `inventory.canonical_name`, then apply `_PYPI_ALIASES` (pypi-only), then derive the
  purl via `inventory.derive_purl` from the alias-resolved canonical name.
- `_PYPI_ALIASES` as a small, curated, git-review-owned dict seeded with
  `sklearn -> scikit-learn` (the one alias the epic AC names), documented as
  extensible-by-review, never a speculative general alias-mining engine.
- `SourceEvidence` (frozen dataclass: `identity`, `source_name`, `locator`, `raw_name`).
- `SourceContract` as an `@runtime_checkable Protocol` (`name: str` +
  `fetch`/`parse`/`validate`/`ingest`), mirroring the `Engine`/`Extractor`/`Router`
  precedent in `interfaces.py`; `ingest` takes no arguments and internally sequences
  `fetch` -> `parse` -> `validate` -> per-entry identity resolution (this shape held up
  well under review — keep it, don't switch to passing `validated` through `ingest`'s
  signature).
- `CycloneDXSourceAdapter`'s and `ManifestSourceAdapter`'s overall fetch/parse/validate/
  ingest sequencing, and their reuse of `discovery.discover` + `extract.extractor_for` +
  `routing.DefaultRouter` unchanged (`ManifestSourceAdapter`) and
  `packageurl.PackageURL.from_string`-driven identity resolution (`CycloneDXSourceAdapter`)
  — both held up well under review; only their exception-handling breadth changes per the
  amendment above, not their overall structure.
- The full existing `test_sources.py` suite's 23 test cases (PEP-503/alias/conda
  identity resolution, both adapters' happy paths and malformed-input paths, both
  adapters' `SourceContract` conformance, and the registry mechanism including the
  AC3 extensibility proof with a stub third adapter) all remain valid and should be
  preserved verbatim, with the new review-driven tests appended alongside them.

## Review Triage Log

### 2026-08-22 — Review pass
- intent_gap: 0
- bad_spec: 1: (high 0, medium 1, low 0)
- patch: 0 (not independently applied/reverified this pass — see note below)
- defer: 2: (high 0, medium 1, low 1)
- reject: 3: (high 0, medium 0, low 3)
- addressed_findings:
  - `[medium]` `[bad_spec]` Tasks & Acceptance's self-registration directive was
    self-contradictory (module-import-time registration vs. call-site-supplied
    construction args for non-zero-arg-constructible adapters); amended per the Spec
    Change Log entry above, folding in 10 related patch-shaped findings (OSError/broad-
    exception tolerance in `ManifestSourceAdapter`, missing purl/locator/raw_name/
    version-less/immutability/isolation test coverage, the idempotency-guard doc
    inaccuracy, and the duplicated version-blank normalization) into the same amendment
    rather than applying them to code about to be reverted — implementation loopback
    triggered via step-03.

Findings not folded into the bad_spec amendment: 2 `defer` (cross-source
de-duplication by identity — Story 7.2's union-computation job; CycloneDX
`specVersion` compatibility — needs a policy decision, not blocking here), both
recorded in frontmatter `deferred`. 3 `reject` (dropped silently): duplicate
blank-version normalization was itself folded into the bad_spec amendment as a
one-site fix rather than rejected outright; the remaining rejects were the
module-split suggestion (already-considered spec-level choice) and the missing
negative-`SourceContract`-conformance test (tests stdlib `typing` behavior more
than this module's own logic; the Protocol's bare-`object` typing is already
justified inline).

### 2026-08-22 — Review pass 2 (post-re-derivation)

- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 1, low 5)
- defer: 1: (high 0, medium 0, low 1)
- reject: 14: (high 0, medium 0, low 14)
- addressed_findings:
  - `[medium]` `[patch]` `ManifestSourceAdapter.parse()` called
    `components.extend(extracted)` OUTSIDE the `try` block guarding
    `extractor.extract(...)` -- a non-iterable/`None` return from a future/buggy
    extractor would crash `ingest()` for the whole target instead of being
    tolerated per-manifest. Moved inside the `try`.
  - `[low]` `[patch]` `CycloneDXSourceAdapter.parse()`'s
    `except (json.JSONDecodeError, ValueError)` was redundant
    (`JSONDecodeError` subclasses `ValueError`); simplified to `except ValueError`.
  - `[low]` `[patch]` No test exercised `ManifestSourceAdapter` against a
    conda-ecosystem manifest (only pypi), unlike the CycloneDX adapter's tests
    which already cover both ecosystems; added
    `test_manifest_adapter_conda_ecosystem_manifest`.
  - `[low]` `[patch]` No test proved `_PYPI_ALIASES` resolution flows
    end-to-end through an adapter's `ingest()` (only unit-tested via
    `resolve_identity` directly); added
    `test_manifest_adapter_alias_resolves_end_to_end_through_ingest`.
  - `[low]` `[patch]` Neither docstring noted that only the flat top-level
    `components[]` is walked (nested/transitive components and
    `metadata.component` are out of this story's scope); added one sentence to
    `CycloneDXSourceAdapter`'s docstring.
  - `[low]` `[patch]` `PackageIdentity`'s docstring hardcoded "11 additional
    fields" on `Component`, which would silently rot if that count changes;
    softened to "several additional fields."

Findings not applied this pass: 1 `defer` (the AST-denylist meta-test
`tests/meta/test_extract_no_execution.py` that enforces "no subprocess" for
`extract/` does not cover `sources.py`, whose scan root sits one level up --
network egress is still caught by the process-global socket-deny harness in
`tests/conftest.py`, but subprocess egress in this new module would not be;
real gap, but it is shared test-governance infrastructure outside this
story's own two files, not recorded in frontmatter `deferred` since fixing it
means editing a file this story's Code Map does not authorize). 14 `reject`
(dropped silently, each mirroring an established, already-shipped codebase
precedent or an already-documented deliberate design choice; among them: no
size cap on `fetch()`'s `read_text()` mirrors `feeds.load_kev_catalog`'s
identical precedent; purl qualifiers dropped on re-derivation matches
`inventory.py`'s own documented qualifier-stripping identity convention; the
component's own `version` field being ignored in favor of the purl's is an
intentional, already-reasoned design choice; the broad
`except (SystemExit, Exception)` in `ManifestSourceAdapter.parse` deliberately
mirrors `cli.py`'s own established backstop at the identical call site; the
registry's lack of a concurrency lock / per-factory error isolation /
`.name`-uniqueness check all mirror `engines.py`'s identical,
never-previously-flagged precedent).

Follow-up review recommendation: this pass's `patch` findings only (1 medium,
5 low) score `3x1 + 1x5 = 8` (>= 5) -> `followup_review_recommended: true`,
even though every one of the 6 was applied and independently re-verified this
same pass (36/36 -> 38/38 new tests, 1978 passed/11 deselected full suite,
`ruff check` clean) -- the threshold is mechanical per this workflow's own
rule, not a signal that residual work remains.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary of implemented change:** Added the `SourceContract` adapter interface + registry, the standalone `PackageIdentity`/`resolve_identity` identity API, and two concrete evidence-source adapters (`CycloneDXSourceAdapter`, `ManifestSourceAdapter`) to `pyforge-warden`, per Epic 7 Story 7.1. This lets Warden ingest package-eligibility evidence from outside the scanned project (an external CycloneDX document, or another local manifest tree) through one pluggable interface, and resolve a canonical cross-source package identity (PEP-503 + a small curated alias table) without constructing a full compliance-scan `Component`. No union/eligibility computation and no CycloneDX output -- those are Stories 7.2/7.3, explicitly out of scope here.

**Files changed:**
- `src/shared/packages/pyforge-warden/src/pyforge/warden/sources.py` (new, 383 lines) -- `PackageIdentity`, `resolve_identity`, `SourceEvidence`, `SourceContract` Protocol, `register_source`/`source_factories`/`registered_sources` registry, `CycloneDXSourceAdapter`, `ManifestSourceAdapter`.
- `src/shared/packages/pyforge-warden/tests/unit/test_sources.py` (new, 38 tests) -- full I/O-matrix coverage plus every review-driven addition (partial-manifest-failure tolerance, malformed-purl/unrecognized-type/no-name/versionless-purl skip paths, unreadable-target degradation, both adapters' `locator`/immutability assertions, dual-ecosystem coverage on `ManifestSourceAdapter`, end-to-end alias resolution through `ingest()`, `monkeypatch`-isolated registry tests, and AC1-3 conformance/extensibility proofs).

**Review findings breakdown (both passes combined):**
- Pass 1: 1 `bad_spec` (self-registration Tasks-text was self-contradictory; corrected via spec amendment + full re-derivation, folding in 10 patch-shaped findings from the same pass); 2 `defer` (recorded in frontmatter `deferred`); 3 `reject`.
- Pass 2 (post-re-derivation): 6 `patch` (applied directly, re-verified green); 1 `defer` (a shared test-governance gap outside this story's own files, not recorded in frontmatter since fixing it is out of this story's authorized surface); 14 `reject` (each matching an established, already-shipped codebase precedent or an already-documented deliberate design choice).
- No `intent_gap` in either pass.

**Follow-up review recommendation:** `true` (pass 2's patch-only score: 1 medium + 5 low = `3x1 + 1x5 = 8` >= 5, per this workflow's mechanical threshold) -- recorded in frontmatter, even though all 6 were applied and independently re-verified within this same pass.

**Verification performed:**
- `pixi run -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_sources.py -v` -- 38/38 passed (independently re-run and confirmed by this orchestrating session, not just the implementation subagent's own report).
- `pixi run -e pyforge-warden pyforge-warden-test` (the fast-loop full suite) -- 1978 passed, 11 deselected (slow-marked), zero regressions.
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-warden/src/pyforge/warden/sources.py src/shared/packages/pyforge-warden/tests/unit/test_sources.py` -- clean.
- Matrix Test Audit: every I/O & Edge-Case Matrix row has a covering test that ran and passed.
- `git status --short` confirmed only the two new files are touched at every checkpoint; every REUSE-ONLY/PATTERN-REFERENCE-ONLY file in the Code Map (`inventory.py`, `models.py`, `interfaces.py`, `engines.py`, `discovery.py`, `extract/__init__.py`, `routing.py`, `sbom.py`, `feeds.py`, `tests/conftest.py`) is unmodified.

**Residual risks:** The two frontmatter `deferred` items (cross-source de-duplication by identity; CycloneDX `specVersion` compatibility) are real, intentionally out-of-scope gaps for Story 7.2 and a later hardening pass respectively -- neither blocks this story's own AC. The AST-denylist meta-test's non-coverage of `sources.py` for subprocess-egress detection (noted in the pass-2 triage log, not recorded in frontmatter `deferred`) is a pre-existing, shared-infrastructure gap this story's own code does not trigger (no subprocess call exists in `sources.py`), but a future edit to this file would not be caught by that specific mechanism.
