# pyforge-marshal

Deterministic BMAD-loop supervisor CLI (`marshal`) wrapping
[`bmad-loop`](https://github.com/bmad-code-org/bmad-loop) with gates-as-objects,
run supervision, landing, fleet status, and adapter portability -- built on a
closed verdict lattice and a coded finding registry.

**Status:** build skeleton (Story 1.1) -- this scaffold lands the package
layout, the closed 6-member verdict lattice + finding-code registry
(`core/model.py`, `core/findings.py`, `core/verdict.py`), and the one
response envelope (`Envelope`, AD-14/AD-39). No real command exists yet --
`marshal --version` / `marshal --help` are the only working invocations. See
[`_bmad-output/projects/pyforge-marshal/planning-artifacts/`](../../../../_bmad-output/projects/pyforge-marshal/planning-artifacts/)
for the PRD/architecture.

## Develop

Run from the repository root (the parent pixi workspace):

```bash
pixi run -e pyforge-marshal pyforge-marshal-test         # run the test suite
pixi run -e pyforge-marshal marshal --version             # console-script smoke test
pixi run -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml  # AD-3/AD-4 contracts

pixi run -e pyforge-marshal pyforge-marshal-build-conda   # .conda package via pixi-build-python
pixi run -e pyforge-marshal pyforge-marshal-build-dist    # wheel + sdist via `python -m build`
pixi run -e pyforge-marshal pyforge-marshal-build         # both of the above
```

The `pyforge-marshal` environment is lean by design (`no-default-feature`): it
carries only the built package plus its conda run-dependencies (`python`,
`pyyaml`, `tomlkit`, `psutil`, `jsonschema`), the build toolchain
(`hatchling`, `python-build`), a test runner (`pytest`), and `import-linter`.
