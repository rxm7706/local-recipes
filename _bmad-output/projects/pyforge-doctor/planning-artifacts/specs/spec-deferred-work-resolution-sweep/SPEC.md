---
id: SPEC-deferred-work-resolution-sweep
status: in-progress   # added 2026-09-09 (doctor-B7): the key was absent entirely, which
                      # silently exempted this Spec from chain-completeness INV-A. Epic 11
                      # is 7/7 done, but CAP-2/CAP-3/CAP-6 measure inert against the live
                      # ledgers (see the 2026-09-08 companion) — `shipped` would encode a
                      # measured non-capability as delivered.
owner-dream: docs/dreams/deferred-work-resolution-sweep.md
companions:
  - precedent-2026-07-30-campaign.md
  - implementation-precedents.md
  - sweep-tooling-effectiveness-2026-09-08.md   # measured: CAP-2/CAP-3/CAP-6 are inert against these ledgers
sources:
  - docs/dreams/deferred-work-resolution-sweep.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. The source document listed in frontmatter is for traceability only.

# Deferred-work resolution sweep

## Why

A tracked deferred-work ledger entry is a claim about code truth *at authoring time* — nobody re-checks it once it lands. This has already been proven valuable to fix, exactly once, by hand, and never made repeatable: PR #147 (2026-07-30) individually re-verified 145 entries across 5 stations and found 12 already-resolved-but-still-marked-open, 2 that got *worse* since authoring, 5 that understated their own scope, and 1 only verifiable by reading a different project's code (full breakdown in `precedent-2026-07-30-campaign.md`). That gap has since grown, not shrunk: three stations (mason, steward, scribe) have never been verified once, and every entry promoted since — including entries promoted this same session — is unverified from day one. This is a pain to solve: a stale `status: open` line actively hides real, cross-cutting signal.

## Capabilities

- **CAP-1 — due-for-verification selection.**
  - **intent:** A sweep can select tracked entries needing verification — no `verified:` line at all, or a `verified:` date older than a staleness threshold — batched per project, without a human enumerating them by hand.
  - **success:** Given the fleet's current ~400+ tracked entries, running the selector returns exactly the entries with no `verified:` line or a stale one — demonstrated against the current ~150+ never-verified entries (mason/steward/scribe plus all promotions since the 2026-07-30 campaign).

- **CAP-2 — churn-based cost filtering.**
  - **intent:** Entries whose named file/path has had zero commits since their last verified date (or since authoring, if never verified) are deprioritized, since nothing could have changed.
  - **success:** Given an entry whose named path has zero commits since its last-verified date, the sweep does not select it for agent verification (or flags it `skip-reason: no-churn`); given commits since, it is selected.

- **CAP-3 — tiered verification, mechanical first.**
  - **intent:** A sweep attempts a cheap structural/grep-level check first for mechanically-checkable claims, escalating to an agent read only when the claim genuinely requires judgment.
  - **success:** Given an entry whose claim is grep-recomputable (e.g. "N call sites of X"), the mechanical check alone produces a verdict with no agent invocation; given a judgment-requiring claim, it escalates.

- **CAP-4 — evidence-grounded verdict recording, four verdicts.**
  - **intent:** For entries needing judgment, a verification agent reads the entry, locates the named code, and writes a `verified: <date> — <verdict>` line backed by cited evidence (a `file:line` or a reproduced/measured fact), never a restatement of the entry's own prose. The verdict is one of four: still-open, resolved, moot/superseded (cited), or pending-on-precondition — never a forced false confirm just to close the loop.
  - **success:** Every `verified:` line cites a `file:line` or a reproduced/measured fact; a scope correction (entry claims 2 packages, sweep finds 8) is written as the corrected number; an entry whose code no longer exists closes as moot/superseded citing what replaced or removed it.

- **CAP-5 — cross-project reach.**
  - **intent:** Whatever selects and verifies work for a batch can read any project's source tree, not just the owning project's.
  - **success:** Given an entry in project A whose defect was actually fixed by a commit in project B (the precedent's real `atlas DW-I5-1` case, resolved in marshal's `core/policy.py`), the sweep's verification step reads project B's tree and correctly closes the entry.

