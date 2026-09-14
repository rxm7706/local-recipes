---
spec: intelligence-hub
status: shipped   # 2026-09-14 -- steward Epic 53 (hub:CAP-1..4) is 5/5 stories done (53.1..53.5);
                  # CAP-5 stays mason lane, not this epic's completion criterion. Doctor's
                  # DEFERRED_SPECS entry already removed. Was `ready` since 2026-09-09 (operator,
                  # fleet-readiness decision batch § 2.3 C4 — the nine-answer bundle approved as
                  # one); that flip's own history is preserved below.
                  # 2026-09-09 (operator, fleet-readiness decision batch § 2.3 C4 — the nine-answer
                  # bundle approved as one). Was `draft` from 2026-09-05, when the Spec was seeded so
                  # the Dream's chain link was durable (dream-chain INV-1); RB-1/RB-2 closed
                  # 2026-09-06. All six declared open questions plus the three the Dream gained on
                  # 2026-09-09 are now answered and the shapes are chosen — see § Decisions.
                  # OWED TO DOCTOR in the same change (cross-station): de-register this Spec from
                  # `pyforge/doctor/sources/board.py` DEFERRED_SPECS. Its entry rationale is also
                  # factually wrong — it says NIC is absent, and `recipes/nebari-infrastructure-core`
                  # landed 2026-09-07.
                  # This flip is the precondition `spec-pyforge-unifying-strategy`'s own
                  # `realization-gate-home` question names: Epic 49 re-homes to `hub:CAP-*` once this
                  # Spec reaches `ready`.
updated: "2026-09-13"
owner-dream: docs/dreams/intelligence-hub.md
surface: []
companions:
  - vocabulary-map.md
  - later-caps.md
sources:
  - ../../../../../../docs/dreams/intelligence-hub.md
open_questions: []
  # ALL ANSWERED 2026-09-09 (operator, batch § 2.3 C4 bundle) — full text in § Decisions.
  # 2026-09-13 D4: Non-goals split — Community Frame, Frame registry, marketplace,
  # NIC-as-substrate, semantic-as-default, wholesale Scribe graph, nebi push, and
  # NebariApp template move to later-caps.md (adopt-anytime). CRC smoke stays a
  # Constraint. B9/B11 first nine Frames stay in-scope; registry is not a hard ban.
---

> **Canonical contract.** This SPEC and `vocabulary-map.md` are the complete contract for
> `docs/dreams/intelligence-hub.md`. As of **2026-09-09** the shapes are **chosen** and every open
> question is answered (§ Decisions), so downstream may bind to it. The two pre-Spec research items
> (RB-1, RB-2) closed on 2026-09-06; their findings live in the Dream's § Research backlog.

# SPEC — PyForge speaks the Intelligence Hub vocabulary deliberately

## Why

