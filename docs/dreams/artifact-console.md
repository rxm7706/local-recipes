---
title: Artifact console — the factory board, hosted as a chat artifact
type: dream
owner: marshal
status: archived
archived-reason: retired
---

# Artifact console — the first attempt at making the factory legible

## The Dream

One page showing the whole factory at a glance — every project, every story,
what shipped and what is in flight — published as a **claude.ai Artifact**, so
it could be shared with a link and updated conversationally without any repo,
build step, or hosting.

## Why it was archived

**Retired, superseded.** The Artifact was ephemeral in exactly the way a source
of record must not be: it lived outside version control, could not be
regenerated from repo state, and drifted the moment anyone landed a commit. Its
successor — [[factory-console]], now the **Guildhall** — is generated from the
repo by `docs/dashboard/generate.py`, published to GitHub Pages, and governed by
a Spec whose surface check reds when the code moves without the contract. Same
intent, durable substrate.

## Kinships

[[factory-console]] (its successor, realized) · [[regenerable-factory]] (the
principle it violated: everything under a spec it can be rebuilt from).

## Realization log

- **2026-07** — replaced by the GitHub Pages console at
  `https://rxm7706.github.io/local-recipes/`.
- **2026-07-25** — **ARCHIVED (retired)** during the Dream-lifecycle
  reconciliation; formerly a hardcoded console entry with no Dream file behind it.
