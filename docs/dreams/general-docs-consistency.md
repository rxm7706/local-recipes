---
title: General documentation stops contradicting itself, and stays that way
type: dream
owner: doctor
status: realized
---

# General documentation stops contradicting itself, and stays that way

## The Dream

This repo's BMAD-tier documentation already has real hygiene detectors —
`capability-effect-verified`, `status-body-consistency`, `sibling-dreams-drift`,
`dreams-hygiene` — all owned by Doctor, all catching the same underlying failure
mode: a claim that used to be true and silently isn't anymore. None of them reach
the **general, human-facing documentation layer**: `README.md`, `CLAUDE.md`,
`AGENTS.md`, station `README.md`s, `.claude/skills/*/skill-brief.yaml`, and
`docs/dreams/*.md`'s own identity claims about what each PyForge station *is*.
That layer has never had a detector, and a two-pass live audit this session
(2026-09-11) proved it needs one. The initial framing was that the tree itself
is fine — `docs/reference/`, `docs/intake/`, `docs/dreams/`, `docs/specs/`,
`archive/docs/` are internally coherent and deliberately maintained — and only
the *content* drifts and contradicts itself across files nobody cross-checks.
That first half still holds for the BMAD spec-driven tier specifically (see
Non-goals). But "internally coherent" is not the same claim as "recognizable
to someone arriving with no prior context" — see the second finding below,
which widens this Dream to cover that gap too.

**Confirmed evidence, this session, each independently verified by direct
file reads before being trusted:**

1. **Doctor's own README contradicts three other authoritative sources about
   itself.** `src/shared/packages/pyforge-doctor/README.md` claims doctor
   consolidates warden + cf_atlas signals into "its own exit-code gate."
   `.claude/skills/pyforge-doctor/skill-brief.yaml`, `CLAUDE.md`'s SKF block, and
   `AGENTS.md` all say explicitly: "Findings stay advisory — not a second PR
   gate," "never a competing PR verdict." "Gate" is a loaded, specifically-owned
   term in this repo (Warden legitimately is one); Doctor's README borrows it
   for a station that everywhere else is defined by NOT being one.
2. **`AGENTS.md` and Herald's own Dream assign the identical named
   responsibility to two different stations.** `docs/dreams/pyforge-herald.md`:
   *"Not infrastructure — BMAD monorepo/multi-project machinery and
   cross-agent portability belong to [[pyforge-marshal]] (the 2026-07-23
   ownership review...)."* `AGENTS.md`: *"Keeping the Dream → spec handoff
   portable across agents is **Herald's** job."* Herald's own Dream disclaims
   this by name, citing a dated ownership review; `AGENTS.md` — the highest-
   visibility cross-tool entry point in the repo — hands it back anyway.
3. **`README.md`'s "GitHub Actions Workflows" section describes 4 of 19 real
   workflow files** and claims CI is "manual trigger only to preserve quota" —
   false for the 15 it omits, several of which (`staged-recipes-linter.yml`,
   `detectors.yml`, `coverage-gates.yml`, `pyforge-station-tests.yml`,
   `platform-ci.yml`) are the repo's actual automatic PR-gate CI.
4. **`README.md` contradicts itself within the same file.** Its own "Project
   structure" tree lists `docs/bmad-setup-plan.md` and `docs/developer-guide.md`
   — neither exists at those paths (real paths: `archive/docs/bmad-setup-plan.md`,
   `docs/reference/developer-guide.md`) — while the SAME file's own prose,
   fifteen and one hundred lines later respectively, cites the correct paths.
5. **The active-project-resolution-priority list is duplicated verbatim in
   `README.md` and `CLAUDE.md`,** with `CLAUDE.md`'s copy carrying the
   two-symlink mechanism and the parallel-agents hazard that `README.md`'s
   copy omits entirely — one fact, two owners, already unequal.
