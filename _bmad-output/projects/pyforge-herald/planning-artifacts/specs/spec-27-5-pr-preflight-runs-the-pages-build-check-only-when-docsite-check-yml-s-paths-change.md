---
title: "27.5: pr-preflight runs the Pages build check only when docsite-check.yml's paths change"
type: 'feature'
created: '2026-09-27'
status: 'blocked'
blocking_condition: 'blocked until steward Story 71.2 (spec-pyforge-steward:CAP-159, "run the lanes CI would run, read from the workflow files") has landed on main; the operator flips the ledger key, never a session'
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-27-2-one-pages-artifact-carries-the-docs-site-the-dossier-and-the-dashboard.md
  - .github/workflows/docsite-check.yml
  - pixi.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** After Story 27.2, CI's `docsite-check.yml` runs `pages-check` (`npm ci`, the Astro build, the dossier mount under `/herald/`, the redirects) on PRs that touch the docs paths. The local twin, `pr-preflight`, still runs only the old `site-check` leg, so it no longer predicts that lane. If `pages-check` were added unconditionally, every push would pay for a site build, even from a diff that never touches the docs. The operator ruled on 2026-09-27 (D8) that `pr-preflight` runs the Pages build check only when the diff touches the docs paths, with no second hand-kept path list: steward's `spec-pyforge-steward:CAP-159` / Story 71.2 selects each `pr-preflight` lane by its CI workflow's own `paths`.

**Approach:** Replace `pr-preflight`'s `{ task = "site-check", environment = "site" }` leg with `{ task = "pages-check", environment = "site" }`, bound to `docsite-check.yml` so that 71.2's workflow-derived filter selects it from that workflow's `paths`. It is a replacement, not an addition, because `pages-check` depends on `pages-build`, which already runs `docsite/build.py --check` (the whole of `site-check`). Keeping both would build the dossier twice per preflight. `site-check` stays a pixi task for the local docsite loop.

## Boundaries & Constraints

**Always:**
- **Blocked until steward Story 71.2 has landed; the operator flips it.** The ledger key is minted `blocked` because marshal's `Deps:` parser is station-local, so a cross-station precondition has to be a ledger gate (AGENTS.md § Known pitfalls). Do not start this story while 71.2 is unlanded.
- The selection is 71.2's, read from `docsite-check.yml`'s own `paths` (set by Story 27.2: `docs/**`, `docs-site/**`, `docsite/**`, `docs/dashboard/**`, `presentations/**`, `pixi.toml`, the workflow itself). Bind the lane to that workflow in whatever form 71.2 defines, and read that form from 71.2's landed spec and code.
- `pixi.toml` changed: run `pixi run -e pyforge-guild pyforge-station-tests` first, and regenerate `environment.yaml` (expected byte-identical). Update `pr-preflight`'s description to say why the leg changed.
- Before landing, reconcile each co-governor: add a memlog entry on every Spec that `spec-surface-check` names, `git add`, run one scoped stamp per named Spec, re-check, and read the exit code.
- The PR carries the `maintenance` label.

