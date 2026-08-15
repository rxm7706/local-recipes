---
status: dreamt
owner: doctor
date: 2026-08-15
---

# Fleet hygiene, verification & exemplar-standard program

## The dream

Tonight's deferred-work audit found two things at once: a real gap (58+
findings invisible to the detector that's supposed to catch exactly
that), and a *pattern* — this is not the first time this fleet has needed
a one-off, by-hand sweep to catch something no always-on gate watches for.
This Dream is the catalog: every recurring hygiene / verification / audit
/ dashboard-metric / exemplar-standard need this fleet has actually hit,
organized by what already has a Dream, what's mechanically gated today,
what's been done once by hand and never systematized, and what has never
been done at all. The goal is not to build all of this — it's to stop
re-discovering the same shape of gap in isolated sessions six weeks apart
(the `normalize_deferred_ledgers.py` heading-less blind spot was named
once on 2026-07-30 and hit again, independently, on 2026-08-15) by making
the whole landscape visible in one place first.

**Exemplar is the load-bearing concept, not one category among six —
and it already has a real document, not just a memory of one.**
`_bmad-output/EXEMPLAR-STANDARD.md` (see Category 5) designates
`pyforge-atlas` as the exemplar for the whole planning-artifact shape and
states the invariants + conformance table that define "done and clean"
structurally, fleet-wide. Categories 1-4 and 6 answer "is X true /
tracked / fresh / bug-free" — necessary, but none of them say what "fully
done and clean" actually *looks like* for a given kind of artifact.
Category 5's exemplars — `EXEMPLAR-STANDARD.md` foremost, plus the
narrower deck/test-architecture/recipe-pattern ones alongside it — are
that definition. Read the other categories as instruments that measure
conformance *to* an exemplar (or flag that no exemplar has been
designated yet for a given artifact class) rather than as a parallel,
unrelated set of checks. Where no exemplar exists yet for something
Categories 1-4 or 6 name, that absence is itself a finding this catalog
should surface — "we can check whether this drifted, but we've never
actually said what 'not drifted' should look like." And where an
exemplar document DOES exist, as `EXEMPLAR-STANDARD.md` proves, it needs
the same freshness discipline as everything else here — see Category 5's
note on its now-stale conformance table.

## Category 1 — Mechanically gated today (the six detectors + meta-suite)

`python -m pyforge.doctor.sources` exposes 10 subcommands:
`bmad-drift`, `chain-completeness`, `check-layout`, `dashboard-drift`,
`deferred-work`, `dream-chain`, `forward-dependency`, `ledger-regression`,
`spec-surface`, `story-status`. These are the fleet's real always-on
floor — deterministic, CI-enforced, exit-code gated. Tonight's audit
proved even a mechanical detector can have a real blind spot
(`deferred-work`'s `tier3-only-deferral` finding is id-diff-based and
cannot see a headerless or pre-convention Tier-3 entry) — so "mechanically
gated" is not the same claim as "complete." Each of these deserves the
same "is what it actually checks the same as what it claims to check"
scrutiny `deferred-work` just got, on its own schedule, not just when a
user happens to challenge one.

**A second one is already confirmed, in a different detector.**
`chain-completeness`'s INV-A decides "this open Spec is decomposed" with a
bare substring test — does the Spec's slug appear anywhere in the
project's PRD/epics prose (`board.py:463-477`). It parses no `CAP-` ids on
either side. So a Spec can grow from 3 capabilities to 10 and still report
`ok -- every open Spec is decomposed` while seven of them have no story
anywhere in the fleet. Found by execution on 2026-08-15 against
`spec-deferred-work-visibility`, and logged as `DW-CHAIN-COMPLETENESS-1`
in pyforge-doctor's tracked deferred-work ledger. It is structurally the
*same* defect class as the one the extended Spec exists to fix — which is
the point of this category: these are not one-off bugs, they are a
recurring shape, and finding the second one within hours of the first is
the evidence.

## Category 2 — Has its own Dream already (don't re-derive, just link)

- **Deferred-work promotion** (Tier-3 → tracked ledger, id-collision-safe,
  format-complete) — `docs/dreams/deferred-work-audit-completeness.md`,
  **now `status: specified`**: converged into the pre-existing
  `spec-deferred-work-visibility` (CAP-4..7) rather than a new spec-kernel,
  after that Spec's own Q2 turned out to have already named this exact
  follow-on. This Dream's own fleet-wide hygiene-sweep angle (Category 3
  below) converged the same way, as CAP-8/9.
- **Deferred-work resolution** (is a tracked entry still true) —
  `docs/dreams/deferred-work-resolution-sweep.md` (still `status: dreamt`
  — deliberately NOT folded into the same Spec; it's a code-verification
  problem, not a promotion/detection one, and spec-deferred-work-visibility
  names it as a distinct future effort pending its own convergence check).
