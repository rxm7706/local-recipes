---
title: '58.4: The branch''s baselines and governance reports are refreshed once, after every unit''s last edit'
type: 'chore'
created: '2026-11-10'
status: 'done'
story: 58-4-the-branch-s-baselines-and-governance-reports-are-refreshed-once-after-every-unit-s-last-edit
spec: spec-pyforge-doctor
difficulty: 'heavy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a check that judges; a gated gate is a silent green (spec-feature-flag-governance Q1; roster list)
surface:
  - 'scripts/.spec-surface-baseline.json'
  - 'docs/governance/fr-baseline.json'
  - 'docs/governance/flag-inventory/pyforge-*.md'
  - 'scripts/spec_surface_allowlist.txt'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml'
  - 'docs-site/src/content/ci-status.json'
  - '_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Stamps are valid only until the next edit of a Spec's surface, so the scoped spec-surface stamps, the baseline prune, the fr-baseline prune, the flag-inventory pages and mason's allowlist lines run once, last on the integration branch, and the PR bar sits here. Data only: every file is written by its own tool, none by hand. The hand-maintained `owners` rows of `docs/governance/fr-baseline.json` are left as they stand (`--prune` carries them unchanged): atlas Story 41.2, the earlier writer of the file, already replaced atlas's rows when it pruned the keys its retitle made stale.

