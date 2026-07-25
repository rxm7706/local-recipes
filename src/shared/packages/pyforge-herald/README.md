# pyforge-herald

Dream-to-deck bridge CLI (`herald`) that seeds, pulls, and syncs [Claude
Design](https://claude.ai/design) decks against this repo's `docs/dreams/`
and `presentations/` trees via the `herald deck` subcommands.

**Status:** build skeleton — this is the Option B pixi *workspace member*
wiring only. The transport/bridge-core/state/error-hierarchy/registry
implementation is specified in
[`_bmad-output/projects/pyforge-herald/planning-artifacts/`](../../../../_bmad-output/projects/pyforge-herald/planning-artifacts/)
and delivered via later stories.

## Develop

Run from the repository root (the parent pixi workspace):

```bash
pixi run -e pyforge-herald herald deck --help  # CLI help
pixi run -e pyforge-herald pyforge-herald-test  # run the test suite
```

The `pyforge-herald` environment is lean by design (`no-default-feature`): it
carries only the built package plus its conda run-dependencies (`python`),
the build tooling that produces it (`hatchling`, `python-build`), and a test
runner (`pytest`).
