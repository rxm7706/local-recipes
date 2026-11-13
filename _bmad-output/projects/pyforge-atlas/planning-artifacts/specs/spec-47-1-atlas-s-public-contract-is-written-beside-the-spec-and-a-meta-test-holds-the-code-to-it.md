---
title: "47.1: Atlas's public contract is written beside the Spec and a meta-test holds the code to it"
type: 'feature'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a companion file and a gate that judges; no runtime path (the shape of atlas Story 42.3 and doctor Story 55.4)
difficulty: heavy
story: '47.1'
spec: pyforge-atlas
surface:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md
  - src/shared/packages/pyforge-atlas/tests/meta/test_public_contract.py
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-47-1-atlas-s-public-contract-is-written-beside-the-spec-and-a-meta-test-holds-the-code-to-it.md
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/__main__.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py
  - src/platform/config/flags.json
  - src/shared/packages/pyforge-atlas/conf/base/globals.yml
  - src/shared/packages/pyforge-atlas/tools/lasuite_bringup.py
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-55-4-doctor-s-live-tree-readers-run-as-their-own-half.md
warnings: []
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in a later epic (S-48.1, S-48.2, S-48.3).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** No atlas Spec file names the 13 MCP tools, the `ipython` and `package` verbs, 7 of the 11 flag keys, most environment variables or the bring-up tool's exit codes, so a rebuild from the Spec cannot know what the station exposes (audit MUST 7, decision D1). Spec text is silent, code is right. CAP-73 was minted on 2026-11-10 to carry that record.

