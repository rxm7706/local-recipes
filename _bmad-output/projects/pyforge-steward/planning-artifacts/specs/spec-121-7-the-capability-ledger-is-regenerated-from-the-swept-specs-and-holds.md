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
  - docs/governance/spec-coverage-gate-independence/SPEC.md
  - docs/governance/spec-coverage-gate-independence/.memlog.md
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
  pixi run --frozen -e pyforge-steward python -c "from pathlib import Path;from pyforge.steward import cutover_ledger_check as c;r=c.check(Path('.'),Path('docs/foundry/capability-ledger.yaml'));x=('rebuild-never-built','pyforge-steward:CAP-181');f=[g for g in r.findings if (g[0],g[1])!=x];u=[g for g in f if g[0]=='unknown-marker'];d=[w for w in r.warnings if w[0]=='defaulted-row'];print(len(f),len(u),len(d));raise SystemExit(1 if f or d else 0)"
  ```
- **AC2 — the same through the CLI.** Expected: exit 0 (the CLI exits 0, or exits 1 naming `pyforge-steward:CAP-181` while Story 123.1 is not `done`; AC1 proves that exemption is its only finding).
  ```bash
  pixi run -q --frozen -e pyforge-guild pyforge steward cutover plan --check > "$TMPDIR/pc.out" 2>&1; rc=$?; test "$rc" = 0 || { test "$rc" = 1 && grep -q 'pyforge-steward:CAP-181' "$TMPDIR/pc.out"; }
  ```
- **AC3 — regenerate changes nothing (committed tree).** Expected: exit 0 (the same exit rule as AC2, should `--regenerate` run the check after writing).
  ```bash
  pixi run -q --frozen -e pyforge-guild pyforge steward cutover plan --regenerate > "$TMPDIR/rg.out" 2>&1; rc=$?; { test "$rc" = 0 || { test "$rc" = 1 && grep -q 'pyforge-steward:CAP-181' "$TMPDIR/rg.out"; }; } && git diff --exit-code docs/foundry/capability-ledger.yaml
  ```
- **AC4 — the live-tree test.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_capability_ledger_live.py -q -m live_tree -p no:cacheprovider
  ```
- **AC5 — doctor's ledger detector agrees (after doctor 56.2 and its asks).** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild capability-ledger-check
  ```
- **AC6 — frozen-path-changed reads the real ledger (after doctor 56.1).** Expected: exit 0.
  ```bash
  pixi run -q --frozen -e pyforge-guild frozen-path-changed-check > "$TMPDIR/fp.out" 2>&1; rc=$?; grep -q 'capability-ledger.yaml' "$TMPDIR/fp.out" && ! grep -q 'pre-cutover' "$TMPDIR/fp.out" && exit $rc
  ```
- **AC7 — the cutover detectors read the regenerated ledger and the roster.** Expected: exit 0 for each (doctor's request: the whole-tree merge bar is 58.4's; `plan --check` is AC2's).
  ```bash
  pixi run --frozen -e pyforge-guild capability-ledger-check && pixi run --frozen -e pyforge-guild frozen-path-changed-check && pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources writer-lock
  ```
- **AC8 — no rebuild row is never built, but for the one exemption, and that row stays rebuild.** Expected: prints `0 rebuild`, exit 0 (`pyforge-steward:CAP-181` is exempt by name: Story 123.1 builds it on A in this PR and depends on this story; Story 122.5 runs the same check with no exemption).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts python -c "import yaml;from pathlib import Path;from pyforge.steward.cutover_ledger_check import check;r=check(Path('.'),Path('docs/foundry/capability-ledger.yaml'));f=[x for x in r.findings if x[0]=='rebuild-never-built' and x[1]!='pyforge-steward:CAP-181'];m={x['id']:x for x in yaml.safe_load(open('docs/foundry/capability-ledger.yaml'))['capabilities']}['pyforge-steward:CAP-181']['mode'];print(len(f),m);raise SystemExit(1 if f or m!='rebuild' else 0)"
  ```
