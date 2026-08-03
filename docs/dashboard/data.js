window.DASHBOARD_DATA = {
  "projects": {
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
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals. 5 of 16 stories measured; the rest predate loop instrumentation and carry wall-clock only (a different metric — see the timing strip), so they are deliberately absent rather than plotted on this axis. A story still in flight contributes only its CLOSED sessions, so its bar is a floor, not a total.",
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
          ]
        ],
        "foot": [
          [
            "~80 min",
            "median / story",
            "var(--done)"
          ],
          [
            "42–427 min",
            "observed range",
            ""
          ],
          [
            "5/16",
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
        "total": 715,
        "totalLabel": "~11.9 h active compute",
        "note": "Derived from 5 measured stories; a story still in flight contributes only its closed sessions.",
        "perStory": {
          "1.1": 101,
          "1.2": 65,
          "1.3": 42,
          "1.4": 427,
          "1.5": 80
        },
        "epicMin": {
          "E1": 715
        }
      },
      "lineState": {
        "state": "paused",
        "at": "2.1"
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
        },
        {
          "badge": "E4",
          "title": "The frontier, decomposed (v1.x — added 2026-08-02)",
          "stories": [
            [
              "4.1",
              "pending",
              "Health scoring (FR-10)"
            ],
            [
              "4.2",
              "pending",
              "Persistent fleet-health surface (FR-11)"
            ],
            [
              "4.3",
              "pending",
              "Adoption-tracking watch axis (FR-12)"
            ],
            [
              "4.4",
              "pending",
              "Safe upgrade-path recommendation (FR-13)"
            ]
          ]
        }
      ],
      "owner": "doctor",
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
      "inflight": {
        "key": "2.2",
        "title": "Verdict aggregation that never false-greens",
        "phase": "dev",
        "attempt": "1",
        "startEpoch": 1785740624,
        "median": 94,
        "lo": 62,
        "hi": 450,
        "phaseAsOf": "2026-08-03 07:26 UTC"
      },
      "velocity": {
        "derived": true,
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals. 12 of 50 stories measured; the rest predate loop instrumentation and carry wall-clock only (a different metric — see the timing strip), so they are deliberately absent rather than plotted on this axis. A story still in flight contributes only its CLOSED sessions, so its bar is a floor, not a total.",
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
            1
          ]
        ],
        "foot": [
          [
            "~94 min",
            "median / story",
            "var(--done)"
          ],
          [
            "1–450 min",
            "observed range",
            ""
          ],
          [
            "11/50",
            "stories complete",
            "var(--done)"
          ],
          [
            "39",
            "remaining",
            ""
          ]
        ]
      },
      "timing": {
        "derived": true,
        "metric": "active agent-compute per story (dev + review; excludes gate-pause wait) — from bmad-loop run journals",
        "total": 1486,
        "totalLabel": "~24.8 h active compute",
        "note": "Derived from 12 measured stories; a story still in flight contributes only its closed sessions.",
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
          "2.2": 1
        },
        "epicMin": {
          "E1": 1343,
          "E2": 143
        }
      },
      "lineState": {
        "state": "in flight",
        "at": "2.2"
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
              "active",
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
            ],
            [
              "2.7",
              "pending",
              "A gate binds to the spec's Success signal *(added 2026-08-01 — FR-64 / AD-49)*"
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
            ],
            [
              "3.8",
              "pending",
              "Stage-bound durability, and fleet-launch wiring *(added 2026-08-01 — FR-61 / AD-46)*"
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
            ],
            [
              "4.7",
              "pending",
              "Landing rules as declared policy *(added 2026-08-01 — FR-59 / CAP-9)*"
            ],
            [
              "4.8",
              "pending",
              "`marshal land` — the last mile lands itself *(added 2026-08-01 — FR-60 / CAP-9)*"
            ],
            [
              "4.9",
              "pending",
              "Derived surfaces regenerate on main; the shared store takes a lock *(added 2026-08-01 — AD-42 / the Q-10 decomposition)*"
            ],
            [
              "4.10",
              "pending",
              "Fleet-wide branch retirement *(added 2026-08-01 — FR-63 / AD-47)*"
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
            ],
            [
              "5.5",
              "pending",
              "Durability as a reported fleet-status dimension *(added 2026-08-01 — FR-62 / AD-48)*"
            ],
            [
              "5.6",
              "pending",
              "`marshal check` — the detector registry through the front door *(added 2026-08-01 — FR-65 / AD-50)*"
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
            ],
            [
              "6.9",
              "pending",
              "Tool-surface rendering and preflight probe *(added 2026-08-01 — AD-43 / the Q-11 resolution; post-MVP)*"
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
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals. 3 of 38 stories measured; the rest predate loop instrumentation and carry wall-clock only (a different metric — see the timing strip), so they are deliberately absent rather than plotted on this axis. A story still in flight contributes only its CLOSED sessions, so its bar is a floor, not a total.",
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
          ]
        ],
        "foot": [
          [
            "~91 min",
            "median / story",
            "var(--done)"
          ],
          [
            "36–402 min",
            "observed range",
            ""
          ],
          [
            "4/38",
            "stories complete",
            "var(--done)"
          ],
          [
            "34",
            "remaining",
            ""
          ]
        ]
      },
      "timing": {
        "derived": true,
        "metric": "active agent-compute per story (dev + review; excludes gate-pause wait) — from bmad-loop run journals",
        "total": 529,
        "totalLabel": "~8.8 h active compute",
        "note": "Derived from 3 measured stories; a story still in flight contributes only its closed sessions.",
        "perStory": {
          "1.2": 91,
          "1.3": 402,
          "1.4": 36
        },
        "epicMin": {
          "E1": 529
        }
      },
      "lineState": {
        "state": "paused",
        "at": "1.5"
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
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals. 4 of 9 stories measured; the rest predate loop instrumentation and carry wall-clock only (a different metric — see the timing strip), so they are deliberately absent rather than plotted on this axis. A story still in flight contributes only its CLOSED sessions, so its bar is a floor, not a total.",
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
            "3/9",
            "stories complete",
            "var(--done)"
          ],
          [
            "6",
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
        "state": "paused",
        "at": "1.4"
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
      "velocity": {
        "derived": true,
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals. 3 of 18 stories measured; the rest predate loop instrumentation and carry wall-clock only (a different metric — see the timing strip), so they are deliberately absent rather than plotted on this axis. A story still in flight contributes only its CLOSED sessions, so its bar is a floor, not a total.",
        "bars": [
          [
            "1.2",
            69
          ],
          [
            "1.3",
            79
          ],
          [
            "1.4",
            360
          ]
        ],
        "foot": [
          [
            "~79 min",
            "median / story",
            "var(--done)"
          ],
          [
            "69–360 min",
            "observed range",
            ""
          ],
          [
            "3/18",
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
        "total": 508,
        "totalLabel": "~8.5 h active compute",
        "note": "Derived from 3 measured stories; a story still in flight contributes only its closed sessions.",
        "perStory": {
          "1.2": 69,
          "1.3": 79,
          "1.4": 360
        },
        "epicMin": {
          "E1": 508
        }
      },
      "lineState": {
        "state": "paused",
        "at": "1.4"
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
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals. 5 of 19 stories measured; the rest predate loop instrumentation and carry wall-clock only (a different metric — see the timing strip), so they are deliberately absent rather than plotted on this axis. A story still in flight contributes only its CLOSED sessions, so its bar is a floor, not a total.",
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
          ]
        ],
        "foot": [
          [
            "~98 min",
            "median / story",
            "var(--done)"
          ],
          [
            "29–417 min",
            "observed range",
            ""
          ],
          [
            "3/19",
            "stories complete",
            "var(--done)"
          ],
          [
            "16",
            "remaining",
            ""
          ]
        ]
      },
      "timing": {
        "derived": true,
        "metric": "active agent-compute per story (dev + review; excludes gate-pause wait) — from bmad-loop run journals",
        "total": 712,
        "totalLabel": "~11.9 h active compute",
        "note": "Derived from 5 measured stories; a story still in flight contributes only its closed sessions.",
        "perStory": {
          "1.1": 60,
          "1.2": 98,
          "1.3": 29,
          "1.4": 108,
          "1.5": 417
        },
        "epicMin": {
          "E1": 712
        }
      },
      "lineState": {
        "state": "paused",
        "at": "1.3"
      },
      "epics": [
        {
          "badge": "E0",
          "title": "Foundation & Infrastructure",
          "stories": [
            [
              "0.1",
              "pending",
              "Set up Modernist-Identity design system and token exports"
            ],
            [
              "0.2",
              "pending",
              "Establish .gitignore strategy and artifact tracking matrix"
            ],
            [
              "0.3",
              "pending",
              "Implement Design-Code-Bridge etagged pull protocol"
            ]
          ]
        },
        {
          "badge": "E1",
          "title": "Design Authoring & Seeding",
          "stories": [
            [
              "1.1",
              "done",
              "Create 9 Design projects (seed per station)"
            ],
            [
              "1.2",
              "done",
              "Establish six-act framework structure in Design prototypes"
            ],
            [
              "1.3",
              "pending",
              "Extract markdown sources from Design prototypes"
            ],
            [
              "1.4",
              "done",
              "Validate station-specific narrative content in all 9 decks"
            ]
          ]
        },
        {
          "badge": "E2",
          "title": "Multi-Format Export Pipeline",
          "stories": [
            [
              "2.1",
              "pending",
              "Implement deckcraft pipeline (Markdown → PPTX with tokens)"
            ],
            [
              "2.2",
              "pending",
              "Implement SVG infographic extraction from Design"
            ],
            [
              "2.3",
              "pending",
              "Build interactive HTML decks via Vite (gitignored, regenerable)"
            ],
            [
              "2.4",
              "pending",
              "Validate all 9 decks via dashboard-check"
            ],
            [
              "2.5",
              "pending",
              "Establish Modernist design token application across all 9 PPTX files"
            ]
          ]
        },
        {
          "badge": "E3",
          "title": "Narration Extraction & Validation",
          "stories": [
            [
              "3.1",
              "pending",
              "Implement mechanical narration extraction from Design speaker notes"
            ],
            [
              "3.2",
              "pending",
              "Implement narration linter (voice bible + blacklist enforcement)"
            ],
            [
              "3.3",
              "pending",
              "Stage narration scripts for bmad-manticore video pipeline"
            ],
            [
              "3.4",
              "pending",
              "Enforce \"no fabricated demos\" constraint"
            ]
          ]
        },
        {
          "badge": "E4",
          "title": "Station-Specific Customization",
          "stories": []
        },
        {
          "badge": "E5",
          "title": "Build, Validation & Shipping",
          "stories": [
            [
              "5.1",
              "pending",
              "Run comprehensive artifact validation (render, format, consistency checks)"
            ],
            [
              "5.2",
              "pending",
              "Verify 62% footprint reduction (tracked vs. unoptimized)"
            ],
            [
              "5.3",
              "pending",
              "Commit tracked artifacts and stage narration for video pipeline"
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
          "title": "Closure — tested, gate, drill-through",
          "stories": [
            [
              "5.1",
              "done",
              "Chain-tested + manifests (atlas / bridge / marshal)"
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
      "owner": "guild",
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
        "WF–WH",
        "WI · post-audit"
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
              "10.1",
              "done",
              "I0 — Atlas dependency completeness — unblock kedro-test (AUD-ATLAS-010/013)"
            ],
            [
              "10.2",
              "done",
              "I1 — Kernel + companion truth-up: retract the false run-admission claim (AUD-ATLAS-046/041/047/049)"
            ],
            [
              "10.3",
              "done",
              "I2 — Uniform story-spec frontmatter + README reversal (AUD-ATLAS-045/048)"
            ],
            [
              "10.4",
              "done",
              "I3 — pandas 3.0 None-identity contracts — FIRST loop story, kedro-test is red until it lands (AUD-ATLAS-011)"
            ],
            [
              "10.5",
              "done",
              "I4 — AD-17 advisory timestamps: MCP read_dataset envelope + per-page build stamps (AUD-ATLAS-043/044)"
            ],
            [
              "10.6",
              "done",
              "I5 — Run admission / single-writer — DW-AD23-1, re-promotes AD-23 (AUD-ATLAS-046 impl half)"
            ]
          ]
        }
      ],
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
      "owner": "atlas",
      "practice": false,
      "inflight": null,
      "velocity": {
        "derived": true,
        "sub": "Active agent-compute per story (dev + review; excludes gate-pause wait) — derived from this line's bmad-loop journals. 3 of 38 stories measured; the rest predate loop instrumentation and carry wall-clock only (a different metric — see the timing strip), so they are deliberately absent rather than plotted on this axis. A story still in flight contributes only its CLOSED sessions, so its bar is a floor, not a total.",
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
          ]
        ],
        "foot": [
          [
            "~194 min",
            "median / story",
            "var(--done)"
          ],
          [
            "68–499 min",
            "observed range",
            ""
          ],
          [
            "38/38",
            "stories complete",
            "var(--done)"
          ],
          [
            "0",
            "remaining",
            ""
          ]
        ]
      }
    }
  },
  "snapshot": "<span>2026-08-03 07:26 UTC</span> · source: sprint-status feeds + merged-PR ground truth (#58–#104) + bmad-loop run journals · timing: Warden = active compute (journals), Atlas = wall-clock (PR timestamps)",
  "defaultProject": "warden",
  "dreams": [
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
      "status": "pitched",
      "owner": "marshal",
      "type": "practice",
      "chain": {
        "deck": "presentations/agentic-sdlc",
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-agentic-sdlc-autonomy"
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
      "slug": "bmad-output-hygiene",
      "title": "One fabricated commit, eight stations of debris",
      "status": "realized",
      "owner": "marshal",
      "type": "dream",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-output-hygiene"
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
      "status": "dreamt",
      "owner": "marshal",
      "type": "dream",
      "chain": {}
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
      "slug": "durable-runs",
      "title": "Durable runs — work survives the machine that made it",
      "status": "archived",
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
      "slug": "factory-console",
      "title": "Factory console — the whole pipeline on one page",
      "status": "archived",
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
      "status": "dreamt",
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
      "slug": "pr-lifecycle",
      "title": "PR lifecycle — a story lands itself",
      "status": "archived",
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
      "owner": "guild",
      "type": "dream",
      "chain": {
        "deck": "presentations/pyforge-genesis"
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
      "slug": "regenerable-factory",
      "title": "Regenerable factory — every line of code under a spec it can be rebuilt from",
      "status": "realized",
      "owner": "marshal",
      "type": "practice",
      "chain": {
        "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-regenerable-factory",
        "program": "regen"
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
      "status": "dreamt",
      "owner": "steward",
      "type": "dream",
      "chain": {}
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
      "slug": "microsoft-org-sweep",
      "project": "pyforge-atlas",
      "title": "microsoft-org-sweep — retirement record",
      "caps": 0,
      "companions": 0,
      "updated": "2026-07-29",
      "dream": "microsoft-org-sweep",
      "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-microsoft-org-sweep"
    },
    {
      "slug": "pyforge-atlas",
      "project": "pyforge-atlas",
      "title": "consolidated: 2026-08-02 — this Spec also carries spec-unity-data-stack and",
      "caps": 31,
      "companions": 5,
      "updated": "2026-08-02",
      "dream": "pyforge-atlas",
      "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas"
    },
    {
      "slug": "pyforge-atlas-intelligence-platform",
      "project": "pyforge-atlas",
      "title": "pyforge-atlas-intelligence-platform — retirement record",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-02",
      "dream": "pyforge-atlas-intelligence-platform",
      "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas-intelligence-platform"
    },
    {
      "slug": "upstream-discovery",
      "project": "pyforge-atlas",
      "title": "upstream discovery — sense what the world is building",
      "caps": 5,
      "companions": 2,
      "updated": "2026-08-02",
      "dream": "upstream-discovery",
      "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-upstream-discovery"
    },
    {
      "slug": "pyforge-doctor",
      "project": "pyforge-doctor",
      "title": "Doctor (pyforge-doctor) — one bedside manner for the whole fleet",
      "caps": 8,
      "companions": 1,
      "updated": "2026-08-02",
      "dream": "pyforge-doctor",
      "path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor"
    },
    {
      "slug": "pyforge-doctor-dependency-health",
      "project": "pyforge-doctor",
      "title": "pyforge-doctor-dependency-health — retirement record",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-02",
      "dream": "pyforge-doctor-dependency-health",
      "path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor-dependency-health"
    },
    {
      "slug": "herald-moments-2-4-missing-surface",
      "project": "pyforge-herald",
      "title": "herald-moments-2-4-missing-surface — retirement record",
      "caps": 3,
      "companions": 0,
      "updated": "2026-08-02",
      "dream": "herald-moments-2-4-missing-surface",
      "path": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-herald-moments-2-4-missing-surface"
    },
    {
      "slug": "pyforge-herald",
      "project": "pyforge-herald",
      "title": "pyforge-herald",
      "caps": 3,
      "companions": 6,
      "updated": "2026-08-02",
      "dream": "pyforge-herald",
      "path": "_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald"
    },
    {
      "slug": "agent-portability",
      "project": "pyforge-marshal",
      "title": "agent-portability — retirement record",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-02",
      "dream": "agent-portability",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-agent-portability"
    },
    {
      "slug": "agent-tool-surface",
      "project": "pyforge-marshal",
      "title": "The agent tool surface — the factory, callable",
      "caps": 4,
      "companions": 0,
      "updated": "2026-07-29",
      "dream": "agent-tool-surface",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-agent-tool-surface"
    },
    {
      "slug": "agentic-sdlc-autonomy",
      "project": "pyforge-marshal",
      "title": "agentic-sdlc-autonomy",
      "caps": 0,
      "companions": 0,
      "updated": "2026-07-29",
      "dream": "agentic-sdlc-autonomy",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-agentic-sdlc-autonomy"
    },
    {
      "slug": "artifact-console",
      "project": "pyforge-marshal",
      "title": "artifact-console — retirement record",
      "caps": 0,
      "companions": 0,
      "updated": "2026-07-29",
      "dream": "artifact-console",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-artifact-console"
    },
    {
      "slug": "bmad-loop-governance",
      "project": "pyforge-marshal",
      "title": "Marshal (graduated-autonomy loop orchestration, as shipped)",
      "caps": 4,
      "companions": 3,
      "updated": "2026-07-29",
      "dream": "",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-loop-governance"
    },
    {
      "slug": "bmad-output-hygiene",
      "project": "pyforge-marshal",
      "title": "bmad-output-hygiene",
      "caps": 12,
      "companions": 0,
      "updated": "2026-08-02",
      "dream": "bmad-output-hygiene",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-output-hygiene"
    },
    {
      "slug": "durable-runs",
      "project": "pyforge-marshal",
      "title": "durable-runs — retirement record",
      "caps": 6,
      "companions": 0,
      "updated": "2026-08-02",
      "dream": "durable-runs",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-durable-runs"
    },
    {
      "slug": "factory-console",
      "project": "pyforge-marshal",
      "title": "factory console (program console + Dreamscape)",
      "caps": 4,
      "companions": 1,
      "updated": "2026-08-01",
      "dream": "factory-console",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-factory-console"
    },
    {
      "slug": "fidelity-enforcement",
      "project": "pyforge-marshal",
      "title": "fidelity-enforcement — retirement record",
      "caps": 9,
      "companions": 3,
      "updated": "2026-08-02",
      "dream": "fidelity-enforcement",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-fidelity-enforcement"
    },
    {
      "slug": "fleet-chain-completeness",
      "project": "pyforge-marshal",
      "title": "fleet chain completeness",
      "caps": 5,
      "companions": 0,
      "updated": "2026-08-02",
      "dream": "fleet-chain-completeness",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-fleet-chain-completeness"
    },
    {
      "slug": "genesis-installer-name-retirement",
      "project": "pyforge-marshal",
      "title": "genesis-installer-name-retirement",
      "caps": 8,
      "companions": 1,
      "updated": "2026-08-02",
      "dream": "genesis-installer-name-retirement",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-genesis-installer-name-retirement"
    },
    {
      "slug": "multi-loop-isolation",
      "project": "pyforge-marshal",
      "title": "multi-loop isolation harness",
      "caps": 3,
      "companions": 0,
      "updated": "2026-07-29",
      "dream": "",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-multi-loop-isolation"
    },
    {
      "slug": "one-front-door",
      "project": "pyforge-marshal",
      "title": "one-front-door — retirement record",
      "caps": 5,
      "companions": 1,
      "updated": "2026-08-02",
      "dream": "one-front-door",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-one-front-door"
    },
    {
      "slug": "pr-lifecycle",
      "project": "pyforge-marshal",
      "title": "pr-lifecycle — retirement record",
      "caps": 6,
      "companions": 0,
      "updated": "2026-08-02",
      "dream": "pr-lifecycle",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pr-lifecycle"
    },
    {
      "slug": "pyforge-marshal",
      "project": "pyforge-marshal",
      "title": "marshal CLI — graduated autonomy, productized",
      "caps": 18,
      "companions": 7,
      "updated": "2026-08-02",
      "dream": "pyforge-marshal",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal"
    },
    {
      "slug": "pyforge-marshal-loop-orchestrator",
      "project": "pyforge-marshal",
      "title": "pyforge-marshal-loop-orchestrator — retirement record",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-02",
      "dream": "pyforge-marshal-loop-orchestrator",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal-loop-orchestrator"
    },
    {
      "slug": "pyforge-testing-charter",
      "project": "pyforge-marshal",
      "title": "PyForge Testing Charter — fleet-wide test architecture",
      "caps": 5,
      "companions": 2,
      "updated": "2026-08-02",
      "dream": "pyforge-testing-charter",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter"
    },
    {
      "slug": "regenerable-factory",
      "project": "pyforge-marshal",
      "title": "regenerable-factory program",
      "caps": 4,
      "companions": 1,
      "updated": "2026-08-01",
      "dream": "regenerable-factory",
      "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-regenerable-factory"
    },
    {
      "slug": "copilot-cli-packaging",
      "project": "pyforge-mason",
      "title": "copilot-cli-packaging — retirement record",
      "caps": 0,
      "companions": 0,
      "updated": "2026-07-29",
      "dream": "copilot-cli-packaging",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-copilot-cli-packaging"
    },
    {
      "slug": "db-gpt-packaging",
      "project": "pyforge-mason",
      "title": "db-gpt-packaging — retirement record",
      "caps": 0,
      "companions": 0,
      "updated": "2026-07-29",
      "dream": "db-gpt-packaging",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-db-gpt-packaging"
    },
    {
      "slug": "fleet-stewardship",
      "project": "pyforge-mason",
      "title": "fleet stewardship (the recipes/ fleet)",
      "caps": 3,
      "companions": 3,
      "updated": "2026-07-29",
      "dream": "fleet-stewardship",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-fleet-stewardship"
    },
    {
      "slug": "packaging-factory",
      "project": "pyforge-mason",
      "title": "the packaging factory (conda-forge-expert machinery)",
      "caps": 4,
      "companions": 2,
      "updated": "2026-07-29",
      "dream": "packaging-factory",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-packaging-factory"
    },
    {
      "slug": "pyforge-mason",
      "project": "pyforge-mason",
      "title": "mason CLI — the packaging factory, made portable",
      "caps": 13,
      "companions": 5,
      "updated": "2026-08-02",
      "dream": "pyforge-mason",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason"
    },
    {
      "slug": "pyforge-mason-recipe-validator",
      "project": "pyforge-mason",
      "title": "pyforge-mason-recipe-validator — retirement record",
      "caps": 0,
      "companions": 0,
      "updated": "2026-08-02",
      "dream": "pyforge-mason-recipe-validator",
      "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason-recipe-validator"
    },
    {
      "slug": "pyforge-scribe",
      "project": "pyforge-scribe",
      "title": "Scribe (pyforge-scribe) — the team's inward voice",
      "caps": 4,
      "companions": 1,
      "updated": "2026-08-02",
      "dream": "pyforge-scribe",
      "path": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe"
    },
    {
      "slug": "pyforge-scribe-team-memory",
      "project": "pyforge-scribe",
      "title": "pyforge-scribe-team-memory — retirement record",
      "caps": 2,
      "companions": 0,
      "updated": "2026-08-02",
      "dream": "pyforge-scribe-team-memory",
      "path": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe-team-memory"
    },
    {
      "slug": "sentinel",
      "project": "pyforge-scribe",
      "title": "sentinel — retirement record",
      "caps": 0,
      "companions": 0,
      "updated": "2026-07-29",
      "dream": "sentinel",
      "path": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-sentinel"
    },
    {
      "slug": "team-memory",
      "project": "pyforge-scribe",
      "title": "team-memory — retirement record",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-02",
      "dream": "team-memory",
      "path": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-team-memory"
    },
    {
      "slug": "enterprise-airgap",
      "project": "pyforge-steward",
      "title": "the factory behind the firewall",
      "caps": 3,
      "companions": 1,
      "updated": "2026-07-29",
      "dream": "enterprise-airgap",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-enterprise-airgap"
    },
    {
      "slug": "pyforge-steward",
      "project": "pyforge-steward",
      "title": "Steward (pyforge-steward) — the estate the factory stands on",
      "caps": 4,
      "companions": 1,
      "updated": "2026-08-01",
      "dream": "pyforge-steward",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward"
    },
    {
      "slug": "pyforge-steward-feedstock-maintenance",
      "project": "pyforge-steward",
      "title": "pyforge-steward-feedstock-maintenance — retirement record",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-02",
      "dream": "pyforge-steward-feedstock-maintenance",
      "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward-feedstock-maintenance"
    },
    {
      "slug": "pyforge-warden",
      "project": "pyforge-warden",
      "title": "Warden — the compliance gate that never false-greens",
      "caps": 12,
      "companions": 3,
      "updated": "2026-07-29",
      "dream": "pyforge-warden",
      "path": "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden"
    },
    {
      "slug": "pyforge-warden-compliance-gates",
      "project": "pyforge-warden",
      "title": "pyforge-warden-compliance-gates — retirement record",
      "caps": 7,
      "companions": 0,
      "updated": "2026-08-02",
      "dream": "pyforge-warden-compliance-gates",
      "path": "_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden-compliance-gates"
    },
    {
      "slug": "pyforge-charter",
      "project": "docs/governance",
      "title": "The Charter — keeping the constitution true",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-02",
      "dream": "pyforge-charter",
      "path": "docs/governance/spec-pyforge-charter"
    },
    {
      "slug": "pyforge-genesis",
      "project": "docs/governance",
      "title": "Genesis — the operating model, recorded",
      "caps": 4,
      "companions": 0,
      "updated": "2026-08-02",
      "dream": "pyforge-genesis",
      "path": "docs/governance/spec-pyforge-genesis"
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
      "name": "Durable runs — work survives the machine that made it",
      "reason": "absorbed",
      "owner": "marshal",
      "note": "Durable runs — work survives the machine that made it",
      "link": "docs/dreams/durable-runs.md"
    },
    {
      "name": "Factory console — the whole pipeline on one page",
      "reason": "absorbed",
      "owner": "marshal",
      "note": "Factory console — the whole pipeline on one page",
      "link": "docs/dreams/factory-console.md"
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
      "name": "PR lifecycle — a story lands itself",
      "reason": "absorbed",
      "owner": "marshal",
      "note": "PR lifecycle — a story lands itself",
      "link": "docs/dreams/pr-lifecycle.md"
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
          "planning_project": "pyforge-doctor"
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
          "planning_project": "pyforge-steward"
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
          "planning_project": "pyforge-scribe"
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
          "planning_project": "pyforge-herald"
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
          "planning_project": "pyforge-marshal"
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
          "planning_project": "pyforge-mason"
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
          "planning_project": "pyforge-mason"
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
          "planning_project": "pyforge-atlas"
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
          "planning_project": "pyforge-atlas"
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
          "planning_project": "pyforge-genesis"
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
          "done": 3,
          "total": 19
        },
        {
          "slug": "pyforge-doctor",
          "pkey": "doctor",
          "stories": 12,
          "state": "running",
          "note": "line 2 — consolidative wrap",
          "done": 5,
          "total": 16
        },
        {
          "slug": "pyforge-scribe",
          "pkey": "scribe",
          "stories": 9,
          "state": "running",
          "note": "line 3 — team memory + graph",
          "done": 3,
          "total": 9
        },
        {
          "slug": "pyforge-steward",
          "pkey": null,
          "stories": 18,
          "state": "running",
          "note": "next free slot",
          "done": 3,
          "total": 18
        },
        {
          "slug": "pyforge-mason",
          "pkey": null,
          "stories": 38,
          "state": "running",
          "note": "longest persona line; CFE Rule-2 retro at closeout",
          "done": 4,
          "total": 38
        },
        {
          "slug": "presenton-pixi-image",
          "pkey": null,
          "stories": 30,
          "state": "held",
          "note": "operator Phase-0 gates: MS disconnected-stack check + memory-subsystem scope",
          "epics_path": "_bmad-output/projects/pyforge-mason/planning-artifacts/epics-presenton-pixi-image.md",
          "done": 0,
          "total": 30
        },
        {
          "slug": "pyforge-marshal",
          "pkey": null,
          "stories": 40,
          "state": "running",
          "note": "epics 1-6 — AD-25–39 adversarial pass + floor quiescence (touches loop machinery)",
          "done": 11,
          "total": 50
        },
        {
          "slug": "genesis-installer",
          "pkey": null,
          "stories": 36,
          "state": "held",
          "note": "epics 7-12 (same ledger as pyforge-marshal, split by epic) — last, model stability + consumes marshal-owned scripts",
          "epics_path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/epics-genesis-installer.md",
          "done": 0,
          "total": 36
        },
        {
          "slug": "wasm-analytics-stack",
          "pkey": null,
          "stories": 0,
          "state": "future",
          "note": "PRD+arch only by design; stories decompose when scheduled",
          "epics_path": null,
          "done": 0,
          "total": 0
        },
        {
          "slug": "unity-data-stack",
          "pkey": null,
          "stories": 0,
          "state": "future",
          "note": "PRD+arch only by design; stories decompose when scheduled",
          "epics_path": null,
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
    "sound": 3,
    "live": 22,
    "reached": 9,
    "gaps": 15,
    "findings": 0,
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
          "spec": "2026-08-02T14:50",
          "research": "2026-07-25",
          "brief": "2026-07-25",
          "prd": "2026-08-01",
          "ux": "",
          "arch": "2026-08-02",
          "context": "2026-08-04",
          "epics": "2026-08-02",
          "sprint": "2026-08-02",
          "tea": "2026-07-30",
          "gates": "2026-08-02",
          "code": "2026-07-29",
          "verify": "2026-07-29",
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
        "staleBy": [],
        "furthest": "retro",
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "0.1.0",
        "progress": "38/38",
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
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "2026-07-25",
          "spec": "2026-08-02T12:57",
          "research": "2026-07-25",
          "brief": "2026-07-25",
          "prd": "2026-08-02",
          "ux": "",
          "arch": "2026-08-02",
          "context": "2026-08-01",
          "epics": "2026-08-02",
          "sprint": "2026-08-02",
          "tea": "2026-07-31",
          "gates": "2026-08-01",
          "code": "2026-07-25",
          "verify": "2026-07-25",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": false,
              "technical": true
            },
            "n": 2,
            "of": 3,
            "missing": [
              "market"
            ],
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
          "verify"
        ],
        "gaps": [],
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "verify",
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "0.1.0",
        "progress": "5/16",
        "complete": 13,
        "of": 13
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
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "2026-07-25",
          "spec": "2026-08-02T14:45",
          "research": "2026-08-01",
          "brief": "2026-08-02",
          "prd": "2026-08-02",
          "ux": "",
          "arch": "2026-08-02",
          "context": "2026-08-02",
          "epics": "2026-08-02",
          "sprint": "2026-08-02",
          "tea": "2026-07-31",
          "gates": "2026-08-01",
          "code": "2026-07-25",
          "verify": "2026-07-25",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": false,
              "market": true,
              "technical": false
            },
            "n": 1,
            "of": 3,
            "missing": [
              "domain",
              "technical"
            ],
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
          "verify"
        ],
        "gaps": [],
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "verify",
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "0.1.0",
        "progress": "3/19",
        "complete": 13,
        "of": 13
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
          "dream": "2026-08-02",
          "deck": "2026-08-01",
          "spec": "2026-08-02T14:36",
          "research": "2026-07-31",
          "brief": "2026-08-02",
          "prd": "2026-08-02",
          "ux": "",
          "arch": "2026-08-02",
          "context": "2026-06-20",
          "epics": "2026-08-02",
          "sprint": "2026-08-02",
          "tea": "2026-08-02",
          "gates": "2026-08-02",
          "code": "2026-07-31",
          "verify": "2026-07-31",
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
        "staleBy": [],
        "furthest": "verify",
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "0.1.0",
        "progress": "11/50",
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
          "spec": "2026-08-02T14:38",
          "research": "2026-07-25",
          "brief": "2026-07-25",
          "prd": "2026-08-01",
          "ux": "",
          "arch": "2026-08-02",
          "context": "2026-08-02",
          "epics": "2026-08-02",
          "sprint": "2026-08-02",
          "tea": "2026-07-31",
          "gates": "2026-08-01",
          "code": "2026-07-25",
          "verify": "2026-07-25",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": false,
              "technical": true
            },
            "n": 2,
            "of": 3,
            "missing": [
              "market"
            ],
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "verify",
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "0.1.0",
        "progress": "4/38",
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
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-08-02",
          "deck": "2026-07-25",
          "spec": "2026-08-02T12:59",
          "research": "2026-07-25",
          "brief": "2026-07-25",
          "prd": "2026-08-01",
          "ux": "",
          "arch": "2026-08-02",
          "context": "2026-08-01",
          "epics": "2026-08-02",
          "sprint": "2026-08-02",
          "tea": "2026-07-31",
          "gates": "2026-08-01",
          "code": "2026-07-25",
          "verify": "2026-07-25",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": false
            },
            "n": 2,
            "of": 3,
            "missing": [
              "technical"
            ],
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
          "verify"
        ],
        "gaps": [],
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "verify",
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "0.1.0",
        "progress": "3/9",
        "complete": 13,
        "of": 13
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
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-07-25",
          "deck": "2026-07-25",
          "spec": "2026-08-01T09:51",
          "research": "2026-07-25",
          "brief": "2026-07-25",
          "prd": "2026-08-01",
          "ux": "",
          "arch": "2026-08-02",
          "context": "2026-08-01",
          "epics": "2026-08-02",
          "sprint": "2026-08-02",
          "tea": "2026-07-31",
          "gates": "2026-08-01",
          "code": "2026-07-25",
          "verify": "2026-07-25",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": false,
              "technical": true
            },
            "n": 2,
            "of": 3,
            "missing": [
              "market"
            ],
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
          "verify"
        ],
        "gaps": [],
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "verify",
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "0.1.0",
        "progress": "3/18",
        "complete": 13,
        "of": 13
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
          "retro": ""
        },
        "updatedAt": {
          "dream": "2026-07-25",
          "deck": "2026-07-24",
          "spec": "2026-07-29",
          "research": "2026-07-25",
          "brief": "2026-07-25",
          "prd": "2026-08-01",
          "ux": "",
          "arch": "2026-08-02",
          "context": "2026-08-01",
          "epics": "2026-08-02",
          "sprint": "2026-08-02",
          "tea": "2026-07-24",
          "gates": "2026-07-16",
          "code": "2026-07-24",
          "verify": "2026-07-24",
          "retro": ""
        },
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": false
            },
            "n": 2,
            "of": 3,
            "missing": [
              "technical"
            ],
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
          "verify"
        ],
        "gaps": [],
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "verify",
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "0.1.0",
        "progress": "31/31",
        "complete": 13,
        "of": 13
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
        "updated": "2026-08-02",
        "age": 1,
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
        "updated": "2026-08-02",
        "age": 1,
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
        "updated": "2026-08-02",
        "age": 1,
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
        "updated": "2026-08-02",
        "age": 1,
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
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 3,
        "of": 4
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
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": false,
              "technical": true
            },
            "n": 2,
            "of": 3,
            "missing": [
              "market"
            ],
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-02",
        "age": 1,
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
          "dream": "2026-08-02",
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
          "dream",
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
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 1,
        "of": 2
      },
      {
        "label": "genesis",
        "slug": "pyforge-genesis",
        "project": "docs/governance",
        "dream": "pyforge-genesis",
        "owner": "guild",
        "stages": {
          "dream": "2026-07-23",
          "deck": "2026-07-23",
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
          "dream": "2026-08-02",
          "deck": "2026-07-25",
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
        "ownerDream": "pyforge-genesis",
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
        "gaps": [],
        "partial": [],
        "staleBy": [],
        "furthest": "spec",
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 2
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
          "spec": "2026-08-02",
          "research": "2026-08-01",
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
              "market": true,
              "technical": false
            },
            "n": 1,
            "of": 3,
            "missing": [
              "domain",
              "technical"
            ],
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-02",
        "age": 1,
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
          "research": "2026-08-01",
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
              "market": true,
              "technical": false
            },
            "n": 1,
            "of": 3,
            "missing": [
              "domain",
              "technical"
            ],
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 4
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
          "spec": "2026-08-02",
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
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
          "spec": "2026-07-29",
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
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
          "dream": "2026-07-29",
          "deck": "",
          "spec": "2026-07-29",
          "research": "2026-07-31",
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
        "dreamStatus": "pitched",
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
        "updated": "2026-08-02",
        "age": 1,
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
          "spec": "2026-07-29",
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
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
          "spec": "2026-07-29",
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
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
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-02T17:11",
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
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
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 4
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
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-02",
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
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
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-01T09:45",
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
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
          "spec": "2026-08-02",
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
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
          "spec": "2026-08-02T13:19",
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
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
          "deck": "",
          "spec": "",
          "research": "2026-07-31",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "2026-07-31",
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
          "research",
          "brief",
          "prd",
          "arch",
          "context",
          "epics"
        ],
        "gaps": [
          "deck",
          "spec",
          "brief",
          "prd",
          "arch",
          "context"
        ],
        "partial": [],
        "staleBy": [],
        "furthest": "epics",
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 3,
        "of": 9
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
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-02T19:30",
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
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
          "spec": "2026-07-29",
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
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
          "spec": "2026-08-02",
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
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
          "dream": "2026-08-02",
          "deck": "",
          "spec": "2026-08-02",
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
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
          "spec": "2026-08-02",
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
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
          "spec": "2026-08-02T11:24",
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
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
          "spec": "2026-08-01T08:27",
          "research": "2026-07-31",
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
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 3,
        "of": 4
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
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": false,
              "technical": true
            },
            "n": 2,
            "of": 3,
            "missing": [
              "market"
            ],
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-02",
        "age": 1,
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
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": false,
              "technical": true
            },
            "n": 2,
            "of": 3,
            "missing": [
              "market"
            ],
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-02",
        "age": 1,
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
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": false,
              "technical": true
            },
            "n": 2,
            "of": 3,
            "missing": [
              "market"
            ],
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-02",
        "age": 1,
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
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": false,
              "technical": true
            },
            "n": 2,
            "of": 3,
            "missing": [
              "market"
            ],
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-02",
        "age": 1,
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
          "research": "2026-07-25",
          "brief": "",
          "prd": "",
          "ux": "",
          "arch": "",
          "context": "",
          "epics": "2026-08-02",
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
              "market": false,
              "technical": true
            },
            "n": 2,
            "of": 3,
            "missing": [
              "market"
            ],
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "epics",
        "updated": "2026-08-02",
        "age": 1,
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
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": false,
              "technical": true
            },
            "n": 2,
            "of": 3,
            "missing": [
              "market"
            ],
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-02",
        "age": 1,
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
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": false
            },
            "n": 2,
            "of": 3,
            "missing": [
              "technical"
            ],
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-02",
        "age": 1,
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
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": false
            },
            "n": 2,
            "of": 3,
            "missing": [
              "technical"
            ],
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-02",
        "age": 1,
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
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": false
            },
            "n": 2,
            "of": 3,
            "missing": [
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-02",
        "age": 1,
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
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": false,
              "technical": true
            },
            "n": 2,
            "of": 3,
            "missing": [
              "market"
            ],
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-02",
        "age": 1,
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
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": false,
              "technical": true
            },
            "n": 2,
            "of": 3,
            "missing": [
              "market"
            ],
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 3
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
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": false,
              "technical": true
            },
            "n": 2,
            "of": 3,
            "missing": [
              "market"
            ],
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-02",
        "age": 1,
        "stale": false,
        "version": "",
        "progress": "",
        "complete": 2,
        "of": 4
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
        "sub": {
          "research": {
            "have": {
              "domain": true,
              "market": true,
              "technical": false
            },
            "n": 2,
            "of": 3,
            "missing": [
              "technical"
            ],
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
        "partial": [
          "research"
        ],
        "staleBy": [],
        "furthest": "research",
        "updated": "2026-08-02",
        "age": 1,
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
              "res": "✅",
              "prod-brief": "✅",
              "PITCH-DECKS": "✅"
            }
          },
          {
            "name": "Marshal",
            "emoji": "⚔️",
            "statuses": {
              "DREAMS": "🚀",
              "res": "✅",
              "prod-brief": "✅",
              "PITCH-DECKS": "✅"
            }
          },
          {
            "name": "Atlas",
            "emoji": "🗺️",
            "statuses": {
              "DREAMS": "🚀",
              "res": "✅",
              "prod-brief": "✅",
              "PITCH-DECKS": "✅"
            }
          },
          {
            "name": "Warden",
            "emoji": "🛡️",
            "statuses": {
              "DREAMS": "🚀",
              "res": "✅",
              "prod-brief": "✅",
              "PITCH-DECKS": "✅"
            }
          },
          {
            "name": "Mason",
            "emoji": "🧱",
            "statuses": {
              "DREAMS": "🚀",
              "res": "✅",
              "prod-brief": "✅",
              "PITCH-DECKS": "✅"
            }
          },
          {
            "name": "Doctor",
            "emoji": "🏥",
            "statuses": {
              "DREAMS": "🚀",
              "res": "✅",
              "prod-brief": "✅",
              "PITCH-DECKS": "✅"
            }
          },
          {
            "name": "Scribe",
            "emoji": "📖",
            "statuses": {
              "DREAMS": "🚀",
              "res": "✅",
              "prod-brief": "✅",
              "PITCH-DECKS": "✅"
            }
          },
          {
            "name": "Steward",
            "emoji": "👑",
            "statuses": {
              "DREAMS": "🚀",
              "res": "✅",
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
        "gate": "Herald coding; others queued or ready",
        "stations": [
          {
            "name": "Herald",
            "emoji": "🎺",
            "statuses": {
              "sprint-status": "✅",
              "code": "✅",
              "tests": "✅",
              "retro": "◯"
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
              "retro": "◯"
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
              "retro": "◯"
            }
          },
          {
            "name": "Scribe",
            "emoji": "📖",
            "statuses": {
              "sprint-status": "✅",
              "code": "✅",
              "tests": "✅",
              "retro": "◯"
            }
          },
          {
            "name": "Steward",
            "emoji": "👑",
            "statuses": {
              "sprint-status": "✅",
              "code": "✅",
              "tests": "✅",
              "retro": "◯"
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
        "state": "drift",
        "findings": 3,
        "verdict": "DRIFT: 3 integrity + 0 currency finding(s). Re-sync via _bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md.",
        "runbook": "_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md"
      },
      {
        "name": "spec-surface",
        "task": "spec-surface-check",
        "guards": "every tracked file under a Spec surface",
        "state": "drift",
        "findings": 28,
        "verdict": "FINDINGS (28):",
        "runbook": ""
      },
      {
        "name": "llms-full",
        "task": "llms-full-check",
        "guards": "library catalog freshness",
        "state": "green",
        "findings": 0,
        "verdict": "",
        "runbook": ""
      }
    ],
    "baseline": {
      "skill": "8.81.0",
      "head": "f38ac349a0",
      "deltas": [],
      "runbook": "_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md"
    }
  },
  "backlog": {
    "rows": [
      {
        "slug": "dashboard-project-path-derivation",
        "title": "The dashboard assumes slug == project directory — it isn't, and won't stay",
        "status": "dreamt",
        "owner": "marshal",
        "blockedOn": "",
        "chain": {}
      },
      {
        "slug": "genesis-installer-name-retirement",
        "title": "Retire genesis-installer — one marshal CLI, one PRD/architecture/epics chain",
        "status": "dreamt",
        "owner": "marshal",
        "blockedOn": "",
        "chain": {
          "spec": "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-genesis-installer-name-retirement"
        }
      },
      {
        "slug": "unified-container",
        "title": "One container, eight stations",
        "status": "dreamt",
        "owner": "steward",
        "blockedOn": "",
        "chain": {}
      }
    ],
    "blocked": 0,
    "byOwner": {
      "marshal": 2,
      "steward": 1
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
        "status": "pitched"
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
        "total": 3,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 1,
          "realized": 0,
          "archived": 2,
          "practice": 0
        },
        "line": "paused 1.3",
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
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "marshal",
        "total": 18,
        "counts": {
          "dreamt": 2,
          "pitched": 0,
          "specified": 0,
          "realized": 2,
          "archived": 10,
          "practice": 4
        },
        "line": "in flight 2.2",
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
            "slug": "durable-runs",
            "title": "Durable runs — work survives the machine that made it",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "factory-console",
            "title": "Factory console — the whole pipeline on one page",
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
            "slug": "one-front-door",
            "title": "One front door — Marshal drives everything BMAD installs",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "pr-lifecycle",
            "title": "PR lifecycle — a story lands itself",
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
            "slug": "dashboard-project-path-derivation",
            "title": "The dashboard assumes slug == project directory — it isn't, and won't stay",
            "status": "dreamt",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "genesis-installer-name-retirement",
            "title": "Retire genesis-installer — one marshal CLI, one PRD/architecture/epics chain",
            "status": "dreamt",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "agentic-sdlc-autonomy",
            "title": "The Agentic SDLC — four views of autonomy, one governed factory",
            "status": "pitched",
            "type": "practice",
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
            "slug": "bmad-output-hygiene",
            "title": "One fabricated commit, eight stations of debris",
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
          }
        ]
      },
      {
        "station": "atlas",
        "total": 6,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 0,
          "realized": 1,
          "archived": 5,
          "practice": 0
        },
        "line": "complete",
        "load": 0,
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
            "slug": "pyforge-atlas",
            "title": "Atlas — the map that maintains itself",
            "status": "realized",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "warden",
        "total": 2,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 0,
          "realized": 1,
          "archived": 1,
          "practice": 0
        },
        "line": "complete",
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
          }
        ]
      },
      {
        "station": "mason",
        "total": 7,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 1,
          "realized": 0,
          "archived": 4,
          "practice": 2
        },
        "line": "paused 1.5",
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
        "total": 2,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 1,
          "realized": 0,
          "archived": 1,
          "practice": 0
        },
        "line": "paused 2.1",
        "load": 0,
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
        "total": 4,
        "counts": {
          "dreamt": 0,
          "pitched": 0,
          "specified": 1,
          "realized": 0,
          "archived": 3,
          "practice": 0
        },
        "line": "paused 1.4",
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
            "status": "specified",
            "type": "dream",
            "blockedOn": ""
          }
        ]
      },
      {
        "station": "steward",
        "total": 4,
        "counts": {
          "dreamt": 1,
          "pitched": 0,
          "specified": 1,
          "realized": 0,
          "archived": 1,
          "practice": 1
        },
        "line": "paused 1.4",
        "load": 1,
        "blocked": 0,
        "dreams": [
          {
            "slug": "pyforge-steward-feedstock-maintenance",
            "title": "\"Dream — PyForge Steward: Feedstock Maintenance Automation\"",
            "status": "archived",
            "type": "dream",
            "blockedOn": ""
          },
          {
            "slug": "unified-container",
            "title": "One container, eight stations",
            "status": "dreamt",
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
      },
      {
        "slug": "pyforge-genesis",
        "title": "Genesis — the seed of the operating model",
        "status": "specified"
      }
    ]
  },
  "openwork": {
    "open": 189,
    "done": 18,
    "triaged": 133,
    "bySeverity": {
      "critical": 0,
      "high": 1,
      "medium": 2,
      "low": 11,
      "unspecified": 175
    },
    "projects": [
      {
        "project": "pyforge-atlas",
        "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md",
        "open": 53,
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
        "project": "pyforge-marshal",
        "path": "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md",
        "open": 35,
        "done": 8,
        "triaged": 15,
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
          }
        ]
      },
      {
        "project": "pyforge-herald",
        "path": "_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md",
        "open": 26,
        "done": 3,
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
            "status": "open",
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
            "status": "open",
            "severity": "unspecified",
            "triaged": false
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
            "triaged": false
          }
        ]
      },
      {
        "project": "pyforge-steward",
        "path": "_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md",
        "open": 21,
        "done": 0,
        "triaged": 0,
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
          }
        ]
      },
      {
        "project": "pyforge-scribe",
        "path": "_bmad-output/projects/pyforge-scribe/planning-artifacts/deferred-work-ledger.md",
        "open": 6,
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
          }
        ]
      },
      {
        "project": "pyforge-mason",
        "path": "_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md",
        "open": 4,
        "done": 0,
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
          }
        ]
      },
      {
        "project": "pyforge-doctor",
        "path": "_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md",
        "open": 3,
        "done": 1,
        "triaged": 3,
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
          }
        ]
      }
    ]
  },
  "status": {
    "source": "sprint-status",
    "running": [
      {
        "station": "Marshal",
        "story": "2.2",
        "phase": "dev",
        "startEpoch": 1785740624
      }
    ],
    "lastShipped": {
      "station": "marshal",
      "story": "2.1",
      "epoch": 1785722370,
      "sha": "ef869e2dd",
      "subject": "Merge bmad-loop/20260802-183704-36df/2-1-standalone-verify-command-runner-project-scoped into loop/pyforge-marshal (bmad"
    },
    "runningAvailable": true,
    "generatedAt": "2026-08-03 07:26 UTC",
    "generatedEpoch": 1785741967
  },
  "storySpecs": [
    {
      "station": "pyforge-atlas",
      "done": 38,
      "tracked": 39,
      "gap": 0
    },
    {
      "station": "pyforge-doctor",
      "done": 5,
      "tracked": 5,
      "gap": 0
    },
    {
      "station": "pyforge-herald",
      "done": 4,
      "tracked": 4,
      "gap": 0
    },
    {
      "station": "pyforge-marshal",
      "done": 11,
      "tracked": 11,
      "gap": 0
    },
    {
      "station": "pyforge-mason",
      "done": 4,
      "tracked": 4,
      "gap": 0
    },
    {
      "station": "pyforge-scribe",
      "done": 3,
      "tracked": 3,
      "gap": 0
    },
    {
      "station": "pyforge-steward",
      "done": 3,
      "tracked": 4,
      "gap": 0
    },
    {
      "station": "pyforge-warden",
      "done": 31,
      "tracked": 31,
      "gap": 0
    }
  ]
};
