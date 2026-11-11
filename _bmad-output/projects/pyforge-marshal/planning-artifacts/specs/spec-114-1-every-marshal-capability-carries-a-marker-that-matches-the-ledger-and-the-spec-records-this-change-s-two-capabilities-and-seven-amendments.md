---
title: "114.1: Every marshal capability carries a marker that matches the ledger, and the Spec records this change's two capabilities and seven amendments"
type: 'docs'
created: '2026-11-10'
status: 'blocked'
retires-flag: pyforge.marshal.context_bundle_digest   # spec-46-2 declared this key and never shipped it; flags.json never held it and no tracked file reads it (BUILD-3 gate)
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: heavy
story: '114.1'
spec: pyforge-marshal
surface:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/cap-marker-truth-2026-11-10.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-74-2-dispatch-refuses-a-story-the-flag-gate-would-red-before-any-session-starts.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-46-2-the-canonical-context-bundle-is-digest-pinned.md
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
warnings: []
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-117.5, S-118.2); their renders define spec-pyforge-core:CAP-12..spec-pyforge-core:CAP-14 and spec-pyforge-testing-charter:CAP-6..spec-pyforge-testing-charter:CAP-7, which this story's FR-250..FR-254 cite, CHAIN-STANDARD section 12.
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** At `82a2b18828` `SPEC.md` does not say what marshal is as built. Of 303 capabilities, 150 read shipped, 49 (CAP-244..CAP-292) read ready although every story citing them is done, 104 carry no marker, and CAP-293..CAP-297 read `(shipped; restored ...)` with no date. Only three marshal story keys are open: 108.2, 110.38 and 33.11. The two capabilities this change mints and the amendments its fix stories realize are in the memlog (2026-11-10) and not yet in `SPEC.md`, so the PRD cannot cite them (CHAIN-STANDARD section 12). Two story specs drifted from the ledger: spec-74-2 reads `in-review` and spec-46-2 `backlog`; both keys are done.

