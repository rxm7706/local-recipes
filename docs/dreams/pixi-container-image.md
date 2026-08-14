---
title: A shared base container image with pixi already installed, if this repo ever ships one
type: dream
owner: mason
status: dreamt
---

# A shared base container image with pixi already installed, if this repo ever ships one

## The Dream

The source dream's actual value — every containerized project inheriting one consistent,
credential-safe pixi installation layer instead of each team hand-rolling its own — presupposes
an organization shipping many containers that all need pixi. This repo ships none. Mason's own
`docker`-mode build path (`cfe.py`'s `build_docker`) uses Docker as a RECIPE cross-compilation
isolation mechanism, not as a shipped application container — a genuinely different concern this
Dream must not be confused with. Captured for parity, not because a real gap exists today.

## What it looks like when real

Left thin, deliberately, since no PyForge artifact currently ships as a container:

- IF this repo (or a station's own artifact) is ever containerized, a shared base layer with pixi
  pre-installed is the right pattern to reach for rather than each container hand-rolling its own
  install — this Dream is where that design would live.
- Credential handling (build-time secret mount, never baked into a layer) is the one piece worth
  retaining regardless of WHEN this gets built, since it's a security discipline, not an
  implementation detail specific to WF's own Artifactory.

## What is real

Nothing. No Dockerfile exists anywhere in this repo's own tracked source (checked directly — the
only `Dockerfile`-named files present are third-party dependency artifacts inside `.pixi/envs/`
and one unrelated test fixture). Mason's `build_docker` mode is a recipe-build execution
mechanism, not an application-shipping concern — confirmed by reading `models.py`'s own Story 2.6
documentation before drafting this, specifically to avoid mistaking the two for overlap.

## Constraints

- **Not to be built until a real containerized artifact exists.** Building a base image with
  nothing to `FROM` it would be pure speculation.

## Non-goals

- **Not multi-architecture support** — moot until a target exists; source dream's own v1 was
  x86_64-only anyway.
- **Not confused with mason's `build_docker` recipe-build mode** — genuinely different concern,
  called out explicitly so a future reader doesn't conflate them.

## Full feature audit against `pixi-container-image`

| Source feature | Disposition | Why |
|---|---|---|
| UBI8-minimal base + pixi pre-install | **Omitted, no target** | No PyForge artifact ships as a container. |
| BuildKit `--mount=type=secret` credential handling | **Pattern retained** | The one piece worth keeping regardless of timing — a security discipline, not WF-specific. |
| Jenkins + `SharedLibrary_cicd` CI/CD, weekly rebuild cron | **Omitted, WF-infrastructure-specific** | This repo runs plain GitHub Actions; no Jenkins presence anywhere. |
| Prisma scan, OCI labels, `microdnf` hardening | **Omitted, no target** | Container-hardening detail with nothing to harden yet. |

## Kinships

[[pyforge-mason]] (nominal owner by the source label; genuinely unclaimed until a container
artifact exists) · [[reusable-cicd-workflows]] and [[miniforge-installer]] (siblings in the same
source org's Tier-3 batch, sharing the same "no current PyForge target" disposition)

## Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit.
  Checked directly for any existing container artifact or Docker-shipping concern before drafting
  (none found; mason's `build_docker` mode is a recipe cross-compilation mechanism, not an
  application-container concern, confirmed by reading its own source docstring). Kept
  intentionally thin — the credential-handling discipline is the only piece worth retaining
  independent of timing.
