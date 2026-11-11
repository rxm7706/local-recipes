---
title: "50.4: Herald's source comments and docstrings cite the folded Spec's capability ids"
type: 'chore'
created: '2026-11-10'
status: 'blocked'
difficulty: easy
story: '50.4'
spec: pyforge-herald
surface:
  - src/shared/packages/pyforge-herald/src/pyforge/herald/**/*.py   # comment and docstring lines only; not cli.py (Story 50.3) and not local_ship.py's code lines (Story 52.2)
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-50-4-herald-s-source-comments-and-docstrings-cite-the-folded-spec-s-capability-ids.md   # a Planned deferral section only, if a citation cannot be placed
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/rekey-2026-09-17.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - scripts/coverage_gate.py
warnings: []
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-52.2).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** 70 citations on 67 lines in 11 modules under `src/shared/packages/pyforge-herald/src` name capability
ids from before the 2026-09-17 remint (measured at `82a2b18828`, from which herald's `src` has not moved on this
branch at mint): the audit counted 93, and `cli.py`'s 23 citations on 22 lines are Story 50.3's. A second root reading
the oracle cannot tell which capability a module serves (audit MUST 8, part). Herald had planned to defer
this, on the premise that a re-key would put 23 modules under the touched-module 80 % coverage floor. That premise is
refuted: `scripts/coverage_gate.py`'s `ast_fingerprint` drops docstrings and comments, so an edit that changes only
them is format-only, and the module does not count as touched (steward Story 66.1).

**Approach:** A chore under CHAIN-STANDARD § 6 (code-cited ids migrate), the same family as steward:S-122.4. The map
is the folded Spec's: each pre-remint `CAP-n` becomes the spec-pyforge-herald id that absorbed it, per the 2026-09-17
remint table in the Spec's memlog and `planning-artifacts/rekey-2026-09-17.md`. No behaviour changes. The one memlog
`event` line for these paths is Story 50.2's (the closer), not this story's. This story carries the work the plan
had reserved as `DW-herald-50-3-1`, so that row is never minted.

**The sites, measured at mint.** A site is a line of a herald `src` module other than `cli.py` and `local_ship.py`, at
`82a2b18828`, that carries a bare `CAP-1`..`CAP-8` or a pre-fold Spec name before `CAP-n` (`spec-design-sync-loop`,
`spec-pptx-custom-shapes`), and is not a citation of spec-pyforge-core (`Story 14.2`, `Story 14.3`,
`SPEC-pyforge-core`). Line numbers are at `82a2b18828`:

- `deck_pipeline.py`: 1, 17, 26, 39, 100, 158, 325, 562, 626, 716, 789, 821, 896, 922, 993, 1188, 1285, 1317, 1460,
  1506, 1508, 1522, 1529, 1531, 1553, 1590, 1592, 1603, 1651, 1676, 1932, 1935, 1963
- `deck_qa.py`: 389 · `errors.py`: 99, 170, 179, 180, 191 · `pptx_pipeline.py`: 1, 36
- `registry.py`: 9, 437, 447, 517, 519, 553 · `state.py`: 3, 4 · `sync_all.py`: 1, 2, 688
- `transport/agent_sdk_transport.py`: 435 · `transport/base.py`: 8, 11, 16, 21, 43, 117, 266, 321, 389, 404
- `transport/mcp_transport.py`: 129, 508 · `watch.py`: 1, 210

Each site is re-keyed, or named as `` `<module>:<line>` `` (the line at `82a2b18828`) with its reason in a
`## Planned deferral (written at build)` section of this spec. Four are known at mint to stay: `registry.py:437` is
code (the f-string heading `(spec-design-sync-loop CAP-6)` that the push-and-prove ledger writes; changing it changes
output, which this story may not), and `registry.py:447` is the docstring that quotes it. `transport/base.py:117`
(inside the attribute docstring of `MODERNIST_DESIGN_SYSTEM_ID`, lines 114-121) and `transport/mcp_transport.py:129`
(the attribute docstring of `_FETCH_TIMEOUT_SECONDS`, lines 129-131) are string statements that follow an
assignment, not the first statement of a body: AC1's fingerprint and `scripts/coverage_gate.py`'s `ast_fingerprint`
drop only a body's first-statement docstring, so they keep these as code, and re-keying either changes the AST and
fails AC1 (checked 2026-11-11 by a tokenize and `ast` pass over the 67 sites at `82a2b18828`: these two and
`registry.py:437` are the only sites that are neither a comment nor a first-statement docstring). A site whose number already
names the folded capability (for example a bridge `CAP-4` that the folded Design-Code-Bridge CAP-4 covers) is also
named there, with that reason. The other 22 citation lines stay as written: they name a folded id already (`CAP-30`,
`CAP-50`, `CAP-53`..`CAP-61`), a spec-pyforge-core id (`spec-pyforge-core:CAP-2`, `spec-pyforge-core:CAP-3` and
`spec-pyforge-core:CAP-5`, cited bare beside Story 14.2 or 14.3) or `spec-pyforge-steward:CAP-137` (cited bare beside
steward Story 59.6). They sit in 17 modules, 12 of which hold no site.

