---
title: "51.2: The dossier's cutover claims, herald section and stale prose are true today, and a test resolves each claim"
type: 'docs'
created: '2026-11-10'
status: 'done'
flag-exempt: detector-or-gate   # type docs, as Story 26.1 (the story that first made the dossier the cutover's control plane); the new test judges the content, and a gated gate reports a silent green; the agent-surface edit removes machine keys from published text and adds none
difficulty: heavy
story: '51.2'
spec: pyforge-herald
surface:
  - docs-site/src/content/dossier/dossier.yml
  - src/shared/packages/pyforge-herald/tests/meta/test_dossier_cutover_claims.py
  - docs-site/src/lib/agent-surface.ts
  - src/shared/packages/pyforge-herald/tests/meta/test_agent_surface_and_changes.py
  - docs/map.yaml
  - docs/MAP.md
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml
  - docs/foundry/capability-ledger.yaml
  - src/platform/config/flags.json
  - docs-site/src/content/dossier/dossier.yml
  - src/shared/packages/pyforge-herald/tests/unit/test_dossier_structure.py
  - src/shared/packages/django-herald/src/django_herald_portal/mcp_asgi.py
warnings: [oversized]
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-52.1).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).
>
> **Unblocked 2026-11-13.** Every story its Deps name is `done` on branch `cutover-readiness-2026-11-10`. The operator's "Start build" consent covered the unblock; CLOSE-LEDGERS moved the key to `done`.

<intent-contract>

## Intent

**Problem:** The dossier is the cutover state `AGENTS.md` points every reader to. On this branch its A→B text is
false since `a1b7d6fcdc`: it says 44.4 to 44.6 are "parked at backlog", but they are `blocked`. It also predates the
2026-11-10 rulings and says B is rebuilt from Frame + Spec. Its herald section misstates the code: it lists 8 of 12
deck verbs and says there is "no MCP server code at all". Steward's duty count ("15") is stale in four prose places,
one line names the dead path `site/tools/verify_claims.py`, and nothing checks a row against the steward ledger (audit
MUST 7; SHOULD: A→B claims, weak evidence, re-verification). This is a content fix plus the test that keeps it fixed;
no product behaviour changes.

**Approach:** Content comes from the tree and from the 2026-11-10 entries of
`docs/dreams/pyforge-unifying-strategy.md`, never from the plan.

- **Scope in `dossier.yml`** is everything Story 51.1 did not touch: the A→B rows, the header comment, `eyebrow`,
  `summary`, the `estate` and `verified` sections, the `herald` section's prose and finding, the four steward duty
  statements, § 09.3, the § 09.6 Shape column, § 09.7 and `footer`.
- **The rulings on the page:**
  - A writes every Dream, Frame, Spec and the capability ledger until the flip, and the flag is the writer lock. B
    reads A at a pinned SHA. B's three kernel leaves are a prototype at PR #1344 (2026-09-14); § 10 rows 2 to 4 say
    they passed their slices then and were not re-pinned.
  - The seed is Dream plus memlog, and a Frame is a pointer, not a seed: no line says B is rebuilt from Frame and
    Spec (today lines 12-13, 87-88, 102, 130 and 211).
  - Launch is a self-hosting slice. 44.4, 44.5 and 44.6 retired as 44.10 did (`blocked`, never dispatched).
  - 'Adopt Frames' holds on A only.
  - The BMAD-suite row reads "not established" until control-plane's re-derived `fnd:CAP-14` names the story that
    re-provisioned from the adoption register (Epic 60 is the estate catalog). It is never defaulted to Done.
  - Ruling 3's ledger rule is phrased without the word 'archived' (for example "rows whose Spec folder moved to the
    archive home leave the ledger"), because `test_dossier_structure.py:141-143` reds on an unnegated 'archived' in
    the estate section.
- **The flip trigger (ruling 1 of the second addendum).** The A→B table's `pyforge.cutover_root` row (`dossier.yml:118`
  today reads `foundry — only after the case list passes and an operator flips it`) states the ruled trigger. The
  operator flips it by hand, with no loop running, once the Launch slice is proven: B lands one story on itself
  through its own dispatch and its own detectors, and every Launch row of the case list reads `verified-in-foundry`.
  Nothing flips it automatically.
