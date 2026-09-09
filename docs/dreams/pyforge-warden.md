---
title: Warden — the gate that never lies
type: dream
owner: warden
status: realized
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

## What is real

- **43/43 stories merged** across epics 1–11
  (`_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml`),
  FR1–FR40 frozen, schema 1.1.0, honest dashboard live. Built loop-driven by
  [[pyforge-marshal]]. Epics 7–11 post-date the original v1 scope: the eligibility
  union (7), the web face (8), the PR-gate hook book + scanner plugins (9), the
  skill/persona/portal slice (10), and the two advisory lenses (11). Epic 12 was
  minted 2026-09-09 for [[golden-path-conda-blind-spot]].
- **In effect, not merely merged:** `warden scan` is the estate's sole PR verdict, and
  `scripts/platform-deploy-verify-promotion.py:31` refuses any digest whose recorded
  verdict is not `clean`.
- Spec: `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/`
  (Tier 2, `shipped`); `docs/specs/pyforge-warden.md` is the absorbed legacy Tier-1
  intake. Package at `src/shared/packages/pyforge-warden/`.

## Realization log

- **2026-07-15/16** — spec-first; v1 re-baselined (D12).
- **2026-07 (through 07-18)** — bmad-loop implementation to 23/31; PAUSED,
  resume at 6.3.
- **2026-07-23** — Dream retro-seeded; chapter deck `presentations/pyforge-warden/`
  (the deck-family exemplar). Registry-perimeter ring links to [[enterprise-airgap]].
- **2026-07-23 (gist audit)** — grounding: the Phase-0 deep review (47 KB), the Python Dependency Policy sketch, and the Enterprise Python Manifest (Assured-OSS lists → the vetted-base row) all pre-figure v1 (`docs/intake/gists/`).
- **2026-09-09** — Fleet readiness pass (operator-approved decision batch,
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`).
  § What is real re-grounded against the live ledger (23/31 → 43/43; epics 7–11 named).
  Realization re-confirmed under the *exercised-in-the-estate* gate rather than the merge
  gate: warden is the sole PR verdict and `platform-deploy` reads it. Two ledger-vs-in-effect
  gaps found on OTHER warden Dreams — the web face's engine import and the eligibility CLI
  — recorded on their own Dreams and Specs, not here.
