---
title: "41.2: The satellite PRDs' FR ids leave the kernel's id space"
type: 'chore'
created: '2026-10-26'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-atlas.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
  - docs/governance/fr-baseline.json
  - scripts/fr_baseline.py
  - docs/dreams/pyforge-unifying-strategy.md
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain.py
difficulty: easy
story: '41.2'
spec: pyforge-atlas
surface:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-41-2-the-satellite-prds-fr-ids-leave-the-kernel-s-id-space.md
  - docs/governance/fr-baseline.json
warnings: []
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name a story in a later epic (S-46.2).
> The key stays `blocked` until that story is `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).
>
> **Unblocked 2026-11-13.** Every story its Deps name is `done` on branch `cutover-readiness-2026-11-10`. The operator's "Start build" consent covered the unblock; CLOSE-LEDGERS moved the key to `done`.

> **Re-scoped 2026-11-10 (cutover readiness).** The operator retired the Unity and Wasm satellites on 2026-11-10
> ("Retire both", `docs/dreams/pyforge-unifying-strategy.md` § Realization log, the 2026-11-10 addendum) and kept
> their planning text on A as history; the FR-block renumber sign-off is withdrawn. The story renumbers nothing: the
> two satellite sections become dated `Fold provenance` record sections. FR-78 went to CAP-73 at the same mint. The
> 2026-10-26 contract is kept at the end of this file as history.

<intent-contract>

## Intent

**Problem:** Two satellite PRDs carried verbatim into the atlas PRD (Unity Data Stack FR-1..FR-60 at `prd.md` § Satellite: Unity Data Stack, Wasm Analytics Stack FR-1..FR-17 at § Satellite: Wasm Analytics Stack) reuse the kernel's FR-1..FR-22 ids and carry no arrows, so 22 ids read as defined twice (`fr-duplicate-id`) and 38 Unity ids and ten Unity NFRs carry no arrow. The 2026-11-10 addendum retires both satellites (`spec-pyforge-atlas` CAP-18..CAP-31) and keeps their planning text on A as history.

**Approach:**
- **Retitle, do not renumber.** The two headings `## Satellite: Unity Data Stack` and `## Satellite: Wasm Analytics Stack` become `## Fold provenance — Satellite: Unity Data Stack (retired 2026-11-10, never built; history)` and `## Fold provenance — Satellite: Wasm Analytics Stack (retired 2026-11-10, never built; history)`. The `Fold provenance` prefix is what doctor's parser reads as a record section (`sources/one_chain.py` `_RECORD_PREFIX_RE`); a title with only a date and the word `history` would not qualify, since `_RECORD_DATED_RE` wants reconcile, provenance, convergence, validation or log. A record section suppresses duplicates only: `_fr_definitions` stops reporting a second definition there, so the 22 `fr-duplicate-id` findings stop, but it still returns a first definition there as a definition. The 38 Unity ids FR-23..FR-60 and the ten Unity NFRs are first definitions, so they stay arrowless definitions and baselined `projects` ids, and every `--prune` keeps them, this story's and doctor Story 58.4's (simulated with the real parser and `prune_fr_baseline` on a copy of the tree, 2026-11-10 and again 2026-11-11: 22 `findings` keys go stale, 0 `projects` ids do, 48 stay). No arrow is added, so no satellite requirement is cited into the live space; the 48 ids held in the baseline for good are the owned gap DW-atlas-46-1-9 (Story 46.1 writes it).
- **Nothing inside moves.** No FR or NFR id is renumbered, no arrow is added and no line inside the two sections changes; the Spec's note that the satellite numbering stays independent stays true, so the Spec takes no entry.
- **The story that makes baseline keys stale prunes them.** The retitle leaves the 22 `findings` keys `fr-duplicate-id:FR-1`..`FR-22` stale, and a stale key is a `fr-baseline-stale` WARN that doctor's live test `test_live_tree_fr_without_cap_has_no_fail_at_ruling_snapshot` (`tests/unit/test_sources_one_chain.py`) fails on. Left for doctor Story 58.4 (BUILD-18), that test would stay red from this story's wave (BUILD-3) on and break doctor Stories 56.4, 58.1, 58.2 and 57.3. So, after the retitle, run `python scripts/fr_baseline.py --prune` (the one routine verb; it never adds). At this wave it removes exactly those 22 keys, leaving `findings.pyforge-atlas` empty, and keeps the 48 `projects` ids (simulated 2026-11-11 on a copy of the tree: `pruned 22 entries`, all `pyforge-atlas: fr-duplicate-id:FR-n`; 0 `fr-baseline-stale` after). If the prune prints any other entry, stop: that key went stale through another story, which owns its prune. Then replace the two hand-maintained `owners.pyforge-atlas` rows (`41.2 (fr-duplicate-id: …)` names the keys just pruned, `41.3 (…)` a story retired at this mint) with the one row `DW-atlas-46-1-9 (the retired Unity satellite's first-defined FR-23..FR-60 and NFR-1..NFR-10, held as history)`; the marshal and mason rows stay. This story is the first writer of `docs/governance/fr-baseline.json` on the branch (writers in order: 41.2, then doctor Story 58.4, which prunes only what is still stale at the end). The file is under `docs/governance/**` on the spec-surface allowlist, so no Spec is reconciled or stamped for it.
- **The PRD says why.** One `## Currency reconciliation — <build date> (Story 41.2)` section records the retitle, the ruling, the prune of the 22 keys and the `owners` row, and that `spec-pyforge-doctor:CAP-92`'s "every entry has an owner story" reads DW-atlas-46-1-9 as the owner of record for the 48 ids, since their owner story 41.3 retired on 2026-11-10 (owner: none; retired satellite history). The story name in the heading keeps it apart from the mint's and Stories 46.1 and 46.2's sections of the same month.
- Story 41.3 is retired at the same mint: its ten NFR lines are the Unity satellite's. The 48 first-defined satellite ids it owned in the baseline (FR-23..FR-60, NFR-1..NFR-10) stay there as retired history, DW-atlas-46-1-9.

