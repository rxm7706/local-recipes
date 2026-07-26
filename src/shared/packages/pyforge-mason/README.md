# pyforge-mason

Mason — the Artisan Builder's station. `mason recipe` / `package` / `environment`.

- **Dream:** `docs/dreams/pyforge-mason.md`
- **Planning:** `_bmad-output/projects/pyforge-mason/planning-artifacts/`
- **Practice it tends:** `docs/dreams/packaging-factory.md`

Story 1.1 delivers build wiring only: the dual-artifact manifest (one hatchling
`pyproject.toml` drives both the conda package and the wheel/sdist), the PEP 420
namespace, and an argparse dispatcher that reports `--version`.

The `recipe` verb will **wrap** the `conda-forge-expert` craft by subprocess
rather than reimplement it — the skill stays canonical for recipe semantics and
keeps improving through the Rule-2 retro loop. It is never forked.
