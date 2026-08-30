---
doc_type: sprint-change-proposal
project: pyforge-atlas
date: 2026-08-30
trigger: Story 21.3 (PR #941) held at marshal's first automated land — workbook still supplies the universe
scope_classification: Moderate
status: approved
approved_by: operator direction 2026-08-30 ("course correction to remove dependencies on the excel file — replan / rescope atlas outstanding epics and stories and run marshal factory drain --mode drain_to_zero on pyforge-atlas")
mode: batch (autonomous session; no interactive checkpoints)
---

# Sprint Change Proposal — retire the Excel workbook from the inventory quartet

## 1. Issue Summary

**Trigger story:** 21.3 *Tier 0 harden and `--live-catalog` contract* (PR #941,
`dispatch/pyforge-atlas/21.3`) — the first story on any pyforge station to reach marshal's
fully automated `dispatch → verify → land` path. It was held on 2026-08-30 because
`--live-catalog-only` read as "workbook-free" while `records` / `tab_packages` (the package
universe, `CDO-ENT-JFROG`/`CDO-ENT-CONDA`/`10k*` membership, roles, the OpenTeams summary)
still came from `docs/Analysis_Dataset-2026-08-12.xlsx`. Because every remaining Epic 21
story chains on `S-21.3` and Epics 22/23 chain on Epic 21, the hold blocked **all 21
remaining atlas stories** — the only backlog left on the fleet.

**Issue type:** misunderstanding of the original requirement's scope (21.3) **plus** a
genuine gap in the plan (no story owned workbook retirement).

**Evidence (re-verified against live code on `main` and the PR branch):**

| Claim | Verdict | Evidence |
|---|---|---|
| 21.3's help text overclaims workbook independence | **Refuted** | PR #941's `--live-catalog-only` help: "Require --live-catalog and all three of its required datasets present, readable, and above their scale floors … exit 2 otherwise." Matches `verification-matrix.md`'s CLI contract ("fail if any required dataset missing/stale") exactly. |
| 21.3 met its contract | **Confirmed** | `stories.yaml` 21.3: `invoke_dev_with: "Thin metrics.py only; no Tier 1 fetches"`; epics.md AC: "verification BOOLs read Parquet only; scale gates pass". 16/16 tests; three adversarial passes; live run 34,098/880,710/21,761 rows. |
| The workbook is a hard, untracked dependency | **Confirmed — severe** | `--analysis-xlsx` is `required=True` (exit 2 if missing); `git ls-files docs/*.xlsx` is empty; the file is 11 MB local-only. A fresh clone or CI runner cannot produce deliverable A at all. |
| No story owns the metrics-side universe cutover | **Confirmed** | Grep of epics.md/stories.yaml/all 23 story specs: 23.4 ports *row logic* to Kedro; 23.7 asserts "no workbook touched" for the **bootstrap** run and reads the scripts' thin paths; its only script-side workbook action is an *optional* `INVENTORY_USE_LEGACY_SCRIPTS` refuse-flag. |
| 23.4's row grain is wrong | **Confirmed** | `spec-23-4` inputs name `identity_packages_primary` (identity-contract grain: one row per OpenTeams-universe package, ~7.5k) but deliverable A is the `verified-all-packages` union — **38,372 rows** on 2026-08-12. A parity test against `metrics.py` would fail on row count alone. |
| Nothing removes the workbook code | **Confirmed** | `openpyxl`/`load_workbook` in identity.py (L45, L893, L917), priority.py (L31, L600, L731–805 write-back), dashboards.py (L14, L187, L270); `XlsxReader` + `--analysis-xlsx` in metrics.py. 21.7's *Never* explicitly keeps `write_xlsx_tab`. |
| `MRS-GATE-007` would refuse later landings | **Confirmed** | PR #942's first cut listed only 21.3's diff paths; 21.7 (identity.py), 21.10 (`kedro-viz-publish.yml`), 22.1 (priority.py), 22.6 all land outside it. Widened before merge (PR #942, second commit). |
| Marshal orders the drain by `Deps:` | **Refuted** | `dispatch_fleet.station_backlog` = tracked-ledger keys in story-key order, optionally re-ordered by `fleet-drain-queue.yaml`; no `depends_on` reader anywhere in `pyforge.marshal`. Without an override, 21-9/21-10 (optional, dep 21.8) and 22-x would dispatch before 23-x regardless of deps. |

## 2. Impact Analysis

### Epic impact
- **Epic 21** — completable as planned. 21.3 lands at its contracted scope (`done`);
  21.4–21.10 unchanged. No story rolled back.
- **Epic 22** — unchanged. 22.1 stays the bridge until 23.5.
- **Epic 23** — **modified**: two stories added (23.8, 23.9); 23.4's deps + row grain
  corrected; 23.7's deps + AC widened to gate the quartet as well as the bootstrap.
- No epic is invalidated; no new epic is needed. Story count 21 → **23** remaining.

### Story impact
| Story | Change |
|---|---|
| 21.3 | `backlog → done`; AC annotated with the actual scope. |
| 23.4 | Deps `S-21.3, S-23.3` → `+ S-23.8`; row grain = `inventory_universe`. Spec change-log entry added. |
| 23.7 | Deps `+ S-23.8, S-23.9`; "no workbook ingest" now covers the quartet (`openpyxl` absent from `scripts/`). |
| **23.8 (new)** | *Workbook-free metrics universe* — Kedro `inventory_universe` dataset (one row per PEP-503 name, workbook provenance labels preserved as strings, `role`, `openteams_universe_member`) + `--analysis-xlsx` optional. Deps `S-21.4, S-21.5`. Effort L. |
| **23.9 (new)** | *Quartet workbook retirement* — identity/priority/dashboards/metrics become thin actuators over the Epic 23 exports; every workbook flag refuses with a pointer; `grep openpyxl\|load_workbook\|XlsxReader scripts/` empty. Deps `S-23.4, S-23.5, S-23.6, S-23.8, S-22.1`. Effort L. |

### Artifact conflicts (all resolved in this PR)
- `SPEC.md` — CAP-8 gains a *workbook retirement* success line; Non-goal "Excel workbook
  ingest or mirror" clarified (Kedro never reads it; retiring the quartet's inputs IS in
  scope; `10kClosed` is reported, not seeded).
