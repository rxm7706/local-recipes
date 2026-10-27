# Sweep tooling effectiveness — measured 2026-09-08

**A shipped capability that matches nothing is indistinguishable from an absent one.**
This file records what CAP-2, CAP-3 and CAP-6 actually delivered when the fleet's first
full sweep ran them against all 1,410 tracked entries. Companion of
`spec-deferred-work-resolution-sweep`.

Written because the operator asked for CAP-3 to be widened, on the assumption that doing so
would mechanise a meaningful share of the 183-entry backlog. It would have mechanised **two**.
The measurement below is why that build was dropped in favour of recording this.

## The headline

| capability | intended leverage | measured leverage |
|---|---|---|
| **CAP-2** churn filter | skip entries whose cited code has not moved | reached **39 of 183** due entries; most extracted "paths" do not resolve |
| **CAP-3** mechanical verification | produce a verdict with no agent | matched **0 of 1,410** entries fleet-wide |
| **CAP-6** correlation | collapse duplicates into defect classes | **1** near-duplicate pair by summary; **0** cross-project shared tokens |

All three are inert against these ledgers. The sweep was 183 agent reads, with no shortcut
available from the machinery built to avoid exactly that.

## Why CAP-3 matched nothing

CAP-3 recognises **one** claim shape: a backtick-quoted bare identifier claimed *unused /
unreferenced / no callers / never called / dead code* within 80 characters. Not one entry in
1,410 is written that way.

Classifying all 183 never-verified entries by the language they actually use:

| claim shape present | entries | share |
|---|---|---|
| generic "deferred / out of scope / a later story" | 181 | 98% |
| "absent / missing / does not exist" | 17 | 9% |
| "hardcoded / duplicated / drifts apart" | 8 | 4% |
| "should / ought to / needs to" | 7 | 3% |
| a count claim ("N call sites") | 3 | 1% |
| "unused / no callers" | 3 | 1% |
| "nothing enforces / no check / untested" | 2 | 1% |

The 98% row is the finding. These entries are **prose about decisions, trade-offs and
scope judgements**, not mechanically recomputable facts. "Was this deferral still the right
call?" is not a question a grep can answer.

**Widening to the only genuinely mechanisable shape gains 2 entries.** An absence claim
naming *both* a token and a path — the one shape a checker could settle — exists in exactly
`atlas/DW-FU-20-4-7` and `steward/DW-FU-41-3-2`, and only one of those paths still resolves.
Even the 17 "absent/missing" hits are mostly prose about runtime errors (`ERROR: relation
"django_site" does not exist`), not claims that a file is missing.

## Why CAP-2 reached so little

CAP-2 needs an extractable path and a resolvable authoring date. Of 183 never-verified
entries, **144 cite no extractable path at all**.

| station | never-verified | with 0 extractable paths |
|---|---|---|
| steward | 139 | 111 |
| marshal | 19 | 14 |
| atlas | 17 | 12 |
| doctor | 3 | 3 |
| mason | 3 | 3 |
| herald | 2 | 1 |

And the 39 that *do* extract something mostly extract false positives — the path regex
over-matches dotted symbols and URLs: `ibis.duckdb.connect`, `duckdb.connect`,
`pyforge.io/query-plane`, `platform.djangoEnv`, `http.disconnect`. Those fail to resolve in
`_churn_since` step 1 and fall back to "not skipped", by design. Net: the churn filter
skipped **zero** entries in this sweep.

## Why CAP-6 found almost nothing

Two axes, both measured across the 183:

- **Near-duplicate summaries** (≥0.72 similarity): **1 group, 2 entries** — both in steward,
  both the same "scoped spec-surface stamp not run by this story" claim.
- **Shared cited tokens**: 51 tokens are cited by more than one due entry, but **0** are
  cited across more than one project.

Cross-project correlation had nothing to find here because 139 of the 183 belong to one
station.

**But the sweep itself found four defect classes by hand that CAP-6 missed**, because they
share a *subject* rather than a token or a phrasing:

1. `steward/DW-FU-42-2-4`, `DW-FU-42-2-17`, `DW-FU-42-3-11` — one class ("this story did not
   run the scoped stamp"), three rows.
2. `steward/DW-FU-46-1-2` and `atlas/DW-FU-24-1` — the **same helper**
   (`_persona_mentions`), indicted from two sides, in two different projects' ledgers, with
   neither entry referencing the other. This is precisely CAP-6's stated intent and it did
   not fire.
3. `atlas/DW-FU-20-5-11` and `DW-FU-20-5-4` — the same "DW-D2-3 stays open" claim.
4. `steward/DW-FU-42-1` and `DW-FU-42-2-5` — the same missing keypair Secret.

## What would actually help the next sweep

Not a wider CAP-3. The binding constraint is that **entries do not cite the code they are
about** — 144 of 183 cite nothing resolvable. Every citation added during this sweep is
therefore worth more than any parser change: it is what gives CAP-2 something to check.

Ranked by measured value:

1. **Require a resolvable `location:` at promotion time.** `deferred_work_intake.py` could
   refuse, or flag, an entry citing no path. This attacks the 144 directly.
2. **Tighten CAP-2's path regex** so a dotted symbol is not mistaken for a file. Cheap, and
   makes the churn filter's "not skipped" mean something.
3. **Correlate by subject, not by token or phrasing** — the four classes above were all
   found by reading, and all four would have been found by grouping on the file/symbol an
   entry is *about* rather than the strings it happens to contain.
4. **Leave CAP-3 alone** until entries are written as checkable claims. The capability is
   not broken; its premise does not match the data.

## Provenance

Measured on branch `chore/deferred-work-sweep-fleet-2026-09-08` against all eight tracked
ledgers (1,410 entries, 183 never-verified) before any verdict was written. Every figure is
reproducible: the shape classification and path/token extraction ran through
`pyforge.doctor.sources.chain`'s own `_verification`, `_entry_named_paths` and
`_entry_unused_symbol_claims`, i.e. the same functions the detector uses, not a parallel
re-implementation.
