---
title: '121.3: The capability ledger takes the rulings: archived rows leave, modes and expiries are decided'
type: 'chore'
created: '2026-11-10'
status: 'backlog'
difficulty: heavy
story: 121.3
spec: foundry-capability-ledger
surface:
  - docs/foundry/capability-ledger.yaml
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/remode-2026-11-10.md
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/modes.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/extract.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Rulings 3 and 4, the addendum and the second addendum, applied to the data now, parallel-safe and before the generator: 162 rows on archived Specs leave, the 87 rows dated 2026-12-31 are decided by group, ruled retirements are set, every rebuild row gets a state, and the header goes to v1. A mechanical bulk edit of one planning file plus its record.

**Approach:** Steps, each change recorded `| id | was | is | rule |` with every exception named. Ids below are ledger ids (`<slug>:CAP-n`, the Spec folder without `spec-`, as `extract.md` writes them), one per id; a range 'X:CAP-a to X:CAP-b' means every id between them, both included. (a) Remove all 162 rows on the 42 archived Specs (pgs:CAP-1 to pgs:CAP-5 included, the archived twins of spec-pyforge-herald:CAP-43 to spec-pyforge-herald:CAP-47), listed under `## Removed` by Spec. (b) Header to v1 (`modes.md` § Schema v1), `cells:` added (conda-forge-expert skill, scripts, mcp-server, data: A-only "mason:39.2"), `never_move` and `story_44_1` dropped. (c) Rename the 20 Unifying rows pap:CAP-1 to pap:CAP-20 to pyforge-unifying-strategy:CAP-1 to pyforge-unifying-strategy:CAP-20 (the record carries the map) and add pap:CAP-1 to pap:CAP-6 (A-only "steward:121.5", note `same text as pyforge-steward:CAP-98..103 (Story 48.8 merge)`, a literal note value). (d) Rule 3, A-only "steward:121.5": pyforge-unifying-strategy:CAP-1 to pyforge-unifying-strategy:CAP-4, pyforge-unifying-strategy:CAP-6 to pyforge-unifying-strategy:CAP-12, pyforge-unifying-strategy:CAP-14, pyforge-unifying-strategy:CAP-17, pyforge-unifying-strategy:CAP-19, pyforge-unifying-strategy:CAP-20; pyforge-steward:CAP-57 to pyforge-steward:CAP-75, pyforge-steward:CAP-78 to pyforge-steward:CAP-103, pyforge-steward:CAP-109 to pyforge-steward:CAP-116, pyforge-steward:CAP-127 to pyforge-steward:CAP-131, pyforge-steward:CAP-174, pyforge-steward:CAP-176 to pyforge-steward:CAP-178 (read each title; a kernel capability stays rebuild and is named); pyforge-atlas:CAP-58 to pyforge-atlas:CAP-60; pyforge-warden:CAP-16, pyforge-warden:CAP-17, pyforge-warden:CAP-19 to pyforge-warden:CAP-22. (e) Rule 6, A-only "mason:39.2": pyforge-mason:CAP-19, pyforge-mason:CAP-21 to pyforge-mason:CAP-26, pyforge-mason:CAP-32 to pyforge-mason:CAP-34; pyforge-atlas:CAP-7. pyforge-mason:CAP-18 is A-only "steward:44.8" and pyforge-mason:CAP-20 A-only "flip". (f) Rule 8, expiry "flip": fnd:CAP-12 to fnd:CAP-15, pyforge-mason:CAP-29. (g) Retire (rules 1, 2 and 7): pyforge-atlas:CAP-18 to pyforge-atlas:CAP-31 and pyforge-mason:CAP-8 to pyforge-mason:CAP-13 (never built); pyforge-atlas:CAP-44 to pyforge-atlas:CAP-47 (the views runtime was retired 2026-09-09 and atlas Story 48.3 deletes it again); pyforge-mason:CAP-14 to pyforge-mason:CAP-17, pyforge-mason:CAP-31, pyforge-mason:CAP-35; pyforge-herald:CAP-6, pyforge-herald:CAP-45, pyforge-herald:CAP-49; pyforge-marshal:CAP-82, pyforge-marshal:CAP-93 to pyforge-marshal:CAP-96; pyforge-scribe:CAP-34; pyforge-steward:CAP-2. (g1) Retire as closed one-time campaigns (rule 2; the second addendum's ruling 4): pyforge-doctor:CAP-37 to pyforge-doctor:CAP-41, pyforge-doctor:CAP-45 to pyforge-doctor:CAP-47, pyforge-doctor:CAP-49, pyforge-doctor:CAP-51, pyforge-doctor:CAP-52, pyforge-doctor:CAP-55, pyforge-doctor:CAP-56, pyforge-doctor:CAP-60, pyforge-doctor:CAP-61, pyforge-doctor:CAP-65 to pyforge-doctor:CAP-68, pyforge-doctor:CAP-70. (g2) Retire, each for the reason doctor Story 57.1 writes into its intent, never as a campaign (the rule column names that reason): pyforge-doctor:CAP-33 (split out to spec-pyforge-doctor:CAP-10 on 2026-08-21; marker `(retired 2026-08-21)`), pyforge-doctor:CAP-50 (rule 1: `docs/specs/` deleted by 070f73edad; `(retired 2026-10-10)`) and pyforge-doctor:CAP-53 (rule 1: `docs/dashboard/kedro-viz/` deleted by 87e8e58c3a; `(retired 2026-10-15)`). (h) The second addendum's ruling 4: pyforge-testing-charter:CAP-4 rebuild; pyforge-testing-charter:CAP-1, pyforge-testing-charter:CAP-2 and pyforge-testing-charter:CAP-5 A-only "steward:44.14" (the rebuild harness and oracle gate, an existing blocked Story this PR already amends, where B first needs the test signal); pyforge-warden:CAP-13 to pyforge-warden:CAP-15 A-only "steward:44.8"; pyforge-warden:CAP-26 rebuild (its kernel half; the portal half is pyforge-warden:CAP-29, whose A-only "steward:121.5" row exists since the mint and is kept); pyforge-atlas:CAP-68 B-only (atlas Story 36.3, blocked, carries it). (i) Rebuild: pyforge-testing-charter:CAP-3, pyforge-warden:CAP-18; pyforge-steward:CAP-7, pyforge-steward:CAP-8, pyforge-steward:CAP-21 to pyforge-steward:CAP-26, pyforge-steward:CAP-40, pyforge-steward:CAP-42, pyforge-steward:CAP-43; pyforge-steward:CAP-41 A-only "steward:44.8". (j) Every rebuild row gets `state: planned`. (k) Every remaining expiry becomes a qualified quoted string (`44.8` -> "steward:44.8").

Ledger key: `121-3-the-capability-ledger-takes-the-rulings-archived-rows-leave-modes-and-expiries-are-decided`. Type / Effort / Deps: chore / L / S-120.2.

### Living CAP citations

- **`spec-foundry-capability-ledger`** — fcl:CAP-1 (schema v1 and the written rules) and fcl:CAP-2 (the refusals and the expiry clock), amended 2026-11-10 and re-derived at mint.

## Boundaries & Constraints

**Always:**
- Each unit marks its own Spec `(retired <date>: <reason>)`; Story 121.6's `retire-without-marker` holds them to it at Story 121.7.
- Row order is kept; Story 121.7's generator re-orders.
- Kernel rows keep `station: pyforge-marshal` (the BMAD project that holds the Spec folder, `extract.md`); the record's `## Station field` says so.

**Never:**
- Never write a `pending` row for a 2026-11-10 question: every one is ruled.
- Never claim `verified-in-foundry` (ruling 1).

## Acceptance Criteria

- **AC1 — header v1, no archived row, every expiry a quoted form, every rebuild row has a state, no row is pending.** Expected: prints the row count, 0 and [], exit 0.
  ```bash
  python3 -c "import yaml,re,sys;d=yaml.safe_load(open('docs/foundry/capability-ledger.yaml'));rows=d['capabilities'];h=set(d);assert d['schema']=='pyforge.capability-ledger/v1' and {'states','frozen_states','modes','cells'}<=h and not {'never_move','story_44_1'}&h;bad=[r['id'] for r in rows if r['path'].startswith('archive/') or r['mode'] not in d['modes'] or r['mode']=='pending' or ('expiry' in r and not (isinstance(r['expiry'],str) and re.fullmatch(r'[a-z-]+:\d+\.\d+|\d{4}-\d{2}-\d{2}|flip',r['expiry']))) or r.get('expiry') in ('2026-12-31','steward:44.5','steward:44.7') or (r['mode']=='rebuild' and r.get('state')!='planned')];print(len(rows),len(bad),bad[:5]);sys.exit(1 if bad else 0)"
  ```
- **AC2 — every changed mode or expiry is in the record with its rule.** Expected: prints a positive count and 0, exit 0.
  ```bash
  python3 -c "import subprocess,yaml,re;old={r['id']:r for r in yaml.safe_load(subprocess.run(['git','show','a2a97a1eef:docs/foundry/capability-ledger.yaml'],capture_output=True,text=True).stdout)['capabilities']};new={r['id']:r for r in yaml.safe_load(open('docs/foundry/capability-ledger.yaml'))['capabilities']};ren={'pap:CAP-%d'%n:'pyforge-unifying-strategy:CAP-%d'%n for n in range(1,21)};ch={ren.get(i,i) for i in old if ren.get(i,i) in new and (old[i]['mode'],str(old[i].get('expiry')))!=(new[ren.get(i,i)]['mode'],str(new[ren.get(i,i)].get('expiry')))};doc=set(re.findall(r'(?m)^\| ([a-z0-9-]+:CAP-\d+) \|',open('_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/remode-2026-11-10.md').read()));print(len(ch),len(ch-doc));raise SystemExit(0 if ch and not ch-doc else 1)"
  ```
- **AC3 — the 162 removed ids are listed by archived Spec.** Expected: prints 162 [], exit 0.
  ```bash
  python3 -c "import subprocess,yaml,re;old=[r for r in yaml.safe_load(subprocess.run(['git','show','a2a97a1eef:docs/foundry/capability-ledger.yaml'],capture_output=True,text=True).stdout)['capabilities'] if r['path'].startswith('archive/')];t=open('_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/remode-2026-11-10.md').read().split('## Removed',1)[1];m=[r['id'] for r in old if r['id'] not in t];print(len(old),m[:5]);raise SystemExit(0 if len(old)==162 and not m else 1)"
  ```
- **AC4 — the Unifying rows are renamed and the real pap rows exist.** Expected: exit 0.
  ```bash
  python3 -c "import yaml;ids={r['id'] for r in yaml.safe_load(open('docs/foundry/capability-ledger.yaml'))['capabilities']};a={'pap:CAP-%d'%n for n in range(1,7)};b={'pyforge-unifying-strategy:CAP-%d'%n for n in range(1,21)};c={'pap:CAP-%d'%n for n in range(7,21)};raise SystemExit(0 if a<=ids and b<=ids and not c&ids else 1)"
  ```
- **AC5 — never-built and station records are written, and pyforge-atlas:CAP-68 is B-only.** Expected: prints 1, 1, then `B-only`, exit 0.
  ```bash
  grep -c '^## Never built' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/remode-2026-11-10.md && grep -c '^## Station field' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/remode-2026-11-10.md && python3 -c "import yaml;r={x['id']:x for x in yaml.safe_load(open('docs/foundry/capability-ledger.yaml'))['capabilities']}['pyforge-atlas:CAP-68'];print(r['mode']);raise SystemExit(0 if r['mode']=='B-only' else 1)"
  ```
- **AC6 — the second addendum's disputed modes are applied.** Expected: prints [], exit 0.
  ```bash
  python3 -c "import yaml,sys;r={x['id']:x for x in yaml.safe_load(open('docs/foundry/capability-ledger.yaml'))['capabilities']};w={'pyforge-testing-charter:CAP-4':('rebuild',None),'pyforge-testing-charter:CAP-1':('A-only','steward:44.14'),'pyforge-testing-charter:CAP-2':('A-only','steward:44.14'),'pyforge-testing-charter:CAP-5':('A-only','steward:44.14'),'pyforge-warden:CAP-13':('A-only','steward:44.8'),'pyforge-warden:CAP-14':('A-only','steward:44.8'),'pyforge-warden:CAP-15':('A-only','steward:44.8'),'pyforge-atlas:CAP-7':('A-only','mason:39.2'),'pyforge-herald:CAP-6':('retire',None),'pyforge-scribe:CAP-34':('retire',None),'pyforge-doctor:CAP-37':('retire',None),'pyforge-doctor:CAP-51':('retire',None),'pyforge-doctor:CAP-70':('retire',None)};bad=[(k,r.get(k,{}).get('mode'),r.get(k,{}).get('expiry')) for k,(m,e) in w.items() if r.get(k,{}).get('mode')!=m or (e and r.get(k,{}).get('expiry')!=e)];print(bad);sys.exit(1 if bad else 0)"
  ```

</intent-contract>

## Binding

Parent: `spec-foundry-capability-ledger` fcl:CAP-1

- Dream: `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the mint entry) and `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth*.
- Epic: Epic 121.
- Ledger key: `121-3-the-capability-ledger-takes-the-rulings-archived-rows-leave-modes-and-expiries-are-decided` (`backlog` at mint).
- Deps: S-120.2.
- Surface: `docs/foundry/capability-ledger.yaml`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/remode-2026-11-10.md`.
- Minted 2026-11-10 by the cutover-readiness mint (control-plane unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-guild capability-ledger-check` — expected: exit 0.

## Notes

- Doctor's closed one-time campaigns retire by the second addendum's ruling 4; doctor Story 57.1 marks them `(retired 2026-11-10: closed one-time campaign)`. pyforge-doctor:CAP-33, pyforge-doctor:CAP-50 and pyforge-doctor:CAP-53 are not campaigns: doctor Story 57.1 retires them for their own reasons (its Notes group 6, its AC2), and step (g2) records those reasons.
- Steward's restore and revoke capability, `spec-pyforge-steward:CAP-180`, was minted at mint, and its row `pyforge-steward:CAP-180` (A-only "steward:121.5") was added to the ledger with the mint's renders; this story keeps it and records it. The same holds for `pyforge-warden:CAP-29`.
- The testing charter's anchor "steward:44.14" is recorded with its reason in the 2026-11-11 decision on the `spec-foundry-capability-ledger` memlog (the integrated plan named no anchor for those three rows; marshal:S-118.2 defers to this story).
- Cross-station: doctor:S-57.1, atlas:S-48.3, atlas:S-36.3, mason:S-39.2 and warden:S-25.1 carry the markers and anchors these modes rely on.
