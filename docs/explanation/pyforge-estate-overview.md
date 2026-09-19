---
sources:
  - docs/dreams/pyforge-charter.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - src/platform/config/urls.py
  - src/platform/deploy/charts/platform/values.yaml
  - src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py
  - docs/how-to/one-chain-station-ops.md
verified: 2026-09-19
---

# PyForge Estate Overview

This document explains the architecture and operational model of the PyForge Estate. It details the BMAD (Build More Architect Dreams) methodology, the eight accountable stations, and the "Canopy" monolithic host design.

## The BMAD Methodology

PyForge operates as an Agentic Software Development Life Cycle (SDLC) driven entirely by autonomous agents. Humans capture their intent as "Dreams" (Tier 0). The system then generates code through a strict pipeline.

1. **Dream:** Human aspiration is recorded in `docs/dreams/`.
2. **Spec:** `bmad-spec` distills the Dream into a strict Contract (`SPEC.md`); the planning chain (`bmad-prd` / `bmad-architecture` / `bmad-create-epics-and-stories`) decomposes it into a PRD, an Architecture Spine, and Epics. Marshal (`marshal chain`, `marshal planning`) can orchestrate that regeneration unattended.
3. **Execution:** Autonomous agents execute the Stories to generate implementation artifacts and source code.
4. **Verification:** Independent stations gate quality and compliance. Agents cannot judge their own work.

:::note[Governed Execution]
Because code is mechanically generated and governed by Specs, you should never hand-edit a `SPEC.md` or a `sprint-status-ledger.yaml`. They are managed via `bmad-spec` and `pixi run -e pyforge-guild sprint-ledger-sync`. For operational instructions on running these commands, see [One-Chain Station Ops](../how-to/one-chain-station-ops.md).
:::

## The Eight Stations of the PyForge Guild

Work is divided among eight accountable "Smiths" (personas). Each holds a station with its own package under `src/shared/packages/pyforge-<station>/`.

| Station | Persona Role | Core Responsibility |
|---------|-------------|---------------------|
| **Herald** | The Proclaimer | Bridges Dreams to Claude Design decks (`herald deck`), and records progress, success claims and operational notices (`herald progress` / `success` / `notice`). |
| **Marshal** | The Commander | The BMAD-loop dispatch/loop supervisor: launches and lands story sessions (`marshal factory dispatch`, `marshal factory drain`, `marshal land`), watches runs (`marshal watch`, `marshal status`), and retires/refreshes loop homes. |
| **Atlas** | The Navigator | Maps dependencies and charts dual-ecosystem (Python and Conda) data pipelines (Kedro/DuckDB). |
| **Warden** | The Guardian | Secures the perimeter. Audits six axes of trust (hygiene, security, license, currency, provenance, maintenance) and is the sole PR gate (`warden scan`). |
| **Mason** | The Artisan Builder | Authors `recipe.yaml` files, resolves environments, and packages artifacts for cross-platform distribution (`mason recipe`, `mason package`, `mason environment`). |
| **Doctor** | The Physician | Runs pre-flight environment diagnostics and continuously monitors fleet and feedstock health. Findings stay advisory, never a second PR gate. |
| **Scribe** | The Chronicler | Curates team memory (`.claude/memory/`) into a knowledge graph. Captures decisions and retros for agent and human recall. |
| **Steward** | The Provisioner | Handles platform deployment, environment provisioning via `pixi`, credential lifecycle, and resource budget enforcement. |

## The Canopy Architecture

PyForge uses a hexagonal (ports-and-adapters) architecture at the package level and a modular monolith at the platform level. This monolithic design is known as the Canopy.

The system runs on one Django and ASGI process, backed by PostgreSQL and Redis. It has no microservices or scattered process trees.

### Platform Host

- **Lane 1 (CMS):** Wagtail mounts at `/` to act as the front door and public dossier (its admin is at `/cms/`).
- **Lane 2 (Portals):** Each station provides a reusable Django app using HTMX. These portals mount uniformly at `/stations/<name>/` (for example, `django-warden`).
- **Service Faces (MCP):** Programmatic APIs for each station are exposed as Model Context Protocol apps mounted at `POST /stations/<name>/mcp`.
- **Chrome:** `django-pyforge` provides the base layout, app switcher, and registration protocol. Portals register here instead of hardcoding routes.

### Domain Logic

The host never imports `pyforge.*`. The underlying business logic lives in isolated factory packages. A unified CLI (`pyforge <station> <noun> <verb>`, `src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py`) acts as the driving adapter for terminal interactions.

### Asynchronous State and Databases

Long-running asynchronous tasks avoid sticky sessions or dropped HTTP pools. They use a start/get pattern over PostgreSQL (`mcp_handles` mapped to supervisor `run_ids`). CloudEvents (v1.0) are published to the Redis Stream `pyforge.events` for cross-station communication.

Production Data Definition Language (DDL) is strictly separated from Django's ORM. It is managed by Liquibase via a Helm hook Job (`src/platform/deploy/charts/platform/values.yaml`).

:::tip[Schema Isolation]
The PostgreSQL instance is partitioned. General data lives in `public`, while specific engines have their own schemas (`langflow_schema`, `dbgpt_schema`). The ORM never crosses schemas.
:::

## Key Developer Invariants

Developers and agents must obey these invariants to keep the ecosystem healthy:

- **The Hand that Builds is Never the Gate that Judges:** Mason builds, and Warden judges. Marshal orchestrates, and Doctor verifies Marshal's conformance.
- **Wrap, Never Reimplement:** Stations are thin adapters over existing external tools. For example, `steward keys` shells out to the `age` CLI for encryption.
- **One Pixi Floor:** All packages share a single `pixi.toml` floor. Dependencies are resolved through dual ecosystems (Conda-forge and PyPI).
- **Dream First:** All work enters as a Dream in `docs/dreams/`, becomes a Spec, and receives a numbered Story before any code is generated.
