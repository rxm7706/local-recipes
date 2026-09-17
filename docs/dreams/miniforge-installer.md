---
title: A custom-branded Python distributable, if this repo ever needs one
type: dream
owner: mason
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-mason]]** on 2026-09-17 (one-chain-per-station mason fold; folded from `miniforge-installer`).
# A custom-branded Python distributable, if this repo ever needs one

## The Dream

The source dream's actual problem — developers and CI agents getting Python from three divergent
per-platform paths, none of them locked to an org's own Artifactory-only conda channels — doesn't
exist here. This repo's own `pixi.toml` already declares public channels directly
(`conda-forge`, `SelfExplainML`), with no Artifactory-only constraint to route around and no
divergent per-platform install story to unify — every contributor and every CI runner already
gets Python the same way, through pixi, from the same public channels. Captured for parity, not
because a real gap exists.

## What it looks like when real

Left thin — no scoped feature, because the premise (an org needing to lock its own custom Python
distributable to a private channel) doesn't hold here:

- IF this repo (or a future enterprise deployment of it, per [[enterprise-airgap]]) ever needs a
  Python distribution locked to a private/mirrored channel set, the source dream's
  Conda-Constructor-based build shape is a reasonable pattern to reach for — but that's
  [[enterprise-airgap]]'s own concern to raise if it ever becomes real, not something to
  pre-build here speculatively.

## What is real

Nothing built or missing. `pixi` itself, installed directly per this repo's own
[[developer-machine-bootstrap]] (also just captured, also aspirational), already serves the role
a custom Miniforge distributable would serve here — one consistent way to get a working Python
environment, for every contributor and every CI runner alike.

## Constraints

- **Not to be built until a private-channel-locking need is real.** [[enterprise-airgap]] is the
  Dream that would surface that need if it ever materializes; this Dream should not get ahead of it.

## Non-goals

- **Not an alternative to `pixi`** — this repo's existing Python-provisioning story (pixi itself)
  already solves what this Dream's source solves differently.
- **Not multi-platform installer engineering** (Docker+QEMU cross-builds, Gradle orchestration)
  — no target to build for.

## Full feature audit against `miniforge-installer`

| Source feature | Disposition | Why |
|---|---|---|
| Custom-branded `Miniforge3_WF` installer | **Omitted, no target** | `pixi` already serves this repo's equivalent role; no private-channel-locking need exists. |
| `construct.yaml` (Conda Constructor blueprint) | **Pattern noted, no target** | Reasonable IF a private-channel need ever materializes via [[enterprise-airgap]]; not built speculatively. |
| CVE-pinned package patching | **Omitted, no target** | Nothing to patch without a distributable to patch. |
| Multi-platform build matrix (Linux x86_64/aarch64, macOS x86_64/arm64, Windows) | **Omitted, no target** | Same. |
| Gradle build system + dual CI (Jenkins + GitHub Actions) | **Omitted, WF-infrastructure-specific** | No Jenkins presence in this repo. |

## Kinships

[[enterprise-airgap]] (the Dream that would actually surface a private-channel-locking need, if
one ever becomes real) · [[developer-machine-bootstrap]] (the sibling Dream this one's role
already substantially overlaps with, via plain `pixi`) · [[pyforge-mason]] (nominal owner by the
source label; genuinely unclaimed)

## Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit.
  Checked `pixi.toml`'s own channel declaration directly before drafting — confirmed public,
  unlocked conda-forge channels with no Artifactory-only constraint this dream's source solves
  for. Kept intentionally thin; the more honest home for this concern, if it ever becomes real, is
  [[enterprise-airgap]], not a new standalone Dream.
