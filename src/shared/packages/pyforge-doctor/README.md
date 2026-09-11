# pyforge-doctor

Pre-flight + fleet-watch diagnostics CLI (`doctor check` / `doctor monitor` /
`doctor diagnose`) consolidating [`pyforge-warden`](../pyforge-warden) +
`cf_atlas` signals into one schema-validated `DoctorReport` envelope; findings
stay advisory — not a second PR gate.

**Status:** all 28 stories shipped (6 epics): the `check`/`monitor`/`diagnose` verbs are live, and `python -m pyforge.doctor.sources` dispatches the 10 detector sources the repo's gates run on
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
