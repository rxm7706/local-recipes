# Glossary — Doctor (pyforge-doctor)

Companion to `SPEC.md`, added 2026-11-01 (EGM fleet audit, finding DOC-M-C6; the decision is in
`.memlog.md`). Pointer-only: one line per word the Spec uses that its reader cannot resolve from the
Spec alone. A word defined elsewhere is named here with where it is defined, never restated; only the
station terms nothing else defines carry a gloss.

## Defined elsewhere

- **Station, Charter, `CAP-n`, `FR-n` / `NFR-n`, `AD-n` and its `canopy:` / `pap:` / `fnd:` prefixes, A and B, CFE, Twin, Tier 0 / 2 / 3, the rebase, Path B** — `docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md` § 0.
- **`spec-<x>:CAP-n`, `← CAP-m`, `(ready <date>)` / `(shipped <date>)`** — CHAIN-STANDARD § 2; the `FR` / `NFR` id grammar is § 6.
- **verdict, gate, detector, check, preflight, advisory; scope `repo` / `runtime`; exit codes** — `docs/reference/judgement-vocabulary.md`.
- **Check, Finding, Source, Watch axis, Prescription, Partition, operability exit code** — the PRD's § 3 Glossary, `../../prds/prd-pyforge-doctor-2026-07-25/prd.md`.
- **`AD-n` as this Spec cites it** — `../../architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md`; the ones it binds are restated in `SPEC.md` § Constraints.
- **`detectors-ci`** — the CI subset of the detector registry `scripts/detectors.py`: `docs/reference/detectors.md`; it is the *harness gate* sense of **gate** in judgement-vocabulary.md, never a verdict.
- **`fleet-picture`** — the read-only fleet report, `scripts/fleet_picture.py`: `docs/how-to/monitor-the-fleet.md`.
- **`flag-exempt:`** — `docs/reference/story-spec-flag-block.md` § The `flag-exempt:` value (`docs/governance/spec-feature-flag-governance/SPEC.md`).
- **Live-proof surface** — `live-proof-surfaces.md` (CAP-77).

## Station terms

- **`REGISTRY`** — Doctor's table of `SourceRegistration` rows (`src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py`), one per `Source`, each naming its scope, its subject station (whose artifact it reads) and its owning station (who holds the verdict).
- **The dispatcher** — `python -m pyforge.doctor.sources <source> [--json]` (`sources/__main__.py`), which runs one source by name.
- **`cli_bridge`** — the one module in the package allowed to spawn a subprocess (AD-5, `SPEC.md` § Constraints).
- **ATTENTION block** — the closing section of `fleet-picture`'s output, its `needs` and `watch` lines; a Doctor probe adds one `watch` line per WARN, its message cut at 110 characters, or one `could not check …` line when the probe raises (CAP-89, CAP-91).
