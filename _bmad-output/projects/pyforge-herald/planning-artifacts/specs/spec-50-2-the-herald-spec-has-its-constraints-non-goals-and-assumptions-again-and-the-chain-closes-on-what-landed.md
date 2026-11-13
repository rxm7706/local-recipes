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
  `grep -c '^### DW-herald-\(50-1-3\|50-2-1\|50-3-2\|50-4-1\|52-1-1\|52-1-2\|52-2-1\):' _bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md && pixi run --frozen -e pyforge-guild deferred-work-check`.
  Expected: prints `7`, then exit 0. (Corrected 2026-11-12 by build review round 1, findings 3 and 5: the pattern
  gains `50-4-1` and `52-1-2`, the count moves from 5 to 7, and the detector call gains `--frozen`.)
- **AC11 — The mint's requirement arrows stand.**
  `grep -c '^\*\*FR-14\.1: .*← CAP-62' …/prd.md; grep -c '^\*\*FR-12\.5: .*← CAP-61, CAP-46' …/prd.md; pixi run --frozen -e pyforge-guild fr-without-cap-check`.
  Expected: prints `1` and `1`, and the detector exits 0. (Corrected 2026-11-12 by build review round 2, finding 3:
  the detector call gains `--frozen`, so the check cannot re-lock `pixi.lock`; the oracle is unchanged.)
- **AC12 — The Dream records the landing.**
  `grep -c '^- \*\*20[0-9][0-9]-[0-9][0-9]-[0-9][0-9] (cutover readiness' docs/dreams/pyforge-herald.md`. Expected:
  prints `2` (the mint's entry and this story's landed line, whatever date it lands).