**Approach:** A docs story under spec-one-chain-per-station:CAP-6 and spec-one-chain-per-station:CAP-9 (CHAIN-STANDARD section 4). Write `research/cap-marker-truth-2026-11-10.md` (frontmatter `chain: pyforge-marshal`, `created`/`updated: 2026-11-10`; columns `| CAP | marker | open story keys | evidence | proposed ledger mode |`): for each capability, join its number and its `<- spec-old CAP-m` provenance to the `### Story` blocks of `epics.md`, read each story's ledger value, check the paths its text names with `git ls-files`, and date the marker from the ledger history (`git log --reverse -S'<key>: done' --format=%as -- sprint-status-ledger.yaml | head -1`) or, for a deleted artifact, from the deleting commit. Append one memlog `correction` entry carrying the markers by reference to the table, then render once through the anchored script (each anchor asserted to occur exactly once) and log both self-validate passes as memlog events. The render carries the memlog entries of 2026-11-10: spec-pyforge-marshal:CAP-304 and spec-pyforge-marshal:CAP-305 at `(ready 2026-11-10)`, the amendments of CAP-13, CAP-23, CAP-208, CAP-227, CAP-229 and CAP-261, core-kit Story 117.3's CAP-287 clause (appended by core-kit's mint), each of those seven amended capabilities at `(ready 2026-11-10)` while any of its fix stories is open and at `(shipped <date>)`, dated the day the last of them reached done, once all are done (memlog 2026-11-10, Marker of an amended capability, and its addendum), and `companions:` gaining `contract.md`. Then write the PRD requirements FR-246..FR-249 (FR-246 for the public contract, FR-247 for the suite as an oracle, FR-248 <- CAP-261, FR-249 <- CAP-227) and core-kit's FR-250..FR-254 in their own section with the cross-Spec colon form (once core-kit's Stories 117.5 and 118.2 have rendered the capabilities they cite), the body sentences of FR-59 (root of record), FR-126 (the six seed codes hold at the process boundary), FR-136 (guarded root) and FR-155 (registered tools equal the inventory), the FR-space line (FR-1..FR-254, no hole; FR-255 is the next free id), AD-7's sentence in the spine (the seed verb group keeps its own closed exit taxonomy), `updated:` of the commit day on the PRD and spine, and set the two drifted story specs to `done`.

Ledger key: `114-1-every-marshal-capability-carries-a-marker-that-matches-the-ledger-and-the-spec-records-this-change-s-two-capabilities-and-seven-amendments`. Type / Effort / Deps: docs / L / S-117.5, S-118.2.

## Boundaries & Constraints

**Always:**
- Every marker is one of `(ready <date>[; <qualifier>])`, `(shipped <date>[; <qualifier>])` or `(retired <date>[: <reason>])` (CHAIN-STANDARD section 4 as amended by steward:S-120.3).
- A capability reads ready only while a story citing it is open in the ledger.
- CAP-82 and CAP-93..CAP-96 read `(retired 2026-08-25: ...)` (the console's `data.js` and `generate.py`, deleted in `e07834580d`); CAP-80, CAP-81, CAP-84..CAP-86 and CAP-121 stay shipped (operator ruling of 2026-11-10).
- A capability no story built reads `(retired 2026-11-10: never built)` when no live `blocked` or `backlog` story carries it, and keeps its ready marker with ledger mode `B-only` when one does (operator ruling of 2026-11-10).
- CAP-13, CAP-23, CAP-208, CAP-227, CAP-229, CAP-261 and CAP-287 follow the rule above at this render: each reads `(ready 2026-11-10)` while any of its fix stories is open (115.3; 115.3; 115.4; 115.1; 115.1 and 114.2; 115.2; 117.3) and `(shipped <date>)`, dated the day the last of them reached done, once all are done (under the plan's CLOSE-LEDGERS step, none of them reads done at this render, so all seven read ready and Story 116.5 flips them). Their research-table rows list those keys; Story 116.5 flips the ones still ready to shipped; a correction of a capability's words alone (Story 114.2) moves no marker.
- Each `<-` tail and any text after a marker's date is kept.
- The table's last column is the input of steward:S-121.3, which regenerates the capability ledger; this story writes no ledger row.

**Never:**
- Never write a marker word other than ready, shipped or retired.
- Never hand-edit `SPEC.md`; never render without both self-validate passes logged.
- Never cite a capability in the PRD before the render defines it.
- Never write `updated:` ahead of the commit day; Story 116.5 re-stamps on its own day.
- Never touch `docs/governance/fr-baseline.json` or the capability ledger.

## Acceptance Criteria

- **AC1 — Every capability heading carries a marker in one of the three forms.**

  ```bash
  python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md').read();h=re.findall(r'^- \*\*CAP-\d+ — .*$',t,re.M);bad=[re.match(r'- \*\*(CAP-\d+)',x).group(1) for x in h if not re.search(r'\((shipped|ready) \d{4}-\d{2}-\d{2}[;)]|\(retired \d{4}-\d{2}-\d{2}[:)]',x)];print(len(h),bad);sys.exit(1 if bad else 0)"
  ```

  Expected: exit 0; prints `305 []` (at `82a2b18828`: 303 and 109 ids, exit 1).

- **AC2 — A capability reads ready only while a story citing it is open in the ledger, with no exception (spec-pyforge-marshal:CAP-304 and spec-pyforge-marshal:CAP-305 are checked against the stories that cite them: 114.1, 114.3 and 116.5, and 114.1, 116.1 to 116.4 and 116.5).**

  ```bash
  python3 -c "import re,sys,yaml;t=open('_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md').read();r={m.group(1) for m in re.finditer(r'^- \*\*(CAP-\d+) — .*\(ready \d{4}-\d{2}-\d{2}[;)]',t,re.M)};tab={l.split('|')[1].strip():l.split('|')[3] for l in open('_bmad-output/projects/pyforge-marshal/planning-artifacts/research/cap-marker-truth-2026-11-10.md') if l.startswith('| CAP-')};tab.update({'CAP-%d'%304:'114.1, 114.3, 116.5','CAP-%d'%305:'114.1, 116.1, 116.2, 116.3, 116.4, 116.5'});st={'.'.join(k.split('-')[:2]):v for k,v in yaml.safe_load(open('_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml'))['development_status'].items() if re.match(r'^\d+-\d+-',k)};bad=[c for c in sorted(r) if not any(st.get(k,'done')!='done' for k in re.findall(r'\b\d+\.\d+\b',tab.get(c,'')))];print(sorted(r),bad);sys.exit(1 if bad else 0)"
  ```

  Expected: exit 0; `bad` is `[]`. At this story's run the stories citing the two new capabilities (114.3 and 116.1 to 116.5, besides 114.1 itself) are open, so both read `(ready 2026-11-10)` under the same rule as every other capability; once Story 116.5 flips them they no longer read ready and the command does not consider them.

  ```bash
  python3 -c "import re,sys,yaml;t=open('_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md').read();st={'.'.join(k.split('-')[:2]):v for k,v in yaml.safe_load(open('_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml'))['development_status'].items() if re.match(r'^\d+-\d+-',k)};fix={13:['115.3'],23:['115.3'],208:['115.4'],227:['115.1'],229:['115.1','114.2'],261:['115.2'],287:['117.3']};want={c:('ready 2026-11-10' if any(st.get(k)!='done' for k in ks) else r'shipped \d{4}-\d{2}-\d{2}') for c,ks in fix.items()};n=[c for c,w in want.items() if not re.search(r'^- \*\*CAP-%d — .*\(%s[;)]'%(c,w),t,re.M)];print(n);sys.exit(1 if n else 0)"
  ```

  Expected: exit 0; prints `[]` (each of the seven amended capabilities reads `(ready 2026-11-10)` while any of its fix stories is open in the ledger and `(shipped <date>)` once all are done). At this story's run, under the plan's CLOSE-LEDGERS step, none of the seven fix stories reads done in the ledger, so the command expects all seven at `(ready 2026-11-10)`; because it derives each expectation from the ledger, it agrees with the first command and with the Always rule whichever fix stories read done when this story runs.

- **AC3 — The research table holds one row per pre-existing capability (column 3 the open story keys, `-` when none) and carries chain frontmatter.**

  ```bash
  test "$(grep -c '^| CAP-' _bmad-output/projects/pyforge-marshal/planning-artifacts/research/cap-marker-truth-2026-11-10.md)" = 303 && python3 -c "import yaml;fm=yaml.safe_load(open('_bmad-output/projects/pyforge-marshal/planning-artifacts/research/cap-marker-truth-2026-11-10.md').read().split('---')[1]);assert fm['chain']=='pyforge-marshal' and str(fm['created'])=='2026-11-10' and str(fm['updated'])=='2026-11-10'"
  ```

  Expected: exit 0.

- **AC4 — The two new capabilities and the companion are in the Spec.**

  ```bash
  test "$(grep -c '^- \*\*CAP-30[45] — ' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md)" = 2 && grep -q '^  - contract.md' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  ```

  Expected: exit 0.

- **AC5 — The PRD carries the nine new arrows.**

  ```bash
  python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md').read();w={'246':'CAP-%d'%304,'247':'CAP-%d'%305,'248':'CAP-261','249':'CAP-227','250':'spec-pyforge-core:CAP-12','251':'spec-pyforge-core:CAP-13','252':'spec-pyforge-core:CAP-14','253':'spec-pyforge-testing-charter:CAP-6','254':'spec-pyforge-testing-charter:CAP-7'};bad=[n for n,c in w.items() if not re.search(r'^#### FR-'+n+r':.*(←|<-) '+re.escape(c)+r'\b',t,re.M)];print(bad);sys.exit(1 if bad else 0)"
  ```

  Expected: exit 0; prints `[]` (FR-246..FR-249 marshal's, FR-250..FR-254 core-kit's; the plan's earlier FR-247..FR-255 numbering is superseded).

- **AC6 — The two drifted story specs read done.**

  ```bash
  grep -l "^status: 'done'" _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-74-2-*.md _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-46-2-*.md | wc -l
  ```

  Expected: prints 2.

- **AC7 — The landing allowlist names the new epics.**

  ```bash
  python3 -c "import tomllib,sys;e=tomllib.load(open('_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml','rb'))['epic_surfaces'];m=[k for k in ('114','115','116','117','118') if k not in e];print(m);sys.exit(1 if m else 0)"
  ```

  Expected: exit 0; prints `[]` (rows 114..116 written by the marshal mint, 117 and 118 by core-kit's).

- **AC8 — Planning detectors stay green.**

  ```bash
  pixi run -e pyforge-guild chain-completeness-check && pixi run -e pyforge-guild story-status-check && pixi run -e pyforge-guild status-body-consistency-check && pixi run -e pyforge-guild fr-without-cap-check && pixi run -e pyforge-guild ad-citation-check
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` (renders spec-pyforge-marshal:CAP-304, spec-pyforge-marshal:CAP-305 and the 2026-11-10 amendments); spec-one-chain-per-station:CAP-6 and spec-one-chain-per-station:CAP-9 (the marker sweep).

- Epic: Epic 114 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 114.1: Every marshal capability carries a marker that matches the ledger, and the Spec records this change's two capabilities and seven amendments`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The Spec says what marshal is, and its roots come from one place.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda.

## Notes

- Same-project dependencies: S-117.5 and S-118.2 (core-kit's renders of spec-pyforge-core and spec-pyforge-testing-charter); both sit in later epics, so the key is minted `blocked` (forward dependency) until both are done.
- Cross-station: the marker grammar is steward:S-120.3's amendment of CHAIN-STANDARD section 4; steward:S-121.3 regenerates the capability ledger from the swept Spec (the table's last column is its input) and steward:S-121.6 checks the markers.
- The memlog entries this story renders were appended by the mint on 2026-11-10 (direction, decision, two `capability` entries written with the qualified id, six `change` entries, the companion `event`, the marker-sweep and stale-names `direction` entries, and the chain-steps `event`). This story appends the marker `correction` entry and the two self-validate events. CAP-287's clause entry is core-kit's (Story 117.3's mint).
- Deferred rows this story's findings feed (written by Story 116.5): DW-marshal-114-1-1 (Story 55.1 has no tracked spec), DW-marshal-114-1-2 (140 story lines cite capabilities by their pre-fold Spec name).

## Spec Change Log

- 2026-11-10: minted at `blocked` (forward dependency: until S-117.5 and S-118.2 are done) by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10) and the memlog entries of `spec-pyforge-marshal` came first; `SPEC.md` is rendered by Story 114.1.
- 2026-11-11: fix pass after the third review of the mint. The Always clause's parenthetical now says that under the plan's CLOSE-LEDGERS step none of the seven fix stories reads done at this render. AC2 no longer exempts spec-pyforge-marshal:CAP-304 and spec-pyforge-marshal:CAP-305: it checks them against the stories that cite them, so it applies the Always rule to every capability and holds at the moment this story runs.

## Integrator note (BUILD-3 gate, 2026-11-11)

This story moved `spec-46-2` from `backlog` to `done`, which puts its `flag:` block in front of the flag gate. The gate then failed with `flag-key-not-in-tree`: `pyforge.marshal.context_bundle_digest` was never in `src/platform/config/flags.json` (`git log -S` finds no commit), and no tracked file reads it. Story 46.2 shipped without the flag it declared. This spec now carries `retires-flag:` for the key, the owning station's declaration that the gate reads (Story 34.7), so the done spec stays as the key's history.
