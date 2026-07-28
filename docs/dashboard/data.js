window.DASHBOARD_DATA = {
  "projects": {
    "deckcraft": {
      "label": "Deckcraft",
      "accentVar": "--accent",
      "branch": "not started",
      "contract": "spec-deckcraft",
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
          "title": "Foundation",
          "stories": [
            [
              "1.1",
              "pending",
              "Project scaffolding and pyproject.toml"
            ],
            [
              "1.2",
              "pending",
              "Platform adapter (paths, RAM, GPU detection)"
            ],
            [
              "1.3",
              "pending",
              "LLM adapter layer (pydantic-ai + 4 backends)"
            ],
            [
              "1.4",
              "pending",
              "Document extractor (markitdown wrapper)"
            ],
            [
              "1.5",
              "pending",
              "Pydantic data model (types.py)"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "Renderers",
          "stories": [
            [
              "2.1",
              "pending",
              "PPTX engine adapter (wraps python-pptx with vendor-fallback hooks)"
            ],
            [
              "2.2",
              "pending",
              "Marp engine (subprocess to marp-cli)"
            ],
            [
              "2.3",
              "pending",
              "Chart renderer (matplotlib + plotly)"
            ],
            [
              "2.4",
              "pending",
              "Mermaid renderer (mermaid-py + playwright headless, fully offline)"
            ],
            [
              "2.5",
              "pending",
              "Asset pipeline with caching + graceful degradation"
            ]
          ]
        },
        {
          "badge": "E3",
          "title": "Style + AI",
          "stories": [
            [
              "3.1",
              "pending",
              "Style loader — PPTX (.potx + .pptx including --as-sample mode) + DOCX"
            ],
            [
              "3.2",
              "pending",
              "Style loader — PDF with OCR fallback (FR-46c)"
            ],
            [
              "3.3",
              "pending",
              "Retrieval module — sentence-transformers RAG + slide dedup"
            ],
            [
              "3.4",
              "pending",
              "LLM outline generator (prompts + JSON-schema-validated output)"
            ],
            [
              "3.5",
              "pending",
              "Image understander (Ollama qwen2.5vl + llama.cpp mmproj fallback)"
            ],
            [
              "3.6",
              "pending",
              "Image generator (diffusers + SDXL-Turbo, opt-in default-off, lazy-load)"
            ],
            [
              "3.7",
              "pending",
              "Layout mapper + bundled templates (default-professional + bmad-prd-pitch)"
            ]
          ]
        },
        {
          "badge": "E4",
          "title": "Surfaces",
          "stories": [
            [
              "4.1",
              "pending",
              "Pipeline class (high-level public API)"
            ],
            [
              "4.2",
              "pending",
              "CLI (typer-based, deckcraft generate / init / describe-image / convert)"
            ],
            [
              "4.3",
              "pending",
              "MCP server (fastmcp stdio transport)"
            ],
            [
              "4.4",
              "pending",
              "Claude Skill (.claude/skills/deck-builder/)"
            ]
          ]
        },
        {
          "badge": "E5",
          "title": "Distribution",
          "stories": [
            [
              "5.1",
              "pending",
              "conda-forge recipe at `recipes/deckcraft/`"
            ],
            [
              "5.2",
              "pending",
              "Default templates (default-professional.potx + bmad-prd-pitch.potx)"
            ],
            [
              "5.3",
              "pending",
              "README + air-gapped deployment guide + BYO style guide"
            ]
          ]
        },
        {
          "badge": "E6",
          "title": "Polish",
          "stories": [
            [
              "6.1",
              "pending",
              "Spike-0 benchmark on Framework laptop (CRITICAL PATH)"
            ],
            [
              "6.2",
              "pending",
              "Spike-1 (full-deck) and Spike-2 (per-machine) benchmarks"
            ],
            [
              "6.3",
              "pending",
              "Pattern enforcement test suite (P-01 through P-10)"
            ],
            [
              "6.4",
              "pending",
              "Cross-platform CI matrix (linux-64 + osx-arm64 + win-64)"
            ],
            [
              "6.5",
              "pending",
              "Air-gapped CI under unshare -n (Linux)"
            ],
            [
              "6.6",
              "pending",
              "Golden-path test fixtures (5 prompts → expected pptx structure)"
            ]
          ]
        }
      ],
      "owner": "herald",
      "practice": false
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
              "Program spec + waves companion (bmad-spec Spec)"
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
              "Retrofit surface: onto existing Specs"
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
              "Factory-console backfill Spec (docs/dashboard)"
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
              "Enterprise-airgap Spec (_http routing + reference)"
            ],
            [
              "3.2",
              "done",
              "Modernist-identity Spec (DS + deck engine)"
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
              "Packaging-factory Spec over the CFE surface"
            ],
            [
              "4.2",
              "done",
              "Fleet-stewardship Spec (absorbs 3 legacy workflows)"
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
      },
      "lineState": {
        "state": "complete",
        "at": ""
      },
      "owner": "marshal",
      "practice": true
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
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals.",
        "bars": [
          [
            "1.1",
            101
          ]
        ],
        "foot": [
          [
            "~101 min",
            "median / story",
            "var(--done)"
          ],
          [
            "101 min",
            "observed range",
            ""
          ],
          [
            "1/12",
            "stories complete",
            "var(--done)"
          ],
          [
            "11",
            "remaining",
            ""
          ]
        ]
      },
      "timing": {
        "derived": true,
        "metric": "active agent-compute per story (dev + review; excludes gate-pause wait) — from bmad-loop run journals",
        "total": 101,
        "totalLabel": "~1.7 h active compute",
        "note": "Derived from 1 measured story; a story still in flight contributes only its closed sessions.",
        "perStory": {
          "1.1": 101
        },
        "epicMin": {
          "E1": 101
        }
      },
      "lineState": {
        "state": "paused",
        "at": "1.2"
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
              "pending",
              "Wrap warden's engine-availability self-check (FR-1)"
            ],
            [
              "1.3",
              "pending",
              "Tri-state, individually addressable checks (FR-2)"
            ],
            [
              "1.4",
              "pending",
              "Credential/environment-hygiene check (FR-3)"
            ],
            [
              "1.5",
              "pending",
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
              "pending",
              "Atlas gather filter — staleness axis, MCP-first with CLI fallback (FR-5, AD-6)"
            ],
            [
              "2.2",
              "pending",
              "cve and abandonment watch axes (FR-4)"
            ],
            [
              "2.3",
              "pending",
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
              "pending",
              "Partition findings by actionability (FR-6, AD-4)"
            ],
            [
              "3.2",
              "pending",
              "Rank the actionable partition (FR-7, AD-4)"
            ],
            [
              "3.3",
              "pending",
              "Root-cause naming (FR-8)"
            ],
            [
              "3.4",
              "pending",
              "`doctor diagnose --target … --prescribe` CLI wiring, `--json` (FR-9)"
            ]
          ]
        }
      ],
      "owner": "doctor",
      "practice": false
    },
    "genesis": {
      "label": "Genesis",
      "accentVar": "--accent",
      "branch": "not started",
      "contract": "spec-pyforge-genesis · the seed: install the operating model anywhere (greenfield + brownfield)",
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
          "title": "Foundation & the Write Guard",
          "stories": [
            [
              "1.1",
              "pending",
              "Package skeleton as a pixi workspace member"
            ],
            [
              "1.2",
              "pending",
              "Error taxonomy and exit codes"
            ],
            [
              "1.3",
              "pending",
              "The `fs` write primitive and the never-write guard"
            ],
            [
              "1.4",
              "pending",
              "Manifest schema, loader, and model-version ranges"
            ],
            [
              "1.5",
              "pending",
              "The V1 extraction manifest (the model, as data)"
            ],
            [
              "1.6",
              "pending",
              "Spike-0 — Copier API fit (CRITICAL GATE)"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "The Managed-Region Engine",
          "stories": [
            [
              "2.1",
              "pending",
              "Marker grammar and the per-format registry"
            ],
            [
              "2.2",
              "pending",
              "Region parser — span discovery, nesting rejection, fence awareness"
            ],
            [
              "2.3",
              "pending",
              "Span substitution — the update primitive"
            ],
            [
              "2.4",
              "pending",
              "Anchor resolution and region insertion"
            ],
            [
              "2.5",
              "pending",
              "Marker deletion as a sanctioned opt-out"
            ]
          ]
        },
        {
          "badge": "E3",
          "title": "Detect & Plan",
          "stories": [
            [
              "3.1",
              "pending",
              "Findings model — severity, types, remedies"
            ],
            [
              "3.2",
              "pending",
              "Repo inventory walker and artifact classification"
            ],
            [
              "3.3",
              "pending",
              "Content hashing for managed files and regions"
            ],
            [
              "3.4",
              "pending",
              "Legacy convention detection"
            ],
            [
              "3.5",
              "pending",
              "Manifest coverage check"
            ],
            [
              "3.6",
              "pending",
              "Plan and Action types, repo fingerprint, and the plan builder"
            ]
          ]
        },
        {
          "badge": "E4",
          "title": "Materialize & the Core Verbs",
          "stories": [
            [
              "4.1",
              "pending",
              "Copier engine wrapper — the single seam"
            ],
            [
              "4.2",
              "pending",
              "State schema and the atomic store"
            ],
            [
              "4.3",
              "pending",
              "The apply runner — transactional, guarded"
            ],
            [
              "4.4",
              "pending",
              "Preconditions, refusals, and skips"
            ],
            [
              "4.5",
              "pending",
              "`genesis check`"
            ],
            [
              "4.6",
              "pending",
              "`genesis adopt`"
            ],
            [
              "4.7",
              "pending",
              "`genesis init`"
            ]
          ]
        },
        {
          "badge": "E5",
          "title": "Derive, Migrate & Update",
          "stories": [
            [
              "5.1",
              "pending",
              "Neutral contract and agent-adapter fan-out"
            ],
            [
              "5.2",
              "pending",
              "`PROJECTS.md` index and artifact-symlink derivation"
            ],
            [
              "5.3",
              "pending",
              "Migration registry and runner"
            ],
            [
              "5.4",
              "pending",
              "`genesis update` — two-phase"
            ],
            [
              "5.5",
              "pending",
              "Referenced-dependency verification and Doctor delegation"
            ],
            [
              "5.6",
              "pending",
              "`genesis explain` and `genesis version`"
            ]
          ]
        },
        {
          "badge": "E6",
          "title": "Packaging, Oracle & Hardening",
          "stories": [
            [
              "6.1",
              "pending",
              "Full pixi wiring, distribution, and repo-gate compliance"
            ],
            [
              "6.2",
              "pending",
              "The `local-recipes` empty-plan oracle (CRITICAL)"
            ],
            [
              "6.3",
              "pending",
              "Offline operation and the egress counter"
            ],
            [
              "6.4",
              "pending",
              "Pattern meta-tests and the never-write proof"
            ],
            [
              "6.5",
              "pending",
              "CLI contract, idempotence harness, and performance gates"
            ],
            [
              "6.6",
              "pending",
              "README, adoption guide, and the finding→remedy reference"
            ]
          ]
        }
      ],
      "owner": "marshal",
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
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals.",
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
            16
          ]
        ],
        "foot": [
          [
            "~60 min",
            "median / story",
            "var(--done)"
          ],
          [
            "16–98 min",
            "observed range",
            ""
          ],
          [
            "2/17",
            "stories complete",
            "var(--done)"
          ],
          [
            "15",
            "remaining",
            ""
          ]
        ]
      },
      "timing": {
        "derived": true,
        "metric": "active agent-compute per story (dev + review; excludes gate-pause wait) — from bmad-loop run journals",
        "total": 174,
        "totalLabel": "~2.9 h active compute",
        "note": "Derived from 3 measured stories; a story still in flight contributes only its closed sessions.",
        "perStory": {
          "1.1": 60,
          "1.2": 98,
          "1.3": 16
        },
        "epicMin": {
          "E1": 174
        }
      },
      "lineState": {
        "state": "paused",
        "at": "1.3"
      },
      "epics": [
        {
          "badge": "E1",
          "title": "Seed a deck into Claude Design",
          "stories": [
            [
              "1.1",
              "done",
              "Package scaffold for `pyforge-herald`"
            ],
            [
              "1.2",
              "done",
              "Transport port + primary MCP-client adapter (the transport spike)"
            ],
            [
              "1.3",
              "pending",
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
              "`herald deck seed <slug>`"
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
              "`herald deck pull <slug>` — prototype pull with etag short-circuit"
            ],
            [
              "2.2",
              "pending",
              "`--commit` opt-in"
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
          "title": "See the bridge's state at a glance",
          "stories": [
            [
              "3.1",
              "pending",
              "`herald deck status [<slug>]`"
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
          "title": "Keep Design current with the shipped exports",
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
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals.",
        "bars": [
          [
            "1.1",
            165
          ]
        ],
        "foot": [
          [
            "~165 min",
            "median / story",
            "var(--done)"
          ],
          [
            "165 min",
            "observed range",
            ""
          ],
          [
            "1/41",
            "stories complete",
            "var(--done)"
          ],
          [
            "40",
            "remaining",
            ""
          ]
        ]
      },
      "timing": {
        "derived": true,
        "metric": "active agent-compute per story (dev + review; excludes gate-pause wait) — from bmad-loop run journals",
        "total": 165,
        "totalLabel": "~2.8 h active compute",
        "note": "Derived from 1 measured story; a story still in flight contributes only its closed sessions.",
        "perStory": {
          "1.1": 165
        },
        "epicMin": {
          "E1": 165
        }
      },
      "lineState": {
        "state": "paused",
        "at": "1.2"
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
              "pending",
              "Story identity, merge-subject rendering, and feed completeness"
            ],
            [
              "1.3",
              "pending",
              "Layered policy composition with provenance and validation"
            ],
            [
              "1.10",
              "pending",
              "Render the harness policy from the canonical EffectivePolicy"
            ],
            [
              "1.4",
              "pending",
              "Provision a loop home"
            ],
            [
              "1.5",
              "pending",
              "Single-sourced Tier-3 store via backlink"
            ],
            [
              "1.6",
              "pending",
              "Isolation verification and home enumeration"
            ],
            [
              "1.7",
              "pending",
              "Preflight, adapter config seeding, and first-run acknowledgement"
            ],
            [
              "1.8",
              "pending",
              "Teardown that refuses to destroy work"
            ],
            [
              "1.9",
              "pending",
              "Packaging, distribution, and version reporting"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "Gates you can run",
          "stories": [
            [
              "2.1",
              "pending",
              "Standalone verify-command runner, project-scoped"
            ],
            [
              "2.2",
              "pending",
              "Verdict aggregation that never false-greens"
            ],
            [
              "2.3",
              "pending",
              "Frozen-surface scope check, narrowing only"
            ],
            [
              "2.4",
              "pending",
              "Doc-only story classification"
            ],
            [
              "2.5",
              "pending",
              "Gate mode ladder with autonomy labels"
            ],
            [
              "2.6",
              "pending",
              "Gate evidence record with redaction at egress"
            ]
          ]
        },
        {
          "badge": "E3",
          "title": "Supervised unattended runs",
          "stories": [
            [
              "3.1",
              "pending",
              "Run identity and the journal writer"
            ],
            [
              "3.2",
              "pending",
              "The journal fold — one producer for accumulating run state"
            ],
            [
              "3.3",
              "pending",
              "Detached launch with scoped story selection"
            ],
            [
              "3.4",
              "pending",
              "Supervisor process lifecycle"
            ],
            [
              "3.5",
              "pending",
              "Idle-strand detection"
            ],
            [
              "3.6",
              "pending",
              "Budget ceilings and the heaviest-story advisory"
            ],
            [
              "3.7",
              "pending",
              "Escalation, deferral, and resume"
            ]
          ]
        },
        {
          "badge": "E4",
          "title": "Landing with a durable paper trail",
          "stories": [
            [
              "4.1",
              "pending",
              "Story-spec promotion with a durability predicate"
            ],
            [
              "4.2",
              "pending",
              "Teardown reachability and spec-recovery assistance"
            ],
            [
              "4.3",
              "pending",
              "Merge-subject conformance and review-cap landing"
            ],
            [
              "4.4",
              "pending",
              "Batch pull request with hygiene preflight"
            ],
            [
              "4.5",
              "pending",
              "Feed refresh with truth partitioned by domain"
            ],
            [
              "4.6",
              "pending",
              "Deploy idempotence and reconciliation of open intents"
            ]
          ]
        },
        {
          "badge": "E5",
          "title": "Fleet visibility",
          "stories": [
            [
              "5.1",
              "pending",
              "Fleet view"
            ],
            [
              "5.2",
              "pending",
              "Per-run detail"
            ],
            [
              "5.3",
              "pending",
              "Escalation queue"
            ],
            [
              "5.4",
              "pending",
              "Ledger-vs-git reconciliation and the versioned status contract"
            ]
          ]
        },
        {
          "badge": "E6",
          "title": "Portability proven",
          "stories": [
            [
              "6.1",
              "pending",
              "Profile-driven adapter selection, project-scoped"
            ],
            [
              "6.2",
              "pending",
              "Skill-tree projection"
            ],
            [
              "6.3",
              "pending",
              "Projection drift detection that can actually fail"
            ],
            [
              "6.4",
              "pending",
              "Adapter probe with a machine-scoped record"
            ],
            [
              "6.5",
              "pending",
              "Conformance smoke in an ephemeral home"
            ],
            [
              "6.6",
              "pending",
              "The conformance matrix"
            ],
            [
              "6.7",
              "pending",
              "Entry-file family drift check, detect-only"
            ],
            [
              "6.8",
              "pending",
              "Upstream contribution register"
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
      "velocity": "",
      "timing": "",
      "lineState": {
        "state": "paused",
        "at": "1.2"
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
              "pending",
              "CLI noun-verb structure and global flags"
            ],
            [
              "1.3",
              "pending",
              "Error taxonomy and exit-code contract"
            ],
            [
              "1.4",
              "pending",
              "Dual output format with stream discipline"
            ],
            [
              "1.5",
              "pending",
              "CFE root resolution chain"
            ],
            [
              "1.6",
              "pending",
              "Interpreter selection and CFE import-floor probe"
            ],
            [
              "1.7",
              "pending",
              "Degradation when CFE is unavailable"
            ],
            [
              "1.8",
              "pending",
              "`mason doctor`"
            ],
            [
              "1.9",
              "pending",
              "Fake CFE root fixture and test harness"
            ],
            [
              "1.10",
              "pending",
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
              "pending",
              "The CFE port"
            ],
            [
              "2.2",
              "pending",
              "The seam guard"
            ],
            [
              "2.3",
              "pending",
              "Credential isolation"
            ],
            [
              "2.4",
              "pending",
              "`mason recipe new`"
            ],
            [
              "2.5",
              "pending",
              "`mason recipe validate`"
            ],
            [
              "2.6",
              "pending",
              "`mason recipe build`"
            ],
            [
              "2.7",
              "pending",
              "`mason recipe diagnose`"
            ],
            [
              "2.8",
              "pending",
              "`mason recipe optimize` and `mason recipe scan`"
            ],
            [
              "2.9",
              "pending",
              "`mason recipe submit`"
            ],
            [
              "2.10",
              "pending",
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
              "pending",
              "Engine protocol and provisioning"
            ],
            [
              "3.2",
              "pending",
              "`mason package build`"
            ],
            [
              "3.3",
              "pending",
              "Ship-target vocabulary and dry-run default"
            ],
            [
              "3.4",
              "pending",
              "The `pypi` ship target"
            ],
            [
              "3.5",
              "pending",
              "The `channel:<name>` ship target"
            ],
            [
              "3.6",
              "pending",
              "The `conda-forge` ship target"
            ],
            [
              "3.9",
              "pending",
              "The `ship` verb and TestPyPI rehearsal"
            ],
            [
              "3.7",
              "pending",
              "Asymmetric receipts, partial failure, and idempotence"
            ],
            [
              "3.8",
              "pending",
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
              "pending",
              "Lock engine adapter and provenance"
            ],
            [
              "4.2",
              "pending",
              "Manifest discovery"
            ],
            [
              "4.3",
              "pending",
              "`mason environment lock`"
            ],
            [
              "4.4",
              "pending",
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
              "pending",
              "CFE-independence test"
            ],
            [
              "5.2",
              "pending",
              "Governance test"
            ],
            [
              "5.3",
              "pending",
              "Delegation-fidelity test"
            ],
            [
              "5.4",
              "pending",
              "Free-inheritance verification"
            ],
            [
              "5.5",
              "pending",
              "Rule-2 conda-forge-expert retrospective"
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
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals.",
        "bars": [
          [
            "1.1",
            70
          ]
        ],
        "foot": [
          [
            "~70 min",
            "median / story",
            "var(--done)"
          ],
          [
            "70 min",
            "observed range",
            ""
          ],
          [
            "1/9",
            "stories complete",
            "var(--done)"
          ],
          [
            "8",
            "remaining",
            ""
          ]
        ]
      },
      "timing": {
        "derived": true,
        "metric": "active agent-compute per story (dev + review; excludes gate-pause wait) — from bmad-loop run journals",
        "total": 70,
        "totalLabel": "~1.2 h active compute",
        "note": "Derived from 1 measured story; a story still in flight contributes only its closed sessions.",
        "perStory": {
          "1.1": 70
        },
        "epicMin": {
          "E1": 70
        }
      },
      "lineState": {
        "state": "paused",
        "at": "1.2"
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
              "pending",
              "`CLAUDE.md` wiring — team memory loads automatically"
            ],
            [
              "1.3",
              "pending",
              "Promotion workflow — proposal-then-confirm, team-voice rewrite"
            ],
            [
              "1.4",
              "pending",
              "Pointer-stub write-back + idempotent re-invocation"
            ],
            [
              "1.5",
              "pending",
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
              "pending",
              "`GraphStore` port + flat-file v1 adapter"
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
              "`scribe recall` — grounded, cited answers"
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
      "velocity": "",
      "timing": "",
      "lineState": {
        "state": "paused",
        "at": "1.2"
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
              "pending",
              "Credentials never attach outside their declared host, and the JFrog leak can never recur silently"
            ],
            [
              "1.3",
              "pending",
              "Secrets Steward stores live encrypted in Git, never as plaintext"
            ],
            [
              "1.4",
              "pending",
              "Rotating a key never breaks what already trusted it"
            ],
            [
              "1.5",
              "pending",
              "The operator can see every credential Steward knows about, never a secret value"
            ],
            [
              "1.6",
              "pending",
              "The operator can ask \"is anything host-unscoped right now?\" and get a real answer"
            ],
            [
              "1.7",
              "pending",
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
              "pending",
              "The dashboard builds through Steward, not a bare pixi task the operator has to remember"
            ],
            [
              "2.2",
              "pending",
              "Nothing happens unless something actually changed"
            ],
            [
              "2.3",
              "pending",
              "The operator can see what would change before it changes"
            ],
            [
              "2.4",
              "pending",
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
              "pending",
              "Any named pixi environment materializes with one command"
            ],
            [
              "3.2",
              "pending",
              "A bmad-loop runner and its environment materialize together"
            ],
            [
              "3.3",
              "pending",
              "The operator can see every environment that exists, before picking one"
            ],
            [
              "3.4",
              "pending",
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
              "pending",
              "A ceiling can be declared, machine-readably"
            ],
            [
              "4.2",
              "pending",
              "The declared ceiling is one command away"
            ],
            [
              "4.3",
              "pending",
              "Asking \"am I under budget?\" never lies"
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
        "state": "complete",
        "at": ""
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
        }
      ],
      "owner": "warden",
      "practice": false
    },
    "atlas": {
      "label": "Atlas",
      "accentVar": "--atlas",
      "branch": "Waves 0–H shipped · Wave I post-audit truth-up in progress",
      "contract": "Kedro + pixi · DuckDB singularity · nebi-scaffolded · 8 Vizro pages shipped (28-CLI inventory deferred, DW-D2-1) · migrates cf_atlas (phases B→N) to a typed, incremental data pipeline",
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
        },
        {
          "badge": "10",
          "title": "Wave I — Post-audit truth-up (Round-3 findings, PR #131 branch abandoned)",
          "stories": [
            [
              "I0",
              "done",
              "Atlas dependency completeness — unblock kedro-test (AUD-ATLAS-010/013)"
            ],
            [
              "I1",
              "done",
              "Kernel + companion truth-up: retract the false run-admission claim (AUD-ATLAS-046/041/047/049)"
            ],
            [
              "I2",
              "done",
              "Uniform story-spec frontmatter + README reversal (AUD-ATLAS-045/048)"
            ],
            [
              "I3",
              "pending",
              "pandas 3.0 None-identity contracts — FIRST loop story, kedro-test is red until it lands (AUD-ATLAS-011)"
            ],
            [
              "I4",
              "pending",
              "AD-17 advisory timestamps: MCP read_dataset envelope + per-page build stamps (AUD-ATLAS-043/044)"
            ],
            [
              "I5",
              "pending",
              "Run admission / single-writer — DW-AD23-1, re-promotes AD-23 (AUD-ATLAS-046 impl half)"
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
      },
      "lineState": {
        "state": "paused",
        "at": "I3"
      },
      "owner": "atlas",
      "practice": false
    }
  },
  "snapshot": "<span>2026-07-28 09:48 UTC</span> · source: sprint-status feeds + merged-PR ground truth (#58–#104) + bmad-loop run journals · timing: Warden = active compute (journals), Atlas = wall-clock (PR timestamps)",
  "defaultProject": "warden",
  "dreams": [
    {
      "slug": "agent-portability",
      "title": "Agent portability — BMAD on any agent, never vendor-locked",
      "status": "dreamt",
      "owner": "marshal",
      "type": "practice",
      "chain": {}
    },
    {
      "slug": "agent-tool-surface",
      "title": "Agent tool surface — every craft reachable through one governed API",
      "status": "realized",
      "owner": "marshal",
      "type": "dream",
      "chain": {}
    },
    {
      "slug": "agentic-sdlc-autonomy",
      "title": "The Agentic SDLC — four views of autonomy, one governed factory",
      "status": "pitched",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "deck": "presentations/agentic-sdlc"
      }
    },
    {
      "slug": "artifact-console",
      "title": "Artifact console — the factory board, hosted as a chat artifact",
      "status": "archived",
      "owner": "marshal",
      "type": "dream",
      "chain": {},
      "archived_reason": "retired"
    },
    {
      "slug": "copilot-cli-packaging",
      "title": "copilot-cli on conda-forge — blocked at the license",
      "status": "archived",
      "owner": "mason",
      "type": "dream",
      "chain": {},
      "archived_reason": "blocked"
    },
    {
      "slug": "db-gpt-packaging",
      "title": "DB-GPT on conda-forge — the multi-output agent stack",
      "status": "archived",
      "owner": "mason",
      "type": "dream",
      "chain": {},
      "archived_reason": "terminal"
    },
    {
      "slug": "deckcraft",
      "title": "Deckcraft — editable decks from primitives, air-gapped",
      "status": "specified",
      "owner": "herald",
      "type": "dream",
      "chain": {
        "deck": "presentations/deckcraft",
        "spec": "_bmad-output/projects/deckcraft/planning-artifacts/specs/spec-deckcraft",
        "project": "_bmad-output/projects/deckcraft"
      }
    },
    {
      "slug": "design-code-bridge",
      "title": "The Design↔Code Bridge",
      "status": "realized",
      "owner": "herald",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-design-code-bridge"
      }
    },
    {
      "slug": "enterprise-airgap",
      "title": "The factory behind the firewall",
      "status": "realized",
      "owner": "steward",
      "type": "practice",
      "chain": {
        "spec": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-enterprise-airgap"
      }
    },
    {
      "slug": "factory-console",
      "title": "Factory console — the whole pipeline on one page",
      "status": "realized",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-factory-console"
      }
    },
    {
      "slug": "fleet-stewardship",
      "title": "Fleet stewardship — tend every feedstock we can touch",
      "status": "realized",
      "owner": "mason",
      "type": "practice",
      "chain": {
        "spec": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-fleet-stewardship"
      }
    },
    {
      "slug": "microsoft-org-sweep",
      "title": "Microsoft org sweep — audit one upstream org, package what is missing",
      "status": "archived",
      "owner": "atlas",
      "type": "dream",
      "chain": {},
      "archived_reason": "absorbed"
    },
    {
      "slug": "modernist-identity",
      "title": "Modernist identity — one visual language for everything PyForge",
      "status": "realized",
      "owner": "herald",
      "type": "practice",
      "chain": {
        "spec": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-modernist-identity"
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
        "spec": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-packaging-factory"
      }
    },
    {
      "slug": "presenton-pixi-image",
      "title": "Presenton, conda-native — AI decks inside the regulated enterprise",
      "status": "specified",
      "owner": "mason",
      "type": "dream",
      "chain": {
        "deck": "presentations/presenton-pixi-image",
        "spec": "_bmad-output/projects/presenton-pixi-image/planning-artifacts/specs/spec-presenton-pixi-image",
        "project": "_bmad-output/projects/presenton-pixi-image"
      },
      "blockedOn": "Phase-0 decision gate (Epic 1)"
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
      "slug": "pyforge-doctor",
      "title": "Doctor — one bedside manner for the whole fleet",
      "status": "specified",
      "owner": "doctor",
      "type": "dream",
      "chain": {
        "deck": "presentations/pyforge-doctor",
        "spec": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor",
        "project": "_bmad-output/projects/pyforge-doctor"
      }
    },
    {
      "slug": "pyforge-genesis",
      "title": "Genesis — the seed of the operating model",
      "status": "specified",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "deck": "presentations/pyforge-genesis",
        "spec": "_bmad-output/projects/pyforge-genesis/planning-artifacts/specs/spec-pyforge-genesis",
        "project": "_bmad-output/projects/pyforge-genesis"
      }
    },
    {
      "slug": "pyforge-herald",
      "title": "Herald — capture the dream, illustrate the telemetry, proclaim the release",
      "status": "specified",
      "owner": "herald",
      "type": "dream",
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
      "type": "dream",
      "chain": {
        "deck": "presentations/pyforge-marshal",
        "spec": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-pyforge-marshal",
        "project": "_bmad-output/projects/pyforge-marshal"
      }
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
      "slug": "pyforge-scribe",
      "title": "Scribe — the inward voice",
      "status": "specified",
      "owner": "scribe",
      "type": "dream",
      "chain": {
        "deck": "presentations/pyforge-scribe",
        "spec": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe",
        "project": "_bmad-output/projects/pyforge-scribe"
      }
    },
    {
      "slug": "pyforge-steward",
      "title": "Steward — provision the line, hold the keys",
      "status": "specified",
      "owner": "steward",
      "type": "dream",
      "chain": {
        "deck": "presentations/pyforge-steward",
        "spec": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward",
        "project": "_bmad-output/projects/pyforge-steward"
      }
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
      "slug": "regenerable-factory",
      "title": "Regenerable factory — every line of code under a spec it can be rebuilt from",
      "status": "realized",
      "owner": "marshal",
      "type": "practice",
      "chain": {
        "spec": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-regenerable-factory",
        "program": "regen"
      }
    },
    {
      "slug": "sentinel",
      "title": "Sentinel — the AI Software Factory (the ancestor)",
      "status": "archived",
      "owner": "scribe",
      "type": "dream",
      "chain": {},
      "archived_reason": "absorbed"
    },
    {
      "slug": "team-memory",
      "title": "Team memory — what the team knows, the agents know",
      "status": "specified",
      "owner": "scribe",
      "type": "dream",
      "chain": {}
    },
    {
      "slug": "unity-data-stack",
      "title": "Unity Data Stack — the enterprise innersource platform",
      "status": "specified",
      "owner": "atlas",
      "type": "dream",
      "chain": {
        "deck": "presentations/unity-data-stack",
        "spec": "_bmad-output/projects/unity-data-stack/planning-artifacts/specs/spec-unity-data-stack",
        "project": "_bmad-output/projects/unity-data-stack"
      }
    },
    {
      "slug": "upstream-discovery",
      "title": "Upstream discovery — package it before it's asked for",
      "status": "specified",
      "owner": "atlas",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-upstream-discovery"
      }
    },
    {
      "slug": "wasm-analytics-stack",
      "title": "Wasm-first analytical data stack (OCP-ready)",
      "status": "specified",
      "owner": "atlas",
      "type": "dream",
      "chain": {
        "deck": "presentations/wasm-analytics-stack",
        "spec": "_bmad-output/projects/wasm-analytics-stack/planning-artifacts/specs/spec-wasm-analytics-stack",
        "project": "_bmad-output/projects/wasm-analytics-stack"
      }
    }
  ],
  "specs": [
    {
      "slug": "deckcraft",
      "project": "deckcraft",
      "title": "deckcraft — the air-gapped, conda-native editable-deck pipeline",
      "caps": 9,
      "companions": 0,
      "updated": "2026-07-25",
      "dream": "deckcraft",
      "path": "_bmad-output/projects/deckcraft/planning-artifacts/specs/spec-deckcraft"
    },
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
      "updated": "2026-07-26",
      "dream": "factory-console",
      "path": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-factory-console"
    },
    {
      "slug": "fleet-stewardship",
      "project": "local-recipes",
      "title": "fleet stewardship (the recipes/ fleet)",
      "caps": 3,
      "companions": 3,
      "updated": "2026-07-25",
      "dream": "fleet-stewardship",
      "path": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-fleet-stewardship"
    },
    {
      "slug": "modernist-identity",
      "project": "local-recipes",
      "title": "one visual language for everything pyforge",
      "caps": 3,
      "companions": 1,
      "updated": "2026-07-25",
      "dream": "modernist-identity",
      "path": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-modernist-identity"
    },
    {
      "slug": "multi-loop-isolation",
      "project": "local-recipes",
      "title": "multi-loop isolation harness",
      "caps": 3,
      "companions": 0,
      "updated": "2026-07-25",
      "dream": "",
      "path": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-multi-loop-isolation"
    },
    {
      "slug": "packaging-factory",
      "project": "local-recipes",
      "title": "the packaging factory (conda-forge-expert machinery)",
      "caps": 4,
      "companions": 2,
      "updated": "2026-07-25",
      "dream": "packaging-factory",
      "path": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-packaging-factory"
    },
    {
      "slug": "pyforge-marshal",
      "project": "local-recipes",
      "title": "Marshal (graduated-autonomy loop orchestration, as shipped)",
      "caps": 4,
      "companions": 3,
      "updated": "2026-07-25",
      "dream": "pyforge-marshal",
      "path": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-pyforge-marshal"
    },
    {
      "slug": "regenerable-factory",
      "project": "local-recipes",
      "title": "regenerable-factory program",
      "caps": 4,
      "companions": 1,
      "updated": "2026-07-25",
      "dream": "regenerable-factory",
      "path": "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-regenerable-factory"
    },
    {
      "slug": "presenton-pixi-image",
      "project": "presenton-pixi-image",
      "title": "presenton-pixi-image — air-gapped conda-native Presenton for OpenShift",
      "caps": 6,
      "companions": 0,
      "updated": "2026-07-25",
      "dream": "presenton-pixi-image",
      "path": "_bmad-output/projects/presenton-pixi-image/planning-artifacts/specs/spec-presenton-pixi-image"
    },
    {
      "slug": "pyforge-atlas",
      "project": "pyforge-atlas",
      "title": "Atlas — the intelligence layer an agent workforce can extend",
      "caps": 17,
      "companions": 4,
      "updated": "2026-07-28",
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
      "slug": "pyforge-doctor",
      "project": "pyforge-doctor",
      "title": "Doctor (pyforge-doctor) — one bedside manner for the whole fleet",
      "caps": 4,
      "companions": 1,
      "updated": "2026-07-25",
      "dream": "pyforge-doctor",
      "path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor"
    },
    {
      "slug": "pyforge-genesis",
      "project": "pyforge-genesis",
      "title": "Genesis — the operating-model installer",
      "caps": 9,
      "companions": 1,
      "updated": "2026-07-25",
      "dream": "pyforge-genesis",
      "path": "_bmad-output/projects/pyforge-genesis/planning-artifacts/specs/spec-pyforge-genesis"
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
    },
    {
      "slug": "pyforge-marshal",
      "project": "pyforge-marshal",
      "title": "marshal CLI — graduated autonomy, productized",
      "caps": 8,
      "companions": 5,
      "updated": "2026-07-26",
      "dream": "pyforge-marshal",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal"
    },
    {
      "slug": "pyforge-mason",
      "project": "pyforge-mason",
      "title": "mason CLI — the packaging factory, made portable",
      "caps": 7,
      "companions": 5,
      "updated": "2026-07-25",
      "dream": "pyforge-mason",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason"
    },
    {
      "slug": "pyforge-scribe",
      "project": "pyforge-scribe",
      "title": "Scribe (pyforge-scribe) — the team's inward voice",
      "caps": 4,
      "companions": 1,
      "updated": "2026-07-25",
      "dream": "pyforge-scribe",
      "path": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe"
    },
    {
      "slug": "pyforge-steward",
      "project": "pyforge-steward",
      "title": "Steward (pyforge-steward) — the estate the factory stands on",
      "caps": 4,
      "companions": 1,
      "updated": "2026-07-25",
      "dream": "pyforge-steward",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward"
    },
    {
      "slug": "pyforge-warden",
      "project": "pyforge-warden",
      "title": "Warden — the compliance gate that never false-greens",
      "caps": 12,
      "companions": 3,
      "updated": "2026-07-25",
      "dream": "pyforge-warden",
      "path": "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden"
    },
    {
      "slug": "unity-data-stack",
      "project": "unity-data-stack",
      "title": "Unity Data Stack — the enterprise innersource python-first platform",
      "caps": 9,
      "companions": 2,
      "updated": "2026-07-25",
      "dream": "unity-data-stack",
      "path": "_bmad-output/projects/unity-data-stack/planning-artifacts/specs/spec-unity-data-stack"
    },
    {
      "slug": "wasm-analytics-stack",
      "project": "wasm-analytics-stack",
      "title": "Wasm Analytics Stack — WASI-sandboxed upload validation, seed use case",
      "caps": 5,
      "companions": 1,
      "updated": "2026-07-25",
      "dream": "wasm-analytics-stack",
      "path": "_bmad-output/projects/wasm-analytics-stack/planning-artifacts/specs/spec-wasm-analytics-stack"
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
      "owner": "herald"
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
      "owner": "marshal"
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
      "export": "2026-07-24",
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
      "name": "Artifact console — the factory board, hosted as a chat artifact",
      "reason": "retired",
      "owner": "marshal",
      "note": "Artifact console — the factory board, hosted as a chat artifact",
      "link": "docs/dreams/artifact-console.md"
    },
    {
      "name": "copilot-cli on conda-forge — blocked at the license",
      "reason": "blocked",
      "owner": "mason",
      "note": "copilot-cli on conda-forge — blocked at the license",
      "link": "docs/dreams/copilot-cli-packaging.md"
    },
    {
      "name": "DB-GPT on conda-forge — the multi-output agent stack",
      "reason": "terminal",
      "owner": "mason",
      "note": "DB-GPT on conda-forge — the multi-output agent stack",
      "link": "docs/dreams/db-gpt-packaging.md"
    },
    {
      "name": "Microsoft org sweep — audit one upstream org, package what is missing",
      "reason": "absorbed",
      "owner": "atlas",
      "note": "Microsoft org sweep — audit one upstream org, package what is missing",
      "link": "docs/dreams/microsoft-org-sweep.md"
    },
    {
      "name": "Sentinel — the AI Software Factory (the ancestor)",
      "reason": "absorbed",
      "owner": "scribe",
      "note": "Sentinel — the AI Software Factory (the ancestor)",
      "link": "docs/dreams/sentinel.md"
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
  ],
  "fleet": {
    "stages": [
      "dream",
      "deck",
      "spec",
      "research",
      "brief",
      "prd",
      "arch",
      "epics",
      "code"
    ],
    "staleDays": 30,
    "rows": [
      {
        "label": "herald",
        "slug": "pyforge-herald",
        "dream": "pyforge-herald",
        "stages": {
          "dream": "07-23",
          "deck": "07-23",
          "spec": "07-23",
          "research": "07-25",
          "brief": "07-25",
          "prd": "07-25",
          "arch": "07-25",
          "epics": "07-25",
          "code": "07-25"
        },
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [],
        "furthest": "code",
        "updated": "2026-07-26",
        "age": 2,
        "stale": false,
        "version": "0.1.0",
        "progress": "2/17",
        "complete": 9,
        "of": 9,
        "owner": "herald"
      },
      {
        "label": "doctor",
        "slug": "pyforge-doctor",
        "dream": "pyforge-doctor",
        "stages": {
          "dream": "07-23",
          "deck": "07-23",
          "spec": "07-25",
          "research": "07-25",
          "brief": "07-25",
          "prd": "07-25",
          "arch": "07-25",
          "epics": "07-25",
          "code": "07-25"
        },
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [],
        "furthest": "code",
        "updated": "2026-07-26",
        "age": 2,
        "stale": false,
        "version": "0.1.0",
        "progress": "1/12",
        "complete": 9,
        "of": 9,
        "owner": "doctor"
      },
      {
        "label": "scribe",
        "slug": "pyforge-scribe",
        "dream": "pyforge-scribe",
        "stages": {
          "dream": "07-23",
          "deck": "07-23",
          "spec": "07-25",
          "research": "07-25",
          "brief": "07-25",
          "prd": "07-25",
          "arch": "07-25",
          "epics": "07-25",
          "code": "07-25"
        },
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [],
        "furthest": "code",
        "updated": "2026-07-26",
        "age": 2,
        "stale": false,
        "version": "0.1.0",
        "progress": "1/9",
        "complete": 9,
        "of": 9,
        "owner": "scribe"
      },
      {
        "label": "steward",
        "slug": "pyforge-steward",
        "dream": "pyforge-steward",
        "stages": {
          "dream": "07-23",
          "deck": "07-23",
          "spec": "07-25",
          "research": "07-25",
          "brief": "07-25",
          "prd": "07-25",
          "arch": "07-25",
          "epics": "07-25",
          "code": "07-25"
        },
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [],
        "furthest": "code",
        "updated": "2026-07-25",
        "age": 3,
        "stale": false,
        "version": "0.1.0",
        "progress": "1/18",
        "complete": 9,
        "of": 9,
        "owner": "steward"
      },
      {
        "label": "marshal",
        "slug": "pyforge-marshal",
        "dream": "pyforge-marshal",
        "stages": {
          "dream": "07-23",
          "deck": "07-23",
          "spec": "07-25",
          "research": "07-25",
          "brief": "07-25",
          "prd": "07-25",
          "arch": "07-25",
          "epics": "07-25",
          "code": "07-26"
        },
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [],
        "furthest": "code",
        "updated": "2026-07-26",
        "age": 2,
        "stale": false,
        "version": "0.1.0",
        "progress": "1/41",
        "complete": 9,
        "of": 9,
        "owner": "marshal"
      },
      {
        "label": "mason",
        "slug": "pyforge-mason",
        "dream": "pyforge-mason",
        "stages": {
          "dream": "07-25",
          "deck": "07-23",
          "spec": "07-25",
          "research": "07-25",
          "brief": "07-25",
          "prd": "07-25",
          "arch": "07-25",
          "epics": "07-25",
          "code": "07-25"
        },
        "backfilled": true,
        "openQuestions": 0,
        "overtaken": false,
        "na": [],
        "furthest": "code",
        "updated": "2026-07-25",
        "age": 3,
        "stale": false,
        "version": "0.1.0",
        "progress": "1/38",
        "complete": 9,
        "of": 9,
        "owner": "mason"
      },
      {
        "label": "atlas",
        "slug": "pyforge-atlas",
        "dream": "pyforge-atlas",
        "stages": {
          "dream": "07-23",
          "deck": "07-23",
          "spec": "07-23",
          "research": "07-25",
          "brief": "07-25",
          "prd": "07-17",
          "arch": "07-17",
          "epics": "07-17",
          "code": "07-17"
        },
        "backfilled": true,
        "openQuestions": 0,
        "overtaken": false,
        "na": [],
        "furthest": "code",
        "updated": "2026-07-28",
        "age": 0,
        "stale": false,
        "version": "0.1.0",
        "progress": "35/38",
        "complete": 9,
        "of": 9,
        "owner": "atlas"
      },
      {
        "label": "warden",
        "slug": "pyforge-warden",
        "dream": "pyforge-warden",
        "stages": {
          "dream": "07-23",
          "deck": "07-14",
          "spec": "07-25",
          "research": "07-25",
          "brief": "07-25",
          "prd": "07-14",
          "arch": "07-14",
          "epics": "07-14",
          "code": "07-14"
        },
        "backfilled": true,
        "openQuestions": 0,
        "overtaken": false,
        "na": [],
        "furthest": "code",
        "updated": "2026-07-25",
        "age": 3,
        "stale": false,
        "version": "0.1.0",
        "progress": "31/31",
        "complete": 9,
        "of": 9,
        "owner": "warden"
      },
      {
        "label": "genesis",
        "slug": "pyforge-genesis",
        "dream": "pyforge-genesis",
        "stages": {
          "dream": "07-23",
          "deck": "07-23",
          "spec": "07-25",
          "research": "07-25",
          "brief": "07-25",
          "prd": "07-25",
          "arch": "07-25",
          "epics": "07-25",
          "code": ""
        },
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [],
        "furthest": "epics",
        "updated": "2026-07-25",
        "age": 3,
        "stale": false,
        "version": "",
        "progress": "0/36",
        "complete": 8,
        "of": 9,
        "owner": "marshal"
      },
      {
        "label": "deckcraft",
        "slug": "deckcraft",
        "dream": "deckcraft",
        "stages": {
          "dream": "07-23",
          "deck": "07-25",
          "spec": "07-25",
          "research": "07-25",
          "brief": "05-10",
          "prd": "05-10",
          "arch": "05-10",
          "epics": "05-10",
          "code": ""
        },
        "backfilled": true,
        "openQuestions": 0,
        "overtaken": false,
        "na": [],
        "furthest": "epics",
        "updated": "2026-07-25",
        "age": 3,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 8,
        "of": 9,
        "owner": "herald"
      },
      {
        "label": "presenton",
        "slug": "presenton-pixi-image",
        "dream": "presenton-pixi-image",
        "stages": {
          "dream": "07-23",
          "deck": "07-25",
          "spec": "07-25",
          "research": "07-25",
          "brief": "07-25",
          "prd": "05-01",
          "arch": "07-25",
          "epics": "07-25",
          "code": ""
        },
        "backfilled": true,
        "openQuestions": 0,
        "overtaken": false,
        "na": [],
        "furthest": "epics",
        "updated": "2026-07-25",
        "age": 3,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 8,
        "of": 9,
        "owner": "mason"
      },
      {
        "label": "unity",
        "slug": "unity-data-stack",
        "dream": "unity-data-stack",
        "stages": {
          "dream": "07-23",
          "deck": "07-25",
          "spec": "07-25",
          "research": "07-25",
          "brief": "07-25",
          "prd": "07-25",
          "arch": "07-25",
          "epics": "",
          "code": ""
        },
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "epics"
        ],
        "furthest": "arch",
        "updated": "2026-07-25",
        "age": 3,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 8,
        "of": 9,
        "owner": "atlas"
      },
      {
        "label": "wasm",
        "slug": "wasm-analytics-stack",
        "dream": "wasm-analytics-stack",
        "stages": {
          "dream": "07-23",
          "deck": "07-25",
          "spec": "07-25",
          "research": "07-25",
          "brief": "07-25",
          "prd": "07-25",
          "arch": "07-25",
          "epics": "",
          "code": ""
        },
        "backfilled": false,
        "openQuestions": 0,
        "overtaken": false,
        "na": [
          "epics"
        ],
        "furthest": "arch",
        "updated": "2026-07-25",
        "age": 3,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 8,
        "of": 9,
        "owner": "atlas"
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
        "verdict": "OK: all tracked BMAD artifacts are in sync with the live factory MINOR.",
        "runbook": "_bmad-output/projects/local-recipes/SYNC-RUNBOOK.md"
      },
      {
        "name": "spec-surface",
        "task": "spec-surface-check",
        "guards": "every tracked file under a Spec surface",
        "state": "drift",
        "findings": 5,
        "verdict": "FINDINGS (5):",
        "runbook": ""
      },
      {
        "name": "llms-full",
        "task": "llms-full-check",
        "guards": "library catalog freshness",
        "state": "drift",
        "findings": 3,
        "verdict": "DRIFT: 3 finding(s). Reconcile by regenerating the catalog (prompt in its header), then re-run.",
        "runbook": ""
      }
    ],
    "baseline": {
      "skill": "8.79.1",
      "head": "d68dad75ae",
      "deltas": [],
      "runbook": "_bmad-output/projects/local-recipes/SYNC-RUNBOOK.md"
    }
  },
  "backlog": {
    "rows": [
      {
        "slug": "agentic-sdlc-autonomy",
        "title": "The Agentic SDLC — four views of autonomy, one governed factory",
        "status": "pitched",
        "owner": "marshal",
        "blockedOn": "",
        "chain": {
          "deck": "presentations/agentic-sdlc"
        }
      },
      {
        "slug": "deckcraft",
        "title": "Deckcraft — editable decks from primitives, air-gapped",
        "status": "specified",
        "owner": "herald",
        "blockedOn": "",
        "chain": {
          "deck": "presentations/deckcraft",
          "spec": "_bmad-output/projects/deckcraft/planning-artifacts/specs/spec-deckcraft",
          "project": "_bmad-output/projects/deckcraft"
        }
      },
      {
        "slug": "pyforge-genesis",
        "title": "Genesis — the seed of the operating model",
        "status": "specified",
        "owner": "marshal",
        "blockedOn": "",
        "chain": {
          "deck": "presentations/pyforge-genesis",
          "spec": "_bmad-output/projects/pyforge-genesis/planning-artifacts/specs/spec-pyforge-genesis",
          "project": "_bmad-output/projects/pyforge-genesis"
        }
      },
      {
        "slug": "team-memory",
        "title": "Team memory — what the team knows, the agents know",
        "status": "specified",
        "owner": "scribe",
        "blockedOn": "",
        "chain": {}
      },
      {
        "slug": "unity-data-stack",
        "title": "Unity Data Stack — the enterprise innersource platform",
        "status": "specified",
        "owner": "atlas",
        "blockedOn": "",
        "chain": {
          "deck": "presentations/unity-data-stack",
          "spec": "_bmad-output/projects/unity-data-stack/planning-artifacts/specs/spec-unity-data-stack",
          "project": "_bmad-output/projects/unity-data-stack"
        }
      },
      {
        "slug": "upstream-discovery",
        "title": "Upstream discovery — package it before it's asked for",
        "status": "specified",
        "owner": "atlas",
        "blockedOn": "",
        "chain": {
          "spec": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-upstream-discovery"
        }
      },
      {
        "slug": "wasm-analytics-stack",
        "title": "Wasm-first analytical data stack (OCP-ready)",
        "status": "specified",
        "owner": "atlas",
        "blockedOn": "",
        "chain": {
          "deck": "presentations/wasm-analytics-stack",
          "spec": "_bmad-output/projects/wasm-analytics-stack/planning-artifacts/specs/spec-wasm-analytics-stack",
          "project": "_bmad-output/projects/wasm-analytics-stack"
        }
      },
      {
        "slug": "presenton-pixi-image",
        "title": "Presenton, conda-native — AI decks inside the regulated enterprise",
        "status": "specified",
        "owner": "mason",
        "blockedOn": "Phase-0 decision gate (Epic 1)",
        "chain": {
          "deck": "presentations/presenton-pixi-image",
          "spec": "_bmad-output/projects/presenton-pixi-image/planning-artifacts/specs/spec-presenton-pixi-image",
          "project": "_bmad-output/projects/presenton-pixi-image"
        }
      }
    ],
    "blocked": 1,
    "byOwner": {
      "marshal": 2,
      "herald": 1,
      "scribe": 1,
      "atlas": 3,
      "mason": 1
    },
    "practices": [
      {
        "slug": "agent-portability",
        "title": "Agent portability — BMAD on any agent, never vendor-locked",
        "owner": "marshal",
        "status": "dreamt"
      },
      {
        "slug": "enterprise-airgap",
        "title": "The factory behind the firewall",
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
        "slug": "modernist-identity",
        "title": "Modernist identity — one visual language for everything PyForge",
        "owner": "herald",
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
        "total": 4,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 2,
          "realized": 1,
          "archived": 0,
          "practice": 1
        },
        "line": "paused 1.3",
        "load": 1,
        "blocked": 0,
        "dreams": [
          {
            "slug": "design-code-bridge",
            "title": "The Design↔Code Bridge",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "modernist-identity",
            "title": "Modernist identity — one visual language for everything PyForge",
            "status": "realized",
            "type": "practice",
            "blockedOn": ""
          },
          {
            "slug": "deckcraft",
            "title": "Deckcraft — editable decks from primitives, air-gapped",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pyforge-herald",
            "title": "Herald — capture the dream, illustrate the telemetry, proclaim the release",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "marshal",
        "total": 8,
        "counts": {
          "dreamt": 0,
          "pitched": 1,
          "specified": 1,
          "realized": 3,
          "archived": 1,
          "practice": 2
        },
        "line": "paused 1.2",
        "load": 2,
        "blocked": 0,
        "dreams": [
          {
            "slug": "artifact-console",
            "title": "Artifact console — the factory board, hosted as a chat artifact",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "agent-portability",
            "title": "Agent portability — BMAD on any agent, never vendor-locked",
            "status": "dreamt",
            "type": "practice",
            "blockedOn": ""
          },
          {
            "slug": "agentic-sdlc-autonomy",
            "title": "The Agentic SDLC — four views of autonomy, one governed factory",
            "status": "pitched",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "agent-tool-surface",
            "title": "Agent tool surface — every craft reachable through one governed API",
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
            "slug": "pyforge-marshal",
            "title": "Marshal — autonomy a human can trust",
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
            "slug": "pyforge-genesis",
            "title": "Genesis — the seed of the operating model",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "atlas",
        "total": 5,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 3,
          "realized": 1,
          "archived": 1,
          "practice": 0
        },
        "line": "paused I3",
        "load": 3,
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
            "slug": "pyforge-atlas",
            "title": "Atlas — the map that maintains itself",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "unity-data-stack",
            "title": "Unity Data Stack — the enterprise innersource platform",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "upstream-discovery",
            "title": "Upstream discovery — package it before it's asked for",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "wasm-analytics-stack",
            "title": "Wasm-first analytical data stack (OCP-ready)",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "warden",
        "total": 1,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 0,
          "realized": 1,
          "archived": 0,
          "practice": 0
        },
        "line": "complete",
        "load": 0,
        "blocked": 0,
        "dreams": [
          {
            "slug": "pyforge-warden",
            "title": "Warden — the gate that never lies",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "mason",
        "total": 6,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 2,
          "realized": 0,
          "archived": 2,
          "practice": 2
        },
        "line": "paused 1.2",
        "load": 1,
        "blocked": 1,
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
            "slug": "presenton-pixi-image",
            "title": "Presenton, conda-native — AI decks inside the regulated enterprise",
            "status": "specified",
            "type": "dream",
            "blockedOn": "Phase-0 decision gate (Epic 1)"
          },
          {
            "slug": "pyforge-mason",
            "title": "Mason — forge the blocks, bind the environment, ship the structure",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "doctor",
        "total": 1,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 1,
          "realized": 0,
          "archived": 0,
          "practice": 0
        },
        "line": "paused 1.2",
        "load": 0,
        "blocked": 0,
        "dreams": [
          {
            "slug": "pyforge-doctor",
            "title": "Doctor — one bedside manner for the whole fleet",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "scribe",
        "total": 3,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 2,
          "realized": 0,
          "archived": 1,
          "practice": 0
        },
        "line": "paused 1.2",
        "load": 1,
        "blocked": 0,
        "dreams": [
          {
            "slug": "sentinel",
            "title": "Sentinel — the AI Software Factory (the ancestor)",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pyforge-scribe",
            "title": "Scribe — the inward voice",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "team-memory",
            "title": "Team memory — what the team knows, the agents know",
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "steward",
        "total": 2,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 1,
          "realized": 0,
          "archived": 0,
          "practice": 1
        },
        "line": "paused 1.2",
        "load": 0,
        "blocked": 0,
        "dreams": [
          {
            "slug": "enterprise-airgap",
            "title": "The factory behind the firewall",
            "status": "realized",
            "type": "practice",
            "blockedOn": ""
          },
          {
            "slug": "pyforge-steward",
            "title": "Steward — provision the line, hold the keys",
            "status": "specified",
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
  }
};
