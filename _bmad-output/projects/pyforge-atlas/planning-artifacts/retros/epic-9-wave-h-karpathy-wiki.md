---
doc_type: retrospective
project: pyforge-atlas
epic: 9
wave: H
title: Wave H — The AI Software Factory & Karpathy Wiki
stories: 4
date: 2026-08-02
basis: reconstructed from tracked evidence (epics.md, sprint-status.yaml,
  deferred-work-ledger.md DW-H1..DW-H4, PRs #99/#100/#101/#102, CFE Rule-2 retro PR #103)
---

# Epic 9 · Wave H — The AI Software Factory & Karpathy Wiki

**Scope:** H1 wiki layout contract + 5 factory personas + storage resolver, FR-22(a)
(`fe52bbdb1e`, #99) · H2 agno `CompileCrew`/`LintCrew`/`QACrew`, FR-22(b) (`2f4240f064`,
#100) · H3 La Suite/Wagtail REST sync, FR-22(c) (`4e95efbfcf`, #101) · H4 Dagster
orchestration of the crews (assets, jobs, weekly lint schedule, new-raw-file sensor),
FR-22(d)/FR-6 (`6cc2dbfeb1`, #102). All four landed 2026-07-18 in a single day via the
in-session agent loop (no `.bmad-loop/runs/` journal exists for this wave — see
`retros/README.md` § Provenance). A parallel CFE Rule-2 skill retro ran the same day
(#103, v8.78.0→v8.79.0) and is a real but differently-shaped record: it validated two
phase-engineering patterns for `atlas-phase-engineering.md` §14, not an epic-level
what-worked/what-did-not accounting. This file is that missing accounting, not a
duplicate of it.

## What worked

- **A Wave-G carry-forward was applied at authoring time, not caught again in
  review.** H1's `factory/wiki.py::stage_path` traversal guard is documented in the
  commit message as "the emitter `_require_safe_name` lesson applied" — the exact
  carry-forward Wave G's retro named ("any component that writes a path from
  external input starts with a name-safety helper... make it a checklist item").
  This is the clearest evidence in the whole effort that a carry-forward item
  actually changed how the next wave was built, rather than only being read.
- **Each attended live-bring-up was deferred honestly and individually, with an
  injectable seam defaulting to offline/refuse.** H1's storage resolver defaults to
  the local filesystem and opens no connection unless `ATLAS_WIKI_S3_ENDPOINT` is
  set (DW-H1); H2's `enricher`/`synthesizer`/`retriever` default to deterministic
  offline behavior (DW-H2); H3's `opener` seam refuses cleanly rather than importing
  `httpx` (DW-H3). None of the three reached for a live host to make its offline
  gate pass.
- **Independent review caught real pre-merge defects and they were fixed before
  merge, not carried as debt.** H2: 2 MUST-FIX (a raw doc's inline `stale:`
  frontmatter was being dropped during compile — i.e. laundered, the exact failure
  AD-13 exists to prevent; and lint/QA crashed on a malformed page instead of
  reporting it) + 1 SHOULD-FIX (leaf-only broken-link matching). H3: 3 SHOULD-FIX
  (malformed-2xx `KeyError`; a non-atomic sidecar write that could brick future
  syncs; a compiled-vs-outputs contract contradiction against H1/§7.4) + NITs. H4
  folded in a review-found `_decode_cursor` crash (a nested-list cursor produced a
  `TypeError` that would have killed the sensor tick) with 8 regression cases.
- **H4 scoped its test invariants correctly instead of forcing a new job kind to
  satisfy old assumptions.** The C1/G3 per-op invariants (timeouts, phase-state
  tags, Phase-P scheduling) were scoped to a new `_kedro_jobs()` helper rather than
  applied to the Wave-H asset-jobs, which legitimately carry neither kedro ops nor
  those tags.

## What did not

- **The live-daemon deferral repeated a third time with no owning item.** C1 first
  deferred live daemon bring-up (`DW-C1-1`), G3 deferred it again (`DW-G3`), and H4
  deferred it a third time (`DW-H4`) before it was promoted to contract level as
  `DC-1` in PRD §6.4. SYNTHESIS.md already names this pattern; H4 is the story that
  completed the repeat. Per SYNTHESIS Action A4 (now standing policy), the second
  occurrence should have triggered the promotion — it took a third.
- **The story whose entire job was "never launder freshness" shipped with freshness
  laundered on one of its two input carriers.** H2's inline-`stale:`-frontmatter
  MUST-FIX means the AD-13 non-laundering guarantee — the acceptance criterion
  itself — was incomplete at first implementation and only made whole by review,
  not by design. The same shape as Wave G's carry-forward #1 (harden a name-safety
  class, not an instance) recurring one wave later against a different invariant.
- **The headline capability ships as a stack of four independently-attended
  deferrals, not exercised together.** H1 (storage server), H2 (agno/LLM synthesis
  + the F3 `vss` retriever), H3 (live Wagtail/httpx), and H4 (the daemon itself,
  which depends on both H1's store and H2's synthesis) are each individually honest
  and well-evidenced, but the "AI software factory" as a running system — crews
  compiling and answering questions against a live wiki on a live CMS — has never
  been exercised end-to-end; only the offline-fixture path has.
- **Sprint-status.yaml's own annotations for H2, H3, and H4 still read "PR
  pending"** as of this writing, despite #100/#101/#102 being merged 2026-07-18 —
  a small, real documentation-lag finding, not a code defect.
- **This retro's absence is itself the finding that motivated it.** Wave H's
  closeout substituted the CFE Rule-2 skill retro for an epic-level retro
  (`retros/README.md` recorded Epic 9 as "satisfied by the CFE Rule-2 retro"). The
  two answer different questions — skill guidance versus epic execution quality —
  and one is not a substitute for the other; the eleven-day currency gap between
  Wave H's code (2026-07-18) and its retro (this file, 2026-08-02) is the direct
  cost of treating them as interchangeable.

## Carry-forward

1. **When a story's acceptance criterion IS an invariant** ("never launder X"),
   enumerate every carrier of X up front as a design checklist item, the way H1
   applied G2's path-safety lesson — don't let review discover a second carrier
   was never enumerated.
2. **A deferral repeating a second time is already the trigger for contract-level
   promotion** (SYNTHESIS A4); H4 is the evidence for why waiting for a third is
   too late. Treat A4 as binding on the next wave, not retrospective-only.
3. **A capability assembled from N independently-deferred attended events should
   name the stack, not just each story's own item** — a reader needs to see in one
   place that H4's daemon cannot run live until H1 and H2 both do, not infer it by
   cross-referencing four ledger entries.
4. **An epic-level retro and a skill-focused Rule-2 retro are both mandatory and
   neither substitutes for the other** — run both at closeout, even when one has
   already happened.
