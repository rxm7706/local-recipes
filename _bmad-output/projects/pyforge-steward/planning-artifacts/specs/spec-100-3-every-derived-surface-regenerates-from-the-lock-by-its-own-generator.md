---
title: '100.3: Every derived surface regenerates from the lock by its own generator'
type: 'feature'
created: '2026-10-13'
status: 'in-progress'
baseline_revision: 'c17b91a9af8e3ae744187e20e29a33cc1d69a9dc'
flag:
  key: pyforge.steward.estate_refresh          # Story 100.2's (one flag per CAP)
  provider: openfeature-file                   # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # Story 100.2's values
  scope: global                                # v1 is global only
  fallback: the `estate reconcile` verb refuses naming the flag; `llms_full_check.py --fix-floors` is a script mode that needs no flag and changes nothing unless invoked
  cleanup: with Story 100.2's flag, 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-100-2-one-command-moves-the-library-pins-on-the-policy-and-restores-what-the-upgrade-loses.md
  - docs/intake/estate-refresh/PLAN-2026-10-13.md
  - scripts/llms_full_check.py
  - docs/reference/library-llms-full.md
  - scripts/bump_pixi_version.py
  - scripts/pixi_env_matrix.py
  - scripts/docs_environments.py
  - scripts/docs_pixi_tasks.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/catalog.py
  - scripts/spec_surface_check.py
  - scripts/.spec-surface-baseline.json
  - _bmad/scripts/memlog.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** After a refresh, seven derived surfaces regenerate by hand, each its own way, and the 2026-10-13 batch
left `llms-full-check` at 81 findings (`DRIFT`), `bmad-estate-check` red on `pins` and `suite`, and
`environment.yaml` stale (`docs/intake/estate-refresh/PLAN-2026-10-13.md` § 2). The library catalog's floors are
re-synced by an LLM prompt in its header (`docs/reference/library-llms-full.md:33-35`), not by a generator. The
seven Specs whose surface names `pixi.toml` / `pixi.lock` / `environment.yaml` are reconciled by hand with a memlog
line and a scoped stamp each.

**Approach:** `estate reconcile`, a fourth verb on Story 100.2's duty, plus one new deterministic mode on the
catalog check.

