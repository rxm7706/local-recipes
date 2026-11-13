---
title: "25.2: The warden PRD, spine, brief and epics follow the Spec, and the chain closes"
type: 'docs'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: 'medium'
story: '25.2'
spec: _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
surface:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/prds/prd-pyforge-warden-2026-07-14/prd.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/architecture/architecture-pyforge-warden-2026-07-14/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/briefs/brief-pyforge-warden-2026-07-25/brief.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - docs/dreams/pyforge-warden.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/test-architecture.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/retros/retro-pyforge-warden-2026-11-*.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/implementation-readiness-report-2026-11-*.md
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - docs/dreams/pyforge-warden.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/prds/prd-pyforge-warden-2026-07-14/prd.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/architecture/architecture-pyforge-warden-2026-07-14/ARCHITECTURE-SPINE.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-26.1, S-26.2, S-26.3, S-27.1).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).
>
> **Unblocked 2026-11-13.** Every story its Deps name is `done` on branch `cutover-readiness-2026-11-10`. The operator's "Start build" consent covered the unblock; CLOSE-LEDGERS moved the key to `done`.

<intent-contract>

## Intent

**Problem:** The PRD, spine, brief, epics and Dream still say what the Spec said before this change: NFR-C1, the spine's two floor lines and the epics *Portability* line read Python 3.12; NFR-S9 and the epics S9 item claim an age for the conda-to-pypi map; the bypass journey's climax names the unbuilt `review_required`; the spine's Project Structure tree predates most modules and says `--deterministic` pinning lives in `report.py` and `cli.py`; the Dream's *What is real* states a stale story count and the dead legacy path. As the change's closer, this story also lands the cascade, the reconcile event and CAP-28's marker after every other edit.

