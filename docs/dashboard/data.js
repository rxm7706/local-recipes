window.DASHBOARD_DATA = {
  "projects": {
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
              "done",
              "Actionable diagnostics & safe-by-default posture"
            ],
            [
              "5.2",
              "done",
              "Fleet-scale validation + corpus / oracle maturation"
            ]
          ]
        },
        {
          "badge": "E6",
          "title": "Multi-axis expansion — license, currency, KEV / EPSS",
          "gatenote": "<b>Epic 6 COMPLETE ✔ — all 10 stories merged.</b> Both hard gates (<code>6.10</code> decision record + <code>6.1</code> schema <code>1.0.0→1.1.0</code>) + 4 axes: <code>6.2</code> license · <code>6.3</code> currency · <code>6.4</code> KEV · <code>6.7</code> EPSS. Plus <code>6.5</code> two-mode policy, <code>6.8</code> baseline/grandfathering, <code>6.9</code> fix-PR actuator (recovered + adversarial-reviewed), and <code>6.6</code> engine version-range pinning (the distribution gate) — <b>1869 green</b>.",
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
              "KEV feed provisioning + the fail-on-kev gate (feeds.py substrate)"
            ],
            [
              "6.5",
              "done",
              "Two-mode policy integration (visibility + flag-gating)"
            ],
            [
              "6.6",
              "done",
              "Engine version-range pinning (the distribution gate)"
            ],
            [
              "6.7",
              "done",
              "EPSS feed + the --min-epss gate"
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
    },
    "regen": {
      "label": "Regen",
      "accentVar": "--regen",
      "branch": "main · in-session Marshal execution",
      "contract": "spec-regenerable-factory · 4 CAPs (surface manifests, backfill waves, spec_surface_check, regeneration drill) · checker never false-greens · Rule 1/2 bound on Wave 4",
      "seglabels": [
        "W0",
        "W1",
        "W2",
        "W3",
        "W4",
        "W5"
      ],
      "epics": [
        {
          "badge": "W0",
          "title": "Foundations — harness + program spec",
          "stories": [
            [
              "0.1",
              "done",
              "Multi-loop isolation harness (worktree loop homes)"
            ],
            [
              "0.2",
              "done",
              "Program spec + waves companion (bmad-spec kernel)"
            ]
          ]
        },
        {
          "badge": "W1",
          "title": "Surface-manifest convention + checker",
          "stories": [
            [
              "1.1",
              "done",
              "Retrofit surface: onto existing kernels"
            ],
            [
              "1.2",
              "done",
              "spec_surface_check v1 — coverage + allowlist + drift"
            ]
          ]
        },
        {
          "badge": "W2",
          "title": "Pilot — factory-console under contract",
          "stories": [
            [
              "2.1",
              "done",
              "Factory-console backfill kernel (docs/dashboard)"
            ],
            [
              "2.2",
              "done",
              "Regeneration drill on generate.py (clean-room rebuild)"
            ]
          ]
        },
        {
          "badge": "W3",
          "title": "Mid backfills",
          "stories": [
            [
              "3.1",
              "done",
              "Enterprise-airgap kernel (_http routing + reference)"
            ],
            [
              "3.2",
              "done",
              "Modernist-identity kernel (DS + deck engine)"
            ]
          ]
        },
        {
          "badge": "W4",
          "title": "Deep backfills — CFE territory (Rule 1/2)",
          "stories": [
            [
              "4.1",
              "done",
              "Packaging-factory kernel over the CFE surface"
            ],
            [
              "4.2",
              "done",
              "Fleet-stewardship kernel (absorbs 3 legacy workflows)"
            ],
            [
              "4.R",
              "done",
              "Rule-2 retro against the conda-forge-expert skill"
            ]
          ]
        },
        {
          "badge": "W5",
          "title": "Closure — verify, gate, drill-through",
          "stories": [
            [
              "5.1",
              "done",
              "Chain-verify + manifests (atlas / bridge / marshal)"
            ],
            [
              "5.2",
              "done",
              "Checker joins the detector test suite"
            ],
            [
              "5.3",
              "done",
              "Dreamscape drill-through links"
            ]
          ]
        }
      ],
      "inflight": null,
      "roadmap": {
        "sub": "Backfill waves per spec-regenerable-factory/waves.md — every realized surface gains a regenerable spec chain; drift checks bind code to contract.",
        "stops": [
          [
            "0",
            "Harness + spec",
            "done"
          ],
          [
            "1",
            "Convention + checker",
            "wip"
          ],
          [
            "2",
            "Pilot + drill",
            ""
          ],
          [
            "3",
            "Mid backfills",
            ""
          ],
          [
            "4",
            "CFE deep + retro",
            ""
          ],
          [
            "5",
            "Gate + drill-through",
            ""
          ]
        ]
      }
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
      "epics": [
        {
          "badge": "E1",
          "title": "Seed a deck into Claude Design",
          "stories": [
            [
              "1.1",
              "done",
              "Package scaffold for pyforge-herald"
            ],
            [
              "1.2",
              "done",
              "Transport port + primary MCP-client adapter (spike)"
            ],
            [
              "1.3",
              "active",
              "Fallback transport adapter"
            ],
            [
              "1.4",
              "pending",
              "Bridge-core skeleton — state, errors, determinism boundary"
            ],
            [
              "1.5",
              "pending",
              "Registry module — README § Design project"
            ],
            [
              "1.6",
              "pending",
              "herald deck seed <slug>"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "Pull Design edits back into the repo",
          "stories": [
            [
              "2.1",
              "pending",
              "deck pull — prototype with etag short-circuit"
            ],
            [
              "2.2",
              "pending",
              "--commit opt-in"
            ],
            [
              "2.3",
              "pending",
              "Marp-source pull"
            ],
            [
              "2.4",
              "pending",
              "Standalone bundle pull"
            ]
          ]
        },
        {
          "badge": "E3",
          "title": "Bridge state at a glance",
          "stories": [
            [
              "3.1",
              "pending",
              "herald deck status [<slug>]"
            ],
            [
              "3.2",
              "pending",
              "Stale hand-mirror detection"
            ]
          ]
        },
        {
          "badge": "E4",
          "title": "Stay in sync automatically",
          "stories": [
            [
              "4.1",
              "pending",
              "Poll loop with quiescence debounce"
            ],
            [
              "4.2",
              "pending",
              "Idle backoff"
            ],
            [
              "4.3",
              "pending",
              "Halt on auth error"
            ]
          ]
        },
        {
          "badge": "E5",
          "title": "Keep Design current with shipped exports",
          "stories": [
            [
              "5.1",
              "pending",
              "Push regenerated exports with etag guard"
            ],
            [
              "5.2",
              "pending",
              "Conflict refusal on export push"
            ]
          ]
        }
      ],
      "inflight": null,
      "velocity": null,
      "timing": null
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
      "epics": [
        {
          "badge": "E1",
          "title": "Walking-skeleton doctor check",
          "stories": [
            [
              "1.1",
              "done",
              "Package scaffold, frozen Finding/DoctorReport contract & exit codes"
            ],
            [
              "1.2",
              "pending",
              "Wrap warden's engine-availability self-check"
            ],
            [
              "1.3",
              "pending",
              "Tri-state, individually addressable checks"
            ],
            [
              "1.4",
              "pending",
              "Credential/environment-hygiene check"
            ],
            [
              "1.5",
              "pending",
              "doctor check CLI wiring, --json, speed budget"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "monitor --fleet",
          "stories": [
            [
              "2.1",
              "pending",
              "Atlas gather filter — staleness axis, MCP-first"
            ],
            [
              "2.2",
              "pending",
              "cve + abandonment watch axes"
            ],
            [
              "2.3",
              "pending",
              "doctor monitor --fleet CLI wiring"
            ]
          ]
        },
        {
          "badge": "E3",
          "title": "diagnose --prescribe",
          "stories": [
            [
              "3.1",
              "pending",
              "Partition findings by actionability"
            ],
            [
              "3.2",
              "pending",
              "Rank the actionable partition"
            ],
            [
              "3.3",
              "pending",
              "Root-cause naming"
            ],
            [
              "3.4",
              "pending",
              "doctor diagnose --prescribe CLI wiring"
            ]
          ]
        }
      ],
      "inflight": null,
      "velocity": null,
      "timing": null
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
      "epics": [
        {
          "badge": "E1",
          "title": "Team Memory — capture & promotion",
          "stories": [
            [
              "1.1",
              "done",
              "Package scaffold + direct capture"
            ],
            [
              "1.2",
              "pending",
              "CLAUDE.md wiring — team memory auto-loads"
            ],
            [
              "1.3",
              "pending",
              "Promotion workflow — proposal-then-confirm"
            ],
            [
              "1.4",
              "pending",
              "Pointer-stub write-back + idempotency"
            ],
            [
              "1.5",
              "pending",
              "Seed promotion — end-to-end proof"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "Knowledge Graph — compile & recall",
          "stories": [
            [
              "2.1",
              "pending",
              "GraphStore port + flat-file v1 adapter"
            ],
            [
              "2.2",
              "pending",
              "Nightly compile from named tool surfaces"
            ],
            [
              "2.3",
              "pending",
              "Fact supersession in the compiled graph"
            ],
            [
              "2.4",
              "pending",
              "scribe recall — grounded, cited answers"
            ]
          ]
        }
      ],
      "inflight": null,
      "velocity": null,
      "timing": null
    }
  },
  "snapshot": "<span>2026-07-25 18:02 UTC</span> · source: sprint-status feeds + merged-PR ground truth (#58–#104) + bmad-loop run journals · timing: Warden = active compute (journals), Atlas = wall-clock (PR timestamps)",
  "defaultProject": "warden",
  "dreams": [
    {
      "slug": "agent-portability",
      "title": "Agent portability — BMAD on any agent, never vendor-locked",
      "status": "seeded",
      "owner": "marshal",
      "chain": {}
    },
    {
      "slug": "agentic-sdlc-autonomy",
      "title": "The Agentic SDLC — four views of autonomy, one governed factory",
      "status": "in-deck",
      "owner": "marshal",
      "chain": {
        "deck": "presentations/agentic-sdlc"
      }
    },
    {
      "slug": "deckcraft",
      "title": "Deckcraft — editable decks from primitives, air-gapped",
      "status": "seeded",
      "owner": "herald",
      "chain": {
        "project": "_bmad-output/projects/deckcraft"
      }
    },
    {
      "slug": "design-code-bridge",
      "title": "The Design↔Code Bridge",
      "status": "realized",
      "owner": "herald",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-design-code-bridge"
      }
    },
    {
      "slug": "enterprise-airgap",
      "title": "The factory behind the firewall",
      "status": "realized",
      "owner": "steward",
      "chain": {
        "spec": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-enterprise-airgap"
      }
    },
    {
      "slug": "factory-console",
      "title": "Factory console — the whole pipeline on one page",
      "status": "realized",
      "owner": "marshal",
      "chain": {
        "spec": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-factory-console"
      }
    },
    {
      "slug": "fleet-stewardship",
      "title": "Fleet stewardship — tend every feedstock we can touch",
      "status": "realized",
      "owner": "mason",
      "chain": {
        "spec": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-fleet-stewardship"
      }
    },
    {
      "slug": "modernist-identity",
      "title": "Modernist identity — one visual language for everything PyForge",
      "status": "realized",
      "owner": "herald",
      "chain": {
        "spec": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-modernist-identity"
      }
    },
    {
      "slug": "packaging-factory",
      "title": "The Packaging Factory",
      "status": "realized",
      "owner": "mason",
      "chain": {
        "deck": "presentations/pyforge-mason",
        "spec": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-packaging-factory"
      }
    },
    {
      "slug": "presenton-pixi-image",
      "title": "Presenton, conda-native — AI decks inside the regulated enterprise",
      "status": "in-spec",
      "owner": "mason",
      "chain": {
        "project": "_bmad-output/projects/presenton-pixi-image"
      }
    },
    {
      "slug": "pyforge-atlas",
      "title": "Atlas — the map that maintains itself",
      "status": "realized",
      "owner": "atlas",
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
      "status": "in-deck",
      "owner": "crew",
      "chain": {
        "deck": "presentations/pyforge-genesis"
      }
    },
    {
      "slug": "pyforge-doctor",
      "title": "Doctor — one bedside manner for the whole fleet",
      "status": "in-spec",
      "owner": "doctor",
      "chain": {
        "deck": "presentations/pyforge-doctor",
        "project": "_bmad-output/projects/pyforge-doctor"
      }
    },
    {
      "slug": "pyforge-genesis",
      "title": "Genesis — the seed of the operating model",
      "status": "in-spec",
      "owner": "crew",
      "chain": {
        "deck": "presentations/pyforge-genesis",
        "project": "_bmad-output/projects/pyforge-genesis"
      }
    },
    {
      "slug": "pyforge-herald",
      "title": "Herald — capture the dream, illustrate the telemetry, proclaim the release",
      "status": "in-spec",
      "owner": "herald",
      "chain": {
        "deck": "presentations/pyforge-herald",
        "project": "_bmad-output/projects/pyforge-herald"
      }
    },
    {
      "slug": "pyforge-marshal",
      "title": "Marshal — autonomy a human can trust",
      "status": "realized",
      "owner": "marshal",
      "chain": {
        "deck": "presentations/pyforge-marshal",
        "spec": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-pyforge-marshal",
        "project": "_bmad-output/projects/pyforge-marshal"
      }
    },
    {
      "slug": "pyforge-scribe",
      "title": "Scribe — the inward voice",
      "status": "in-spec",
      "owner": "scribe",
      "chain": {
        "deck": "presentations/pyforge-scribe",
        "project": "_bmad-output/projects/pyforge-scribe"
      }
    },
    {
      "slug": "pyforge-steward",
      "title": "Steward — provision the line, hold the keys",
      "status": "in-spec",
      "owner": "steward",
      "chain": {
        "deck": "presentations/pyforge-steward",
        "project": "_bmad-output/projects/pyforge-steward"
      }
    },
    {
      "slug": "pyforge-warden",
      "title": "Warden — the gate that never lies",
      "status": "in-spec",
      "owner": "warden",
      "chain": {
        "deck": "presentations/pyforge-warden",
        "project": "_bmad-output/projects/pyforge-warden",
        "program": "warden"
      }
    },
    {
      "slug": "regenerable-factory",
      "title": "Regenerable factory — every line of code under a spec it can be rebuilt from",
      "status": "realized",
      "owner": "marshal",
      "chain": {
        "spec": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-regenerable-factory",
        "program": "regen"
      }
    },
    {
      "slug": "sentinel",
      "title": "Sentinel — the AI Software Factory (the ancestor)",
      "status": "seeded",
      "owner": "scribe",
      "chain": {}
    },
    {
      "slug": "team-memory",
      "title": "Team memory — what the team knows, the agents know",
      "status": "in-spec",
      "owner": "scribe",
      "chain": {}
    },
    {
      "slug": "unity-data-stack",
      "title": "Unity Data Stack — the enterprise innersource platform",
      "status": "in-spec",
      "owner": "crew",
      "chain": {
        "project": "_bmad-output/projects/unity-data-stack"
      }
    },
    {
      "slug": "upstream-discovery",
      "title": "Upstream discovery — package it before it's asked for",
      "status": "in-spec",
      "owner": "atlas",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-upstream-discovery"
      }
    },
    {
      "slug": "wasm-analytics-stack",
      "title": "Wasm-first analytical data stack (OCP-ready)",
      "status": "in-spec",
      "owner": "crew",
      "chain": {
        "project": "_bmad-output/projects/wasm-analytics-stack"
      }
    }
  ],
  "specs": [
    {
      "slug": "enterprise-airgap",
      "project": "local-recipes",
      "title": "the factory behind the firewall",
      "caps": 3,
      "companions": 1,
      "updated": "2026-07-23",
      "dream": "enterprise-airgap",
      "path": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-enterprise-airgap"
    },
    {
      "slug": "factory-console",
      "project": "local-recipes",
      "title": "factory console (program console + Dreamscape)",
      "caps": 4,
      "companions": 1,
      "updated": "2026-07-25",
      "dream": "factory-console",
      "path": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-factory-console"
    },
    {
      "slug": "fleet-stewardship",
      "project": "local-recipes",
      "title": "fleet stewardship (the recipes/ fleet)",
      "caps": 3,
      "companions": 3,
      "updated": "2026-07-23",
      "dream": "fleet-stewardship",
      "path": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-fleet-stewardship"
    },
    {
      "slug": "modernist-identity",
      "project": "local-recipes",
      "title": "one visual language for everything pyforge",
      "caps": 3,
      "companions": 1,
      "updated": "2026-07-23",
      "dream": "modernist-identity",
      "path": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-modernist-identity"
    },
    {
      "slug": "multi-loop-isolation",
      "project": "local-recipes",
      "title": "multi-loop isolation harness",
      "caps": 3,
      "companions": 0,
      "updated": "2026-07-23",
      "dream": "",
      "path": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-multi-loop-isolation"
    },
    {
      "slug": "packaging-factory",
      "project": "local-recipes",
      "title": "the packaging factory (conda-forge-expert machinery)",
      "caps": 4,
      "companions": 2,
      "updated": "2026-07-23",
      "dream": "packaging-factory",
      "path": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-packaging-factory"
    },
    {
      "slug": "pyforge-marshal",
      "project": "local-recipes",
      "title": "Marshal (graduated-autonomy loop orchestration, as shipped)",
      "caps": 4,
      "companions": 3,
      "updated": "2026-07-24",
      "dream": "pyforge-marshal",
      "path": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-pyforge-marshal"
    },
    {
      "slug": "regenerable-factory",
      "project": "local-recipes",
      "title": "regenerable-factory program",
      "caps": 4,
      "companions": 1,
      "updated": "2026-07-23",
      "dream": "regenerable-factory",
      "path": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-regenerable-factory"
    },
    {
      "slug": "pyforge-atlas",
      "project": "pyforge-atlas",
      "title": "pyforge-atlas (chain-verify kernel)",
      "caps": 1,
      "companions": 3,
      "updated": "2026-07-23",
      "dream": "pyforge-atlas",
      "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas"
    },
    {
      "slug": "upstream-discovery",
      "project": "pyforge-atlas",
      "title": "upstream discovery — sense what the world is building",
      "caps": 5,
      "companions": 2,
      "updated": "2026-07-25",
      "dream": "upstream-discovery",
      "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-upstream-discovery"
    },
    {
      "slug": "design-code-bridge",
      "project": "pyforge-herald",
      "title": "herald CLI — the Design↔Code Bridge, formalized",
      "caps": 5,
      "companions": 2,
      "updated": "2026-07-25",
      "dream": "design-code-bridge",
      "path": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-design-code-bridge"
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
      "export": "2026-07-23",
      "path": "presentations/agentic-sdlc"
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
      "path": "presentations/pyforge-atlas"
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
      "path": "presentations/pyforge-doctor"
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
      "path": "presentations/pyforge-genesis"
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
      "path": "presentations/pyforge-herald"
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
      "export": "2026-07-24",
      "path": "presentations/pyforge-marshal"
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
      "path": "presentations/pyforge-mason"
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
      "path": "presentations/pyforge-scribe"
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
      "path": "presentations/pyforge-steward"
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
      "path": "presentations/pyforge-warden"
    }
  ],
  "archived": [
    {
      "name": "Sentinel — knowledge-graph persona",
      "reason": "absorbed",
      "note": "charter absorbed into Scribe ('the graph is the product')",
      "link": "docs/dreams/pyforge-scribe.md"
    },
    {
      "name": "microsoft-conda-forge sweep",
      "reason": "absorbed",
      "note": "absorbed as trendshift Track B (the June 2026 org audit)",
      "link": "docs/specs/trendshift-conda-forge.md"
    },
    {
      "name": "claude.ai Artifact console",
      "reason": "retired",
      "note": "replaced by this GitHub Pages console (2026-07)",
      "link": "docs/dashboard"
    },
    {
      "name": "DB-GPT conda-forge effort",
      "reason": "terminal",
      "note": "delivered externally via staged-recipes #33883 (consume-not-submit, G58)",
      "link": "docs/specs/db-gpt-conda-forge.md"
    },
    {
      "name": "copilot-cli recipe",
      "reason": "blocked",
      "note": "LICENSE §2 standalone-redistribution clause — staged-recipes #32522 rejected",
      "link": "recipes/copilot-cli"
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
          "status": "landed"
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
          "status": "landed"
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
          "status": "landed"
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
          "status": "landed"
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
          "status": "landed"
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
          "status": "landed"
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
          "status": "landed"
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
            "epics": false
          },
          "n": 4,
          "of": 4,
          "status": "landed"
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
            "epics": false
          },
          "n": 4,
          "of": 4,
          "status": "landed"
        },
        {
          "wave": "2d",
          "slug": "pyforge-genesis",
          "model": "opus",
          "depth": "epics",
          "state": "queued",
          "have": {
            "research": true,
            "brief": true,
            "prd": true,
            "architecture": true,
            "epics": true
          },
          "n": 5,
          "of": 5,
          "status": "landed"
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
          "state": "running",
          "note": "line 1 — smallest full product, spec settled 0 OQs",
          "done": 2,
          "total": 17
        },
        {
          "slug": "pyforge-doctor",
          "pkey": "doctor",
          "stories": 12,
          "state": "running",
          "note": "line 2 — consolidative wrap",
          "done": 1,
          "total": 12
        },
        {
          "slug": "pyforge-scribe",
          "pkey": "scribe",
          "stories": 9,
          "state": "running",
          "note": "line 3 — team memory + graph",
          "done": 1,
          "total": 9
        },
        {
          "slug": "pyforge-steward",
          "pkey": null,
          "stories": 18,
          "state": "queued",
          "note": "next free slot",
          "done": 0,
          "total": 18
        },
        {
          "slug": "deckcraft",
          "pkey": null,
          "stories": 28,
          "state": "queued",
          "note": "planned pre-campaign (6 epics); research backfill advisable before launch",
          "done": 0,
          "total": 28
        },
        {
          "slug": "pyforge-mason",
          "pkey": null,
          "stories": 38,
          "state": "queued",
          "note": "longest persona line; CFE Rule-2 retro at closeout",
          "done": 0,
          "total": 38
        },
        {
          "slug": "presenton-pixi-image",
          "pkey": null,
          "stories": 30,
          "state": "held",
          "note": "operator Phase-0 gates: MS disconnected-stack check + memory-subsystem scope",
          "done": 0,
          "total": 30
        },
        {
          "slug": "pyforge-marshal",
          "pkey": null,
          "stories": 40,
          "state": "held",
          "note": "AD-25–39 adversarial pass + floor quiescence (touches loop machinery)",
          "done": 0,
          "total": 40
        },
        {
          "slug": "pyforge-genesis",
          "pkey": null,
          "stories": 36,
          "state": "held",
          "note": "last — model stability + consumes marshal-owned scripts",
          "done": 0,
          "total": 36
        },
        {
          "slug": "wasm-analytics-stack",
          "pkey": null,
          "stories": 0,
          "state": "future",
          "note": "PRD+arch only by design; stories decompose when scheduled",
          "done": 0,
          "total": 0
        },
        {
          "slug": "unity-data-stack",
          "pkey": null,
          "stories": 0,
          "state": "future",
          "note": "PRD+arch only by design; stories decompose when scheduled",
          "done": 0,
          "total": 0
        }
      ]
    }
  ]
};
