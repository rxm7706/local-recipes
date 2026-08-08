<!-- RECOVERED 2026-08-08 Tier 3 (epics.md-derived Intent + ACs). No session transcript or
     bmad-loop worktree snapshot survived for this story (it landed via a manual maintainer-edit
     PR, not a bmad-loop run) — regenerated from epics.md per CLAUDE.md's recovery priority order. -->
---
title: "Story 2-1: Atlas gather filter — staleness axis, MCP-first with CLI fallback"
type: "feature"
created: "2026-08-07"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-08-08"
---

## Intent
`doctor monitor --fleet --watch staleness` queries cf_atlas's `staleness_report` signal via
whichever access path is available (MCP tool if an in-process client exists, else the
`staleness-report` CLI through `doctor.cli_bridge`), so the same command works identically for a
human at a terminal and an MCP-capable agent (Marshal). FR-5, AD-6.

## Acceptance Criteria

- **Given** an MCP client is available in-process, **When** `doctor monitor --fleet --watch
  staleness` runs, **Then** `doctor.sources.atlas` calls the `staleness_report` MCP tool and
  normalizes its output into `Finding(source=Source.STALENESS_REPORT, ...)` objects.
- **Given** no MCP client is available (bare terminal invocation), **When** the same command
  runs, **Then** `doctor.sources.atlas` falls back to the `staleness-report` CLI via
  `doctor.cli_bridge` (AD-5) — argv as a list, bounded timeout, `NO_COLOR`-equivalent discipline,
  typed `Finding(status=fail)` on subprocess failure — and produces the **same** `Finding` shape
  as the MCP path for equivalent underlying data.
- **Given** the repo, **When** a meta-test runs, **Then** it asserts `doctor.cli_bridge` is the
  only module in `pyforge-doctor` containing a `subprocess` call (AD-5's sole-subprocess-site
  guard, mirroring Story 1.2's AD-1 guard).

## Delivery Record
Merged via PR #290 (`doctor: Story 2.1 — atlas gather filter, staleness axis, MCP-first with CLI
fallback`), merge commit `095a5087c5`, 2026-08-07T11:25:38Z.
https://github.com/rxm7706/local-recipes/pull/290

## Notes
This is the pattern Stories 2.2 (cve/abandonment axes) and 4.3 (adoption-tracking axis) extend
verbatim — see epics.md's own cross-references at Stories 2.2 and 4.3.
