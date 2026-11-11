---
title: "118.2: The testing charter says what was built, and carries Epic 118's capabilities"
type: 'docs'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: easy
story: '118.2'
spec: pyforge-testing-charter
surface:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/station-tea-status.md
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/station-tea-status.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml
  - scripts/fleet_scan.py
  - docs/governance/spec-coverage-gate-independence/SPEC.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Decision D4 of the 2026-11-10 design pass and the audit's findings on the charter Spec: at `82a2b18828` no capability carries a status marker though Stories 19.1 to 19.5 are done, spec-pyforge-testing-charter:CAP-1 names a `generate.py` that no longer exists, the surface comment says the kit is `net-new, not yet created`, and the companion's 2026-08-02 counts read as current. This is also the one mint-time re-derive of the charter before Story 118.1 starts.

**Approach:** The mint of 2026-11-10 appended to this Spec's memlog: the Dream direction, the rulings decision, the `capability` entries for spec-pyforge-testing-charter:CAP-6 and spec-pyforge-testing-charter:CAP-7, the `change` entries for spec-pyforge-testing-charter:CAP-3, spec-pyforge-testing-charter:CAP-1 and spec-pyforge-testing-charter:CAP-4, the marker-sweep direction, the companion event and the chain-steps event. This story appends one `change` entry carrying each shipped date, derived with git (spec-pyforge-testing-charter:CAP-2 19-1; spec-pyforge-testing-charter:CAP-4 19-3; spec-pyforge-testing-charter:CAP-5 19-4; spec-pyforge-testing-charter:CAP-1 from the commit that put `src/shared/packages/{slug}/tests/**/test_*.py` into the tea glob, found with `git log -S`), then renders once through the anchored script and logs both self-validate passes as `self-validate 2026-11-10 (Story 118.2)`. Frontmatter: the surface comment says what the path governs, `companions` gains `contract.md`, `updated: 2026-11-10` is added. The Why section's station counts are the Spec-authoring measurement and stay, dated. `station-tea-status.md` keeps its table under `## Snapshot at Spec authoring (2026-08-02)` and gains `## Live signal` with the two commands that measure today (`git ls-files ':(glob)src/shared/packages/pyforge-<s>/tests/**/test_*.py' | wc -l`, and `grep -c TBD` on each station's `test-architecture.md`) and no number, since other units add tests inside this PR. spec-pyforge-testing-charter:CAP-7 keeps only the no-host promise; the lane clause sits on spec-pyforge-testing-charter:CAP-3.

Ledger key: `118-2-the-testing-charter-says-what-was-built-and-carries-epic-118-s-capabilities`. Type / Effort / Deps: docs / S / —.

## Boundaries & Constraints

**Always:**
- `SPEC.md` moves only through the anchored script render, never by Edit or Write.
- spec-pyforge-testing-charter:CAP-3, spec-pyforge-testing-charter:CAP-6 and spec-pyforge-testing-charter:CAP-7 read `(ready 2026-11-10)` at this render; Story 117.8 flips them to shipped inside the PR (operator ruling of 2026-11-10), so this story's AC1 holds at its own landing only.
- The AD step is a no-op recorded in the memlog.

**Never:**
- Never re-append the mint's `capability` entries.
- Never write the PRD lines here: Story 114.1 writes FR-253 and FR-254 after this render (CHAIN-STANDARD section 12).
- Never write a ledger mode: spec-pyforge-testing-charter:CAP-3 and spec-pyforge-testing-charter:CAP-4 `rebuild`, spec-pyforge-testing-charter:CAP-1, spec-pyforge-testing-charter:CAP-2 and spec-pyforge-testing-charter:CAP-5 `A-only` with a Story as expiry are steward:S-121.3's rows (operator ruling of 2026-11-10).
- Never append a `Surface reconcile` line to any Spec's memlog and never run `spec_surface_check.py --write-baseline`: the governed paths go in this spec's `surface:`, Story 117.8 reconciles core and the testing charter, and doctor:S-58.4 stamps once.

## Acceptance Criteria

- **AC1 — Every capability carries a dated marker; the three with open stories read ready.**

  ```bash
  python3 -c "import re,sys,pathlib; t=pathlib.Path('_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md').read_text(encoding='utf-8'); caps=dict(re.findall(r'^- \*\*(CAP-\d+) \u2014 .*?\((shipped|ready) \d{4}-\d{2}-\d{2}', t, re.M)); ready=sorted(k for k,v in caps.items() if v=='ready'); print(len(caps), ready); sys.exit(set(caps)!={f'CAP-{i}' for i in range(1,8)} or set(ready)!={'CAP-3','CAP-6','CAP-7'})"
  ```

  Expected: exit 0, prints `7 ['CAP-3', 'CAP-6', 'CAP-7']`.

- **AC2 — The two capabilities are minted through the memlog.**

  ```bash
  grep -cE '^- \(capability[^)]*\) CAP-[67] ' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/.memlog.md
  ```

  Expected: prints 2 (the mint appended the two `capability` entries on 2026-11-10; this story appends neither again).

- **AC3 — Stale text is gone.**

  ```bash
  grep -cE 'generate\.py|not yet created' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md
  ```

  Expected: prints 0 (grep exits 1 on no match).

- **AC4 — contract.md a companion, frontmatter dated, no open question.**

  ```bash
  pixi run -q -e pyforge-guild python -c "import yaml,sys,pathlib; fm=yaml.safe_load(pathlib.Path('_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md').read_text(encoding='utf-8').split('---')[1]); print(fm.get('open_questions'), fm.get('companions'), fm.get('updated')); sys.exit(fm.get('open_questions')!=[] or not any('contract.md' in str(c) for c in (fm.get('companions') or [])) or str(fm.get('updated'))[:10]!='2026-11-10')"
  ```

  Expected: exit 0.

- **AC5 — The companion keeps its snapshot dated and measures today by command, with no number.**

  ```bash
  python3 -c "import re,sys,pathlib; t=pathlib.Path('_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/station-tea-status.md').read_text(encoding='utf-8'); s=t.split('## Live signal')[1].split('\n## ')[0] if '## Live signal' in t else ''; ok=('## Snapshot at Spec authoring (2026-08-02)' in t and 'git ls-files' in s and 'TBD' in s and not re.search(r'^\|.*\b\d+\b.*\|', s, re.M)); print(ok); sys.exit(not ok)"
  ```

  Expected: exit 0, prints `True`.

- **AC6 — SPEC.md moved only through the bmad-spec render.**

  ```bash
  grep -ci 'self-validate.*2026-11-10.*Story 118\.2' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/.memlog.md
  ```

  Expected: prints 2.

- **AC7 — Chain detectors, once the marshal unit's mint of Epic 118 is on the branch.**

  ```bash
  pixi run -e pyforge-guild chain-completeness-check && pixi run -e pyforge-guild fr-without-cap-check
  ```

  Expected: exit 0 each.

</intent-contract>

## Binding

Parent: `spec-pyforge-testing-charter` (spec-pyforge-testing-charter:CAP-1..spec-pyforge-testing-charter:CAP-7; Spec truth and mint; memlog 2026-11-10); spec-one-chain-per-station:CAP-6; no AD.

- Epic: Epic 118 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 118.2: The testing charter says what was built, and carries Epic 118's capabilities`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The shared floor says what it is: core and the testing kit before the cutover.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda (operator, "Accept all, run mint").

## Notes

- Runs first in Epic 118 and is the only render of this `SPEC.md` before Story 117.8.
- Needed by Story 114.1: it writes FR-253 <- spec-pyforge-testing-charter:CAP-6 and FR-254 <- spec-pyforge-testing-charter:CAP-7 (the charter's FRs live in the marshal PRD, FR-128..FR-132) only after this render.
- Deferred row (written by Story 116.5): DW-marshal-118-2-1 (the coverage gate judges the eight stations and neither shared package).
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (core and the testing charter: Story 117.8; marshal: Story 116.5; steward and the host: steward:S-122.5), and doctor:S-58.4 runs every scoped stamp once, after the last edit on the branch.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10, the shared-floor section) and the memlog entries of `spec-pyforge-testing-charter` came first; this story renders `SPEC.md`.
