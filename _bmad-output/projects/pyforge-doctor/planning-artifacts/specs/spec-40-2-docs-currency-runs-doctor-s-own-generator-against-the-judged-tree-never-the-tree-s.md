---
title: "40.2: docs-currency runs Doctor's own generator against the judged tree, never the tree's"
type: 'fix'
created: '2026-10-05'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-40-1-doctor-executes-no-code-from-the-judged-tree-and-an-unresolved-head-or-a-failed-gather-reads-as-unevaluable.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_currency.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/cli_bridge.py
  - scripts/_docs_gen_common.py
  - docs/map.yaml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 40.1 made Doctor execute no code from the judged tree at its two module loaders. Its review then found a third site, recorded as `DW-doctor-40-1-2` (high, unverified).

- **The third site.** `sources/docs_currency.py` (`_check_generated_page`, around :452-468) builds `generator_path = target / generator` from the judged tree's own `docs/map.yaml`. It runs that script through `cli_bridge.run_check_script` with `cwd=target`, at Doctor's privileges.
- **The trust model was left open.** The module's design note treats each generator as an opaque, already-decided verdict, and `tests/meta/test_source_independence.py` governs only textual import and exec references, not a subprocess. 40.1's spec asked for a ruling.
- **The ruling.** On 2026-10-05 the operator ruled to fix it: Doctor may not run the judged tree's declared generators.
- **Why the obvious fix is not enough.** Every generator (`scripts/docs_pixi_tasks.py`, `docs_station_cli.py`, `docs_skills_catalog.py`, `docs_environments.py`, `docs_detectors.py`) takes its root from `scripts/_docs_gen_common.py`'s `REPO_ROOT = Path(__file__).resolve().parent.parent`. Simply running Doctor's own copy would judge Doctor's checkout instead of the target.

**Approach:**
- `scripts/_docs_gen_common.py` and each declared generator take an optional `--root <path>`. It defaults to today's `REPO_ROOT`, so `pixi run docs-*` and a bare `--check` behave exactly as before. Every path a generator reads or compares resolves from that root.
- `docs_currency` resolves the declared generator in Doctor's own checkout, located by walking up from the module's own `__file__` (40.1's pattern, never from `target`). It runs that copy with `--check --root <target>`. `target` supplies only the data.
- The declared path must be a repo-relative `scripts/docs_*.py` with no `..`; any other path is a WARN naming it and is never run.
- If Doctor's checkout has no such generator, the existing "could not run" WARN reports it; nothing falls back to the target's copy.
- Add a conformance test that names the trust model: no `docs_currency` code path passes a file under `target` to a subprocess or a loader.
- Close `DW-doctor-40-1-2` on landing, with a `resolution:` and a cited `verified:` line.

Ledger key: `40-2-docs-currency-runs-doctor-s-own-generator-against-the-judged-tree-never-the-tree-s`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- Story 40.1 (FR-15, Stories 6.4–6.6), Story 30.3 (`spec-pyforge-doctor` CAP-84, the generated-page check). A defect of shipped behaviour, so no new CAP. Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.

## Acceptance Criteria

- Given a judged tree whose `docs/map.yaml` names `scripts/docs_environments.py` and whose copy of that script differs from Doctor's (for example, it writes a marker file) When `docs_currency` runs Then Doctor's copy runs with `--root <target>`, the target's copy never runs, and the marker is never written
- Given Doctor's copy run with `--root <target>` When the target's generated page is current or stale Then the verdict matches what the target's own `pixi run docs-* -- --check` reports for the target's data
- Given a declared generator outside `scripts/docs_*.py`, or a path with `..` When `docs_currency` runs Then one WARN names it and nothing runs
- Given `pixi run -e pyforge-guild docs-environments` (or any `docs-*` task) with no `--root` When it runs Then its output and exit code are unchanged
- Given the rule removed (the target's copy run again) When the tests run Then the conformance test fails (mutation)
- Given this story lands When `DW-doctor-40-1-2` is read Then it is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it read

## Boundaries & Constraints

**Always:**
- Keep each generator's own `--check` exit-code contract (0 current, non-zero stale) unchanged.
- Keep Story 40.1's two loaders as they are.

**Never:**
- Never fall back to the target's generator when Doctor's copy is missing.
- Never import `pyforge.doctor` from a `scripts/docs_*.py` generator, or a generator from Doctor (Story 6.10, independence is structural).

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-05 (generator trust) entry.
- Epic: Epic 40. It reopens (operator ruling, 2026-10-04: a fix joins its own epic and reopens it).
- Ledger key: `40-2-docs-currency-runs-doctor-s-own-generator-against-the-judged-tree-never-the-tree-s`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Minted 2026-10-05 at the operator's request ("the doctor DW-doctor-40-1-2: chain fix story 40.2 into Epic 40"), the ruling 40.1's spec asked for.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks:**
- `pixi run -e pyforge-guild docs-environments -- --check` exits as before on `main`.
- `pixi run --frozen -e pyforge-guild detectors-ci` reports no new `docs-currency` finding.

## Review Triage Log

- No review has run yet.
