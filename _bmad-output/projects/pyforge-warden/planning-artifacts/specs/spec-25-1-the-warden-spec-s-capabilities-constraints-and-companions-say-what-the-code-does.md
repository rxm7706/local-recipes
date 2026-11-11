---
title: "25.1: The warden Spec's capabilities, constraints and companions say what the code does"
type: 'docs'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: 'heavy'
story: '25.1'
spec: _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
surface:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/verdict-contract.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/axes.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/glossary.md
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - docs/dreams/pyforge-warden.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/hooks.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/scanner_plugins.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/sbom.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/mapping.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The read-only cutover readiness audit at main `82a2b18828` (`_bmad-output/projects/pyforge-warden/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md`) found `spec-pyforge-warden` resolving against the tree but not ready for a rebuild from Frame + Spec. It names none of the nine feature flags that gate CAP-24..CAP-26; four capabilities read `ready` after their stories landed on 2026-11-01; it states things the code lacks (`review_required`, a snapshot age on the conda-to-pypi map, `--deterministic` pinning) and leaves out what the code does (the default KEV gate, six scan flags, the forge and feed environment variables); no capability carries the PR-gate hook book; the Spec text still carries other capabilities' clauses and stale counts; and the memlog has no capability entry for CAP-13..CAP-22.

**Approach:** **The capability text is already rendered.** The mint of 2026-11-10 applied every capability mint and amendment of this change through memlog entries and the anchor-asserting script render, with both self-validate passes logged: CAP-27 (the hook book) and CAP-29 (the fleet's portal half, split from CAP-26 by the operator's ruling) minted shipped, CAP-28 minted ready, CAP-5..CAP-7 and CAP-9..CAP-26 amended (CAP-8 was not), CAP-23..CAP-26 moved to `(shipped 2026-11-01)` (decision D4), and a capability entry appended for CAP-13..CAP-22 from the archived memlogs and the pre-fold Specs at `548e907247^`. This story checks that text against the code and against this spec, and corrects it the same way if it drifted.

**Then the non-capability text**, each change a memlog entry (`constraint`, `correction` or `assumption`) followed by the script render:
1. *Runtime shape*: Python ≥ 3.14 (the package's `requires-python`; 22 PEP 758 `except` sites). Decision D6.
2. *Bundled data carries its own age*: the LTS registry carries `updated:` and a 180-day maximum age; the conda-to-pypi map carries no snapshot and no age check, an absent name is "no candidate" and is withheld, and a stale wrong mapping is not detected. Operator ruling 2026-11-10: the narrowed Constraint stands and no map age gate is built (row `DW-warden-cutover-2026-11-10-1`, Story 25.4).
3. *Determinism discipline*: `--deterministic` is reserved and pins nothing today; the report is byte-identical by default; the SBOM's `serialNumber` and `metadata.timestamp` are volatile. Operator ruling 2026-11-10 (row `-2`).
4. The schema Constraint: the report stays closed at 1.1.0 (operator ruling 2026-11-10, row `-3`); the `advisory` and `actuation` slots are open there and their key sets are in `contract.md`.
5. *Naming is a contract*: other packages import only the symbols `contract.md` names.
6. Assumptions: no story or epic count is written; the line points at `sprint-status-ledger.yaml` as the count of record; `tests/conformance/` was renamed `tests/integration/` on 2026-09-07 (`aec4c74f6e`), so older story specs cite the old path; each capability's proving modules, lane and command are in `proof-map.md`, because CAP-1..CAP-22's success clauses predate the 2026-11-01 rule.
7. The split's pointers: the Non-goal *A fleet-level verdict* and *No silent egress* name CAP-29 for the fleet run and its clones (CAP-26 keeps the read-only clients); *Runtime shape*'s non-Python scope sentence keeps CAP-26.
8. Frontmatter: one `updated:` key, and its comment's "CAP-5..CAP-26 amended" reads "CAP-5..CAP-7 and CAP-9..CAP-26 amended" (the mint's `(correction)` memlog entry: CAP-8 was not amended). `companions:` gains `contract.md` and `proof-map.md` in Story 25.2, after both files exist; the body names them from the mint. The `surface:` block does not change: by the operator's ruling of 2026-11-10 `spec-pyforge-warden` does not co-govern `django-warden`, and `contract.md`'s table of where each capability lives is the answer.
9. Companions: `verdict-contract.md` loses `review_required` (line 104); `axes.md` Axis 2 names `fail-on-kev` and its default, and its Provenance row says the LTS registry, not "bundled data"; `glossary.md` gains `contract.md`, `proof-map.md` and CAP-27 pointers.

