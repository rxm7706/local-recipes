---
title: pyforge-foundry-full is the laptop SBOM
type: dream
owner: steward
status: dreamt
seeded: 2026-09-21
pr: https://github.com/rxm7706/local-recipes/pull/1564
branch: sbom/pyforge-foundry-full-compose
kins:
  - pyforge-steward
  - pyforge-mason
  - pyforge-marshal
  - foundry-regenerate-not-fold
  - package-inventory-eligibility
---

# pyforge-foundry-full is the laptop SBOM

## The Dream

A PyForge developer laptop installs **one** pixi environment — `pyforge-foundry-full` — and from that env alone can:

1. `pixi install -e pyforge-foundry-full`
2. Launch the apps (stations / guild / Langflow + dashboard when the agent-platform gap closes)
3. Run tests, lint, and local CI mirrors
4. Bring up the platform local stack (Postgres + pgvector, Redis, Silo/object storage) via **existing** features
5. Use optional plugins by composing features that already exist — never by inventing a `desktop-lab` kitchen sink

The fat `local-recipes` **feature blob** is not the SBOM. It is a historical pin dump. Foundry-full is the checkable bill of materials.

> If the laptop still needs the fat feature to work, the SBOM is incomplete — that is a ticket, not a compose line.

## Why now (what this session proved)

- Estate work needs a **checkable** SBOM, not “whatever solves if we compose everything.”
- Phase 1 compose + lock work already lives on **PR #1564** (`sbom/pyforge-foundry-full-compose`). Without a Dream → Spec, later phases drift and agents “fix” solves the wrong way.
- Live incidents this session made the constraints non-negotiable:
  - Remote `pixi.toml` was twice reduced to a stub (`# PLACEHOLDER_WILL_REPLACE`, ~26 bytes) by auth-probe / `push_files` experiments. CI went red immediately. **Never** push placeholder or path stubs to prove write access.
  - An assistant briefly bumped `postgresql` to `>=18.3,<19` so `platform-dev` would union-solve with libpq 18. **Operator rejected that.** Postgres major **17** is intentional.
  - Dropping `platform-dev` to dodge the solve was also rejected. Keep the feature; fix the libraries that force libpq 18.

## Root cause (libpq 17 vs 18) — learned 2026-09-21

Not “postgresql wants 18.” Other pins force **libpq 18**:

| Pin that forced libpq 18 | Fix (keep PG17) |
|---|---|
| `psycopg >=3.3.4` / `>=3.2.10` (e.g. pyforge-scribe, mcp-host, platform-ci-test) → `psycopg-c` needing libpq ≥18. Last line on libpq 17: **psycopg / psycopg-c 3.2.9** | `psycopg = ">=3.2.9,<3.2.10"` |
| `pgvector >=0.8.2` (floors like `>=0.8.6` on scribe-pg; `>=0.8.1` on platform-dev can float up) | `pgvector = ">=0.8.0,<0.8.2"` |
| `postgresql` itself | Stay `>=17.11,<18` everywhere in the estate local stack |

Local lock **did** solve with PG17 + `platform-dev` retained after those caps. That is the intended contract.

## Inclusion rule (not a name blacklist)

**In** foundry-full if:

- used by **PyForge code**, or
- needed by a **PyForge developer / operator** workflow

**Out** if unused kitchen-sink — even if pinned today under fat `local-recipes`.

**Never compose** the fat `local-recipes` feature. **No** `desktop-lab` feature.

Examples:

| Package | Stance |
|---|---|
| `vizro`, `dagster` via atlas | **In** when evidence is in code / feature deps |
| `wagtail` via python-agent-platform | **In** once that feature solves into the union |
| vizro-ai / dbt-* / minio / ollama / coderedcms fat-only piles | **Out** until code/operator need is shown |
| fat `local-recipes` feature as a whole | **Never** |

## Hard constraints (operator)

1. **PostgreSQL major 17** — `postgresql = ">=17.11,<18"`. Do not bump to 18 to make a union solve.
2. **Keep `platform-dev`** in `pyforge-foundry-full` features. Do not drop it to dodge the solve.
3. **Libpq17 caps** — `psycopg = ">=3.2.9,<3.2.10"`; `pgvector = ">=0.8.0,<0.8.2"`.
4. **Edit PR #1564 only** for this campaign (side Copilot PRs only if merged into the SBOM branch). Prefer open-for-review; operator merges.
5. **`pixi.toml` integrity** — must stay ~290KB+. After any write, verify `wc -c`, zero `PLACEHOLDER`, and PG17 / platform-dev still present. Restore from last known-good commit (`ffdb723e` lineage / local good tree) if corrupted; never leave a stub.
6. **Large-file writes** — embedding full `pixi.toml` / `pixi.lock` via MCP `push_files` with tiny test content is how corruption happened. Prefer Contents API with the real file, Copilot with explicit restore-from-git-history, or a valid PAT. Do not “probe auth” by overwriting the manifest.

