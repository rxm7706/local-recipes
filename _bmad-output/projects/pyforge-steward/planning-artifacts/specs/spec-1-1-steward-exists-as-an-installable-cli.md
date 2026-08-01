<!-- RECOVERED 2026-08-04 Tier 3 (epics.md-derived Intent + ACs). Tier 1/2 recovery failed; promote to full narrative after development context known. -->
---
title: "Story 1-1: Steward exists as an installable CLI"
type: "feature"
created: "2026-07-???"
status: "done"
recovery_tier: 3
recovery_source: "epics.md:109-131"
recovery_date: "2026-08-04"
---

## Intent

As the repo maintainer, I want `pyforge-steward` to install and run as a real package (`steward --version` works) the same way `pyforge-warden` does today, so that every later duty has a package, a CLI dispatcher, and a shared contract to build against instead of starting from nothing.

## Acceptance Criteria

**Given** the repo's pixi workspace
**When** `src/shared/packages/pyforge-steward/` is scaffolded (`pyproject.toml` with `hatchling` backend, `[project.scripts] steward = "pyforge.steward.cli:main"`, `pixi.toml` with `[package.build.backend] name = "pixi-build-python"`) and wired into repo-root `pixi.toml` (`[feature.pyforge-steward.dependencies]` path-dependency into a lean `no-default-feature = true` `pyforge-steward` environment, plus `pyforge-steward-build-conda`/`-build-dist`/`-test`/`-dogfood` tasks mirroring `pyforge-warden`'s task names verbatim)
**Then** `pixi run -e pyforge-steward steward --version` prints a version string and exits 0
**And** `pixi run -e pyforge-steward pyforge-steward-test` runs a passing (if minimal) `pytest` suite under `tests/unit/`, `tests/conformance/`, `tests/meta/`

**Given** `cli.py`'s dispatcher
**When** an `argparse.ArgumentParser` with one subparser per duty (`keys`, `deploy`, `provision`, `budget` — the latter three accepting no verbs yet, since their duty modules land in later epics) is built
**Then** `steward --help` lists all four subcommands
**And** `main()` is the sole owner of the process exit code: it catches `KeyboardInterrupt` (→ a documented SIGINT exit code), `SystemExit` raised inside a duty (→ projected as an internal-error exit, never trusted verbatim), and any other `Exception` (→ a documented internal-error exit, never the bare interpreter default `1`) — per AD-8

**Given** `interfaces.py`
**When** a `Duty` `Protocol` (`name: str`, `run(ns: argparse.Namespace) -> DutyResult`) and a `DutyResult` dataclass are defined
**Then** a minimal `NullDuty`-shaped stub satisfies the protocol and is unit-tested for protocol conformance (mirrors `pyforge-warden`'s `interfaces.py` null-engine precedent) — per AD-7

**And** the repo-root `pixi.toml`'s existing `environment.yaml` sync-gate check still passes after this story's `pixi.toml` edits (CLAUDE.md's ungated CI check)

## Notes

This spec was recovered from epics.md-derived Intent + ACs only. Promote to full narrative spec + I/O matrix once story development context is available.