The whitepaper *The Distributed AI Economy* (Oliphant, August 2026, Rev 9) argues an
organisation should own its intelligence — context, AI workers, workflows, the checks on their
work and the evidence they leave, inside a perimeter it governs, built from shared abstractions
(Frames, Cogs, Ops, Guards, Gates, Tracks — six; Organizational Memory is tiered
separately by the paper as Layer-1 infrastructure, not a seventh peer. Corrected 2026-09-14). PyForge is already such a hub
in miniature: an owned factory on pixi + conda-forge, context in tracked files, workers as
station skills, workflows as bmad-loop runs, checks as detectors + Warden, evidence in ledgers.
It speaks that vocabulary by accident. This Spec exists to decide which of the paper's shapes
PyForge adopts, aligns to, or merely names — deliberately. One tension is carried, not assumed:
PyForge rents the model and the harness (Claude Code sits on the paper's rented-black-box list)
while owning the context, the workflows, the checks and the evidence — the split the paper says
matters most. Owner: **steward** (the estate) — settled 2026-09-09 (§ Decisions B6), with
`hub:CAP-3` (Track) relayed to marshal and the Frame-store half of CAP-2 relayed to scribe.

## Capabilities

*Chosen 2026-09-09 (§ Decisions). The reading of "align" is **reading 2** — adopt the artifact
model on the existing stack — with reading 1 (the vocabulary cross-walk) folded in because the
cross-walk is free. Reading 3 (NIC as substrate) is an **adopt-anytime later-cap** (D4,
2026-09-13), not a Non-goal and not Launch. All five CAPs below are in scope; none was dropped.
CAP-5 stays the mason lane — do not mint mason stories on the steward Hub epic.*

- **CAP-1 — Vocabulary alignment only.**
  - **intent:** the Charter's Lexicon and the station roster map once to the paper's six shared
    abstractions — Frames / Cogs / Ops / Guards / Gates / Tracks — plus Organizational Memory,
    which the paper tiers as Layer-1 infrastructure rather than a sixth peer and which is mapped
    here anyway because Scribe really does relay it. Recorded in `pyforge-charter.md` or the
    Unifying Strategy — the cheapest realisation; no code. *(Count corrected 2026-09-14; the
    mapping itself never changed.)*
  - **success:** every row of `vocabulary-map.md` names its Charter term and its gap, and the
    rented-model / owned-context tension is stated in the recording document.
- **CAP-2 — Frames as first-class** *(gate lifted 2026-09-06 — RB-1: Frame Spec v0.2.0 is
  published; single-file Markdown + YAML frontmatter; registries, identity and provenance out
  of its scope).*
  - **intent:** the repo's own context — the `AGENTS.md` verified block, the station personas —
    published as Frame-shaped artifacts with named accountable owners: **one Company Frame plus
    eight station Frames that `inherits` it, with git as the store** (decided 2026-09-09, B9/B11).
    A Community Frame and a Frame registry are **later-caps** (D4, 2026-09-13) — not this
    story's first nine Frames, and not a hard ban.
  - **success:** each artifact passes an **IN-REPO four-field preflight** implementing Frame Spec
    v0.2's required fields (`type`, `name`, `description`, `visibility`) and names its owner.
    Upstream's `tools/validate_frames.py` is an **optional cross-check only** — `openteams-ai/frame-spec`
    has no LICENSE file and no git tag (RB-1), so no acceptance criterion in this repo may depend
    on it. *(Contract fix 2026-09-09, B11.)*
- **CAP-3 — A declared validation strategy per run.**
  - **intent:** a bmad-loop run or `marshal factory spin` declares its Guards by stage, its
    Gates as threshold rules, and its Track contents + retention, so the several evidence files
    converge on one structured Track (landing-evidence grammar and durable-runs are the
    precedents it extends).
  - **success:** one run yields one structured Track record with enumerated fields and a stated
    retention; the Guards and Gates it ran are readable from the record, not inferred from
    policy TOML.
- **CAP-4 — Guards as a library.**
  - **intent:** detectors, Warden axes and review lenses exposed as reusable Guards, each with a
    declared category from the paper's seven.
  - **success:** a Spec can name which Guard categories it lacks; Warden stays the sole PR
    verdict and doctor stays advisory — no Guard mints a second verdict.
- **CAP-5 — Package the Nebari / Nebi lineage where missing** *(narrowed 2026-09-06 — RB-2:
  `nebari` 2025.10.1 and `nebi` 0.15 are already on conda-forge and are consumed as-is).*
  - **intent:** a Mason / `conda-forge-expert` lane builds local recipes for what is actually
    missing — `nebari-infrastructure-core` (Go, Apache-2.0, v0.14.0; GitHub-release binaries and
    a Homebrew cask only) and, if the registry is adopted, the `frames` client (Go, Apache-2.0,
    v0.1.7) — in the Go-source shape `nebi-feedstock` already uses.
  - **success:** a green local build ends the task; nothing is re-packaged that conda-forge
    already ships; no external PR without an ask.

## Constraints

- **Dream-first.** No code from the seed; this Spec chooses among CAP-1..5 before any code.
  *(Satisfied 2026-09-09 — the shapes are chosen; see § Decisions.)*
- **Any `hub:` NIC-profile story is GATED on the first green `ocp-portability-smoke` run.** The
  OCP profile is already a profile by construction (`pap:AD-11` keeps the core chart unchanged and
  confines OCP specifics to `overlays/ocp/`), so a NIC overlay would sit beside it cleanly — but
  the OCP profile has never been proven on a cluster, and two unproven profiles side by side
  double the claim with zero evidence. Steward's first-green funding decision
  (`spec-ocp-as-a-portability-profile`, batch C14) is therefore the prerequisite for the Dream's
  shape 6, not a separate errand.
- **An external vocabulary is cross-walked and NEVER enters the seven Lexicon terms.** The
  Charter's CAP-4 ruling (guild-E3): the Hub vocabulary maps to the Lexicon, it does not join it.
- **The whitepaper is the source of record.** No claim the paper does not make; re-verify any
  statistic or vendor fact at intake; cite later revisions by tag from
  `openteams-ai/inthub-whitepaper` (Revision 9 = `v9`), never by PDF URL alone.
- **Copyright.** Distilled in our words with short attributed quotations; the PDF is not tracked.
- **Foundry invariants stand.** `src/platform/` never imports `pyforge.*`; the infra-kinds lock
  and AD-1 (re-affirmed 2026-09-05) are untouched; the paper's Organizational Memory menu is its
  menu, not a licence to add stores to the platform.
- **One PR verdict.** Warden stays the sole gate; doctor findings stay advisory; "Guard" language
  must not mint a second verdict.
- **No implied platform adoption.** Naming Nebari / Nebi adopts nothing; the Unifying Strategy
  owns the platform shape.
- **No new `docs/specs/` file; no external PRs; no outward dispatch without operator
  confirmation.**

## Non-goals

- Replacing the Foundry with a Nebari deployment.
- Replacing `conda-forge-expert` with anything.
- Endorsing or marketing OpenTeams — an architecture-and-vocabulary seed only.
- Reproducing the whitepaper; readers who need the text go to the source.
- **Submitting `nebari-infrastructure-core` or `nebari-frames` to conda-forge** *(2026-09-09,
  B10 — "not now"; D2/D4 keep)*. Revisit on first real consumption. Local recipes stay mason
  lane; green local build ends the task; no external PR without an ask.
- Re-packaging `nebari` or `nebi` — both are on conda-forge (RB-2); version bumps there are
  PRs to feedstocks rxm7706 does not maintain, not this chain's work.
- Building a Desktop / Web Application as a product replacement.

*Moved 2026-09-13 (D4) to `later-caps.md` (adopt-anytime, may land before or after 44.3):
Community Frame, Frame registry, Skills/Agent Marketplace, NIC-as-substrate, semantic-as-default,
wholesale docs/recipes in the Scribe graph, `nebi push`, `NebariApp` template. Not Launch.*

## Success signal

*Reached 2026-09-09 for the choosing half:* the operator has chosen among CAP-1..5 (each choice a
memlog decision; nothing dropped silently — later readings live in `later-caps.md` after D4), RB-1
and RB-2 closed in the Dream with dated evidence (2026-09-06), every remaining question is
answered, and this Spec is `ready` — so it leaves doctor's `DEFERRED_SPECS` and decomposes into
steward epics. D4 (2026-09-13) re-derived Non-goals vs later-caps without flipping Epic 44.

*The signal that remains:* the Charter carries the vocabulary cross-walk and its reverse block;
one Company Frame plus eight station Frames pass the in-repo four-field preflight; one bmad-loop
run emits one tracked `track.json` with its enumerated fields and stated retention; and a Spec can
name which Guard categories it lacks, with source-grounding running on dev/review output rather
than at one site.

## Assumptions

- Owner `steward` — **settled 2026-09-09 (B6)**, no longer an assumption; marshal and scribe hold
  relays, never the Lexicon amendment.
- The candidate shapes are independent; more than one may be chosen, and CAP-1 may be chosen
  alone. *(All five were chosen.)*
- Frame Spec v0.2 stays a single-file format (its directory form is deferred) and its repository
  stays licence-less until upstream says otherwise; conformant documents can be authored
  regardless, and the spec text itself is never vendored here.
- `nebari-feedstock` and `nebi-feedstock` stay maintained by nebari-dev people; rxm7706 is not a
  maintainer on either, so any bump there is a reviewed PR, never a push.

## Decisions — 2026-09-09

Nine answers, approved by the operator as one bundle (`fleet-readiness-decision-batch-2026-09-09.md`
§ 2.3 C4). They flip this Spec `draft → ready`.

**B6 — Owner: STEWARD stays owner.** `hub:CAP-3` (Track) relays to marshal; the Frame-store half of
CAP-2 relays to scribe. The alignment work is a Charter/Unifying amendment plus a deploy profile,
and both are steward surfaces (`spec-pyforge-unifying-strategy` is steward's — `SPEC.md:21` carries
the `extends:`; an NIC profile would land beside `steward/deploy_profiles.py`). Same
one-owner-plus-relays shape already proven at eight stations by `spec-bmad-suite-lifecycle`. Marshal
owns the Ops/Gates mechanics and scribe Organizational Memory **as relays, never as owners of the
Lexicon amendment**.

**B7 — Missing Guard categories: exactly TWO of the paper's seven.**

- **Source-Grounding** exists at exactly one site — `scribe/recall.py` AD-8, "no code path may
  return synthesized prose without a resolvable citation" — and **nowhere on the dev/review output
  that actually lands code**.
- **Outcome** is absent entirely (eval-quality's catch rate is a Guard on a Guard, not an Outcome
  Guard).

The other five map to live surfaces: Algorithmic = the ~30 `*-check` detectors + warden's verdict
lattice; Consensus = the parallel review lenses; Expert = `gate_mode` + the operator-confirmation
lines at `AGENTS.md:29-30`; Policy & Safety = warden license/vuln/waiver + marshal's 14 MRS-GATEs;
Regression & Drift = `bmad-drift-check`, `spec_surface_check.py`, doctor's `frozen_path.py`.
**SOURCE-GROUNDING GOES FIRST** — a working in-repo pattern exists to copy (AD-8), the repo's own
memory names the failure it prevents, and Outcome Guards are blocked on `build-league-scorecard`'s
measure set (batch C13).

**B8 — Track + retention: a bmad-loop run does NOT yet constitute a Track.** Enough content, wrong
shape and wrong place. A run emits `journal.jsonl`, a gate record (`gate-record.json`),
`state.json`, `session.log` and `dispatch-supervisor.log`, all under a Tier-3 **gitignored**
`dispatch-runs/<run>/` dir — roughly 60 % of the paper's Track field list (the Op run,
Guards-as-commands with results, the Gate verdict, timestamps, tree revision), missing
model/adapter version and config, human approvals/overrides, and any retention statement anywhere
in the repo. **Decision: assemble ONE TRACKED `track.json` per run** from what already exists plus
those three field groups; keep the **Track indefinitely** and the **raw payload 90 days**. Marshal
supplies the field enumeration (relay). Evidence in a gitignored tree is the same failure that lost
13 warden story specs to worktree teardown.

