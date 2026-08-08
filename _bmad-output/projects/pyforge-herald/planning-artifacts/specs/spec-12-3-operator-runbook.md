---
title: 'Operator Runbook'
type: 'feature'
created: '2026-08-08'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** The Epic 12 AC calls for a "getting started" overview (what
Herald is, the four Moments), per-Moment how-to guides with "realistic
command output" and "web screenshots," and an FAQ. No single doc in this
package currently orients a first-time operator across both the CLI and
the web dashboard together -- `cli-runbooks.md` (Story 12.1) and
`web-ux-guide.md` (Story 12.2) each cover one surface in task-oriented
depth, neither is an entry point.

**Approach:** write `docs/operator-guide.md` as that entry point: a
one-paragraph "what is Herald" (the deck-bridge CLI plus the Four Moments
surface, explicitly including the "no live backend" architecture fact up
front), then one real, captured how-to per Moment (Progress/Success/
Operations) with a pointer to the matching web tab and to the deeper
runbook file for full detail, closing with an FAQ built from the
confusions the scaled-down architecture actually produces (not the
epics doc's webhook-era FAQ candidates).

**Judgment call: text description of "where to find each web tab" instead
of screenshots.** The original AC says "web screenshots"; this repo's
documentation convention (every other `.md` under `docs/` and
`_bmad-output/`) is prose + captured CLI output, not binary image assets
committed to a spec-tracked doc directory, and no screenshot tooling was
in scope for a documentation-only story. Each Moment's how-to instead
names its web tab and links to `web-ux-guide.md`'s fuller per-tab section
(which itself describes every visual element in prose: card layout,
badges, empty/error states) -- a strictly more maintainable substitute
that doesn't go stale the next time a panel's styling changes.

## Boundaries & Constraints

**Always:**
- Command output quoted here is the same real, captured output used in
  `cli-runbooks.md` (Story 12.1) -- not a second, independently-run
  capture that could drift from it. Both files were authored from the
  same scratch-directory session, 2026-08-08.
- The FAQ's first entry addresses the single most likely confusion this
  architecture produces ("why doesn't a PR merge auto-create a progress
  record") with the direct CLI-command answer, per the story's own worked
  example in the parent task.
- Every FAQ answer that names a limitation links to the Dream file
  (`docs/dreams/herald-moments-2-4-live-backend.md`) rather than
  re-explaining the scope decision inline.

**Block If:** N/A -- no spike gate; pure documentation.

**Never:**
- No screenshot binaries added to `docs/` -- see the Judgment call above.
- No FAQ entry invented from the epics doc's original webhook-era framing
  without being re-grounded in what the current architecture actually
  does (each entry cross-checked against `cli.py`/`web/src/` source during
  authoring).

## I/O & Edge-Case Matrix

N/A -- documentation-only story. FAQ coverage table (each row grounded in
this story's own research, not assumed):

| FAQ question | Grounded in |
|---|---|
| Why no auto-create on PR merge? | Absence of any webhook/trigger in `cli.py`; Dream file's own framing |
| Web dashboard shows stale data after a CLI write? | `web-ux-guide.md`'s snapshot-regeneration section (Story 12.2) |
| `herald auth login` doesn't exist? | `auth.py` source (no such subcommand); `cli-runbooks.md`'s known-gap note (Story 12.1) |
| Did a failed publish partially write? | `cli.py::_run_success_publish` -- gate/confirm/evidence-check all run inside `dispatch`'s `operation` closure before `claims.publish` persists anything |
| How to check evidence staleness later? | `herald success validate` (Story 12.4's scope) |
| Where's the REST API/database? | Confirmed absent by reading every `.py` file in `src/pyforge/herald/` during this epic's research; `.herald/*.json` are the only persistence |
| Known station list? | `progress.py`'s `STATIONS` tuple |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/docs/operator-guide.md` -- create --
  the getting-started guide + FAQ.
- `src/shared/packages/pyforge-herald/docs/README.md` -- shared across
  Stories 12.1-12.4 (index entry; file created once by Story 12.1).

No `src/pyforge/herald/` or `web/src/` (production code) changes.

## Design Notes

Deliberately does not restate `cli-runbooks.md`'s full command reference
or `web-ux-guide.md`'s full per-tab tour -- each Moment's how-to here is
the minimum realistic example plus a link out, keeping this file scannable
as a true "start here" rather than a third copy of the same content.

## Verification

**Commands:**
- No automated test suite applies to markdown-only changes.
- Every command example cross-checked against the same captured
  scratch-directory session used for `cli-runbooks.md` (Story 12.1) --
  verified for exact-match wording, not re-run independently, to avoid a
  second capture silently drifting from the first.

## Spec Change Log

## Review Triage Log
