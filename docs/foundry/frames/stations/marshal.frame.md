---
type: frame [0.3]
identifier: pyforge/marshal
license: https://www.apache.org/licenses/LICENSE-2.0
name: PyForge Marshal
description: Station Frame for Marshal — deterministic BMAD-loop supervisor. Load when supervising runs, landing stories, or checking fleet/loop-home state.
visibility: private
version: 0.1.0
scope: station
maintainer:
  - marshal
inherits:
  - pyforge/company
---

# Marshal

- Grammar: `pyforge marshal …` and `POST /stations/marshal/mcp`. Do not import `pyforge.marshal` internals.
- Wraps bmad-loop with gates-as-objects, run supervision, landing, and Genesis seed.
- Hub Track field enumeration is a relay from steward's Intelligence Hub epic — do not invent a second factory-spin surface here.
- One agent, one worktree, one Story. Never `scripts/bmad-switch` from a parallel agent.
