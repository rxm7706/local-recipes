<!-- RECOVERED 2026-08-04 Tier 3 (epics.md-derived Intent + ACs). Tier 1/2 recovery failed; promote to full narrative after development context known. -->
---
title: "Story 1-1: Workspace member scaffold and dual-artifact build"
type: "feature"
created: "2026-07-???"
status: "done"
recovery_tier: 3
recovery_source: "epics.md:180-218"
recovery_date: "2026-08-04"
---

## Intent

As a **maintainer of this repository**, I want **`pyforge-mason` to build as both a conda package and a wheel from one manifest**, so that **Mason is distributable the same way its sibling packages already are**.

## Acceptance Criteria

**Given** the repository root at `src/shared/packages/`
**When** the member package is created
**Then** `src/shared/packages/pyforge-mason/pyproject.toml` exists with `hatchling.build`, `name = "pyforge-mason"`, `requires-python = ">=3.12"`, and `[tool.hatch.build.targets.wheel] packages = ["src/pyforge"]`
**And** `[project.scripts]` declares `mason = "pyforge.mason.cli:main"`
**And** `src/pyforge/mason/` exists as a PEP-420 namespace package with **no** `src/pyforge/__init__.py`

**Given** the member package
**When** its `pixi.toml` is authored
**Then** it contains a `[package]` table and `[package.build.backend]` naming `pixi-build-python` `0.*`
**And** it contains **no** `[workspace]` table

**Given** the root `pixi.toml`
**When** workspace wiring is added
**Then** `[feature.pyforge-mason.dependencies]` declares `pyforge-mason = { path = "src/shared/packages/pyforge-mason" }`
**And** a `pyforge-mason` environment exists with `no-default-feature = true`
**And** tasks `pyforge-mason-build-conda`, `pyforge-mason-build-dist`, and `pyforge-mason-build` (depending on both) are defined

**Given** the build tasks
**When** `pyforge-mason-build` runs
**Then** a `.conda` file appears in `dist-conda/` and a wheel plus sdist appear in `dist/`
**And** `mason --version` reports the installed distribution version

**Given** NFR-10 and FR-41
**When** wheel dependencies are declared
**Then** only libraries `pyforge.mason` actually imports are listed
**And** no CLI-framework dependency (click, typer) is present

**Effort:** M. Realizes FR-36, FR-37, FR-38, FR-39, FR-41, NFR-11.

## Notes

This spec was recovered from epics.md-derived Intent + ACs only. Promote to full narrative spec + I/O matrix once story development context is available.
