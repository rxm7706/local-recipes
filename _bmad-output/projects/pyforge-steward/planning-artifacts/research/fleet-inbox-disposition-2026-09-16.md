---
title: "Fleet inbox disposition — intake, Dream seeds, deferred (2026-09-16)"
chain: "pyforge-unifying-strategy"
created: "2026-09-16"
type: research
owner: steward
head: b13856d281
status: approved
---

# Fleet inbox disposition — 2026-09-16

**Scope.** After PR #1379 minted tracked story specs for steward 59–62, doctor 23–24, and
Herald 21.10 / 23.x, the operator asked what else in intake, Dream seeds, and deferred
registers still needed **story decomposition** (`epics.md` + ledger keys +
`spec-<ledger-key>.md`) so `marshal factory dispatch` / `bmad-build-auto` can run.

**Ruling.** The rest of the inbox is **not a second decompose wave**. Most `specified`
Dreams and `ready` SPECs already have epics; frontmatter was never flipped. Taking them
to story decomposition again would mint duplicate work. This file is the revisit record:
each row says what was decided and why, so a later session can reopen a named item
without rediscovering the whole inbox.

**Method.** Live join on `origin/main` at `b13856d281` (#1379): Dream frontmatter,
`SPEC.md` `status:` / `open_questions:`, each station's `epics.md` +
`sprint-status-ledger.yaml`, `DEFERRED_SPECS` in `pyforge.doctor.sources.board`,
`docs/intake/`, legacy `docs/specs/` (`bmad_drift_check.py --specs`), scribe
`later-caps.md`, and the tracked deferred-work ledgers. No blocked ledger key was
flipped. No intake tree was archived here — that is doctor Story 23.4.

**Sibling.** The 2026-09-09 readiness batch
(`fleet-readiness-decision-batch-2026-09-09.md`) graded realization. This batch
dispositions **decompose vs dispatch vs park**.

---

## 1. Already at story state — dispatch, do not remint

| Queue | What | Gate | Why not remint |
|---|---|---|---|
| Steward 59–62 | 19 stories | Repo-only. Start this campaign first (fleet-wide drain lock). | Stories + specs on `main` (#1379). |
| Doctor 23–24 | 10 stories | After steward, or after that campaign ends. **23.4** is how leftover intake leaves the tree. | Same. |
| Herald 22.1 + 23.1 / 23.2 / 23.5–23.8 | Repo | Specs exist (22.1 pre-existed; 23.x on #1379). | Same. |
| Herald 21.6–21.9 | Specs already on `main` | Claude Design push is the AC. | Spec gap is closed; ACs are Design. |
| Herald 21.10 | Spec on #1379 | After those Design pushes. | Registry story waits on decks that exist in Design. |
| Herald 21.4 | Still no story spec | Design-gated. Mint a spec only if marshal must see the key. | Do not treat missing spec as a new epic. |

**Blocked — do not flip:** marshal **33.11**, atlas **25.2**, steward **44.x** (foundry
cutover; product after 54.5 is `python-foundry` / B), steward **49.11 / 49.13**.

## 2. Do not decompose

| Item | Disposition | Revisit if |
|---|---|---|
| `spec-pyforge-charter` | Stay in `DEFERRED_SPECS`. Constitutive; CAP-1/4/5/6/8 are document-integrity, not stories. | Charter CAPs become implementable mechanism (they should not). |
| `spec-agentic-sdlc-autonomy` | Stay in `DEFERRED_SPECS`. Standing position; not a deliverable. | The Spec's own text stops saying that. |
| `spec-golden-path-conda-blind-spot` | **De-registered** this PR. Warden Epic 12 is `done` and cites CAP-1..5. Do not mint Epic 13. | A new CAP is added that Epic 12 does not cover. |
| Foundry-product after 54.5 / steward Epic 44 | A-only factory/CFE/recipes until a foundry CFE exists. Do not mint a second foundry-product Dream here. | Operator opens a named A-only expiry or a B-only Spec. |
| Steward Epic 8 | Jira↔GitHub sync, already built. **Not** work-passports (Epic 61). | A new sync CAP that 8.x does not cover. |
| Deferred-work ledgers (`DW-*`) | Historical re-verify campaign, not 300 stories. Process Dream: `deferred-work-resolution-sweep`. | That Dream is specified and a **single** re-verify story is minted. |
| Scribe `later-caps.md` | Hoisted into Epics 9–17; ledger complete. | A new later-cap is added that is not hoisted. |
| Extension-points (`enterprise-data-models-and-apis`, `miniforge-installer`, `reusable-cicd-workflows`) | Parked on purpose. | A native subject (atlas) or an un-park ruling. |
| Most `specified` Dreams whose epics are already `done` | Status hygiene later (do not mass-flip here). Not new stories. Atlas Artifactory/Wagtail; steward OCP / local-OCP / secure-dashboards / jira; warden web-face / inventory; mason CFE rebuild; scribe recall cluster; marshal run-watch / cursor-routing / token-economy. | An epic is still `backlog` for that slug (none were, except the dispatch queues above). |
| Gists and white papers | Grounding, not contracts. | A gist names a capability no Dream owns. |

Draft marshal SPECs stay parked: `spec-loop-home-fleet-refresh`,
`spec-sprint-status-auto-promote`, `spec-dashboard-project-path-derivation`,
`spec-pyforge-core`. Loop homes 31 commits behind is already `marshal refresh`.

## 3. Intake — route, do not station-ize

`docs/intake/` is doctor **23.4** (plus **23.3** for `docs/specs/`). This PR only
corrects the inbox README so the 2026-09-16 ruling is visible before 23.4 moves files.

| Drop | Disposition | Archive when |
|---|---|---|
| `jira-github-projects-sync/` | Grounding for shipped Epic 8. | 23.4 |
| `secure-live-dashboards/` | README was stale (“no Dream”). Epic 9 shipped `pyforge/steward/dashboard/`. | 23.4 |
| `local-ocp-hybrid-environment/` | Spec source. Epic 12 including 12.9 is `done`. | 23.4 |
| `agentic-sdlc/` | Teaching deck / standing autonomy Spec. Steward **59.4** names the deck. Dream is `specified`, not `pitched`. Do not mint a second autonomy epic. | After 59.4 + any remaining teaching pull |
| `gists/` | Cited or already archived. 23.4 + `gists/INDEX.md`. | 23.4 |
| `external-repos-analysis-2026-08-22/` | Research record (sibling OpenTeams fleet, prf pipeline). Fold notes only. | Optional with 23.4 |
| Legacy `docs/specs/` | 2 `in-progress` (flyte, feedstock-refresh) + 3 `workflow` are **CFE / mason**, not new station epics. | 23.3 sunsets the shelf |

## 4. Dreamt seeds

| Dream | Disposition | Next act |
|---|---|---|
| `status-body-consistency` | **Only new Spec → Story worth minting.** Spec still `draft`. | Answer the scope OQ (Dreams+Specs vs all planning prose), `bmad-spec` to `ready`, **one** doctor epic. |
| `pixi-candidate-currency` | Doctor 21.7 `done`. **Flipped `realized` this PR.** | None. |
| `spec-surface-overlap-tolerance` | Marshal Epic 42 shipped #1378. **Flipped `realized` this PR.** | None. |
| `deferred-work-resolution-sweep` | Keep as a **program** Dream. | After status-body, optionally one re-verify story — not a ledger dump. |
| `fleet-hygiene-verification-exemplar-program` | Catalog of gaps, not a product. | Do not decompose the catalog. |
| `enterprise-data-models-and-apis` | Stay `extension-point`. | Native subject in this repo. |

## 5. Applied in this PR

- This file (the revisit record).
- `DEFERRED_SPECS`: remove `spec-golden-path-conda-blind-spot`; keep charter + autonomy; comment the 2026-09-16 reason.
- Dream frontmatter + Realization log: `pixi-candidate-currency`, `spec-surface-overlap-tolerance`.
- `docs/intake/README.md` dispositions (no moves).
- `docs/dreams/README.md` table status for the two flips.
- Team-memory pointer.
- Doctor unit pin: golden-path is not in `DEFERRED_SPECS`.

**Deliberately not applied:** intake archive; `docs/specs/` sunset; mass `specified` →
`realized` flips; steward Epic 44 / 33.11 / 25.2 / 49.11 / 49.13; Herald 21.4 story
spec; status-body epic; marshal factory dispatch.

## 6. Recommended apply order after merge

1. `marshal factory dispatch pyforge-steward --stories` 59.1–62.3.
2. Then doctor 23–24 (23.4 clears intake).
3. Herald 22.1 + 23.x when wanted; Design for 21.6–21.9 before 21.10.
4. Next decompose: `status-body-consistency` only.

## 7. Operator follow-up 2026-09-16 — Charter / autonomy (not a remint)

The operator confirmed three rulings and left the Guildhall referent (Q1) open.

| Id | Ruling | What we do |
|---|---|---|
| **Q2** | Mint the doctor CAP-3 `CONSTITUTIVE` story now (named, local, not Charter decompose). | **Do not mint.** Doctor **21.4** already shipped 2026-09-10 (`spec-21-4-constitutive-is-derived-from-the-roster-not-hardcoded-beside-it`, ledger `done`). `chain.py` derives via `_load_constitutive()`; `_CONSTITUTIVE_FALLBACK` is the documented degrade path, not a second source of truth. A new epic would duplicate 21.4. |
| **Q3** | Autonomy L1–L5 stays **teaching-only in the deck (59.4)** until the hall exists. Labels without AUT-3 would be a maturity score (autonomy non-goal). | Bind 59.4: no L-level / autonomy-% labels. Do not mint AUT-1..3. |
| **Q4** | Charter Dream stays **`specified`**. `realized` would lie the same way `shipped` on the Spec would. | Frontmatter stays `specified`. CAP-3 leftover is closed in code; HELD is now **CAP-7 / CAP-2** (unbacked hall) only. |
| **Q1** | Still open. | No Vizro / Wagtail / portal / Hub product until a Charter amendment names the hall. |

Charter and autonomy stay in `DEFERRED_SPECS`. CAP-7 / AUT-3 wait on Q1. Charter `SPEC.md` still names `chain.py:96` as hardcoded — that body is stale; append the memlog, do not hand-edit the Spec; re-derive on the next Charter amendment.
