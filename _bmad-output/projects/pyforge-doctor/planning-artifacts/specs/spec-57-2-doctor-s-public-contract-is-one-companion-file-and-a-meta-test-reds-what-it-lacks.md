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
  git grep --untracked -c 'pytestmark = pytest.mark.live_tree' -- src/shared/packages/pyforge-doctor/tests/meta/test_public_contract.py
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

## Review findings (build, round 1, 2026-11-11)

An independent reviewer failed the first attempt. Each finding, and what the fix round did:

1. **Major — helper resolution failed open** (`tests/meta/test_public_contract.py`, `resolve()`'s helper branch and
   the helper loop's `definition is None: continue` and private-attribute-call skip). A `check=<parameter>` site
   recorded nothing itself and counted only through call sites the loop could bind, so a private method called as
   `self._emit('x')`, a helper passed as a callback (`map(_emit, [...])`) or a call through `**{'check': ...}` added a
   code with no contract line and no failure (spec-pyforge-doctor:CAP-97's success clause). **Fixed:** the loop now
   fails closed. A helper is itself a computed site, `(module, helper, parameter)`, when it is a method, when a
   private helper is called through an attribute, when a call's `*` or `**` argument may bind the parameter or the
   call omits it with no default, when the name is loaded as a value (a callback) or imported under another name,
   and when no call binds it at all; the readable calls still resolve to their codes. Helpers are carried as their
   own definition node, so the `definition is None` branch is gone. New mutation tests:
   `test_mutation_an_unreadable_helper_is_a_computed_site[method|callback|double-star|starred|never-called|private-attribute|aliased]`.
   The live tree adds no row: every one of its eight helpers is a module-level function whose every caller binds
   the parameter.
2. **Minor — a positional `Finding(...)` was invisible** (only `check=` keywords were scanned). **Fixed, one step
   stronger than proposed:** a `Finding(...)` with no `check=` keyword is read at `check`'s place in the dataclass's
   own field order (index taken from `dataclasses.fields(Finding)`): a literal or constant there is a check code like
   any other, a parameter there is a helper, anything else is a computed site; a `*` or `**` argument that may carry
   the code is a computed site keyed by its unparsed form (`*rest`, `**kwargs`). New test:
   `test_mutation_a_positional_finding_is_read`. The package has no positional Finding today. contract.md's reading
   rules (§ Check codes, § Computed check sites) say the same.
3. **Minor — AC5 reads `git grep`, which skips an untracked file.** Not an oracle fault and not changed: the build may
   not `git add`, and `git grep --untracked -c` prints `test_public_contract.py:1` today. The wave gate re-runs AC5
   verbatim after its commit and records the result.
4. **Minor — AC4's prose and the Notes miscount.** The reviewer is right; the code, contract.md and the test were
   already correct. Corrected mix of the 19 rows: 8 `item['kind']` sites in 6 rows (board.py
   `_gather_chain_completeness`; chain.py `_gather_dream_chain`, `_gather_spec_surface` (two sites),
   `_gather_deferred_work`, `_wrap_as_findings`; ledger.py `gather` (two sites)), chain.py's `roster_err['kind']`,
   5 `HygieneFindingKind` members, 4 `f.check` pass-throughs in status_body_consistency.py, warden's `check.name`,
   `__main__._run_check`'s `engines_name`, and board.py `_gather_chain_layers_audit`'s loop-bound `check`; 6 + 1 + 5 +
   4 + 1 + 1 + 1 = 19. The Notes' "six pyforge.core modules" is eight in the code (`verdict`, `report`, `hooks`,
   `landing_evidence`, `published_loop`, `roster`, `cutover_root`, `flags`). The AC4 command is unchanged (no oracle
   fault); the station Spec's own wording is corrected at Story 57.3's re-derive, by memlog and `bmad-spec`, never a
   hand edit of `SPEC.md`.

## Review findings (build, round 2, 2026-11-11)

An independent reviewer failed the round-1 fix. Each finding, and what this round did:

1. **Major — a private helper reached from another module failed open** (`tests/meta/test_public_contract.py`, the
   helper loop's `if method or (private and module != helper_module): continue`). A private helper imported into a
   second module (`from .syn_a import _emit`, aliased or not) or called there as `syn_a._emit(...)` added a code with
   no contract line, no site and no failure, although round 1's text claimed the rule failed closed for an attribute
   call and an import under another name (spec-pyforge-doctor:CAP-97's success clause). **Fixed:** a private helper
   is now read in its own module and in each module that imports it by name: a plain `from <its module> import _emit`
   (relative levels resolved to the dotted module) makes that module's bare-name calls resolve like local ones, the
   code keyed to the caller's module as a public helper's is; an aliased import, a module that also defines that
   name, and any same-named attribute in any other module (`syn_a._emit(...)`, or another object's method, which the
   AST cannot tell apart) make the helper a computed site `(module, helper, parameter)`. Same-named private
   functions of different modules are never merged (a module that only defines its own `_emit` is not read for the
   other's). New mutation tests, each with a readable call in the defining module:
   `test_mutation_a_private_helper_reached_from_another_module[imported|imported-absolute|imported-aliased|module-attribute|imported-callback|imported-and-redefined]`
   and `test_mutation_same_named_private_helpers_are_not_merged`. The live tree adds no row: its six private check
   helpers (`board._checkpoint_finding`, `deps._finding`, `factory._finding`, `one_chain._fold_fail`,
   `one_chain._fr_fail`, `atlas._one_fail_finding`) are imported nowhere and no other module names them as an
   attribute; the seven cross-module private imports the reviewer counted import non-check helpers such as
   `chain._frontmatter_parse_text`.
2. **Minor — the `callback` and `method` cases did not test their own rules.** **Fixed:** every unreadable-helper
   case except `never-called` and `private-method` now carries a readable direct call in the same synthetic module,
   so only the rule the case names can make the helper a site. `method` is now a public method whose call binds a
   second positional (`Emitter().emit_synthetic('silent-code-a', 'detail')`), so without the method rule the
   parameter would read `'detail'`; the old private-method case stays as `private-method`. The same audit found
   `double-star` was also caught by the omitted-with-no-default fallback, so its helper now has a default (only the
   `**` rule can fire), and a separate `omitted-without-default` case covers the fallback. Scratch mutants (one rule
   disabled at a time, the module loaded under its real path from the build's scratch folder) confirm each rule's
   case fails when its rule is removed: `_names_as_value` (callback, aliased, imported-callback), the method rule
   (method), the private-attribute call (private-attribute), the cross-module read (all six cross-module cases), the
   foreign-attribute rule (module-attribute), `_binds` (imported-and-redefined), `_rebinds` (rebound-parameter), the
   `**` rule (double-star), the `*` rule (starred), the never-called rule (never-called), and each kind, alias and
   environment rule (its own cases). The mutant logs are scratch evidence, not tracked files.
3. **Minor — unreadable `"kind"` values in a kind module were skipped.** **Fixed:** in a module whose `check=` reads
   `<row>['kind']`, the item rows' `"kind"` values are read from `{"kind": ...}`, `dict(kind=...)` and
   `<row>['kind'] = ...` (never a Finding's `evidence=`); a value no reading resolves is a computed site
   `(module, function, value)`, with any strings a loop binds to it counted as codes. New test:
   `test_mutation_an_item_row_kind_in_another_form_is_read[dict-computed|dict-call|dict-call-computed|assigned|assigned-computed]`.
   The live tree has none of these forms; its row count is unchanged.
4. **Minor — four more edges failed open.** **Fixed:** `Finding` under an alias (`from ...models import Finding as
   F`, or `F = Finding`) is read positionally (`test_mutation_a_finding_under_another_name_is_read`); an environment
   read's key is read from `key=` too (`os.getenv(key='K')`, `os.environ.get(key='K')`), and `environ` / `getenv`
   are read under any name the module binds to them (`from os import environ as E`, `E = os.environ`, `from os import
   getenv as read`) (`test_mutation_an_environment_read_in_another_form_is_missing[...]`, five cases); a helper
   parameter the helper rebinds before `check=` (an assignment, loop or `with` target, `except ... as`, import,
   match capture or nested definition) is a computed site of its own instead of resolving to its callers' values
   (`test_mutation_an_unreadable_helper_is_a_computed_site[rebound-parameter]`). The rebind rule found one live
   case: `__main__._gather_engines` rebinds `name = str(name)` before `check=name`. So the engines row of
   contract.md § Computed check sites moves from `__main__.py | _run_check | engines_name` (its caller's argument)
   to `__main__.py | _gather_engines | name`; the count stays 19.
5. **Minor — AC5 cannot pass before the wave gate's commit.** Unchanged, as in round 1: the build may not `git add`;
   `git grep --untracked -c` prints `test_public_contract.py:1`. The wave gate re-runs AC5 verbatim after its commit
   and records the result. Not an oracle fault, so the command stays as written.
6. **Minor — AC4's Expected prose still gives the old mix of the 19 rows.** The AC4 command is unchanged (no oracle
   fault), and the AC block's prose is not edited by the build. The authoritative mix is round 1's finding 4 with
   this round's move: 8 `item['kind']` sites in 6 rows (board.py `_gather_chain_completeness`; chain.py
   `_gather_dream_chain`, `_gather_spec_surface` (two sites), `_gather_deferred_work`, `_wrap_as_findings`; ledger.py
   `gather` (two sites)), chain.py's `roster_err['kind']`, 5 `HygieneFindingKind` members, 4 `f.check`
   pass-throughs in status_body_consistency.py, warden's `check.name`, `__main__._gather_engines`'s `name`, and
   board.py `_gather_chain_layers_audit`'s loop-bound `check`; 6 + 1 + 5 + 4 + 1 + 1 + 1 = 19. AC4's Expected text
   and the Notes line are read through this correction; the station Spec's wording is corrected at Story 57.3's
   re-derive, by memlog and `bmad-spec`, never a hand edit of `SPEC.md`.

contract.md's reading rules (§ the code side, *Environment variables*, *Check codes*, *Computed check sites*) and
the test module's docstring now state exactly these rules.

## Review findings (build, round 3, 2026-11-11)

An independent reviewer failed the round-2 fix. Each finding, and what this round did:

1. **Major — the feature-flag-key half of the guard was never proven** (`tests/meta/test_public_contract.py`, the
   flag-key reader in `_code_facts`). Replacing the reader with `if False:` left every test green, because the live
   tree compares an empty set with an empty set and no mutation test fed it a key. The reader also saw only one call
   form, a positional first argument: `read_boolean(key='pyforge.x')`, OpenFeature
   `client.get_boolean_value(flag_key='pyforge.x', default_value=False)` (and the other `get_*_value` forms) and an
   aliased reader (`from pyforge.core.flags import read_boolean as rb; rb('pyforge.x')`, or a module alias) added a
   key with no contract line and no failure (spec-pyforge-doctor:CAP-97's success clause). **Fixed:** the reader is
   `_flag_reads`, keyed `(key, module, reader)` as the contract's `Key | Module | Reader` rows are. It reads every
   reader of `pyforge.core.flags` (`read_boolean`, `kill_switch_on`, `require`, `disabled_help`) and
   `django_pyforge.flags` (`evaluate_boolean`, `evaluate_cli_boolean`) and each OpenFeature client evaluation method
   (`get_<type>_value` and `get_<type>_details`, sync and async), with the key taken where that reader takes it,
   positionally or by keyword (`key=`, `flag_key=`); a reader under any name the module binds to it (an aliased
   import, `rb = fl.read_boolean`, `get = client.get_integer_value`) or on a name bound to a flags module
   (`from pyforge.core import flags as fl`, `import pyforge.core.flags as fl`, the dotted `pyforge.core.flags.x`).
   `require` and `disabled_help` count only when bound from a flags module, so an unrelated `require(...)` is no key.
   It fails closed: a computed key, a `*` / `**` key and a reader loaded as a value (a callback) read `<expr>`. The
   unused `is_enabled` entry is gone (no reader of that name exists in the estate). New tests:
   `test_mutation_a_flag_key_in_each_form_is_missing[...]` (16 forms: positional, keyword, constant,
   openfeature-positional, openfeature-keyword, openfeature-details-async, aliased-import, module-alias,
   module-import-as, module-dotted, assigned, assigned-method, django-aliased, computed, starred, callback),
   `test_mutation_a_listed_flag_key_is_neither_missing_nor_stale` (a row parses to the code side's item),
   `test_mutation_a_common_name_off_a_flags_module_is_no_flag_key`, and the stale case
   `test_mutation_a_contract_line_with_no_code_is_stale[flag-key]` (a `Key | Module | Reader` row no code backs).
   Scratch mutants outside the worktree (the module copied to the build's scratch folder, its root pinned to this
   worktree, one rule disabled each) all red: the reviewer's `if False:` around the reader reds 17 tests; reading
   positionals only reds the 4 keyword forms; dropping aliases reds 7; dropping the reader-as-value rule reds
   `callback`; not reading the contract's flag rows reds the stale and listed cases; matching `require` anywhere reds
   the common-name case. The live tree still reads no flag key, so contract.md § Feature-flag keys stays "None".
2. **Minor — a private check helper re-exported one hop failed open** (`from .b import _emit` where `b` imported it
   from `a`): the caller's import names `b`, not the defining module, so its calls were never read. **Fixed:**
   `_private_importers` follows the re-export chain to a fixed point (any number of hops, a package `__init__`
   included); a plain chain reads the caller's calls like local ones, an alias anywhere on it makes the helper a site.
   New test `test_mutation_a_re_exported_private_helper_is_read[one-hop|two-hops|package-init|one-hop-aliased]`; with
   the chain disabled in a scratch mutant all four red.
3. **Minor — three environment-read forms failed open:** a read through a copy (`env = dict(os.environ)` or
   `os.environ.copy()`, then `env.get(...)`), `os.environ.setdefault(...)`, and `os.environb`. **Fixed:** a name
   bound to a copy (`dict(os.environ)`, `os.environ.copy()`, `{**os.environ}`, a copy of a copy) is the environment
   in the function that binds it, and everywhere for a module-level copy (`_environ_copies`); `.setdefault` and `.pop`
   read like `.get`; `os.environb` (and `from os import environb as X`) is the environment, its bytes key decoded.
   New cases of `test_mutation_an_environment_read_in_another_form_is_missing` (copy-dict, copy-method,
   copy-unpacked, copy-of-a-copy, copy-module-level, setdefault, pop, environb, environb-imported-as) and
   `test_mutation_a_copy_is_read_only_in_its_own_function` (cli_bridge's `env` copies stay child keys, and a
   parameter named `env` elsewhere is no environment). Each rule disabled in a scratch mutant reds its own cases.
   The live tree's reads are unchanged (`GH_TOKEN`, `GITHUB_TOKEN`; `NO_COLOR` set for a child).
4. **Minor — two item-row `"kind"` forms failed open:** `row.update(kind=...)` and `row.setdefault('kind', ...)`.
   **Fixed:** `_kind_values` reads both; a value no reading resolves is a computed site like the other forms. New
   cases of `test_mutation_an_item_row_kind_in_another_form_is_read` (updated, updated-computed, setdefault,
   setdefault-computed); disabled in a scratch mutant, all four red. The live tree adds no code and no site.
5. **Oracle — AC5 run verbatim exits 1 before the wave gate's commit**, because `git grep` skips the untracked new
   module and the build may not `git add`. The reviewer gave the corrected form, `git grep --untracked`, which checks
   the same line and also finds it once the file is tracked. **Changed:** AC5's command above and the story's AC5 in
   the build plan (`plan.json`, stories[key=57.2]) now read `git grep --untracked -c ...`; it prints
   `src/shared/packages/pyforge-doctor/tests/meta/test_public_contract.py:1` (a count of 1) and exits 0.

contract.md's reading rules (§ the code side: *Feature-flag keys*, *Environment variables*, *Check codes*,
*Computed check sites*; § Feature-flag keys) and the test module's docstring state exactly these rules. The module
now holds 99 tests (62 before this round).
