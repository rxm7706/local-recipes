---
title: Genesis installer — the seed, made executable
type: dream
owner: marshal
status: archived
archived-reason: absorbed
---

> **Narrative consolidated 2026-08-02 (dream-level only).** This Dream's narrative now lives
> in [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md) under "Kept separate on purpose."
>
> **Superseded the same day (explicit user override, third pass, 2026-08-02).** The
> paragraph originally here said the downstream chain "remain[ed] exactly as they were...
> deliberately kept separate from `marshal` the CLI's own FR-1..65." That is no longer true
> for brief/PRD/architecture/Spec: `research/product-brief-pyforge-genesis.md`,
> `prds/prd-genesis-installer-2026-07-25/`, `architecture/architecture-genesis-installer-2026-07-25/`,
> and `specs/spec-genesis-installer/` were **consolidated** into `pyforge-marshal`'s own single
> brief / PRD / architecture / Spec — a "Satellite: Genesis Installer" section in the brief and
> PRD, a continued `AD-51..AD-65` in the architecture, a continued `CAP-10..CAP-18` in the Spec.
> **Only the epics genuinely stay separate**, exactly as before: `epics-genesis-installer.md`
> (6 epics / 36 stories, epics 7–12) is unchanged and was explicitly out of scope for this
> consolidation. The four original standalone documents are preserved, not deleted, at
> `archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/{research/product-brief-pyforge-genesis.md,
> prds/prd-genesis-installer-2026-07-25/, architecture/architecture-genesis-installer-2026-07-25/,
> specs/spec-genesis-installer/}`. genesis-installer's own `FR1..FR62` (no dash) numbering is
> unchanged and was never renumbered into Marshal's `FR-1..FR-65` (with dash) — the two ranges
> stay distinct namespaces inside the one merged PRD.

# Genesis installer — the seed, made executable

## The Dream

[[pyforge-genesis]] is the operating model: the Charter, the Lexicon, the Guild, the
Dream→Code chain. This Dream is the **machine that installs it** — the difference between
a model that exists in one repository and a model that can be adopted by any repository.

```bash
marshal <verb>   # greenfield: a new repo born Dream-first
                 # brownfield: layer the model onto a repo without disturbing what runs
```

> **Renaming pending (operator call 2026-07-31): no `genesis` binary.** The verbs fold
> into Marshal's CLI. The name `genesis-installer` records the project this Dream was
> *carved out of* in the 2026-07-28 Charter §5 split — and that split completed on
> 2026-07-30, leaving **zero shared artifacts**: `pyforge-genesis` now holds only the two
> constitutive Dreams and an `epics.md` beginning *"No epics, and that is the contract"*,
> while this installer's whole chain lives under `pyforge-marshal`. The product is
> therefore named after a project deliberately separated from it, on the Charter's own
> grounds that *"constitutive records and the machine that installs them are different
> nouns."* The exact verb mapping is unsettled — `genesis init` collides head-on with the
> shipped `marshal init <slug>` (loop-home provisioning, story 1.4) — and is recorded as
> an open question in the Spec's memlog rather than guessed here, because the 19 story
> keys under Epics 10–12 carry the old verb names.

What it stands up — stated in the Spec's own two registers, because the difference is
the whole design and this Dream previously blurred it:

- **Verified, never installed** (`REFERENCED`): the pixi environment and Python toolchain,
  `bmad-method`, `bmad-loop`/`bmad-dev-auto`, and the BMAD module set — `skill-forge`
  and the BMM / BMB / TEA / CIS packages. Genesis asserts presence and a version floor;
  the packages come from conda-forge and are never vendored.
- **Materialized** (`COPIED` / `GENERATED` / `HYBRID`): the multi-project wiring
  (`scripts/bmad-switch`, per-project config and artifact isolation, concurrent loop
  homes via `scripts/bmad-loop-worktree`), the detector set and its CI wiring, the tier
  layout (`docs/dreams/`, `_bmad-output/projects/<station>/`), the `AGENTS.md` family,
  and the deck family.

*Corrected 2026-07-31.* The earlier wording listed `skill-forge` and BMM/BMB/TEA
alongside the copied artifacts, implying Genesis installs them. It does not, and no
capability or manifest row ever claimed it did — the promise existed only here, in
prose, which is precisely the Dream↔Spec gap [[fidelity-enforcement]] names.