Ledger key: `50-4-herald-s-source-comments-and-docstrings-cite-the-folded-spec-s-capability-ids`.
Type / Effort / Deps: chore / S / S-50.1, S-50.3, S-52.2.

## Boundaries & Constraints

**Always:**
- Change comment and docstring lines only: every edited module keeps the same syntax tree once docstrings are
  dropped. A docstring here is the first statement of a module, class or function body; a string statement after
  an assignment (an attribute docstring) is not one, and the fingerprint keeps it.
- Re-key through the remint map, never by guess. A citation the map cannot place, a site that already names the
  folded id, or a site that is not a comment or a first-statement docstring (re-keying it changes the AST) is kept
  as written and listed in a `## Planned deferral (written at build)` section appended to this
  story spec, as `` `<module>:<line>` `` (the line at `82a2b18828`) with its reason. Story
  50.2 (the closer) writes its deferred-work row as `DW-herald-50-4-1` and this spec's `deferred:` entry in the same
  change, as it does for the other stories' planned deferrals; `deferred-work-check` refuses a frontmatter deferral
  with no tracked row, so this story writes neither.

**Never:**
- Never touch `cli.py` (Story 50.3) or `local_ship.py`'s code lines (Story 52.2), and never edit tests.
- Never write `SPEC.md`, the memlog, the deferred-work ledger, this spec's `deferred:` frontmatter or any other
  planning file. The one planning edit allowed is the Planned deferral section above, in this story spec.

## Acceptance Criteria

Each verdict is read from the exit code, never through a pipe.

- **AC1 — Same syntax tree.** Every herald source module this story edits has the same syntax tree once docstrings
  are dropped (`BASE` is this spec's `baseline_revision`). Expected: exit 0, printing the file count and `[]`.

```bash
python3 -c "import ast,subprocess,sys
b=sys.argv[1]
def fp(t):
 tr=ast.parse(t)
 for n in ast.walk(tr):
  for f in ('body','orelse','finalbody'):
   v=getattr(n,f,None)
   if isinstance(v,list) and v and isinstance(v[0],ast.Expr) and isinstance(getattr(v[0],'value',None),ast.Constant) and isinstance(v[0].value.value,str): setattr(n,f,v[1:])
 return ast.dump(tr)
fs=[f for f in subprocess.check_output(['git','diff','--diff-filter=M','--name-only',b,'HEAD','--','src/shared/packages/pyforge-herald/src'],text=True).split() if f.endswith('.py') and not f.endswith(('/cli.py','/local_ship.py'))]
bad=[f for f in fs if fp(subprocess.check_output(['git','show',b+':'+f],text=True))!=fp(open(f).read())]
print(len(fs),bad);sys.exit(bool(bad))" "$BASE"
```

- **AC2 — Every site is re-keyed or named.** For each of the 67 sites listed in the Approach, its line text at
  `82a2b18828` no longer occurs in that module, unless the Planned deferral section names it as
  `` `<module>:<line>` ``. Expected: exit 0, printing `67`, the count of named sites (at least 4: `registry.py:437`,
  `registry.py:447`, `transport/base.py:117` and `transport/mcp_transport.py:129`) and `[]`. On today's tree, and on any hollow landing, it exits 1 and lists every site not re-keyed.

```bash
python3 - <<'EOF'
import re,subprocess,sys
M='82a2b18828'
R='src/shared/packages/pyforge-herald/src/pyforge/herald/'
SITES={'deck_pipeline.py':[1,17,26,39,100,158,325,562,626,716,789,821,896,922,993,1188,1285,1317,1460,1506,1508,1522,1529,1531,1553,1590,1592,1603,1651,1676,1932,1935,1963],
 'deck_qa.py':[389],'errors.py':[99,170,179,180,191],'pptx_pipeline.py':[1,36],
 'registry.py':[9,437,447,517,519,553],'state.py':[3,4],'sync_all.py':[1,2,688],
 'transport/agent_sdk_transport.py':[435],'transport/base.py':[8,11,16,21,43,117,266,321,389,404],
 'transport/mcp_transport.py':[129,508],'watch.py':[1,210]}
spec=open('_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-50-4-herald-s-source-comments-and-docstrings-cite-the-folded-spec-s-capability-ids.md').read()
sec=re.search(r'^## Planned deferral \(written at build\)\n(.*?)(?=^## |\Z)',spec,re.M|re.S)
named=set(re.findall(r'`([\w/]+\.py):(\d+)`',sec.group(1))) if sec else set()
left=[]
for mod,lines in SITES.items():
    old=subprocess.run(['git','show',M+':'+R+mod],capture_output=True,text=True,check=True).stdout.split('\n')
    new=open(R+mod).read().split('\n')
    left+=[f'{mod}:{n}' for n in lines if (mod,str(n)) not in named and old[n-1] in new]
print(sum(map(len,SITES.values())),len(named),left); sys.exit(1 if left else 0)
EOF
```

- **AC3 — Only re-keyed citations are added.** Every added line under herald's `src` (outside `cli.py` and
  `local_ship.py`) carries a `CAP-` citation. The diff is written to a file and judged in Python, with no pipe; an
  empty diff fails. Expected: exit 0, printing the added and removed line counts (each at least 1) and `[]`.

