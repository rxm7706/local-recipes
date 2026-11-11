---
title: '122.5: The steward and host Specs close on what landed: shipped markers and one Surface reconcile each'
type: 'chore'
created: '2026-11-10'
status: 'blocked'
difficulty: medium
story: 122.5
spec: pyforge-steward
surface:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/briefs/brief-pyforge-steward-2026-07-25/brief.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/implementation-readiness-report-2026-1*.md
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-unifying-strategy.md
context:
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
declared_low_risk: false
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-123.1, S-123.2, S-123.3, S-124.1, S-124.2, S-124.3, S-124.4).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** Every unit asked steward-station for co-governor Surface reconcile events on the steward and host Specs, and the capabilities minted at mint finish in this PR; the chain has to say so once, after the last edit.

**Approach:** Append with `uv run _bmad/scripts/memlog.py` (one `updated:` key): the reconcile events and one `change` entry per marker flip (CAP-153, CAP-166, CAP-179, CAP-181, CAP-182; each date the day its last citing story reached `done`); re-derive the steward Spec through the anchored script render with both self-validate passes; re-stamp brief, PRD, spine and epics on this story's own day after its last memlog append; write a readiness report only if this runs on or after 2026-12-01; add `- **<date> (cutover readiness, closed)** — ...` to both Dreams (CHAIN-STANDARD section 3 step 7).

Ledger key: `122-5-the-steward-and-host-specs-close-on-what-landed-shipped-markers-and-one-surface-reconcile-each`. Type / Effort / Deps: chore / M / S-29.5, S-120.5, S-121.1, S-121.2, S-121.6, S-121.7, S-122.2, S-122.3, S-122.4, S-123.1, S-123.2, S-123.3, S-124.1, S-124.2, S-124.3, S-124.4.

### Living CAP citations

