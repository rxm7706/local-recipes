---
title: '122.1: The steward Spec''s markers, numbers and names match the tree, and restore and revoke have a capability'
type: 'docs'
created: '2026-11-10'
status: 'backlog'
flag-exempt: docs-only
difficulty: heavy
story: 122.1
spec: pyforge-steward
surface:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/briefs/brief-pyforge-steward-2026-07-25/brief.md
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

<intent-contract>

## Intent

**Problem:** Spec text is wrong where the code is right (MUST 6 and MUST 7 of the 2026-11-10 audit): a gone verb, a never-written driver, stale counts and line references, markers that lag their stories, archive-only companions, and two shipped duties with no capability. It is the one story that re-derives the steward SPEC.md in this PR, so it also carries control-plane's CAP-53 and CAP-6 requests and core-kit's CAP-46 finding.

**Approach:** Verify each memlog `change` entry the Notes below list (written in the mint's fix pass on 2026-11-11) against the ledger, the merges and the tree, and append a correcting `change` entry wherever the tree differs: a `(ready <date>)` marker becomes `(shipped <date>)` only when every citing story reads `done`, the date being the merge day of the last one; then one bmad-spec re-derive (the anchored script render approved for this PR, both self-validate passes logged), then the cascade: brief, PRD, spine and epics `updated:` re-stamped once with a Currency reconciliation section naming this re-derive and the three cutover-Spec re-derives (FR delta: FR-53..FR-56, written at mint).

Ledger key: `122-1-the-steward-spec-s-markers-numbers-and-names-match-the-tree-and-restore-and-revoke-have-a-capability`. Type / Effort / Deps: docs / L / S-120.1, S-120.2, S-120.3, S-120.4, S-120.5.

### Living CAP citations

- **`spec-pyforge-steward` CAP-180** — `steward restore --drill` and `steward revoke --sub` drive the host's own commands and own the exit code; minted 2026-11-10 `(shipped 2026-09-02)` and rendered at mint, its success corrected and re-rendered in the fix pass of 2026-11-11 (no message names `--python`). The amendments of existing capabilities below are memlog entries written in that fix pass, verified and rendered here.

## Boundaries & Constraints

**Always:**
- Every amendment is a memlog `change` entry before the re-derive (the fix pass wrote them; a correction is a later entry, never an edit); never edit SPEC.md by hand.
- Verify every marker date against the ledger and the citing story's merge before writing it; a capability with an open story keeps `ready`, a story of this PR included: CAP-153 (Story 124.3 builds the package `pixi.toml` floor clause) and CAP-166 (Story 124.2 adds the registry rows) keep `ready` here, and Story 122.5 flips them.
- Use CHAIN-STANDARD section 4's marker grammar as Story 120.3 amends it (`(retired <date>[: <reason>])`, `; superseded by CAP-n`); no `(unbuilt)` token.

**Never:**
- Never change code or tests.
- Never amend CAP-21 (13 is the active suite membership the code asserts).
- Never touch the spine's cutover satellite (from `## Satellite: python-foundry cutover` up to `## Satellite: secure-live-dashboards`; Story 120.1's, which rewrites it first, so no line number holds) or the Epic 44 block and binding lines of epics.md (Story 120.3's).
- Never append a `Surface reconcile` line or run a stamp.

## Acceptance Criteria

- **AC1 — every capability heading leads its parenthesis with a marker.** Expected: exit 0; prints `182 []` (178 capabilities plus the four minted).
  ```bash
  python3 -c "import re,sys;L=[l for l in open('_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md') if re.match(r'- \*\*CAP-\d+ — ',l)];bad=[l[:22] for l in L if not re.search(r'\((ready|shipped|retired) \d{4}-\d{2}-\d{2}',l)];print(len(L),bad);sys.exit(bool(bad))"
  ```
- **AC2 — only capabilities with an open story read ready.** Expected: prints `[153, 165, 166, 172, 173, 175, 176, 177, 178, 179, 181, 182]`; CAP-153 and CAP-166 keep `ready` because Stories 124.3 and 124.2 of this PR cite them and are open at this story's wave; CAP-180 is minted `(shipped 2026-09-02; ...)` because its duties landed then; CAP-153, CAP-166, CAP-179, CAP-181 and CAP-182 flip in the closing pass (Story 122.5).
  ```bash
  python3 -c "import re;print(sorted(int(m.group(1)) for l in open('_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md') for m in [re.match(r'- \*\*CAP-(\d+) — .*\(ready \d{4}',l)] if m))"
  ```
- **AC3 — no capability id is defined twice.** Expected: exit 0; prints `[]`.
  ```bash
  python3 -c "import re,sys,collections;c=collections.Counter(m.group(1) for l in open('_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md') for m in [re.match(r'- \*\*(CAP-\d+)\b',l)] if m);d=[k for k,v in c.items() if v>1];print(d);sys.exit(bool(d))"
  ```
- **AC4 — CAP-2 is retired by name.** Expected: prints 1.
  ```bash
  grep -cE '^- \*\*CAP-2 — .*\(retired 2026-10-15; superseded by CAP-168\)' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  ```
- **AC5 — every Spec line naming the gone verb says it is gone.** Expected: prints 0.
  ```bash
  grep -n 'deploy dashboard' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md | grep -vcE 'retired|removed|replac|no other tracked file'
  ```
- **AC6 — every PRD and spine line naming the gone verb points at the supersession.** Expected: prints 0.
  ```bash
  grep -n 'deploy dashboard' _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md | grep -vcE 'supersed|retire|removed|deleted|amended|history'
  ```
- **AC7 — no script that was never written.** Expected: prints 0 for each file.
  ```bash
  grep -c 'station_suite_ci' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  ```
- **AC8 — no pixi.toml line references.** Expected: prints 0.
  ```bash
  grep -cE 'pixi\.toml:[0-9]+' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  ```
- **AC9 — no stale task count.** Expected: prints 0.
  ```bash
  grep -c '51 Guild' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  ```
- **AC10 — the suite count stays 13.** Expected: prints 1 (CAP-21 is right and is not amended).
  ```bash
  grep -c 'each of the 13 packages' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  ```
- **AC11 — CAP-46 says who calls the validator.** Expected: prints 1 or more (0 today).
  ```bash
  awk '/^- \*\*CAP-46 —/{f=1;print;next} f&&/^- \*\*CAP-/{f=0} f' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md | grep -c 'validate_measure_cite'
  ```
- **AC12 — CAP-46's never-built consumer half is marked retired and its validator stays shipped (operator ruling 2026-11-10).** Expected: prints 1 or more, then 1.
  ```bash
  awk '/^- \*\*CAP-46 —/{f=1;print;next} f&&/^- \*\*CAP-/{f=0} f' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md | grep -c 'retired 2026-11-10: never built' && grep -cE '^- \*\*CAP-46 — .*\(shipped 2026-09-15' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  ```
- **AC13 — control-plane's CAP-53 entry is rendered.** Expected: prints 1 or more (0 today).
  ```bash
  awk '/^- \*\*CAP-53 —/{f=1;print;next} f&&/^- \*\*CAP-/{f=0} f' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md | grep -c 'pointer'
  ```
- **AC14 — no Constraint lead shaped like a capability heading.** Expected: prints 0.
  ```bash
  grep -cE '^- \*\*CAP-[0-9]+ \(' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  ```
- **AC15 — archive-only companions carry their path.** Expected: prints 0.
  ```bash
  grep -cE '`(cutover-readiness|retire-skip|pixitainer-eval|backends-and-sources|later-caps|transports-and-vendors)\.md`' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  ```
- **AC16 — chain.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild chain-completeness-check
  ```
- **AC17 — fr arrows.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild fr-without-cap-check
  ```
- **AC18 — citations.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild ad-citation-check
  ```
- **AC19 — names resolve.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild governance-currency
  ```
- **AC20 — ledger and story status.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild story-status-check
  ```
- **AC21 — the Spec is not behind its memlog.** Expected: exit 0; prints two equal dates or the Spec's later.
  ```bash
  python3 -c "import re,sys;d='_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/';s=re.search(r'^updated: \"?(\d{4}-\d{2}-\d{2})',open(d+'SPEC.md').read(),re.M).group(1);m=re.search(r'^updated: (\d{4}-\d{2}-\d{2})',open(d+'.memlog.md').read(),re.M).group(1);print(s,m);sys.exit(s<m)"
  ```

</intent-contract>

## Binding

Parent: `spec-pyforge-steward` CAP-180 (minted 2026-11-10) and the markers and text of the existing capabilities the Notes list

- Dream: `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth* (subsection *The steward Spec, suite and shared surfaces*) and `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the steward-station mint entry).
- Epic: Epic 122.
- Ledger key: `122-1-the-steward-spec-s-markers-numbers-and-names-match-the-tree-and-restore-and-revoke-have-a-capability` (`backlog` at mint).
- Deps: S-120.1, S-120.2, S-120.3, S-120.4, S-120.5.
- Surface: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md` (re-derive only), `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md` (the `change` entries), `_bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md` (pointers on the FR-8..FR-11, UJ-2, D6 and SM-2 lines, the driver line and the Currency reconciliation section), `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md` (the pointer on AD-4's `steward deploy dashboard` **Rule:** line, the `station_suite_ci.py` bullet (**No duty, port or adapter.**) of § *Currency reconciliation — 2026-10-27 (CAP-175)*, and the frontmatter `updated:`; anchored by content, since Story 120.1 rewrites the satellite above them first; not the cutover satellite, which is Story 120.1's), `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md` (the frontmatter `updated:` and currency lines only), `_bmad-output/projects/pyforge-steward/planning-artifacts/briefs/brief-pyforge-steward-2026-07-25/brief.md`.
- Minted 2026-11-10 by the cutover-readiness mint (steward-station unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `python3 -c "import re,sys;L=[l for l in open('_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md') if re.match(r'- \*\*CAP-\d+ — ',l)];bad=[l[:22] for l in L if not re.search(r'\((ready|shipped|retired) \d{4}-\d{2}-\d{2}',l)];print(len(L),bad);sys.exit(bool(bad))"` — expected: exit 0; prints `182 []` (178 capabilities plus the four minted).
- `python3 -c "import re;print(sorted(int(m.group(1)) for l in open('_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md') for m in [re.match(r'- \*\*CAP-(\d+) — .*\(ready \d{4}',l)] if m))"` — expected: prints `[153, 165, 166, 172, 173, 175, 176, 177, 178, 179, 181, 182]`; CAP-153 and CAP-166 keep `ready` (Stories 124.3 and 124.2 of this PR cite them and are open); CAP-180 is minted `(shipped 2026-09-02; ...)` because its duties landed then; CAP-153, CAP-166, CAP-179, CAP-181 and CAP-182 flip in the closing pass (Story 122.5).

## Notes

- Cross-station: none. Same-station deps: Stories 120.1..120.5 (control-plane) move the Frames, launch-slice.md, case-list.md and two cutover memlogs first, so the cascade runs after every control-plane planning edit.
- CAP-180 was minted at mint as `(shipped 2026-09-02; minted 2026-11-10 for Stories 41.1 and 42.2)`: restore.py and revoke.py first landed 2026-09-02 and both stories are done. It reads no kill switch; the operator's 2026-11-10 ruling adds none, and Story 122.5 writes the deferred row (DW-steward-cutover-2026-11-10-2).
- CAP-46 (operator ruling 2026-11-10): the validator `pyforge.core.league_measure.validate_measure_cite` stays `(shipped 2026-09-15)`; the consumer half no station built is text marked `(retired 2026-11-10: never built)`.
- CAP-2's date: Story 102.3 reached main in 38ec9a2d25 (PR #2240), committed 2026-10-15.
- The 28 epic binding lines that read `CAP-1..145` are Story 120.3's. Done Story 117.2's Surface line is history and stays.
- Not planned here: a close read of the other 148 capability blocks against code (deferred row DW-steward-cutover-2026-11-10-6, written by Story 122.5).
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (steward and host: Story 122.5) and doctor Story 58.4 runs every scoped stamp once, after the last edit.
- Amendments written as memlog `change` entries in the mint's fix pass (2026-11-11, one entry per capability, one per marker group), which this story verifies, corrects by a later entry where the tree differs, then renders in one re-derive (the integrated plan of 2026-11-10, adjusted by the operator's rulings of that day):
  - CAP-150, CAP-152..CAP-164, CAP-166..CAP-168, CAP-174: `(ready <date>)` becomes `(shipped <date>)`, the date the day the last citing story reached done (read from that story's merge); each is re-checked against the ledger before the entry is written, and one that still has an open story keeps `ready`. On 2026-11-11 that is CAP-153 (Story 124.3) and CAP-166 (Story 124.2), both stories of this PR, so the entry renders them `ready` and Story 122.5 flips them; this story writes a correcting `change` entry only if the ledger shows otherwise when it runs.
  - CAP-169, CAP-170, CAP-171: gain `(shipped <date>)` (Stories 109.1..109.3 and 109.6..109.8 are done).
  - CAP-172, CAP-173: gain `(ready 2026-10-21)`; the pointers to Story 109.4 (backlog) and Story 109.5 (in-progress) stay.
  - CAP-146..CAP-149: the parenthesis leads with the marker, `(shipped 2026-09-19; folded 2026-09-19, ...)`.
  - CAP-2: marker `(retired 2026-10-15; superseded by CAP-168)`; intent and success say `steward deploy dashboard` and `deploy status` were removed by Story 102.3 and `steward pages build|deploy|status` carries the behaviour.
  - Constraint AD-4 and the Success signal: AD-4 names `steward pages deploy` and the hash compare as the reconciliation (the spine's 2026-10-14 amendment); the Success signal's second measure becomes CAP-168's (deploys per 30 days, zero bot commits for Pages) and its 'conformance suite' the named regression test.
  - CAP-4: success says `budget check` returns exit 3 (no metered spend source configured) and that 0 and 1 are reserved for a comparison no story has built.
  - CAP-5: 'The 51 Guild/planning tasks' becomes 'the tasks of `[feature.guild-tasks]`' with the count as a dated measure (95 on 2026-11-10).
  - CAP-7: success names the floor as `pixi.toml`'s `bmad-eval-quality` pin (>=4.3.0 on 2026-11-10), with no line numbers; the 2026-09-11 `verified:` line is marked as that day's reading.
  - CAP-26, CAP-43, CAP-161, CAP-167: each `pixi.toml:<line>` reference becomes the table or key it meant.
  - CAP-46: the text says the refusal is `pyforge.core.league_measure.validate_measure_cite` and that on 2026-11-10 no station calls it; the marker stays `(shipped 2026-09-15)` for the validator, and the consumer half no station built is text marked `(retired 2026-11-10: never built)` (operator ruling 2026-11-10).
  - CAP-53 (control-plane's request): a Frame is a pointer to the seed (the station Dream and the Spec memlog) and to the Spec and companions derived from it, never the seed, and A writes the nine Frames until the flip (operator ruling 1, 2026-11-10).
  - CAP-6 (control-plane's request): the re-pin line names the two frame-spec head SHAs Story 120.4 read and what moved since d7213c18 and 4596579f.
  - CAP-153: the floors `target-version-check` holds include each package `pixi.toml`'s host and run `python` floor (built by Story 124.3).
  - CAP-159: intent names `steward preflight verify-deferred [--since YYYY-MM-DD]` (Story 103.6) and its exit codes.
  - CAP-175: the one driver is `scripts/coverage_gates_ci.py` (with `scripts/run_station_coverage_gate.py` for the named-module ratchet).
  - CAP-38, CAP-70, CAP-93, CAP-117, CAP-122, CAP-139: each companion citation carries its `archive/...` path.
  - Constraints (five leads) and Open Questions (two): the Constraint leads `- **CAP-5 (...`, CAP-6, CAP-166, CAP-167 and CAP-168 are reworded so no Constraint starts like a capability heading; the Open Questions that wait on Stories 100.1 and 102.2 are restated as they stand.

## Planned deferral (written at build)

- The AD-6 Constraint of `spec-pyforge-steward` (and AD-6 on the steward spine) still says `steward budget check` "returns one of three distinct exit codes"; the code returns exit 3 only, as the re-derived CAP-4 now says. The 2026-11-10 audit named CAP-4 alone and this story's amend list does not carry AD-6, so it is left as written here: it belongs with the close read of the other capability blocks and Constraints against the code, deferred row DW-steward-cutover-2026-11-10-6, which Story 122.5 writes.
- Of the 15 `verified:` lines dated 2026-09-11, only CAP-7's carried a claim the tree now contradicts (the `1.4.1` floor); it is marked as that day's reading. The other 14 are dated readings already and are left as written; a re-verification of them, if wanted, rides the same deferred row.
- `capability-ledger-check` reports heading-text mismatches between `docs/foundry/capability-ledger.yaml` and the live Specs (pre-existing, none from a marker this story moved); the ledger is regenerated from the live Specs by control-plane's `plan --regenerate` in Story 122.5's closing pass, so no row is written here.
