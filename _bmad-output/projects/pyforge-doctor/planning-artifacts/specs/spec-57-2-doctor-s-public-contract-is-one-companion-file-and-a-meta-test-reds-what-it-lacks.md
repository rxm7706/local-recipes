---
title: '57.2: Doctor''s public contract is one companion file, and a meta-test reds what it lacks'
type: 'feature'
created: '2026-11-10'
status: 'backlog'
story: 57-2-doctor-s-public-contract-is-one-companion-file-and-a-meta-test-reds-what-it-lacks
spec: spec-pyforge-doctor
difficulty: 'heavy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: docs-only   # prose and planning artifacts only; the capabilities it writes down are existing code (spec-feature-flag-governance Q2; roster list)
surface:
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/contract.md'
  - 'src/shared/packages/pyforge-doctor/tests/meta/test_public_contract.py'
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

**Problem:** Decision D1: the station records its public contract in contract.md beside SPEC.md, and a meta-test in its own tests/meta fails when the code has a verb, flag, MCP tool, flag key, environment variable or diagnostic the file lacks.

**Approach:** Hand-written contract.md (no generator, no CLI verb) with the thirteen sections the acceptance names; a live-tree meta-test compares it with the code both ways. A new computed `check=` site must be added to the table or the test fails, so 'every diagnostic' holds without refactoring 19 call sites. `companions: contract.md` enters the Spec frontmatter in Story 57.3's re-derive.

Ledger key: `57-2-doctor-s-public-contract-is-one-companion-file-and-a-meta-test-reds-what-it-lacks`.
Type / Effort / Deps: feature / L / S-56.1, S-56.2, S-56.3, S-56.4, S-56.5.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-97** — Doctor's public contract is written once, and the package-local half is the oracle (minted 2026-11-10).
- **`spec-pyforge-unifying-strategy:CAP-20`** — the MCP start tools django-doctor serves (start_scan, get_scan, run_scan).

## Boundaries & Constraints

**Always:**
- Read explicit paths (no root hand-off); mark the module `pytestmark = pytest.mark.live_tree`.
- List the ten FR-15 sources under CAP-93 and each later Source under its own capability or the qualified outcome it mechanizes (fold-complete spec-one-chain-per-station:CAP-11, chain-sprawl spec-one-chain-per-station:CAP-2, capability-ledger CAP-95 and CAP-87).

**Never:**
- Never generate contract.md or add a CLI verb for it; never change a source to fit the table.
- Never hand-edit `SPEC.md` (memlog, then `bmad-spec` or the anchored script render with both self-validate passes logged); never append a `Surface reconcile` line to another Spec's memlog or run `spec_surface_check.py --write-baseline` (Story 58.4 stamps every Spec once, last on the branch); never add new behaviour or a kill switch beyond this story's capability text (operator ruling of 2026-11-10: each gap is a deferred-work row).

## Acceptance Criteria

- **AC1 — The contract has every section D1 asks for, plus inputs and bridges.** Expected: prints `[]`, exit 0.

  ```bash
  python3 -c "import sys;t=open('_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/contract.md',encoding='utf-8').read();h=['## CLI','## MCP tools','## Feature-flag keys','## Environment variables','## Exit codes','## Sources','## Check codes','## Computed check sites','## Bridges and import closure','## Inputs each source reads','## Identity constants','## Scripts outside the package','## Python floor'];m=[x for x in h if x not in t];print(m);sys.exit(1 if m else 0)"
  ```

- **AC2 — Code has nothing the contract lacks, and the contract nothing the code lacks.** Expected: exit 0; it reads the parsers `doctor` and the sources dispatcher build, DISPATCH, the Source enum, the check codes (literal `check=` strings, module-level constants, HygieneFindingKind values and the `"kind"` literals of the modules whose `check=` reads item['kind']), the os.environ reads, the exit constants in verdict.py, and the *_TOOL constants of django-doctor's mcp_asgi.py.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/meta/test_public_contract.py -q -m live_tree -p no:cacheprovider
  ```

- **AC3 — The check fires both ways on synthetic input.** Expected: exit 0, 8 or more selected: a synthetic extra flag, verb, check code, environment key, Source, MCP tool and computed site are each reported missing from the contract, and a contract line with no code is reported stale.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/meta/test_public_contract.py -q -p no:cacheprovider -k mutation
  ```

