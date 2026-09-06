---
title: Deferred-work resolution sweep
status: dreamt
owner: doctor
date: 2026-08-15
---

# Deferred-work resolution sweep

## The dream

Getting a Tier-3 finding into the tracked ledger (see the sibling Dream,
`deferred-work-audit-completeness.md`) only proves it survives a worktree
teardown. It says nothing about whether the finding is still *true*. A
tracked `status: open` line is a claim about the code at authoring time —
nobody re-checks it once it lands. That re-check — read the entry, find
the code it names, confirm the defect is still there (or isn't) — is a
distinct capability from promotion, and it has already been proven
valuable exactly once, by hand, and never made repeatable.

## The precedent (2026-07-30, PR #147, `deferred-work-verify-campaign`)

Every tracked entry across the fleet-as-it-existed-then (atlas 57, warden
43, herald 24, marshal 17, doctor 4 — **145 total**, mason/steward/scribe
didn't exist yet) was individually re-verified against live code, entirely
by hand (`bmad-loop-sweep` is automation-only and scoped to the wrong
tier — Tier-3, not the tracked ledger — so it could not be used). What it
found is the whole argument for doing this again:

- **12 entries were already resolved and nobody closed them.** The
  sharpest case: one root defect (`bmad-ui` losing its local
  `./build_artifacts` channel) had been independently hit and fixed
  THREE times across three different stories in three different
  projects, and two of the three ledger entries still read `open`.
- **2 entries got *worse* since authoring** (a duplication bug that
  roughly doubled, a per-entry cost that grew) — a stale `status: open`
  cannot show drift in either direction; only re-reading the code can.
- **5 entries understated their own scope** once the pattern was traced
  to sibling packages that cloned the same defect.
- **1 finding could only be verified by reading a DIFFERENT project's
  code** (`atlas DW-I5-1`'s part (b) turned out to be resolved in
  marshal's `core/policy.py`) — a single-project sweep cannot catch this
  class at all.

That is real, cross-cutting signal a stale ledger entry actively hides.
Full account in auto-memory `project_deferred_work_verification_campaign`.

## Why this needs to become systematic (not just "run it again")

1. **It's badly stale.** The campaign is six weeks old and covered 5 of
   what are now 8 stations. mason (48 tracked entries as of tonight),
   steward (74), and scribe (7) have **never** been verified once. Every
   entry the two promotion passes tonight added (67 in atlas, 5 more
   across marshal/mason/steward) is also unverified from day one — they
   were moved from Tier-3 to tracked storage verbatim, not re-checked
   against current code.
2. **The campaign named its own tooling gaps, and none of them are
   fixed**, meaning a re-run today hits the identical failure modes:
   - `normalize_deferred_ledgers.py` cannot see a heading-less entry
     (undercounted marshal's real deferral count by 2 at the time). This
     is the **exact same blind spot** `deferred-work-audit-completeness.md`
     documents from tonight's atlas/marshal/mason/steward audit — the
     same bug class independently rediscovered six weeks apart because
     nothing fixed the root cause the first time it was named.
   - `warden DW-1-4-1` — marked `done` off the wrong half of two
     deferrals sharing one id — still needs splitting into two ids;
     never done.
   - atlas's own frontmatter declared an `entries: 55` count against 57
     real entries, in a file whose whole job is to declare that count
     correctly.
3. **The protocol that worked is real evidence for what a tool needs to
   preserve**, not just automate: batch 8-14 entries, gather evidence
   with a few wide greps covering many entries per pass, apply results
   via `{id: (status, note)}` (not per-entry `Edit`, since every
   `status:` line is textually identical and unaddressable), commit per
   project, and — the part that resists full automation — **prove each
   verdict by reading or executing the actual code**, not by pattern-
   matching the entry's own prose back at itself. Three entries in the
   2026-07-30 campaign were only correctly resolved by actually running
   the code (AST-evasion, dict-key collapse, schema gap reproduction).

## Beyond the precedent: what a real capability needs that the one-off
## campaign didn't have to solve

The 2026-07-30 campaign was a single, bounded, human-paced push. A
*repeatable* capability inherits every cost problem that a one-time
effort can ignore, plus a few the campaign never had to face because the
fleet was smaller and it only ran once. Thinking past just replaying
warden's protocol:

- **Cost has to be bounded structurally, not by discipline.** ~400+
  tracked entries exist today (atlas 122, marshal 109, steward 74, mason
  48, warden 43, herald 45, doctor 20, scribe 7) and the number only
  grows. A full LLM-driven re-read of every entry on every run doesn't
  scale — this fleet already has two precedents for bounding exactly this
  kind of recurring cost that a resolution sweep should study rather than
  reinvent: bmad-loop's own `limits.max_followup_reviews` damping cap
  (a hard ceiling on repeated review passes per story), and — pointedly
  — **pyforge-warden's own product domain**, which is a compliance gate
  built entirely around baseline/grandfathering/waiver semantics for
  "known finding, don't re-flag every run until something changes."
  Verifying warden's OWN deferred-work ledger with warden's OWN
  baseline-and-waiver *model* (not the tool itself — the design pattern)
  would be a fitting, self-referential fit.
- **Prioritize by what actually could have changed.** Most tracked
  entries name a specific file. If that file has zero commits since the
  entry's last `verified:` (or since authoring, if never verified), the
  entry is a low-value re-read — nothing could have resolved or worsened
  it. `git log --since=<verified-date> -- <path>` per entry is a cheap
  filter that could shrink a "verify everything" sweep down to "verify
  only entries whose named code actually churned," which is where the
  precedent's real findings concentrated anyway (the incidentally-fixed
  and got-worse cases were all in files that had, in fact, changed).
- **Tier the verification itself, not just its scheduling.** Not every
  entry needs an agent to read and reason about code. Some claims are
  mechanically checkable: "raises a bare `KeyError`", "no `try/except`
  around X", "function Y is unused", a named test that does or doesn't
  exist, a count ("N call sites") that a grep can recompute exactly. A
  sweep should attempt a cheap structural/grep-level check FIRST and only
  escalate to an agent read when the claim genuinely requires judgment
  (does this behavior matter, is the scope still accurate, is this really
  resolved). This mirrors `spec_surface_check.py`'s own two-tier design
  (hash-drift is mechanical; `drift-presumed` needs a human to confirm
  the memlog covers it) — worth reusing that shape rather than a new one.
- **Cross-entry and cross-project correlation, not just per-entry
  verification.** The precedent's sharpest finding — one root cause hit
  three times across three projects — was found by a human noticing a
  pattern while reading, not by any structural check. A systematic sweep
  should actively look for near-duplicate entries (same file/symbol
  named across different projects' ledgers, or similar summary text) and
  surface them as a *defect class*, not three independent low-priority
  entries nobody connects. This is the same shape of value BMAD's own
  cross-spec-sync convention already recognizes for specs
  (`feedback_specs_cross_sync` in auto-memory) — deferred-work entries
  deserve the same treatment.
- **Close the loop into future planning, not just the ledger.** Today an
  entry says `owner: Story 4.5` in prose and nothing enforces that Story
  4.5's actual scope addresses it — closing an entry depends entirely on
  someone remembering to grep the ledger when writing that story's spec.
  A resolution sweep's natural complement is a **backlog-intake check**:
  when a new story/spec is drafted for an epic, surface any tracked
  deferred-work entries whose `owner:`/prose names that epic or story, so
  they become candidate acceptance criteria instead of staying inert
  prose forever (or worse, silently missed the way FR-28's attribution
  scope was almost over-built earlier this session before the CRITICAL
  escalation caught it).
- **Handle the "this code doesn't exist anymore" case explicitly,
  distinct from "verified still open."** A file or whole package can be
  deleted, superseded, or a project can move to `shipped`/archived status
  between one sweep and the next (pyforge-atlas's own legacy Kedro
  migration retired entire modules this way). The precedent's protocol
  only had two outcomes it exercised (confirm-still-open,
  confirm-resolved) — a real sweep needs a third: **moot/superseded**,
  closed with the same evidentiary bar (cite what replaced or removed
  the code), not silently dropped and not left open forever pointing at
  nothing.
- **Surface staleness as an ongoing signal, not just a campaign trigger.**
  `fleet_picture.py`'s ATTENTION block already aggregates cross-cutting
  fleet health (it grew a baseline-drift check this very session). A
  "% of tracked entries verified within N days, per project" line there
  would make the NEXT six-week staleness gap visible incrementally
  instead of requiring another pointed user challenge to notice it went
  quiet again.
- **Escalation, not forced resolution.** Some entries will be genuinely
  undecidable by reading code alone (a design-tradeoff entry, a
  "revisit when Story X lands" entry where Story X hasn't landed yet).
  The sweep needs a legitimate third verdict beyond
  open/resolved — **still-pending-on-a-named-precondition** — so it
  doesn't force a false confirm just to close the loop, the same failure
  mode `feedback_verify_before_destructive_or_debt_claims` warns against
  in a different context.

## Proposed capability (sketch — size properly via `bmad-spec`)

A repeatable resolution sweep, likely agent-driven rather than purely
mechanical (verifying "is this defect still in the code" is not a
parseable fact the way "does this id exist in file X" is):

1. **A due-for-verification selector**: every tracked entry gains (or
   already has, per the 2026-07-30 convention) a `verified: <date> —
   <verdict>` line. A sweep should be able to select entries with no
   `verified:` line at all (everything promoted since the last real
   campaign — currently ~150+ entries across mason/steward/scribe plus
   tonight's fresh promotions) or with a `verified:` date older than
   some staleness threshold, batched per project the way the precedent
   did it by hand.
2. **Fix the machinery gaps the precedent already named** before or
   alongside building this: `normalize_deferred_ledgers.py`'s
   heading-less blind spot (shared root cause with the promotion-side
   Dream — worth fixing once, used by both), the still-unsplit
   `warden DW-1-4-1`, and a self-consistency check so a project's
   declared entry count can't silently drift from the real count again.
3. **Batch dispatch to a verification agent** per the proven protocol:
   read the entry, locate the named code, confirm/refute by reading or
   executing it, write a `verified:` line with the same evidentiary bar
   the precedent set (a `file:line` or a measured/reproduced count, not
   a restatement of the entry's own claim) — and, critically, **do not
   silently narrow scope**: if an entry claims 2 packages and the sweep
   finds it now affects 8, that's the finding, not a reason to leave the
   `2` uncorrected.
4. **Cross-project reach**: the precedent's `atlas DW-I5-1` case shows a
   per-project sweep structurally cannot catch a fix that landed in a
   sibling project's code. Whatever selects work for a batch should be
   able to look at any project's source tree, not just the owning
   project's.

## Realization log

- **2026-08-15** — Spec'd as `spec-deferred-work-resolution-sweep` (pyforge-doctor), CAP-1..8, decomposed into Epic 11 (Stories 11.1-11.8). CAP-8's own scope-boundary question (this Dream's "backlog-intake check" bullet above) left open at spec time.
- **2026-08-21** — **CAP-8 split into its own companion Spec, `spec-backlog-intake-check`** (operator decision, tracked `DW-11-8-1` in pyforge-doctor's deferred-work-ledger.md pending it). Epic 11 shipped cleanly as Stories 11.1-11.7, a self-contained read-only sweep pipeline; bundling CAP-8's write-adjacent, story-drafting-time capability into it after the fact would have muddied that result. This Dream remains the owner-dream for both Specs — the "resolution sweep" (periodic re-verification, CAP-1..7) and the "backlog-intake check" (drafting-time surfacing, `spec-backlog-intake-check`'s CAP-1) are two capabilities this one Dream always named, now two Specs.

## Relationship to the sibling Dream

`deferred-work-audit-completeness.md` is "get every real finding into
durable, tracked storage, with a correct id, without duplicating or
colliding." This Dream is "once it's there, periodically confirm it's
still true." They share one root-cause bug (heading-less entries breaking
both `deferred-work-check`'s promotion detection and
`normalize_deferred_ledgers.py`'s status tracking) worth fixing together,
but the promotion problem is a parsing problem and the resolution problem
is a code-comprehension problem — different enough in kind that they
should very likely be scoped as two stories, not one, when this reaches
`bmad-spec`.
