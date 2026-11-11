# pyforge-mason

General documentation (architecture, operations, how-tos): docs/MAP.md at the repository root.

Mason — the Artisan Builder's station. `mason recipe` / `package` / `environment`.

- **Dream:** `docs/dreams/pyforge-mason.md`
- **Planning:** `_bmad-output/projects/pyforge-mason/planning-artifacts/`
- **Practice it tends:** `archive/docs/dreams/packaging-factory.md`

Mason ships its three verb-bearing nouns and `doctor`: `recipe` (`new`, `validate`,
`build`, `diagnose`, `optimize`, `scan`, `submit`, `update`), `package` (`build`,
`ship`) and `environment` (`lock`, `check`), on a noun-verb CLI with global flags,
text and JSON output and one exit-code contract. CFE root and interpreter
resolution probes the import floor and degrades gracefully; `mason doctor`
reports it. The package's Python floor is 3.14 (decision D6).

The `recipe` noun **wraps** the `conda-forge-expert` craft by subprocess
rather than reimplementing it — the skill stays canonical for recipe semantics and
keeps improving through the Rule-2 retro loop. It is never forked.

**Agents:** consult `.claude/skills/conda-forge-expert/SKILL.md` for every recipe
question; consult this package's compiled station skill (`.claude/skills/pyforge-mason/`)
for `pyforge mason …` grammar, `package`/`environment` crafts and `doctor` — the
grammar reaches every verb; never import `pyforge.mason` internals.

**The MCP face is a supervised build, not a second grammar.** `POST /stations/mason/mcp`
(django-mason's `mcp_asgi.py`) serves `start_build`, which returns a handle, and
`get_build`, which returns the run's record. Its runner, `run_build`, runs one row of
django-pyforge's closed verb table, `pyforge mason recipe build recipes/<slug> --format json`
for a recipe tracked in git, and refuses while the kill switch
`pyforge.steward.start_tool_cli` is off. No other Mason verb is reachable through the
face (EGM MAS-R-F2).

The JSON envelope, the ship states and the exit codes are written down in the Spec's
public contract, `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md`.
