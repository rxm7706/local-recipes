---
title: "38.3: Mason's adapters pass only what the wrapped scripts declare"
type: 'feature'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a meta-test only (spec-feature-flag-governance Q1; roster list)
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py
  - src/shared/packages/pyforge-mason/src/pyforge/mason/recipe.py
  - src/shared/packages/pyforge-mason/tests/integration/test_delegation_fidelity.py
  - .claude/skills/conda-forge-expert/SKILL.md
surface:
  - src/shared/packages/pyforge-mason/tests/meta/test_cfe_adapter_argv_live.py
deferred:
  - id: real-cfe-fidelity-nine-wrapped-scripts
    summary: "Mason's fidelity test runs one of ten wrapped scripts for real (validate); the other nine wrapped scripts have a static option check only. Generate, update, scan and submit need the network or credentials and submit is outward; the argv contract proper belongs to conda-forge-expert's own Spec (Story 39.2, blocked on the flip)."
    location: src/shared/packages/pyforge-mason/tests/integration/test_delegation_fidelity.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** An oracle gap the audit measured: the one real-CFE fidelity test covers `validate`; the other nine wrapped scripts are exercised only against stubs Mason wrote, so a renamed script or a dropped option in conda-forge-expert would leave Mason's suite green. A static, network-free check closes the part that needs no CFE run. No Mason or CFE code changes.

**Approach:**
- Read the script names from `pyforge.mason.cfe._CFE_SCRIPTS` and the options from the adapter functions by AST (string literals beginning `--` in `cfe.py` and `recipe.py` argument lists); never restate a script name or a CFE option in the test (CAP-7's knowledge-free rule; AD-3: script names live in `cfe.py` alone).
- The wrappers under `.claude/scripts/conda-forge-expert/` are thin: follow each to the canonical script it runs and read that file's `add_argument` calls as text. `native-build.sh` is checked for existence only.
- Paths are anchored on `Path(__file__)`; the test hands the repository root to no package code.
- A mismatch that is Mason's is fixed under this key only if it is a one-line adapter fix; otherwise, and always when it is CFE's, it is a `deferred:` row, never a CFE edit here.
- Lowest priority of the station: dropped first if the PR is over budget, and then its path leaves Story 37.1's integration check and the CAP-7 marker pair.

Ledger key: `38-3-mason-s-adapters-pass-only-what-the-wrapped-scripts-declare`.
Ledger status: `backlog`.
Type / Effort / Deps: feature / S / —.

### Living CAP citations

- **CAP-7** (amended 2026-11-10; FR-62): `tests/meta/test_cfe_adapter_argv_live.py` (live-tree half) exits 1 on a missing script or an undeclared option. Marker as in Story 38.2.
- AD-1, AD-3.
- `spec-feature-flag-governance` Q2: `flag-exempt: detector-or-gate`.

## Boundaries & Constraints

**Always:**
- Read source text; run nothing; need no network.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never edit `.claude/skills/conda-forge-expert/`, `.claude/scripts/conda-forge-expert/` or `build-locally.py` (a CFE change needs the skill and a retro).
- Never add behaviour or a flag (operator ruling 2026-11-10: no new behaviour and no new kill switch in this PR).
- Never append a `Surface reconcile` line to another Spec's memlog and never run `spec_surface_check.py --write-baseline`: Story 37.4 writes mason's reconcile event, each other Spec's closer writes its own, and doctor Story 58.4 runs every scoped stamp once, after the last edit (cutover readiness plan, integration 2026-11-10).

## Acceptance Criteria

**AC1 — The check passes on the tree.**

```bash
PYTHONPATH=src/shared/packages/pyforge-mason/src:scripts pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta/test_cfe_adapter_argv_live.py -q; echo $?
```

Expect: 0, with no test skipped when run from the repository root.

**AC2 — It is proven by planted violations.**

```bash
PYTHONPATH=src/shared/packages/pyforge-mason/src:scripts pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta/test_cfe_adapter_argv_live.py -q -k planted; echo $?
```

Expect: 0 and `2 passed`: a script table entry with no file, and a script source that lacks an option the adapter passes.

**AC3 — It never runs in the package half.**

```bash
grep -c '^pytestmark = pytest.mark.live_tree' src/shared/packages/pyforge-mason/tests/meta/test_cfe_adapter_argv_live.py
```

Expect: prints 1.

**AC4 — Any mismatch found is recorded, not patched in CFE.**

```bash
git diff --quiet a2a97a1eef -- .claude/skills/conda-forge-expert .claude/scripts/conda-forge-expert build-locally.py; echo $?
```

Expect: 0.

**AC5 — The live-run fidelity gap for the other nine scripts is recorded.**

```bash
python3 - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-38-3-*.md' 'wrapped scripts' <<'EOF'
"""Exit 0 when a story spec's frontmatter `deferred:` list carries one row for each phrase given (case-
insensitive match in the row's summary). Run from the repo root. argv: story spec path (glob allowed),
then one or more phrases."""
import glob
import sys

import yaml

path = sorted(glob.glob(sys.argv[1]))[0]
text = open(path, encoding="utf-8").read()
fm = yaml.safe_load(text.split("\n---", 1)[0].lstrip("-\n")) or {}
rows = [str(r.get("summary", "")).lower() for r in (fm.get("deferred") or []) if isinstance(r, dict)]
missing = [p for p in sys.argv[2:] if not any(p.lower() in r for r in rows)]
print(f"{path}: deferred rows={len(rows)} missing={missing}")
sys.exit(1 if missing else 0)
EOF
```

Expect: exit 0 once the build has written the row listed under Notes into this story spec's `deferred:` (exit 1 at mint, where `deferred: []`: the row is written at build, not at mint, and Story 37.4's intake mints its DW-mason twin).