- **AC9 — a simulated ledger close leaves no finding but the one exemption (added by the integrator ruling).** It takes the story keys from the `build(<station>):` subjects of `git log --format=%s main..HEAD`, treats each as `done` in memory (no file is written), re-runs `cutover_ledger_check.check`, and fails on any finding except `rebuild-never-built` on `pyforge-steward:CAP-181`. Expected: prints `<build keys> <findings> 0` (`83 1 0` on 2026-11-12), exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward python -c "import re,subprocess;from pathlib import Path;from pyforge.steward import cutover_ledger_check as c;s=subprocess.run(['git','log','--format=%s','main..HEAD'],capture_output=True,text=True,check=True).stdout.splitlines();b={('pyforge-'+m.group(1),k) for x in s for m in [re.match(r'build\(([a-z-]+)\):',x)] if m for k in re.findall(r'\b\d+\.\d+\b',x)};o=c._Stations.status;c._Stations.status=lambda self,st,k:'done' if (st,k) in b else o(self,st,k);r=c.check(Path('.'),Path('docs/foundry/capability-ledger.yaml'));x=('rebuild-never-built','pyforge-steward:CAP-181');f=[g for g in r.findings if (g[0],g[1])!=x];[print(*g) for g in f];print(len(b),len(r.findings),len(f));raise SystemExit(1 if f else 0)"
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

## Review findings (build, round 1, 2026-11-11)

An independent review of the first build failed it. Each finding below gives its severity, where it is, the problem, and what this round did. No acceptance command was called wrong, so AC1 to AC8 are unchanged.

1. **Blocker: `docs/governance/spec-coverage-gate-independence/SPEC.md:106`** (Story 120.3's surface, built in BUILD-1; outside this story's files_owned).
   - **Problem.** `cutover_ledger_check` reports `unknown-marker` on `coverage-gate-independence:CAP-4`. The heading reads `*(minted 2026-09-27 (late); kinships …; doctor Story 32.1)*`, and `modes.md` § Marker tokens reads `minted` as an unknown marker. This finding is not the `pyforge-steward:CAP-181` exemption, and the exemption may not widen. So AC1 (which expects `0 0 0`) and AC4 stay red. The reviewer's simulated ledger close, with every plan story `done`, leaves this as the only finding. No later story in `plan.json` owns that Spec.
   - **This round.** Not fixed, because this story may not fix it. The fix is in Story 120.3's files: append a memlog `event` on `docs/governance/spec-coverage-gate-independence`, then re-derive (anchored script render) so that CAP-4's marker takes a pinned form, `(shipped 2026-09-27; …)`, as doctor Story 32.1 landed it. Doctor 32.1 is the story that met CAP-4's success. That needs an Integrator ruling: either assign the fix to Story 120.3's surface, or widen this story's files_owned. Neither SPEC.md is edited by hand, and the id is not exempted in the check or in the test. The fix leaves the bold title alone, so the ledger row (heading, mode, state) does not change. A `plan --regenerate` after it changes nothing, and AC1, AC2, AC4 and AC8 are re-run after it.
2. **Minor: the sprint-status ledgers at review time** (AC1, AC2, AC4, AC8).
   - **Problem.** Twenty-six rebuild rows read `rebuild-never-built`. All of them have citing stories that are built on this branch, and `remode-2026-11-10.md` § *Never built, as Story 121.7 decided it* names them. They read `backlog` or `blocked` only because the ledger close promotes statuses at the end of the build.
   - **Not a defect.** Keeping them `rebuild` follows this spec's Never clause and its Notes. Setting them B-only would freeze the wrong mode through `regenerate`.
   - **This round.** No row changed. The red window is the integrator's to record in an Integrator note. AC1, AC2, AC4, AC8 and `plan --check` are re-run after the ledger close and after finding 1's fix. Once the built stories read `done`, the reviewer's simulation leaves only the exempt `pyforge-steward:CAP-181` and finding 1.
