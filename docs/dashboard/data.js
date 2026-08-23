window.DASHBOARD_DATA = {
  "projects": {
    "atlas": {
      "label": "Atlas",
      "accentVar": "--atlas",
      "branch": "Waves 0–H shipped · Wave I post-audit truth-up in progress",
      "contract": "Kedro + pixi · DuckDB singularity · nebi-scaffolded · 8 Vizro pages shipped (28-CLI inventory deferred, DW-D2-1) · migrates cf_atlas (phases B→N) to a typed, incremental data pipeline",
      "seglabels": [
        "W0",
        "WA–WB",
        "WC–WE",
        "WF–WH",
        "WI · post-audit"
      ],
      "inflight": null,
      "velocity": {
        "derived": true,
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals. 21 of 57 stories measured; the rest predate loop instrumentation and carry wall-clock only (a different metric — see the timing strip), so they are deliberately absent rather than plotted on this axis. A story still in flight contributes only its CLOSED sessions, so its bar is a floor, not a total.",
        "bars": [
          [
            "10.4",
            68
          ],
          [
            "10.5",
            499
          ],
          [
            "10.6",
            194
          ],
          [
            "12.1",
            95
          ],
          [
            "12.2",
            116
          ],
          [
            "12.3",
            16
          ],
          [
            "13.1",
            86
          ],
          [
            "13.2",
            76
          ],
          [
            "13.3",
            172
          ],
          [
            "13.4",
            53
          ],
          [
            "13.5",
            80
          ],
          [
            "14.1",
            57
          ],
          [
            "14.2",
            54
          ],
          [
            "14.3",
            96
          ],
          [
            "14.4",
            39
          ],
          [
            "15.1",
            29
          ],
          [
            "15.2",
            39
          ],
          [
            "15.3",
            67
          ],
          [
            "16.1",
            70
          ],
          [
            "16.2",
            169
          ],
          [
            "17.2",
            219
          ]
        ],
        "foot": [
          [
            "~76 min",
            "median / story",
            "var(--done)"
          ],
          [
            "16–499 min",
            "observed range",
            ""
          ],
          [
            "57/57",
            "stories complete",
            "var(--done)"
          ],
          [
            "0",
            "remaining",
            ""
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
      },
      "lineState": {
        "state": "complete",
        "at": ""
      },
      "roadmap": {
        "sub": "Complete: all of Waves 0–H are shipped (per merged PRs #69–#102) — the Kedro port, MCP surface, parity harness, Universal SBOM intake, orchestration, the BSL + Vizro + Vizro-AI dashboards, A2A + OpenLineage/OTel, the full DuckDB singularity (cold-start gate, Pandera contracts, vss RAG, F4’s hygiene node importing Warden’s ComplianceReport), Wave G’s WASM read surface + static-host Parquet emitter + Dagster sensors, and Wave H’s AI software factory (Karpathy wiki + 5 factory personas, agno crews, La Suite sync, Dagster orchestration). The migration was closed out by the CFE Rule-2 retro #103 (v8.79.0) — 32/32. Wave I is NOT part of the migration: it is post-audit remediation, opened 2026-07-27 after an independent Round-3 spec-to-code audit raised 49 findings (PR #131, branch abandoned — the incorporation record is the only surviving account). Six stories close the verified atlas subset at source and all six landed (merged as PR #132, 6/6, kedro-test 803 -> 901 passed); it is ordered by the tested gate rather than by wave, because kedro-test was red on main until I3 landed.",
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
          ],
          [
            "I",
            "post-audit truth-up",
            "done"
          ]
        ]
      },
      "epics": [
        {
          "badge": "E1",
          "title": "Wave 0 — Legacy Translation via Skill Forge (SKF)",
          "stories": [
            [
              "1.1",
              "done",
              "Generate legacy contextual skill"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "Wave A — `nebi` Scaffold & Catalog",
          "stories": [
            [
              "2.1",
              "done",
              "Scaffold the Kedro + pixi project via `nebi`"
            ],
            [
              "2.2",
              "done",
              "Define the Data Catalog for all sources + outputs"
            ],
            [
              "2.3",
              "done",
              "Implement `IncrementalParquetDataset` for TTL gating"
            ]
          ]
        },
        {
          "badge": "E3",
          "title": "Wave B — Pipeline Node Porting & MCP Integration",
          "stories": [
            [
              "3.1",
              "done",
              "Port the conda-side backbone phases into Kedro nodes"
            ],
            [
              "3.2",
              "done",
              "Port the PyPI & Vulnerability pipelines"
            ],
            [
              "3.3",
              "done",
              "Re-expose the data surface as Kedro-API-native MCP tools"
            ],
            [
              "3.4",
              "done",
              "Verify dataset parity against the legacy orchestrator"
            ],
            [
              "3.5",
              "done",
              "Port the external-refresh assets (§ 3.4)"
            ],
            [
              "3.6",
              "done",
              "Port the Seed-Gaps pipeline"
            ],
            [
              "3.7",
              "done",
              "Extend the Universal SBOM intake (resolver, formats, universe BOM, buckets)"
            ],
            [
              "3.8",
              "done",
              "Basilisk conda-native vulnerability ingestion"
            ],
            [
              "3.9",
              "done",
              "Release-to-availability velocity columns"
            ],
            [
              "3.10",
              "done",
              "Migration-readiness datasets + classification node"
            ]
          ]
        },
        {
          "badge": "E4",
          "title": "Wave C — Orchestration & Visualization",
          "stories": [
            [
              "4.1",
              "done",
              "Integrate `kedro-dagster` for scheduling + execution"
            ],
            [
              "4.2",
              "done",
              "Integrate `kedro-viz` + expose a pixi task"
            ]
          ]
        },
        {
          "badge": "E5",
          "title": "Wave D — Semantic Layer & Dashboards",
          "stories": [
            [
              "5.1",
              "done",
              "Define the Boring Semantic Layer (BSL) models"
            ],
            [
              "5.2",
              "done",
              "Build the Vizro dashboard + port the 28 CLIs to pages"
            ],
            [
              "5.3",
              "done",
              "Integrate Vizro-AI + expose the NL interface as an MCP tool"
            ]
          ]
        },
        {
          "badge": "E6",
          "title": "Wave E — A2A Integration, Lineage & Observability",
          "stories": [
            [
              "6.1",
              "done",
              "Implement the A2A communication interfaces"
            ],
            [
              "6.2",
              "done",
              "Integrate OpenLineage + OpenTelemetry"
            ]
          ]
        },
        {
          "badge": "E7",
          "title": "Wave F — The DuckDB Singularity",
          "stories": [
            [
              "7.1",
              "done",
              "Complete the DuckDB consolidation + prove the cold-start claim"
            ],
            [
              "7.2",
              "done",
              "Implement the data-validation hook and inline Pandera contracts"
            ],
            [
              "7.3",
              "done",
              "Implement Vector Similarity Search (RAG) via DuckDB `vss`"
            ],
            [
              "7.4",
              "done",
              "Dependency-hygiene node + unified CI policy gate"
            ]
          ]
        },
        {
          "badge": "E8",
          "title": "Wave G — WebAssembly Portability & Event-Driven Sensors",
          "stories": [
            [
              "8.1",
              "done",
              "Compile the intelligence layer to Pyodide / DuckDB-WASM"
            ],
            [
              "8.2",
              "done",
              "Emit Parquet artifacts to a static web host"
            ],
            [
              "8.3",
              "done",
              "Implement Dagster Sensors for near-real-time ingestion"
            ]
          ]
        },
        {
          "badge": "E9",
          "title": "Wave H — The AI Software Factory & Karpathy Wiki",
          "stories": [
            [
              "9.1",
              "done",
              "Scaffold the Karpathy Wiki folder structure and Agent Personas"
            ],
            [
              "9.2",
              "done",
              "Implement Agno Compilation, Linting, and Q&A Crews"
            ],
            [
              "9.3",
              "done",
              "Integrate La Suite Docs REST API Sync"
            ],
            [
              "9.4",
              "done",
              "Orchestrate Crews via Dagster"
            ]
          ]
        },
        {
          "badge": "E10",
          "title": "Post-Audit Remediation — Round-3 Findings",
          "stories": [
            [
              "10.1",
              "done",
              "Restore atlas dependency-completeness so the suite can collect"
            ],
            [
              "10.2",
              "done",
              "Truth-up the Spec kernel and its companions"
            ],
            [
              "10.3",
              "done",
              "Uniform story-spec frontmatter, without laundering provenance"
            ],
            [
              "10.4",
              "done",
              "Preserve NULL identity under pandas 3.0"
            ],
            [
              "10.5",
              "done",
              "Stamp advisory data with its build provenance (AD-17)"
            ],
            [
              "10.6",
              "done",
              "Make run admission real, or stop claiming it"
            ]
          ]
        },
        {
          "badge": "E12",
          "title": "Kedro-org tooling — audit, publish, decide",
          "stories": [
            [
              "12.1",
              "done",
              "kedro-skills audit-then-adopt (FR-61)"
            ],
            [
              "12.2",
              "done",
              "Publish the real DAG continuously (FR-62)"
            ],
            [
              "12.3",
              "done",
              "Record the `vscode-kedro` verdict (FR-63)"
            ]
          ]
        },
        {
          "badge": "E13",
          "title": "Upstream discovery — what to package next",
          "stories": [
            [
              "13.1",
              "done",
              "Trending ingest (FR-64)"
            ],
            [
              "13.2",
              "done",
              "Tier classification (FR-65)"
            ],
            [
              "13.3",
              "done",
              "`trending-candidates` operator surface (FR-66)"
            ],
            [
              "13.4",
              "done",
              "Fixed-source audit track (FR-67)"
            ],
            [
              "13.5",
              "done",
              "Downstream handoff to Mason (FR-68)"
            ]
          ]
        },
        {
          "badge": "E14",
          "title": "Atlas query dashboards — hand-someone-a-link views",
          "stories": [
            [
              "14.1",
              "done",
              "Static view catalog (CAP-1)"
            ],
            [
              "14.2",
              "done",
              "Pluggable widget registry (CAP-3)"
            ],
            [
              "14.3",
              "done",
              "Bokeh WebSocket interactivity (CAP-2)"
            ],
            [
              "14.4",
              "done",
              "Air-gap asset rewriting (CAP-4)"
            ]
          ]
        },
        {
          "badge": "E15",
          "title": "Artifactory download intelligence — mock-first AQL",
          "stories": [
            [
              "15.1",
              "done",
              "Injectable AQL adapter (CAP-1)"
            ],
            [
              "15.2",
              "done",
              "Identity join and internal flag (CAP-2, CAP-3)"
            ],
            [
              "15.3",
              "done",
              "Kedro pipeline surfacing (CAP-4)"
            ]
          ]
        },
        {
          "badge": "E16",
          "title": "Wagtail corporate brain — the narrow DW-H3 contract",
          "stories": [
            [
              "16.1",
              "done",
              "Instance deploy definition (CAP-1)"
            ],
            [
              "16.2",
              "done",
              "Httpx opener and rehearsal (CAP-2, CAP-3)"
            ]
          ]
        },
        {
          "badge": "E17",
          "title": "The packaging-inventory intake engine, governed",
          "stories": [
            [
              "17.1",
              "done",
              "The from-scratch run is a chartered capability"
            ],
            [
              "17.2",
              "done",
              "Handoffs are execution-ready"
            ]
          ]
        }
      ],
      "owner": "atlas",
      "practice": false
    },
    "doctor": {
      "label": "Doctor",
      "accentVar": "--warden",
      "branch": "loop/pyforge-doctor",
      "contract": "9 FRs · exit codes {0,2,130} strict subset of warden's · consolidative wrap of atlas/warden instruments · dist pyforge-doctor / CLI doctor",
      "seglabels": [
        "E1 · spine",
        "E2 · wedge",
        "E3–E5",
        "E6 · multi-axis"
      ],
      "inflight": null,
      "velocity": {
        "derived": true,
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals. 29 of 61 stories measured; the rest predate loop instrumentation and carry wall-clock only (a different metric — see the timing strip), so they are deliberately absent rather than plotted on this axis. A story still in flight contributes only its CLOSED sessions, so its bar is a floor, not a total.",
        "bars": [
          [
            "1.1",
            101
          ],
          [
            "1.2",
            65
          ],
          [
            "1.3",
            42
          ],
          [
            "1.4",
            427
          ],
          [
            "1.5",
            80
          ],
          [
            "6.2",
            50
          ],
          [
            "6.3",
            34
          ],
          [
            "6.4",
            123
          ],
          [
            "6.5",
            145
          ],
          [
            "6.6",
            195
          ],
          [
            "6.8",
            139
          ],
          [
            "6.9",
            217
          ],
          [
            "6.10",
            58
          ],
          [
            "6.11",
            397
          ],
          [
            "7.1",
            99
          ],
          [
            "7.2",
            79
          ],
          [
            "7.3",
            403
          ],
          [
            "7.4",
            259
          ],
          [
            "9.1",
            31
          ],
          [
            "9.2",
            64
          ],
          [
            "9.3",
            43
          ],
          [
            "9.4",
            40
          ],
          [
            "10.1",
            61
          ],
          [
            "10.2",
            65
          ],
          [
            "10.3",
            92
          ],
          [
            "11.1",
            68
          ],
          [
            "11.2",
            63
          ],
          [
            "11.3",
            96
          ],
          [
            "11.4",
            93
          ]
        ],
        "foot": [
          [
            "~80 min",
            "median / story",
            "var(--done)"
          ],
          [
            "31–427 min",
            "observed range",
            ""
          ],
          [
            "61/61",
            "stories complete",
            "var(--done)"
          ],
          [
            "0",
            "remaining",
            ""
          ]
        ]
      },
      "timing": {
        "derived": true,
        "metric": "active agent-compute per story (dev + review; excludes gate-pause wait) — from bmad-loop run journals",
        "total": 3629,
        "totalLabel": "~60.5 h active compute",
        "note": "Derived from 29 measured stories; a story still in flight contributes only its closed sessions.",
        "perStory": {
          "1.1": 101,
          "1.2": 65,
          "1.3": 42,
          "1.4": 427,
          "1.5": 80,
          "6.2": 50,
          "6.3": 34,
          "6.4": 123,
          "6.5": 145,
          "6.6": 195,
          "6.8": 139,
          "6.9": 217,
          "6.10": 58,
          "6.11": 397,
          "7.1": 99,
          "7.2": 79,
          "7.3": 403,
          "7.4": 259,
          "9.1": 31,
          "9.2": 64,
          "9.3": 43,
          "9.4": 40,
          "10.1": 61,
          "10.2": 65,
          "10.3": 92,
          "11.1": 68,
          "11.2": 63,
          "11.3": 96,
          "11.4": 93
        },
        "epicMin": {
          "E1": 715,
          "E6": 1358,
          "E7": 840,
          "E9": 178,
          "E10": 218,
          "E11": 320
        }
      },
      "lineState": {
        "state": "complete",
        "at": ""
      },
      "epics": [
        {
          "badge": "E1",
          "title": "Pre-flight Check (walking skeleton)",
          "stories": [
            [
              "1.1",
              "done",
              "Package scaffold, frozen Finding/DoctorReport contract & exit-code module"
            ],
            [
              "1.2",
              "done",
              "Wrap warden's engine-availability self-check (FR-1)"
            ],
            [
              "1.3",
              "done",
              "Tri-state, individually addressable checks (FR-2)"
            ],
            [
              "1.4",
              "done",
              "Credential/environment-hygiene check (FR-3)"
            ],
            [
              "1.5",
              "done",
              "`doctor check` CLI wiring, `--json`, and the speed budget (FR-9, NFR-4)"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "Fleet Pulse (doctor monitor --fleet)",
          "stories": [
            [
              "2.1",
              "done",
              "Atlas gather filter — staleness axis, MCP-first with CLI fallback (FR-5, AD-6)"
            ],
            [
              "2.2",
              "done",
              "cve and abandonment watch axes (FR-4)"
            ],
            [
              "2.3",
              "done",
              "`doctor monitor --fleet` CLI wiring, default axis set, `--json` (FR-9)"
            ]
          ]
        },
        {
          "badge": "E3",
          "title": "Diagnose & Prescribe (doctor diagnose --prescribe)",
          "stories": [
            [
              "3.1",
              "done",
              "Partition findings by actionability (FR-6, AD-4)"
            ],
            [
              "3.2",
              "done",
              "Rank the actionable partition (FR-7, AD-4)"
            ],
            [
              "3.3",
              "done",
              "Root-cause naming (FR-8)"
            ],
            [
              "3.4",
              "done",
              "`doctor diagnose --target … --prescribe` CLI wiring, `--json` (FR-9)"
            ]
          ]
        },
        {
          "badge": "E4",
          "title": "The frontier, decomposed (v1.x — added 2026-08-02)",
          "stories": [
            [
              "4.1",
              "done",
              "Health scoring (FR-10)"
            ],
            [
              "4.2",
              "done",
              "Persistent fleet-health surface (FR-11)"
            ],
            [
              "4.3",
              "done",
              "Adoption-tracking watch axis (FR-12)"
            ],
            [
              "4.4",
              "done",
              "Safe upgrade-path recommendation (FR-13)"
            ]
          ]
        },
        {
          "badge": "E5",
          "title": "The verdict on the Marshal's own row",
          "stories": [
            [
              "5.1",
              "done",
              "Marshal-durability source, independent by construction"
            ],
            [
              "5.2",
              "done",
              "Render the verdict through a `doctor` verb"
            ]
          ]
        },
        {
          "badge": "E6",
          "title": "Every verdict comes home (Charter §6, generalized)",
          "stories": [
            [
              "6.1",
              "done",
              "Profile `doctor check` and bring it inside its budget"
            ],
            [
              "6.2",
              "done",
              "A source registry Doctor owns"
            ],
            [
              "6.3",
              "done",
              "The repo/runtime split survives the move"
            ],
            [
              "6.4",
              "done",
              "The ledger verdicts come home"
            ],
            [
              "6.5",
              "done",
              "The board verdicts come home"
            ],
            [
              "6.6",
              "done",
              "The chain verdicts come home"
            ],
            [
              "6.7",
              "done",
              "`forward_dependency` comes home, and the harness coupling is decided"
            ],
            [
              "6.8",
              "done",
              "`bmad_drift` comes home without breaking the board"
            ],
            [
              "6.9",
              "done",
              "The `scripts/` shims retire"
            ],
            [
              "6.10",
              "done",
              "Independence is structural, for every source"
            ],
            [
              "6.11",
              "done",
              "The classifier recognizes a spike report *(added 2026-08-11 — FR-16)*"
            ]
          ]
        },
        {
          "badge": "E7",
          "title": "Deferred-work visibility",
          "stories": [
            [
              "7.1",
              "done",
              "The emitter mints identity at defer time"
            ],
            [
              "7.2",
              "done",
              "Grandfather the 470 at a dated cut-off"
            ],
            [
              "7.3",
              "done",
              "The detector sees anonymous Tier-3 entries"
            ],
            [
              "7.4",
              "done",
              "One severity, both sides"
            ]
          ]
        },
        {
          "badge": "E8",
          "title": "The legacy deferred-work backlog comes home",
          "stories": [
            [
              "8.1",
              "done",
              "The parser reads every legacy Tier-3 shape"
            ],
            [
              "8.2",
              "done",
              "Minting picks the next free suffix per station convention"
            ],
            [
              "8.3",
              "done",
              "The fix mode promotes the backlog and refuses on collision"
            ],
            [
              "8.4",
              "done",
              "The baseline re-stamps so a second run is a no-op"
            ]
          ]
        },
        {
          "badge": "E9",
          "title": "The hygiene sweep generalizes, and staleness surfaces itself",
          "stories": [
            [
              "9.1",
              "done",
              "The five hygiene finding classes get testable definitions"
            ],
            [
              "9.2",
              "done",
              "The sweep runs against all eight stations"
            ],
            [
              "9.3",
              "done",
              "Hygiene findings report and never mutate"
            ],
            [
              "9.4",
              "done",
              "Loop-home staleness surfaces in the ATTENTION block"
            ]
          ]
        },
        {
          "badge": "E10",
          "title": "Doctor notices when BMAD-METHOD's own installed core falls behind upstream",
          "stories": [
            [
              "10.1",
              "done",
              "The declared floor and the installed core are compared and reported"
            ],
            [
              "10.2",
              "done",
              "The installed core is compared against the latest upstream release"
            ],
            [
              "10.3",
              "done",
              "The drift surfaces ambiently, never gates"
            ]
          ]
        },
        {
          "badge": "E11",
          "title": "Tracked deferred-work entries get periodically re-verified against live code",
          "stories": [
            [
              "11.1",
              "done",
              "Due-for-verification entries are selected, per project"
            ],
            [
              "11.2",
              "done",
              "Churn-based cost filtering skips entries whose code has not moved"
            ],
            [
              "11.3",
              "done",
              "Mechanically-checkable claims are verified without an agent"
            ],
            [
              "11.4",
              "done",
              "Judgment-requiring entries get an evidence-grounded verdict"
            ],
            [
              "11.5",
              "done",
              "Verification reaches across project boundaries"
            ],
            [
              "11.6",
              "done",
              "Near-duplicate entries surface as one defect class"
            ],
            [
              "11.7",
              "done",
              "Verification staleness surfaces in the ambient fleet report"
            ]
          ]
        },
        {
          "badge": "E12",
          "title": "The fleet's own hygiene/verification tooling gets its documented sharp edges fixed",
          "stories": [
            [
              "12.1",
              "done",
              "The hygiene/verification catalog stays a maintained, current artifact"
            ],
            [
              "12.2",
              "done",
              "The exemplar standard conformance table is refreshed and re-verified"
            ],
            [
              "12.3",
              "done",
              "Chain completeness parses capability ids, not a bare substring match"
            ],
            [
              "12.4",
              "done",
              "Dream chain gap count surfaces in the ambient ATTENTION block"
            ],
            [
              "12.5",
              "done",
              "The spec surface baseline write race is closed"
            ]
          ]
        },
        {
          "badge": "E13",
          "title": "Backlog-intake surfaces deferred entries during story drafting",
          "stories": [
            [
              "13.1",
              "done",
              "A drafting session surfaces matching deferred-work entries for an epic"
            ]
          ]
        },
        {
          "badge": "E14",
          "title": "The bmad-suite's lag is as visible as the core's",
          "stories": [
            [
              "14.1",
              "done",
              "The bmad-suite is compared against upstream, derived not declared"
            ]
          ]
        },
        {
          "badge": "E15",
          "title": "The suite pipeline's drift is ambient at every stage",
          "stories": [
            [
              "15.1",
              "done",
              "GitHub releases unblind the npm-invisible packages"
            ],
            [
              "15.2",
              "done",
              "Channel and recipe staleness are ambient findings"
            ]
          ]
        },
        {
          "badge": "E16",
          "title": "Sibling dreams directories don't drift silently",
          "stories": [
            [
              "16.1",
              "done",
              "The shared-title diff is an ambient finding"
            ]
          ]
        }
      ],
      "owner": "doctor",
      "practice": false
    },
    "herald": {
      "label": "Herald",
      "accentVar": "--warden",
      "branch": "loop/pyforge-herald",
      "contract": "SPEC-design-code-bridge CAP-1..5 · FR-01–FR-26 · AD-1–AD-8 · deterministic no-LLM core · dist pyforge-herald / module pyforge.herald / CLI herald",
      "seglabels": [
        "E1 · spine",
        "E2 · wedge",
        "E3–E5",
        "E6 · multi-axis"
      ],
      "inflight": null,
      "velocity": {
        "derived": true,
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals. 14 of 58 stories measured; the rest predate loop instrumentation and carry wall-clock only (a different metric — see the timing strip), so they are deliberately absent rather than plotted on this axis. A story still in flight contributes only its CLOSED sessions, so its bar is a floor, not a total.",
        "bars": [
          [
            "1.1",
            60
          ],
          [
            "1.2",
            98
          ],
          [
            "1.3",
            29
          ],
          [
            "1.4",
            108
          ],
          [
            "1.5",
            417
          ],
          [
            "13.1",
            229
          ],
          [
            "13.2",
            169
          ],
          [
            "13.3",
            539
          ],
          [
            "13.4",
            144
          ],
          [
            "13.5",
            409
          ],
          [
            "13.6",
            342
          ],
          [
            "14.1",
            33
          ],
          [
            "14.2",
            62
          ],
          [
            "14.3",
            39
          ]
        ],
        "foot": [
          [
            "~126 min",
            "median / story",
            "var(--done)"
          ],
          [
            "29–539 min",
            "observed range",
            ""
          ],
          [
            "58/58",
            "stories complete",
            "var(--done)"
          ],
          [
            "0",
            "remaining",
            ""
          ]
        ]
      },
      "timing": {
        "derived": true,
        "metric": "active agent-compute per story (dev + review; excludes gate-pause wait) — from bmad-loop run journals",
        "total": 2678,
        "totalLabel": "~44.6 h active compute",
        "note": "Derived from 14 measured stories; a story still in flight contributes only its closed sessions.",
        "perStory": {
          "1.1": 60,
          "1.2": 98,
          "1.3": 29,
          "1.4": 108,
          "1.5": 417,
          "13.1": 229,
          "13.2": 169,
          "13.3": 539,
          "13.4": 144,
          "13.5": 409,
          "13.6": 342,
          "14.1": 33,
          "14.2": 62,
          "14.3": 39
        },
        "epicMin": {
          "E1": 712,
          "E13": 1832,
          "E14": 134
        }
      },
      "lineState": {
        "state": "complete",
        "at": ""
      },
      "epics": [
        {
          "badge": "E1",
          "title": "Foundation — package spine & transport",
          "stories": [
            [
              "1.1",
              "done",
              "Package scaffold for pyforge herald"
            ],
            [
              "1.2",
              "done",
              "Transport port primary mcp client adapter the transport spike"
            ],
            [
              "1.3",
              "done",
              "Fallback transport adapter"
            ],
            [
              "1.4",
              "done",
              "Bridge core skeleton state errors determinism boundary"
            ],
            [
              "1.5",
              "done",
              "Registry module readme design project"
            ],
            [
              "1.6",
              "done",
              "Herald deck seed slug"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "Deck pull — prototype, marp, bundle",
          "stories": [
            [
              "2.1",
              "done",
              "Herald deck pull slug prototype pull with etag short circuit"
            ],
            [
              "2.2",
              "done",
              "Commit opt in"
            ],
            [
              "2.3",
              "done",
              "Marp source pull"
            ],
            [
              "2.4",
              "done",
              "Standalone bundle pull"
            ]
          ]
        },
        {
          "badge": "E3",
          "title": "Deck status & stale-mirror detection",
          "stories": [
            [
              "3.1",
              "done",
              "Herald deck status slug"
            ],
            [
              "3.2",
              "done",
              "Stale hand mirror detection"
            ]
          ]
        },
        {
          "badge": "E4",
          "title": "Watch — poll, backoff, halt",
          "stories": [
            [
              "4.1",
              "done",
              "Poll loop with quiescence debounce"
            ],
            [
              "4.2",
              "done",
              "Idle backoff"
            ],
            [
              "4.3",
              "done",
              "Halt on auth error"
            ]
          ]
        },
        {
          "badge": "E5",
          "title": "Export push-back",
          "stories": [
            [
              "5.1",
              "done",
              "Push regenerated exports with etag guard"
            ],
            [
              "5.2",
              "done",
              "Conflict refusal on export push"
            ]
          ]
        },
        {
          "badge": "E6",
          "title": "Foundation — CLI architecture & shared infrastructure",
          "stories": [
            [
              "6.1",
              "done",
              "Implement Herald CLI Dispatcher"
            ],
            [
              "6.2",
              "done",
              "Implement Shared Argument Conventions"
            ],
            [
              "6.3",
              "done",
              "Implement CLI Authentication & Authorization"
            ],
            [
              "6.4",
              "done",
              "Implement Evidence Link Validation Protocol (Shared Infrastructure)"
            ],
            [
              "6.5",
              "done",
              "CLI Help & First-Day Usability (Inline)"
            ]
          ]
        },
        {
          "badge": "E7",
          "title": "Foundation — web surface",
          "stories": [
            [
              "7.1",
              "done",
              "Design & Implement Web Layout (Header, Tabs, Sidebar, Responsive)"
            ],
            [
              "7.2",
              "done",
              "Implement Web Tooltips & Inline Help"
            ]
          ]
        },
        {
          "badge": "E8",
          "title": "Moment 2 — progress visibility",
          "stories": [
            [
              "8.1",
              "done",
              "Implement Progress Data Model & Database Schema"
            ],
            [
              "8.2",
              "done",
              "Implement On-Ship Webhook & Weekly Cron Automation"
            ],
            [
              "8.3",
              "done",
              "Implement Progress CLI (`herald progress` subcommand)"
            ],
            [
              "8.4",
              "done",
              "Implement Progress Web Tab"
            ]
          ]
        },
        {
          "badge": "E9",
          "title": "Moment 3 — success proclamation",
          "stories": [
            [
              "9.1",
              "done",
              "Implement Claim Data Model & Database Schema"
            ],
            [
              "9.2",
              "done",
              "Implement Auto-Extract & Operator Review Gate"
            ],
            [
              "9.3",
              "done",
              "Implement Success CLI"
            ],
            [
              "9.4",
              "done",
              "Implement Success Web Archive"
            ],
            [
              "9.5",
              "done",
              "Implement Evidence Validation (Sync + Async)"
            ]
          ]
        },
        {
          "badge": "E10",
          "title": "Moment 4 — operations notices",
          "stories": [
            [
              "10.1",
              "done",
              "Notice Data Model & Archive Storage"
            ],
            [
              "10.2",
              "done",
              "Notice Authoring Workflow (CLI)"
            ],
            [
              "10.3",
              "done",
              "Notice Archive & Redirects"
            ],
            [
              "10.4",
              "done",
              "Notice CLI"
            ],
            [
              "10.5",
              "done",
              "Operations Web Tab"
            ],
            [
              "10.6",
              "done",
              "Notice Lifecycle"
            ]
          ]
        },
        {
          "badge": "E11",
          "title": "Integration testing & automation reliability",
          "stories": [
            [
              "11.1",
              "done",
              "Integration Testing (CLI + Web + Automation)"
            ],
            [
              "11.2",
              "done",
              "Automation Reliability"
            ],
            [
              "11.3",
              "done",
              "Evidence Linking (Cross-Moment)"
            ],
            [
              "11.4",
              "done",
              "Performance Testing"
            ]
          ]
        },
        {
          "badge": "E12",
          "title": "Documentation & operator experience",
          "stories": [
            [
              "12.1",
              "done",
              "CLI Runbooks & Troubleshooting"
            ],
            [
              "12.2",
              "done",
              "Web Surface UX Guide"
            ],
            [
              "12.3",
              "done",
              "Operator Runbook"
            ],
            [
              "12.4",
              "done",
              "Automation Troubleshooting Guide"
            ]
          ]
        },
        {
          "badge": "E13",
          "title": "The live backend — a ship records itself",
          "stories": [
            [
              "13.1",
              "done",
              "The state layer survives a second writer"
            ],
            [
              "13.2",
              "done",
              "The serverless-intermediate decision, recorded"
            ],
            [
              "13.3",
              "done",
              "DB-backed storage behind the existing seam, with migrations"
            ],
            [
              "13.4",
              "done",
              "The webhook endpoint CI calls"
            ],
            [
              "13.5",
              "done",
              "The scheduler enforces what was displayed"
            ],
            [
              "13.6",
              "done",
              "A ship records itself, end to end"
            ]
          ]
        },
        {
          "badge": "E14",
          "title": "A deck is proven to look right",
          "stories": [
            [
              "14.1",
              "done",
              "Gate report interface"
            ],
            [
              "14.2",
              "done",
              "Headless render gate"
            ],
            [
              "14.3",
              "done",
              "Image slot scan"
            ]
          ]
        },
        {
          "badge": "E15",
          "title": "Editable decks — the PowerPoint-native pipeline",
          "stories": [
            [
              "15.1",
              "done",
              "Template-parse-then-fill produces a genuinely editable deck"
            ],
            [
              "15.2",
              "done",
              "Dense content renders as shapes that fit"
            ]
          ]
        }
      ],
      "owner": "herald",
      "practice": false
    },
    "marshal": {
      "label": "Marshal",
      "accentVar": "--accent",
      "branch": "loop/pyforge-marshal · CRITICALS-RESOLVED — S-1.1 unblocked 2026-07-25",
      "contract": "spec-pyforge-marshal · graduated autonomy on the factory floor · AD-25..39 6 CRITICALs resolved; 12 HIGH + 8 MED open · S-1.10 renders harness policy (closes the F-1 bleed)",
      "seglabels": [
        "E1",
        "E2",
        "E3",
        "E4",
        "E5",
        "E6"
      ],
      "inflight": null,
      "velocity": {
        "derived": true,
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals. 58 of 162 stories measured; the rest predate loop instrumentation and carry wall-clock only (a different metric — see the timing strip), so they are deliberately absent rather than plotted on this axis. A story still in flight contributes only its CLOSED sessions, so its bar is a floor, not a total.",
        "bars": [
          [
            "1.1",
            165
          ],
          [
            "1.2",
            65
          ],
          [
            "1.3",
            153
          ],
          [
            "1.4",
            97
          ],
          [
            "1.5",
            69
          ],
          [
            "1.6",
            450
          ],
          [
            "1.7",
            110
          ],
          [
            "1.8",
            92
          ],
          [
            "1.9",
            80
          ],
          [
            "1.10",
            62
          ],
          [
            "2.1",
            142
          ],
          [
            "2.2",
            27
          ],
          [
            "2.4",
            35
          ],
          [
            "2.5",
            34
          ],
          [
            "2.6",
            121
          ],
          [
            "2.8",
            398
          ],
          [
            "3.1",
            57
          ],
          [
            "3.2",
            91
          ],
          [
            "3.3",
            169
          ],
          [
            "3.4",
            153
          ],
          [
            "3.5",
            271
          ],
          [
            "3.6",
            168
          ],
          [
            "3.7",
            486
          ],
          [
            "3.11",
            398
          ],
          [
            "3.12",
            328
          ],
          [
            "3.13",
            63
          ],
          [
            "4.11",
            58
          ],
          [
            "4.12",
            126
          ],
          [
            "4.13",
            75
          ],
          [
            "4.14",
            193
          ],
          [
            "4.15",
            33
          ],
          [
            "5.8",
            53
          ],
          [
            "5.9",
            200
          ],
          [
            "5.10",
            44
          ],
          [
            "7.1",
            39
          ],
          [
            "7.4",
            143
          ],
          [
            "7.5",
            107
          ],
          [
            "7.6",
            37
          ],
          [
            "8.1",
            75
          ],
          [
            "8.2",
            60
          ],
          [
            "8.3",
            96
          ],
          [
            "8.4",
            69
          ],
          [
            "8.5",
            212
          ],
          [
            "9.1",
            60
          ],
          [
            "9.2",
            81
          ],
          [
            "9.3",
            72
          ],
          [
            "9.4",
            49
          ],
          [
            "9.5",
            49
          ],
          [
            "9.6",
            249
          ],
          [
            "10.1",
            66
          ],
          [
            "10.2",
            65
          ],
          [
            "10.3",
            80
          ],
          [
            "10.4",
            124
          ],
          [
            "14.1",
            36
          ],
          [
            "14.2",
            223
          ],
          [
            "14.3",
            97
          ],
          [
            "14.4",
            101
          ],
          [
            "16.1",
            76
          ]
        ],
        "foot": [
          [
            "~86 min",
            "median / story",
            "var(--done)"
          ],
          [
            "27–486 min",
            "observed range",
            ""
          ],
          [
            "113/162",
            "stories complete",
            "var(--done)"
          ],
          [
            "49",
            "remaining",
            ""
          ]
        ]
      },
      "timing": {
        "derived": true,
        "metric": "active agent-compute per story (dev + review; excludes gate-pause wait) — from bmad-loop run journals",
        "total": 7332,
        "totalLabel": "~122.2 h active compute",
        "note": "Derived from 58 measured stories; a story still in flight contributes only its closed sessions.",
        "perStory": {
          "1.1": 165,
          "1.2": 65,
          "1.3": 153,
          "1.4": 97,
          "1.5": 69,
          "1.6": 450,
          "1.7": 110,
          "1.8": 92,
          "1.9": 80,
          "1.10": 62,
          "2.1": 142,
          "2.2": 27,
          "2.4": 35,
          "2.5": 34,
          "2.6": 121,
          "2.8": 398,
          "3.1": 57,
          "3.2": 91,
          "3.3": 169,
          "3.4": 153,
          "3.5": 271,
          "3.6": 168,
          "3.7": 486,
          "3.11": 398,
          "3.12": 328,
          "3.13": 63,
          "4.11": 58,
          "4.12": 126,
          "4.13": 75,
          "4.14": 193,
          "4.15": 33,
          "5.8": 53,
          "5.9": 200,
          "5.10": 44,
          "7.1": 39,
          "7.4": 143,
          "7.5": 107,
          "7.6": 37,
          "8.1": 75,
          "8.2": 60,
          "8.3": 96,
          "8.4": 69,
          "8.5": 212,
          "9.1": 60,
          "9.2": 81,
          "9.3": 72,
          "9.4": 49,
          "9.5": 49,
          "9.6": 249,
          "10.1": 66,
          "10.2": 65,
          "10.3": 80,
          "10.4": 124,
          "14.1": 36,
          "14.2": 223,
          "14.3": 97,
          "14.4": 101,
          "16.1": 76
        },
        "epicMin": {
          "E1": 1343,
          "E2": 757,
          "E3": 2184,
          "E4": 485,
          "E5": 297,
          "E7": 326,
          "E8": 512,
          "E9": 560,
          "E10": 335,
          "E14": 457,
          "E16": 76
        }
      },
      "lineState": {
        "state": "paused",
        "at": "11.5"
      },
      "epics": [
        {
          "badge": "E1",
          "title": "Provisioned, verified loop homes",
          "stories": [
            [
              "1.1",
              "done",
              "Package spine, verdict lattice, findings registry, and the meta-tests that enforce them"
            ],
            [
              "1.2",
              "done",
              "Story identity, merge-subject rendering, and feed completeness"
            ],
            [
              "1.3",
              "done",
              "Layered policy composition with provenance and validation"
            ],
            [
              "1.10",
              "done",
              "Render the harness policy from the canonical EffectivePolicy"
            ],
            [
              "1.4",
              "done",
              "Provision a loop home"
            ],
            [
              "1.5",
              "done",
              "Single-sourced Tier-3 store via backlink"
            ],
            [
              "1.6",
              "done",
              "Isolation verification and home enumeration"
            ],
            [
              "1.7",
              "done",
              "Preflight, adapter config seeding, and first-run acknowledgement"
            ],
            [
              "1.8",
              "done",
              "Teardown that refuses to destroy work"
            ],
            [
              "1.9",
              "done",
              "Packaging, distribution, and version reporting"
            ],
            [
              "1.12",
              "done",
              "A stale loop home cannot be spun *(added 2026-08-09 — FR-180)*"
            ],
            [
              "1.11",
              "done",
              "A loop agent cannot mutate repo-wide git state *(added 2026-08-09 — FR-178)*"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "Gates you can run",
          "stories": [
            [
              "2.1",
              "done",
              "Standalone verify-command runner, project-scoped"
            ],
            [
              "2.2",
              "done",
              "Verdict aggregation that never false-greens"
            ],
            [
              "2.3",
              "done",
              "Frozen-surface scope check, narrowing only"
            ],
            [
              "2.4",
              "done",
              "Doc-only story classification"
            ],
            [
              "2.5",
              "done",
              "Gate mode ladder with autonomy labels"
            ],
            [
              "2.6",
              "done",
              "Gate evidence record with redaction at egress"
            ],
            [
              "2.7",
              "done",
              "A gate binds to the spec's Success signal *(added 2026-08-01 — FR-64 / AD-49)*"
            ],
            [
              "2.8",
              "done",
              "A low-risk story's review runs lighter, never absent *(added 2026-08-11 — FR-185)*"
            ]
          ]
        },
        {
          "badge": "E3",
          "title": "Supervised unattended runs",
          "stories": [
            [
              "3.1",
              "done",
              "Run identity and the journal writer"
            ],
            [
              "3.2",
              "done",
              "The journal fold — one producer for accumulating run state"
            ],
            [
              "3.3",
              "done",
              "Detached launch with scoped story selection"
            ],
            [
              "3.4",
              "done",
              "Supervisor process lifecycle"
            ],
            [
              "3.5",
              "done",
              "Idle-strand detection"
            ],
            [
              "3.6",
              "done",
              "Budget ceilings and the heaviest-story advisory"
            ],
            [
              "3.7",
              "done",
              "Escalation, deferral, and resume"
            ],
            [
              "3.8",
              "done",
              "Stage-bound durability, and fleet-launch wiring *(added 2026-08-01 — FR-61 / AD-46)*"
            ],
            [
              "3.9",
              "done",
              "A retired story branch is not a push failure"
            ],
            [
              "3.10",
              "done",
              "Unpushed work is measured by tip, never by name"
            ],
            [
              "3.11",
              "done",
              "A story's declared difficulty actually picks its model *(added 2026-08-11 — FR-182)*"
            ],
            [
              "3.12",
              "done",
              "A struggling retry runs under a stronger model *(added 2026-08-11 — FR-183)*"
            ],
            [
              "3.13",
              "done",
              "The parallel-fan-out clamp is surfaced, not silent *(added 2026-08-11 — FR-184)*"
            ]
          ]
        },
        {
          "badge": "E4",
          "title": "Landing with a durable paper trail",
          "stories": [
            [
              "4.1",
              "done",
              "Story-spec promotion with a durability predicate"
            ],
            [
              "4.2",
              "done",
              "Teardown reachability and spec-recovery assistance"
            ],
            [
              "4.3",
              "done",
              "Merge-subject conformance and review-cap landing"
            ],
            [
              "4.4",
              "done",
              "Batch pull request with hygiene preflight"
            ],
            [
              "4.5",
              "done",
              "Feed refresh with truth partitioned by domain"
            ],
            [
              "4.6",
              "done",
              "Deploy idempotence and reconciliation of open intents"
            ],
            [
              "4.7",
              "done",
              "Landing rules as declared policy *(added 2026-08-01 — FR-59 / CAP-9)*"
            ],
            [
              "4.8",
              "done",
              "`marshal land` — the last mile lands itself *(added 2026-08-01 — FR-60 / CAP-9)*"
            ],
            [
              "4.9",
              "done",
              "Derived surfaces regenerate on main; the shared store takes a lock *(added 2026-08-01 — AD-42 / the Q-10 decomposition)*"
            ],
            [
              "4.10",
              "done",
              "Fleet-wide branch retirement *(added 2026-08-01 — FR-63 / AD-47)*"
            ],
            [
              "4.11",
              "done",
              "`marshal land` refuses while a run is in flight *(added 2026-08-09 — FR-172)*"
            ],
            [
              "4.12",
              "done",
              "A landing leaves the loop home current with `main` *(added 2026-08-09 — FR-173)*"
            ],
            [
              "4.13",
              "done",
              "The loop's deferred work reaches the tracked ledger *(added 2026-08-09 — FR-175)*"
            ],
            [
              "4.14",
              "done",
              "The failed-story safety net is reported *(added 2026-08-09 — FR-176)*"
            ],
            [
              "4.15",
              "done",
              "One pusher, not two *(added 2026-08-09 — FR-177)*"
            ]
          ]
        },
        {
          "badge": "E5",
          "title": "Fleet visibility",
          "stories": [
            [
              "5.1",
              "done",
              "Fleet view"
            ],
            [
              "5.2",
              "done",
              "Per-run detail"
            ],
            [
              "5.3",
              "done",
              "Escalation queue"
            ],
            [
              "5.4",
              "done",
              "Ledger-vs-git reconciliation and the versioned status contract"
            ],
            [
              "5.5",
              "done",
              "Durability as a reported fleet-status dimension *(added 2026-08-01 — FR-62 / AD-48)*"
            ],
            [
              "5.6",
              "done",
              "`marshal check` — the detector registry through the front door *(added 2026-08-01 — FR-65 / AD-50)*"
            ],
            [
              "5.7",
              "done",
              "The board answers \"how much is left\" *(added 2026-08-09 — FR-179)*"
            ],
            [
              "5.8",
              "done",
              "A dead supervisor sidecar doesn't hide a live engine *(added 2026-08-11 — FR-181)*"
            ],
            [
              "5.9",
              "done",
              "A story finished by hand isn't invisible to the ledger *(added 2026-08-11 — FR-186)*"
            ],
            [
              "5.10",
              "done",
              "`marshal land` renders a detectable merge subject *(added 2026-08-12 — FR-187, backlog)*"
            ]
          ]
        },
        {
          "badge": "E6",
          "title": "Portability proven",
          "stories": [
            [
              "6.1",
              "done",
              "Profile-driven adapter selection, project-scoped"
            ],
            [
              "6.2",
              "done",
              "Skill-tree projection"
            ],
            [
              "6.3",
              "done",
              "Projection drift detection that can actually fail"
            ],
            [
              "6.4",
              "done",
              "Adapter probe with a machine-scoped record"
            ],
            [
              "6.5",
              "done",
              "Conformance smoke in an ephemeral home"
            ],
            [
              "6.6",
              "done",
              "The conformance matrix"
            ],
            [
              "6.7",
              "done",
              "Entry-file family drift check, detect-only"
            ],
            [
              "6.8",
              "done",
              "Upstream contribution register"
            ],
            [
              "6.9",
              "done",
              "Tool-surface rendering and preflight probe *(added 2026-08-01 — AD-43 / the Q-11 resolution; post-MVP)*"
            ]
          ]
        },
        {
          "badge": "E7",
          "title": "Foundation & the Write Guard",
          "stories": [
            [
              "7.1",
              "done",
              "The seed module tree inside pyforge-marshal"
            ],
            [
              "7.2",
              "done",
              "Error taxonomy and exit codes"
            ],
            [
              "7.3",
              "done",
              "The `fs` write primitive and the never-write guard"
            ],
            [
              "7.4",
              "done",
              "Manifest schema, loader, and model-version ranges"
            ],
            [
              "7.5",
              "done",
              "The V1 extraction manifest (the model, as data)"
            ],
            [
              "7.6",
              "done",
              "Spike-0 — Copier API fit (CRITICAL GATE)"
            ]
          ]
        },
        {
          "badge": "E8",
          "title": "The Managed-Region Engine",
          "stories": [
            [
              "8.1",
              "done",
              "Marker grammar and the per-format registry"
            ],
            [
              "8.2",
              "done",
              "Region parser — span discovery, nesting rejection, fence awareness"
            ],
            [
              "8.3",
              "done",
              "Span substitution — the update primitive"
            ],
            [
              "8.4",
              "done",
              "Anchor resolution and region insertion"
            ],
            [
              "8.5",
              "done",
              "Marker deletion as a sanctioned opt-out"
            ]
          ]
        },
        {
          "badge": "E9",
          "title": "Detect & Plan",
          "stories": [
            [
              "9.1",
              "done",
              "Findings model — severity, types, remedies"
            ],
            [
              "9.2",
              "done",
              "Repo inventory walker and artifact classification"
            ],
            [
              "9.3",
              "done",
              "Content hashing for managed files and regions"
            ],
            [
              "9.4",
              "done",
              "Legacy convention detection"
            ],
            [
              "9.5",
              "done",
              "Manifest coverage check"
            ],
            [
              "9.6",
              "done",
              "Plan and Action types, repo fingerprint, and the plan builder"
            ]
          ]
        },
        {
          "badge": "E10",
          "title": "Materialize & the Core Verbs",
          "stories": [
            [
              "10.1",
              "done",
              "Copier engine wrapper — the single seam"
            ],
            [
              "10.2",
              "done",
              "State schema and the atomic store"
            ],
            [
              "10.3",
              "done",
              "The apply runner — transactional, guarded"
            ],
            [
              "10.4",
              "done",
              "Preconditions, refusals, and skips"
            ],
            [
              "10.5",
              "done",
              "`marshal seed check`"
            ],
            [
              "10.6",
              "done",
              "`marshal seed adopt`"
            ],
            [
              "10.7",
              "done",
              "`marshal seed init`"
            ],
            [
              "10.8",
              "done",
              "Manifest-declared writable artifacts are exempt from their own never-write collision"
            ]
          ]
        },
        {
          "badge": "E11",
          "title": "Derive, Migrate & Update",
          "stories": [
            [
              "11.1",
              "done",
              "Neutral contract and agent-adapter fan-out"
            ],
            [
              "11.2",
              "done",
              "`PROJECTS.md` index and artifact-symlink derivation"
            ],
            [
              "11.3",
              "done",
              "Migration registry and runner"
            ],
            [
              "11.4",
              "done",
              "`marshal seed update` — two-phase"
            ],
            [
              "11.5",
              "pending",
              "Referenced-dependency verification and Doctor delegation"
            ],
            [
              "11.6",
              "pending",
              "`marshal seed explain` and `marshal seed version`"
            ]
          ]
        },
        {
          "badge": "E12",
          "title": "Packaging, Oracle & Hardening",
          "stories": [
            [
              "12.1",
              "pending",
              "Full pixi wiring, distribution, and repo-gate compliance"
            ],
            [
              "12.2",
              "pending",
              "The `local-recipes` empty-plan oracle (CRITICAL)"
            ],
            [
              "12.3",
              "pending",
              "Offline operation and the egress counter"
            ],
            [
              "12.4",
              "pending",
              "Pattern meta-tests and the never-write proof"
            ],
            [
              "12.5",
              "pending",
              "CLI contract, idempotence harness, and performance gates"
            ],
            [
              "12.6",
              "pending",
              "README, adoption guide, and the finding→remedy reference"
            ]
          ]
        },
        {
          "badge": "E13",
          "title": "Surface drift reconciliation — a gate that can be cleared, a signal that can be trusted",
          "stories": [
            [
              "13.1",
              "done",
              "A baseline can be stamped for one spec"
            ],
            [
              "13.2",
              "done",
              "A moved contract reconciles only the paths it names"
            ],
            [
              "13.3",
              "done",
              "The no-baseline, ungoverned and stale-allowlist findings are cleared"
            ],
            [
              "13.4",
              "done",
              "The 34 drift findings are reconciled or recorded"
            ],
            [
              "13.5",
              "done",
              "A Spec cannot declare a surface it has no contract for"
            ],
            [
              "13.6",
              "done",
              "The presumed set is worked down by measurement"
            ],
            [
              "13.7",
              "done",
              "The producer reconciles the surface it drifts *(added 2026-08-09 — FR-174)*"
            ]
          ]
        },
        {
          "badge": "E14",
          "title": "The shared floor — pyforge-core",
          "stories": [
            [
              "14.1",
              "done",
              "The leaf exists and is provably a leaf"
            ],
            [
              "14.2",
              "done",
              "Atomic write has one implementation"
            ],
            [
              "14.3",
              "done",
              "One lattice, one envelope, one exception root"
            ],
            [
              "14.4",
              "done",
              "The subprocess seam is reconciled and sole ownership is gated"
            ]
          ]
        },
        {
          "badge": "E15",
          "title": "Fleet operations run themselves",
          "stories": [
            [
              "15.1",
              "pending",
              "One command refreshes the fleet's homes"
            ],
            [
              "15.2",
              "pending",
              "Landing promotes the ledger, and staleness is its own check"
            ]
          ]
        },
        {
          "badge": "E16",
          "title": "The board derives truth",
          "stories": [
            [
              "16.1",
              "done",
              "One resolver, derived sources, loud failures"
            ]
          ]
        },
        {
          "badge": "E17",
          "title": "Instruments verified, chains regenerable",
          "stories": [
            [
              "17.1",
              "pending",
              "The detectors' remaining blind spots are fixture-pinned, with an incident log"
            ],
            [
              "17.2",
              "pending",
              "The dreams hygiene mode exists"
            ],
            [
              "17.3",
              "pending",
              "Chain-completeness audit mode reports layers"
            ],
            [
              "17.4",
              "pending",
              "Orchestrated regeneration that cannot lose code status"
            ]
          ]
        },
        {
          "badge": "E18",
          "title": "The governed tool surface",
          "stories": [
            [
              "18.1",
              "pending",
              "Marshal's capabilities become named, typed tools"
            ],
            [
              "18.2",
              "pending",
              "Parity and coverage are gated numbers"
            ]
          ]
        },
        {
          "badge": "E19",
          "title": "The testing charter, enforced",
          "stories": [
            [
              "19.1",
              "pending",
              "One generator produces every station's test architecture"
            ],
            [
              "19.2",
              "pending",
              "The shared test-support kit"
            ],
            [
              "19.3",
              "pending",
              "Coverage gates that name the module"
            ],
            [
              "19.4",
              "pending",
              "Test architecture stays current as stories land"
            ]
          ]
        },
        {
          "badge": "E20",
          "title": "The loop cannot lose work, and a landing is always recognizable",
          "stories": [
            [
              "20.1",
              "pending",
              "Baseline-drift detector at the seam"
            ],
            [
              "20.2",
              "pending",
              "Baseline-drift defers get loud"
            ],
            [
              "20.3",
              "pending",
              "The gated upstream filing"
            ],
            [
              "20.4",
              "pending",
              "Intent-gap attempts are preserved"
            ],
            [
              "20.5",
              "pending",
              "Missing-preserve detector"
            ],
            [
              "20.6",
              "pending",
              "The verify_scope primitive"
            ],
            [
              "20.7",
              "pending",
              "Both guards hard-fail on drift"
            ],
            [
              "20.8",
              "pending",
              "The landing-evidence grammar"
            ],
            [
              "20.9",
              "pending",
              "Doctor consumes the grammar"
            ],
            [
              "20.10",
              "pending",
              "Marshal consumes the grammar"
            ]
          ]
        },
        {
          "badge": "E21",
          "title": "The planning chain regenerates itself, and audits whether it's coherent",
          "stories": [
            [
              "21.1",
              "pending",
              "Chain-completeness audit mode extends layer-presence into full CAP-3 coverage"
            ],
            [
              "21.2",
              "pending",
              "Orchestrated chain regeneration"
            ],
            [
              "21.3",
              "pending",
              "Code-status preservation"
            ],
            [
              "21.4",
              "pending",
              "Orphan detection with review-gated cleanup"
            ],
            [
              "21.5",
              "pending",
              "Configurable per-project invocation"
            ]
          ]
        },
        {
          "badge": "E22",
          "title": "Single-story dispatch is a marshal verb, not a session's discipline",
          "stories": [
            [
              "22.1",
              "pending",
              "The dispatch verb launches one governed, isolated story session"
            ],
            [
              "22.2",
              "pending",
              "Completion is judged from git and process facts, and a zombie is never redispatched"
            ],
            [
              "22.3",
              "pending",
              "Verification is the product — no landing on a self-report"
            ],
            [
              "22.4",
              "pending",
              "A verified story lands through the existing machinery, classified marshal-native"
            ],
            [
              "22.5",
              "pending",
              "One story in flight per station; stations in parallel; overlap is loud"
            ],
            [
              "22.6",
              "pending",
              "The dispatched run survives its operator, and its journal carries the timing signal"
            ]
          ]
        },
        {
          "badge": "E23",
          "title": "Velocity captures hand-driven work",
          "stories": [
            [
              "23.1",
              "pending",
              "Wall-clock fallback derivation from promoted-spec revision fields"
            ],
            [
              "23.2",
              "pending",
              "Wall-clock is never blended with active-compute"
            ],
            [
              "23.3",
              "pending",
              "The coverage caption partitions by true reason"
            ]
          ]
        },
        {
          "badge": "E24",
          "title": "Liveness is one command",
          "stories": [
            [
              "24.1",
              "pending",
              "Marshal gains the missing liveness primitive"
            ],
            [
              "24.2",
              "pending",
              "The operator answer is one documented command"
            ],
            [
              "24.3",
              "pending",
              "An UNSUPERVISED row has a cheap, documented double-check"
            ]
          ]
        },
        {
          "badge": "E25",
          "title": "Aligned to the installed BMAD era",
          "stories": [
            [
              "25.1",
              "done",
              "Retired skill IDs are purged and guarded"
            ],
            [
              "25.2",
              "done",
              "bmad-loop's repo skills match the installed package"
            ],
            [
              "25.3",
              "done",
              "Every spec folder accepts a 6.11 bmad-spec update"
            ],
            [
              "25.4",
              "done",
              "The 0.10/0.11 policy knobs are governable"
            ],
            [
              "25.5",
              "done",
              "Marshal speaks the 0.11 status vocabulary"
            ],
            [
              "25.6",
              "pending",
              "A hand-driven run's deferrals reach the ledger unaided"
            ],
            [
              "25.7",
              "pending",
              "The factory's living docs are re-grounded, with a named owner"
            ]
          ]
        }
      ],
      "owner": "marshal",
      "practice": false
    },
    "mason": {
      "label": "Mason",
      "accentVar": "--accent",
      "branch": "main · S-1.1 landed outside the loop",
      "contract": "spec-pyforge-mason · recipe / package / environment · `recipe` WRAPS the conda-forge-expert craft by subprocess, never forks it (D-1 Option C)",
      "seglabels": [
        "E1",
        "E2",
        "E3",
        "E4",
        "E5"
      ],
      "inflight": null,
      "velocity": {
        "derived": true,
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals. 37 of 47 stories measured; the rest predate loop instrumentation and carry wall-clock only (a different metric — see the timing strip), so they are deliberately absent rather than plotted on this axis. A story still in flight contributes only its CLOSED sessions, so its bar is a floor, not a total.",
        "bars": [
          [
            "1.2",
            91
          ],
          [
            "1.3",
            402
          ],
          [
            "1.4",
            36
          ],
          [
            "1.5",
            16
          ],
          [
            "1.6",
            36
          ],
          [
            "1.7",
            34
          ],
          [
            "1.8",
            46
          ],
          [
            "1.9",
            49
          ],
          [
            "1.10",
            162
          ],
          [
            "2.1",
            45
          ],
          [
            "2.2",
            124
          ],
          [
            "2.3",
            119
          ],
          [
            "2.4",
            396
          ],
          [
            "2.5",
            435
          ],
          [
            "2.6",
            308
          ],
          [
            "2.7",
            82
          ],
          [
            "2.8",
            102
          ],
          [
            "2.9",
            58
          ],
          [
            "2.10",
            57
          ],
          [
            "3.1",
            57
          ],
          [
            "3.2",
            64
          ],
          [
            "3.3",
            41
          ],
          [
            "3.4",
            42
          ],
          [
            "3.5",
            74
          ],
          [
            "3.6",
            93
          ],
          [
            "3.7",
            238
          ],
          [
            "3.8",
            118
          ],
          [
            "3.9",
            133
          ],
          [
            "4.1",
            44
          ],
          [
            "4.2",
            37
          ],
          [
            "4.3",
            56
          ],
          [
            "4.4",
            127
          ],
          [
            "5.1",
            33
          ],
          [
            "5.2",
            48
          ],
          [
            "5.3",
            79
          ],
          [
            "5.4",
            14
          ],
          [
            "5.5",
            284
          ]
        ],
        "foot": [
          [
            "~64 min",
            "median / story",
            "var(--done)"
          ],
          [
            "14–435 min",
            "observed range",
            ""
          ],
          [
            "47/47",
            "stories complete",
            "var(--done)"
          ],
          [
            "0",
            "remaining",
            ""
          ]
        ]
      },
      "timing": {
        "derived": true,
        "metric": "active agent-compute per story (dev + review; excludes gate-pause wait) — from bmad-loop run journals",
        "total": 4180,
        "totalLabel": "~69.7 h active compute",
        "note": "Derived from 37 measured stories; a story still in flight contributes only its closed sessions.",
        "perStory": {
          "1.2": 91,
          "1.3": 402,
          "1.4": 36,
          "1.5": 16,
          "1.6": 36,
          "1.7": 34,
          "1.8": 46,
          "1.9": 49,
          "1.10": 162,
          "2.1": 45,
          "2.2": 124,
          "2.3": 119,
          "2.4": 396,
          "2.5": 435,
          "2.6": 308,
          "2.7": 82,
          "2.8": 102,
          "2.9": 58,
          "2.10": 57,
          "3.1": 57,
          "3.2": 64,
          "3.3": 41,
          "3.4": 42,
          "3.5": 74,
          "3.6": 93,
          "3.7": 238,
          "3.8": 118,
          "3.9": 133,
          "4.1": 44,
          "4.2": 37,
          "4.3": 56,
          "4.4": 127,
          "5.1": 33,
          "5.2": 48,
          "5.3": 79,
          "5.4": 14,
          "5.5": 284
        },
        "epicMin": {
          "E1": 872,
          "E2": 1726,
          "E3": 860,
          "E4": 264,
          "E5": 458
        }
      },
      "lineState": {
        "state": "complete",
        "at": ""
      },
      "epics": [
        {
          "badge": "E1",
          "title": "Install, run, and diagnose Mason",
          "stories": [
            [
              "1.1",
              "done",
              "Workspace member scaffold and dual-artifact build"
            ],
            [
              "1.2",
              "done",
              "CLI noun-verb structure and global flags"
            ],
            [
              "1.3",
              "done",
              "Error taxonomy and exit-code contract"
            ],
            [
              "1.4",
              "done",
              "Dual output format with stream discipline"
            ],
            [
              "1.5",
              "done",
              "CFE root resolution chain"
            ],
            [
              "1.6",
              "done",
              "Interpreter selection and CFE import-floor probe"
            ],
            [
              "1.7",
              "done",
              "Degradation when CFE is unavailable"
            ],
            [
              "1.8",
              "done",
              "`mason doctor`"
            ],
            [
              "1.9",
              "done",
              "Fake CFE root fixture and test harness"
            ],
            [
              "1.10",
              "done",
              "Configuration surface, logging, and child-output streaming"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "Author, build, and submit recipes",
          "stories": [
            [
              "2.1",
              "done",
              "The CFE port"
            ],
            [
              "2.2",
              "done",
              "The seam guard"
            ],
            [
              "2.3",
              "done",
              "Credential isolation"
            ],
            [
              "2.4",
              "done",
              "`mason recipe new`"
            ],
            [
              "2.5",
              "done",
              "`mason recipe validate`"
            ],
            [
              "2.6",
              "done",
              "`mason recipe build`"
            ],
            [
              "2.7",
              "done",
              "`mason recipe diagnose`"
            ],
            [
              "2.8",
              "done",
              "`mason recipe optimize` and `mason recipe scan`"
            ],
            [
              "2.9",
              "done",
              "`mason recipe submit`"
            ],
            [
              "2.10",
              "done",
              "`mason recipe update`"
            ]
          ]
        },
        {
          "badge": "E3",
          "title": "Ship a library to both ecosystems",
          "stories": [
            [
              "3.1",
              "done",
              "Engine protocol and provisioning"
            ],
            [
              "3.2",
              "done",
              "`mason package build`"
            ],
            [
              "3.3",
              "done",
              "Ship-target vocabulary and dry-run default"
            ],
            [
              "3.4",
              "done",
              "The `pypi` ship target"
            ],
            [
              "3.5",
              "done",
              "The `channel:<name>` ship target"
            ],
            [
              "3.6",
              "done",
              "The `conda-forge` ship target"
            ],
            [
              "3.9",
              "done",
              "The `ship` verb and TestPyPI rehearsal"
            ],
            [
              "3.7",
              "done",
              "Asymmetric receipts, partial failure, and idempotence"
            ],
            [
              "3.8",
              "done",
              "Mason ships Mason"
            ]
          ]
        },
        {
          "badge": "E4",
          "title": "Bind environments into lockfiles",
          "stories": [
            [
              "4.1",
              "done",
              "Lock engine adapter and provenance"
            ],
            [
              "4.2",
              "done",
              "Manifest discovery"
            ],
            [
              "4.3",
              "done",
              "`mason environment lock`"
            ],
            [
              "4.4",
              "done",
              "`mason environment check`"
            ]
          ]
        },
        {
          "badge": "E5",
          "title": "Prove the seam holds",
          "stories": [
            [
              "5.1",
              "done",
              "CFE-independence test"
            ],
            [
              "5.2",
              "done",
              "Governance test"
            ],
            [
              "5.3",
              "done",
              "Delegation-fidelity test"
            ],
            [
              "5.4",
              "done",
              "Free-inheritance verification"
            ],
            [
              "5.5",
              "done",
              "Rule-2 conda-forge-expert retrospective"
            ]
          ]
        },
        {
          "badge": "E6",
          "title": "The CFE rebuild — pilot slice, parallel-run, and the re-scope gate",
          "stories": [
            [
              "6.1",
              "done",
              "Slice map and campaign state"
            ],
            [
              "6.2",
              "done",
              "The divergence-and-endgame guard, proven red first"
            ],
            [
              "6.3",
              "done",
              "Pilot slice — recipe generation, built and parallel-validated"
            ],
            [
              "6.4",
              "done",
              "The re-scope gate — measured cost, recorded decision"
            ]
          ]
        },
        {
          "badge": "E7",
          "title": "Machine-checked recipe knowledge",
          "stories": [
            [
              "7.1",
              "done",
              "The failure catalog derives from the skill spec"
            ],
            [
              "7.2",
              "done",
              "The pointers lint and the drift gates"
            ]
          ]
        },
        {
          "badge": "E8",
          "title": "One pixi base-layer discipline across the Containerfiles",
          "stories": [
            [
              "8.1",
              "done",
              "The convention is written and guarded"
            ]
          ]
        },
        {
          "badge": "E9",
          "title": "External integration seams",
          "stories": [
            [
              "9.1",
              "done",
              "The repo's CI is consumable via workflow_call"
            ],
            [
              "9.2",
              "done",
              "The air-gap distribution contract has a socket"
            ]
          ]
        }
      ],
      "owner": "mason",
      "practice": false
    },
    "scribe": {
      "label": "Scribe",
      "accentVar": "--warden",
      "branch": "loop/pyforge-scribe",
      "contract": "15 FRs · event-sourced capture + rebuildable read-model · team memory + knowledge graph · dist pyforge-scribe / CLI scribe",
      "seglabels": [
        "E1 · spine",
        "E2 · wedge",
        "E3–E5",
        "E6 · multi-axis"
      ],
      "inflight": null,
      "velocity": {
        "derived": true,
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals. 4 of 11 stories measured; the rest predate loop instrumentation and carry wall-clock only (a different metric — see the timing strip), so they are deliberately absent rather than plotted on this axis. A story still in flight contributes only its CLOSED sessions, so its bar is a floor, not a total.",
        "bars": [
          [
            "1.1",
            70
          ],
          [
            "1.2",
            39
          ],
          [
            "1.3",
            360
          ],
          [
            "1.4",
            9
          ]
        ],
        "foot": [
          [
            "~54 min",
            "median / story",
            "var(--done)"
          ],
          [
            "9–360 min",
            "observed range",
            ""
          ],
          [
            "11/11",
            "stories complete",
            "var(--done)"
          ],
          [
            "0",
            "remaining",
            ""
          ]
        ]
      },
      "timing": {
        "derived": true,
        "metric": "active agent-compute per story (dev + review; excludes gate-pause wait) — from bmad-loop run journals",
        "total": 478,
        "totalLabel": "~8.0 h active compute",
        "note": "Derived from 4 measured stories; a story still in flight contributes only its closed sessions.",
        "perStory": {
          "1.1": 70,
          "1.2": 39,
          "1.3": 360,
          "1.4": 9
        },
        "epicMin": {
          "E1": 478
        }
      },
      "lineState": {
        "state": "complete",
        "at": ""
      },
      "epics": [
        {
          "badge": "E1",
          "title": "Team Memory — Capture & Promotion",
          "stories": [
            [
              "1.1",
              "done",
              "Package scaffold + direct capture into team memory"
            ],
            [
              "1.2",
              "done",
              "`CLAUDE.md` wiring — team memory loads automatically"
            ],
            [
              "1.3",
              "done",
              "Promotion workflow — proposal-then-confirm, team-voice rewrite"
            ],
            [
              "1.4",
              "done",
              "Pointer-stub write-back + idempotent re-invocation"
            ],
            [
              "1.5",
              "done",
              "Seed promotion — the end-to-end proof"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "Knowledge Graph — Compile & Recall",
          "stories": [
            [
              "2.1",
              "done",
              "`GraphStore` port + flat-file v1 adapter"
            ],
            [
              "2.2",
              "done",
              "Nightly compile from named tool surfaces"
            ],
            [
              "2.3",
              "done",
              "Fact supersession in the compiled graph"
            ],
            [
              "2.4",
              "done",
              "`scribe recall` — grounded, cited answers"
            ]
          ]
        },
        {
          "badge": "E3",
          "title": "Scribe reaches the raw transcripts",
          "stories": [
            [
              "3.1",
              "done",
              "The scanner surfaces what sessions said but memory missed"
            ],
            [
              "3.2",
              "done",
              "Transcripts join the compile sources"
            ]
          ]
        }
      ],
      "owner": "scribe",
      "practice": false
    },
    "steward": {
      "label": "Steward",
      "accentVar": "--accent",
      "branch": "main · S-1.1 landed outside the loop",
      "contract": "spec-pyforge-steward · keys / deploy / provision / budget · Duty protocol (AD-7); main() sole owner of the exit code (AD-8)",
      "seglabels": [
        "E1",
        "E2",
        "E3",
        "E4"
      ],
      "inflight": null,
      "velocity": {
        "derived": true,
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals. 19 of 74 stories measured; the rest predate loop instrumentation and carry wall-clock only (a different metric — see the timing strip), so they are deliberately absent rather than plotted on this axis. A story still in flight contributes only its CLOSED sessions, so its bar is a floor, not a total.",
        "bars": [
          [
            "8.1",
            182
          ],
          [
            "8.2",
            61
          ],
          [
            "8.3",
            44
          ],
          [
            "8.4",
            81
          ],
          [
            "8.5",
            27
          ],
          [
            "8.6",
            61
          ],
          [
            "8.7",
            128
          ],
          [
            "9.1",
            147
          ],
          [
            "9.2",
            400
          ],
          [
            "9.3",
            468
          ],
          [
            "9.4",
            296
          ],
          [
            "9.5",
            80
          ],
          [
            "9.6",
            47
          ],
          [
            "9.7",
            204
          ],
          [
            "10.1",
            122
          ],
          [
            "10.2",
            84
          ],
          [
            "10.3",
            280
          ],
          [
            "10.4",
            91
          ],
          [
            "11.1",
            184
          ]
        ],
        "foot": [
          [
            "~122 min",
            "median / story",
            "var(--done)"
          ],
          [
            "27–468 min",
            "observed range",
            ""
          ],
          [
            "53/74",
            "stories complete",
            "var(--done)"
          ],
          [
            "21",
            "remaining",
            ""
          ]
        ]
      },
      "timing": {
        "derived": true,
        "metric": "active agent-compute per story (dev + review; excludes gate-pause wait) — from bmad-loop run journals",
        "total": 2987,
        "totalLabel": "~49.8 h active compute",
        "note": "Derived from 19 measured stories; a story still in flight contributes only its closed sessions.",
        "perStory": {
          "8.1": 182,
          "8.2": 61,
          "8.3": 44,
          "8.4": 81,
          "8.5": 27,
          "8.6": 61,
          "8.7": 128,
          "9.1": 147,
          "9.2": 400,
          "9.3": 468,
          "9.4": 296,
          "9.5": 80,
          "9.6": 47,
          "9.7": 204,
          "10.1": 122,
          "10.2": 84,
          "10.3": 280,
          "10.4": 91,
          "11.1": 184
        },
        "epicMin": {
          "E8": 584,
          "E9": 1642,
          "E10": 577,
          "E11": 184
        }
      },
      "lineState": {
        "state": "paused",
        "at": "12.3"
      },
      "epics": [
        {
          "badge": "E1",
          "title": "Keys — Credential Lifecycle",
          "stories": [
            [
              "1.1",
              "done",
              "Steward exists as an installable CLI"
            ],
            [
              "1.2",
              "done",
              "Credentials never attach outside their declared host, and the JFrog leak can never recur silently"
            ],
            [
              "1.3",
              "done",
              "Secrets Steward stores live encrypted in Git, never as plaintext"
            ],
            [
              "1.4",
              "done",
              "Rotating a key never breaks what already trusted it"
            ],
            [
              "1.5",
              "done",
              "The operator can see every credential Steward knows about, never a secret value"
            ],
            [
              "1.6",
              "done",
              "The operator can ask \"is anything host-unscoped right now?\" and get a real answer"
            ],
            [
              "1.7",
              "done",
              "Retiring a credential leaves a record, not a silent gap"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "Deploy — Reconciled Dashboard Publishing",
          "stories": [
            [
              "2.1",
              "done",
              "The dashboard builds through Steward, not a bare pixi task the operator has to remember"
            ],
            [
              "2.2",
              "done",
              "Nothing happens unless something actually changed"
            ],
            [
              "2.3",
              "done",
              "The operator can see what would change before it changes"
            ],
            [
              "2.4",
              "done",
              "The operator can ask \"when did the dashboard last actually deploy?\""
            ]
          ]
        },
        {
          "badge": "E3",
          "title": "Provision — Environment & Runner Access",
          "stories": [
            [
              "3.1",
              "done",
              "Any named pixi environment materializes with one command"
            ],
            [
              "3.2",
              "done",
              "A bmad-loop runner and its environment materialize together"
            ],
            [
              "3.3",
              "done",
              "The operator can see every environment that exists, before picking one"
            ],
            [
              "3.4",
              "done",
              "The environment.yaml sync gate is one command away, not a remembered incantation"
            ]
          ]
        },
        {
          "badge": "E4",
          "title": "Budget — Declared Resource Ceilings",
          "stories": [
            [
              "4.1",
              "done",
              "A ceiling can be declared, machine-readably"
            ],
            [
              "4.2",
              "done",
              "The declared ceiling is one command away"
            ],
            [
              "4.3",
              "done",
              "Asking \"am I under budget?\" never lies"
            ]
          ]
        },
        {
          "badge": "E5",
          "title": "The Marshal seam — obligations from the 2026-08-08 seam ratification",
          "stories": [
            [
              "5.1",
              "done",
              "Retire `provision --runner bmad-loop` in favour of `marshal init`"
            ],
            [
              "5.2",
              "done",
              "Consume the sprint ledger; never derive story status"
            ]
          ]
        },
        {
          "badge": "E6",
          "title": "Module provisioning",
          "stories": [
            [
              "6.1",
              "done",
              "`provision --module <name>`"
            ],
            [
              "6.2",
              "done",
              "`provision --list-modules`"
            ],
            [
              "6.3",
              "done",
              "Partial install is a named failure"
            ]
          ]
        },
        {
          "badge": "E7",
          "title": "The one-container Guild",
          "stories": [
            [
              "7.1",
              "done",
              "One build, whole Guild"
            ],
            [
              "7.2",
              "done",
              "The repo at a fixed short path"
            ],
            [
              "7.3",
              "done",
              "Credentials never enter image layers"
            ],
            [
              "7.4",
              "done",
              "State outlives the container"
            ],
            [
              "7.5",
              "done",
              "The image proves itself at build time"
            ]
          ]
        },
        {
          "badge": "E8",
          "title": "Two boards, one truth",
          "stories": [
            [
              "8.1",
              "done",
              "Bidirectional propagation"
            ],
            [
              "8.2",
              "done",
              "Zero-loop guarantee"
            ],
            [
              "8.3",
              "done",
              "Idempotent update processing"
            ],
            [
              "8.4",
              "done",
              "The schedule trigger enumerates real candidates"
            ],
            [
              "8.5",
              "done",
              "Fail loud, fail alone"
            ],
            [
              "8.6",
              "done",
              "Explicit status-vocabulary translation"
            ],
            [
              "8.7",
              "done",
              "Assignee and identity-link propagation"
            ]
          ]
        },
        {
          "badge": "E9",
          "title": "Secure live dashboards",
          "stories": [
            [
              "9.1",
              "done",
              "Identity at the boundary, declared isolation, and the cache invariant"
            ],
            [
              "9.2",
              "done",
              "An unauthorized page is absent, not hidden"
            ],
            [
              "9.3",
              "done",
              "The audit trail records what was seen"
            ],
            [
              "9.4",
              "done",
              "Export gated server-side"
            ],
            [
              "9.5",
              "done",
              "The perimeter ships with the pattern"
            ],
            [
              "9.6",
              "done",
              "Isolation proven by tests that cannot pass vacuously"
            ],
            [
              "9.7",
              "done",
              "Hosted or static, no fork"
            ]
          ]
        },
        {
          "badge": "E10",
          "title": "python-agent-platform — the host takes root",
          "stories": [
            [
              "10.1",
              "done",
              "The host renders into src/platform"
            ],
            [
              "10.2",
              "done",
              "One factory-sourced environment"
            ],
            [
              "10.3",
              "done",
              "One image, both engines"
            ],
            [
              "10.4",
              "done",
              "The bcrypt pin stops blocking 3.14"
            ],
            [
              "10.5",
              "done",
              "The DB-GPT sidecar image + docker-compose wiring"
            ]
          ]
        },
        {
          "badge": "E11",
          "title": "The engines join as pluggable apps",
          "stories": [
            [
              "11.1",
              "done",
              "Langflow joins as a pluggable app"
            ],
            [
              "11.2",
              "done",
              "DB-GPT joins via its configured integration pattern"
            ],
            [
              "11.3",
              "done",
              "Async work never blocks Django"
            ],
            [
              "11.4",
              "done",
              "Isolation and statelessness proven"
            ]
          ]
        },
        {
          "badge": "E12",
          "title": "Deploy anywhere, including nowhere-connected",
          "stories": [
            [
              "12.1",
              "done",
              "The vanilla chart with an OCP overlay"
            ],
            [
              "12.2",
              "done",
              "GKE as a portability profile"
            ],
            [
              "12.3",
              "pending",
              "Air-gap parity is a failing check"
            ]
          ]
        },
        {
          "badge": "E13",
          "title": "Scratch worktrees become one command",
          "stories": [
            [
              "13.1",
              "pending",
              "Workspace verbs over git worktree"
            ],
            [
              "13.2",
              "pending",
              "Status and the feed-mirror decision"
            ],
            [
              "13.3",
              "pending",
              "A repo set opens as one workspace"
            ],
            [
              "13.4",
              "pending",
              "The set reports and tears down safely"
            ]
          ]
        },
        {
          "badge": "E14",
          "title": "The BMAD core upgrades repeatably",
          "stories": [
            [
              "14.1",
              "pending",
              "The pre-flight diff retrodicts a real upgrade"
            ],
            [
              "14.2",
              "pending",
              "Apply is deliberate, branched, and never clobbers custom"
            ],
            [
              "14.3",
              "pending",
              "Clobbered custom surfaces are caught and re-applied"
            ],
            [
              "14.4",
              "pending",
              "The pin fan-out is enumerated, not discovered by red tests"
            ],
            [
              "14.5",
              "pending",
              "One command proves the upgrade landed"
            ]
          ]
        },
        {
          "badge": "E15",
          "title": "The bmad-suite channel is a governed product",
          "stories": [
            [
              "15.1",
              "pending",
              "One command reports the whole pipeline's truth"
            ],
            [
              "15.2",
              "pending",
              "One command advances a stale package end-to-end"
            ],
            [
              "15.3",
              "pending",
              "Five modules wire through the provisioning verb"
            ],
            [
              "15.4",
              "pending",
              "The upgrade gate spot-checks one native path per class"
            ]
          ]
        },
        {
          "badge": "E16",
          "title": "The platform host earns its 15 factors",
          "stories": [
            [
              "16.1",
              "pending",
              "Dependencies are pixi-sourced, single-authority"
            ],
            [
              "16.2",
              "pending",
              "Startup refuses misconfiguration, two-stage and named"
            ],
            [
              "16.3",
              "pending",
              "Every process speaks structlog + OTel"
            ],
            [
              "16.4",
              "pending",
              "Policy is a test suite"
            ],
            [
              "16.5",
              "pending",
              "Identity is OIDC-delegated, no local passwords"
            ]
          ]
        },
        {
          "badge": "E17",
          "title": "A fresh machine reaches validate-fast through steward verbs",
          "stories": [
            [
              "17.1",
              "pending",
              "steward init/shell-init detect and prepare the machine"
            ],
            [
              "17.2",
              "pending",
              "steward setup/initrepo take the machine to green"
            ]
          ]
        }
      ],
      "owner": "steward",
      "practice": false
    },
    "warden": {
      "label": "Warden",
      "accentVar": "--warden",
      "branch": "main · WARDEN COMPLETE ✔ 31/31 — all 6 epics merged to main (PR #110); history purged, key rotated",
      "contract": "FR1–FR40 · exit codes {0,1,2,130} · verdict lattice error &gt; policy-violation &gt; indeterminate &gt; warn &gt; bypassed &gt; clean &gt; not-applicable",
      "seglabels": [
        "E1 · spine",
        "E2 · wedge",
        "E3–E5",
        "E6 · multi-axis"
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
          ],
          [
            "6.4",
            35
          ],
          [
            "6.3",
            265
          ],
          [
            "6.5",
            105
          ],
          [
            "6.7",
            83
          ],
          [
            "6.8",
            89
          ],
          [
            "6.9",
            60
          ],
          [
            "6.6",
            83
          ],
          [
            "5.1",
            147
          ],
          [
            "5.2",
            175
          ]
        ],
        "foot": [
          [
            "~85 min",
            "median / story",
            "var(--done)"
          ],
          [
            "35–265 min",
            "observed range",
            ""
          ],
          [
            "31/31",
            "stories complete",
            "var(--done)"
          ],
          [
            "0",
            "remaining — Warden done",
            ""
          ]
        ]
      },
      "timing": {
        "metric": "active agent-compute per story (dev + review; excludes gate-pause wait) — from bmad-loop run journals",
        "totalLabel": "~41 h active compute",
        "note": "Measured stories only. The earliest keystones 1.1 / 1.2, plus 2.6 and the recovered 6.10 spike, predate clean journaling and are excluded. 6.4’s bar is its delivered dev-2 pass (35m); a rolled-back dev-1 cost ~49m more that isn’t counted as delivery. 6.9’s bar (~60m) is the dev-to-commit span recovered from a stalled session + a manual adversarial review. 5.1’s bar (147m) is its full span across TWO adversarial review cycles (the followup-flagged security fixes re-reviewed until clean). Epic-6 note: 6.10 (design spike) + 6.2 have no journal record — bars show journal-backed stories only; 6.3 / 6.5 / 6.7 mined from loop-home run journals.",
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
          "6.4": 35,
          "6.3": 265,
          "6.5": 105,
          "6.7": 83,
          "6.8": 89,
          "6.9": 60,
          "6.6": 83,
          "5.1": 147,
          "5.2": 175
        },
        "epicMin": {
          "E1": 534,
          "E2": 617,
          "E3": 264,
          "E4": 96,
          "E5": 322,
          "E6": 801
        },
        "total": 2264
      },
      "lineState": {
        "state": "paused",
        "at": "7.3"
      },
      "epics": [
        {
          "badge": "E1",
          "title": "Spine + PyPI engine (walking skeleton)",
          "stories": [
            [
              "1.1",
              "done",
              "Frozen contract, verdict lattice & projection-safety (C0a)"
            ],
            [
              "1.2",
              "done",
              "Interfaces, null engine, regression harness & socket-deny (C0c)"
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
              "Manifest discovery, deterministic selection & the resolved scan set (FR1)"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "The conda/pixi source-manifest wedge",
          "stories": [
            [
              "2.1",
              "done",
              "conda→pypi map + the ecosystem-identity predicate"
            ],
            [
              "2.2",
              "done",
              "Non-rendering extraction (common case) + differential-oracle"
            ],
            [
              "2.3",
              "done",
              "The full supported-construct matrix (ratcheted)"
            ],
            [
              "2.4",
              "done",
              "Honest split coverage + the indeterminate producer (C0b)"
            ],
            [
              "2.5",
              "done",
              "Name-level CVE tier + stale-DB + cross-ecosystem non-merge"
            ],
            [
              "2.6",
              "done",
              "Lockfile extraction — the locked-closure vuln hero path (split from 2.1, 2026-07-16)"
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
              "done",
              "Actionable diagnostics & safe-by-default posture"
            ],
            [
              "5.2",
              "done",
              "Fleet-scale validation + corpus/oracle maturation"
            ]
          ]
        },
        {
          "badge": "E6",
          "title": "Multi-axis expansion — license, currency, KEV/EPSS & adoption (added 2026-07-15; re-baselined 2026-07-16, D12)",
          "stories": [
            [
              "6.1",
              "done",
              "The versioned `ComplianceReport` schema amendment"
            ],
            [
              "6.2",
              "done",
              "License axis producer + gate flags (Axis 3)"
            ],
            [
              "6.3",
              "done",
              "Currency axis producer + gate flags (Axis 4)"
            ],
            [
              "6.4",
              "done",
              "KEV feed provisioning, enrichment & the `--fail-on-kev` gate"
            ],
            [
              "6.5",
              "done",
              "Two-mode policy integration (unconfigured visibility + flag-activated gating)"
            ],
            [
              "6.6",
              "done",
              "Engine version-range pinning (the distribution gate)"
            ],
            [
              "6.7",
              "done",
              "EPSS feed + the `--min-epss` gate"
            ],
            [
              "6.8",
              "done",
              "Baseline & grandfathering (gate new findings only)"
            ],
            [
              "6.9",
              "done",
              "Fix-PR actuator (opt-in remediation PRs)"
            ],
            [
              "6.10",
              "done",
              "Amendment design spike — finding-ID families, verdict encoding, rung-discriminator & fold semantics (decision record)"
            ]
          ]
        },
        {
          "badge": "E7",
          "title": "One provenance trail, one eligibility answer",
          "stories": [
            [
              "7.1",
              "done",
              "SourceContract adapters + the identity API"
            ],
            [
              "7.2",
              "done",
              "The eligibility union carries its provenance"
            ],
            [
              "7.3",
              "pending",
              "CycloneDX out, the corpus in"
            ]
          ]
        },
        {
          "badge": "E8",
          "title": "A web face for the compliance factory",
          "stories": [
            [
              "8.1",
              "pending",
              "Upload runs the real engines, async"
            ],
            [
              "8.2",
              "pending",
              "Results render with derived progress"
            ]
          ]
        }
      ],
      "owner": "warden",
      "practice": false
    },
    "presenton-pixi-image": {
      "label": "Presenton-pixi-image",
      "accentVar": "--accent",
      "branch": "not started",
      "contract": "spec-presenton-pixi-image",
      "seglabels": [
        "E1",
        "E2",
        "E3",
        "E4",
        "E5",
        "E6"
      ],
      "inflight": null,
      "velocity": "",
      "timing": "",
      "lineState": {
        "state": "ready",
        "at": "1.1"
      },
      "epics": [
        {
          "badge": "E1",
          "title": "Phase-0 Decision Readiness",
          "stories": [
            [
              "1.1",
              "pending",
              "GGUF model and quantization tier selection"
            ],
            [
              "1.2",
              "pending",
              "Tier-1 reference LLM class commitment"
            ],
            [
              "1.3",
              "pending",
              "Fixture-capture v1 baseline (one-time, manual)"
            ],
            [
              "1.4",
              "pending",
              "JFrog allowlist gap analysis"
            ],
            [
              "1.5",
              "pending",
              "Capability Claim Statement committed"
            ],
            [
              "1.6",
              "pending",
              "Microsoft disconnected-stack verification (Redmond-contingency check)"
            ],
            [
              "1.7",
              "pending",
              "Memory-subsystem scope decision"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "Air-Gapped Browser Rendering Capability",
          "stories": [
            [
              "2.1",
              "pending",
              "Build, validate, scan, and optimize `playwright-with-chromium`"
            ],
            [
              "2.2",
              "pending",
              "Submit `playwright-with-chromium` to staged-recipes and land the merge"
            ]
          ]
        },
        {
          "badge": "E3",
          "title": "Clean-Room Deck Export Pipeline",
          "stories": [
            [
              "3.1",
              "pending",
              "Build, validate, scan, and optimize `presenton-export-node`"
            ],
            [
              "3.2",
              "pending",
              "Build, validate, scan, and optimize `pptx-assembler`"
            ],
            [
              "3.3",
              "pending",
              "Spike, build, validate, scan, and optimize `pptx-thumbnail-inject`"
            ],
            [
              "3.4",
              "pending",
              "Submit the three export-pipeline recipes and land the merges"
            ],
            [
              "3.5",
              "pending",
              "Wire the clean-room pipeline into Presenton via patches"
            ]
          ]
        },
        {
          "badge": "E4",
          "title": "LLM Provider Abstraction & Tiering",
          "stories": [
            [
              "4.1",
              "pending",
              "Build, validate, scan, and optimize `llmai`"
            ],
            [
              "4.2",
              "pending",
              "Submit `llmai` to staged-recipes and land the merge"
            ],
            [
              "4.3",
              "pending",
              "Wire the three-tier LLM provider model into the Helm chart"
            ],
            [
              "4.4",
              "pending",
              "Verify the `copilot-bridge` dev-path integration"
            ]
          ]
        },
        {
          "badge": "E5",
          "title": "Signed Air-Gapped Image Assembly",
          "stories": [
            [
              "5.1",
              "pending",
              "Assemble the pixi-locked build environment"
            ],
            [
              "5.2",
              "pending",
              "Assemble the OCI image via pixitainer"
            ],
            [
              "5.3",
              "pending",
              "Wire the memory-subsystem feature-flag fork"
            ],
            [
              "5.4",
              "pending",
              "Generate SBOM and sign the image"
            ]
          ]
        },
        {
          "badge": "E6",
          "title": "OCP Deployment & Operations",
          "stories": [
            [
              "6.1",
              "pending",
              "Helm chart with Restricted-SCC-compatible SecurityContext"
            ],
            [
              "6.2",
              "pending",
              "Wire the Chromium sandbox default and escape hatch"
            ],
            [
              "6.3",
              "pending",
              "Ship the versioned `/metrics` schema artifact"
            ],
            [
              "6.4",
              "pending",
              "Day-0 install preflight fixtures"
            ],
            [
              "6.5",
              "pending",
              "Day-2 operational fixtures shipped inside the image"
            ]
          ]
        },
        {
          "badge": "E7",
          "title": "Upstream Drift Defense",
          "stories": [
            [
              "7.1",
              "pending",
              "Reusable online-capture CI workflow"
            ],
            [
              "7.2",
              "pending",
              "Enforce the air-gapped/online CI-topology split"
            ],
            [
              "7.3",
              "pending",
              "Weekly drift-detection harness with auto-issue filing"
            ]
          ]
        }
      ],
      "owner": "mason",
      "practice": false
    }
  },
  "snapshot": "<span>2026-08-23 03:11 UTC</span> · source: sprint-status feeds + merged-PR ground truth (#58–#104) + bmad-loop run journals · timing: Warden = active compute (journals), Atlas = wall-clock (PR timestamps)",
  "defaultProject": "warden",
  "dreams": [
    {
      "slug": "adaptive-model-tiering",
      "title": "FR-51's model tiering is fully wired and never turned on",
      "status": "realized",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-adaptive-model-tiering"
      }
    },
    {
      "slug": "agent-portability",
      "title": "Agent portability — BMAD on any agent, never vendor-locked",
      "status": "archived",
      "owner": "marshal",
      "type": "practice",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-agent-portability"
      },
      "archived_reason": "absorbed"
    },
    {
      "slug": "agent-tool-surface",
      "title": "Agent tool surface — every craft reachable through one governed API",
      "status": "realized",
      "owner": "marshal",
      "type": "practice",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-agent-tool-surface"
      }
    },
    {
      "slug": "agentic-sdlc-autonomy",
      "title": "The Agentic SDLC — four views of autonomy, one governed factory",
      "status": "specified",
      "owner": "marshal",
      "type": "practice",
      "chain": {
        "deck": "presentations/agentic-sdlc",
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-agentic-sdlc-autonomy"
      }
    },
    {
      "slug": "artifact-chain-reconciliation",
      "title": "A backlog authored before the code existed is a plan for a different codebase",
      "status": "realized",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-artifact-chain-reconciliation"
      }
    },
    {
      "slug": "artifact-console",
      "title": "Artifact console — the factory board, hosted as a chat artifact",
      "status": "archived",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-artifact-console"
      },
      "archived_reason": "retired"
    },
    {
      "slug": "artifactory-download-intelligence",
      "title": "An enterprise Artifactory mirror's own download telemetry joins the universe picture",
      "status": "specified",
      "owner": "atlas",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-artifactory-download-intelligence"
      }
    },
    {
      "slug": "asgi-multiplexer-monolith",
      "title": "Django, Langflow, and DB-GPT co-locate in one ASGI process without starving each other",
      "status": "absorbed   # 2026-08-22 pointer spec authored (spec-asgi-multiplexer-monolith); realized through python-agent-platform per the 2026-08-14 Realization log",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-asgi-multiplexer-monolith"
      }
    },
    {
      "slug": "atlas-query-dashboards",
      "title": "A query against the atlas DB becomes an interactive dashboard, no SPA framework",
      "status": "specified",
      "owner": "atlas",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-query-dashboards"
      }
    },
    {
      "slug": "bmad-611-era-alignment",
      "title": "PyForge's artifacts, patterns, and station code stay aligned to the installed BMAD era — 6.11 today, v7-ready tomorrow",
      "status": "specified   # 2026-08-22 — spec-bmad-611-era-alignment under pyforge-marshal (7 CAPs, 2 companions), decomposed as marshal Epic 25 (7 stories, all independent)",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-611-era-alignment"
      }
    },
    {
      "slug": "bmad-drift-new-artifact-shape",
      "title": "A spike report is not a corrupt file, and the classifier can't yet tell the difference",
      "status": "realized",
      "owner": "doctor",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-drift-new-artifact-shape"
      }
    },
    {
      "slug": "bmad-loop-baseline-drift",
      "title": "A story's orchestrator-recorded baseline can never drift out from under its own worktree",
      "status": "specified",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-loop-baseline-drift"
      }
    },
    {
      "slug": "bmad-loop-forward-dependency-blindness",
      "title": "bmad-loop can't see a story's own documented dependency",
      "status": "archived",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-loop-forward-dependency-blindness"
      }
    },
    {
      "slug": "bmad-loop-intent-gap-work-preservation",
      "title": "An intent-gap revert can never discard real work without a recoverable trace",
      "status": "specified",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-loop-intent-gap-work-preservation"
      }
    },
    {
      "slug": "bmad-loop-liveness-footgun",
      "title": "Nobody has to hand-parse engine.pid to answer \"is this run alive?\"",
      "status": "specified",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-loop-liveness-footgun"
      }
    },
    {
      "slug": "bmad-method-core-upgrade",
      "title": "BMAD-METHOD's own core stays current, not stuck at whatever version got installed",
      "status": "specified   # 2026-08-21 — spec-bmad-method-core-upgrade under pyforge-steward, grounded in the live 6.10.0→6.11.0 upgrade session",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade"
      }
    },
    {
      "slug": "bmad-method-version-drift",
      "title": "Doctor notices when BMAD-METHOD's own installed core falls behind upstream",
      "status": "realized   # core CAPs 1-3 shipped as Epic 10 (10.1/10.2, 2026-08-16); suite extension",
      "owner": "doctor",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-method-version-drift"
      }
    },
    {
      "slug": "bmad-module-provisioning",
      "title": "BMAD Method modules are provisioned, not hand-installed",
      "status": "realized",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-module-provisioning"
      }
    },
    {
      "slug": "bmad-output-hygiene",
      "title": "One fabricated commit, eight stations of debris",
      "status": "archived",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-output-hygiene"
      }
    },
    {
      "slug": "bmad-suite-channel-product",
      "title": "The SelfExplainML bmad-suite is a governed product — always latest, dual-path installable, modules provisioned",
      "status": "specified   # 2026-08-22 — spec-bmad-suite-channel-product (5 CAPs + install-matrix.md); decomposed as steward Epic 15 (4 stories) + doctor Epic 15 (2 stories, CAP-5 relay); channel bmad-method refreshed to 6.11.0 same day",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-channel-product"
      }
    },
    {
      "slug": "bmad-switch-scope-enforcement",
      "title": "A BMAD write can never land in the wrong project's artifacts, mechanically",
      "status": "specified",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-switch-scope-enforcement"
      }
    },
    {
      "slug": "compliance-factory-web-face",
      "title": "A web face for the compliance factory — upload a manifest, watch warden and atlas analyze it",
      "status": "specified   # 2026-08-22 — spec + station decomposition landed same day",
      "owner": "warden",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-compliance-factory-web-face"
      }
    },
    {
      "slug": "conda-forge-expert-rebuild",
      "title": "Rebuild conda-forge-expert as a Skill-Forge-authored skill, slice by slice",
      "status": "specified",
      "owner": "mason",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild"
      }
    },
    {
      "slug": "conda-forge-packaging-inventory-operations",
      "title": "Build a conda-forge packaging inventory from scratch as a continuous intake engine",
      "status": "specified   # 2026-08-22 — spec + station decomposition landed same day",
      "owner": "atlas",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-conda-forge-packaging-inventory-operations"
      }
    },
    {
      "slug": "copilot-cli-packaging",
      "title": "copilot-cli on conda-forge — blocked at the license",
      "status": "archived",
      "owner": "mason",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-copilot-cli-packaging"
      },
      "archived_reason": "blocked"
    },
    {
      "slug": "dashboard-project-path-derivation",
      "title": "The dashboard assumes slug == project directory — it isn't, and won't stay",
      "status": "archived",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-dashboard-project-path-derivation"
      }
    },
    {
      "slug": "dashboard-velocity-captures-hand-driven-work",
      "title": "Dashboard velocity counts every story's real effort, not just bmad-loop-journaled ones",
      "status": "specified",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-dashboard-velocity-captures-hand-driven-work"
      }
    },
    {
      "slug": "db-gpt-django-plugin",
      "title": "DB-GPT's agentic, file-hungry model integrates into a stateless Django control plane",
      "status": "absorbed   # 2026-08-22 pointer spec authored (spec-db-gpt-django-plugin); realized through python-agent-platform per the 2026-08-14 Realization log",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-db-gpt-django-plugin"
      }
    },
    {
      "slug": "db-gpt-packaging",
      "title": "DB-GPT on conda-forge — the multi-output agent stack",
      "status": "archived",
      "owner": "mason",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-db-gpt-packaging"
      },
      "archived_reason": "terminal"
    },
    {
      "slug": "deck-visual-qa",
      "title": "A deck is proven to look right, not merely to render without crashing",
      "status": "specified",
      "owner": "herald",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-visual-qa"
      }
    },
    {
      "slug": "deferred-work-audit-completeness",
      "title": "deferred-work-audit-completeness",
      "status": "specified",
      "owner": "doctor",
      "type": "dream",
      "chain": {}
    },
    {
      "slug": "deferred-work-resolution-sweep",
      "title": "deferred-work-resolution-sweep",
      "status": "dreamt",
      "owner": "doctor",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-deferred-work-resolution-sweep"
      }
    },
    {
      "slug": "deferred-work-visibility",
      "title": "A deferral that nobody can see is a deferral that never happened",
      "status": "specified",
      "owner": "doctor",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-deferred-work-visibility"
      }
    },
    {
      "slug": "developer-machine-bootstrap",
      "title": "A new contributor or agent is productive on this repo without tribal knowledge",
      "status": "specified   # 2026-08-22 — spec-developer-machine-bootstrap, decomposed into the station backlog same day",
      "owner": "steward",
      "type": "practice",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-developer-machine-bootstrap"
      }
    },
    {
      "slug": "django-accelerator-framework",
      "title": "A Django-service scaffolding engine, if this repo ever births new Django-based stations",
      "status": "specified",
      "owner": "mason",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-django-accelerator-framework"
      }
    },
    {
      "slug": "dream-to-code-model-self-verification",
      "title": "The Dream-to-Code model has never verified itself",
      "status": "archived",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-dream-to-code-model-self-verification"
      }
    },
    {
      "slug": "durable-runs",
      "title": "Durable runs — work survives the machine that made it",
      "status": "realized",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-durable-runs"
      },
      "archived_reason": "absorbed"
    },
    {
      "slug": "enterprise-airgap",
      "title": "Firewalled Factory",
      "status": "realized",
      "owner": "steward",
      "type": "practice",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-enterprise-airgap"
      }
    },
    {
      "slug": "enterprise-data-models-and-apis",
      "title": "A normalized data model and REST API pattern, waiting for a PyForge-native subject",
      "status": "specified   # 2026-08-22 — reframed as an EXTENSION-POINT (operator): the fleet ships the socket/contract; the capability develops separately (incl. air-gapped) — see the spec's Extension contract section",
      "owner": "atlas",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-enterprise-data-models-and-apis"
      }
    },
    {
      "slug": "enterprise-multi-agent-orchestration",
      "title": "Django, Langflow, and DB-GPT scale as isolated containers behind one gateway",
      "status": "absorbed   # 2026-08-22 pointer spec authored (spec-enterprise-multi-agent-orchestration); realized through python-agent-platform per the 2026-08-14 Realization log",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-enterprise-multi-agent-orchestration"
      }
    },
    {
      "slug": "factory-console",
      "title": "Factory console — the whole pipeline on one page",
      "status": "realized",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-factory-console"
      },
      "archived_reason": "absorbed"
    },
    {
      "slug": "fidelity-enforcement",
      "title": "Fidelity enforcement — a contract is only a contract if something fails against it",
      "status": "archived",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-fidelity-enforcement"
      },
      "archived_reason": "absorbed"
    },
    {
      "slug": "fleet-chain-completeness",
      "title": "Fleet Chain Completeness — Orchestrated Dream-to-Code Regeneration",
      "status": "archived",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-fleet-chain-completeness"
      },
      "archived_reason": "absorbed"
    },
    {
      "slug": "fleet-hygiene-verification-exemplar-program",
      "title": "fleet-hygiene-verification-exemplar-program",
      "status": "dreamt",
      "owner": "doctor",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-fleet-hygiene-verification-exemplar-program"
      }
    },
    {
      "slug": "fleet-status-supervisor-fallback",
      "title": "A dead supervisor and a dead engine report identically — and only one of them needs help",
      "status": "realized",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-fleet-status-supervisor-fallback"
      }
    },
    {
      "slug": "fleet-stewardship",
      "title": "Fleet stewardship — tend every feedstock we can touch",
      "status": "realized",
      "owner": "mason",
      "type": "practice",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-fleet-stewardship"
      }
    },
    {
      "slug": "genesis-installer-name-retirement",
      "title": "Retire genesis-installer — one marshal CLI, one PRD/architecture/epics chain",
      "status": "archived",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-genesis-installer-name-retirement"
      }
    },
    {
      "slug": "genesis-installer",
      "title": "Genesis installer — the seed, made executable",
      "status": "archived",
      "owner": "marshal",
      "type": "dream",
      "chain": {},
      "archived_reason": "absorbed"
    },
    {
      "slug": "herald-moments-2-4-live-backend",
      "title": "Herald Moments 2-4 run on a real live backend, not local-storage/CLI-triggered",
      "status": "specified",
      "owner": "herald",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-herald-moments-2-4-live-backend"
      }
    },
    {
      "slug": "herald-moments-2-4-missing-surface",
      "title": "Herald — Moments 2–4 Missing Surface",
      "status": "archived",
      "owner": "herald",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-herald-moments-2-4-missing-surface"
      },
      "archived_reason": "absorbed"
    },
    {
      "slug": "herald-pitch",
      "title": "Herald's Pitch Deck — Moment 1 Orchestration (Consolidated)",
      "status": "archived",
      "owner": "herald",
      "type": "dream",
      "chain": {},
      "archived_reason": "absorbed"
    },
    {
      "slug": "horizontal-run-concurrency",
      "title": "One story in flight at a time, silently, by an upstream stub",
      "status": "realized",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-horizontal-run-concurrency"
      }
    },
    {
      "slug": "jira-github-projects-sync",
      "title": "A ticket moves once, both boards know",
      "status": "specified",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-jira-github-projects-sync"
      }
    },
    {
      "slug": "kedro-org-tooling-adoption",
      "title": "Atlas's own Kedro tooling gap — skills, viz publishing, IDE integration",
      "status": "realized",
      "owner": "atlas",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-kedro-org-tooling-adoption"
      }
    },
    {
      "slug": "landing-evidence-grammar",
      "title": "A legitimate landing is recognizable no matter which of the three-plus paths landed it",
      "status": "specified",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-landing-evidence-grammar"
      }
    },
    {
      "slug": "langflow-django-plugin",
      "title": "Langflow integrates into a cookiecutter-django project without fighting it",
      "status": "absorbed   # 2026-08-22 pointer spec authored (spec-langflow-django-plugin); realized through python-agent-platform per the 2026-08-14 Realization log",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-langflow-django-plugin"
      }
    },
    {
      "slug": "local-ocp-hybrid-environment",
      "title": "A local OpenShift hybrid environment runs the agentic SDLC end to end — visual lifecycle, wired BMAD suite, multiplexed apps, synced tracker",
      "status": "specified   # 2026-08-22 — spec-local-ocp-hybrid-environment (5 CAPs, 2 companions), decomposed as steward Epic 12 extension S-12.4..12.8 (operator-locked)",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-local-ocp-hybrid-environment"
      }
    },
    {
      "slug": "loop-home-fleet-refresh",
      "title": "Refreshing every loop-home from main is a hand-run ritual",
      "status": "archived",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-loop-home-fleet-refresh"
      }
    },
    {
      "slug": "machine-checked-recipe-knowledge",
      "title": "The CFE failure catalog is generated from the skill spec, every row lint-verified against its enforcing check",
      "status": "specified   # 2026-08-22 — spec + station decomposition landed same day",
      "owner": "mason",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-machine-checked-recipe-knowledge"
      }
    },
    {
      "slug": "marshal-land-cross-project-story-key-collision",
      "title": "A GitHub PR-merge branch from one project never masquerades as a same-numbered story in another",
      "status": "specified",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-land-cross-project-story-key-collision"
      }
    },
    {
      "slug": "marshal-land-merge-subject",
      "title": "Marshal-driven landings are provably Marshal-driven",
      "status": "realized",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-land-merge-subject"
      }
    },
    {
      "slug": "marshal-single-story-dispatch",
      "title": "Single-story dispatch is a marshal verb, not a session's discipline",
      "status": "specified",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch"
      }
    },
    {
      "slug": "marshal-status-harness-run-id-poisoning",
      "title": "A spin-time poll timeout never permanently blinds marshal status to a healthy run",
      "status": "specified",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-status-harness-run-id-poisoning"
      }
    },
    {
      "slug": "microsoft-org-sweep",
      "title": "Microsoft org sweep — audit one upstream org, package what is missing",
      "status": "archived",
      "owner": "atlas",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-microsoft-org-sweep"
      },
      "archived_reason": "absorbed"
    },
    {
      "slug": "miniforge-installer",
      "title": "A custom-branded Python distributable, if this repo ever needs one",
      "status": "specified   # 2026-08-22 — reframed as an EXTENSION-POINT (operator): the fleet ships the socket/contract; the capability develops separately (incl. air-gapped) — see the spec's Extension contract section",
      "owner": "mason",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-miniforge-installer"
      }
    },
    {
      "slug": "multi-repo-workspaces",
      "title": "One workspace opens every repo a story touches",
      "status": "specified   # 2026-08-22 — spec-multi-repo-workspaces, decomposed into the station backlog same day",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-multi-repo-workspaces"
      }
    },
    {
      "slug": "one-front-door",
      "title": "One front door — Marshal drives everything BMAD installs",
      "status": "archived",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-one-front-door"
      },
      "archived_reason": "absorbed"
    },
    {
      "slug": "package-inventory-eligibility",
      "title": "Every package has one provenance trail and one eligibility answer, from any source",
      "status": "specified   # 2026-08-22 — spec + station decomposition landed same day",
      "owner": "warden",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-package-inventory-eligibility"
      }
    },
    {
      "slug": "packaging-factory",
      "title": "The Packaging Factory",
      "status": "realized",
      "owner": "mason",
      "type": "practice",
      "chain": {
        "deck": "presentations/pyforge-mason",
        "spec": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-packaging-factory"
      }
    },
    {
      "slug": "pixi-container-image",
      "title": "A shared base container image with pixi already installed, if this repo ever ships one",
      "status": "specified   # 2026-08-22 — spec + station decomposition landed same day",
      "owner": "mason",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pixi-container-image"
      }
    },
    {
      "slug": "platform-fifteen-factors",
      "title": "The platform host earns its 15 factors — OIDC-delegated auth, telemetry, startup refusals, policy-as-tests, pixi-sourced deps",
      "status": "specified   # 2026-08-22 — spec-platform-fifteen-factors, decomposed into the station backlog same day",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-platform-fifteen-factors"
      }
    },
    {
      "slug": "pptx-custom-shapes",
      "title": "Programmatic OOXML shapes for information-dense slides, if the .pptx pipeline ever exists",
      "status": "specified   # 2026-08-22 — UNPARKED same day (Marp inadequacy proven + operator named the 21-station stakeholder audience); decomposed as herald Epic 15",
      "owner": "herald",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pptx-custom-shapes"
      }
    },
    {
      "slug": "pptx-deck-generation",
      "title": "A second, PowerPoint-native deck pipeline, if this repo ever needs editable .pptx output",
      "status": "specified   # 2026-08-22 — UNPARKED same day (Marp inadequacy proven + operator named the 21-station stakeholder audience); decomposed as herald Epic 15",
      "owner": "herald",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pptx-deck-generation"
      }
    },
    {
      "slug": "pr-lifecycle",
      "title": "PR lifecycle — a story lands itself",
      "status": "realized",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pr-lifecycle"
      },
      "archived_reason": "absorbed"
    },
    {
      "slug": "presenton-pixi-image",
      "title": "Presenton, conda-native — AI decks inside the regulated enterprise",
      "status": "archived",
      "owner": "mason",
      "type": "dream",
      "chain": {
        "deck": "presentations/presenton-pixi-image"
      },
      "blockedOn": "Phase-0 decision gate (Epic 1)",
      "archived_reason": "blocked"
    },
    {
      "slug": "pyforge-atlas-intelligence-platform",
      "title": "\"Dream — PyForge Atlas Intelligence Platform\"",
      "status": "archived",
      "owner": "atlas",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas-intelligence-platform"
      },
      "archived_reason": "duplicate"
    },
    {
      "slug": "pyforge-atlas",
      "title": "Atlas — the map that maintains itself",
      "status": "realized",
      "owner": "atlas",
      "type": "dream",
      "chain": {
        "deck": "presentations/pyforge-atlas",
        "spec": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas",
        "project": "_bmad-output/projects/pyforge-atlas",
        "program": "atlas"
      }
    },
    {
      "slug": "pyforge-charter",
      "title": "The PyForge Charter",
      "status": "pitched",
      "owner": "guild",
      "type": "dream",
      "chain": {
        "deck": "presentations/pyforge-genesis"
      }
    },
    {
      "slug": "pyforge-core",
      "title": "One primitive, one home — the shared floor under eight stations",
      "status": "archived",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core"
      }
    },
    {
      "slug": "pyforge-doctor-dependency-health",
      "title": "\"Dream — PyForge Doctor: Dependency Health Diagnostics\"",
      "status": "archived",
      "owner": "doctor",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor-dependency-health"
      },
      "archived_reason": "absorbed"
    },
    {
      "slug": "pyforge-doctor",
      "title": "Doctor — one bedside manner for the whole fleet",
      "status": "realized",
      "owner": "doctor",
      "type": "dream",
      "chain": {
        "deck": "presentations/pyforge-doctor",
        "spec": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor",
        "project": "_bmad-output/projects/pyforge-doctor"
      }
    },
    {
      "slug": "pyforge-herald",
      "title": "Herald — capture the dream, illustrate the telemetry, proclaim the release",
      "status": "realized",
      "owner": "herald",
      "type": "dream",
      "chain": {
        "deck": "presentations/pyforge-herald",
        "spec": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald",
        "project": "_bmad-output/projects/pyforge-herald"
      }
    },
    {
      "slug": "pyforge-marshal-loop-orchestrator",
      "title": "\"Dream — PyForge Marshal: Loop Orchestrator\"",
      "status": "archived",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal-loop-orchestrator"
      },
      "archived_reason": "duplicate"
    },
    {
      "slug": "pyforge-marshal",
      "title": "Marshal — autonomy a human can trust",
      "status": "realized",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "deck": "presentations/pyforge-marshal",
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal",
        "project": "_bmad-output/projects/pyforge-marshal"
      }
    },
    {
      "slug": "pyforge-mason-recipe-validator",
      "title": "\"Dream — PyForge Mason: Recipe Validator\"",
      "status": "archived",
      "owner": "mason",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason-recipe-validator"
      },
      "archived_reason": "conflicts-with-decided-architecture"
    },
    {
      "slug": "pyforge-mason",
      "title": "Mason — forge the blocks, bind the environment, ship the structure",
      "status": "specified",
      "owner": "mason",
      "type": "dream",
      "chain": {
        "deck": "presentations/pyforge-mason",
        "spec": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason",
        "project": "_bmad-output/projects/pyforge-mason"
      }
    },
    {
      "slug": "pyforge-scribe-team-memory",
      "title": "\"Dream — PyForge Scribe: Team Memory Management\"",
      "status": "archived",
      "owner": "scribe",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe-team-memory"
      },
      "archived_reason": "duplicate"
    },
    {
      "slug": "pyforge-scribe",
      "title": "Scribe — the inward voice",
      "status": "realized",
      "owner": "scribe",
      "type": "dream",
      "chain": {
        "deck": "presentations/pyforge-scribe",
        "spec": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe",
        "project": "_bmad-output/projects/pyforge-scribe"
      }
    },
    {
      "slug": "pyforge-steward-feedstock-maintenance",
      "title": "\"Dream — PyForge Steward: Feedstock Maintenance Automation\"",
      "status": "archived",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward-feedstock-maintenance"
      },
      "archived_reason": "absorbed"
    },
    {
      "slug": "pyforge-steward",
      "title": "Steward — provision the line, hold the keys",
      "status": "realized",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "deck": "presentations/pyforge-steward",
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward",
        "project": "_bmad-output/projects/pyforge-steward"
      }
    },
    {
      "slug": "pyforge-testing-charter",
      "title": "\"Dream — PyForge Testing Charter: Systematic Testing for the Guild\"",
      "status": "archived",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter"
      },
      "archived_reason": "absorbed"
    },
    {
      "slug": "pyforge-warden-compliance-gates",
      "title": "\"Dream — PyForge Warden: Compliance Gates\"",
      "status": "archived",
      "owner": "warden",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden-compliance-gates"
      },
      "archived_reason": "duplicate"
    },
    {
      "slug": "pyforge-warden",
      "title": "Warden — the gate that never lies",
      "status": "realized",
      "owner": "warden",
      "type": "dream",
      "chain": {
        "deck": "presentations/pyforge-warden",
        "spec": "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden",
        "project": "_bmad-output/projects/pyforge-warden",
        "program": "warden"
      }
    },
    {
      "slug": "python-agent-platform",
      "title": "One Django service hosts the agentic engines as pluggable applications, anywhere — including air-gapped",
      "status": "specified",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform"
      }
    },
    {
      "slug": "quick-dev-reconciliation",
      "title": "Two ways to finish a story, and Marshal has only ever heard of one",
      "status": "realized",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-quick-dev-reconciliation"
      }
    },
    {
      "slug": "regenerable-factory",
      "title": "Regenerable factory — every line of code under a spec it can be rebuilt from",
      "status": "realized",
      "owner": "marshal",
      "type": "practice",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-regenerable-factory"
      }
    },
    {
      "slug": "reusable-cicd-workflows",
      "title": "A centrally-maintained CI/CD workflow family, if this repo ever needs more than plain Actions",
      "status": "specified   # 2026-08-22 — reframed as an EXTENSION-POINT (operator): the fleet ships the socket/contract; the capability develops separately (incl. air-gapped) — see the spec's Extension contract section",
      "owner": "mason",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-reusable-cicd-workflows"
      }
    },
    {
      "slug": "risk-tiered-review-depth",
      "title": "A one-line doc fix and a cross-module rewrite get the identical review",
      "status": "realized",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-risk-tiered-review-depth"
      }
    },
    {
      "slug": "scratch-worktree-lifecycle",
      "title": "A scratch worktree for one story's work is one command, not five",
      "status": "specified",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-scratch-worktree-lifecycle"
      }
    },
    {
      "slug": "scribe-mines-raw-session-transcripts",
      "title": "Scribe reaches past curated memory into the raw session transcripts underneath it",
      "status": "specified   # 2026-08-22 — spec + station decomposition landed same day",
      "owner": "scribe",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-mines-raw-session-transcripts"
      }
    },
    {
      "slug": "secure-live-dashboards",
      "title": "A dashboard can be handed to the company without being rebuilt",
      "status": "specified",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-secure-live-dashboards"
      }
    },
    {
      "slug": "sentinel",
      "title": "Sentinel — the AI Software Factory (the ancestor)",
      "status": "archived",
      "owner": "scribe",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-sentinel"
      },
      "archived_reason": "absorbed"
    },
    {
      "slug": "sibling-dreams-drift",
      "title": "Sibling dreams directories don't drift silently",
      "status": "specified   # 2026-08-22 — spec-sibling-dreams-drift, decomposed into the station backlog same day",
      "owner": "doctor",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-sibling-dreams-drift"
      }
    },
    {
      "slug": "sprint-status-auto-promote",
      "title": "The dashboard goes stale because promotion is a remembered step",
      "status": "archived",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-sprint-status-auto-promote"
      }
    },
    {
      "slug": "surface-drift-reconciliation",
      "title": "A drift gate nobody can clear, and a drift signal anyone can launder",
      "status": "realized",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-surface-drift-reconciliation"
      }
    },
    {
      "slug": "team-memory",
      "title": "Team memory — what the team knows, the agents know",
      "status": "archived",
      "owner": "scribe",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-team-memory"
      },
      "archived_reason": "absorbed"
    },
    {
      "slug": "unified-container",
      "title": "One container, eight stations",
      "status": "realized",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-unified-container"
      }
    },
    {
      "slug": "unity-data-stack",
      "title": "Unity Data Stack — the enterprise innersource platform",
      "status": "archived",
      "owner": "atlas",
      "type": "dream",
      "chain": {
        "deck": "presentations/unity-data-stack"
      },
      "archived_reason": "absorbed"
    },
    {
      "slug": "upstream-discovery",
      "title": "Upstream discovery — package it before it's asked for",
      "status": "archived",
      "owner": "atlas",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-upstream-discovery"
      },
      "archived_reason": "absorbed"
    },
    {
      "slug": "wagtail-corporate-brain",
      "title": "The \"Corporate Brain\" CMS atlas's own WikiSyncer has been waiting to push to",
      "status": "specified",
      "owner": "atlas",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wagtail-corporate-brain"
      }
    },
    {
      "slug": "wasm-analytics-stack",
      "title": "WASM Data Stack",
      "status": "archived",
      "owner": "atlas",
      "type": "dream",
      "chain": {
        "deck": "presentations/wasm-analytics-stack"
      },
      "archived_reason": "absorbed"
    }
  ],
  "specs": [
    {
      "slug": "artifactory-download-intelligence",
      "project": "pyforge-atlas",
      "title": "Atlas gains an org's own Artifactory download telemetry — an AQL join + internal/private flag, mock-first",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "artifactory-download-intelligence",
      "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-artifactory-download-intelligence"
    },
    {
      "slug": "atlas-query-dashboards",
      "project": "pyforge-atlas",
      "title": "A `cf_atlas.db` query renders as a hand-someone-a-link dashboard — Panel/Bokeh, no SPA",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "atlas-query-dashboards",
      "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-query-dashboards"
    },
    {
      "slug": "conda-forge-packaging-inventory-operations",
      "project": "pyforge-atlas",
      "title": "The packaging-inventory intake engine, governed",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "conda-forge-packaging-inventory-operations",
      "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-conda-forge-packaging-inventory-operations"
    },
    {
      "slug": "enterprise-data-models-and-apis",
      "project": "pyforge-atlas",
      "title": "A normalized data model and REST API pattern (PARKED)",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "enterprise-data-models-and-apis",
      "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-enterprise-data-models-and-apis"
    },
    {
      "slug": "kedro-org-tooling-adoption",
      "project": "pyforge-atlas",
      "title": "kedro-org-tooling-adoption — Spec",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "kedro-org-tooling-adoption",
      "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-kedro-org-tooling-adoption"
    },
    {
      "slug": "microsoft-org-sweep",
      "project": "pyforge-atlas",
      "title": "microsoft-org-sweep — retirement record",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "microsoft-org-sweep",
      "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-microsoft-org-sweep"
    },
    {
      "slug": "pyforge-atlas",
      "project": "pyforge-atlas",
      "title": "consolidated: 2026-08-02 — this Spec also carries spec-unity-data-stack and",
      "caps": 31,
      "companions": 5,
      "updated": "2026-08-22",
      "dream": "pyforge-atlas",
      "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas"
    },
    {
      "slug": "pyforge-atlas-intelligence-platform",
      "project": "pyforge-atlas",
      "title": "pyforge-atlas-intelligence-platform — retirement record",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "pyforge-atlas-intelligence-platform",
      "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas-intelligence-platform"
    },
    {
      "slug": "upstream-discovery",
      "project": "pyforge-atlas",
      "title": "upstream discovery — sense what the world is building",
      "caps": 5,
      "companions": 2,
      "updated": "2026-08-22",
      "dream": "upstream-discovery",
      "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-upstream-discovery"
    },
    {
      "slug": "wagtail-corporate-brain",
      "project": "pyforge-atlas",
      "title": "All 3 open_questions resolved. Two by S-16.1 2026-08-15 (deployment substrate; DW-H1 dependency",
      "caps": 3,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "wagtail-corporate-brain",
      "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wagtail-corporate-brain"
    },
    {
      "slug": "backlog-intake-check",
      "project": "pyforge-doctor",
      "title": "Backlog-intake check",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "",
      "path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-backlog-intake-check"
    },
    {
      "slug": "bmad-drift-new-artifact-shape",
      "project": "pyforge-doctor",
      "title": "`bmad_drift`'s classifier has no rule yet for a spike-report artifact",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "bmad-drift-new-artifact-shape",
      "path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-drift-new-artifact-shape"
    },
    {
      "slug": "bmad-method-version-drift",
      "project": "pyforge-doctor",
      "title": "Doctor notices when BMAD-METHOD's own installed core falls behind upstream",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "bmad-method-version-drift",
      "path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-method-version-drift"
    },
    {
      "slug": "deferred-work-resolution-sweep",
      "project": "pyforge-doctor",
      "title": "Deferred-work resolution sweep",
      "caps": 8,
      "companions": 2,
      "updated": "2026-08-22",
      "dream": "deferred-work-resolution-sweep",
      "path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-deferred-work-resolution-sweep"
    },
    {
      "slug": "deferred-work-visibility",
      "project": "pyforge-doctor",
      "title": "deferred-work-visibility",
      "caps": 10,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "deferred-work-visibility",
      "path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-deferred-work-visibility"
    },
    {
      "slug": "fleet-hygiene-verification-exemplar-program",
      "project": "pyforge-doctor",
      "title": "Fleet hygiene, verification & exemplar-standard catalog",
      "caps": 7,
      "companions": 1,
      "updated": "2026-08-22",
      "dream": "fleet-hygiene-verification-exemplar-program",
      "path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-fleet-hygiene-verification-exemplar-program"
    },
    {
      "slug": "pyforge-doctor",
      "project": "pyforge-doctor",
      "title": "Doctor (pyforge-doctor) — one bedside manner for the whole fleet",
      "caps": 9,
      "companions": 1,
      "updated": "2026-08-22",
      "dream": "pyforge-doctor",
      "path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor"
    },
    {
      "slug": "pyforge-doctor-dependency-health",
      "project": "pyforge-doctor",
      "title": "pyforge-doctor-dependency-health — retirement record",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "pyforge-doctor-dependency-health",
      "path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor-dependency-health"
    },
    {
      "slug": "sibling-dreams-drift",
      "project": "pyforge-doctor",
      "title": "Sibling dreams directories don't drift silently",
      "caps": 1,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "sibling-dreams-drift",
      "path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-sibling-dreams-drift"
    },
    {
      "slug": "deck-visual-qa",
      "project": "pyforge-herald",
      "title": "Herald's deck pipeline has no gate that proves a deck LOOKS right",
      "caps": 3,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "deck-visual-qa",
      "path": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-visual-qa"
    },
    {
      "slug": "herald-moments-2-4-live-backend",
      "project": "pyforge-herald",
      "title": "herald-moments-2-4-live-backend",
      "caps": 5,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "herald-moments-2-4-live-backend",
      "path": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-herald-moments-2-4-live-backend"
    },
    {
      "slug": "herald-moments-2-4-missing-surface",
      "project": "pyforge-herald",
      "title": "herald-moments-2-4-missing-surface — retirement record",
      "caps": 3,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "herald-moments-2-4-missing-surface",
      "path": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-herald-moments-2-4-missing-surface"
    },
    {
      "slug": "pptx-custom-shapes",
      "project": "pyforge-herald",
      "title": "Programmatic shapes + real-font autofit for the .pptx pipeline",
      "caps": 1,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "pptx-custom-shapes",
      "path": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pptx-custom-shapes"
    },
    {
      "slug": "pptx-deck-generation",
      "project": "pyforge-herald",
      "title": "A PowerPoint-native deck pipeline (editable .pptx)",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "pptx-deck-generation",
      "path": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pptx-deck-generation"
    },
    {
      "slug": "pyforge-herald",
      "project": "pyforge-herald",
      "title": "pyforge-herald",
      "caps": 3,
      "companions": 6,
      "updated": "2026-08-22",
      "dream": "pyforge-herald",
      "path": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald"
    },
    {
      "slug": "adaptive-model-tiering",
      "project": "pyforge-marshal",
      "title": "FR-51's model tiering is fully wired and never turned on",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "adaptive-model-tiering",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-adaptive-model-tiering"
    },
    {
      "slug": "agent-portability",
      "project": "pyforge-marshal",
      "title": "agent-portability — retirement record",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "agent-portability",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-agent-portability"
    },
    {
      "slug": "agent-tool-surface",
      "project": "pyforge-marshal",
      "title": "The agent tool surface — the factory, callable",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "agent-tool-surface",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-agent-tool-surface"
    },
    {
      "slug": "agentic-sdlc-autonomy",
      "project": "pyforge-marshal",
      "title": "agentic-sdlc-autonomy",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "agentic-sdlc-autonomy",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-agentic-sdlc-autonomy"
    },
    {
      "slug": "artifact-chain-reconciliation",
      "project": "pyforge-marshal",
      "title": "Artifact-Chain Reconciliation — the pause-and-audit",
      "caps": 8,
      "companions": 3,
      "updated": "2026-08-22",
      "dream": "artifact-chain-reconciliation",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-artifact-chain-reconciliation"
    },
    {
      "slug": "artifact-console",
      "project": "pyforge-marshal",
      "title": "artifact-console — retirement record",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "artifact-console",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-artifact-console"
    },
    {
      "slug": "bmad-611-era-alignment",
      "project": "pyforge-marshal",
      "title": "PyForge stays aligned to the installed BMAD era",
      "caps": 7,
      "companions": 2,
      "updated": "2026-08-22",
      "dream": "bmad-611-era-alignment",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-611-era-alignment"
    },
    {
      "slug": "bmad-loop-baseline-drift",
      "project": "pyforge-marshal",
      "title": "A story's orchestrator-recorded baseline can never *silently* drift out from under its own worktree",
      "caps": 3,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "bmad-loop-baseline-drift",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-loop-baseline-drift"
    },
    {
      "slug": "bmad-loop-forward-dependency-blindness",
      "project": "pyforge-marshal",
      "title": "bmad-loop's forward-dependency blindness, closed",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "bmad-loop-forward-dependency-blindness",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-loop-forward-dependency-blindness"
    },
    {
      "slug": "bmad-loop-governance",
      "project": "pyforge-marshal",
      "title": "Marshal (graduated-autonomy loop orchestration, as shipped)",
      "caps": 4,
      "companions": 3,
      "updated": "2026-08-22",
      "dream": "",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-loop-governance"
    },
    {
      "slug": "bmad-loop-intent-gap-work-preservation",
      "project": "pyforge-marshal",
      "title": "`bmad-loop`'s intent-gap revert leaves no recoverable git artifact",
      "caps": 3,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "bmad-loop-intent-gap-work-preservation",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-loop-intent-gap-work-preservation"
    },
    {
      "slug": "bmad-loop-liveness-footgun",
      "project": "pyforge-marshal",
      "title": "Nobody has to hand-parse engine.pid to answer \"is this run alive?\"",
      "caps": 3,
      "companions": 1,
      "updated": "2026-08-22",
      "dream": "bmad-loop-liveness-footgun",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-loop-liveness-footgun"
    },
    {
      "slug": "bmad-output-hygiene",
      "project": "pyforge-marshal",
      "title": "bmad-output-hygiene",
      "caps": 12,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "bmad-output-hygiene",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-output-hygiene"
    },
    {
      "slug": "bmad-switch-scope-enforcement",
      "project": "pyforge-marshal",
      "title": "The BMAD switch has two divergent guards, and neither checks the slug the caller asked for",
      "caps": 3,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "bmad-switch-scope-enforcement",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-switch-scope-enforcement"
    },
    {
      "slug": "dashboard-project-path-derivation",
      "project": "pyforge-marshal",
      "title": "The dashboard derives project paths — slug ≠ directory stops being a bug factory",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "dashboard-project-path-derivation",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-dashboard-project-path-derivation"
    },
    {
      "slug": "dashboard-velocity-captures-hand-driven-work",
      "project": "pyforge-marshal",
      "title": "Every done story leaves a timing mark — \"unmeasured\" stops meaning \"not loop-driven\"",
      "caps": 3,
      "companions": 1,
      "updated": "2026-08-22",
      "dream": "dashboard-velocity-captures-hand-driven-work",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-dashboard-velocity-captures-hand-driven-work"
    },
    {
      "slug": "dream-to-code-model-self-verification",
      "project": "pyforge-marshal",
      "title": "dream-to-code-model-self-verification — the detectors get detected",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "dream-to-code-model-self-verification",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-dream-to-code-model-self-verification"
    },
    {
      "slug": "durable-runs",
      "project": "pyforge-marshal",
      "title": "durable-runs — retirement record",
      "caps": 6,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "durable-runs",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-durable-runs"
    },
    {
      "slug": "factory-console",
      "project": "pyforge-marshal",
      "title": "factory console (program console + Dreamscape)",
      "caps": 4,
      "companions": 1,
      "updated": "2026-08-22",
      "dream": "factory-console",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-factory-console"
    },
    {
      "slug": "fidelity-enforcement",
      "project": "pyforge-marshal",
      "title": "fidelity-enforcement — retirement record",
      "caps": 9,
      "companions": 3,
      "updated": "2026-08-22",
      "dream": "fidelity-enforcement",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-fidelity-enforcement"
    },
    {
      "slug": "fleet-chain-completeness",
      "project": "pyforge-marshal",
      "title": "fleet chain completeness",
      "caps": 5,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "fleet-chain-completeness",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-fleet-chain-completeness"
    },
    {
      "slug": "fleet-status-supervisor-fallback",
      "project": "pyforge-marshal",
      "title": "Fleet status wants a fallback liveness check when the supervisor sidecar is gone",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "fleet-status-supervisor-fallback",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-fleet-status-supervisor-fallback"
    },
    {
      "slug": "genesis-installer-name-retirement",
      "project": "pyforge-marshal",
      "title": "genesis-installer-name-retirement",
      "caps": 8,
      "companions": 1,
      "updated": "2026-08-22",
      "dream": "genesis-installer-name-retirement",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-genesis-installer-name-retirement"
    },
    {
      "slug": "horizontal-run-concurrency",
      "project": "pyforge-marshal",
      "title": "One story in flight at a time, silently, by an upstream stub",
      "caps": 3,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "horizontal-run-concurrency",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-horizontal-run-concurrency"
    },
    {
      "slug": "landing-evidence-grammar",
      "project": "pyforge-marshal",
      "title": "A legitimate landing is recognizable no matter which of the three-plus paths landed it",
      "caps": 3,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "landing-evidence-grammar",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-landing-evidence-grammar"
    },
    {
      "slug": "loop-home-fleet-refresh",
      "project": "pyforge-marshal",
      "title": "loop-home fleet refresh",
      "caps": 3,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "loop-home-fleet-refresh",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-loop-home-fleet-refresh"
    },
    {
      "slug": "marshal-land-cross-project-story-key-collision",
      "project": "pyforge-marshal",
      "title": "A GitHub PR-merge branch from one project never masquerades as a same-numbered story in another",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "marshal-land-cross-project-story-key-collision",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-land-cross-project-story-key-collision"
    },
    {
      "slug": "marshal-land-merge-subject",
      "project": "pyforge-marshal",
      "title": "marshal land renders a detectable merge subject",
      "caps": 1,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "marshal-land-merge-subject",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-land-merge-subject"
    },
    {
      "slug": "marshal-single-story-dispatch",
      "project": "pyforge-marshal",
      "title": "Single-story dispatch is a marshal verb, not a session's discipline",
      "caps": 6,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "marshal-single-story-dispatch",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch"
    },
    {
      "slug": "marshal-status-harness-run-id-poisoning",
      "project": "pyforge-marshal",
      "title": "A spin-time poll timeout never permanently blinds marshal status to a healthy run",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "marshal-status-harness-run-id-poisoning",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-status-harness-run-id-poisoning"
    },
    {
      "slug": "multi-loop-isolation",
      "project": "pyforge-marshal",
      "title": "multi-loop isolation harness",
      "caps": 3,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-multi-loop-isolation"
    },
    {
      "slug": "one-front-door",
      "project": "pyforge-marshal",
      "title": "one-front-door — retirement record",
      "caps": 5,
      "companions": 1,
      "updated": "2026-08-22",
      "dream": "one-front-door",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-one-front-door"
    },
    {
      "slug": "pr-lifecycle",
      "project": "pyforge-marshal",
      "title": "pr-lifecycle — retirement record",
      "caps": 6,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "pr-lifecycle",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pr-lifecycle"
    },
    {
      "slug": "pyforge-core",
      "project": "pyforge-marshal",
      "title": "pyforge-core",
      "caps": 7,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "pyforge-core",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core"
    },
    {
      "slug": "pyforge-marshal",
      "project": "pyforge-marshal",
      "title": "marshal CLI — graduated autonomy, productized",
      "caps": 18,
      "companions": 7,
      "updated": "2026-08-22",
      "dream": "pyforge-marshal",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal"
    },
    {
      "slug": "pyforge-marshal-loop-orchestrator",
      "project": "pyforge-marshal",
      "title": "pyforge-marshal-loop-orchestrator — retirement record",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "pyforge-marshal-loop-orchestrator",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal-loop-orchestrator"
    },
    {
      "slug": "pyforge-testing-charter",
      "project": "pyforge-marshal",
      "title": "PyForge Testing Charter — fleet-wide test architecture",
      "caps": 5,
      "companions": 2,
      "updated": "2026-08-22",
      "dream": "pyforge-testing-charter",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter"
    },
    {
      "slug": "quick-dev-reconciliation",
      "project": "pyforge-marshal",
      "title": "Two ways to finish a story, and Marshal has only ever heard of one",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "quick-dev-reconciliation",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-quick-dev-reconciliation"
    },
    {
      "slug": "regenerable-factory",
      "project": "pyforge-marshal",
      "title": "regenerable-factory program",
      "caps": 4,
      "companions": 1,
      "updated": "2026-08-22",
      "dream": "regenerable-factory",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-regenerable-factory"
    },
    {
      "slug": "risk-tiered-review-depth",
      "project": "pyforge-marshal",
      "title": "A one-line doc fix and a cross-module rewrite get the identical review",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "risk-tiered-review-depth",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-risk-tiered-review-depth"
    },
    {
      "slug": "sprint-status-auto-promote",
      "project": "pyforge-marshal",
      "title": "sprint-status auto-promote",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "sprint-status-auto-promote",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-sprint-status-auto-promote"
    },
    {
      "slug": "surface-drift-reconciliation",
      "project": "pyforge-marshal",
      "title": "Surface drift reconciliation — a gate that can be cleared, a signal that can be trusted",
      "caps": 7,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "surface-drift-reconciliation",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-surface-drift-reconciliation"
    },
    {
      "slug": "conda-forge-expert-rebuild",
      "project": "pyforge-mason",
      "title": "conda-forge-expert rebuild — Skill-Forge-authored, slice by slice, parallel-run to an enforced end cutover",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "conda-forge-expert-rebuild",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild"
    },
    {
      "slug": "copilot-cli-packaging",
      "project": "pyforge-mason",
      "title": "copilot-cli-packaging — retirement record",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "copilot-cli-packaging",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-copilot-cli-packaging"
    },
    {
      "slug": "db-gpt-packaging",
      "project": "pyforge-mason",
      "title": "db-gpt-packaging — retirement record",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "db-gpt-packaging",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-db-gpt-packaging"
    },
    {
      "slug": "django-accelerator-framework",
      "project": "pyforge-mason",
      "title": "The Django accelerator is a contract today; the engine waits for a third surface",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "django-accelerator-framework",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-django-accelerator-framework"
    },
    {
      "slug": "fleet-stewardship",
      "project": "pyforge-mason",
      "title": "fleet stewardship (the recipes/ fleet)",
      "caps": 3,
      "companions": 3,
      "updated": "2026-08-22",
      "dream": "fleet-stewardship",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-fleet-stewardship"
    },
    {
      "slug": "machine-checked-recipe-knowledge",
      "project": "pyforge-mason",
      "title": "Machine-checked recipe knowledge",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "machine-checked-recipe-knowledge",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-machine-checked-recipe-knowledge"
    },
    {
      "slug": "miniforge-installer",
      "project": "pyforge-mason",
      "title": "A custom-branded Python distributable (PARKED)",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "miniforge-installer",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-miniforge-installer"
    },
    {
      "slug": "packaging-factory",
      "project": "pyforge-mason",
      "title": "the packaging factory (conda-forge-expert machinery)",
      "caps": 4,
      "companions": 2,
      "updated": "2026-08-22",
      "dream": "packaging-factory",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-packaging-factory"
    },
    {
      "slug": "pixi-container-image",
      "project": "pyforge-mason",
      "title": "One pixi base-layer discipline across the repo's Containerfiles",
      "caps": 1,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "pixi-container-image",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pixi-container-image"
    },
    {
      "slug": "pyforge-mason",
      "project": "pyforge-mason",
      "title": "mason CLI — the packaging factory, made portable",
      "caps": 13,
      "companions": 5,
      "updated": "2026-08-22",
      "dream": "pyforge-mason",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason"
    },
    {
      "slug": "pyforge-mason-recipe-validator",
      "project": "pyforge-mason",
      "title": "pyforge-mason-recipe-validator — retirement record",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "pyforge-mason-recipe-validator",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason-recipe-validator"
    },
    {
      "slug": "reusable-cicd-workflows",
      "project": "pyforge-mason",
      "title": "A centrally-maintained CI/CD workflow family (PARKED)",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "reusable-cicd-workflows",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-reusable-cicd-workflows"
    },
    {
      "slug": "pyforge-scribe",
      "project": "pyforge-scribe",
      "title": "Scribe (pyforge-scribe) — the team's inward voice",
      "caps": 4,
      "companions": 1,
      "updated": "2026-08-22",
      "dream": "pyforge-scribe",
      "path": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe"
    },
    {
      "slug": "pyforge-scribe-team-memory",
      "project": "pyforge-scribe",
      "title": "pyforge-scribe-team-memory — retirement record",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "pyforge-scribe-team-memory",
      "path": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe-team-memory"
    },
    {
      "slug": "scribe-mines-raw-session-transcripts",
      "project": "pyforge-scribe",
      "title": "Scribe reaches past curated memory into the raw transcripts",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "scribe-mines-raw-session-transcripts",
      "path": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-mines-raw-session-transcripts"
    },
    {
      "slug": "sentinel",
      "project": "pyforge-scribe",
      "title": "sentinel — retirement record",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "sentinel",
      "path": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-sentinel"
    },
    {
      "slug": "team-memory",
      "project": "pyforge-scribe",
      "title": "team-memory — retirement record",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "team-memory",
      "path": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-team-memory"
    },
    {
      "slug": "asgi-multiplexer-monolith",
      "project": "pyforge-steward",
      "title": "Django, Langflow, and DB-GPT co-locate in one ASGI process (ABSORBED)",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "asgi-multiplexer-monolith",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-asgi-multiplexer-monolith"
    },
    {
      "slug": "bmad-method-core-upgrade",
      "project": "pyforge-steward",
      "title": "The installed BMAD-METHOD core upgrades repeatably, not by heroics",
      "caps": 5,
      "companions": 1,
      "updated": "2026-08-22",
      "dream": "bmad-method-core-upgrade",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade"
    },
    {
      "slug": "bmad-module-provisioning",
      "project": "pyforge-steward",
      "title": "BMAD modules are provisioned, not hand-installed",
      "caps": 3,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "bmad-module-provisioning",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-module-provisioning"
    },
    {
      "slug": "bmad-suite-channel-product",
      "project": "pyforge-steward",
      "title": "The SelfExplainML bmad-suite is a governed product",
      "caps": 5,
      "companions": 1,
      "updated": "2026-08-22",
      "dream": "bmad-suite-channel-product",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-channel-product"
    },
    {
      "slug": "db-gpt-django-plugin",
      "project": "pyforge-steward",
      "title": "DB-GPT joins Django as a pluggable app (ABSORBED)",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "db-gpt-django-plugin",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-db-gpt-django-plugin"
    },
    {
      "slug": "developer-machine-bootstrap",
      "project": "pyforge-steward",
      "title": "A fresh machine reaches validate-fast through steward verbs",
      "caps": 1,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "developer-machine-bootstrap",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-developer-machine-bootstrap"
    },
    {
      "slug": "enterprise-airgap",
      "project": "pyforge-steward",
      "title": "the factory behind the firewall",
      "caps": 3,
      "companions": 1,
      "updated": "2026-08-22",
      "dream": "enterprise-airgap",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-enterprise-airgap"
    },
    {
      "slug": "enterprise-multi-agent-orchestration",
      "project": "pyforge-steward",
      "title": "Enterprise multi-agent orchestration atop the platform (ABSORBED)",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "enterprise-multi-agent-orchestration",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-enterprise-multi-agent-orchestration"
    },
    {
      "slug": "jira-github-projects-sync",
      "project": "pyforge-steward",
      "title": "All three open questions were ANSWERED by the architecture run on 2026-08-09 and by the",
      "caps": 5,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "jira-github-projects-sync",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-jira-github-projects-sync"
    },
    {
      "slug": "langflow-django-plugin",
      "project": "pyforge-steward",
      "title": "Langflow joins Django as a pluggable app (ABSORBED)",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "langflow-django-plugin",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-langflow-django-plugin"
    },
    {
      "slug": "local-ocp-hybrid-environment",
      "project": "pyforge-steward",
      "title": "The local OpenShift hybrid environment runs the agentic SDLC end to end",
      "caps": 5,
      "companions": 2,
      "updated": "2026-08-22",
      "dream": "local-ocp-hybrid-environment",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-local-ocp-hybrid-environment"
    },
    {
      "slug": "multi-repo-workspaces",
      "project": "pyforge-steward",
      "title": "One workspace opens every repo a story touches",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "multi-repo-workspaces",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-multi-repo-workspaces"
    },
    {
      "slug": "platform-fifteen-factors",
      "project": "pyforge-steward",
      "title": "The platform host earns its 15 factors",
      "caps": 5,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "platform-fifteen-factors",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-platform-fifteen-factors"
    },
    {
      "slug": "pyforge-steward",
      "project": "pyforge-steward",
      "title": "Steward (pyforge-steward) — the estate the factory stands on",
      "caps": 4,
      "companions": 1,
      "updated": "2026-08-22",
      "dream": "pyforge-steward",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward"
    },
    {
      "slug": "pyforge-steward-feedstock-maintenance",
      "project": "pyforge-steward",
      "title": "pyforge-steward-feedstock-maintenance — retirement record",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "pyforge-steward-feedstock-maintenance",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward-feedstock-maintenance"
    },
    {
      "slug": "python-agent-platform",
      "project": "pyforge-steward",
      "title": "python-agent-platform — one Django service hosts the agentic engines, anywhere",
      "caps": 6,
      "companions": 1,
      "updated": "2026-08-22",
      "dream": "python-agent-platform",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform"
    },
    {
      "slug": "scratch-worktree-lifecycle",
      "project": "pyforge-steward",
      "title": "Story-scoped scratch worktrees get a named lifecycle: `steward workspace start/ls/status/clean`",
      "caps": 5,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "scratch-worktree-lifecycle",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-scratch-worktree-lifecycle"
    },
    {
      "slug": "secure-live-dashboards",
      "project": "pyforge-steward",
      "title": "All six open questions were ANSWERED by the architecture run of 2026-08-09 and by",
      "caps": 8,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "secure-live-dashboards",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-secure-live-dashboards"
    },
    {
      "slug": "unified-container",
      "project": "pyforge-steward",
      "title": "SHIPPED 2026-08-09: steward Epic 7 \"The one-container Guild\" closed 5/5, and the",
      "caps": 5,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "unified-container",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-unified-container"
    },
    {
      "slug": "compliance-factory-web-face",
      "project": "pyforge-warden",
      "title": "A web face for the compliance factory",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "compliance-factory-web-face",
      "path": "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-compliance-factory-web-face"
    },
    {
      "slug": "package-inventory-eligibility",
      "project": "pyforge-warden",
      "title": "Every package has one provenance trail and one eligibility answer",
      "caps": 3,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "package-inventory-eligibility",
      "path": "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-package-inventory-eligibility"
    },
    {
      "slug": "pyforge-warden",
      "project": "pyforge-warden",
      "title": "Warden — the compliance gate that never false-greens",
      "caps": 12,
      "companions": 3,
      "updated": "2026-08-22",
      "dream": "pyforge-warden",
      "path": "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden"
    },
    {
      "slug": "pyforge-warden-compliance-gates",
      "project": "pyforge-warden",
      "title": "pyforge-warden-compliance-gates — retirement record",
      "caps": 7,
      "companions": 0,
      "updated": "2026-08-22",
      "dream": "pyforge-warden-compliance-gates",
      "path": "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden-compliance-gates"
    },
    {
      "slug": "pyforge-charter",
      "project": "docs/governance",
      "title": "The Charter — keeping the constitution true",
      "caps": 8,
      "companions": 0,
      "updated": "2026-08-08",
      "dream": "pyforge-charter",
      "path": "docs/governance/spec-pyforge-charter"
    }
  ],
  "pitch": [
    {
      "slug": "agentic-sdlc",
      "title": "Agentic AI across the SDLC",
      "have": {
        "prototype": true,
        "exec": false,
        "infographic": false,
        "marp": true,
        "standalone": true,
        "pptx": true
      },
      "n": 4,
      "of": 6,
      "export": "2026-08-01",
      "path": "presentations/agentic-sdlc",
      "owner": "marshal"
    },
    {
      "slug": "deckcraft",
      "title": "PyForge Deckcraft",
      "have": {
        "prototype": true,
        "exec": true,
        "infographic": true,
        "marp": true,
        "standalone": true,
        "pptx": true
      },
      "n": 6,
      "of": 6,
      "export": "2026-07-25",
      "path": "presentations/deckcraft",
      "owner": ""
    },
    {
      "slug": "presenton-pixi-image",
      "title": "PyForge Presenton-pixi-image",
      "have": {
        "prototype": true,
        "exec": true,
        "infographic": true,
        "marp": true,
        "standalone": true,
        "pptx": true
      },
      "n": 6,
      "of": 6,
      "export": "2026-07-25",
      "path": "presentations/presenton-pixi-image",
      "owner": "mason"
    },
    {
      "slug": "pyforge-atlas",
      "title": "PyForge Atlas",
      "have": {
        "prototype": true,
        "exec": true,
        "infographic": true,
        "marp": true,
        "standalone": true,
        "pptx": true
      },
      "n": 6,
      "of": 6,
      "export": "2026-07-24",
      "path": "presentations/pyforge-atlas",
      "owner": "atlas"
    },
    {
      "slug": "pyforge-doctor",
      "title": "PyForge Doctor",
      "have": {
        "prototype": true,
        "exec": true,
        "infographic": true,
        "marp": true,
        "standalone": true,
        "pptx": true
      },
      "n": 6,
      "of": 6,
      "export": "2026-07-24",
      "path": "presentations/pyforge-doctor",
      "owner": "doctor"
    },
    {
      "slug": "pyforge-genesis",
      "title": "PyForge Genesis",
      "have": {
        "prototype": true,
        "exec": true,
        "infographic": true,
        "marp": true,
        "standalone": true,
        "pptx": true
      },
      "n": 6,
      "of": 6,
      "export": "2026-07-24",
      "path": "presentations/pyforge-genesis",
      "owner": "guild"
    },
    {
      "slug": "pyforge-herald",
      "title": "PyForge Herald",
      "have": {
        "prototype": true,
        "exec": true,
        "infographic": true,
        "marp": true,
        "standalone": true,
        "pptx": true
      },
      "n": 6,
      "of": 6,
      "export": "2026-07-24",
      "path": "presentations/pyforge-herald",
      "owner": "herald"
    },
    {
      "slug": "pyforge-marshal",
      "title": "PyForge Marshal",
      "have": {
        "prototype": true,
        "exec": true,
        "infographic": true,
        "marp": true,
        "standalone": true,
        "pptx": true
      },
      "n": 6,
      "of": 6,
      "export": "2026-07-31",
      "path": "presentations/pyforge-marshal",
      "owner": "marshal"
    },
    {
      "slug": "pyforge-mason",
      "title": "PyForge Mason",
      "have": {
        "prototype": true,
        "exec": true,
        "infographic": true,
        "marp": true,
        "standalone": true,
        "pptx": true
      },
      "n": 6,
      "of": 6,
      "export": "2026-07-24",
      "path": "presentations/pyforge-mason",
      "owner": "mason"
    },
    {
      "slug": "pyforge-scribe",
      "title": "PyForge Scribe",
      "have": {
        "prototype": true,
        "exec": true,
        "infographic": true,
        "marp": true,
        "standalone": true,
        "pptx": true
      },
      "n": 6,
      "of": 6,
      "export": "2026-07-24",
      "path": "presentations/pyforge-scribe",
      "owner": "scribe"
    },
    {
      "slug": "pyforge-steward",
      "title": "PyForge Steward",
      "have": {
        "prototype": true,
        "exec": true,
        "infographic": true,
        "marp": true,
        "standalone": true,
        "pptx": true
      },
      "n": 6,
      "of": 6,
      "export": "2026-07-24",
      "path": "presentations/pyforge-steward",
      "owner": "steward"
    },
    {
      "slug": "pyforge-warden",
      "title": "PyForge Warden",
      "have": {
        "prototype": true,
        "exec": true,
        "infographic": true,
        "marp": true,
        "standalone": true,
        "pptx": true
      },
      "n": 6,
      "of": 6,
      "export": "2026-07-15",
      "path": "presentations/pyforge-warden",
      "owner": "warden"
    },
    {
      "slug": "unity-data-stack",
      "title": "PyForge Unity-data-stack",
      "have": {
        "prototype": true,
        "exec": true,
        "infographic": true,
        "marp": true,
        "standalone": true,
        "pptx": true
      },
      "n": 6,
      "of": 6,
      "export": "2026-07-25",
      "path": "presentations/unity-data-stack",
      "owner": "atlas"
    },
    {
      "slug": "wasm-analytics-stack",
      "title": "PyForge Wasm-analytics-stack",
      "have": {
        "prototype": true,
        "exec": true,
        "infographic": true,
        "marp": true,
        "standalone": true,
        "pptx": true
      },
      "n": 6,
      "of": 6,
      "export": "2026-07-25",
      "path": "presentations/wasm-analytics-stack",
      "owner": "atlas"
    }
  ],
  "archived": [
    {
      "name": "Agent portability — BMAD on any agent, never vendor-locked",
      "reason": "absorbed",
      "owner": "marshal",
      "note": "Agent portability — BMAD on any agent, never vendor-locked",
      "link": "docs/dreams/agent-portability.md"
    },
    {
      "name": "Artifact console — the factory board, hosted as a chat artifact",
      "reason": "retired",
      "owner": "marshal",
      "note": "Artifact console — the factory board, hosted as a chat artifact",
      "link": "docs/dreams/artifact-console.md"
    },
    {
      "name": "bmad-loop can't see a story's own documented dependency",
      "reason": "retired",
      "owner": "marshal",
      "note": "bmad-loop can't see a story's own documented dependency",
      "link": "docs/dreams/bmad-loop-forward-dependency-blindness.md"
    },
    {
      "name": "One fabricated commit, eight stations of debris",
      "reason": "retired",
      "owner": "marshal",
      "note": "One fabricated commit, eight stations of debris",
      "link": "docs/dreams/bmad-output-hygiene.md"
    },
    {
      "name": "copilot-cli on conda-forge — blocked at the license",
      "reason": "blocked",
      "owner": "mason",
      "note": "copilot-cli on conda-forge — blocked at the license",
      "link": "docs/dreams/copilot-cli-packaging.md"
    },
    {
      "name": "The dashboard assumes slug == project directory — it isn't, and won't stay",
      "reason": "retired",
      "owner": "marshal",
      "note": "The dashboard assumes slug == project directory — it isn't, and won't stay",
      "link": "docs/dreams/dashboard-project-path-derivation.md"
    },
    {
      "name": "DB-GPT on conda-forge — the multi-output agent stack",
      "reason": "terminal",
      "owner": "mason",
      "note": "DB-GPT on conda-forge — the multi-output agent stack",
      "link": "docs/dreams/db-gpt-packaging.md"
    },
    {
      "name": "The Dream-to-Code model has never verified itself",
      "reason": "retired",
      "owner": "marshal",
      "note": "The Dream-to-Code model has never verified itself",
      "link": "docs/dreams/dream-to-code-model-self-verification.md"
    },
    {
      "name": "Fidelity enforcement — a contract is only a contract if something fails against it",
      "reason": "absorbed",
      "owner": "marshal",
      "note": "Fidelity enforcement — a contract is only a contract if something fails against it",
      "link": "docs/dreams/fidelity-enforcement.md"
    },
    {
      "name": "Fleet Chain Completeness — Orchestrated Dream-to-Code Regeneration",
      "reason": "absorbed",
      "owner": "marshal",
      "note": "Fleet Chain Completeness — Orchestrated Dream-to-Code Regeneration",
      "link": "docs/dreams/fleet-chain-completeness.md"
    },
    {
      "name": "Retire genesis-installer — one marshal CLI, one PRD/architecture/epics chain",
      "reason": "retired",
      "owner": "marshal",
      "note": "Retire genesis-installer — one marshal CLI, one PRD/architecture/epics chain",
      "link": "docs/dreams/genesis-installer-name-retirement.md"
    },
    {
      "name": "Genesis installer — the seed, made executable",
      "reason": "absorbed",
      "owner": "marshal",
      "note": "Genesis installer — the seed, made executable",
      "link": "docs/dreams/genesis-installer.md"
    },
    {
      "name": "Herald — Moments 2–4 Missing Surface",
      "reason": "absorbed",
      "owner": "herald",
      "note": "Herald — Moments 2–4 Missing Surface",
      "link": "docs/dreams/herald-moments-2-4-missing-surface.md"
    },
    {
      "name": "Herald's Pitch Deck — Moment 1 Orchestration (Consolidated)",
      "reason": "absorbed",
      "owner": "herald",
      "note": "Herald's Pitch Deck — Moment 1 Orchestration (Consolidated)",
      "link": "docs/dreams/herald-pitch.md"
    },
    {
      "name": "Refreshing every loop-home from main is a hand-run ritual",
      "reason": "retired",
      "owner": "marshal",
      "note": "Refreshing every loop-home from main is a hand-run ritual",
      "link": "docs/dreams/loop-home-fleet-refresh.md"
    },
    {
      "name": "Microsoft org sweep — audit one upstream org, package what is missing",
      "reason": "absorbed",
      "owner": "atlas",
      "note": "Microsoft org sweep — audit one upstream org, package what is missing",
      "link": "docs/dreams/microsoft-org-sweep.md"
    },
    {
      "name": "One front door — Marshal drives everything BMAD installs",
      "reason": "absorbed",
      "owner": "marshal",
      "note": "One front door — Marshal drives everything BMAD installs",
      "link": "docs/dreams/one-front-door.md"
    },
    {
      "name": "Presenton, conda-native — AI decks inside the regulated enterprise",
      "reason": "blocked",
      "owner": "mason",
      "note": "Presenton, conda-native — AI decks inside the regulated enterprise",
      "link": "docs/dreams/presenton-pixi-image.md"
    },
    {
      "name": "\"Dream — PyForge Atlas Intelligence Platform\"",
      "reason": "duplicate",
      "owner": "atlas",
      "note": "\"Dream — PyForge Atlas Intelligence Platform\"",
      "link": "docs/dreams/pyforge-atlas-intelligence-platform.md"
    },
    {
      "name": "One primitive, one home — the shared floor under eight stations",
      "reason": "retired",
      "owner": "marshal",
      "note": "One primitive, one home — the shared floor under eight stations",
      "link": "docs/dreams/pyforge-core.md"
    },
    {
      "name": "\"Dream — PyForge Doctor: Dependency Health Diagnostics\"",
      "reason": "absorbed",
      "owner": "doctor",
      "note": "\"Dream — PyForge Doctor: Dependency Health Diagnostics\"",
      "link": "docs/dreams/pyforge-doctor-dependency-health.md"
    },
    {
      "name": "\"Dream — PyForge Marshal: Loop Orchestrator\"",
      "reason": "duplicate",
      "owner": "marshal",
      "note": "\"Dream — PyForge Marshal: Loop Orchestrator\"",
      "link": "docs/dreams/pyforge-marshal-loop-orchestrator.md"
    },
    {
      "name": "\"Dream — PyForge Mason: Recipe Validator\"",
      "reason": "conflicts-with-decided-architecture",
      "owner": "mason",
      "note": "\"Dream — PyForge Mason: Recipe Validator\"",
      "link": "docs/dreams/pyforge-mason-recipe-validator.md"
    },
    {
      "name": "\"Dream — PyForge Scribe: Team Memory Management\"",
      "reason": "duplicate",
      "owner": "scribe",
      "note": "\"Dream — PyForge Scribe: Team Memory Management\"",
      "link": "docs/dreams/pyforge-scribe-team-memory.md"
    },
    {
      "name": "\"Dream — PyForge Steward: Feedstock Maintenance Automation\"",
      "reason": "absorbed",
      "owner": "steward",
      "note": "\"Dream — PyForge Steward: Feedstock Maintenance Automation\"",
      "link": "docs/dreams/pyforge-steward-feedstock-maintenance.md"
    },
    {
      "name": "\"Dream — PyForge Testing Charter: Systematic Testing for the Guild\"",
      "reason": "absorbed",
      "owner": "marshal",
      "note": "\"Dream — PyForge Testing Charter: Systematic Testing for the Guild\"",
      "link": "docs/dreams/pyforge-testing-charter.md"
    },
    {
      "name": "\"Dream — PyForge Warden: Compliance Gates\"",
      "reason": "duplicate",
      "owner": "warden",
      "note": "\"Dream — PyForge Warden: Compliance Gates\"",
      "link": "docs/dreams/pyforge-warden-compliance-gates.md"
    },
    {
      "name": "Sentinel — the AI Software Factory (the ancestor)",
      "reason": "absorbed",
      "owner": "scribe",
      "note": "Sentinel — the AI Software Factory (the ancestor)",
      "link": "docs/dreams/sentinel.md"
    },
    {
      "name": "The dashboard goes stale because promotion is a remembered step",
      "reason": "retired",
      "owner": "marshal",
      "note": "The dashboard goes stale because promotion is a remembered step",
      "link": "docs/dreams/sprint-status-auto-promote.md"
    },
    {
      "name": "Team memory — what the team knows, the agents know",
      "reason": "absorbed",
      "owner": "scribe",
      "note": "Team memory — what the team knows, the agents know",
      "link": "docs/dreams/team-memory.md"
    },
    {
      "name": "Unity Data Stack — the enterprise innersource platform",
      "reason": "absorbed",
      "owner": "atlas",
      "note": "Unity Data Stack — the enterprise innersource platform",
      "link": "docs/dreams/unity-data-stack.md"
    },
    {
      "name": "Upstream discovery — package it before it's asked for",
      "reason": "absorbed",
      "owner": "atlas",
      "note": "Upstream discovery — package it before it's asked for",
      "link": "docs/dreams/upstream-discovery.md"
    },
    {
      "name": "WASM Data Stack",
      "reason": "absorbed",
      "owner": "atlas",
      "note": "WASM Data Stack",
      "link": "docs/dreams/wasm-analytics-stack.md"
    }
  ],
  "campaigns": [
    {
      "id": "spec-completion-2026-07-25",
      "title": "Spec Completion",
      "kind": "planning",
      "status": "completed",
      "completed": "2026-07-25",
      "record": "_bmad-output/projects/local-recipes/planning-artifacts/campaign-spec-completion-2026-07-25.md",
      "launched": "2026-07-25",
      "chain": "research → brief → PRD → architecture → epics",
      "rows": [
        {
          "wave": "1a",
          "slug": "pyforge-doctor",
          "model": "sonnet",
          "depth": "epics",
          "state": "running",
          "have": {
            "research": true,
            "brief": true,
            "prd": true,
            "architecture": true,
            "epics": true
          },
          "n": 5,
          "of": 5,
          "status": "landed",
          "planning_project": "pyforge-doctor",
          "redirect": null
        },
        {
          "wave": "1b",
          "slug": "pyforge-steward",
          "model": "sonnet",
          "depth": "epics",
          "state": "running",
          "have": {
            "research": true,
            "brief": true,
            "prd": true,
            "architecture": true,
            "epics": true
          },
          "n": 5,
          "of": 5,
          "status": "landed",
          "planning_project": "pyforge-steward",
          "redirect": null
        },
        {
          "wave": "1c",
          "slug": "pyforge-scribe",
          "model": "sonnet",
          "depth": "epics",
          "state": "running",
          "have": {
            "research": true,
            "brief": true,
            "prd": true,
            "architecture": true,
            "epics": true
          },
          "n": 5,
          "of": 5,
          "status": "landed",
          "planning_project": "pyforge-scribe",
          "redirect": null
        },
        {
          "wave": "1d",
          "slug": "pyforge-herald",
          "model": "sonnet",
          "depth": "epics",
          "state": "running",
          "have": {
            "research": true,
            "brief": true,
            "prd": true,
            "architecture": true,
            "epics": true
          },
          "n": 5,
          "of": 5,
          "status": "landed",
          "planning_project": "pyforge-herald",
          "redirect": null
        },
        {
          "wave": "1e",
          "slug": "pyforge-marshal",
          "model": "opus",
          "depth": "epics",
          "state": "running",
          "have": {
            "research": true,
            "brief": true,
            "prd": true,
            "architecture": true,
            "epics": true
          },
          "n": 5,
          "of": 5,
          "status": "landed",
          "planning_project": "pyforge-marshal",
          "redirect": null
        },
        {
          "wave": "1f",
          "slug": "pyforge-mason",
          "model": "opus",
          "depth": "epics",
          "state": "running",
          "have": {
            "research": true,
            "brief": true,
            "prd": true,
            "architecture": true,
            "epics": true
          },
          "n": 5,
          "of": 5,
          "status": "landed",
          "planning_project": "pyforge-mason",
          "redirect": null
        },
        {
          "wave": "2a",
          "slug": "presenton-pixi-image",
          "model": "sonnet",
          "depth": "epics",
          "state": "running",
          "have": {
            "research": true,
            "brief": true,
            "prd": true,
            "architecture": true,
            "epics": true
          },
          "n": 5,
          "of": 5,
          "status": "landed",
          "planning_project": "pyforge-mason",
          "redirect": null
        },
        {
          "wave": "2b",
          "slug": "wasm-analytics-stack",
          "model": "sonnet",
          "depth": "prd+arch",
          "state": "running",
          "have": {
            "research": true,
            "brief": true,
            "prd": true,
            "architecture": true,
            "epics": true
          },
          "n": 4,
          "of": 4,
          "status": "landed",
          "planning_project": "pyforge-atlas",
          "redirect": null
        },
        {
          "wave": "2c",
          "slug": "unity-data-stack",
          "model": "opus",
          "depth": "prd+arch",
          "state": "running",
          "have": {
            "research": true,
            "brief": true,
            "prd": true,
            "architecture": true,
            "epics": true
          },
          "n": 4,
          "of": 4,
          "status": "landed",
          "planning_project": "pyforge-atlas",
          "redirect": null
        },
        {
          "wave": "2d",
          "slug": "pyforge-genesis",
          "model": "opus",
          "depth": "epics",
          "state": "queued",
          "have": {
            "research": false,
            "brief": false,
            "prd": false,
            "architecture": false,
            "epics": false
          },
          "n": 0,
          "of": 5,
          "status": "queued",
          "planning_project": null,
          "redirect": "docs/governance"
        }
      ]
    },
    {
      "id": "build-2026-07-25",
      "title": "The Build",
      "kind": "build",
      "status": "active",
      "launched": "2026-07-25",
      "rows": [
        {
          "slug": "pyforge-herald",
          "pkey": "herald",
          "stories": 17,
          "state": "done",
          "note": "line 1 — smallest full product, spec settled 0 OQs",
          "done": 58,
          "total": 58,
          "epics_path": "_bmad-output/projects/pyforge-herald/planning-artifacts/epics.md",
          "redirect": null
        },
        {
          "slug": "pyforge-doctor",
          "pkey": "doctor",
          "stories": 12,
          "state": "done",
          "note": "line 2 — consolidative wrap",
          "done": 61,
          "total": 61,
          "epics_path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md",
          "redirect": null
        },
        {
          "slug": "pyforge-scribe",
          "pkey": "scribe",
          "stories": 9,
          "state": "done",
          "note": "line 3 — team memory + graph",
          "done": 11,
          "total": 11,
          "epics_path": "_bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md",
          "redirect": null
        },
        {
          "slug": "pyforge-steward",
          "pkey": null,
          "stories": 18,
          "state": "in-progress",
          "note": "next free slot",
          "done": 53,
          "total": 79,
          "epics_path": "_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md",
          "redirect": null
        },
        {
          "slug": "pyforge-mason",
          "pkey": null,
          "stories": 38,
          "state": "done",
          "note": "longest persona line; CFE Rule-2 retro at closeout",
          "done": 47,
          "total": 47,
          "epics_path": "_bmad-output/projects/pyforge-mason/planning-artifacts/epics.md",
          "redirect": null
        },
        {
          "slug": "presenton-pixi-image",
          "pkey": null,
          "stories": 30,
          "state": "held",
          "note": "operator Phase-0 gates: MS disconnected-stack check + memory-subsystem scope",
          "done": 0,
          "total": 30,
          "epics_path": "_bmad-output/projects/pyforge-mason/planning-artifacts/epics-presenton-pixi-image.md",
          "redirect": null
        },
        {
          "slug": "pyforge-marshal",
          "pkey": null,
          "stories": 86,
          "state": "in-progress",
          "note": "epics 1-12 — the seed installer's epics 7-12 merged in 2026-08-08; one canonical epics.md",
          "done": 113,
          "total": 162,
          "epics_path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md",
          "redirect": null
        },
        {
          "slug": "wasm-analytics-stack",
          "pkey": null,
          "stories": 0,
          "state": "future",
          "note": "PRD+arch only by design; stories decompose when scheduled",
          "done": 0,
          "total": 0,
          "epics_path": null,
          "redirect": null
        },
        {
          "slug": "unity-data-stack",
          "pkey": null,
          "stories": 0,
          "state": "future",
          "note": "PRD+arch only by design; stories decompose when scheduled",
          "done": 0,
          "total": 0,
          "epics_path": null,
          "redirect": null
        }
      ]
    }
  ],
  "fleet": {
    "stages": [
      "dream",
      "deck",
      "spec",
      "research",
      "brief",
      "prd",
      "ux",
      "arch",
      "context",
      "epics",
      "sprint",
      "tea",
      "gates",
      "code",
      "verify",
      "retro"
    ],
    "staleDays": 30,
    "shelfLife": {
      "dream": null,
      "deck": 90,
      "spec": null,
      "research": 90,
      "brief": 90,
      "prd": 90,
      "ux": 90,
      "arch": 90,
      "context": null,
      "epics": 90,
      "sprint": 90,
      "tea": null,
      "gates": 90,
      "code": 90,
      "verify": 90,
      "retro": null
    },
    "sound": 0,
    "live": 81,
    "reached": 8,
    "gaps": 80,
    "findings": 25,
    "rows": [
      {
        "label": "atlas",
        "slug": "pyforge-atlas",
        "project": "pyforge-atlas",
        "dream": "pyforge-atlas",
        "owner": "atlas",
        "stages": {
          "dream": "2026-07-23",
          "deck": "2026-07-23",
          "spec": "2026-07-23",
          "research": "2026-07-25",
          "brief": "2026-07-25",
          "prd": "2026-07-17",
          "ux": "",
          "arch": "2026-07-17",
          "context": "2026-08-04",
          "epics": "2026-07-17",
          "sprint": "2026-07-29",
          "tea": "2026-07-17",
          "gates": "2026-07-17",
          "code": "2026-07-17",
          "verify": "2026-07-17",
          "retro": "2026-07-25"
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "2026-07-25",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "2026-07-25",
          "prd": "2026-08-01",
          "ux": "",
          "arch": "2026-08-02",
          "context": "2026-08-04",
          "epics": "2026-08-14",
          "sprint": "2026-08-22",
          "tea": "2026-08-20",
          "gates": "2026-08-10",
          "code": "2026-08-14",
          "verify": "2026-08-14",
          "retro": "2026-08-02"
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": false
          },
          "deck": {
            "have": {
              "prototype": true,
              "exec": true,
              "infographic": true,
              "marp": true,
              "standalone": true,
              "pptx": true
            },
            "n": 6,
            "of": 6,
            "missing": []
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "pyforge-atlas",
        "noDream": false,
        "unowned": false,
        "backfilled": true,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research",
          "brief",
          "prd",
          "arch",
          "context",
          "epics",
          "sprint",
          "tea",
          "gates",
          "code",
          "verify",
          "retro"
        ],
        "gaps": [],
        "partial": [],
        "staleBy": [
          {
            "kind": "feeds",
            "stage": "research",
            "than": "brief",
            "at": "2026-08-08",
            "other": "2026-07-25"
          },
          {
            "kind": "feeds",
            "stage": "spec",
            "than": "prd",
            "at": "2026-08-22T05:38",
            "other": "2026-08-01"
          },
          {
            "kind": "feeds",
            "stage": "code",
            "than": "retro",
            "at": "2026-08-14",
            "other": "2026-08-02"
          }
        ],
        "furthest": "retro",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "0.1.0",
        "progress": "57/57",
        "complete": 14,
        "of": 14
      },
      {
        "label": "doctor",
        "slug": "pyforge-doctor",
        "project": "pyforge-doctor",
        "dream": "pyforge-doctor",
        "owner": "doctor",
        "stages": {
          "dream": "2026-07-23",
          "deck": "2026-07-23",
          "spec": "2026-07-25",
          "research": "2026-07-25",
          "brief": "2026-07-25",
          "prd": "2026-07-25",
          "ux": "",
          "arch": "2026-07-25",
          "context": "2026-08-01",
          "epics": "2026-07-25",
          "sprint": "2026-07-29",
          "tea": "2026-07-25",
          "gates": "2026-08-01",
          "code": "2026-07-25",
          "verify": "2026-07-25",
          "retro": "2026-08-08"
        },
        "updatedAt": {
          "dream": "2026-08-08",
          "deck": "2026-07-25",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "2026-07-25",
          "prd": "2026-08-02",
          "ux": "",
          "arch": "2026-08-02",
          "context": "2026-08-01",
          "epics": "2026-08-15",
          "sprint": "2026-08-22",
          "tea": "2026-08-22",
          "gates": "2026-08-10",
          "code": "2026-08-13",
          "verify": "2026-08-13",
          "retro": "2026-08-08"
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": false
          },
          "deck": {
            "have": {
              "prototype": true,
              "exec": true,
              "infographic": true,
              "marp": true,
              "standalone": true,
              "pptx": true
            },
            "n": 6,
            "of": 6,
            "missing": []
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "pyforge-doctor",
        "noDream": false,
        "unowned": false,
        "backfilled": true,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research",
          "brief",
          "prd",
          "arch",
          "context",
          "epics",
          "sprint",
          "tea",
          "gates",
          "code",
          "verify",
          "retro"
        ],
        "gaps": [],
        "partial": [],
        "staleBy": [
          {
            "kind": "feeds",
            "stage": "research",
            "than": "brief",
            "at": "2026-08-08",
            "other": "2026-07-25"
          },
          {
            "kind": "feeds",
            "stage": "spec",
            "than": "prd",
            "at": "2026-08-22T05:38",
            "other": "2026-08-02"
          },
          {
            "kind": "feeds",
            "stage": "code",
            "than": "retro",
            "at": "2026-08-13",
            "other": "2026-08-08"
          }
        ],
        "furthest": "retro",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "0.1.0",
        "progress": "61/61",
        "complete": 14,
        "of": 14
      },
      {
        "label": "herald",
        "slug": "pyforge-herald",
        "project": "pyforge-herald",
        "dream": "pyforge-herald",
        "owner": "herald",
        "stages": {
          "dream": "2026-07-23",
          "deck": "2026-07-23",
          "spec": "2026-07-29",
          "research": "2026-07-25",
          "brief": "2026-08-01",
          "prd": "2026-08-01",
          "ux": "",
          "arch": "2026-08-01",
          "context": "2026-08-02",
          "epics": "2026-07-25",
          "sprint": "2026-07-29",
          "tea": "2026-07-25",
          "gates": "2026-08-01",
          "code": "2026-07-25",
          "verify": "2026-07-25",
          "retro": "2026-08-08"
        },
        "updatedAt": {
          "dream": "2026-08-08",
          "deck": "2026-07-25",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "2026-08-02",
          "prd": "2026-08-02",
          "ux": "",
          "arch": "2026-08-02",
          "context": "2026-08-02",
          "epics": "2026-08-22",
          "sprint": "2026-08-22",
          "tea": "2026-08-22",
          "gates": "2026-08-10",
          "code": "2026-08-22",
          "verify": "2026-08-22",
          "retro": "2026-08-08"
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": false
          },
          "deck": {
            "have": {
              "prototype": true,
              "exec": true,
              "infographic": true,
              "marp": true,
              "standalone": true,
              "pptx": true
            },
            "n": 6,
            "of": 6,
            "missing": []
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "pyforge-herald",
        "noDream": false,
        "unowned": false,
        "backfilled": true,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research",
          "brief",
          "prd",
          "arch",
          "context",
          "epics",
          "sprint",
          "tea",
          "gates",
          "code",
          "verify",
          "retro"
        ],
        "gaps": [],
        "partial": [],
        "staleBy": [
          {
            "kind": "feeds",
            "stage": "research",
            "than": "brief",
            "at": "2026-08-08",
            "other": "2026-08-02"
          },
          {
            "kind": "feeds",
            "stage": "spec",
            "than": "prd",
            "at": "2026-08-22T05:38",
            "other": "2026-08-02"
          },
          {
            "kind": "feeds",
            "stage": "code",
            "than": "retro",
            "at": "2026-08-22",
            "other": "2026-08-08"
          }
        ],
        "furthest": "retro",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "0.1.0",
        "progress": "58/58",
        "complete": 14,
        "of": 14
      },
      {
        "label": "marshal",
        "slug": "pyforge-marshal",
        "project": "pyforge-marshal",
        "dream": "pyforge-marshal",
        "owner": "marshal",
        "stages": {
          "dream": "2026-07-23",
          "deck": "2026-07-23",
          "spec": "2026-07-25",
          "research": "2026-07-16",
          "brief": "2026-07-25",
          "prd": "2026-07-25",
          "ux": "",
          "arch": "2026-07-25",
          "context": "2026-06-20",
          "epics": "2026-07-25",
          "sprint": "2026-07-29",
          "tea": "2026-07-26",
          "gates": "2026-06-21",
          "code": "2026-07-26",
          "verify": "2026-07-26",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-21",
          "deck": "2026-08-01",
          "spec": "2026-08-22T07:48",
          "research": "2026-08-08",
          "brief": "2026-08-02",
          "prd": "2026-08-14",
          "ux": "",
          "arch": "2026-08-10",
          "context": "2026-06-20",
          "epics": "2026-08-22",
          "sprint": "2026-08-22",
          "tea": "2026-08-22",
          "gates": "2026-08-10",
          "code": "2026-08-21",
          "verify": "2026-08-21",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": false
          },
          "deck": {
            "have": {
              "prototype": true,
              "exec": true,
              "infographic": true,
              "marp": true,
              "standalone": true,
              "pptx": true
            },
            "n": 6,
            "of": 6,
            "missing": []
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "pyforge-marshal",
        "noDream": false,
        "unowned": false,
        "backfilled": true,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research",
          "brief",
          "prd",
          "arch",
          "context",
          "epics",
          "sprint",
          "tea",
          "gates",
          "code",
          "verify"
        ],
        "gaps": [],
        "partial": [],
        "staleBy": [
          {
            "kind": "feeds",
            "stage": "research",
            "than": "brief",
            "at": "2026-08-08",
            "other": "2026-08-02"
          },
          {
            "kind": "feeds",
            "stage": "prd",
            "than": "arch",
            "at": "2026-08-14",
            "other": "2026-08-10"
          },
          {
            "kind": "feeds",
            "stage": "spec",
            "than": "prd",
            "at": "2026-08-22T07:48",
            "other": "2026-08-14"
          }
        ],
        "furthest": "verify",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "0.1.0",
        "progress": "113/162",
        "complete": 13,
        "of": 13
      },
      {
        "label": "mason",
        "slug": "pyforge-mason",
        "project": "pyforge-mason",
        "dream": "pyforge-mason",
        "owner": "mason",
        "stages": {
          "dream": "2026-07-25",
          "deck": "2026-07-23",
          "spec": "2026-07-25",
          "research": "2026-07-25",
          "brief": "2026-07-25",
          "prd": "2026-07-25",
          "ux": "",
          "arch": "2026-07-25",
          "context": "2026-08-02",
          "epics": "2026-07-25",
          "sprint": "2026-07-29",
          "tea": "2026-07-25",
          "gates": "2026-08-01",
          "code": "2026-07-25",
          "verify": "2026-07-25",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "2026-07-25",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "2026-07-25",
          "prd": "2026-08-01",
          "ux": "",
          "arch": "2026-08-02",
          "context": "2026-08-02",
          "epics": "2026-08-02",
          "sprint": "2026-08-22",
          "tea": "2026-08-22",
          "gates": "2026-08-10",
          "code": "2026-08-14",
          "verify": "2026-08-14",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": false
          },
          "deck": {
            "have": {
              "prototype": true,
              "exec": true,
              "infographic": true,
              "marp": true,
              "standalone": true,
              "pptx": true
            },
            "n": 6,
            "of": 6,
            "missing": []
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "pyforge-mason",
        "noDream": false,
        "unowned": false,
        "backfilled": true,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research",
          "brief",
          "prd",
          "arch",
          "context",
          "epics",
          "sprint",
          "tea",
          "gates",
          "code",
          "verify"
        ],
        "gaps": [],
        "partial": [],
        "staleBy": [
          {
            "kind": "feeds",
            "stage": "research",
            "than": "brief",
            "at": "2026-08-08",
            "other": "2026-07-25"
          },
          {
            "kind": "feeds",
            "stage": "spec",
            "than": "prd",
            "at": "2026-08-22T05:39",
            "other": "2026-08-01"
          },
          {
            "kind": "behind-code",
            "stage": "prd",
            "at": "2026-08-01",
            "other": "2026-08-14"
          },
          {
            "kind": "behind-code",
            "stage": "arch",
            "at": "2026-08-02",
            "other": "2026-08-14"
          }
        ],
        "furthest": "verify",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "0.1.0",
        "progress": "47/47",
        "complete": 13,
        "of": 13
      },
      {
        "label": "scribe",
        "slug": "pyforge-scribe",
        "project": "pyforge-scribe",
        "dream": "pyforge-scribe",
        "owner": "scribe",
        "stages": {
          "dream": "2026-07-23",
          "deck": "2026-07-23",
          "spec": "2026-07-25",
          "research": "2026-07-25",
          "brief": "2026-07-25",
          "prd": "2026-07-25",
          "ux": "",
          "arch": "2026-07-25",
          "context": "2026-08-01",
          "epics": "2026-07-25",
          "sprint": "2026-07-29",
          "tea": "2026-07-25",
          "gates": "2026-08-01",
          "code": "2026-07-25",
          "verify": "2026-07-25",
          "retro": "2026-08-08"
        },
        "updatedAt": {
          "dream": "2026-08-08",
          "deck": "2026-07-25",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "2026-07-25",
          "prd": "2026-08-01",
          "ux": "",
          "arch": "2026-08-02",
          "context": "2026-08-01",
          "epics": "2026-08-02",
          "sprint": "2026-08-22",
          "tea": "2026-08-22",
          "gates": "2026-08-10",
          "code": "2026-08-12",
          "verify": "2026-08-12",
          "retro": "2026-08-08"
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": false
          },
          "deck": {
            "have": {
              "prototype": true,
              "exec": true,
              "infographic": true,
              "marp": true,
              "standalone": true,
              "pptx": true
            },
            "n": 6,
            "of": 6,
            "missing": []
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "pyforge-scribe",
        "noDream": false,
        "unowned": false,
        "backfilled": true,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research",
          "brief",
          "prd",
          "arch",
          "context",
          "epics",
          "sprint",
          "tea",
          "gates",
          "code",
          "verify",
          "retro"
        ],
        "gaps": [],
        "partial": [],
        "staleBy": [
          {
            "kind": "feeds",
            "stage": "research",
            "than": "brief",
            "at": "2026-08-08",
            "other": "2026-07-25"
          },
          {
            "kind": "feeds",
            "stage": "spec",
            "than": "prd",
            "at": "2026-08-22T05:39",
            "other": "2026-08-01"
          },
          {
            "kind": "feeds",
            "stage": "code",
            "than": "retro",
            "at": "2026-08-12",
            "other": "2026-08-08"
          }
        ],
        "furthest": "retro",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "0.1.0",
        "progress": "11/11",
        "complete": 14,
        "of": 14
      },
      {
        "label": "steward",
        "slug": "pyforge-steward",
        "project": "pyforge-steward",
        "dream": "pyforge-steward",
        "owner": "steward",
        "stages": {
          "dream": "2026-07-23",
          "deck": "2026-07-23",
          "spec": "2026-07-25",
          "research": "2026-07-25",
          "brief": "2026-07-25",
          "prd": "2026-07-25",
          "ux": "",
          "arch": "2026-07-25",
          "context": "2026-08-01",
          "epics": "2026-07-25",
          "sprint": "2026-07-29",
          "tea": "2026-07-25",
          "gates": "2026-08-01",
          "code": "2026-07-25",
          "verify": "2026-07-25",
          "retro": "2026-08-08"
        },
        "updatedAt": {
          "dream": "2026-08-08",
          "deck": "2026-07-25",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "2026-07-25",
          "prd": "2026-08-01",
          "ux": "",
          "arch": "2026-08-02",
          "context": "2026-08-01",
          "epics": "2026-08-15",
          "sprint": "2026-08-22",
          "tea": "2026-08-21",
          "gates": "2026-08-10",
          "code": "2026-08-21",
          "verify": "2026-08-21",
          "retro": "2026-08-08"
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": false
          },
          "deck": {
            "have": {
              "prototype": true,
              "exec": true,
              "infographic": true,
              "marp": true,
              "standalone": true,
              "pptx": true
            },
            "n": 6,
            "of": 6,
            "missing": []
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "pyforge-steward",
        "noDream": false,
        "unowned": false,
        "backfilled": true,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research",
          "brief",
          "prd",
          "arch",
          "context",
          "epics",
          "sprint",
          "tea",
          "gates",
          "code",
          "verify",
          "retro"
        ],
        "gaps": [],
        "partial": [],
        "staleBy": [
          {
            "kind": "feeds",
            "stage": "research",
            "than": "brief",
            "at": "2026-08-08",
            "other": "2026-07-25"
          },
          {
            "kind": "feeds",
            "stage": "spec",
            "than": "prd",
            "at": "2026-08-22T05:39",
            "other": "2026-08-01"
          },
          {
            "kind": "feeds",
            "stage": "code",
            "than": "retro",
            "at": "2026-08-21",
            "other": "2026-08-08"
          }
        ],
        "furthest": "retro",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "0.1.0",
        "progress": "53/74",
        "complete": 14,
        "of": 14
      },
      {
        "label": "warden",
        "slug": "pyforge-warden",
        "project": "pyforge-warden",
        "dream": "pyforge-warden",
        "owner": "warden",
        "stages": {
          "dream": "2026-07-23",
          "deck": "2026-07-14",
          "spec": "2026-07-25",
          "research": "2026-07-25",
          "brief": "2026-07-25",
          "prd": "2026-07-14",
          "ux": "",
          "arch": "2026-07-14",
          "context": "2026-08-01",
          "epics": "2026-07-14",
          "sprint": "2026-07-29",
          "tea": "2026-07-14",
          "gates": "2026-07-11",
          "code": "2026-07-14",
          "verify": "2026-07-14",
          "retro": "2026-07-17"
        },
        "updatedAt": {
          "dream": "2026-07-25",
          "deck": "2026-07-24",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "2026-07-25",
          "prd": "2026-08-01",
          "ux": "",
          "arch": "2026-08-02",
          "context": "2026-08-01",
          "epics": "2026-08-02",
          "sprint": "2026-08-22",
          "tea": "2026-08-22",
          "gates": "2026-08-10",
          "code": "2026-08-12",
          "verify": "2026-08-12",
          "retro": "2026-08-08"
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": false
          },
          "deck": {
            "have": {
              "prototype": true,
              "exec": true,
              "infographic": true,
              "marp": true,
              "standalone": true,
              "pptx": true
            },
            "n": 6,
            "of": 6,
            "missing": []
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "pyforge-warden",
        "noDream": false,
        "unowned": false,
        "backfilled": true,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research",
          "brief",
          "prd",
          "arch",
          "context",
          "epics",
          "sprint",
          "tea",
          "gates",
          "code",
          "verify",
          "retro"
        ],
        "gaps": [],
        "partial": [],
        "staleBy": [
          {
            "kind": "feeds",
            "stage": "research",
            "than": "brief",
            "at": "2026-08-08",
            "other": "2026-07-25"
          },
          {
            "kind": "feeds",
            "stage": "spec",
            "than": "prd",
            "at": "2026-08-22T05:39",
            "other": "2026-08-01"
          },
          {
            "kind": "feeds",
            "stage": "code",
            "than": "retro",
            "at": "2026-08-12",
            "other": "2026-08-08"
          }
        ],
        "furthest": "retro",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "0.1.0",
        "progress": "33/36",
        "complete": 14,
        "of": 14
      },
      {
        "label": "artifactory-download-intelligence",
        "slug": "artifactory-download-intelligence",
        "project": "pyforge-atlas",
        "dream": "artifactory-download-intelligence",
        "owner": "atlas",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-14",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "artifactory-download-intelligence",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 2,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "atlas-query-dashboards",
        "slug": "atlas-query-dashboards",
        "project": "pyforge-atlas",
        "dream": "atlas-query-dashboards",
        "owner": "atlas",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-14",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "atlas-query-dashboards",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 3,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "conda-forge-packaging-inventory-operations",
        "slug": "conda-forge-packaging-inventory-operations",
        "project": "pyforge-atlas",
        "dream": "conda-forge-packaging-inventory-operations",
        "owner": "atlas",
        "stages": {
          "dream": "2026-08-16",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T20:15",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "conda-forge-packaging-inventory-operations",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "enterprise-data-models-and-apis",
        "slug": "enterprise-data-models-and-apis",
        "project": "pyforge-atlas",
        "dream": "enterprise-data-models-and-apis",
        "owner": "atlas",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:51",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "enterprise-data-models-and-apis",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "kedro-org-tooling-adoption",
        "slug": "kedro-org-tooling-adoption",
        "project": "pyforge-atlas",
        "dream": "kedro-org-tooling-adoption",
        "owner": "atlas",
        "stages": {
          "dream": "2026-08-07",
          "deck": "",
          "spec": "2026-08-08",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-10",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "kedro-org-tooling-adoption",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 4,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "microsoft-org-sweep",
        "slug": "microsoft-org-sweep",
        "project": "pyforge-atlas",
        "dream": "microsoft-org-sweep",
        "owner": "atlas",
        "stages": {
          "dream": "2026-07-25",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-07-25",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "microsoft-org-sweep",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "atlas-intelligence-platform",
        "slug": "pyforge-atlas-intelligence-platform",
        "project": "pyforge-atlas",
        "dream": "pyforge-atlas-intelligence-platform",
        "owner": "atlas",
        "stages": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-02",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "pyforge-atlas-intelligence-platform",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "unity",
        "slug": "unity-data-stack",
        "project": "pyforge-atlas",
        "dream": "unity-data-stack",
        "owner": "atlas",
        "stages": {
          "dream": "2026-07-23",
          "deck": "2026-07-25",
          "spec": "",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "2026-07-25",
          "spec": "",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": true,
              "exec": true,
              "infographic": true,
              "marp": true,
              "standalone": true,
              "pptx": true
            },
            "n": 6,
            "of": 6,
            "missing": []
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "epics"
        ],
        "required": [
          "dream",
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "spec"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 3,
        "of": 4
      },
      {
        "label": "upstream-discovery",
        "slug": "upstream-discovery",
        "project": "pyforge-atlas",
        "dream": "upstream-discovery",
        "owner": "atlas",
        "stages": {
          "dream": "2026-07-23",
          "deck": "",
          "spec": "2026-07-25",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "upstream-discovery",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 6,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "wagtail-corporate-brain",
        "slug": "wagtail-corporate-brain",
        "project": "pyforge-atlas",
        "dream": "wagtail-corporate-brain",
        "owner": "atlas",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-14",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "wagtail-corporate-brain",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "wasm",
        "slug": "wasm-analytics-stack",
        "project": "pyforge-atlas",
        "dream": "wasm-analytics-stack",
        "owner": "atlas",
        "stages": {
          "dream": "2026-07-23",
          "deck": "2026-07-25",
          "spec": "",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "2026-07-25",
          "spec": "",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": true,
              "exec": true,
              "infographic": true,
              "marp": true,
              "standalone": true,
              "pptx": true
            },
            "n": 6,
            "of": 6,
            "missing": []
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "epics"
        ],
        "required": [
          "dream",
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "spec"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 3,
        "of": 4
      },
      {
        "label": "backlog-intake-check",
        "slug": "backlog-intake-check",
        "project": "pyforge-doctor",
        "dream": "backlog-intake-check",
        "owner": "doctor",
        "stages": {
          "dream": "",
          "deck": "",
          "spec": "2026-08-21",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "",
        "ownerDream": "deferred-work-resolution-sweep",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "bmad-drift-new-artifact-shape",
        "slug": "bmad-drift-new-artifact-shape",
        "project": "pyforge-doctor",
        "dream": "bmad-drift-new-artifact-shape",
        "owner": "doctor",
        "stages": {
          "dream": "2026-08-11",
          "deck": "",
          "spec": "2026-08-11",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "bmad-drift-new-artifact-shape",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "bmad-method-version-drift",
        "slug": "bmad-method-version-drift",
        "project": "pyforge-doctor",
        "dream": "bmad-method-version-drift",
        "owner": "doctor",
        "stages": {
          "dream": "2026-08-15",
          "deck": "",
          "spec": "2026-08-15",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-21",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "bmad-method-version-drift",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "deferred-work-audit-completeness",
        "slug": "deferred-work-audit-completeness",
        "project": "pyforge-doctor",
        "dream": "deferred-work-audit-completeness",
        "owner": "doctor",
        "stages": {
          "dream": "2026-08-15",
          "deck": "",
          "spec": "",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-15",
          "deck": "",
          "spec": "",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "ux"
        ],
        "required": [
          "dream",
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck",
          "spec"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 4
      },
      {
        "label": "deferred-work-resolution-sweep",
        "slug": "deferred-work-resolution-sweep",
        "project": "pyforge-doctor",
        "dream": "deferred-work-resolution-sweep",
        "owner": "doctor",
        "stages": {
          "dream": "2026-08-15",
          "deck": "",
          "spec": "2026-08-15",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-15",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "dreamt",
        "ownerDream": "deferred-work-resolution-sweep",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "deferred-work-visibility",
        "slug": "deferred-work-visibility",
        "project": "pyforge-doctor",
        "dream": "deferred-work-visibility",
        "owner": "doctor",
        "stages": {
          "dream": "2026-08-10",
          "deck": "",
          "spec": "2026-08-10",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-10",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "deferred-work-visibility",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 1,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "fleet-hygiene-verification-exemplar-program",
        "slug": "fleet-hygiene-verification-exemplar-program",
        "project": "pyforge-doctor",
        "dream": "fleet-hygiene-verification-exemplar-program",
        "owner": "doctor",
        "stages": {
          "dream": "2026-08-15",
          "deck": "",
          "spec": "2026-08-15",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-15",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "dreamt",
        "ownerDream": "fleet-hygiene-verification-exemplar-program",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "doctor-dependency-health",
        "slug": "pyforge-doctor-dependency-health",
        "project": "pyforge-doctor",
        "dream": "pyforge-doctor-dependency-health",
        "owner": "doctor",
        "stages": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-02",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "pyforge-doctor-dependency-health",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "sibling-dreams-drift",
        "slug": "sibling-dreams-drift",
        "project": "pyforge-doctor",
        "dream": "sibling-dreams-drift",
        "owner": "doctor",
        "stages": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:17",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "sibling-dreams-drift",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "charter",
        "slug": "pyforge-charter",
        "project": "docs/governance",
        "dream": "pyforge-charter",
        "owner": "guild",
        "stages": {
          "dream": "2026-07-25",
          "deck": "",
          "spec": "2026-08-02",
          "research": "",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-08",
          "deck": "",
          "spec": "2026-08-08",
          "research": "",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": false,
              "market": false,
              "technical": false
            },
            "n": 0,
            "of": 3,
            "missing": [
              "domain",
              "market",
              "technical"
            ],
            "inherited": false
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "pitched",
        "ownerDream": "pyforge-charter",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "brief",
          "context",
          "dream",
          "research",
          "ux"
        ],
        "required": [
          "deck",
          "spec"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "spec",
        "updated": "2026-08-08",
        "age": 14,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 1,
        "of": 2
      },
      {
        "label": "deck-visual-qa",
        "slug": "deck-visual-qa",
        "project": "pyforge-herald",
        "dream": "deck-visual-qa",
        "owner": "herald",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-14",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "deck-visual-qa",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 2,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "herald-moments-2-4-live-backend",
        "slug": "herald-moments-2-4-live-backend",
        "project": "pyforge-herald",
        "dream": "herald-moments-2-4-live-backend",
        "owner": "herald",
        "stages": {
          "dream": "2026-08-08",
          "deck": "",
          "spec": "2026-08-08",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-10",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "herald-moments-2-4-live-backend",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 3,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "herald-moments-2-4-missing-surface",
        "slug": "herald-moments-2-4-missing-surface",
        "project": "pyforge-herald",
        "dream": "herald-moments-2-4-missing-surface",
        "owner": "herald",
        "stages": {
          "dream": "2026-08-01",
          "deck": "",
          "spec": "2026-08-02",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "herald-moments-2-4-missing-surface",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "herald-pitch",
        "slug": "herald-pitch",
        "project": "pyforge-herald",
        "dream": "herald-pitch",
        "owner": "herald",
        "stages": {
          "dream": "2026-08-01",
          "deck": "",
          "spec": "",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "ux"
        ],
        "required": [
          "dream",
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck",
          "spec"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 4
      },
      {
        "label": "pptx-custom-shapes",
        "slug": "pptx-custom-shapes",
        "project": "pyforge-herald",
        "dream": "pptx-custom-shapes",
        "owner": "herald",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:41",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "pptx-custom-shapes",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "pptx-deck-generation",
        "slug": "pptx-deck-generation",
        "project": "pyforge-herald",
        "dream": "pptx-deck-generation",
        "owner": "herald",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:41",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "pptx-deck-generation",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 1,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "adaptive-model-tiering",
        "slug": "adaptive-model-tiering",
        "project": "pyforge-marshal",
        "dream": "adaptive-model-tiering",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-11",
          "deck": "",
          "spec": "2026-08-11",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T07:48",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "adaptive-model-tiering",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 3,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "agent-portability",
        "slug": "agent-portability",
        "project": "pyforge-marshal",
        "dream": "agent-portability",
        "owner": "marshal",
        "stages": {
          "dream": "2026-07-23",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": false
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "agent-portability",
        "noDream": false,
        "unowned": false,
        "backfilled": true,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "agent-tool-surface",
        "slug": "agent-tool-surface",
        "project": "pyforge-marshal",
        "dream": "agent-tool-surface",
        "owner": "marshal",
        "stages": {
          "dream": "2026-07-25",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-07-29",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "agent-tool-surface",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 1,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "agentic-sdlc-autonomy",
        "slug": "agentic-sdlc-autonomy",
        "project": "pyforge-marshal",
        "dream": "agentic-sdlc-autonomy",
        "owner": "marshal",
        "stages": {
          "dream": "2026-07-23",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-21",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "agentic-sdlc-autonomy",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "artifact-chain-reconciliation",
        "slug": "artifact-chain-reconciliation",
        "project": "pyforge-marshal",
        "dream": "artifact-chain-reconciliation",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-10",
          "deck": "",
          "spec": "2026-08-10",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-10",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "artifact-chain-reconciliation",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 2,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "artifact-console",
        "slug": "artifact-console",
        "project": "pyforge-marshal",
        "dream": "artifact-console",
        "owner": "marshal",
        "stages": {
          "dream": "2026-07-25",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-07-25",
          "deck": "",
          "spec": "2026-08-22T05:38",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "artifact-console",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "bmad-611-era-alignment",
        "slug": "bmad-611-era-alignment",
        "project": "pyforge-marshal",
        "dream": "bmad-611-era-alignment",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T09:13",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "bmad-611-era-alignment",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 1,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "bmad-loop-baseline-drift",
        "slug": "bmad-loop-baseline-drift",
        "project": "pyforge-marshal",
        "dream": "bmad-loop-baseline-drift",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-14",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "bmad-loop-baseline-drift",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 3,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "bmad-loop-forward-dependency-blindness",
        "slug": "bmad-loop-forward-dependency-blindness",
        "project": "pyforge-marshal",
        "dream": "bmad-loop-forward-dependency-blindness",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-03",
          "deck": "",
          "spec": "2026-08-08",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-08",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "bmad-loop-forward-dependency-blindness",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "bmad-loop-governance",
        "slug": "bmad-loop-governance",
        "project": "pyforge-marshal",
        "dream": "bmad-loop-governance",
        "owner": "marshal",
        "stages": {
          "dream": "",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "",
          "deck": "",
          "spec": "2026-08-22T09:13",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "",
        "ownerDream": "pyforge-marshal",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "bmad-loop-intent-gap-work-preservation",
        "slug": "bmad-loop-intent-gap-work-preservation",
        "project": "pyforge-marshal",
        "dream": "bmad-loop-intent-gap-work-preservation",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-14",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T07:48",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "bmad-loop-intent-gap-work-preservation",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 2,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "bmad-loop-liveness-footgun",
        "slug": "bmad-loop-liveness-footgun",
        "project": "pyforge-marshal",
        "dream": "bmad-loop-liveness-footgun",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-21",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-21",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "bmad-loop-liveness-footgun",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 3,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "bmad-output-hygiene",
        "slug": "bmad-output-hygiene",
        "project": "pyforge-marshal",
        "dream": "bmad-output-hygiene",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-02",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-08",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "bmad-output-hygiene",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "bmad-switch-scope-enforcement",
        "slug": "bmad-switch-scope-enforcement",
        "project": "pyforge-marshal",
        "dream": "bmad-switch-scope-enforcement",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-14",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "bmad-switch-scope-enforcement",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 2,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "dashboard-project-path-derivation",
        "slug": "dashboard-project-path-derivation",
        "project": "pyforge-marshal",
        "dream": "dashboard-project-path-derivation",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-08",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-08",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "dashboard-project-path-derivation",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 3,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "dashboard-velocity-captures-hand-driven-work",
        "slug": "dashboard-velocity-captures-hand-driven-work",
        "project": "pyforge-marshal",
        "dream": "dashboard-velocity-captures-hand-driven-work",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-15",
          "deck": "",
          "spec": "2026-08-21",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-21",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "dashboard-velocity-captures-hand-driven-work",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 4,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "dream-to-code-model-self-verification",
        "slug": "dream-to-code-model-self-verification",
        "project": "pyforge-marshal",
        "dream": "dream-to-code-model-self-verification",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-03",
          "deck": "",
          "spec": "2026-08-08",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-08",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "dream-to-code-model-self-verification",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 3,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "durable-runs",
        "slug": "durable-runs",
        "project": "pyforge-marshal",
        "dream": "durable-runs",
        "owner": "marshal",
        "stages": {
          "dream": "2026-07-31",
          "deck": "",
          "spec": "2026-08-01",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-09",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "durable-runs",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "factory-console",
        "slug": "factory-console",
        "project": "pyforge-marshal",
        "dream": "factory-console",
        "owner": "marshal",
        "stages": {
          "dream": "2026-07-23",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-09",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "factory-console",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "fidelity-enforcement",
        "slug": "fidelity-enforcement",
        "project": "pyforge-marshal",
        "dream": "fidelity-enforcement",
        "owner": "marshal",
        "stages": {
          "dream": "2026-07-31",
          "deck": "",
          "spec": "2026-08-01",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "fidelity-enforcement",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "fleet-chain-completeness",
        "slug": "fleet-chain-completeness",
        "project": "pyforge-marshal",
        "dream": "fleet-chain-completeness",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-01",
          "deck": "",
          "spec": "2026-08-02",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "fleet-chain-completeness",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 4,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "fleet-status-supervisor-fallback",
        "slug": "fleet-status-supervisor-fallback",
        "project": "pyforge-marshal",
        "dream": "fleet-status-supervisor-fallback",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-11",
          "deck": "",
          "spec": "2026-08-11",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "fleet-status-supervisor-fallback",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 1,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "genesis-installer",
        "slug": "genesis-installer",
        "project": "pyforge-marshal",
        "dream": "genesis-installer",
        "owner": "marshal",
        "stages": {
          "dream": "2026-07-29",
          "deck": "",
          "spec": "",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "ux"
        ],
        "required": [
          "dream",
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck",
          "spec"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 4
      },
      {
        "label": "genesis-installer-name-retirement",
        "slug": "genesis-installer-name-retirement",
        "project": "pyforge-marshal",
        "dream": "genesis-installer-name-retirement",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-02",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-08",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "genesis-installer-name-retirement",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 3,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "horizontal-run-concurrency",
        "slug": "horizontal-run-concurrency",
        "project": "pyforge-marshal",
        "dream": "horizontal-run-concurrency",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-11",
          "deck": "",
          "spec": "2026-08-11",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T07:48",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "horizontal-run-concurrency",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 2,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "landing-evidence-grammar",
        "slug": "landing-evidence-grammar",
        "project": "pyforge-marshal",
        "dream": "landing-evidence-grammar",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-14",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "landing-evidence-grammar",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 2,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "loop-home-fleet-refresh",
        "slug": "loop-home-fleet-refresh",
        "project": "pyforge-marshal",
        "dream": "loop-home-fleet-refresh",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-03",
          "deck": "",
          "spec": "2026-08-08",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-08",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "loop-home-fleet-refresh",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 3,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "marshal-land-cross-project-story-key-collision",
        "slug": "marshal-land-cross-project-story-key-collision",
        "project": "pyforge-marshal",
        "dream": "marshal-land-cross-project-story-key-collision",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-15",
          "deck": "",
          "spec": "2026-08-15",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-21",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "marshal-land-cross-project-story-key-collision",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "marshal-land-merge-subject",
        "slug": "marshal-land-merge-subject",
        "project": "pyforge-marshal",
        "dream": "marshal-land-merge-subject",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-12",
          "deck": "",
          "spec": "2026-08-12",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "marshal-land-merge-subject",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "marshal-single-story-dispatch",
        "slug": "marshal-single-story-dispatch",
        "project": "pyforge-marshal",
        "dream": "marshal-single-story-dispatch",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-21",
          "deck": "",
          "spec": "2026-08-21",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-21",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "marshal-single-story-dispatch",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 5,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "marshal-status-harness-run-id-poisoning",
        "slug": "marshal-status-harness-run-id-poisoning",
        "project": "pyforge-marshal",
        "dream": "marshal-status-harness-run-id-poisoning",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-15",
          "deck": "",
          "spec": "2026-08-15",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-21",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "marshal-status-harness-run-id-poisoning",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "multi-loop-isolation",
        "slug": "multi-loop-isolation",
        "project": "pyforge-marshal",
        "dream": "multi-loop-isolation",
        "owner": "marshal",
        "stages": {
          "dream": "",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "",
        "ownerDream": "pyforge-marshal",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "one-front-door",
        "slug": "one-front-door",
        "project": "pyforge-marshal",
        "dream": "one-front-door",
        "owner": "marshal",
        "stages": {
          "dream": "2026-07-31",
          "deck": "",
          "spec": "2026-08-01",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "one-front-door",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 1,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "pr-lifecycle",
        "slug": "pr-lifecycle",
        "project": "pyforge-marshal",
        "dream": "pr-lifecycle",
        "owner": "marshal",
        "stages": {
          "dream": "2026-07-31",
          "deck": "",
          "spec": "2026-08-01",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-09",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "pr-lifecycle",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "core",
        "slug": "pyforge-core",
        "project": "pyforge-marshal",
        "dream": "pyforge-core",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-08",
          "deck": "",
          "spec": "2026-08-08",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "2026-08-12",
          "gates": "",
          "code": "2026-08-12",
          "verify": "2026-08-12",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-08",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "2026-08-13",
          "gates": "",
          "code": "2026-08-12",
          "verify": "2026-08-12",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "pyforge-core",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 3,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research",
          "brief",
          "prd",
          "arch",
          "context",
          "epics",
          "sprint",
          "tea",
          "gates",
          "code",
          "verify"
        ],
        "gaps": [
          "deck",
          "brief",
          "prd",
          "arch",
          "context",
          "epics",
          "sprint",
          "gates"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "verify",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 5,
        "of": 13
      },
      {
        "label": "marshal-loop-orchestrator",
        "slug": "pyforge-marshal-loop-orchestrator",
        "project": "pyforge-marshal",
        "dream": "pyforge-marshal-loop-orchestrator",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-02",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "pyforge-marshal-loop-orchestrator",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "testing-charter",
        "slug": "pyforge-testing-charter",
        "project": "pyforge-marshal",
        "dream": "pyforge-testing-charter",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-02",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "pyforge-testing-charter",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "quick-dev-reconciliation",
        "slug": "quick-dev-reconciliation",
        "project": "pyforge-marshal",
        "dream": "quick-dev-reconciliation",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-11",
          "deck": "",
          "spec": "2026-08-11",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "quick-dev-reconciliation",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 1,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "regenerable-factory",
        "slug": "regenerable-factory",
        "project": "pyforge-marshal",
        "dream": "regenerable-factory",
        "owner": "marshal",
        "stages": {
          "dream": "2026-07-23",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "2026-07-25",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-07-25",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "2026-07-25",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "regenerable-factory",
        "noDream": false,
        "unowned": false,
        "backfilled": true,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "arch",
          "brief",
          "context",
          "dream",
          "prd",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research",
          "epics"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "epics",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 3,
        "of": 4
      },
      {
        "label": "risk-tiered-review-depth",
        "slug": "risk-tiered-review-depth",
        "project": "pyforge-marshal",
        "dream": "risk-tiered-review-depth",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-11",
          "deck": "",
          "spec": "2026-08-11",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "risk-tiered-review-depth",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "sprint-status-auto-promote",
        "slug": "sprint-status-auto-promote",
        "project": "pyforge-marshal",
        "dream": "sprint-status-auto-promote",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-03",
          "deck": "",
          "spec": "2026-08-08",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-08",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "sprint-status-auto-promote",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 3,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "surface-drift-reconciliation",
        "slug": "surface-drift-reconciliation",
        "project": "pyforge-marshal",
        "dream": "surface-drift-reconciliation",
        "owner": "marshal",
        "stages": {
          "dream": "2026-08-08",
          "deck": "",
          "spec": "2026-08-08",
          "research": "2026-07-16",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-09",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "surface-drift-reconciliation",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 2,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "conda-forge-expert-rebuild",
        "slug": "conda-forge-expert-rebuild",
        "project": "pyforge-mason",
        "dream": "conda-forge-expert-rebuild",
        "owner": "mason",
        "stages": {
          "dream": "2026-08-07",
          "deck": "",
          "spec": "2026-08-08",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-10",
          "deck": "",
          "spec": "2026-08-22T09:13",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "conda-forge-expert-rebuild",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "copilot-cli-packaging",
        "slug": "copilot-cli-packaging",
        "project": "pyforge-mason",
        "dream": "copilot-cli-packaging",
        "owner": "mason",
        "stages": {
          "dream": "2026-07-25",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-07-25",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "copilot-cli-packaging",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "db-gpt-packaging",
        "slug": "db-gpt-packaging",
        "project": "pyforge-mason",
        "dream": "db-gpt-packaging",
        "owner": "mason",
        "stages": {
          "dream": "2026-07-25",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-07-25",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "db-gpt-packaging",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "django-accelerator-framework",
        "slug": "django-accelerator-framework",
        "project": "pyforge-mason",
        "dream": "django-accelerator-framework",
        "owner": "mason",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-14",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "django-accelerator-framework",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 1,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "fleet-stewardship",
        "slug": "fleet-stewardship",
        "project": "pyforge-mason",
        "dream": "fleet-stewardship",
        "owner": "mason",
        "stages": {
          "dream": "2026-07-23",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-07-25",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "fleet-stewardship",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "machine-checked-recipe-knowledge",
        "slug": "machine-checked-recipe-knowledge",
        "project": "pyforge-mason",
        "dream": "machine-checked-recipe-knowledge",
        "owner": "mason",
        "stages": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:34",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "machine-checked-recipe-knowledge",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 1,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "miniforge-installer",
        "slug": "miniforge-installer",
        "project": "pyforge-mason",
        "dream": "miniforge-installer",
        "owner": "mason",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:51",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "miniforge-installer",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "packaging-factory",
        "slug": "packaging-factory",
        "project": "pyforge-mason",
        "dream": "packaging-factory",
        "owner": "mason",
        "stages": {
          "dream": "2026-07-23",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-07-25",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "packaging-factory",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "pixi-container-image",
        "slug": "pixi-container-image",
        "project": "pyforge-mason",
        "dream": "pixi-container-image",
        "owner": "mason",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:34",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "pixi-container-image",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "presenton",
        "slug": "presenton-pixi-image",
        "project": "pyforge-mason",
        "dream": "presenton-pixi-image",
        "owner": "mason",
        "stages": {
          "dream": "2026-07-23",
          "deck": "2026-07-25",
          "spec": "",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "2026-07-29",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "2026-07-25",
          "spec": "",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "2026-08-08",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": true,
              "exec": true,
              "infographic": true,
              "marp": true,
              "standalone": true,
              "pptx": true
            },
            "n": 6,
            "of": 6,
            "missing": []
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [],
        "required": [
          "dream",
          "deck",
          "spec",
          "research",
          "brief",
          "prd",
          "ux",
          "arch",
          "context",
          "epics"
        ],
        "gaps": [
          "spec",
          "brief",
          "prd",
          "ux",
          "arch",
          "context"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "epics",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 4,
        "of": 10
      },
      {
        "label": "mason-recipe-validator",
        "slug": "pyforge-mason-recipe-validator",
        "project": "pyforge-mason",
        "dream": "pyforge-mason-recipe-validator",
        "owner": "mason",
        "stages": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-02",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "pyforge-mason-recipe-validator",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "reusable-cicd-workflows",
        "slug": "reusable-cicd-workflows",
        "project": "pyforge-mason",
        "dream": "reusable-cicd-workflows",
        "owner": "mason",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:51",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "reusable-cicd-workflows",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "scribe-team-memory",
        "slug": "pyforge-scribe-team-memory",
        "project": "pyforge-scribe",
        "dream": "pyforge-scribe-team-memory",
        "owner": "scribe",
        "stages": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-02",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "pyforge-scribe-team-memory",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "scribe-mines-raw-session-transcripts",
        "slug": "scribe-mines-raw-session-transcripts",
        "project": "pyforge-scribe",
        "dream": "scribe-mines-raw-session-transcripts",
        "owner": "scribe",
        "stages": {
          "dream": "2026-08-15",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:35",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "scribe-mines-raw-session-transcripts",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 1,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "sentinel",
        "slug": "sentinel",
        "project": "pyforge-scribe",
        "dream": "sentinel",
        "owner": "scribe",
        "stages": {
          "dream": "2026-07-23",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-07-25",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "sentinel",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "team-memory",
        "slug": "team-memory",
        "project": "pyforge-scribe",
        "dream": "team-memory",
        "owner": "scribe",
        "stages": {
          "dream": "2026-07-23",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": false
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "team-memory",
        "noDream": false,
        "unowned": false,
        "backfilled": true,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "asgi-multiplexer-monolith",
        "slug": "asgi-multiplexer-monolith",
        "project": "pyforge-steward",
        "dream": "asgi-multiplexer-monolith",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-13",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:06",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "absorbed",
        "ownerDream": "asgi-multiplexer-monolith",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "bmad-method-core-upgrade",
        "slug": "bmad-method-core-upgrade",
        "project": "pyforge-steward",
        "dream": "bmad-method-core-upgrade",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-15",
          "deck": "",
          "spec": "2026-08-21",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-21",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "bmad-method-core-upgrade",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 3,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "bmad-module-provisioning",
        "slug": "bmad-module-provisioning",
        "project": "pyforge-steward",
        "dream": "bmad-module-provisioning",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-07",
          "deck": "",
          "spec": "2026-08-08",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-15",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "bmad-module-provisioning",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 3,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "bmad-suite-channel-product",
        "slug": "bmad-suite-channel-product",
        "project": "pyforge-steward",
        "dream": "bmad-suite-channel-product",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T06:20",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "bmad-suite-channel-product",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 1,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "db-gpt-django-plugin",
        "slug": "db-gpt-django-plugin",
        "project": "pyforge-steward",
        "dream": "db-gpt-django-plugin",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-13",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:06",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "absorbed",
        "ownerDream": "db-gpt-django-plugin",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "developer-machine-bootstrap",
        "slug": "developer-machine-bootstrap",
        "project": "pyforge-steward",
        "dream": "developer-machine-bootstrap",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:16",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "developer-machine-bootstrap",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 1,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "enterprise-airgap",
        "slug": "enterprise-airgap",
        "project": "pyforge-steward",
        "dream": "enterprise-airgap",
        "owner": "steward",
        "stages": {
          "dream": "2026-07-23",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-07-31",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "enterprise-airgap",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "enterprise-multi-agent-orchestration",
        "slug": "enterprise-multi-agent-orchestration",
        "project": "pyforge-steward",
        "dream": "enterprise-multi-agent-orchestration",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-13",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:06",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "absorbed",
        "ownerDream": "enterprise-multi-agent-orchestration",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "jira-github-projects-sync",
        "slug": "jira-github-projects-sync",
        "project": "pyforge-steward",
        "dream": "jira-github-projects-sync",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-03",
          "deck": "",
          "spec": "2026-08-08",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "2026-08-09",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-10",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "2026-08-10",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "jira-github-projects-sync",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research",
          "brief",
          "prd",
          "arch"
        ],
        "gaps": [
          "deck",
          "brief",
          "prd"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "arch",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 3,
        "of": 6
      },
      {
        "label": "langflow-django-plugin",
        "slug": "langflow-django-plugin",
        "project": "pyforge-steward",
        "dream": "langflow-django-plugin",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-13",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:06",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "absorbed",
        "ownerDream": "langflow-django-plugin",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "local-ocp-hybrid-environment",
        "slug": "local-ocp-hybrid-environment",
        "project": "pyforge-steward",
        "dream": "local-ocp-hybrid-environment",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:05",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "local-ocp-hybrid-environment",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "multi-repo-workspaces",
        "slug": "multi-repo-workspaces",
        "project": "pyforge-steward",
        "dream": "multi-repo-workspaces",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:17",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "multi-repo-workspaces",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 1,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "platform-fifteen-factors",
        "slug": "platform-fifteen-factors",
        "project": "pyforge-steward",
        "dream": "platform-fifteen-factors",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:16",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "platform-fifteen-factors",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 1,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "steward-feedstock-maintenance",
        "slug": "pyforge-steward-feedstock-maintenance",
        "project": "pyforge-steward",
        "dream": "pyforge-steward-feedstock-maintenance",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-02",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "pyforge-steward-feedstock-maintenance",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "python-agent-platform",
        "slug": "python-agent-platform",
        "project": "pyforge-steward",
        "dream": "python-agent-platform",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-14",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-21",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "python-agent-platform",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "scratch-worktree-lifecycle",
        "slug": "scratch-worktree-lifecycle",
        "project": "pyforge-steward",
        "dream": "scratch-worktree-lifecycle",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-14",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "scratch-worktree-lifecycle",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 2,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "secure-live-dashboards",
        "slug": "secure-live-dashboards",
        "project": "pyforge-steward",
        "dream": "secure-live-dashboards",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-09",
          "deck": "",
          "spec": "2026-08-09",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "2026-08-09",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-10",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "2026-08-09",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "secure-live-dashboards",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research",
          "brief",
          "prd",
          "arch"
        ],
        "gaps": [
          "deck",
          "brief",
          "prd"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "arch",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 3,
        "of": 6
      },
      {
        "label": "unified-container",
        "slug": "unified-container",
        "project": "pyforge-steward",
        "dream": "unified-container",
        "owner": "steward",
        "stages": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-08",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "2026-08-09",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-10",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "2026-08-09",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "realized",
        "ownerDream": "unified-container",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 4,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research",
          "brief",
          "prd",
          "arch"
        ],
        "gaps": [
          "deck",
          "brief",
          "prd"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "arch",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 3,
        "of": 6
      },
      {
        "label": "compliance-factory-web-face",
        "slug": "compliance-factory-web-face",
        "project": "pyforge-warden",
        "dream": "compliance-factory-web-face",
        "owner": "warden",
        "stages": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:34",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "compliance-factory-web-face",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 1,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "package-inventory-eligibility",
        "slug": "package-inventory-eligibility",
        "project": "pyforge-warden",
        "dream": "package-inventory-eligibility",
        "owner": "warden",
        "stages": {
          "dream": "2026-08-14",
          "deck": "",
          "spec": "2026-08-22",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-22",
          "deck": "",
          "spec": "2026-08-22T07:34",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": false,
        "dreamStatus": "specified",
        "ownerDream": "package-inventory-eligibility",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 1,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      },
      {
        "label": "warden-compliance-gates",
        "slug": "pyforge-warden-compliance-gates",
        "project": "pyforge-warden",
        "dream": "pyforge-warden-compliance-gates",
        "owner": "warden",
        "stages": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-02",
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-22T05:39",
          "research": "2026-08-08",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "",
          "sprint": "",
          "tea": "",
          "gates": "",
          "code": "",
          "verify": "",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": true
            },
            "n": 3,
            "of": 3,
            "missing": [],
            "inherited": true
          },
          "deck": {
            "have": {
              "prototype": false,
              "exec": false,
              "infographic": false,
              "marp": false,
              "standalone": false,
              "pptx": false
            },
            "n": 0,
            "of": 6,
            "missing": [
              "exec",
              "infographic",
              "marp",
              "pptx",
              "prototype",
              "standalone"
            ]
          }
        },
        "archived": true,
        "dreamStatus": "archived",
        "ownerDream": "pyforge-warden-compliance-gates",
        "noDream": false,
        "unowned": false,
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "dream",
          "ux"
        ],
        "required": [
          "deck",
          "spec",
          "research"
        ],
        "gaps": [
          "deck"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-22",
        "age": 0,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
      }
    ]
  },
  "commandCenter": {
    "phases": [
      {
        "id": "analysis",
        "name": "ANALYSIS Phase",
        "flow": "Dream → Pitch deck",
        "artifacts": [
          "DREAMS",
          "res-domain",
          "res-market",
          "res-tech",
          "prod-brief",
          "PITCH-DECKS"
        ],
        "gate": "All 8 stations complete analysis",
        "stations": [
          {
            "name": "Herald",
            "emoji": "🎺",
            "statuses": {
              "DREAMS": "🚀",
              "res-domain": "✅",
              "res-market": "✅",
              "res-tech": "✅",
              "prod-brief": "✅",
              "PITCH-DECKS": "✅"
            }
          },
          {
            "name": "Marshal",
            "emoji": "⚔️",
            "statuses": {
              "DREAMS": "🚀",
              "res-domain": "✅",
              "res-market": "✅",
              "res-tech": "✅",
              "prod-brief": "✅",
              "PITCH-DECKS": "✅"
            }
          },
          {
            "name": "Atlas",
            "emoji": "🗺️",
            "statuses": {
              "DREAMS": "🚀",
              "res-domain": "✅",
              "res-market": "✅",
              "res-tech": "✅",
              "prod-brief": "✅",
              "PITCH-DECKS": "✅"
            }
          },
          {
            "name": "Warden",
            "emoji": "🛡️",
            "statuses": {
              "DREAMS": "🚀",
              "res-domain": "✅",
              "res-market": "✅",
              "res-tech": "✅",
              "prod-brief": "✅",
              "PITCH-DECKS": "✅"
            }
          },
          {
            "name": "Mason",
            "emoji": "🧱",
            "statuses": {
              "DREAMS": "🚀",
              "res-domain": "✅",
              "res-market": "✅",
              "res-tech": "✅",
              "prod-brief": "✅",
              "PITCH-DECKS": "✅"
            }
          },
          {
            "name": "Doctor",
            "emoji": "🏥",
            "statuses": {
              "DREAMS": "🚀",
              "res-domain": "✅",
              "res-market": "✅",
              "res-tech": "✅",
              "prod-brief": "✅",
              "PITCH-DECKS": "✅"
            }
          },
          {
            "name": "Scribe",
            "emoji": "📖",
            "statuses": {
              "DREAMS": "🚀",
              "res-domain": "✅",
              "res-market": "✅",
              "res-tech": "✅",
              "prod-brief": "✅",
              "PITCH-DECKS": "✅"
            }
          },
          {
            "name": "Steward",
            "emoji": "👑",
            "statuses": {
              "DREAMS": "🚀",
              "res-domain": "✅",
              "res-market": "✅",
              "res-tech": "✅",
              "prod-brief": "✅",
              "PITCH-DECKS": "✅"
            }
          }
        ]
      },
      {
        "id": "planning",
        "name": "PLANNING Phase",
        "flow": "PRD requirements",
        "artifacts": [
          "PRD"
        ],
        "gate": "All 8 stations have PRD",
        "stations": [
          {
            "name": "Herald",
            "emoji": "🎺",
            "statuses": {
              "PRD": "✅"
            }
          },
          {
            "name": "Marshal",
            "emoji": "⚔️",
            "statuses": {
              "PRD": "✅"
            }
          },
          {
            "name": "Atlas",
            "emoji": "🗺️",
            "statuses": {
              "PRD": "✅"
            }
          },
          {
            "name": "Warden",
            "emoji": "🛡️",
            "statuses": {
              "PRD": "✅"
            }
          },
          {
            "name": "Mason",
            "emoji": "🧱",
            "statuses": {
              "PRD": "✅"
            }
          },
          {
            "name": "Doctor",
            "emoji": "🏥",
            "statuses": {
              "PRD": "✅"
            }
          },
          {
            "name": "Scribe",
            "emoji": "📖",
            "statuses": {
              "PRD": "✅"
            }
          },
          {
            "name": "Steward",
            "emoji": "👑",
            "statuses": {
              "PRD": "✅"
            }
          }
        ]
      },
      {
        "id": "solutioning",
        "name": "SOLUTIONING Phase",
        "flow": "Architecture → specs",
        "artifacts": [
          "arch",
          "epics",
          "specs"
        ],
        "gate": "All 8 stations complete solutioning",
        "stations": [
          {
            "name": "Herald",
            "emoji": "🎺",
            "statuses": {
              "arch": "✅",
              "epics": "✅",
              "specs": "✅"
            }
          },
          {
            "name": "Marshal",
            "emoji": "⚔️",
            "statuses": {
              "arch": "✅",
              "epics": "✅",
              "specs": "✅"
            }
          },
          {
            "name": "Atlas",
            "emoji": "🗺️",
            "statuses": {
              "arch": "✅",
              "epics": "✅",
              "specs": "✅"
            }
          },
          {
            "name": "Warden",
            "emoji": "🛡️",
            "statuses": {
              "arch": "✅",
              "epics": "✅",
              "specs": "✅"
            }
          },
          {
            "name": "Mason",
            "emoji": "🧱",
            "statuses": {
              "arch": "✅",
              "epics": "✅",
              "specs": "✅"
            }
          },
          {
            "name": "Doctor",
            "emoji": "🏥",
            "statuses": {
              "arch": "✅",
              "epics": "✅",
              "specs": "✅"
            }
          },
          {
            "name": "Scribe",
            "emoji": "📖",
            "statuses": {
              "arch": "✅",
              "epics": "✅",
              "specs": "✅"
            }
          },
          {
            "name": "Steward",
            "emoji": "👑",
            "statuses": {
              "arch": "✅",
              "epics": "✅",
              "specs": "✅"
            }
          }
        ]
      },
      {
        "id": "implementation",
        "name": "IMPLEMENTATION Phase",
        "flow": "Code → ship + retro",
        "artifacts": [
          "sprint-status",
          "code",
          "tests",
          "retro"
        ],
        "gate": "5 complete (atlas, doctor, herald, mason, scribe); 3 building (marshal, steward, warden)",
        "stations": [
          {
            "name": "Herald",
            "emoji": "🎺",
            "statuses": {
              "sprint-status": "✅",
              "code": "✅",
              "tests": "✅",
              "retro": "✅"
            }
          },
          {
            "name": "Marshal",
            "emoji": "⚔️",
            "statuses": {
              "sprint-status": "✅",
              "code": "✅",
              "tests": "✅",
              "retro": "◯"
            }
          },
          {
            "name": "Atlas",
            "emoji": "🗺️",
            "statuses": {
              "sprint-status": "✅",
              "code": "✅",
              "tests": "✅",
              "retro": "✅"
            }
          },
          {
            "name": "Warden",
            "emoji": "🛡️",
            "statuses": {
              "sprint-status": "✅",
              "code": "✅",
              "tests": "✅",
              "retro": "✅"
            }
          },
          {
            "name": "Mason",
            "emoji": "🧱",
            "statuses": {
              "sprint-status": "✅",
              "code": "✅",
              "tests": "✅",
              "retro": "◯"
            }
          },
          {
            "name": "Doctor",
            "emoji": "🏥",
            "statuses": {
              "sprint-status": "✅",
              "code": "✅",
              "tests": "✅",
              "retro": "✅"
            }
          },
          {
            "name": "Scribe",
            "emoji": "📖",
            "statuses": {
              "sprint-status": "✅",
              "code": "✅",
              "tests": "✅",
              "retro": "✅"
            }
          },
          {
            "name": "Steward",
            "emoji": "👑",
            "statuses": {
              "sprint-status": "✅",
              "code": "✅",
              "tests": "✅",
              "retro": "✅"
            }
          }
        ]
      }
    ]
  },
  "health": {
    "detectors": [
      {
        "name": "drift-check",
        "task": "bmad-drift-check",
        "guards": "BMAD artifacts vs the live factory",
        "state": "green",
        "findings": 0,
        "verdict": "",
        "runbook": "_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md"
      },
      {
        "name": "spec-surface",
        "task": "spec-surface-check",
        "guards": "every tracked file under a Spec surface",
        "state": "drift",
        "findings": 0,
        "verdict": "",
        "runbook": ""
      },
      {
        "name": "llms-full",
        "task": "llms-full-check",
        "guards": "library catalog freshness",
        "state": "drift",
        "findings": 51,
        "verdict": "DRIFT: 51 finding(s). Reconcile by regenerating the catalog (prompt in its header), then re-run.",
        "runbook": ""
      }
    ],
    "baseline": {
      "skill": "8.83.0",
      "head": "4708f15c25",
      "deltas": [],
      "runbook": "_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md"
    }
  },
  "backlog": {
    "rows": [
      {
        "slug": "deferred-work-audit-completeness",
        "title": "deferred-work-audit-completeness",
        "status": "specified",
        "owner": "doctor",
        "blockedOn": "",
        "chain": {}
      },
      {
        "slug": "marshal-land-cross-project-story-key-collision",
        "title": "A GitHub PR-merge branch from one project never masquerades as a same-numbered story in another",
        "status": "specified",
        "owner": "marshal",
        "blockedOn": "",
        "chain": {
          "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-land-cross-project-story-key-collision"
        }
      },
      {
        "slug": "marshal-status-harness-run-id-poisoning",
        "title": "A spin-time poll timeout never permanently blinds marshal status to a healthy run",
        "status": "specified",
        "owner": "marshal",
        "blockedOn": "",
        "chain": {
          "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-status-harness-run-id-poisoning"
        }
      },
      {
        "slug": "asgi-multiplexer-monolith",
        "title": "Django, Langflow, and DB-GPT co-locate in one ASGI process without starving each other",
        "status": "absorbed   # 2026-08-22 pointer spec authored (spec-asgi-multiplexer-monolith); realized through python-agent-platform per the 2026-08-14 Realization log",
        "owner": "steward",
        "blockedOn": "",
        "chain": {
          "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-asgi-multiplexer-monolith"
        }
      },
      {
        "slug": "enterprise-data-models-and-apis",
        "title": "A normalized data model and REST API pattern, waiting for a PyForge-native subject",
        "status": "specified   # 2026-08-22 — reframed as an EXTENSION-POINT (operator): the fleet ships the socket/contract; the capability develops separately (incl. air-gapped) — see the spec's Extension contract section",
        "owner": "atlas",
        "blockedOn": "",
        "chain": {
          "spec": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-enterprise-data-models-and-apis"
        }
      },
      {
        "slug": "enterprise-multi-agent-orchestration",
        "title": "Django, Langflow, and DB-GPT scale as isolated containers behind one gateway",
        "status": "absorbed   # 2026-08-22 pointer spec authored (spec-enterprise-multi-agent-orchestration); realized through python-agent-platform per the 2026-08-14 Realization log",
        "owner": "steward",
        "blockedOn": "",
        "chain": {
          "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-enterprise-multi-agent-orchestration"
        }
      }
    ],
    "blocked": 0,
    "byOwner": {
      "doctor": 1,
      "marshal": 2,
      "steward": 2,
      "atlas": 1
    },
    "practices": [
      {
        "slug": "agent-portability",
        "title": "Agent portability — BMAD on any agent, never vendor-locked",
        "owner": "marshal",
        "status": "archived"
      },
      {
        "slug": "agent-tool-surface",
        "title": "Agent tool surface — every craft reachable through one governed API",
        "owner": "marshal",
        "status": "realized"
      },
      {
        "slug": "agentic-sdlc-autonomy",
        "title": "The Agentic SDLC — four views of autonomy, one governed factory",
        "owner": "marshal",
        "status": "specified"
      },
      {
        "slug": "developer-machine-bootstrap",
        "title": "A new contributor or agent is productive on this repo without tribal knowledge",
        "owner": "steward",
        "status": "specified   # 2026-08-22 — spec-developer-machine-bootstrap, decomposed into the station backlog same day"
      },
      {
        "slug": "enterprise-airgap",
        "title": "Firewalled Factory",
        "owner": "steward",
        "status": "realized"
      },
      {
        "slug": "fleet-stewardship",
        "title": "Fleet stewardship — tend every feedstock we can touch",
        "owner": "mason",
        "status": "realized"
      },
      {
        "slug": "packaging-factory",
        "title": "The Packaging Factory",
        "owner": "mason",
        "status": "realized"
      },
      {
        "slug": "regenerable-factory",
        "title": "Regenerable factory — every line of code under a spec it can be rebuilt from",
        "owner": "marshal",
        "status": "realized"
      }
    ]
  },
  "guild": {
    "stations": [
      "herald",
      "marshal",
      "atlas",
      "warden",
      "mason",
      "doctor",
      "scribe",
      "steward"
    ],
    "order": [
      "dreamt",
      "pitched",
      "specified",
      "realized",
      "practice",
      "archived"
    ],
    "rows": [
      {
        "station": "herald",
        "total": 7,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 2,
          "realized": 1,
          "archived": 2,
          "practice": 0
        },
        "line": "complete",
        "load": 0,
        "blocked": 0,
        "dreams": [
          {
            "slug": "herald-moments-2-4-missing-surface",
            "title": "Herald — Moments 2–4 Missing Surface",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "herald-pitch",
            "title": "Herald's Pitch Deck — Moment 1 Orchestration (Consolidated)",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pyforge-herald",
            "title": "Herald — capture the dream, illustrate the telemetry, proclaim the release",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "deck-visual-qa",
            "title": "A deck is proven to look right, not merely to render without crashing",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "herald-moments-2-4-live-backend",
            "title": "Herald Moments 2-4 run on a real live backend, not local-storage/CLI-triggered",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pptx-custom-shapes",
            "title": "Programmatic OOXML shapes for information-dense slides, if the .pptx pipeline ever exists",
            "status": "specified   # 2026-08-22 — UNPARKED same day (Marp inadequacy proven + operator named the 21-station stakeholder audience); decomposed as herald Epic 15",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pptx-deck-generation",
            "title": "A second, PowerPoint-native deck pipeline, if this repo ever needs editable .pptx output",
            "status": "specified   # 2026-08-22 — UNPARKED same day (Marp inadequacy proven + operator named the 21-station stakeholder audience); decomposed as herald Epic 15",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "marshal",
        "total": 41,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 9,
          "realized": 12,
          "archived": 15,
          "practice": 4
        },
        "line": "paused 11.5",
        "load": 2,
        "blocked": 0,
        "dreams": [
          {
            "slug": "agent-portability",
            "title": "Agent portability — BMAD on any agent, never vendor-locked",
            "status": "archived",
            "type": "practice",
            "blockedOn": ""
          },
          {
            "slug": "artifact-console",
            "title": "Artifact console — the factory board, hosted as a chat artifact",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "bmad-loop-forward-dependency-blindness",
            "title": "bmad-loop can't see a story's own documented dependency",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "bmad-output-hygiene",
            "title": "One fabricated commit, eight stations of debris",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "dashboard-project-path-derivation",
            "title": "The dashboard assumes slug == project directory — it isn't, and won't stay",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "dream-to-code-model-self-verification",
            "title": "The Dream-to-Code model has never verified itself",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "fidelity-enforcement",
            "title": "Fidelity enforcement — a contract is only a contract if something fails against it",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "fleet-chain-completeness",
            "title": "Fleet Chain Completeness — Orchestrated Dream-to-Code Regeneration",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "genesis-installer",
            "title": "Genesis installer — the seed, made executable",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "genesis-installer-name-retirement",
            "title": "Retire genesis-installer — one marshal CLI, one PRD/architecture/epics chain",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "loop-home-fleet-refresh",
            "title": "Refreshing every loop-home from main is a hand-run ritual",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "one-front-door",
            "title": "One front door — Marshal drives everything BMAD installs",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pyforge-core",
            "title": "One primitive, one home — the shared floor under eight stations",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pyforge-marshal-loop-orchestrator",
            "title": "\"Dream — PyForge Marshal: Loop Orchestrator\"",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pyforge-testing-charter",
            "title": "\"Dream — PyForge Testing Charter: Systematic Testing for the Guild\"",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "sprint-status-auto-promote",
            "title": "The dashboard goes stale because promotion is a remembered step",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "adaptive-model-tiering",
            "title": "FR-51's model tiering is fully wired and never turned on",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "agent-tool-surface",
            "title": "Agent tool surface — every craft reachable through one governed API",
            "status": "realized",
            "type": "practice",
            "blockedOn": ""
          },
          {
            "slug": "artifact-chain-reconciliation",
            "title": "A backlog authored before the code existed is a plan for a different codebase",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "durable-runs",
            "title": "Durable runs — work survives the machine that made it",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "factory-console",
            "title": "Factory console — the whole pipeline on one page",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "fleet-status-supervisor-fallback",
            "title": "A dead supervisor and a dead engine report identically — and only one of them needs help",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "horizontal-run-concurrency",
            "title": "One story in flight at a time, silently, by an upstream stub",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "marshal-land-merge-subject",
            "title": "Marshal-driven landings are provably Marshal-driven",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pr-lifecycle",
            "title": "PR lifecycle — a story lands itself",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pyforge-marshal",
            "title": "Marshal — autonomy a human can trust",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "quick-dev-reconciliation",
            "title": "Two ways to finish a story, and Marshal has only ever heard of one",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "regenerable-factory",
            "title": "Regenerable factory — every line of code under a spec it can be rebuilt from",
            "status": "realized",
            "type": "practice",
            "blockedOn": ""
          },
          {
            "slug": "risk-tiered-review-depth",
            "title": "A one-line doc fix and a cross-module rewrite get the identical review",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "surface-drift-reconciliation",
            "title": "A drift gate nobody can clear, and a drift signal anyone can launder",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "agentic-sdlc-autonomy",
            "title": "The Agentic SDLC — four views of autonomy, one governed factory",
            "status": "specified",
            "type": "practice",
            "blockedOn": ""
          },
          {
            "slug": "bmad-loop-baseline-drift",
            "title": "A story's orchestrator-recorded baseline can never drift out from under its own worktree",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "bmad-loop-intent-gap-work-preservation",
            "title": "An intent-gap revert can never discard real work without a recoverable trace",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "bmad-loop-liveness-footgun",
            "title": "Nobody has to hand-parse engine.pid to answer \"is this run alive?\"",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "bmad-switch-scope-enforcement",
            "title": "A BMAD write can never land in the wrong project's artifacts, mechanically",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "dashboard-velocity-captures-hand-driven-work",
            "title": "Dashboard velocity counts every story's real effort, not just bmad-loop-journaled ones",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "landing-evidence-grammar",
            "title": "A legitimate landing is recognizable no matter which of the three-plus paths landed it",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "marshal-land-cross-project-story-key-collision",
            "title": "A GitHub PR-merge branch from one project never masquerades as a same-numbered story in another",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "marshal-single-story-dispatch",
            "title": "Single-story dispatch is a marshal verb, not a session's discipline",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "marshal-status-harness-run-id-poisoning",
            "title": "A spin-time poll timeout never permanently blinds marshal status to a healthy run",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "bmad-611-era-alignment",
            "title": "PyForge's artifacts, patterns, and station code stay aligned to the installed BMAD era — 6.11 today, v7-ready tomorrow",
            "status": "specified   # 2026-08-22 — spec-bmad-611-era-alignment under pyforge-marshal (7 CAPs, 2 companions), decomposed as marshal Epic 25 (7 stories, all independent)",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "atlas",
        "total": 12,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 3,
          "realized": 2,
          "archived": 5,
          "practice": 0
        },
        "line": "complete",
        "load": 1,
        "blocked": 0,
        "dreams": [
          {
            "slug": "microsoft-org-sweep",
            "title": "Microsoft org sweep — audit one upstream org, package what is missing",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pyforge-atlas-intelligence-platform",
            "title": "\"Dream — PyForge Atlas Intelligence Platform\"",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "unity-data-stack",
            "title": "Unity Data Stack — the enterprise innersource platform",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "upstream-discovery",
            "title": "Upstream discovery — package it before it's asked for",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "wasm-analytics-stack",
            "title": "WASM Data Stack",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "kedro-org-tooling-adoption",
            "title": "Atlas's own Kedro tooling gap — skills, viz publishing, IDE integration",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pyforge-atlas",
            "title": "Atlas — the map that maintains itself",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "artifactory-download-intelligence",
            "title": "An enterprise Artifactory mirror's own download telemetry joins the universe picture",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "atlas-query-dashboards",
            "title": "A query against the atlas DB becomes an interactive dashboard, no SPA framework",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "wagtail-corporate-brain",
            "title": "The \"Corporate Brain\" CMS atlas's own WikiSyncer has been waiting to push to",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "enterprise-data-models-and-apis",
            "title": "A normalized data model and REST API pattern, waiting for a PyForge-native subject",
            "status": "specified   # 2026-08-22 — reframed as an EXTENSION-POINT (operator): the fleet ships the socket/contract; the capability develops separately (incl. air-gapped) — see the spec's Extension contract section",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "conda-forge-packaging-inventory-operations",
            "title": "Build a conda-forge packaging inventory from scratch as a continuous intake engine",
            "status": "specified   # 2026-08-22 — spec + station decomposition landed same day",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "warden",
        "total": 4,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 0,
          "realized": 1,
          "archived": 1,
          "practice": 0
        },
        "line": "paused 7.3",
        "load": 0,
        "blocked": 0,
        "dreams": [
          {
            "slug": "pyforge-warden-compliance-gates",
            "title": "\"Dream — PyForge Warden: Compliance Gates\"",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pyforge-warden",
            "title": "Warden — the gate that never lies",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "compliance-factory-web-face",
            "title": "A web face for the compliance factory — upload a manifest, watch warden and atlas analyze it",
            "status": "specified   # 2026-08-22 — spec + station decomposition landed same day",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "package-inventory-eligibility",
            "title": "Every package has one provenance trail and one eligibility answer, from any source",
            "status": "specified   # 2026-08-22 — spec + station decomposition landed same day",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "mason",
        "total": 13,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 3,
          "realized": 0,
          "archived": 4,
          "practice": 2
        },
        "line": "complete",
        "load": 0,
        "blocked": 0,
        "dreams": [
          {
            "slug": "copilot-cli-packaging",
            "title": "copilot-cli on conda-forge — blocked at the license",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "db-gpt-packaging",
            "title": "DB-GPT on conda-forge — the multi-output agent stack",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "presenton-pixi-image",
            "title": "Presenton, conda-native — AI decks inside the regulated enterprise",
            "status": "archived",
            "type": "dream",
            "blockedOn": "Phase-0 decision gate (Epic 1)"
          },
          {
            "slug": "pyforge-mason-recipe-validator",
            "title": "\"Dream — PyForge Mason: Recipe Validator\"",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "fleet-stewardship",
            "title": "Fleet stewardship — tend every feedstock we can touch",
            "status": "realized",
            "type": "practice",
            "blockedOn": ""
          },
          {
            "slug": "packaging-factory",
            "title": "The Packaging Factory",
            "status": "realized",
            "type": "practice",
            "blockedOn": ""
          },
          {
            "slug": "conda-forge-expert-rebuild",
            "title": "Rebuild conda-forge-expert as a Skill-Forge-authored skill, slice by slice",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "django-accelerator-framework",
            "title": "A Django-service scaffolding engine, if this repo ever births new Django-based stations",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pyforge-mason",
            "title": "Mason — forge the blocks, bind the environment, ship the structure",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "miniforge-installer",
            "title": "A custom-branded Python distributable, if this repo ever needs one",
            "status": "specified   # 2026-08-22 — reframed as an EXTENSION-POINT (operator): the fleet ships the socket/contract; the capability develops separately (incl. air-gapped) — see the spec's Extension contract section",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "reusable-cicd-workflows",
            "title": "A centrally-maintained CI/CD workflow family, if this repo ever needs more than plain Actions",
            "status": "specified   # 2026-08-22 — reframed as an EXTENSION-POINT (operator): the fleet ships the socket/contract; the capability develops separately (incl. air-gapped) — see the spec's Extension contract section",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "machine-checked-recipe-knowledge",
            "title": "The CFE failure catalog is generated from the skill spec, every row lint-verified against its enforcing check",
            "status": "specified   # 2026-08-22 — spec + station decomposition landed same day",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pixi-container-image",
            "title": "A shared base container image with pixi already installed, if this repo ever ships one",
            "status": "specified   # 2026-08-22 — spec + station decomposition landed same day",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "doctor",
        "total": 9,
        "counts": {
          "dreamt": 2,
          "pitched": 0,
          "specified": 2,
          "realized": 2,
          "archived": 1,
          "practice": 0
        },
        "line": "complete",
        "load": 1,
        "blocked": 0,
        "dreams": [
          {
            "slug": "pyforge-doctor-dependency-health",
            "title": "\"Dream — PyForge Doctor: Dependency Health Diagnostics\"",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "deferred-work-resolution-sweep",
            "title": "deferred-work-resolution-sweep",
            "status": "dreamt",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "fleet-hygiene-verification-exemplar-program",
            "title": "fleet-hygiene-verification-exemplar-program",
            "status": "dreamt",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "bmad-drift-new-artifact-shape",
            "title": "A spike report is not a corrupt file, and the classifier can't yet tell the difference",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pyforge-doctor",
            "title": "Doctor — one bedside manner for the whole fleet",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "bmad-method-version-drift",
            "title": "Doctor notices when BMAD-METHOD's own installed core falls behind upstream",
            "status": "realized   # core CAPs 1-3 shipped as Epic 10 (10.1/10.2, 2026-08-16); suite extension",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "deferred-work-audit-completeness",
            "title": "deferred-work-audit-completeness",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "deferred-work-visibility",
            "title": "A deferral that nobody can see is a deferral that never happened",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "sibling-dreams-drift",
            "title": "Sibling dreams directories don't drift silently",
            "status": "specified   # 2026-08-22 — spec-sibling-dreams-drift, decomposed into the station backlog same day",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "scribe",
        "total": 5,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 0,
          "realized": 1,
          "archived": 3,
          "practice": 0
        },
        "line": "complete",
        "load": 0,
        "blocked": 0,
        "dreams": [
          {
            "slug": "pyforge-scribe-team-memory",
            "title": "\"Dream — PyForge Scribe: Team Memory Management\"",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "sentinel",
            "title": "Sentinel — the AI Software Factory (the ancestor)",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "team-memory",
            "title": "Team memory — what the team knows, the agents know",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pyforge-scribe",
            "title": "Scribe — the inward voice",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "scribe-mines-raw-session-transcripts",
            "title": "Scribe reaches past curated memory into the raw session transcripts underneath it",
            "status": "specified   # 2026-08-22 — spec + station decomposition landed same day",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "steward",
        "total": 19,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 4,
          "realized": 3,
          "archived": 1,
          "practice": 2
        },
        "line": "paused 12.3",
        "load": 2,
        "blocked": 0,
        "dreams": [
          {
            "slug": "asgi-multiplexer-monolith",
            "title": "Django, Langflow, and DB-GPT co-locate in one ASGI process without starving each other",
            "status": "absorbed   # 2026-08-22 pointer spec authored (spec-asgi-multiplexer-monolith); realized through python-agent-platform per the 2026-08-14 Realization log",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "db-gpt-django-plugin",
            "title": "DB-GPT's agentic, file-hungry model integrates into a stateless Django control plane",
            "status": "absorbed   # 2026-08-22 pointer spec authored (spec-db-gpt-django-plugin); realized through python-agent-platform per the 2026-08-14 Realization log",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "enterprise-multi-agent-orchestration",
            "title": "Django, Langflow, and DB-GPT scale as isolated containers behind one gateway",
            "status": "absorbed   # 2026-08-22 pointer spec authored (spec-enterprise-multi-agent-orchestration); realized through python-agent-platform per the 2026-08-14 Realization log",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "langflow-django-plugin",
            "title": "Langflow integrates into a cookiecutter-django project without fighting it",
            "status": "absorbed   # 2026-08-22 pointer spec authored (spec-langflow-django-plugin); realized through python-agent-platform per the 2026-08-14 Realization log",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pyforge-steward-feedstock-maintenance",
            "title": "\"Dream — PyForge Steward: Feedstock Maintenance Automation\"",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "bmad-module-provisioning",
            "title": "BMAD Method modules are provisioned, not hand-installed",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "enterprise-airgap",
            "title": "Firewalled Factory",
            "status": "realized",
            "type": "practice",
            "blockedOn": ""
          },
          {
            "slug": "pyforge-steward",
            "title": "Steward — provision the line, hold the keys",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "unified-container",
            "title": "One container, eight stations",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "jira-github-projects-sync",
            "title": "A ticket moves once, both boards know",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "python-agent-platform",
            "title": "One Django service hosts the agentic engines as pluggable applications, anywhere — including air-gapped",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "scratch-worktree-lifecycle",
            "title": "A scratch worktree for one story's work is one command, not five",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "secure-live-dashboards",
            "title": "A dashboard can be handed to the company without being rebuilt",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "bmad-method-core-upgrade",
            "title": "BMAD-METHOD's own core stays current, not stuck at whatever version got installed",
            "status": "specified   # 2026-08-21 — spec-bmad-method-core-upgrade under pyforge-steward, grounded in the live 6.10.0→6.11.0 upgrade session",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "bmad-suite-channel-product",
            "title": "The SelfExplainML bmad-suite is a governed product — always latest, dual-path installable, modules provisioned",
            "status": "specified   # 2026-08-22 — spec-bmad-suite-channel-product (5 CAPs + install-matrix.md); decomposed as steward Epic 15 (4 stories) + doctor Epic 15 (2 stories, CAP-5 relay); channel bmad-method refreshed to 6.11.0 same day",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "developer-machine-bootstrap",
            "title": "A new contributor or agent is productive on this repo without tribal knowledge",
            "status": "specified   # 2026-08-22 — spec-developer-machine-bootstrap, decomposed into the station backlog same day",
            "type": "practice",
            "blockedOn": ""
          },
          {
            "slug": "local-ocp-hybrid-environment",
            "title": "A local OpenShift hybrid environment runs the agentic SDLC end to end — visual lifecycle, wired BMAD suite, multiplexed apps, synced tracker",
            "status": "specified   # 2026-08-22 — spec-local-ocp-hybrid-environment (5 CAPs, 2 companions), decomposed as steward Epic 12 extension S-12.4..12.8 (operator-locked)",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "multi-repo-workspaces",
            "title": "One workspace opens every repo a story touches",
            "status": "specified   # 2026-08-22 — spec-multi-repo-workspaces, decomposed into the station backlog same day",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "platform-fifteen-factors",
            "title": "The platform host earns its 15 factors — OIDC-delegated auth, telemetry, startup refusals, policy-as-tests, pixi-sourced deps",
            "status": "specified   # 2026-08-22 — spec-platform-fifteen-factors, decomposed into the station backlog same day",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      }
    ],
    "constitutive": [
      {
        "slug": "pyforge-charter",
        "title": "The PyForge Charter",
        "status": "pitched"
      }
    ]
  },
  "openwork": {
    "open": 462,
    "done": 28,
    "triaged": 145,
    "bySeverity": {
      "critical": 0,
      "high": 1,
      "medium": 19,
      "low": 48,
      "unspecified": 394
    },
    "projects": [
      {
        "project": "pyforge-atlas",
        "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md",
        "open": 118,
        "done": 4,
        "triaged": 53,
        "entries": [
          {
            "id": "DW-A1-5",
            "title": "local-recipes doc re-sync + drift baseline re-stamp (surface-changed)",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B1-1",
            "title": "parity-diff harness under-checks (HIGH, B4 must resolve before it trusts parity)",
            "status": "open",
            "severity": "high",
            "triaged": true
          },
          {
            "id": "DW-B1-2",
            "title": "RateLimitedScheduler not yet wired to the fetch path (MEDIUM, B2/live-fetch)",
            "status": "done",
            "severity": "medium",
            "triaged": true
          },
          {
            "id": "DW-B1-3",
            "title": "enumerate_conda_packages tie-break + B.5 inactive placeholder rows (LOW/MEDIUM, B4 parity)",
            "status": "open",
            "severity": "low",
            "triaged": true
          },
          {
            "id": "DW-B2-1",
            "title": "DAG-level persistence of operator notes edited on the SCORED output (MEDIUM, persistence boundary)",
            "status": "open",
            "severity": "medium",
            "triaged": true
          },
          {
            "id": "DW-B2-2",
            "title": "coerce_cvss_score not on the B2 node data path until B5 wires the vdb boundary (LOW, B5)",
            "status": "open",
            "severity": "low",
            "triaged": true
          },
          {
            "id": "DW-B2-3",
            "title": "vuln_kev_affecting_current in the report-only rollup is package-wide, not version-scoped (LOW, report-only)",
            "status": "open",
            "severity": "low",
            "triaged": true
          },
          {
            "id": "DW-B2-4",
            "title": "Phase P cost-gate class not yet wired into the catalog (B3/B4 pre-flight, MEDIUM)",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B2-5",
            "title": "pypi_intelligence pipeline not end-to-end runnable unattended (by design, note-only)",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B4-1",
            "title": "the credentialed full parity run (ATTENDED, AD-19) — DEFERRED to the wave-boundary event",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B4-2",
            "title": "human sign-off + marking legacy retirement (FR-4) — DEFERRED (human act)",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B4-3",
            "title": "fixture recapture from a real legacy run (DW-B1-1 part a) — tool SHIPPED, recapture DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B4-4",
            "title": "DW-B2-4 BigQuery-routing pre-flight before any credentialed Phase-P run — DEFERRED (carries DW-B2-4)",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B4-5",
            "title": "parity-reconcile items surfaced at the credentialed run (carries DW-B1-3 / DW-B2-3) — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B4-6",
            "title": "credentialed-mode read-path hardening (attended event) — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B5-1",
            "title": "re-point name_resolver.py / recipe-generator.py at Phase C + verify the live authoring read (Q6) — DEFERRED (read-only .",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B5-2",
            "title": "C1 wires the Dagster Schedules AND the concrete refresher/fetcher INJECTION (+ store-format fidelity) — DEFERRED (attend",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B5-3",
            "title": "DW-A2-P4 JFrog dynamic per-host credential attachment for enterprise-mirrored refresh stores — DEFERRED (no live surface",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B5-4",
            "title": "wire the AD-13 staleness marker into the G/G' consumer read-path (degrade to indeterminate) — DEFERRED (consumer-side, B",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B6-1",
            "title": "spdx-schema-gap atlas-usage ranking needs `conda_license` (not yet produced by core) — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B6-2",
            "title": "cwe-seed-gap `_other_impact` headline needs the per-package CWE-rollup dataset — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B7-1",
            "title": "the UPDATE-FEEDSTOCK bucket needs an upstream-of-record column (not yet on core_packages_enumerated) — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B7-2",
            "title": "the real transitive resolver (pip --dry-run / py-rattler solve) is injected, not shipped in-package — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B7-3",
            "title": "universe-BOM standalone pypi-only completeness (not a scope hole; a widening) — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B8-1",
            "title": "the concrete live Basilisk fetcher (querybatch / detail GET) is injected, not shipped in-package — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B8-2",
            "title": "the no-currency-conflation view's behind-upstream join is fixture-supplied — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-B8-3",
            "title": "the full 21,163-package Basilisk population run is credentialed/attended — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-C1-1",
            "title": "the live Dagster schedule bring-up (ATTENDED, Q2) — DEFERRED to the wave-boundary event",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-C1-2",
            "title": "per-op runtime ENFORCEMENT + profile-config run-wiring are bring-up concerns (structural-only in C1)",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-D2-1",
            "title": "the full 28-page Vizro inventory is CIS-two-spine deferred",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-D2-2",
            "title": "shell pages await their composed-store materialization (staleness / query-atlas / detail-cf-atlas / behind-upstream / wh",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-D2-3",
            "title": "DEV-AUTO visual verification of the rendered UI (headless container cannot)",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-D3-1",
            "title": "the live Vizro-AI NL→chart backend bring-up (ATTENDED, Q3) — DEFERRED to the wave-boundary event",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-D3-2",
            "title": "the dashboard NL query field (the D2 Vizro dashboard's NL entry point) — DEFERRED (carries DW-D3-1 + the CIS spine)",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-E1-1",
            "title": "the live cross-process A2A wire (a running fasta2a server / broker) — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-E2-1",
            "title": "the live OTel collector + OpenLineage backend wiring (env-driven) — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-E2-2",
            "title": "Dagster-plane observability inheritance verification + span-key footgun (bring-up)",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-E2-3",
            "title": "AtlasNodeMetricsRunFacet provenance stamp (cosmetic)",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-F1-1",
            "title": "the cold-start / warm-incremental benchmark (ATTENDED, SM-3) — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-F2-1",
            "title": "the Great Expectations boundary adapter (version-capped at cf 1.18.2) — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-F2-2",
            "title": "wire a real A2A alert_sink into the shipped validation hook (gated on F4's first contract)",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-F3-1",
            "title": "a real learned embedding model (upgrade from the deterministic default)",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-F3-2",
            "title": "live `vss` extension provisioning (the one-time network INSTALL)",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-G1-1",
            "title": "full Vizro-AI dashboard RENDERED inside Pyodide (the heavy read-surface half)",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-G1-2",
            "title": "heavy WASM build assets are gitignored; CI must run `wasm-build` before `wasm-smoke`",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-G2-1",
            "title": "the LIVE GitHub Pages publish is the ATTENDED boundary event (not automated)",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-G2-2",
            "title": "migrate the G1 wasm/ runtime to consume the emitter's manifest (single-owner completion)",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-G3",
            "title": "the live Dagster sensor DAEMON bring-up (ATTENDED, Q2) — DEFERRED to the wave-boundary event",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-H1",
            "title": "the MinIO/PostgreSQL SERVER provisioning + bring-up (ATTENDED) — DEFERRED to the H1 precondition event",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-H2",
            "title": "the live `agno`-Agent / LLM synthesis + F3-vss production retriever bring-up (ATTENDED) — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-H3",
            "title": "the live La Suite/Wagtail SERVER + credential + httpx opener bring-up (ATTENDED) — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-H4",
            "title": "the live factory-crew daemon bring-up (sensor RUNNING + weekly lint + live wiki store) (ATTENDED) — DEFERRED",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-I4-1",
            "title": "10.5 finalized on a spent review budget, not on convergence (LOW) — DEFERRED",
            "status": "open",
            "severity": "low",
            "triaged": true
          },
          {
            "id": "DW-AD23-1",
            "title": "Run admission was asserted but never implemented (HIGH) — CLOSED",
            "status": "done",
            "severity": "high",
            "triaged": true
          },
          {
            "id": "DW-AD23-2",
            "title": "Run-admission release residuals: Dagster-plane process-locality, `in_process` coupling, and the hook-ordering strand win",
            "status": "open",
            "severity": "medium",
            "triaged": true
          },
          {
            "id": "DW-I5-1",
            "title": "10.6 also finalized on a spent review budget (LOW) — DEFERRED",
            "status": "open",
            "severity": "low",
            "triaged": true
          },
          {
            "id": "DW-AD23-3",
            "title": "the lock store's DEFAULT location is the hazardous one (MEDIUM) — CLOSED",
            "status": "done",
            "severity": "medium",
            "triaged": true
          },
          {
            "id": "DW-FU-13-3",
            "title": "13.3 finalized on a spent follow-up-review budget (LOW) — DEFERRED",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-14-2-1",
            "title": "get_widget() and get_view() both raise a bare, unwrapped KeyError with a confusing repr-quoted message on lookup failure",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-14-3-1",
            "title": "tests/dashboard/test_dashboard_e2e.py's Playwright navigation races the Dash dev server's startup, reliably failing with",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-14-3-2",
            "title": "Bokeh 3.9.2's `patch_curdoc()` context manager has no exception safety — a callback that raises corrupts `curdoc()` for ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-A1-6",
            "title": "The registered `[verify]` command `pixi run --frozen -e pyforge-atlas kedro-test` cannot run until the workstation re-lo",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-A1-7",
            "title": "`.bmad-loop/policy.toml [scm] worktree_seed` still lists only pyforge-warden's implementation-artifacts path — an atlas",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-A1-8",
            "title": "`[verify].commands` is a flat list — every loop story in either package now materializes BOTH the pyforge-warden and pyf",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-A1-9",
            "title": "kedro-test import provenance is mixed in the lean env — smokes import the INSTALLED conda build of pyforge-atlas while `",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-A2-1",
            "title": "Dynamic per-host JFrog credential attachment does NOT exist — credential references are static per-entry catalog config,",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-A3-1",
            "title": "No epoch-seconds-vs-milliseconds magnitude guard on the `fetched_at` stamp/read in `IncrementalParquetDataset`. If a fut",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-A3-2",
            "title": "`IncrementalParquetDataset` reaches into the composed dataset's PRIVATE internals — `self._inner._describe()` and `self",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-A3-3",
            "title": "One-tick TTL boundary parity is UNVERIFIED against the legacy gate. Legacy `atlas_phase` treated a row as stale when `ag",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-4-1",
            "title": "A future pandera `Column(str)` contract registered in `DEFAULT_CONTRACTS` (`validation.py`) will spuriously halt on a le",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-4-2",
            "title": "`pyforge.atlas/__init__.py`'s `future.infer_string` pin is process-wide mutable pandas state, not scoped to this package",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-4-3",
            "title": "`ci_red`'s business logic is duplicated as raw SQL outside the declared-once `semantic/metrics.py` definition — `wasm/in",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-5-1",
            "title": "The dashboard's per-page AD-17 provenance is resolved once at `build_dashboard()` time while each page's grid data is a",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-5-2",
            "title": "`provenance.py`'s `resolve_for_catalog_dataset` reaches into kedro's underscore-prefixed `_describe()` (`\"filepath\"`, `\"",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-5-3",
            "title": "`resolve_for_catalog_dataset`'s `ParquetDataset` branch uses `dataset._describe()[\"filepath\"]` unconditionally, which fo",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-5-4",
            "title": "The dashboard's `_provenance_line` never renders `ProvenanceInfo.build_stamp_newest`, so a future dashboard page wired t",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-5-5",
            "title": "`resolve_for_catalog_dataset`'s kind dispatch covers 61 of the catalog's 86 entries; 8 of the remaining 25 (7 `json.JSON",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-5-6",
            "title": "Three catalog entries (`AnacondaDownloadsDataset`, `GitHubRequestDataset`, `PyPIJsonRequestDataset`) perform a real live",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-5-7",
            "title": "The dashboard and the MCP read surface resolve the SAME logical dataset's backing file through two independent path mech",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-5-8",
            "title": "Reusing `IncrementalParquetDataset._to_epoch_seconds` on the READ path makes its `logger.warning` (\"normalizing N ms-mag",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-6-1",
            "title": "`AtlasObservabilityHooks.__deepcopy__` (and any hook copying this pattern) hand-copies a fixed list of attributes via `c",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-6-2",
            "title": "Run admission is writer-writer exclusion only, and the concurrency it deliberately PERMITS is reader-writer unsafe: `pan",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-6-3",
            "title": "`observability.py` states, in three places, that \"C1's `KedroProjectTranslator` deep-copies the settings hooks at `to_da",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-12-1-1",
            "title": "Unconfirmed whether `src/shared/packages/pyforge-atlas/.claude/skills/catalog-config/` — the first nested, directory-sco",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-12-1-2",
            "title": "The two upstream-issue texts drafted in `kedro-skills-audit-report.md` (layer-tag nesting; the numbered 8-layer director",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-12-1-3",
            "title": "The live `sprint-status.yaml`'s `story_meta.depends_on` lists still reference the retired `d1-`/`d2-` key spelling for E",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-12-2-1",
            "title": "`kedro-viz-publish.yml`'s trigger path filter (`src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/**` only,",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-12-2-2",
            "title": "`kedro-viz-publish.yml` pushes directly to `main` with the default `GITHUB_TOKEN` and no PR; if branch protection is eve",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-12-2-3",
            "title": "A narrow non-fast-forward race exists in `kedro-viz-publish.yml`: if two pipeline-touching pushes to `main` land in quic",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-12-2-4",
            "title": "No end-to-end GitHub Actions execution of `kedro-viz-publish.yml` was exercised before this story's PR — only the underl",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-12-2-5",
            "title": "`normalize_viz_build.py`'s `_iter_text_files` silently skips any file under `build/` that isn't valid UTF-8 (via a bare",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-12-2-6",
            "title": "`normalize_viz_build.py`'s anchor-strip uses a literal `str.replace()` substring match with no path-boundary check — a f",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-12-2-7",
            "title": "The live `sprint-status.yaml`'s `story_meta.depends_on` lists still reference the retired `d1-`/`d2-` key spelling for E",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-1-1",
            "title": "The GitHub Search API fallback query (`sort=stars&order=desc`, no date/activity filter) doesn't represent \"trending\" at",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-1-2",
            "title": "`TrendingSnapshotDataset.STORE_FILENAME` is a single fixed filename, so each refresh fully overwrites the prior snapshot",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-1-3",
            "title": "`parse_trending_html`'s `article.find(\"h2\")`/`article.find(\"p\")` grab the FIRST matching tag anywhere in a repo card's s",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-1-4",
            "title": "Row dicts mix Python `int` and `None` for `stars_total`/`stars_today`/`forks_total`; `pd.DataFrame(rows)` upcasts any su",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-1-5",
            "title": "`parse_trending_html`'s `repo_full_name` is built by stripping slashes off the scraped `href`, assuming it is always a r",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-1-6",
            "title": "`pipelines/upstream_discovery/nodes.py::_coerce_cadence` (post-patch) and the precedent it mirrors, `pipelines/vulnerabi",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-1-7",
            "title": "`_STARS_DELTA_RE` searches the WHOLE card's concatenated text (`article.get_text(\" \", strip=True)`), not a scoped stars-",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-1-8",
            "title": "`_parse_count`'s `_DIGITS_RE = re.compile(r\"[\\d,]+\")` only captures digit/comma runs — an abbreviated count like \"1.2k s",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-1-9",
            "title": "`TrendingSnapshotDataset._write`'s malformed-frame guard checks only that `_REQUIRED_COLUMNS` are PRESENT, not that they",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-2-1",
            "title": "`_resolve_pypi_name` is fully implemented and tested but unused in `classify_trending_candidates`'s hot path, which inli",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-2-2",
            "title": "`trending_candidates_classified` re-materializes only in the WEEKLY `bootstrap_data` job while its own source `trending_",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-2-3",
            "title": "The license gate emits the affirmative reason `not-osi-license` for two states that are actually \"signal unavailable\" —",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-2-4",
            "title": "The repo-name -> PyPI-name heuristic has an undocumented FALSE-POSITIVE direction: an unrelated repo whose name collides",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-2-5",
            "title": "`pypi_intelligence_enriched` is a bounded top-N enrichment slice, which structurally excludes freshly-trending packages",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-2-6",
            "title": "A repo trending in more than one window appears up to 3x in `trending_candidates` (once per `daily`/`weekly`/`monthly` p",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-3-1",
            "title": "`query_trending_candidates`'s `with _session.bootstrapped_session(...) as s: catalog = _session.loaded_catalog(s)` is NO",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-3-2",
            "title": "CAP-3's literal success signal in `spec-upstream-discovery/SPEC.md` is \"JSON output validates against a documented schem",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-3-3",
            "title": "`build_stamp_newest` is `null` in every real `query_trending_candidates` response, because `provenance.py` populates it",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-3-4",
            "title": "The default `--not-on-cf` filter excludes only the exact reason `already-on-conda-forge`, but CAP-2 also emits `unclassi",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-3-5",
            "title": "Every MCP tool that bootstraps a Kedro session (`read_dataset`, `list_datasets`, and now `query_trending_candidates`) in",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-3-6",
            "title": "`mcp/tools.py::read_dataset` — the seam `query_trending_candidates` was modelled on — returns `result.to_dict(orient=\"re",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-4-1",
            "title": "`classify_trending_candidates` can only ever reach a tier via a resolved PyPI name, so a genuinely PyPI-less candidate (",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-4-2",
            "title": "The exact-normalized-repo-segment PyPI-name resolution heuristic (`_resolve_pypi_name`, Story 13.2, already an accepted",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-5-1",
            "title": "The two CLI entrypoints now living in `trending_candidates/` enforce incompatible exit-code contracts for the same failu",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-5-2",
            "title": "`scripts/spec_surface_check.py`'s `--write-baseline` has no structural safeguard against stamping a stale or incomplete",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-5-3",
            "title": "`scripts/spec_surface_check.py --write-baseline` does an unlocked read-modify-write of `scripts/.spec-surface-baseline.j",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-5-9",
            "title": "Follow-up review still recommended for 10-5-stamp-advisory-data-with-its-build-provenance after the damping cap was spen",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-10-6-4",
            "title": "Follow-up review still recommended for 10-6-make-run-admission-real-or-stop-claiming-it after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-13-3-7",
            "title": "Follow-up review still recommended for 13-3-trending-candidates-operator-surface after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          }
        ]
      },
      {
        "project": "pyforge-marshal",
        "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md",
        "open": 103,
        "done": 11,
        "triaged": 25,
        "entries": [
          {
            "id": "DW-1-1-1",
            "title": "The `pyforge-mason`, `pyforge-steward`, and `pyforge-warden` `*-build-conda` pixi tasks (root `p…",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-1-2",
            "title": "`pyforge-doctor` and `pyforge-warden`'s package `.gitignore` files put comments inline after the…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-1-3",
            "title": "Every pyforge sibling package (doctor, warden, steward, mason, and now marshal) declares `licens…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-1-4",
            "title": "The `pyforge-mason-build-dist` and `pyforge-steward-build-dist` pixi tasks (root `pixi.toml`) ru…",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-FU-1-1",
            "title": "Follow-up review still recommended for 1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enfor",
            "status": "open",
            "severity": "low",
            "triaged": true
          },
          {
            "id": "DW-1-2-1",
            "title": "`architecture.md`'s AD-23 rule text still says the story key is \"purely numeric on both parts\", contradicting AD-38",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-3-1",
            "title": "`core/policy.py`'s `content_hash` (and therefore `materialize()`'s content-addressed filename) i…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-3-2",
            "title": "`schemas/policy.json`'s `policyField` `$defs` entry does not constrain the TYPE of `value`/`raw_…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-3-3",
            "title": "`cli/config.py::materialize()` can leave an orphaned `.policy-*.tmp` file in the target director…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-FU-1-3",
            "title": "Follow-up review still recommended for 1-3-layered-policy-composition-with-provenance-and-validation after the damping c",
            "status": "open",
            "severity": "low",
            "triaged": true
          },
          {
            "id": "DW-1-10-7",
            "title": "No project-policy source supplies `gate_mode=\"none\"` / `max_followup_reviews=2`, so the first real `write_policy_toml` c",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-10-1",
            "title": "`adapters/harness_bmadloop.py`'s vendored `_POLICY_TEMPLATE` is a hand-copied snapshot of `bmad_…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-10-2",
            "title": "`write_policy_toml`'s unconditional whole-file overwrite will silently discard harness-native st…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-10-3",
            "title": "This story's untrack (`git rm --cached .bmad-loop/policy.toml`) only closes the F-1 cross-projec…",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-10-4",
            "title": "Between this story's merge (which untracks `.bmad-loop/policy.toml`) and the later story that wi…",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-10-5",
            "title": "The `max_followup_reviews = 2` value in the (now untracked) live policy.toml was explicitly bran…",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-10-6",
            "title": "The tracked `.bmad-loop/policy.toml` this story deletes carried curated operational commentary w…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-7-1",
            "title": "The supported harness range had three unsynchronized declarations",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-8-1",
            "title": "Preflight lacks init and teardown's Git-ref-shape slug guard",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-8-2",
            "title": "Teardown hardcodes the integration branch as `main`",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-8-3",
            "title": "Teardown has a branch-deletion TOCTOU window",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-8-4",
            "title": "Teardown cannot see valuable gitignored content",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-8-5",
            "title": "Teardown can destroy nested registered worktrees",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-8-6",
            "title": "Teardown has no active-run liveness guard",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-9-1",
            "title": "Marshal's README still describes a Story 1.1 skeleton",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-9-2",
            "title": "The future run journal must record Marshal and harness versions",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-AUD-2026-07-31-1",
            "title": "Stories 1.7-1.9 shipped without canonical memlog reconciliation",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-AUD-2026-07-31-2",
            "title": "Four Marshal-owned Dreams still have no Tier-2 Spec",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-AUD-2026-07-31-3",
            "title": "Deferred-work detector ignores anonymous Tier-3 entries",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-4-1",
            "title": "`cli/init.py`'s project-existence check (`MRS-INIT-002`) reads `_bmad-output/pro…",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-4-2",
            "title": "The `MRS-INIT-003` marker/symlink desync guard has two blind spots: (1) `_slug_f…",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-4-3",
            "title": "`adapters/fs_local.py`'s two atomic-write helpers disagree on stale-temp-file ha…",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-4-4",
            "title": "`marshal init <slug>` has no protection against two concurrent invocations for t…",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-4-5",
            "title": "`cli/init.py::_loop_home_root()`'s real default fallback (`Path.home() / \".bmad-…",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-4-6",
            "title": "`tests/unit/test_vcs_git.py` and `tests/integration/test_init_worktree.py` each …",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-4-7",
            "title": "`cli/init.py`'s printed `launch_line` (`cd <home> && export BMAD_ACTIVE_PROJECT=…",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-4-8",
            "title": "`marshal init` has no guard against the total loop-home path length, despite thi…",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-4-9",
            "title": "`cli/main.py::main` catches only `SystemExit` and `KeyboardInterrupt` — it has n…",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-4-10",
            "title": "`tests/integration/test_init_worktree.py` — the only end-to-end proof of both wo…",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-5-11",
            "title": "`cli/init.py`'s `tier3_backlink` step gives a real, non-empty DIRECTORY at the l…",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-5-13",
            "title": "`tier3_backlink`'s convergence check compares the raw (unresolved) symlink target…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-5-14",
            "title": "A failed `ensure_dir`/`repoint_symlink_atomic` after `remove_empty_dir` leaves the…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-5-12",
            "title": "A home provisioned by `marshal init` alone still lacks the TOP-LEVEL `_bmad-outp…",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-4-2-1",
            "title": "`marshal teardown` reports every landed story as an unreachable promotion for …",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-SYNC-2026-08-08-1",
            "title": "`sprint-ledger-sync` silently DOWNGRADES the tracked ledger when …",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-LEDGER-2026-08-08-1",
            "title": "RETRACTED. Herald's \"34 orphan story specs\" was damage I caus…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-LEDGER-2026-08-08-2",
            "title": "VOID (measured after the DW-LEDGER-1 damage; doctor's real orpha…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-LEDGER-2026-08-08-3",
            "title": "RETRACTED. Atlas's feed and twin agree exactly; there is no …",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-LEDGER-2026-08-08-4",
            "title": "VOID. Its table was measured after the damage, not before it.",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-DOCTOR-2026-08-08-1",
            "title": "`doctor check` is 7.04s against its documented 5.0s budget",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-DOCTOR-2026-08-08-2",
            "title": "Doctor's discovery walk borrowed warden's entry cap, where hitting it means the opposite thing",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-BOARD-2026-08-08-1",
            "title": "Herald's build line and Herald's ledger describe DIFFERENT sto…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-SURFACE-2026-08-08-1",
            "title": "memlog movement is surface-wide, so one entry launders every pending drift finding",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-SURFACE-2026-08-08-2",
            "title": "`--write-baseline` is all-or-nothing, so no spec can be reconciled in isolation",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-FU-2-1",
            "title": "Follow-up review still recommended for 2-1-standalone-verify-command-runner-project-scoped after the damping cap was spe",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-FU-2-6",
            "title": "Follow-up review still recommended for 2-6-gate-evidence-record-with-redaction-at-egress after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-FU-3-3",
            "title": "Follow-up review still recommended for 3-3-detached-launch-with-scoped-story-selection after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-FU-3-4",
            "title": "Follow-up review still recommended for 3-4-supervisor-process-lifecycle after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-FU-3-5",
            "title": "Follow-up review still recommended for 3-5-idle-strand-detection after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-FU-4-14",
            "title": "source_spec: `spec-4-14-the-failed-story-safety-net-is-reported.md`",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9",
            "title": "Follow-up review still recommended for 7-4-manifest-schema-loader-and-model-version-ranges after the damping cap was spe",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-10-2-1",
            "title": "`pyforge-deps-test` fails on `pyforge-mason`'s five conda-only run-dependencies, reddening a verify command every story ",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-10-3-1",
            "title": "Writing `plan.json` to its canonical path flips the fingerprint's dirty flag, so the first apply of every freshly built ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-10",
            "title": "A failed rollback wraps an interrupt in a catchable `InternalError`, so a CLI's `except SeedError` swallows the operator",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-2",
            "title": "Rollback restores a file's bytes but not its mode, so a failed apply leaves every executable managed artifact non-execut",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-3",
            "title": "A directory target snapshots as `None` and is never removed, so a rolled-back apply leaves the whole tree it created",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-4",
            "title": "A symlinked target is snapshotted through the link but restored over it, leaving neither the link nor its referent as th",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-5",
            "title": "An interrupt raised during rollback discards the list of paths rollback already knew it could not restore",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-6",
            "title": "The never-write guard is applied to rollback restores, so a target `commit` wrote into a never-write path can never be p",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-7",
            "title": "A plan's fingerprint records no repo identity, so a plan built against one non-git directory applies cleanly to a differ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-8",
            "title": "`fingerprint_drift` performs an unguarded arbitrary-path read; containment lives only in its caller, and Story 10.4 owns",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-9",
            "title": "`build_plan` emits Actions whose `target_path` escapes `repo_root`, so one bad manifest entry makes `run_apply` refuse t",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-4-1",
            "title": "A symlinked ancestor directory defeats the never-write guard, because the pattern is matched against the resolved destin",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-4-2",
            "title": "The new never-imported packaging ratchet cannot see `python-build`, the one exempted name its own docstring says the gat",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-4-3",
            "title": "`ManagedRecord`'s region-bearing shape has no source in the state model Story 10.2 actually landed, so rung 6 cannot be ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-4-4",
            "title": "`managed_after_skips` cannot protect the artifact class rung 6 actually guards, because a hand-edited managed file never",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-4-5",
            "title": "An action whose target is an existing DIRECTORY clears all six precondition rungs and fails later as an untyped `IsADire",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-14-1-1",
            "title": "`pyforge-core/.gitignore`'s `/dist/` and `/dist-conda/` lines carry inline comments gitignore cannot parse, so both patt",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-14-2-1",
            "title": "story deferred at the dev verify-gate — substantive work committed locally but never merged, blocked on cross-spec spec-",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-14-3-1",
            "title": "Doctor and Steward still carry un-reparented exception roots outside Story 14.3's CAP-5 scope",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-14-4-1",
            "title": "Herald, Mason, and Scribe carry real, un-migrated subprocess implementations outside Story 14.4's CAP-6 scope",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-14-4-2",
            "title": "AD-4's import-linter contract has a verification blind spot for pyforge-core's own internal os/subprocess imports",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-2-8-1",
            "title": "epics.md's Story 2.8 entry omits the **Surface:** line every sibling Epic-2 story carries",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-12-1",
            "title": "A resumed run's retry-escalation ceilings are read from whatever policy.toml is on disk now, not the policy that governe",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-12-2",
            "title": "A newly-struggling story is never named in the escalation journal once a resumed run's model is already floor-raised",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-12-3",
            "title": "A model-tiering policy.toml write can land on disk before its own launch/resume intent is journaled, in both run_spin an",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-12-4",
            "title": "A TOML serialization failure ahead of the atomic policy.toml write is never wrapped in HarnessPolicyWriteError, in both ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-13-1",
            "title": "Policy-vocabulary key-count literals in cli/config.py's comments and two test names were already stale before this story",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-5-10-1",
            "title": "A malformed `merge_subject_template` (missing or duplicate `{key}` placeholder) crashes `marshal land`'s full-merge path",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-5-10-2",
            "title": "A multi-key `marshal land` wave under `landing_merge_strategy: squash` or `rebase` renders its subject from the wave's p",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-5-10-3",
            "title": "`gh pr merge --subject`'s `commitHeadline` has no merge commit to title under `landing_merge_strategy: rebase`, so a reb",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-5-8-1",
            "title": "`is_run_live`, which gates `marshal land`'s branch retirement off the same `FleetHomeFacts` this story extends, never co",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-5-8-2",
            "title": "`ProcessPort.is_alive`'s bare pid-existence probe has no identity/start-time corroboration and admits a degenerate `pid:",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-5-8-3",
            "title": "`tests/packaging/test_dependency_completeness.py`'s `BASELINE_UNDECLARED_IMPORTS` ratchet is a shared, repo-wide file wi",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-5-9-1",
            "title": "Two distinct raw sprint-status-ledger.yaml keys that both normalize to the identical StoryKey silently collapse in recon",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-5-9-2",
            "title": "`cli/deploy.py::run_promote` reports a story key in `data[\"promoted\"]` even when the `commit_paths` that would make the ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-5-9-3",
            "title": "`promote_sprint_status.py::repair_feed` matches the tracked ledger's raw key spelling against the Tier-3 feed's raw key ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-5-9-4",
            "title": "A failed ledger `commit_paths` after a successful `git add` leaves the git INDEX staged with pre-rollback content, even ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-5-9-5",
            "title": "A literal duplicate raw key appearing twice as separate lines in the tracked ledger's own text has only its FIRST occurr",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-8-1-1",
            "title": "the region-name forward-reference entry S-7.4's own ledger opened for S-8.1 is now closed in fact but still reads `statu",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-1-1",
            "title": "`spec_surface_check.py --write-baseline --spec` stamps every file the named spec governs, not just the paths a reconcili",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-3-1",
            "title": "`check_managed_file`/`check_managed_region` never distinguish a shape-invalid `recorded_sha` from a genuine hand-edit",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-4-1",
            "title": "Epic 9.4's AC prose names a glob (`docs/specs/*.md`) for the canonical legacy worked example that this module's presence",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-5-1",
            "title": "Manifest coverage check can never actually fire against any manifest built through normal construction",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-5-2",
            "title": "A second, independent review pass re-confirms manifest coverage is structurally redundant with `ManifestEntry.__post_ini",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-5-3",
            "title": "Manifest coverage only sees version-filtered entries, so a staged or retired entry's corrupted class/rationale produces ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-6-1",
            "title": "`build_plan`'s git fingerprint can misreport an ancestor repository's HEAD/dirty state for a nested target",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-6-2",
            "title": "Writing `plan.json` before the target's `.gitignore` region is materialized can make the plan file itself flip a subsequ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-4-14-1",
            "title": "Follow-up review still recommended for 4-14-the-failed-story-safety-net-is-reported after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-FU-8-5",
            "title": "Follow-up review still recommended for 8-5-marker-deletion-as-a-sanctioned-opt-out after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-BL011-1",
            "title": "loop-stall-check labels a bmad-loop 0.11 `awaiting-operator` parked run \"stalled\" — attention arrives, mislabeled",
            "status": "done",
            "severity": "low",
            "triaged": true
          },
          {
            "id": "DW-BL011-2",
            "title": "the deferred-work pipeline's intake shape changes on the FIRST bmad-loop 0.11 run — Tier-3 `deferred-work.md` is no long",
            "status": "open",
            "severity": "medium",
            "triaged": false
          },
          {
            "id": "DW-25-4-1",
            "title": "`repo_defaults` compose parameter is accepted but never folded — `policy-defaults.toml` is functionally inert for all 28",
            "status": "open",
            "severity": "medium",
            "triaged": false
          },
          {
            "id": "DW-25-5-1",
            "title": "Story 25.5's review round landed AFTER the merge — two layers' findings dispositioned here, unapplied",
            "status": "open",
            "severity": "medium",
            "triaged": false
          }
        ]
      },
      {
        "project": "pyforge-steward",
        "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md",
        "open": 75,
        "done": 2,
        "triaged": 1,
        "entries": [
          {
            "id": "DW-1-2-1",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-th",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-2-2",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-th",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-2-3",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-th",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-2-4",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-th",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-2-5",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-2-credentials-never-attach-outside-their-declared-host-and-th",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-1",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plain",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-2",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plain",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-3",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plain",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-4",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plain",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-5",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plain",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-6",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plain",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-7",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plain",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-8",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plain",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-9",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plain",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-10",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plain",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-11",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plain",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-12",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plain",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-13",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plain",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-14",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plain",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-15",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plain",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-16",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-secrets-steward-stores-live-encrypted-in-git-never-as-plain",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-7-1-1",
            "title": "source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-7-1-one-build-whole-guild.md`",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-7-1-2",
            "title": "source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-7-1-one-build-whole-guild.md`",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-9-1-1",
            "title": "source_spec: `_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-9-1-identity-at-the-boundary-declared-",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10",
            "title": "Follow-up review still recommended for 10-3-one-image-both-engines after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-9",
            "title": "Follow-up review still recommended for 9-3-the-audit-trail-records-what-was-seen after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-10-1-1",
            "title": "spec-python-agent-platform's `environment.yaml` surface declaration has no counterpart in sibling specs that also declar",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-2-1",
            "title": "`python-agent-platform`'s `platforms = [\"linux-64\", \"osx-arm64-min\"]` excludes win-64 with no stated rationale",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-2-2",
            "title": "`channel-priority = \"flexible\"` on `[feature.python-agent-platform]` widens cross-channel resolution eligibility to ever",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-2-3",
            "title": "two other specs that also declare `pixi.toml` in their `surface:` (`pyforge-marshal/spec-pyforge-core`, `pyforge-steward",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-2-4",
            "title": "`gather_spec_surface`'s file-drift hash reads raw on-disk bytes, not git's blob content, so a `text eol=...`-normalized ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-1",
            "title": "`src/platform/Containerfile`'s pip layer swaps the app's Postgres driver from psycopg 3 to conda's psycopg2, with no ORM",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-10",
            "title": "Platform CI's two path filters are duplicated by hand with nothing enforcing they stay equal, so a one-sided edit silent",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-2",
            "title": "`src/platform/Containerfile`'s 8 manually-added transitive pip packages have no automated drift guard against future `re",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-3",
            "title": "`production.py`'s hardcoded `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE` silently break login and every CSRF-protected f",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-4",
            "title": "Nothing tests the platform image's actual runtime stack — every automated test runs a different set of package versions ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-5",
            "title": "The platform image ships its own source tree writable by the runtime user, and whether it does depends on the umask of t",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-6",
            "title": "User-uploaded media under `src/platform/` is not gitignored, because the pattern meant to cover it names a directory tha",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-7",
            "title": "Platform CI's path filter now bills the repo's highest-traffic source trees for a two-engine container matrix plus an un",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-8",
            "title": "The repo-root Containerfile pins a pixi below the floor its own manifest declares, so that image's builder stage cannot ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-10-3-9",
            "title": "Two marshal specs carry stale pixi.toml baselines that the spec-surface gate cannot report, because a moved memlog downg",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-8-4-1",
            "title": "`sync reconcile --schedule`'s per-candidate failure detail is computed but never reaches the operator through the CLI",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-8-4-2",
            "title": "`_LIST_PROJECT_ITEMS_QUERY`'s `fieldValues(first: 50)` cap now runs board-wide, automatically, on every scheduled tick",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-8-5-1",
            "title": "the loop-home worktree's local `epics.md` and tracked `sprint-status-ledger.yaml` are 60 commits stale, still carrying p",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-8-5-2",
            "title": "a GitHub Projects V2 board item deliberately never meant to link to Jira fails loudly on every scheduled tick forever, w",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-8-6-1",
            "title": "`load_config`'s `document.get(...) or {}` idiom silently coerces a falsy-but-malformed `status_mapping`/`field_overrides",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-8-6-2",
            "title": "no operator-facing documentation page covers `status_mapping`/`user_mapping`/`field_overrides` outside the example YAML'",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-8-6-3",
            "title": "`sprint-change-proposal-2026-08-13.md`'s root-cause rationale for the Jira↔GitHub write direction is backwards",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-8-6-4",
            "title": "`status_mapping`'s `or {}` idiom independently reconfirmed to swallow an explicit falsy top-level value (`false`/`0`/`\"\"",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-2-1",
            "title": "`dashboard_role` is a hardcoded scope-key string duplicated independently in the writer (`middleware.py`) and the reader",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-2-2",
            "title": "`build_navigation_view`'s duplicate-path guard only rejects byte-identical strings, so `/reports` and `/reports/` (or di",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-2-3",
            "title": "A whitespace-padded role reaching `filter_by_role` and `build_navigation` from the same request is refused loudly by one",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-3-1",
            "title": "AD-14's PostgreSQL contention proof is not delivered for the new audit store — every test runs against in-memory SQLite ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-3-10",
            "title": "every AUDIT_READ row records the same constant \"of what\", so CAP-4's read-side provenance is unrecoverable from the trai",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-3-2",
            "title": "`query_audit_entries` does not filter its results by the reader's role — AD-7's \"the trail is itself role-isolated data\"",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-3-3",
            "title": "`purge_expired_entries` destroys audit rows without recording that anyone destroyed them, while `query_audit_entries` re",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-3-4",
            "title": "`query_audit_entries` materializes the whole matching set with no limit, and each read appends a row the next read retur",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-3-5",
            "title": "an actor made only of zero-width characters passes the non-blank check, so CAP-4's \"who saw\" can still be recorded as an",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-3-6",
            "title": "a future-dated `occurred_at` is never older than any cutoff, so a caller can write audit rows that no retention policy c",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-3-7",
            "title": "`query_audit_entries`' `transaction.atomic()` is a savepoint inside a caller's transaction, so an outer rollback discard",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-3-8",
            "title": "nothing makes the audit trail append-only, so a single ORM call rewrites or erases CAP-4 evidence leaving no record that",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-3-9",
            "title": "the identity perimeter admits an actor longer than the audit column's cap, so such a user can neither use the dashboard ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-4-1",
            "title": "The refusal-webhook POST blocks synchronously for up to 5s with no rate limit, on a path a caller can trigger repeatedly",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-4-2",
            "title": "`maybe_encrypt_export` never removes the plaintext source after encrypting",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-4-3",
            "title": "The export-refusal webhook payload is unsigned, so a receiver cannot verify it actually came from this service",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-4-4",
            "title": "`ExportPolicy.webhook_url` has no protection against loopback/link-local/internal targets",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-4-5",
            "title": "`authorize_export` being \"the ONLY place the decision is made\" is a documented convention, not something enforced at the",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-5-1",
            "title": "The `perimeter` verb exposes no `--base-port`/`--bind-host` flags, leaving `_worker_ports`'s range check and `bind_host`",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-5-2",
            "title": "The rendered systemd unit name and nginx upstream name are hardcoded, so two perimeter deployments to the same host woul",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-6-1",
            "title": "the dashboard test files' hand-duplicated `settings.configure()` guard, now in a fourth file, aborts the whole run when ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-7-1",
            "title": "dashboard_diff() cannot see a file staged (git add) but left uncommitted after a failed git commit",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-9-7-2",
            "title": "publishing a static board requires a full dashboard-gen rebuild and a valid Steward sprint ledger, because deploy dashbo",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-7-1-3",
            "title": "Follow-up review still recommended for 7-1-one-build-whole-guild after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-9-1-2",
            "title": "Follow-up review still recommended for 9-1-identity-at-the-boundary-declared-isolation-and-the-cache-invariant after the",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-11-2-1",
            "title": "Story 11-2's original Pattern-A groundwork is superseded, not lost",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-11-2-2",
            "title": "DB-GPT's own metadata store cannot be wired to real PostgreSQL — verified upstream limitation, AD-9-blocked",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-FU-11-4",
            "title": "`langflow_integration/tests.py` keeps an unguarded `cursor.fetchone()[0]` — the identical",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          }
        ]
      },
      {
        "project": "pyforge-mason",
        "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md",
        "open": 50,
        "done": 1,
        "triaged": 0,
        "entries": [
          {
            "id": "DW-1-3-1",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-error-taxonomy-and-exit-code-contract.md`",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-3-2",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-3-error-taxonomy-and-exit-code-contract.md`",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-4-1",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-4-dual-output-format-with-stream-discipline.md`",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-4-2",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-4-dual-output-format-with-stream-discipline.md`",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-10-1",
            "title": "source_spec: `_bmad-output/implementation-artifacts/spec-1-10-configuration-surface-logging-and-child-output-streaming.m",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-2",
            "title": "Follow-up review still recommended for 2-2-the-seam-guard after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-2-3-1",
            "title": "source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-2-3-credential-isolation.md`",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-4-4-5",
            "title": "source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`",
            "status": "open",
            "severity": "medium",
            "triaged": false
          },
          {
            "id": "DW-4-4-6",
            "title": "source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-4-4-7",
            "title": "source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-4-4-8",
            "title": "source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-4-4-9",
            "title": "source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-4-4-10",
            "title": "source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-4-4-11",
            "title": "source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`",
            "status": "open",
            "severity": "medium",
            "triaged": false
          },
          {
            "id": "DW-4-4-12",
            "title": "source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-4-4-13",
            "title": "source_spec: `_bmad-output/projects/pyforge-mason/implementation-artifacts/spec-4-4-mason-environment-check.md`",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-2-10-1",
            "title": "`recipe update`'s default (non-`--dry-run`) apply has no VCS safety net and shows a thinner plan than `--dry-run`",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-2-10-2",
            "title": "CFE's `recipe_updater.py` hardcodes the bare command `\"python\"` for its internal `recipe_editor.py` subprocess call, unl",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-2-5-1",
            "title": "`mason recipe validate`'s `EXIT_FAILED` conflates \"the recipe failed validation\" with \"an anticipated Mason-side error o",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-2-5-2",
            "title": "The hand-maintained verb-registration ordinal comments in `cli.py` (e.g. \"the second verb registered\", \"the third verb r",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-2-5-3",
            "title": "No test structurally proves every OTHER `recipe` verb's `cli.py` branch stays `EXIT_OK` regardless of its wrapped tool's",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-2-5-4",
            "title": "`cfe.validate_recipe([\"--json\", recipe_path], ...)` has no `--` separator, so a `recipe_path` beginning with `-` could b",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-2-6-1",
            "title": "`doctor.py`'s per-noun `unavailable_verbs` granularity is now inaccurate for `recipe build`",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-2-7-1",
            "title": "A malformed `MASON_CFE_TIMEOUT` environment value is silently ignored with no warning",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-2-7-2",
            "title": "`mason package`/`mason environment` still print the literal `{}` token for an invalid verb",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-2-8-1",
            "title": "`render_text`'s one-line-per-key format double-prints `scan`'s findings, now the largest payload it renders",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-2-8-2",
            "title": "`_OPTIMIZE_RELEVANT_FLOOR`/`_SCAN_RELEVANT_FLOOR` are hand-declared, never derived from or cross-checked against the rea",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-2-9-1",
            "title": "The unparseable-body PENDING fallback in `_ship_target_result_from_cfe_result` carries no reference or message",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-1-1",
            "title": "`CfeImportFloorError` lacks a `__reduce__` override, so `deepcopy`/`pickle` corrupt its `.args`/`repr()` on round-trip -",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-4-1",
            "title": "`ship_pypi` unconditionally builds the `.conda` package too, coupling a PyPI-only ship to conda-side build/version-misma",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-5-1",
            "title": "`engines.pixi.upload()`'s argv has no `--` separator, so a `channel_name` (or `conda_path`) starting with `-`/`--` is mi",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-5-2",
            "title": "`engines.pixi.upload()` sets no `stdin=subprocess.DEVNULL`, unlike `twine.py`'s documented interactivity defense -- an u",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-6-1",
            "title": "`ship_conda_forge`'s `try/except (OSError, ValueError)` around `Path.expanduser().resolve()` does not catch `RuntimeErro",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-6-2",
            "title": "`resolve_cfe_root` returns flag/environment roots un-expanded and `cfe.py` never expands them, so a `~`-prefixed CFE roo",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-6-3",
            "title": "`resolve_cfe_root`'s unguarded `start_directory.resolve()` sits outside every caller's `try`, so a deleted process cwd m",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-7-1",
            "title": "A concurrent ship of the same PyPI/channel name+version between `version_exists`/`pixi.search` returning `False` and the",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-7-2",
            "title": "`pypi_index.version_exists` always queries the public `pypi.org` index, even when the caller's own environment points `t",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-7-3",
            "title": "`ship_pypi`'s idempotence check derives package identity from the wheel filename only, never cross-validated against the",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-8-1",
            "title": "the `pyforge-mason-test-slow` pixi task's own description text is stale, understating the slow suite it actually runs",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-3-9-1",
            "title": "the FR-24/FR-50 TestPyPI rehearsal gate validates an artifact that is not provably the same bytes later uploaded to `pyp",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-4-1-1",
            "title": "The `__reduce__`-plus-explanatory-comment boilerplate for deepcopy/pickle round-trip safety is now hand-duplicated acros",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-4-3-1",
            "title": "`mason environment lock --help` still advertises `--cfe-root`/`--cfe-python`/`--cfe-timeout`, three flags that are silen",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-4-4-1",
            "title": "`mason environment check` should default to the lockfile's own `metadata.platforms` when `--platform` is omitted, becaus",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-4-4-2",
            "title": "every `engines.condalock.check()` test mocks `subprocess.run` against a fixture that real conda-lock would reject, so th",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-4-4-3",
            "title": "`mason environment check --format json` reports `status: \"ok\"` with an empty `errors` array even when the conda-lock sub",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-4-4-4",
            "title": "Story 4.4's spec (`spec-4-4-mason-environment-check.md`) has not been promoted from gitignored `implementation-artifacts",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-10-2",
            "title": "Follow-up review still recommended for 1-10-configuration-surface-logging-and-child-output-streaming after the damping c",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-2-3-2",
            "title": "Follow-up review still recommended for 2-3-credential-isolation after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-5-5-1",
            "title": "The ~26 correct-but-duplicated `_get_data_dir()`/`REPO_ROOT` copies Story 5.5 deliberately left un-migrated to the new s",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-FU-5-5",
            "title": "Follow-up review still recommended for 5-5-rule-2-conda-forge-expert-retrospective after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-5-4-1",
            "title": "SM-4 (free inheritance) recorded provisionally against v8.82.0 — re-confirm at the next organic CFE MINOR",
            "status": "open",
            "severity": "low",
            "triaged": false
          }
        ]
      },
      {
        "project": "pyforge-warden",
        "path": "_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md",
        "open": 41,
        "done": 2,
        "triaged": 41,
        "entries": [
          {
            "id": "DW-1-1-1",
            "title": "The loop's exact `[verify]` command (`pixi run -e python-deptry-osv-scanner python-deptry-osv-sc…",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-BMAD-LOOP-1",
            "title": "`scm.isolation = \\\"worktree\\\"` + `cleanup.trim_artifacts = true` silently lose any dev/review-se…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-4-1",
            "title": "The 1.4 fixture proves offline OSV matching only for the literal pin `pdos-vuln-fixture==1.0.0`;…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-3-1",
            "title": "The report schema has no `runtime_python` field on `ComplianceReport`/the currency section — epi…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-3-2",
            "title": "`scripts/refresh_endoflife_feed.py` fetches one HTTP request per registry product slug with no r…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-3-3",
            "title": "`_resolve_from_lines`/`_resolve_from_cycles` (currency.py) compute `lag` by counting entries rel…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-3-4",
            "title": "`currency.py`'s `DEFAULT_CURRENCY_POLICY` and `config.py`'s `EffectiveConfig.currency_policy` pr…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-3-5",
            "title": "The endoflife.date cache reuses `feeds.DEFAULT_FEED_MAX_AGE_DAYS` (7 days, tuned for KEV's frequ…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-3-6",
            "title": "Both currency resolvers parse and DROP the `lts` boolean (registry `lts_lines` entries and endof…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-3-7",
            "title": "`currency:`/`license:` finding ids (`<axis>:<reason>:<name>@<version>`) carry no ecosystem discr…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-3-8",
            "title": "The frozen 6.1 model invariant (\"currency eol/over-lag finding requires non-null latest/lag/eol_…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-3-9",
            "title": "`ComplianceReport.__post_init__`'s duplicate-finding-id invariant turns ANY producer-side id col…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-FU-6-3",
            "title": "Follow-up review still recommended for 6-3-currency-axis-producer-gate-flags after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": true
          },
          {
            "id": "DW-6-5-1",
            "title": "The bundled `data/lts-registry.yaml` carries a fixed `updated:` date (currently `2026-07-06`) an…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-5-2",
            "title": "The `warn-as-error` exit projection leaves no trace anywhere in the output — the report persists…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-5-3",
            "title": "Under an active gate with an absent/stale feed, `CurrencyEngine.run` (deliberately mirroring `Os…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-7-1",
            "title": "`OsvParse.kev_candidates` (the finding.id -> CVE-alias-tuple mapping populated at OSV-parse time…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-7-2",
            "title": "The EPSS cache reuses `feeds.DEFAULT_FEED_MAX_AGE_DAYS` (7 days) unchanged — the same shared con…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-7-3",
            "title": "The real FIRST.org EPSS feed (~290k rows, republished daily) was poured into cache conventions s…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-7-4",
            "title": "The `feeds.py` atomic-write shape now carries FOUR copies of a latent double-close: if `json.dum…",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-7-5",
            "title": "The conformance-suite helper trio is now duplicated wholesale across feed-enrichment test files…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-8-1",
            "title": "`architecture.md`'s \"Project Structure\" tree (§ around the `waiver.py`/`report.py`/`verdict.py`…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-8-2",
            "title": "`--baseline-emit` stamps every proposed entry with `expires_at = now + waiver_default_expiry_day…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-8-3",
            "title": "An EXPIRED suppression (waiver or baseline) is invisible in the machine-readable contract: `supp…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-8-4",
            "title": "`report-schema.json`'s top-level `suppressions` description (the `\"description\"` string on the `…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-6-8-5",
            "title": "`load_waivers` still parses with plain `yaml.safe_load`, which silently keeps the LAST of two du…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-5-1-1",
            "title": "A hygiene-axis remediation line's manifest+location clause is frequently unavailable because `hy…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-5-1-2",
            "title": "`--doctor` silently no-ops every other `scan` flag it's combined with (`--sbom-output`, `--basel…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-5-1-3",
            "title": "`report._remediation_line`'s vuln branch recovers the advisory id for display by re-splitting th…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-5-1-4",
            "title": "`tests/conftest.py`'s comment describing the ambient offline OSV DB fixture still claims \"its ON…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-5-1-5",
            "title": "The literal argv `[\"deptry\", \"--version\"]` / `[\"osv-scanner\", \"--version\"]` now exists independe…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-5-1-6",
            "title": "`vuln._extract_fixed_version` takes the FIRST well-formed `fixed` event in document order (an in…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-5-1-7",
            "title": "The remediation line's manifest-location clause unions provenance across ALL same-named componen…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-5-1-8",
            "title": "The `manifest_locations` lookup applies PEP-503 canonicalization (`_canonical_subject_key`) to E…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-FU-5-1",
            "title": "Follow-up review still recommended for 5-1-actionable-diagnostics-safe-by-default-posture after the damping cap was spen",
            "status": "open",
            "severity": "low",
            "triaged": true
          },
          {
            "id": "DW-5-2-1",
            "title": "The new `ThreadPoolExecutor`-based 4-axis engine fan-out in `cli.py`'s `_run_scan` changes SIGIN…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-5-2-2",
            "title": "`test_extraction_oracle.py`'s corpus-scale comparison excludes any manifest whose raw text match…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-5-2-3",
            "title": "`scripts/harvest_corpus.py`'s `write_sources_md` hardcodes the 3-bullet \"Hand-authored\" descript…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-5-2-4",
            "title": "`test_perf_overhead.py`'s `REPRESENTATIVE_TARGET` hardcodes a single corpus feedstock path (`rec…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-5-2-5",
            "title": "No CI workflow or scheduled runner ever executes the new `pyforge-warden-test-corpus-oracle` pix…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-5-2-6",
            "title": "`.warden-baseline.yaml`'s first entry hardcodes the running interpreter's patch version in its f…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-5-2-7",
            "title": "All 19 entries in the committed `.warden-baseline.yaml` expire simultaneously at 2027-07-24T00:0…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-CROSS-CUTTING-1",
            "title": "`pixi-build-python` 0.8.3 panics with an unsigned byte-index underflow (`tools.rs:461`, `end byt…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          }
        ]
      },
      {
        "project": "pyforge-herald",
        "path": "_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md",
        "open": 40,
        "done": 5,
        "triaged": 21,
        "entries": [
          {
            "id": "DW-1-1-1",
            "title": "Fresh bmad-loop worktrees can't `pixi run`/`pixi lock`/`pixi install` any brand-new or never-yet…",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-1-2",
            "title": "The `/dist/` and `/dist-conda/` lines in the pixi-package `.gitignore` pattern (copied verbatim…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-1-3",
            "title": "None of `pyforge-warden`/`pyforge-atlas`/`pyforge-herald`'s `pyproject.toml` scope `[tool.hatch.…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-1-4",
            "title": "`pyforge-warden`/`pyforge-atlas`/`pyforge-herald` each declare `license = { text = \"MIT\" }` in `…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-1-5",
            "title": "`pyforge-herald`'s version `\"0.1.0\"` (like warden's/atlas's) is hand-duplicated between the pack…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-1-6",
            "title": "`pyforge-herald`'s root `pixi.toml` feature block pins `python-build = \">=1.5.0\"` with no upper…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-1-7",
            "title": "The verify-gate repair for this story (populating `build_artifacts/linux64` stubs so `pixi run -…",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-1-8",
            "title": "No meta-test enumerates or validates the set of registered pixi environments/features in root `p…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-2-1",
            "title": "`McpTransport` opens one `asyncio.run()`-scoped MCP session per tool call (one extra `initialize…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-2-2",
            "title": "bmad-loop worktree paths longer than ~173 characters make EVERY `pixi` source-package operation…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-2-3",
            "title": "The `DesignTransport` port has no `list_files` or `delete_files` method, but the live `finalize_…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-2-4",
            "title": "`FileRead` drops the server's `untrusted-project-content` provenance marking — the wrapper exist…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-2-5",
            "title": "A conflicted write is returned to the caller as an ordinary success `Mapping`. The live `write_f…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-2-6",
            "title": "`_call_tool_async` — the only code that builds the three auth headers, filters MCP content block…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-2-7",
            "title": "A server-*answered* JSON-RPC error is reported as `TransportUnreachableError`. The `mcp` SDK rai…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-2-8",
            "title": "HTTP 429 and 5xx have no distinct error class — both land on `TransportUnreachableError`, so a r…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-2-9",
            "title": "No request timeout is set on either `streamablehttp_client(...)` or `session.call_tool(...)`, so…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-2-10",
            "title": "`mcp>=1.28.1` is declared with no upper bound in all three manifests while `_call_tool_async` bi…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-2-11",
            "title": "`McpTransport` resolves the credential once and caches it on the instance for the process lifeti…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-2-12",
            "title": "`AuthError` subclasses `TransportError`, so the natural retry predicate for the parent class (`e…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-2-13",
            "title": "`sanitize_payload` collapses two distinct string mapping keys that both name the tokenized previ…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-2-14",
            "title": "`mcp_transport.py` imports `_as_text` and `_as_optional_text` from `base.py` as underscored priv…",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-2-15",
            "title": "`ARCHITECTURE-SPINE.md`'s amended *Etag headers* convention row asserts that `read_file`'s `if_n…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-1-9",
            "title": "Story 1.1's spec was never promoted from the gitignored Tier-3 `implementation-artifacts/` into…",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-4-1",
            "title": "Follow-up review still recommended for 1-4-bridge-core-skeleton-state-errors-determinism-boundar",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-1-4-2",
            "title": "`state.py`'s `write()` does an unlocked read-modify-write of the whole slug-keyed document (read…",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-4-3",
            "title": "`state.py`'s `write()` calls `state_path.parent.mkdir(parents=True, exist_ok=True)` unguarded — …",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1",
            "title": "Follow-up review still recommended for 1-4-bridge-core-skeleton-state-errors-determinism-boundary after the damping cap ",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-1-5-1",
            "title": "`registry.read()` raises \"malformed\" (`expected exactly two body lines, found 5`) against every …",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-6-1",
            "title": "Write-level conflict detection (the wire shape DW-1-2-5 could not pin) is out of `seed`'s scope",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-2",
            "title": "Follow-up review still recommended for 13-1-the-state-layer-survives-a-second-writer after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-3",
            "title": "Follow-up review still recommended for 13-3-db-backed-storage-behind-the-existing-seam-with-migrations after the damping",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-13-3-1",
            "title": "One corrupt legacy JSON file blocks all three Moments' stores, where before Story 13.3 it blocked only its own",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-3-2",
            "title": "A read-only `.herald/` directory now fails every herald command, where before Story 13.3 reads still worked",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-4-1",
            "title": "The webhook's HMAC scheme signs only the body, so one captured signed request stays a valid, reusable forgery token fore",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-4-2",
            "title": "The webhook's claim idempotency guard reads and creates in two separate transactions, so two concurrent deliveries of on",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-4-3",
            "title": "A single webhook request can occupy a thread-pool worker for well over a minute, and neither the handler nor the caller ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-4-4",
            "title": "`herald success create --shipped-date` accepts any string, and one malformed value then breaks `herald success list --da",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-5-1",
            "title": "Evidence revalidation runs unbatched sequential HTTP checks, now reachable unattended via cron instead of only under an ",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-6-1",
            "title": "Steward's `deploy perimeter` cannot target an arbitrary ASGI application, only a hardcoded Django placeholder -- so Hera",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-13-6-2",
            "title": "`webhook_host.py`'s bounded timeout stops the client from waiting, but does not free the OS thread a genuinely-hung hand",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-14-1-1",
            "title": "A gate returning a non-JSON-serializable field value crashes `herald deck qa` with an unhandled `TypeError` instead of a",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-14-1-2",
            "title": "`deck_qa.run()` calls each gate synchronously with no timeout, so a hanging gate blocks the whole `herald deck qa` invoc",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-14-2-1",
            "title": "No CI workflow runs `pyforge-herald`'s pytest suite, so the render gate's Chromium dependency is unprovisioned in CI",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-14-3-1",
            "title": "`image_slot_gate` has no duplicate-manifest-id disambiguation, unlike `render_gate`'s own `seen_ids` guard in the same f",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          }
        ]
      },
      {
        "project": "pyforge-doctor",
        "path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md",
        "open": 28,
        "done": 3,
        "triaged": 4,
        "entries": [
          {
            "id": "DW-1-1-1",
            "title": "The loop's exact `[verify]` command (`pixi run -e pyforge-doctor pyforge-doctor-test`, unfrozen)…",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-1-2",
            "title": "The team's own auto-memory (`project_bmad_loop_worktree_path_length_limit.md`, updated 2026-07-2…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-1-3",
            "title": "Three uncoordinated version constraints exist for the same `hatchling` build backend across the…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-1-1-4",
            "title": "The AD-2 sole-ownership meta-test's AST exit-literal detector (mirroring `pyforge-warden/tests/m…",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-FU-6-4",
            "title": "Follow-up review still recommended for 6-4-the-ledger-verdicts-come-home after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-FU-6-5",
            "title": "Follow-up review still recommended for 6-5-the-board-verdicts-come-home after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-FU-6-6",
            "title": "Follow-up review still recommended for 6-6-the-chain-verdicts-come-home after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-FU-6-8",
            "title": "Follow-up review still recommended for 6-8-bmad-drift-comes-home-without-breaking-the-board after the damping cap was sp",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-FU-7-1",
            "title": "The Review Triage Log's `addressed_findings` never itemizes `defer` entries by the id they were just minted",
            "status": "open",
            "severity": "medium",
            "triaged": false
          },
          {
            "id": "DW-FU-7-1-2",
            "title": "The `DW-FU-{story}` shape this story mints for non-mason stations already has an established, different meaning",
            "status": "open",
            "severity": "medium",
            "triaged": false
          },
          {
            "id": "DW-FU-7-1-3",
            "title": "`bmad-loop-sweep`'s canonical deferred-work format mandates a different id scheme and a dedupe check for the very file t",
            "status": "open",
            "severity": "medium",
            "triaged": false
          },
          {
            "id": "DW-FU-7-1-4",
            "title": "Three stations fall into the emitter's \"every other station\" default whose tracked ledgers use mason's shape exclusively",
            "status": "open",
            "severity": "medium",
            "triaged": false
          },
          {
            "id": "DW-FU-7-1-5",
            "title": "Minting an id converts every new Tier-3 defer into a hard `tier3-only-deferral` FAIL of the always-on deferred-work gate",
            "status": "open",
            "severity": "medium",
            "triaged": false
          },
          {
            "id": "DW-FU-7-1-6",
            "title": "The minted entry carries no `status:`, and giving it an id heading makes it look already-canonical to the one mechanism ",
            "status": "open",
            "severity": "medium",
            "triaged": false
          },
          {
            "id": "DW-5",
            "title": "Follow-up review still recommended for 7-1-the-emitter-mints-identity-at-defer-time after the damping cap was spent",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-FU-7-1-7",
            "title": "marshal's promoter cannot suffix around an id collision, so a minted id that reuses a promoted-follow-up id silently can",
            "status": "open",
            "severity": "medium",
            "triaged": false
          },
          {
            "id": "DW-FU-7-2",
            "title": "Whether the backlog's growth from 470 to 506 predates or postdates Story 7.1's merge is unverified, so this baseline nei",
            "status": "open",
            "severity": "medium",
            "triaged": false
          },
          {
            "id": "DW-FU-7-2-2",
            "title": "A project whose Tier-3 file is deleted can never have its baseline entry lowered or zeroed via `--project`",
            "status": "open",
            "severity": "medium",
            "triaged": false
          },
          {
            "id": "DW-6-11-1",
            "title": "No test in test_sources_factory.py asserts classify()'s literal return string for any rule, including the new spike-repo",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-7-3-1",
            "title": "The committed anonymous-Tier-3 baseline has no automated freshness check, only this landing's one-off manual verificatio",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-CHAIN-COMPLETENESS-1",
            "title": "INV-A's spec-not-decomposed test is a bare substring match, so a Spec can grow capabilities with no stories and still re",
            "status": "open",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-CHAIN-COMPLETENESS-2",
            "title": "Story 12.3's newly-precise INV-A surfaces 7 real CAP-coverage gaps in pyforge-marshal and pyforge-steward that the old b",
            "status": "open",
            "severity": "medium",
            "triaged": false
          },
          {
            "id": "DW-CHAIN-COMPLETENESS-3",
            "title": "`_parse_declared_cap_ids`'s `## Capabilities` heading match is exact-string, case-sensitive, no trailing text, so a SPEC",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-CHAIN-COMPLETENESS-4",
            "title": "Round 4's per-file preamble stripping only strips text BEFORE a file's own first `## ` heading — irrelevant content AFTE",
            "status": "open",
            "severity": "medium",
            "triaged": false
          },
          {
            "id": "DW-CHAIN-COMPLETENESS-5",
            "title": "a source file with NO `## ` heading anywhere is kept whole, unstripped — its entire text (including anything preamble-sh",
            "status": "open",
            "severity": "low",
            "triaged": false
          },
          {
            "id": "DW-11-8-1",
            "title": "CAP-8 (backlog-intake check) split out of Epic 11 — RESOLVED, follow-on Spec + Epic 13 now exist",
            "status": "done",
            "severity": "unspecified",
            "triaged": true
          },
          {
            "id": "DW-FU-12-4",
            "title": "A glob-less, trailing-slash spec-surface entry that can never match (foreign defect, surfaced by Story 12.4's review)",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-FU-12-5",
            "title": "Corrupt committed baseline dies with a raw JSONDecodeError on scoped stamps",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-FU-12-5-2",
            "title": "Zero-discoverable-specs full stamp silently wipes the baseline to `{}` at exit 0",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-14-1-1",
            "title": "GitHub-releases fallback for the 6 npm-invisible bmad-suite packages — RESOLVED",
            "status": "done",
            "severity": "medium",
            "triaged": true
          },
          {
            "id": "DW-12-5-3",
            "title": "The spec-surface baseline write race RECURRED cross-process — scoped stamps from two live processes drop each other's en",
            "status": "open",
            "severity": "medium",
            "triaged": false
          }
        ]
      },
      {
        "project": "pyforge-scribe",
        "path": "_bmad-output/projects/pyforge-scribe/planning-artifacts/deferred-work-ledger.md",
        "open": 7,
        "done": 0,
        "triaged": 0,
        "entries": [
          {
            "id": "DW-1-2-1",
            "title": "source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-2-2",
            "title": "source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-2-3",
            "title": "source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-2-4",
            "title": "source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-2-5",
            "title": "source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-1-2-6",
            "title": "source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          },
          {
            "id": "DW-2-1-3",
            "title": "source_spec: `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md`",
            "status": "open",
            "severity": "unspecified",
            "triaged": false
          }
        ]
      }
    ]
  },
  "status": {
    "source": "sprint-status",
    "running": [],
    "lastShipped": {
      "station": "marshal",
      "story": "11.4",
      "epoch": 1787441447,
      "sha": "b7f89a2d4",
      "subject": "reconcile spec-surface drift for marshal Story 11.4 (verification repair)"
    },
    "runningAvailable": true,
    "generatedAt": "2026-08-23 03:11 UTC",
    "generatedEpoch": 1787454673
  },
  "storySpecs": [
    {
      "station": "pyforge-atlas",
      "done": 57,
      "tracked": 50,
      "gap": 7
    },
    {
      "station": "pyforge-doctor",
      "done": 61,
      "tracked": 50,
      "gap": 11
    },
    {
      "station": "pyforge-herald",
      "done": 58,
      "tracked": 50,
      "gap": 8
    },
    {
      "station": "pyforge-marshal",
      "done": 113,
      "tracked": 65,
      "gap": 48
    },
    {
      "station": "pyforge-mason",
      "done": 47,
      "tracked": 18,
      "gap": 29
    },
    {
      "station": "pyforge-scribe",
      "done": 11,
      "tracked": 11,
      "gap": 0
    },
    {
      "station": "pyforge-steward",
      "done": 53,
      "tracked": 25,
      "gap": 28
    },
    {
      "station": "pyforge-warden",
      "done": 33,
      "tracked": 33,
      "gap": 0
    }
  ],
  "readiness": {
    "rows": [
      {
        "station": "marshal",
        "project": "pyforge-marshal",
        "epicsPath": "_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md",
        "ledgerPath": "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml",
        "specsPath": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs",
        "openSpecs": [
          {
            "slug": "spec-agent-tool-surface",
            "status": "in-progress",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-agent-tool-surface/SPEC.md"
          },
          {
            "slug": "spec-bmad-611-era-alignment",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-611-era-alignment/SPEC.md"
          },
          {
            "slug": "spec-bmad-loop-baseline-drift",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-loop-baseline-drift/SPEC.md"
          },
          {
            "slug": "spec-bmad-loop-intent-gap-work-preservation",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-loop-intent-gap-work-preservation/SPEC.md"
          },
          {
            "slug": "spec-bmad-loop-liveness-footgun",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-loop-liveness-footgun/SPEC.md"
          },
          {
            "slug": "spec-bmad-switch-scope-enforcement",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-switch-scope-enforcement/SPEC.md"
          },
          {
            "slug": "spec-dashboard-project-path-derivation",
            "status": "draft",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-dashboard-project-path-derivation/SPEC.md"
          },
          {
            "slug": "spec-dashboard-velocity-captures-hand-driven-work",
            "status": "draft",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-dashboard-velocity-captures-hand-driven-work/SPEC.md"
          },
          {
            "slug": "spec-dream-to-code-model-self-verification",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-dream-to-code-model-self-verification/SPEC.md"
          },
          {
            "slug": "spec-fleet-chain-completeness",
            "status": "draft",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-fleet-chain-completeness/SPEC.md"
          },
          {
            "slug": "spec-landing-evidence-grammar",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-landing-evidence-grammar/SPEC.md"
          },
          {
            "slug": "spec-loop-home-fleet-refresh",
            "status": "draft",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-loop-home-fleet-refresh/SPEC.md"
          },
          {
            "slug": "spec-marshal-single-story-dispatch",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/SPEC.md"
          },
          {
            "slug": "spec-pyforge-core",
            "status": "draft",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md"
          },
          {
            "slug": "spec-pyforge-testing-charter",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md"
          },
          {
            "slug": "spec-sprint-status-auto-promote",
            "status": "draft",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-sprint-status-auto-promote/SPEC.md"
          },
          {
            "slug": "spec-surface-drift-reconciliation",
            "status": "in-progress",
            "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-surface-drift-reconciliation/SPEC.md"
          }
        ],
        "done": 113,
        "backlog": 49,
        "blocked": 0,
        "total": 162,
        "next": "11-5-referenced-dependency-verification-and-doctor-delegation",
        "blockedKeys": [],
        "backlogKeys": [
          "11-5-referenced-dependency-verification-and-doctor-delegation",
          "11-6-marshal-seed-explain-and-version",
          "12-1-full-pixi-wiring-distribution-and-repo-gate-compliance",
          "12-2-the-local-recipes-empty-plan-oracle",
          "12-3-offline-operation-and-the-egress-counter",
          "12-4-pattern-meta-tests-and-the-never-write-proof",
          "12-5-cli-contract-idempotence-harness-and-performance-gates",
          "12-6-readme-adoption-guide-and-the-finding-remedy-reference"
        ],
        "state": "ready"
      },
      {
        "station": "steward",
        "project": "pyforge-steward",
        "epicsPath": "_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md",
        "ledgerPath": "_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml",
        "specsPath": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs",
        "openSpecs": [
          {
            "slug": "spec-bmad-method-core-upgrade",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/SPEC.md"
          },
          {
            "slug": "spec-bmad-suite-channel-product",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-channel-product/SPEC.md"
          },
          {
            "slug": "spec-developer-machine-bootstrap",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-developer-machine-bootstrap/SPEC.md"
          },
          {
            "slug": "spec-jira-github-projects-sync",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-jira-github-projects-sync/SPEC.md"
          },
          {
            "slug": "spec-local-ocp-hybrid-environment",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-local-ocp-hybrid-environment/SPEC.md"
          },
          {
            "slug": "spec-multi-repo-workspaces",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-multi-repo-workspaces/SPEC.md"
          },
          {
            "slug": "spec-platform-fifteen-factors",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-platform-fifteen-factors/SPEC.md"
          },
          {
            "slug": "spec-python-agent-platform",
            "status": "in-progress",
            "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/SPEC.md"
          },
          {
            "slug": "spec-scratch-worktree-lifecycle",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-scratch-worktree-lifecycle/SPEC.md"
          },
          {
            "slug": "spec-secure-live-dashboards",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-secure-live-dashboards/SPEC.md"
          }
        ],
        "done": 53,
        "backlog": 26,
        "blocked": 0,
        "total": 79,
        "next": "12-3-air-gap-parity-is-a-failing-check",
        "blockedKeys": [],
        "backlogKeys": [
          "12-3-air-gap-parity-is-a-failing-check",
          "12-4-the-cluster-bring-up-is-documented-reproducible-and-key-disciplined",
          "12-5-the-db-gpt-sidecar-joins-the-chart",
          "12-6-redis-is-hardened-still-ephemeral",
          "12-7-the-12-1-tier-3-items-are-verified-on-the-live-cluster",
          "12-8-github-projects-v2-lands-in-github-metrics-via-dlt",
          "13-1-workspace-verbs-over-git-worktree",
          "13-2-status-and-the-feed-mirror-decision"
        ],
        "state": "ready"
      },
      {
        "station": "warden",
        "project": "pyforge-warden",
        "epicsPath": "_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md",
        "ledgerPath": "_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml",
        "specsPath": "_bmad-output/projects/pyforge-warden/planning-artifacts/specs",
        "openSpecs": [
          {
            "slug": "spec-compliance-factory-web-face",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-compliance-factory-web-face/SPEC.md"
          },
          {
            "slug": "spec-package-inventory-eligibility",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-package-inventory-eligibility/SPEC.md"
          }
        ],
        "done": 33,
        "backlog": 3,
        "blocked": 0,
        "total": 36,
        "next": "7-3-cyclonedx-out-the-corpus-in",
        "blockedKeys": [],
        "backlogKeys": [
          "7-3-cyclonedx-out-the-corpus-in",
          "8-1-upload-runs-the-real-engines-async",
          "8-2-results-render-with-derived-progress"
        ],
        "state": "ready"
      },
      {
        "station": "atlas",
        "project": "pyforge-atlas",
        "epicsPath": "_bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md",
        "ledgerPath": "_bmad-output/projects/pyforge-atlas/planning-artifacts/sprint-status-ledger.yaml",
        "specsPath": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs",
        "openSpecs": [
          {
            "slug": "spec-artifactory-download-intelligence",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-artifactory-download-intelligence/SPEC.md"
          },
          {
            "slug": "spec-atlas-query-dashboards",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-query-dashboards/SPEC.md"
          },
          {
            "slug": "spec-conda-forge-packaging-inventory-operations",
            "status": "in-progress",
            "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-conda-forge-packaging-inventory-operations/SPEC.md"
          },
          {
            "slug": "spec-wagtail-corporate-brain",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wagtail-corporate-brain/SPEC.md"
          }
        ],
        "done": 57,
        "backlog": 0,
        "blocked": 0,
        "total": 57,
        "next": "",
        "blockedKeys": [],
        "backlogKeys": [],
        "state": "complete"
      },
      {
        "station": "doctor",
        "project": "pyforge-doctor",
        "epicsPath": "_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md",
        "ledgerPath": "_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml",
        "specsPath": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs",
        "openSpecs": [
          {
            "slug": "spec-deferred-work-visibility",
            "status": "in-progress",
            "path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-deferred-work-visibility/SPEC.md"
          },
          {
            "slug": "spec-sibling-dreams-drift",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-sibling-dreams-drift/SPEC.md"
          }
        ],
        "done": 61,
        "backlog": 0,
        "blocked": 0,
        "total": 61,
        "next": "",
        "blockedKeys": [],
        "backlogKeys": [],
        "state": "complete"
      },
      {
        "station": "herald",
        "project": "pyforge-herald",
        "epicsPath": "_bmad-output/projects/pyforge-herald/planning-artifacts/epics.md",
        "ledgerPath": "_bmad-output/projects/pyforge-herald/planning-artifacts/sprint-status-ledger.yaml",
        "specsPath": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs",
        "openSpecs": [
          {
            "slug": "spec-deck-visual-qa",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-visual-qa/SPEC.md"
          },
          {
            "slug": "spec-herald-moments-2-4-live-backend",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-herald-moments-2-4-live-backend/SPEC.md"
          },
          {
            "slug": "spec-pptx-custom-shapes",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pptx-custom-shapes/SPEC.md"
          },
          {
            "slug": "spec-pptx-deck-generation",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pptx-deck-generation/SPEC.md"
          }
        ],
        "done": 58,
        "backlog": 0,
        "blocked": 0,
        "total": 58,
        "next": "",
        "blockedKeys": [],
        "backlogKeys": [],
        "state": "complete"
      },
      {
        "station": "mason",
        "project": "pyforge-mason",
        "epicsPath": "_bmad-output/projects/pyforge-mason/planning-artifacts/epics.md",
        "ledgerPath": "_bmad-output/projects/pyforge-mason/planning-artifacts/sprint-status-ledger.yaml",
        "specsPath": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs",
        "openSpecs": [
          {
            "slug": "spec-conda-forge-expert-rebuild",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/SPEC.md"
          },
          {
            "slug": "spec-django-accelerator-framework",
            "status": "draft",
            "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-django-accelerator-framework/SPEC.md"
          },
          {
            "slug": "spec-machine-checked-recipe-knowledge",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-machine-checked-recipe-knowledge/SPEC.md"
          },
          {
            "slug": "spec-pixi-container-image",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pixi-container-image/SPEC.md"
          }
        ],
        "done": 47,
        "backlog": 0,
        "blocked": 0,
        "total": 47,
        "next": "",
        "blockedKeys": [],
        "backlogKeys": [],
        "state": "complete"
      },
      {
        "station": "scribe",
        "project": "pyforge-scribe",
        "epicsPath": "_bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md",
        "ledgerPath": "_bmad-output/projects/pyforge-scribe/planning-artifacts/sprint-status-ledger.yaml",
        "specsPath": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs",
        "openSpecs": [
          {
            "slug": "spec-scribe-mines-raw-session-transcripts",
            "status": "ready",
            "path": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-mines-raw-session-transcripts/SPEC.md"
          }
        ],
        "done": 11,
        "backlog": 0,
        "blocked": 0,
        "total": 11,
        "next": "",
        "blockedKeys": [],
        "backlogKeys": [],
        "state": "complete"
      }
    ],
    "totals": {
      "done": 433,
      "backlog": 78,
      "blocked": 0,
      "total": 511
    }
  },
  "fleetProgress": {
    "rows": [
      {
        "key": "atlas",
        "stories": 57,
        "done": 57,
        "blocked": 0,
        "epics": 16,
        "epicsDone": 16,
        "complete": true,
        "running": false,
        "projected": 57
      },
      {
        "key": "doctor",
        "stories": 61,
        "done": 61,
        "blocked": 0,
        "epics": 16,
        "epicsDone": 16,
        "complete": true,
        "running": false,
        "projected": 61
      },
      {
        "key": "herald",
        "stories": 58,
        "done": 58,
        "blocked": 0,
        "epics": 15,
        "epicsDone": 15,
        "complete": true,
        "running": false,
        "projected": 58
      },
      {
        "key": "marshal",
        "stories": 162,
        "done": 113,
        "blocked": 0,
        "epics": 25,
        "epicsDone": 13,
        "complete": false,
        "running": false,
        "projected": 113
      },
      {
        "key": "mason",
        "stories": 47,
        "done": 47,
        "blocked": 0,
        "epics": 9,
        "epicsDone": 9,
        "complete": true,
        "running": false,
        "projected": 47
      },
      {
        "key": "scribe",
        "stories": 11,
        "done": 11,
        "blocked": 0,
        "epics": 3,
        "epicsDone": 3,
        "complete": true,
        "running": false,
        "projected": 11
      },
      {
        "key": "steward",
        "stories": 79,
        "done": 53,
        "blocked": 0,
        "epics": 17,
        "epicsDone": 11,
        "complete": false,
        "running": false,
        "projected": 53
      },
      {
        "key": "warden",
        "stories": 36,
        "done": 33,
        "blocked": 0,
        "epics": 8,
        "epicsDone": 6,
        "complete": false,
        "running": false,
        "projected": 33
      }
    ],
    "total": {
      "stories": 511,
      "done": 433,
      "blocked": 0,
      "epics": 109,
      "epicsDone": 89
    },
    "note": "counts from the tracked sprint ledgers; blocked stories are counted separately because they will not run. Live run state and projections are local-only (`pixi run -e local-recipes fleet-picture`). Live fields present: this is a LOCAL render. A Pages render omits them because CI cannot read tmux or ~/.bmad-loops.",
    "live": {
      "running": [],
      "projected": 433
    }
  }
};