## What it looks like when real

- [ ] `pixi install -e pyforge-foundry-full` succeeds on the estate’s laptop platforms
- [ ] Laptop gate green from that env alone (lint / tests / local CI / platform bring-up smokes) — Phase 2
- [ ] `platform-dev` still in the foundry-full features list
- [ ] Every `postgresql =` in scope is `>=17.11,<18`
- [ ] psycopg / pgvector caps held; lock reflects libpq 17 for the platform stack
- [ ] Langflow/dashboard either in-union or documented interim (`-e python-agent-platform` / `-e platform-dev`) with OpenTeams tickets
- [ ] Fat `local-recipes` / `desktop-lab` never composed
- [ ] OpenTeams tickets exist for every remaining CF / solve gap — Phase 3
- [ ] CFE / AGENTS / mason point at foundry-full — Phase 4
- [ ] CF gaps closed or explicitly deferred with owners — Phase 5
- [ ] Dream → Spec (`bmad-spec`) → numbered stories before further realization outside dreams/spec

## Phase plan (campaign map)

### Phase 1 — BoM core + full platform local stack *(PR #1564)*

**Target compose:** `build` + `grayskull` + `crm` + `conda-smithy` + `platform-dev` + `python-agent-platform` + `platform-object-storage` + `pnpm` (on existing python/guild feature).

**Landed (solvable union, 2026-09-21):** `build` + `grayskull` + `crm` + `platform-dev` + `platform-object-storage` + `pnpm`, with PG17 + libpq17 caps + lock refresh after stub restore.

**Residual solve gaps (ticket; do not compose fat `local-recipes`):**

| Gap | Blocker | Interim |
|---|---|---|
| `conda-smithy` | 3.x wants older `py-rattler` / `conda`; union has newer from `build` | Keep `pixi exec` lint path; ticket co-solve |
| `python-agent-platform` | `langflow` vs `pandas` / `onnxruntime` in station union | Dashboard/Langflow via dedicated env until union solves |

### Phase 2 — Checkable SBOM + laptop gate

CI install + `pixi list` + channel audit + **laptop gate**. Failure ⇒ SBOM incomplete, not “use fat local-recipes.”

### Phase 3 — OpenTeams triage

Ticket every CF gap (SEM / pip / node / npm) **and** every fat-only pin: promote (usage proven) or won’t-do. **Also** Phase 1 residuals above. Phase 3 is “tickets exist,” not “gaps closed.”

### Phase 4 — Point estate at foundry-full

CFE / AGENTS / mason / ops docs → `pixi install -e pyforge-foundry-full` as the default laptop SBOM.

### Phase 5 — Close conda-forge gaps

Execute the OpenTeams list until residual unions solve or are deferred with owners.

## Non-goals

- Bumping PostgreSQL to 18 to clear a solver conflict
- Dropping `platform-dev` to clear a solver conflict
- Composing fat `local-recipes` or adding `desktop-lab`
- Auth / MCP probes that overwrite `pixi.toml` with stubs
- Merging #1564 without operator review
- Skipping Dream → Spec → Story for “just one more pin”

## Session ledger (2026-09-21) — keep for Spec acceptance

- Stub corruption SHA / tip around `PLACEHOLDER_WILL_REPLACE` after `test push_files auth` commits; Copilot #1574 / #1575 stalled on “Initial plan” only — closed after direct restore.
- Restore landed via GitHub Contents API with operator PAT (`pixi.toml` ~291676 bytes; lock refreshed). Verify size before declaring CI-related work done.
- PR #1564 body holds the same plan + Dream outline; this file is the durable Dream seed.
- Tooling limits observed: Cursor cloud-agent usage exhausted; box `gh` / injected `GITHUB_TOKEN` invalid; user machine shell sometimes `spawn /bin/bash ENOENT`. Prefer working GitHub connector + real PAT for large blobs.
- Prefer open PRs for review; operator merges.

## After this seed

1. Run **`bmad-spec`** → Spec (`draft → ready`) with pin assertions and Phase 2 gate acceptance copied from above.
2. Mint numbered stories (Phase 2 gate; Phase 3 tickets for smithy + agent-platform + CF gaps) **before** more code outside dreams/spec.
3. Close Phase 1 on #1564 only when CI is green and the manifest is still the real ~290KB file.

## Mental model

```
include  = PyForge code OR PyForge developer/operator need
exclude  = unused kitchen-sink; never compose fat local-recipes
PG17     = intentional; cap psycopg/pgvector instead of bumping Postgres
platform-dev stays; ticket union gaps; edit #1564 only
Dream → Spec → Story before more realization
```