Ledger key: `41-2-the-satellite-prds-fr-ids-leave-the-kernel-s-id-space`.
Type / Effort / Deps: chore / S / S-41.1, S-46.2.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-18..CAP-31**: the retired capabilities the satellite requirements described (retired 2026-11-10, never built; Story 46.1 renders the markers).
- **`spec-one-chain-per-station:CAP-5`** (amended) and **`spec-one-chain-per-station:CAP-6`**; CHAIN-STANDARD § 6 (one id family, defined once per PRD).

## Acceptance Criteria

Each command runs from the worktree root; read every verdict from its exit code, never through a pipe.

- **AC1 — No live satellite section remains.** Expected: prints 0 (2 today).

  ```bash
  grep -c '^## Satellite: ' _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md
  ```

- **AC2 — Both satellite sections are Fold provenance record sections.** Expected: prints 2.

  ```bash
  grep -cE '^## Fold provenance — Satellite: (Unity Data Stack|Wasm Analytics Stack) \(retired 2026-11-10, never built; history\)$' _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md
  ```

- **AC3 — No FR or NFR definition line changed except the mint's FR-78.** Expected: exit 0; the list it prints holds at most the `#### FR-78: …` heading the 2026-11-10 mint registered (adjusted from the plan's whole-diff count, which the mint's FR-78 registration and this story's own reconciliation section would trip).

  ```bash
  python3 -c "import re,subprocess,sys;P='_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md';r=re.compile(r'(?m)^(?:#{1,6} |- \*\*)N?FR-\d+.*$');a=set(r.findall(subprocess.run(['git','show','origin/main:'+P],capture_output=True,text=True).stdout));b=set(r.findall(open(P).read()));d=sorted(b-a)+sorted(a-b);print(d);sys.exit(0 if all(x.startswith('#### FR-78:') for x in d) else 1)"
  ```

- **AC4 — The PRD says why, in a dated section named for this story.** Expected: prints 1 (0 today; the mint's 2026-11-10 section and Stories 46.1 and 46.2's sections do not match).

  ```bash
  grep -cE '^## Currency reconciliation — [0-9]{4}-[0-9]{2}-[0-9]{2} \(Story 41\.2\)$' _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md
  ```

