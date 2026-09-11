---
id: SPEC-general-docs-consistency
status: ready
owner-dream: docs/dreams/general-docs-consistency.md
companions: []
sources:
  - ../../../../../../docs/dreams/general-docs-consistency.md
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate. The source Dream is for traceability — consult it only for narrative rationale this contract intentionally omits.

# General documentation stops contradicting itself, and stays that way

## Why

**A pain to solve, in two parts.** Doctor already runs real hygiene detectors
(`capability-effect-verified`, `status-body-consistency`, `sibling-dreams-drift`,
`dreams-hygiene`) that catch a claim which used to be true and silently isn't
anymore — but only inside BMAD-tier planning artifacts. A live two-pass audit
this session (2026-09-11) proved the same failure mode reaches the
general, human-facing documentation layer nothing watches: `README.md`,
`CLAUDE.md`, `AGENTS.md`, and station `README.md`s/`skill-brief.yaml`s
contradict each other and, in two places, contradict themselves.

A second, operator-directed finding (2026-09-11) widened the scope: that
content-correctness gap isn't the whole complaint. The layer also has no
recognizable information architecture — a newcomer has no map distinguishing
"where do I start," "how do I do X," "what's the exact config/CLI surface,"
and "why does this work this way." `docs/reference/` already accidentally
covers most of a Diátaxis "Reference" quadrant; nothing plays the Tutorials or
How-to-Guides role explicitly, so that content is scattered instead of living
somewhere a newcomer would predict. This half is an *adaptation* of Diátaxis
to what's already here, not an import of a generic template — and it is
scoped to the general-facing layer only. The BMAD spec-driven tier
(`docs/dreams/`, `docs/specs/` legacy, `_bmad-output/*/planning-artifacts/`,
gitignored `implementation-artifacts/`) is a different layer — the
spec-and-build pipeline, already coherent — and stays untouched by either
half of this Spec.

## Capabilities

- **CAP-1**
  - **intent:** Every authoritative source that describes what Doctor is and
    what Herald owns agrees with itself. Doctor's `README.md` currently claims
    "its own exit-code gate," contradicting `skill-brief.yaml`/`CLAUDE.md`/
    `AGENTS.md`'s "advisory — not a second PR gate." `AGENTS.md` currently
    assigns Herald "keeping the Dream → spec handoff portable across agents,"
    contradicting Herald's own Dream, which explicitly assigns that
    responsibility to Marshal (citing a dated ownership review).
  - **success:** `pyforge-doctor/README.md` no longer uses gate language for
    itself; it matches the "advisory" framing everywhere else. `AGENTS.md`'s
    cross-agent-portability claim names Marshal (or is reworded so it makes no
    ownership claim at all), matching `docs/dreams/pyforge-herald.md`.

- **CAP-2**
  - **intent:** The four confirmed decay findings in the repo's two
    highest-visibility docs are corrected. `README.md`'s "GitHub Actions
    Workflows" section lists 4 of 19 real workflow files and claims CI is
    "manual trigger only," false for the automatic PR-gate workflows it omits.
    `README.md`'s own project-structure tree cites `docs/bmad-setup-plan.md`
    and `docs/developer-guide.md`, neither of which exists at those paths,
    while the same file's own prose elsewhere cites the correct paths. The
    active-project-resolution-priority list is duplicated verbatim in
    `README.md` and `CLAUDE.md`, with `CLAUDE.md`'s copy substantially
    richer. `CLAUDE.md` names 8 PyForge Guild stations in one place and "7
    skills" (silently omitting Mason) in its own SKF Skills block.
  - **success:** `README.md`'s workflow section accurately distinguishes the
    automatic PR-gate workflows from the on-demand/manual ones, against the
    real `.github/workflows/*.yml` trigger types. `README.md`'s tree cites
    only paths that exist. The priority list exists in exactly one place
    (`CLAUDE.md`), with `README.md` pointing to it rather than duplicating it.
    `CLAUDE.md`'s SKF block and its 8-station list agree, with Mason's
    deliberate skill-omission noted rather than silent.

