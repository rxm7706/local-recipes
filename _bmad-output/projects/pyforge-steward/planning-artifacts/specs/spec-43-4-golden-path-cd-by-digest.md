---
title: "Golden Path CD by digest"
type: "feature"
created: "2026-09-02"
status: "done"
review_loop_iteration: 1
followup_review_recommended: false
updated: "2026-09-03"
baseline_commit: "58ee07a0"
baseline_revision: "a323a9cbcd0ed7c8f35a44e9825de10a1eb94662"
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
  - summary: >-
      GitOps repository / Argo profile (steward deploy-profile).
  - summary: >-
      golden-path-promotion rebuilds all three images after the container job — extra CI minutes per platform-ci run.
    evidence: |-
      The promotion job runs three docker builds independently rather than reusing container job artifacts.
    location: >-
      .github/workflows/platform-ci.yml
    severity: medium
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

- [x] CI push-by-digest + artifact
- [x] Chart `required` + refusal test
- [x] Deploy workflow
- [x] 12.9 gating
- [x] Ledger `43-4-golden-path-cd-by-digest` → `review` then `done` via `sprint-ledger-sync`.

## Review Triage Log

### 2026-09-03 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 1: (high 0, medium 1, low 0)
- reject: 2
- addressed_findings:
  - `[low]` `[patch]` Optional registry push used invalid `docker push repo@digest` syntax — retagged with `:${{ github.sha }}` and push by tag.

## Auto Run Result

Status: done

Summary: Golden-path CD by digest — chart refuses bare/`latest` renders; Platform CI publishes a combined `golden-path-promotion` artifact (three image digests + Warden JSON); new `platform-deploy.yml` verifies the artifact and helm-templates by digest only.

Files changed:
- `src/platform/deploy/charts/platform/templates/_helpers.tpl` — digest-or-pinned-tag required; `latest` refused
- `src/platform/deploy/charts/platform/values.yaml` — removed mutable `latest` defaults
- `src/platform/tests/test_chart_invariants.py` — auto-inject test digests; refusal tests
- `.github/workflows/platform-ci.yml` — `golden-path-promotion` job; optional registry push
- `.github/workflows/platform-deploy.yml` — deploy-by-digest workflow (new)
- `scripts/platform-golden-path-promotion.sh` — record digests + Warden verdict (new)
- `scripts/platform-deploy-verify-promotion.py` — refuse digests without verdict (new)
- `src/platform/deploy/README.md` — digest requirement documented
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml` — `43-4` → `done`

Review findings: 1 patch applied; 1 deferred (golden-path-promotion rebuilds images after `container` — CI cost); 2 rejected (noise).

Follow-up review recommendation: false (1 low patch; score 1 < 5).

Verification:
- `82 passed` — `src/platform/tests/test_chart_invariants.py` (platform-dev helm on PATH)
- `actionlint` clean on `platform-deploy.yml`; `platform-ci.yml` only pre-existing shellcheck infos
- `pixi run -e local-recipes sprint-ledger-sync --project steward` — wrote steward (239)

Residual risks: `golden-path-promotion` adds a third docker build pass on every platform-ci run; live registry push path not exercised without `PLATFORM_CI_PUSH_REGISTRY` + `PLATFORM_CI_REGISTRY`; GitOps/Argo profile still deferred.

`helm template` invariants; workflow lint (`actionlint` via `pixi exec`).

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 43.4). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