Each capability keeps its bold heading bullet, provenance arrow, marker parenthesis, intent and success, the shape the capability-ledger extract and `fr-without-cap` read. No marker reads retired or unbuilt: the operator's addendum of 2026-11-10 ("Retire both") names atlas and mason capabilities only. CAP-13..CAP-15 are built and tested, an uncalled library; by the operator's ruling their mode is `A-only` with expiry steward Story 44.8, a ledger row the control plane writes.

Ledger key: `25-1-the-warden-spec-s-capabilities-constraints-and-companions-say-what-the-code-does`.
Type / Effort / Deps: docs / L / —.

### Living CAP citations

- spec-pyforge-warden CAP-27 (FR-44): minted at the mint for the hook book Stories 9.1–9.3 shipped (2026-08-24). Its code, `hooks.py` and `scanner_plugins.py`, is no CLI, MCP, REST or portal entry point, so `scripts/flag_inventory.py` classes it `module`.
- spec-pyforge-warden CAP-29 (FR-43 re-traced): the portal half of CAP-26, minted at the mint by the operator's ruling of 2026-11-10; mode `A-only`, expiry steward Story 121.5.
- spec-pyforge-warden CAP-5..CAP-7 and CAP-9..CAP-26: their text, corrected (CAP-8 unchanged; no other CAP minted).
- Decisions D4 (markers move with landings) and D6 (Python floor 3.14) of the 2026-11-10 cutover readiness plan; the operator ruling of 2026-09-14 (`review_required` is not built).
- `spec-feature-flag-governance` Q1: a `docs` story needs no flag.

## Boundaries & Constraints

**Always:**
- Append the memlog first, then run the anchor-asserting script render through Bash, first on a dry-run copy; log both self-validate passes as `(event)` entries labelled `Story 25.1 self-validate pass 1/2` and `Story 25.1 self-validate pass 2/2` (AC9 counts those labels, not the mint's two passes).
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not Edit or Write `SPEC.md` (the session hook denies it).
- Do not change product code or add a flag.
- Do not append a `Surface reconcile` line to another Spec's memlog or run `spec_surface_check.py --write-baseline`: Story 25.2 writes warden's reconcile event and doctor Story 58.4 stamps.
- Do not write a story or epic count into the Spec.

</intent-contract>

## Acceptance Criteria

- **AC1 — No capability but the new CAP-28 still reads (ready ...).** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md').read();sys.exit(1 if re.search(r'^- \*\*CAP-(?!28 )\d+ [^\n]*\(ready ',t,re.M) else 0)"`
  Expect: exit 0.
- **AC2 — 29 capability definition lines (CAP-27, CAP-28 and CAP-29 minted at the mint).** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,sys;n=len(re.findall(r'^- \*\*CAP-\d+ — ',open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md').read(),re.M));print(n);sys.exit(0 if n==29 else 1)"`
  Expect: prints 29, exit 0.
- **AC3 — All nine feature-flag keys are named, with the per-environment truth.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md').read();m=[x for x in ['pyforge.warden.fix_target_resolution', 'pyforge.warden.fix_manifest_edit', 'pyforge.warden.fix_draft_pr_estate', 'pyforge.warden.sast_opengrep', 'pyforge.warden.non_python_ecosystems', 'pyforge.warden.fleet_inventory', 'pyforge.warden.fleet_scan', 'pyforge.warden.fleet_fix_proposals', 'pyforge.warden.fleet_project_items']+['flag-overlays.json','production','PYFORGE_ENVIRONMENT'] if x not in t];print(m);sys.exit(1 if m else 0)"`
  Expect: prints [], exit 0.
- **AC4 — review_required is gone from the Spec and its verdict companion.** Run from the repo root, verdict from the exit code (never through a pipe):
  `bash -c '! grep -q review_required _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/verdict-contract.md'`
  Expect: exit 0.
- **AC5 — The Runtime-shape Constraint states Python 3.14.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md').read();sys.exit(0 if 'Python ≥ 3.14' in t and 'Python ≥ 3.12' not in t else 1)"`
  Expect: exit 0.
- **AC6 — What the code does is stated, and the false network sentence is not.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md').read();b=[s for s in ('fail-on-kev','changes nothing','OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY','PYFORGE_WARDEN_FEED_CACHE_DIR','GITHUB_REPOSITORY','--sbom-output','--baseline-emit','--pixi-environment','contract.md','proof-map.md') if s not in t]+[s for s in ('only network users',) if s in t];print(b);sys.exit(1 if b else 0)"`
  Expect: prints [], exit 0.
- **AC7 — Absorbed numbering and stale counts are gone; Assumptions point at the ledger and record the test-tree rename.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md').read();b=[s for s in ('CAP-1 set','43 story keys','CAP-2 eligibility-union','CAP-2 results') if s in t]+[s for s in ('sprint-status-ledger.yaml','tests/conformance/') if s not in t];print(b);sys.exit(1 if b else 0)"`
  Expect: prints [], exit 0.
- **AC8 — The memlog carries a capability entry for each of CAP-13..CAP-22 and CAP-27..CAP-29 (either tag form).** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md').read();m=[n for n in list(range(13,23))+[27,28,29] if not re.search(r'^- \(capability(?: by [^)]+)?\) CAP-%d\b'%n,t,re.M)];print(m);sys.exit(1 if m else 0)"`
  Expect: prints [], exit 0.
- **AC9 — Both self-validate passes of this story's re-derive are logged (the mint's two do not count).** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md').read();s=sorted(set(re.findall(r'^- \(event[^)]*\) [^\n]*Story 25\.1 self-validate pass ([12])/2',t,re.M)));print(s);sys.exit(0 if s==['1','2'] else 1)"`
  Expect: prints ['1', '2'], exit 0.
- **AC10 — axes.md names the KEV key.** Run from the repo root, verdict from the exit code (never through a pipe):
  `grep -c 'fail-on-kev' _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/axes.md`
  Expect: prints a number >= 1, exit 0.
- **AC11 — The bundled-data age claim is narrowed to the LTS registry in the Spec and axes.md (the conda-to-pypi map carries no snapshot).** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md').read();a=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/axes.md').read();b=[s for s in ('The LTS registry and the conda→pypi map carry a build-time','verdicts derived from bundled data carry') if s in t+a];print(b);sys.exit(1 if b or 'Bundled data carries its own age' not in t else 0)"`
  Expect: prints [], exit 0 (the two old phrases are gone; the Constraint heading stays).