3. **Minor: `src/shared/packages/pyforge-steward/tests/meta/test_capability_ledger_live.py`** (`test_the_ledger_has_no_finding_but_the_exemption`).
   - **Problem.** The test checked that the exempt row reads `rebuild` only when `check()` reported the exempt finding. If `pyforge-steward:CAP-181` were set to B-only (the regression this spec forbids), `check()` would report nothing on that row: `_judge_spec_rows` calls `_never_built` only for rebuild rows. The mode assertion would then be skipped, and the test would pass.
   - **Fixed.** A new helper, `exempt_mode_problem`, is asserted every time the exemption holds, whether or not the finding is present. A parametrised case proves that it fires on a B-only row and on a missing row, and that it is silent once the exemption lapses.

## Review findings (build, round 2, 2026-11-11)

An independent review of the round-1 fix failed it again. Each finding below gives its severity, where it is, the problem, and what this round did.

1. **Blocker: `docs/governance/spec-coverage-gate-independence/SPEC.md:106`** (Story 120.3's files_owned, built in BUILD-1; outside this story's files_owned).
   - **Problem.** Round-1 finding 1 is still open. `cutover_ledger_check` still reports `unknown-marker` on `coverage-gate-independence:CAP-4`. The heading marker reads `(minted 2026-09-27 (late); …)`, which was already on main at 82a2b18828, and `modes.md` § Marker tokens names `minted` as unknown. AC1 prints `27 1 0` and exits 1. A close simulation that promotes only the stories built so far (83 keys, taken from the build commits) leaves two findings: the exempt `pyforge-steward:CAP-181` and this one. This spec has no Integrator ruling, so AC1 and AC4 cannot reach green, and no later plan story owns that Spec.
   - **This round.** Not fixed: it still needs an Integrator ruling. The check judges the marker from the Spec heading alone (`_judge_markers`), never from the ledger row, so nothing in this story's files can clear it except a wider exemption, which this spec forbids. The fix is the one round 1 named. Either reopen Story 120.3's surface or widen this story's files_owned to the `docs/governance/spec-coverage-gate-independence/` folder. Then append a memlog `event` and re-derive with the anchored script render, so that CAP-4 reads a pinned form, `(shipped 2026-09-27; …)`, as doctor Story 32.1 met it. The bold title stays, so the ledger row does not change and `plan --regenerate` changes nothing. AC1, AC2, AC4 and AC8 are re-run after it. This round re-ran the reviewer's simulation and got the same two findings.
2. **Major: AC1, AC2, AC4 and AC8 against the sprint-status ledgers at review time** (this spec has no Integrator note).
   - **Problem.** 26 rebuild rows report `rebuild-never-built` because their citing stories still read `backlog` or `blocked`. Every one of those stories is built on this branch in BUILD-1 to BUILD-7, and the close simulation clears all 26. So the cause is a real ledger-close window, not a wrong mode, and keeping the rows `rebuild` follows this spec's Never clause. But no Integrator note names this as a planned red window, so the criteria fail as written. AC1 exits 1, AC4 reports 1 failed and 8 passed, and AC8 prints `26 rebuild` and exits 1. AC2's command exits 0 only through its grep for `pyforge-steward:CAP-181`. Its own text says AC1 proves that CAP-181 is the only finding, and AC1 does not.
   - **This round.** No row changed: the reviewer agrees the rows stay `rebuild`. Recording the window is the integrator's act, and an implementer does not write an `## Integrator note`. AC1, AC2, AC4 and AC8 are reported as failing, with this reason. They are judged after the PR ledger close and after finding 1's fix, and no ledger row changes then.
