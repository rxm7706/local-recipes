---
title: '120.3: Epic 44, the epic bindings and the chain standard say what is true'
type: 'docs'
created: '2026-11-10'
status: 'done'
flag-exempt: docs-only
difficulty: medium
story: 120.3
spec: python-foundry-cutover
surface:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-44-8-the-working-set.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-44-14-rebuild-harness-and-oracle-gate.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - docs/governance/spec-one-chain-per-station/.memlog.md
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-coverage-gate-independence/.memlog.md
  - docs/governance/spec-coverage-gate-independence/SPEC.md
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/cutover.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Audit defect plus rulings 1 and 2 and the second addendum's rulings 2 and 7. Epic 44's intro still archives A and moves the estate; spec-44-8 speaks of manifest rows; the fold commit 97e0816ad2 rewrote 28 epic bindings to one blanket range, so INV-A cannot fire for those Specs; CHAIN-STANDARD § 0 says B is the root the cutover moves to and rebuilds from Frame and Spec, and § 4 has no marker for a retired capability; spec-coverage-gate-independence is three memlog events behind its SPEC.md.

**Approach:** Restore each of the 28 ranges from the pre-fold `epics.md`; lines added after the fold (the 3174, 3175 and 3218 `pap:` lines) take the named Spec's real range. Rewrite Epic 44's intro (A is never archived; capabilities reach foundry by their ledger mode; the flag is the writer lock, seam marshal Story 117.2, guard Story 121.4; 44.4, 44.5 and 44.6 retired 2026-11-10, 44.10 on 2026-09-25, 44.1 on 2026-11-10). Add dated notes to Stories 44.8 (a working-set list replaces manifest rows; Mason's ship and submit root resolves through `pyforge.core.cutover_root.root_of_record()`), 44.12 (stays done; its consumer clause is carried by Story 121.4, doctor Story 56.5 and marshal Story 115.4) and 44.14 (re-derived from the memlog B reads at the pin; states without `moving`), and the matching lines to spec-44-8 and spec-44-14. Amend CHAIN-STANDARD § 0 and § 4 with `event` lines on its memlog, then re-derive spec-one-chain-per-station and spec-coverage-gate-independence.

Ledger key: `120-3-epic-44-the-epic-bindings-and-the-chain-standard-say-what-is-true`. Type / Effort / Deps: docs / M / —.

### Living CAP citations

- **`spec-python-foundry-cutover`** — fnd:CAP-2, fnd:CAP-8 (the writer lock), fnd:CAP-9 (the ledger generator) and fnd:CAP-11, amended 2026-11-10 by memlog and re-derived at mint.

## Boundaries & Constraints

**Always:**
- Restore from `git show 97e0816ad2^:_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`; a pre-fold line that no longer exists in any form is named in this spec and left out of the set.
- A restored range that surfaces an INV-A or cap-citation finding on another unit's Spec is reported to that unit, never answered by widening the range.

**Never:**
- Never move a ledger status or key; never touch Story 44.1's block (retired at mint).
- Never write an `(unbuilt)` marker (the second addendum's ruling 2).

## Acceptance Criteria

- **AC1 — only the two true fold-window citations remain.** Expected: 2 (lines 24 and 36).
  ```bash
  grep -c 'CAP-1\.\.145' _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  ```
- **AC2 — Epic 54 and 55 cite their real ranges.** Expected: 2.
  ```bash
  grep -c -E '^## Epic 54: .*fnr:CAP-1\.\.5 / fnd:CAP-11\)$|^## Epic 55: .*fcl:CAP-1\.\.3\)$' _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  ```
- **AC3 — every restored line equals its pre-fold range.** Expected: prints a positive count and [], exit 0 (a pre-fold line that no longer exists in any form is named in the story spec and left out of the set).
  ```bash
  python3 -c "import subprocess,re,sys;p=sys.argv[1];old=subprocess.run(['git','show','97e0816ad2^:'+p],capture_output=True,text=True).stdout;new=open(p).read();r=re.compile(r'(spec-[a-z0-9-]+.? \(?.?(?:[a-z]+:)?CAP-1\.\.\d+)');o=set(r.findall(old));missing=sorted(x for x in o if x not in new);print(len(o),missing);sys.exit(1 if missing or not o else 0)" _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  ```
- **AC4 — Epic 44 no longer archives A.** Expected: exit 0.
  ```bash
  awk '/^## Epic 44:/{f=1;next} /^## Epic [0-9]+:/{f=0} f' _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md > "$TMPDIR/e44.md" && test $(grep -c 'archived read-only' "$TMPDIR/e44.md") -eq 0
  ```
- **AC5 — the three amended stories carry the dated note, inside Epic 44 only, and Story 44.1 carries its mint-time retired note.** Expected: prints 1, exit 0 (Stories 44.8, 44.12 and 44.14 amended; 44.1 retired at mint).
  ```bash
  awk '/^## Epic 44:/{f=1;next} /^## Epic [0-9]+:/{f=0} f' _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md > "$TMPDIR/e44.md" && test $(grep -c '^> \*\*Amended 2026-11-10' "$TMPDIR/e44.md") -eq 3 && awk '/^### Story 44.1:/{f=1;next} /^### Story /{f=0} f' _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md | grep -c '^> \*\*Retired 2026-11-10'
  ```
- **AC6 — spec-44-8 no longer moves recipes by manifest.** Expected: 0.
  ```bash
  grep -c 'manifest rows\|the recipes move' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-44-8-the-working-set.md
  ```
- **AC7 — CHAIN-STANDARD section 0 follows ruling 1.** Expected: 0.
  ```bash
  grep -c 'the root the cutover moves to\|B rebuilds its engines from Frame and Spec' docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  ```
- **AC8 — no blocked or done key moved.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-guild ledger-regression-check && pixi run -e pyforge-guild story-status-check
  ```
- **AC9 — every open Spec is still decomposed and named paths resolve.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-guild chain-completeness-check && pixi run -e pyforge-guild governance-currency
  ```
- **AC10 — Story 44.8 carries ruling 2's third consumer.** Expected: prints 1 or more twice.
  ```bash
  awk '/^## Epic 44:/{f=1;next} /^## Epic [0-9]+:/{f=0} f' _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md > "$TMPDIR/e44.md" && grep -c 'root_of_record()' "$TMPDIR/e44.md" && grep -c 'root_of_record()' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-44-8-the-working-set.md
  ```
- **AC11 — Story 44.12's note names no herald consumer.** Expected: prints 0.
  ```bash
  awk '/^### Story 44.12/{f=1;next} /^### Story /{f=0} f' _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md | grep -ci herald
  ```
- **AC12 — CHAIN-STANDARD section 4 carries the retired marker and the three qualifiers, and no unbuilt token.** Expected: prints 1 or more four times, exit 0.
  ```bash
  grep -c '(retired <date>\[: <reason>\])' docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md && grep -c 'not met: <clause>, DW-<id>' docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md && grep -c 'operator act open, DW-<id>' docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md && grep -c 'superseded by CAP-n' docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md && test $(grep -c -i 'unbuilt' docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md) -eq 0
  ```
- **AC13 — CHAIN-STANDARD section 0's Frame row says the ruled seed.** Expected: 1 or more.
  ```bash
  grep -c 'Dream plus memlog' docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  ```
- **AC14 — both governance Specs are not older than their memlogs.** Expected: exit 0.
  ```bash
  for d in docs/governance/spec-one-chain-per-station docs/governance/spec-coverage-gate-independence; do python3 -c "import re,sys;g=lambda p:re.search(r'(?m)^updated:\s*[\x22\x27]?(\d{4}-\d{2}-\d{2})',open(p).read()).group(1);d=sys.argv[1];s,m=g(d+'/SPEC.md'),g(d+'/.memlog.md');print(d,s,m);sys.exit(0 if s>=m else 1)" $d || exit 1; done
  ```

</intent-contract>

## Binding

Parent: `spec-python-foundry-cutover` fnd:CAP-2; `spec-one-chain-per-station:CAP-9`

- Dream: `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the mint entry) and `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth*.
- Epic: Epic 120.
- Ledger key: `120-3-epic-44-the-epic-bindings-and-the-chain-standard-say-what-is-true` (`backlog` at mint).
- Deps: —.
- Surface: `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-44-8-the-working-set.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-44-14-rebuild-harness-and-oracle-gate.md`, `docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md`, `docs/governance/spec-one-chain-per-station/.memlog.md`, `docs/governance/spec-one-chain-per-station/SPEC.md`, `docs/governance/spec-coverage-gate-independence/.memlog.md`, `docs/governance/spec-coverage-gate-independence/SPEC.md` (in `epics.md`, only the Epic 44 block, the 28 lines that carry the fold window's blanket range and the Epic 54 and Epic 55 headings; each governance SPEC.md is re-derived only).
- Minted 2026-11-10 by the cutover-readiness mint (control-plane unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild story-status-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild ledger-regression-check` — expected: exit 0.

## Notes

- The 28 binding lines and the Epic 54 and 55 headings are this story's; steward-station Story 122.1 does not touch them.
- CHAIN-STANDARD is a governance page: its Dream `docs/dreams/one-chain-per-station.md` takes a dated 2026-11-10 Realization-log pointer line, written at mint (by the integrator: the file is outside the steward mint's owned paths); this story writes none.
- Cross-station: marshal:S-117.2 (the seam named in the Epic 44 intro), doctor:S-56.5 and marshal:S-115.4 (the 44.12 note).