- **AC5 — The requirement detector is green and reports no atlas duplicate and no stale atlas key.** Expected: exit 0 for both commands. The first prints no atlas `fr-duplicate-id` FAIL and no atlas `fr-counted-run`. No atlas `fr-baseline-stale` WARN fires: the retitle stops the 22 `findings` keys `fr-duplicate-id:FR-1`..`FR-22` firing, and this story's `--prune` removes them. No atlas `projects` id goes stale: FR-23..FR-60 and NFR-1..NFR-10 stay baselined `projects` ids, because a record section suppresses only duplicates and `_fr_definitions` still returns their first definitions as arrowless definitions (`sources/one_chain.py` `_stale` reports a `projects` id only once it is no longer an arrowless definition), so the prune keeps them (DW-atlas-46-1-9). The second command prints `0 []`; it exits 1 if any atlas `fr-baseline-stale` WARN fires (after the retitle alone, before the prune, it prints the 22 keys), if an atlas `fr-duplicate-id` or `fr-counted-run` fires, or if an atlas `fr-duplicate-id` key is still reported as baselined (it prints `0` and the 22 keys and exits 1 today).

  ```bash
  pixi run -e pyforge-guild fr-without-cap-check
  pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap --json > "${TMPDIR:-/tmp}/frw.json"; python3 -c "import json,sys;f=[x for x in json.load(open(sys.argv[1])) if x.get('evidence',{}).get('station')=='atlas'];st=[x['evidence'] for x in f if x['check']=='fr-baseline-stale'];bad=[e['key'] for e in st];bad+=[x['check'] for x in f if x['check'] in ('fr-duplicate-id','fr-counted-run')];bad+=[k for x in f if x['check']=='fr-baselined' for k in x['evidence'].get('keys',[]) if k.startswith('fr-duplicate-id:')];print(len(st),bad);sys.exit(1 if bad else 0)" "${TMPDIR:-/tmp}/frw.json"
  ```

- **AC6 — The baseline loses exactly the keys the retitle made stale, atlas's owner row names what atlas still carries, and doctor's live test passes.** Expected: the first command prints `22 0 True` and exits 0 (it prints `0 0 False` and exits 1 today): against `docs/governance/fr-baseline.json` at the merge-base with origin/main, the removed `projects`/`findings` entries are exactly the 22 atlas `findings` keys `fr-duplicate-id:FR-1`..`FR-22`, nothing is added, `owners.pyforge-atlas` is the one DW-atlas-46-1-9 row while every other `owners` row and every other top-level key is unchanged, and the 48 atlas `projects` ids stay. The second command exits 0: `gather_fr_without_cap` reports no `fr-baseline-stale` for any station (`-k` selects the test by name, so it still finds it once doctor Story 58.1 moves the live readers to `test_live_sources_one_chain.py`).

  ```bash
  python3 -c "import json,subprocess,sys;P='docs/governance/fr-baseline.json';mb=subprocess.run(['git','merge-base','HEAD','origin/main'],capture_output=True,text=True,check=True).stdout.strip();a=json.loads(subprocess.run(['git','show',mb+':'+P],capture_output=True,text=True,check=True).stdout);b=json.load(open(P));ks=lambda d:{(s,k,x) for k in ('projects','findings') for s,v in d.get(k,{}).items() for x in v};rest=lambda d:{k:v for k,v in d.items() if k not in ('projects','findings','owners')};dup={('pyforge-atlas','findings','fr-duplicate-id:FR-%d'%n) for n in range(1,23)};row='DW-atlas-46-1-9 (the retired Unity satellite\'s first-defined FR-23..FR-60 and NFR-1..NFR-10, held as history)';rm=ks(a)-ks(b);add=ks(b)-ks(a);ok=rm==dup and not add and b['owners']==dict(a['owners'],**{'pyforge-atlas':[row]}) and rest(a)==rest(b) and len(b['projects']['pyforge-atlas'])==48;print(len(rm),len(add),ok);sys.exit(0 if ok else 1)"
  pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit -q -p no:cacheprovider -k test_live_tree_fr_without_cap_has_no_fail_at_ruling_snapshot
  ```

## Boundaries & Constraints

