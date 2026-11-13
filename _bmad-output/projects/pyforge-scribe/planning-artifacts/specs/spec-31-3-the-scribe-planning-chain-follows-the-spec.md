---
title: '31.3: The scribe planning chain follows the Spec'
type: 'docs'
created: '2026-11-10'
status: 'done'
difficulty: 'medium'
story: 31-3-the-scribe-planning-chain-follows-the-spec
spec: spec-pyforge-scribe
surface:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/briefs/brief-pyforge-scribe-2026-07-25/brief.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/prds/prd-pyforge-scribe-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/architecture/architecture-pyforge-scribe-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-scribe.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/retros/retro-pyforge-scribe-2026-11-*.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/implementation-readiness-report-2026-11-*.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-31-3-the-scribe-planning-chain-follows-the-spec.md
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
  - _bmad-output/projects/pyforge-doctor/CHAIN-CURRENCY-RUNBOOK.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - scripts/fleet_scan.py
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The chain-currency edges this change opens stay red until the planning chain follows the re-derived
Spec (audit SHOULD S5): the research stage is already 2026-11-10 against a brief of 2026-11-05, Stories 33.1 and
33.2 move the code stage past the newest retro, and the PRD, spine and epics carry the three-command claim, a 3.12
floor, an unqualified FR-45 and an input document that does not exist.

**Approach:** Planning files only, in an order that satisfies each feed edge as it is written:

1. `brief.md`: re-stamped for `research/cutover-readiness-audit-2026-11-10.md`, with a § *Currency reconciliation*
   paragraph (problem, users and scope unchanged).
2. `prd.md`: FR-14 follows CAP-4 (five command groups), FR-16 follows CAP-27; FR-51 to FR-54, registered at the mint,
   are checked against the re-derived capabilities (FR-52 stays marked retired with CAP-34); the reconciliation
   section says what moved.
3. The spine: AD-3's wording follows the nested schema; the Stack row reads `python >=3.14`; no AD is added.
4. `epics.md`: both FR-45 lines read `canopy:FR-45` (the Epic 4 intro and Story 4.1's FR/AD field);
   `inputDocuments` names `archive/docs/specs/claude-team-memory.md`; a dated currency note.
5. A retro, `retros/retro-pyforge-scribe-<date>.md`, for Epics 31 to 33, dated on or after the last commit of the
   package `pyproject.toml` (the code stage, which Stories 33.1 and 33.2 move).
6. `deferred-work-ledger.md`: the rows the operator rulings of 2026-11-10 leave open, with their ids as the plan
   numbered them: DW-scribe-cutover-2026-11-10-1 (`scribe capture --supersedes` stays library-only; the row holds
   the ask for a later Dream entry), -2 (five tests run in no lane), -3 (the PRD traces 9 of 35 capabilities), -4 (no
   scheduled re-derive comparison), -5 (`scribe index move-list` and its half of `index refresh` are retired with
   CAP-34; a Story removes them), -7 (a contract change hidden in a bookkeeping event), -10
   (`spec-pyforge-unifying-strategy:CAP-14` does not name the four changesets). Rows -6, -8 and -9 are not written:
   the rulings closed them (the seed includes `archive/**/.memlog.md`, no backfill; steward Story 120.3 re-derives
   both Guild Specs; Story 32.2 moves the approved records). DW-8-1-2 gains an evidence line (the primary checkout's
   `graph.json` dated 2026-11-06 at the audit), and DW-scribe-egm-2026-11-05-3 closes citing Story 32.1.
7. The Dream's Realization log gains the closing line of the 2026-11-10 entry, naming Epics 31 to 33.

The PRD and the spine each have a `.memlog.md` from the 2026-07-25 authoring session that no re-stamp has appended
to, so this story does not either: a re-stamp is recorded in the artifact's `updated:` comment and its
reconciliation section.

Ledger key: `31-3-the-scribe-planning-chain-follows-the-spec`. Type / Effort / Deps: docs / M / 31.2.

### Living CAP citations

- `spec-pyforge-scribe` CAP-4, CAP-27 and CAP-33..CAP-35 (FR-14, FR-16, FR-51..FR-54); no AD moves.

## Boundaries & Constraints

**Always:**
- Brief, PRD, spine, epics, in that order, each dated no earlier than the package manifest's last commit (the Dream
  is `specified`, so the behind-code rule applies, `scripts/fleet_scan.py`).
- Read each detector from its exit code, never through a pipe.

**Never:**
- Do not re-derive the Spec here; Story 31.2 did.
- Do not append a `Surface reconcile` line to another Spec's memlog or run `spec_surface_check.py --write-baseline`:
  scribe's closer, Story 31.4, writes scribe's reconcile, and doctor:S-58.4 runs every scoped stamp once.

</intent-contract>

## Acceptance Criteria

