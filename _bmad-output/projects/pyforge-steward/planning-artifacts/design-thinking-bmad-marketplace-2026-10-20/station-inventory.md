# Station inventory — skills & agents a work teammate could use

Source: `rxm7706/local-recipes` @ `53aed16fe` (main, 2026-10-19 05:49 CDT), read-only. Compiled 2026-10-20.
Stations found (`docs/foundry/frames/stations/*.frame.md`, `src/shared/packages/pyforge-*`): **atlas, doctor, herald,
marshal, mason, scribe, steward, warden** (8). Each has three layers:

- **Persona agent** `.claude/skills/bmad-agent-<station>/` (SKILL.md + customize.toml). Every one says it "acts only through
  pyforge <station> grammar and POST /stations/<station>/mcp", and activation runs
  `uv run {project-root}/_bmad/scripts/resolve_customization.py`. So it needs the station CLI **and** the station MCP server
  (Django `django-<station>` package) **and** a `_bmad/` project.
- **CLI skill** `.claude/skills/pyforge-<station>/0.1.0/pyforge-<station>/SKILL.md` (SKF-exported 2026-08-26, "claude-code, other").
  Teaches `pixi run -e pyforge-<station> <cmd>`; cites `src/shared/packages/...` source lines.
- **Python package** `src/shared/packages/pyforge-<station>/` (pyproject, depends on `pyforge-core`). SKILL texts say
  "PyPI `pyforge-<station>` 0.1.0", but **pypi.org returns 404** for pyforge-core/-mason/-scribe/-warden (checked 2026-10-20).
  No conda recipe exists for any station package; the only `pyforge-*` recipe is `recipes/pyforge-estate-catalog`.

Portability: **High** = drop into any repo, no estate tooling. **Medium** = generic job, but needs a station package
installed (not yet published) and the skill text rewritten off `pixi run -e …` / repo paths. **Low** = needs estate
internals (station servers, `_bmad-output`, `.bmad-loops`, conda-forge infra, rxm7706 config).

| Station | Item (path under `.claude/skills/`) | What a teammate would use it for | Portability | Packaged? |
|---|---|---|---|---|
| warden | `pyforge-warden/…` | Scan Python/Conda/Pixi manifests for vulnerable or unlicensed deps (osv-scanner, CycloneDX SBOM); has an **offline OSV DB** mode | **Medium** (deps: PyYAML, cyclonedx, packageurl, license-expression + external scanners) | No |
| warden | `bmad-agent-warden` | Persona over the scanner | Low | No |
| mason | `mason-environment` | Lock mixed conda + pip manifests into one lockfile; check it isn't stale | **Medium** — closest fit to Artifactory conda/pip teams | No |
| mason | `mason-package` | Build wheel, sdist and conda artifacts from one manifest; ship to PyPI/TestPyPI/a conda channel | **Medium** | No |
| mason | `pyforge-mason/…` | CLI grammar for recipe/package/environment crafts | Medium | No |
| mason | `mason-feedstock-failure-remediation`, `mason-feedstock-platform-expansion` | Fix failing conda-forge feedstock PRs; widen build matrix | Low (conda-forge infra; rxm7706 refs) | No |
| mason (CFE) | `conda-forge-expert` | Full conda recipe lifecycle: generate, scan, build, debug, submit | **Low** as-is (381 files; 62 files say `pixi run`, 84 cite repo paths, 49 mention rxm7706; `pixi install -e local-recipes` ≈10 GB) — high value for conda packagers if slimmed | No |
| mason | `bmad-agent-mason` | Persona | Low | No |
| scribe | `pyforge-scribe/…` | Capture team decisions and recall cited answers ("why did we pin X") | Medium-Low (writes `.claude/memory`; Postgres is an optional extra; graph features need graphifyy) | No |
| scribe | `bmad-agent-scribe` | Persona | Low | No |
| doctor | `pyforge-doctor/…` | Pre-flight checks and fleet-watch diagnostics, advisory findings | Low (checks are estate-shaped) | No |
| atlas | `pyforge-atlas/…`, `cf-atlas-legacy` | conda-forge ecosystem data pipelines (Kedro/Dagster/DuckDB) | Low (conda-forge-specific data) | No |
| herald | `pyforge-herald/…` | Seed/pull Claude Design decks; reports | Low (Claude Design bridge, playwright, boto3) | No |
| marshal | `pyforge-marshal/…`, `marshal-run-watch` | Supervise BMAD-loop runs, fleet status | Low (`.bmad-loops`, rxm7706 refs) | No |
| steward | `pyforge-steward/…` | Provision keys, deploy, suite install, the v1 catalog | Low (estate provisioner) | No |
| all 8 | `bmad-agent-<station>` | Address the station as a persona | **Low** (MCP server + `_bmad`) | No |

Not station-owned but in the same skills folder:
- **BMAD official modules** (bmad-builder, CIS, TEA, utility-skills, bmad-method, …): already conda-packaged under `recipes/bmad-*`;
  installers copy skills into `.claude/skills/` (e.g. `bmad-cis-install --dest`, default `.claude/skills`). Upstream-owned.
- **Generic engineering skills** (`api-and-interface-design`, `code-review-and-quality`, `test-driven-development`, `idea-refine`,
  `using-agent-skills`, …): frontmatter says `source: https://github.com/addyosmani/agent-skills` — **third-party**, already
  conda-packaged as `recipes/agent-skills` (0.5.0, into `$PREFIX/share/agent-skills`). Not rxm7706's to list as his.
- `slides-generator`, `multi-repo-git-ops`: High portability, no estate refs; origin not recorded in frontmatter (added in a bulk
  import, PR #1184, 2026-09-10) — check licence/authorship before listing.
- Other skill-bundle recipes already in the repo: `andrej-karpathy-skills`, `kedro-skills`, `bmad-labs-skills`, `skillsctl`.
  **Proven pattern: a noarch conda package that ships skill folders + a small installer** — directly reusable for Artifactory.

## Recommended first 3–5 listings (evidence-based)

1. **Warden dependency & vulnerability scan** (`pyforge-warden` skill + package). Generic job for any Python/conda repo;
   offline OSV DB fits "no public github.com at install time"; small, declared dependency set. Needs: publish wheel/conda to
   Artifactory, rewrite skill off `pixi run -e pyforge-warden`.
2. **Mason environment lock/check** (`mason-environment` + `pyforge-mason`). Matches the teammates' stack exactly
   (conda + pip via Artifactory). Same publish + rewrite work.
3. **Mason package build/ship** (`mason-package`). Teammates who publish internal packages to Artifactory; same package as #2,
   so one install covers both listings.
4. **Scribe team memory** (`pyforge-scribe`) — optional 4th. A team-level job ("why did we decide X"), Postgres optional; but it
   writes to `.claude/memory`, so it's Claude-shaped and needs a tool-neutral path.
5. **A slim "conda recipe helper" cut of `conda-forge-expert`** — high value, but only after stripping estate paths and the
   10 GB env; not a week-one item.

Not recommended first: the 8 `bmad-agent-*` personas (need station MCP servers running), atlas/herald/marshal/steward
(estate/conda-forge-specific), and the addyosmani skills (not ours; teammates can install `agent-skills` directly).