**B9 — Publish the repo's context as Frames: YES, minimally and privately.** One Company Frame
derived from the `AGENTS.md` verified block, plus eight station Frames that `inherits` it, with
**git as the store**. Community Frame and registry are **later-caps** after D4 (2026-09-13), not
this story's first nine Frames. Conformance is four frontmatter fields with a free-form body
(frame-spec PR #25, merged 2026-09-07), and the eight `bmad-agent-<station>` persona `SKILL.md`
files already are that shape. **Prerequisite: refresh the `AGENTS.md` managed block via
`bmad-project-context` first** — it is stamped "Verified 2026-09-06 against `99e595cc6a`" and
main is `fe4025ea90`.

**B10 — Package NIC / the frames client: the question was STALE AS WRITTEN**, and is rewritten
before it is answered. Both recipes landed 2026-09-07, two days before the Dream recorded the lane:
`recipes/nebari-infrastructure-core/recipe.yaml:5` (0.14.0, `dd7c4e7eb7`) and
`recipes/nebari-frames/recipe.yaml:5` (0.1.7, `3469ee97cb`). Rewritten as *"when, if ever, do NIC
and nebari-frames go to conda-forge?"* and answered **NOT NOW**: NIC's own README says "under heavy
development and very unstable … not yet suitable for production", rxm7706 maintains neither
neighbouring feedstock, nothing in the estate consumes either recipe, and an external PR needs an
explicit ask (`AGENTS.md:28`). **Trigger for revisiting: first real consumption.**

**B11 — Author the first `.frame.md` now or after the shape decision: NOW.** It is the same work as
B9 and one of the few moves the cutover does not penalise — the Dream's own A→B→C sequence puts
Frames in the "now" column precisely because Dreams and memlogs are re-derived into the foundry,
not migrated. Cost is a frontmatter block over text that already exists plus a ~30-line four-field
check. **Contract fix in the same ruling:** CAP-2's success must not bind to upstream's unlicensed
`tools/validate_frames.py` — rewritten to the in-repo preflight (see CAP-2).

**D-1 — Which reading of "align": READING 2** (adopt the artifact model on the existing stack) with
reading 1 (the vocabulary cross-walk) folded in, because the cross-walk is free. **Reading 3** (NIC
as substrate) is an adopt-anytime later-cap (D4), not a Non-goal.

**D-2 — `NebariApp` template: later-cap, not Launch** (D4). The chart's Ingress/Route stays
primary (`pap:AD-11`). A NIC **kind profile** still requires the first green
`ocp-portability-smoke` run — see § Constraints (not a Non-goal).

**D-3 — `nebi push`: later-cap, not Launch** (D4) — still not the Launch campaign.

**D4 — 2026-09-13 Non-goals split.** True Non-goals stay the D2 bans (no Foundry←Nebari
replacement, no CFE replacement, no OpenTeams marketing, no whitepaper reproduction, no
conda-forge PRs for NIC/frames). Adopt-anytime later-caps: Community Frame, Frame registry,
Skills/Agent Marketplace, NIC-as-substrate, semantic-as-default, wholesale docs/recipes in the
Scribe graph, `nebi push`, `NebariApp` template.

**guild-E3 — Charter amendment shape for CAP-1:** close the "or the Unifying Strategy" branch **in
the Charter's favour** — the vocabulary map lands in `pyforge-charter.md`, not the Unifying
Strategy. Add the **reverse cross-walk block** (three Lexicon nouns with no Hub counterpart; the
Cogs collision), and carry an explicit **CAP-4 ruling** that an external vocabulary is cross-walked
and never enters the seven Lexicon terms.
