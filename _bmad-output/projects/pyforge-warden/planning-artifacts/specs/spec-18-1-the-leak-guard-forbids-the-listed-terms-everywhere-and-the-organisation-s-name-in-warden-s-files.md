---
title: "18.1: The leak guard forbids the listed terms everywhere and the organisation's name in warden's files"
type: 'fix'
created: '2026-10-11'
status: 'done'
landing_review: 'passed'
baseline_revision: 'e872476980ee67672170f68477e6f080b865a2ce'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-1-warden-inventories-a-ghe-organisation-s-repos.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-5-warden-inventories-the-items-of-the-operator-designated-github-projects.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - docs/dreams/pyforge-warden.md
  - src/platform/tests/test_warden_fleet_inventory.py
  - src/shared/packages/django-warden/src/django_warden_fabric/fleet_inventory.py
  - .claude/memory/README.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the leak guard forbids the operator-designated organisation's name in every file it scans, but that name
is public and already appears in files the operator wrote before warden existed. With the operator's real
configuration present the guard fails on them, so it cannot cover the whole tree, which is where the private names
(the repositories and projects) need guarding.

Line numbers below are at the Story 16.5 branch tip `b4e89a7930` (PR #2146), which this story builds on (Deps
S-16.5). Main at `d6f61ddba1` holds Story 16.1's guard without 16.5's changed-files scan.

- **The guard today** (`src/platform/tests/test_warden_fleet_inventory.py`):
  - `_leak_guard_terms()` (:798-:805) returns `[organisation.lower(), *leak_guard_terms]` from the configured target,
    through `load_organisation_from_config` and `load_leak_guard_terms`, or `None` when the config is absent.
  - `_LEAK_SCAN_ROOTS` (:107-:123) lists the roots it scans: warden's project, both warden packages, all of
    `src/platform/`, the station Dream, `.gitignore`, `.claude/memory/`, three co-governor memlogs and
    `pyforge-core/tests/unit/test_flags.py`.
  - `_story_changed_files()` (:836-:852) adds every file the branch changes against `origin/main` (committed, staged,
    unstaged and untracked), and never `.warden/`.
  - `_leak_hits()` (:855-:873) reports each scanned file that contains any term, as a case-insensitive fixed string,
    by path only.
  - `test_leak_guard_no_operator_terms_in_tracked_tree` (:965-:970) runs it live, and skips when the config is absent
    (CI).
- **The config reader.** `load_leak_guard_terms`
  (`src/shared/packages/django-warden/src/django_warden_fabric/fleet_inventory.py:136-:153`) returns `[]` when the
  config is absent, has no `[github]` table or has no `leak_guard_terms` key. It refuses a value that is not a list of
  strings (16.1's N5) and drops blank entries. The guard is its only caller (`git grep -n load_leak_guard_terms` at
  `d6f61ddba1`).
- **The defect.** The organisation's name is always a term. On 2026-10-11 the orchestrator checked, against the
  operator's real configuration kept outside the repository, that the name appears in 31 operator-authored tracked
  files that predate warden: Dreams, research notes, links to public repositories under that organisation, and a `gh`
  inventory note. The organisation is public. What must stay private is that warden inventories it, and which of its
  repositories and projects. With the real configuration present:
  - the guard fails on each of those files it scans;
  - a story that edits one of them goes red through the changed-files scan;
  - the guard cannot widen to the whole tree, which is where the repository and project names need guarding.
- **A second gap.** A configuration with no `leak_guard_terms` makes the guard check the organisation alone. Once the
  organisation leaves the global terms, such a configuration would check nothing outside warden's files and still pass.

**Ruling.** Operator, 2026-10-11 (AskUserQuestion; the chosen option's label and text, verbatim; the
`spec-pyforge-warden` memlog records it): "Drop org from terms (Recommended)", "The org is already public in your own
docs; what must stay private is that warden inventories it, and which repos and projects. The guard forbids only the
leak_guard_terms you list (repo and project names) plus the org name in warden's own files (pyforge-warden,
django-warden, warden specs and memlogs). A small warden fix story."

**Approach:** two rules over one scan.

- **The files scanned.** Every tracked file of the checkout (`git ls-files -z`, no pathspec), plus every file the
  branch changes (`_story_changed_files`, unchanged: `.warden/` is never read). Measured at `d6f61ddba1`: 26,037
  tracked files, about 262 MB; `cat` reads them all in under a second. Binary files decode with `errors="replace"`, as
  today.
- **Rule T, the listed terms.** Each `leak_guard_terms` entry is forbidden in every scanned file. Entries are
  stripped and compared case-insensitively as fixed strings.