- **AC13 — Herald's chain is whole.**
  `pixi run --frozen -e pyforge-guild chain-completeness-check && pixi run --frozen -e pyforge-guild dream-chain-check && pixi run --frozen -e pyforge-guild dreams-hygiene-check && pixi run --frozen -e pyforge-guild status-body-consistency-check && pixi run --frozen -e pyforge-guild ad-citation-check`.
  Expected: exit 0, and herald is not listed stale. (Corrected 2026-11-12 by build review round 1, finding 3: each
  call gains `--frozen`, so the check cannot re-lock `pixi.lock`; the oracle is unchanged.)
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
- **`DW-herald-50-2-2`** (medium, open; location `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md`; added at build by review round 2, 2026-11-12): 58 constraint, non-goal and assumption entries in the archived memlogs of the Specs folded into spec-pyforge-herald never entered its memlog, so the re-derived sections cannot render them: 25 from the nine Specs the 2026-09-17 fold absorbed and 33 from spec-deckcraft and spec-design-code-bridge (60 counted on 2026-11-12, two already in herald's memlog). Replaying, retiring or ruling out each one is a Spec pass of its own, beyond this story's Intent (a), which re-derives from herald's own memlog; a fix no Story carries takes its own Story (AGENTS.md § Behavioural guidelines item 3).

## Review findings (build, round 1, 2026-11-11)

An independent reviewer failed the first build attempt: one major and seven minor findings. Each is listed with its
severity, where it is and the problem, then what round 1 did (2026-11-12).

1. **major** — `spec-pyforge-herald/SPEC.md` § Assumptions, and CAP-30's success clause. CAP-30's success reads
   "pulled byte-exact to the design-system home (see Assumptions)", but no bullet of the re-derived Assumptions names
   that home. The referent is `spec-design-sync-loop`'s assumption at commit `e55710af3b`: the design-system mirrors
   live at `presentations/_design-systems/<name>/`. The 2026-09-17 fold dropped it and it never entered herald's
   memlog, so a re-derive from memlog entries alone cannot recover it, and AC2 (bullets against entries) cannot see
   the gap. The self-validate passes and the readiness report called the five-field contract whole regardless.
   **Fixed.** One `(assumption by claude)` memlog entry restores it with its provenance (`broadsheet`, `modernist`
   and `nocturne`, 84 tracked files on 2026-11-12; excluded from the deck roster by name in `scripts/fleet_scan.py`'s
   `_NOT_A_DECK`; read by path only by `pptx_native.py`). `SPEC.md` was written back from its HEAD copy (a file
   write, not a git write) and re-rendered by `render_50_2.py` with the bullet added. The counts move to 10
   Assumptions bullets and five entries recorded that day, in `updated:`, in the section's italic note and in a
   superseding `(decision by claude)` memlog entry: the memlog is append-only, so the earlier sections decision stays
   as written and the later entry supersedes its counts, as Story 50.1's re-run event did. Both self-validate passes
   are logged again. The retro's finding 1 and the readiness report carry the corrected counts and the fold's second
   loss.
2. **minor** — `scripts/spec_surface_allowlist.txt:57` (not this story's file) and `spec-surface-check`. Adding
   `scripts/deck_export.py` to herald's `surface:` leaves the allowlist entry `scripts/deck_export.py` matching
   nothing, so `pixi run --frozen -e pyforge-guild spec-surface-check` exits 2 with `stale-allowlist: fail`; mason's
   `scripts/cfe_rebuild_guard_check.py` entry is in the same state at HEAD. The first attempt's report did not name
   the new FAIL. **Recorded; no change to this story's files.** A planned red window, BUILD-10 to BUILD-18:
   plan.json's doctor Story 58.4 (BUILD-18) removes `scripts/deck_export.py` from the allowlist by content (its
   `files_owned` entry and its allowlist acceptance check both name it), with `scripts/detectors.py`,
   `scripts/cfe_rebuild_guard_check.py` and the cfe comment block.
3. **minor** — AC13, and plan.json's form of it. Its five `pixi run` calls carry no `--frozen`; on this branch the
   path dependencies' manifests changed, so AC13 as written re-locks `pixi.lock` (the first attempt restored the lock
   from HEAD; only steward Story 124.3, BUILD-13, re-locks). The reviewer re-ran it with `--frozen`: all five exit 0
   and the lock is unchanged. **Oracle corrected** (the fault is the command's; the check is the same): each of the
   five calls gains `--frozen`. Old: `pixi run -e pyforge-guild chain-completeness-check && pixi run -e pyforge-guild
   dream-chain-check && …` (five calls). New: `pixi run --frozen -e pyforge-guild chain-completeness-check && pixi run
   --frozen -e pyforge-guild dream-chain-check && …` (the same five, each `--frozen`). AC11's `fr-without-cap-check`
   call has the same fault and no finding; round 1 ran it with `--frozen` (the build rule) and left its text to the
   spec owner.
4. **minor** — Intent (i); the frontmatter of story specs 50.2, 50.3, 50.4, 52.1 and 52.2. Intent (i) asks for each
   row's `deferred:` frontmatter entry in the same change; the build rules forbid it, so none was written, and each
   ledger row carries `origin: spec-deferred <fp>` instead. The reviewer checked all six fingerprints against
   `harvest_fingerprint(summary, location)`: all match. **The integrator's:** write the five `deferred:` entries,
   copying summary and location byte for byte from the ledger twins (the retro's action 1). Round 1 changed no
   summary or location of those rows (finding 8 touched evidence and fix fields only), and the six fingerprints were
   re-checked after it.
5. **minor** — Intent (i) and AC10. Neither names `DW-herald-52-1-2`, and AC10 does not count `DW-herald-50-4-1`;
   both rows were rightly written (Story 52.1's round-2 review and Story 50.4's Planned deferral hand them to 50.2),
   so AC10's count of 5 checks only part of what was written. **Oracle corrected** (a stricter check, nothing
   dropped): AC10's pattern gains `50-4-1` and `52-1-2`, its expected count moves from 5 to 7, and its
   `deferred-work-check` call gains `--frozen` (finding 3's fault). Old: `grep -c
   '^### DW-herald-\(50-1-3\|50-2-1\|50-3-2\|52-1-1\|52-2-1\):' … && pixi run -e pyforge-guild deferred-work-check`,
   expecting `5`. New: `grep -c '^### DW-herald-\(50-1-3\|50-2-1\|50-3-2\|50-4-1\|52-1-1\|52-1-2\|52-2-1\):' … &&
   pixi run --frozen -e pyforge-guild deferred-work-check`, expecting `7`. Intent (i) is not a section a build round
   may write; it already names `DW-herald-50-4-1` (conditionally), and the spec owner adds `DW-herald-52-1-2` to it
   with a Spec Change Log line.
6. **minor** — the CAP-46 and CAP-62 markers. Intent (e) asks for the date each story landed; the markers read
   `(shipped 2026-11-11)`, the date of build commit `cf3caf4f45` on the integration branch, because the single PR has
   no merge date at build (the memlog change entry says why). **No change now:** the integrator may move both dates
   to the merge date with a memlog change entry when the PR lands.
7. **minor** — the `pyforge-herald-test-built` Assumptions bullet (memlog entry of 2026-11-12) says the built-site
   oracle tests run "only" in that task, which overstates. **Fixed, with one correction to the finding:** the other
   task that runs docs-site's install first and sets `HERALD_DOCS_SITE_REQUIRED=1` is `pyforge-herald-test-coverage`
   (the named-module coverage report through `scripts/run_station_coverage_gate.py`, `-m "not slow"` over unit and
   meta, live-tree modules included), not `pyforge-herald-coverage-gate`, which `pixi.toml` keeps install-free on
   purpose (herald Story 45.1's comment above it). A `(change by claude)` memlog entry narrows the wording, and the
   re-rendered bullet names both tasks. Its point stands: a green `pyforge-herald-test` proves nothing for those
   capabilities.
8. **minor** — capability ids this story wrote without a Spec qualifier: `CAP-17` in `DW-herald-50-2-1`, `CAP-4` and
   `CAP-34` in `DW-herald-50-4-1`, and `(CAP-46, FR-12.5)` and `` `spec-pyforge-herald` CAP-62 `` in the Dream's
   landed line. **Fixed:** each reads `spec-pyforge-herald:CAP-n` (the quoted literal heading
   `(spec-design-sync-loop CAP-6)` stays as the code writes it). Only evidence and fix fields changed in the ledger,
   so no fingerprint moved.

**Round 1 result (2026-11-12).** The two oracle corrections are also written to plan.json's `stories[50.2].acceptance`
(AC10 there still carried the pre-ruling pattern, `50-1-[123]` and `50-3-[12]` expecting 8; it now carries the
corrected form above, expecting 7; AC13 there gains the same five `--frozen`). Every acceptance command was re-run
on the round-1 tree, each verdict read from its exit code: AC1 `3`; AC2 `[]`, exit 0 (bullets 8, 3 and 10 against 8,
3 and 10 live entries); AC3 exit 1; AC4 `3 1 1 7 1 2`; AC5 prints nothing; AC6 exit 1, `1`, `1`; AC7 `62 [] []`; AC8
eight keys, `[]`; AC9 `66 []`; AC10 `7`, `deferred-work-check` exit 0; AC11 `1`, `1`, `fr-without-cap-check` exit
0 (run with `--frozen`); AC12 `2`; AC13 the five checks exit 0 with `--frozen`; AC14 `0`, exit 0 (the
spec-surface run itself exits 2 on finding 2's two `stale-allowlist` rows, `scripts/deck_export.py` and
`scripts/cfe_rebuild_guard_check.py`, the planned window doctor Story 58.4 closes); AC15 `2026-11-12 2026-11-11`;
AC16 lists the 2026-11-12 report; AC17 exit 0, herald current; AC18 `2`; AC19 `1 []`. `pixi.lock` is unchanged
(byte-equal to HEAD before and after).

## Review findings (build, round 2, 2026-11-11)

An independent reviewer failed the round-1 build: one major and three minor findings. Each is listed with its
severity, where it is and the problem; what round 2 did (2026-11-12) follows the list.

1. **major** — `spec-pyforge-herald/SPEC.md`, the "Consolidated 2026-08-02" note (lines 98-99) and the re-derived
   `## Constraints`, `## Non-goals` and `## Assumptions`; the memlog decision of 2026-09-09 (memlog line 262). Round 1
   fixed one dangling citation (spec-pyforge-herald:CAP-30's "see Assumptions"), but audit MUST 3 names a second one
   ("yet line 96 and CAP-30 cite them"): the note still reads "HER-1, HER-2, HER-3 and both Constraints/two of the
   Non-goals below are unchanged from the pre-consolidation version", and no section below carries them. `SPEC.md`
   at `4251c42229^` had two station-level constraints ("The Dream is Tier 0 and this Spec is Tier 2"; "Ownership does
   not move with the work") and two station-level non-goals ("Owning the console", its Guildhall referent pending a
   Charter amendment; "Infrastructure. Moved to Marshal"). The 2026-09-17 fold dropped all four, none was ever a typed
   memlog entry, so a re-derive from typed entries could not recover them, and AC2 compares counts only. The fold also
   dropped `## Residual dependencies (2026-09-09)`, which the live decision of 2026-09-09 orders rendered "as a dated
   DEPENDENCY in Assumptions/Residual"; the Charter question is still open, and the re-derive renders it nowhere. So
   MUST 3 was half closed, and self-validate pass 2, the retro's finding 1 and the readiness report called the three
   sections whole.
2. **minor** — the retro's findings 1 and 10, the readiness report's Spec row and the Dream's landed line. Four facts
   are wrong: finding 10 says AC10's pattern "does not count it and does not need to" (`DW-herald-52-1-2`), but round
   1 corrected AC10 to count it (7 rows); finding 1 says the design-system home was something "no memlog held", but
   the archived `spec-design-sync-loop/.memlog.md:25` holds it as an `(assumption)`, and its "one more thing" framing
   understates the fold's losses (the station-level constraints and non-goals, `§ Residual dependencies`, and about
   60 typed entries in the absorbed Specs' archived memlogs); the readiness report says "contract.md and eight other
   companions", but `companions:` lists 10, nine besides `contract.md`; the Dream's landed line credits Story 50.1
   with "59 shipped, 3 retired", but Story 50.1 left 57 shipped, 2 ready (spec-pyforge-herald:CAP-46 and
   spec-pyforge-herald:CAP-62) and 3 retired, and 59/3 is the state after Story 50.2.
3. **minor** — AC11, and plan.json's `stories[50.2].acceptance[10]`. AC11 still runs `pixi run -e pyforge-guild
   fr-without-cap-check` without `--frozen`, the fault round 1 corrected in AC13 (finding 3): run as written on this
   branch, it re-locks `pixi.lock`, which only steward Story 124.3 may do.
4. **minor** — the retro and the readiness report (new text). Several lines use bare ids ("CAP-46 and CAP-62 say
   what ...", "CAP-47 and CAP-58..CAP-61", "CAP-1 to CAP-62", "AD-23's 300-line bound"); round 1's finding 8
   qualified ids in the ledger and the Dream only.

**What round 2 did (2026-11-12).**

1. **Fixed.** Each of the four station-level entries still holds, so each is restored, not retired, by one typed memlog
   entry with its provenance (`SPEC.md` at `4251c42229^`, first written 2026-07-29 in `55ce2f4bae`, dropped by the
   2026-09-17 fold): two `(constraint by claude)` entries (the Tier 0 and Tier 2 rule, which AGENTS.md § The tiers
   still states; "Ownership does not move with the work", Charter §5's outcome-and-mechanism rule) and two
   `(non-goal by claude)` entries ("Owning the console", its rule left un-reworded as the question entry of 2026-09-09
   orders; "Infrastructure", whose referent the Dream's § The Dream still names as pyforge-marshal). One
   `(assumption by claude)` entry renders the 2026-09-09 decision's Guildhall dependency, re-measured that day: the
   Charter's open question is still open, factory-console's Dream is archived and its Spec absorbed, and
   `retired-console-check` is registered. A superseding `(decision by claude)` entry sets the counts (10, 5 and 11
   bullets). `SPEC.md` was written back from its HEAD copy (a file write) and re-rendered by `render_50_2.py`, which
   now also asserts the two citation anchors (the consolidation note and spec-pyforge-herald:CAP-30's "see
   Assumptions") once in the pre-render copy, each added bullet once and each section's bullet count in its output;
   a second run refuses. Both self-validate passes are logged as memlog events: the coherence pass resolves every
   in-Spec "below", "above" and "see <section>" citation (the note's two, Why's three, those of
   spec-pyforge-herald:CAP-1, spec-pyforge-herald:CAP-2, spec-pyforge-herald:CAP-3 and spec-pyforge-herald:CAP-30,
   the console non-goal's pointer and the italic notes' "note above") and the external section citations;
   the preservation pass finds everything outside `updated:` and the three sections byte-identical to the round-1
   render, and every round-1 bullet standing. A `(note by claude)` entry narrows the pass-2 event's last clause to the
   three rendered types. The retro (finding 1, action 3, new action 6) and the readiness report carry the counts and
   the losses of the fold that round 2 had found (corrected on round 3: not every loss of the fold, since five more
   items of herald's own pre-fold Constraints and Non-goals and the nine absorbed Specs' SPEC text were missing; see
   § Review findings (build, round 3, 2026-11-12)). The reviewer's "60 or so" typed entries in the absorbed Specs' memlogs measure 60 exactly
   outside spec-herald-pitch and spec-herald-moments-2-4 (whose entries the 2026-08-02 consolidation replayed): 26 in
   the nine Specs the 2026-09-17 fold absorbed and 34 in spec-deckcraft and spec-design-code-bridge, which herald
   took in through spec-herald-pitch; 2 are in herald's memlog, and spec-deckcraft's 21 govern the standalone
   deckcraft product (`apps/deckcraft/**`) more than herald. Replaying, retiring or ruling out the 58 is a Spec pass
   beyond Intent (a), so it is deferred with a tracked row, `DW-herald-50-2-2` (medium), and a § Planned deferral
   entry; no `deferred:` frontmatter is written (the build rules).
2. **Fixed.** Retro finding 10 now says round 1 corrected AC10 to count `DW-herald-52-1-2` (7 rows); finding 1 names
   the archived `spec-design-sync-loop/.memlog.md:25` as the design-system home's holder and lists every loss of the
   fold; the readiness report reads "`contract.md` and nine other companions"; the Dream's landed line gives Story
   50.1 57 shipped, 3 retired and spec-pyforge-herald:CAP-46 and spec-pyforge-herald:CAP-62 ready, and puts 59 and 3
   after Story 50.2. The landed line and the readiness report also name `DW-herald-50-2-2`.
3. **Oracle corrected** (the fault is the command's; the check is the same): AC11's detector call gains `--frozen`, in
   the AC block above and in plan.json's `stories[50.2].acceptance[10]` (whose `expect` records the correction). Old:
   `…; pixi run -e pyforge-guild fr-without-cap-check`. New: `…; pixi run --frozen -e pyforge-guild
   fr-without-cap-check`. The two `grep -c` counts and their expected `1` and `1` are unchanged.
4. **Fixed.** Every capability id in the retro and the readiness report now reads `spec-pyforge-herald:CAP-n` (a range
   as `spec-pyforge-herald:CAP-58..CAP-61`), and AD-23 reads `herald:AD-23`, the spine prefix herald's `epics.md`
   uses; `grep -P '(?<![:\w.-])(CAP|AD)-\d+'` finds no bare id in either file.

**Round 2 result (2026-11-12).** Every acceptance command was re-run on the round-2 tree, each verdict read from its
exit code: AC1 `3`; AC2 `[]`, exit 0 (bullets 10, 5 and 11 against 10, 5 and 11 live entries); AC3 exit 1; AC4
`3 1 1 7 1 2`; AC5 prints nothing; AC6 exit 1, `1`, `1`; AC7 `62 [] []`; AC8 eight keys, `[]`; AC9 `66 []`; AC10 `7`,
`deferred-work-check` exit 0; AC11 `1`, `1`, `fr-without-cap-check` exit 0 (with `--frozen`); AC12 `2`; AC13 the five
checks exit 0, herald in no finding; AC14 `0`, exit 0 (the spec-surface run itself exits 2 on the two
`stale-allowlist` rows of round 1's finding 2, the window doctor Story 58.4 closes); AC15 `2026-11-12 2026-11-11`; AC16
lists the 2026-11-12 report; AC17 exit 0, `pyforge-herald: current`; AC18 `2`; AC19 `1 []`. `pixi.lock` is byte-equal
to HEAD before and after.


## Integrator ruling (2026-11-12, before the chunk-7 retry)

This ruling binds the implementer and the reviewer. It closes round 3's major in two parts. Herald's own pre-fold
items are restored or retired (the reviewer's option a). The absorbed Specs' SPEC-text bullets are tracked, not
restored.

1. **Herald's own five pre-fold items** (herald's SPEC.md at `4251c42229^`). Give each item one typed memlog
   entry. Write it with `uv run _bmad/scripts/memlog.py` from the repo root, and cite that provenance in it.
   - Restore the non-goals "Replacing Moment 1" and "Marketing proclamation". Only update their wording to
     today's names.
   - Retire the non-goal "Implementing automation yet" with a `(change)` entry that says why: herald now
     automates.
   - For the constraint "No silent shipping", search herald's source, CI and pixi tasks for a gate that enforces
     it. If none exists, retire it. If one exists, restore it and name that gate.
   - Narrow "Multi-surface readiness" to the surfaces that remain after CAP-6's retirement.
   Then re-render once with `render_50_2.py` from the HEAD copy and assert the new counts. Log both
   self-validate passes: the render is byte-identical, and a second run refuses.
2. **The nine absorbed Specs' SPEC-text bullets: track them.**
   - Widen only the evidence and fix of DW-herald-50-2-2. Leave its summary and location unchanged, so its
     fingerprint stays.
   - The evidence gives measured counts per Spec: the SPEC-text Constraints, Non-goals and Assumptions bullets at
     `4251c42229^`, deduplicated against each Spec's typed memlog entries.
   - The fix recovers the SPEC-text bullets, not only the memlog entries.
   - Run `deferred-work-check` afterwards.
3. **Correct the accounting.** Fix retro finding 1 and action 6, the DW-herald-50-2-2 concern row in the
   readiness report, and this spec's round-2 line. None of them may claim that more of the fold's loss is restored
   or tracked than items 1 and 2 do. Append one `(note by claude)` memlog entry that narrows the round-2
   decision's claim.
4. **Round 3's minor: bare ids.** Qualify the bare ids in the new lines only: the spine's § Currency
   reconciliation — 2026-11-12, and the Standing lines of the five companions. Write CAP ids as
   `spec-pyforge-herald:CAP-n`. Write the AD id in the project form that steward 124.5's ruling used
   (`pyforge-atlas:AD-13`), here `pyforge-herald:AD-23`. Run `ad-citation-check` afterwards.
5. Do not stamp; doctor 58.4 stamps. Never change `pixi.lock`. Every AC must still pass. Append
   `## Review findings (build, round 3, 2026-11-12)` and say how each item closed.

## Review findings (build, round 3, 2026-11-12)

An independent reviewer failed the round-2 build: one major and one minor finding. The integrator's ruling above
(2026-11-12) decided how each closes. Each finding is listed with its severity, where it is and the problem; what
round 3 did follows, by ruling item.

1. **major** — fold-loss accounting: `DW-herald-50-2-2` (summary, evidence and fix), the retro's finding 1 and action
   6, the readiness report's `DW-herald-50-2-2` concern row, the round-2 superseding decision on
   `spec-pyforge-herald/.memlog.md` and this spec's round-2 line ("every loss of the fold"). Round 2 claimed every
   loss of the 2026-09-17 fold (`4251c42229`) was restored or tracked, and the ledger row's evidence said round 2
   "restored what the fold dropped from SPEC.md itself". Neither held. Five items of herald's own `SPEC.md` at
   `4251c42229^` were rendered nowhere, retired by no change entry and named in no row: the constraints
   "Multi-surface readiness" and "No silent shipping", and the non-goals "Replacing Moment 1", "Implementing
   automation yet" and "Marketing proclamation". And the fold stubbed the nine absorbed Specs' `SPEC.md`, whose 89
   Constraints, Non-goals and Assumptions bullets at `4251c42229^` stood against 26 typed memlog entries, while the row
   scoped the loss to the archived typed entries alone.
2. **minor** — bare ids in text this story wrote: the spine's § Currency reconciliation — 2026-11-12 (its citations
   of spec-pyforge-herald:CAP-46, spec-pyforge-herald:CAP-62 and pyforge-herald:AD-23 were unqualified) and the
   Standing lines of `artifact-tracking-matrix.md`,
   `workflow-stages.md`, `six-act-framework.md`, `bridge-protocol.md` and `epic-structure.md`.

**What round 3 did (2026-11-12), by ruling item.**

1. **Herald's five pre-fold items: closed.** Five typed memlog entries, each citing `SPEC.md` at `4251c42229^` (line
   174, 181, 196, 197 or 198), its first writing on 2026-08-02 by the consolidation (`0db72d1e9b`) and its archived
   source line (spec-herald-pitch `SPEC.md:153`; spec-herald-moments-2-4 `SPEC.md:87`, `:93`, `:97`, `:99`).
   "Replacing Moment 1" and "Marketing proclamation" are restored by `(non-goal by claude)` entries, worded with
   today's names only (`herald deck`, spec-pyforge-herald:CAP-4..CAP-10; `herald progress`, `herald success` and
   `herald notice`, spec-pyforge-herald:CAP-11..CAP-13). "Implementing automation yet" is retired by a `(change by
   claude) retires non-goal:` entry: herald now automates (spec-pyforge-herald:CAP-11..CAP-13 shipped, and
   spec-pyforge-herald:CAP-38 and spec-pyforge-herald:CAP-39 in the operator-run form ruling 4 of 2026-11-10 made the
   end state). "No silent shipping" is retired by a `(change by claude) retires constraint:` entry, because no gate
   enforces it: `git grep -nIiE 'silent[ -]shipping|pre-ship|preship' -- src/shared/packages/pyforge-herald .github
   pixi.toml scripts docs-site` exits 1, and no workflow, pre-commit hook or pixi task runs `herald success` or
   `pyforge.herald.claims` (exit 1); a draft claim is recorded only when the operator runs `herald-ship-local`, and
   spec-pyforge-herald:CAP-12's success clause still states the outcome. "Multi-surface readiness" is restored narrowed
   by a `(constraint by claude)` entry: interactive HTML, editable PPTX and static infographics, with video scripts
   gone with spec-pyforge-herald:CAP-6. A superseding `(decision by claude)` entry sets the counts, 11, 7 and 11
   bullets, and the order (the constraint after the etag bullet, the two non-goals after "Real-time collaboration", as
   the pre-fold text ordered them), and says why the typed-minus-retired arithmetic reads one under the bullets in
   Constraints and Non-goals: the two retire entries of this round retire SPEC-text items that had no typed entry.
   `SPEC.md` was written back from its HEAD copy (a file write) and re-rendered once by `render_50_2.py`, which now
   also asserts the three added bullets once and in their places, no bullet for the two retired items, and the new
   counts. Both self-validate passes are logged as memlog events: the render is byte-identical (the same script re-run
   on a scratch HEAD copy outside the worktree writes a file equal to `SPEC.md` byte for byte), and a second run
   refuses and writes nothing (on the worktree, and with its own output as the pre-render copy). Against the round-2
   render only `updated:`, the Constraints and Non-goals italic notes and the three added bullets differ; every round-2
   bullet stands byte for byte. Each of the 12 Constraints and 10 Non-goals bullets of herald's `SPEC.md` at
   `4251c42229^` is now rendered, retired by a dated change entry, or was already struck in that text ("Re-specifying
   Moments 2–4", AMENDED 2026-08-02).
2. **The nine absorbed Specs' SPEC-text items: tracked, not restored.** `DW-herald-50-2-2`'s evidence and fix are
   widened; its summary and location are unchanged, so its fingerprint stays `612d0732d695` (re-computed after the
   edit). The evidence gives, per Spec, the SPEC-text Constraints, Non-goals and Assumptions bullets at `4251c42229^`,
   the Spec's typed entries, and the bullets no typed entry carries: currency 16, 11, 5; lockstep 14, 4, 7; visual-qa
   11, 0, 11; design-sync-loop 14, 8, 6; moments-2-4-live-backend 15, 2, 12; moments-2-4-missing-surface 3, 0, 3;
   pptx-custom-shapes 1, 0, 1; pptx-deck-generation 0, 0, 0; pyforge-pages 15, 1, 9. In all, 89 bullets against 26
   typed entries and 54 bullets no typed entry carries, plus 6 prose paragraphs (the two pptx Specs wrote their
   Constraints and Non-goals as prose). The fix now recovers those SPEC-text items as well as the 58 archived typed
   entries, and says that a replay of the typed entries alone does not close the row. `deferred-work-check` exits 0
   after the edit.
3. **Accounting: corrected.** The retro's finding 1 lists every loss (herald's own five items and the nine Specs'
   stubbed SPEC text included), says the instance is fixed for herald's own Spec text only, and names what stays
   tracked; action 6 recovers the SPEC-text items and the typed entries; action 3's prevention adds the folded Specs'
   untyped Constraints, Non-goals and Assumptions text. The readiness report's concern row names both parts of
   `DW-herald-50-2-2` and says none of them is restored, and its Spec row carries 11, 7 and 11. This spec's round-2
   line now reads "the losses of the fold that round 2 had found", with the correction named. A `(note by claude)`
   memlog entry narrows the round-2 superseding decision's claim to the station-level items and § Residual
   dependencies, and names the five items and the nine Specs' text it left out.
4. **Bare ids: qualified.** In the spine's § Currency reconciliation — 2026-11-12 (and the matching clause of its new
   `updated:` stamp), the ids read spec-pyforge-herald:CAP-46, spec-pyforge-herald:CAP-62 and pyforge-herald:AD-23. In
   the five Standing lines they read spec-pyforge-herald:CAP-6, spec-pyforge-herald:CAP-8,
   spec-pyforge-herald:CAP-51, spec-pyforge-herald:CAP-37..CAP-39, and, for the bridge's pre-fold ids,
   spec-design-code-bridge:CAP-1..CAP-5. No companion body changed (`station-roster.md`'s Standing line had no id).
   `ad-citation-check` exits 0 with no herald row.
5. **No stamp; `pixi.lock` unchanged.** `spec_surface_check.py --write-baseline` was not run (doctor Story 58.4 stamps
   once). `pixi.lock` is byte-equal to HEAD before and after every command.

**Round 3 result (2026-11-12).** Every acceptance command was re-run on the round-3 tree, each verdict read from its
exit code: AC1 `3`; AC2 `[]`, exit 0 (bullets 11, 7 and 11 against 10, 6 and 11 typed entries less retire entries);
AC3 exit 1; AC4 `3 1 1 7 1 2`; AC5 prints nothing; AC6 exit 1, `1`, `1`; AC7 `62 [] []`; AC8 eight keys, `[]`; AC9
`66 []`; AC10 `7`, `deferred-work-check` exit 0; AC11 `1`, `1`, `fr-without-cap-check` exit 0 (with `--frozen`); AC12
`2`; AC13 the five checks exit 0, herald in no finding; AC14 `0`, exit 0 (the spec-surface run itself exits 2 on three
`stale-allowlist` rows, `scripts/detectors.py`, `scripts/deck_export.py` and `scripts/cfe_rebuild_guard_check.py`,
all in the window doctor Story 58.4 closes); AC15 `2026-11-12 2026-11-11`; AC16 lists the 2026-11-12 report; AC17
exit 0, `pyforge-herald: current`; AC18 `2`; AC19 `1 []`. Doctor's three live deferred-work and hygiene test modules
(8 passed) and herald's `test_public_contract.py` and `test_verify_claims_emit.py` (47 passed) are green.
