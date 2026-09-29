---
title: A legitimate landing is recognizable no matter which of the three-plus paths landed it
type: dream
owner: marshal
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-marshal]]** on 2026-09-16 (one-chain-per-station CAP-8 pilot; folded from `landing-evidence-grammar`).

# A legitimate landing is recognizable no matter which of the three-plus paths landed it

## The Dream

Every detector and classifier that asks "did this story actually land on `main`?" consults the
same, single grammar of landing evidence — and that grammar covers every sanctioned way a story
can land: a bmad-loop native merge, a `deploy land-story` / `marshal land` templated merge, a
quick-dev PR merge, and a manual recovery landing. A story that is demonstrably on `main` is
never re-flagged as missing by one tool while another tool counts it done, and no operator ever
again proves a landing by hand with `git log --all --grep` because three classifiers each speak a
different dialect.

## What it looks like when real

- One vocabulary of recognized landing-evidence shapes — merge-subject templates, branch-name
  grammars (`land/<station>-<story>…`, `bmad-loop/<run>/<story>`), and the recovery-commit
  convention — defined once, consumed everywhere that classifies landings.
- Consumers converge on it:
  - Doctor's `story-status` evidence routes (`sources/marshal.py:479-517`) — today route 2 greps
    only bmad-loop's native `/{key} into` shape and route 3 demands the literal conjunction
    `<slug>` + `story <e>.<s>` in a `main` subject.
  - Marshal's `core.promotion.merged_story_keys` / `marshal_native_merged_keys` three-pattern
    chain (`promotion.py:93-107`), including `_GITHUB_MERGE_SUBJECT_RE`'s requirement that the
    branch's final segment *lead* with a story key — which `land/marshal-10-1-recovery` fails.
  - `marshal status`'s MRS-STATUS-010 failed-patch classifier and `marshal retire`'s
    patch-id matching (today: 0 retirement proposals because recovered branches can't be
    confirmed merged).
- A documented recovery-landing convention: a manual recovery commit/PR has a named, grammar-
  conformant subject shape, so the *next* recovery is born recognizable instead of born invisible.
- Detector deltas measured the day it ships: the three standing `story-status` false positives
  (marshal 8-2, marshal 10-1, mason 3-7 — all verified genuinely landed, PRs #482/#486/#483) go
  green with no per-story whitelist; MRS-STATUS-010's UNCONFIRMED pile shrinks to genuinely
  unlanded patches; `marshal retire` proposes real retirements again.

## What is real

- The false-positive family is live and measured (2026-08-14 detector run): 3 `story-status`
  hard-FAILs on landed stories, 26 MRS-STATUS-010 UNCONFIRMED warns, `retire` at 0 proposals —
  all one root cause: recovery-PR landings match none of the recognized grammars.
- The five stuck-orchestrator-baseline recoveries (PRs #482-#488) created the recovery-landing
  class this grammar must cover; `docs/dreams/bmad-loop-baseline-drift.md` documents why more
  recoveries may happen.
- Marshal already owns the *emitting* side end-to-end: `identity.render_merge_subject` (AD-24) and
  FR-187 (`marshal land` renders it) make Marshal-driven landings conformant going forward. The
  gap is the *consuming* side's fragmentation, plus the unconformant manual-recovery class.
- MRS-STATUS-010 already words absence-of-match honestly ("UNCONFIRMED, not proof it never
  landed", `core/status.py:836-861`) — the hedge is correct; the grammar makes it decidable.

## Constraints

- **Doctor never imports `pyforge.marshal`** (classifier-independence rule, per-check isolation).
  The shared grammar therefore cannot be a code import from Marshal: it is either a contract with
  a cross-package conformance test, a shared data artifact both read, or a `pyforge-core` home —
  the same shared-spine move Story 14.2 made for atomic-write. Deciding which is Spec work.
- Absence of evidence stays hedged where it is hedged today: the grammar widens what is
  *recognizable*, it must not convert "no match" into a confident "never landed" anywhere.
- Forward-compatible with FR-187: the templated subject is one shape in the grammar, not the
  grammar itself.

## Non-goals

- **Not** retroactive rewriting of historical merge subjects — the grammar must recognize the
  existing recovery landings as they were actually written (or accept a one-time, reviewed
  allowlist for the pre-convention era), never rewrite history.
- **Not** a new landing path — this recognizes landings, it does not perform them.
- **Not** a general provenance system — the question is exactly "did story X land on main",
  nothing broader.

## Kinships

- [[marshal-land-merge-subject]] — realized; made Marshal's own landings conformant (FR-187).
  This dream is its consuming-side completion.
- [[quick-dev-reconciliation]] — realized; `not-loop-native` completions reach the ledger
  (FR-186). This dream sharpens what `not-loop-native` can be *decomposed into*.
- [[bmad-loop-baseline-drift]] — the producer of the recovery-landing class this grammar must
  recognize.

## Realization log

- **2026-08-14** — Captured by the 2026-08-14 broken-windows audit, which root-caused the three
  standing `story-status` false positives, the 26-warn MRS-STATUS-010 pile, and `marshal
  retire`'s 0-proposal state to one shared cause: three independent classifiers, three partial
  grammars, and a recovery-landing class none of them recognize. Verified against
  `sources/marshal.py` (routes 1-3), `core/promotion.py` (three patterns), and the live recovery
  commits (`accc097e6a`, `5290c9bcd2`, `03d8fc8c86`) that each fail a different predicate.
- **2026-08-14** — Specified:
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-landing-evidence-grammar/SPEC.md`
  (status: ready) carries the contract — CAP-1 the shared grammar artifact (home decided at story
  level within the doctor-never-imports-marshal boundary), CAP-2 doctor-side adoption, CAP-3
  marshal-side adoption. Decomposed the same day into epics.md Epic 20 (Stories 20.8–20.10,
  FR-191).

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`specified` → `realized`,
  verified in effect rather than by ledger.** Stories 20.8–20.11 shipped
  `pyforge.core.landing_evidence` as the shared spine (no station import — the Story 14.2 precedent),
  consumed by `doctor/sources/marshal.py:53` and `marshal/core/promotion.py:58`; Spec `ready` →
  `shipped` with both frontmatter questions resolved by 20.8 (home = a `pyforge-core` module;
  pre-convention history = a SHA-prefix allowlist, `parse_recovery_commit_sha` at `:315`, never a
  rewrite of history). Live measurement the same day:
  `pyforge.doctor.sources.marshal::gather_story_status` reports *"no `done` story contradicts its
  landing evidence (898 audited, 708 with no run record (unchecked))"*; the three standing false
  positives (marshal 8-2, marshal 10-1, mason 3-7) are fixture-pinned at
  `landing_evidence.py:441/450/461` with no per-story whitelist. **Operator ruling:** accept the
  green and record the coverage number in the success signal — the green is real over the 190 stories
  that carry a run record; no coverage story is minted, because recovering run records for
  pre-dispatch-era stories is what this Dream's own non-goals forbid. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.
