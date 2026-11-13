---
title: "25.4: Every open warden deferral is re-verified and carries a severity and an owner"
type: 'chore'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: 'medium'
story: '25.4'
spec: _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
surface:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
  - docs/dreams/pyforge-unifying-strategy.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The control plane must tell the truth, and the deferred-work ledger is part of it: 55 of its 70 rows read open, 40 of them legacy rows with no severity, and no row was re-verified after the 2026-09-02 pass.

**Approach:** Re-read each open row against the tree at the branch head and append one `verified: 2026-11-<day> - <still-open|done> - <command or path:line>` line; a closed row gets `status: done <date>` with that evidence. Add severity and owner where a legacy row has none. Never edit a row's id, `summary:` or `location:` (the intake fingerprint is `harvest_fingerprint(summary, location)`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py`; an edit re-ingests the row), and never run `deferred_work_intake.py --fix`. Add a dated section *Curation — 2026-11-10* under the header. Rows the audit names first: DW-warden-16-1, DW-warden-16-3, DW-warden-16-4, DW-warden-16-4-2, DW-warden-egm-2026-11-1 (operator-owned, stays open), DW-5-2-5 (the slow lane in no workflow, stays open until steward's lane lands), DW-warden-103-3-1.

**This change's eleven rows**, `### DW-warden-cutover-2026-11-10-<n>:`, each with `owner: warden`, a severity, `promoted: 2026-11-10 — cutover readiness plan` and the source `planning-artifacts/research/cutover-readiness-audit-2026-11-10.md`. Where the plan's row text named an open operator question, it carries the ruling of 2026-11-10 instead:

| n | summary | severity | status |
|---|---|---|---|
| 1 | The bundled conda-to-pypi map carries no build-time snapshot and nothing checks its age. | medium | done 2026-11-10: the narrowed Constraint stands (operator ruling 2026-11-10) |
| 2 | `--deterministic` is parsed and never read; the SBOM's `serialNumber` and `metadata.timestamp` differ run to run. | medium | done 2026-11-10: the re-worded Spec stands (operator ruling 2026-11-10) |
| 3 | The report schema leaves `advisory` and `actuation` untyped, so the output shapes of CAP-23..CAP-26 are held by `contract.md` and a test, not by the schema. | low | done 2026-11-10: the schema stays 1.1.0 (operator ruling 2026-11-10) |
| 4 | Warden's tested engine ranges trail the estate (osv-scanner, deptry, pixi, opengrep; tea-test-review has no range). | medium | open: an engine run in warden's env and an estate refresh |
| 5 | The bundled LTS registry (`updated: 2026-07-06`, 180-day max age) reads stale from 2027-01-02. | medium | open: a conda-forge-expert data change with its retro, before 2027-01-02 |
| 6 | The 2026-11-05 EGM audit left 86 medium and 16 low warden findings untriaged. | low | open: operator triage through marshal's EGM process |
| 7 | Warden's architecture spine has no numbered AD-n. | low | open: Dream-sized, a `bmad-architecture` re-derive |
| 8 | CAP-26 spanned kernel and portal code, so its kernel half had no rebuild route. | medium | done 2026-11-10: CAP-26 split, the portal half minted as CAP-29 (operator ruling 2026-11-10; the mint's render) |
| 9 | CAP-13..CAP-15 (`sources.py`, `eligibility.py`, `eligibility_sbom.py`) have no CLI verb and no portal caller, and their cutover mode was unruled. | low | done 2026-11-10: `A-only`, expiry steward Story 44.8 (operator ruling 2026-11-10) |
| 10 | `spec-pyforge-warden`'s `surface:` block is the kernel package only, while `django-warden` realizes CAP-16, CAP-17, CAP-29 and the MCP face. | medium | done 2026-11-10: no co-governance; `contract.md`'s where-it-lives table stands (operator ruling 2026-11-10) |
| 11 | CAP-1..CAP-22's success clauses name no proving test or command inline; `proof-map.md` carries the proof per capability. | low | open: one re-derive after Story 26.2 (both rulings it waited on are made) |

Story 26.2 runs after this story and appends its own proof-map gap rows from `DW-warden-cutover-2026-11-10-12` up; it never edits a row this story wrote.

Ledger key: `25-4-every-open-warden-deferral-is-re-verified-and-carries-a-severity-and-an-owner`.
Type / Effort / Deps: chore / M / —.

### Living CAP citations

- The capabilities that shipped each behaviour (the stories each row names); no CAP minted or cited by number, no FR.
- `spec-feature-flag-governance` Q1: a `chore` needs no flag.

## Boundaries & Constraints

**Always:**
- Append a `verified:` line per row; keep each row's id, `summary:` and `location:` byte-identical.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not run `deferred_work_intake.py --fix`.
- Do not change code: verification only.
- Do not close an operator-owned row (DW-warden-egm-2026-11-1).

</intent-contract>

## Acceptance Criteria

- **AC1 — The deferred-work detector accepts the ledger.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run -e pyforge-guild deferred-work-check`
  Expect: exit 0.
- **AC2 — Every open row has a severity, an owner and a line dated in this change.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md').read();b=re.split(r'(?m)^(?=#{2,3} DW-)',t)[1:];bad=[x.split('\n',1)[0][:60] for x in b if re.search(r'(?m)^\s*status: open',x) and not (re.search(r'(?m)^\s*severity: (high|medium|low)',x) and re.search(r'(?m)^\s*owner: ',x) and re.search(r'(?m)^\s*(verified|promoted): 2026-(11-[123]|12-)\d',x))];print(len(b),bad);sys.exit(1 if bad else 0)"`
  Expect: prints the row count and [], exit 0. The date pattern admits any day from 2026-11-10 through 2026-12, so the AC holds when the story is built or re-run after 2026-11-19, while the ledger's earlier `verified: 2026-11-01` and `promoted: 2026-11-01` / `2026-11-05` lines still do not count as this change's re-verification.
- **AC3 — This change's eleven deferral rows exist.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md').read();m=[n for n in range(1,12) if '### DW-warden-cutover-2026-11-10-%d:'%n not in t];print(m);sys.exit(1 if m else 0)"`
  Expect: prints [], exit 0.