- **Asserts.** Every row of A→B.3, each body line of the Operator watch callout and each § 10 row carries `asserts:`.
  It is a list from a closed grammar that the test resolves as data:
  - `story:<station>/<E>-<S>=<status>` and `epic:<station>/<E>=<status>`, against that station's tracked
    `sprint-status-ledger.yaml`;
  - `flag:pyforge.cutover_root=<variant>`, against `src/platform/config/flags.json`;
  - `ledger:mode:<mode>=<n>` (used as `ledger:mode:move=0`) and `ledger:claim:verified-in-foundry=<n>`, against
    `docs/foundry/capability-ledger.yaml`;
  - `ledger:claim-field=absent|present`.
- **The claim field.** The capability ledger has no claim or state field today, so a claim count is unresolvable,
  never 0. The row that says nothing is recorded as in effect on B carries `ledger:claim-field=absent`. That turns red
  the day control-plane lands the field, which forces the row to be restated with a real count. The resolver's one
  constant is `claim`, the word the ledger's own header comment uses, until control-plane names the field.
- **Text and date rules.**
  - A story number or `Epic <n>` named in a row's text has an assert in that row; a range such as 44.4–44.6 needs one
    per story.
  - The eyebrow date, `estate.measured`, `verified.measured` and `footer.date` are equal.
  - `footer.note` says what each date means: the control plane and § 10 as of that day; each station section the day
    its prose was last read; every band and scale-table figure counted at build.
- **Herald section**, rewritten from the code, with `measured:` set to the day of the re-read: 5 top-level commands;
  a `chips` block with the 12 deck verbs; the finding becomes "the MCP face lives in django-herald
  (`POST /stations/herald/mcp`: start_notice, get_notice; steward Epic 119), not in the base package".