- **AC4 — Computed check codes and environment keys are enumerated, not guessed.** Expected: exit 0; the AST's computed `check=` sites (19 today: 7 item['kind'] in board.py, chain.py, ledger.py; roster_err['kind'] in chain.py; 5 HygieneFindingKind members; 4 f.check pass-throughs in status_body_consistency.py; warden's check.name; cli_bridge's `check=False` is a subprocess flag, not a code) and the one computed environment read (sibling_dreams.py, GH_TOKEN and GITHUB_TOKEN) equal the `## Computed check sites` table, module and function per row.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/meta/test_public_contract.py -q -p no:cacheprovider -k computed_sites
  ```

- **AC5 — The meta-test is a live-tree module (it reads the Spec folder and django-doctor).** Expected: prints 1.

  ```bash
  git grep -c 'pytestmark = pytest.mark.live_tree' -- src/shared/packages/pyforge-doctor/tests/meta/test_public_contract.py
  ```

- **AC6 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-57-2-*.md)"
  ```

- **AC7 — Lint, types and the doctor suite halves stay green.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild lint-types && pixi run --frozen -e pyforge-doctor pyforge-doctor-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-97 (minted 2026-11-10); FR-28 ← CAP-97.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-10 (the cutover readiness audit) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § *Realization log*.
- Epic: Epic 57, minted with this story.
- Ledger key: `57-2-doctor-s-public-contract-is-one-companion-file-and-a-meta-test-reds-what-it-lacks` (`backlog`).
- Deps: S-56.1, S-56.2, S-56.3, S-56.4, S-56.5.
- Surface: `marshal-policy.toml` `[epic_surfaces]."57"`.
- Minted 2026-11-10 in the one chain commit of the integration branch `cutover-readiness-2026-11-10`, before any doctor story builds.

## Notes

- Decision D1; no generator, no CLI verb.
- Sections: CLI (five verbs and every option; the sources dispatcher and its flags); MCP tools; feature-flag keys (none read); environment variables (GH_TOKEN, GITHUB_TOKEN read in sibling_dreams; NO_COLOR set for children, listed apart, not read); exit codes (`doctor` {0, 2, 130}; the dispatcher; the aggregate's {0, 1, 2} is scripts/detectors.py's); Sources (46 with writer-lock: scope, subject station, governing capability, check codes); Check codes; Computed check sites; Bridges and import closure (six pyforge.core modules, optional pyforge.warden.engines.run_doctor_checks, DoctorCheck and pyforge.warden.verdict.LATTICE as warden's contract lists them, optional django_pyforge.flags, atlas over MCP or CLI, steward `ci status --json`, platform-ci-test pytest, the repo scripts it executes); Inputs each source reads (scripts/.spec-surface-baseline.json and the Spec `surface:` globs, scripts/.deferred-work-baseline.json, docs/MAP.md, docs/map.yaml, docs/governance/*-baseline.json, guild-roster.json, the capability ledger, _bmad-output/projects/pyforge-marshal/ for bmad-drift); Identity constants (PAGES_ROOT_URL, the sibling repository owner, the schema `$id`s); Python floor (3.14: requires-python >=3.14 and ruff py314; decision D6); Scripts outside the package (fleet_picture.py, deferred_work_promote.py, spec_surface_check.py under CAP-59, fr_baseline.py, flag_inventory.py, each with the capability it realizes; mason_cfe_surface_check.py and memlog_fidelity_check.py named as other chains').
- Computed `check=` sites today: 19 (7 item['kind'] in board.py, chain.py, ledger.py; roster_err['kind'] in chain.py; 5 HygieneFindingKind members; 4 f.check pass-throughs in status_body_consistency.py; warden's check.name); cli_bridge's `check=False` is a subprocess flag, not a code.
- Rulings of 2026-11-10 applied (`docs/dreams/pyforge-unifying-strategy.md` § Realization log, the second addendum, 'Accept all, run mint'): a source that measured nothing reads `unmeasured`, a warning the merge bar does not fail on; `doctor flags kill-switch` stays Doctor's one actuator; doctor's closed one-time campaigns retire; the marker grammar is CHAIN-STANDARD section 4 as steward Story 120.3 amends it (`(retired <date>[: <reason>])` and semicolon qualifiers, no `(unbuilt)` token); the operator flips `pyforge.cutover_root` by hand once the Launch slice is proven, and nothing flips it automatically.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code (never through a pipe).

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check` — expected: exit 0 each.

## Spec Change Log

- 2026-11-10: minted from the station Dream's 2026-11-10 entry (the cutover readiness audit) and the operator's rulings of 2026-11-10.
