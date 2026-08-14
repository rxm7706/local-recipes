---
spec: artifactory-download-intelligence
status: ready
owner-dream: docs/dreams/artifactory-download-intelligence.md
surface:
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/
sources:
  - ../../../../../../docs/dreams/artifactory-download-intelligence.md
open_questions:
  - Excel governance rendering of the joined data — deliberately undecided at Spec time.
  - Which live Artifactory instance, and when its attended bring-up happens — outside this Spec.
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/artifactory-download-intelligence.md` is listed in
> `sources:` for narrative rationale this contract intentionally omits.

# Atlas gains an org's own Artifactory download telemetry — an AQL join + internal/private flag, mock-first

## Why

Atlas already answers "what does the PyPI/conda-forge universe look like" at universe scale from
public sources — Phase D enumerates the full PyPI Simple index, Phase H/O track versions and
serial activity, Phase P fetches public BigQuery download counts, Phase C/C.5 join PyPI↔conda-forge
identity via parselmouth's `compressed_mapping.json` extended with source-URL matches. What it
structurally cannot answer is the org-specific question a platform engineer with their own
Artifactory mirror wants: "what is THIS organization actually pulling from ITS OWN repository, and
which of those pulls have no public counterpart at all." The owner dream pre-narrowed this
rigorously against real code (`pypi_intelligence/nodes.py`, checked line by line, not assumed):
every other capability its source dream (`python-supply-lens`) described — PyPI enrichment,
conda-forge crossref, caching, credentials, observability — already exists in Phases C/C.5/D/H/O/P/R.
Exactly two things are genuinely new: (a) an AQL adapter for an Artifactory instance's own download
telemetry, and (b) the internal/private flag only that telemetry can produce. Operator decision
(2026-08-14, binding): **mock-first injectable** — this Spec binds to NO named Artifactory
instance; the AQL client is built network-injectable against a mock transport, the exact shape
atlas already proved with `LaSuiteClient` (`factory/lasuite.py`: the default opener refuses to run
because no transport was injected; live bring-up is attended, later, separately).

## Capabilities

- **CAP-1**
  - **intent:** An AQL adapter queries an Artifactory instance's own telemetry: it resolves
    virtual-repo topology to the backing repositories and aggregates download counts by package
    name and version. The client takes an injectable transport (LaSuiteClient shape); with no
    transport injected it refuses to run rather than reaching for any network default.
  - **success:** Against a mock AQL transport serving canned topology + download responses, the
    adapter returns backing-repo-resolved, name+version-aggregated download rows; constructing it
    without a transport fails loudly, and no test path opens a live connection.
- **CAP-2**
  - **intent:** Adapter results join into the SAME identity space Phase C/C.5 already maintain —
    parselmouth's `compressed_mapping.json` plus atlas's source-URL extension — so an
    Artifactory-observed package resolves to the identical PyPI/conda-forge identity every other
    atlas signal uses. Enrichment reuses atlas's existing machinery; nothing is re-fetched through
    a second parallel path.
  - **success:** A mock-served package that exists publicly joins to the same identity row Phase
    C/C.5 would produce for it (same mapping, same normalization); no new PyPI-metadata or
    conda-forge-crossref fetch path exists in the diff.
- **CAP-3**
  - **intent:** A package pulled from Artifactory with no public PyPI counterpart — absent from
    Phase D's universe enumeration — is flagged **internal/private**: the one signal a
    universe-scale public crawl structurally cannot see.
  - **success:** In a mock run containing both a public package and a mock-only package, exactly
    the mock-only one carries the internal/private flag, and the flag is queryable from the
    joined output.
- **CAP-4**
  - **intent:** The work ships as a new atlas Kedro pipeline following the established phase
    conventions (per-phase caching, env-var concurrency knobs, structured logging — the rule book
    in `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md`), and its output
    composes with atlas's existing surfaces: rows land in the atlas DB and export in
    `export-purls`-shaped form, not a second disconnected report format.
  - **success:** The pipeline registers alongside the existing atlas pipelines and its output is
    consumable by the existing export surface without a bespoke reader; no parallel report
    format is introduced.

## Constraints

- **Always:** credentials route through `_http.py`'s existing truststore + JFrog auth chain — no
  second, bespoke Artifactory credential-resolution path, ever.
- **Always:** identity is enriched, never forked — every join goes through the Phase C/C.5
  mapping atlas already maintains; a drift-prone duplicate identity path is a defect, not a
  convenience.
- **Always:** mock-first injectable — no named instance appears anywhere in this Spec's scope,
  code, config, or tests; the transport is the only seam, and its no-injection default refuses.
  Live-instance wiring is a separate, later, attended step outside this Spec's success signal.

## Non-goals

- **Not** conda-forge or npm download statistics — excluded by the owner dream, carried over.
- **Not** a web dashboard or any new UI surface.
- **Not** live-instance bring-up, instance selection, or any network call to a real Artifactory —
  deferred to the attended step this Spec explicitly excludes.
- **Not** an Excel governance view — a Spec-time non-decision (see Open Questions); if ever
  wanted it is a rendering of the same joined data, never a second pipeline.

## Success signal

A mock-verified end-to-end run: against a mock AQL transport, the pipeline resolves virtual-repo
topology to backing repositories, aggregates downloads by name+version, joins the results into
atlas's existing Phase C/C.5 identity space, and flags the mock-only package internal/private —
with the public-counterpart package joined and unflagged in the same run. No live Artifactory
instance is required, named, or contacted anywhere in the verification; constructing the client
without an injected transport fails loudly. That is this Spec's whole finish line — live wiring
is the later attended step, not part of this signal.

## Open Questions

- **Excel rendering:** deliberately undecided at Spec time. Any future Excel governance view is a
  rendering of the atlas data this pipeline already produces — a downstream decision, not scope.
- **Live instance:** which Artifactory deployment this eventually targets, and when its attended
  bring-up happens — the operator decision defers both outside this Spec entirely.
