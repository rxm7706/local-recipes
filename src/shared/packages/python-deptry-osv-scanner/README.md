# python-deptry-osv-scanner

Unified dependency-hygiene + vulnerability scanner that orchestrates
[`deptry`](https://deptry.com/) (unused / missing / transitive deps) and
Google's [`osv-scanner`](https://github.com/google/osv-scanner) (known CVEs)
over Python / Conda / Pixi manifests, emitting one schema-validated
`ComplianceReport` and acting as a strict CI/CD exit-code gate.

**Status:** build skeleton — this is the Option B pixi *workspace member*
wiring only. The E1–E4 implementation is specified in
[`docs/specs/python-deptry-osv-scanner.md`](../docs/specs/python-deptry-osv-scanner.md) and delivered
via `bmad-quick-dev`.

## Develop

Run from the repository root (the parent pixi workspace):

```bash
pixi run -e python-deptry-osv-scanner python-deptry-osv-scan          # run the scanner
pixi run -e python-deptry-osv-scanner python-deptry-osv-scanner-test  # run the test suite
```

The `python-deptry-osv-scanner` environment is lean by design (`no-default-feature`): it
carries only the built package plus its conda run-dependencies
(`python`, `deptry`, `osv-scanner`) and a test runner.
