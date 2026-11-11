---
title: "50.1: Every herald capability's marker and text say what is true"
type: 'chore'
created: '2026-11-10'
status: 'backlog'
difficulty: heavy
story: '50.1'
spec: pyforge-herald
surface:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-50-1-every-herald-capability-s-marker-and-text-say-what-is-true.md
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-herald.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** At `82a2b18828` herald's Spec does not describe its code. 19 capability markers read shipped, 37 read
ready and 5 read in-progress (CAP-37, CAP-38, CAP-39, CAP-48, CAP-49), against a ledger of 152/152 stories done, so 42
markers are stale. CAP-44, CAP-45, CAP-46, CAP-49, CAP-52, CAP-53 and CAP-56 describe the retired docsite as live.
CAP-38 names a webhook route the code does not serve. CAP-6 claims a narration extractor and a video pipeline that are
in no tracked path. CAP-11 claims a cost derivation that was never built. Deck counts disagree across CAP-4..CAP-30, and
four modules over 500 lines (`agent_sdk_transport.py`, `deck_qa.py`, `pptx_pipeline.py`, `pptx_native.py`) are named
by no capability (`research/cutover-readiness-audit-2026-11-10.md`, MUST 1 and MUST 2).

**Approach:** The mint (2026-11-10) logged fourteen `decision` entries on the Spec's memlog, each marked "Story 50.1
renders", carrying the operator's rulings of 2026-11-10 (second addendum, rulings 2 and 4); the mint's review added a
fifteenth on 2026-11-11, which gives CAP-44, CAP-52, CAP-53, CAP-56 and CAP-61 their shipped markers, so each of the 38
`ready` markers at the mint has an instruction (36 leave `ready`; CAP-46 and CAP-62 keep it). This story writes one
`change` entry with the shipped-date table, then renders every group in one anchored script re-derive, then writes
the deferred-work rows. No code changes. It is the first build-time writer of the Spec; Story 50.2 is the second and
last.

- **Markers.** A marker reads `(ready <date>)`, `(shipped <date>)` or `(retired <date>[: <reason>])`. A qualifier may
  follow a semicolon: `not met: <clause>, DW-<id>`, `operator act open, DW-<id>`, `superseded by CAP-n`. An existing
  `; amended …` or `; extends …` tail stays. There is no `(unbuilt)` marker.
- **Shipped dates.** Each shipped date is the landing of the last story whose FR/AD line cites the capability (every
  such story is `done`), read from `git log --merges --grep 'Merge pyforge-herald/<key>'` or from the story spec's
  flip to `done`. The table goes in the `change` entry and in this spec's Spec Change Log. The stories of Epics 50
  to 52 that cite CAP-43 or CAP-61 (Story 51.1 through FR-12.5, Story 51.2) count or mend what the shipped capability
  already does, so they hold no marker at `ready`; only CAP-46 (Story 51.1 changes what it does) and CAP-62 (Story
  50.3 realizes it) keep `ready`.
