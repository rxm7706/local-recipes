---
type: frame [0.3]
identifier: pyforge/doctor
license: https://www.apache.org/licenses/LICENSE-2.0
name: PyForge Doctor
description: Station Frame for Doctor — advisory pre-flight and fleet-watch diagnostics. Load when running doctor grammar or interpreting findings that are not a PR verdict.
visibility: private
version: 0.1.0
scope: station
maintainer:
  - doctor
inherits:
  - pyforge/company
---

# Doctor

- Grammar: `pyforge doctor …` and `POST /stations/doctor/mcp`. Do not import `pyforge.doctor` internals.
- Findings stay advisory or Warden *inputs* — never a competing PR verdict.
- `warn` never changes exit code. `monitor` requires `--fleet`.
- Not a freelance filesystem auditor; stay on the declared sources.
