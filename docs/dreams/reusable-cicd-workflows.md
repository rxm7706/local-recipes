---
title: A centrally-maintained CI/CD workflow family, if this repo ever needs more than plain Actions
type: dream
owner: mason
status: dreamt
---

# A centrally-maintained CI/CD workflow family, if this repo ever needs more than plain Actions

## The Dream

The source dream's actual subject — a 63-family EPLX system of reusable GitHub Actions workflows
built on Jenkins/Harness/Vault/Kaniko/FCD-governance/ThreadFix, letting any pixi project reach
production with zero custom CI logic — solves a problem this repo doesn't have: this repo has
ONE consuming project (itself), running on plain GitHub Actions (`detectors.yml`,
`staged-recipes-linter.yml`, `dashboard.yml`), with no Jenkins, no Harness CD, no enterprise
governance gate, and nothing else to centrally maintain workflows FOR. Captured for parity, not
because a real gap exists.

## What it looks like when real

Left thin — no scoped feature, because the premise (multiple consuming repos needing shared,
centrally-maintained CI) doesn't hold here yet:

- IF this repo's workflows ever need to be shared across multiple consuming repos (a genuine
  multi-repo estate, unlike today's single mono-repo), the source dream's two-tier architecture
  (step workflows + flattened entry points) is a reasonable pattern to reach for.
- The one concretely transferable idea, independent of that premise: this repo's own
  `detectors.yml`/`staged-recipes-linter.yml` could plausibly run some of their own steps in
  parallel rather than serially, the way the source dream's build engine does (documented 53%
  speedup from parallel lint/test/build/typecheck in one job) — but no specific current bottleneck
  was found to justify this as more than a speculative future optimization; checked both existing
  CI workflow files directly and found neither an obvious serial-that-should-be-parallel
  structure nor evidence either is currently slow enough to warrant it.

## What is real

Nothing built or missing — this repo's existing `detectors.yml` and `staged-recipes-linter.yml`
already do what this repo needs, on plain GitHub Actions, with no shared-workflow-family problem
to solve.

## Constraints

- **Not to be built until a second consuming repo exists.** The entire premise of a "reusable
  workflow family" requires more than one consumer; building one for a single mono-repo would be
  pure ceremony.

## Non-goals

- **Not Jenkins, Harness, Vault, Kaniko, or FCD governance** — none of this repo's infrastructure.
- **Not GitLab CI** — this repo uses GitHub Actions exclusively.

## Full feature audit against `reusable-cicd-workflows`

| Source feature | Disposition | Why |
|---|---|---|
| Two-tier reusable workflow architecture (step workflows + entry points) | **Pattern noted, no target** | Reasonable pattern IF a multi-repo estate ever exists here; premise doesn't hold today. |
| Parallel lint/test/build/typecheck in one job | **Noted as a possible future optimization, not scoped** | No specific current CI bottleneck identified to justify building this now. |
| `PIXI_FROZEN: true` frozen installs | **Already this repo's own convention** | Not something to port — this repo already runs pixi tasks with frozen lockfiles as standard practice. |
| Kaniko in-cluster container builds | **Omitted, no target** | No containers ship from this repo (see [[pixi-container-image]]). |
| Prisma/Checkmarx/BlackDuck scanning, FCD governance gate, ThreadFix | **Omitted, WF-infrastructure-specific** | No equivalent enterprise scanning/governance infrastructure exists or is planned here. |
| `vault-action`, HPOS Object Storage, Kafka-triggered Harness CD | **Omitted, WF-infrastructure-specific** | Same. |

## Kinships

[[pyforge-mason]] (nominal owner by the source label; genuinely unclaimed until a multi-repo
estate or a real CI bottleneck exists) · [[pixi-container-image]] and [[miniforge-installer]]
(siblings in the same source batch, same "no current PyForge target" disposition)

## Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit.
  Checked this repo's actual CI workflows (`detectors.yml`, `test-all.yml` and siblings) directly
  before drafting rather than assuming the source dream's premise applies — found no multi-repo
  estate, no Jenkins/Harness presence, and no obvious serial-CI bottleneck the source dream's
  parallel-job pattern would concretely fix. Kept thin and honest about the mismatch rather than
  manufacturing a scoped feature set with no real target.
- **2026-08-14** — **Air-gapped realization requirements (operator, from the source original
  reusable-cicd-workflows.md):** the source family is a complete worked example of disconnected
  CI, recorded here against the day a second consuming repo exists: (1) toolchain bootstrap never
  touches the public internet — Miniforge downloads from internal object storage (HPOS), not
  GitHub releases, and every build runs `PIXI_FROZEN: true` against `pixi.lock`; (2) channel
  topology is committed, credentials are not — consumer repos carry a `.condarc-cicd` naming the
  enterprise conda channels (the mirror-URL analog of this repo's swappable pixi channels), while
  secrets inject per-job via `vault-action` (HashiCorp Vault), the CI counterpart of `_http.py`'s
  env-vars-only rule; (3) container builds are in-cluster Kaniko (no Docker daemon) with separate
  `builder_base_image`/`runtime_base_image` inputs, both pulled from the internal registry and
  published to Artifactory docker-local — composing with [[pixi-container-image]]'s base layer
  and today's K8s/OCP deployment decision; (4) artifacts publish to Artifactory
  conda-local/pypi-local with checksum verification, and inter-job data moves through internal
  object storage rather than GitHub-hosted artifact storage; (5) the scanning/governance slots
  (Prisma, Checkmarx/BlackDuck, ThreadFix, FCD gate) all run against internal services — a
  PyForge equivalent would fill them with Warden's registry-perimeter gates on Artifactory
  ([[enterprise-airgap]]'s frontier), not WF's own scanners.
