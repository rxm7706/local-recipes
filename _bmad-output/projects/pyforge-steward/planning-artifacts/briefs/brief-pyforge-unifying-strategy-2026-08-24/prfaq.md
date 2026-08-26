---
title: "PRFAQ: PyForge Enterprise Platform & Unified Agentic Operating System"
status: "superseded"
created: "2026-08-23"
updated: "2026-08-24"
chain: "pyforge-unifying-strategy"
stage: "verdict"
superseded_by: "../../specs/spec-pyforge-unifying-strategy/SPEC.md"
inputs:
  - "docs/dreams/pyforge-unifying-strategy.md"
---

> **Pre-audit — retained as the working-backwards exercise, not as a description of the system.**
> Written 2026-08-23, before the convergence audit found `src/platform/` already shipped and before
> Phase-2 research invalidated four Dream directives. Its narrative value survives; several of its
> technical claims do not. Specifically wrong here: `pyforge_host` is a role name, not an artifact;
> Lane 2 portals do not live at `/stations/{station}/` (warden's is at `/compliance/` until FR-9a);
> the `:8001–:8008` port assignments were never real; Wagtail **CRX** was dropped when CodeRed proved
> unmaintained; and the BS-1 answer below describes a SQLite/PostgreSQL dual driver that does not
> exist — Scribe ships a single flat JSON file. Five-tier symmetry in this FAQ is the **03** station
> shape, not every 01/02 task (Dream Grounding Q2). The binding contract is `SPEC.md`; the
> corrections are tabulated in `addendum.md`.
>
> **2026-08-26:** do not append Epic 34–37 realization here. The binding contract
> is `SPEC.md`; the living Dream and PRD carry the first-slice stamp. This file
> stays the 2026-08-23 working-backwards exercise.

# PyForge Unveils the First Unified Developer & AI Operating System for Modern Python & Conda Packaging

## A single enterprise Platform Canopy unites 8 specialized capability stations across web portals, CLI commands, and autonomous Model Context Protocol (MCP) AI agents.

**SAN FRANCISCO, CA — August 23, 2026** — Today, the PyForge team announced the general availability of **PyForge Enterprise**, the industry's first Unified Developer & Autonomous AI Operating System. Designed from the ground up to eliminate the fragmentation of managing software supply chains, package recipes, and compliance audits across isolated command-line tools, PyForge delivers an integrated **Hub-and-Spoke Enterprise Architecture**. By combining a central Platform Canopy (`pyforge_host` / Guildhall) with **8 specialized capability stations** (`warden`, `atlas`, `mason`, `marshal`, `doctor`, `herald`, `scribe`, `steward`), PyForge provides complete **5-Tier Symmetry**—enabling human developers, enterprise operators, and autonomous AI agents to collaborate seamlessly over a shared execution fabric.

Before PyForge, maintaining enterprise conda-forge recipes and Python supply chains was an agonizing, disjointed manual labor. Security auditors used separate vulnerability scanners that emitted disconnected SARIF files. Packaging engineers manually tuned compiler flags in obscure YAML files. Platform operators had zero visibility into cloud resource quotas, while autonomous AI coding agents operated in isolated terminal silos without structured access to corporate memory or deterministic compliance gates. A single breaking upstream dependency or CVE vulnerability could paralyze development teams for days while developers pieced together fragmented logs.

PyForge transforms this chaos into an orchestrated, self-healing ecosystem. Powered by **Pixi** for universal cross-platform parity and modern server-driven UI architecture (`django-pyforge`), PyForge establishes a central web front door at `/` (the Guildhall) mounting 8 zero-model HTMX station portals. Paired with high-performance FastAPI compute microservices (`:8001–:8008`), dedicated domain skills (`SKILL.md`), and embedded autonomous agent personas (`Agent-Warden`, `Agent-Mason`, `Agent-Atlas`, etc.), PyForge automates the entire supply-chain lifecycle: from raw human inspiration to automated wheel compilation, continuous compliance gating, diagnostic auto-remediation, and broadcast release reporting.

> "For the first time, human developers, security teams, and autonomous AI agents share the exact same operating picture," said the Principal Enterprise Architect of PyForge. "Whether you interact via the command line, click through a reactive web portal, or let an AI agent orchestrate an overnight build sprint, the execution contracts, identity propagation, and governance policies remain 100% deterministic."

### How It Works

1. **The Central Front Door (Lane 1 — The Guildhall at `/`):** Operators and developers log in through enterprise Keycloak Single Sign-On (OIDC). The Wagtail CRX-powered Guildhall provides an instant knowledge portal, corporate brain, and the universal `django-pyforge` App Switcher.
2. **Interactive Station Portals (Lane 2):** Navigating to any station (e.g. `/stations/warden/`) reveals a specialized, server-rendered HTMX action portal where operators can view real-time compliance scorecards, audit package dependency trees, synthesize new recipes, or trigger 1-click self-healing tasks.
3. **Embedded AI Copilot & Council (Lane 2 Sidebar):** Every portal embeds an autonomous AI station agent equipped with domain-specific skills. When a policy check fails in Warden, operators simply ask `@warden-agent` to explain the SPDX license conflict and draft an instant waiver.
4. **Autonomous Agentic Execution Fabric (Lane 2 to Compute Plane):** In the background, `pyforge-marshal` coordinates autonomous multi-agent sprints over Redis Streams and Model Context Protocol (MCP) tools. `Agent-Mason` compiles the wheel matrix, `Agent-Warden` audits the SBOM, `Agent-Doctor` diagnoses lockfile drift, and `Agent-Herald` captures automated visual deck summaries.
5. **Rock-Solid Enterprise Infrastructure (Data & Infra Plane):** All database changes are deterministically governed by **Liquibase** (`db/changelog/`), credentials and dynamic database leases are rotated via **HashiCorp Vault**, and state persists across PostgreSQL `pgvector`, DuckDB analytical engines, and MinIO S3 object mirrors.

> "PyForge cut our package maintenance overhead by over 80%. When an upstream security vulnerability hits, Doctor automatically pinpoints the patch, Mason verifies the cross-compiled wheel, Warden approves the SBOM gate, and our team receives a visual slide summary before our morning standup."
> — Lead Platform Engineer, Global Financial Institution

### Getting Started

PyForge provides 100% offline local-to-production parity. Developers can launch the entire stack on Linux, macOS, or Windows with a single command:
```bash
pixi run pyforge host start
```
Enterprise platform teams can deploy the multi-container Helm overlay directly into Red Hat OpenShift under `restricted-v2` SCC with HashiCorp Vault and Keycloak integration.

---

## Customer FAQ

### Q: Why do we need PyForge if our team already uses standard package managers and CI/CD pipelines?
**A:** Traditional CI/CD pipelines are passive, stateless scripts that fail blindly when dependencies drift or vulnerabilities arise. PyForge is an **active, self-healing operating system**. It maintains an AST knowledge graph of your entire codebase, evaluates policy gates deterministically before builds occur, and provides autonomous AI agents with standardized MCP tools to diagnose and resolve conflicts automatically.

### Q: Does PyForge require our developers to abandon their preferred tools?
**A:** Absolutely not. PyForge enforces complete 5-tier symmetry. Developers who prefer the terminal use the universal `pyforge <station>` CLI. DevOps operators use the reactive Django/HTMX web portals and Vizro dashboards. Autonomous AI agents connect over Model Context Protocol (MCP). All three interfaces execute identical domain logic against the same backend microservices.

### Q: How does PyForge ensure security and compliance in air-gapped environments?
**A:** PyForge is designed for zero cloud egress. It operates seamlessly with internal Artifactory/Quay registries, local Keycloak OIDC authentication, HashiCorp Vault secret injection, and local offline CVE vulnerability databases (`deptry`, `osv-scanner`, `cyclonedx-bom`).

### Q: Can AI agents make unauthorized changes or trigger runaway builds?
**A:** No. PyForge embeds multi-layered governance:
1. **RBAC & Scoped Identity:** Agents operate under delegated Keycloak identities (`idp_subject`) with strict role-gating.
2. **Rate Limiting & Circuit Breakers:** Redis-backed Token-Bucket rate limiters throttle agent requests, while semantic circuit breakers trip if an agent exceeds 10 build calls per minute.
3. **Loop-Depth Ceilings:** All inter-station events enforce a hard maximum of 5 automated hops (`X-PyForge-Loop-Depth <= 5`).

### Q: How does PyForge handle multi-tenant isolation?
**A:** Multi-tenancy is enforced across the entire stack: cryptographic `X-Tenant-Signature` headers between the Django Host and FastAPI backends, separate schema isolation in PostgreSQL (`warden_schema`, `atlas_schema`, `scribe_schema`), and strict CSP iframe sandboxing for embedded analytics dashboards.

### Q: What platforms are supported?
**A:** PyForge runs natively on Linux (`x86_64`), macOS (Apple Silicon `M1–M4` on macOS 14.5+), and Windows (`x86_64` via PowerShell, CMD, or WSL2) through Pixi package management.

### Q: How do human operators collaborate with the autonomous AI agents?
**A:** Every web portal features an embedded AI Copilot sidebar. Operators can review agent proposals, approve one-click auto-remedy patches, and inspect full step-by-step reasoning traces captured by Scribe and OpenLineage.

### Q: How does PyForge manage database migrations across 8 different stations?
**A:** Database DDL is governed exclusively by **Liquibase** (`db/changelog/`). No Python ORM alters database tables at runtime. Migrations are executed as pre-install Kubernetes Helm hooks with atomic checksum verification and deterministic rollback scripts.

### Q: Can we selectively adopt individual stations rather than the whole suite?
**A:** Yes. The station portals are pluggable Django Reusable Apps (`pyforge_<station>_portal`). Organizations can enable only the stations they need (e.g. Warden for compliance + Mason for builds) in `INSTALLED_APPS`.

### Q: What is the learning curve for new developers?
**A:** Near zero. The universal CLI uses consistent grammar (`pyforge <station> <noun> <verb>`), while the Guildhall web portal provides interactive documentation, guided walkthroughs, and instant search across corporate memory.

---

## Internal FAQ

### Q: Why did we separate the Django Host (Lane 1/2) from FastAPI Compute (Layer 5) instead of a pure monolith?
**A:** Separation preserves stability and responsiveness. Django + Wagtail excels at session management, OIDC authentication, CMS document routing, and server-rendered HTMX UI. FastAPI excels at high-throughput async APIs, streaming SSE connections for Model Context Protocol (MCP), and delegating heavy batch jobs to Celery. Separating them prevents heavy AST scans or compiler runs from freezing the operator's web UI.

### Q: How do we prevent Uvicorn event-loop starvation when mixing REST and streaming MCP traffic?
**A:** Via **RFC-1 (Worker Pool Separation)**. Each station microservice splits compute into two dedicated pools: Worker Pool A (low-latency REST with a 500ms timeout ceiling for Django HTMX) and Worker Pool B (persistent SSE/MCP agent connections with CPU-bound work offloaded to Celery).

### Q: Why do we maintain two distinct Redis instances?
**A:** Via **RFC-2 (Broker vs. Cache Separation)**. `redis-broker` runs with `maxmemory-policy noeviction` to guarantee zero message loss for Celery queues and Redis Streams. `redis-cache` runs with `allkeys-lru` for volatile Django session caches and rate-limit counters, preventing cache growth from crashing task ingestion.

### Q: How do we handle Keycloak token expiration during 2-hour autonomous agent sprints?
**A:** Via **RFC-3 & BS-3 (OAuth 2.0 Token Exchange RFC 8693)**. Background Celery workers receive the user's `delegation_context` (`idp_subject`) and use Keycloak confidential client credentials to mint scoped background execution tokens that remain valid throughout the sprint.

### Q: How does PyForge prevent SQLite database locking in multi-pod OpenShift clusters?
**A:** Via **BS-1 (Dual-Driver Scribe Engine)**. Scribe uses SQLite for local single-developer workflows but dynamically switches to PostgreSQL native schema (`scribe_schema`) with `pgvector` in multi-node Kubernetes deployments.

### Q: What prevents OpenShift HAProxy ingress routers from severing 5-minute agent builds?
**A:** Via **BS-2 (SSE Keep-Alive & Route Timeouts)**. FastAPI emits periodic keep-alive SSE frames (`:keepalive\n\n`) every 15 seconds, and OpenShift Routes declare `haproxy.router.openshift.io/timeout: 30m`.

### Q: How is database DDL schema drift prevented across teams?
**A:** Via **RFC-5 (Liquibase Single Source of Truth)**. All DDL across `public`, `warden_schema`, `atlas_schema`, etc., is declared in Liquibase YAML/SQL changelogs. Django and FastAPI microservices consume tables as read/write targets but are strictly prohibited from generating runtime DDL.

### Q: What is the peak cluster compute footprint required for enterprise HA?
**A:** Sizing benchmarks specify **32 to 64 vCPUs and 64 to 128 GB RAM** across minimum 3 worker nodes to accommodate concurrent `pgvector` HNSW index caching, in-memory DuckDB analytical sweeps, and multi-Python batch wheel compilations.

### Q: How do we ensure fast CI validation across the 1,000+ package Pixi lockfile?
**A:** Pixi uses shared binary prefix caching, while CI runs automated lockfile drift checks (`pixi run -e local-recipes llms-full-check`) to detect dependency divergence before PR merges.

### Q: What happens if an unhandled panic occurs in an inter-station event consumer?
**A:** Via **RFC-4 (PEL Reclaim & Dead Letter Queue)**. Unacknowledged messages in the Redis Streams Pending Entries List (PEL) are automatically harvested by an `XAUTOCLAIM` consumer and routed to `pyforge:events:dlq` with detailed stack traces.

---

## The Verdict

| Architectural Area | Evaluation | Status | Rationale |
| :--- | :---: | :---: | :--- |
| **Topology & Seam Modularity** | **Forged in Steel** | ✅ **READY** | Clear separation between Canopy (Lane 1), Portals (Lane 2), Dashboards (Lane 3), and FastAPI compute (Layer 5). |
| **5-Tier Station Symmetry** | **Forged in Steel** | ✅ **READY** | 1:1:1:1:1 symmetry across CLI, Portal, Microservice/MCP, Skill, and Agent persona across all 8 stations. |
| **Enterprise Governance & DDL** | **Forged in Steel** | ✅ **READY** | Single-source Liquibase DDL + HashiCorp Vault secrets eliminate schema chaos and credential leaks. |
| **Distributed Systems Hardening** | **Hardened via RFCs** | ✅ **READY** | RFC 1–5 and BS 1–8 provide explicit mitigations for token decay, router timeouts, event-loop starvation, and PEL recovery. |
| **Deployment Parity** | **Forged in Steel** | ✅ **READY** | 100% native Linux/macOS/Windows execution with LocalStack-style local-to-OpenShift parity. |

**Final Recommendation:** The concept is battle-hardened, customer-validated, and ready for immediate decomposition into the Product Brief, UX journey maps, and BMAD Planning Specifications.
