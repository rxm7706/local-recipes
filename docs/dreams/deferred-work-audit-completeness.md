---
status: specified
owner: doctor
date: 2026-08-15
specified-by: _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-deferred-work-visibility/SPEC.md (CAP-4..7, extending the pre-existing deferred-work-visibility Spec rather than a new one, per operator direction to keep one big process instead of several small ones)
---

# Deferred-work audit completeness

## The dream

`pixi run -e local-recipes deferred-work-check` should be able to answer
"does every station's Tier-3 deferred-work record have a durable, tracked
twin?" with full confidence — not just "every entry that already carries a
`## DW-<id>` heading and isn't yet in the tracked ledger." Two real blind
spots survived a full manual fleet audit on 2026-08-15 and would recur on
the next station that ships an old-format or headerless Tier-3 file.

## Why now

A user challenge ("just because a station is complete doesn't mean it has
no deferred work") drove a by-hand, content-level audit of all 8 stations'
`implementation-artifacts/deferred-work.md` against their tracked
`planning-artifacts/deferred-work-ledger.md` twins — not trusting the
`tier3-only-deferral` finding's id-diff alone. It found:

1. **Pre-convention formats are invisible to id-based detection.**
   pyforge-warden's Tier-3 file predates the `## DW-<id>` heading
   convention entirely (`## Deferred from: code review of <spec> (<date>)`
   section headers, no id anywhere) — turned out to be already fully
   promoted and even code-verified (PRs #145-147), so no harm done, but
   the *reason* it read "0 findings" had nothing to do with the detector
   actually checking it. pyforge-atlas's Tier-3 file carries a **second**,
   different pre-convention format: a `bmad-dev-auto step-04 defer
   category` block of flat `- source_spec: / summary: / evidence:`
   bullets with an explicit comment ("one entry per finding") and no id
   or header at all. This one was NOT already promoted — 58 real findings
   (dating back to Story A1, 2026-07) sat undetected in gitignored
   Tier-3 storage, at the exact kind of risk CLAUDE.md's Tier-3 warning
   describes (pyforge-warden's own tracked-ledger preamble: "this repo has
   already lost data that way").

2. **A `#`-prefixed header swallows its own body in a paragraph-level
   content-diff**, producing false "already covered" reads. Bare
   `### DW-<n>: Follow-up review still recommended for <story>...`
   review-budget-followup entries in atlas, marshal, mason, and steward
   were missed by both the id-based detector (their content WAS promoted
   under a different id after a prior session's manual rename, which any
   raw id-string diff can't see) and by an ad-hoc content check built
   during this audit (which skips any paragraph starting with `#`,
   silently including the header+body together and then discarding it as
   "not a bullet to check"). 5 entries recovered by hand once the false
   read was caught.

3. **Doctor already has half the answer.** `_check_project_deferred_work`
   (`pyforge.doctor.sources.chain`) has a Story 7.3 grandfather-baseline
   mechanism (`scripts/.deferred-work-baseline.json`) that already
   detects headerless/anonymous Tier-3 entries beyond a stamped count —
   this is `tier3-entry-unidentified`, and it correctly flagged 72 more
   entries across marshal (30), steward (38), mason (2), and herald (2)
   that this session did NOT attempt to promote (see below). The
   detection half of this capability already exists; only the
   **promotion** half (mint a real id, append to the tracked ledger,
   verify no collision/duplicate) is missing, and doing it by hand
   tonight proved error-prone.

## What went wrong trying to do this by hand (evidence for why this needs
real code, not another one-off script)

Two distinct bugs shipped and were caught only by re-running the detector
after each pass:

- **Content duplication**: a flat-bullet scanner that doesn't check
  whether a `- source_spec:` bullet is already owned by a `##`/`###`
  header directly above it will re-promote already-headed entries under a
  fresh id. Caught by a summary-text uniqueness scan across the whole
  ledger (6 duplicates found in atlas, removed).
- **Structural mismatch across stations**: the same "look at the nearest
  non-blank line above; if it's a header, this bullet is owned" heuristic
  that correctly parsed atlas's flat-append format (one header, one
  bullet, always adjacent) overcounted by roughly 10x on marshal/steward
  (231 and 91 spurious mints against a true count of 30 and 38) because
  those stations' `### DW-FU-<story>` entries can have **multiple**
  `- source_spec:` bullets stacked under one header — a shape the
  heuristic can't distinguish from an orphan. All spurious entries were
  identified via the "pass 3" marker text and mechanically stripped
  before commit; no bad content shipped, but it took two clean-up passes
  including one that (transiently, before being caught by a count check)
  deleted legitimate already-committed content via an over-broad
  string-split filter.

Both incidents were caught before landing because every promotion pass
was followed by a full re-run of `deferred-work-check` plus a
duplicate-id/duplicate-content scan — that verification loop is exactly
what a real implementation should encode as a test fixture, not
re-improvise by hand each time.

## Proposed capability (for `bmad-spec` to size properly — this is a
sketch, not a committed design)

Extend `pyforge.doctor.sources.chain`'s deferred-work check (or a sibling
module) with:

1. **A real entry-boundary parser** that understands all three Tier-3
   shapes seen in production: `## DW-<id>` / `### DW-<id>` headed entries
   (single or multi-bullet body), bare `### DW-<n>: Follow-up review...`
   review-budget-followup entries, and headerless flat
   `- source_spec: / summary: / evidence:` bullets under a top-of-file
   marker comment. Each shape needs its own tested boundary rule — the
   header-ownership question (is this bullet part of the entry above it,
   or an orphan?) is exactly the thing two ad-hoc heuristics got wrong
   tonight.
2. **A promotion mode** (`--fix`, mirroring `spec_surface_check.py
   --write-baseline`'s existing pattern) that mints a collision-free
   `DW-<epic>-<story>-<n>` id per orphan entry (querying the tracked
   ledger's existing max suffix per story, not a fixed starting number),
   appends it with a `status: open` line and a `promoted:` provenance
   note, and refuses to run if it would produce a duplicate id or
   duplicate summary text against the existing ledger.
3. **Extend the Story 7.3 grandfather baseline's role**: today it only
   suppresses re-flagging already-accepted anonymous entries. It should
   also be the input to `--fix` (promote everything *not* covered by the
   baseline, then re-stamp the baseline to the new total).

## Relationship to the sibling Dream

This Dream is "get every real finding into durable, tracked storage,
correctly and without duplication." It says nothing about whether a
tracked entry is still *true* once it's there — that's a distinct,
harder, code-comprehension problem with its own precedent (a fleet-wide
by-hand verification campaign, PR #147, 2026-07-30) and its own proposed
capability: see `docs/dreams/deferred-work-resolution-sweep.md`. The two
share one root-cause bug worth fixing together (a heading-less entry
breaks both this Dream's promotion detection AND that campaign's
`normalize_deferred_ledgers.py` status tracking — the same blind spot,
independently rediscovered six weeks apart) but are different enough in
kind to size as separate stories.

## Known remaining scope (not yet promoted, tracked by the detector today)

`pixi run -e local-recipes deferred-work-check`'s `tier3-entry-unidentified`
finding, as of 2026-08-15, still names real content beyond the grandfather
baseline: **marshal 30, steward 38, mason 2, herald 2** (72 total). These
are not at the same acute loss risk as atlas's flat-append format was
(they're already visible to the detector, just not yet promoted) — but
they are real deferred findings sitting in gitignored Tier-3 storage.
Whoever implements this capability should promote them as its first real
run.
