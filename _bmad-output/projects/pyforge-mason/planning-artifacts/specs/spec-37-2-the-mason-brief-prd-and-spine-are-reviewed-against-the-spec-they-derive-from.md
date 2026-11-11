---
title: "37.2: The mason brief, PRD and spine are reviewed against the Spec they derive from"
type: 'chore'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/briefs/brief-pyforge-mason-2026-07-25/brief.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - scripts/fleet_scan.py
surface:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/briefs/brief-pyforge-mason-2026-07-25/brief.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/implementation-readiness-report-2026-11-*.md
deferred: []
---

<intent-contract>

## Intent

**Problem:** The PRD and the spine were re-stamped on 2026-11-05 but last reviewed on 2026-09-14 and 2026-09-17, before CAP-28..CAP-35; they still state a 3.12 floor and six knobs. The research stage moved on 2026-11-10 past the brief by more than the two-day grace, and the readiness gate (2026-08-10, no frontmatter) passed its 90-day shelf on 2026-11-08, so the chain-currency sweep reds mason. CAP-27 and CAP-28 are rebuild capabilities with no requirement.

**Approach:**
- Edit and stamp in feed order, each `updated:` on or after the one above it: brief, PRD, spine, epics.
- **Brief:** a `currency_review:` line (reviewed against the 2026-11-10 audit; its problem and users stand); `dream:` to `archive/docs/dreams/packaging-factory.md` and `adopted_kernel:` to the archived `spec-packaging-factory` path; no body change unless the review finds one.
- **PRD:** FR-58 to FR-64 were written at mint (CHAIN-STANDARD § 3 step 3; § Currency reconciliation — 2026-11-10). Trace each against its capability's intent and success as Story 37.1 finally words it (FR-58 native-only). Amend FR-48 (six global knobs with a flag and a variable each, plus the two environment-only factory-island variables, citing CAP-36), NFR-11 and D-6 (floor 3.14), restate `frCount` (64), and add a dated retirement note to the Presenton satellite section. One sentence says why the retired capabilities and the A-only CAP-18..CAP-26 carry no requirement: an A-only capability's FR is written when it is rebuilt.
- **Spine:** one `Currency reconciliation — 2026-11-1x` section in the established shape; `binds:` FR-1..FR-64; the stack row to 3.14; AD-13 notes the two environment-only variables; AD-16 is amended for the two halves (relay of spec-pyforge-steward:CAP-175, ruling D4); two new decisions, numbered from the spine's next free id, record the factory-island resolution (a second pure chain with no flag form, native build only) and the contract companion with its meta-test.
- **Epics:** the frontmatter counts and currency line and a dated validation note only; headings and stories are the mint's.
- **Readiness gate:** `bmad-sprint-planning`'s check implementation readiness, run after these edits; a point-in-time report, never hand-written.

Ledger key: `37-2-the-mason-brief-prd-and-spine-are-reviewed-against-the-spec-they-derive-from`.
Ledger status: `backlog`.
Type / Effort / Deps: chore / L / S-37.1, S-37.3.

### Living CAP citations

- **CAP-27** (FR-63) and **CAP-28** (FR-64): the backfill for the two rebuild capabilities no requirement cited.
- FR-58 to FR-62 reviewed against **CAP-36**, **CAP-37**, **CAP-5** and **CAP-7**.
- Decision D6 (floor 3.14); spec-pyforge-steward:CAP-175 (the two halves).

## Boundaries & Constraints

**Always:**
- Stamp in feed order.
- Trace each arrow from its capability's intent and success; never number in sequence.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never build beside Story 33.2: it edits the same `prd.md` (its 16 NFR arrows stay with it).
- Never touch `docs/governance/fr-baseline.json`.
- Never hand-edit a `SPEC.md` or `sprint-status-ledger.yaml`.
- Never append a `Surface reconcile` line to another Spec's memlog and never run `spec_surface_check.py --write-baseline`: Story 37.4 writes mason's reconcile event, each other Spec's closer writes its own, and doctor Story 58.4 runs every scoped stamp once, after the last edit (cutover readiness plan, integration 2026-11-10).

## Acceptance Criteria

**AC1 — FR-58..FR-64 are each defined once with an arrow.**

```bash
python3 -c "import re,sys; t=open('_bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md',encoding='utf-8').read(); ok=all(len(re.findall(r'^#### FR-%d: .* \u2190 .*CAP-\d+' % n, t, re.M))==1 for n in range(58,65)); sys.exit(0 if ok else 1)"
```

Expect: exit 0.

**AC2 — Every requirement cites a defined capability.**

```bash
pixi run -e pyforge-guild fr-without-cap-check; echo $?
```

Expect: 0.

**AC3 — The PRD's floor requirement reads 3.14.**

```bash
grep -cE '^- \*\*NFR-11 \(Python floor\)\.\*\* `requires-python >= 3\.14`' _bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md
```

Expect: prints 1.

**AC4 — The spine's stack row reads 3.14.**

```bash
grep -cE '^\| Python \| `>=3\.14`' _bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md
```

Expect: prints 1.

**AC5 — The spine carries the decisions this change made.**