**Always:**
- Change only the two `##` headings inside the satellite sections; add one dated reconciliation section.
- Write `docs/governance/fr-baseline.json` only through `python scripts/fr_baseline.py --prune`, plus the one hand edit its own `$comment` allows: the hand-maintained `owners.pyforge-atlas` rows, replaced after the prune by the one DW-atlas-46-1-9 row.

**Never:**
- Never renumber an FR or NFR id, add an arrow, or promote a satellite requirement into the live space; never hand-edit `SPEC.md`.
- Never hand-edit the `projects`, `findings` or `forced` maps of `docs/governance/fr-baseline.json`, never touch another station's `owners` row, and never run `fr_baseline.py` with `--force`, `--project` or a `--snapshot` verb; never prune a key another story left stale (stop and name it instead).

## I/O & Edge-Case Matrix

| Section | Before | After |
|---|---|---|
| `## Satellite: Unity Data Stack` (FR-1..FR-60, NFR-1..NFR-10) | live section; 22 ids defined twice, no arrows | `## Fold provenance — Satellite: Unity Data Stack (retired 2026-11-10, never built; history)`: a record section; its second definitions of FR-1..FR-22 are no longer duplicates, its first definitions FR-23..FR-60 and NFR-1..NFR-10 still count, arrowless |
| `## Satellite: Wasm Analytics Stack` (FR-1..FR-17) | live section; no arrows | `## Fold provenance — Satellite: Wasm Analytics Stack (retired 2026-11-10, never built; history)`: every id is a second definition, so none is a duplicate |
| atlas `fr-duplicate-id` findings | 22 (baselined) | 0 (this story's `--prune` removes the baseline's 22 `findings` keys) |
| atlas `fr-baseline-stale` WARNs | 0 | 0: the retitle alone would leave 22 (the `findings` keys `fr-duplicate-id:FR-1`..`FR-22`) and red doctor's live test; this story prunes them in the same change |
| atlas `projects` ids in `fr-baseline.json` (FR-23..FR-60, NFR-1..NFR-10) | 48, arrowless | 48, still arrowless definitions: none goes stale and the prune keeps them (DW-atlas-46-1-9) |
| `owners.pyforge-atlas` in `fr-baseline.json` | two rows, `41.2 (fr-duplicate-id: …)` and `41.3 (arrowless NFR lines and …)` | one row, `DW-atlas-46-1-9 (the retired Unity satellite's first-defined FR-23..FR-60 and NFR-1..NFR-10, held as history)`; the marshal and mason rows unchanged |

</intent-contract>

## Binding

- Parent capabilities: `spec-pyforge-atlas` CAP-18..CAP-31; `spec-one-chain-per-station:CAP-5` and `spec-one-chain-per-station:CAP-6`.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-26 entry (the origin) and the 2026-11-10 (cutover readiness) entry (the re-scope); the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the entry of that date and its two addenda).
- Epic: Epic 41, minted with Story 41.1.
- Ledger key: `41-2-the-satellite-prds-fr-ids-leave-the-kernel-s-id-space`.
- Deps: S-41.1, S-46.2 (46.2 is the last story before this one that writes the atlas PRD; the writers in order are 46.1, 46.2, 41.2, 48.4).
- Writers of `docs/governance/fr-baseline.json` on the branch, in order: this story (BUILD-3: the prune of the 22 atlas `findings` keys its retitle makes stale, and the atlas `owners` row), then doctor:S-58.4 (BUILD-18: a final `--prune` of whatever is still stale at the end of the branch; its AC12 re-checks the atlas row this story writes). Both keep the 48 `projects` ids, DW-atlas-46-1-9.
- Minted 2026-10-26 in one chain commit; built in the same PR (the one-PR "every requirement derives from a capability" effort: atlas 41.1, doctor 50.1, herald 47.1, marshal 108.1, mason 33.1, scribe 27.1, steward 111.1, warden 20.1).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: exit 0.

**Run before the push:** the acceptance commands above, and `pixi run -e pyforge-guild detectors-ci` (exit 0).

## Auto Run Result

Status: blocked (forward dependency on S-46.2, 2026-11-10; minted 2026-10-26, operator ruling (d): not built in the one-PR effort; re-scoped 2026-11-10 and built in the cutover-readiness PR).