- **Generators, in order, each a subprocess (AD-1), never a regex over a derived file:** `environment.yaml` ←
  `pixi project export conda-environment -e build`; the library catalog's floors ← `python
  scripts/llms_full_check.py --fix-floors` (new, below); the BMAD-estate catalog ← `scribe catalog bmad-estate
  --write`; the env matrix ← `python scripts/pixi_env_matrix.py --update docs/dreams/pyforge-unifying-strategy.md`;
  the generated docs ← `docs-environments` and `docs-pixi-tasks`; the pixi-version sites ← `bump-pixi-version`
  when the journal says the `pixi` floor moved; the `bmad-suite` metapackage ← `generate-bmad-suite` when the
  journal says a `bmad-*` floor moved.
- **`llms_full_check.py --fix-floors`.** For each `floor-drift` finding (an existing catalog row whose recorded
  floor differs from `pixi.toml`'s), rewrite that row's floor token in place and nothing else; `undocumented-dep`
  and `ghost-entry` findings are left for a human and still red the check. Prose is byte-identical outside the
  floor tokens; the header gains one line naming the command and the date (replacing the prompt's floor clause).
- **Checks, each by exit code, journaled:** `llms-full-check`, `bmad-estate-check`, `pixi-version-check`,
  `target-version-check`, `sbom-gaps-check` (fnd:CAP-12's disposition rows for a new feature or fat-only pin),
  `platform-policy-suite-check`, `pin-policy-check`, `pixi lock --check` (all three platforms solve — ruling Q14).
  Two warn-only rows, never red: `pixi-currency-staleness-check` (doctor's ledgers go stale on doctor's own chain)
  and `steward deck-drift` (herald's deck family; `spec-deck-family-currency`'s surface names `pixi.toml`).
- **Spec-surface reconcile.** Read `scripts/.spec-surface-baseline.json`; for each file the refresh moved
  (`pixi.toml`, `pixi.lock`, `environment.yaml`, and every regenerated file), collect the Specs whose surface
  governs it (seven for `pixi.toml` today); append one `(event)` line per Spec with `uv run _bmad/scripts/memlog.py
  append --workspace <spec-folder> --type event --text "Surface reconcile <date>: estate refresh moved <paths>;
  journal <path>"`, checking each exit code; `git add` the moved files; run `python scripts/spec_surface_check.py
  --write-baseline --spec <project>/<spec>` for exactly those Specs; re-run `spec-surface-check`. A memlog without
  frontmatter is a refusal naming the file (team memory 2026-09-05), never a silent skip.
- **Journal.** The `reconcile` block: each generator's argv and exit, each check's exit, the Specs reconciled, and
  `result_sha` after the caller commits (the duty prints the commit it recommends; it never commits).

Ledger key: `100-3-every-derived-surface-regenerates-from-the-lock-by-its-own-generator`.
Type / Effort / Deps: feature / M / S-100.2.

### Living CAP citations

- **`spec-pyforge-steward` CAP-167** (FR-40): the reconcile verb and `--fix-floors`.
- **AD-1**: every regeneration is the surface's own generator; `--fix-floors` lives in the catalog check that
  already parses both files. **AD-8**: child exit codes are recorded, `main()` projects the duty's.
- **Co-governors:** `scripts/llms_full_check.py` and `docs/reference/library-llms-full.md` are on
  `spec-pyforge-steward`'s own surface; `docs/reference/bmad-estate-llms-full.md` is scribe's generated file
  (regenerated through scribe's command, never edited); `docs/dreams/pyforge-unifying-strategy.md`'s matrix block is
  the script's own marker region.
- **Flag:** Story 100.2's `pyforge.steward.estate_refresh`.
- **Origin.** The 2026-10-13 Dream entry; plan Q7 (deterministic floor re-sync).

## Acceptance Criteria

- **AC1 — Generators run in order.** With every generator faked, `estate reconcile` records the argv of each in the
  listed order; `bump-pixi-version` and `generate-bmad-suite` appear only when the journal's `moves` include `pixi`
  or a `bmad-*` package respectively.
- **AC2 — `--fix-floors`.** Over a fixture pair (the 2026-10-13 batch's `pixi.toml` and the catalog at
  `233e07909b`), `llms_full_check.py --fix-floors` brings the check from 81 findings to 0, and the catalog differs
  from its input only in floor tokens and one header line (a test diffs the two and asserts every changed hunk is a
  floor token or the header); an `undocumented-dep` fixture stays red after `--fix-floors`.
- **AC3 — Checks journaled.** Each of the eight checks appears in the journal with its exit code; one non-zero
  reds the reconcile with a documented exit code; the two warn-only rows appear with their exit codes and never
  change the reconcile's.
- **AC4 — Spec-surface reconcile.** With a fixture baseline naming three Specs for `pixi.toml`, the reconcile
  appends exactly three memlog events (fake `memlog.py` records them), stamps exactly those three
  (`--write-baseline --spec` argv recorded), never a bare `--write-baseline`, and refuses naming the file on a
  memlog fixture without frontmatter.
- **AC5 — Never commits.** The reconcile stages files and prints the recommended commit; no `git commit` argv is
  recorded.
- **AC6 — Nothing live.** No test calls a live generator, `pixi`, `git commit` or the network; the catalog at
  `HEAD` is unchanged by the suite.

## Boundaries & Constraints

- No regex over a derived file: `environment.yaml`, both catalogs, the matrix block and the generated docs are
  written only by their generators.
- `--fix-floors` never adds, removes or reorders a catalog row and never touches prose.
- The Spec list comes from the baseline file; a hard-coded Spec list is a review-blocking finding.
- The reconcile never runs `--write-baseline` without `--spec`.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| journal with no moves | generators still run (idempotent), checks run, no memlog events for unmoved files |
| a catalog row whose pin is an inline table | `--fix-floors` rewrites the floor only, keeps the channel note |
| a package pinned in two features with different floors | the catalog row records both, as the check already expects |
| `scribe catalog bmad-estate --write` exits non-zero | reconcile reds naming scribe's command, continues the remaining checks, exit non-zero |
| baseline names a Spec whose memlog lacks frontmatter | refusal naming the file before any stamp |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-167 (FR-40), minted 2026-10-13.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-13 (estate refresh) entry.
- Epic: Epic 100, Stories 100.1–100.7.
- Ledger key: `100-3-every-derived-surface-regenerates-from-the-lock-by-its-own-generator`.
- Ledger status at mint: `backlog`.
- Deps: S-100.2. `marshal factory dispatch` stamps `baseline_revision` with the launch commit (Story 100.1's run did), so no
  hand re-base is needed.
- Surface: `marshal-policy.toml` `[epic_surfaces]."100"` (added with the mint).
- Minted 2026-10-13 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_estate_reconcile.py -q` — expected: pass (AC1, AC3–AC5).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_llms_full_check.py -q` — expected: pass (AC2).
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass.
- `pixi run --frozen -e pyforge-guild llms-full-check` — expected: exit 0 on the tree.
- `pixi run --frozen -e pyforge-guild detectors-ci` and `lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py` and `spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

## Spec Change Log

- 2026-10-13: minted with CAP-167 / FR-40 and Epic 100. `type: feature`, Story 100.2's flag. `--fix-floors` replaces
  the catalog header's LLM floor-re-sync prompt by ruling Q7 (recommended answer, adopted); prose stays
  hand-written.
