# pyforge-doctor

Pre-flight + fleet-watch diagnostics CLI (`doctor check` / `doctor monitor` /
`doctor diagnose`) consolidating [`pyforge-warden`](../pyforge-warden) +
`cf_atlas` signals into one schema-validated `DoctorReport` envelope and its
own exit-code gate.

**Status:** build skeleton (Story 1.1) — this scaffold lands the package
layout, the frozen `Finding`/`DoctorReport` contract (`models.py`), and
Doctor's own sole-owned exit-code projection (`verdict.py`, domain
`{0, 2, 130}`). No `check`/`monitor`/`diagnose` verb is implemented yet —
`doctor --version` / `doctor --help` are the only working invocations. See
[`_bmad-output/projects/pyforge-doctor/planning-artifacts/`](../../../../_bmad-output/projects/pyforge-doctor/planning-artifacts/)
for the PRD/architecture.

## Develop

Run from the repository root (the parent pixi workspace):

```bash
pixi run -e pyforge-doctor pyforge-doctor-test  # run the test suite
pixi run -e pyforge-doctor doctor --version     # console-script smoke test
```

The `pyforge-doctor` environment is lean by design (`no-default-feature`): it
carries only the built package plus its conda run-dependencies (`python`,
`jsonschema`) and a test runner.
