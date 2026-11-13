---
title: '122.5: The steward and host Specs close on what landed: shipped markers and one Surface reconcile each'
type: 'chore'
created: '2026-11-10'
status: 'done'
difficulty: medium
story: 122.5
spec: pyforge-steward
surface:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/stack.md
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
- **AC12 — a simulated ledger close leaves no finding (added by the integrator ruling).** Expected: prints `<keys> 0 False` (`100 0 False` on 2026-11-13), exit 0. It takes the story keys from the `build(<station>):` subjects of `git log --format=%s 82a2b18828..HEAD`, adds steward 122.5, treats each as `done` in memory, writing no file, and re-runs `cutover_ledger_check.check` with no exemption; the `False` shows that 121.5, which stays blocked, is not among the keys.
  ```bash
  pixi run --frozen -e pyforge-steward python -c "import re,subprocess;from pathlib import Path;from pyforge.steward import cutover_ledger_check as c;s=subprocess.run(['git','log','--format=%s','82a2b18828..HEAD'],capture_output=True,text=True,check=True).stdout.splitlines();b={('pyforge-'+m.group(1),k) for x in s for m in [re.match(r'build\(([a-z-]+)\):',x)] if m for k in re.findall(r'\b\d+\.\d+\b',re.sub(r'\(BUILD[^)]*\)','',x))}|{('pyforge-steward','122.5')};o=c._Stations.status;c._Stations.status=lambda self,st,k:'done' if (st,k) in b else o(self,st,k);r=c.check(Path('.'),Path('docs/foundry/capability-ledger.yaml'));[print(*g) for g in r.findings];print(len(b),len(r.findings),('pyforge-steward','121.5') in b);raise SystemExit(1 if r.findings else 0)"
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

## Review findings (build, round 1, 2026-11-11)

An independent reviewer failed the previous attempt on one major and one minor finding. Neither fix lies in this story's own files, so this round changed no file in its files_owned. It wrote this section and re-ran every criterion. `pixi.lock`'s sha256 was the same before and after every command, and every `pixi run` used `--frozen`.

1. **major. Where:** AC10, both halves: `cutover_ledger_check.check` and `pyforge steward cutover plan --check`. The same four findings also fail steward's `tests/meta/test_capability_ledger_live.py::test_the_ledger_has_no_finding_but_the_exemption`, which is Story 121.7's file.
   - **Problem.** Re-run, AC10 prints `4 4 rebuild` and exits 1, and `plan --check` exits 1. The four findings are `rebuild-never-built` on `fnd:CAP-3`, `pyforge-atlas:CAP-43`, `pyforge-steward:CAP-172` and `pyforge-steward:CAP-173`. Their citing stories are built on this branch but read `backlog` until CLOSE-LEDGERS: 120.1 (`build(steward): 120.1, …` in BUILD-1), atlas 46.1 and 46.2 (`build(atlas): 46.1, …, 46.2, …` in BUILD-1 and BUILD-2), and 122.1 (`build(steward): …, 122.1` in BUILD-3). This spec has no Integrator note naming that window. The 2026-11-12 Integrator ruling in spec-121-7 covers these findings in Story 121.7's ACs only, so it does not cover this story's AC10.
   - **Response.** The reviewer is right on the facts and right about the cause: this is a real ledger-close window, not a fault in this story's work. The reviewer names an integrator act as the fix, and an implementer does not write an `## Integrator note`, as spec-121-7's round 2 also recorded. No ledger row, mode or exemption changed. The reviewer does not say the AC10 command is wrong, so the oracle rule does not apply and AC10 stays as written.
   - **Evidence this round.** This round repeated the reviewer's simulated close in memory, writing no file. The script patches `_Stations._read_statuses` to read `done` for every story key in the `build(...)` subjects of `git log origin/main..HEAD`, plus 122.5, and re-runs `cutover_ledger_check.check`. It counts 99 keys and 121.5 is not among them. It reports 0 findings, `pyforge-steward:CAP-181` still reads `rebuild`, and it exits 0. `plan --check` also prints 55 `no-marker` warnings, all on the host Spec's capabilities, which DW-steward-cutover-2026-11-10-5 records. Warnings do not set its exit code.
   - **Asked of the integrator.** Add an `## Integrator note` to this spec. It should name AC10, both halves, as a planned red window that closes at CLOSE-LEDGERS, limited to `rebuild-never-built` findings whose citing stories are built on this branch: `fnd:CAP-3` (120.1), `pyforge-atlas:CAP-43` (atlas 46.1, 46.2), and `pyforge-steward:CAP-172` and `pyforge-steward:CAP-173` (122.1). Optionally it can add an AC that proves the window with the simulated close, as spec-121-7's AC9 does. After CLOSE-LEDGERS, AC10 must print `0 0 rebuild` and `plan --check` must exit 0. Until then this round reports AC10 as failing, for this reason only.
