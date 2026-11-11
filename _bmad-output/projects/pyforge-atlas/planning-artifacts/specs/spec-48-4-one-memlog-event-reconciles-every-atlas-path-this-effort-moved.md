---
title: "48.4: One memlog event reconciles every atlas path this effort moved"
type: 'chore'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: medium
story: '48.4'
spec: pyforge-atlas
surface:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-48-4-one-memlog-event-reconciles-every-atlas-path-this-effort-moved.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/briefs/brief-pyforge-atlas-2026-07-25/brief.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/retros/retro-pyforge-atlas-2026-11-*.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/implementation-readiness-report-2026-11-*.md
  - docs/dreams/pyforge-atlas.md
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - scripts/.spec-surface-baseline.json
  - .claude/memory/feedback/a-scoped-spec-surface-stamp-scripts-spec-surface-check-py-wr.md
  - docs/dreams/pyforge-atlas.md
  - scripts/fleet_scan.py
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-47-1-atlas-s-public-contract-is-written-beside-the-spec-and-a-meta-test-holds-the-code-to-it.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-47-2-the-catalog-and-gate-companions-name-every-dataset-and-gate-the-code-has.md
  - docs/dreams/pyforge-unifying-strategy.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Chain mechanics, no Spec or code defect of its own. Six stories (46.1, 47.1, 47.2, 48.1, 48.2, 48.3) of this unit change files in the Spec's `surface:`; `spec-surface` reads a move as reconciled only when the owning Spec's memlog names the path in full. Parallel appends to one memlog tail conflict on every merge and a union merge leaves two `updated:` keys, so one story writes one event after the others are on the branch. And CAP-73, minted `(ready 2026-11-10)` at the mint and built by Stories 47.1 and 47.2 in this PR, must read shipped when the chain closes: ruling 6 of the second addendum flips the markers of capabilities this PR builds at each station's closing Story, and this is atlas's.

**Approach:**
- **CAP-73 flips first (ruling 6).** Once Stories 47.1 and 47.2 are both `done`, append one memlog `change` entry (`uv run _bmad/scripts/memlog.py append --workspace _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas --type change --text "CAP-73 ... (ready 2026-11-10) becomes (shipped <date>) ..."`) that flips CAP-73's marker from `(ready 2026-11-10)` to `(shipped <date>)`, the date the later of Stories 47.1 and 47.2 reached `done`, read from its story spec's Auto Run Result (never guessed); the provenance notes after the date stay. Render it into `SPEC.md` through the anchored script render the operator approved for this PR (ruling 7 of the second addendum: a python3 script that asserts each anchor occurs exactly once before it replaces it), then run the bmad-spec self-validation twice and log each pass as a memlog event (`Self-validate pass 1/2 after script render …`, `… pass 2/2 …`). The diff of `SPEC.md` holds the CAP-73 heading line and the `updated:` stamp, nothing else.
- **One reconcile event.** `python _bmad/scripts/memlog.py append --workspace _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas --type event --text "Surface reconcile 2026-11-10 (Stories 46.1, 47.1, 47.2, 48.1, 48.2, 48.3): <every path, full and repo-relative, space-separated>"`, the list taken from `git diff --name-only $(git merge-base origin/main HEAD) HEAD -- src/shared/packages/pyforge-atlas _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md`. A line that groups files by directory or names basenames reconciles nothing.
- **Co-governors.** `pyforge-steward/spec-pyforge-unifying-strategy` holds every atlas path (both manifests, AGENTS.md, src and every test, the 14 views files among them) and `pyforge-marshal/spec-pyforge-core` holds the atlas `src` paths (the 7 views modules, `query_plane_boot.py` and `dashboard/identity_gist.py` among them). Each needs the same paths named in its own memlog before its scoped stamp takes; those memlogs are steward's and marshal's, the baseline is doctor's (Story 58.4), and this story hands them the list. The atlas Spec's `surface-drift-exclude:` leaves the member manifests and six marked test modules to the unifying-strategy Spec alone, so the atlas event may name them without harm and the unifying-strategy event must.
- **Chain close.** After the last memlog append (the reconcile event follows the flip and its two passes), re-stamp `updated:` on the atlas brief, PRD, spine and `epics.md`, each with one dated `Currency reconciliation` line, on its own day; write `retros/retro-pyforge-atlas-<date>.md` through `bmad-retrospective`, dated on or after the last commit that touched `src/shared/packages/pyforge-atlas/pyproject.toml`; write a fresh `implementation-readiness-report-<date>.md` through the bmad readiness check (the newest, 2026-08-10, passed its 90-day shelf life on 2026-11-08); add one closing line `- **<date> (cutover readiness, closed)** — …` at the end of `docs/dreams/pyforge-atlas.md` § Realization log, after the 2026-11-10 (cutover readiness) entry, naming CAP-73 shipped.
- A stamp is valid only until the next edit in the surface: nothing of this unit lands after it.

