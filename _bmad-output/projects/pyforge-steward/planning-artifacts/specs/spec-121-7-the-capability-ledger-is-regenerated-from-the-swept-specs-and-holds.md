---
title: '121.7: The capability ledger is regenerated from the swept Specs and holds'
type: 'chore'
created: '2026-11-10'
status: 'blocked'
difficulty: heavy
story: 121.7
spec: foundry-capability-ledger
surface:
  - docs/foundry/capability-ledger.yaml
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/remode-2026-11-10.md
  - src/shared/packages/pyforge-steward/tests/meta/test_capability_ledger_live.py
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/modes.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/extract.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
declared_low_risk: false
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-122.1, S-124.5).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** The integration tail: after every unit's Spec sweep, the generator writes the headings from the Spec titles, joins retired markers, adds rows for every CAP minted in this change (and the governance and pap rows), and the ledger passes both judges. Without it, the new CAP ids of nine units stay unclassified.

**Approach:** Run by the integrator on the integration branch. Steps: `plan --regenerate`; settle each `defaulted` row by `modes.md`'s rules and clear `defaulted`; mark the Launch rows; re-run until `plan --check` is clean but for the one exemption below; append to `remode-2026-11-10.md` the marker-joined and newly added rows. The meta-test is `pytestmark = pytest.mark.live_tree` and asserts `cutover_ledger_check.check` returns no finding on the repository but the exemption, and every row id resolves to a live Spec heading. Re-run `--regenerate` after any later Spec change in the PR; `plan --check` exit 0 is the statement that the ledger is current.

