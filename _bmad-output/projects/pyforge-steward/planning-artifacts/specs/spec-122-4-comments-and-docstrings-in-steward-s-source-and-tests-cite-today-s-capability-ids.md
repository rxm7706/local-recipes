---
title: '122.4: Comments and docstrings in steward''s source and tests cite today''s capability ids'
type: 'chore'
created: '2026-11-10'
status: 'blocked'
difficulty: heavy
story: 122.4
spec: pyforge-steward
surface:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/**/*.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/data/bmad_core_releases/*.yaml
  - src/shared/packages/pyforge-steward/src/pyforge/steward/data/track.schema.json
  - src/shared/packages/pyforge-steward/tests/unit/**/*.py
  - src/shared/packages/pyforge-steward/tests/meta/**/*.py
  - src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py
context:
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
declared_low_risk: false
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-124.2, S-124.3).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** The rest of MUST 5: comment, docstring and data citations of absorbed Specs' ids.

**Approach:** A mechanical bulk edit of one family. It is the last story that edits steward source and tests, so it follows every story of this PR that does; on control-plane's files it touches comment lines only. A citation qualified with an absorbed Spec's name becomes `spec-pyforge-steward CAP-n`. One `event` entry on the steward memlog lists the migrated modules.

Ledger key: `122-4-comments-and-docstrings-in-steward-s-source-and-tests-cite-today-s-capability-ids`. Type / Effort / Deps: chore / L / S-120.5, S-121.1, S-121.2, S-121.3, S-121.6, S-121.7, S-122.3, S-124.2, S-124.3.

### Living CAP citations

- **`spec-pyforge-steward`** — every capability heading's provenance map; CHAIN-STANDARD section 6 (code citations migrate when their module is touched).

## Boundaries & Constraints

**Always:**
- Change comment, docstring and description text only.
- Keep the schema additive-only: a description is not a field.

**Never:**
- Never change code, a test body or a data value.
- Never append a `Surface reconcile` line or run a stamp.

## Acceptance Criteria

- **AC1 — the citation test covers comments and docstrings and passes.** Expected: exit 0, with the comment and docstring domain on for every .py under the package's src and tests (tokenize for comments, ast for docstrings).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py -q
  ```
- **AC2 — the new domain can fire.** Expected: exit 0 with at least 2 tests selected.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py -q -k 'fires and (comment or docstring)'
  ```
