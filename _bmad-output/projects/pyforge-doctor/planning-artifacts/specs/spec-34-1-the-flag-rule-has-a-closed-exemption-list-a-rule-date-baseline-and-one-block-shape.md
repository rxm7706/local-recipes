---
title: '34.1: The flag rule has a closed exemption list, a rule-date baseline and one block shape'
type: 'feature'
created: '2026-09-28'
status: 'done'
flag-exempt: flag-infrastructure   # the rule's own infrastructure (spec-feature-flag-governance Q2)
baseline_revision: '1b7ccfe5646529502d61f1952d241fdc09354f34'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/dreams/feature-flag-governance.md
  - docs/governance/guild-roster.json
  - docs/governance/chain-sprawl-baseline.json
  - scripts/chain_sprawl_baseline.py
  - docs/reference/station-verify-commands.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-09-28 the operator ruled that every capability ships behind a flag and that a gate no station owns
enforces it (`docs/governance/spec-feature-flag-governance/SPEC.md`, `ready`, rule date 2026-09-28). CAP-1 is the rule
itself: every story spec of `type: feature` minted on or after the rule date carries either a `flag:` block (key, provider,
default per environment, scope, fallback, cleanup) or a `flag-exempt:` value from a closed list in
`docs/governance/guild-roster.json`. Today nothing declares that list, nothing can tell a pre-rule spec from a post-rule
one, and no page tells a story author the block's shape. Every story spec is dated by a `created:` string it declares
about itself, and several `type: feature` specs were minted on 2026-09-28 before the Spec reached `ready` (for example
doctor 33.1 and marshal 66.1-73.2), so a date alone cannot draw the line.

**Approach:** four pieces, all outside every `pyforge.<station>` package (Charter §6):
- `docs/governance/guild-roster.json` gains `flag_exemptions` — exactly `flag-infrastructure`, `docs-only`,
  `recipe-build`, `planning-ledger-only`, `detector-or-gate` — and a `$comment_flag_exemptions` that names a change to the
  list a governance act, in the `fold_exemptions` shape beside it.
- `docs/governance/flag-rule-baseline.json` is the pre-rule population: every tracked
  `_bmad-output/projects/*/planning-artifacts/specs/spec-<E>-<S>-*.md` at the merge SHA of the PR that took the Spec to
  `ready` (PR #1654; record the SHA in the file). `scripts/flag_rule_baseline.py` stamps it (`--snapshot` once;
  `--prune` only removes a path that no longer exists), the `scripts/chain_sprawl_baseline.py` shape. A spec is post-rule
  exactly when it is absent from the baseline.
- `scripts/flag_rule.py` is pure: `classify(path)` reads one story spec's frontmatter and returns `flag`, `exempt` or
  `neither` with its reasons. `flag` needs all six fields of the block (`key`, `provider`, `default`, `scope`,
  `fallback`, `cleanup`); `exempt` needs a `flag-exempt:` value on the roster's list; anything else is `neither`, with one
  reason per missing field and per unknown value. `is_post_rule(path)` reads the baseline; `in_scope(spec)` is `type:
  feature` (Q1). Stdlib and PyYAML only.
- `docs/reference/story-spec-flag-block.md` writes the block's one shape (the six fields, the rule date, the exemption
  values by pointer to the roster, a flagged and an exempt example, and the Q3 rule for an OFF CLI verb), registered in
  `docs/map.yaml`, and `docs/reference/station-verify-commands.md` — the page Marshal's spec gates send a story author
  to — gains one pointer line. bmad-build's copy is marshal Story 74.3's `_bmad/custom/` persistent fact, which points
  here.

Ledger key: `34-1-the-flag-rule-has-a-closed-exemption-list-a-rule-date-baseline-and-one-block-shape`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / —.

### Living CAP citations