2. **minor. Where:** `plan.json` stories[122.5].files_owned, and this spec's frontmatter `surface:`.
   - **Problem.** This story rendered `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md`, and only its `updated:` line changed. Item 3 of the 2026-11-12 Integrator ruling in spec-124-5 sanctions that render ("renders SPEC.md in the same pass"). But `plan.json` files_owned names only `stack.md` for it, and the frontmatter `surface:` names neither `stack.md` nor the host SPEC.md. So no list of this story's files records the edit.
   - **Response.** The reviewer is right. Both lists are the integrator's to change: `plan.json` is not this story's file beyond the oracle rule, and a build writes body sections only, never the mint's frontmatter. The two files are recorded here instead. Beyond its Binding § Surface, this story changed `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/stack.md`, where the `python-duckdb` row now cites `pyforge-atlas:AD-13` and its `updated:` line moved, and `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md`, a re-derive only, where the `updated:` line alone changed. The integrator is asked to add both to `plan.json` stories[122.5].files_owned and, if it keeps the frontmatter in step, to `surface:`.

**Re-run, 2026-11-13.** AC1 prints 6, then 6. AC2 exits 0 (10 passed). AC3 and AC4 print 0 and exit 0; the spec-surface JSON has no drift row at all, only 3 `stale-allowlist` rows. AC5 and AC6 print 1. AC7 exits 0 (`pyforge-steward: current`). AC8 prints 4, then 12, and `deferred-work-check` exits 0. AC9 prints `25 []` and exits 0. AC10 prints `4 4 rebuild` and exits 1, and `plan --check` exits 1: this is finding 1's window. AC11 exits 0.

## Review findings (build, round 2, 2026-11-11)

The independent reviewer failed round 1 on one major and one minor finding. Both carry over from round 1. For each, the reviewer names an integrator act as the fix. This round changed no file in this story's files_owned. It wrote this section and made one oracle correction in `plan.json`. `pixi.lock`'s sha256 was the same before and after every command, and every `pixi run` used `--frozen`.

1. **major. Where:** AC10, both halves: `cutover_ledger_check.check` over `docs/foundry/capability-ledger.yaml`, and `pyforge steward cutover plan --check`.
   - **Problem.** Round-1 finding 1 is still open. At HEAD 501890d2ab, AC10 prints `4 4 rebuild` and exits 1, and `plan --check` exits 1. All four findings are `rebuild-never-built`. On `fnd:CAP-3` the citing story is 120.1. On `pyforge-atlas:CAP-43` they are atlas 46.1 and 46.2. On `pyforge-steward:CAP-172` and `pyforge-steward:CAP-173` it is 122.1. Every one of those stories reads `backlog`. This spec still has no `## Integrator note` or `## Integrator ruling` that names this planned red window. The spec-121-7 ruling of 2026-11-12 covers only Story 121.7's own ACs. An implementer's request in round 1 cannot grant the window. The reviewer finds the cause real and not a fault in this story's work. Its simulated close runs in memory. It reads as `done` every key in the `build(<station>)` subjects on `origin/main..HEAD`, skips the "deferred twins" commits and adds 122.5. That gives 99 keys, without `pyforge-steward:121.5`. The check then reports 0 findings and exits 0, and `pyforge-steward:CAP-181` still reads `rebuild` with no exemption applied.
   - **Response.** Agreed. No implementer fix exists, and none was attempted. Only the integrator can grant the window: an `## Integrator note` or ruling that names AC10, both halves, as a planned red window closing at CLOSE-LEDGERS and limited to those four findings. It may also add a simulated-close AC like spec-121-7's AC9. This story cannot write either one. The oracle rule lets a build correct a command the reviewer calls wrong, given its corrected form. It does not let a build add an AC, and the reviewer does not call AC10's command wrong. AC10 therefore stays as written. No ledger row, mode or exemption changed. After CLOSE-LEDGERS, AC10 must print `0 0 rebuild` and `plan --check` must exit 0.
   - **Evidence this round.** This round re-ran the reviewer's script read-only in `-e pyforge-steward`: `/tmp/claude-1000/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/552e28f7-6060-4942-926f-c593d0973dbf/scratchpad/cutover/build/122.5/rev2/sim.py`. It printed `99 False`, then `0 ()`, and exited 0. That matches the reviewer's output.
