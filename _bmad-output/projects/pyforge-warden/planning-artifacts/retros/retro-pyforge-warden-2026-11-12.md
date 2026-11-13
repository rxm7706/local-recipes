---
title: 'pyforge-warden — Retrospective (2026-11-12: Epics 25 to 27, the cutover readiness change)'
project: pyforge-warden
created: '2026-11-12'
updated: '2026-11-12'
epics: [25, 26, 27]
date: '2026-11-12'
verdict: rejected
criteria: declared
headless: true
scope: 'Epics 25, 26 and 27 of the single cutover-readiness PR (branch cutover-readiness-2026-11-10): the warden chain says what the code does (Epic 25), the public contract is one companion held by a test (Epic 26), and the live-tree readers run as their own half (Epic 27, a relay of spec-pyforge-steward:CAP-175). Written by bmad-retrospective, headless, as Story 25.2''s close step. The package pyproject.toml moved on 2026-11-11 (6a48762004, Story 27.1), so this is the code->retro retrospective the chain-currency sweep owes.'
evidence:
  - 'range e48d98cdeb^..HEAD on cutover-readiness-2026-11-10 (HEAD bf0b000be4 at the time of reading): 50 commits, 0 merges (merge_count 0, merges_measured 0); scripts/git_evidence.py output kept in the build scratch folder'
  - 'story commits: e48d98cdeb (the mint), 6a48762004 (25.1, 25.3, 25.4, 26.1, 26.3, 27.1; waves BUILD-1 and BUILD-2), fd92346310 (26.2, BUILD-3); bf0b000be4 (steward 124.3, the package pixi.toml floor); Story 25.2 is uncommitted at the time of writing (the wave gate commits it)'
  - 'sprint_status.py detect-epic --epic 25, 26 and 27 on implementation-artifacts/sprint-status.yaml (2026-11-12)'
  - 'pixi run --frozen -e pyforge-warden pyforge-warden-test (2251 + 264 passed) and pyforge-warden-live-test (148 passed), 2026-11-12'
---

# pyforge-warden — Retrospective, Epics 25 to 27 (2026-11-12)

## Epic summary

