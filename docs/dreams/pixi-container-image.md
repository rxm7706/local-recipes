---
title: A shared base container image with pixi already installed, if this repo ever ships one
type: dream
owner: mason
status: realized    # 2026-09-09 — convention doc + guard test live; four Containerfiles, one pattern
---

# A shared base container image with pixi already installed, if this repo ever ships one

## The Dream

The source dream's actual value — every containerized project inheriting one consistent,
credential-safe pixi installation layer instead of each team hand-rolling its own — presupposes
an organization shipping many containers that all need pixi. This repo now ships three (see "What
is real" below), and all three independently converged on the same pixi-materialization discipline
rather than actually inheriting one shared pre-built layer — that convergence is what's real today,
not the shared-layer artifact itself. Mason's own `docker`-mode build path (`cfe.py`'s
`build_docker`) uses Docker as a RECIPE cross-compilation isolation mechanism, not as a shipped
application container — a genuinely different concern this Dream must not be confused with.
Captured for parity originally; partially realized now (see "What is real" and "Constraints") in
the discipline, not yet in a shared base image.

## What it looks like when real

Left thin originally, since no PyForge artifact shipped as a container at the time this Dream was
captured. Three now do (see "What is real"), so the "IF" below has partly resolved — not into a
shared pre-built base image, but into three independently-built images that converged on the same
pixi-materialization discipline and are now held to it explicitly:

- A shared base layer with pixi pre-installed is still the right pattern to reach for IF a fourth
  Containerfile, or a real divergence between the three that exist, ever makes hand-rolling the
  same builder stage three-plus times worth consolidating — this Dream is where that design would
  live; it hasn't been built because it hasn't been needed (see "Constraints").
- Credential handling (build-time secret mount, never baked into a layer) is the one piece that
  didn't wait for a shared base image to become real — it's already true today across all three
  Containerfiles, documented and guarded by
  `docs/reference/container-base-layer-convention.md`, since it's a security discipline, not an
  implementation detail specific to a shared base layer or WF's own Artifactory.

## What is real

The trigger fired. **Four** Containerfiles now ship in this repo's own tracked source:
`Containerfile` (root, Story 7.1), `src/platform/Containerfile` (Story 10.3),
`src/platform/compose/dbgpt/Containerfile` (Story 10.5), and
`src/platform/compose/mcp-host/Containerfile` (spec-mcp-era-isolation slice 1 —
`ghcr.io/prefix-dev/pixi:0.80.0` builder + `registry.access.redhat.com/ubi9/ubi-minimal:9.6`
runtime, no `ENV` credential). All four converged independently on the
same base-layer pattern — a registry-pinned `ghcr.io/prefix-dev/pixi` builder stage plus a minimal
runtime stage, no credential ever baked into a layer or `ENV`. That convergence is now written down
as policy in `docs/reference/container-base-layer-convention.md` and enforced by
`tests/packaging/test_containerfile_base_layer_convention.py` (which sweeps every `FROM`/`ENV` line
across the files it enumerates — three of the four today; see the 2026-09-09 log entry), alongside the pre-existing `scripts/pixi_version_registry.py` (which keeps
the pixi builder-stage tag in sync with `pixi.toml`'s `requires-pixi` floor). Mason's `build_docker`
mode remains the separate recipe cross-compilation concern this Dream never covers — confirmed by
reading `models.py`'s own Story 2.6 documentation before drafting this, specifically to avoid
mistaking the two for overlap.

## Constraints

- **The discipline is real; a repo-owned base image still is not.** The three Containerfiles above
  all build directly `FROM` the upstream `ghcr.io/prefix-dev/pixi` image — none of them, and nothing
  else in this repo, builds or publishes a custom pixi-preinstalled base image.
  `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pixi-container-image/SPEC.md`
  (the spec this Dream produced) keeps it that way deliberately: the official pixi image stays the
  base, and a shipped repo-owned base image stays out of scope until at least two Containerfiles
  diverge for reasons a shared custom base would actually solve — not true today, since all three
  still follow one documented pattern. This Dream's original "not to be built until a real
  containerized artifact exists" premise has therefore only partially resolved: the artifacts exist
  and the pattern they converged on is now documented and guarded, but the larger ask this Dream
  captures — an actual shared, repo-owned base image — remains speculative until a real divergence
  makes one worth building.

## Non-goals

- **Not multi-architecture support** — moot until a target exists; source dream's own v1 was
  x86_64-only anyway.
- **Not confused with mason's `build_docker` recipe-build mode** — genuinely different concern,
  called out explicitly so a future reader doesn't conflate them.

## Full feature audit against `pixi-container-image`

| Source feature | Disposition | Why |
|---|---|---|
| UBI8-minimal base + pixi pre-install | **Omitted, no target** | No PyForge artifact builds or publishes a shared, repo-owned, pixi-preinstalled base image — the three Containerfiles that now exist (see "What is real") each materialize pixi independently in their own builder stage rather than inheriting one. |
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
- **2026-08-22** — **Correction: the "nothing exists yet" premise is stale.** Story
  `spec-8-1-the-convention-is-written-and-guarded` (from `spec-pixi-container-image`) found the
  repo now ships three Containerfiles (root `Containerfile`, `src/platform/Containerfile`,
  `src/platform/compose/dbgpt/Containerfile` — Stories 7.1, 10.3, 10.5), all three already
  base-tag-pinned to `ghcr.io/prefix-dev/pixi` and free of any `ENV`-baked credential. Corrected
  "What is real" and "Constraints" above in place (prior entries left untouched) to state that,
  added `docs/reference/container-base-layer-convention.md` naming the three pillars (base-tag
  pinning, the multi-stage pixi-materialization shape, and the `--mount=type=secret`-only
  credential rule this Dream's own air-gapped requirements entry above already named as the piece
  worth retaining), and added `tests/packaging/test_containerfile_base_layer_convention.py` to
  statically guard against a future unpinned base or `ENV`-declared credential across all three
  files. No repo-owned base image was built or published — the upstream `ghcr.io/prefix-dev/pixi`
  image stays the base for every builder stage, per `spec-pixi-container-image`'s own Constraints.
- **2026-09-09** — **Realized, with a coverage gap named** (operator ruling,
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
  § 2.2). A **fourth** Containerfile — `src/platform/compose/mcp-host/Containerfile`
  (spec-mcp-era-isolation slice 1) — now ships and follows the same convention, so the
  "three Containerfiles, one pattern" reading above was one behind; corrected in place. The Spec
  flips `ready → shipped`. The gap: the two enumerations in the repo **disagree**.
  `scripts/pixi_version_registry.py:79-87` already covers all four, but
  `tests/packaging/test_containerfile_base_layer_convention.py:50-52` hard-codes only three, so
  the fourth file is **ungoverned by the convention guard**. It is compliant today; the finding is
  that nothing would notice if it stopped being. The fix is to **derive** the list (glob
  `Containerfile*`), not to append a fourth literal — a declared list where a derived one was
  needed. That fix is a code change and needs a story; it is not applied by this documentation
  pass.
