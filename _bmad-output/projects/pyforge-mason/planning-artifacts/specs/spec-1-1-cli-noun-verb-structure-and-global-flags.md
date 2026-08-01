<!-- RECOVERED 2026-08-04 Tier 3 (epics.md-derived Intent + ACs). Tier 1/2 recovery failed; promote to full narrative after development context known. -->
---
title: "Story 1-1: CLI noun-verb structure and global flags"
type: "feature"
created: "2026-07-???"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-08-04"
---

## Intent
Define the canonical noun-verb CLI structure for the Mason choreography engine, establish global flag conventions (dry-run, retry, timeout, output format), and ensure consistency across all Mason subcommands.

## Acceptance Criteria
- CLI follows the `mason <noun> <verb>` pattern (e.g., `marshal exec`, `marshal test`, `marshal gate`)
- Global flags (--dry-run, --retry, --timeout, --json, --verbose) are available on all subcommands
- Help text is generated from the command structure
- All Mason CLI examples in architecture/PRD use the canonical structure

## Notes
This spec was recovered from epics.md-derived ACs only. Promote to full narrative spec + I/O matrix once story development context is available. The foundation for all other Mason stories (1-2..1-10) depends on this structure being finalized.
