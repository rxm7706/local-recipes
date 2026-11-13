---
title: "117.5: The core Spec says what the leaf is, and carries Epic 117's capabilities"
type: 'docs'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: medium
story: '117.5'
spec: pyforge-core
surface:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-113-18-the-first-automated-audit-lands-its-residue.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Decision D4 of the 2026-11-10 design pass and the audit's MUST 6: at `82a2b18828` the core Spec is wrong where the code is right. No capability carries a status marker; the Non-goals say `Six primitives` and `Not the station roster, yet`; Q1..Q3 stand open though the code answered them; spec-pyforge-core:CAP-9 names the kit exemption retired on 2026-09-30 and spec-pyforge-core:CAP-10 the `coverage-gates.yml` deleted on 2026-10-27; the frontmatter says `# net-new, not yet created` and names two archived Specs. This is also the one mint-time re-derive of spec-pyforge-core before the build stories start, so no two sessions render one `SPEC.md`.

**Approach:** The mint of 2026-11-10 appended to this Spec's memlog: the Dream direction, the rulings decision, the `capability` entries for spec-pyforge-core:CAP-12, spec-pyforge-core:CAP-13 and spec-pyforge-core:CAP-14, the `change` entries for spec-pyforge-core:CAP-7, spec-pyforge-core:CAP-8 and spec-pyforge-core:CAP-1/spec-pyforge-core:CAP-5/spec-pyforge-core:CAP-6, the `correction` entries for spec-pyforge-core:CAP-9 and spec-pyforge-core:CAP-10, the marker-sweep direction, the companion event and the chain-steps event. This story appends, with `uv run _bmad/scripts/memlog.py append --workspace _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core` from the repository root: (change) the status markers, each shipped date derived with `git log` from the merge carrying the realizing ledger key (spec-pyforge-core:CAP-1 14-1; spec-pyforge-core:CAP-2 14-2; spec-pyforge-core:CAP-3, spec-pyforge-core:CAP-4 and spec-pyforge-core:CAP-5 14-3; spec-pyforge-core:CAP-6 14-4; spec-pyforge-core:CAP-9 52-1; spec-pyforge-core:CAP-10 63-1; spec-pyforge-core:CAP-11 71-1), never typed from memory; (question) Q1 closed: the roster lives in `pyforge.core.roster` since steward Story 59.6 (spec-pyforge-steward:CAP-137, 2026-09-25); (question) Q2 closed: the kit is its own package (Q-26, Story 19.2) and its stdlib-leaf premise retired 2026-09-30 (Story 74.1); (question) Q3 closed: ProcessPort won in Story 14.4 and steward is a sanctioned station-level opt-out; (non-goal) `Six primitives` becomes: six primitives sit under this Spec's capabilities and the leaf also hosts modules whose capability is on another Spec, listed with their governor in `contract.md` (no count), while `Not a plugin system` and `Not the station roster, yet` retire; (constraint) `Leaf or nothing` states the dynamic OpenFeature load; (constraint) `No new primitive earns a place on one caller` records how the hosted modules were admitted and that `league_measure` has no importer; (correction) frontmatter: the `# net-new, not yet created` and `the copies each extraction retires` comments say why each station's `src` is on the surface (the sole-ownership scans read it), the surface-drift-exclude comments naming the archived spec-run-state-one-publisher and spec-dispatch-tier-routing-fails-safe name spec-pyforge-marshal, `owner-dream` points at `docs/dreams/pyforge-marshal.md`, `companions: [contract.md]`, `open_questions: []`, `updated: 2026-11-10`. Then the anchored script render (the per-PR approval of 2026-11-10: a python3 script that asserts each anchor occurs exactly once before replacing it), and both self-validate passes logged as memlog events with the text `self-validate 2026-11-10 (Story 117.5)`. The render also clears the five lower-case `2026-10-27 surface reconcile` events scribe:S-32.3 counts as unrendered. The Why section's census is dated history and stays.

Ledger key: `117-5-the-core-spec-says-what-the-leaf-is-and-carries-epic-117-s-capabilities`. Type / Effort / Deps: docs / M / —.

## Boundaries & Constraints

**Always:**
- `SPEC.md` moves only through the anchored script render, never by Edit or Write.
- spec-pyforge-core:CAP-7, spec-pyforge-core:CAP-8, spec-pyforge-core:CAP-12, spec-pyforge-core:CAP-13 and spec-pyforge-core:CAP-14 read `(ready 2026-11-10)` at this render; Story 117.8 flips them to shipped inside the PR (operator ruling of 2026-11-10), so this story's AC1 holds at its own landing only.
- The AD step is a no-op recorded in the memlog: spec-pyforge-core:CAP-12..spec-pyforge-core:CAP-14 land on AD-66..AD-69 as written (spec-pyforge-core:CAP-13 also on fnd:AD-11 and fnd:AD-17).

**Never:**
- Never narrow the `surface:` paths: spec-pyforge-core keeps its surface (operator ruling of 2026-11-10).
- Never re-append the mint's `capability` entries, and never write a count of modules into the Non-goals.
- Never write the PRD lines here: Story 114.1 writes FR-250..FR-252 after this render (CHAIN-STANDARD section 12).
- Never append a `Surface reconcile` line to any Spec's memlog and never run `spec_surface_check.py --write-baseline`: the governed paths go in this spec's `surface:`, Story 117.8 reconciles core and the testing charter, and doctor:S-58.4 stamps once.

