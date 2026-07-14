# pyforge-warden

Unified dependency-hygiene + vulnerability scanner that orchestrates
[`deptry`](https://deptry.com/) (unused / missing / transitive deps) and
Google's [`osv-scanner`](https://github.com/google/osv-scanner) (known CVEs)
over Python / Conda / Pixi manifests, emitting one schema-validated
`ComplianceReport` and acting as a strict CI/CD exit-code gate.

**Status:** build skeleton — this is the Option B pixi *workspace member*
wiring only. The E1–E4 implementation is specified in
[`docs/specs/pyforge-warden.md`](../docs/specs/pyforge-warden.md) and delivered
via `bmad-quick-dev`.

## Develop

Run from the repository root (the parent pixi workspace):

```bash
pixi run -e pyforge-warden warden-scan          # run the scanner
pixi run -e pyforge-warden pyforge-warden-test  # run the test suite
```

The `pyforge-warden` environment is lean by design (`no-default-feature`): it
carries only the built package plus its conda run-dependencies
(`python`, `deptry`, `osv-scanner`) and a test runner.