**Approach:** Order: (1) `python scripts/spec_surface_check.py --prune`; (2) `spec-surface-check` lists the drifted Specs; (3) from a clean tree after `git add -A`, `python scripts/spec_surface_check.py --write-baseline --spec <project>/<spec>` once per Spec it names, never bare (a refusal for a path deleted long ago is accepted with `--accept <path>` only when `git log --diff-filter=D -1 -- <path>` shows the deletion on origin/main, each recorded with its commit here; a refusal for a path this PR changed goes back to the unit whose memlog must name it); (4) `python scripts/fr_baseline.py --prune`, which removes only what is still stale at the end of the branch (atlas Story 41.2, the earlier writer, pruned the 22 atlas `findings` keys its retitle made stale and wrote atlas's `owners` row at BUILD-3; no `owners` row is edited here); (5) `pixi run --frozen -e pyforge-guild flag-inventory`; (6) allowlist edits by content; (7) after a fetch, refresh `docs-site/src/content/ci-status.json` and reconcile it on herald's Spec surface; (8) re-stamp any Spec the steps touched last; (9) after the CLOSE-LEDGERS job, promote this story's own key through doctor's Tier-3 feed and `sprint-ledger-sync`; (10) the PR bar on that final head.

Ledger key: `58-4-the-branch-s-baselines-and-governance-reports-are-refreshed-once-after-every-unit-s-last-edit`.
Type / Effort / Deps: chore / L / S-56.1, S-56.2, S-56.3, S-56.4, S-56.5, S-57.1, S-57.2, S-57.3, S-58.1, S-58.2, S-58.3; cross-station: every other story of the integration branch (listed in the notes).

### Living CAP citations

- **`spec-pyforge-doctor` CAP-59** — the baseline's writer, whose `--prune` (Story 58.3) this story runs once.

## Boundaries & Constraints

**Always:**
- Edit the allowlist by content, never by line number; read every lane from its exit code, never through a pipe; run `pr-preflight` alone on the machine (the scribe lane shares one Postgres).
- Write each file through its own tool; scripts/.spec-surface-baseline.json only through the CAP-59 script; docs/governance/fr-baseline.json only through `--prune`, leaving every `owners` row as it stands (atlas's is Story 41.2's, the earlier writer).

**Never:**
- Never run a bare `--write-baseline`; never use `--allow-regression`; never hand-edit `sprint-status-ledger.yaml`.
- Never add new behaviour or a kill switch (ruling of 2026-11-10).

## Acceptance Criteria

- **AC1 — Every baseline key names a live Spec.** Expected: prints 0, exit 0 (166 before).

  ```bash
  python scripts/spec_surface_check.py --prune && python3 -c "import json,glob,re,sys;b=json.load(open('scripts/.spec-surface-baseline.json'));live={re.sub(r'^_bmad-output/projects/([^/]+)/planning-artifacts/specs/([^/]+)/SPEC.md$',r'\1/\2',p) for p in glob.glob('_bmad-output/projects/*/planning-artifacts/specs/*/SPEC.md')};dead=[k for k in b if '/' in k and k.split('/')[0].startswith('pyforge-') and k not in live];print(len(dead));sys.exit(1 if dead else 0)"
  ```

- **AC2 — The spec-surface detector is green on the whole tree.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild spec-surface-check
  ```

- **AC3 — The FR baseline holds no entry that no longer applies.** Expected: exit 0 for each, and the last prints `0`. The prune removes only what is still stale at the end of the branch; it names no `pyforge-atlas` `findings` key, because atlas Story 41.2, the earlier writer, pruned the 22 its retitle made stale at BUILD-3. After it, `fr-without-cap` reports no `fr-baseline-stale` for any station.

  ```bash
  python scripts/fr_baseline.py --prune && pixi run --frozen -e pyforge-guild fr-without-cap-check && pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap --json > "${TMPDIR:-/tmp}/frw.json" && python3 -c "import json,sys;n=sum(x['check']=='fr-baseline-stale' for x in json.load(open(sys.argv[1])));print(n);sys.exit(1 if n else 0)" "${TMPDIR:-/tmp}/frw.json"
  ```

- **AC4 — The flag-inventory pages are current and the generator is idempotent.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild flag-inventory && git add docs/governance/flag-inventory && pixi run --frozen -e pyforge-guild flag-inventory && git diff --exit-code -- docs/governance/flag-inventory
  ```

- **AC5 — Doctor's rows: none unknown or failing, and only the two sources a checkout may lack read unmeasured.** Expected: prints `30 [] [...]` (29 sources plus writer-lock), exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild python scripts/detectors.py --scope repo --json > "${TMPDIR:-/tmp}/doctor-detectors.json"; python3 -c "import json,os;r=json.load(open(os.environ.get('TMPDIR','/tmp')+'/doctor-detectors.json'))['results'];d=[x for x in r if x['path'].startswith('pyforge.doctor.sources:')];bad=[x['name'] for x in d if x['status'] in ('unknown','FINDINGS')];u=sorted(x['name'] for x in d if x['status']=='unmeasured');print(len(d),bad,u);raise SystemExit(0 if len(d)==30 and not bad and set(u)<={'platform-policy-suite','story-status'} else 1)"
  ```

- **AC6 — The PR bar on the final head (after CLOSE-LEDGERS and this story's own key).** Expected: exit 0 for each, read one at a time from its exit code (run pr-preflight alone on the machine: the scribe lane shares one Postgres; platform-ci-local replays Platform CI's test job and its three image builds; the guild image needs docker or podman).

  ```bash
  pixi run --frozen -e pyforge-guild detectors-ci && PYFORGE_PREFLIGHT_SCOPE=full pixi run --frozen -e pyforge-guild pr-preflight && pixi run --frozen -e pyforge-guild pyforge-station-tests && pixi run --frozen -e pyforge-guild platform-ci-local && pixi run --frozen -e pyforge-steward pyforge-steward-guild-image-build && CI=1 pixi run --frozen -e pyforge-atlas pyforge-atlas-test && HERALD_DOCS_SITE_REQUIRED=1 pixi run --frozen -e pyforge-herald pyforge-herald-test-built && pixi run --frozen -e pyforge-scribe-pg scribe-pg-up && pixi run --frozen -e pyforge-scribe pyforge-scribe-test && pixi run --frozen -e pyforge-guild test-ci-meta
  ```

- **AC7 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-58-4-*.md)"
  ```

- **AC8 — the allowlist drops the three claimed entries and the cfe comment, by content, and keeps the rest.** Expected: prints `[]`, exit 0.

  ```bash
  for e in scripts/detectors.py scripts/deck_export.py scripts/cfe_rebuild_guard_check.py; do test $(grep -c "^$e " scripts/spec_surface_allowlist.txt) -eq 0 || exit 1; done; test $(grep -c 'cfe_rebuild_guard_check.py IS contract-bound' scripts/spec_surface_allowlist.txt) -eq 0 && for e in scripts/pixi_version_registry.py scripts/pixi_version_check.py scripts/bump_pixi_version.py scripts/apply_verification_verdicts.py scripts/apply_actions_policy.py; do grep -q "^$e " scripts/spec_surface_allowlist.txt || exit 1; done; pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources spec-surface --json > "${TMPDIR:-/tmp}/ss.json"; python3 -c "import json,os,sys;f=json.load(open(os.environ.get('TMPDIR','/tmp')+'/ss.json'));b=[x['message'][:80] for x in f if x['status']=='fail'];print(b);sys.exit(1 if b else 0)"
  ```

- **AC9 — every station Frame's Derived line resolves (120.4's integration check).** Expected: prints [], exit 0.

  ```bash
  python3 -c "import re,glob,os;m=[(f,p) for f in glob.glob('docs/foundry/frames/stations/*.frame.md') for l in re.findall(r'(?m)^- Derived: (.*)$',open(f).read()) for p in re.findall(r'\x60([^\x60]+)\x60',l) if not os.path.exists(p)];print(m);raise SystemExit(1 if m else 0)"
  ```