- **`spec-pyforge-steward` CAP-153, CAP-166, CAP-179, CAP-181, CAP-182** — flip to `(shipped <date>)` here, one `change` entry each; CAP-180 was minted `shipped`. CAP-153 (the package `pixi.toml` floor clause Story 124.3 builds) and CAP-166 (the registry rows Story 124.2 adds) keep `ready` at Story 122.1 because those stories are open then (ruling 6 of the second addendum: markers of capabilities this PR builds flip at the station's closing Story). **`spec-pyforge-unifying-strategy`** — the host Spec's Surface reconcile.

## Boundaries & Constraints

**Always:**
- Name every path in full; the scoped stamp wants literal paths.
- Write each deferred row with severity, owner and `status: open` (or `resolved` where a story of this PR resolved it).

**Never:**
- Never run `spec_surface_check.py --write-baseline`.
- Never flip a ledger key.

## Acceptance Criteria

- **AC1 — CAP-153, CAP-166 and CAP-179..CAP-182 read shipped.** Expected: prints 6, then 6 (CAP-180 was minted shipped; CAP-153, CAP-166, CAP-179, CAP-181 and CAP-182 flip here).
  ```bash
  grep -cE '^- \*\*CAP-(153|166|179|180|181|182) .*\((ready|shipped) 2026-' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md && grep -cE '^- \*\*CAP-(153|166|179|180|181|182) .*\(shipped 2026-' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  ```
- **AC2 — the Specs are not behind their memlogs.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-scribe env PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pytest src/shared/packages/pyforge-scribe/tests/meta/test_spec_not_behind_memlog.py -q
  ```
- **AC3 — no unreconciled drift row names pyforge-steward/spec-pyforge-steward (the closer's memlog names every changed path; doctor 58.4 stamps).** Expected: prints 0, exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources spec-surface --json > "$TMPDIR/ss.json"; python3 -c "import json,sys;d=json.load(open(sys.argv[1]));rows=d if isinstance(d,list) else (d.get('findings') or d.get('rows') or []);n=[r for r in rows if r.get('check') in ('drift','drift-presumed') and sys.argv[2] in json.dumps(r)];print(len(n));sys.exit(1 if n else 0)" "$TMPDIR/ss.json" pyforge-steward/spec-pyforge-steward
  ```
- **AC4 — no unreconciled drift row names pyforge-steward/spec-pyforge-unifying-strategy (the closer's memlog names every changed path; doctor 58.4 stamps).** Expected: prints 0, exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources spec-surface --json > "$TMPDIR/ss.json"; python3 -c "import json,sys;d=json.load(open(sys.argv[1]));rows=d if isinstance(d,list) else (d.get('findings') or d.get('rows') or []);n=[r for r in rows if r.get('check') in ('drift','drift-presumed') and sys.argv[2] in json.dumps(r)];print(len(n));sys.exit(1 if n else 0)" "$TMPDIR/ss.json" pyforge-steward/spec-pyforge-unifying-strategy
  ```
- **AC5 — docs/dreams/pyforge-steward.md records the close.** Expected: prints 1 or more.
  ```bash
  grep -c 'cutover readiness, closed' docs/dreams/pyforge-steward.md
  ```
- **AC6 — docs/dreams/pyforge-unifying-strategy.md records the close.** Expected: prints 1 or more.
  ```bash
  grep -c 'cutover readiness, closed' docs/dreams/pyforge-unifying-strategy.md
  ```
- **AC7 — steward's chain is current: no feeds finding and no shelf finding, read from the exit code.** Expected: exit 0 (1 is a finding, 2 could not run; never through a pipe).
  ```bash
  pixi run --frozen -e pyforge-guild chain-currency-sweep-check -- --project pyforge-steward
  ```
- **AC8 — the steward project's deferred rows are tracked.** Expected: prints 4, then 12, then exit 0 (DW-steward-cutover-2026-11-10-1 is written `status: resolved` naming Story 123.3, so the numbering stays whole).
  ```bash
  grep -cE '^### DW-steward-121-[1-4]\b' _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md && grep -cE '^### DW-steward-cutover-2026-11-10-[0-9]+\b' _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md && pixi run --frozen -e pyforge-guild deferred-work-check
  ```
- **AC9 — every path the host Spec's widened surface newly governs is named in its reconcile event.** Expected: prints the count of newly governed paths and [], exit 0.
  ```bash
  python3 - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md <<'EOF'
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
- **AC10 — the ledger check is clean with no exemption, and `pyforge-steward:CAP-181` stays rebuild.** Expected: prints `0 0 rebuild`, then `plan --check` exits 0 (Story 121.7 exempted the `rebuild-never-built` finding on `pyforge-steward:CAP-181` only while Story 123.1 was not `done`; none is applied here).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts python -c "import yaml;from pathlib import Path;from pyforge.steward.cutover_ledger_check import check;r=check(Path('.'),Path('docs/foundry/capability-ledger.yaml'));f=[x for x in r.findings if x[0]=='rebuild-never-built'];m={x['id']:x for x in yaml.safe_load(open('docs/foundry/capability-ledger.yaml'))['capabilities']}['pyforge-steward:CAP-181']['mode'];print(len(f),len(r.findings),m);raise SystemExit(1 if r.findings or m!='rebuild' else 0)" && pixi run -q -e pyforge-guild pyforge steward cutover plan --check
  ```
- **AC11 — one `change` entry per flipped capability.** Expected: exit 0 (each of the five ids has a `change` entry carrying its `(shipped <date>)` marker).
  ```bash
  for n in 153 166 179 181 182; do grep -qE "^- \(change\) CAP-$n\b.*\(shipped 2026-" _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md || { echo "CAP-$n"; exit 1; }; done
  ```

</intent-contract>

## Binding

Parent: `spec-pyforge-steward` CAP-153, CAP-166, CAP-179, CAP-181, CAP-182; `spec-pyforge-unifying-strategy` (Surface reconcile)

- Dream: `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth* (subsection *The steward Spec, suite and shared surfaces*) and `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the steward-station mint entry).
- Epic: Epic 122.
- Ledger key: `122-5-the-steward-and-host-specs-close-on-what-landed-shipped-markers-and-one-surface-reconcile-each` (`backlog` at mint).
- Deps: S-29.5, S-120.5, S-121.1, S-121.2, S-121.6, S-121.7, S-122.2, S-122.3, S-122.4, S-123.1, S-123.2, S-123.3, S-124.1, S-124.2, S-124.3, S-124.4.
- Surface: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md` (append), `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md` (re-derive only), `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md` (append), `_bmad-output/projects/pyforge-steward/planning-artifacts/briefs/brief-pyforge-steward-2026-07-25/brief.md, _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md, _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md and _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md` (frontmatter `updated:` and one dated Currency reconciliation line each), `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` (append: DW-steward-121-1..4 and DW-steward-cutover-2026-11-10-1..12), `_bmad-output/projects/pyforge-steward/planning-artifacts/implementation-readiness-report-<date>.md` (new, only when this story runs on or after 2026-12-01), `docs/dreams/pyforge-steward.md and docs/dreams/pyforge-unifying-strategy.md` (one closing Realization-log line each).
- Minted 2026-11-10 by the cutover-readiness mint (steward-station unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `grep -cE '^- \*\*CAP-(153|166|179|180|181|182) .*\((ready|shipped) 2026-' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md && grep -cE '^- \*\*CAP-(153|166|179|180|181|182) .*\(shipped 2026-' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md` — expected: prints 6, then 6 (CAP-180 was minted shipped; CAP-153, CAP-166, CAP-179, CAP-181 and CAP-182 flip here).
- `pixi run --frozen -e pyforge-scribe env PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pytest src/shared/packages/pyforge-scribe/tests/meta/test_spec_not_behind_memlog.py -q` — expected: exit 0.

## Notes

- Cross-station deps (the stories whose edits the reconcile lines name): scribe:S-31.1, scribe:S-31.4, scribe:S-32.1, scribe:S-32.2, scribe:S-32.3, scribe:S-33.1, scribe:S-33.2, atlas:S-47.1, atlas:S-47.2, atlas:S-48.1, atlas:S-48.2, atlas:S-48.3, herald:S-50.4, marshal:S-117.1, marshal:S-117.2, marshal:S-117.3, marshal:S-117.4, marshal:S-117.6, marshal:S-117.7; doctor:S-58.4 runs after it.
- Deferred rows, written after Story 123.3's DW-steward-119-2 entry: DW-steward-121-1..4 (control-plane; DW-steward-121-5 is not written, doctor 56.5 builds its branch judge) and DW-steward-cutover-2026-11-10-1..12 (steward-station's eleven and the django-scribe lane row). Under the operator's 2026-11-10 rulings: -1 (session check finding (2) could not fail) is written `status: resolved` naming Story 123.3, which fixes it; -2 records that `restore` and `revoke` read no kill switch (ruled: none added in this PR); -5 records that the host Spec's 20 capabilities carry no dated marker.
- CAP-180 needs no flip: it was minted `(shipped 2026-09-02; ...)`.
- Fix pass 2026-11-11 (independent review): CAP-153 and CAP-166 join the flips (Story 122.1's AC2 now expects them `ready`, since Stories 124.3 and 124.2 cite them and are open at its wave), and AC10 closes Story 121.7's one exemption: with Story 123.1 `done`, the check must be clean with none applied.
