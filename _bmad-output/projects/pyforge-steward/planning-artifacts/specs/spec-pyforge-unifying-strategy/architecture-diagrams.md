---
title: "Architecture diagrams"
chain: "pyforge-unifying-strategy"
created: "2026-08-24"
updated: "2026-08-26"
---

# Architecture diagrams

Companion to `SPEC.md` — Spec Law rule 2 keeps diagrams out of the kernel. These render the
contract: **solid** boxes are shipped (`spec-python-agent-platform` **or** this chain's drain,
2026-08-25; closeout 2026-08-26). **Dashed** leftover is honesty-only (isolated `mfa`
sqlmigrate fake; optional 12.9 `ocp-portability-smoke` when Actions minutes return).

## The Canopy as it stands and as it extends

```mermaid
graph TB
    User["Operator / Agent"]

    subgraph Canopy["The Canopy — src/platform/ (SHIPPED)"]
        Host["config/ + platformapp/<br/>Django 5.2 · ASGI seam"]
        Auth["django-allauth<br/>OIDC SSO"]
        FastAPIseam["config/fastapi_app.py<br/>in-host /api/health"]
        LF["langflow_integration<br/>langflow_schema"]
        DG["dbgpt_integration<br/>dbgpt_schema"]
        CF["warden portal<br/>django-warden — 8 of 8 prefix"]
        L1["Wagtail Lane 1"]
        P7["Eight portals /stations/{name}/"]
        DP["django-pyforge chrome"]
        SVC["MCP on host ASGI"]
        CLI["pyforge CLI"]
        CLIENT["trusted client CAP-6"]
        SD["Lane 3 row isolation"]
        EV["CloudEvents on redis-broker"]
        SK["domain skills CAP-15"]
        PER["personas CAP-16"]
        SUP["supervisor CAP-17"]
    end

    subgraph Residual["Honesty leftover after closeout (2026-08-26)"]
        LIVE["mfa sqlmigrate fake only<br/>optional 12.9 CI job"]
    end

    User --> Host
    Host --> Auth
    Host --> LF
    Host --> DG
    Host --> CF
    Host --> L1
    Host --> P7
    DP --> CF
    DP --> P7
    DP --> L1
    CF --> CLIENT
    P7 --> CLIENT
    CLIENT --> SVC
    FastAPIseam -->|same ASGI; RFC-1 is Celery workers| SVC
    SVC --> EV
    Host --> SD
    CLI --> SVC
    PER -->|"acts only through"| CLI
    PER -->|"and through"| SVC
    SK --> PER
    Host -->|"queries — never reads a filesystem"| SUP
    Host -.-> LIVE

    classDef shipped fill:#1a3a52,stroke:#4a9eda,color:#fff
    classDef residual fill:#3a2a1a,stroke:#daa54a,color:#fff,stroke-dasharray: 5 3
    class Host,Auth,FastAPIseam,LF,DG,CF,DP,L1,P7,SVC,CLI,CLIENT,SD,EV,SK,PER,SUP shipped
    class LIVE residual
```

## Request path and the identity chain (CAP-6)

Load-bearing detail: no portal ever constructs a raw request, and no service ever trusts a
forwarded header. The delegated assertion is the only accepted identity.

```mermaid
sequenceDiagram
    participant U as Operator
    participant K as Keycloak
    participant H as Host (Django)
    participant P as station_portal
    participant C as pyforge.core.client
    participant S as station service
    participant Q as Celery worker

    U->>K: OIDC authorization
    K-->>H: id_token + session
    U->>P: GET /warden/
    P->>C: call(station, noun, verb)
    Note over C: mint signed internal JWT<br/>idp_subject + roles<br/>delegated_by: pyforge-host
    C->>S: POST /mcp  (audience-bound)
    S->>S: verify signature + audience
    alt operation under ~30s
        S-->>C: response (SSE stream, progress events)
    else multi-minute
        S-->>C: Task handle (taskId, ttlMs, pollIntervalMs)
        S->>Q: enqueue with delegation_context
        Note over Q: BS-3 — mint scoped execution<br/>token from captured idp_subject
        C->>S: tasks/get (poll)
        S-->>C: terminal status + result
    end
    C-->>P: typed result
    P-->>U: HTMX partial
    Note over P: Lane 2 is HTMX (Q7).<br/>No DRF JSON:API on the portal.
```

