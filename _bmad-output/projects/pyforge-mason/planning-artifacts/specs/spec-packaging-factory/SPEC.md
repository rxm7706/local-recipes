---
id: SPEC-packaging-factory
spec: packaging-factory
status: absorbed
absorbed-into: spec-pyforge-mason
updated: "2026-09-17"
owner-dream: docs/dreams/packaging-factory.md
surface:
  - .claude/skills/conda-forge-expert/**
  - .claude/scripts/conda-forge-expert/**
  - .claude/tools/conda_forge_server.py
surface-drift-exclude:
  # 2026-09-12: also governed by the spec(s) named below, which already
  # reconciles each of these files cleanly -- this kernel spec's own
  # memlog does not move for routine story work anymore, so double-
  # claiming them only produced permanent drift-presumed noise here.
  # Coverage is unchanged (still listed under `surface:` above); only
  # this spec's own drift tracking for these specific files is off.
  - .claude/skills/conda-forge-expert/tests/conftest.py   # also governed by pyforge-mason/spec-conda-forge-expert-rebuild
surface-drift: sentinel:.claude/skills/conda-forge-expert/CHANGELOG.md
companions:
  - ../../../../../../.claude/skills/conda-forge-expert/SKILL.md        # adopted: the living operating contract (v8.90.1)
  - ../../../../../../.claude/skills/conda-forge-expert/CHANGELOG.md    # adopted: the release record Rule 2 maintains
---

# Absorbed into spec-pyforge-mason

This Spec folder was folded on 2026-09-17 (one-chain-per-station CAP-3 / mason fold). The decision record is `.memlog.md` in this folder. Companion documents stay as record (CHAIN-STANDARD §7 item 3, marshal pilot lesson 15). Derived SPEC body disposed; git remains the historical record.
 Companion/record files kept in this folder: .memlog.md.

