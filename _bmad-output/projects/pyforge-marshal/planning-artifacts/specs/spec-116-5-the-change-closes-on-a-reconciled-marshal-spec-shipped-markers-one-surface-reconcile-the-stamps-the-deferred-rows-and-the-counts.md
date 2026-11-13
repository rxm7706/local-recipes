---
title: "116.5: The change closes on a reconciled marshal Spec: shipped markers, one surface reconcile, the stamps, the deferred rows and the counts"
type: 'chore'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: medium
story: '116.5'
spec: pyforge-marshal
surface:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/test-architecture.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/briefs/brief-pyforge-marshal-2026-07-25/brief.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/retros/retro-pyforge-marshal-2026-11-*.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/implementation-readiness-report-2026-1*.md
  - docs/dreams/pyforge-marshal.md
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/test-architecture.md
  - scripts/deferred_work_intake.py
  - scripts/spec_surface_check.py
warnings: []
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-117.1, S-117.2, S-117.3, S-117.4, S-117.6, S-117.7, S-117.8); it also waits on Stories 114.1 to 116.4, and on the cross-station closers its Notes name, which only the integration branch's wave order sequences.
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).
>
> **Unblocked 2026-11-13.** Every story its Deps name is `done` on branch `cutover-readiness-2026-11-10`. The operator's "Start build" consent covered the unblock; CLOSE-LEDGERS moved the key to `done`.

<intent-contract>

## Intent

**Problem:** Every planning file this unit shares has one owner at the end of the change. The Spec's surface (`src/shared/packages/pyforge-marshal/**`, `src/shared/packages/pyforge-core/`, `pixi.toml`, `environment.yaml`, `scripts/promote_sprint_status.py`, Doctor's `sources/marshal.py` and `sources/chain.py`, ...) moves under stories of several units, and the scoped stamp refuses a path the memlog does not name (`scripts/spec_surface_check.py:434-436`). spec-pyforge-marshal:CAP-304, spec-pyforge-marshal:CAP-305 and the seven capabilities this change amends with a fix (CAP-13, CAP-23, CAP-208, CAP-227, CAP-229, CAP-261, CAP-287) must not land at ready with their stories done (operator ruling of 2026-11-10: markers of capabilities this change builds flip to shipped inside the PR).

**Approach:** Runs last on the integration branch, after every story of any unit whose diff touches spec-pyforge-marshal's surface (core-kit 117.x and 118.x, steward 124.x, doctor 56.3 and 58.1, scribe's catalog files, and this unit's); the integrator orders it. From a clean tree: (1) one memlog `change` entry flipping spec-pyforge-marshal:CAP-304, spec-pyforge-marshal:CAP-305 and those of the seven amended capabilities (CAP-13, CAP-23, CAP-208, CAP-227, CAP-229, CAP-261, CAP-287; memlog 2026-11-10, Marker of an amended capability, and its addendum) that still read ready to `(shipped <date>)` (Story 114.1's render already shipped any whose fix stories were all done), each dated the day the last of its stories reached done, then the anchored render with both self-validate passes logged. (2) One `event` `Surface reconcile <date>: <paths>` naming every path from `git diff --name-only origin/main...HEAD` that matches the Spec's `surface:` and not its `surface-drift-exclude:` (other units' paths included: they append nothing to this memlog). (3) Deferred work: close DW-FU-53-2-2 (moot by design, superseded by Story 115.2); close DW-FU-4-4-2 for the constant (Story 115.4) and add DW-marshal-115-4-3 for the remote check; add every deferred row of the change whose unit is marshal or core-kit and DW-marshal-cutover-2026-11-10-1; run `python scripts/deferred_work_intake.py --fix --project pyforge-marshal` for the `deferred:` entries of this unit's story specs (Story 115.1's run-state debt). (4) `epics.md` `epicCount`/`storyCount` from the headings. (5) `python _bmad/scripts/bmad_tea_playwright.py --project pyforge-marshal`. (6) The retro through `bmad-retrospective` over this station's Epics of the change; the brief, PRD and spine take `updated:` and one dated Currency reconciliation line each; the Dream's Realization log records the close, covering both 2026-11-10 sections (marshal's and core-kit's).