## Why this is the Marshal's

Splitting this out of [[pyforge-genesis]] (2026-07-28, Charter §5 amendment) resolved a
Dream that was doing two jobs at once. Genesis-the-Dream is **constitutive** — it records
the Charter, the Lexicon, and the Guild's membership, and is owned by `guild` because it
precedes the stations. The installer is **buildable work**, and buildable work with no
accountable Smith is the exact condition the station model exists to make impossible.

It is the Marshal's by the Charter's own text, not by assignment: Marshal's toolkit already
lists every component this installs (bmad-method, bmad-loop, BMM/BMB/TEA, skill-forge,
web bundles), Marshal already owns *Monorepo & Multi-Project Operation* (`bmad-switch`,
per-project isolation, loop homes), and Marshal's CLI cadence already opens with
`marshal init — initialize a new BMAD-compliant project blueprint`. The installer is that
verb, made real.

## What is real

- **The Spec** — `spec-genesis-installer`'s 9 capabilities live on as `spec-pyforge-marshal`'s
  `CAP-10..CAP-18` *(folded in 2026-08-02, explicit user override)*, with its extraction
  manifest (now `spec-pyforge-marshal/extraction-manifest.md`): what is **copied**
  (conventions, skills, workflows) vs **referenced** (bmad-method releases) vs **generated**
  (per-repo Dreams). The original standalone Spec is preserved at
  `archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-genesis-installer/`.
- **The four verbs** — `init` (CAP-14, greenfield), `adopt` (CAP-12, brownfield,
  dry-run by default), `check` (CAP-13, read-only conformance, CI-shaped), `update`
  (CAP-15, versioned migration with no hand edits) — all one `resolve → detect → plan →
  apply` pipeline. The master success switch is the **empty-plan oracle**: `genesis
  adopt --dry-run` against this repository at the shipped model version must produce an
  empty plan, or the model and the repo it was extracted from have diverged. **Zero
  execution weight so far** — all 36 stories in `epics-genesis-installer.md` (epics
  7–12) are `backlog`; no code exists under `src/shared/packages/` for any of it.
- **The proof** — this repository was the first brownfield adoption, installed by hand from
  `archive/docs/bmad-setup-plan.md`. The installer is that procedure, generalized.
- **The chain** — PRD and architecture *(folded in 2026-08-02, explicit user override)* now
  live inside `pyforge-marshal`'s own PRD (a "Satellite: Genesis Installer PRD" section,
  `FR1..FR62`) and architecture (a "Satellite: Genesis Installer Architecture" section,
  `AD-51..AD-65` continuing the station's own `AD-1..AD-50`) rather than as separate
  documents; the originals are preserved under `archive/`. **Epics stay separate, unchanged**:
  `epics-genesis-installer.md` (Foundation & the Write Guard · the Managed-Region Engine ·
  Detect & Plan, 6 epics / 36 stories) under `pyforge-marshal`, inherited from the pre-split
  `pyforge-genesis` project.

## The frontier

- **The write guard and managed regions** are the hard part: `adopt` must layer the model
  onto a live repo without clobbering what already runs. Every write is either into a
  managed region it owns, or refused.
- **Idempotent re-adoption** — running `adopt` twice must be a no-op, and running it after
  a model upgrade must migrate rather than overwrite.
- **Close the manifest's coverage holes** (found 2026-07-31 by auditing the manifest
  against a live inventory). CAP-1 promises a coverage check that HARD-fails on any
  unclassified artifact; measured against what is actually installed, the V1 manifest
  classifies **none** of: `skill-forge` (`_bmad/skf/**`, 59 directories), BMB, TEA, CIS,
  `bmad-dashboard`, or the four remaining `bmad-*` packages. An adopting repo would
  therefore inherit a model the manifest cannot describe — and CAP-1's own check would
  be the thing that reports it, if the manifest listed them to begin with.
- **Derive the detector set, do not list it.** The manifest names one detector
  (`bmad_drift_check.py`); the repo now has **ten**, discovered by `scripts/detectors.py`.
  A repo adopting the model today gets a tenth of the conformance surface. The manifest
  row should resolve through the registry, for the same reason the registry exists.
