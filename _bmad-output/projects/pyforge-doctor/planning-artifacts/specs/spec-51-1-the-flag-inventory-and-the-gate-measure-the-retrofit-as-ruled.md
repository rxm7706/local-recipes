---
title: "51.1: the flag inventory and the gate measure the retrofit as ruled"
type: 'fix'
created: '2026-10-26'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - scripts/flag_inventory.py
  - scripts/flag_gate_check.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_effect.py
  - docs/governance/guild-roster.json
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - tests/scripts/test_flag_inventory.py
  - tests/scripts/test_flag_gate_check.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_capability_effect_caller_reach.py
---

<intent-contract>

## Intent

**Problem:** the retrofit (spec-feature-flag-governance CAP-7) is minted against two numbers the inventory reports: runtime rows with no flag, and warned specs. Measured on 2026-10-26 at `97c8211773`, neither was the ruling's number.
- **The join lost rows.** `capability_effect._story_surface_by_cap` joins a CAP to the *last* `epics.md` story block that cites it. Steward Story 111.1 (done) cites `spec-pyforge-steward CAP-1..CAP-168` on one line with a planning-only Surface, so every steward CAP read `unresolved` and twelve runtime rows vanished; marshal 108.1 did the same to marshal CAP-1, CAP-2 and CAP-3. The join also admits a story at any status, so `spec-python-foundry-cutover` CAP-6 read `runtime` because blocked Story 44.9 names `cli.py` in its Surface.
- **The warning counted history.** The gate's `flag-pre-rule` warned on every pre-rule `type: feature` spec: 840, of which 826 are `done`. Scope ruling 3 (2026-09-28) names the warned population as *stories already in backlog*; a done story's capability is retrofitted at the CAP (one flag per CAP), and its spec is never rewritten.
- **CAPs were attributed to every Spec on a line.** `_caps_cited_on_spec_line` gives each CAP on a line to every Spec the line names, so steward Story 13.5's `spec-pyforge-steward CAP-107 (<- spec-scratch-worktree-lifecycle CAP-4, CAP-5)` made steward CAP-5 `runtime`, and Story 86.1's `spec-pyforge-unifying-strategy CAP-10 over the CAP-6 seam ... spec-python-foundry-cutover` made two unbuilt cutover capabilities `runtime`. The same reading let a retrofit story for `spec-pyforge-core` CAP-11 that names the station's inventory file gate the station Spec's CAP-11 too.
- **The flag platform cannot flag itself.** A capability whose code is the flag reader is covered only by an exempt retrofit story (operator ruling R4), which the inventory could not read.

**Approach:**
- Doctor gains `_story_surface_citations_by_cap`: every citing story of each CAP, `epics.md` order then story specs, deciding nothing. The caller-reach detector keeps `_story_surface_by_cap` (last-wins) unchanged.
- Doctor gains `_caps_attributed_on_line`: each CAP token belongs to the nearest Spec mention on its left (else the first on its right); a mention inside a parenthetical speaks until the group closes; a mention of a Spec that is not open keeps its CAPs out of every open Spec; an open Spec's bare name inside a path (`.../pyforge-steward.md`) is not a mention. A `spec-<name>` token counts as a mention only when it names a tracked Spec folder, open or ended (`spec-surface-check` is a tool, `spec-21-4` a story file). The citations join and the inventory's flag and cover reads use it.
- In the citations join a story block also ends at the next `## ` heading, so an epic heading and its intro never join the story above them (the last-wins join keeps its reading).
- Measured and not adopted: dropping `type: fix` stories from a CAP's runtime reach would leave 35 runtime rows with no evidence (marshal `status`, `watch`, steward `workspace clean` among them), so a fix story's code `Surface:` still counts.
- The inventory joins through landed stories only (an `epics.md` story whose ledger key reads `done` in the tracked `sprint-status-ledger.yaml`; a story spec with `status: done`) and keeps the best-classified Surface (runtime over module over planning over unresolved; a tie keeps the earliest). A project with an `epics.md` and no readable ledger is exit 2.
- The gate's `flag-pre-rule` warns only on a spec whose status is not in `ENDED_STORY_STATUSES` (`done`, `superseded`); the inventory's warned list follows, so report and gate cannot disagree.
- The roster gains `flag_retrofit_cover_exemptions` (`["flag-infrastructure", "detector-or-gate"]`: R4's value, and the operator's amendment of 2026-10-26 for a capability that is itself a gate; a governance act with its `$comment`); the inventory reads an exempt story under that value whose `Parent:` line cites the Spec and CAP as the CAP's cover (`exempt: <value> (<story key>)`), never counted unflagged. A prose citation covers nothing. The script holds no copy of the value.