**Never:**
- Do not flip this story's ledger key, or any other `blocked` key.
- Do not write a second, hand-kept path list for the lane: not in `pixi.toml`, not in a script, not in a test fixture that stands in for `docsite-check.yml`.
- Do not implement or change 71.2's lane filter: that is steward's code (Kinship, not work in steward's tree).
- Do not let `pr-preflight` run `site-check` and `pages-check` together.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| far-away diff | changed files only under `src/shared/packages/pyforge-marshal/` | 71.2's selection leaves `pages-check` unselected | none |
| docs diff | a changed file `docs/how-to/x.md` | 71.2's selection includes `pages-check` in `site` | a red `pages-check` fails `pr-preflight` |
| docsite diff | a changed file under `docsite/` | `pages-check` selected | as above |
| lane list | `pixi.toml` `pr-preflight` depends-on | `pages-check` in `site` present; `site-check` absent | `test_preflight_pages_lane.py` fails naming the leg |
| 71.2 absent | this story dispatched before 71.2 landed | refused: the ledger key is `blocked` | operator gate |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald CAP-52` (FR-8.5; decision D8 in the Spec's `.memlog.md`, the operator ruling of 2026-09-27).
Architecture: AD-21.
Ledger key: `27-5-pr-preflight-runs-the-pages-build-check-only-when-docsite-check-yml-s-paths-change`.
Ledger status at mint: `blocked`, until steward Story 71.2 has landed; the operator flips it.
Deps: S-27.2 (`pages-check` and `docsite-check.yml`'s docs path filters). Cross-station gate: steward Story 71.2 (`spec-pyforge-steward:CAP-159`).
Kinship: `spec-pyforge-steward:CAP-159` / Story 71.2 owns the workflow-derived lane filter.
Minted 2026-09-27 from `epics.md` so `marshal factory dispatch` can resolve this spec once the operator unblocks it.

## Epic excerpt

**Type:** feature • **Effort:** S • **Deps:** S-27.2 • **FR/AD:** spec-pyforge-herald CAP-52 (FR-8.5; D8); AD-21 • cross-project gate: steward Story 71.2 (`spec-pyforge-steward:CAP-159`) must have landed first — the ledger key is minted `blocked` and the operator flips it, per AGENTS.md (marshal's `Deps:` parser is station-local)

**Surface:**
- `pixi.toml`, and only `pr-preflight`'s lane list:
  - the `{ task = "site-check", environment = "site" }` leg is replaced by `{ task = "pages-check", environment = "site" }`, with its description saying why
  - it is a replacement, not an addition: `pages-check` depends on `pages-build`, which already runs `docsite/build.py --check` (the whole of `site-check`), so keeping both would build the dossier twice per preflight
  - `site-check` stays a pixi task for the local docsite loop (`docsite/README.md`)
  - the lane is selected by steward Story 71.2's workflow-derived filter, which reads `docsite-check.yml`'s own `paths` (set by 27.2) through the lane-to-workflow binding 71.2 defines; no second, hand-kept path list is written anywhere
- `src/shared/packages/pyforge-herald/tests/meta/test_preflight_pages_lane.py` (new), checking:
  - `pr-preflight` carries `pages-check` in `site` and no `site-check` leg
  - the lane is bound to `docsite-check.yml` the way 71.2 reads it
  - against `docsite-check.yml`'s `paths` under GitHub's glob semantics, a diff touching only `src/shared/packages/pyforge-marshal/` matches no path, and one touching `docs/how-to/x.md` matches

**Given** steward Story 71.2 has landed (pr-preflight selects each lane by its CI workflow's `paths`), and Story 27.2 made `docsite-check.yml` run `pages-check` on `docs/**`, `docs-site/**`, `docsite/**`, `docs/dashboard/**`, `presentations/**`, `pixi.toml` and the workflow itself
**When** `pr-preflight` selects its lanes for a fixture diff
**Then** a diff touching only `src/shared/packages/pyforge-marshal/` leaves `pages-check` unselected, and a diff touching `docs/how-to/x.md` selects it, as shown by 71.2's own selection report
**And** `test_preflight_pages_lane.py` passes in `pyforge-herald-test`; `pr-preflight` never runs `site-check` and `pages-check` together

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; `tests/meta/test_preflight_pages_lane.py` runs inside it).

**Manual checks:**
- Through steward Story 71.2's selection entry point (named in 71.2's landed spec), run the two fixture diffs: one touching only `src/shared/packages/pyforge-marshal/`, which should leave `pages-check` unselected, and one touching `docs/how-to/x.md`, which should select it.
- `pixi run -e pyforge-guild pr-preflight` on a docs-only branch — expected: exit 0, having run `pages-check` (read the exit code, never through a pipe).