- **AC12 — Chain and status detectors.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run -e pyforge-guild chain-completeness-check && pixi run -e pyforge-guild status-body-consistency-check && pixi run -e pyforge-guild ad-citation-check`
  Expect: exit 0.
- **AC13 — Determinism discipline no longer promises pinning, and the fleet pointers name CAP-29.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md').read();l=lambda h:(re.search(r'(?m)^- \*\*'+re.escape(h)+r'[^\n]*',t) or [''])[0];b=[n for n,ok in (('determinism pins',re.search(r'deterministic\S* pins the documented volatile-field set',t) is None),('fleet-level verdict',bool(l('A fleet-level verdict')) and 'CAP-29' in l('A fleet-level verdict')),('no silent egress',bool(l('No silent egress.')) and 'CAP-29' in l('No silent egress.'))) if not ok];print(b);sys.exit(1 if b else 0)"`
  Expect: prints [], exit 0 (the *Determinism discipline* Constraint no longer says `--deterministic` pins a volatile-field set; the Non-goal *A fleet-level verdict* and the *No silent egress* Constraint each name CAP-29).
- **AC14 — The frontmatter has one `updated:` key, and its comment no longer claims CAP-8 was amended (Approach item 8).** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import sys;fm=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md').read().split('---',2)[1];b=[s for s in ('CAP-5..CAP-26 amended',) if s in fm]+[s for s in ('CAP-5..CAP-7 and CAP-9..CAP-26 amended',) if s not in fm]+(['updated: keys != 1'] if fm.count(chr(10)+'updated:')!=1 else []);print(b);sys.exit(1 if b else 0)"`
  Expect: prints [], exit 0 (exits 1 on the mint's render, whose comment still reads "CAP-5..CAP-26 amended").

## Binding

- Story: `_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md` § *Story 25.1: The warden Spec's capabilities, constraints and companions say what the code does*.
- Dream: `docs/dreams/pyforge-warden.md`, Realization log, *2026-11-10 (the cutover readiness audit)*; the operator's rulings of 2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md`, Realization log, second addendum).
- Ledger key: `25-1-the-warden-spec-s-capabilities-constraints-and-companions-say-what-the-code-does`.
- Deps: —.
- Flag: none (a `docs` story, `spec-feature-flag-governance` Q1).