Ledger key: `116-5-the-change-closes-on-a-reconciled-marshal-spec-shipped-markers-one-surface-reconcile-the-stamps-the-deferred-rows-and-the-counts`. Type / Effort / Deps: chore / M / S-114.1, S-114.2, S-114.3, S-115.1, S-115.2, S-115.3, S-115.4, S-116.1, S-116.2, S-116.3, S-116.4, S-117.1, S-117.2, S-117.3, S-117.4, S-117.6, S-117.7, S-117.8 (same-station keys, as in `epics.md`; the cross-station dependencies are in Notes).

## Boundaries & Constraints

**Always:**
- Writes the Surface reconcile events of the Specs it closes and nothing in `scripts/.spec-surface-baseline.json`; doctor:S-58.4 runs every scoped stamp once, after the last edit on the branch.
- The chain closes with `chain-completeness`, `story-status`, `status-body-consistency`, `fr-without-cap`, `ad-citation` and `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight`.

**Never:**
- Never run a bare `--write-baseline`.
- Never write DW-marshal-117-8-1: the operator ruled that the markers flip inside the PR, so no post-merge flip row exists.
- Never hand-edit `SPEC.md` or the ledger.

## Acceptance Criteria

- **AC1 — No capability reads ready unless a story citing it is open; spec-pyforge-marshal:CAP-304, spec-pyforge-marshal:CAP-305 and the seven amended capabilities read shipped.**

  ```bash
  python3 -c "import re,sys,yaml;t=open('_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md').read();r={m.group(1) for m in re.finditer(r'^- \*\*(CAP-\d+) — .*\(ready \d{4}-\d{2}-\d{2}[;)]',t,re.M)};tab={l.split('|')[1].strip():l.split('|')[3] for l in open('_bmad-output/projects/pyforge-marshal/planning-artifacts/research/cap-marker-truth-2026-11-10.md') if l.startswith('| CAP-')};st={'.'.join(k.split('-')[:2]):v for k,v in yaml.safe_load(open('_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml'))['development_status'].items() if re.match(r'^\d+-\d+-',k)};bad=[c for c in sorted(r) if not any(st.get(k,'done')!='done' for k in re.findall(r'\b\d+\.\d+\b',tab.get(c,'')))];print(bad);sys.exit(1 if bad else 0)"
  ```

  Expected: exit 0; prints `[]`.

  ```bash
  python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md').read();n=[c for c in (13,23,208,227,229,261,287,304,305) if not re.search(r'^- \*\*CAP-%d — .*\(shipped \d{4}-\d{2}-\d{2}[;)]'%c,t,re.M)];print(n);sys.exit(1 if n else 0)"
  ```

  Expected: exit 0; prints `[]`.

- **AC2 — The reconcile event names every changed path on the Spec's surface.**

  ```bash
  python3 -c "import yaml,fnmatch,subprocess,sys;fm=yaml.safe_load(open('_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md').read().split('---')[1]);inc=fm['surface'];exc=fm.get('surface-drift-exclude') or [];m=lambda p,gs:any(fnmatch.fnmatch(p,g) or (g.endswith('/') and p.startswith(g)) or (g.endswith('/**') and p.startswith(g[:-2])) for g in gs);ch=[p for p in subprocess.run(['git','diff','--name-only','origin/main...HEAD'],capture_output=True,text=True).stdout.split() if m(p,inc) and not m(p,exc)];ml=open('_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md').read();miss=[p for p in ch if p not in ml];print(len(ch),miss);sys.exit(1 if miss else 0)"
  ```

  Expected: exit 0; prints a count and `[]`.

- **AC3 — The deferred rows: DW-FU-53-2-2 closed moot by design, DW-FU-4-4-2 closed for the constant with a narrowed remote-check row, the change's rows and every story spec `deferred:` entry ingested.**

  ```bash
  pixi run --frozen -e pyforge-guild python scripts/deferred_work_intake.py --fix --project marshal && grep -A14 '^### DW-FU-53-2-2' _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md | grep -c 'status: closed' && grep -A14 '^### DW-FU-4-4-2' _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md | grep -c 'status: closed' && grep -c '^### DW-marshal-11[4-8]-' _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md && grep -c '^### DW-marshal-cutover-2026-11-10-1\b' _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md && pixi run -e pyforge-guild deferred-work-check
  ```

  Expected: the counts print 1, 1, 17 or more (marshal 9, core-kit 8) and 1, then exit 0.