- **Version floors are hand-written and drift.** `bmad-loop` is pinned `>=0.8.1` while
  0.9.0 is what the model is exercised against. Not wrong — a floor is a minimum — but
  it is a restated number in a companion, which `EXEMPLAR-STANDARD`'s provenance rule 3
  (*derive counts; do not restate them*) exists to prevent.

## Realization log

- **2026-08-02 (dream-coverage audit)** — a separate pass audited the merged brief/PRD/
  architecture/Spec against this Dream and `docs/dreams/pyforge-marshal.md`, checking every
  substantial CAP-10..CAP-18 / FR1..FR62 / AD-51..AD-65 item for coverage and execution
  weight (epics-genesis-installer.md, Marshal's own `sprint-status.yaml`, and
  `src/shared/packages/` — genesis-installer has none of the three: all 36 stories are
  `backlog`, no code exists). One gap found and closed: this Dream named only two of the
  four verbs (`init`, `adopt`); `check` and `update` — and the empty-plan oracle that is the
  PRD's own primary success criterion (SC-01) — were absent even at summary level. Added
  above, in "What is real." Both flagged contradictions (CLI framework, `check` collision)
  confirmed to still have **zero execution weight on either side of the collision** — no
  genesis code exists, and Marshal's own `marshal check` (FR-65) is speced but its story
  (5-6) is still `backlog` too — so nothing here was silently resolved by the audit.
  Everything else in the merged chain was already reflected here or in
  `docs/dreams/pyforge-marshal.md`'s "Kept separate on purpose" section; no pruning was
  warranted.
- **2026-08-02 (explicit user override)** — **brief/PRD/architecture/Spec consolidated into
  `pyforge-marshal`'s own single chain**, reversing the "kept separate on purpose" call
  `docs/dreams/pyforge-marshal.md` made earlier the same day. `research/product-brief-pyforge-genesis.md`
  became a "Satellite: Genesis Installer" section in `product-brief-pyforge-marshal.md`;
  `prds/prd-genesis-installer-2026-07-25/prd.md` (`FR1..FR62`) became a "Satellite: Genesis
  Installer PRD" section, own numbering preserved and never renumbered into Marshal's
  `FR-1..FR-65`; `architecture/architecture-genesis-installer-2026-07-25/architecture.md`'s
  `AD-01..AD-15` became a "Satellite: Genesis Installer Architecture" section renumbered
  `AD-51..AD-65`; `specs/spec-genesis-installer/SPEC.md`'s `CAP-1..CAP-9` continued this
  station's own Spec sequence as `CAP-10..CAP-18`, its `AD-01..AD-09` references renumbered
  to match. Two contradictions surfaced by the fold, flagged rather than resolved: the CLI
  framework (Marshal's shipped `argparse` vs this installer's designed `typer`+`rich`), and a
  `marshal check` / `genesis check` verb-name collision (both feed Open Question 17). Only
  `epics-genesis-installer.md` stays a separate document, unchanged, per the same override.
  The four original standalone documents are preserved (not deleted) at
  `archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/`.
- **2026-07-31** — **fold the CLI into Marshal; retire the `genesis` binary** (operator
  call), and correct the Dream's over-promise (it listed `skill-forge` and BMM/BMB/TEA
  among what Genesis *stands up*, which no capability or manifest row ever claimed —
  those are REFERENCED, verified and never installed). A manifest audit against a live
  inventory added ten missing REFERENCED rows and flagged two as restated-rather-than-
  derived: the detector row named **one** file while the repo had grown to **ten**, and
  the `bmad-loop` floor is hand-written. Findings recorded in the Spec's memlog for
  re-derivation, never hand-patched into `SPEC.md`. **The naming problem is that there is
  no relation left to name:** the 2026-07-28 split completed 2026-07-30 and the two
  projects now share zero artifacts. Verb mapping deliberately left open — `genesis init`
  collides with the shipped `marshal init <slug>`.
- **2026-07-28** — split from [[pyforge-genesis]] per the Charter §5 amendment
  ("owning is becoming — at the planning tier"). Genesis keeps the constitutive records;
  the installer becomes this Dream, owned by the Marshal. The chain (Spec, PRD,
  architecture, epics) moves to `pyforge-marshal` — physically blocked until Marshal's
  planning tree is sharded, because both trees are currently flat and their `prd.md` /
  `architecture.md` / `epics.md` would collide.