- **AC3 — every re-key follows the provenance map.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py -q -k rekey_pairs
  ```
- **AC4 — no code changed.** Expected: exit 0; prints the file count and `[]` (BASE is the `baseline_revision` in this story's spec frontmatter): each modified file's syntax tree, docstrings blanked, equals its tree at BASE.
  ```bash
  python3 -c "import ast,subprocess,sys
  b=sys.argv[1]
  fs=[f for f in subprocess.check_output(['git','diff','--diff-filter=M','--name-only',b,'HEAD','--','src/shared/packages/pyforge-steward'],text=True).split() if f.endswith('.py') and not f.endswith('test_cap_citations.py')]
  def n(s):
   t=ast.parse(s)
   for x in ast.walk(t):
    if isinstance(x,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and x.body and isinstance(x.body[0],ast.Expr) and isinstance(getattr(x.body[0],'value',None),ast.Constant) and isinstance(x.body[0].value.value,str): x.body[0].value.value=''
   return ast.dump(t)
  bad=[f for f in fs if n(subprocess.check_output(['git','show',b+':'+f],text=True))!=n(open(f).read())]
  print(len(fs),bad)
  sys.exit(bool(bad))" "$BASE"
  ```
- **AC5 — no line is added or removed.** Expected: prints 0.
  ```bash
  git diff --numstat "$BASE"..HEAD -- src/shared/packages/pyforge-steward/src/pyforge/steward src/shared/packages/pyforge-steward/tests/unit src/shared/packages/pyforge-steward/tests/meta ':(exclude)src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py' | awk '$1!=$2' | wc -l
  ```
- **AC6 — no pre-fold phrase anywhere in steward source or data.** Expected: exit 1 (no match; the comment, docstring and data lines Story 122.3's notes list still match before this story).
  ```bash
  git grep -nE 'hub:CAP-|pre-flight \(CAP-1\)|pipeline-truth \(CAP-1|CAP-8/A[D]-10|install-class CAP-3|CAP-2/6/7|CAP-9: retire|CAP-4 report-only|CAP-5 post-apply|CAP-1: report upstream|CAP-2: advance|CAP-1 report-only|CAP-2 one-command|topology.*CAP-6\)|Story 9\.5, CAP-6|CAP-4 audit trail|CAP-4.s .who saw|class-path \(CAP-3\)|CAP-3 path is|dated-extracts CAP-4|CAP-1 whole-pipeline|Automated CAP-2 advance|CAP-3 (clear|incomplete)|deliberate apply \(CAP-2\)|## CAP-[378] |CAP-1 preflight consumed|CAP-5 prove-landed|CAP-5 verdict|for CAP-2 del' -- src/shared/packages/pyforge-steward/src/pyforge/steward
  ```
- **AC7 — package data keeps its structure.** Expected: exit 0; prints `[]` (BASE is the `baseline_revision` in this story's spec frontmatter): each changed YAML or JSON file under data/ parses to the same value at BASE and HEAD with every `description` blanked.
  ```bash
  python3 -c "import json,yaml,subprocess,sys
  b=sys.argv[1]
  def s(o):
   if isinstance(o,dict): return {k:(None if k=='description' else s(v)) for k,v in o.items()}
   if isinstance(o,list): return [s(x) for x in o]
   return o
  fs=subprocess.check_output(['git','diff','--name-only',b,'HEAD','--','src/shared/packages/pyforge-steward/src/pyforge/steward/data'],text=True).split()
  L=lambda f,t:(json.loads if f.endswith('.json') else yaml.safe_load)(t)
  bad=[f for f in fs if s(L(f,subprocess.check_output(['git','show',b+':'+f],text=True)))!=s(L(f,open(f).read()))]
  print(bad);sys.exit(bool(bad))" "$BASE"
  ```
- **AC8 — package half.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-test
  ```
- **AC9 — live-tree half.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```
- **AC10 — lint and types.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild lint-types
  ```

</intent-contract>

## Binding

Parent: `spec-pyforge-steward` (CHAIN-STANDARD section 6)

- Dream: `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth* (subsection *The steward Spec, suite and shared surfaces*) and `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the steward-station mint entry).
- Epic: Epic 122.
- Ledger key: `122-4-comments-and-docstrings-in-steward-s-source-and-tests-cite-today-s-capability-ids` (`backlog` at mint).
- Deps: S-120.5, S-121.1, S-121.2, S-121.3, S-121.6, S-121.7, S-122.3, S-124.2, S-124.3.
- Surface: `src/shared/packages/pyforge-steward/src/pyforge/steward/**/*.py` (comment and docstring lines only), `src/shared/packages/pyforge-steward/src/pyforge/steward/data/bmad_core_releases/*.yaml` (comment lines only), `src/shared/packages/pyforge-steward/src/pyforge/steward/data/track.schema.json` (the `description` string at :5 only), `src/shared/packages/pyforge-steward/tests/unit/**/*.py and src/shared/packages/pyforge-steward/tests/meta/**/*.py` (comment and docstring lines only), `src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py` (the comment and docstring domain is switched on).
- Minted 2026-11-10 by the cutover-readiness mint (steward-station unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py -q` — expected: exit 0, with the comment and docstring domain on for every .py under the package's src and tests (tokenize for comments, ast for docstrings).
- `pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py -q -k 'fires and (comment or docstring)'` — expected: exit 0 with at least 2 tests selected.

## Notes

- Cross-station: none. Story 29.5 recompiles the skill after it; no line moves, so `[SRC:]` references stay valid.
- `$BASE` in the acceptance criteria is the `baseline_revision` the build writes into this spec's frontmatter when it starts (the commit it starts from); it is not set at mint.
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (steward and host: Story 122.5) and doctor Story 58.4 runs every scoped stamp once, after the last edit.