- **AC4 — epics.md frontmatter counts equal the headings, after both units' mints.**

  ```bash
  python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md').read();e=len(re.findall(r'^## Epic \d+',t,re.M));s=len(re.findall(r'^### Story \d+\.\d+',t,re.M));fe=int(re.search(r'^epicCount: (\d+)',t,re.M).group(1));fs=int(re.search(r'^storyCount: (\d+)',t,re.M).group(1));print(e,fe,s,fs);sys.exit(0 if (e,s)==(fe,fs) else 1)"
  ```

  Expected: exit 0.

- **AC5 — The test architecture names every story.**

  ```bash
  pixi run --frozen -e pyforge-guild python _bmad/scripts/bmad_tea_playwright.py --project pyforge-marshal && pixi run -e pyforge-guild tea-playwright-check
  ```

  Expected: exit 0.

- **AC6 — Marshal's planning detectors (the PR bar is doctor:S-58.4's).**

  ```bash
  pixi run -e pyforge-guild chain-completeness-check && pixi run -e pyforge-guild story-status-check && pixi run -e pyforge-guild status-body-consistency-check && pixi run -e pyforge-guild fr-without-cap-check && pixi run -e pyforge-guild ad-citation-check
  ```

  Expected: exit 0.

- **AC7 — Post-condition for doctor:S-58.4, not this story's close gate: no unreconciled drift row names pyforge-marshal/spec-pyforge-marshal at the branch head once doctor:S-58.4 has stamped.**

  ```bash
  pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources spec-surface --json > "$TMPDIR/ss.json"; python3 -c "import json,sys;d=json.load(open(sys.argv[1]));rows=d if isinstance(d,list) else (d.get('findings') or d.get('rows') or []);n=[r for r in rows if r.get('check') in ('drift','drift-presumed') and sys.argv[2] in json.dumps(r)];print(len(n));sys.exit(1 if n else 0)" "$TMPDIR/ss.json" pyforge-marshal/spec-pyforge-marshal
  ```

  Expected: doctor:S-58.4 reads it after its stamps: prints 0, exit 0. It is not read at this story's close, because 58.4 runs after it; this story's close gate for the surface is AC2.

- **AC8 — The marshal retro is dated on or after the last package-manifest commit.**

  ```bash
  python3 -c "import glob,re,subprocess,sys;f=sorted(glob.glob('_bmad-output/projects/pyforge-marshal/planning-artifacts/retros/retro-pyforge-marshal-2026-1*.md'));d=re.search(r'\d{4}-\d{2}-\d{2}',f[-1]).group(0) if f else '';c=subprocess.run(['git','log','-1','--format=%cs','--','src/shared/packages/pyforge-marshal/pyproject.toml'],capture_output=True,text=True).stdout.strip();print(d,c);sys.exit(0 if d and d>=c else 1)"
  ```

  Expected: prints two dates, the retro's not earlier; exit 0.

- **AC9 — The station Dream records the close.**

  ```bash
  grep -c 'cutover readiness, closed' docs/dreams/pyforge-marshal.md
  ```

  Expected: prints 1 or more.

- **AC10 — Marshal's chain is current: no feeds finding and no shelf finding, read from the exit code.**

  ```bash
  pixi run --frozen -e pyforge-guild chain-currency-sweep-check -- --project pyforge-marshal
  ```

  Expected: exit 0 (1 is a finding, 2 could not run; never through a pipe).

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` (flips spec-pyforge-marshal:CAP-304, spec-pyforge-marshal:CAP-305 and the seven amended capabilities to shipped; reconciles the surface).

- Epic: Epic 116 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 116.5: The change closes on a reconciled marshal Spec: shipped markers, one surface reconcile, the stamps, the deferred rows and the counts`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The Spec says what marshal is, and its roots come from one place.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda.

## Notes

- Cross-station dependencies: scribe:S-31.4, doctor:S-56.4, doctor:S-58.1, steward:S-121.7, steward:S-124.1, steward:S-124.3, steward:S-124.4. They are not in the `epics.md` Deps line, because marshal's Deps parser drops a station prefix and would read each as a marshal key; only the integration branch's wave order (plan.json) holds them. doctor:S-58.4 runs after this story and stamps every Spec once (`--spec pyforge-marshal/spec-pyforge-marshal`, `--spec pyforge-marshal/spec-pyforge-core` and the rest, one each) and prunes the baseline (`--prune`).
- Same-project dependencies: Stories 114.1 to 116.4 and core-kit's 117.1, 117.2, 117.3, 117.4, 117.6, 117.7 and 117.8.
- Deferred rows it writes (marshal): DW-marshal-114-1-1, DW-marshal-114-1-2, DW-marshal-114-2-1, DW-marshal-114-2-2, DW-marshal-114-3-1, DW-marshal-115-1-1, DW-marshal-115-4-1, DW-marshal-115-4-2, DW-marshal-115-4-3, DW-marshal-cutover-2026-11-10-1; core-kit's DW-marshal-117-*/118-* rows as that unit's plan states them.