Ledger key: `51-1-the-flag-inventory-and-the-gate-measure-the-retrofit-as-ruled`.
Type / Effort / Deps: fix / M / none.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-20** — the per-station flag inventory (Story 34.4) this fix corrects; the gate is Story 34.2's.
- **`spec-feature-flag-governance` CAP-2 and CAP-7** — the gate and the retrofit; rulings R4, R6 and R8 of 2026-10-26.
- **Charter section 6** — the evaluator stays outside every station package; Doctor's join is imported, never re-implemented.

## Acceptance Criteria

- **AC1 — A later chore cannot hide a landed row.** A done story citing `CAP-1..CAP-2` with a planning Surface after a done story whose Surface names `cli.py` leaves CAP-1 `runtime`.
- **AC2 — Only a landed story joins.** A `blocked` story's Surface does not classify its CAP; the row reads `no landed story cites this CAP (1 citing story not done)`; a story spec at `in-review` does not join through its Parent line.
- **AC3 — Best class wins.** Among landed citations ordered module, none, runtime, the row reads `runtime`.
- **AC4 — The warning.** A pre-rule feature spec at `done` or `superseded` is not warned; at `blocked` it is.
- **AC5 — The cover.** An exempt story under `flag-infrastructure` whose `Parent:` line cites the CAP reads `exempt: flag-infrastructure (<key>)` and is not counted; the same story citing the CAP only in prose covers nothing; `docs-only` covers nothing; a tree key is named before a cover.
- **AC8 — Attribution.** On `spec-a CAP-1 (<- spec-x CAP-2), CAP-3`, spec-a holds CAP-1 and CAP-3 and nothing holds CAP-2; on `spec-a CAP-1 ... spec-b`, spec-b holds nothing; a bare name in a path is not a mention; `spec-surface-check` is no mention.
- **AC9 — Block boundary.** An epic heading and intro that cite a CAP never join the story that precedes them in the citations join.
- **AC6 — No ledger is exit 2** naming `sprint-status-ledger.yaml`, nothing written.
- **AC7 — The scripts suite's import pin holds** (no new stdlib import in `flag_inventory.py`); the inventory names no exemption value.

## Boundaries & Constraints

**Always:**
- Keep the caller-reach detector's join as it was; the inventory reads the new citations join.

**Never:**
- Never read the Tier-3 feed; the tracked ledger is the twin of record. Never rewrite a done spec to clear a warning.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-doctor` CAP-20 (the flag inventory); the Guild rulings R4, R6, R8 of 2026-10-26 on `spec-feature-flag-governance` CAP-7.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-26 (the inventory and the gate measure the retrofit as ruled) entry.
- Epic: Epic 51, minted with this story.
- Ledger key: `51-1-the-flag-inventory-and-the-gate-measure-the-retrofit-as-ruled`.
- Deps: none.
- Minted 2026-10-26 in one chain commit; built in the same PR (the CAP-7 retrofit effort: marshal Epic 110, steward Epic 114, atlas Epic 42, scribe Epic 29, doctor Epic 51).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_flag_inventory.py tests/scripts/test_flag_gate_check.py -q` — expected: pass (AC1–AC7).
- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_capability_effect_caller_reach.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-guild flag-inventory` — expected: exit 0, eight reports regenerated.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass.

## Auto Run Result

Status: in-progress (hand-built in the retrofit PR).

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 at the operator's approval of the CAP-7 retrofit sheet (R1–R8).

## Review Triage Log

- (none yet)
