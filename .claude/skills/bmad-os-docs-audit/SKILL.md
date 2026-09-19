---
name: bmad-os-docs-audit
description: Orchestrates a repository-wide documentation audit. Discovers unmapped Markdown files, identifies persona gaps, and delegates writing tasks to bmad-os-diataxis. Use when user asks to 'audit docs', 'find missing documentation', or 'update docs map'.
---

# Documentation Audit Skill

## Overview

This skill allows an autonomous agent to systematically audit the PyForge documentation footprint, ensuring adherence to the Diátaxis structure governed by `docs/MAP.md`. It does not write prose itself; instead, it discovers gaps and delegates the writing to the `bmad-os-diataxis` skill.

## On Activation

1. **Scan the Footprint**: Search for all `.md` files in `docs/`, `src/platform/`, and `src/shared/packages/`. Exclude `node_modules`, `.venv`, and `build_artifacts`.
2. **Parse the Map**: Read `docs/MAP.md` and extract all registered document paths.
3. **Analyze Alignment**:
   - Find any files that exist on disk but are not listed in `docs/MAP.md`.
   - Find any files listed in `docs/MAP.md` that do not exist on disk (broken links).
4. **Persona Gap Analysis**: 
   - Read `pixi.toml` for new tasks/environments.
   - Read `src/shared/packages/pyforge-*/cli.py` for new station duties.
   - Compare these capabilities against the existing operational guides in `docs/how-to/` and `docs/tutorials/`.
5. **Delegate**: For every identified gap, generate a specific writing prompt and spawn a subagent equipped with the `bmad-os-diataxis` skill to author or update the documentation.
6. **Report**: Present a comprehensive summary of discovered drift, created documents, and updated map entries to the user.

## Critical Constraints

- **Never write prose directly**: Your job is to orchestrate. Use `bmad-os-diataxis` for all prose generation.
- **Never modify Tier 2 or Tier 3 files**: Ignore `_bmad-output/` completely.
- **Never modify `docs/dreams/` or `docs/specs/`**: These are governed by the BMAD chain and are explicitly excluded from the general Diátaxis map.
