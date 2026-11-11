---
type: frame
identifier: pyforge/steward
license: https://www.apache.org/licenses/LICENSE-2.0
name: PyForge Steward
description: Station Frame for Steward — the estate's provisioner and the cutover control plane; its duties are the ones contract.md lists. Load when running estate duties or opening worktrees.
visibility: private
version: 0.2.0
scope: station
maintainer:
  - steward
inherits:
  - pyforge/company
---

# Steward

- Seed: `docs/dreams/pyforge-steward.md`
- Seed: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`
- Derived: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/oracle-map.md`
- Grammar: `pyforge steward …` / `steward`. Do not import `pyforge.steward` internals.
- Duties return `DutyResult` and never `sys.exit`; `main()` owns the process exit code.
- Prefer `pyforge steward workspace start <slug>` over hand `git worktree add`.
- Owns the Intelligence Hub estate recording and in-repo Frame preflight. Relays Track to marshal and Frame-store pointers to scribe.
