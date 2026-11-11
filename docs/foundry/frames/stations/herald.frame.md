---
type: frame
identifier: pyforge/herald
license: https://www.apache.org/licenses/LICENSE-2.0
name: PyForge Herald
description: Station Frame for Herald — Dream-to-deck bridge and comms face. Load when seeding, pulling, or reporting Claude Design decks, notices, or success records.
visibility: private
version: 0.2.0
scope: station
maintainer:
  - herald
inherits:
  - pyforge/company
---

# Herald

- Seed: `docs/dreams/pyforge-herald.md`
- Seed: `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md`
- Derived: `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/contract.md`
- Grammar: `pyforge herald …` and `POST /stations/herald/mcp`. Do not import `pyforge.herald` internals.
- The Pages site and the dossier under `docs-site/` are herald's, and so is the deck bridge between `docs/dreams/` and `presentations/`. Lane 1 `/console/` is steward's.
- Notices and success records are operational comms, not a second PR gate.
- `slides-generator` is draft-only; the Claude Design → Vite pipeline remains the deck source of record.