- **Epics:** 25 (*The warden chain says what the code does*), 26 (*Warden's public contract is one companion, held by
  a test*), 27 (*Warden's live-tree readers run as their own half*), all minted 2026-11-10 in `e48d98cdeb` from the
  station Dream's entry of that date (`docs/dreams/pyforge-warden.md`, Realization log, *2026-11-10 (the cutover
  readiness audit)*) and the operator rulings of 2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md`, Realization
  log, second addendum).
- **Diff range:** `e48d98cdeb^..HEAD`: 50 commits, no merges, no binary revisions on a warden path. 44 warden-related
  paths changed; under the package, 17 (`git diff --name-only origin/main...HEAD -- src/shared/packages/pyforge-warden`).
- **Stories built and reviewed on the branch:** 25.1, 25.3, 25.4, 26.1, 26.3 and 27.1 (`6a48762004`, waves BUILD-1 and
  BUILD-2), 26.2 (`fd92346310`, BUILD-3). Each build commit records an independent review and a wave gate. Story 25.2 is
  the story writing this document (BUILD-14). The cross-station dependencies landed first: steward 121.7 (`d2951f07fd`,
  the capability ledger's warden rows) and steward 124.3 (`bf0b000be4`, the package `pixi.toml` floor).
- **Stories not `done` in the feed** (`sprint_status.py detect-epic --epic <n>` on
  `implementation-artifacts/sprint-status.yaml`, 2026-11-12): Epic 25: 25-1, 25-2, 25-3, 25-4; Epic 26: 26-1, 26-2,
  26-3; Epic 27: 27-1. The tracked ledger reads the same (five `backlog`, three `blocked`; 76 of 84 stories done). The
  change's ledger close promotes every key, after this retro.
- **Evidence inventory.** Available: `planning-artifacts/epics.md` § Epic 25 to § Epic 27, the eight story specs
  (`planning-artifacts/specs/spec-25-*` to `spec-27-*`), the build commits, the gate records two story specs carry
  (25.4 and 26.3 § *Gate findings*), the Spec memlog, both suite halves and the three contract tests run today.
  Missing: the build agents' session logs (not kept in the tree), so process lessons come from the gate records and
  the commits, nothing else.

## Findings

Each finding carries its source and two dispositions: this instance (fix now / defer / accept), and what prevents the
next one.

### Spec-to-implementation reconciliation

1. **The chain said what the Spec said before the change, and Story 25.2 closes it.** Source: the audit
   (`research/cutover-readiness-audit-2026-11-10.md`, MUST 4 and 5, NICE *Spine*) and the pre-change text: PRD NFR-C1,
   the spine's two floor lines and the epics *Portability* line read Python 3.12 against `pyproject.toml`'s
   `requires-python = ">=3.14"`; NFR-S9 and the epics S9 item claimed an age for the conda-to-pypi map, which carries
   none (`data/conda_pypi_map.json`, `mapping.py`); Journey 4 named the unbuilt `review_required`; the spine's tree
   listed `determinism.py`, `errors.py` and `tests/conformance/`, and lacked `sast.py` and `native_lockfiles.py`.
   *Instance:* fixed now by Story 25.2 (PRD § Currency reconciliation — 2026-11-10 (Story 25.2); spine § Currency
   reconciliation — 2026-11-10; epics § Currency reconciliation — 2026-11-10 (Story 25.2)). *Next:* a story that
   re-derives a Spec Constraint names, in its own acceptance, the PRD and spine lines that restate it; 25.1 and 25.2
   split that by artifact, which held only because 25.2 depended on 25.1.
2. **NFR-R3.2 contradicted the capability it cites.** Source: PRD NFR-R3.2 (before this pass) had the opt-in
   `--deterministic` mode reach byte-identical output "by pinning a documented volatile-field set (report/SBOM
   timestamps, CycloneDX `serialNumber`/`bom-ref` ...)", while `spec-pyforge-warden` CAP-10's success (re-derived
   2026-11-10) says the flag changes nothing and the SBOM's `serialNumber` and `metadata.timestamp` differ run to run
   (`cli.py:56-58`, `sbom.py:36-40`). The story spec named the spine's 2026-08-26 sentence but not this PRD line.
   *Instance:* fixed now in Story 25.2 (healed tissue in a file it owns; recorded in the PRD's Story 25.2 section).
   *Next:* the audit grep for a removed claim (here "volatile-field") runs over every chain artifact, not only the one
   the finding was read in.
3. **CAP-28 reads shipped once its three stories are built.** Source: `SPEC.md` CAP-28 heading (now
   `(shipped 2026-11-11)`), the Story 25.2 capability entry and two self-validate events in `.memlog.md`, and
   `tests/meta/test_public_contract.py`, `tests/meta/test_contract_surface.py`, `tests/meta/test_capability_proof_map.py`
   (119 passed, 2026-11-12). *Instance:* accept. *Next:* nothing.
4. **What the change left unbuilt is ledgered, not hidden.** Source: `deferred-work-ledger.md`
   DW-warden-cutover-2026-11-10-1 to -13 (Story 25.4): the map's age, `--deterministic` pinning, the untyped
   `advisory` and `actuation` slots, the engine ranges, the LTS registry's 2027-01-02 cliff, 102 untriaged EGM
   findings, the spine's missing AD-n, the `django-warden` surface, and CAP-16 and CAP-17 proofs. *Instance:* defer
   (each row carries its owner and severity). *Next:* nothing; this is the rule working.

### Story boundaries (diff-scope review, inline)

5. **Five `live_tree` modules derive the repository root at import, so a shallow export cannot collect the package
   half.** Source: `tests/meta/test_public_contract.py:59` and `tests/meta/test_contract_surface.py:75` (Stories 26.1
   and 26.3), `tests/integration/test_pixi_lock_environment_scope.py:19`, `tests/unit/test_currency_cfe_parity.py:22`
   and `tests/integration/test_fix_solver_real_pixi.py:29` (Story 27.1) each evaluate `Path(__file__).resolve().parents[6]`
   at module level. The package half selects with `-m "not slow and not live_tree"` (`pixi.toml`,
   `[feature.pyforge-warden.tasks.pyforge-warden-test]`), and pytest imports a module before it deselects it, so an
   export of the package to a path fewer than seven components deep raises `IndexError` at collection
   (`Path('/tmp/x/pyforge-warden/tests/unit/f.py').parents[6]` raises it). Story 26.2's module computes the root inside
   a function for exactly this reason (`tests/meta/test_capability_proof_map.py:315`, its docstring says so).
   `tests/meta/test_pixi_range_floor_matches_workspace.py:31` climbs from `pyforge.warden.__file__` the same way.
   In this checkout every module collects (both halves green), so the failure needs an export. *Instance:* defer, low:
   the fix touches 27.1's and 26.x's test modules, outside Story 25.2's files; recorded in Story 25.2's
   *Planned deferral* section for the ledger row. *Next:* `tests/meta/test_live_tree_marker.py` (Story 27.1's guard)
   also fails a module-level climb above the package root, so the rule the build briefs state is checked, not asserted.
6. **The two contract tests carry the same eight table helpers.** Source: `_both_ways`, `_inject_row`, `_keyed_rows`,
   `_missing_cap`, `_plain`, `_rows`, `_section`, `_tokens` are defined in both `tests/meta/test_public_contract.py`
   (Story 26.1) and `tests/meta/test_contract_surface.py` (Story 26.3); Story 26.2's module has its own `_section` and
   `_table_rows`. The two stories split `contract.md` by section and were built in the same wave. *Instance:* accept:
   the copies agree today and both tests pass; a shared helper is a refactor no story carries. *Next:* when one
   companion is split across stories, the first story's spec names the helper module the second imports.
7. **README, `__init__.py` and `pixi.toml` all point at the live Spec, across two stations.** Source: Story 25.3's
   `README.md` and `src/pyforge/warden/__init__.py` diffs (`6a48762004`) and steward 124.3's `pixi.toml` diff
   (`bf0b000be4`, the header comment the warden plan ceded); `git grep -l docs/specs/pyforge-warden.md --
   src/shared/packages/pyforge-warden` is empty (AC14 of Story 25.2). *Instance:* accept. *Next:* nothing.

### Aggregate views

8. **Size growth is test-side only.** Source: `git_evidence.py` `files`: `test_contract_surface.py` +1111,
   `test_public_contract.py` +972, `test_capability_proof_map.py` +527, `test_live_tree_marker.py` +527; no module under
   `src/pyforge/warden/` changed beyond `__init__.py`'s docstring (+3/−3). *Instance:* accept: each is a derivation
   test whose size is its inventory of derivation rules (each module's docstring states them). *Next:* see finding 6.
9. **Architecture delta: none.** Source: no import under `src/pyforge/warden/` changed (the diff touches the package
   only in docstrings, the manifests and tests); the spine's § Currency reconciliation — 2026-11-10 records no AD
   moving. *Instance:* accept.
10. **Pattern divergence: the story's own pattern was followed.** Source: every new test module carries
    `pytestmark = pytest.mark.live_tree` when it reads outside the package (`test_live_tree_marker.py` holds it; the
    live half passes 148 tests). *Instance:* accept, apart from finding 5.

### Process (from the gate records and the commits)

11. **Two bare AD citations reached the wave gate.** Source: `spec-25-4-*.md` § *Gate findings (build, BUILD-1)* (the
    `verified:` line of DW-warden-cutover-2026-11-10-7 cited two suite-spine ADs unqualified) and `spec-26-3-*.md`
    § *Gate findings (build, BUILD-2)* (a `contract.md` row copied a bare AD id from `tea_advisory.py`'s docstring).
    Both were fixed at the gate. *Instance:* accept (fixed). *Next:* a story whose text cites an AD carries
    `ad-citation-check` in its acceptance list; neither story did.
12. **Forward-dependency stories needed the operator's consent to build.** Source: `72f3e3158f` (the recorded
    consent) and the three `blocked` keys (25.2, 25.3, 26.2). The consent held the order; no story built ahead of its
    dependency. *Instance:* accept. *Next:* nothing.

## Behavior verification

The change moved no runtime behaviour (documentation, manifests and tests only; finding 9). What was exercised on
2026-11-12, from the repository root:

- `pixi run --frozen -e pyforge-warden pyforge-warden-test`: exit 0 (2251 passed in the unit + meta segment, 264 in
  the rest of the package half).
- `pixi run --frozen -e pyforge-warden pyforge-warden-live-test`: exit 0 (148 passed).
- `pytest tests/meta/test_public_contract.py tests/meta/test_contract_surface.py tests/meta/test_capability_proof_map.py`
  under `-e pyforge-warden`: 119 passed, before and after CAP-28's marker render.
- `pixi run -e pyforge-guild capability-ledger-check`: exit 0 (923 live CAP extracts match 923 rows).

`warden scan` itself was not run end to end in this retro: no scan code moved.

## Previous-retro follow-through

The previous retro is `retros/retro-pyforge-warden-2026-09-20.md` (the fleet lint and type gate). It records two
carry-forward lessons and no tracked action items; `implementation-artifacts/sprint-status.yaml` carries no
`action_items` key at all, so nothing is addressable by id. Its one open note, the `call-arg` mypy baseline to fix
"when that module is next touched", still stands (`pyproject.toml:120`, `disable_error_code = ["call-arg"]`); no
module it covers was touched by Epics 25 to 27, so no evidence it landed and no status to propose.

## Action items

| # | Action | Owner | Kind |
|---|---|---|---|
| 1 | Compute the repository root inside a fixture or function in the five `live_tree` modules of finding 5, and have `tests/meta/test_live_tree_marker.py` fail a module-level climb above the package root | warden (a story of its own; ledger row from Story 25.2's *Planned deferral*) | proposed remediation |
| 2 | Promote the eight keys of Epics 25 to 27 (and `epic-25`..`epic-27`) once the PR lands | the change's ledger close | tracking |
| 3 | A story that cites an AD lists `ad-citation-check` in its acceptance criteria | station planners (the mint template) | process lesson |
| 4 | When one companion is split across stories, the first story names the shared helper module the second imports | station planners | process lesson |

## Acceptance verdict

**Machine verdict: rejected** (criteria declared: each story spec's acceptance criteria, and Story 25.2's for the
chain close). Every story is built and reviewed on the branch and Story 25.2's acceptance checks run green except
where they wait on this retro and the readiness report, but `pending_stories` is non-empty for all three epics: 25-1,
25-2, 25-3, 25-4, 26-1, 26-2, 26-3 and 27-1 are not `done` in the feed until the change's ledger close. By the
skill's rule an unfinished story forces **rejected** in a headless run; a human may override after the ledger close.
No blocking finding stands: finding 5 is low and deferred, findings 1 and 2 are fixed.

## Open questions

- Should a package-half export test run in CI (copy the package to a shallow path, collect with
  `-m "not live_tree"`)? It would turn finding 5 from a rule into a check; spec-pyforge-steward:CAP-175 owns the split.

## Assumptions

- Epics 25, 26 and 27 were taken from the invocation (`-H`), not auto-detected; `detect-epic --epic 25|26|27`
  returned story counts 4, 3 and 1 and the pending lists above.
- The machine verdict is **rejected** because `pending_stories` is non-empty; no human decision was taken.
- The sprint-status update of Phase 5 was **not** run: the build's rules forbid this story from writing a Tier-3 feed
  or a ledger, and the change's ledger close owns `epic-25-retrospective`..`epic-27-retrospective`. No
  `--set-action-status` transition is proposed (there are no prior action items).
- `bmad-review` was not invoked: each story had an independent review and a wave gate at build (the build commits say
  so), and the diff-scope review above ran inline over the story boundaries, the package diff and the gate records.
- Session logs were not available; process findings come from the gate records and commits only.
- The four action items are proposals; none is applied by this retro.
