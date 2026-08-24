---
title: "UX Design & Cross-Station Operator Journeys: PyForge Enterprise Platform"
status: "ready"
created: "2026-08-23"
updated: "2026-08-24"
chain: "pyforge-unifying-strategy"
author: "herald"
inputs:
  - "docs/dreams/pyforge-unifying-strategy.md"
  - "brief.md"
---

# UX Design & Cross-Station Operator Journeys

## 1. UI Topology & Navigation Architecture

The PyForge user experience is divided into **3 distinct visual lanes** unified by the **`django-pyforge` App Switcher** and the **Modernist Design Theme**:

```mermaid
graph TD
    subgraph Lane1["Lane 1: Central Guildhall (Root /)"]
        GHeader["Global Header: Modernist Brand + Station Selector Dropdown + User Profile"]
        GBody["Wagtail CRX CMS: Knowledge Base, Documentation, Search & Corporate Brain"]
        GQuick["Quick Action Hub: 8 Station Launch Badges & Live Fleet Status"]
    end

    subgraph Lane2["Lane 2: Pluggable Station Action Portals (/stations/{station}/)"]
        PHeader["Station Header: Active Station Indicator + Context Breadcrumbs"]
        PBody["Zero-Model HTMX Workspace: Transactional Forms, Scorecards, Live Event Tables"]
        PSidebar["Embedded AI Copilot Sidebar: Station-Specific Agent (e.g. @warden-agent)"]
    end

    subgraph Lane3["Lane 3: Isolated Deep Analytics (/analytics/{station}/)"]
        VHeader["Proxy Header: Inherited Security Context (X-Tenant-Signature)"]
        VBody["Vizro / Panel Dashboards: Reactive Plotly Graphs, Dependency Trees, Latency Heatmaps"]
    end

    Lane1 --> Lane2
    Lane1 --> Lane3
    Lane2 <--> Lane3
```

---

## 2. Master Wireframe: The Pluggable Station Portal (`Lane 2`)

```
+--------------------------------------------------------------------------------------------------------------------+
|  [P] PyForge Guildhall   |  [Stations Dropdown v]  |  Docs  |  Search... (/)  |  [Status: Healthy]  |  [User: rxm7706]  |
+--------------------------------------------------------------------------------------------------------------------+
|  < Stations / Warden Compliance & Policies >                                                                        |
+---------------------------------------------------------------------------------+----------------------------------+
|  WARDEN COMPLIANCE CONSOLE                                                      |  AI COPILOT: @warden-agent       |
|  Active Target: local-recipes (Python 3.14 / linux-64)                          |  Skill: pyforge-warden           |
|                                                                                 +----------------------------------+
|  +------------------------+  +------------------------+  +--------------------+ |  Warden: I detected a GPL-3.0    |
|  | SBOM Compliance: 99.4% |  | Unresolved CVEs: 0     |  | Active Waivers: 2  | |  license conflict in package     |
|  +------------------------+  +------------------------+  +--------------------+ |  `libfoo-core` against policy.   |
|                                                                                 |                                  |
|  POLICY VIOLATION DETECTED                                                      |  Operator: Can you explain and   |
|  -----------------------------------------------------------------------------  |  draft a waiver for 30 days?     |
|  Package: `libfoo-core` (v1.4.2)                                                |                                  |
|  Rule: Enterprise Permissive Policy (SPDX Expression Failure)                    |  Warden: Analysis:               |
|  Impact: Blocks Mason build release gate                                        |  - Direct dependency is MIT      |
|                                                                                 |  - Bundled C-header is GPL-3.0   |
|  [View SARIF Report]   [Open in Scribe Graph]   [Request Waiver]                |                                  |
|                                                                                 |  [ Draft Waiver Action Button ]  |
|  +---------------------------------------------------------------------------+  |                                  |
|  | ONE-CLICK REMEDIATION (Powered by Doctor & Mason)                         |  |  [ Ask Follow-up Question... ]  |
|  | Doctor identified a compatible MIT drop-in replacement: `libfoo-free`     |  |                                  |
|  | [ Execute 1-Click Auto-Remedy & Rebuild Matrix ]                          |  |                                  |
|  +---------------------------------------------------------------------------+  |                                  |
+---------------------------------------------------------------------------------+----------------------------------+
|  Footer: PyForge v2026.8.23 · Air-Gapped LocalStack Mode · OCP Restricted-v2 SCC Verified                           |
+--------------------------------------------------------------------------------------------------------------------+
```

---

## 3. End-to-End Operator Journey: The Self-Healing Supply Chain

```mermaid
sequenceDiagram
    autonumber
    actor Op as Human Operator
    participant GH as Guildhall UI (Lane 1)
    participant WPortal as Warden Portal (Lane 2)
    participant WAgt as Agent-Warden (Sidebar)
    participant FastW as Warden Service (:8004)
    participant FastDoc as Doctor Service (:8008)
    participant FastMas as Mason Service (:8007)
    participant Herald as Herald Deck Stage (:8006)

    Op->>GH: Opens Guildhall at / via Keycloak SSO
    GH->>WPortal: Switches to Warden Portal via App Switcher
    WPortal->>FastW: HTMX fetch compliance scorecard
    FastW-->>WPortal: Renders failing policy gate (GPL conflict)
    Op->>WAgt: "@warden-agent: Diagnose and propose fix"
    WAgt->>FastDoc: Queries Doctor auto-remedy database
    FastDoc-->>WAgt: Returns clean MIT alternative `libfoo-free`
    WAgt-->>WPortal: Renders interactive "1-Click Auto-Remedy" card
    Op->>WPortal: Clicks [ Execute Auto-Remedy ]
    WPortal->>FastMas: Dispatches batch wheel compilation to Celery
    FastMas-->>WPortal: Streams build progress via SSE
    FastMas->>Herald: Notifies Herald on successful build
    Herald-->>GH: Auto-generates updated presentation slide summary
```

---

## 4. Key UX Principles & Accessibility

1. **Zero Layout Shift & Instant HTMX Swaps:** State mutations use partial DOM replacements with smooth CSS transitions (`opacity 0.2s ease-in-out`), eliminating full page reloads.
2. **Keyboard-First Power Navigation:**
   * `/` — Focus global corporate brain search.
   * `Ctrl + K` / `Cmd + K` — Open instant Station Switcher palette.
   * `Ctrl + J` — Toggle embedded AI Copilot sidebar.
3. **Air-Gapped Color Contrast & Theme Invariants:** Strict WCAG 2.1 AAA contrast compliance utilizing the Modernist monochromatic palette with semantic state badges (`#107C41` for Healthy, `#D83B01` for Blocked, `#0078D4` for Active).