**Approach:**
- **Derive, never declare.** `tests/meta/test_public_contract.py` derives each family from the code and compares it with `contract.md`. Verbs: `pyforge.atlas.__main__.discover_cli_verbs()` (Kedro's project commands: run, ipython, package) plus the first-token `--version`. Options: each Click command's params for the Kedro group, and an AST scan of `add_argument` literals for the `python -m` entry points (trending_candidates, trending_candidates.handoff_main, query_plane_boot, publish, datasets.vdb_extract) and the nine `tools/` scripts. Tools: `mcp.tools.TOOL_SPECS`. Flag keys: string constants passed to a `pyforge.core.flags` reader or bound to a `*_FLAG_KEY` name, and the derived set equals the `pyforge.atlas.*` keys of `flags.json` (logger names such as `pyforge.atlas.node` are not keys: never match on the prefix alone). Environment variables: AST over `os.environ.get`, `os.environ[...]` and `os.getenv` in `src/` and `tools/`, resolving a Name argument to its module-level string constant (14 names after Story 48.3), every `${env_or:NAME,…}` in `conf/base/*.yml` (38 names in `globals.yml`), and the five reads through a variable (core_sources.py, request_datasets.py twice, factory/storage.py, settings.py), each resolved from the table that feeds it. Exit codes: integer returns of each entry point's `main` (the frozen 0, 1, 2, 130, and `lasuite_bringup`'s 0 to 4), under a heading `## Exit codes`.
- **Prose the test does not judge.** `contract.md` also records the HTTP face `POST /stations/atlas/mcp` (hosted by django-atlas); the five `pyforge.core.hooks` entry points and that `cap18.py` is named for spec-pyforge-unifying-strategy:CAP-18; the one cross-station import (`pyforge.warden` through the `gate` extra); the four data-root resolvers and their blank handling; the planning-tree read in `dashboard/factory_status.py`; `tools/normalize_viz_build.py`'s Pages staging path; the two places the recipes repository slug lives; and `observability.PRODUCER` exactly as the code has it (`…/tree/main/pyforge-atlas`, a path that does not exist; deferred row DW-atlas-46-1-7).
- **After 48.2 and 48.3.** The contract describes the code this change leaves: no views runtime (ruling 6 of the second addendum: Story 48.3 deletes it), the plane default resolved from the member. `contract.md` names neither `PYFORGE_ATLAS_CFE_SCRIPTS_DIR` nor `PYFORGE_ATLAS_LIVE_BOKEH_URL`.
- The test reads the Spec folder, so it carries `pytestmark = pytest.mark.live_tree` (registered by Story 48.1).
- The mint wrote CAP-73 (memlog `capability` entry and render), the `companions:` line and FR-78; this story owns no `SPEC.md` text and appends nothing to the memlog. Story 48.4, the unit's closer, writes the one surface-reconcile event and flips CAP-73's marker to `(shipped <date>)` once this story and Story 47.2 are done (ruling 6 of the second addendum: markers of capabilities this PR builds flip to shipped at the station's closing Story). `capability-ledger-check`'s classification of CAP-73 is judged at steward Story 121.7, not here; until then the new id reads `unclassified` by design. Story 121.7 is not a precondition of this story.

Ledger key: `47-1-atlas-s-public-contract-is-written-beside-the-spec-and-a-meta-test-holds-the-code-to-it`.
Type / Effort / Deps: feature / L / S-48.1, S-48.2, S-48.3.

### Living CAP citations

- `spec-pyforge-atlas` CAP-73 (minted 2026-11-10: the public contract is written beside the Spec and held to the code); FR-78 ← CAP-73

## Acceptance Criteria

Each command runs from the worktree root; read every verdict from its exit code, never through a pipe.

- **AC1 — The contract meta-test passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/meta/test_public_contract.py -q
  ```

- **AC2 — contract.md names every registered MCP tool.** Expected: exit 0, prints 13 [].

  ```bash
  python3 -c 'import ast,sys;t=ast.parse(open('"'"'src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py'"'"').read());d=next(n for n in t.body if isinstance(n,(ast.AnnAssign,ast.Assign)) and getattr(n.target if isinstance(n,ast.AnnAssign) else n.targets[0],'"'"'id'"'"','"'"''"'"')=='"'"'TOOL_SPECS'"'"');names=[k.value for k in d.value.keys];c=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md'"'"').read();bad=[n for n in names if chr(96)+n+chr(96) not in c];print(len(names),bad);sys.exit(1 if bad or len(names)<13 else 0)'
  ```

- **AC3 — contract.md names every pyforge.atlas flag key in the tree.** Expected: exit 0, prints 11 [].

  ```bash
  python3 -c 'import json,sys;k=sorted(x for x in json.load(open('"'"'src/platform/config/flags.json'"'"'))['"'"'flags'"'"'] if x.startswith('"'"'pyforge.atlas.'"'"'));c=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md'"'"').read();bad=[x for x in k if chr(96)+x+chr(96) not in c];print(len(k),bad);sys.exit(1 if bad else 0)'
  ```

- **AC4 — contract.md names the verbs, the outside reads and the exit codes as code tokens, and nothing of the retired views runtime.** Expected: exit 0, prints [].

  ```bash
  python3 -c 'import re,sys;c=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md'"'"').read();q=chr(96);need=['"'"'pyforge atlas run'"'"','"'"'pyforge atlas ipython'"'"','"'"'pyforge atlas package'"'"','"'"'PYFORGE_ATLAS_SEED_ROOT'"'"','"'"'PYFORGE_ATLAS_LOCAL_RECIPES_DIR'"'"','"'"'PYFORGE_ATLAS_LOCAL_RECIPES_REPO_SLUG'"'"','"'"'PYFORGE_ATLAS_DATA_ROOT'"'"','"'"'PYFORGE_ATLAS_LOCK_ROOT'"'"','"'"'PYFORGE_ATLAS_CREDENTIALED'"'"','"'"'cf_atlas.db'"'"','"'"'vuln-db'"'"','"'"'tools/lasuite_bringup.py'"'"','"'"'pyforge.core.hooks'"'"','"'"'pyforge.warden'"'"','"'"'POST /stations/atlas/mcp'"'"'];bad=[n for n in need if q+n+q not in c];m=re.search(r'"'"'(?ms)^## Exit codes\n(.*?)(?=^## |\Z)'"'"',c);sec=m.group(1) if m else '"'"''"'"';bad+=['"'"'exit code '"'"'+x for x in ['"'"'0'"'"','"'"'1'"'"','"'"'2'"'"','"'"'130'"'"','"'"'3'"'"','"'"'4'"'"'] if q+x+q not in sec];bad+=[x for x in ['"'"'PYFORGE_ATLAS_CFE_SCRIPTS_DIR'"'"','"'"'PYFORGE_ATLAS_LIVE_BOKEH_URL'"'"'] if x in c];print(bad);sys.exit(1 if bad else 0)'
  ```

- **AC5 — The test is not vacuous: one negative case per family.** Expected: exit 0 with at least 6 tests selected and passed (verbs, options, tools, flag keys, environment variables, exit codes).

  ```bash
  pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/meta/test_public_contract.py -q -k absent
  ```

- **AC6 — The Spec lists the companion.** Expected: exit 0 (the mint added the `companions:` line with CAP-73 on 2026-11-10).

  ```bash
  grep -qE '^  - contract\.md' _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  ```

## Boundaries & Constraints

**Always:**
- Derive every family from the code; one negative case per family adds a synthetic name and expects the comparison to fail.
- Spell every name in `contract.md` as a code token.

**Never:**
- Never hand-type a list the test trusts; never skip or `xfail` a family.
- Never edit `SPEC.md` or the memlog; never add a runtime path or a flag.

</intent-contract>

## Binding

- Parent: `spec-pyforge-atlas` CAP-73 (minted 2026-11-10: the public contract is written beside the Spec and held to the code); FR-78 ← CAP-73.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-11-10 (cutover readiness) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the entry of that date and its two addenda).
- Epic: Epic 47, minted 2026-11-10 with this story.
- Ledger key: `47-1-atlas-s-public-contract-is-written-beside-the-spec-and-a-meta-test-holds-the-code-to-it`.
- Deps: S-48.1, S-48.2, S-48.3.
- Cross-station deps: none.
- Followed by: steward:S-121.7 (classifies CAP-73 in the capability ledger, where `capability-ledger-check` is judged; it does not gate this story).
- Flag: `flag-exempt: detector-or-gate` (a gate is never flagged: a flag-OFF gate is a silent green).
- Surface: `marshal-policy.toml` `[epic_surfaces]."47"`, narrowed by this spec's `surface:`.
- Minted 2026-11-10 in the atlas mint of the one cutover-readiness PR (branch `cutover-readiness-2026-11-10`); built in the same PR.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: exit 0.

**Run before the push:** the acceptance commands above, each read from its exit code.

## Auto Run Result

Status: blocked (forward dependency on S-48.1, S-48.2 and S-48.3, 2026-11-10; minted 2026-11-10).

## Planned deferral (written at build)

The row below is not in the deferred-work ledger yet and is not in this spec's frontmatter (`deferred-work-check`
reds a frontmatter row with no tracked ledger twin). The atlas station closer of the cutover-readiness PR writes it
to `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md`.

- **`DW-atlas-47-1-1`** (low; owner atlas; location
  `src/shared/packages/pyforge-atlas/tests/meta/test_public_contract.py`): the meta-test derives environment reads
  exactly as the Approach names them (`os.environ.get`, `os.environ[...]`, `os.getenv`, the five reads through a
  variable, and `${env_or:…}` in `conf/base/*.yml`), in `src/` and `tools/`. Two reads stay outside that derivation,
  and `contract.md` lists both as prose the test does not judge: (1) four modules read through an `env` mapping that
  defaults to `os.environ` (`factory/lasuite.py`, `nl/backend.py`, `orchestration/definitions.py`,
  `pipelines/universal_sbom/gate.py`; 13 names, among them the five `PYFORGE_ATLAS_<KEY>` profile overrides built
  from `PROFILES` in a loop); (2) `wasm/build.py`, outside `src/` and `tools/`, whose `sys.exit("<message>")` exits
  `1`. Fix: extend the derivation to a mapping parameter whose default is `os.environ` (the profile loop needs its
  table resolved from `PROFILES`'s keys) and to the member's other script roots, then move those rows into the
  judged tables (spec-pyforge-atlas:CAP-73).

## Spec Change Log

- 2026-11-10: minted from the station Dream's entry of 2026-11-10 (cutover readiness) under the operator's rulings of 2026-11-10 ("Accept all", "Retire both", "Accept all, run mint"). Acceptance adjusted by the rulings: the views runtime is deleted (ruling 6), so the plan's branch for a stopped Story 48.3 is dropped; the `companions:` line was written at the mint.

- 2026-11-10 (review of the mint): steward:S-121.7 leaves the cross-station deps (the plan's deps are 48.1, 48.2 and 48.3; 121.7 only judges CAP-73's ledger class later) and is kept as a downstream note; CAP-73's flip to shipped is Story 48.4's (ruling 6).

- 2026-11-11 (third review of the mint): the key is `blocked` (forward dependency: Deps name S-48.1, S-48.2 and S-48.3, a later epic; the one policy every station took at this mint), and Deps take the `S-<epic>.<num>` grammar doctor's forward-dependency detector parses.

## Review Triage Log

- (none yet)
