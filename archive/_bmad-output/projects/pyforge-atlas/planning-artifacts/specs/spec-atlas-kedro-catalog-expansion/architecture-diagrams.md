# Architecture diagrams

Companion to `SPEC.md`.

## Station ownership

```mermaid
flowchart TB
  subgraph atlas ["pyforge-atlas (OWNER)"]
    CAT[catalog.yml datasets]
    PIP[pipelines: core, pypi_intelligence, upstream_discovery, ...]
    EXP[identity_export_parquet]
  end
  subgraph quartet ["inventory quartet (CONSUMER)"]
    MET[metrics.py --live-catalog]
    PRI[priority.py]
    ID[identity.py thin wrapper]
    GIST[gist publish]
  end
  subgraph legacy ["legacy (parallel, not retired)"]
    BOOT[bootstrap-data]
    SQLITE[cf_atlas.db]
    CFE[conda-forge-expert CLIs]
  end
  CAT --> PIP --> EXP
  EXP --> MET
  EXP --> ID
  PRI --> GIST
  ID --> GIST
  BOOT -.-> SQLITE
  SQLITE -.->|"no longer required"| PIP
```

## Data plane (steady state)

```
PYFORGE_ATLAS_DATA_ROOT/          # default: member data/
├── raw/                          # HTTP → Parquet
├── primary/
├── derived/
│   ├── identity_export_parquet/          # Epic 21
│   ├── enterprise_jfrog_consumption/     # Epic 23.2
│   ├── inventory_verified_packages/      # Epic 23.4
│   └── identity_complete_export/         # Epic 23.5 — canonical
└── stores/
    ├── vdb/
    ├── osv/
    └── pypi_conda_map.json
```

## Phase flow

```mermaid
flowchart LR
  A[Phase A relocate globals] --> B[Phase B drop SQLite seeds]
  B --> C[Phase C catalog expansion]
  C --> D[Phase D upstream_discovery identity]
  D --> Q[Quartet thin-out]
  Q --> V[parity-diff + bsl-metric-check]
```

## Mapping vs identity (prefix-dev)

```mermaid
flowchart LR
  PM[parselmouth / pypi_conda_mapping] -->|"conda name ↔ PyPI name"| VER[CondaForge_Verified]
  PA[purl-associator] -->|"conda name → upstream PURL/CPE"| ID[identity_packages_primary]
```

Parselmouth: [prefix-dev/parselmouth](https://github.com/prefix-dev/parselmouth) via Phase C.
PURL Associator: [prefix-dev/purl-associator](https://github.com/prefix-dev/purl-associator) via Phase D.

## Operator surfaces (Epic 21)

```mermaid
flowchart TB
  subgraph core ["21.1–18.8 core"]
    BOOT[pyforge-atlas-bootstrap]
    PQ[Parquet catalog]
  end
  subgraph optional ["21.9–21.10 optional"]
    VZ[Vizro: index / identity / coverage pages]
    KV[Kedro-Viz CI on catalog + datasets]
  end
  subgraph epic19 ["Epic 22 CAP-7"]
    VP[Vizro identity-catalog / ops / workbook]
    CV[Cursor canvases parallel until parity gate]
  end
  subgraph epic20 ["Epic 23 CAP-8"]
    COMP[identity_complete_export.parquet]
    ENT[enterprise_jfrog_consumption.parquet]
  end
  subgraph quartet ["inventory quartet (bridge until 23.7)"]
    GIST[gist actuator + optional ranked bridge]
  end
  BOOT --> PQ
  PQ --> VZ
  ENT --> COMP
  PQ --> COMP
  COMP --> VP
  COMP --> GIST
  GIST --> CV
  VP -.->|parity 22.5| CV
  core --> KV
```

See `operator-surfaces.md`, `vizro-canvas-parity.md`, and `complete-export-contract.md`.