- **AC4 — No row lost its id, summary or location (the intake fingerprint is summary plus location).** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,subprocess,sys;f='_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md';o=subprocess.run(['git','show','origin/main:'+f],capture_output=True,text=True,check=True).stdout;n=open(f).read();k=lambda t:set(re.findall(r'(?m)^(#{2,3} DW-[^\n]*|\s*summary: [^\n]*|\s*location: [^\n]*)',t));m=sorted(k(o)-k(n));print(m[:5],len(m));sys.exit(1 if m else 0)"`
  Expect: prints [] 0, exit 0.
- **AC5 — The header no longer calls the ledger an uncurated copy without saying when it was curated.** Run from the repo root, verdict from the exit code (never through a pipe):
  `grep -c 'Curation . 2026-11-1' _bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md`
  Expect: prints a number >= 1, exit 0.
- **AC6 — No done row regresses and the planning detectors stay green.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run -e pyforge-guild ledger-regression-check && pixi run -e pyforge-guild story-status-check`
  Expect: exit 0.
- **AC7 — The six rows the operator's rulings of 2026-11-10 answer are closed on the ruling date.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md').read();b={m.group(1):m.group(2) for m in re.finditer(r'(?ms)^### DW-warden-cutover-2026-11-10-(\d+):(.*?)(?=^#{2,3} |\Z)',t)};m=[n for n in ('1','2','3','8','9','10') if not re.search(r'(?m)^\s*status: done 2026-11-10',b.get(n,''))];print(m);sys.exit(1 if m else 0)"`
  Expect: prints [], exit 0 (rows 1, 2, 3, 8, 9 and 10 carry `status: done 2026-11-10`; rows 4 to 7 and 11 stay open).

## Binding

- Story: `_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md` § *Story 25.4: Every open warden deferral is re-verified and carries a severity and an owner*.
- Dream: `docs/dreams/pyforge-warden.md`, Realization log, *2026-11-10 (the cutover readiness audit)*; the operator's rulings of 2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md`, Realization log, second addendum).
- Ledger key: `25-4-every-open-warden-deferral-is-re-verified-and-carries-a-severity-and-an-owner`.
- Deps: —.
- Flag: none (a `chore` story, `spec-feature-flag-governance` Q1).

## Gate findings (build, BUILD-1)

- 2026-11-11, `python3 scripts/ad_citation_check.py` (exit 1, 2 new issues): the `verified:` line this story wrote on DW-warden-cutover-2026-11-10-7 (`deferred-work-ledger.md:1234`) cited two suite-spine ADs unqualified. Fixed in the ledger: the line now reads suite:AD-9 and suite:AD-10, as the rest of the ledger does; the row's id, summary and location are untouched. Re-run exits 0 (7 baselined, 0 new).
