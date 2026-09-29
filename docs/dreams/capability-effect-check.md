---
title: A capability is not done until something exercises it
type: dream
owner: doctor
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-doctor]]** on 2026-09-17 (one-chain-per-station doctor fold).

# A capability is not done until something exercises it

## The Dream

The fleet's ledgers say 737 of 775 stories are `done`, and the fleet is not switched on.
The 2026-09-09 readiness pass found **eighteen** capabilities of one identical shape: a
`done` epic, merged code, a green suite — and a named success criterion that has never
been exercised in the running estate. `risk-tiered-review-depth` is `shipped` with zero
callers outside `tests/unit/test_gate.py`. `marshal-token-economy` is 24/24 `done` with
every layer off. `marshal-parallel-dispatch-fanout` has `max_parallel = 1` everywhere and
has never run a wave. Three of those four were visible only by grepping for call sites;
no board, no detector and no ledger could tell.

The Dream is the cheap, ambient half of the realization gate: a doctor Source that, for
every capability the fleet declares, asks **"is anything reaching this?"** — and says so
in the same breath as `story-status-check` says whether the story landed. Two questions,
side by side, every time anyone runs `detectors`: *did it merge* and *is it in effect*.

It is deliberately not a judgement. It is the difference between "nobody noticed" and
"we chose not to" — the same distinction `chain-completeness`'s INV-A was built to make
one tier up, applied one tier down, to the capability rather than the Spec.

## The join key (named up front, on purpose)

The check joins on **`(spec-slug, CAP-N)`** — the pair `board.py`'s own
`_parse_declared_cap_ids` and `_cited_cap_ids_by_spec` already produce for INV-A. That
key reaches code through the citing story's `Surface:` line in the owning station's
`epics.md`, and reaches evidence through an optional `verified:` line on the CAP itself
in `SPEC.md`. Nothing new is parsed that the fleet does not already parse.

Naming the key in the Dream is not ceremony. This station shipped
[[sibling-dreams-drift]] against a join (`title:`) the estate does not share, and the
detector has been structurally incapable of a finding since the day it merged. The
lesson is written into this Dream's Constraints: **the join must be proven against live
data, not a fixture, before the first story closes.**

## What it looks like when real

- **The cheapest test first: a caller outside its own test file.** For a capability whose
  citing story names Python surfaces, the check asks whether any symbol those surfaces
  define is referenced from somewhere that is not that module and not a test. A `shipped`
  capability whose every reference is a test is reported — warn, named, with the file it
  looked in. This single question would have caught all four marshal cases in one pass.
- **The evidence line, when someone has looked.** A CAP may carry `verified: <date> — <what
  was exercised, where>`. The check renders that line beside the capability, and reports
  a `shipped`/`realized` capability that carries none. This is the "realized versus
  verified" column the Unifying Strategy's own review asked for, made mechanical.
- **It renders beside `story-status-check`.** Same ambient surface, same `detectors` run,
  same report. An operator reading "story 33.4 landed" reads "and nothing calls it" on
  the next line, not three weeks later in a readiness pass.
- **It goes quiet when the fleet is in effect.** A capability with live callers and a
  current `verified:` line produces nothing at all.
- **It fails open, loudly.** When a station's `epics.md` cannot be parsed, or a surface
  path no longer exists, the check says *that* — it never renders "could not look" as
  "looked and agreed" (the second lesson [[sibling-dreams-drift]] paid for).

## Constraints / Non-goals

- **Advisory, always.** Warn at most, never a second PR verdict. Doctor's exit-code
  contract is sole-owned by `pyforge.doctor.verdict.exit_code_for` and pinned by
  `tests/meta/test_verdict_sole_ownership.py`; this Source produces `Finding`s and
  nothing else. The fleet already has exactly one fail-closed gate and this is not it.
- **Fail-open, and say so.** An unreadable `epics.md`, an absent surface path, a station
  with no ledger: each degrades to a named finding, never to silence and never to a hard
  failure.
- **The join key is proven on live data before the first story closes.** A fixture that
  constructs both sides from the same synthetic value cannot reproduce a live failure —
  that is precisely how `sibling-dreams-drift` shipped silent.
- **Not a coverage tool, not a call-graph resolver.** "Has a caller outside its own test
  file" is a textual, whole-word reach over declared surfaces — deliberately cheap,
  deliberately approximate, and honest about it in the finding text.
- **Not a re-implementation of `story-status-check`.** That check answers "did the story
  land". This one answers "is the capability reached". They render together and stay
  separate modules.
- **It does not write.** No status is flipped, no ledger row is moved, no `verified:` line
  is authored by the check. Read-only, per doctor's NFR-1.

## Kinships

[[pyforge-unifying-strategy]] (the criterion's home — steward Story 49.2 mints it there;
this Dream is the implementation half the 2026-09-09 batch relayed to doctor, § 2.3 C8) ·
[[intelligence-hub]] (the re-home: Epic 49's gate moves to `hub:CAP-*` Guards once that
Spec is `ready`; a doctor-side Spec makes that a pointer change rather than a migration) ·
[[sibling-dreams-drift]] (the shape — ambient, warn-only, fail-open, one new Source, one
capability — and the cautionary tale about picking a join key nobody shares) ·
[[marshal-token-economy]] (the motivating pathology in its purest form: 24 of 24 stories
`done`, every layer off) · [[pyforge-doctor]] (the station; `bmad_method.py:9-20` is
doctor's own written precedent for a dedicated module over an extension of an existing
Source).

## Realization log

- **2026-09-09** — Captured. Relayed from steward Story 49.2 by the fleet-readiness
  decision batch (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
  § 2.3 C8, operator-approved the same day): the *criterion* stays on
  `spec-pyforge-unifying-strategy`; the *implementation* comes home to doctor, because
  every other doctor Source arrived through doctor's own chain and because a steward story
  writing a new module into `src/shared/packages/pyforge-doctor/**` is a foreign edit to a
  doctor-governed surface that `spec-surface-check` would red at merge. The incoming
  surface claim is recorded in `spec-pyforge-doctor`'s memlog the same day. The cheapest
  first test — "has a caller outside its own test file" — comes from the readiness pass's
  marshal-B report § E-6, which found three of marshal's four dormant capabilities visible
  by no other means.
- **2026-09-13** — Realized. Shipped via doctor Stories 21.9 (`c27e8386d8`, the caller-reach
  check), 21.10, and 21.11 (`2bb7bc58f5`, wired beside `story-status-check`), plus a
  surface-path resolver fix (`b2e5b9e948`). `sources/capability_effect.py` walks every
  project under `_bmad-output/projects/` (not a hardcoded station list), joining on
  `(spec-slug, CAP-N)` exactly as specced. Live run against the real fleet: 396 findings
  across steward/warden/marshal/doctor Specs, `pixi run -e local-recipes
  capability-effect-check` exit 0 (advisory, as constrained). `pyforge-doctor-test -k
  capability_effect`: 30/30 pass. This unblocks steward Stories 49.2 and 49.8 (49.8 already
  closed separately, `96387a0730`).