## DDL governance (CAP-9, revised RFC-5)

The ordering matters and is the part most easily got wrong: Liquibase runs in a **pre-upgrade Job**,
not an init container, and `migrate --fake` still runs so `post_migrate` can populate content
types, permissions and sites.

```mermaid
graph LR
    Dev["Developer authors<br/>Django migration"]
    SQL["sqlmigrate extraction"]
    CS["Liquibase changeset<br/>db/changelog/"]
    Gate{"CI gate:<br/>extraction stale?"}
    Job["Helm pre-upgrade Job<br/>migration role"]
    Fake["migrate --fake<br/>app role"]
    Post["post_migrate fires:<br/>contenttypes, permissions, sites"]
    Pods["App pods start<br/>DML-only role"]
    Test["Test DB:<br/>Django migrate, CARVED OUT"]

    Dev --> SQL --> CS --> Gate
    Gate -->|stale| Fail["build fails"]
    Gate -->|current| Job
    Job --> Fake --> Post --> Pods
    Dev -.-> Test

    classDef built fill:#3a2a1a,stroke:#daa54a,color:#fff,stroke-dasharray: 5 3
    classDef carve fill:#2a2a2a,stroke:#888,color:#ccc
    class SQL,CS,Gate,Job,Fake built
    class Test carve
```

## Event backbone (CAP-8, RFC-4 + BS-6)

```mermaid
graph LR
    Pub["Publishing station"]
    Stream["pyforge:events<br/>Redis Streams"]
    CG["Consumer groups<br/>per station"]
    PEL["Pending Entries List"]
    Claim["XAUTOCLAIM harvester"]
    DLQ["pyforge:events:dlq"]
    Sub["Consuming station"]

    Pub -->|"CloudEvents envelope<br/>schema_version 2.x<br/>spec_id + git sha + SBOM purl<br/>optional work-item id<br/>X-PyForge-Loop-Depth ≤ 5"| Stream
    Stream --> CG --> Sub
    CG -.->|unacked| PEL
    PEL --> Claim
    Claim -->|"retries exhausted"| DLQ
    Sub -.->|"validation in domain adapter,<br/>never at stream boundary"| Sub
```

## Lane 1 supersession (CAP-2)

Decided 2026-08-24: Wagtail Lane 1 **supersedes** Marshal's statically-built console. The ordering
is the whole content of this diagram — parity is proven before the old path is removed, and the
spec correction lands in the same chain rather than trailing it.

```mermaid
graph LR
    GH["docs/dashboard/<br/>Marshal's console<br/>spec-factory-console"]
    INV["Parity inventory<br/>every view enumerated"]
    Build{"Runtime<br/>equivalent<br/>exists?"}
    Scope["Scope conversation<br/>— build-time-only view"]
    W["Wagtail Lane 1 at /<br/>+ station portal routes"]
    Proof["Parity proven"]
    Rm["Old build path removed<br/>not merely unlinked"]
    CC["correct-course:<br/>spec-factory-console retired"]
    HW["pyforge-herald/web/<br/>Moments UI — unaffected"]

    GH --> INV --> Build
    Build -->|no| Scope
    Build -->|yes| W
    W --> Proof --> Rm --> CC
    HW -.->|"not Lane 1,<br/>out of scope"| W

    classDef gate fill:#3a2a1a,stroke:#daa54a,color:#fff
    classDef out fill:#2a2a2a,stroke:#888,color:#ccc
    class INV,Build,Proof gate
    class HW,Scope out
```