Build 2026-11-11 (wave BUILD-3, after S-46.2 was built on the branch; the status moves at the ledger close, not here):
- The two satellite headings are retitled to the `Fold provenance` record headings; no line inside either section
  moves. The PRD gains `## Currency reconciliation — 2026-11-11 (Story 41.2)`.
- A dry run of `prune_fr_baseline` on the retitled tree removed exactly the 22 atlas `findings` keys
  `fr-duplicate-id:FR-1`..`FR-22` and nothing else; `python scripts/fr_baseline.py --prune` then printed
  `pruned 22 entries`, all `pyforge-atlas: fr-duplicate-id:FR-n`, and kept the 48 atlas `projects` ids. The two
  `owners.pyforge-atlas` rows became the one DW-atlas-46-1-9 row by hand; the marshal and mason rows are unchanged.
- The PRD's `updated:` moves to 2026-11-11 with a dated comment, as every earlier reconciliation section of the PRD
  did. Without it the PRD's date is older than the atlas code dated 2026-11-11 on the branch, and the chain-currency
  sweep reported the PRD as behind its code. No FR or NFR line is touched by the move (AC3).
- Commands: AC1 prints 0, AC2 prints 2, AC3 prints only the mint's `#### FR-78: …` heading and exits 0, AC4 prints 1,
  AC5 exits 0 for both commands (the second prints `0 []`), AC6 prints `22 0 True` and doctor's live test passes
  (1 passed); `pixi run --frozen -e pyforge-atlas kedro-catalog-check` exits 0 (70 passed).
- Re-verified 2026-11-11 after the interrupted attempt: a dry `prune_fr_baseline` on the tree removes nothing (the file
  is the prune's fixed point, `owners` aside), and every command above gives the same result.
- Outside this story's files (reported, not edited): doctor's live test
  `test_live_tree_reference_headings_never_duplicate_and_satellites_do`
  (`src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py`, line 944) asserts
  `fr-duplicate-id:FR-1` is still in atlas's findings, which the retitle ends by design, so it fails from this wave
  until its owner, doctor:S-56.4 (BUILD-4, which owns that file and runs `pyforge-doctor-test`), flips the assertion
  to atlas reporting no `fr-duplicate-id`. Recorded as a planned deferral with that owner (§ Planned deferral
  (written at build)); doctor:S-58.1 only moves the file and is not the owner. The atlas chain-currency sweep still
  reds on links this story does not own (the spine behind code dated 2026-11-11, the retro feed, the gate report's
  shelf); the PRD link is current.

## Planned deferral (written at build)

The row below is not in the deferred-work ledger yet and is not in this spec's frontmatter (`deferred-work-check`
reds a frontmatter row with no tracked ledger twin). The atlas station closer of the cutover-readiness PR writes it
to `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md`: open if the assertion below is
still unflipped when the closer runs, otherwise resolved with a pointer to doctor:S-56.4's change.

- **`DW-atlas-41-2-1`** (medium; owner doctor:S-56.4, wave BUILD-4; location
  `src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py:944`): this story's retitle of
  the two satellite sections to `Fold provenance` record sections ends atlas's `fr-duplicate-id` findings by design
  (`sources/one_chain.py` `_fr_definitions` suppresses second definitions in a record section), so doctor's live test
  `test_live_tree_reference_headings_never_duplicate_and_satellites_do` fails on its last line,
  `assert "fr-duplicate-id:FR-1" in dups["pyforge-atlas"]` (`assert 'fr-duplicate-id:FR-1' in []`; reproduced
  2026-11-11: 1 failed). The fix is a one-line flip of that assertion to `dups["pyforge-atlas"] == []` (atlas now
  reports no `fr-duplicate-id`, the satellites being record sections), dropping the satellite comment. It lands with
  doctor:S-56.4, which owns the file in BUILD-4 and whose AC runs `pixi run -e pyforge-doctor pyforge-doctor-test`;
  doctor:S-58.1 (BUILD-5) only moves the live readers and is not the owner. Until BUILD-4 lands, `pyforge-doctor-test`
  is red on this one test from BUILD-3. This story cannot make the flip: the file is outside its `files_owned`.

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 (every requirement derives from a capability) at the operator's rulings of 2026-10-26 ("yes forbid it"; the ruling sheet accepted in full).