6. **`CLAUDE.md` states two different station counts in the same file.** Line
   30 names all 8 PyForge Guild stations; its own "SKF Skills" block, further
   down, says "7 skills" and lists 7 — omitting Mason. (Mason genuinely has no
   `.claude/skills/pyforge-mason/` — confirmed deliberate, documented policy in
   `AGENTS.md`, not a gap — but the SKF block doesn't say so, so a reader hits
   an unexplained-looking discrepancy.)

A **light identity-consistency pass on the other 6 stations** (atlas, marshal,
mason, scribe, steward, warden) found nothing comparable — so this is not "the
whole fleet's documentation is rotten," it's "two specific stations and five
specific shared-doc facts have drifted, and nothing would have caught it."

**Second finding, operator-directed (2026-09-11), widening the Dream:** the
content-correctness problem above is real, but it is not the whole complaint.
The operator's own framing: *"content is incorrect and outdated and
inconsistent, [and it] does not align to a standard or structure that people
are familiar with, e.g. Diátaxis — with just adaption / limited customization
to fit BMAD-METHOD and PyForge needs."* The general-facing documentation layer
this Dream scopes (`README.md`, `CLAUDE.md`, `AGENTS.md`, station `README.md`s,
`docs/reference/`, `docs/intake/`, onboarding/operational material) has no
recognizable information-architecture lens applied to it — a newcomer has no
Diátaxis-shaped map of "where do I start" vs. "how do I do X" vs. "what's the
exact config/CLI surface" vs. "why does this work this way." `docs/reference/`
already accidentally IS most of a Diátaxis "Reference" quadrant; nothing plays
the "Tutorials" (learning-oriented, get-something-running) or "How-to guides"
(task-oriented, operational) roles explicitly, so that content is scattered
across `README.md`'s "Common Commands," `docs/reference/developer-guide.md`,
and skill-scoped guides instead of living somewhere a newcomer would predict.

**This is explicitly an *adaptation*, not an import.** The BMAD spec-driven
tier — `docs/dreams/` (Tier 0), `docs/specs/` (Tier 1, legacy),
`_bmad-output/*/planning-artifacts/` (Tier 2), gitignored
`implementation-artifacts/` (Tier 3) — is Diátaxis-orthogonal: it is not
"documentation" in the sense Diátaxis addresses (explaining a working system
to its users), it is the spec-and-build pipeline itself, already coherent, and
explicitly out of scope for restructuring (see Non-goals). Diátaxis's four
quadrants apply only to the general/human-facing layer this Dream already
scoped in its first finding.

**What this Dream asks for, now in two parts:**

1. **Content correctness** (the original ask, unchanged): fix the confirmed
   instances (the 2 identity conflicts + 4 cross-cutting decay findings above),
   AND make it a repeatable capability rather than a one-off cleanup — a Doctor
   detector (or an extension of an existing one) that periodically
   cross-references what a station's README/skill-brief/Dream/AGENTS.md say
   against each other and flags a real divergence, the same discipline
   `capability-effect-verified` already applies to BMAD specs, applied one
   layer up to the general docs a human actually reads first.