- **AC10 — this story's own key is promoted after CLOSE-LEDGERS.** Expected: exit 0, then prints 1.

  ```bash
  pixi run --frozen -e pyforge-guild sprint-ledger-sync -- --project doctor && pixi run --frozen -e pyforge-guild story-status-check && grep -c '^  58-4-.*: done$' _bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml
  ```

- **AC11 — ci-status.json is refreshed at the final head after a fetch (operator chore delegated to the session, ruling of 2026-11-10).** Expected: exit 0; the file parses and carries rows; its `Surface reconcile` event is on spec-pyforge-herald's memlog and herald's Spec is re-stamped scoped.

  ```bash
  git fetch origin && pixi run --frozen -e pyforge-guild pyforge steward ci status --json > docs-site/src/content/ci-status.json; python3 -c "import json,sys;d=json.load(open('docs-site/src/content/ci-status.json'));sys.exit(0 if d.get('rows') else 1)"
  ```

- **AC12 — the FR baseline's atlas owner row still names what atlas carries after the final prune.** Expected: prints `True`, exit 0: `owners.pyforge-atlas` is exactly the one DW-atlas-46-1-9 row atlas Story 41.2 wrote (the earlier writer; this story leaves it as it stands), atlas has no `findings` key left (41.2 pruned the 22 `fr-duplicate-id` keys at BUILD-3), and its 48 `projects` ids survive this story's `--prune`.

  ```bash
  python3 -c "import json,sys;d=json.load(open('docs/governance/fr-baseline.json'));row='DW-atlas-46-1-9 (the retired Unity satellite\'s first-defined FR-23..FR-60 and NFR-1..NFR-10, held as history)';ok=d['owners'].get('pyforge-atlas')==[row] and not d['findings'].get('pyforge-atlas') and len(d['projects'].get('pyforge-atlas',[]))==48;print(ok);sys.exit(0 if ok else 1)"
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-59 (the prune it runs); no CAP minted or amended; none (data only).
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-10 (the cutover readiness audit) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § *Realization log*.
- Epic: Epic 58, minted with this story.
- Ledger key: `58-4-the-branch-s-baselines-and-governance-reports-are-refreshed-once-after-every-unit-s-last-edit` (`backlog`).
- Deps: S-56.1, S-56.2, S-56.3, S-56.4, S-56.5, S-57.1, S-57.2, S-57.3, S-58.1, S-58.2, S-58.3; cross-station: every other story of the integration branch (listed in the notes).
- Surface: `marshal-policy.toml` `[epic_surfaces]."58"`.
- Minted 2026-11-10 in the one chain commit of the integration branch `cutover-readiness-2026-11-10`, before any doctor story builds.

## Notes

- Last story on the integration branch. Cross-unit preconditions (named, not doctor keys): every unit's last edit has landed, in particular steward Story 121.3 (the regenerated ledger), steward-station's re-key of test_station_tests_trigger_map.py and its pixi.toml task, mason Story 37.1 (claims scripts/cfe_rebuild_guard_check.py), atlas Story 41.2 (atlas 41.3 retired at mint), and each unit's own `Surface reconcile` memlog lines.
- Allowlist edits by content: remove the entries `scripts/detectors.py` (doctor Story 57.3's surface claims it), `scripts/deck_export.py` (herald Story 50.2's surface claims it) and `scripts/cfe_rebuild_guard_check.py` (mason Story 37.1's surface claims it), and the three-line comment block that begins `# cfe_rebuild_guard_check.py IS contract-bound`; the pixi-version trio, the verdict applier, apply_actions_policy.py and every other entry stay.
- The PR bar on the final head: detectors-ci, a full pr-preflight, `pyforge-station-tests`, Platform CI's local twin, the guild-container build, atlas's browser gate under CI=1, herald's built-site check, scribe's Postgres lane and the CFE regression net's PR lane (Story 58.3 edits scripts/spec_surface_check.py, which triggers it). Its output is the recorded merge-bar evidence.
- Ownership: scripts/.spec-surface-baseline.json is on spec-pyforge-marshal's `surface:` but no baseline entry hashes it, so stamping drifts no Spec; doctor writes it only through its CAP-59 script, at the five units' request (marshal informed). A Spec `surface:` entry wins over an allowlist glob (chain.py `_governed_and_ungoverned` consults the allowlist only for files no Spec owns).
- fr-baseline.json has two writers on the branch, in order: atlas Story 41.2 (BUILD-3), then this story (BUILD-18). The rule is that the story that makes baseline keys stale prunes them: left here, the 22 atlas `findings` keys 41.2's retitle makes stale would keep doctor's live test `test_live_tree_fr_without_cap_has_no_fail_at_ruling_snapshot` red from BUILD-3 to BUILD-18. So 41.2 runs `--prune` (exactly those 22 keys) and replaces the two `owners.pyforge-atlas` rows with the one row `DW-atlas-46-1-9 (the retired Unity satellite's first-defined FR-23..FR-60 and NFR-1..NFR-10, held as history)`, and records in its own PRD reconciliation section that CAP-92's "every entry has an owner story" reads DW-atlas-46-1-9 as the owner of record for those 48 ids (their owner story 41.3 retired on 2026-11-10). This story's `--prune` removes only what is still stale at the end of the branch, edits no `owners` row (the marshal and mason rows, and atlas's, stay as they stand), and AC12 re-checks atlas's row. The file sits on no Spec's baseline (`docs/governance/**` is allowlisted), so no stamp follows either write.
- ci-status.json (ruling of 2026-11-10, the second addendum): refreshed at the final head after a fetch with `pixi run -e pyforge-guild pyforge steward ci status --json > docs-site/src/content/ci-status.json`, the operator-owned chore delegated to the session, and reconciled on herald's Spec surface (a `Surface reconcile` event on spec-pyforge-herald's memlog naming the file, then herald's scoped stamp) — the one reconcile line this story writes outside doctor's Spec.
- Cross-station deps (every other built story of the branch): warden:S-25.1, warden:S-25.2, warden:S-25.3, warden:S-25.4, warden:S-26.1, warden:S-26.2, warden:S-26.3, warden:S-27.1, steward:S-29.5, scribe:S-31.1, scribe:S-31.2, scribe:S-31.3, scribe:S-31.4, scribe:S-32.1, scribe:S-32.2, scribe:S-32.3, scribe:S-33.1, scribe:S-33.2, mason:S-37.1, mason:S-37.2, mason:S-37.3, mason:S-37.4, mason:S-38.1, mason:S-38.2, mason:S-38.3, mason:S-39.1, atlas:S-41.2, atlas:S-46.1, atlas:S-46.2, atlas:S-47.1, atlas:S-47.2, atlas:S-48.1, atlas:S-48.2, atlas:S-48.3, atlas:S-48.4, herald:S-50.1, herald:S-50.2, herald:S-50.3, herald:S-50.4, herald:S-51.1, herald:S-51.2, herald:S-52.1, herald:S-52.2, marshal:S-114.1, marshal:S-114.2, marshal:S-114.3, marshal:S-115.1, marshal:S-115.2, marshal:S-115.3, marshal:S-115.4, marshal:S-116.1, marshal:S-116.2, marshal:S-116.3, marshal:S-116.4, marshal:S-116.5, marshal:S-117.1, marshal:S-117.2, marshal:S-117.3, marshal:S-117.4, marshal:S-117.5, marshal:S-117.6, marshal:S-117.7, marshal:S-117.8, marshal:S-118.1, marshal:S-118.2, steward:S-120.1, steward:S-120.2, steward:S-120.3, steward:S-120.4, steward:S-120.5, steward:S-121.1, steward:S-121.2, steward:S-121.3, steward:S-121.4, steward:S-121.6, steward:S-121.7, steward:S-122.1, steward:S-122.2, steward:S-122.3, steward:S-122.4, steward:S-122.5, steward:S-123.1, steward:S-123.2, steward:S-123.3, steward:S-124.1, steward:S-124.2, steward:S-124.3, steward:S-124.4, steward:S-124.5. Steward 121.5, mason 39.2 and the retired 44.1 and atlas 41.3 are minted blocked and are not dependencies.
- Rulings of 2026-11-10 applied (`docs/dreams/pyforge-unifying-strategy.md` § Realization log, the second addendum, 'Accept all, run mint'): a source that measured nothing reads `unmeasured`, a warning the merge bar does not fail on; `doctor flags kill-switch` stays Doctor's one actuator; doctor's closed one-time campaigns retire; the marker grammar is CHAIN-STANDARD section 4 as steward Story 120.3 amends it (`(retired <date>[: <reason>])` and semicolon qualifiers, no `(unbuilt)` token); the operator flips `pyforge.cutover_root` by hand once the Launch slice is proven, and nothing flips it automatically.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code (never through a pipe).

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check` — expected: exit 0 each.

## Spec Change Log

- 2026-11-10: minted from the station Dream's 2026-11-10 entry (the cutover readiness audit) and the operator's rulings of 2026-11-10.
- 2026-11-10: step (4) gains the hand edit of fr-baseline.json's atlas `owners` rows (one DW-atlas-46-1-9 row after the prune; atlas's request, routed by the branch orchestrator), the Intent and Always lines name it as the one hand edit, and AC12 checks it.
- 2026-11-11 (orchestrator decision: the story that makes baseline keys stale prunes them): the atlas prune and the atlas `owners` row move to atlas Story 41.2, the earlier writer of fr-baseline.json (BUILD-3), because 22 stale keys left for this story would keep doctor's live fr-without-cap test red from BUILD-3 to BUILD-18 and break Stories 56.4, 58.1, 58.2 and 57.3's AC13. Step (4) now prunes only what is still stale at the end and edits no `owners` row; the doctor-memlog event about that row is dropped (41.2's PRD reconciliation section records it); the Intent and Always lines say there is no hand edit; AC3 also checks that no `fr-baseline-stale` remains; AC12 re-checks the row 41.2 wrote.

## Review findings (build, round 1, 2026-11-13)

The independent review of the first attempt failed the story on four findings. Each is stated as the reviewer wrote it, then what round 1 did about it.

1. **Blocker. Where: AC6, the PR bar on the final head (head 940ccc6941 plus the staged 58.4 diff).** AC6 is red, and the spec names no later story that owns it. `detectors-ci` exits 1: `flag_gate_check` reports `flag-test-not-two-state` on steward's `spec-121-1-a-generator-derives-the-capability-ledger-from-the-live-specs.md`. Doctor's `test_live_tree_every_doctor_epics_status_matches_the_ledger` fails because 12 epics.md `**Status:**` lines for 56.1 to 58.4 read `backlog` or `blocked` while the ledger reads `done`. 58.4's own line is one of them since AC10's promotion. `test-ci-meta`'s `test_live_tree_has_no_bare_retired_skill_ids` fails on marshal epics.md lines 11374 and 11376, minted in 66a1d3ce24. The full pr-preflight also showed atlas's `test_epics_per_story_status_matches_sprint_ledger` red, and doctor's and atlas's coverage gates did not run.
   - Round 1 confirmed all four on head 940ccc6941, each run alone with exit 1. `flag-gate-check --spec` on the 121.1 spec gives verdict `red`. Its last writer is the CLOSE-LEDGERS commit db952dbbff, which made the spec `done`, and that is when the gate starts asking for the two-state test. The doctor module fails 1 and passes 3. The CFE meta module fails 1 and passes 8. Atlas `-k test_epics_per_story_status_matches_sprint_ledger` fails 1.
   - Every cause sits in a file outside this story's files_owned: the 121.1 story spec, each station's epics.md and marshal's epics.md. This round does not edit them. As the reviewer's fix says, they belong to the integrator:
     - (a) Name `src/shared/packages/pyforge-steward/tests/unit/test_cutover.py` in the 121.1 story spec's `## Verification`. That module carries `@flag_states("pyforge.steward.cutover_ledger_write")`.
     - (b) After CLOSE-LEDGERS, align every station's epics.md `**Status:**` lines with its ledger. The reviewer's counts: atlas 9, doctor 12 (58.4 included), herald 8, marshal 22, mason 8, scribe 9, steward 25 plus 44.4 to 44.6, warden 8.
     - (c) Give the two bare `bmad-dev-auto` mentions in marshal's epics.md a same-line gloss.
     - (d) Write a memlog line before any of these edits moves a governed path, then re-stamp scoped.
   - AC6 stays red until (a) to (d) land. Its PR does not merge before every AC6 leg re-runs green on the final head. The round 1 re-run of each leg is recorded below.
2. **Major. Where: `scripts/.spec-surface-baseline.json`, the scoped stamps of `pyforge-mason/spec-pyforge-mason`, `pyforge-doctor/spec-pyforge-doctor` and `pyforge-herald/spec-pyforge-herald`.** The stamps accept steward Story 124.2's edits (84fa9d8c13, 2026-11-12) to governed test files. No memlog line written after those edits names them, so each stamp is a stamp without a reconcile (AGENTS.md pre-PR item 5).
   - Mason: `tests/meta/test_adapter_sole_caller.py` and `tests/unit/test_errors.py`. The first attempt's own check listed both (`not-named-on-branch=2`) and stamped anyway.
   - Doctor: `tests/unit/test_sources_writer_lock.py`.
   - Herald: `tests/meta/test_preflight_pages_lane.py`.
   - The stamp gate did not refuse, because it matches a path anywhere in a memlog that moved.
   - **Round 1 verdict.** The reviewer is right, and one more path has the same gap: herald's `tests/meta/test_built_site_tests_install_first.py`. 124.2 rewrote its CI test to read the `herald-live-test` job. The Story 52.1 event that names that path narrates Story 124.1's edit, and the integrator's 2026-11-13 event names it only as a test run. Round 1 checked every path this story's stamps moved: for each, does a memlog line added at or after the path's last branch commit name it (full path)? The check also read the 124.2 lines on spec-pyforge-core, spec-pyforge-marshal, spec-pyforge-testing-charter, spec-pyforge-scribe and spec-pyforge-unifying-strategy. It found no other gap.
   - **Doctor (fixed).** Round 1 appended a `Surface reconcile` event to spec-pyforge-doctor's memlog with `uv run _bmad/scripts/memlog.py append`. It names 124.2's edit of `test_sources_writer_lock.py`: tracked-path literals spelled as joins, each equal to the literal it replaces. That module: 20 passed. The scoped stamp `--write-baseline --spec pyforge-doctor/spec-pyforge-doctor` then exited 0.
   - **Herald (fixed).** Round 1 appended one event to spec-pyforge-herald's memlog. It names 124.2's edits of `test_preflight_pages_lane.py` and `test_built_site_tests_install_first.py`. Both modules: 22 passed. The scoped stamp `--spec pyforge-herald/spec-pyforge-herald` then exited 0. That memlog is on this story spec's `surface:`. plan.json's files_owned routes only the ci-status reconcile there.
   - Both stamps moved only the Spec's memlog hash, no file hash.
   - **Mason (not fixed here).** spec-pyforge-mason's memlog is on neither this story's files_owned nor its `surface:`, so round 1 does not write it. The integrator, or 124.2's unit, appends the event and then re-stamps `pyforge-mason/spec-pyforge-mason` scoped. Until then, mason's stamp still accepts the two paths without a reconcile line. Both modules pass now: 282 passed in `-e pyforge-mason`. Suggested event text: "Surface reconcile 2026-11-13: src/shared/packages/pyforge-mason/tests/meta/test_adapter_sole_caller.py and src/shared/packages/pyforge-mason/tests/unit/test_errors.py were last edited by steward Story 124.2 (build commit 84fa9d8c13, 2026-11-12). The edit spells `_CFE_PATH_SUBSTRING` and one assertion's `.claude/scripts/conda-forge-expert` literal as `"/".join((".claude", "scripts", "conda-forge-expert"))`, with a comment saying why: steward's trigger-map scan counts a bare tracked-path literal as a read of the live tree, and these modules read none. Each joined string equals the literal it replaces, so no assertion changes meaning and no mason source moves."
3. **Minor. Where: `scripts/spec_surface_allowlist.txt`, the section header `# --- pixi-version enforcement trio + verdict applier + rebuild guard (2026-08-21)`.** The rebuild-guard entry and its comment are gone, but the header still names the guard, so the line is stale.
   - Round 1 does not fix it. files_owned limits this story's allowlist edits, by content, to the three named entries and the three-line cfe comment block, and the reviewer agrees that leaving the header was right.
   - Dropping ` + rebuild guard` needs an integrator ruling that widens that content scope.
4. **Minor. Where: doctor's ledger (`58-4` done, `epic-58` done) and this spec's frontmatter `status: 'done'`.** The spec runs AC10's promotion before the PR bar, so the story and epic read done while AC6, the merge-bar evidence, is red. The done state is not yet earned.
   - Round 1 keeps the promotion, as the reviewer's fix says. Status is not this round's to change.
   - The PR lands only after AC6 re-runs green on the final head. If a red this story owns remains then, the key rolls back through doctor's Tier-3 feed and `sprint-ledger-sync`, never by hand.
   - None of the reds round 1 found is in this story's files (finding 1).

Where the reviewer is wrong: on substance, nowhere. One correction: the herald gap is two paths, not one (finding 2).

## Integrator ruling (2026-11-13, before the chunk-10 retry)

The integrator stopped the chunk-9 run during fix round 1 and did the items round 1 named as the integrator's. The retry starts from that state.

1. **Finding 1 (a) to (d): done in commit df2a292e18.**
   - (a) The 121.1 story spec's `## Verification` now names `src/shared/packages/pyforge-steward/tests/unit/test_cutover.py`. `flag-gate-check --spec` on it gives verdict `pass`, and the whole-tree `flag-gate-check` exits 0.
   - (b) Every station's epics.md `**Status:**` lines now match its tracked ledger: 104 lines. That is the 100 CLOSE-LEDGERS stories plus 58.4 set to `done`, and steward 44.4 to 44.6 set to `blocked (retired 2026-11-10, never dispatched)`. A rescan with doctor's join finds 0 mismatches on all eight stations. Doctor's `test_epics_status_tracks_the_ledger.py` passes (4) and atlas's `test_planning_record.py` passes (9).
   - (c) The two bare `bmad-dev-auto` mentions on marshal epics.md lines 11374 and 11376 carry a same-line gloss. `test_no_retired_bmad_skill_ids.py` passes (9).
   - (d) No path a Spec's surface hashes moved: epics.md and story specs are on no hashed surface. `spec-surface-check` exits 0.
   - The commit also adds a dated unblock note under each of the 31 forward-dependency banners, whose story specs now read `done`.
2. **Finding 2, mason: done.** Commit df2a292e18 appends a `Surface reconcile` event to spec-pyforge-mason's memlog naming both mason test paths and 124.2's edit. The scoped re-stamp `--write-baseline --spec pyforge-mason/spec-pyforge-mason` then moved only that Spec's memlog hash. The re-stamp sits uncommitted in `scripts/.spec-surface-baseline.json` and rides this story's gate commit with the rest of that file.
3. **Finding 3: done, uncommitted.** The allowlist header now reads `# --- pixi-version enforcement trio + verdict applier (2026-08-21)`. This ruling widens the story's allowlist scope by that one header line. It rides this story's gate commit.
4. **Finding 4: unchanged.** The promotion stays. AC6 on the final head decides whether the done state holds. A red this story owns rolls the key back through doctor's Tier-3 feed and `sprint-ledger-sync`.
5. **After the integrator's work:** `detectors-ci` exits 0 on the working tree (head df2a292e18 plus this story's staged diff).
6. **What the retry does.** Keep the work on disk; it is right. Re-run every AC on the current head. AC1 to AC5 and AC7 to AC12 should be no-ops or idempotent re-runs. Run AC6's full pr-preflight once, alone, after the last edit, with TMPDIR off tmpfs. Read every verdict from its exit code. If a lane is red for a cause outside this story's files, name the failing test and the file, and stop; do not edit outside the files this story owns.