**The one exemption, `pyforge-steward:CAP-181`.** Its building Story 123.1 depends on this story (its oracle map names this story's test module), so when this story runs the capability's heading reads `(ready 2026-11-10)`, no citing story (123.1, backlog; 122.5, blocked) reads `done`, and Story 121.6 names the row `rebuild-never-built`. It is not a never-built capability: 123.1 builds it on A in this PR and Story 122.5 flips its marker to shipped. So the row stays `rebuild` (never the never-built rule's B-only, which `regenerate` would keep as a decided field to the merge), and that one finding is exempt by id and code, with this reason, in AC1, AC2, AC3, AC8 and `test_capability_ledger_live.py`. In the test it is a module constant naming the id, the code `rebuild-never-built` and the reason, applied only while the steward ledger key `123-1-every-steward-capability-names-the-modules-that-realize-it-and-the-tests-that-prove-it` is not `done`, so it lapses by itself when 123.1 is done (123.1's own live-half run, before it is marked done, still passes). Story 122.5, after 123.1, runs the check with no exemption.

Ledger key: `121-7-the-capability-ledger-is-regenerated-from-the-swept-specs-and-holds`. Type / Effort / Deps: chore / L / S-120.3, S-120.5, S-121.1, S-121.2, S-121.3, S-121.6, S-122.1, S-124.5.

### Living CAP citations

- **`spec-foundry-capability-ledger`** — fcl:CAP-1 (schema v1 and the written rules) and fcl:CAP-2 (the refusals and the expiry clock), amended 2026-11-10 and re-derived at mint.

## Boundaries & Constraints

**Always:**
- Apply the same three integrator resolutions as Story 121.3: `pyforge-atlas:CAP-44` to `pyforge-atlas:CAP-47` retire; `pyforge-mason:CAP-18` is A-only "steward:44.8" and `pyforge-mason:CAP-20` A-only "flip"; doctor's closed one-time campaigns retire. Doctor's `pyforge-doctor:CAP-33`, `pyforge-doctor:CAP-50` and `pyforge-doctor:CAP-53` also retire, each for the reason doctor Story 57.1 writes into its intent (not as a campaign), as Story 121.3 records them.
- Keep `pyforge-steward:CAP-181` at `rebuild` and apply its exemption only as the Approach states; no other id is exempt.
- Closers that only flip `(ready)` to `(shipped)` may follow: the ledger heading is the bold title, which excludes the marker.

**Never:**
- Never leave a row `pending` for a 2026-11-10 question; marshal capabilities that marshal Story 114.1 finds never built follow the same rule (B-only with a live Story, else retire).

## Acceptance Criteria

- **AC1 — the ledger passes its own validator with no unknown marker and no undecided row, but for the one exemption.** Expected: prints `0 0 0`, exit 0 (the `rebuild-never-built` finding on `pyforge-steward:CAP-181` is excluded by id and code: Story 123.1 builds it in this PR and depends on this story).
  ```bash
  pixi run -e pyforge-steward python -c "from pathlib import Path;from pyforge.steward import cutover_ledger_check as c;r=c.check(Path('.'),Path('docs/foundry/capability-ledger.yaml'));x=('rebuild-never-built','pyforge-steward:CAP-181');f=[g for g in r.findings if (g[0],g[1])!=x];u=[g for g in f if g[0]=='unknown-marker'];d=[w for w in r.warnings if w[0]=='defaulted-row'];print(len(f),len(u),len(d));raise SystemExit(1 if f or d else 0)"
  ```
- **AC2 — the same through the CLI.** Expected: exit 0 (the CLI exits 0, or exits 1 naming `pyforge-steward:CAP-181` while Story 123.1 is not `done`; AC1 proves that exemption is its only finding).
  ```bash
  pixi run -q -e pyforge-guild pyforge steward cutover plan --check > "$TMPDIR/pc.out" 2>&1; rc=$?; test "$rc" = 0 || { test "$rc" = 1 && grep -q 'pyforge-steward:CAP-181' "$TMPDIR/pc.out"; }
  ```
- **AC3 — regenerate changes nothing (committed tree).** Expected: exit 0 (the same exit rule as AC2, should `--regenerate` run the check after writing).
  ```bash
  pixi run -q -e pyforge-guild pyforge steward cutover plan --regenerate > "$TMPDIR/rg.out" 2>&1; rc=$?; { test "$rc" = 0 || { test "$rc" = 1 && grep -q 'pyforge-steward:CAP-181' "$TMPDIR/rg.out"; }; } && git diff --exit-code docs/foundry/capability-ledger.yaml
  ```
- **AC4 — the live-tree test.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_capability_ledger_live.py -q -m live_tree -p no:cacheprovider
  ```
- **AC5 — doctor's ledger detector agrees (after doctor 56.2 and its asks).** Expected: exit 0.
  ```bash
  pixi run -e pyforge-guild capability-ledger-check
  ```
- **AC6 — frozen-path-changed reads the real ledger (after doctor 56.1).** Expected: exit 0.
  ```bash
  pixi run -q -e pyforge-guild frozen-path-changed-check > "$TMPDIR/fp.out" 2>&1; rc=$?; grep -q 'capability-ledger.yaml' "$TMPDIR/fp.out" && ! grep -q 'pre-cutover' "$TMPDIR/fp.out" && exit $rc
  ```
- **AC7 — the cutover detectors read the regenerated ledger and the roster.** Expected: exit 0 for each (doctor's request: the whole-tree merge bar is 58.4's; `plan --check` is AC2's).
  ```bash
  pixi run -e pyforge-guild capability-ledger-check && pixi run -e pyforge-guild frozen-path-changed-check && pixi run -e pyforge-guild python -m pyforge.doctor.sources writer-lock
  ```
- **AC8 — no rebuild row is never built, but for the one exemption, and that row stays rebuild.** Expected: prints `0 rebuild`, exit 0 (`pyforge-steward:CAP-181` is exempt by name: Story 123.1 builds it on A in this PR and depends on this story; Story 122.5 runs the same check with no exemption).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts python -c "import yaml;from pathlib import Path;from pyforge.steward.cutover_ledger_check import check;r=check(Path('.'),Path('docs/foundry/capability-ledger.yaml'));f=[x for x in r.findings if x[0]=='rebuild-never-built' and x[1]!='pyforge-steward:CAP-181'];m={x['id']:x for x in yaml.safe_load(open('docs/foundry/capability-ledger.yaml'))['capabilities']}['pyforge-steward:CAP-181']['mode'];print(len(f),m);raise SystemExit(1 if f or m!='rebuild' else 0)"
  ```

</intent-contract>

## Binding

Parent: `spec-foundry-capability-ledger` fcl:CAP-1

- Dream: `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the mint entry) and `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth*.
- Epic: Epic 121.
- Ledger key: `121-7-the-capability-ledger-is-regenerated-from-the-swept-specs-and-holds` (`backlog` at mint).
- Deps: S-120.3, S-120.5, S-121.1, S-121.2, S-121.3, S-121.6, S-122.1, S-124.5.
- Surface: `docs/foundry/capability-ledger.yaml`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/remode-2026-11-10.md`, `src/shared/packages/pyforge-steward/tests/meta/test_capability_ledger_live.py`.
- Minted 2026-11-10 by the cutover-readiness mint (control-plane unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_capability_ledger_live.py -q -m live_tree -p no:cacheprovider` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild capability-ledger-check` — expected: exit 0.

## Notes

- Fix pass 2026-11-11 (independent review): the `pyforge-steward:CAP-181` exemption is new here. Without it AC1, AC2 and AC8 and the live-tree test fail at this story's wave (no story citing CAP-181 is `done` until 123.1, one wave later), and the never-built rule would set B-only on a capability this PR builds on A. Every other capability minted in this change has a citing story in an earlier wave.
- Cross-station: warden:S-25.1, scribe:S-31.2, mason:S-37.1, atlas:S-41.2, atlas:S-46.1, atlas:S-46.2, herald:S-50.1, doctor:S-56.1, doctor:S-56.2, doctor:S-57.1, marshal:S-114.1, marshal:S-114.2, marshal:S-117.5 and marshal:S-118.2 sweep a Spec this story reads; each lands first.
