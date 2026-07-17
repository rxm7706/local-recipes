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

## Live-CLI verification (same day, post env-provisioning)

The pixi `local-recipes` environment was provisioned in the remote container
(pixi 0.73.0 via the conda-forge package; `pixi install --frozen`), and the
previously environment-deferred checks were executed live:

| Check | Result |
|---|---|
| `bmad-drift-check` | **OK — no findings** (53 files classified; run post-rename to `pyforge-atlas`) |
| `bmad-drift-check --specs` | kedro-migration spec listed `in-progress` ✓ |
| `bmad-groundtruth` | skill **v8.78.0**, schema **v29**, **46** MCP tools, **23** phases, gotchas G1–G106, 11 pixi envs — matches the § 3.3 snapshot and this note's git-surface verdict exactly |
| `llms-full-check` | clean — 216 active deps all cataloged, no ghost entries / floor drift |

The Wave-0 precondition items "live bmad-groundtruth / bmad-drift-check /
llms-full-check" are therefore discharged for this container; the attended
0.1 session re-runs them cheaply as a matter of course (they are
deterministic and fast).