```bash
D="${TMPDIR:-/tmp}/d50-4.diff"
git diff -U0 "$BASE" HEAD -- src/shared/packages/pyforge-herald/src ':!*/cli.py' ':!*/local_ship.py' > "$D" && python3 - "$D" <<'EOF'
import sys
d=open(sys.argv[1]).read().split('\n')
add=[l for l in d if l.startswith('+') and not l.startswith('+++')]
rem=[l for l in d if l.startswith('-') and not l.startswith('---')]
bad=[l[:80] for l in add if 'CAP-' not in l]
print(len(add),len(rem),bad); sys.exit(1 if bad or not add else 0)
EOF
```

- **AC4 — The package half and lint pass.**
  `pixi run --frozen -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests -q -m 'not slow and not live_tree' && pixi run --frozen -e pyforge-guild lint-types`.
  Expected: exit 0.

</intent-contract>

## Binding

- No CAP is minted and no FR or AD moves. Code-cited ids migrate under CHAIN-STANDARD § 6, with spec-pyforge-herald's
  2026-09-17 remint table as the map.
- Dream: `docs/dreams/pyforge-herald.md`, the 2026-11-10 (cutover readiness) entry.
- Epic 50. Ledger key `50-4-herald-s-source-comments-and-docstrings-cite-the-folded-spec-s-capability-ids`.
- Sibling: steward:S-122.4 (the same re-key over steward's source and tests).
- Findings closed: MUST 8, part (the audit's 93 pre-fold citations less `cli.py`'s 23: 70 citations on the 67 sites
  in 11 modules listed in the Approach).

## Spec Change Log

- 2026-11-10: minted (backlog) by the integrated plan. It replaces the deferral the herald plan had drafted as
  `DW-herald-50-3-1`, whose stated blocker `scripts/coverage_gate.py`'s `ast_fingerprint` refutes.
- 2026-11-10: status set to blocked (forward dependency on a later epic; unblocked only with operator confirmation).
- 2026-11-11: the mint's review found that no acceptance check failed on an empty diff, and that AC2 read its verdict
  through a pipe. The 67 sites are now listed in the Approach, measured at `82a2b18828` (70 citations in 11 modules,
  not the earlier '71 in 22 modules', which subtracted `cli.py`'s lines from the audit's citation count); a new AC2
  fails until each site is re-keyed or named in the Planned deferral section; AC3 (formerly AC2) reads the diff from a
  file and judges it in Python; the package-half AC is now AC4.
- 2026-11-11 (second review): `transport/base.py:117` and `transport/mcp_transport.py:129` are attribute docstrings
  (string statements after an assignment), which AC1's fingerprint and `scripts/coverage_gate.py` keep as code, so
  the plan's instruction to re-key them broke AC1. Verified by a tokenize and `ast` pass over the 67 sites at
  `82a2b18828` (re-keying either changes both fingerprints; the other sites are comments or first-statement
  docstrings, but for `registry.py:437`). Both join the known stays beside `registry.py:437`, the Always rule allows
  keeping a site that is not a comment or a first-statement docstring, and AC2's expected text and the epics Then line
  name the four.