## Spec Change Log

- 2026-11-10: minted at `blocked` (forward dependency: until every story its Deps name is done) by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10) and the memlog entries of `spec-pyforge-marshal` came first; `SPEC.md` is rendered by Story 114.1.
- 2026-11-11: fix pass after the third review of the mint. The cross-station keys left the Deps line here and in `epics.md` (marshal's Deps parser read them as marshal keys); they stay in Notes, held only by the integration branch's wave order.

## Review findings (build, round 1, 2026-11-11)

An independent reviewer failed the first build attempt with one major and two minor findings. Each is listed with its severity, where it was found, the problem and the disposition.

1. **major** — § Acceptance Criteria, AC3 (and plan.json `stories[116.5].acceptance[3]`). **Problem:** the AC as written cannot pass. `python scripts/deferred_work_intake.py --fix --project pyforge-marshal` exits 2 at argument validation (`unknown project(s): pyforge-marshal; known: atlas, doctor, herald, marshal, ...`), because the script keys projects by the short name, and bare `python` is not on `PATH` outside pixi. The first attempt ran a working form but left the AC text unchanged. **Fixed under the oracle rule** (the reviewer named the fault as the oracle's and gave the corrected form):
   - AC3, old: `python scripts/deferred_work_intake.py --fix --project pyforge-marshal && …`; new: `pixi run --frozen -e pyforge-guild python scripts/deferred_work_intake.py --fix --project marshal && …`. The rest of the command (the four greps and `deferred-work-check`) is unchanged.
   - AC5, the same prefix, old: `python _bmad/scripts/bmad_tea_playwright.py --project pyforge-marshal && …`; new: `pixi run --frozen -e pyforge-guild python _bmad/scripts/bmad_tea_playwright.py --project pyforge-marshal && …`. The generator takes the long slug, so only the interpreter changes.
   - Why this is not a weakened oracle: the old AC3 exits before it checks anything. The new one runs the same intake over the same project's ledger, then every grep and the detector after it, so it checks strictly more. No assertion is dropped, no count is loosened and no skip is added. plan.json `acceptance[3]` and `acceptance[5]` carry the same two commands.
   - The Approach's step (3) prose keeps the command as minted. The Intent is not an oracle, and the AC is the command of record. Letting the script accept the long slug is repo tooling for a Story under the Spec that owns the script (the retro's action item 4), not this story's file.
2. **minor** — bare ids in text this story wrote: the PRD's § Currency reconciliation — 2026-11-13 (Story 116.5), the Dream's closing line, the retro's findings, and the deferred-work ledger's `DW-marshal-114-3-2` (`marshal's AD-31`). **Fixed:**
   - the PRD line, the Dream line and retro findings 1 and 5 cite `spec-pyforge-marshal:CAP-n`;
   - `DW-marshal-114-3-2` cites `pyforge-marshal:AD-31`. Marshal's spine defines AD-31 bare and has no colon namespace of its own, so this follows the station-qualified form the fleet uses for a spine's own ids (`pyforge-atlas:AD-13`, atlas Story 37.13 and steward Story 124.5);
   - `DW-marshal-118-2-1` cites `spec-coverage-gate-independence:CAP-2`;
   - retro finding 11 records this oracle correction.
   - Left as written: `DW-marshal-114-2-3` and retro finding 5 quote `test_spec_names_live_paths.py` verbatim ('open while CAP-305 reads ready'). The `Prior` text inside each frontmatter `updated:` comment was written by earlier stories. Memlog entries are append-only.
3. **minor** — `DW-marshal-116-4-1`; Story 116.4 § Planned deferral (the off-tree start `_package_half_off_the_tree` is unnamed in `spec-pyforge-marshal:CAP-305`'s guard clause). **No change**, as the reviewer finds. This story's Intent names marker flips only. Whether this PR carries the `spec-pyforge-marshal:CAP-305` amendment (a memlog change entry plus an anchored render) or leaves the open row to marshal's next Spec story is the integrator's decision. The retro records it as its open question and action item 1.
