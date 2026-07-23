---
title: Warden — the gate that never lies
type: dream
status: in-spec
---

# Warden — the compliance gate that never false-greens

## The Dream

The Guardian's dream: **one gate for both Python worlds** — PyPI applications
and the conda/conda-forge data stacks — interrogating every dependency across
six axes of trust (hygiene · security · license · currency · provenance ·
maintenance) and returning one honest verdict. The soul of the dream is a
negative promise: **Warden refuses to fake a pass.** An honest "not verified"
beats a false "all clear," at fleet scale (20k+ repos), without ever mutating
the host or the source.

## What it looks like when real

- One CLI, pluggable engines (deptry, osv-scanner + KEV/EPSS, license-expression,
  EOL ladders), one schema-validated ComplianceReport + CycloneDX SBOM, a frozen
  exit-code contract `{0,1,2,130}` and the verdict lattice.
- Waivers as code (expiring, committed); baselines that gate only *new* debt;
  an opt-in fix-PR actuator; the three-ring vision (consumption edge → registry
  perimeter → public upstream).

## What is real (in-build)

- **23/31 stories merged** (epics 1–4 + 6.1/6.2/6.4/6.10), FR1–FR40 frozen,
  schema 1.1.0, honest dashboard live. Remaining: 6.3 (in progress), 6.5–6.9,
  then Epic 5. Built loop-driven by [[pyforge-marshal]].
- Spec: `docs/specs/pyforge-warden.md` (legacy tier); package at
  `src/shared/packages/pyforge-warden/`.

## Realization log

- **2026-07-15/16** — spec-first; v1 re-baselined (D12).
- **2026-07 (through 07-18)** — bmad-loop implementation to 23/31; PAUSED,
  resume at 6.3.
- **2026-07-23** — Dream retro-seeded; chapter deck `presentations/pyforge-warden/`
  (the deck-family exemplar). Registry-perimeter ring links to [[enterprise-airgap]].
- **2026-07-23 (gist audit)** — grounding: the Phase-0 deep review (47 KB), the Python Dependency Policy sketch, and the Enterprise Python Manifest (Assured-OSS lists → the vetted-base row) all pre-figure v1 (`docs/specs/gists/`).