2. **minor. Where:** `plan.json` stories[122.5].files_owned and acceptance[0], and this spec's frontmatter `surface:`.
   - **Problem.** Round-1 finding 2 is settled in substance. Item 3 of the spec-124-5 Integrator ruling of 2026-11-12 routes both the `stack.md` correction and the host SPEC.md render to this story. Both went through the memlog, then an anchored script, then two self-validate events. The bookkeeping still lags in three places. `plan.json` files_owned does not name `spec-pyforge-unifying-strategy/SPEC.md`. The frontmatter `surface:` names neither `stack.md` nor the host SPEC.md. And `plan.json` acceptance[0] still carries a stale command, while this spec, the source of record, carries AC1.
   - **Response, acceptance[0]: an oracle correction, made this round.** The reviewer says the command is wrong and gives its corrected form: this spec's AC1 command. The old entry read check `CAP-179..CAP-182 read shipped`, command `grep -cE '^- \*\*CAP-(187|188|189|190) .*\(shipped 2026-' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md`, expect `prints 4`. The new entry reads check `CAP-153, CAP-166 and CAP-179..CAP-182 read shipped`, with this spec's AC1 command copied byte for byte and its expectation, `prints 6, then 6`. The old command could never pass, because none of the ids 187 to 190 exists in spec-pyforge-steward's SPEC.md: on today's tree it prints 0 and exits 1. Its own check text names `spec-pyforge-steward:CAP-179` to `spec-pyforge-steward:CAP-182`, but its regex names the ids 187 to 190. It also missed the `spec-pyforge-steward:CAP-153` and `spec-pyforge-steward:CAP-166` flips that the 2026-11-11 fix pass added. The new command checks more than the old one did. It counts six ids that carry a dated marker, and then six that carry `(shipped 2026-`. So no assertion is dropped, no count is loosened and no skip is added. Only stories[122.5].acceptance[0] changed, under the `plan-json.lock` flock. The AC block in this spec already read the corrected form and did not change.
   - **Response, files_owned and `surface:`.** These remain the integrator's. Beyond the oracle rule, `plan.json` files_owned is not this story's file to change. A build writes only body sections, never the mint's frontmatter. Round 1's item 2 names both files in full, with what changed in each. The integrator is asked to add `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md` to `plan.json` stories[122.5].files_owned. If the frontmatter is kept in step, it and `stack.md` also go in `surface:`.

**Re-run, 2026-11-13 (round 2).** AC1 prints 6, then 6, and the corrected `plan.json` acceptance[0] gives the same result. AC2 exits 0 (10 passed). AC3 and AC4 each print 0 and exit 0. The spec-surface JSON has no drift row, only 3 `stale-allowlist` rows. AC5 and AC6 each print 1. AC7 exits 0 (`pyforge-steward: current`). AC8 prints 4, then 12, and `deferred-work-check` exits 0. AC9 prints `25 []` and exits 0. AC10 prints `4 4 rebuild` and exits 1, and `plan --check` exits 1 with the same four `rebuild-never-built` findings and 55 `no-marker` warnings. That is finding 1's window, and it closes only at CLOSE-LEDGERS. AC11 exits 0. The `plan --check` half ran with `--frozen` added, per the build's lock rule. Otherwise the AC10 command is unchanged.


## Integrator ruling (2026-11-13, before the chunk-8 retry)

This story failed three reviews on one finding that no file of its own could close: AC10's four `rebuild-never-built`
findings. The BUILD-17 gate also found two NEW `ad_citation_check.py` issues in this spec. This ruling binds the
implementer and the reviewer.

1. **AC10 is a planned red window that closes at CLOSE-LEDGERS.** It covers AC10, both halves
   (`cutover_ledger_check.check` and `pyforge steward cutover plan --check`), and only `rebuild-never-built` findings
   whose citing stories are built on this branch: `fnd:CAP-3` (steward 120.1), `pyforge-atlas:CAP-43` (atlas 46.1 and
   46.2), and `pyforge-steward:CAP-172` and `pyforge-steward:CAP-173` (steward 122.1). Every other AC10 finding is
   real. The ledgers move to `done` only at CLOSE-LEDGERS, after the last build wave, so no story can close this window
   before then. After CLOSE-LEDGERS the integrator re-runs AC10: it must print `0 0 rebuild`, and `plan --check` must
   exit 0. Until then AC10 passes when its only findings are the four above and AC12 exits 0.
2. **AC12 is added.** Append it to the Acceptance Criteria block, labelled `(added by the integrator ruling)`, and
   record it as stories[122.5].acceptance in plan.json under the `plan-json.lock` flock. It is a simulated ledger close.
   It takes the story keys from the `build(<station>):` subjects of `git log --format=%s 82a2b18828..HEAD`, adds
   steward 122.5, and treats each as `done` in memory, writing no file. Then it re-runs `cutover_ledger_check.check`
   with no exemption. Expected: prints `<keys> 0 False` (`100 0 False` on 2026-11-13), exit 0. The `False` shows that
   121.5, which stays blocked, is not among the keys. Command:
   ```bash
   pixi run --frozen -e pyforge-steward python -c "import re,subprocess;from pathlib import Path;from pyforge.steward import cutover_ledger_check as c;s=subprocess.run(['git','log','--format=%s','82a2b18828..HEAD'],capture_output=True,text=True,check=True).stdout.splitlines();b={('pyforge-'+m.group(1),k) for x in s for m in [re.match(r'build\(([a-z-]+)\):',x)] if m for k in re.findall(r'\b\d+\.\d+\b',re.sub(r'\(BUILD[^)]*\)','',x))}|{('pyforge-steward','122.5')};o=c._Stations.status;c._Stations.status=lambda self,st,k:'done' if (st,k) in b else o(self,st,k);r=c.check(Path('.'),Path('docs/foundry/capability-ledger.yaml'));[print(*g) for g in r.findings];print(len(b),len(r.findings),('pyforge-steward','121.5') in b);raise SystemExit(1 if r.findings else 0)"
   ```
3. **Reword the two bare ids.** The round-2 section names the ids 187 and 190 outside a code span, and
   `ad_citation_check.py` reports both as NEW issues. These ids exist in no Spec, so do not qualify them. Reword the
   prose to name "the ids 187 to 190", and leave the quoted regex as a code span. Then run
   `pixi run --frozen -e pyforge-guild python scripts/ad_citation_check.py`. It must report no NEW issue from this spec.
4. **Bookkeeping (round-1 and round-2 finding 2) is closed by the integrator.** Before this retry, the integrator added
   `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md` and `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/stack.md` to this spec's frontmatter `surface:` and to plan.json
   stories[122.5].files_owned.
5. **The integrator's pixi.toml edit.** Commit `efbd42f3bb`, the integrator's fix for the stale job texts, changed only
   the descriptions of five root `pixi.toml` tasks. That commit gave the spec-pyforge-core, spec-pyforge-marshal,
   spec-pyforge-doctor and spec-pyforge-herald memlogs their reconcile lines. Your Surface reconcile `event` lines on
   spec-pyforge-steward and spec-pyforge-unifying-strategy must name `pixi.toml` with that commit and that reason.
   Extend your existing line; do not add a second reconcile event.
6. Never change a ledger row's mode, an exemption or `pixi.lock`. Append
   `## Review findings (build, round 3, 2026-11-13)`, saying how this ruling closed each finding.

## Review findings (build, round 3, 2026-11-13)

This round follows the `## Integrator ruling (2026-11-13, before the chunk-8 retry)` above. It changed this spec's Acceptance Criteria block (AC12 appended) and its round-2 section (the reword), `plan.json` stories[122.5].acceptance (AC12, under the `plan-json.lock` flock), and the one Surface reconcile `event` line on each of the spec-pyforge-steward and spec-pyforge-unifying-strategy memlogs. No ledger row, mode, exemption, status line or `pixi.lock` changed. `pixi.lock`'s sha256 was the same before and after every command, and every `pixi run` used `--frozen`. The scripts and outputs are in the build scratchpad, under `cutover/build/122.5/rev3/`.

1. **AC10 (finding 1 of rounds 1 and 2). Closed by ruling item 1, with AC12 as its proof.**
   - AC10's first half prints `4 4 rebuild` and exits 1. Run on its own, because the `&&` stops after the first half, `plan --check` exits 1 with 4 findings and 55 warnings.
   - Both halves list the same four `rebuild-never-built` findings and no others: `fnd:CAP-3` (steward 120.1), `pyforge-atlas:CAP-43` (atlas 46.1 and 46.2), and `pyforge-steward:CAP-172` and `pyforge-steward:CAP-173` (steward 122.1). These are exactly the four that the ruling names.
   - AC12 prints `100 0 False` and exits 0. Under item 1, AC10 therefore passes in this window.
   - After CLOSE-LEDGERS the integrator re-runs AC10. It must print `0 0 rebuild`, and `plan --check` must exit 0.
   - A correction to rounds 1 and 2: the 55 `no-marker` warnings do not all fall on the host Spec. 20 are on spec-pyforge-unifying-strategy, which DW-steward-cutover-2026-11-10-5 records. The other 35 are on the governance Specs and the pap host Spec: 11 on one-chain-per-station, 8 on pyforge-charter, 7 on feature-flag-governance, 6 on pap and 3 on coverage-gate-independence. Warnings do not set the exit code.
2. **AC12 (ruling item 2). Added.**
   - It is appended to the Acceptance Criteria block, labelled `(added by the integrator ruling)`. Its command is the ruling's, copied byte for byte: a script compared the two commands, both 762 bytes, and found them equal.
   - It is also stories[122.5].acceptance[9] in `plan.json`. That entry was written under the `plan-json.lock` flock and keeps the file's own JSON format: the dump with `indent=1` and `ensure_ascii=False` reproduces the original bytes exactly.
   - `plan.json` held AC1 to AC9 before this round. AC10 and AC11 live in this spec only. This round did not add them to `plan.json`, because the ruling names only AC12.
3. **The two bare ids (ruling item 3). Reworded, but one residual remains, in the ruling's own text.**
   - The round-2 section now says "the ids 187 to 190" in both places: the pair in code spans and the bare pair. `ad_citation_check.py` reads code spans too, because its `_CAP_CITE` pattern runs on every line. The quoted regex stays a code span, and its parenthesised form does not match that pattern.
   - `pixi run --frozen -e pyforge-guild python scripts/ad_citation_check.py` still exits 1, with 2 NEW issues from this spec: the bare 187 and the bare 190. This spec's occurrences fell from 6 to 2.
   - Both remaining occurrences are in the first sentence of ruling item 3, which quotes the two ids in code spans. A build does not edit an integrator ruling, so this round left that sentence as it is.
   - Evidence: `adc_sim.py` replaces that one sentence's two ids with "the ids 187 and 190", in memory, writing no file, and then runs the check. The check exits 0 and reports no NEW issue and no row that names this spec.
   - Asked of the integrator: reword that sentence to name "the ids 187 and 190". The check will then report no NEW issue from this spec. Until that happens, this round reports item 3's check as failing, for this reason only.
4. **Bookkeeping (finding 2 of rounds 1 and 2). Closed by ruling item 4.** The frontmatter `surface:` and `plan.json` stories[122.5].files_owned both now name `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md` and `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/stack.md`. This round confirmed both lists and changed neither.
5. **pixi.toml (ruling item 5). The existing line was extended, and no second event was added.**
   - Each Surface reconcile line now says it was extended at branch head efbd42f3bb. Its pixi.toml clause names the integrator's commit efbd42f3bb, which changed only the descriptions of five root tasks; task commands and dependencies are unchanged. The line now groups pixi.toml as `[steward 124.1; integrator efbd42f3bb]`.
   - `extend_reconcile.py` asserted that each of its three anchors occurs exactly once in its file and inside the one reconcile line. It also checked that no other line changed. Each memlog still holds exactly one such event, and its `updated:` key did not move.
   - Since 501890d2ab, the head the lines were first written at, pixi.toml is the only path either Spec governs that moved on the branch. This comes from `git diff --name-only 501890d2ab HEAD` matched against both surfaces.

**Re-run, 2026-11-13 (round 3), at HEAD efbd42f3bb.**
- AC1 prints 6, then 6.
- AC2 exits 0 (10 passed).
- AC3 and AC4 each print 0 and exit 0. The spec-surface JSON has no drift row, only 3 `stale-allowlist` rows.
- AC5 and AC6 each print 1.
- AC7 exits 0 (`pyforge-steward: current`).
- AC8 prints 4, then 12, and `deferred-work-check` exits 0.
- AC9 prints `25 []` and exits 0.
- AC10 prints `4 4 rebuild` and exits 1, and `plan --check` exits 1 with the same four findings. This is the ruling's window, so AC10 passes under item 1.
- AC11 exits 0.
- AC12 prints `100 0 False` and exits 0.

The `plan --check` half ran with `--frozen` added, per the build's lock rule. Otherwise every command ran as written. After the memlog edits, AC2, AC3, AC4, AC9 and AC11 were run a second time, with the same results.

## Gate findings (build, BUILD-R5)

- `scripts/ad_citation_check.py` exited 1 with 2 NEW cap-citation issues from this spec: the bare ids 187 and 190 in the first sentence of ruling item 3 of the `## Integrator ruling (2026-11-13, before the chunk-8 retry)` above (the `_CAP_CITE` pattern matches inside code spans too). Integrator fix (wave fix, BUILD-R5): that sentence now names "the ids 187 and 190", as round 3 finding 3 asked; nothing else in the ruling changed. Re-run: `pixi run --frozen -e pyforge-guild python scripts/ad_citation_check.py` exits 0 and reports no NEW issue and no row naming this spec, so ruling item 3 is met. No other story's file was edited.