- **The groups**, as the memlog decisions state them:
  - CAP-20..CAP-35, CAP-40..CAP-43, CAP-51, CAP-54, CAP-55, CAP-57, CAP-58, CAP-60: `(ready …)` becomes
    `(shipped <date>)`. Text is unchanged, unless a success clause is found unproven; then the capability takes
    `; not met: <clause>, DW-<id>` with a new row.
  - CAP-37 and CAP-48: `(in-progress …)` becomes `(shipped <date>)`.
  - CAP-45 and CAP-49: `(retired 2026-10-15: carried by CAP-61, Story 43.7)`. Intent and success move to the past
    tense and name `pages-build`, `pages-check` and `pages.yml`'s pull-request build as what stands in their place.
  - CAP-44, CAP-52, CAP-53 and CAP-56: intent and success are restated to the live end state, as the decision says,
    and `(ready …)` becomes `(shipped <date>; …)`, the existing tail kept (the 2026-11-11 decision).
  - CAP-36 and CAP-50: `(shipped <date>; not met: a live second run never reports all-unchanged, DW-FU-23-6-1)`.
  - CAP-38 (ruling 4): the route is corrected to `/stations/herald/api/v1/webhooks/on-ship` and `/on-pr-close`, and
    success takes the operator-run form: the endpoint, its HMAC check, and the operator task `herald-ship-local`.
    Marker `(shipped <date>)`, with no not-met qualifier.
  - CAP-39 (ruling 4): success takes the operator-run form. `herald scheduler run` is one cron-shaped pass that the
    operator runs, or schedules with an optional crontab line. Marker `(shipped <date>)`.
  - CAP-61: `(ready 2026-10-14; …)` becomes `(shipped <date>; …existing tail…; not met: /changes/ and /status/runs/
    publish 'input absent', DW-steward-43-6-1)` (the 2026-11-11 decision), and the intent names
    `docs-site/src/lib/herald-pages.ts` and `docs-site/src/lib/agent-surface.ts`.
  - CAP-47 and CAP-59: `(shipped <date>; operator act open, DW-herald-egm-2026-11-01-1)`.
  - CAP-6 (ruling 4): `(retired 2026-11-10: no video was rendered and the extractor is in no tracked path)`. Intent
    and success move to the past tense. The 27 tracked narration extracts and the master script under
    `presentations/*/src/marp/` stay as history.
  - CAP-11 (ruling 4): the cost-derivation clause is struck. Cost and the unblock narrative are operator-entered
    fields of `herald progress --update`. The marker stays `(shipped 2026-09-17)`.
  - CAP-4, CAP-8, CAP-10, CAP-15, CAP-16, CAP-23 and CAP-30: each deck count is dated to its capability's day. One
    sentence in CAP-30 says the live count is whatever `herald deck status` lists (17 directories on 2026-11-10).
  - CAP-1, CAP-26, CAP-41 and CAP-57: the intent names the module that realizes the capability
    (`transport/agent_sdk_transport.py`, `deck_qa.py`, `pptx_pipeline.py`, `pptx_native.py`).
- **Deferred-work ledger.** Rows are written by hand, before the Spec cites them:
  - `DW-herald-50-1-3`: new, low, open; this spec's planned deferral (below), written with its `deferred:` entry.
  - `DW-herald-egm-2026-11-01-1` gains one sentence: 'Re-measured 2026-11-10: snapshot 63 rows (3 stuck, 2
    paused-manually) against 75 registry rows (59 live, 9 retired, 7 opt-in-off); doctor Story 58.4 refreshes it once
    at the head of the cutover-readiness branch (operator ruling 2026-11-10).'
  - `DW-21-7-1` gains one sentence: 'Repo copy re-read clean in the 2026-11-10 audit; Design-side read-back pending
    the operator.' It stays open (ruling 7 of the second addendum).
  - The plan reserved `DW-herald-50-1-1` (the uncalled webhook and the uninstalled schedule) and `DW-herald-50-1-2`
    (the CAP-6 extractor and the CAP-11 cost derivation). Neither is minted, because ruling 4 closed both gaps.

Ledger key: `50-1-every-herald-capability-s-marker-and-text-say-what-is-true`.
Type / Effort / Deps: chore / L / —.

## Boundaries & Constraints

**Always:**
- Memlog first: one `change` entry with the shipped-date table. Then one anchored script render of `SPEC.md`: assert
  each anchor occurs exactly once before replacing it, and assert 62 capability lines in order before and after.
  Then self-validate pass 1 (coherence) and pass 2 (preservation), each logged as a memlog `event`.
- Leave the CAP-46 and CAP-62 blocks exactly as the mint wrote them (they read `ready` until Stories 51.1 and 50.3
  land; Story 50.2 flips them).
- Keep every CAP id, order, title and provenance arrow. A retired name survives only in a sentence that says retired,
  `until <date>`, replaced or no longer.
- Write the deferred-work rows by hand before the Spec cites them.

**Never:**
- Never hand-edit `SPEC.md` with Edit or Write, and never run a bare `--write-baseline`.
- Never build an unmet clause, never add a kill switch, and never write `(unbuilt)`.
- Never write `sprint-status-ledger.yaml`, the PRD, the spine, the brief or `epics.md` (the mint and Story 50.2 own
  them). Never touch the capability ledger's modes (control-plane, steward Stories 121.3 and 121.7).

## Acceptance Criteria

Each verdict is read from the exit code, never through a pipe.

- **AC1 — The mint ran first.** CAP-62 exists, and every new story has its ledger key and its matrix row:
  `grep -c '^- \*\*CAP-62 — ' _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md && pixi run -e pyforge-guild story-status-check && pixi run -e pyforge-guild tea-playwright-check`.
  Expected: prints `1`, then exit 0 twice. A failure blocks the story (status `blocked`, condition: mint incomplete);
  it is never fixed by hand-editing `SPEC.md`.
