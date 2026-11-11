---
title: '120.4: The nine Frames point at the seed and agree with the rulings'
type: 'docs'
created: '2026-11-10'
status: 'backlog'
flag-exempt: docs-only
difficulty: medium
story: 120.4
spec: pyforge-steward
surface:
  - docs/foundry/frames/pyforge.frame.md
  - docs/foundry/frames/stations/*.frame.md
  - docs/foundry/frames/README.md
  - docs/foundry/frames/upstream-pin.yaml
  - docs/foundry/frames/conformance-profile.yaml
  - docs/foundry/frames/frame-index.yaml
  - docs/foundry/frames/browse.yaml
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/foundry/frames/README.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Ruling 1 (A writes the Frames until the flip; a Frame is a pointer, not a seed) and audit defects: the company and Mason Frames contradict the 2026-09-28 Mason-skills ruling, the steward Frame names 7 of 31 duties, and the upstream pin is two months old. Each station unit asked for its Frame line.

**Approach:** Company Frame: Mason has its own skills and conda-forge-expert is one of them; `.claude/skills/pyforge-mason/` is A-only until the flip; A writes Dreams, Frames, Specs and the ledger until the flip; recipe craft uses conda-forge-expert. Each station Frame: two `- Seed: \`<path>\`` lines and one `- Derived: ` line. Per-station asks: atlas (`-e pyforge-atlas`, data root via `contract.md`, drop the cf-atlas-legacy sibling bullet); doctor (`python -m pyforge.doctor.sources <name>`, exit domain {0, 2, 130}, the kill switch as its one actuator); herald (Pages site and dossier under `docs-site/` are herald's; Lane 1 `/console/` is steward's); marshal and scribe (pointer only); mason (six skills, five of its own plus conda-forge-expert; B rebuilds the station skill under `skills/stations/`; package, environment and doctor verbs); steward (SPEC, `contract.md`, `oracle-map.md`, no duty list); warden (exit enum {0, 1, 2, 130}; CAP-24..26 behind flags that default off, listed in `contract.md`; import only the symbols `contract.md` names; fix-PR actuator and the fleet run as the A-only portal). README: `A Frame is a pointer, not a seed (operator ruling 2026-11-10)`, and `spec-intelligence-hub CAP-2` becomes `spec-pyforge-steward:CAP-53`. If the heads did not move, only the pin date changes and the memlog line says so.

Ledger key: `120-4-the-nine-frames-point-at-the-seed-and-agree-with-the-rulings`. Type / Effort / Deps: docs / M / —.

### Living CAP citations

- **`spec-pyforge-steward:CAP-53`** — a Frame is a pointer to the seed; **`spec-pyforge-steward:CAP-6`** — the frame-spec pin (memlog lines and render are Story 122.1's).

## Boundaries & Constraints

**Always:**
- The seed is Dream plus memlog; SPEC.md and `contract.md` are named on a `- Derived:` line, never as seed.
- If the new draft fails a Frame, fix the Frame or `conformance-profile.yaml` here.

**Never:**
- Never write anything upstream: `git ls-remote` is a read.
- Never edit `src/shared/packages/pyforge-steward/src/pyforge/steward/frames.py` here; never write a steward Spec file (Story 122.1 does).

## Acceptance Criteria

- **AC1 — in-repo preflight.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-steward frame-preflight
  ```
- **AC2 — upstream validator at the new pin (network).** Expected: exit 0 (exit 2 means it did not run; the story is not done).
  ```bash
  pixi run -e pyforge-steward frame-upstream-check
  ```
- **AC3 — the pin equals today's upstream heads.** Expected: exit 0.
  ```bash
  python3 -c "import re,subprocess;p=open('docs/foundry/frames/upstream-pin.yaml').read();s=re.findall(r'sha: ([0-9a-f]{40})',p);o=subprocess.run(['git','ls-remote','https://github.com/openteams-ai/frame-spec','refs/pull/28/head','refs/pull/29/head'],capture_output=True,text=True,check=True).stdout.split();h=[o[0],o[2]];print(s,h);raise SystemExit(0 if s==h else 1)"
  ```
- **AC4 — the two Mason contradictions are gone.** Expected: each file prints :0.
  ```bash
  grep -c 'never a mason skill tree\|Do not SKF-compile\|or `.claude/skills/pyforge-mason/`' docs/foundry/frames/pyforge.frame.md docs/foundry/frames/stations/mason.frame.md
  ```
- **AC5 — the generated indexes are current.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-steward pyforge steward catalog render && git diff --exit-code docs/foundry/frames/frame-index.yaml docs/foundry/frames/browse.yaml
  ```
- **AC6 — each station Frame has exactly two Seed lines, the Dream and the Spec memlog, and both exist.** Expected: prints `8 []`, exit 0.
  ```bash
  python3 -c "import re,glob,os;F=sorted(glob.glob('docs/foundry/frames/stations/*.frame.md'));bad=[];[bad.append((f,s)) for f in F for s in [re.findall(r'(?m)^- Seed: \x60([^\x60]+)\x60',open(f).read())] if len(s)!=2 or not s[0].startswith('docs/dreams/pyforge-') or not s[1].endswith('/.memlog.md') or any(('SPEC.md' in p or 'contract.md' in p or not os.path.exists(p)) for p in s)];print(len(F),bad);raise SystemExit(1 if bad or len(F)!=8 else 0)"
  ```
- **AC7 — derived files are named on a Derived line, never as seed (integration check; Story 58.4 re-runs it).** Expected: prints [] [], exit 0 once every station's contract.md exists.
  ```bash
  python3 -c "import re,glob,os;m=[(f,p) for f in glob.glob('docs/foundry/frames/stations/*.frame.md') for l in re.findall(r'(?m)^- Derived: (.*)$',open(f).read()) for p in re.findall(r'\x60([^\x60]+)\x60',l) if not os.path.exists(p)];c=[f for f in glob.glob('docs/foundry/frames/stations/*.frame.md') if len(re.findall(r'(?m)^- Derived: ',open(f).read()))!=1];print(m,c);raise SystemExit(1 if m or c else 0)"
  ```

</intent-contract>

## Binding

Parent: `spec-pyforge-steward:CAP-53`, `spec-pyforge-steward:CAP-6`

- Dream: `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the mint entry) and `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth*.
- Epic: Epic 120.
- Ledger key: `120-4-the-nine-frames-point-at-the-seed-and-agree-with-the-rulings` (`backlog` at mint).
- Deps: —.
- Surface: `docs/foundry/frames/pyforge.frame.md`, `docs/foundry/frames/stations/*.frame.md`, `docs/foundry/frames/README.md`, `docs/foundry/frames/upstream-pin.yaml`, `docs/foundry/frames/conformance-profile.yaml`, `docs/foundry/frames/frame-index.yaml`, `docs/foundry/frames/browse.yaml`.
- Minted 2026-11-10 by the cutover-readiness mint (control-plane unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward frame-preflight` — expected: exit 0.

## Notes

- Cross-station: doctor:S-58.4 re-runs the Derived-path check after every station's `contract.md` lands.