- 2026-11-10: re-scoped at the cutover readiness mint (operator rulings of 2026-11-10: "Retire both"; "Accept all, run mint"): the satellite sections become dated `Fold provenance` record sections, nothing is renumbered, no re-key map; the count is the 22 `fr-duplicate-id` findings that stop; Deps gains 46.2; Effort M → S; AC3 compares definition lines so the mint's FR-78 registration does not trip it.

- 2026-11-10 (review of the mint): AC5 names the `fr-baseline-stale` WARNs the retitle leaves until doctor:S-58.4 prunes the baseline, so the AC can pass as written; the Binding names the 2026-11-10 Dream entry and rulings that carry the re-scope.

- 2026-11-10 (second review of the mint): AC5, the I/O matrix and the Approach match doctor's parser. A record section suppresses duplicates only (`sources/one_chain.py` `_fr_definitions`); a first definition there still counts. Simulated with the real parser and `prune_fr_baseline` on a copy of the tree with both headings retitled: 22 `fr-baseline-stale` WARNs, all `findings` keys `fr-duplicate-id:FR-1`..`FR-22`; no `projects` id goes stale; the prune removes the 22 keys and keeps the 48 `projects` ids. The first review's count also counted those 48 ids as stale, which was wrong. AC5 gains a JSON check that holds the stale set to those 22 keys. The 48 ids held in the baseline for good are the owned gap DW-atlas-46-1-9, which Story 46.1 writes (rule R4: each gap is a deferred-work row).

- 2026-11-11 (third review of the mint): the key is `blocked` (forward dependency: Deps name S-46.2, a later epic; the one policy every station took at this mint), and Deps take the `S-<epic>.<num>` grammar doctor's forward-dependency detector parses. AC4 matches only a section named `(Story 41.2)`, since the mint's own 2026-11-10 section already matched the old pattern. The `spec-one-chain-per-station` citations are qualified (`spec-one-chain-per-station:CAP-5`, `:CAP-6`). AC5 re-simulated with the real parser on a copy of the tree (`_fr_definitions`, `gather_fr_without_cap`, `prune_fr_baseline`): the AC5 check exits 1 today (the 22 keys are still baselined and fire), prints `22 []` after the retitle and `0 []` after the prune; the expectation stands.

- 2026-11-11 (orchestrator decision: the story that makes baseline keys stale prunes them): left for doctor:S-58.4 (BUILD-18), the 22 stale keys this retitle leaves would keep doctor's live test `test_live_tree_fr_without_cap_has_no_fail_at_ruling_snapshot` (it asserts no `fr-baseline-stale`) red from BUILD-3 to BUILD-18 and break doctor Stories 56.4, 58.1, 58.2 and 57.3's AC13. This story now owns `docs/governance/fr-baseline.json` as its first writer (then 58.4): it runs `scripts/fr_baseline.py --prune` after the retitle and replaces the two atlas `owners` rows with the one DW-atlas-46-1-9 row (moved here from 58.4). Re-simulated on a copy of the tree with doctor's real parser: the retitle alone gives 22 `fr-baseline-stale` (all atlas `findings` keys `fr-duplicate-id:FR-1`..`FR-22`), the prune removes exactly those 22 and keeps the 48 `projects` ids, and 0 `fr-baseline-stale` remains. Surface gains the file; AC5 now requires no stale atlas key; AC6 is new (exact removed set against the merge-base, the owners row, and doctor's live test; it exits 1 today); Always/Never, the I/O matrix and the Binding follow.

- 2026-11-11 (build, review round 1): two accepted points from the build review. (1) The PRD's frontmatter `updated:` is re-stamped to 2026-11-11 with a dated comment, beyond the Always line's "change only the two `##` headings; add one dated reconciliation section". This is an accepted deviation, not a scope change: `scripts/fleet_scan.py`'s behind-code check would otherwise report the PRD (2026-11-10) as behind atlas code dated 2026-11-11 on the branch, every earlier reconciliation section of this PRD re-stamped `updated:` the same way, and the line carries no FR or NFR definition, so AC3 holds. The Always line is read as including that re-stamp. (2) The retitle also makes doctor's live test `test_live_tree_reference_headings_never_duplicate_and_satellites_do` stale (it asserts atlas still reports `fr-duplicate-id:FR-1`), which the 2026-11-11 orchestrator decision above missed; the test file is outside this story's files, so it is a planned deferral, `DW-atlas-41-2-1`, owned by doctor:S-56.4 (§ Planned deferral (written at build)).

