---
title: Genesis installer — the seed, made executable
type: dream
owner: marshal
status: archived
archived-reason: absorbed
---

> **Narrative consolidated 2026-08-02 (dream-level only).** This Dream's narrative now lives
> in [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md) under "Kept separate on purpose."
> Unlike this session's other Marshal satellite retirements, **its downstream chain is
> untouched and stays fully live**: `spec-genesis-installer`, `prds/prd-genesis-installer-2026-07-25/`,
> `architecture/architecture-genesis-installer-2026-07-25/`, and `epics-genesis-installer.md`
> all remain exactly as they were — real, substantial, Marshal-owned buildable work with its
> own FR/AD range, deliberately kept separate from `marshal` the CLI's own FR-1..65. Only the
> top-level Dream file consolidates; nothing downstream was merged, retired, or reworded.

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

- **The Spec** — `spec-genesis-installer` (9 capabilities), with its extraction manifest:
  what is **copied** (conventions, skills, workflows) vs **referenced** (bmad-method
  releases) vs **generated** (per-repo Dreams).
- **The proof** — this repository was the first brownfield adoption, installed by hand from
  `archive/docs/bmad-setup-plan.md`. The installer is that procedure, generalized.
- **The chain** — PRD, architecture and epics exist (Foundation & the Write Guard · the
  Managed-Region Engine · Detect & Plan), inherited from the pre-split `pyforge-genesis`
  project.

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
