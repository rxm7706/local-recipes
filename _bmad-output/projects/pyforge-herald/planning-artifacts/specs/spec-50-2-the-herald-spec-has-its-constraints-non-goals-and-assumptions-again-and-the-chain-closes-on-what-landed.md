---
title: "50.2: The herald Spec has its Constraints, Non-goals and Assumptions again, and the chain closes on what landed"
type: 'chore'
created: '2026-11-10'
status: 'blocked'
difficulty: medium
story: '50.2'
spec: pyforge-herald
surface:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/artifact-tracking-matrix.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/workflow-stages.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/six-act-framework.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/station-roster.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/bridge-protocol.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/epic-structure.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/facts-ledger.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/prds/prd-pyforge-herald-2026-08-01/prd.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/architecture/architecture-pyforge-herald-2026-08-01/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/briefs/brief-pyforge-herald-2026-08-01/brief.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-50-2-the-herald-spec-has-its-constraints-non-goals-and-assumptions-again-and-the-chain-closes-on-what-landed.md   # its own `deferred:` entry
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-50-3-herald-s-public-contract-is-one-companion-and-a-meta-test-holds-the-code-to-it.md   # `deferred:` entry only
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-50-4-herald-s-source-comments-and-docstrings-cite-the-folded-spec-s-capability-ids.md   # `deferred:` entry only, if Story 50.4 listed one
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-52-1-herald-s-live-tree-readers-carry-the-live-tree-marker.md   # `deferred:` entry only
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-52-2-herald-s-landing-record-names-this-checkout-s-forge-and-its-package-names-python-3-14.md   # `deferred:` entry only
  - docs/dreams/pyforge-herald.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/retros/retro-pyforge-herald-2026-11-*.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/implementation-readiness-report-2026-11-*.md
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
  - docs/dreams/pyforge-herald.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - docs-site/scripts/verify_claims.py
  - scripts/deck_facts.py
warnings: [oversized]
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-51.1, S-51.2, S-52.1, S-52.2).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** On 2026-11-10 herald's Spec has no Constraints, Non-goals or Assumptions section. The 2026-09-17 fold
dropped them, though the memlog holds 11 constraint, 4 non-goal and 7 assumption entries (counting the two
`(constraint by claude)` and two `(assumption by claude)` entries, as AC2 does), and CAP-30 still cites them.
Its Why quotes `cli.py` at 1,764 lines and 26 subparsers (1,943 and 30 on 2026-11-10). Its six 2026-08-02 companions
do not say whether they are a record or live. `facts-ledger.md:50` names `-e local-recipes`. Its frontmatter omits
`scripts/deck_export.py` from `surface:` and `contract.md` from `companions:` (audit MUST 3; NICE: Why, companions,
facts-ledger). CHAIN-STANDARD § 3 step 7 needs one last writer: once the code stories are done, CAP-46 and CAP-62
read shipped, and the PRD, spine, brief, epics and Dream carry the landing.

**Approach:** Runs last in herald's unit, after every code story, in one session: memlog entries first, then one
anchored script re-derive of `SPEC.md` (both self-validate passes logged), then the cascade. No code changes. It is
the second and last build-time writer of the Spec.

