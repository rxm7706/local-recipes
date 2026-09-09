---
spec: landing-evidence-grammar
status: shipped
updated: "2026-09-09"
owner-dream: docs/dreams/landing-evidence-grammar.md
surface:
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py
  - src/shared/packages/pyforge-core/
sources:
  - ../../../../../../docs/dreams/landing-evidence-grammar.md
open_questions: []
  # ANSWERED 2026-09-09, both retired -- RESOLVED BY STORY 20.8, propagated now
  # (fleet-readiness batch Class B, row mars-B). Full text with answers in
  # § Open questions -- closed 2026-09-09.
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/landing-evidence-grammar.md` is listed in
> `sources:` for narrative rationale — and the full evidence trail of the 2026-08-14
> broken-windows audit — this contract intentionally omits.

# A legitimate landing is recognizable no matter which of the three-plus paths landed it

## Why

Every detector and classifier that asks "did this story actually land on `main`?" currently speaks
its own partial dialect. Doctor's `story-status` evidence routes (`sources/marshal.py:479-517`)
grep only bmad-loop's native `/{key} into` merge shape (route 2) or demand the literal conjunction
`<slug>` + `story <e>.<s>` in a `main` subject (route 3). Marshal's promotion chain
(`core/promotion.py:93-107`, `merged_story_keys` / `marshal_native_merged_keys`) runs a different
three-pattern chain, including `_GITHUB_MERGE_SUBJECT_RE`'s requirement that the merged branch's
final segment *lead* with a story key — which `land/marshal-10-1-recovery` fails. `marshal
status`'s MRS-STATUS-010 failed-patch classifier and `marshal retire`'s patch-id matching form a
third and fourth partial view. One root cause, measured live on 2026-08-14: three `story-status`
hard-FAILs on demonstrably landed stories (marshal 8-2, marshal 10-1, mason 3-7 — PRs
#482/#486/#483), 26 MRS-STATUS-010 UNCONFIRMED warns, and `marshal retire` at 0 proposals because
recovered branches cannot be confirmed merged. The recovery-landing class created by the five
stuck-orchestrator-baseline recoveries (PRs #482–#488) matches none of the recognized grammars —
each live recovery commit (`accc097e6a`, `5290c9bcd2`, `03d8fc8c86`) fails a *different* predicate.

The emitting side is already solved: `identity.render_merge_subject` (AD-24) and FR-187 (`marshal
land` renders it) make Marshal-driven landings conformant going forward. The gap is the *consuming*
side's fragmentation, plus the unconformant manual-recovery class — so operators keep proving
landings by hand with `git log --all --grep` while one tool re-flags what another counts done.

## Capabilities

- **CAP-1**
  - **intent:** ONE shared grammar of landing-evidence shapes — merge-subject templates,
    branch-name grammars (`land/<station>-<story>…`, `bmad-loop/<run>/<story>`), and a documented
    recovery-commit convention — defined once as a contract/data/pyforge-core artifact (home is
    this capability's own design decision, bounded by the Constraints), consumed by everything
    that classifies landings. The recovery-landing convention is part of the grammar: the *next*
    manual recovery is born recognizable instead of born invisible.
  - **success:** The grammar recognizes, as written (or via the one-time reviewed allowlist of the
    open question), the three live recovery commits `accc097e6a` / `5290c9bcd2` / `03d8fc8c86`
    that today each fail a different predicate — alongside bmad-loop's native `/{key} into` shape,
    the FR-187 templated subject, and the `land/…` branch grammars — and a cross-package
    conformance surface exists that both doctor and marshal test against without doctor importing
    `pyforge.marshal`.
- **CAP-2**
  - **intent:** Doctor-side adoption — `story-status`'s evidence routes (`sources/marshal.py:
    479-517`) consume the shared grammar instead of route 2/route 3's private dialects, widening
    what is *recognizable* while leaving the hedged treatment of absence-of-match untouched.
  - **success:** On the live repo, the three standing `story-status` false positives (marshal 8-2,
    marshal 10-1, mason 3-7) go green with **no per-story whitelist**; a genuinely-unlanded story
    still fails exactly as today.
- **CAP-3**
  - **intent:** Marshal-side adoption — the promotion classifiers (`core/promotion.py:93-107`),
    MRS-STATUS-010's failed-patch classifier, and `marshal retire`'s patch-id matching consume the
    same grammar, so a recovery landing confirmed by one classifier is confirmed by all of them.
  - **success:** MRS-STATUS-010's UNCONFIRMED pile shrinks from 26 to only genuinely-unlanded
    patches (its honest "UNCONFIRMED, not proof it never landed" wording at `core/status.py:
    836-861` retained); `marshal retire` proposes real retirements again on the live tree, where
    recovered branches are demonstrably merged.
- **CAP-4** *(added 2026-08-28 — motivated by a live fleet-wide hygiene sweep that found 25
  standing `story-status` FAILs across doctor/marshal/mason/steward, all independently confirmed
  genuinely-landed via `git merge-base --is-ancestor`)*
  - **intent:** Story 20.9's own doctor-side adoption of the grammar was incomplete in two ways,
    both closed here without touching the grammar itself: (a) `sources/marshal.py`'s Routes 2/3
    never tried `classify_branch_name`'s `land/<station>-<epic>-<seq>` / `bmad-loop/<run>/<key>`
    branch-name grammars when a captured GitHub-PR branch didn't carry a station/dispatch prefix
    — `core/promotion.py::_classify_merge_subject` (CAP-3's own implementation) already had this
    exact fallback; doctor's port never picked it up. (b) A residual class of real, hand-authored
    landing commits (`"<station>: promote story <e>.<s> to done..."`,
    `"land <station> <e1>.<s1>+<e2>.<s2> (N stories): ..."`, etc.) matches no anchored grammar
    shape at all and never will — scoped to doctor's own advisory detector only (never the shared
    grammar, never anything marshal's actual gating logic reads), a fourth, deliberately loose
    "station + exact numeric key co-occur anywhere" route closes this without loosening any
    safety-critical consumer.
  - **success:** All 25 standing false positives (doctor 6 stories, marshal 10, mason 7, steward 2
    — see this capability's own story for the full list) go green with no per-story whitelist,
    same bar CAP-2 itself set; a genuinely-unlanded story (wrong station, or a longer numeric key
    like "11.10" for a "11-1" search) still fails exactly as today, pinned by dedicated negative
    tests; zero changes to `pyforge.core.landing_evidence` or `pyforge.marshal.core.promotion`.

## Constraints

- **HARD:** doctor never imports `pyforge.marshal` (classifier-independence rule, per-check
  isolation). The shared grammar therefore cannot be a code import from Marshal: it is a contract
  with a cross-package conformance test, a shared data artifact both read, or a `pyforge-core`
  home — the same shared-spine move Story 14.2 made for atomic-write. Which one is decided at
  story level (open question), inside this boundary.
- **Always:** absence of evidence stays hedged where it is hedged today — the grammar widens what
  is *recognizable*; it must not convert "no match" into a confident "never landed" anywhere.
- **Always:** forward-compatible with FR-187 — the templated merge subject is one shape *in* the
  grammar, never the grammar itself.

## Non-goals

- **Not** retroactive rewriting of historical merge subjects — the grammar recognizes the existing
  recovery landings as they were actually written (or accepts a one-time, reviewed allowlist for
  the pre-convention era); it never rewrites history.
- **Not** a new landing path — this recognizes landings, it does not perform them.
- **Not** a general provenance system — the question is exactly "did story X land on `main`",
  nothing broader.

## Success signal

Today, a story demonstrably on `main` is re-flagged as missing by one tool while another counts it
done, and a landing is proven by hand with `git log --all --grep`. After this spec: the three
standing `story-status` false positives (marshal 8-2, 10-1, mason 3-7) read green with no
per-story whitelist (CAP-2); MRS-STATUS-010's UNCONFIRMED pile shrinks to genuinely-unlanded
patches and `marshal retire` proposes real retirements (CAP-3); and the next manual recovery
follows a documented, grammar-conformant convention, so it is recognized by every consumer on the
day it lands (CAP-1). Absence-of-match stays hedged everywhere it is hedged today.

**Measured 2026-09-09.** `pyforge.doctor.sources.marshal::gather_story_status` over the live
tree reports: *no `done` story contradicts its landing evidence — **898 audited, 708 with no run
record (unchecked)***. The green is real over the **190** stories that carry a run record; it is
not a fleet-wide claim, and the success signal says so rather than reading as one. The hedge is
correct by design (the Dream's own Constraints: absence of evidence stays hedged where it is
hedged today), so **no coverage story is minted** — one is worth it only if run records become
recoverable for pre-dispatch-era stories, which this Spec's Non-goals forbid rewriting history to
achieve.

## Open questions — closed 2026-09-09

Both resolved by **Story 20.8** and propagated to the frontmatter on 2026-09-09. Question text
preserved; the answer follows each.

- ~~"Grammar home (a story-level design decision): a contract with a cross-package conformance
  test, a shared data artifact both packages read, or a `pyforge-core` module (the Story 14.2
  atomic-write shared-spine precedent) — constrained by the HARD rule that doctor never imports
  `pyforge.marshal`."~~ **CLOSED: a `pyforge-core` module.** The grammar lives in the shared
  spine as `pyforge-core` `landing_evidence.py` — no station import, the Story 14.2 precedent —
  and is consumed by `pyforge/doctor/sources/marshal.py:53` and
  `pyforge/marshal/core/promotion.py:58`. The HARD constraint holds by construction.
- ~~"Pre-convention history: whether the grammar recognizes the existing recovery landings
  exactly as they were written, or a one-time, reviewed allowlist covers the pre-convention era —
  never a rewrite of history either way."~~ **CLOSED: a SHA-prefix allowlist**
  (`parse_recovery_commit_sha` at `landing_evidence.py:315`) — never a rewrite. The three standing
  false positives are fixture-pinned at `landing_evidence.py:441` / `:450` / `:461`, with no
  per-story whitelist.

## Decomposition

CAP-1..CAP-4 decompose to Stories 20.8–20.11, all `done`.
