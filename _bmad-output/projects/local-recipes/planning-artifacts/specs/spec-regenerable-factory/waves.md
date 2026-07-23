# Waves — regenerable-factory program

Companion to `SPEC.md` (CAP-2 order). Formal epics + story files are produced
from this matrix by `bmad-create-epics-and-stories` at loop-prep; the loop
runs on the Wave-0 harness (`scripts/bmad-loop-worktree local-recipes`).

| Wave | Story | What | Mode |
|---|---|---|---|
| 0 | 0.1 | Multi-loop isolation harness (`spec-multi-loop-isolation`) | **DONE 2026-07-23** |
| 0 | 0.2 | This program spec | **DONE 2026-07-23** |
| 1 | 1.1 | Surface-manifest convention (CAP-1): retrofit `surface:` onto multi-loop-isolation + design-code-bridge kernels | gated |
| 1 | 1.2 | `scripts/spec_surface_check.py` v1 (CAP-3): coverage + allowlist + drift baseline, pixi task | gated |
| 2 | 2.1 | Pilot backfill: factory-console kernel + surface manifest (`docs/dashboard/**`) | gated |
| 2 | 2.2 | Regeneration drill on `docs/dashboard/generate.py` (CAP-4) | gated |
| 3 | 3.1 | Backfill: enterprise-airgap (grounds: `docs/reference/enterprise-deployment.md`, `_http.py` routing) | auto |
| 3 | 3.2 | Backfill: modernist-identity (grounds: DS project, deck engine files) | auto |
| 4 | 4.1 | Deep backfill: packaging-factory — `bmad-document-project` over the CFE skill surface, then kernel (+Rule 1) | auto |
| 4 | 4.2 | Deep backfill: fleet-stewardship (absorbs the 3 legacy workflow specs' contracts) | auto |
| 4 | 4.R | Rule-2 closeout: `bmad-retrospective` against the CFE skill | required |
| 5 | 5.1 | Chain-verify + manifests: pyforge-atlas, design-code-bridge, pyforge-marshal (existing chains) | auto |
| 5 | 5.2 | Checker → CI gate; coverage to 100%-or-allowlisted repo-wide | gated |
| 5 | 5.3 | Console drill-through: Dreamscape chip → deck / spec / project row (factory-console frontier) | auto |

Gating: `gated` = human approval before merge (graduated-gates on the new
pattern); `auto` = unattended once Waves 1–2 prove the pattern; Wave-4 retro
is mandatory (Rule 2).

Dashboard: this program gets a third project entry in `docs/dashboard/data.js`
at loop-prep so the console tracks it (done-detection:
`Merge bmad-loop/<run-id>/<story>` on main).
