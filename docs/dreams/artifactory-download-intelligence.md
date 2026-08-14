---
title: An enterprise Artifactory mirror's own download telemetry joins the universe picture
type: dream
owner: atlas
status: specified
---

# An enterprise Artifactory mirror's own download telemetry joins the universe picture

## The Dream

Atlas already answers "what does the PyPI/conda-forge universe look like" — enumeration,
enrichment, cross-ecosystem mapping, download counts — at universe scale, from public sources
(the PyPI Simple index, BigQuery's public download dataset, parselmouth's compressed mapping).
What it cannot answer is the narrower, org-specific question a platform engineer with their own
Artifactory mirror actually wants: "what is THIS ORGANIZATION actually pulling, from ITS OWN
repository, and which of those pulls have no public counterpart at all" — because that requires
querying a specific Artifactory instance's AQL API, which atlas has never had a reason to do
(atlas's download signal is BigQuery's public dataset, not any one org's private pull telemetry).
This Dream is that missing join: enrich atlas's already-universe-scale picture with one
organization's own Artifactory download reality, and flag whatever in that reality has no public
PyPI presence at all — the one thing a universe-scale public crawl can never see on its own.

## What it looks like when real

- An Artifactory AQL query resolves virtual-repo topology to backing repositories and aggregates
  downloads by package name and version — the one genuinely new capability, since nothing in
  atlas's existing pipeline talks to any org's private Artifactory instance for this purpose.
- Every result is enriched through atlas's EXISTING machinery, not a second parallel enrichment
  path: PyPI metadata via atlas's own PyPI-facing phases, conda-forge cross-referencing via the
  SAME parselmouth mapping atlas's Phase C/C.5 already consumes.
- A package pulled from Artifactory with no PyPI presence at all is flagged internal/private —
  the one thing atlas's universe-scale crawl structurally cannot see (it only knows what's public).
- Output composes with atlas's existing surfaces (its own DB, `export-purls`-shaped output) rather
  than inventing a second, disconnected report format; an Excel governance view can be a rendering
  of the same underlying data atlas already tracks, not a separate pipeline.

## What is real

The overlap with atlas's existing `pypi_intelligence` pipeline (`src/pyforge/atlas/pipelines/pypi_intelligence/`)
is substantially larger than the source dream's own framing suggests — checked directly against
`nodes.py`, not assumed:

- **Phase D** already enumerates the full PyPI universe from the Simple index.
- **Phase H** already fetches current PyPI versions, serial-gated for efficiency (never-fetched /
  serial-moved / 30-day safety re-check eligibility).
- **Phase O** already snapshots PyPI serials on a 90-day rolling window, deriving an activity band
  from the deltas.
- **Phase P** already fetches monthly PyPI download counts — via BigQuery's public dataset, under
  a documented two-layer cost gate — the same *kind* of signal the source dream wants, from a
  different (public, not org-private) source.
- **Phase C / Phase C.5** already join PyPI↔conda-forge identity via the SAME parselmouth
  `compressed_mapping.json` the source dream names, extended with source-URL-derived matches
  beyond parselmouth's own coverage.
- **Phase R** already enriches with deterministic packaging-shape classification.
- Disk-based response caching, credential precedence (CLI → env → NETRC), and enterprise
  SSL/certificate support already exist repo-wide via `_http.py`'s truststore + JFrog/GitHub/.netrc
  auth chain, used by every atlas phase that makes a network call.

Genuinely missing: any code path that queries a SPECIFIC org's Artifactory AQL API for ITS OWN
download telemetry (atlas's Phase P is public-BigQuery-sourced, not any one org's private
Artifactory), and the internal/private-package flag this telemetry alone can produce (public-only
crawls have no way to see a package that was never public in the first place).

## Constraints

- **Enrich atlas's existing pipeline; do not fork a second one.** A result from this Dream's
  Artifactory query joins the SAME identity space (`Phase C`'s mapping, `Phase D`'s enumeration)
  atlas already maintains — it does not stand up a parallel PyPI-metadata or conda-forge-crossref
  path that could drift from the one atlas already has.
