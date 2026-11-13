---
type: frame
identifier: pyforge/warden
license: https://www.apache.org/licenses/LICENSE-2.0
name: PyForge Warden
description: Station Frame for Warden — sole PR-gate verdict over dependency hygiene, vulns, license, and currency. Load when scanning manifests or projecting a compliance exit code.
visibility: private
version: 0.2.0
scope: station
maintainer:
  - warden
inherits:
  - pyforge/company
---

# Warden

- Seed: `docs/dreams/pyforge-warden.md`
- Seed: `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md`
- Derived: `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md`, `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md`
- Grammar: `warden scan` / `pyforge warden scan`. Import only the symbols `contract.md` names.
- The CLI is the sole gate; its exit enum is {0, 1, 2, 130}. `--doctor` never exits 1. Do not invent a second PR-gate verdict; Hub "Guard" language must not mint another verdict beside this one.
- CAP-24, CAP-25 and CAP-26 sit behind feature flags that default off (off in production, on in dev and staging); `contract.md` lists them.
- The fix-PR actuator (`scan --open-fix-prs`) runs after the verdict; `--fix-prs-dry-run` plans it without opening a socket.
- The fleet run is the portal's (`django-warden`), A-only.
- Does not replace `conda-forge-expert`.