- **CAP-3**
  - **intent:** This class of drift gets a repeatable detector instead of
    staying a one-off manual catch. A Doctor detector (new, or an extension of
    an existing `sources/` module) cross-references a station's
    `README.md`/`skill-brief.yaml`/Dream/`AGENTS.md` claims against each other
    and names a real divergence — the same discipline
    `capability-effect-verified` already applies to BMAD specs, one layer up.
  - **success:** The detector runs, is warn-only and fail-open (matches
    Doctor's existing hygiene-check contract, never a second PR gate), and
    fires against at least the Doctor/Herald cases that motivated this Spec
    when replayed as fixtures — plus a clean-station fixture that proves it
    does not false-positive on consistent sources.

- **CAP-4**
  - **intent:** Design and adopt a Diátaxis-adapted information architecture
    for the general-facing documentation layer (`README.md`, `docs/reference/`,
    `docs/intake/`, scattered onboarding/operational content), explicitly
    excluding the BMAD spec-driven tier.
  - **success:** A documented map exists naming four quadrants —
    Tutorials/Getting-Started, How-to Guides, Reference, and Explanation.
    `docs/reference/`'s existing content is preserved but split by kind: true
    reference material (config/CLI/schema specs) stays in the Reference
    quadrant; architecture-rationale/"why this works this way" content (e.g.
    `mcp-server-architecture.md`'s design reasoning,
    `enterprise-deployment.md`'s rationale) moves to the new Explanation
    quadrant. Files are relocated and split by kind, not rewritten from
    scratch. The BMAD spec-driven tier (`docs/dreams/`, `docs/specs/` legacy,
    `_bmad-output/*/planning-artifacts/`, `implementation-artifacts/`) is
    untouched by the map.

- **CAP-5**
  - **intent:** Give the general-facing docs layer a discoverable
    Tutorials/Getting-Started path and a discoverable How-to-Guides path —
    both currently absent as named destinations, with their content scattered
    across `README.md`'s Common Commands, `docs/reference/developer-guide.md`,
    and skill-scoped guides.
  - **success:** A newcomer with no prior context can find one place to get a
    working environment running (Tutorials/Getting Started) and one place to
    find task-oriented operational instructions (How-to Guides). The content
    populating both is relocated/corrected existing material, not rewritten
    from scratch.

- **CAP-6**
  - **intent:** `README.md`, `CLAUDE.md`, and `AGENTS.md` point cleanly into
    the reorganized general-docs structure instead of duplicating or going
    stale against it.
  - **success:** No internal link into the reorganized structure is broken.
    No fact that lives in the new structure is also duplicated verbatim in
    `README.md`/`CLAUDE.md`/`AGENTS.md` without one side pointing to the
    other — the same discipline CAP-2 already applies, now applied to the new
    structure.

## Constraints

- No documentation restructuring **for CAP-1..3** — those fixes touch only
  the lines the confirmed findings name.
- Surgical fixes only for CAP-1/CAP-2 — no wholesale rewrite of `README.md`,
  `CLAUDE.md`, or `AGENTS.md` beyond the confirmed findings.
- CAP-3's detector stays bounded, textual, and explainable, matching Doctor's
  existing hygiene checks — never a heavier NLP/semantic tool than the
  problem needs, and never itself a second PR gate.
- CAP-3's findings must be evidence-based, quoting both sides directly —
  never an inferred or invented contradiction (matches
  `capability-effect-verified`'s own discipline).
- CAP-4..6: the BMAD spec-driven tier (`docs/dreams/`, `docs/specs/` legacy
  Tier 1, `_bmad-output/*/planning-artifacts/`, gitignored
  `implementation-artifacts/`) is out of scope, full stop — not touched,
  moved, merged, or reorganized.
- CAP-4..6: Diátaxis is adapted, not imported wholesale — no generic
  `/docs/getting-started` + `/docs/guides` + `/docs/reference` scaffold
  bolted on regardless of fit. The structure grows from what's already here;
  `docs/reference/` survives as the Reference quadrant's home, sized to this
  repo's actual content volume.
- CAP-4..6: content is relocated and corrected, not regenerated — moving a
  file into the new structure and fixing a confirmed contradiction in it is
  in scope; rewriting accurate prose from scratch "for consistency" is not.

## Non-goals

- A full editorial pass of every document in the repo. Scope is the 6
  confirmed CAP-1/CAP-2 findings, the CAP-3 detector, and the CAP-4..6
  structural adaptation — not an open-ended sweep.
- Re-auditing the 6 stations a light pass already found clean this session
  (atlas, marshal, mason, scribe, steward, warden).
- Refreshing `docs/reference/*.md`'s 5 already-known self-flagged-stale files
  (`github-workflows.md`, `station-verify-commands.md`,
  `enterprise-deployment.md`, `mcp-server-architecture.md`,
  `library-llms-full.md`) — a separate, already-tracked issue.

## Success signal

`pyforge-doctor/README.md`, `skill-brief.yaml`, `CLAUDE.md`, and `AGENTS.md`
all describe Doctor identically (advisory, never a gate); `AGENTS.md`'s Herald
claim matches Herald's own Dream; `README.md`'s workflow section and
project-structure tree are both accurate against the live repo; the
active-project-priority fact lives in one place; `CLAUDE.md`'s station count
and skill count agree. A new Doctor detector, run against the fixtures this
Spec's own motivating findings provide, catches them and does not
false-positive on a clean station. Separately: the general-facing docs layer
has a documented, Diátaxis-adapted map that a newcomer can navigate across all
four quadrants (Tutorials, How-to, Reference, Explanation); `docs/reference/`'s
content is relocated intact, split by kind between the Reference and
Explanation homes; `README.md`/`CLAUDE.md`/`AGENTS.md` link into the map
without duplicating it; the BMAD spec-driven tier is provably untouched by
every change this Spec makes.

## Assumptions

- Mason's own missing `.claude/skills/pyforge-mason/` directory is confirmed
  deliberate policy (`AGENTS.md:31`, wrapped in a
  `governance-currency:ignore` marker) — CAP-2's `CLAUDE.md` fix documents
  this rather than adding a skill for Mason.
