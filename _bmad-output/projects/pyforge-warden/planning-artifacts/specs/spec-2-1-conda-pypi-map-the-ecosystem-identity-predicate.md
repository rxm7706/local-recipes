---
title: 'Story 2.1: conda→pypi map + the ecosystem-identity predicate'
type: 'feature'
status: 'regenerated'
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'lost to the Tier-3 paper-trail gap; dev-notes / review-triage-log not recovered'
---

> **Regenerated contract-spec (2026-07-25).** The original per-story spec file was
> lost when its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed on
> worktree teardown. This file **recovers the load-bearing contract** — the Intent and
> Acceptance Criteria below are lifted **verbatim** from the tracked, authoritative
> `planning-artifacts/epics.md` (the source the original spec was derived from), and the
> Realized-in section maps it to the shipped implementation on `main`. What is **not**
> recovered: the original implementation dev-notes and the review-triage log (those lived
> only in the lost file). Behaviour is verified by the current green suite; the story is
> done and merged.

## Contract (from epics.md — verbatim, authoritative)

### Story 2.1: conda→pypi map + the ecosystem-identity predicate

As a **conda/pixi maintainer**,
I want my conda dependencies mapped to their PyPI identity (or honestly withheld),
So that vulnerability matching can't silently misfire on a name mismatch.

**Acceptance Criteria:**

**Given** the atlas `export-purls` conda↔pypi TSVs, **When** the map generator runs *(invoke `conda-forge-expert` — CFE Rule 1; runs as a **parallel read-only data task**, so 2.1 consumes a finished `data/conda_pypi_map.json`)*, **Then** a bundled map with a stable schema is produced, **preserving the per-pair `match_source` + `match_confidence` columns** (never flattened to name→name — the DEP001-block and identity-trust rules read these provenance tiers: `parselmouth`/`recipe_source_url` → block-eligible/trusted, `name_coincidence` → warn, `none` → withheld); `prefix-dev/purl-associator` serves as a second corroborator (added 2026-07-12). **And** the generator supports a **parselmouth-direct refresh mode** (consume `prefix-dev/parselmouth`'s published mapping artifacts — pixi's own default `conda-pypi-map` source) so non-atlas organizations can regenerate the bundled map (added 2026-07-12).

**Given** a conda component, **When** its `pypi_identity` is resolved, **Then** it is taken from pixi.lock `pypi:` / explicit PyPI sections / the map (with a confidence value); an unmapped or `native-nonpypi` package resolves to `None` and is **withheld from osv** (never fed under the conda name) — closing the silent `pytorch`→`torch` false-green. **And** `vuln_matchable = (pypi_identity ≠ None) AND version==X.Y.Z`.