- **Rule O, the organisation.** The organisation's name, stripped and compared case-insensitively as a fixed string,
  is forbidden only in warden's own files:
  1. *Whole file*, for a path in the declared warden-owned set (one constant of repo-relative POSIX paths):
     - `src/shared/packages/pyforge-warden/` and `src/shared/packages/django-warden/`: warden's code and tests.
     - `_bmad-output/projects/pyforge-warden/`: its Spec and memlog, epics, ledger, story specs and research.
     - `docs/dreams/pyforge-warden.md`: the station Dream. Every new warden Dream entry lands there (one chain per
       station).
     - `src/platform/tests/test_warden_*.py`: warden's platform tests, this guard's own file included.
     - `.claude/skills/pyforge-warden/` and `.claude/skills/bmad-agent-warden/`: warden's station skill and persona.
     - `presentations/pyforge-warden/`: warden's chapter deck.
  2. *Whole entry*, for a team-memory entry `.claude/memory/<type>/<slug>.md` whose text names warden.
  3. *One line*, for these files: `.claude/memory/MEMORY.md` (one line per entry); every `.memlog.md` outside
     `_bmad-output/projects/pyforge-warden/` (one line per entry; warden stories append surface reconciles to
     co-governors' memlogs); and every other file the branch changes. In them, a line that names warden must not name
     the organisation.
  - *Names warden* means `re.search(r"(?<![a-z])warden(?![a-z])", text.lower())`: `pyforge-warden`,
    `django_warden_fabric` and `Warden` match; `vaultwarden` does not.
  - Every other file may name the organisation.
  - Left out on purpose: the folded warden Dreams and `archive/`, which are frozen and never written again; and other
    stations' files, which the ruling leaves public. Units 2 and 3 keep the places Story 16.5 scanned for the
    organisation (team memory, the co-governor memlogs) without failing on the operator's earlier mentions there.
- **Empty terms are refused.** With the config present, a missing, empty or all-blank `leak_guard_terms` raises
  `FleetTargetConfigError` naming `leak_guard_terms` and the config path, never a value, unless `[github]` sets
  `allow_empty_leak_guard_terms = true`.
  - The opt-in must be a TOML boolean. Any other type is refused the same way.
  - With the opt-in, Rule T checks nothing and Rule O still runs.
  - The check sits in `load_leak_guard_terms`, beside 16.1's non-list refusal.
  - With the config absent, the live test still skips and names the path (CI).
- **Output.** A failure lists repo-relative paths, sorted and de-duplicated. It never prints a term, the organisation
  or a matched line.
- **Shape.** The scan helpers take the repo root and the file list as arguments, so each acceptance test runs on a
  temporary git repository with a fixture config; the live test composes them over `_REPO_ROOT`. The warden-owned set
  replaces `_LEAK_SCAN_ROOTS`, and `test_leak_guard_scan_roots_exist` checks the new set instead. The tests stay in
  the platform file: the guard and its helpers live there, warden's own tests cannot import them, and the dispatch runs
  the platform suite as its cross-surface check.

Ledger key: `18-1-the-leak-guard-forbids-the-listed-terms-everywhere-and-the-organisation-s-name-in-warden-s-files`.
Type / Effort / Deps: fix / S / S-16.5.

### Living CAP citations

- `spec-pyforge-warden` CAP-26 (FR-43): Story 16.1's AC9 and Story 16.5's changed-files scan. This story fixes how
  they guard the target's names. It changes no behaviour CAP-26 names, so no CAP is minted and `SPEC.md` does not
  change. The Spec memlog's 2026-10-11 decisions (the target is never named in a tracked file) govern it, as they do
  16.1 and 16.5.
- No flag: under `spec-feature-flag-governance` Q1 a `fix` needs no flag, and this one changes only a test and the
  config reader.

## Acceptance Criteria

Each of AC1-AC5 runs on a temporary git repository (`git init`, fixture files committed, hooks off, no signing). Its
fixture config is written under `tmp_path` and named through `WARDEN_FLEET_TARGET_CONFIG`:
`organisation = "example-org"`, `leak_guard_terms = ["example-repo", "example-project"]`. No real name appears in any
test.

- **AC1 — The organisation in a non-warden file passes.**
  - **Given** tracked files that name `Example-Org` (mixed case) and do not name warden: `docs/dreams/other.md`,
    `src/platform/tests/test_other.py`, `.claude/memory/project/old-note.md`, a line of `.claude/memory/MEMORY.md`, and
    a line of `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-x/.memlog.md`.
  - **And** an unchanged tracked file outside every class that names warden on one line and the organisation on
    another.
  - **When** the guard scans, **Then** it reports no path.
- **AC2 — The organisation in a warden file fails.**
  - **Given** the same name placed once in each of these:
    - a tracked file under each entry of the warden-owned set (one file per entry, the `test_warden_*.py` glob
      included);
    - a `.claude/memory/project/<slug>.md` entry that names warden on another line;
    - a `MEMORY.md` line that names warden;
    - a co-governor `.memlog.md` line that names warden.
  - **When** the guard scans, **Then** it reports exactly those paths, sorted.
  - **And** its output holds neither `example-org` nor any term.
- **AC3 — A listed term fails anywhere.** **Given** `EXAMPLE-REPO` in a tracked non-warden file, `example-project`
  in a tracked warden file, and `example-repo` in a tracked file outside every class (for example
  `recipes/x/recipe.yaml`), **When** the guard scans, **Then** it reports all three.
- **AC4 — The branch's changed files carry both rules.**
  - **Given** a base commit, and after it:
    1. a committed file outside the warden-owned set naming `example-repo`;
    2. an untracked file under `src/shared/packages/pyforge-warden/` naming `example-org`;
    3. an unstaged edit to a tracked non-warden file, adding a line that names warden and `example-org`;
    4. an untracked non-warden file naming `example-org` and not warden;
    5. an unstaged edit to a tracked non-warden file, adding warden on one line and `example-org` on another;
    6. `.warden/fleet-target.toml` naming `example-org` and `example-repo`.
  - **When** the guard scans the tracked files plus `_story_changed_files(..., base=<the base>)`, **Then** it reports
    1, 2 and 3, and not 4, 5 or 6.
  - **And** `.warden/` is never opened.
- **AC5 — An empty term list is refused.**
  - **Given** the config present with no `leak_guard_terms`, with `leak_guard_terms = []`, and with
    `leak_guard_terms = ["  "]`, **When** the terms are loaded, **Then** each raises `FleetTargetConfigError`. Its
    message names `leak_guard_terms` and the config path, and no value.
  - **Given** `allow_empty_leak_guard_terms = true` and no terms, **Then** loading succeeds, Rule T checks nothing, and
    `example-org` in a warden file still fails.
  - **Given** `allow_empty_leak_guard_terms = "true"` (a string) or `= 1`, **Then** it is refused.
  - **Given** the config absent, **Then** the live test skips and names the path.
  - 16.1's `test_leak_guard_skips_when_config_absent` and `test_leak_guard_terms_must_be_a_list` keep passing.
- **AC6 — Mutations.** Run each on a copy, or restore it from a backup and prove the restore against the last commit:
  `git diff HEAD --stat` is empty for both files. The harness auto-checkpoint can commit a mutation, so `cmp` against
  a backup alone is not proof.
  - Add the organisation back to the global terms (Rule T): AC1's test fails.
  - Remove Rule O's warden-owned check: AC2's test fails.
  - Remove the empty-terms refusal: AC5's test fails.
  - The spec's Auto Run Result records each outcome.
- **AC7 — The live guard scans the whole tree.**
  - `test_leak_guard_no_operator_terms_in_tracked_tree` passes every tracked file (`git ls-files`, no pathspec) and
    `_story_changed_files(_REPO_ROOT)` through both rules.
  - `test_leak_guard_scan_roots_exist` asserts that each warden-owned entry exists in the checkout and has at least
    one tracked file, so a renamed directory cannot drop out silently.
  - `test_leak_guard_reads_the_configured_target` checks the new return shape, with the organisation and the terms
    apart.
  - In the dispatch worktree the config is absent, and the live test skips.
- **AC8 — Live, against the real configuration.**
  - Before landing, the orchestrator (never the implementer) runs the platform guard tests with
    `WARDEN_FLEET_TARGET_CONFIG` naming the operator's real configuration, which is kept outside the repository. The
    live test passes.
  - The Review Triage Log records that the run happened and passed, and the commit it ran at. It never records a term
    or the organisation.
  - If the run fails, the implementer adds no exemption. The orchestrator brings the reported paths to the operator.
- **AC9 — Never weakened, nothing else moves.**
  - The diff adds no `skip`, `skipif`, `xfail` or rerun beyond the existing config-absent skip.
  - It drops no 16.1 or 16.5 guard test: each is kept, or updated to the new shape.
  - Outside `_bmad-output/` and `scripts/.spec-surface-baseline.json`, `git diff origin/main...HEAD --stat` names
    only `src/platform/tests/test_warden_fleet_inventory.py` and
    `src/shared/packages/django-warden/src/django_warden_fabric/fleet_inventory.py`, plus a team-memory capture if the
    run makes one.
  - The inventory, the project-items reader, the exports, `.gitignore` and the flags do not change.
- **AC10 — Gates and surface.**
  - `pixi run --frozen -e pyforge-warden pyforge-warden-test` exits 0.
  - `pixi run -e pyforge-guild platform-ci-local -- --test` exits 0.
  - The `spec-pyforge-unifying-strategy` memlog gets one surface-reconcile entry naming both files and this story.
    The Spec is stamped scoped (`--spec pyforge-steward/spec-pyforge-unifying-strategy`), and `spec-surface-check`
    exits 0.

## Boundaries & Constraints

**Always:**
- Keep the guard in `src/platform/tests/test_warden_fleet_inventory.py`. Reuse 16.5's `_story_changed_files` and
  16.1's config loaders.
- Use fictional identifiers only: `example-org`, `example-repo`, `example-project`.
- Print paths only on failure.
- Declare the warden-owned set as one constant, so a reviewer reads it in one place.

**Never:**
- Name the operator-designated organisation, its repositories or its projects in a tracked file, a test, a fixture,
  a commit message, a PR body or a memlog. The implementer never learns them.
- Read anything under `.warden/` from a test, or the operator's real configuration from the dispatch.
- Reach the network, or run `gh`.
- Widen an exemption to make the live run pass.
- Change the inventory, the project-items reader, their exports, `.gitignore` or a flag.

**Residual risk:**
- Rule O's line unit catches warden and the organisation on one line of a shared log or a changed file. A paragraph
  that names warden on one line and the organisation on the next, in a file outside the warden-owned set and the
  memory entries, passes. The whole-file and whole-entry units cover the places warden writes most.
- The guard reads contents, not path names. A tracked path whose name alone holds a listed term passes, as today.
- A listed term that is a common word fails across the tree. The operator lists distinctive strings.
- The whole-tree scan reads every tracked file on each platform run: at 262 MB, a few seconds. A much larger tree
  would want a size cap, recorded then.
- The live guard runs only where the operator's configuration is; CI and the dispatch skip it.

## I/O & Edge-Case Matrix

| Situation | Today (16.5 tip `b4e89a7930`) | After |
|---|---|---|
| the organisation in an operator Dream that never names warden | fails, when the file is scanned | passes |
| the organisation in `src/shared/packages/pyforge-warden/**` | fails | fails |
| the organisation in a team-memory entry that names warden | fails (`.claude/memory/` is a root) | fails |
| the organisation on a `MEMORY.md` line that does not name warden | fails | passes |
| a listed repository name in any tracked file | fails only under the roots or in a changed file | fails anywhere |
| a story edits a Dream that names the organisation | fails (changed-files scan) | passes, unless one line names warden and the organisation |
| a config with no `leak_guard_terms` | checks the organisation alone | refused, naming the key |
| `allow_empty_leak_guard_terms = true` and no terms | not a key | Rule O only |
| the config absent (CI, the dispatch) | skips, naming the path | skips, naming the path |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-warden` CAP-26 (FR-43), through Story 16.1's AC9 and Story 16.5's
  changed-files scan. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the *2026-10-11 (leak guard terms)* entry.
- Epic: Epic 18 (new), minted with `epic-18` (`backlog`) and `epic-18-retrospective` (`optional`). Epic 16 holds the
  fleet features and closes when Story 16.5 lands; this fix builds on 16.5 and does not reopen it.
- Ledger key: `18-1-the-leak-guard-forbids-the-listed-terms-everywhere-and-the-organisation-s-name-in-warden-s-files`.
- Ledger status at mint: `backlog`.
- Deps: S-16.5 (station-local; PR #2146 was landing at mint). This story's line numbers and its changed-files helper
  are 16.5's.
- Co-governors, from the Specs' `surface:` globs and `scripts/.spec-surface-baseline.json`: both code files are on
  `pyforge-steward/spec-pyforge-unifying-strategy`'s surface (`src/platform/**`, `src/shared/packages/django-*/**`).
  `spec-pyforge-warden`'s surface is `src/shared/packages/pyforge-warden/**`, so it reconciles nothing here unless a
  warden-package file changes.
- Spec memlog: the `spec-pyforge-warden` memlog records the ruling verbatim, the design and this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."18"` (added with this mint) covers both files, warden's package,
  specs and ledger, and every Spec memlog.
- Minted 2026-10-11 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding). It does not run `src/platform/tests`; because the diff touches `src/platform/`, the dispatch runs `pixi run -e pyforge-guild platform-ci-local -- --test` as its cross-surface check (MRS-GATE-015).

**Run before the push (not dispatch gates):**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: exit 0 (AC1-AC5, AC7, AC10, with Ruff, Ruff format and mypy over the platform tests). The live guard skips: the worktree has no config.
- The AC6 mutations — expected: each named test fails; each file is then restored and proved against the last commit.
- `git diff origin/main...HEAD --stat` — expected: AC9's two code paths.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entry and the scoped stamp (AC10).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: no new finding against `main`.
- `pixi run -e pyforge-guild python scripts/flag_gate_check.py --spec _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-18-1-the-leak-guard-forbids-the-listed-terms-everywhere-and-the-organisation-s-name-in-warden-s-files.md` — expected: pass (a `fix` carries no flag).

**Manual checks:**
- AC8, by the orchestrator only, before landing: export `WARDEN_FLEET_TARGET_CONFIG` as the path of the operator's
  real configuration, kept outside the checkout, then run `pixi run -e pyforge-guild platform-ci-local -- --test` from
  the story's worktree (the script passes the environment through). Expected: exit 0, and a skip count one lower than
  the same run without the variable, because the live guard ran instead of skipping. Record the outcome and the commit
  in the Review Triage Log, without any name.

## Spec Change Log

- 2026-10-11: minted from the operator's ruling "Drop org from terms (Recommended)". `type: fix`, no flag, no CAP;
  bound to `spec-pyforge-warden` CAP-26 through Stories 16.1 and 16.5.

## Review Triage Log

### 2026-10-12 — Orchestrator verification and AC8 live run: passed

The orchestrator (not the implementer, not either reviewer) read the N1-N4 delta at 12223003af and re-ran one mutation: dropping the `.warden/` filter from `_all_tracked_files` reds `test_leak_guard_never_opens_a_tracked_warden_file` (1 failed, 18 passed); restored byte-identical. AC8: the live test `test_leak_guard_no_operator_terms_in_tracked_tree` ran against the operator's real configuration (organisation plus the two listed repository names, kept outside the repository and pointed at through `WARDEN_FLEET_TARGET_CONFIG`) and PASSED (1 passed, not skipped, 3.08 s); its output carried none of the real terms. The implementer's gates after the last edit: `pyforge-warden-test` 0 (2440 passed), `lint-types` 0, `platform-ci-local -- --test` 0 (1350 passed, 14 skipped), `spec-surface-check` 0, flag gate `--spec` pass, `deferred-work-check` 0. Story done; landing review passed; landing proceeds.

### 2026-10-12 — Fix pass for iteration 2 lows (implementer)

Implementer pass on N1-N4, uncommitted on `dispatch/pyforge-warden/18.1` at 4f6d32fc68. Only
`src/platform/tests/test_warden_fleet_inventory.py` changes; `fleet_inventory.py` does not. Only `example-*`
identifiers are used; nothing under `.warden/` was read; no network, no `gh`.

- N1 fixed: three tests run the live test itself against a `leak_repo` fixture. Each patches the module's `_REPO_ROOT`
  and puts `refs/remotes/origin/main` at the base commit (`_live_fixture_repo`, `:1361`).
  - `test_leak_guard_live_test_fails_with_paths_only` (`:1371`) asserts `pytest.fail.Exception` with exactly
    `committed.txt` and `docs/term.md`, and no term or organisation in the message. `committed.txt` (warden and the
    organisation on one line, committed after the base) is reported only through the `origin/main...HEAD` leg.
  - `test_leak_guard_live_test_passes_on_a_clean_repo` (`:1396`): the organisation alone, no warden, passes.
  - `test_leak_guard_live_test_reports_errors_without_values` (`:1408`): a scan raising an error that carries a term
    fails with `RuntimeError during the leak-guard scan` alone. A config with no terms fails with the key and the
    path, never the organisation.
- N2 fixed: AC2's sample for `_bmad-output/projects/pyforge-warden/**` is now nested and hidden
  (`.../planning-artifacts/specs/spec-pyforge-warden/.memlog.md`, `:1159`). It replaces the one-level `note.txt`, so
  each entry keeps exactly one sample and a widened entry still fails.
- N3 fixed: `test_leak_guard_reads_the_configured_target` (`:1066`) lists a term padded with spaces and a tab, and
  asserts the stripped value.
- N4 fixed:
  - AC4 is parametrised (`:1225`). Its `warden-not-ignored` case has no `.warden/` line in `.gitignore`, so the
    untracked leg lists the target file and only the guard's own filter keeps it out.
  - `_all_tracked_files` (`:834`) now excludes paths under `.warden/` (`_in_warden_target_dir`, `:829`), so a
    force-added target file is never opened. `_guard_scan` reports such a tracked path by name, without opening it
    (`:1013`).
  - `test_leak_guard_never_opens_a_tracked_warden_file` (`:1334`) force-adds `.warden/fleet-target.toml` with a spy
    on `Path.read_bytes`. It asserts the guard reports that path, and that no file under `.warden/` was read.
  - The live tree tracks no `.warden/` path, checked by name with `git ls-files`.

Mutations. Each was applied in place, the named tests run, and the file restored. Each restore was proved
byte-identical to the pre-mutation copy, with HEAD unmoved and the `git diff HEAD` hash unchanged. All were caught:
- N1: the wrapper always returns None, the fails-with-paths test red. Errors swallowed to None, the errors test red.
  `pytest.fail` dropped, both red. The live scan with `base="HEAD"`, the fails-with-paths test red.
- N2: `full_match` swapped for `match` in `_is_warden_owned_whole_file`: AC2 red.
- N3: `.strip()` dropped from `load_leak_guard_terms`: the configured-target test red.
- N4: the `.warden/` filter dropped from `_story_changed_files`: AC4 `warden-not-ignored` red (`warden-ignored`
  stays green, which shows why the variant is needed). The filter dropped from `_all_tracked_files`: the force-added
  test red. The tracked-path naming dropped: the force-added test red.

Gates: `pyforge-warden-test` 0 (2440 passed); `lint-types` 0; `platform-ci-local -- --test` 0 (1350 passed, 14 skipped;
the live guard skips, config absent); `spec-surface-check` 0 (no drift named, so no memlog entry or stamp); flag gate
`--spec` 0 (pass); `deferred-work-check` 0. Status stays `in-progress`.

### 2026-10-12 — Independent review, iteration 2: passed (4 low)

Fresh separate agent, review at 97c2af17d6. F1-F7 closed, each confirmed by the reviewer's own mutation (unstaged/untracked/committed legs, the warden-owned constant's entries, the fixture config routed through `WARDEN_FLEET_TARGET_CONFIG`, `_guard_scan` composition, the boundary regex, `NoReturn`); the AC6 mutations caught. F6 confirmed under `pytest -l -rA -vv --tb=long` with fictional configs: terms present, empty terms and an undecodable config each fail with paths or a type name only, 0 output lines carrying a term. `PurePosixPath.full_match` on Python 3.14.7 matches `/**` nested and dot-files, `test_warden_*.py` within one segment. 31 mutations, 20 caught; the survivors below or unreachable. Confidentiality clean across the diff, every history-only line of the branch's 10 commits, the commit messages and PR #2158. Gates: `pyforge-warden-test` 0 (2440 passed), `lint-types` 0, `spec-surface-check` 0, flag gate `--spec` pass, `deferred-work-check` 0, `platform-ci-local -- --test` 0 (1345 passed, 14 skipped); `detectors-ci` 1 only on `ledger-direction` (branch behind main).

- `[low]` `[patch]` N1 `src/platform/tests/test_warden_fleet_inventory.py:1010-1023, 1311-1321` nothing exercises the live test's fail path (the wrapper always returning None, swallowing errors, dropping `pytest.fail`, scanning with `base="HEAD"` all survive). Fix: a test pointing the module's `_REPO_ROOT` at a `leak_repo` fixture with an `origin/main` ref at the base, asserting `pytest.fail.Exception` with exactly the expected paths and no term, and a pass on a clean repo.
- `[low]` `[patch]` N2 `:1143-1152` AC2's samples all sit one level below their entry; swapping `full_match` for `match` survives. Fix: one nested, hidden sample (a warden spec memlog).
- `[low]` `[patch]` N3 `fleet_inventory.py:165`, test `:1057-1067` nothing pins the stripping of listed terms (dropping `.strip()` survives). Fix: a padded term in the configured-target test.
- `[low]` `[patch]` N4 `:911-920`, `:829-838` AC4's fixture ignores `.warden/` in `.gitignore`, so the explicit `.warden/` filter is never exercised; `_all_tracked_files` excludes nothing, so a force-added `.warden/` file would be opened. Fix: an AC4 variant without the ignore line, and exclude `.warden/` from the scan set.
- Info: N5 dropping the regex lookahead only makes Rule O stricter (reject); N6 the harness-written Auto Run Result is stale; N7 a path whose name holds a listed term prints it only when its content holds a term too (beside the recorded residual risk; defer).

N1-N4 are fixed in a follow-on pass before landing; the orchestrator re-verifies that delta and runs AC8 (the live guard against the operator's real configuration, kept outside the repository) before setting `landing_review: 'passed'`.

### 2026-10-12 — Fix pass for iteration 1 (implementer)

Implementer pass on F1-F8, uncommitted on `dispatch/pyforge-warden/18.1` at e11b82c989. Only `example-*` identifiers
are used; nothing under `.warden/` was read; no network, no `gh`.

- F1 fixed: `test_leak_guard_ac4_changed_files_carry_both_rules` (`:1208`) commits `edited.txt` and `split.txt` in the
  base and adds their new lines as unstaged edits. It asserts that `_story_changed_files(..., base="base")` lists
  exactly `committed.txt`, `edited.txt`, `plain.txt`, `split.txt` and the untracked warden file, and that the guard
  reports 1, 2 and 3 only.
- F2 fixed: one constant, `_LEAK_WARDEN_OWNED` (`:109`), holds `PurePosixPath.full_match` patterns (six directories,
  the Dream, the `test_warden_*.py` glob). `_is_warden_owned_whole_file` (`:818`) and `test_leak_guard_scan_roots_exist`
  (`:1040`) both read it; the second list (`_leak_warden_owned_roots`) and `_tracked_files_under` are gone. The
  existence test checks a wildcard entry with the guard's own matcher over `git ls-files` (`_tracked_owned_matches`,
  `:923`), and a file entry with `git ls-files --error-unmatch` and `is_file()`. AC2 also asserts that exactly one of
  its literal samples covers each entry.
- F3 fixed: `_fixture_leak_config` is used. The `leak_repo` fixture (`:941`) writes it beside the repository and names
  it through `WARDEN_FLEET_TARGET_CONFIG`; `_guard_scan` (`:988`) reads the organisation and the terms only through
  `_leak_guard_target()`. AC5's opt-in leg routes its config the same way, and adds a non-warden file naming a term,
  which passes (Rule T checks nothing).
- F4 fixed: the live test calls `_guard_scan(_REPO_ROOT)` through `_live_guard_failure` (`:1010`); no inline
  composition remains.
- F5 fixed: `test_leak_guard_warden_name_boundary` (`:1035`) is parametrised: `pyforge-warden`, `django_warden_fabric`
  and `Warden` match; `vaultwarden` does not.
- F6 fixed: the live test (`:1311`) holds only the config path and the failure text, and fails with
  `pytest.fail(text, pytrace=False)` outside any handler. `_live_guard_failure` returns the paths, a
  `FleetTargetConfigError` message (key and path, no value), or for any other error its type alone. The frames that
  held the organisation and the terms have returned before the test fails.
- F7 fixed: `_refuse_missing_leak_guard_terms` is annotated `NoReturn` (`fleet_inventory.py:141`).
- F8 deferred: `DW-warden-18-1` in `planning-artifacts/deferred-work-ledger.md`.

Mutations. Each was applied in place, the named tests run, and the files restored. Because this pass is uncommitted,
each restore was proved three ways: byte-identical to the pre-mutation copy, HEAD unmoved, and `git diff HEAD`
hashing the same before and after.
- AC6: the organisation back in the global terms: AC1 red. Rule O's whole-file check removed: AC2 red. The
  empty-terms refusal removed: AC5 red.
- F1: the `diff --name-only HEAD` leg removed: AC4 red (it survived before this pass). The untracked leg removed: AC4
  red. The committed `base...HEAD` leg removed: AC4 red.
- F2: `bmad-agent-warden/**` typo'd: `test_leak_guard_scan_roots_exist` and AC2 red. The Dream file entry typo'd: both
  red. The `test_warden_*.py` glob dropped: AC2 red.
- F3: the fixture config's terms changed: AC3 red.
- F4: `_guard_scan` drops `changed_rel`: AC4 red. The `or rel in changed_rel` line scope removed: AC4 red.
- F5: a bare `warden` regex: the `vaultwarden` case red.
- F6: the live test alone under `pytest -l -rA`, with fictional configs kept outside the checkout. With the terms
  present in the tree, it fails listing paths, and 0 output lines carry `example-org`, `example-repo` or
  `example-project`. With no terms, it fails with the refusal message alone, again 0 such lines. The pre-fix test file
  under the same two runs printed the `organisation` and `terms` locals (2 and 3 such lines); it was restored and
  proved as above.

Gates: `pyforge-warden-test` 0 (2440 passed); `lint-types` 0; `pixi install --frozen -e platform-ci-test` 0, then
`platform-ci-local -- --test` 0 (1345 passed, 14 skipped; the live guard skips, config absent); `spec-surface-check` 0
(it names no drift, so no new memlog entry or stamp; the AC10 entry stands); `detectors-ci` 0 (46 detectors pass, branch
not behind `origin/main`); flag gate `--spec` 0 (pass); `deferred-work-check` 0. Status stays `in-progress`; the
iteration-2 independent review gates the landing.

### 2026-10-12 — Independent review, iteration 1: sent back (2 medium, 5 low patch; 1 low defer)

Separate agent, review at 7faa149aec against the merge-base. The production logic is correct: every AC6 mutation the spec names is caught (organisation back in the global terms, Rule O removed, the empty-terms refusal removed, Rule T removed, each changed-file leg but one, team-memory/MEMORY.md/external-memlog units removed, a case-sensitive scan, a non-boolean opt-in, the `test_warden_*.py` glob removed). The live guard over the full tracked tree took about 3.9 s. Confidentiality: only `example-*` identifiers in the diff, spec, commit messages and PR; nothing under `.warden/` read. Gates: `pyforge-warden-test` 0 (2440 passed), `lint-types` 0, `spec-surface-check` 0, flag gate `--spec` pass, `platform-ci-local -- --test` 0 (1341 passed, 14 skipped); `detectors-ci` 1 only on `ledger-direction` (branch behind main).

- `[medium]` `[patch]` F1 `src/platform/tests/test_warden_fleet_inventory.py:1188-1198` AC4's "unstaged edit to a tracked non-warden file" is never exercised: the test commits `edited.txt`/`split.txt` after the base and rewrites them with the same bytes, so deleting the `diff --name-only HEAD` leg survives (a regression against 16.5's test). Fix: base-commit both files, add the new lines unstaged, assert the changed-file list.
- `[medium]` `[patch]` F2 `:936-1026` vs `:105-113` the scan-roots existence test checks a second hand-kept list, not the guard's constants (`_LEAK_WARDEN_OWNED_DIR_PREFIXES`, `_LEAK_WARDEN_OWNED_FILES`, the inline `test_warden_` string); its file branch is tautological; a typo'd `bmad-agent-warden/` prefix survives. Fix: one constant used by both, `git ls-files --error-unmatch` for file entries.
- `[low]` `[patch]` F3 `:949` `_fixture_leak_config` is dead; AC1-AC4 never route the fixture config through `WARDEN_FLEET_TARGET_CONFIG` as the spec says. Fix: route `_guard_scan` through the env var and `_leak_guard_target()`, or delete the helper and amend the spec.
- `[low]` `[patch]` F4 `:1263-1279` the live test repeats `_guard_scan`'s composition inline (dropping `changed_rel` survives). Fix: the live test calls `_guard_scan`.
- `[low]` `[patch]` F5 `:114` no test pins the `warden` boundary rule (a bare `warden` regex survives). Fix: a parametrised test (`pyforge-warden`, `django_warden_fabric`, `Warden` match; `vaultwarden` does not).
- `[low]` `[patch]` F6 the live test's failure output prints the `organisation` and `terms` locals under `pytest -l`. Fix: `pytest.fail("\n".join(paths), pytrace=False)` with no term-bearing locals in the failing frame.
- `[low]` `[patch]` F7 `fleet_inventory.py:141` `_refuse_missing_leak_guard_terms` always raises; annotate `NoReturn`.
- `[low]` `[defer]` F8 Rule T compares fixed strings: a multi-word listed term wrapped across a line, or zero-width / full-width variants, pass. Not required by the spec (paragraph splits already a recorded residual risk); a warden deferred-work row.
- Info: AC8 (the live run against the operator's real configuration) is the orchestrator's, run before landing.

Send-back: F1-F7 in one pass, F8 as a deferred-work row; a fresh independent review (iteration 2) gates the landing.

### 2026-10-12 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (Bugbot review of branch diff; no defects filed.)
- AC8: orchestrator-only live run with operator configuration not performed in this dispatch (config absent in worktree).

## Auto Run Result

Status: done

**Summary:** Split the leak guard into Rule T (`leak_guard_terms` anywhere in the scan set) and Rule O (organisation name only in warden-owned paths, warden-named memory entries, and line-scoped co-governor/changed files). The scan set is all tracked files plus branch changed files (`.warden/` still excluded). `load_leak_guard_terms` now refuses missing/empty term lists unless `allow_empty_leak_guard_terms = true` (boolean).

**Files changed:**
- `src/platform/tests/test_warden_fleet_inventory.py` — guard helpers, warden-owned constants, AC1–AC5 fixture tests, live test uses whole tree.
- `src/shared/packages/django-warden/src/django_warden_fabric/fleet_inventory.py` — empty-term refusal and opt-in boolean validation.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md` — surface reconcile for both code paths (Story 18.1).

**Review:** 0 patch / defer / intent_gap items. Bugbot reported no bugs.

**Follow-up review recommended:** false

**Verification:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — exit 0 (2440 passed).
- `pixi run -e pyforge-guild platform-ci-local -- --test` — exit 0 (leak_guard tests: 10 passed, 1 skipped live).
- `python scripts/spec_surface_reconcile.py` — exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — ok (no `--write-baseline` in this run).
- `pixi run -e pyforge-guild python scripts/flag_gate_check.py --spec …/spec-18-1-….md` — pass.
- AC6 mutations: org-in-global-terms → AC1 failed; drop Rule O whole-file → AC2 failed; drop empty-term refusal → AC5 failed; files restored, `git diff HEAD --stat` empty for both code files after restore.

**Residual risks:** AC8 live guard against operator config remains for orchestrator before merge. Whole-tree scan cost unchanged order-of-magnitude per spec.