**Approach:** **PRD.** The mint registered FR-44..FR-50 (§ *Currency reconciliation — 2026-11-10 (the cutover readiness mint)*, each traced from its capability) and re-traced FR-43 to `← CAP-26, CAP-29` (the operator's split). This story owns every other PRD edit: NFR-C1's floor; NFR-S9 narrowed to the LTS registry (the map carries no snapshot; operator ruling 2026-11-10); the journey climax at about :243 (Alex sees the waiver through status `bypassed` and the waiver stanza; the dated record sections keep their wording); the Epic 9 history line's bare `CAP-18` qualified as `spec-pyforge-unifying-strategy:CAP-18`; a section *Currency reconciliation — 2026-11-10 (Story 25.2)*. FR-51 is the next free id.

**Spine.** Replace the Project Structure tree with the module map as built (every module under `src/pyforge/warden`, including `sast.py`, `native_lockfiles.py`, `fix_solver.py`, `manifest_*.py`, `fleet_github_*.py`, `tea_advisory.py`, `scanner_plugins.py`, `hooks.py`), correct the two floor lines and the 2026-08-26 sentence on `--deterministic`, and append *Currency reconciliation — 2026-11-10*.

**Brief, epics, Dream.** The brief and epics take the dated re-stamp. `epics.md:79` *C1 Python ≥ 3.12* becomes 3.14; S9 narrows like NFR-S9; Story 21.1 gains `**Status:** done` (healed tissue). The Dream's two *What is real* bullets state no story count (they point at the ledger) and name `archive/docs/specs/pyforge-warden.md`.

**Spec.** CAP-28's marker `(ready 2026-11-10)` becomes `(shipped <the day 26.1, 26.2 and 26.3 are all done>)` and `companions:` gains `contract.md` and `proof-map.md`: one memlog entry, the script render, both self-validate passes; one `updated:` key. No clause is re-worded.

**Close.** Regenerate the Story Coverage Matrix with `python _bmad/scripts/bmad_tea_playwright.py --project pyforge-warden` after the last story block and test file (never hand-edit it). Append one `(event)` `Surface reconcile 2026-11-10` memlog entry naming every path under the package that Stories 25.3, 26.1, 26.2, 26.3 and 27.1 changed and why (literal full paths, from `git diff --name-only origin/main...HEAD`), then `git add`; doctor Story 58.4 runs the scoped stamps once, after the last edit. Run `bmad-retrospective` over Epics 25-27 and the bmad readiness check (frontmatter `updated:`).

Ledger key: `25-2-the-warden-prd-spine-brief-and-epics-follow-the-spec-and-the-chain-closes`.
Type / Effort / Deps: docs / M / S-25.1, S-25.3, S-25.4, S-26.1, S-26.2, S-26.3, S-27.1 (the cross-station deps are under Binding).

### Living CAP citations

- spec-one-chain-per-station:CAP-5 (a requirement cites defined CAPs; CHAIN-STANDARD § 12).
- spec-pyforge-warden CAP-28: its marker moves to shipped here (decision D4).
- The warden capabilities FR-43..FR-50 realize, traced at the mint; no CAP minted.
- Decisions D4 and D6 of the 2026-11-10 cutover readiness plan.
- `spec-feature-flag-governance` Q1: a `docs` story needs no flag.

## Boundaries & Constraints

**Always:**
- Re-stamp only; keep exactly one `updated:` key per artifact.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not hand-edit `test-architecture.md`, `sprint-status-ledger.yaml` or `SPEC.md`.
- Do not touch `docs/governance/fr-baseline.json`.
- Do not re-word a capability clause.
- Do not stamp the spec-surface baseline yourself (doctor Story 58.4 does, once).

</intent-contract>

## Acceptance Criteria

- **AC1 — Every warden requirement cites defined CAPs.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run -e pyforge-guild fr-without-cap-check`
  Expect: exit 0.
- **AC2 — Every capability CAP-1..CAP-29 has at least one FR or NFR arrow.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,sys;c=set();[c.update(int(x) for x in re.findall(r'(?<![a-z-]:)CAP-(\d+)',(l.split('←',1)[1].split(':')[0] if l.startswith('- **') else l.split('←',1)[1]))) for l in open('_bmad-output/projects/pyforge-warden/planning-artifacts/prds/prd-pyforge-warden-2026-07-14/prd.md') if re.match(r'^(- \*\*N?FR-|#### FR-)',l) and '←' in l];m=[n for n in range(1,30) if n not in c];print(m);sys.exit(1 if m else 0)"`
  Expect: prints [], exit 0.
- **AC3 — NFR-C1, the two spine lines and the epics Portability line state Python 3.14.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,sys;p=[l for l in open('_bmad-output/projects/pyforge-warden/planning-artifacts/prds/prd-pyforge-warden-2026-07-14/prd.md') if l.startswith('- **NFR-C1**')];s=[l for l in open('_bmad-output/projects/pyforge-warden/planning-artifacts/architecture/architecture-pyforge-warden-2026-07-14/ARCHITECTURE-SPINE.md') if re.match(r'^- (python|Language/runtime)',l)];e=[l for l in open('_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md') if l.startswith('- **Portability:**')];bad=[l[:60] for l in p+s+e if '3.14' not in l or '3.12' in l];print(bad,len(p),len(s),len(e));sys.exit(1 if bad or not p or len(s)<2 or not e else 0)"`
  Expect: prints [] and three non-zero counts, exit 0.
- **AC4 — The PRD's bypass journey names the bypassed status, not the unbuilt field.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import sys;l=[x for x in open('_bmad-output/projects/pyforge-warden/planning-artifacts/prds/prd-pyforge-warden-2026-07-14/prd.md') if x.startswith('**Climax')];w=[x for x in l if x.startswith('**Climax — the other side')];print(len(l),len(w));sys.exit(0 if len(w)==1 and not any('review_required' in x for x in l) and 'bypassed' in w[0] else 1)"`
  Expect: prints 5 1, exit 0 (no journey climax names review_required; the bypass journey's climax at :243 names bypassed).
- **AC5 — NFR-S9 in the PRD and S9 in the epics inventory claim an age only for the LTS registry.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import sys;p=[l for l in open('_bmad-output/projects/pyforge-warden/planning-artifacts/prds/prd-pyforge-warden-2026-07-14/prd.md') if l.startswith('- **NFR-S9')];e=[l for l in open('_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md') if l.startswith('- **Security:**')];b=[l[:60] for l in p+e if 'LTS registry, conda→pypi map) carry' in l or 'LTS-registry/map-derived' in l or 'LTS' not in l];print(len(p),len(e),b);sys.exit(1 if b or not p or not e else 0)"`
  Expect: prints 1 1 [], exit 0 (the two old phrases are gone and each line still names the LTS registry).
- **AC6 — The Epic 9 history line qualifies the foreign capability.** Run from the repo root, verdict from the exit code (never through a pipe):
  `bash -c "! grep -q 'canopy:FR-44, CAP-18 retrofit' _bmad-output/projects/pyforge-warden/planning-artifacts/prds/prd-pyforge-warden-2026-07-14/prd.md && grep -q 'spec-pyforge-unifying-strategy:CAP-18' _bmad-output/projects/pyforge-warden/planning-artifacts/prds/prd-pyforge-warden-2026-07-14/prd.md"`
  Expect: exit 0.
- **AC7 — The spine names every shipped module.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import pathlib,sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/architecture/architecture-pyforge-warden-2026-07-14/ARCHITECTURE-SPINE.md').read();m=sorted(p.name for p in pathlib.Path('src/shared/packages/pyforge-warden/src/pyforge/warden').rglob('*.py') if p.name!='__init__.py' and p.name not in t);print(m);sys.exit(1 if m else 0)"`
  Expect: prints [], exit 0.
- **AC8 — The Dream's 'What is real' states no stale count and no dead legacy path.** Run from the repo root, verdict from the exit code (never through a pipe):
  `bash -c "! grep -q '43/43 stories merged' docs/dreams/pyforge-warden.md && ! grep -qE '^  .docs/specs/pyforge-warden.md. is the absorbed' docs/dreams/pyforge-warden.md && grep -q 'archive/docs/specs/pyforge-warden.md' docs/dreams/pyforge-warden.md"`
  Expect: exit 0.
- **AC9 — The Story Coverage Matrix holds every story of the change.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run -e pyforge-guild tea-playwright-check`
  Expect: exit 0.
- **AC10 — The generated matrix was regenerated after the last story block and test file.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,pathlib,sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/test-architecture.md').read();s=int(re.search(r'^story_count: (\d+)',t,re.M).group(1));f=int(re.search(r'^test_file_count: (\d+)',t,re.M).group(1));e=len(re.findall(r'^### Story \d',open('_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md').read(),re.M));n=len(list(pathlib.Path('src/shared/packages/pyforge-warden/tests').rglob('test_*.py')));print(s,e,f,n);sys.exit(0 if s==e and f==n else 1)"`
  Expect: prints two equal pairs, exit 0.
- **AC11 — Every package path the branch changed is named in a Surface reconcile memlog entry.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import subprocess,sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md').read();c=subprocess.run(['git','diff','--name-only','origin/main...HEAD','--','src/shared/packages/pyforge-warden'],capture_output=True,text=True,check=True).stdout.split();m=[p for p in c if p not in t];print(len(c),m);sys.exit(1 if m or not c else 0)"`
  Expect: prints a non-zero count and [], exit 0.
- **AC12 — CAP-28 reads shipped and the frontmatter lists both new companions, which exist.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,os,sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md').read();fm=t.split('---',2)[1];ok=bool(re.search(r'^- \*\*CAP-28 [^\n]*\(shipped 2026-11-',t,re.M)) and 'contract.md' in fm and 'proof-map.md' in fm and os.path.isfile('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md') and os.path.isfile('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/proof-map.md') and len(re.findall(r'^updated:',fm,re.M))==1;sys.exit(0 if ok else 1)"`
  Expect: exit 0.
- **AC13 — Dream, governance and chain detectors.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run -e pyforge-guild dream-chain-check && pixi run -e pyforge-guild dreams-hygiene-check && pixi run -e pyforge-guild governance-currency && pixi run -e pyforge-guild chain-completeness-check && pixi run -e pyforge-guild status-body-consistency-check`
  Expect: exit 0.
- **AC14 — Cross-unit observable: the package manifest floors read 3.14 and no package file names the dead legacy path (steward-station Story 124.3).** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import tomllib,subprocess,sys;d=tomllib.load(open('src/shared/packages/pyforge-warden/pixi.toml','rb'))['package'];g=subprocess.run(['git','grep','-l','docs/specs/pyforge-warden.md','--','src/shared/packages/pyforge-warden'],capture_output=True,text=True).stdout.split();print(d['host-dependencies']['python'],d['run-dependencies']['python'],g);sys.exit(0 if d['host-dependencies']['python']=='>=3.14' and d['run-dependencies']['python']=='>=3.14' and not g else 1)"`
  Expect: prints >=3.14 >=3.14 [], exit 0, once Story 124.3 is on the branch.
- **AC15 — Cross-unit observable: every Spec CAP has a ledger row (control-plane's regenerated ledger).** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run -e pyforge-guild capability-ledger-check`
  Expect: exit 0, once control-plane's ledger story is on the branch.
- **AC16 — Cross-unit observable: steward's live half passes with warden's new readers (steward-station Story 124.2).** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run --frozen -e pyforge-steward pyforge-steward-live-test`
  Expect: exit 0.
- **AC17 — no unreconciled drift row names pyforge-warden/spec-pyforge-warden (the closer's memlog names every changed path; doctor 58.4 stamps).** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources spec-surface --json > "${TMPDIR:-/tmp}/ss.json"; python3 -c "import json,sys;d=json.load(open(sys.argv[1]));rows=d if isinstance(d,list) else (d.get('findings') or d.get('rows') or []);n=[r for r in rows if r.get('check') in ('drift','drift-presumed') and sys.argv[2] in json.dumps(r)];print(len(n));sys.exit(1 if n else 0)" "${TMPDIR:-/tmp}/ss.json" pyforge-warden/spec-pyforge-warden`
  Expect: prints 0, exit 0.
- **AC18 — the warden retro is dated on or after the last package-manifest commit.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import glob,re,subprocess,sys;f=sorted(glob.glob('_bmad-output/projects/pyforge-warden/planning-artifacts/retros/retro-pyforge-warden-2026-1*.md'));d=re.search(r'\d{4}-\d{2}-\d{2}',f[-1]).group(0) if f else '';c=subprocess.run(['git','log','-1','--format=%cs','--','src/shared/packages/pyforge-warden/pyproject.toml'],capture_output=True,text=True).stdout.strip();print(d,c);sys.exit(0 if d and d>=c else 1)"`
  Expect: prints two dates, the retro's not earlier; exit 0.
- **AC19 — warden's readiness gate is fresh.** Run from the repo root, verdict from the exit code (never through a pipe):
  `ls _bmad-output/projects/pyforge-warden/planning-artifacts/implementation-readiness-report-2026-1*.md`
  Expect: lists one file or more.
- **AC20 — warden's chain is current: no feeds finding and no shelf finding, read from the exit code.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run --frozen -e pyforge-guild chain-currency-sweep-check -- --project pyforge-warden`
  Expect: exit 0 (1 is a finding, 2 could not run; never through a pipe).

## Binding

- Story: `_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md` § *Story 25.2: The warden PRD, spine, brief and epics follow the Spec, and the chain closes*.
- Dream: `docs/dreams/pyforge-warden.md`, Realization log, *2026-11-10 (the cutover readiness audit)*; the operator's rulings of 2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md`, Realization log, second addendum).
- Ledger key: `25-2-the-warden-prd-spine-brief-and-epics-follow-the-spec-and-the-chain-closes`.
- Deps: S-25.1, S-25.3, S-25.4, S-26.1, S-26.2, S-26.3, S-27.1.
- Flag: none (a `docs` story, `spec-feature-flag-governance` Q1).
- Cross-station deps: `steward:S-121.7` (the capability ledger's warden rows, CAP-27..CAP-29 among them), `steward:S-124.2` (the live-tree half that AC16 runs) and `steward:S-124.3` (the package manifest's Python floor and its re-lock). AC14, AC15 and AC16 pass only once those three steward stories are on the branch; a failure there names the missing cross-unit edit, not a warden defect.
- The warden chain-currency cascade is planned red from the mint's memlog appends until this story lands.

## Planned deferral (written at build)

- **Five `live_tree` test modules derive the repository root at import** (found 2026-11-12 by this story's
  retrospective, `retros/retro-pyforge-warden-2026-11-12.md` finding 5 and action 1). Evidence:
  `src/shared/packages/pyforge-warden/tests/meta/test_public_contract.py:59`,
  `tests/meta/test_contract_surface.py:75`, `tests/integration/test_pixi_lock_environment_scope.py:19`,
  `tests/unit/test_currency_cfe_parity.py:22` and `tests/integration/test_fix_solver_real_pixi.py:29` evaluate
  `Path(__file__).resolve().parents[6]` at module level (and `tests/meta/test_pixi_range_floor_matches_workspace.py:31`
  climbs from `pyforge.warden.__file__`); the package half deselects them with `-m "not slow and not live_tree"` only
  after importing them, so an export of the package to a path fewer than seven components deep raises `IndexError`
  at collection. Fix: compute the root in a fixture or function, as `tests/meta/test_capability_proof_map.py:315`
  does, and have `tests/meta/test_live_tree_marker.py` fail a module-level climb above the package root. Owner:
  warden. Severity: low (both halves collect and pass in this checkout). Why deferred: the modules are Stories 26.1,
  26.3 and 27.1's, outside this story's files, and the fix is a test change no story of this change carries. The
  ledger row is written by whoever owns `deferred-work-ledger.md` at the change's close (this story's files do not
  include it).