- **AC1 — The stage dates are in order and none is older than the package manifest's last change.**
  `python3 -c "import re,sys,subprocess,glob;u=lambda p:re.search(r'^updated:\s*[\'\"]?(\d{4}-\d{2}-\d{2})',open(p).read(),re.M).group(1);b,p,s,a,e=[u(x) for x in ('_bmad-output/projects/pyforge-scribe/planning-artifacts/briefs/brief-pyforge-scribe-2026-07-25/brief.md','_bmad-output/projects/pyforge-scribe/planning-artifacts/prds/prd-pyforge-scribe-2026-07-25/prd.md','_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md','_bmad-output/projects/pyforge-scribe/planning-artifacts/architecture/architecture-pyforge-scribe-2026-07-25/ARCHITECTURE-SPINE.md','_bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md')];r=max(u(x) for x in glob.glob('_bmad-output/projects/pyforge-scribe/planning-artifacts/retros/retro-pyforge-scribe-2026-11-*.md'));c=subprocess.run(['git','log','-1','--format=%cs','--','src/shared/packages/pyforge-scribe/pyproject.toml'],capture_output=True,text=True).stdout.strip();print(b,p,s,a,e,r,c);sys.exit(0 if '2026-11-10'<=b<=p<=a<=e and s<=p and min(s,p,a,r)>=c else 1)"` exits 0.
- **AC2 — The three-command claim is gone from the PRD.**
  `grep -c -e 'three top-level commands' -e 'three independently invocable' _bmad-output/projects/pyforge-scribe/planning-artifacts/prds/prd-pyforge-scribe-2026-07-25/prd.md` prints 0.
- **AC3 — FR-51 to FR-54 each stand once with an arrow to a defined capability.**
  `python3 -c "import re,sys;p=open('_bmad-output/projects/pyforge-scribe/planning-artifacts/prds/prd-pyforge-scribe-2026-07-25/prd.md').read();s=open('_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md').read();want={51:33,52:34,53:35,54:4};ok=all(len(re.findall(r'^#### FR-%d: .* ← CAP-%d\b'%(f,c),p,re.M))==1 and re.search(r'^- \*\*CAP-%d '%c,s,re.M) for f,c in want.items());sys.exit(0 if ok else 1)"` exits 0.
- **AC4 — The spine states the 3.14 floor.**
  `grep -c 'member-package floor) | `>=3.12`' _bmad-output/projects/pyforge-scribe/planning-artifacts/architecture/architecture-pyforge-scribe-2026-07-25/ARCHITECTURE-SPINE.md` prints 0.
- **AC5 — Every FR-45 in epics.md is canopy's, qualified.**
  `python3 -c "import sys;t=open('_bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md').read();sys.exit(0 if t.count('FR-45')==t.count('canopy:FR-45')>=2 else 1)"` exits 0.
- **AC6 — epics.md names an input document that exists.**
  `grep -c '^  - docs/specs/claude-team-memory.md' _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md` prints 0.
- **AC7 — The deferred rows the rulings leave open are written.**
  `grep -c '^### DW-scribe-cutover-2026-11-10-' _bmad-output/projects/pyforge-scribe/planning-artifacts/deferred-work-ledger.md` prints 7.
- **AC8 — The Dream's Realization log closes the entry.** `grep -c 'Epics 31' docs/dreams/pyforge-scribe.md` prints 2
  or more (the mint entry and the closing line).
- **AC9 — The planning detectors name no scribe finding.**
  `D=$(mktemp -d) && for s in fr-without-cap chain-completeness dream-chain dreams-hygiene deferred-work; do pixi run -q --frozen -e pyforge-guild python -m pyforge.doctor.sources $s --json > "$D/$s.json" || true; done; python3 -c "import json,sys,glob;bad=[f for p in glob.glob(sys.argv[1]+'/*.json') for f in json.load(open(p)) if 'pyforge-scribe' in json.dumps(f) and f.get('status') in ('fail','warn')];print(len(bad));sys.exit(1 if bad else 0)" "$D"`
  prints 0 and exits 0.
- **AC10 — Citations resolve.** `pixi run --frozen -e pyforge-guild ad-citation-check` exits 0.
- **AC11 — The readiness gate is fresh.** `ls _bmad-output/projects/pyforge-scribe/planning-artifacts/implementation-readiness-report-2026-1*.md` lists one file or more.
- **AC12 — Scribe's chain is current.** `pixi run --frozen -e pyforge-guild chain-currency-sweep-check -- --project pyforge-scribe` exits 0 (1 is a finding, 2 could not run; read from the exit code).

## Binding

- Parent capabilities: `spec-pyforge-scribe` CAP-4, CAP-27, CAP-33..CAP-35; no AD moves.
- Dream: `docs/dreams/pyforge-scribe.md` § Realization log, the 2026-11-10 (cutover readiness) entry.
- Epic: Epic 31. Ledger key `31-3-the-scribe-planning-chain-follows-the-spec`, minted `backlog`.
- Deps: 31.2. Wave BUILD-4. Chain close for pyforge-scribe: this story's re-stamp; Story 31.4 later appends only a
  `Surface reconcile` event (bookkeeping), so the Spec date does not move after it.

## Notes

- Closes audit SHOULD S5 (PRD and epics).
- AC9 reads each detector's JSON for scribe's own findings only; other stations' half-built state on the integration
  branch is theirs.

## Spec Change Log

- 2026-11-10: minted with Epic 31 at the cutover-readiness mint; AC7 counts seven rows, not the plan's ten, because
  the operator rulings of 2026-11-10 closed rows -6, -8 and -9. AC9 counts only `fail` and `warn` findings: the
  plan's form counted every finding naming `pyforge-scribe`, and `fr-without-cap`'s `ok` summary names every
  station in its counts, so it could never print 0 (measured at the mint).