**Given** a **low-confidence** identity (below the chosen threshold), **When** classified, **Then** it resolves to **`indeterminate`, not a silent clean** (ties the threshold decision back to 1.1's lattice). **And** landing the confidence gate **activates hygiene's DEP001 block-on-high-confidence** — upgrading story 1.3's deliberate all-`warn` `DEFAULT_HYGIENE_POLICY` to the Gap-A decision (DEP001 blocks on a trusted mapping; ambiguous → `warn`).

*(Lockfile extraction moved to Story 2.6, 2026-07-16 — the 2026-07-12 Major-2 bolt-on made 2.1 a two-session story; readiness Major-3 split.)*

### Story 2.2: Non-rendering extraction (common case) + differential-oracle

As a **conda/pixi maintainer**,
I want my source manifests' common-case dependency set extracted without a resolved environment, validated against a real render,
So that I can scan my source recipe pre-build with confidence it isn't silently dropping deps.

**Acceptance Criteria:**

**Given** a common-case `recipe.yaml`/`meta.yaml`/`environment.yml`/`pixi.toml`, **When** extracted, **Then** it is **parse-as-data, never rendered** — the extract module imports no execution primitive and no `jinja2` (S1 AST-denylist) — and its deps land in the inventory (**FR3** — tagged 2026-07-12). **And** pixi extraction covers the `[feature.*]` and `[target.*]` tables (provenance-tagged) beyond the base sections. **And** `run_constrained:`/`run_constraints:` entries are **constraints, not dependencies** — excluded or ingested as `provenance: constraint` (out of vuln matching + SBOM counts), matching the shipped `scan_project` semantics (added 2026-07-12). **And** the C0c socket-deny gate holds (extraction performs no egress — explicit NFR-S2 AC). **And** with adjacent Python source present, deptry consumes the synthesized front-door so **hygiene findings surface for the conda-sourced project too** (FR8's conda half — was implicit). **And** extraction is **line-bounded with a per-line byte cap + a total manifest-size cap**, and no compiled pattern carries nested unbounded quantifiers (NFR-S5 — statically asserted).

**Given** the **differential-oracle**, **When** it runs on the fixture corpus, **Then** the non-rendering dep-set ⊇ the rattler-build/conda-build render (modulo name-only-marked), with 0 uncaught exceptions. **And** the oracle is **skip-if-renderer-unavailable** (fixture scale here; matured to corpus scale in 5.2) so 2.2 never hard-blocks on renderer provisioning.

### Story 2.3: The full supported-construct matrix (ratcheted)

As a **conda/pixi maintainer with a Jinja-heavy recipe**,
I want selectors, templating, multi-output, and pin_subpackage handled by an explicit, tested matrix,
So that a complex recipe degrades honestly instead of silently mis-extracting.

**Acceptance Criteria:**

**Given** the construct matrix, **When** a recipe uses them, **Then** `compiler()`/`stdlib()` → build-tool-exclude, `pin_subpackage()` → internal-exclude, `# [sel]`/`if-then-else` → **union both branches + mark**, expression-logic → degrade to name-only+marked (FR5). **And** each rule is ratcheted against the 2.2 differential-oracle (a matrix regression fails CI).

### Story 2.4: Honest split coverage + the indeterminate producer (C0b)

As a **conda/pixi maintainer**,
I want a truthful verdict that never claims "clean" for deps it couldn't assess,
So that a green check is trustworthy.

**Acceptance Criteria:**

**Given** a manifest where some deps resolve and some don't, **When** reported, **Then** coverage is **split** into hygiene vs vulnerability dimensions (FR15) and a partial result renders a **coverage-qualified verdict governed by the FR20 lattice** (partial vuln coverage ⇒ `indeterminate`, non-zero), never bare "clean" — the retired "clean at N%" phrasing is outlawed by FR16 (wording aligned 2026-07-16). **And** the coverage marks `direct-only` vs `locked-closure` (a loose manifest lists direct deps only; transitive vulns invisible without a lockfile).

**Given** a name-only / range / unmapped dep, **When** classified, **Then** it becomes `indeterminate` with a `WithholdReason` (`no-version`/`unmapped-ecosystem`/`native-nonpypi`/`range-only`) and is **never dropped or defaulted to clean** (C0b — FR13); the verdict exits **red-by-design** without needing E3's waivers. **And** an empty extraction is distinguished from "deps present but unresolved" (FR6).

**Given** a manifest-only repo with **no adjacent Python source** (the fleet's majority shape — feedstocks), **When** the hygiene axis runs, **Then** hygiene coverage is honestly **`not-applicable`/skipped, the reduced scope recorded — never a 100%-DEP002 noise wall** — matching Kedro FR-16's already-specced semantics for this schema's second producer. *(Added 2026-07-12 per readiness Major 3.)*

### Story 2.5: Name-level CVE tier + stale-DB + cross-ecosystem non-merge

As a **conda/pixi maintainer**,
I want a risk signal for my unpinned deps and honesty about the vuln-data freshness,
So that "vuln-coverage 12%" becomes an actionable worry-list, not a dead end.
*(Consumes the 1.4 provisioning decision for its stale-DB semantics.)*

**Acceptance Criteria:**

**Given** a mapped-but-unversioned dep, **When** the name-level tier runs, **Then** it flags whether the package carries **any known critical CVE across any version** ("pin/lock to prove immunity") — never assuming a version (FR13 guardrail).

**Given** an offline DB older than `--db-max-age` (per the 1.4 definition of "stale"), **When** scanned, **Then** the run routes to **`indeterminate` (exit 1) with a typed `vuln-data-stale` driver** — never a confident clean, never a silent 0 (FR12, aligned 2026-07-16 with NFR-S8 + C0); the report records the DB source + timestamp (FR11).

**Given** the same package name in a conda manifest AND a PyPI manifest, **When** inventoried, **Then** they stay **distinct per-ecosystem components** — no silent merge (FR7).

## Realized in

- **Package:** `src/shared/packages/pyforge-warden/` (import `pyforge.warden`).
- **Status:** done + merged to `main`.
- **Verification:** the shipped behaviour for this story is covered by the current
  `pixi run --frozen -e pyforge-warden pyforge-warden-test` suite (green on `main`).
  For the precise file-level Code Map, read the implementation on `main` — this
  regenerated spec deliberately does not guess a per-file map it cannot verify from the
  lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Root cause: story specs lived in Tier-3
gitignored `implementation-artifacts/`; they are now tracked here in
`planning-artifacts/specs/` so they survive worktree teardown and are in every clone.