- **`engine.pid` two-field liveness footgun** (a float+identity string
  misread as a bare pid, corrupting `marshal status`, `fleet-picture`,
  and `dashboard-gen`'s in-flight card alike) —
  `docs/dreams/bmad-loop-liveness-footgun.md` (captured 2026-08-14/15,
  still unspecced per the `dream-chain` detector).

## Category 3 — Done once by hand, never systematized (the real gap
## class this Dream exists to name)

- **`bmad-output-hygiene` sweep** (`CAP-1` dead test scaffolding
  archival, `CAP-2` hollow `sprint-status.yaml`, `CAP-4` README
  placeholders, `CAP-5` orphan files, `CAP-12` stale currency pairs, plus
  a stale-Dream-status flip and a "research-dot" bug fix) — run once,
  for one project (pyforge-warden, commits `bfa9fd68`/`1567a478`/
  `5c5e3727`/`22da995c`/`f7654a4c` on 2026-08-14/15). Never run against
  the other 7 projects. Each `CAP-*` is itself a small, well-scoped
  hygiene check that could become a `pyforge.doctor.sources` subcommand
  the same way `deferred-work`'s Story 7.3 grandfather baseline did —
  but right now it's a memory of a manual session, not a tool.
- **Repo-wide audit remediation waves** (`AUD-CFE-*`, `AUD-REPO-001`
  findings, PRs #131/#133-138) — a broad, one-time repo audit whose
  findings were fixed but whose *audit methodology* was never turned into
  a repeatable check. Worth asking: did the underlying audit questions
  ("is PR #131's remediation actually runnable", the class of question
  that motivated wave 2) get a permanent gate, or just a one-time fix?
- **Deferred-work resolution campaign itself** (see Category 2) — already
  has its own Dream; listed here too because it's the sharpest example of
  this whole category's failure mode: done once, named its own tooling
  gaps, gaps never fixed, gap rediscovered independently six weeks later.
- **Loop-home branch staleness** — tonight's session found all 4 active
  stations' `loop/pyforge-<slug>` branches 55-60 commits behind
  `origin/main` (confirmed pure ancestors, fast-forwarded by hand after
  explicit user authorization). Nothing watches for this — a station
  could re-spin from a stale branch and silently miss weeks of fixes to
  shared infrastructure (the exact `spec-django-accelerator-framework`
  spec-surface-drift-blind bug earlier this session was independently
  rediscovered by 3 stations *because* their branches hadn't caught up).
  A `fleet-picture` ATTENTION line ("loop/pyforge-X is N commits behind
  main") would have surfaced this without a user having to ask "want
  those fast-forwarded" out of nowhere.

## Category 4 — Dashboard / fleet health metrics (the visibility layer)

`fleet_picture.py`'s ATTENTION block already aggregates cross-cutting
health (it grew the baseline-drift check this very session — a good
exemplar of "a finding this shape belongs in the ambient report, not just
a detector run someone has to remember to invoke"). Candidate additions
surfaced by tonight's work alone:
- **Deferred-work verification staleness** — "% of tracked entries with a
  `verified:` date, per project" (ties directly to the resolution-sweep
  Dream).
- **Loop-home branch staleness** — commits-behind-main per
  `loop/pyforge-<slug>` (Category 3, above).
- **`dream-chain` gap count** in the ambient report rather than only a
  separate detector run — `bmad-loop-liveness-footgun.md` sitting
  unspecced is exactly the kind of thing that should nag quietly instead
  of waiting to be noticed.
- The published **GuildHall Fleet Status Dashboard**
  (`docs/reference/GuildHall_Fleet_Status.md`,
  https://rxm7706.github.io/local-recipes/) is the human-facing mirror of
  all of this — worth asking, as this program matures, which of these
  new signals belong on that board too, not just in the CLI report.

## Category 5 — Exemplar / golden-standard references (a different kind
## of "audit" — quality-bar conformance, not correctness)

Everything above is about *correctness* (is this still true, is this
tracked, is this fresh). This category is about *quality* — this fleet
has already designated several artifacts as the standard other work
should match.

**The primary one is not a memory entry — it's a real, structured
document: `_bmad-output/EXEMPLAR-STANDARD.md`.** It designates
`pyforge-atlas`'s `planning-artifacts/` tree as the single exemplar for
the entire 16-stage Dream-to-Code chain (Dream · Deck · Spec · Rsch ·
Brief · PRD · UX · Arch · Context · Epics · Sprint · TEA · Gates · Code ·
Tested · Retro), states five binding invariants (INV-0..INV-5 — one Spec
per Dream, one build-tree shape, detector self-ownership, one canonical
convention register), carries an explicit conformance table scoring every
other station against it, and names its own detector
(`scripts/dream_chain_check.py`) as the mechanical arbiter. This is not
aspirational prose — it's the closest thing this repo has to Category 5's
own answer to "what does 'done and clean' mean," already partially
mechanically enforced, and it should be the anchor everything else in
this category is checked against or modeled on, not a peer example.

**Its conformance table is stale on exactly the row this session's work
touched.** The table (`## Conformance status`) scores a "DW ledger"
column and shows only `pyforge-atlas` as ✅, with warden, doctor, mason,
herald, scribe, steward, and marshal all ❌. That was true when the table
was last written — it is not true now. Tonight's two promotion passes
gave every one of those projects a real, populated, git-tracked
`deferred-work-ledger.md` (warden 43 entries since 2026-07-29, atlas 122,
marshal 109, mason 48, steward 74, herald 45, doctor 20, scribe 7). This
is a live instance of the exact failure mode `EXEMPLAR-STANDARD.md` warns
about in its own text ("a detector's own bugs propagate outward as
confident, wrong numbers") — except here it's the *document*, not a
detector, that went stale, because nothing re-runs `dream_chain_check.py`
against a state change like this one and reconciles the hand-written
table against it. Refreshing that table (and checking whether the other
columns — companions, story specs, delivery records, README — are
equally stale) is a concrete, bounded, immediately-actionable first task
for whoever picks this Dream up — arguably before anything else here,
since it's the one place in Category 5 that already has teeth.

Below that primary reference, the fleet also carries several
narrower, purely-manual exemplars with no mechanical backing at all:
- **The six-act deck framework** (`docs/reference/reference_six_act_deck_framework.md`
  equivalent in auto-memory — cover hook, Acts I-VI, appendix personas,
  L.A.T.C.H. visual principles) — the canonical template for all 21
  station decks.
- **Warden-standalone as the infographic exemplar** (Design `100ca8cc`,
  user-designated best) — the shape reference for server-side infographic
  work.
- **"Full depth + acts for ALL Herald deck/infographic work"** — a
  standing instruction that work should never be size-restricted at
  authoring time, i.e. the exemplar sets a *floor*, not a target to
  economize against.
- Recipe-domain exemplars inside `conda-forge-expert` itself (the
  canonical npm recipe pattern, the v0↔v1 about-field mapping) — same
  shape: a hand-curated "this is what good looks like," consulted by
  convention, never checked mechanically.
- Narrower canonical-*form* conventions, same failure mode at smaller
  scale: BMAD conda-forge specs must use CFE's `add-recipe-<name>`
  branch-naming convention (drift here was found once, 2026-06-10 S1
  retro, and is easy to silently reintroduce in a future hand-authored
  spec since nothing checks it).

Two data points on what "graduating" an exemplar out of pure convention
looks like — worth studying as the aspirational end-state for the ones
still purely manual above, not just naming the gap:
- **The universal conda-forge.yml pre-seed** started as a hand-maintained
  convention (established 2026-06-16), got a per-setting applicability
  audit (G83) that corrected real drift in it, and is now **auto-emitted
  by the recipe generator itself** — the exemplar became the default,
  so there's nothing left for an author to forget. This is the target
  shape a lightweight checklist should aim for, not settle for.
- **Herald's TEA+Playwright test-architecture was designated the fleet's
  canonical reference** (2026-08-02 decision) specifically so the other
  7 stations wouldn't each re-derive their own test strategy — and,
  checked directly while writing this Dream, the fleet-wide rollout
  actually happened: all 8 stations carry a real
  `planning-artifacts/test-architecture.md` today (Category 3's own
  `bmad-output-hygiene` sweep independently confirms this — one of its
  fixes was replacing several stations' *fabricated* test-architecture
  files with real ones). A genuine success case of an exemplar becoming
  a fleet-wide standard through a repeatable script rather than staying
  a one-station reference nobody else copies.

For the exemplars still purely manual (the deck/infographic family,
recipe-domain patterns), the open question is the same one these two
success cases answer differently: does becoming mechanical mean baking
the standard into a generator/template (conda-forge.yml's path), or does
it mean a repeatable apply-to-the-whole-fleet script plus a durable
"is this still the reference" check (Herald's path)? Worth deciding
per-exemplar when this program is sized, not assuming one shape fits all
of Category 5.

## Category 6 — Named ledger/artifact machinery bugs (small, concrete,
## currently untracked as their own fix)

Bugs specific enough to fix directly rather than needing a whole Dream,
but real enough that they shouldn't just live in a memory file:
- `normalize_deferred_ledgers.py`'s heading-less-entry blind spot (shared
  root cause between Category 2's two deferred-work Dreams).
- `warden DW-1-4-1` — still needs splitting into two ids (named
  2026-07-30, never done).
- `scripts/spec_surface_check.py --write-baseline`'s unlocked
  read-modify-write race on `scripts/.spec-surface-baseline.json` — named
  as a deferred finding by this very session's atlas promotion
  (`DW-13-5-2`), real given this repo's own documented history of
  concurrent-agent races on shared per-worktree state.

## What this Dream is NOT

Not a commitment to build all of this. Not a spec — none of these
categories are sized, prioritized against each other, or scoped for
implementation here. The point is narrower: the next time someone (human
or agent) is about to spend a session rediscovering "huh, nothing
actually checks for X" for some X that rhymes with one of the six
categories above, this file should be the first thing they read, so the
finding lands as "yes, catalogued, category 3, still not done" rather
than as a fresh, isolated discovery that fades from context again in six
weeks.