- **AC2 — Every marker is dated, and none reads in-progress.** Every capability line opens with one dated `ready`,
  `shipped` or `retired` marker, and `ready` survives only where a story is open. Expected: exit 0, printing
  `62 [] ['CAP-46', 'CAP-62']`.

```bash
python3 - <<'EOF'
import re,sys
t=open('_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md').read()
L=re.findall(r'^- \*\*CAP-\d+ — .*$',t,re.M)
bad=[l[:30] for l in L if '(in-progress' in l or not re.search(r'\((shipped|ready|retired) \d{4}-\d{2}-\d{2}[;:)]',l)]
ready=sorted(re.findall(r'^- \*\*(CAP-\d+) — .*\(ready 20',t,re.M))
print(len(L),bad,ready); sys.exit(0 if len(L)==62 and not bad and ready==['CAP-46','CAP-62'] else 1)
EOF
```

- **AC3 — Each block says its own state.** Retired, not-met, operator-open and restated capabilities say so in
  their own block, with the row that tracks them. CAP-11 no longer claims derivation, and CAP-38 and CAP-39 carry no
  not-met qualifier. Expected: exit 0, printing `[]`.

```bash
python3 - <<'EOF'
import re,sys
t=open('_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md').read()
def blk(n):
    return re.search(r'^- \*\*CAP-%d — .*?(?=^- \*\*CAP-|^## )'%n,t,re.M|re.S).group(0)
need={45:['(retired 2026-10-15'],49:['(retired 2026-10-15'],36:['not met','DW-FU-23-6-1'],50:['not met','DW-FU-23-6-1'],38:['/stations/herald/api/v1/webhooks/on-ship','herald-ship-local'],39:['herald scheduler run','crontab'],61:['not met','DW-steward-43-6-1','herald-pages.ts'],47:['operator act open','DW-herald-egm-2026-11-01-1'],59:['operator act open','DW-herald-egm-2026-11-01-1'],6:['(retired 2026-11-10','no tracked path'],11:['herald progress --update'],1:['agent_sdk_transport.py'],26:['deck_qa.py'],41:['pptx_pipeline.py'],57:['pptx_native.py']}
bad=[(n,w) for n,ws in need.items() for w in ws if w not in blk(n)]
bad+=[(n,w) for n,w in ((11,'bmad-loop journals'),(38,'not met'),(39,'not met')) if w in blk(n)]
print(bad); sys.exit(1 if bad else 0)
EOF
```

- **AC4 — No retired artifact reads as live.** No retired artifact is a present-tense condition in the intent or
  success of CAP-44, CAP-45, CAP-46, CAP-49, CAP-52, CAP-53 or CAP-56. Expected: exit 0, printing `[]`. Today it
  lists CAP-44, CAP-45, CAP-49, CAP-52, CAP-53 and CAP-56; the mint already cleared CAP-46.

```bash
python3 - <<'EOF'
import re,sys
t=open('_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md').read()
names=['dashboard.yml','docsite-check.yml','docsite/build.py','site-check','site-verify','site-serve','pages_second_host','with the flag OFF the host inputs','With the flag OFF the host inputs']
ok=re.compile(r'retired|until 20\d\d|no longer|does not exist|replaced')
bad=[]
for n in (44,45,46,49,52,53,56):
    b=re.search(r'^- \*\*CAP-%d — .*?(?=^- \*\*CAP-|^## )'%n,t,re.M|re.S).group(0)
    for line in b.split('\n')[1:]:
        for s in re.split(r'(?<=[.;])\s+',line):
            hit=[x for x in names if x in s]
            if hit and not ok.search(s): bad.append((n,hit,s[:70]))
print(bad); sys.exit(1 if bad else 0)
EOF
```

- **AC5 — The wrong route and the OFF sentence are gone.**
  `git grep -nF -e '/api/herald/webhooks/on-ship' -e 'the flag OFF the host inputs' -- _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md`.
  Expected: exit 1 (no match).
- **AC6 — Every cited row exists.** Every deferred-work id a capability marker cites has a row in herald's or
  steward's tracked ledger. Expected: exit 0, and the second list is `[]`.

```bash
python3 - <<'EOF'
import re,sys
t=open('_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md').read()
rows=set(re.findall(r'^#{2,3} (DW-[\w-]+)',open('_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md').read()+open('_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md').read(),re.M))
cited=set(re.findall(r'DW-[A-Za-z0-9][\w-]*\d',' '.join(re.findall(r'^- \*\*CAP-\d+ — .*$',t,re.M))))
missing=sorted(cited-rows)
print(sorted(cited),missing); sys.exit(1 if missing or not cited else 0)
EOF
```

