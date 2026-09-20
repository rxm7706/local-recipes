---
title: "Story 1-1: Workspace member scaffold and dual-artifact build"
type: "feature"
created: "2026-07-???"
status: "done"
recovery_tier: 3
recovery_source: "epics.md:180-218"
recovery_date: "2026-08-04"
---

<!-- RECOVERED 2026-08-04 Tier 3 (epics.md-derived Intent + ACs). Tier 1/2 recovery failed; promote to full narrative after development context known. -->

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

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `8a90d7025c` (2026-07-25, "mason + steward: record Story 1.1 in the spec memlogs; re-baseline surfaces"); also `c9c5b33930` (2026-07-25, "mason + steward: Story 1.1 — two stations reach code, chain 8/9 -> 9/9"). Ledger row `1-1-workspace-member-scaffold-and-dual-artifact-build: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`, `docs/dashboard/data.js`, `scripts/.spec-surface-baseline.json`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
