---
title: "Vocabulary — three-source reconciliation (BMAD-METHOD × PyForge Lexicon × Intelligence Hub)"
chain: "vocabulary-one-name-one-job"
created: "2026-09-14"
type: research
owner: steward
head: 445976e5be
status: draft   # research input for the Dream seed; no decision taken here
---

# Vocabulary — where three vocabularies meet, and where they disagree

**Why this exists.** PyForge now carries three vocabularies at once: BMAD-METHOD's upstream
terms, our own Lexicon and its derived artifact statuses, and the Intelligence Hub / Frame-spec
terms we began adopting 2026-09-13 (steward Epic 53). Nobody has ever compared all three in one
pass. This document records what each actually says — measured, not remembered — so a Dream can
decide what to standardize. **It takes no decision itself.**

**Method.** Three parallel read-only passes on 2026-09-14 against `main` `445976e5be`:
(1) a live inventory of this repo's own vocabulary, measured with the real parsers, not regex;
(2) upstream BMAD-METHOD at tag **v6.12.0**, shallow-cloned and grepped exhaustively;
(3) OpenTeams' `inthub-whitepaper` (tag `v9`), `frame-spec`, and `ownyourintelligence.ai`.
Every claim below cites where it was read. Where our own records turned out to be **wrong**,
that is called out explicitly — those corrections are the most load-bearing findings here.

---

## 1. The governing rule we already have

The Lexicon states its own design rule twice, in the Design-side poster and the worked example
(Design project `f58c0f17`, `Lexicon Poster.dc.html` / `Lexicon to PyForge.dc.html`):

> **Every noun does exactly one job; every job has exactly one noun.**

The seven Lexicon nouns, each a *unit of*: **Charter** (legitimacy) → **Spec** (contract) →
**Guild** (body) → **Smiths** (identity) → **Stations** (accountability) → **Skills**
(execution) → **Guildhall** (accountability made real). Forward = authorization, backward =
audit: *every artifact traces to a Spec, every Spec to a Dream, every Dream to the Charter.*

That rule is the yardstick for everything below. Note what it exposes immediately: **"Dream" is
not one of the seven nouns**, yet it is the Tier-0 entry point of the flow and the single most
numerous artifact we have (163 files). The Charter itself *is* a Dream
(`docs/dreams/pyforge-charter.md`). So Dream is the container format and Charter is a
distinguished instance of it — a relationship the Lexicon never states.

---

## 2. CORRECTION — the Hub has SIX shared abstractions, not seven

**Our Charter is factually wrong, and the error propagated.**

`docs/dreams/pyforge-charter.md:606` reads: *"The whitepaper names Frames · Cogs · Ops · Guards ·
Gates · Tracks · Organizational Memory."* Three independent upstream sources say six:

- `openteams-ai/inthub-whitepaper` README: *"the shared abstractions (Frames, Cogs, Ops, Guards,
  Gates, Tracks) that let many parties build to it"*
- The guide's glossary, entry **Shared abstraction**: *"Frames, Cogs, Ops, Guards, Gates, and
  Tracks are proposed as the AI era's set"* (https://ownyourintelligence.ai/glossary/)