- **(a) Three sections.** Constraints, Non-goals and Assumptions are re-derived from the memlog entries of those
  types. An entry that no longer holds is retired by a memlog line beginning `(change) retires <type>: …` and is not
  rendered. New Assumptions take one memlog entry each:
  - the Spec-named oracle tests of CAP-47 and CAP-58..CAP-61 run only in `pyforge-herald-test-built` (node and
    docs-site's npm install);
  - the dossier block goldens cannot be regenerated, because the Jinja generator that produced them is gone, so they
    change only by review in the PR that changes the renderer (CAP-61's success already names the frozen file);
  - `scripts/export_notices_snapshot.py` is wired to no task, and `web/` is built by no workflow;
  - `docs-site/src/lib/marketplace.ts` realizes `spec-pyforge-steward:CAP-171` inside herald's surface.
- **(b) Frontmatter.** `surface:` gains `scripts/deck_export.py`, and `companions:` gains `contract.md` (Story 50.3
  wrote it).
- **(c) Why.** It is re-grounded with measured, dated figures: `cli.py` lines and parsers on the day, and stories and
  epics as the ledger reads that day.
- **(d) Companions.** Each 2026-08-02 companion gets one `> **Standing:**` line (record of 2026-08-02, or live and
  re-checked), with no body rewrite. In `facts-ledger.md` only line 50 changes, and line 40 gets a note.
- **(e) Markers.** CAP-62 flips to `(shipped <date Story 50.3 landed>)`. CAP-46 flips to `(shipped <date Story 51.1
  landed>; amended 2026-11-10: Story 51.1)`. Either text is corrected by a memlog `change` entry if it disagrees with
  what Stories 50.3, 51.1 and 52.2 built.
- **(f) Reconcile.** One `(event) Surface reconcile <date>: <full path> …` memlog line per story, for every governed
  path Stories 50.3, 50.4, 51.1, 51.2, 52.1 and 52.2 moved, each path literal. The same event names every tracked path
  that the widened `surface:` newly governs and that this PR did not change (`scripts/deck_export.py`); otherwise those
  paths read `drift-presumed`. Doctor:S-58.4 runs the scoped stamp once, after the last edit.
- **(g) Cascade.** `updated:` and one dated line on the PRD, the spine (no AD: the how did not change), the brief and
  `epics.md`. The PRD's FR text is the mint's and is only verified here.
- **(h) Ledger.** This story does not write it. The CLOSE-LEDGERS job promotes every story of this change to `done`
  (Tier-3 feed, then `sprint-ledger-sync -- --project herald`, then `story-status-check`).
- **(i) Deferred-work ledger.** It writes, with their ids verbatim, the rows the other stories' Planned deferral
  sections name, each with that story spec's `deferred:` entry in the same change:
  `DW-herald-50-3-2`, `DW-herald-52-1-1` and `DW-herald-52-2-1`. If Story 50.4 listed a citation the remint map could
  not place, it writes that row too, as `DW-herald-50-4-1`, with spec-50-4's `deferred:` entry. It also writes its own
  `DW-herald-50-2-1` (with this spec's `deferred:` entry) and the two
  integration rows `DW-herald-cutover-2026-11-10-1` (the warden deck's dead path) and `DW-herald-cutover-2026-11-10-2`
  (mason's `facts.yaml`). Story 50.1 already wrote `DW-herald-50-1-3`. The plan's `DW-herald-50-3-1` is not minted,
  because Story 50.4 carries its work.
- **(j) Dream.** One dated line after the 2026-11-10 entry, headed `- **<landing date> (cutover readiness, landed) —
  …**` in the file's entry form. It names the eight stories as landed, and what stays not met (`DW-FU-23-6-1`,
  `DW-steward-43-6-1`) or open to the operator (`DW-herald-egm-2026-11-01-1`).
- **(k) Retro and readiness.** One `bmad-retrospective` over Epics 50, 51 and 52 (`retros/retro-pyforge-herald-2026-11-*.md`)
  and one fresh readiness report (`implementation-readiness-report-2026-11-*.md`).

Ledger key: `50-2-the-herald-spec-has-its-constraints-non-goals-and-assumptions-again-and-the-chain-closes-on-what-landed`.
Type / Effort / Deps: chore / M / S-50.1, S-50.3, S-50.4, S-51.1, S-51.2, S-52.1, S-52.2 (and steward:S-121.7).

## Boundaries & Constraints

**Always:**
- Memlog first, then one anchored script render with both self-validate passes logged. Re-stamp the PRD, spine, brief
  and epics in the same change.
- Name every reconciled path literally (a scoped stamp matches literal paths).
- Read every verdict from the exit code.

**Never:**
- Never hand-edit `SPEC.md`, never run `spec_surface_check.py --write-baseline` (doctor:S-58.4 stamps once), and never
  append a reconcile line to another Spec's memlog.
- Never write `sprint-status-ledger.yaml` or the Tier-3 feed.
- Never rewrite a companion's body, and never move a CAP id.

## Acceptance Criteria

Each verdict is read from the exit code, never through a pipe.

- **AC1 — The three sections exist.**
  `grep -cE '^## (Constraints|Non-goals|Assumptions)$' _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md`.
  Expected: prints `3`.
- **AC2 — Every live memlog entry is rendered.** Each section carries bullets, and every memlog constraint, non-goal
  and assumption is rendered or retired by a dated change entry. Expected: exit 0, printing `[]`.

```bash
python3 - <<'EOF'
import re,sys
t=open('_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md').read(); m=open('_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md').read()
bad=[]
for h,k in (('Constraints','constraint'),('Non-goals','non-goal'),('Assumptions','assumption')):
    s=re.search(r'^## %s\n(.*?)(?=^## )'%h,t,re.M|re.S)
    n=len(re.findall(r'^- ',s.group(1),re.M)) if s else 0
    live=len(re.findall(r'^- \(%s(?: by \w+)?\)'%k,m,re.M))-len(re.findall(r'^- \(change(?: by \w+)?\) retires %s'%k,m,re.M))
    if n<1 or n<live: bad.append((h,n,live))
print(bad); sys.exit(1 if bad else 0)
EOF
```

- **AC3 — Why is measured and dated.**
  `git grep -nF -e '1764 lines' -e '26 subparsers' -e 'spec-herald-moments-2-4-live-backend`, `in-progress`' -- _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md`.
  Expected: exit 1 (no match).
- **AC4 — The audit's unnamed items are named.** Run `grep -c` on `SPEC.md` for each of `scripts/deck_export.py`,
  `  - contract.md`, `export_notices_snapshot.py`, `pyforge-herald-test-built`, `marketplace.ts` and
  `cannot be regenerated`. Expected: six counts, each at least 1.
- **AC5 — Each 2026-08-02 companion is dated.**
  `grep -L '^> \*\*Standing:\*\*'` over `artifact-tracking-matrix.md`, `workflow-stages.md`, `six-act-framework.md`,
  `station-roster.md`, `bridge-protocol.md` and `epic-structure.md` in the Spec folder. Expected: prints nothing.
- **AC6 — The facts-ledger names the Guild env.** It names the Guild env for the run command and keeps the literal the
  script writes:
  `git grep -n 'e local-recipes deck-facts' -- …/facts-ledger.md; grep -c 'DW-herald-50-2-1' …/facts-ledger.md; grep -c 'e local-recipes bmad-groundtruth' …/facts-ledger.md`.
  Expected: the first prints nothing (exit 1), then `1` and `1`.
- **AC7 — Nothing reads ready.** Every story of this unit is done, and its capability says shipped. Expected: exit 0,
  printing `62 [] []`.

```bash
python3 - <<'EOF'
import re,sys
t=open('_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md').read()
L=re.findall(r'^- \*\*CAP-\d+ — .*$',t,re.M)
bad=[l[:30] for l in L if '(in-progress' in l or not re.search(r'\((shipped|ready|retired) \d{4}-\d{2}-\d{2}[;:)]',l)]
ready=sorted(re.findall(r'^- \*\*(CAP-\d+) — .*\(ready 20',t,re.M))
print(len(L),bad,ready); sys.exit(0 if len(L)==62 and not bad and ready==[] else 1)
EOF
```

- **AC8 — CAP-46 names only keys the measurer has.** Expected: exit 0, listing eight keys, and the second list is
  `[]`.

```bash
python3 - <<'EOF'
import re,sys
t=open('_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md').read(); v=open('docs-site/scripts/verify_claims.py').read()
b=re.search(r'^- \*\*CAP-46 — .*?(?=^- \*\*CAP-|^## )',t,re.M|re.S).group(0)
keys=[k for k in re.findall(r'`([a-z_]+)`',b) if k.endswith(('_lines','_epics','_floor')) or k=='stations']
bad=[k for k in keys if '"%s"'%k not in v and "'%s'"%k not in v]
print(sorted(set(keys)),bad); sys.exit(1 if bad or len(set(keys))<8 else 0)
EOF
```

- **AC9 — Every moved governed path has a reconcile line.** Each one names its full path. Expected: exit 0, printing
  the count of moved paths and `[]`.

```bash
python3 - <<'EOF'
import subprocess,sys
m=[l for l in open('_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md').read().split('\n') if l.startswith('- (event') and 'Surface reconcile 2026-11-' in l]
paths=[p for p in subprocess.check_output('git diff --name-only origin/main...HEAD -- src/shared/packages/pyforge-herald docs-site presentations scripts/deck_facts.py scripts/deck_trio.py docs/index.md docs/404.md .gitignore'.split(),text=True).split('\n') if p]
bad=[p for p in paths if not any(p in l for l in m)]
print(len(paths),bad); sys.exit(1 if bad or not paths else 0)
EOF
```

- **AC10 — Every deferral of this unit has its row.**
  `grep -c '^### DW-herald-\(50-1-3\|50-2-1\|50-3-2\|52-1-1\|52-2-1\):' _bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md && pixi run -e pyforge-guild deferred-work-check`.
  Expected: prints `5`, then exit 0.
- **AC11 — The mint's requirement arrows stand.**
  `grep -c '^\*\*FR-14\.1: .*← CAP-62' …/prd.md; grep -c '^\*\*FR-12\.5: .*← CAP-61, CAP-46' …/prd.md; pixi run -e pyforge-guild fr-without-cap-check`.
  Expected: prints `1` and `1`, and the detector exits 0.
- **AC12 — The Dream records the landing.**
  `grep -c '^- \*\*20[0-9][0-9]-[0-9][0-9]-[0-9][0-9] (cutover readiness' docs/dreams/pyforge-herald.md`. Expected:
  prints `2` (the mint's entry and this story's landed line, whatever date it lands).
- **AC13 — Herald's chain is whole.**
  `pixi run -e pyforge-guild chain-completeness-check && pixi run -e pyforge-guild dream-chain-check && pixi run -e pyforge-guild dreams-hygiene-check && pixi run -e pyforge-guild status-body-consistency-check && pixi run -e pyforge-guild ad-citation-check`.
  Expected: exit 0, and herald is not listed stale.
- **AC14 — No unreconciled drift names herald's Spec.** No unreconciled drift row names
  `pyforge-herald/spec-pyforge-herald` (this story's memlog names every changed path; doctor:S-58.4 stamps).
  Expected: prints `0`, exit 0.

```bash
pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources spec-surface --json > "$TMPDIR/ss.json"; python3 -c "import json,sys;d=json.load(open(sys.argv[1]));rows=d if isinstance(d,list) else (d.get('findings') or d.get('rows') or []);n=[r for r in rows if r.get('check') in ('drift','drift-presumed') and sys.argv[2] in json.dumps(r)];print(len(n));sys.exit(1 if n else 0)" "$TMPDIR/ss.json" pyforge-herald/spec-pyforge-herald
```

- **AC15 — The retro is current.** The herald retro is dated on or after the last package-manifest commit. Expected:
  prints two dates, the retro's not earlier, exit 0.

```bash
python3 -c "import glob,re,subprocess,sys;f=sorted(glob.glob('_bmad-output/projects/pyforge-herald/planning-artifacts/retros/retro-pyforge-herald-2026-1*.md'));d=re.search(r'\d{4}-\d{2}-\d{2}',f[-1]).group(0) if f else '';c=subprocess.run(['git','log','-1','--format=%cs','--','src/shared/packages/pyforge-herald/pyproject.toml'],capture_output=True,text=True).stdout.strip();print(d,c);sys.exit(0 if d and d>=c else 1)"
```

- **AC16 — The readiness gate is fresh.**
  `ls _bmad-output/projects/pyforge-herald/planning-artifacts/implementation-readiness-report-2026-1*.md`. Expected:
  lists one file or more.
- **AC17 — Herald's chain is current.**
  `pixi run --frozen -e pyforge-guild chain-currency-sweep-check -- --project pyforge-herald`. Expected: exit 0 (1 is
  a finding, 2 could not run).
- **AC18 — The two integration rows are tracked.**
  `grep -cE '^### DW-herald-cutover-2026-11-10-[12]\b' _bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md`.
  Expected: prints `2`.
- **AC19 — The newly governed script is reconciled.** `scripts/deck_export.py` is named in the reconcile event.
  Expected: prints `1 []`, exit 0.

```bash
python3 - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md <<'EOF'
import sys,subprocess,yaml,fnmatch
spec,ml=sys.argv[1],sys.argv[2]
surf=lambda t:(yaml.safe_load(t.split('---')[1]) or {}).get('surface') or []
new=surf(open(spec).read());old=surf(subprocess.run(['git','show','origin/main:'+spec],capture_output=True,text=True).stdout)
files=subprocess.run(['git','ls-files'],capture_output=True,text=True).stdout.split()
m=lambda p,gs:any(fnmatch.fnmatch(p,g) or (g.endswith('/**') and p.startswith(g[:-2])) or (g.endswith('/') and p.startswith(g)) for g in gs)
added=[p for p in files if m(p,new) and not m(p,old)];t=open(ml).read();miss=[p for p in added if p not in t]
print(len(added),miss);sys.exit(1 if miss else 0)
EOF
```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-herald CAP-46 and CAP-62 (markers flip to shipped). The Spec's three sections are
  re-derived. No CAP is minted, and no FR or AD moves.
- Dream: `docs/dreams/pyforge-herald.md`, the 2026-11-10 (cutover readiness) entry. Rulings:
  `docs/dreams/pyforge-unifying-strategy.md`, the three 2026-11-10 entries.
- Epic 50. Ledger key
  `50-2-the-herald-spec-has-its-constraints-non-goals-and-assumptions-again-and-the-chain-closes-on-what-landed`.
- Cross-station: steward:S-121.7 (the capability ledger regenerated after every Spec sweep) and doctor:S-58.4 (the
  scoped stamps, once, after the last edit). Both are held by the single PR's integration order.
- Findings closed: MUST 3; SHOULD: goldens frozen from the retired Jinja generator; NICE: README, Why, companions,
  facts-ledger, deck help; NICE: unwired scripts, `web/` unbuilt, deck_facts env strings.

## Spec Change Log

- 2026-11-10: minted (backlog) from the station Dream's 2026-11-10 (cutover readiness) entry and the operator's
  rulings of 2026-11-10. The rulings set the marker regexes (they add `retired`), the deferred row set (`50-1-1`,
  `50-1-2` and `50-3-1` are not minted) and AC10's count of 5.
- 2026-11-10: status set to blocked (forward dependency on a later epic; unblocked only with operator confirmation).

## Planned deferral (written at build)

The row below is not in the deferred-work ledger yet. This story writes it to
`planning-artifacts/deferred-work-ledger.md` and adds it to this spec's `deferred:` frontmatter in the same change,
because `deferred-work-check` refuses a frontmatter deferral with no tracked twin. Station deferred-work rows are
written at build, never at mint.

- **`DW-herald-50-2-1`** (low, open; location `scripts/deck_facts.py`): scripts/deck_facts.py names `-e local-recipes` at :81, :124, :687 and :1177, though deck-facts and bmad-groundtruth are Guild tasks. Two of the four strings are written into every deck's facts.yaml (a `source:` value and the header), so the fix re-derives 14 ledgers and their posters, and the Design mirror then needs a credentialed push to stay byte-equal (CAP-17), which is the operator's. The companion facts-ledger.md:40 keeps quoting the literal the script writes, with a note naming this row. Fix with the next deck-family refresh that pushes to Design.
