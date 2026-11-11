---
title: '120.1: The cutover Spec and its decisions name one writer, no fold and a self-hosted Launch'
type: 'docs'
created: '2026-11-10'
status: 'backlog'
flag-exempt: docs-only
difficulty: heavy
story: 120.1
spec: python-foundry-cutover
surface:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/.memlog.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/cutover.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/launch-slice.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/.memlog.md
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/cutover.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The operator's 2026-11-10 rulings changed the cutover contract: A writes every Dream, Frame, Spec and the capability ledger until the flip; the fold path, `apply` and the move manifest retire; Launch is one story B lands on itself; the flip is made by hand, with no loop running, once the Launch slice is proven. The mint re-derived the CAP text only. The markers, companions, Constraints, blockquote, Non-goals and Success signal of SPEC.md, `cutover.md` and the spine's cutover satellite still describe the fold, and no CAP carries a dated marker (D4).

**Approach:** Verify the marker entries the mint's fix pass wrote on 2026-11-11 (fnd:CAP-1, fnd:CAP-6, fnd:CAP-7, fnd:CAP-10, fnd:CAP-12, fnd:CAP-13, fnd:CAP-15), each against the citing stories' ledger keys before keeping ready or shipped, and correct any by a later entry; append memlog entries for the markers of the CAPs whose text the mint amended, the `launch-slice.md` companion, the Constraint, blockquote, Non-goal, Success-signal and frontmatter wording, then re-derive SPEC.md once more through the anchored script render with both self-validate passes logged. Rewrite `cutover.md` (§ The flag and the plan, § The capability ledger, the first-pass table, the Phases table keeping 44.4, 44.5, 44.6 and 44.10 as retired rows, § Move-list manifest as a pointer to the ledger, § Order ending at the flip). Write `launch-slice.md`: the proof sentence, one table (step | A verb or detector | capability `spec-<x>:CAP-n` | A test nodeid or `oracle gap`), derived from a real dispatch journal on A, and a final section naming the doctor sources `detectors-ci` runs with a pointer to `spec-pyforge-doctor` `contract.md` for each import closure. Update the satellite with `bmad-architecture`.

Ledger key: `120-1-the-cutover-spec-and-its-decisions-name-one-writer-no-fold-and-a-self-hosted-launch`. Type / Effort / Deps: docs / L / —.

### Living CAP citations

- **`spec-python-foundry-cutover`** — fnd:CAP-2, fnd:CAP-8 (the writer lock), fnd:CAP-9 (the ledger generator) and fnd:CAP-11, amended 2026-11-10 by memlog and re-derived at mint.

## Boundaries & Constraints

**Always:**
- Every flip sentence states the decided rule: the operator flips `pyforge.cutover_root` by hand, with no loop running, once the Launch slice is proven (B lands one story on itself through its own dispatch and detectors, and every Launch row of the case list reads `verified-in-foundry`); nothing flips it automatically.
- The seed is Dream plus memlog, `archive/**/.memlog.md` included, with no backfill.
- Cite another Spec's capability as `spec-<x>:CAP-n`; `fcl:`/`fnr:` stay only in the existing `## Epic` heading form.
- This story's AD lines land in the spine `.memlog.md` before any steward-station append to it; the spine's `updated:` line and the chain-currency re-stamp are Story 122.5's.

**Never:**
- Never hand-edit SPEC.md; never edit the spine frontmatter.
- Never name a herald consumer of the flag: ruling 2 names three consumers.
- Never write an `(unbuilt)` marker; never mint a capability (the 2026-11-10 entry mints none).
- Never append a `Surface reconcile` line or run `spec_surface_check.py --write-baseline`: Story 122.5 and doctor Story 58.4 do.

## Acceptance Criteria

- **AC1 — no move, moved or moving in the contract.** Expected: each file prints :0 (grep exit 1).
  ```bash
  grep -c -w -E 'move|moved|moving' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/cutover.md _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/launch-slice.md
  ```
- **AC2 — the replay verb is gone.** Expected: each file prints :0 (grep exit 1).
  ```bash
  grep -c 'apply --phase' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/cutover.md
  ```