- Guide §13: *"Shared abstractions ask it to adopt **six nouns**"*
  (https://ownyourintelligence.ai/guide/drawing-the-stack/)

The canonical mnemonic (whitepaper `GLOSSARY.md`, which self-declares as *"the authoritative
definition set"*): **"Frames guide the work. Cogs perform the work. Ops orchestrate the work.
Guards verify the work. Gates decide whether the work proceeds. Tracks make the work
accountable."**

**Organizational Memory is real vocabulary but a different tier** — Layer-1 *infrastructure*
("the Hub's persistent context substrate"), alongside Intelligence Hub / Nebari / Nebi — not one
of the six execution/accountability abstractions. Flattening it into the six erases a
distinction OpenTeams draws deliberately. The architecture is *three layers plus a cross-cutting
Accountability Plane (Guards/Gates/Tracks)* — explicitly "never 'four layers'".

**Blast radius of the error — three places, one of them Tier-0:**

| File | Line | Reads |
|---|---|---|
| `docs/dreams/pyforge-charter.md` | 606 | seven names, incl. Organizational Memory |
| `spec-intelligence-hub/SPEC.md` | 48, 68 | same seven, in § Why and CAP-1 intent |
| `spec-intelligence-hub/vocabulary-map.md` | table | Organizational Memory as a peer row |

The Charter is Tier 0 and changes *only by recorded amendment*, so this is an amendment, not an
edit. Note the substantive ruling it carries (cross-walked, never joins; the Cogs/Smith collision
named; Charter·Guild·Stations have no Hub counterpart) is **unaffected** — only the enumeration
is wrong.

**Also corrected: Guard category order.** The seven categories are right, the order is not.
Whitepaper §5.5 "Seven Categories of Guards", canonical order and Title Case:
**1 Algorithmic · 2 Source-Grounding · 3 Consensus · 4 Expert · 5 Policy & Safety ·
6 Regression & Drift · 7 Outcome.** We recorded Source-Grounding sixth
(`spec-intelligence-hub/SPEC.md:192-199`). Our *substantive* B7 finding — that Source-Grounding
exists at exactly one site and Outcome is absent — stands; only the ordinal was wrong. That
matters because "Source-Grounding goes first" is upstream's own ranking, not just our preference.

---

## 3. BMAD-METHOD's vocabulary — what is actually prescribed

Upstream at **v6.12.0**. Caution recorded for future readers: our installed copy under
`.claude/skills/bmad-*` is **not pristine** — `sprint_plan.py` carries local patches
(`f527e526f0`, `6ba6bd9eb6`). Everything here is upstream.

### 3.1 Four status vocabularies, exact literals

`src/bmm-skills/plan/bmad-sprint-planning/scripts/sprint_plan.py` L59-65:

```python
STORY_RANK  = {"backlog": 0, "ready-for-dev": 1, "in-progress": 2, "review": 3, "done": 4}
EPIC_RANK   = {"backlog": 0, "in-progress": 1, "done": 2}
RETRO_RANK  = {"optional": 0, "done": 1}
ACTION_STATUSES = ("open", "in-progress", "done")
```

Story-spec frontmatter is a fifth, separate lattice
(`bmad-build/spec-template.md` L5): `draft | ready-for-dev | in-progress | in-review | done`,
plus `blocked` in `bmad-build-auto`. **Upstream carries its own inconsistency**: the sprint file
says `review`, the story spec says `in-review` — same concept, two spellings.

### 3.2 The decisive negatives

- **`SPEC.md` has no `status` field upstream, at all.** Its frontmatter is only `id`,
  `companions`, `sources` (`bmad-spec/assets/spec-template.md`). Our eight Spec statuses are
  **100% local invention**.
- **`stories.yaml` bans status outright** — `stories-schema.md` § Validity rules, rule 3,
  verbatim: *"No `status` field, ever."*
- **Epic files carry no status**; status lives only in `sprint-status.yaml`.
- **`shipped` is upstream's canonical *illegal* value.** `test_sprint_plan.py::
  test_illegal_existing_status_warns_and_resets` asserts a `shipped` value is warned on and
  **reset to `backlog`**. It is our single most-used Spec status (67 of 163).
- **`blocked` is not upstream** in sprint-status; our copy added it (`f527e526f0`).
- **"Dream" does not exist in BMAD-METHOD.** Grepped all of `src/`, `docs/`, `README.md` at
  v6.12.0 — only the brainstorming technique "Dream Fusion Laboratory" and incidental prose.
  Dream is entirely ours.
- **There is no extension point for status vocabulary.** `customize-bmad` exposes activation
  steps, persistent facts, lenses, review layers — never statuses. `sprint_plan.py` hard-codes
  the ranks and **silently resets** unrecognized values to the computed one. That fail-open
  reset is precisely what our local `STICKY_STATUSES` patch was written to defeat.

### 3.3 Our ledger is more conformant than it looked

Measured fleet-wide, our `sprint-status-ledger.yaml` uses five values:
`done` 1122 · `optional` 183 · `backlog` 16 · `blocked` 13 · `in-progress` 5.

Read against upstream's *two* lattices this is mostly correct, not sprawl: `done`/`backlog`/
`in-progress` are the story lattice, and `optional` is the **retrospective** lattice applied
exactly where it belongs (`epic-N-retrospective` rows). Only **`blocked` is net-new local**, and
we never use upstream's `ready-for-dev` or `review` at all. Our filename also differs —
`sprint-status-ledger.yaml` vs upstream `sprint-status.yaml`.

---

## 4. Our own vocabulary — measured current state

### 4.1 Four status vocabularies, one declared

| Vocabulary | Values in live use | Declared where? |
|---|---|---|
| **Dream** | `realized` 61 · `specified` 58 · `archived` 37 · `dreamt` 7 | ✅ `docs/dreams/README.md:63-104`, with rationale + rejected alternatives |
| **Spec** | `shipped` 67 · `ready` 43 · `archived` 20 · `in-progress` 16 · `draft` 7 · `absorbed` 5 · `extension-point` 3 · `superseded` 2 | ❌ **nowhere** — only `extension-point` is defined, and that in the *Dream* README |
| **Ledger** | `done` 1122 · `optional` 183 · `backlog` 16 · `blocked` 13 · `in-progress` 5 | ❌ nowhere (upstream-derived; see 3.3) |
| **Doctor code** | `OPEN_SPEC_STATUSES`, `DELIVERED_SPEC_STATUSES`, `TERMINAL_STATUSES`, `_STATUSES_REQUIRING_REALIZATION_LOG`, `_SPEC_READY_FOR_SPECIFIED` | ⚠️ implicit, scattered across `board.py` / `chain.py` / `status_body_consistency.py` |

`guild-roster.json` declares a fifth Dream status, **`pitched`**, that no live Dream uses.

### 4.2 The Dream ladder is principled — and the principle is the transferable asset

`docs/dreams/README.md:63-104` is the only place any of our vocabularies states a *rule*:

- **"each state names the act that completed, never the artifact that proves it"** — and it was
  renamed 2026-07-25 from `seeded`/`in-deck`/`in-spec` precisely because those "named a file or
  a place rather than a state".
- **`specified` requires a Spec at `ready` or beyond**, not merely a Spec that exists.
- **`extension-point` is the Spec-side sibling of `dreamt`** — a parked contract nothing can bind
  to; a Dream whose only Spec is `extension-point` reads `dreamt`, never `specified`.
  *(This corrects an assessment made earlier the same day that called `extension-point` a
  category error. It is not — it is deliberate and documented.)*
- **Status is not a proxy for work remaining, in either direction — the ledger is.**
- **There is deliberately no `building` state.** Status declares what *exists*; the console
  *derives* what is happening. A `building` status was considered and rejected because it goes
  stale the moment a line pauses.

The Spec vocabulary has no equivalent statement — and `in-progress` (16 live Specs) is exactly
the "what is happening" shape the Dream side deliberately rejected.

### 4.3 A recurring, three-times-repeated failure

`docs/dreams/README.md:90-98` records `bmad-module-provisioning` and `unified-container` both
reading `dreamt` while their epics were 3/3 and 5/5 done and merged. On 2026-09-14
`intelligence-hub` was found reading `dreamt` while steward Epic 53 was 5/5 done — the **third**
instance of one class, each hand-fixed. The same pass found `platform-image-one-pixi-env` and
`mcp-era-isolation` reading `specified` against `shipped` Specs.

Related structural gaps found in the same audit (detector-side, recorded here because they are
vocabulary-shaped):

- `board.py` INV-A skipped **every** non-open Spec status, so a `shipped` Spec with no epic was
  invisible; ten such Specs existed fleet-wide.
- `board.py` INV-B discards every `epic-*` key before comparing, so epic-level rows are never
  checked against `## Epic N` headings — `pyforge-steward` `epic-18` and `pyforge-marshal`
  `epic-29` are live orphans, and `fleet-picture` counts epics from exactly those keys.

---

## 5. Frame Spec — what we built on, and the risk we carry

- **Released version is v0.2.0 (2026-08-18).** Required frontmatter is exactly
  `type`, `name`, `description`, `visibility` — our record of this is **correct** and is
  enforced by upstream's `tools/validate_frames.py`. Recommended optional: `version`, `scope`,
  `maintainer`, `inherits`. **`owner` never existed** (it is `maintainer`, renamed from `author`
  by merged PR #20); **`identifier` and `license` exist only in the v0.3 draft.**
- **`frame-spec` has no LICENSE on `main` today.** `GET /repos/openteams-ai/frame-spec/license`
  → 404; the repo's `license` field is `null`. **PR #28**, which adds Apache-2.0 and the v0.3
  data model, is **still OPEN** (created 2026-09-07). PR #29 (reference validator) is open and
  targets #28's branch. PR #25 merged 2026-09-07 as we recorded.
- **v0.2.0 has no git tag and no GitHub release** — the README's advertised release link is dead.
- **Our nine Frames are authored against the unmerged draft**: they carry `type: frame [0.3]`,
  `identifier:`, and an Apache-2.0 `license:` IRI — all v0.3-only fields, from a PR that has not
  landed, in a repo that currently grants no rights. Story 53.5 accepted this knowingly ("we
  adjust when #28 / #29 merge"); this pass confirms **#28 has still not merged**.
- **Frame v0.3 draft is the first place a status registry appears**: `draft`, `review`,
  `approved`, `deprecated`, `revoked` — **recommended, not required**, with a rule that a reader
  *must preserve* an unregistered value and *must not reject* a Frame for carrying one. Upstream
  chose that because requiring them "would have made nine of this repository's own examples
  invalid" — the identical problem our own 8-value Spec vocabulary presents.
- **Only Frames have a written spec.** `docs/ecosystem.md`: *"no Cog spec exists yet"*. No Op,
  Guard, or Track spec exists — everything else is whitepaper prose.

**Track field list** (whitepaper §5.3 / §5.6 manifest) — directly usable for Story 53.3's
`track.json`: Op run · Cogs invoked · Frames applied · input data and source references · model
versions and configuration · Guards executed with results and confidence · Gates
passed/failed/escalated · human approvals, edits, overrides · final outputs or actions ·
timestamps, user identity, permissions, environment · links to Organizational Memory entries.

---

## 5b. The Design tier — a fourth vocabulary, recorded but never practised

The three Design artifacts in project `f58c0f17` are not just renderings of the Lexicon; the
45-slide deck **teaches a whole practice vocabulary that never entered `vocabulary-map.md`, the
Charter cross-walk, or any repo-side glossary.** Two distinct problems.

### 5b.1 Vocabulary taught in Design, absent from every repo vocabulary artifact

From `Agentic SDLC.marp.md` (local copy, `presentations/agentic-sdlc/project/`):

| Term taught | Slide | Where it lives in repo vocabulary |
|---|---|---|
| **Four phases** (analysis · planning · solutioning · implementation) | "Four phases, one throughline" | nowhere — and upstream 6.12 now says *"These are independent tools, **not stages**"* |
| **Three tracks** (Quick Flow · BMad Method · Enterprise) | "Three tracks, sized to the work" | nowhere — **and collides with Hub `Track`** (see 6.8) |
| **Parallel track** (Quick Dev / Dev Auto) | "Small, well-understood work skips the ceremony" | nowhere |
| **Party mode** | "the whiteboard meeting, minus the scheduling" | nowhere |
| **Execution matrix** | "Every phase ships with skills, every skill has an owner" | nowhere |
| **Method vs machinery** as distinct layers | "Method and machinery are different layers" | nowhere — yet it is the cleanest statement we have of why the harness is not a Skill |
| **project-context as constitution** | "The documents are the product's memory" | partially — the Charter is our constitution, but the deck's framing never joined it |

The Lexicon slide itself **is** current: its seven nouns match the Charter exactly, including the
Spec's 2026-07-25 addition. The drift is in everything *around* the Lexicon.

### 5b.2 The deck teaches four names BMAD retired

Measured against upstream v6.12.0 (§3): the deck still names **`bmad-quick-dev`**,
**`bmad-dev-auto`**, **`bmad-create-story`**, **`bmad-dev-story`** — all renamed or deprecated in
6.11 (→ `bmad-build`, `bmad-build-auto`; the story pair to shims) — and **Paige**, the Tech
Writer persona, three times; Paige went on hiatus in 6.11 and the agent roster is now five.
`CLAUDE.md` already records these renames correctly, so the repo knows; the *public-facing deck*
does not.

### 5b.3 The Design→repo pull is stale again

Local copies are dated **2026-08-01** — the Charter's own log (line 826) records that pull as the
*first* one ever, made to fix Lexicon artifacts that had described the pre-2026-07-25 six-noun
model since 2026-07-25 and were never pulled. Sizes today:

| Artifact | Design | Repo (2026-08-01) |
|---|---|---|
| `Agentic SDLC.dc.html` | 206,638 B | 193,114 B — **13.5 KB behind** |
| `Lexicon Poster.dc.html` | 12,213 B | 12,271 B |
| `Lexicon to PyForge.dc.html` | 14,892 B | 14,930 B |

The two Lexicon posters differ only by harness-strip artifacts; the **deck is materially behind**.
This is the same drift class the Charter named in 2026-08-01 — recurring, not new.

## 6. The disagreements, stated plainly

1. **Same word, different meaning — `in-progress`.** Upstream story lattice (a story being
   worked), our Spec vocabulary (a contract mid-flight), our ledger. Three jobs, one noun.
2. **Same job, different words.** Upstream `done` · our Spec `shipped` · our Dream `realized`.
   Upstream `review` vs its own `in-review`. One job, four nouns.
3. **A word that is illegal upstream is our most-used.** `shipped` (67) is the exact value
   upstream's test suite resets to `backlog`.
4. **Two disjoint sets with a coupling rule and no shared home.** Dream statuses and Spec
   statuses share no value, yet `specified`-requires-`ready` and `extension-point`→`dreamt`
   couple them — and both rules live in the *Dream* README.
5. **`Spec` itself is overloaded**: the Lexicon's unit-of-contract, BMAD's `SPEC.md` artifact,
   and the legacy Tier-1 `docs/specs/*.md` files, which CLAUDE.md already marks superseded.
6. **`Guard`/`Gate` arrive with Hub meanings** next to our existing "verdict"/"gate_mode"/
   detector vocabulary. The Charter named the Cogs/Smith collision; Guard/Gate was not examined.
7. **`pitched` is declared and unused** (5 declared, 4 live).
8. **`Track` means two different things, and the collision is unnamed.** Hub `Track` = *"the
   durable evidence record of an Op or Cog execution"* (whitepaper §5.3) — the thing Story 53.3
   built `track.json` for. The deck's `Track` = a BMAD **planning lane** (Quick Flow / BMad
   Method / Enterprise), sized by story count. The Charter's cross-walk named the Cogs/Smith
   collision and stopped there; this one is live in a public-facing artifact and in the
   `hub:CAP-3` work at once.
9. **`Guard` / `Gate` were never examined for collision.** The Charter maps them in one row
   ("station verdicts; Warden stays the sole PR verdict") but our estate already uses `gate_mode`,
   "gate report", "readiness gate" and ~30 `*-check` detectors with none of the Hub's
   Guards-check/Gates-decide split. Upstream BMAD adds a third sense: `PASS`/`CONCERNS`/`FAIL`
   gate *verdicts*.
10. **The Design tier teaches vocabulary no repo artifact carries** (§5b.1), and four of its BMAD
    names are retired upstream (§5b.2).

---

## 7. What this research does NOT settle

Deliberately left to the Dream and its Spec: whether the Spec ladder should be declared as-is or
reduced; whether `in-progress` survives on Specs given the Dream side rejected "what is
happening" states; whether our ledger should rename toward upstream `sprint-status.yaml`; whether
a BMAD↔Lexicon cross-walk belongs in the Charter beside the Hub one; and how far to follow
Frame v0.3's recommended-not-required + must-preserve pattern. **No decision is taken here.**

---

## Sources

- Design project `f58c0f17-087b-417e-9cfa-c410de6169dc` — `Lexicon Poster.dc.html`,
  `Lexicon to PyForge.dc.html`
- `docs/dreams/README.md`, `docs/dreams/pyforge-charter.md`, `docs/governance/guild-roster.json`
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-intelligence-hub/`
  (`SPEC.md`, `vocabulary-map.md`)
- BMAD-METHOD v6.12.0 — `sprint_plan.py`, `spec-template.md`, `stories-schema.md`,
  `epics-template.md`, `removals.txt`, CHANGELOG; https://docs.bmad-method.org/
- `openteams-ai/inthub-whitepaper` tag `v9` (README, `GLOSSARY.md`, §5.3/§5.5/§5.6);
  `openteams-ai/frame-spec` (`spec/v0.2.md`, `tools/validate_frames.py`, PRs #20/#25/#28/#29);
  https://ownyourintelligence.ai/guide/ (§13, glossary, field map)
