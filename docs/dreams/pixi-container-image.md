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
- **2026-08-14** — **Air-gapped realization requirements (operator, from the source original
  pixi-container-image.md):** the source Dockerfile is itself the airgap mechanism; its specifics
  should transfer intact if this is ever built: (1) the base is an internally-certified
  UBI8-minimal pulled from the enterprise registry, never public Docker Hub, and the produced
  image publishes back to that registry so K8s/OCP pulls (per today's operator decision) never
  leave the perimeter; (2) the pixi binary downloads from an Artifactory generic-repo mirror
  (`ARTIFACTORY_URL` + `ARTIFACTORY_REPO_PATH`, with a `${PIXI_VERSION%%.*}.x` major-version
  subdirectory) — direct prefix.dev download is an explicit source non-goal; (3) credentials
  cross the build boundary only via BuildKit `--mount=type=secret` read inline as
  `$(cat /run/secrets/...)` — never ENV, never COPY, never persisted in any layer — the
  build-time twin of `_http.py`'s env-only runtime posture, followed by `.pem`/`.enc` cleanup;
  (4) TLS to the mirror trusts the internal CA via a `CA_PATH` build arg, the image-build analog
  of the truststore half of `_http.py`'s runtime chain; (5) OS updates run `microdnf update`
  against internal `rpm-OraLinux*` repos only (credentials via `--setopt` from the same mounted
  secrets, `tsflags=nodocs`, caches cleaned), on a weekly rebuild cron so patching continues with
  no container ever reaching the public net; (6) downstream layers that later run `pixi install`
  resolve their channels from the same Artifactory conda mirrors this repo's pixi channels
  already swap to.
