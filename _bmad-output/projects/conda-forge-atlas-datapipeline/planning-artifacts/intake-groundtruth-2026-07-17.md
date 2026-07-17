# Intake Groundtruth Check — 2026-07-17

Per the spec's **Groundtruth rule** (§ 1): re-verify the migration surface at BMAD
intake rather than trusting inline literals.

## Verdict

**The spec's § 3.3 live-surface snapshot (grounding commit `58a6dcc`, skill
v8.78.0, 2026-07-16) remains valid at intake HEAD `4cf1b74` (2026-07-17).**

## Evidence

`git diff --stat 58a6dcc..4cf1b74` over the atlas migration surface:

| Surface | Drift |
|---|---|
| `.claude/skills/conda-forge-expert/` (skill, scripts, phases, CLIs) | none |
| `.claude/scripts/` (CLI entrypoint layer) | none |
| `.claude/tools/` (FastMCP server) | none |
| `recipes/` | none |
| `pixi.toml` | +3 lines — pyforge-warden **test-only** oracles (`py-rattler`, `py-rattler-build`, `conda-build`), scoped to `feature.pyforge-warden`; not part of the atlas surface |

Everything else that landed between the two commits is pyforge-warden work
(PR #65) and the kedro-migration spec/analysis artifacts themselves (PR #64).
No cf_atlas phase, CLI, MCP tool, or schema changed — the § 3.3 counts
(23 cataloged phases, 28 read CLIs, schema v29) carry forward unchanged.

## Caveats

- `pixi run -e local-recipes bmad-groundtruth` and `bmad-drift-check` could not
  be executed in this remote container (pixi environments not provisioned;
  `.pixi/` is a stub). The check above is the git-surface equivalent. Run the
  live groundtruth CLI at the first workstation session — it is already listed
  in the Wave-0 preconditions (§ 14) before any loop run.
- Skill version pin: § 3.3 states v8.78.0; no skill CHANGELOG entries landed
  after `58a6dcc`, so the pin is current.
