---
id: SPEC-conda-forge-expert-rebuild
spec: conda-forge-expert-rebuild
status: absorbed
absorbed-into: spec-pyforge-mason
updated: "2026-09-17"
owner-dream: docs/dreams/conda-forge-expert-rebuild.md
surface:
  - .claude/skills/conda-forge-expert/**      # the skill being rebuilt slice by slice (parallel-run target; flips at the end cutover)
  - .claude/scripts/conda-forge-expert/**     # CLI wrapper layer — each slice redirects its wrappers
  - .claude/tools/conda_forge_server.py       # MCP registrations — each slice redirects its tools
companions:
  - campaign-state.yaml
  - slice-map.md
---

# Absorbed into spec-pyforge-mason

This Spec folder was folded on 2026-09-17 (one-chain-per-station CAP-3 / mason fold). The decision record is `.memlog.md` in this folder. Companion documents stay as record (CHAIN-STANDARD §7 item 3, marshal pilot lesson 15). Derived SPEC body disposed; git remains the historical record.
 Companion/record files kept in this folder: .memlog.md, campaign-state.yaml, slice-map.md.