```bash
grep -cE '^### AD-(27|28) — ' _bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md; grep -c 'live_tree' _bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md
```

Expect: prints 2, then 1 or more.

**AC6 — Brief, PRD and spine each record a review, not a re-stamp.**

```bash
grep -cE '^currency_review: "Reviewed 2026-11-1[0-9]' _bmad-output/projects/pyforge-mason/planning-artifacts/briefs/brief-pyforge-mason-2026-07-25/brief.md _bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md _bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md
```

Expect: each file prints 1.

**AC7 — The brief's stale source paths resolve.**

```bash
python3 -c "import yaml,os,sys; fm=yaml.safe_load(open('_bmad-output/projects/pyforge-mason/planning-artifacts/briefs/brief-pyforge-mason-2026-07-25/brief.md',encoding='utf-8').read().split('---')[1]); sys.exit(0 if os.path.isfile(fm['dream']) and os.path.isfile(fm['adopted_kernel']) else 1)"
```

Expect: exit 0 (exit 1 today: docs/dreams/packaging-factory.md and _bmad-output/projects/local-recipes/... moved to archive/).

**AC8 — The chain's dates are in feed order up to the epics.**

```bash
python3 -c "import re,sys; g=lambda p: re.search(r'^updated:\s*[\x22\x27]?(\d{4}-\d{2}-\d{2})', open(p,encoding='utf-8').read().split('\n---',1)[0], re.M).group(1); d=[g(p) for p in ('_bmad-output/projects/pyforge-mason/planning-artifacts/briefs/brief-pyforge-mason-2026-07-25/brief.md','_bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md','_bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md','_bmad-output/projects/pyforge-mason/planning-artifacts/epics.md')]; sys.exit(0 if d==sorted(d) and d[0]>='2026-11-10' else 1)"
```

Expect: exit 0: brief <= PRD <= spine <= epics, all on or after 2026-11-10.

**AC9 — A readiness gate dated this change exists and passes.**

```bash
ls _bmad-output/projects/pyforge-mason/planning-artifacts/implementation-readiness-report-2026-11-*.md && grep -ciE 'overall.*(ready|pass)' _bmad-output/projects/pyforge-mason/planning-artifacts/implementation-readiness-report-2026-11-*.md
```

Expect: one file, written by `bmad-sprint-planning` (check implementation readiness) over the PRD, spine and epics after this story's edits; prints 1 or more.

**AC10 — The epics frontmatter counts equal the headings.**

```bash
python3 -c "import re,sys,yaml; t=open('_bmad-output/projects/pyforge-mason/planning-artifacts/epics.md',encoding='utf-8').read(); fm=yaml.safe_load(t.split('---')[1]); s=len(re.findall(r'^### Story \d+\.\d+:',t,re.M)); e=len(re.findall(r'^## Epic \d+:',t,re.M)); sys.exit(0 if (fm['storyCount'],fm['epicCount'])==(s,e)==(138,39) else 1)"
```

Expect: exit 0 (129 stories and 36 epics before this change; 9 and 3 minted).

**AC11 — Ledger, story and citation detectors.**

```bash
pixi run -e pyforge-guild story-status-check; echo $?; pixi run -e pyforge-guild ledger-regression-check; echo $?; pixi run -e pyforge-guild ad-citation-check; echo $?
```

Expect: 0, 0 and 0.

*Mint adjustment (2026-11-10):* AC1's range is corrected to FR-58..FR-64 (the plan's `range(59,66)` read FR-59..FR-65; FR-65 is the next free id, not a requirement of this change).

</intent-contract>

## Binding

- Parent: `spec-pyforge-mason`.
- Requirements: FR-63 ← CAP-27, FR-64 ← CAP-28.
- Dream: `docs/dreams/pyforge-mason.md`, Realization log, *2026-11-10 (the cutover readiness audit)*.
- Epic 37, `### Story 37.2: The mason brief, PRD and spine are reviewed against the Spec they derive from` in `planning-artifacts/epics.md`.
- Wave: BUILD-3 (cutover readiness plan).
- Findings closed: SHOULD: chain currency (PRD and spine re-stamps, NFR arrows); SHOULD: `spec-pyforge-mason:CAP-8` to CAP-28 have no FR; SHOULD: Python floor.

## Notes

- The chain-currency sweep is judged once, at Story 37.4, after the retro.

## Planned deferral (written at build)

- **spec-pyforge-mason's `companions:` comments trail the reviewed chain** (severity: low). `SPEC.md`'s frontmatter
  comments read `FR-1..FR-50 / NFR-1..NFR-16 / D-1..D-13` for the PRD and `AD-1..AD-16 + AD-25/AD-26; Presenton
  AD-17..AD-24` for the spine; after this review the PRD holds FR-1..FR-64 and the spine adds AD-27 and AD-28.
  Location: `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md` (`companions:`).
  This story may not edit `SPEC.md` (memlog entry and anchored render only, Story 37.1's), and no capability text,
  surface or acceptance criterion depends on the comments. Fix: the next re-derive of `spec-pyforge-mason` restates
  both ranges. Story 37.4 writes the ledger row (the station closer, per the build rules).
