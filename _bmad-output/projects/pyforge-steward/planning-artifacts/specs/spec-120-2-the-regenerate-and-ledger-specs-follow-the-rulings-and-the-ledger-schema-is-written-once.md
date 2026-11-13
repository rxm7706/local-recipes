---
title: '120.2: The regenerate and ledger Specs follow the rulings, and the ledger schema is written once'
type: 'docs'
created: '2026-11-10'
status: 'done'
flag-exempt: docs-only
difficulty: medium
story: 120.2
spec: foundry-regenerate-not-fold
surface:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/.memlog.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/ab-sync.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/.memlog.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/modes.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/extract.md
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/ab-sync.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/case-list.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Rulings 1, 3 and 4 and the two addenda: `spec-foundry-regenerate-not-fold` and `ab-sync.md` made B the writer after a 48-hour kit, fnr CAP-3 promised a `frames` duty that never existed, and `spec-foundry-capability-ledger` promised less than the ledger must now carry. Two units (this one and doctor) read the schema, so it is written once, here, before Stories 121.1, 121.3, 121.6 and doctor Stories 56.1 and 56.2 build. The mint re-derived the CAP text; markers, companions and the rest of the wording remain.

**Approach:** Verify fcl:CAP-3's marker entry (written in the mint's 2026-11-11 fix pass) against Story 55.3's merge, append memlog entries for each remaining change and re-derive both Specs through the anchored script render, logging both self-validate passes. Write `modes.md` § Schema v1 (header: schema `pyforge.capability-ledger/v1`, generated_by, updated, source_sha, extract, modes [rebuild, retire, A-only, B-only, pending], states [planned, rebuilding, verified-in-foundry, cut], frozen_states [rebuilding]; row key order id, spec, station, heading, path, mode, expiry, state, launch, depends_on, frozen_paths, case_id, pending_on, defaulted, note; expiry always a quoted string `"<station>:<E>.<S>"`, `YYYY-MM-DD` or `flip`; `cells:` rows `cell:conda-forge-expert/<part>`, A-only, expiry "mason:39.2") and § The rules of 2026-11-10 in order: (1) artifact deleted on A: retire; (2) closed one-time campaign, recipe or doctor's: retire; (3) host, platform, portal: A-only "steward:121.5"; (4) row on an archived Spec: absent; (5) testing kit and kernel library: rebuild; (6) conda-forge-expert and what runs through it: A-only "mason:39.2"; (7) never built: B-only when a live `blocked` or `backlog` Story carries it, else retire with `(retired <date>: never built)`; (8) fnd:CAP-12..15 and `pyforge-mason:CAP-29`: A-only "flip"; (9) a row whose two proposals disagree: `pending` on a named operator question; (10) everything else: rebuild, state planned. Pin the marker tokens: `(ready YYYY-MM-DD…)`, `(shipped YYYY-MM-DD…)`, `(retired YYYY-MM-DD[: <reason>])` and the legacy `RETIRED YYYY-MM-DD`. Write `extract.md`: id rule `fnd|fnr|fcl:CAP-n` for the three cutover Specs, `pap:CAP-n` for a prefixed heading, `<spec>:CAP-n` otherwise; heading normalisation as doctor's `extract_caps`; station is the BMAD project that holds the Spec folder.

Ledger key: `120-2-the-regenerate-and-ledger-specs-follow-the-rulings-and-the-ledger-schema-is-written-once`. Type / Effort / Deps: docs / M / —.

### Living CAP citations

