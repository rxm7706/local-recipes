---
title: "26.3: The contract names what other code imports, where each capability lives, and the open slots"
type: 'chore'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a companion section and a meta-test that judges (spec-feature-flag-governance Q1, Q2)
difficulty: 'medium'
story: '26.3'
spec: _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
surface:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md
  - src/shared/packages/pyforge-warden/tests/meta/test_contract_surface.py
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
  - src/shared/packages/pyforge-warden/pyproject.toml
  - src/shared/packages/pyforge-warden/src/pyforge/warden/scanner_plugins.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/hooks.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The second half of the caller-visible surface. Atlas, doctor, `django-warden` and three platform tests import 29 `pyforge.warden` names no Spec text names (audit MUST 8); `django-warden` realizes CAP-16, CAP-17 and CAP-29 under another Spec's surface (MUST 9); the report's `advisory` and `actuation` slots are untyped; the engine ranges and the agent dependency are in no Spec text.

**Approach:** `contract.md` sections 8 to 12, appended to Story 26.1's file: (8) hook specs (3), plugin entry points (10) and optional scanner ids (7; `opengrep` and `tea-test-review` are ids, not entry points). (9) Key sets of the report's open slots as emitted (each advisory record, the actuation object), with the dataclass or builder each comes from; the schema stays closed at 1.1.0 (operator ruling 2026-11-10). (10) Engines and tested ranges (deptry, osv-scanner, pixi, opengrep; `tea-test-review --agent claude` with no range and an agent CLI on `PATH`), bundled data (`conda_pypi_map.json`: no snapshot; `lts-registry.yaml`: `updated:` and 180 days; `sast-rules/`), the three refresh scripts. (11) Python import surface: module, names, importer; the test's derivation is the count of record. (12) *Where each capability lives*: one row per CAP-1..CAP-29 with package or path and governing Spec (CAP-16, CAP-17 and CAP-29 in `django-warden` under spec-pyforge-unifying-strategy; CAP-19..CAP-22 in platform scripts and workflows; the rest in the kernel), then pointers for what warden does not mint: the MCP face (`spec-pyforge-unifying-strategy:CAP-4`, `spec-pyforge-unifying-strategy:CAP-20`), the skill and persona (`spec-pyforge-unifying-strategy:CAP-15`, `spec-pyforge-unifying-strategy:CAP-16`), the two review lenses `bmad-os-review-pr` and `bmad-os-findings-triage` (`spec-pyforge-steward:CAP-32`, warden Story 11.1), the TEA advisory's provisioning (`spec-pyforge-steward:CAP-33`). It records as-is the frozen schema `$id`, `DEFAULT_AUDIT_TARGET = 'src/platform'` and the compliance/check stub (steward's code). By the operator's ruling of 2026-11-10 this table is the answer to MUST 9: `spec-pyforge-warden` does not co-govern `django-warden`, and its `surface:` block does not move.

**Test.** `tests/meta/test_contract_surface.py`, `pytestmark = pytest.mark.live_tree`. Entry points from the package's `pyproject.toml`; ids and hook specs from `scanner_plugins.OPTIONAL_SCANNER_IDS` and `hooks.PR_GATE_HOOK_SPECS`; ranges from the `engines.py` range constants; slot key sets from the models and builders. Imports by text, not AST, so subprocess source strings are seen: over every tracked text file under `src/` and `scripts/` outside the package (`git ls-files` from the repo root), the regexes `from\s+(pyforge\.warden(?:\.\w+)*)\s+import\s+(\(?[^;"')]+)` (a parenthesised list read to its closing bracket) and `import\s+(pyforge\.warden(?:\.\w+)*)`. A named allowlist, `IMPORT_FIXTURE_FILES`, holds the five files that only quote import lines as fixtures or comments, each with a reason; an entry whose file no longer matches fails. Both directions: an import with no row fails; a row no file imports fails. The scan hands the repo root to git, which steward's scanner counts as a root handoff: steward declares this module in `ROOT_HANDOFF_INPUTS` with globs `src/**` and `scripts/**`.

Ledger key: `26-3-the-contract-names-what-other-code-imports-where-each-capability-lives-and-the-open-slots`.
Type / Effort / Deps: chore / M / S-26.1.

### Living CAP citations

- spec-pyforge-warden CAP-28 (FR-45).
- Decision D1 of the 2026-11-10 cutover readiness plan.
- `flag-exempt: detector-or-gate`.

## Boundaries & Constraints

**Always:**
- Derive every list from the code and compare it both ways.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not change code, the schema or the `surface:` block.
- Do not mutate a tracked file in a negative test.

</intent-contract>

## Acceptance Criteria

- **AC1 — The surface test.** Run from the repo root, verdict from the exit code (never through a pipe):
  `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/meta/test_contract_surface.py -q`
  Expect: exit 0.
- **AC2 — The test fails on drift, on a stale row and on a stale allowlist entry.** Run from the repo root, verdict from the exit code (never through a pipe):
  `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/meta/test_contract_surface.py -q -k 'unlisted or stale_row or allowlist'`
  Expect: exit 0 with at least 7 tests selected and passed.
- **AC3 — Independent re-derivation: every pyforge.warden module a tracked file outside the package imports is in contract.md.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,subprocess,sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md').read();x=['src/shared/packages/pyforge-doctor/tests/meta/test_no_warden_import.py', 'src/shared/packages/pyforge-doctor/tests/meta/test_sources_warden_no_subprocess.py', 'src/shared/packages/pyforge-core/tests/meta/test_leaf_constraint.py', 'src/shared/packages/pyforge-steward/tests/meta/test_first_portal_slice_provision_list.py', 'src/shared/packages/pyforge-steward/tests/meta/test_object_store_seam_boundaries.py'];o=subprocess.run(['git','grep','-h','-o','-E','(from pyforge\.warden[A-Za-z_.]* import|import pyforge\.warden[A-Za-z_.]*)','--','src','scripts',':(exclude)src/shared/packages/pyforge-warden']+[':(exclude)'+p for p in x],capture_output=True,text=True).stdout;mods=sorted(set(re.findall(r'pyforge\.warden(?:\.[A-Za-z_]+)*',o)));m=[d for d in mods if d not in t];print(len(mods),m);sys.exit(1 if m or len(mods)<12 else 0)"`
  Expect: prints a count >= 12 and [], exit 0.
- **AC4 — Independent re-derivation: hook specs, entry points and optional scanner ids are in contract.md.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import tomllib,sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md').read();e=list(tomllib.load(open('src/shared/packages/pyforge-warden/pyproject.toml','rb'))['project']['entry-points']['pyforge.core.hooks']);k=e+['pyforge.warden.pr_gate.scan','pyforge.warden.pr_gate.aggregate','pyforge.warden.pr_gate.verdict','checkmarx','sonar','blackduck','ghas','profile-local','opengrep','tea-test-review'];m=[x for x in k if x not in t];print(len(e),m);sys.exit(1 if m or len(e)!=10 else 0)"`
  Expect: prints 10 [], exit 0.
- **AC5 — Where-it-lives has one row per capability and every path it names exists.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,os,sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md').read();s=t.split('## Where each capability lives',1)[1].split('\n## ',1)[0];miss=[n for n in range(1,30) if not re.search(r'(?m)^\| CAP-%d \|'%n,s)];dead=sorted(set(p for p in re.findall(r'((?:src|scripts|\.github)/[\w./*-]+)',s) if '*' not in p and not os.path.exists(p)));print(miss,dead);sys.exit(1 if miss or dead else 0)"`
  Expect: prints [] [], exit 0.
- **AC6 — The lenses cite the routing capability, not the TEA one.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md').read();l=[x for x in t.splitlines() if 'bmad-os-review-pr' in x];sys.exit(0 if l and all('spec-pyforge-steward:CAP-32' in x and 'CAP-'+'33' not in x for x in l) else 1)"`
  Expect: exit 0.
- **AC7 — Post-condition (Story 124.2 runs it): Cross-unit: steward's trigger map accepts the new module, with its root handoff declared.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q`
  Expect: exit 0 once steward Story 124.2 carries the paths and the ROOT_HANDOFF_INPUTS row this story names (shared request); red before it by design (other units' new reads).
- **AC8 — Lint and types.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run -e pyforge-guild lint-types`
  Expect: exit 0.

## Binding

- Story: `_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md` § *Story 26.3: The contract names what other code imports, where each capability lives, and the open slots*.
- Dream: `docs/dreams/pyforge-warden.md`, Realization log, *2026-11-10 (the cutover readiness audit)*; the operator's rulings of 2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md`, Realization log, second addendum).
- Ledger key: `26-3-the-contract-names-what-other-code-imports-where-each-capability-lives-and-the-open-slots`.
- Deps: S-26.1.
- Flag: none (`flag-exempt: detector-or-gate`).
- Cross-station: `steward:S-124.2` carries this module's reads and its `ROOT_HANDOFF_INPUTS` row; AC7 passes once it is on the branch.

## Gate findings (build, BUILD-2)

- `ad_citation_check` (2026-11-11): the `tea-test-review` row of `contract.md` section 8 cited the module roster as a bare AD id copied from the `tea_advisory.py` docstring, and pyforge-warden's spine defines no ADs. Fixed in `contract.md`: the row now cites `suite:AD-9` (steward's spine, *One module roster, one config-pin path*). Re-run: `pixi run --frozen -e pyforge-guild ad-citation-check` and the 26.3 acceptance checks.
