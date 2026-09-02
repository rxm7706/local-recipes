---
title: "Golden Path CD by digest"
type: "feature"
created: "2026-09-02"
status: "ready-for-dev"
updated: "2026-09-02"
baseline_commit: "58ee07a0"
severity: "HIGH"
context:
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md"
  - ".github/workflows/platform-ci.yml"
  - "src/platform/deploy/charts/platform/values.yaml"
  - "src/platform/deploy/charts/platform/templates/_helpers.tpl"
warnings: []
deferred:
  - "GitOps repository / Argo profile (steward deploy-profile)."
---

<intent-contract>

## Intent

**Problem:** CI builds and tests images but pushes nothing; the chart defaults to
`tag: latest` with `pullPolicy: Always`, the opposite of "the artifact that
passed Warden is the artifact Steward deploys". No deploy workflow, no digest
record, no promotion. Story 12.9 (OCP smoke) is optional. Red-team **B-4**,
directive **R-15**.

**Approach:** Push images by digest from CI; make `image.tag` (or `image.digest`)
`required` with no `latest` default; record the Warden verdict against the
digest as a build artifact; add a `deploy` workflow (or GitOps repo pointer)
that promotes exactly that digest; make 12.9 a required check the moment
Actions minutes exist.

## Acceptance Criteria

- Given `helm template` with no `image.digest`/pinned tag, when rendered, then it fails naming the values path; `latest` is refused.
- Given a green `platform-ci` run, when it completes, then it publishes the image digest and the Warden verdict JSON as one artifact.
- Given the `deploy` workflow, when triggered with a digest, then it renders the chart with that digest only and refuses a digest with no Warden verdict.
- Given `.github/workflows`, when read, then 12.9 exists as a job gated on a minutes-available variable, not deleted.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `43-4-golden-path-cd-by-digest`. Host never imports `pyforge.*`. Warden is the only PR gate (Q8). Registry stays relocatable (CAP-6).

**Block If:** Implementation would add a second quality verdict, or a deploy that pulls `latest`.

**Never:** A mutable tag in a deployed values file.

</intent-contract>

## Tasks

- [ ] CI push-by-digest + artifact
- [ ] Chart `required` + refusal test
- [ ] Deploy workflow
- [ ] 12.9 gating
- [ ] Ledger `43-4-golden-path-cd-by-digest` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`helm template` invariants; workflow lint (`actionlint` via `pixi exec`).

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 43.4). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
