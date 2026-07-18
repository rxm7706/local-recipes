window.DASHBOARD_DATA = {
  "projects": {
    "warden": {
      "label": "Warden",
      "accentVar": "--warden",
      "branch": "pyforge-warden-epic3-policy",
      "contract": "FR1–FR40 · exit codes {0,1,2,130} · verdict lattice error &gt; policy-violation &gt; indeterminate &gt; warn &gt; bypassed &gt; clean &gt; not-applicable",
      "seglabels": [
        "E1 · spine",
        "E2 · wedge",
        "E3–E5",
        "E6 · multi-axis"
      ],
      "epics": [
        {
          "badge": "E1",
          "title": "Spine + PyPI engine (walking skeleton)",
          "stories": [
            [
              "1.1",
              "done",
              "Frozen contract, verdict lattice & projection-safety"
            ],
            [
              "1.2",
              "done",
              "Interfaces, null engine, regression harness & socket-deny"
            ],
            [
              "1.3",
              "done",
              "deptry as the first engine (hygiene findings)"
            ],
            [
              "1.4",
              "done",
              "OSV-DB offline provisioning spike (decision + fixture DB)"
            ],
            [
              "1.5",
              "done",
              "osv-scanner as the second engine (vulnerability findings)"
            ],
            [
              "1.6",
              "done",
              "Severity gate + verdict composition end-to-end"
            ],
            [
              "1.7",
              "done",
              "Typed errors & the no-scan guard (the fail-closed net)"
            ],
            [
              "1.8",
              "done",
              "Human & machine report renderers"
            ],
            [
              "1.9",
              "done",
              "Manifest discovery, deterministic selection & the resolved scan set"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "The conda / pixi source-manifest wedge",
          "stories": [
            [
              "2.1",
              "done",
              "conda→pypi map + the ecosystem-identity predicate"
            ],
            [
              "2.2",
              "done",
              "Non-rendering extraction + differential-oracle"
            ],
            [
              "2.3",
              "done",
              "The full supported-construct matrix (ratcheted)"
            ],
            [
              "2.4",
              "done",
              "Honest split coverage + the indeterminate producer"
            ],
            [
              "2.5",
              "done",
              "Name-level CVE tier + stale-DB + cross-ecosystem non-merge"
            ],
            [
              "2.6",
              "done",
              "Lockfile extraction — the locked-closure vuln hero path"
            ]
          ]
        },
        {
          "badge": "E3",
          "title": "Policy control + auditable waivers + warn-only",
          "stories": [
            [
              "3.1",
              "done",
              "Configurable policy (the ConfigLoader)"
            ],
            [
              "3.2",
              "done",
              "Auditable expiring waivers"
            ],
            [
              "3.3",
              "done",
              "Waiver expiry + warn-only adoption on-ramp"
            ]
          ]
        },
        {
          "badge": "E4",
          "title": "Machine contract + CycloneDX SBOM",
          "stories": [
            [
              "4.1",
              "done",
              "CycloneDX SBOM emission"
            ]
          ]
        },
        {
          "badge": "E5",
          "title": "Fleet-readiness & adoption on-ramp",
          "stories": [
            [
              "5.1",
              "pending",
              "Actionable diagnostics & safe-by-default posture"
            ],
            [
              "5.2",
              "pending",
              "Fleet-scale validation + corpus / oracle maturation"
            ]
          ]
        },
        {
          "badge": "E6",
          "title": "Multi-axis expansion — license, currency, KEV / EPSS",
          "gatenote": "<b>Both hard gates cleared ✔</b> — <code>6.10</code> (decision record) + <code>6.1</code> (schema <code>1.0.0→1.1.0</code>). Producers underway: <code>6.4</code> (KEV feed — the <code>feeds.py</code> substrate 6.3/6.7 consume + <code>fail-on-kev</code>) is <b>landed ✔ (1334 green)</b>. <code>6.2</code> (license axis) is next; 7 producers remain.",
          "stories": [
            [
              "6.10",
              "done",
              "Amendment design spike — ID families, verdict encoding, fold semantics (decision record)"
            ],
            [
              "6.1",
              "done",
              "The versioned ComplianceReport schema amendment (1.0.0→1.1.0, additive)"
            ],
            [
              "6.2",
              "pending",
              "License axis producer + gate flags (Axis 3)"
            ],
            [
              "6.3",
              "pending",
              "Currency axis producer + gate flags (Axis 4)"
            ],
            [
              "6.4",
              "done",
              "KEV feed provisioning + the fail-on-kev gate (feeds.py substrate)"
            ],
            [
              "6.5",
              "pending",
              "Two-mode policy integration (visibility + flag-gating)"
            ],
            [
              "6.6",
              "pending",
              "Engine version-range pinning (the distribution gate)"
            ],
            [
              "6.7",
              "pending",
              "EPSS feed + the --min-epss gate"
            ],
            [
              "6.8",
              "pending",
              "Baseline & grandfathering (gate new findings only)"
            ],
            [
              "6.9",
              "pending",
              "Fix-PR actuator (opt-in remediation PRs)"
            ]
          ]
        }
      ],
      "inflight": null,
      "velocity": {
        "sub": "Active agent-compute time per completed story (dev + review; excludes gate-pause wait). Median holds near steady-state; the Epic-2 extraction stories (2.2–2.4) ran heavy.",
        "bars": [
          [
            "1.3",
            78
          ],
          [
            "1.4",
            95
          ],
          [
            "1.5",
            73
          ],
          [
            "1.6",
            49
          ],
          [
            "1.7",
            67
          ],
          [
            "1.8",
            35
          ],
          [
            "1.9",
            137
          ],
          [
            "2.1",
            95
          ],
          [
            "2.2",
            194
          ],
          [
            "2.3",
            148
          ],
          [
            "2.4",
            113
          ],
          [
            "2.5",
            67
          ],
          [
            "3.1",
            80
          ],
          [
            "3.2",
            57
          ],
          [
            "3.3",
            127
          ],
          [
            "4.1",
            96
          ],
          [
            "6.1",
            81
          ]
        ],
        "foot": [
          [
            "~80 min",
            "median / story",
            "var(--done)"
          ],
          [
            "35–194 min",
            "observed range",
            ""
          ],
          [
            "9",
            "stories remaining",
            ""
          ],
          [
            "~18–22 h",
            "est. active compute left",
            ""
          ]
        ]
      },
      "timing": {
        "metric": "active agent-compute per story (dev + review; excludes gate-pause wait) — from bmad-loop run journals",
        "totalLabel": "~27 h active compute",
        "note": "Measured stories only. The earliest keystones 1.1 / 1.2, plus 2.6 and the recovered 6.10 spike, predate clean journaling and are excluded. 6.4’s bar is its delivered dev-2 pass (35m); a rolled-back dev-1 cost ~49m more that isn’t counted as delivery.",
        "perStory": {
          "1.3": 78,
          "1.4": 95,
          "1.5": 73,
          "1.6": 49,
          "1.7": 67,
          "1.8": 35,
          "1.9": 137,
          "2.1": 95,
          "2.2": 194,
          "2.3": 148,
          "2.4": 113,
          "2.5": 67,
          "3.1": 80,
          "3.2": 57,
          "3.3": 127,
          "4.1": 96,
          "6.1": 81,
          "6.4": 35
        },
        "epicMin": {
          "E1": 534,
          "E2": 617,
          "E3": 264,
          "E4": 96,
          "E6": 116
        },
        "total": 1627
      }
    },
    "atlas": {
      "label": "Atlas",
      "accentVar": "--atlas",
      "branch": "migration complete — Waves 0–H shipped",
      "contract": "Kedro + pixi · DuckDB singularity · nebi-scaffolded · 28 CLIs → Vizro pages · migrates cf_atlas (phases B→N) to a typed, incremental data pipeline",
      "seglabels": [
        "W0",
        "WA–WB",
        "WC–WE",
        "WF–WH"
      ],
      "epics": [
        {
          "badge": "0",
          "title": "Wave 0 — Legacy translation via Skill Forge",
          "stories": [
            [
              "0.1",
              "done",
              "Generate legacy contextual skill (cf-atlas-legacy@8.78.0)"
            ]
          ]
        },
        {
          "badge": "A",
          "title": "Wave A — nebi scaffold & catalog",
          "stories": [
            [
              "A1",
              "done",
              "Scaffold the Kedro + pixi project via nebi"
            ],
            [
              "A2",
              "done",
              "Define the Data Catalog for all sources + outputs"
            ],
            [
              "A3",
              "done",
              "IncrementalParquetDataset for TTL gating"
            ]
          ]
        },
        {
          "badge": "B",
          "title": "Wave B — Pipeline node porting & MCP integration",
          "stories": [
            [
              "B1",
              "done",
              "Port the conda-side backbone phases into Kedro nodes"
            ],
            [
              "B2",
              "done",
              "Port the PyPI & vulnerability pipelines"
            ],
            [
              "B3",
              "done",
              "Re-expose the data surface as Kedro-API-native MCP tools"
            ],
            [
              "B4",
              "done",
              "Verify dataset parity against the legacy orchestrator"
            ],
            [
              "B5",
              "done",
              "Port the external-refresh assets"
            ],
            [
              "B6",
              "done",
              "Port the Seed-Gaps pipeline"
            ],
            [
              "B7",
              "done",
              "Extend the Universal SBOM intake (resolver, formats, buckets)"
            ],
            [
              "B8",
              "done",
              "Basilisk conda-native vulnerability ingestion"
            ],
            [
              "B9",
              "done",
              "Release-to-availability velocity columns"
            ],
            [
              "B10",
              "done",
              "Migration-readiness datasets + classification node"
            ]
          ]
        },
        {
          "badge": "C",
          "title": "Wave C — Orchestration & visualization",
          "stories": [
            [
              "C1",
              "done",
              "Integrate kedro-dagster for scheduling + execution"
            ],
            [
              "C2",
              "done",
              "Integrate kedro-viz + expose a pixi task"
            ]
          ]
        },
        {
          "badge": "D",
          "title": "Wave D — Semantic layer & dashboards",
          "stories": [
            [
              "D1",
              "done",
              "Define the Boring Semantic Layer (BSL) models"
            ],
            [
              "D2",
              "done",
              "Build the Vizro dashboard + port the 28 CLIs to pages"
            ],
            [
              "D3",
              "done",
              "Integrate Vizro-AI + expose the NL interface as an MCP tool"
            ]
          ]
        },
        {
          "badge": "E",
          "title": "Wave E — A2A integration, lineage & observability",
          "stories": [
            [
              "E1",
              "done",
              "Implement the A2A communication interfaces"
            ],
            [
              "E2",
              "done",
              "Integrate OpenLineage + OpenTelemetry"
            ]
          ]
        },
        {
          "badge": "F",
          "title": "Wave F — The DuckDB singularity",
          "stories": [
            [
              "F1",
              "done",
              "DuckDB consolidation + prove the cold-start claim"
            ],
            [
              "F2",
              "done",
              "Data-validation hook + inline Pandera contracts"
            ],
            [
              "F3",
              "done",
              "Vector Similarity Search (RAG) via DuckDB vss"
            ],
            [
              "F4",
              "done",
              "Dependency-hygiene node + unified CI policy gate  ·  imports Warden's ComplianceReport"
            ]
          ]
        },
        {
          "badge": "G",
          "title": "Wave G — WebAssembly portability & sensors",
          "stories": [
            [
              "G1",
              "done",
              "Compile the intelligence layer to Pyodide / DuckDB-WASM"
            ],
            [
              "G2",
              "done",
              "Emit Parquet artifacts to a static web host (HTTP-Range gate)"
            ],
            [
              "G3",
              "done",
              "Dagster Sensors for near-real-time ingestion"
            ]
          ]
        },
        {
          "badge": "H",
          "title": "Wave H — The AI software factory & Karpathy wiki",
          "stories": [
            [
              "H1",
              "done",
              "Scaffold the Karpathy Wiki structure + 5 factory personas"
            ],
            [
              "H2",
              "done",
              "Agno compilation, linting & Q&A crews"
            ],
            [
              "H3",
              "done",
              "Integrate La Suite / Wagtail Docs REST API sync"
            ],
            [
              "H4",
              "done",
              "Orchestrate crews via Dagster"
            ]
          ]
        }
      ],
      "roadmap": {
        "sub": "Complete: all of Waves 0–H are shipped (per merged PRs #69–#102) — the Kedro port, MCP surface, parity harness, Universal SBOM intake, orchestration, the BSL + Vizro + Vizro-AI dashboards, A2A + OpenLineage/OTel, the full DuckDB singularity (cold-start gate, Pandera contracts, vss RAG, F4’s hygiene node importing Warden’s ComplianceReport), Wave G’s WASM read surface + static-host Parquet emitter + Dagster sensors, and Wave H’s AI software factory (Karpathy wiki + 5 factory personas, agno crews, La Suite sync, Dagster orchestration). The migration was closed out by the CFE Rule-2 retro #103 (v8.79.0). 32/32.",
        "stops": [
          [
            "0",
            "Legacy skill",
            "done"
          ],
          [
            "A",
            "nebi scaffold",
            "done"
          ],
          [
            "B",
            "node porting",
            "done"
          ],
          [
            "C",
            "orchestration",
            "done"
          ],
          [
            "D",
            "semantic layer",
            "done"
          ],
          [
            "E",
            "lineage / A2A",
            "done"
          ],
          [
            "F",
            "DuckDB",
            "done"
          ],
          [
            "G",
            "WASM",
            "done"
          ],
          [
            "H",
            "AI factory",
            "done"
          ]
        ]
      },
      "timing": {
        "metric": "wall-clock between story landings (create → dev → review → merge) — from PR timestamps; includes gate waits & idle, NOT active compute",
        "totalLabel": "25.0 h wall-clock",
        "note": "Full calendar span 2026-07-17 09:58 → 2026-07-18 11:00 UTC; the per-story intervals partition it exactly (no double-counting). Wave B’s total is idle-inflated — B1 (227m) and B3 (217m) each absorbed a long overnight / interleaved gap, not active work.",
        "perStory": {
          "0.1": 44,
          "A1": 55,
          "A2": 71,
          "A3": 118,
          "B1": 227,
          "B2": 78,
          "B3": 217,
          "B4": 34,
          "B5": 57,
          "B6": 30,
          "B7": 50,
          "B8": 42,
          "B9": 16,
          "B10": 23,
          "C1": 34,
          "C2": 4,
          "D1": 30,
          "D2": 26,
          "D3": 27,
          "E1": 76,
          "E2": 24,
          "F1": 8,
          "F2": 25,
          "F3": 23,
          "F4": 32,
          "G1": 28,
          "G2": 26,
          "G3": 22,
          "H1": 11,
          "H2": 14,
          "H3": 14,
          "H4": 17
        },
        "epicMin": {
          "0": 44,
          "A": 244,
          "B": 775,
          "C": 38,
          "D": 82,
          "E": 100,
          "F": 88,
          "G": 76,
          "H": 56
        },
        "total": 1502
      }
    }
  },
  "snapshot": "<span>2026-07-18 15:50 UTC</span> · source: sprint-status feeds + merged-PR ground truth (#58–#104) + bmad-loop run journals · timing: Warden = active compute (journals), Atlas = wall-clock (PR timestamps)",
  "defaultProject": "warden"
};