2. **Structural adaptation** (new): reorganize the general-facing documentation
   layer only — `README.md`, `docs/reference/`, `docs/intake/`, and any
   onboarding/operational content currently scattered outside them — into a
   Diátaxis-shaped map (something like Tutorials/Getting Started, How-to
   Guides, Reference, Explanation), customized to this repo's real needs
   rather than a generic four-folder template. `docs/reference/`'s existing
   content is the seed of the Reference quadrant, not something to discard and
   rebuild. `CLAUDE.md` and `AGENTS.md` stay where they are (tool entry
   points, not general docs) but gain corrected, non-duplicated pointers into
   the reorganized structure. The downstream Spec (already drafted once
   against this Dream's narrower first version, now stale) needs re-deriving
   against this expanded scope before any restructuring work starts.

## Non-goals

- **The BMAD spec-driven tier is out of scope, full stop.** `docs/dreams/`,
  `docs/specs/` (legacy Tier 1), `_bmad-output/*/planning-artifacts/`, and
  gitignored `implementation-artifacts/` are not touched, moved, merged, or
  reorganized by this Dream — they are a different layer (the spec-and-build
  pipeline, not general documentation) with their own already-coherent
  convention, documented at length in this repo's own `CLAUDE.md`.
- **Diátaxis is adapted, not imported wholesale.** No generic
  `/docs/getting-started/` + `/docs/guides/` + `/docs/reference/` scaffold
  bolted on regardless of fit — the new structure grows from what's already
  here (`docs/reference/` survives as the Reference quadrant's home) and is
  sized to this repo's actual content volume, not a template's assumed shape.
- **Content is relocated and corrected, not regenerated.** Moving a file into
  the new structure and fixing a confirmed contradiction in it is in scope;
  rewriting accurate prose from scratch "for consistency" is not — the same
  surgical discipline as the original content-correctness finding, now applied
  to files that also move.
- Not a call graph or NLP-based "meaning" checker for the repeatable-detector
  half — matching Doctor's existing detectors' own discipline (bounded,
  textual, explainable, never a false green), not a heavier tool than the
  problem needs.

## Realization log

- **2026-09-11 (operator-directed widening)** — Scope expanded from
  content-correctness-only to include a Diátaxis-adapted restructure of the
  general-facing documentation layer, per the operator's own stated
  motivation (content is "incorrect and outdated and inconsistent" AND
  "does not align to a standard or structure that people are familiar with").
  The BMAD spec-driven tier stays explicitly out of scope (see Non-goals);
  this is an adaptation of Diátaxis to this repo's existing `docs/reference/`
  seed, not an import of a generic four-folder template. The Spec already
  drafted against this Dream's original, narrower version
  (`_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-general-docs-consistency/`)
  is now stale and needs re-deriving via `bmad-spec` against this widened
  Dream before any restructuring work starts.
- **2026-09-11 (later, same day)** — Spec re-derived via `bmad-spec` against
  the widened Dream (6 capabilities, self-validate PASS on both passes).
  Decomposed into doctor Epic 22 (Stories 22.1-22.6), minted `backlog`, per
  the operator's own request to get this Dream dispatch-ready for `marshal`.
  Status: dreamt → specified.
- **2026-09-11 (later, same session)** — Epic 22 drained 6/6, dispatched via
  `marshal factory dispatch`. Story 22.1: the two identity contradictions
  fixed at their source (`local-recipes#1251`). Story 22.2: the four
  cross-cutting decay findings corrected (`local-recipes#1253`). Story 22.3:
  the repeatable `general_docs_consistency` doctor detector, recovered from
  an orphaned dispatch session and finished by hand (`local-recipes#1254`).
  Story 22.4: the Diátaxis-adapted information architecture designed
  (`local-recipes#1252`). Story 22.5: the Tutorials/How-to quadrants
  populated (`local-recipes#1256`). Story 22.6: `README.md`/`CLAUDE.md`/
  `AGENTS.md` repointed into the reorganized structure (`local-recipes#1257`).
  All six capabilities in `spec-general-docs-consistency/SPEC.md` are done;
  the Spec and this Dream both close as `shipped`/`realized`. Status:
  `specified` → `realized`.
- **2026-09-14 (residue — leftover shelf)** — Epic 22 shipped the map
  (`docs/MAP.md`), the four quadrants, the identity detector, and entry-point
  pointers. A live shelf sweep the same day (operator + pass-2 fold analysis)
  found the **leftover class** that campaign's own Non-goals left on the
  table: dated `_bmad-output/` notes, intake dumps with no disposition
  frontmatter, three `workflow` files still living in legacy `docs/specs/`,
  marshal brownfield binders that tell humans and agents to read different
  pages, and air-gap / getting-started facts still copied in three places.
  That residue is **not a reopen of CAP-1..6**. It is the next campaign, seeded
  as [[docs-shelf-alignment]] (`docs/dreams/docs-shelf-alignment.md`, Spec
  `spec-docs-shelf-alignment`, `draft`). This Dream stays `realized` — the
  first campaign ran. The sibling owns fold, sunset-by-status, dual-audience
  indexes, and the repeatable check that the shelf does not grow back.