**AC6 — Lint and types.**

```bash
pixi run -e pyforge-guild lint-types; echo $?
```

Expect: 0.

</intent-contract>

## Binding

- Parent: `spec-pyforge-mason`; amends CAP-7.
- Requirements: FR-62 ← CAP-7.
- Dream: `docs/dreams/pyforge-mason.md`, Realization log, *2026-11-10 (the cutover readiness audit)*.
- Epic 38, `### Story 38.3: Mason's adapters pass only what the wrapped scripts declare` in `planning-artifacts/epics.md`.
- Wave: BUILD-1 (cutover readiness plan).
- Findings closed: SHOULD: real-CFE fidelity covers validate only.

## Notes

- Cross-station: the root file `build-locally.py` joins steward's `mason_paths` trigger list (steward:S-124.2).
- Row this story writes to its `deferred:` at build, with any mismatch row the check finds (not at mint, so no row sits in frontmatter without a ledger twin; Story 37.4's intake mints the DW-mason twin, and `deferred-work-check` reads the row as `spec-frontmatter-only-deferral` until then):
  - id `real-cfe-fidelity-nine-wrapped-scripts`; severity low; location `src/shared/packages/pyforge-mason/tests/integration/test_delegation_fidelity.py`; summary: "Mason's fidelity test runs one of ten wrapped scripts for real (validate); the other nine wrapped scripts have a static option check only. Generate, update, scan and submit need the network or credentials and submit is outward; the argv contract proper belongs to conda-forge-expert's own Spec (Story 39.2, blocked on the flip)."

## Gate findings (build, BUILD-1)

- 2026-11-11, `pixi run -e pyforge-guild deferred-work-check` (exit 2): `spec-frontmatter-only-deferral` for this spec's frontmatter `deferred:` row `real-cfe-fidelity-nine-wrapped-scripts`, which has no twin in `pyforge-mason/planning-artifacts/deferred-work-ledger.md`. Not fixed here, by plan (Notes above): the mason ledger belongs to Story 37.4 (BUILD-9), whose intake mints the DW-mason twin. The finding stays red at each wave gate until 37.4 lands, unless the orchestrator moves the intake earlier.