- **Steward and § 09.**
  - The duty statements at `:884`, `:1098` and `:1271` become dated history or lose the number ("15 on 2026-10-14;
    `pyforge steward --help` lists today's"). The steward section keeps `measured: 2026-10-14`: the re-read scope is the
    plan's default, as ruled on 2026-11-10.
  - § 09.3's last sentence names `docs-site/scripts/verify_claims.py` and what it does now.
  - § 09.7 gains one sentence: from 2026-11-10 the bands and the scale table are counted at every build.
- **Agent surface.** `asserts`, `check`, `source` and `section` join `NON_TEXT_KEYS` in
  `docs-site/src/lib/agent-surface.ts`, so `/llms-full.txt` publishes no machine key.
- **The new test** is a `live_tree` module from birth (Story 52.1 registers the marker).
- **`docs/map.yaml` and `docs/MAP.md`.** Herald plans no row of its own. This story is where another unit's request
  for a docs page row lands, written after doctor:S-56.5's stamp edit; `pixi run -e pyforge-guild docs-map-render`
  regenerates `MAP.md`.

Ledger key: `51-2-the-dossier-s-cutover-claims-herald-section-and-stale-prose-are-true-today-and-a-test-resolves-each-claim`.
Type / Effort / Deps: docs (`flag-exempt: detector-or-gate`) / L / S-51.1, S-52.1 (and doctor:S-56.5, steward:S-124.1).

## Boundaries & Constraints

**Always:**
- Build after control-plane's ledger and Epic 44 edits are on the integration branch. If they land later, the test
  reds on the row that moved, which is its job.
- Resolve every assert as data from tracked files: no `gh`, no `pyforge.steward` import, no network.
- Edit content only. `test_dossier_structure.py` passes unedited.

**Never:**
- Never name another flip trigger, and never say B is rebuilt from Frame and Spec.
- Never default a not-established row to Done, and never re-date the steward section without a full re-read.
- Never append a `Surface reconcile` line to another Spec's memlog, and never run `spec_surface_check.py
  --write-baseline`. Each Spec's closer writes its own event (herald 50.2; doctor 57.3 and 58.4 for `docs/map.yaml`),
  and doctor:S-58.4 stamps once.

## Acceptance Criteria

Each verdict is read from the exit code, never through a pipe.

- **AC1 — Every A→B claim resolves, and the structure rules hold.**
  `pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/meta/test_dossier_cutover_claims.py src/shared/packages/pyforge-herald/tests/unit/test_dossier_structure.py -q`.
  Expected: exit 0, with `test_dossier_structure.py` not edited.
- **AC2 — The test reds on a false, unasserted or unresolvable claim.** Its own negative cases run over fixture
  ledgers and a fixture flag tree:
  `pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/meta/test_dossier_cutover_claims.py -q -k planted`.
  Expected: exit 0, with at least 8 tests selected. Each of these is named:
  - `story:steward/44-4=backlog` is named false;
  - a row whose text names Story 44.9 without an assert is named;
  - a row in A→B.3 with no `asserts:` is named;
  - `flag:pyforge.cutover_root=foundry` is named false;
  - an eyebrow date that differs from the estate section's `measured:` is named;
  - on a fixture ledger with one row claiming `verified-in-foundry`, `ledger:claim:verified-in-foundry=0` is named
    false;
  - on a fixture ledger with no claim field, the same assert is named unresolvable, never true;
  - `ledger:claim-field=absent` is named false once a row carries the field.
- **AC3 — The pre-ruling wording is gone.** Phrases are matched in the parsed YAML with whitespace collapsed, because
  the file wraps prose across lines. Expected: exit 0, printing `[]`. On 2026-11-10 it exits 1 with 8 hits.

```bash
python3 - <<'EOF'
import yaml,sys
out=[]
def walk(x,p=''):
    if isinstance(x,dict):
        for k,v in x.items(): walk(v,p+'/'+str(k))
    elif isinstance(x,list):
        for i,v in enumerate(x): walk(v,p+'/%d'%i)
    elif isinstance(x,str): out.append((p,' '.join(x.split())))
walk(yaml.safe_load(open('docs-site/src/content/dossier/dossier.yml')))
hits=[(ph,p) for ph in ['parked at backlog','State, 2026-10-14','CUTOVER — 2026-10-14','file-move stories','re-verified against the working tree on the date shown'] for p,s in out if ph in s]
raw=open('docs-site/src/content/dossier/dossier.yml').read()
hits+=[(ph,'raw') for ph in ['Prose re-verified against the working tree 2026-10-14'] if ph in raw]
print(hits); sys.exit(1 if hits else 0)
EOF
```

- **AC4 — The rulings are on the page.** Run `grep -c` on `docs-site/src/content/dossier/dossier.yml` for each of
  `'writer lock'`, `'self-hosting slice'` and `'PR #1344'`. Expected: three counts, each at least 1.
- **AC5 — The stale herald, steward and synthesis claims are gone.** They are matched in the parsed YAML, so phrases
  that wrap across lines are caught. Expected: exit 0, printing `[]`. On 2026-11-10 it exits 1 with 7 hits.

```bash
python3 - <<'EOF'
import yaml,sys
out=[]
def walk(x,p=''):
    if isinstance(x,dict):
        for k,v in x.items(): walk(v,p+'/'+str(k))
    elif isinstance(x,list):
        for i,v in enumerate(x): walk(v,p+'/%d'%i)
    elif isinstance(x,str): out.append((p,' '.join(x.split())))
walk(yaml.safe_load(open('docs-site/src/content/dossier/dossier.yml')))
hits=[(ph,p) for ph in ['15 duties','Fifteen "duties','there are now 15','fails loudly when a stated figure drifts','site/tools/verify_claims.py','no MCP server code at all','did not locate',"didn't locate"] for p,s in out if ph in s]
print(hits); sys.exit(1 if hits else 0)
EOF
```

- **AC6 — The herald section matches the code.** It lists the deck verbs the parser has and names the MCP tools the
  portal defines:
  `pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/meta/test_dossier_cutover_claims.py -q -k herald_section`.
  Expected: exit 0. The section's `chips` block equals the deck parser's choices (12 today), and its text names the
  two tool constants of `django_herald_portal/mcp_asgi.py` (`start_notice`, `get_notice`).
- **AC7 — No scale-table Shape cell carries a figure.** Expected: exit 0, printing `[]`.

```bash
python3 - <<'EOF'
import yaml,re,sys
d=yaml.safe_load(open('docs-site/src/content/dossier/dossier.yml'))
bad=[r['cells'][0] for s in d['sections'] for b in s.get('blocks',[]) if b['type']=='table' and b.get('headers',[])[:2]==['Station','Source lines'] for r in b['rows'] if re.search(r'\d',r['cells'][3])]
print(bad); sys.exit(1 if bad else 0)
EOF
```

- **AC8 — The published agent surface carries no machine key.**
  `HERALD_DOCS_SITE_REQUIRED=1 pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/meta/test_agent_surface_and_changes.py -q -k machine_keys`.
  Expected: exit 0. The built `/llms-full.txt` holds no `story:steward/` string, no `flag:pyforge.cutover_root=`
  string, and no line that is only a check key.
- **AC9 — The docs registry and its render are current.**
  `pixi run -e pyforge-guild docs-map-hygiene-check && pixi run -e pyforge-guild docs-currency-check`. Expected: exit
  0. Both files are untouched unless another unit asked for a row.
- **AC10 — The site builds, and the built-site suite holds.**
  `pixi run -e site pages-check && HERALD_DOCS_SITE_REQUIRED=1 pixi run -e pyforge-herald pyforge-herald-test-built`.
  Expected: exit 0.
- **AC11 — Post-condition, run by steward:S-124.2.**
  `pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q`.
  Expected: exit 0 once steward-station has added the station sprint ledgers to herald's trigger paths. Before that
  it fails by design.
- **AC12 — No dossier line says B is rebuilt from Frame and Spec.** Phrases are matched, case-insensitively, in the
  parsed YAML and in the comment lines, each with whitespace collapsed, because the file wraps prose across lines.
  Expected: exit 0, printing `[]`. On 2026-11-10 it exits 1 with 5 hits.

```bash
python3 - <<'EOF'
import yaml,sys
out=[]
def walk(x,p=''):
    if isinstance(x,dict):
        for k,v in x.items(): walk(v,p+'/'+str(k))
    elif isinstance(x,list):
        for i,v in enumerate(x): walk(v,p+'/%d'%i)
    elif isinstance(x,str): out.append((p,' '.join(x.split()).lower()))
raw=open('docs-site/src/content/dossier/dossier.yml').read()
walk(yaml.safe_load(raw))
out.append(('#comments',' '.join(' '.join(l.strip()[1:] for l in raw.split('\n') if l.strip().startswith('#')).split()).lower()))
hits=[(ph,p) for ph in ['from frame + spec','from frame and spec'] for p,s in out if ph in s]
print(hits); sys.exit(1 if hits else 0)
EOF
```

- **AC13 — The dossier states the ruled flip trigger and no other.** The same parsed-YAML walk, whitespace collapsed:
  'Nothing flips it automatically' is found at least once, and neither retired trigger phrase is found. Expected:
  exit 0, printing a count of at least `1` and `[]`. On 2026-11-10 it exits 1, printing `0` and one hit.

```bash
python3 - <<'EOF'
import yaml,sys
out=[]
def walk(x,p=''):
    if isinstance(x,dict):
        for k,v in x.items(): walk(v,p+'/'+str(k))
    elif isinstance(x,list):
        for i,v in enumerate(x): walk(v,p+'/%d'%i)
    elif isinstance(x,str): out.append((p,' '.join(x.split())))
walk(yaml.safe_load(open('docs-site/src/content/dossier/dossier.yml')))
n=sum(1 for p,s in out if 'Nothing flips it automatically' in s)
old=[(ph,p) for ph in ["triggers the flip is the operator's to name",'only after the case list passes'] for p,s in out if ph in s]
print(n,old); sys.exit(0 if n>=1 and not old else 1)
EOF
```

</intent-contract>

## Binding

- No CAP is minted and no FR or AD moves. The content serves `spec-python-foundry-cutover:CAP-14` (the dossier states
  the cutover's control plane; herald Epic 26) and spec-pyforge-herald CAP-43 and CAP-61 (the dossier as the one
  source, one generator).
- Dream: `docs/dreams/pyforge-herald.md`, the 2026-11-10 (cutover readiness) entry. Rulings:
  `docs/dreams/pyforge-unifying-strategy.md`, the 2026-11-10 entry (rulings 1 to 4), its addendum and its second
  addendum (ruling 1: the flip trigger).
- Epic 51. Ledger key
  `51-2-the-dossier-s-cutover-claims-herald-section-and-stale-prose-are-true-today-and-a-test-resolves-each-claim`.
- Cross-station: doctor:S-56.5 (`docs/map.yaml` is written after its stamp edit) and steward:S-124.1 (the suites'
  two task halves) are gates held by the single PR's integration order. Steward:S-124.2 is a post-condition.
  Control-plane (steward:S-120.3, steward:S-121.7) names the capability ledger's claim field. Scribe's request lands
  here: the Frame + Spec lines state the ruled seed.
- Findings closed: MUST 7; SHOULD: dossier A→B claims true today; SHOULD: weak evidence behind true claims; SHOULD:
  re-verification.

## Spec Change Log

- 2026-11-10: minted (backlog). Ruling 1 of the second addendum replaced the plan's "what event triggers the flip is
  the operator's to name" with the ruled trigger, and AC13 checks for it. The operator's acceptance of every
  recommendation in the same addendum kept the plan's default re-read scope.
- 2026-11-10: status set to blocked (forward dependency on a later epic; unblocked only with operator confirmation).