- **CAP-6 — cross-entry, cross-project correlation.**
  - **intent:** The sweep actively looks for near-duplicate entries (same file/symbol across different projects' ledgers, or near-identical summary text) and surfaces them as one defect-class group, not independent low-priority entries.
  - **success:** Given two or more tracked entries across different projects naming the same file/symbol or near-identical summary text, the sweep's report groups them as a single defect class.

- **CAP-7 — fleet-wide staleness signal.**
  - **intent:** `fleet_picture.py`'s ATTENTION block surfaces "% of tracked entries verified within N days, per project" as an ongoing signal.
  - **success:** After the sweep has run at least once, fleet-picture's ATTENTION block includes a per-project staleness percentage line, sourced from each project's tracked ledger's `verified:` dates.

- **CAP-8 — backlog-intake check. SPLIT OUT 2026-08-21 — no longer part of this Spec.**
  - Was: when a new story/spec is drafted for an epic, tracked deferred-work entries whose `owner:`/prose names that same epic or story are surfaced as candidate acceptance criteria.
  - Its scope-boundary Open Question (below) resolved to "own follow-on Spec," decided once this Spec's CAP-1..7 shipped cleanly as Epic 11 (pyforge-doctor), Stories 11.1–11.7 — a self-contained read-only sweep pipeline that a write-adjacent capability like CAP-8 would have muddied. No follow-on Spec/Dream exists yet; tracked in pyforge-doctor's `deferred-work-ledger.md` (`DW-11-8-1`) rather than silently dropped. This Spec now covers CAP-1..7 only.

- **CAP-9 — the intake guard.**
  - **intent:** Deferred-work intake refuses — or explicitly flags — an entry that cites no resolvable `location:`, so the ledger stops accumulating claims no sweep can ever check.
  - **success:** An entry with no extractable repo path is rejected at defer time (or emitted carrying an explicit unverifiable marker), and the fleet's never-verified population stops growing.

## Constraints

- **Reuse, don't re-solve, the heading-less-entry parser fix.** `deferred-work-audit-completeness`'s Spec (CAP-4..7, folded into `spec-deferred-work-visibility`) already addresses the same root-cause bug (`normalize_deferred_ledgers.py`'s blind spot) from the promotion side — fix once, consumed by both.
- **Verification must be code-grounded.** A cited `file:line` or a reproduced/measured fact, never a restatement of the entry's own claim. Three entries in the 2026-07-30 precedent were only correctly resolved by actually running the code — reading alone was insufficient.
- **Never silently narrow a scope claim on correction.** If an entry claims impact to 2 packages and verification finds 8, the corrected number is the finding to record, not a reason to leave the stale `2` uncorrected.

## Non-goals

- Not a fully mechanical/parseable capability — "is this defect still in the code" is not a fact the way "does this id exist in file X" is; this Spec is agent-driven for judgment-requiring claims by design.
- Not deciding which Tier-3 findings get promoted into tracked storage in the first place — that is `deferred-work-audit-completeness`'s territory.
- Not a full ledger data-quality audit of pre-existing issues — warden `DW-1-4-1`'s still-unsplit id and atlas's own `entries:` count self-consistency gap are pre-existing cleanup items this Spec does not itself fix, though CAP-4's own evidentiary discipline would catch new instances of both classes going forward.

## Success signal

Running the sweep against the fleet's current ~400+ tracked entries reduces the never-verified count and reports Findings for entries whose named code changed since last check — without requiring a human to re-run the 2026-07-30 campaign by hand again.

## Assumptions

- CAP-2/CAP-3/CAP-6 stay as written: the mechanism is built and correct, but its premise — that entries are written as checkable claims — does not hold for this corpus (measured 2026-09-08: CAP-3 matched 0 of 1,410 entries, CAP-2 skipped 0 of 183 due entries, CAP-6 found 1 near-duplicate pair against 4 defect classes found by hand). Rewriting their success criteria to describe the corpus would close the chain and retire the lead; CAP-9 attacks the cause instead.
- Assumed this Spec stays independent from `deferred-work-audit-completeness` (already folded into `spec-deferred-work-visibility`) rather than being folded in too — the source Dream's own "Relationship to the sibling Dream" section states the two problems (parsing vs. code-comprehension) differ enough in kind to warrant separate stories.

## Open Questions

- ~~**CAP-8's scope boundary.**~~ **Resolved 2026-08-21: own follow-on Spec**, not the same wave as CAP-1..7 — see CAP-8's entry above.
- **CAP-1's staleness threshold.** How many days before a `verified:` date counts as stale enough to re-select is undecided — the source Dream does not name a number.
