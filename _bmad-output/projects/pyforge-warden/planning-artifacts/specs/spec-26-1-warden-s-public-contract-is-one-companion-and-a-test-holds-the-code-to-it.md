---
title: "26.1: Warden's public contract is one companion, and a test holds the code to it"
type: 'chore'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a companion and a meta-test that judges (spec-feature-flag-governance Q1, Q2)
difficulty: 'heavy'
story: '26.1'
spec: _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
surface:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md
  - src/shared/packages/pyforge-warden/tests/meta/test_public_contract.py
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/config.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/models.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/actuator.py
  - src/shared/packages/django-warden/src/django_warden_fabric/fleet.py
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-55-4-doctor-s-live-tree-readers-run-as-their-own-half.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Decision D1: a second root rebuilds every surface a caller of warden reaches from the Spec folder alone. At main `82a2b18828` the audit found the Spec naming none of the nine flags, six of the scan flags, the forge and feed environment variables, the MCP tools or the management commands (audit MUST 1 and MUST 7). The mint's render of 2026-11-10 wrote those names into the capabilities that own them (the flags into CAP-24..CAP-26 and CAP-29, the scan options into CAP-7, CAP-9 and CAP-18, the variables into CAP-11 and CAP-12, the management commands into CAP-29), but no companion lists the whole surface a caller reaches, and no test fails when the code and the list part. The code is right; the contract is not written down in one place.

**Approach:** `contract.md` sections 1 to 7, each a table the test parses: (1) CLI: `warden scan <path>` (the same verb as `pyforge warden scan`), 23 options and `--version`, each with its CAP. (2) The 13 `[tool.pyforge-warden]` keys with defaults (`fail-on-kev = true`; `fix-pr-estate-repos = rxm7706/local-recipes, rxm7706/python-foundry`, both roots, decision D3). (3) Exit codes {0, 1, 2, 130}, the seven Status rungs, the nine ErrorKind values, the finding-id families (pointers to `verdict-contract.md` and `finding-id-verdict-encoding-decision.md`); the schema `$id` urn:local-recipes:pyforge-warden:report-schema is frozen at 1.1.0 (operator ruling 2026-11-10). (4) The nine feature flags, one row each: `| key | flags.json | dev | staging | production | reader | flag-off behaviour |` (off, on, on, off for all nine today), then one paragraph: `PYFORGE_ENVIRONMENT` unset means dev, so a run in this repository reads them on; every reader passes default False, so a run that resolves no tree reads them off; flags are read through `pyforge.core.flags.read_boolean`. Never write "off by default" without the environment. (5) Environment variables: read by the kernel (exactly seven: GH_TOKEN, GITHUB_API_URL, GITHUB_REPOSITORY, GITHUB_TOKEN, OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY, PYFORGE_WARDEN_FEED_CACHE_DIR, WARDEN_OPTIONAL_SCANNERS); set by the kernel for an engine subprocess (exactly four: NO_COLOR, SEMGREP_SEND_METRICS, OPENGREP_ENABLE_VERSION_CHECK, OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY); read by `django-warden` (WARDEN_FLEET_TARGET_CONFIG, WARDEN_FLEET_INVENTORY_PATH, WARDEN_FLEET_PROJECT_ITEMS_PATH); passed through to its git subprocesses (GITHUB_TOKEN, GH_TOKEN, GH_ENTERPRISE_TOKEN, GITHUB_ENTERPRISE_TOKEN); set by it for the actuator and the scan (GITHUB_REPOSITORY, OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY); its two Django settings (WARDEN_OSV_DB_CACHE_DIRECTORY, WARDEN_FLEET_APPROVAL_EXPIRY_SECONDS). (6) MCP tools `start_audit` and `get_audit` at POST /stations/warden/mcp (`spec-pyforge-unifying-strategy:CAP-4` and `spec-pyforge-unifying-strategy:CAP-20`). (7) The four management commands. Sections 8 to 12 are Story 26.3's; the proof map is Story 26.2's file.

**Test.** `tests/meta/test_public_contract.py`, `pytestmark = pytest.mark.live_tree` (`contract.md` lives in the planning tree; Story 27.1 registers the marker). Derivation, so the guard is not blind: CLI from `cli._build_parser()` actions; keys from `config._RECOGNIZED_KEYS`; Status, ErrorKind and the exit values from `models` and `verdict`; flags from an AST scan for module constants whose value starts `pyforge.warden.` in the kernel and in `django-warden`, compared both ways with the `pyforge.warden.*` rows of `flags.json` and, per environment, of `flag-overlays.json`. Environment variables by AST over every kernel module: a read is an upper-case string (literal or module constant) passed to `.get()`, `.pop()`, `.setdefault()` or `os.getenv()`, or a Load-context subscript, on `os.environ` or a name bound to an environment mapping (`env`, `environ`, `source`), plus every `*_ENV` and `*_ENV_VAR` constant; a set is a Store-context subscript on such a mapping or a string key of a dict literal passed as `env=` or `extra_env=` (or `env.update()`), so finding-id and licence dict literals are not variables. The test asserts the derived kernel read set equals the seven and the set-for-engine set the four, then compares both with `contract.md`. `django-warden`'s rows are derived the same way. MCP tools from the `@server.tool()` functions in `mcp_asgi.py`; commands from `management/commands/*.py`. Every outside path is a `Path(__file__)`-anchored constant, so steward's trigger-map scanner derives the reads. Negative tests use synthetic inventories and source text, never a mutated tracked file.