Ledger key: `48-4-one-memlog-event-reconciles-every-atlas-path-this-effort-moved`.
Type / Effort / Deps: chore / M / S-41.2, S-46.1, S-47.1, S-47.2, S-48.1, S-48.2, S-48.3.

### Living CAP citations

- `spec-pyforge-atlas` CAP-73 (its marker only: ready → shipped, ruling 6 of the second addendum); otherwise chain mechanics (CHAIN-STANDARD § 3 step 7) over `spec-pyforge-atlas`'s `surface:`; no FR

## Acceptance Criteria

Each command runs from the worktree root; read every verdict from its exit code, never through a pipe.

- **AC1 — The memlog names, in full, every path under the package and the deferred-work ledger that differs from main.** Expected: exit 0; prints the path count (about 90, the 14 deleted views files among them) and [].

  ```bash
  python3 -c 'import subprocess,sys;base=subprocess.run(['"'"'git'"'"','"'"'merge-base'"'"','"'"'origin/main'"'"','"'"'HEAD'"'"'],capture_output=True,text=True).stdout.strip();paths=subprocess.run(['"'"'git'"'"','"'"'diff'"'"','"'"'--name-only'"'"',base,'"'"'HEAD'"'"','"'"'--'"'"','"'"'src/shared/packages/pyforge-atlas'"'"','"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md'"'"'],capture_output=True,text=True).stdout.split();m=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md'"'"').read();bad=[p for p in paths if p not in m];print(len(paths),bad);sys.exit(1 if bad or not paths else 0)'
  ```

- **AC2 — The memlog keeps one `updated:` key and its fidelity check passes.** Expected: exit 0.

  ```bash
  test "$(grep -c '^updated:' _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md)" -eq 1 && pixi run -e pyforge-guild memlog-fidelity-check
  ```

- **AC3 — The Spec and the tree agree about the retired runtime.** Expected: exit 0 (Story 48.3 deletes `views/`, ruling 6 of the second addendum; Story 46.1 renders CAP-44..CAP-47 retired).

  ```bash
  test ! -e src/shared/packages/pyforge-atlas/src/pyforge/atlas/views && grep -q '(retired 2026-09-09' _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  ```