- `spec-feature-flag-governance` CAP-1 (the Guild's Spec; doctor's `epics.md` Epic 34 and the Spec's `.memlog.md`
  enumerate its stories — the doctor Epic 24/25/32 relay; no doctor CAP or FR).
- Kinship: marshal Story 74.3 (bmad-build's copy of the shape); doctor Story 34.2 (the gate that reads all of this).

## Acceptance Criteria

- Given the roster after this story When it is loaded Then `flag_exemptions` equals the five values in the Spec's Q2, in that order, and `$comment_flag_exemptions` names a change a governance act
- Given a spec whose frontmatter carries a `flag:` block with all six fields When `classify` runs Then it returns `flag` with no reasons
- Given the same block missing `cleanup` and `fallback` When `classify` runs Then it returns `neither` with two reasons, one per field
- Given `flag-exempt: docs-only` When `classify` runs Then it returns `exempt`; given `flag-exempt: no-flag-needed` Then it returns `neither` naming the unknown value
- Given a spec with both a `flag:` block and a `flag-exempt:` value When `classify` runs Then it returns `neither` naming the conflict
- Given a spec listed in the baseline When `is_post_rule` runs Then it is false; given one minted after the rule SHA Then it is true
- Given `type: fix`, `chore` or `docs` When `in_scope` runs Then it is false (Q1)
- Given the five values hard-coded in `scripts/flag_rule.py` When the unit suite runs Then a test fails (the roster is the one declared source)
- Given the new page When `pixi run -e pyforge-guild docs-currency-check` runs Then it exits 0 with the page registered in `docs/map.yaml` and `docs/MAP.md` re-rendered by `docs-map-render`
- Given the change When `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- Keep every new file outside every `pyforge.<station>` package: `scripts/`, `docs/governance/`, `docs/reference/`,
  `tests/scripts/` (Charter §6; the coverage-gate-independence resolution, Story 24.1).
- Read the exemption list from the roster at run time; the code holds no copy.
- Add one reason-tagged line per new script to `scripts/spec_surface_allowlist.txt`, in the `scripts/coverage_gate.py`
  shape (the owning Spec is guild-owned under `docs/governance/`, so it cannot declare a surface that detector reads).
- Record the new paths in the Guild Spec's `.memlog.md` with `uv run _bmad/scripts/memlog.py append` (the surface
  declaration in its `SPEC.md` is re-rendered later through the approved route, never hand-edited).

**Never:**
- Do not add a value to the exemption list, or rename one; that is a governance act.
- Do not import any `pyforge.<station>` module from `scripts/flag_rule.py`.
- Do not judge any spec yet (no finding, no exit code): that is Story 34.2's gate.
- Do not edit `SPEC.md`, `sprint-status-ledger.yaml` or an installer-owned skill file; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| flagged | six fields present | `flag` | — |
| partial block | `key`, `provider` only | `neither`, four reasons | — |
| exempt | `flag-exempt: recipe-build` | `exempt` | — |
| unknown exemption | `flag-exempt: later` | `neither`, one reason | — |
| both | block and exemption | `neither`, the conflict | — |
| pre-rule | path in the baseline | `is_post_rule` false | — |
| no frontmatter | a spec without a fence | `neither`, "no frontmatter" | never a crash |
| unreadable roster | file missing | — | raises a named error Story 34.2 turns into exit 2 |

</intent-contract>

## Code Map

- `docs/governance/guild-roster.json` -- add `flag_exemptions` and `$comment_flag_exemptions` directly after `fold_exemptions`
  (the list-of-strings comment shape). Readers take a key at a time (`pyforge.doctor.sources.one_chain._roster`), so a new key is additive.
- `docs/governance/chain-sprawl-baseline.json`, `scripts/chain_sprawl_baseline.py` -- the shape to mirror (`$comment`, `ruling_sha`,
  sorted list; `--snapshot` refuses over an existing file; `--prune` only removes). Read-only: it imports `pyforge.doctor.sources.one_chain`
  and reads the working tree, so neither is copied.
- `docs/governance/flag-rule-baseline.json` -- NEW. `scripts/flag_rule_baseline.py` -- NEW, self-contained stamper.
- `scripts/flag_rule.py` -- NEW, pure: `classify`, `is_post_rule`, `in_scope`, two named errors. PyYAML for the frontmatter.
- `scripts/spec_surface_allowlist.txt` -- append one reason-tagged line per new script (the `scripts/coverage_gate.py` line is the model).
- `docs/reference/story-spec-flag-block.md` -- NEW; `docs/map.yaml` row beside `reference/station-verify-commands.md`; `docs/MAP.md`
  re-rendered by `docs-map-render`; `docs/reference/station-verify-commands.md` gains one pointer line.
- `tests/scripts/test_flag_rule.py` -- NEW; conventions from `tests/scripts/test_docs_gen_common.py` (`pytest.importorskip("yaml")`,
  `sys.path` insert of `scripts/`).
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-25-1-a-per-repo-dependency-history-dataset-from-git-pkgs-and-an-estate-pixi-parser.md`
  -- read-only evidence: the one live `flag:` block (`default` is a per-environment mapping, `scope: global`).
- PR #1654 merge: `5e977accb9643ff81f02ef9feca3e435d86816f9` (`Merge intake-triage-2026-09-28 into main`); the Spec reads `status: ready` at that commit.
- `docs/governance/spec-feature-flag-governance/.memlog.md` -- append the surface reconcile naming every new and changed path.

## Tasks & Acceptance

**Execution:**
- [x] `docs/governance/guild-roster.json` -- add `flag_exemptions` (the five Q2 values, in Q2's order) and `$comment_flag_exemptions` -- one declared source
- [x] `scripts/flag_rule.py` -- pure classifier, exemptions read from the roster at call time -- the rule's machine form
- [x] `scripts/flag_rule_baseline.py` -- `--snapshot` (once, at the PR #1654 merge SHA) and `--prune` (only removes) -- the rule-date line
- [x] `docs/governance/flag-rule-baseline.json` -- stamp with the stamper, never by hand -- the pre-rule population
- [x] `tests/scripts/test_flag_rule.py` -- one test per AC row and per I/O row, plus the roster-is-the-source scan -- the oracle
- [x] `docs/reference/story-spec-flag-block.md`, `docs/map.yaml`, `docs/MAP.md`, `docs/reference/station-verify-commands.md` -- the block's one written shape and its pointer
- [x] `scripts/spec_surface_allowlist.txt` -- two reason-tagged lines -- the new scripts have no folder-spec surface
- [x] `docs/governance/spec-feature-flag-governance/.memlog.md` -- surface reconcile entry via `_bmad/scripts/memlog.py append`, plus each co-governor `spec-surface-check` names

**Acceptance Criteria:**
- Given the intent contract's ten Given/When/Then rows, when `tests/scripts/test_flag_rule.py`, `docs-currency-check`, `spec-surface-check`, `python scripts/spec_surface_reconcile.py` and `pyforge-doctor-test` run, then each exits 0.

## Spec Change Log

- 2026-09-29 -- planned by bmad-build-auto: status `backlog` -> `draft` -> `ready-for-dev`; Code Map, Tasks and Design Notes added; the intent contract is unchanged.
- 2026-09-29 -- implemented by bmad-build-auto: status `in-progress` -> `in-review`; all eight tasks done; the intent contract is unchanged.
- 2026-09-29 -- review pass by bmad-build-auto: 14 review rows patched (test, docstring and page edits plus one `_frontmatter` fix), none touched the intent contract. The Design Notes line saying the suite skips in `pyforge-ci` is superseded: `pixi.lock` carries `pyyaml` in that env, so the suite runs in the `scripts-suite` lane, and the test docstring now says so.

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-1 and its Q1/Q2 rulings (memlog 23),
`docs/dreams/feature-flag-governance.md`, and the chain-sprawl baseline precedent (doctor Story 25.1), decomposed
2026-09-28 (night) as Epic 34's mint.

## Binding

Parent Spec capability: `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-1 (Guild-owned; Doctor as mechanism
Smith, the Epic 24 relay).
Dream: `docs/dreams/feature-flag-governance.md` § Realization log → *2026-09-28 (night)*.
Ledger key: `34-1-the-flag-rule-has-a-closed-exemption-list-a-rule-date-baseline-and-one-block-shape`.
Ledger status at mint: `backlog`.
Policy: `marshal-policy.toml` `[epic_surfaces]` `"34"` admits the `scripts/`, `docs/governance/`, `docs/reference/` and
`tests/scripts/` paths beside the default surface.

## Design Notes

- The snapshot reads `git ls-tree -r -z --name-only <sha>`, not the working tree: the population is "at the merge SHA", and `HEAD`
  already holds specs minted after it (this one, `created: '2026-09-28'`), which are post-rule by design. `-z` because default
  `core.quotePath` octal-quotes the accented Diátaxis path (`scripts/spec_surface_allowlist.txt`, the last line).
- The population is `spec-<E>-<S>-*.md` minus `*.memlog.md`; a memlog matches the glob but is not a story spec.
- `flag_rule.py` never calls `sys.exit`: it raises `FlagRuleError` subclasses (`RosterUnreadable`, `BaselineUnreadable`) that Story
  34.2 turns into exit 2. A malformed or absent frontmatter is a `neither` verdict, never a raise.
- Golden shape (the block is atlas 25.1's, verbatim keys):

  ```yaml
  flag:
    key: pyforge.atlas.dependency_history
    provider: openfeature-file
    default: {production: off, staging: on, dev: on}
    scope: global
    fallback: "the legacy behaviour"
    cleanup: 90 days after ON in every environment (Q4)
  ```
- `pytest.importorskip("yaml")` skips the suite in `pyforge-ci` (no PyYAML), as `test_docs_*` do; the Verification's manual check runs it in
  `pyforge-guild`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_flag_rule.py -q` — expected: pass.
- `pixi run -e pyforge-guild docs-currency-check` — expected: exit 0 (after `pixi run -e pyforge-guild docs-map-render`).
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 (each new script allowlisted).

## Review Triage Log

### 2026-09-29 — Review pass
- verdicts: 34 findings — high 0, medium 4, low 23, false 7, maybe-false 0
- findings:
  - Blind Hunter
    - `[low]` `[reject]` `in_scope` is False for every `type:` other than the string `feature` (`story`, `change`, absent, `docs+feature`) — verified true, but the intent settles it: `in_scope(spec)` is `type: feature` (Q1, AC 7). Every one of the 40 post-rule story specs in the tree is `feature`, `fix`, `docs` or `chore`, so nothing escapes today; the non-`feature` spellings sit in the pre-rule population. A wider reading is Story 34.2's gate decision and would add a branch beyond the contract.
    - `[low]` `[reject]` `--force` and `--ruling-sha` let `--snapshot` be re-taken — verified true, and identical to `scripts/chain_sprawl_baseline.py`, the shape the intent names. It is a maintainer tool whose rewrite is a visible diff in a tracked file; removing the flags would deviate from the named shape.
    - `[medium]` `[patch]` nothing checks the committed baseline against the ruling commit's tree, so a hand-added or hand-deleted entry passes every test — verified real (the only baseline tests read internal shape). Patched: `test_the_committed_baseline_matches_the_ruling_commits_tree` (skips without the ruling commit; `scripts-suite` uses `fetch-depth: 0`). Mutation-checked: a hand-added and a hand-deleted entry both fail it.
    - `[low]` `[reject]` `--prune` treats a renamed pre-rule spec as removed, so the new name reads post-rule — verified true but it is the intent's own rule ("post-rule exactly when absent from the baseline"; prune "only removes a path that no longer exists"), and without `--prune` the renamed spec is absent anyway. A rename is a new spec; rare. No in-repo caller renames story specs.
    - `[low]` `[reject]` `is_post_rule` returns True for a path outside the repo root — verified true. Callers pass repo-relative or in-root paths (the physical-path rule in AGENTS.md); the path interface belongs to Story 34.2's `--spec`, and a new error class would go beyond the two the intent's matrix names.
    - `[low]` `[patch]` two tests hard-code atlas spec paths — `test_is_post_rule_reads_the_live_baseline` breaks if that spec is pruned. Patched: the baselined path now comes from `read_baseline()["specs"][0]`. `test_the_live_atlas_block_is_flag` stays: it is the one live sample of a full block, and an edit that breaks that block is what the gate should red.
    - `[low]` `[patch]` the page's two fenced examples are never run through `classify`, so the page could rot silently — patched: `test_the_reference_pages_yaml_examples_classify_as_written`.
    - `[low]` `[patch]` the page cites Q1–Q5 without saying where they are defined — patched: the opening paragraph names `docs/governance/spec-feature-flag-governance/SPEC.md`.
    - `[low]` `[reject]` presence-only check: a scalar `default: off`, `provider: launchdarkly` or `scope: tenant` classifies `flag` while the page says otherwise — verified true, but the intent says `flag` "needs all six fields" and gives one reason "per missing field and per unknown value", and the page states that the checker reads presence, not value. Per-environment defaults are Story 34.3's check.
    - `[low]` `[reject]` stamper `_write` sits outside the `try`, and refusals print to stdout — verified true, and the same in `scripts/chain_sprawl_baseline.py`. The baseline's parent is a tracked directory, so the raw traceback is unreachable in a real checkout.
    - `[low]` `[patch]` the population regex leaves six live spec files outside the baseline, one of them a pre-rule `type: feature` (`spec-land-promote-isolation.md`) — verified (six at the ruling SHA). Story 34.2's tree mode walks the same `spec-<E>-<S>-*.md` glob, so it never judges them; the caller risk is the only harm. Patched: `is_post_rule` docstring says it answers for a story spec only, the page says the naming is what puts a spec under the rule, and `spec-land-promote-isolation.md` joins the `is_story_spec` cases.
    - `[low]` `[patch]` the test docstring says PyYAML is missing from `pyforge-ci` — verified false against `pixi.lock` (the `pyforge-ci` block carries `pyyaml-6.0.3`), so the suite runs in the `scripts-suite` lane. Patched: docstring corrected; no pixi task added (`pixi.toml` is outside the intent's surface, and `test_docs_*` accept the same transitive `importorskip`).
    - `[false]` `[reject]` the memlog names no co-governor for the roster edit and the evidence is only asserted — `spec-surface-check` and `spec_surface_reconcile.py` both exit 0 and name no co-governor (`docs/governance/**` is allowlisted); I re-ran both on the final tree.
  - Edge Case Hunter
    - `[medium]` `[patch]` `_frontmatter` catches only `yaml.YAMLError`, so `created: 2026-02-30` makes `classify` and `in_scope` raise `ValueError` — verified by running it. Patched: catches `ValueError` and `OverflowError`; `test_an_impossible_frontmatter_date_is_neither_never_a_raise`.
    - `[low]` `[patch]` `is_post_rule` reads a legacy-named pre-rule spec as post-rule — same root as the population finding above; patched together with it.
    - `[low]` `[reject]` `in_scope` is False for an unreadable frontmatter or a `type` variant — same root as the first row; an unparseable spec already returns `neither` from `classify` with its own reason.
    - `[low]` `[reject]` `--prune` on a sparse or older checkout drops entries — same root as the rename row. The new baseline-vs-ruling-tree test fails in a full clone if such a prune ever lands.
    - `[low]` `[reject]` `repo_relative` on a cwd-relative path, the `_bmad-output/planning-artifacts` symlink alias or another worktree — same root as the outside-the-repo row. An absolute alias path already resolves through `Path.resolve()`.
    - `[low]` `[reject]` `read_baseline` accepts `specs: []` — verified true, but the failure is loud (every spec reads post-rule and the gate reds them all), a truncated file fails JSON parse with the named error, and an empty list is the legitimate end state of a baseline that only shrinks.
    - `[low]` `[reject]` `_write` unguarded — same root as the stamper row above.
    - `[low]` `[reject]` the stamper imports `flag_rule`, which imports `yaml` — the stamper runs once, in `pyforge-guild`, where PyYAML is present; the `chain_sprawl_baseline.py` precedent imports a station package.
    - `[medium]` `[patch]` claim "malformed frontmatter never raises" — false as shipped (same defect as the first Edge row, verified). Fixed by the same patch.
    - `[low]` `[patch]` claim "absent from the baseline means post-rule" for a non-population spec — same root as the population finding; patched with it.
  - Verification Gap
    - `[medium]` `[patch]` the live baseline's contents are never compared with the ruling commit — same root as the Blind Hunter medium row; one patch.
    - `[low]` `[patch]` docstring contradicts the lock, and PyYAML reaches `pyforge-ci` only transitively — docstring patched; the missing explicit leg is not added (see the docstring row above).
    - `[low]` `[patch]` a pre-rule `type: feature` spec is outside the baseline's population — same root as the population finding; patched with it.
  - Intent Alignment
    - `[false]` `[reject]` AC 10 names `pyforge-doctor-test` while the new tests live in `tests/scripts/` — the Boundaries place them there, and AC 10 is the no-collateral guard. The auditor's one failure came from calling the env's python outside the task; `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` exits 0 (2476 passed, 1 skipped), run twice.
    - `[false]` `[reject]` `classify` returns a `(verdict, reasons)` tuple, not a bare string — the intent says it returns `flag` "with its reasons", which needs a pair; no bad outcome shown.
    - `[low]` `[reject]` an extra "field is empty" reason, and presence-only values — same root as the presence-only row; the empty-value reason is a stricter reading of "missing".
    - `[false]` `[reject]` the roster is read before the spec is opened, so a missing roster raises even for a spec with no frontmatter — both matrix rows hold (each in its own state); a missing roster is a hard configuration error either way, and a test pins the order.
    - `[false]` `[reject]` `$comment_flag_exemptions` defines each value — that is the `fold_exemptions` shape the intent names, and the definitions come from the Dream and the Spec's Q2.
    - `[false]` `[reject]` the hard-coded-value scan takes its values from the live roster — the AC 1 test pins the roster to Q2's five, so the scan's values are the AC's five, and a rename fails that test first.
    - `[false]` `[reject]` the page extends Q3 with the frozen-exit-code and two-state-test text — both come from the Spec's own constraints ("Frozen exit-code domains hold in both flag states") and CAP-4.
    - `[low]` `[patch]` `is_post_rule` is True for non-story paths — same root as the population finding; patched with it.

## Auto Run Result

Status: done

**Summary.** The flag rule now has its data, its reader and its one written shape, and judges nothing (Story 34.2 owns the gate). The roster declares the closed exemption list; a rule-date baseline of 1,148 pre-rule story specs is stamped at the PR #1654 merge SHA `5e977accb9643ff81f02ef9feca3e435d86816f9`; `scripts/flag_rule.py` classifies one spec as `flag`, `exempt` or `neither` with one reason per defect; the block's shape is written once on a reference page.

**Files changed.**
- `docs/governance/guild-roster.json` -- `flag_exemptions` (the five Q2 values, in order) and `$comment_flag_exemptions` naming a change a governance act.
- `scripts/flag_rule.py` -- pure classifier: `classify`, `is_post_rule`, `in_scope`, two named errors; reads the roster at call time and imports no station module.
- `scripts/flag_rule_baseline.py` -- mutation-only stamper: `--snapshot` once (from the ruling commit's git tree, `-z`), `--prune` only removes.
- `docs/governance/flag-rule-baseline.json` -- the pre-rule population, stamped by the script.
- `docs/reference/story-spec-flag-block.md`, `docs/map.yaml`, `docs/MAP.md`, `docs/reference/station-verify-commands.md` -- the block's one shape, its registration and the pointer line.
- `scripts/spec_surface_allowlist.txt` -- two reason-tagged lines for the new scripts.
- `docs/governance/spec-feature-flag-governance/.memlog.md` -- surface reconcile entry naming every new and changed path; the detector named no co-governor.
- `tests/scripts/test_flag_rule.py` -- 70 tests: one per acceptance row and per I/O row, the roster-is-the-source scan, the stamper against a temporary git repo, the baseline-versus-ruling-tree check and the page-examples check.

**Review findings.** 34 findings: 14 patched (medium 4, low 10), 20 rejected, 0 deferred.
- Patched: `_frontmatter` raised `ValueError` on an impossible date such as `created: 2026-02-30` (now `neither`); a hand-edited baseline passed every test (now compared with the ruling commit's tree, mutation-checked both ways); a test hard-coded a live atlas path; the page's examples were never classified; the page did not say where Q1-Q5 live; the test docstring misdescribed `pyforge-ci`; `is_post_rule` answers for `spec-<E>-<S>-*.md` only (documented, plus a test row).
- Rejected, with reasons in the Review Triage Log: `in_scope` reads only `type: feature` (the intent's own definition); `--force`, unguarded `_write` and stdout messages (the `chain_sprawl_baseline.py` shape the intent names); prune-on-rename and paths outside the repo root (the intent's own rule; Story 34.2 owns the path interface); presence-only value checks (Story 34.3); and seven findings shown false or contradicted by the Spec.

**Verification performed** (exit codes read directly, never through a pipe; on the final tree).
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_flag_rule.py -q` -- exit 0, 70 passed.
- `pixi run -e pyforge-guild docs-currency-check` -- exit 0. `pixi run -e pyforge-guild spec-surface-check` -- exit 0. `python scripts/spec_surface_reconcile.py` -- exit 0 ("every tracked file governed or allowlisted; no drift"). `pixi run -e pyforge-guild governance-currency` -- exit 0. `--write-baseline` was never passed.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- exit 0, 2476 passed, 1 skipped.
- `pixi run -e pyforge-guild python -m pytest tests/scripts -q` -- exit 0, 888 passed, 4 skipped.
- The baseline was recomputed independently from `git ls-tree -r -z` at the ruling SHA and matched byte for byte (1,148 paths). Every post-rule story spec in the tree (40) classifies `flag` (19) or `exempt` (21).

**Follow-up review recommendation: `true`.** Two medium entries were patched (the impossible-date crash and the baseline-versus-ruling-tree check). The unverified risk: `tests/scripts/test_flag_rule.py` was run only from `pyforge-guild`; the `pyforge-ci` env (the `scripts-suite` lane) was not installed here, so its run there rests on `pixi.lock` carrying `pyyaml` and on `git` being present for the stamper tests. The baseline-versus-ruling-tree test skips in a clone without the ruling commit; `scripts-suite` uses `fetch-depth: 0`.

**Residual risks.**
- `is_post_rule` reports any path outside `spec-<E>-<S>-*.md` (six legacy-named specs at the ruling SHA, one of them `type: feature`) as post-rule; Story 34.2's tree mode walks the same glob, so it must keep filtering with `is_story_spec`.
- `in_scope` is False for a spec whose frontmatter cannot be read; Story 34.2 should surface an unparseable post-rule spec from `classify`'s reason rather than rely on `in_scope`.
- The test file has no dedicated pixi leg; it runs in `pyforge-doctor-scripts-test` (transitive PyYAML), as `test_docs_*` do.
