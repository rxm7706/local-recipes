---
type: frame
identifier: pyforge/doctor
license: https://www.apache.org/licenses/LICENSE-2.0
name: PyForge Doctor
description: Station Frame for Doctor — advisory pre-flight and fleet-watch diagnostics. Load when running doctor grammar or interpreting findings that are not a PR verdict.
visibility: private
version: 0.2.0
scope: station
maintainer:
  - doctor
inherits:
  - pyforge/company
---

# Doctor

- Seed: `docs/dreams/pyforge-doctor.md`
- Seed: `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`
- Derived: `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/contract.md`
- Grammar: `pyforge doctor …`, `python -m pyforge.doctor.sources <name>` for one source, and `POST /stations/doctor/mcp`. Do not import `pyforge.doctor` internals.
- Findings stay advisory or Warden *inputs* — never a competing PR verdict. The exit domain is {0, 2, 130}; `warn` never changes the exit code. `monitor` requires `--fleet`.
- The kill switch (`doctor flags kill-switch`) is its one actuator.
- Not a freelance filesystem auditor; stay on the declared sources.