- **AC7 — The new row and the two appends are in the ledger.**
  `grep -c '^### DW-herald-50-1-3:' …/deferred-work-ledger.md; grep -c 'Re-measured 2026-11-10' …/deferred-work-ledger.md; grep -c 'Repo copy re-read clean in the 2026-11-10 audit' …/deferred-work-ledger.md; pixi run -e pyforge-guild deferred-work-check`
  (`…` is `_bmad-output/projects/pyforge-herald/planning-artifacts`). Expected: prints `1`, `1` and `1`, and the
  detector exits 0.
- **AC8 — The story touched only its files.**
  `git diff --name-only "$STORY_BASE"..HEAD | sort -u`, where `STORY_BASE` is the commit this story's session
  started from. Expected: exactly four paths: `SPEC.md`, `.memlog.md`, `deferred-work-ledger.md` and this story
  spec. `git diff "$STORY_BASE"..HEAD -- …/SPEC.md` shows no edit inside the CAP-46 or CAP-62 blocks.
- **AC9 — The chain detectors hold.**
  `pixi run -e pyforge-guild chain-completeness-check && pixi run -e pyforge-guild status-body-consistency-check`.
  Expected: exit 0.

</intent-contract>

## Binding

- Capabilities: spec-pyforge-herald CAP-1, CAP-4, CAP-6, CAP-8, CAP-10, CAP-11, CAP-15, CAP-16 and CAP-20..CAP-61
  (markers and text only). No CAP is minted, and no FR or AD moves.
- Dream: `docs/dreams/pyforge-herald.md`, Realization log, the 2026-11-10 (cutover readiness) entry. Rulings:
  `docs/dreams/pyforge-unifying-strategy.md`, the three 2026-11-10 entries; for this story, the second addendum's
  rulings 2 (markers) and 4 (CAP-6, CAP-11, CAP-38, CAP-39).
- Epic 50. Ledger key `50-1-every-herald-capability-s-marker-and-text-say-what-is-true`.
- Cross-station: steward:S-120.3 amends CHAIN-STANDARD § 4 to the marker grammar this story writes. Steward:S-121.3
  and steward:S-121.7 set CAP-6's capability-ledger mode to `retire`. This story leaves both to them.
- Findings closed: audit MUST 1, MUST 2; SHOULD: Spec vs code (CAP-11 cost, CAP-6 extractor, deck counts); SHOULD:
  chain (Spec behind its memlog).
- Integration: `capability-ledger-check` exit 0 is judged at steward:S-121.7 (regenerated after every Spec sweep),
  not here; until then new ids read `unclassified` by design. The chain-currency sweep is not this story's check;
  Story 50.2 re-stamps the chain.

## Spec Change Log

- 2026-11-10: minted (backlog) from the station Dream's 2026-11-10 (cutover readiness) entry and the operator's
  rulings of 2026-11-10 ("Accept all, run mint"). Ruling 4 replaced the plan's not-met forms for CAP-6, CAP-11,
  CAP-38 and CAP-39 with retire, strike and the operator-run form. The plan's rows `DW-herald-50-1-1` and
  `DW-herald-50-1-2` are therefore not minted.
- 2026-11-11: the mint's review found that the fourteen decisions left CAP-44, CAP-52, CAP-53, CAP-56 and CAP-61 with
  no instruction to leave `ready`, so a render that followed them would fail AC2. A fifteenth `decision` entry on the
  Spec's memlog gives each a shipped marker; the groups above, the epics.md Story 50.1 block and its reconciliation
  section now say fifteen. AC2 is unchanged.

## Planned deferral (written at build)

The row below is not in the deferred-work ledger yet. This story writes it to
`planning-artifacts/deferred-work-ledger.md`, before its Spec render, and adds it to this spec's `deferred:` frontmatter in the same change,
because `deferred-work-check` refuses a frontmatter deferral with no tracked twin. Station deferred-work rows are
written at build, never at mint.

- **`DW-herald-50-1-3`** (low, open; location `_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md`): 48 open rows of herald's deferred-work ledger carry no severity, so a sweep cannot rank them. The 2026-11-10 cutover readiness audit counted 68 open rows of 113 (1 high, 3 medium, 16 low, 48 unlabelled). Fix: one `bmad-loop sweep` over herald's ledger, which labels each open row or closes it.
