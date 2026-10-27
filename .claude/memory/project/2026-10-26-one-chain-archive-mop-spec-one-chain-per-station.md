---
name: "2026-10-26-one-chain-archive-mop-spec-one-chain-per-station"
description: "2026-10-27 LANDED: one-chain archive mop (spec-one-chain-per-station:CAP-11), PR #2328 merged 7a167ba6b6; 158 archived Dreams in archive/docs/dreams/; traps: docs link gate, station-tests trigger map"
metadata:
  type: project
---

**Landed 2026-10-27.** The 2026-10-26 one-chain archive mop (spec-one-chain-per-station:CAP-11, CHAIN-STANDARD section 11) merged as PR #2328, merge commit `7a167ba6b6` ("Merge pyforge-marshal/111-1 into main"). CI: 35 checks passed, 5 skipped, 0 failed. After the merge, `sprint-ledger-sync` for all eight stations changed nothing, and `story-status-check` exits 0.

**What moved.** The 158 `status: archived` Dreams left `docs/dreams/` for `archive/docs/dreams/<same name>`. 113 of them were folded verbatim into their station Dream first. `fold-complete` reads 159 complete, 6 baselined, 0 archived in the live tree.

**Readers follow the move:**
- Doctor `dreams-hygiene` resolves a Kinship wikilink under the archive.
- `pixi-currency` reads its ledger there.
- `deck_facts` reads a deck's Dream there.

Live pointers were re-pointed. Dated records were left as written. 265 SPEC.md `surface:`/`covers-dreams:`/`owner-dream:` lines in 101 Specs were script-rendered under the operator's 2026-10-26 approval (memlog first, anchors asserted, validate passes logged, scoped stamps).

**Stories.** One PR, one relay story per station, numbered past two sibling sessions' claims: atlas 44.1, doctor 53.1, herald 48.1, marshal 111.1, mason 35.1, scribe 28.1, steward 115.1, warden 23.1. All are `done`.

**Lessons:**
- **More than one banner.** A second sub-fold banner can sit after the H1 (13 marshal files). Strip every Consolidated-into blockquote, not only the leading one.
- **Scoped stamp.** spec-surface's scoped stamp refuses unless the memlog names each changed path literally.
- **ad-citation.** ad-citation reads 'spec X CAP-n' (with a space) as a bare cite. New planning text writes `spec-one-chain-per-station:CAP-11`.
- **Docs link gate.** `docs-site-validate-links` counts any link target outside `docs/` as dead. It also reads a bare URL ending in `.md` as a relative path. So a link from `docs/` to a moved file names the repository URL as a CommonMark angle-bracket destination, `](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/<slug>.md>)`. Apply the same link text in the archived copy too, so `fold-complete` still reads the fold as verbatim.
- **Station-tests trigger map.** Steward's `test_station_tests_trigger_map.py` derives every repository path a station test names, including string literals. It requires that the suite's `changes` filter in `.github/workflows/pyforge-station-tests.yml` fires on each one. When a moved path leaves a filtered directory, the path joins that job's `<station>_paths` list. Example: `test_guards.py` asserts `archive/docs/dreams/build-league-scorecard.md`, and that path is now in `steward_paths`. Without it, the first full pr-preflight refused the push.
- **Merging main into a planning branch.** In `epics.md`, keep both sides. Chain the `updated:` note as "<ours>. Prior <main's note>", and drop any duplicate `epicCount`/`storyCount`/`updated:` lines that keep-both leaves. Then re-measure the counts from the synced ledger.

**Left of CAP-11:**
- Step 2: the absorbed and archived Spec folders.
- `docs/dreams/archive/pyforge-unifying-strategy-2026-08-23-topology.md`: a split-off snapshot, not a fold.
- Step 3: `docs/intake/` and `docs/specs/`.
- Two docstrings under `.claude/skills/conda-forge-expert/tests/meta/` still name a moved Dream. They wait for the next CFE retro.