3. **Minor: `pixi.lock`** (in the worktree; Story 124.3's file).
   - **Problem.** `pixi.lock` is modified in the worktree. The reviewer's `--frozen` runs left it untouched (checked by sha256 before and after). The AC commands as this spec wrote them omit `--frozen`, so running them literally can re-lock the file, and this story does not own `pixi.lock`.
   - **This round, an oracle correction.** The reviewer named the corrected form: add `--frozen` to the commands in AC1 to AC7. Without it, `pixi run` may re-solve and rewrite `pixi.lock`, a file only Story 124.3 may change. With it, each command runs the same task against the committed lock, so every criterion checks what it did before: no assertion is dropped, no count is loosened and no skip is added. Each command is otherwise byte-identical. The change is made in this spec's AC block and in `plan.json` stories[121.7].acceptance[0] to [6]. AC8 and § Verification already read `--frozen`.

     | AC | Old command starts | New command starts |
     |---|---|---|
     | AC1 | `pixi run -e pyforge-steward python -c "…"` | `pixi run --frozen -e pyforge-steward python -c "…"` |
     | AC2 | `pixi run -q -e pyforge-guild pyforge steward cutover plan --check > …` | `pixi run -q --frozen -e pyforge-guild pyforge steward cutover plan --check > …` |
     | AC3 | `pixi run -q -e pyforge-guild pyforge steward cutover plan --regenerate > …` | `pixi run -q --frozen -e pyforge-guild pyforge steward cutover plan --regenerate > …` |
     | AC4 | `pixi run -e pyforge-steward pytest …` | `pixi run --frozen -e pyforge-steward pytest …` |
     | AC5 | `pixi run -e pyforge-guild capability-ledger-check` | `pixi run --frozen -e pyforge-guild capability-ledger-check` |
     | AC6 | `pixi run -q -e pyforge-guild frozen-path-changed-check > …` | `pixi run -q --frozen -e pyforge-guild frozen-path-changed-check > …` |
     | AC7 | `pixi run -e pyforge-guild …` (three times) | `pixi run --frozen -e pyforge-guild …` (three times) |

     Every command this round ran used `--frozen`, and `pixi.lock`'s sha256 was the same before and after them. Restoring `pixi.lock` from HEAD is a git write, so it is the wave gate's to do, not this story's.

## Gate findings (build, BUILD-8)

The BUILD-8 wave gate ran `pyforge-steward-live-test`, and `tests/meta/test_capability_ledger_live.py::test_the_ledger_has_no_finding_but_the_exemption` failed with 27 unexcused findings. The wave fix re-ran it on 2026-11-12 and got the same result. Nothing was fixed, because neither cause lies in this story's files_owned. No test, ledger row or exemption was changed or loosened.

- **Finding 1: `unknown-marker` on `coverage-gate-independence:CAP-4`.** Not fixed; it needs an Integrator ruling.
  - **Cause.** The heading at `docs/governance/spec-coverage-gate-independence/SPEC.md:106` reads `(minted 2026-09-27 (late); …)`. `modes.md` § Marker tokens pins only `ready`, `shipped`, `retired` and the legacy `RETIRED`. `_judge_markers` reads the Spec heading alone, so no file this story owns can clear the finding.
  - **Whose files.** That SPEC.md and its memlog are Story 120.3's files_owned. Story 120.3 re-derived the Spec on 2026-11-11, and its scope event says no capability changes, so its render kept the marker.
  - **Evidence for the fix.** Doctor Story 32.1 met CAP-4's success and reads `done` in doctor's sprint-status ledger.
  - **The fix rounds 1 and 2 named, unchanged.** An Integrator ruling assigns it to Story 120.3's surface or widens this story's files_owned. Then a memlog `event` goes on `docs/governance/spec-coverage-gate-independence`, and an anchored script render sets the marker to `(shipped 2026-09-27; …)`. The bold title stays, so neither the ledger row nor a `plan --regenerate` changes.
- **Finding 2: 26 `rebuild-never-built` rows.** Not fixed; this is a ledger-close window.
  - **Cause.** Each row's citing stories read `backlog` or `blocked`, because statuses are promoted only at the PR ledger close.
  - **Close simulation.** The simulation patched the check's `_Stations.status` in memory and wrote no file. Treating as `done` the 83 plan stories built in the branch's `build(...)` commits leaves 2 findings: the exempt `pyforge-steward:CAP-181` and finding 1. Treating all 104 plan stories as `done` leaves finding 1 alone.
  - **Result.** The 26 rows clear at the close with no mode change, and they stay `rebuild`, as § Never requires. Naming this as a planned red window is the integrator's act: an `## Integrator note`.
- **Exit codes after the wave fix.** AC4, the live-tree test, exits 1: 1 failed and 8 passed, with the same 27 findings. AC1 prints `27 1 0` and exits 1. AC8 prints `26 rebuild` and exits 1. `pixi.lock`'s sha256 was the same before and after every command.

## Gate findings (build, BUILD-12)

The BUILD-12 wave gate, which built Story 124.2's wave, ran `pyforge-steward-live-test`. In that run, `tests/meta/test_capability_ledger_live.py::test_the_ledger_has_no_finding_but_the_exemption` failed with 27 unexcused findings. The module is this story's files_owned. It is untracked: it is not at HEAD 2fe6e661a3, because this story has not passed a build. The wave fix re-ran the test on 2026-11-12 and got the same 28 findings as the BUILD-8 gate. They are 27 `rebuild-never-built`, among them the exempt `pyforge-steward:CAP-181`, and 1 `unknown-marker`.

Nothing was fixed. Neither cause lies in this story's files_owned. No test, ledger row, mode or exemption was changed, loosened or removed, and no status was changed. The integrator's pinned-old-value exception does not apply: the test pins no value that a passed story changed on purpose.

- **Finding 1: `unknown-marker` on `coverage-gate-independence:CAP-4`.** Not fixed, and unchanged since rounds 1 and 2 and BUILD-8.
  - **Cause.** The heading at `docs/governance/spec-coverage-gate-independence/SPEC.md:106` still reads `(minted 2026-09-27 (late); …)`.
  - **Whose files.** That SPEC.md and its `.memlog.md` are Story 120.3's files_owned in `plan.json`. `rulings-impact.md` § Steward put them there: "120.3: … ALSO re-derives docs/governance/spec-coverage-gate-independence". Story 120.3 was built in BUILD-1.
  - **The fix.** The fix is the one this spec already names: a memlog `event`, then an anchored script render to `(shipped 2026-09-27; …)`, on that surface. It still needs an Integrator ruling that reopens Story 120.3 or widens this story's files_owned. The bold title stays, so neither the ledger row nor a `plan --regenerate` changes.
- **Finding 2: 26 `rebuild-never-built` rows.** Not fixed; this is the ledger-close window this spec already records. The rows stay `rebuild`, as § Never requires.
  - **Close simulation.** It was re-run on 2026-11-12 with `_Stations.status` patched in memory, and it wrote no file. Two cases were run:
    - The 83 plan stories built in the branch's `build(...)` commits read `done`. This leaves 2 findings: the exempt `pyforge-steward:CAP-181` and finding 1.
    - All 104 plan stories read `done`. This leaves finding 1 alone.
  - **Before Story 121.7 is built and before Story 124.2 is retried,** one of two things must happen:
    - The PR ledger close promotes the citing stories.
    - An `## Integrator note` names this window as planned red.

  Neither is an implementer's act.
- **Exit codes after the wave fix**, all run with `--frozen`:

  | Check | Result | Exit code |
  |---|---|---|
  | The gate's node, `pytest …/test_capability_ledger_live.py::test_the_ledger_has_no_finding_but_the_exemption -m live_tree` | 1 failed | 1 |
  | AC4, the whole module | 1 failed, 8 passed | 1 |
  | AC1 | prints `27 1 0` | 1 |
  | AC8 | prints `26 rebuild` | 1 |

  `pixi.lock`'s sha256 was the same before and after every command.

## Gate findings (build, BUILD-13)

The BUILD-13 wave gate, which built Story 124.3's wave, ran `pyforge-steward-live-test`, and `tests/meta/test_capability_ledger_live.py::test_the_ledger_has_no_finding_but_the_exemption` failed again with 27 unexcused findings. The wave fix re-ran the check on 2026-11-12 at HEAD 2fe6e661a3. The module is still untracked, and this story is still unbuilt.

- **Nothing was fixed.** The findings match the BUILD-8 and BUILD-12 sections above: 28 in all, 27 `rebuild-never-built` (the exempt `pyforge-steward:CAP-181` among them) and 1 `unknown-marker` on `coverage-gate-independence:CAP-4`. Neither cause lies in this story's files_owned. Story 124.3 did not cause the red, and the gate itself says it does not block. No test, ledger row, mode, exemption or status was changed. The integrator's pinned-old-value exception does not apply, because the test pins no value that a passed story changed on purpose.
- **What still clears it, unchanged.** An Integrator ruling for finding 1: reopen Story 120.3's surface, or widen this story's files_owned to `docs/governance/spec-coverage-gate-independence/`. Then the PR ledger close, or an `## Integrator note` naming the planned red window, for the 26 rows. Both are integrator acts.
- **Exit codes after the wave fix**, all run with `--frozen`:

  | Check | Result | Exit code |
  |---|---|---|
  | The gate's node, `pytest …/test_capability_ledger_live.py::test_the_ledger_has_no_finding_but_the_exemption -m live_tree` | 1 failed | 1 |
  | AC4, the whole module | 1 failed, 8 passed | 1 |

  `pixi.lock`'s sha256 was the same before and after every command.

## Integrator ruling (2026-11-12, before the chunk-6 retry)

This ruling binds the implementer and the reviewer. It closes the two findings that review rounds 1 to 3 and the
BUILD-8 and BUILD-12 gates left open.

1. **The `(minted` marker on coverage-gate-independence:CAP-4.** This story now owns `docs/governance/spec-coverage-gate-independence/SPEC.md` and `docs/governance/spec-coverage-gate-independence/.memlog.md`, for this
   one marker only. Doctor Story 32.1 realized CAP-4 and is `done` in doctor's ledger; confirm its landing date with
   `git merge-base --is-ancestor` and the merge commit's date before writing. Append one `(correction)` memlog entry with
   `uv run _bmad/scripts/memlog.py` saying the marker becomes `(shipped <landing date>; …)`, keeping the kinships and the
   story reference. Then render SPEC.md with an anchored script in the same pass, as Story 120.3 did, so the Spec is
   never behind its memlog. Change no other text in that Spec. After this, `cutover_ledger_check` reports no
   `unknown-marker`.
2. **The 26 `rebuild-never-built` rows.** Every one of them is cited by a story built on this branch, which the
   reviewer confirmed against the `build(...)` commit subjects on `main..HEAD`. Those rows read `backlog` or `blocked`
   only because the plan promotes ledger keys at CLOSE-LEDGERS, after BUILD-17. This is a **planned red window that
   closes at CLOSE-LEDGERS**. It covers these `rebuild-never-built` findings, and only those, in AC1, AC2's CLI count,
   AC4 (`test_the_ledger_has_no_finding_but_the_exemption`), AC5, AC7 and AC8. No row changes mode, as the Never clause
   requires. Prove the window instead of asserting it: add an AC9 `(added by the integrator ruling)` that simulates the
   close and exits 0. It takes the story keys from `git log --format=%s main..HEAD` subjects starting `build(`, treats
   them as `done`, re-runs `cutover_ledger_check`, and fails on any finding except the exempt
   `pyforge-steward:CAP-181`. The reviewer judges AC9 now, and judges AC1, AC4, AC5, AC7 and AC8 as passing when their
   only findings are rows AC9 clears. The integrator re-runs AC1 and AC8 after CLOSE-LEDGERS, and both must exit 0
   then.

## Review findings (build, round 3, 2026-11-12)

The Integrator ruling of 2026-11-12 (the section above) closed both open findings. This round did what the ruling says and nothing beyond it. No ledger row changed mode, no exemption widened, no test was loosened, and `pixi.lock` did not change.

1. **Finding 1, closed: `unknown-marker` on `coverage-gate-independence:CAP-4`.**
   - **The landing date, from git.** Doctor Story 32.1's last commit, `82d7ab294b` ("marshal 62.1 / doctor 32.1: review 2 fixes; …"), is an ancestor of `main`: `git merge-base --is-ancestor` exits 0. The first-parent merge that brought it in is `0a15f786d8`, "Merge pyforge-marshal/62-1 into main", dated 2026-09-27. That merge's first parent does not hold the commit. Doctor's sprint-status ledger reads `32-1-the-gates-base-normalizer-names-the-remote-tracking-ref: done`.
   - **The memlog.** One `(correction)` entry was appended to `docs/governance/spec-coverage-gate-independence/.memlog.md` with `uv run _bmad/scripts/memlog.py`, from the worktree root. It says the marker becomes `(shipped 2026-09-27; …)` and keeps the kinships and the story reference.
   - **The render.** An anchored script asserted each of its three anchors exactly once and changed one span on one line: CAP-4's marker `(minted 2026-09-27 (late); …)` became `(shipped 2026-09-27; …)`. The script is `cutover/build/121.7/r3/render_cap4_marker.py` in the session scratchpad. The kinships `marshal:CAP-270` and `pyforge-doctor:CAP-85` and "doctor Story 32.1" stay. The bold title, the frontmatter (its `updated:` line included) and every other line are byte-identical. Two self-validate passes, one for coherence and one for preservation, passed and are logged as memlog events.
   - **The result.** `check` reports no `unknown-marker`: AC1 prints `26 0 0`. The ledger row is unchanged (`rebuild`, `planned`), and `plan --regenerate` reports `unchanged; 0 added, 0 dropped, 0 remoded`. Scribe's `test_spec_not_behind_memlog.py` reports nothing on `spec-coverage-gate-independence`.
2. **Finding 2, closed as a planned red window: 26 `rebuild-never-built` rows.**
   - **What the ruling decided.** The window closes at CLOSE-LEDGERS. AC9 proves the window instead of asserting it. AC9 is now in the AC block above, and its command is recorded in `plan.json` as stories[121.7].acceptance[8].
   - **AC9 now.** It prints `83 1 0` and exits 0. The 37 `build(...)` subjects on `main..HEAD` name 83 station story keys, and each reads `done` in memory. The one finding left is the exempt `pyforge-steward:CAP-181`.
   - **AC9 can fail.** Two scratch probes ran the same logic, and neither wrote a file. With an empty key set, it exits 1 on the 26 rows. With CAP-4's old marker put back in memory, it exits 1 on the one `unknown-marker`.
   - **No row changed mode.** The 26 rows stay `rebuild`, and so does `pyforge-steward:CAP-181` (AC8 prints `26 rebuild`).
3. **Exit codes after this round.** Every command ran with `--frozen`, and `pixi.lock`'s sha256 (`61c46ec7…`) was the same before and after all of them.

   | AC | Result | Exit code | Verdict under the ruling |
   |---|---|---|---|
   | AC1 | prints `26 0 0` | 1 | Passes: all 26 findings are rows AC9 clears. Re-run after CLOSE-LEDGERS. |
   | AC2 | the CLI exits 1 on 27 `rebuild-never-built` findings and names `pyforge-steward:CAP-181` | 0 | Passes. |
   | AC3 | `--regenerate` reports `unchanged`, and the ledger is byte-identical to its copy from before the run | 0 on that comparison | Passes on the committed tree. The literal `git diff --exit-code` exits 1 now only because the ledger is not committed yet; the wave gate commits it. |
   | AC4 | 1 failed, 8 passed; the failing test lists 26 unexcused `rebuild-never-built` rows | 1 | Passes: all 26 are rows AC9 clears. |
   | AC5 | `ok -- 923 live CAP extract(s) match the ledger's 923 row(s)` | 0 | Passes. |
   | AC6 | `ok -- 0 frozen of 923 rows` | 0 | Passes. |
   | AC7 | all three detectors report `ok` | 0 | Passes. |
   | AC8 | prints `26 rebuild` | 1 | Passes: all 26 are rows AC9 clears. Re-run after CLOSE-LEDGERS. |
   | AC9 | prints `83 1 0` | 0 | Passes. |