## Acceptance Criteria

- **AC1 — Every capability carries a dated marker; the five with open stories read ready.**

  ```bash
  python3 -c "import re,sys,pathlib; t=pathlib.Path('_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md').read_text(encoding='utf-8'); caps=dict(re.findall(r'^- \*\*(CAP-\d+) \u2014 .*?\((shipped|ready) \d{4}-\d{2}-\d{2}', t, re.M)); ready=sorted(k for k,v in caps.items() if v=='ready'); print(len(caps), ready); sys.exit(set(caps)!={f'CAP-{i}' for i in range(1,15)} or set(ready)!={'CAP-7','CAP-8','CAP-12','CAP-13','CAP-14'})"
  ```

  Expected: exit 0, prints `14 ['CAP-12', 'CAP-13', 'CAP-14', 'CAP-7', 'CAP-8']`.

- **AC2 — The three capabilities are minted through the memlog.**

  ```bash
  grep -cE '^- \(capability[^)]*\) CAP-1[234] ' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md
  ```

  Expected: prints 3 (the mint appended the three `capability` entries on 2026-11-10; this story appends none of them again).

- **AC3 — Stale text is gone.**

  ```bash
  grep -cE 'coverage-gates\.yml|Six primitives|not yet created|Not the station roster, yet|spec-run-state-one-publisher|spec-dispatch-tier-routing-fails-safe|copies each extraction retires' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
  ```

  Expected: prints 0 (grep exits 1 on no match).

- **AC4 — Open questions closed, contract.md a companion, frontmatter dated.**

  ```bash
  pixi run -q -e pyforge-guild python -c "import yaml,sys,pathlib; fm=yaml.safe_load(pathlib.Path('_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md').read_text(encoding='utf-8').split('---')[1]); print(fm.get('open_questions'), fm.get('companions'), fm.get('updated')); sys.exit(fm.get('open_questions')!=[] or not any('contract.md' in str(c) for c in (fm.get('companions') or [])) or str(fm.get('updated'))[:10]!='2026-11-10')"
  ```

  Expected: exit 0.

- **AC5 — Non-goals point at contract.md for the module list and state no count.**

  ```bash
  python3 -c "import re,sys,pathlib; t=pathlib.Path('_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md').read_text(encoding='utf-8'); s=t.split('## Non-goals')[1].split('## Success signal')[0]; bad=re.findall(r'\b(?:six|\d+) (?:primitives|modules)\b', s, re.I); print(bad, 'contract.md' in s); sys.exit(bool(bad) or 'contract.md' not in s)"
  ```

  Expected: exit 0, prints `[] True`.

- **AC6 — SPEC.md moved only through the bmad-spec render.**

  ```bash
  grep -ci 'self-validate.*2026-11-10.*Story 117\.5' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md
  ```

  Expected: prints 2 (Pass 1 and Pass 2, each naming the date and the story).

- **AC7 — Chain detectors, once the marshal unit's mint of Epics 117 and 118 is on the branch.**

  ```bash
  pixi run -e pyforge-guild chain-completeness-check && pixi run -e pyforge-guild fr-without-cap-check && pixi run -e pyforge-guild dream-chain-check
  ```

  Expected: exit 0 each.

</intent-contract>

## Binding

Parent: `spec-pyforge-core` (spec-pyforge-core:CAP-1..spec-pyforge-core:CAP-14; Spec truth and mint; memlog 2026-11-10); spec-one-chain-per-station:CAP-6; AD-66..AD-69 (no AD moves).

- Epic: Epic 117 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 117.5: The core Spec says what the leaf is, and carries Epic 117's capabilities`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The shared floor says what it is: core and the testing kit before the cutover.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda (operator, "Accept all, run mint").

## Notes

- Runs first in Epic 117: every other Epic 117 story depends on it.
- Needed by Story 114.1: it writes FR-250 <- spec-pyforge-core:CAP-12, FR-251 <- spec-pyforge-core:CAP-13 and FR-252 <- spec-pyforge-core:CAP-14 only after this render, because `fr-without-cap` resolves a cite only against a capability the named Spec defines.
- Incoming memlog lines from other units in this PR are accepted append-only, written `(event) Surface reconcile 2026-11-10 (...)`, merged main-first with one `updated:` frontmatter key kept; none of them stamps.
- Deferred rows (written by Story 116.5): DW-marshal-117-5-1 (the OpenFeature path of `read_boolean` always skips where the core suite runs), DW-marshal-117-5-2 (B's pyforge-core is the PR #1344 prototype; ruling 1).
- The chain-currency sweep is not this story's check: it is red for every station from the 2026-11-10 research files until that station's closer re-stamps.
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (core and the testing charter: Story 117.8; marshal: Story 116.5; steward and the host: steward:S-122.5), and doctor:S-58.4 runs every scoped stamp once, after the last edit on the branch.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10, the shared-floor section) and the memlog entries of `spec-pyforge-core` came first; this story renders `SPEC.md`.
