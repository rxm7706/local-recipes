---
type: frame [0.3]
identifier: pyforge-herald
license: https://www.apache.org/licenses/LICENSE-2.0
name: pyforge-herald
description: Station Frame for Herald — Dream-to-deck bridge and comms face. Load when seeding, pulling, or reporting Claude Design decks, notices, or success records.
visibility: private
owner: herald
version: 0.1.0
scope: station
inherits: pyforge
---

# Herald

- Grammar: `pyforge herald …` and `POST /stations/herald/mcp`. Do not import `pyforge.herald` internals.
- Owns deck seed / pull / status against `docs/dreams/` and `presentations/`. Lane 1 CMS stays steward.
- Notices and success records are operational comms, not a second PR gate.
- `slides-generator` is draft-only; the Claude Design → Vite pipeline remains the deck source of record.