## Review Triage Log

- (none yet)

## History: the 2026-10-26 contract (superseded 2026-11-10)

The story was minted to renumber the satellite series from FR-78 (Unity FR-1..FR-60 → FR-78..FR-137; Wasm FR-1..FR-17 → FR-138..FR-154), trace each heading's arrow to CAP-18..CAP-31 by subsection, commit `planning-artifacts/rekey-<date>.md` and re-point every reference, with `scripts/fr_baseline.py --prune` removing the 39 atlas `fr-duplicate-id` entries then baselined. The 2026-11-10 rulings withdrew that: the satellites are retired, never built, and their text stays as history.

## Review findings (build, round 1, 2026-11-11)

An independent reviewer failed the first build. Each finding, and what this round did:

- **Major — `src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py:944` (not a 41.2 file)
  and this story spec's body.** The retitle breaks `pyforge-doctor-test`:
  `test_live_tree_reference_headings_never_duplicate_and_satellites_do` fails with
  `assert 'fr-duplicate-id:FR-1' in []` (reproduced 2026-11-11: 1 failed). The spec's own rule (the story whose change
  makes a doctor live test stale handles it) covered only `test_live_tree_fr_without_cap_has_no_fail_at_ruling_snapshot`
  and missed this assertion; no story spec on the branch named the fix, and the finding was only in Auto Run Result,
  not in a `## Planned deferral (written at build)` section, so the regression had no owner. **Fixed in this story's
  files:** § Planned deferral (written at build) now carries `DW-atlas-41-2-1` (the file and line, the assertion to
  flip to atlas reporting no `fr-duplicate-id`, owner doctor:S-56.4, BUILD-4), for the atlas closer to write; the Auto
  Run Result bullet names doctor:S-56.4 alone as owner (doctor:S-58.1 only moves the file); the Spec Change Log
  records the miss. **Not fixable here:** the test file is doctor:S-56.4's `files_owned`, so the one-line flip, and an
  amendment to doctor:S-56.4's story spec (or the plan's files_owned) that lands it in BUILD-4, are the
  orchestrator's; reported in the build notes.
- **Minor — the PRD's frontmatter `updated:` (`prd.md:6`).** The Always line says to change only the two `##`
  headings and add one dated reconciliation section, but the build also re-stamps `updated:`. The reviewer confirmed
  the re-stamp is justified (`scripts/fleet_scan.py`'s behind-code check; every earlier reconciliation did the same;
  no FR or NFR line moves, AC3 holds) but unreconciled with the Boundaries line. **Fixed:** a Spec Change Log line
  (2026-11-11, build, review round 1) records the re-stamp as an accepted deviation. No change to the PRD.

## Gate findings (build, BUILD-3)

- 2026-11-11, `pyforge-doctor-live-test` (wave gate BUILD-3): red on one test,
  `test_live_tree_reference_headings_never_duplicate_and_satellites_do`
  (`src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py:944`,
  `assert 'fr-duplicate-id:FR-1' in []`), the regression this story's planned deferral `DW-atlas-41-2-1` names. Not
  fixable in this story's files: the test file is doctor:S-56.4's (BUILD-4), and the only change inside this story's
  files that greens it would undo the retitle, which is this story's intent (AC5, AC6). Re-run by the wave fix: the
  targeted test still fails (1 failed, exit 1). The flip is verified on the live tree: doctor's
  `one_chain.snapshot_fr_findings` reports no `fr-duplicate-id` for any station (atlas `[]`), so
  `assert dups["pyforge-atlas"] == []` holds; the one-line patch passes `git apply --check`. Left to the orchestrator:
  name the flip in doctor:S-56.4's story spec and plan notes, and list this red in the gate's planned windows from
  BUILD-3 until BUILD-4 lands.