- **AC3 — 15 CAPs, each with a dated marker on its heading line (no CAP is minted).** Expected: prints `15 0`, exit 0.
  ```bash
  python3 -c "import re,sys;t=open(sys.argv[1]).read();h=re.findall(r'(?m)^- \*\*CAP-\d+ — .*$',t);bad=[x for x in h if not re.search(r'\((ready|shipped|retired) \d{4}-\d{2}-\d{2}|RETIRED \d{4}-\d{2}-\d{2}',x)];print(len(h),len(bad));sys.exit(0 if len(h)==int(sys.argv[2]) and not bad else 1)" _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md 15
  ```
- **AC4 — fnd:CAP-9 no longer promises a drift report; the freeze cites doctor.** Expected: exit 0.
  ```bash
  test $(grep -c 'reports a change under' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md) -eq 0 && grep -q 'spec-pyforge-doctor:CAP-94' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
  ```
- **AC5 — the seam is named.** Expected: 1 or more (exit 0).
  ```bash
  grep -c 'root_of_record() -> RootOfRecord(root, forge_slug, source)' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
  ```
- **AC6 — launch-slice.md exists and is a declared companion.** Expected: exit 0.
  ```bash
  test -f _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/launch-slice.md && grep -q 'launch-slice.md' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
  ```
- **AC7 — SPEC.md is not older than its memlog.** Expected: prints two dates, the first not earlier; exit 0.
  ```bash
  python3 -c "import re,sys;g=lambda p:re.search(r'(?m)^updated:\s*[\x22\x27]?(\d{4}-\d{2}-\d{2})',open(p).read()).group(1);d=sys.argv[1];s,m=g(d+'/SPEC.md'),g(d+'/.memlog.md');print(s,m);sys.exit(0 if s>=m else 1)" _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover
  ```
- **AC8 — the spine satellite names no replay verb, no manifest file and no move state.** Expected: exit 0.
  ```bash
  awk '/^## Satellite: python-foundry cutover/{f=1} /^## Satellite: secure-live-dashboards/{f=0} f' _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md > "$TMPDIR/sat.md" && test $(grep -c -E 'apply --phase|docs/foundry/manifest|moving|move-list' "$TMPDIR/sat.md") -eq 0
  ```
- **AC9 — three new decisions and five retired fold decisions.** Expected: exit 0.
  ```bash
  test $(grep -c -E '^#### fnd:AD-(24|25|26) — ' _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md) -eq 3 && test $(grep -c -E '^#### fnd:AD-(6|7|12|13|15) — .*RETIRED 2026-11-10' _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md) -eq 5
  ```
- **AC10 — fnd:AD-24 states the merge-base rule and the default-source rule.** Expected: exit 0.
  ```bash
  awk '/^#### fnd:AD-24 /{f=1;next} /^#### /{f=0} f' _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md > "$TMPDIR/ad24.md" && grep -q 'merge base' "$TMPDIR/ad24.md" && grep -q "source == 'default'" "$TMPDIR/ad24.md"
  ```