- **Enterprise credentials route through `_http.py`'s existing auth chain** — no second,
  bespoke Artifactory credential-resolution path.

## Non-goals

- **Not conda-forge download statistics** — the source dream's own v1 scope excludes this too;
  carried over unchanged.
- **Not npm download statistics** — same, carried over unchanged.
- **Not a web dashboard** — output composes with atlas's existing surfaces; a UI, if ever wanted,
  is a separate decision.
- **Not deciding which specific Artifactory instance this targets** — like
  [[package-inventory-eligibility]]'s own deferred Artifactory adapter, this presupposes a real
  target environment that hasn't been named yet; this Dream captures the CAPABILITY, not a
  commitment to a specific enterprise deployment.

## Full feature audit against `python-supply-lens`

Every capability the source dream names, and this Dream's disposition on each:

| Source feature | Disposition | Why |
|---|---|---|
| Artifactory AQL querying (virtual-repo resolution, download aggregation) | **Included, new** | The genuine gap — nothing in atlas talks to a private Artifactory instance today. |
| PyPI metadata enrichment (latest version, project URLs, GitHub link) | **Reused, already exists** | Atlas's Phase D/H/O already do this at universe scale; this Dream joins into it rather than re-fetching independently. |
| Conda-forge cross-referencing via parselmouth | **Reused, already exists** | Atlas's Phase C/C.5 already consume the identical `compressed_mapping.json`, extended beyond it with source-URL matching. |
| Internal/private package detection | **Included, new** | The one signal a universe-scale public crawl structurally cannot produce alone — genuinely needs the Artifactory-side telemetry this Dream adds. |
| Disk-based response caching (configurable TTL, force-refresh, cache-only) | **Reused, already exists** | Every atlas phase making a network call already caches; a new Artifactory adapter should follow the same convention, not invent a second caching layer. |
| Dual Excel + JSON output | **Reconsidered** | JSON: atlas already has structured output surfaces this should compose with rather than duplicate. Excel: no current atlas output targets Excel — if wanted, it is a rendering of atlas's existing data, decided at Spec time, not a second pipeline. |
| Credential management (CLI → env → NETRC, bearer token, enterprise SSL) | **Reused, already exists** | `_http.py`'s truststore + JFrog/GitHub/.netrc chain already provides this repo-wide. |
| Observability (structured logging, run manifests, package-level traceability, degraded-but-usable execution) | **Reused, already exists** | Atlas's own Kedro-pipeline logging and phase-level manifests already cover this; a new phase inherits it rather than reimplementing. |

## Kinships

[[pyforge-atlas]] (the estate this extends — Phase C/C.5/D/H/O/P/R are all direct prior art) ·
[[package-inventory-eligibility]] (the sibling Warden dream with the same deferred
"which specific Artifactory instance" open question — captured independently, not because the two
dreams should merge: one is estate-wide PyPI/conda-forge intelligence, the other is enterprise
eligibility provenance)

## Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit.
  Substantially re-scoped from the source's own framing after checking atlas's actual
  `pypi_intelligence` pipeline directly (`nodes.py`'s Phase C/C.5/D/H/O/P/R) rather than assuming
  the source dream's premise that this capability doesn't exist yet — it mostly does, at greater
  scale than the source dream's own v1. Renamed from `python-supply-lens` to reflect the narrowed
  scope: only the Artifactory-telemetry join and the internal/private-package flag it enables are
  genuinely new; everything else the source dream described is already atlas's, checked line by
  line against real code rather than trusted from the source's own "What it owns" list.
- **2026-08-14** — Spec authored (spec-artifactory-download-intelligence, pyforge-atlas) per
  operator decision: mock-first injectable — no named instance; AQL adapter + internal/private
  flag join Phase C's identity space through _http.py's auth chain, mock-verified; live wiring
  stays a later attended step.