Ledger key: `26-1-warden-s-public-contract-is-one-companion-and-a-test-holds-the-code-to-it`.
Type / Effort / Deps: chore / L / —.

### Living CAP citations

- spec-pyforge-warden CAP-28 (FR-45): minted `ready` at the mint; Story 25.2 moves it to shipped.
- Decision D1 of the 2026-11-10 cutover readiness plan.
- `flag-exempt: detector-or-gate`: a gated check would report a silent green.

## Boundaries & Constraints

**Always:**
- Derive every inventory from the code and compare it both ways with `contract.md`.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not change product code, add a CLI verb or a generator.
- Do not mutate a tracked file in a negative test.

</intent-contract>

## Acceptance Criteria

- **AC1 — The contract test (kernel inventories, django-warden, the flag tree and its overlay).** Run from the repo root, verdict from the exit code (never through a pipe):
  `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/meta/test_public_contract.py -q`
  Expect: exit 0.
- **AC2 — The test fails on drift: each inventory has a synthetic-drift negative, both directions.** Run from the repo root, verdict from the exit code (never through a pipe):
  `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/meta/test_public_contract.py -q -k 'unlisted or stale_row'`
  Expect: exit 0 with at least 9 tests selected and passed.
- **AC3 — The environment-variable derivation sees literal reads: the derived kernel read set is exactly the seven and the set-for-engine set exactly the four.** Run from the repo root, verdict from the exit code (never through a pipe):
  `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/meta/test_public_contract.py -q -k 'kernel_env'`
  Expect: exit 0 with at least 3 tests selected and passed (the read equality, the set equality, and a synthetic source.get('NEW_VAR') that is caught).
- **AC4 — Independent re-derivation: every scan option string is in contract.md.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import ast,sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md').read();f=[a.value for n in ast.walk(ast.parse(open('src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py').read())) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='add_argument' for a in n.args if isinstance(a,ast.Constant) and str(a.value).startswith('--')];m=[x for x in f if x not in t];print(len(f),m);sys.exit(1 if m or len(f)<24 else 0)"`
  Expect: prints 24 [], exit 0.
- **AC5 — Independent re-derivation: each flag row states flags.json, dev, staging and production as the two files do.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import json,re,sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md').read();f=json.load(open('src/platform/config/flags.json'));f=f.get('flags',f);o=json.load(open('src/platform/config/flag-overlays.json'));bad=[];[bad.append(k) for k in sorted(x for x in f if x.startswith('pyforge.warden.')) if not (lambda r:r and [c.strip() for c in r.group(1).split('|')][:4]==[f[k]['defaultVariant'],o['dev'].get(k,f[k]['defaultVariant']),o['staging'].get(k,f[k]['defaultVariant']),o['production'].get(k,f[k]['defaultVariant'])])(re.search(r'(?m)^\| .?'+re.escape(k)+r'.? \|([^\n]*)',t))];print(bad);sys.exit(1 if bad else 0)"`
  Expect: prints [], exit 0 (row form: | `key` | flags.json | dev | staging | production | reader | flag-off behaviour |).
- **AC6 — Independent re-derivation: environment variables, MCP tools, commands and config keys are in contract.md.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md').read();k=['GH_TOKEN', 'GITHUB_API_URL', 'GITHUB_REPOSITORY', 'GITHUB_TOKEN', 'OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY', 'PYFORGE_WARDEN_FEED_CACHE_DIR', 'WARDEN_OPTIONAL_SCANNERS']+['NO_COLOR','SEMGREP_SEND_METRICS','OPENGREP_ENABLE_VERSION_CHECK','WARDEN_FLEET_TARGET_CONFIG','WARDEN_FLEET_INVENTORY_PATH','WARDEN_FLEET_PROJECT_ITEMS_PATH','GH_ENTERPRISE_TOKEN','GITHUB_ENTERPRISE_TOKEN','WARDEN_OSV_DB_CACHE_DIRECTORY','WARDEN_FLEET_APPROVAL_EXPIRY_SECONDS','PYFORGE_ENVIRONMENT','start_audit','get_audit','warden_fleet_run','warden_fleet_approve','warden_fleet_inventory','warden_fleet_project_items','fail-on-kev','fix-pr-estate-repos','flag-overlays.json'];m=[x for x in k if x not in t];print(m);sys.exit(1 if m else 0)"`
  Expect: prints [], exit 0.
- **AC7 — Post-condition (Story 124.2 runs it): Cross-unit: steward's trigger map accepts the new module's reads.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q`
  Expect: exit 0 once steward Story 124.2 carries the paths this story names (shared request); red before it by design (other units' new reads).
- **AC8 — Cross-unit: steward's whole live-tree half stays green with this module in the tree.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run --frozen -e pyforge-steward pyforge-steward-live-test`
  Expect: exit 0 after steward-station's edit for this story's reads is on the branch.
- **AC9 — Lint and types.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run -e pyforge-guild lint-types`
  Expect: exit 0.

## Binding

- Story: `_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md` § *Story 26.1: Warden's public contract is one companion, and a test holds the code to it*.
- Dream: `docs/dreams/pyforge-warden.md`, Realization log, *2026-11-10 (the cutover readiness audit)*; the operator's rulings of 2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md`, Realization log, second addendum).
- Ledger key: `26-1-warden-s-public-contract-is-one-companion-and-a-test-holds-the-code-to-it`.
- Deps: —.
- Flag: none (`flag-exempt: detector-or-gate`).
- Cross-station: `steward:S-124.2` carries this module's outside reads in steward's trigger map (shared request); AC7 and AC8 pass once it is on the branch.