- **AC11 — chain detectors.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-guild dream-chain-check && pixi run -e pyforge-guild chain-sprawl-check && pixi run -e pyforge-guild ad-citation-check
  ```
- **AC12 — fnd:CAP-8 carries the writer lock, both guard halves and exactly ruling 2's consumers (no herald).** Expected: exit 0.
  ```bash
  awk '/^- \*\*CAP-8 — /{f=1;print;next} f&&/^- \*\*CAP-/{f=0} f' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md > "$TMPDIR/cap8.md" && grep -q 'writer lock' "$TMPDIR/cap8.md" && grep -q 'writer-lock' "$TMPDIR/cap8.md" && grep -q '121.4' "$TMPDIR/cap8.md" && grep -q '56.5' "$TMPDIR/cap8.md" && grep -q '115.4' "$TMPDIR/cap8.md" && test $(grep -ci herald "$TMPDIR/cap8.md") -eq 0
  ```
- **AC13 — the decided flip rule is stated in the Spec, cutover.md (twice) and the spine satellite (fnd:AD-17, fnd:AD-22).** Expected: prints three counts (1 or more, 2 or more, 2 or more), exit 0.
  ```bash
  awk '/^## Satellite: python-foundry cutover/{f=1} /^## Satellite: secure-live-dashboards/{f=0} f' _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md > "$TMPDIR/sat.md" && python3 -c "import re,sys;n=lambda p:re.sub(r'\s+',' ',open(p).read());r='by hand, with no loop running, once the Launch slice is proven';c=[n(p).count(r) for p in sys.argv[1:]];print(c);sys.exit(0 if c[0]>=1 and c[1]>=2 and c[2]>=2 else 1)" _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/cutover.md "$TMPDIR/sat.md"
  ```
- **AC14 — no stale or open trigger survives.** Expected: exit 0 (SPEC.md:208 and cutover.md:15 say `after 44.5 today` at mint; cutover.md:73 says `when the dependencies are verified`).
  ```bash
  awk '/^## Satellite: python-foundry cutover/{f=1} /^## Satellite: secure-live-dashboards/{f=0} f' _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md > "$TMPDIR/sat.md" && test $(cat _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/cutover.md "$TMPDIR/sat.md" | grep -c -E "after 44\.5 today|when the dependencies are verified|allowed once the capabilities it depends on|flip is allowed only when|operator's to name|trigger is open") -eq 0
  ```
- **AC15 — the loop-home remotes clause is gone.** Expected: prints 0 (SPEC.md:124 today).
  ```bash
  grep -c 'loop-home remotes' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
  ```
- **AC16 — B keeps its repository, epoch and CI, and the epoch keeps its record.** Expected: prints 1 or more twice.
  ```bash
  grep -c 'B keeps rxm7706/python-foundry' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/.memlog.md && awk '/^#### fnd:AD-16 /{f=1;next} /^#### /{f=0} f' _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md | grep -c 'docs/foundry/EPOCH.md'
  ```

</intent-contract>

## Binding

Parent: `spec-python-foundry-cutover` fnd:CAP-1..15

- Dream: `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the mint entry) and `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth*.
- Epic: Epic 120.
- Ledger key: `120-1-the-cutover-spec-and-its-decisions-name-one-writer-no-fold-and-a-self-hosted-launch` (`backlog` at mint).
- Deps: —.
- Surface: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/cutover.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/launch-slice.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/.memlog.md` (SPEC.md is re-derived by `bmad-spec` through the anchored script render, never by hand; in the spine, only `## Satellite: python-foundry cutover` (never the frontmatter); the spine `.memlog.md` append only).
- Minted 2026-11-10 by the cutover-readiness mint (control-plane unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-guild dream-chain-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild chain-sprawl-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild ad-citation-check` — expected: exit 0.

## Notes

- The CAP text of fnd:CAP-2..5, fnd:CAP-8, fnd:CAP-9, fnd:CAP-11 and fnd:CAP-14 and the fnd:CAP-1 decision (B keeps rxm7706/python-foundry, its epoch and its CI) were written at mint; this story writes the rest.
- The Open Questions line citing `deck-family-lockstep:CAP-1..4` cites `spec-pyforge-herald:CAP-20` to `spec-pyforge-herald:CAP-23`.
- Reword `file-move` and `never move` too: `grep -w` matches both.
- fnd:AD-24..26 are outside the pre-assigned ranges; no other unit mints `fnd:` ADs (highest today fnd:AD-23). Until this story mints fnd:AD-24, fnd:CAP-8 cites it as '(fnd:AD-24, minted by Story 120.1)' (the 2026-11-11 fix pass); this story's re-derive drops the qualifier.
- The kill-switch decision of 2026-11-11 on this Spec's memlog (ruling 5 forbids retrofit switches only) keeps `pyforge.steward.cutover_ledger_write` in fnd:CAP-9; this story changes no flag.
- Cross-station: marshal:S-117.2 builds `root_of_record()`; doctor:S-56.5 builds the `writer-lock` source; marshal:S-115.4 is the forge-remote consumer.
