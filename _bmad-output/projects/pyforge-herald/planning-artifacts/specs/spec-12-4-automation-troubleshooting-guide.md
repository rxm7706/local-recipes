---
title: 'Automation Troubleshooting Guide (honestly scoped)'
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

**Problem:** The Epic 12 AC for this story is four diagnosis-and-fix
sections that all assume live automation this codebase never built:
"webhook not firing," "cron job missed," "auto-extract failed," "stale
link warning." Three of the four have no corresponding real system to
diagnose at all -- writing them would document troubleshooting steps for
infrastructure that cannot exist, actively misleading an operator who
hits an unrelated real problem and searches this doc for it.

**Approach:** reframe the story's actual content, once, at the top of
`docs/automation-troubleshooting.md`, as "what to do when the
CLI-triggered equivalents of that automation don't behave as expected,"
then cover the three failure modes that are real, reproducible, and were
each triggered live in a scratch directory during authoring: (1) stale/
broken evidence links via `herald success validate` (the operator-run
replacement for the spec's weekly re-validation cron -- distinct from
`success publish`'s own publish-time hard-abort, which Story 12.1 already
covers), (2) a malformed `.herald/*.json` local storage file surfacing as
a `HeraldError`, and (3) a stale web snapshot (no error at all -- the
dashboard just shows old data until the matching exporter is re-run,
covered in depth by `web-ux-guide.md`/Story 12.2 and cross-referenced
here rather than duplicated).

**Judgment call: three sections, not the AC's four.** "Webhook not
firing" and "cron job missed" collapse into nothing documentable (there is
no webhook or cron to diagnose); "auto-extract failed" maps onto the
publish-time evidence-link abort already fully covered in
`cli-runbooks.md` (Story 12.1), so repeating it here would duplicate
content Simplicity First argues against -- this file instead covers only
the `validate`-command's soft-flag case, which is genuinely distinct
(already-published claim, no abort, in-place flag update) and not
addressed elsewhere. "Stale link warning" becomes the evidence-validation
section; "stale web snapshot" is a fourth real failure mode the AC's
literal four-item list didn't anticipate (because it assumed a live API
with nothing to go stale) but the scaled-down architecture makes into the
single most common real support question -- included because it is real
and un-covered elsewhere at this depth (`web-ux-guide.md` explains the
mechanism; this file gives it a dedicated diagnosis/fix treatment).

## Boundaries & Constraints

**Always:**
- The "no webhook/cron/database exists" caveat appears exactly once, in
  the intro, per the parent task's explicit instruction not to repeat it
  per subsection.
- Every diagnosis command and its output in this file was actually run
  (`pixi run --frozen -e pyforge-herald herald success validate ...`,
  hand-corrupting a `.herald/claims.json` copy, etc.) during authoring,
  2026-08-08 -- not inferred from source reading alone.
- Cross-references rather than duplicates: the publish-time evidence-link
  abort (`cli-runbooks.md`), and the web-snapshot regeneration commands
  (`web-ux-guide.md`) are linked, not re-explained in full.

**Block If:** N/A -- no spike gate; pure documentation.

**Never:**
- No "webhook not firing" or "cron job missed" section -- there is nothing
  true to write for either; including a section with only "this cannot
  happen, see the Dream" for both AC items was considered and rejected as
  padding that doesn't help an operator (the single top-of-file caveat
  already covers it).

## I/O & Edge-Case Matrix

N/A -- documentation-only story. Failure modes documented, each verified
by live reproduction on 2026-08-08:

| Failure mode | Reproduction | Real result |
|---|---|---|
| `success validate` on a claim with a dead link | `herald success validate <id>` | `revalidated claim <id>: 0/1 evidence link(s) valid` (no error; in-place flag update) |
| `success validate` with both/neither of `<claim-id>`/`--all` | `herald success validate --all <id>` | `HeraldError: herald success validate: supply exactly one of <claim-id> or --all` (exit 1) |
| Corrupt `claims.json` | hand-edit to invalid JSON, then `herald success list` | `HeraldError: claims file ... could not be read: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)` (exit 1) |
| Stale `success.json`/`notices.json`/`progress.json` | CLI write succeeds, web tab still shows old state | No error anywhere -- silent; fix is re-running the matching exporter |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/docs/automation-troubleshooting.md`
  -- create -- the reframed troubleshooting guide.
- `src/shared/packages/pyforge-herald/docs/README.md` -- shared across
  Stories 12.1-12.4 (index entry; file created once by Story 12.1).

No `src/pyforge/herald/` or `web/src/` (production code) changes.

## Design Notes

This story's file is the one most directly shaped by the "reframe rather
than fabricate" instruction in the parent task -- its structure (three
real sections, each with its own "what it replaces" framing sentence)
exists specifically so a reader coming from the original epics doc's AC
language ("webhook not firing," etc.) can map each of those phrases onto
either "doesn't exist, see the Dream" (stated once, up top) or the actual
CLI-triggered equivalent that does exist and can genuinely misbehave.

## Verification

**Commands:**
- Every command in the "Stale or broken evidence links" and "Malformed
  local storage file" sections was run against the built `herald` binary
  (`pixi run --frozen -e pyforge-herald herald ...`) in a scratch
  directory, output captured verbatim.
- No automated test suite applies to markdown-only changes.

## Spec Change Log

## Review Triage Log

### 2026-08-08 -- Adversarial review pass (Blind Hunter + Edge Case Hunter, no shared context)

- `[medium]` `[patch]` **"Auto-extract failed" (one of the original epic's four named failure modes) was never actually addressed anywhere in the guide's body** -- the intro's "None of the first three can happen" line implicitly lumped it in with the genuinely-nonexistent webhook/cron infrastructure, but Epic 9's `herald success create` IS auto-extract's real, CLI-triggered replacement and does have real, reproducible failure modes. A reader searching this guide for "auto-extract" found only the intro paragraph and no actual section. Fixed: reworded the intro to name `herald success create` explicitly as auto-extract's replacement, and added a new "'Auto-extract failed'" section covering its real failure mode (empty/whitespace project name) and clarifying its fixed evidence-flag shape (no free-form type to mistype).
- `[low]` `[patch]` **The claim id `9c3590d4-...` was reused from `cli-runbooks.md`/`operator-guide.md`'s clean-evidence walkthrough, but shown here with a deliberately-broken evidence link** -- since the docs' whole credibility pitch is "captured real output, not fabricated," a reader cross-referencing the same id across files and seeing it behave inconsistently (valid link vs. broken link) was more likely to read it as a documentation error than the actual explanation (separate, unrelated scratch sessions). Fixed: swapped to a distinct id (`a17e2b60-...`) with an explicit note that example ids don't match across these independently-captured docs.
- `addressed_findings`: 2 (1 medium, 1 low). No `intent_gap`, no `bad_spec`, no `defer`, no `reject`.

**Follow-up review recommendation:** none outstanding for this story.