- **AC4 — no unreconciled drift row names pyforge-atlas/spec-pyforge-atlas (the closer's memlog names every changed path; doctor 58.4 stamps).** Expected: prints 0, exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources spec-surface --json > "${TMPDIR:-/tmp}/ss.json"; python3 -c "import json,sys;d=json.load(open(sys.argv[1]));rows=d if isinstance(d,list) else (d.get('findings') or d.get('rows') or []);n=[r for r in rows if r.get('check') in ('drift','drift-presumed') and sys.argv[2] in json.dumps(r)];print(len(n));sys.exit(1 if n else 0)" "${TMPDIR:-/tmp}/ss.json" pyforge-atlas/spec-pyforge-atlas
  ```

- **AC5 — the atlas retro is dated on or after the last package-manifest commit.** Expected: prints two dates, the retro's not earlier; exit 0.

  ```bash
  python3 -c "import glob,re,subprocess,sys;f=sorted(glob.glob('_bmad-output/projects/pyforge-atlas/planning-artifacts/retros/retro-pyforge-atlas-2026-1*.md'));d=re.search(r'\d{4}-\d{2}-\d{2}',f[-1]).group(0) if f else '';c=subprocess.run(['git','log','-1','--format=%cs','--','src/shared/packages/pyforge-atlas/pyproject.toml'],capture_output=True,text=True).stdout.strip();print(d,c);sys.exit(0 if d and d>=c else 1)"
  ```

- **AC6 — atlas's readiness gate is fresh.** Expected: lists one file or more.

  ```bash
  ls _bmad-output/projects/pyforge-atlas/planning-artifacts/implementation-readiness-report-2026-1*.md
  ```

- **AC7 — docs/dreams/pyforge-atlas.md records the close.** Expected: prints 1 or more.

  ```bash
  grep -c 'cutover readiness, closed' docs/dreams/pyforge-atlas.md
  ```

- **AC8 — atlas's chain is current: no feeds finding and no shelf finding, read from the exit code.** Expected: exit 0 (1 is a finding, 2 could not run; never through a pipe).

  ```bash
  pixi run --frozen -e pyforge-guild chain-currency-sweep-check -- --project pyforge-atlas
  ```

- **AC9 — CAP-73 reads shipped, and the memlog carries the `change` entry that flipped it (ruling 6).** Expected: prints True, exit 0; then the grep exits 0.

  ```bash
  python3 -c 'import re,sys;s=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md'"'"').read();l=re.search(r'"'"'(?m)^- \*\*CAP-73 — .*$'"'"',s).group(0);ok='"'"'(shipped 2026-1'"'"' in l and '"'"'(ready '"'"' not in l;print(ok);sys.exit(0 if ok else 1)' && grep -qE '^- \(change\) .*CAP-73.*\(shipped 2026-1' _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md
  ```

## Boundaries & Constraints

**Always:**
- Name every path in full; write exactly one reconcile event.
- Re-stamp the chain after the last memlog append, on the same day.
- Flip CAP-73 through a memlog `change` entry and the anchored script render, both self-validate passes logged.

**Never:**
- Never group paths by directory or basename; never write a second `updated:` key.
- Never stamp a Spec this change did not touch.
- Never hand-edit `SPEC.md`; never flip CAP-73 before Stories 47.1 and 47.2 are both `done`, and never touch another capability's marker (Stories 46.1 and 46.2 own those).

</intent-contract>

## Binding

- Parent: `spec-pyforge-atlas` CAP-73 (its marker only: ready → shipped, ruling 6 of the second addendum); otherwise chain mechanics (CHAIN-STANDARD § 3 step 7) over `spec-pyforge-atlas`'s `surface:`; no FR.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-11-10 (cutover readiness) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the entry of that date and its two addenda).
- Epic: Epic 48, minted 2026-11-10 with this story.
- Ledger key: `48-4-one-memlog-event-reconciles-every-atlas-path-this-effort-moved`.
- Deps: S-41.2, S-46.1, S-47.1, S-47.2, S-48.1, S-48.2, S-48.3.
- Cross-station deps: steward:S-121.7 (the capability ledger regenerated from the swept Specs).
- Followed by: doctor:S-58.4 (the branch's baselines and the scoped stamps; it depends on this story, not the reverse).
- Flag: none (`type: chore`: planning artifacts only, no runtime path; spec-feature-flag-governance Q1).
- Surface: `marshal-policy.toml` `[epic_surfaces]."48"`, narrowed by this spec's `surface:`.
- Minted 2026-11-10 in the atlas mint of the one cutover-readiness PR (branch `cutover-readiness-2026-11-10`); built in the same PR.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: exit 0.

**Run before the push:** the acceptance commands above, each read from its exit code.

## Auto Run Result

Status: backlog (minted 2026-11-10).

## Spec Change Log

- 2026-11-10: minted from the station Dream's entry of 2026-11-10 (cutover readiness) under the operator's rulings of 2026-11-10 ("Accept all", "Retire both", "Accept all, run mint"). Acceptance adjusted by the rulings: the retired-runtime check no longer carries the stopped-48.3 branch (ruling 6).

- 2026-11-10 (review of the mint): re-scoped to apply ruling 6 of the second addendum (markers of capabilities this PR builds flip to shipped at the station's closing Story): the story now flips CAP-73 to `(shipped <date>)` by a memlog `change` entry and the anchored script render after Stories 47.1 and 47.2 are done, before the reconcile event and the re-stamp; `SPEC.md` joins `surface:`; AC9 checks the marker. doctor:S-58.4 moves from cross-station deps to `Followed by:` (58.4 lists this story among its own deps). The closing Dream line goes at the end of § Realization log.

- 2026-11-10 (second review of the mint): the Problem counts six stories that change files in the Spec's `surface:` (46.1, 47.1, 47.2, 48.1, 48.2, 48.3), the six the reconcile event already names.

- 2026-11-11 (third review of the mint): AC4 writes and reads `"${TMPDIR:-/tmp}/ss.json"`, so it runs where `TMPDIR` is unset (it exited 1 there whatever the drift state); Deps take the `S-<epic>.<num>` grammar doctor's forward-dependency detector parses (every dep is an earlier epic or this one, so the key stays `backlog`).

## Review Triage Log

- (none yet)