- **`spec-foundry-regenerate-not-fold`** — fnr:CAP-1 (the case list is the Launch slice's oracle) to fnr:CAP-5 (A writes until the flip), amended 2026-11-10 and re-derived at mint.
- **`spec-foundry-capability-ledger`** — fcl:CAP-1 (schema v1 and the written rules) and fcl:CAP-2 (the refusals and the expiry clock), amended 2026-11-10 and re-derived at mint.

## Boundaries & Constraints

**Always:**
- The schema lives in `modes.md` § Schema v1 only; every reader (Stories 121.1, 121.3, 121.6, doctor Stories 56.1 and 56.2) cites it.
- Marker qualifiers follow CHAIN-STANDARD § 4 as Story 120.3 amends it (`; not met: <clause>, DW-<id>`).

**Never:**
- Never write a rule that leaves a 2026-11-10 question pending: every one is ruled.
- Never hand-edit SPEC.md; never mint a capability (expiry judging folds into fcl:CAP-2, the rules into fcl:CAP-1).

## Acceptance Criteria

- **AC1 — A is the writer in the protocol.** Expected: 1.
  ```bash
  grep -c '^| Dream, Frame, Spec and the capability ledger | \*\*Writer\*\* until the flip |' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/ab-sync.md
  ```
- **AC2 — B is no longer named the writer.** Expected: each file prints :0.
  ```bash
  grep -c -i 'B is writer\|B is the Frame writer\|Writer\*\* once the 48h kit' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/SPEC.md _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/ab-sync.md
  ```
- **AC3 — fnr:CAP-3 lists no frames duty.** Expected: 0.
  ```bash
  grep -c 'workspace, frames, guards' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/SPEC.md
  ```
- **AC4 — fnr markers.** Expected: prints `5 0`, exit 0.
  ```bash
  python3 -c "import re,sys;t=open(sys.argv[1]).read();h=re.findall(r'(?m)^- \*\*CAP-\d+ — .*$',t);bad=[x for x in h if not re.search(r'\((ready|shipped|retired) \d{4}-\d{2}-\d{2}|RETIRED \d{4}-\d{2}-\d{2}',x)];print(len(h),len(bad));sys.exit(0 if len(h)==int(sys.argv[2]) and not bad else 1)" _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/SPEC.md 5
  ```
- **AC5 — fcl markers, three CAPs (none minted).** Expected: prints `3 0`, exit 0.
  ```bash
  python3 -c "import re,sys;t=open(sys.argv[1]).read();h=re.findall(r'(?m)^- \*\*CAP-\d+ — .*$',t);bad=[x for x in h if not re.search(r'\((ready|shipped|retired) \d{4}-\d{2}-\d{2}|RETIRED \d{4}-\d{2}-\d{2}',x)];print(len(h),len(bad));sys.exit(0 if len(h)==int(sys.argv[2]) and not bad else 1)" _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/SPEC.md 3
  ```
- **AC6 — the schema block parses and carries the header keys and the expiry forms.** Expected: exit 0.
  ```bash
  python3 -c "import re,yaml;t=open('_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/modes.md').read();b=t.split('## Schema v1',1)[1];y=yaml.safe_load(re.search(r'```yaml\n(.*?)```',b,re.S).group(1));assert {'schema','states','frozen_states','modes'}<=set(y) and y['frozen_states']==['rebuilding'] and 'pending' in y['modes'];r=y['capabilities'][0];assert isinstance(r['expiry'],str);assert 'cells' in y"
  ```
- **AC7 — the rule table and the marker tokens are written.** Expected: exit 0.
  ```bash
  grep -q '^## The rules of 2026-11-10' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/modes.md && grep -q '(retired YYYY-MM-DD' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/modes.md && grep -q 'never built' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/modes.md
  ```
- **AC8 — the remode record is a declared companion.** Expected: 1 or more (exit 0).
  ```bash
  grep -c 'remode-2026-11-10.md' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/SPEC.md
  ```
- **AC9 — both SPECs are not older than their memlogs.** Expected: exit 0.
  ```bash
  python3 -c "import re,sys;g=lambda p:re.search(r'(?m)^updated:\s*[\x22\x27]?(\d{4}-\d{2}-\d{2})',open(p).read()).group(1);d=sys.argv[1];s,m=g(d+'/SPEC.md'),g(d+'/.memlog.md');print(s,m);sys.exit(0 if s>=m else 1)" _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold && python3 -c "import re,sys;g=lambda p:re.search(r'(?m)^updated:\s*[\x22\x27]?(\d{4}-\d{2}-\d{2})',open(p).read()).group(1);d=sys.argv[1];s,m=g(d+'/SPEC.md'),g(d+'/.memlog.md');print(s,m);sys.exit(0 if s>=m else 1)" _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger
  ```
- **AC10 — chain detectors.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-guild dream-chain-check && pixi run -e pyforge-guild chain-sprawl-check
  ```
- **AC11 — fnr CAP-2..4 read ready with the prototype qualifier, never shipped.** Expected: prints `3 []`, exit 0.
  ```bash
  python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/SPEC.md').read();h=[l for l in t.splitlines() if re.match(r'- \*\*CAP-[234] — ',l)];bad=[l[:14] for l in h if '(ready 2026-' not in l or 'PR #1344' not in l or '(shipped' in l];print(len(h),bad);sys.exit(0 if len(h)==3 and not bad else 1)"
  ```
- **AC12 — the seed is never Frame + Spec in the regenerate and ledger Specs.** Expected: each file prints :0 (fnr SPEC.md:34, fcl SPEC.md:62 and ab-sync.md:15 today).
  ```bash
  grep -c 'Frame + Spec' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/SPEC.md _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/SPEC.md _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/ab-sync.md
  ```
- **AC13 — rules (2) and (7) say what the 2026-11-10 rulings say, and extract.md states the station rule.** Expected: prints 1 or more four times, exit 0 (no never-built row is left pending: B-only when a live blocked or backlog Story carries it, else retire).
  ```bash
  grep -c 'closed one-time' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/modes.md && grep -c 'never built' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/modes.md && grep -c 'B-only' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/modes.md && test $(grep -c 'never-built row is `pending`' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/modes.md) -eq 0 && grep -c 'BMAD project that holds the Spec folder' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/extract.md
  ```
- **AC14 — neither Spec keeps the flag at local-recipes until a kernel list is green.** Expected: each file prints :0 (the decided flip rule replaces both).
  ```bash
  grep -c 'until the kernel passes the shared list\|until the kernel list is green' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/SPEC.md _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/SPEC.md
  ```

</intent-contract>

## Binding

Parent: `spec-foundry-regenerate-not-fold` fnr:CAP-1..5; `spec-foundry-capability-ledger` fcl:CAP-1..3

- Dream: `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the mint entry) and `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth*.
- Epic: Epic 120.
- Ledger key: `120-2-the-regenerate-and-ledger-specs-follow-the-rulings-and-the-ledger-schema-is-written-once` (`backlog` at mint).
- Deps: —.
- Surface: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/SPEC.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/ab-sync.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/SPEC.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/modes.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/extract.md` (each SPEC.md is re-derived by `bmad-spec` through the anchored script render, never by hand).
- Minted 2026-11-10 by the cutover-readiness mint (control-plane unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-guild dream-chain-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild chain-sprawl-check` — expected: exit 0.

## Notes

- `case-list.md` is Story 120.5's; `remode-2026-11-10.md` is Story 121.3's (declared here only).
- Each owner Dream (`docs/dreams/foundry-regenerate-not-fold.md`, `docs/dreams/foundry-capability-ledger.md`) takes a dated 2026-11-10 Realization-log pointer line, written at mint (by the integrator: those files are outside the steward mint's owned paths); this story writes none.
- Cross-station: doctor:S-56.1 and doctor:S-56.2 read this story's schema; name this story spec in their inputs.