- `complete-export-contract.md` — §6 epic map still said 18/19/20 (pre-2026-08-29
  renumbering) → 21/22/23; §7 "Excel workbook remains out of scope" → gated on zero
  `.xlsx` reads; new **§9 workbook retirement map** (sheet → dataset → story, with the
  2026-08-12 row counts).
- `verification-matrix.md` — "Excel workbook tabs" moved from *stays outside* to
  *retired by 23.8/23.9*.
- `epics.md`, `stories.yaml`, tracked `sprint-status-ledger.yaml` (+ Tier-3 feed) —
  updated as above; dated course-correction note appended to epics.md.
- `docs/reference/…_replay.md` — 21.3's scope paragraph added on the PR branch before
  merge (states the workbook is still required until 23.8/23.9).
- PRD / architecture / UX — **no conflict**: the PRD's only `.xlsx` mentions are an unrelated
  upload journey; the architecture spine's AD-2/AD-3/AD-13 are honored by 23.8's design.
- Marshal policy — `epic_surfaces` widened to the whole quartet + docs/conf + CI workflow +
  `pixi.toml`/`pixi.lock`/`environment.yaml` for Epics 21/22/23 (PR #942).
- Marshal queue — new `_bmad-output/projects/pyforge-marshal/planning-artifacts/fleet-drain-queue.yaml`
  with the explicit dependency-respecting order (§ 5).

### Technical impact
- One new pure Kedro node + catalog entry (23.8); script-side plumbing; no new fetch code or
  credentials. 23.9 is deletion-heavy (script + docs). No infrastructure or deployment change.
- `verify_commands` for atlas stays **empty** for the campaign (operator direction, PR #940):
  every landed story is UNVERIFIED by marshal until it is restored — see § 5 handoff.

## 3. Recommended Approach

**Option 1 — Direct Adjustment (selected).** Land 21.3 at its contracted scope, add the
two missing stories inside Epic 23, correct 23.4/23.7, and make the drain order explicit.
Effort: Medium (planning) + two L stories. Risk: Low — nothing is rolled back; every
existing story spec stays valid; the only spec whose *contract* changed (23.4) had a latent
parity failure that this fixes.

**Option 2 — Rollback** (revert 21.3 and re-implement it as "workbook-free"): Not viable.
21.3's contract never included the universe; a workbook-free universe needs 21.4/21.5
outputs that do not exist yet — the story would be blocked, not broader.

**Option 3 — MVP review** (drop workbook retirement, keep the plan's "out of scope"
wording): Not viable against the operator's stated goal, and it leaves deliverable A
unproducible from a fresh clone.

**Hybrid considered:** put the universe union in `metrics.py` only (script-side, no Kedro).
Rejected — 23.9 would delete it again and 23.4 would still lack a full-grain row source.

## 4. Detailed Change Proposals

All applied in this PR; before/after in the diff. Summary of each edit:

1. **epics.md 21.3** — `Status: backlog → done`; italic scope note. *Rationale:* record what
   actually shipped so the ledger, the spec (`status: done` via PR #941), and the epic agree.
2. **epics.md 23.4** — Deps `+ S-23.8`; Given-clause names `inventory_universe` as the row
   grain "(~38k rows), not the OpenTeams-universe grain". *Rationale:* evidence row 5.
3. **epics.md 23.7** — Deps `+ S-23.8, S-23.9`; Given-clause "by the bootstrap **and** by the
   quartet (`openpyxl` absent from `scripts/`)". *Rationale:* the gate must gate the thing
   the operator asked for.
4. **epics.md 23.8 / 23.9 (new)** — full Given/When/Then; Effort L each. Contract specs:
   `specs/spec-23-8-workbook-free-metrics-universe.md`,
   `specs/spec-23-9-quartet-workbook-retirement.md` (each carries the sheet→dataset map,
   boundaries, I/O matrix, code map with line anchors, ACs, and a `Block If` on its deps).
5. **stories.yaml** — 23.4 `depends_on + "23.8"`; 23.7 `depends_on + "23.8","23.9"`,
   `done_checkpoint` mentions the quartet; 23.8/23.9 entries added.
6. **SPEC.md / complete-export-contract.md / verification-matrix.md** — as in § 2.
7. **spec-23-4** — Spec Change Log entry (row grain + deps).
8. **Ledger** — Tier-3 feed + tracked twin: `21-3 → done`; `23-8-workbook-free-metrics-universe`,
   `23-9-quartet-workbook-retirement` added as `backlog` (via `sprint-ledger-sync --project atlas`).
9. **Marshal** — `fleet-drain-queue.yaml` (order below); `epic_surfaces` widened (PR #942).

## 5. Implementation Handoff

**Scope classification: Moderate** — backlog reorganization + two new stories; no
fundamental replan. Routed to the Developer agent via marshal's fleet drain (unattended,
`gate_mode = "none"`, independent reviewer still runs per story).

**Drain order** (`order_overrides.pyforge-atlas`; workbook-retirement critical path first,
every `Deps:` edge respected; marshal runs one story per station at a time):

`21.4 → 21.5 → 21.6 → 23.8 → 21.7 → 21.8 → 23.1 → 23.2 → 23.3 → 23.4 → 22.1 → 23.5 → 23.6 → 23.9 → 22.2 → 22.3 → 22.4 → 22.5 → 23.7 → 22.6 → 21.9 → 21.10`

The workbook becomes **optional** for the operator run after the 4th story (23.8) and is
**gone from `scripts/`** after the 14th (23.9). The seven optional stories (22.2–22.6, 21.9,
21.10) sit last; cut them with a `skip_policies` entry if you want the drain shorter —
that is a scope decision this proposal deliberately does not make.

**Command:** `pixi run -e pyforge-marshal marshal factory drain --mode drain_to_zero`
(detached campaign supervisor; `marshal factory dispatch-attach pyforge-atlas` to follow).

**Open operator decisions (do not block the drain):**
1. **`10kClosed` (10,000 rows)** — no catalog source, no Dream row. 23.8 reports the delta.
   Accept it, or mint a follow-up `discovery_tenk_closed_seed` story with a real upstream.
2. **`verify_commands` restoration** — atlas's policy still has both commands commented out
   (PR #940). Every story the drain lands is unverified by marshal until they are restored;
   plan a hand-run of `kedro-test` + `kedro-catalog-check` across the landed set, then
   uncomment.
3. **Optional-story scope** — see the `skip_policies` note above.

**Success criteria:**
- Drain reaches `DRAINED` for pyforge-atlas with the ledger at 23/23 remaining → `done`.
- After 23.8: `metrics.py --live-catalog "$PYFORGE_ATLAS_DATA_ROOT"` with no `--analysis-xlsx`
  exits 0 and writes deliverable A; `10kClosed` delta printed.
- After 23.9: `grep -rn 'openpyxl\|load_workbook\|XlsxReader\|analysis-xlsx' scripts/` is empty.
- After 23.7: bootstrap + quartet on a fresh clone with no workbook on disk — zero `.xlsx` reads.
- Rule-2 CFE retro at closeout (CLAUDE.md) — this effort touches no recipe, so expect a
  "verified existing guidance held" CHANGELOG entry unless the drain surfaces conda-forge
  work.
