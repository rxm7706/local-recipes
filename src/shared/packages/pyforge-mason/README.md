# pyforge-mason

Mason — the Artisan Builder's station. `mason recipe` / `package` / `environment`.

- **Dream:** `docs/dreams/pyforge-mason.md`
- **Planning:** `_bmad-output/projects/pyforge-mason/planning-artifacts/`
- **Practice it tends:** `docs/dreams/packaging-factory.md`

Epic 1 (complete) delivers the runnable skeleton: dual-artifact build wiring,
the noun-verb CLI with global flags and dual output formats, the error
taxonomy/exit-code contract, CFE root+interpreter resolution with import-floor
probing and graceful degradation, `mason doctor`, the fake-CFE-root test
harness, and child-output streaming. The recipe / package / environment verbs
land story-by-story in Epics 2-4.

The `recipe` verb will **wrap** the `conda-forge-expert` craft by subprocess
rather than reimplement it — the skill stays canonical for recipe semantics and
keeps improving through the Rule-2 retro loop. It is never forked.
