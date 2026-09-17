---
title: "Story 46.9: pipeline-truth's installed stage reads the applied core, and wired is a declared per-class predicate"
type: story
created: 2026-09-07
baseline_revision: 317228f3a3
status: done
review_loop_iteration: 1
followup_review_recommended: false
context: pyforge-steward
warnings: []
deferred:
  - summary: "_skills_census() now runs unconditionally at the top of _module_census_hit, a wasted iterdir() for bmad-module-skill-forge (which could previously short-circuit via wire_bmad_dirs alone)"
    evidence: "Edge Case Hunter finding #3; negligible cost, no behavioral effect"
    location: "src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py::_module_census_hit"
    severity: low
  - summary: "Manticore's wired probe (studio root + _bmad/ + mc-* census) is written against best-available evidence but not empirically verified against a real, completed studio install, since Story 46.6 is separately blocked (interactive installer, awaiting operator --tools decision)"
    evidence: "Spec's own Boundaries & Constraints, re-confirmed sound by Intent Alignment review; this story's own manticore tests correctly assert unwired against the real, empty studio root"
    location: "src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py::probe_wired (INSTALL_CLASS_STUDIO_MODULE branch)"
    severity: low
---

# Story 46.9: pipeline-truth's installed stage reads the applied core, and `wired` is a declared per-class predicate

<intent-contract>

## Intent

Two independent, mechanically-verified bugs in `steward suite pipeline-truth`
get fixed:

1. **The `installed` stage for the installer-tree class (`bmad-method`) reads
   the wrong source.** It currently calls the generic
   `read_installed_version` (a `.pixi/envs/*/conda-meta/` scan) for EVERY
   package uniformly — which for `bmad-method` answers "what version is
   pixi-pinned," not "what version `_bmad/` actually runs." Verified live:
   this repo's own `_bmad/_config/manifest.yaml` (`installation.version:
   6.12.0`) happens to agree with the pinned env today, but the exact
   divergent shape from 2026-09-05 (env bumped to 6.12.0 while `_bmad/` was
   still 6.11.0 — a real, already-corrected incident) would have silently
   reported a false green. The fix reads the APPLIED core version from the
   manifest first, falls back to the conda-meta read only when the manifest
   is absent, and names a drift when both are present and disagree.
2. **The `wired` probe's per-class predicates don't all observe the
   provisioning path the register actually names.** Verified live, reading
   `probe_wired` and every `SuitePackageDef` directly: `bmad-labs-skills`
   (plugin-path class) only ever checks whether the playbook DOCUMENTS the
   plugin path — it never looks at `.claude/skills` at all, so Story 46.5's
   real four-skill provisioning is invisible to it (register row 10 stuck at
   `documented` forever). `bmad-builder`'s prefix-based census
   (`wire_skill_prefixes`) covers only 3 of its actual 5 provisioned
   directories (`bmad-workflow-builder`/`bmad-eval-runner` are entirely
   absent from the current prefix list) — an incomplete signal, not a wrong
   one today, but not "the five dirs" the register promises either.
   `bmad-manticore` falls through to the generic module-census bottom
   branch, which checks THIS REPO's `.claude/skills/mc-*` — a signal AD-3
   (2026-09-06) explicitly retired ("studio-only tooling is never
   provisioned into the repo tree"); the correct signal is the studio
   declaration + the studio's OWN `mc-*` census, entirely outside this
   repo. `bmad-method-test-architecture-enterprise` / `bmad-creative-
   intelligence-suite` / `bmad-utility-skills` (the three genuinely AD-9-
   migrated module-class members) use the same imprecise prefix/dir census
   instead of the AD-9 roster (`_bmad/custom/config.toml [modules.<name>]`)
   that `--list-modules` and provision.py's own post-success gate already
   treat as the single source of truth.

Once both are fixed, the register's § 1 "Wired" column is regenerated from a
live `pipeline-truth --json` run and `install-matrix.md`'s "installed-stage
caveat" (documenting bug #1 as a known limitation) is retired.

## Boundaries & Constraints

- **`doctor`'s own `bmad-method-version-drift` check is the loud, gating
  signal and is not duplicated.** Verified by reading
  `pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py::_gather`
  directly: it already reads the SAME `_bmad/_config/manifest.yaml`
  `installation.version` and compares it against `pixi.toml`'s declared
  floor, raising a WARN `Finding` when installed is behind. This story's fix
  is a DIFFERENT comparison (manifest/applied vs. conda-meta/env — "is what
  actually runs the same as what's pinned," not "is what's applied at least
  the declared floor") for a DIFFERENT consumer (pipeline-truth's own
  per-stage report table, not a Finding/alert). `pyforge.doctor` is never
  imported (suite.py's own existing module docstring: "without importing
  `pyforge.doctor`"); the manifest reader is a small, independent function
  in `suite.py`, not a cross-import of doctor's.
- **A judgment call on the two literally-separate AC clauses "bmb: the five
  dirs" vs. "module class: the AD-9 roster" — treated as two genuinely
  different mechanisms, not one restated twice.** `bmb` is NOT part of the
  AD-9 migration (`provision.py`'s own module docstring, Story 46.2:
  "`bmb` is untouched -- `merge-config.py` still writes `_bmad/config.yaml`
  itself"), so it has no `[modules.bmb]` roster entry to read — its fix is
  an EXPLICIT, COMPLETE five-name allowlist requiring ALL FIVE present
  (`bmad-bmb-setup`, `bmad-agent-builder`, `bmad-workflow-builder`,
  `bmad-module-builder`, `bmad-eval-runner`), directly observing the real
  provisioning artifact (Story 46.4's own copy target) rather than a proxy.
  `tea`/`cis`/`utility-skills` genuinely ARE recorded (in `_bmad/custom/
  config.toml [modules.<name>]`, or the legacy `_bmad/config.yaml` fallback
  for `cis`'s still-unmigrated entry — Story 46.2's own two-location read),
  and `provision.py`'s own post-success gate already refuses to report
  `ok=True` unless the roster entry AND the skills actually landed together
  — so trusting that roster for these three is not a weaker signal than a
  census, it is the SAME signal `--list-modules` already exposes, read once
  instead of re-derived by a second, divergent mechanism (AD-9's own "one
  roster, one pin path... every consumer reads" principle). Verified live:
  all three roster entries genuinely exist in this repo today
  (`grep -n "\[modules.tea\]" _bmad/custom/config.toml`, same for
  `utility-skills`; `grep -n "^cis:" _bmad/config.yaml` for the legacy
  entry) — the switch is a strict precision improvement, not a behavior
  change, for all three today.
- **"labs: the named skill dirs and no other"** — the "and no other" half is
  interpreted as already enforced by Story 46.5's own dedicated meta-test
  (`test_no_labs_skill_outside_the_consent_list_is_present`), not
  re-implemented a second time inside `probe_wired` (AD-1: one check, one
  place). This story's `probe_wired` fix for the plugin-path class checks
  ONLY that all four consented names are present (an ALL-of, not
  ANY-of/no-other, semantics) — reporting `wired` when they are, falling
  back to the EXISTING `documented`/`missing` behavior otherwise (never a
  regression for the pre-46.5 or a hypothetical partial-provision state).
- **Manticore's fix is a NEW, dedicated install class
  (`INSTALL_CLASS_STUDIO_MODULE`), not a variant of the generic "module"
  fallback**, matching the register's own distinct "module (`--custom-
  source`)" label (never the plain "module" the other four CAP-3 members
  use) — this also, as a side effect, correctly REMOVES manticore from ever
  being swept into the module-class AD-9-roster fix above (it was never
  supposed to be there per AD-3; today it happened to fall into the generic
  fallback branch only because no `install_class` had been declared for
  it). The new branch checks: does the studio root
  (`$PYFORGE_STUDIO_ROOT`, default `~/pyforge-studio`, expanded) exist as a
  directory; does it have its own `_bmad/` subdirectory (the applied-native-
  install marker); does its own `.claude/skills/` contain any `mc-`-
  prefixed directory. **Caveat, disclosed rather than hidden:** Story 46.6
  (the story that was supposed to prove the real on-disk shape the native
  install produces) HALTED blocked on 2026-09-07 — the native installer
  turned out to be interactive-only and never completed, so the studio root
  exists but is EMPTY (verified live: `~/pyforge-studio` has zero entries).
  This story's manticore probe is therefore written against the BEST
  AVAILABLE evidence (the register's own stated shape: `_bmad/` +
  `.claude/skills/mc-*`, matching every other install-class's own
  `.claude/skills/`-based convention) but is NOT yet empirically verified
  against a real, completed studio install — that verification is 46.6's
  own remaining job once it unblocks, and this story's spec says so
  explicitly rather than silently assuming correctness. Given the studio is
  genuinely empty today, the live-repo test for this class asserts
  `"unwired"` (the honest, currently-true answer), not a fabricated
  `"wired"` state.
- **`adoption-register.md`'s § 1 "Wired" column is regenerated for ALL 13
  rows from a real, live `steward suite pipeline-truth --json` run** (AD-6)
  — not hand-derived from reasoning about what SHOULD happen. Verified by
  reasoning through each row against the fix (documented per-row in Design
  Notes) that only row 10 (`bmad-labs-skills`, `documented` → `wired`) is
  expected to actually change; every other row's live value should match
  its current cell. The live run is the actual proof, not this reasoning —
  if any OTHER row also changes, that is recorded as a finding, not
  silently overwritten without comment.
- **`install-matrix.md`'s "installed-stage caveat" is retired** — located
  and removed as a discrete edit (its exact current text is read fresh
  before editing, never assumed).
- **Neither `provision.py` nor `.claude/skills/**` nor any live conda
  package is modified by this story.** This is a read-only-probe fix; the
  only NEW cross-module coupling is `suite.py` importing
  `module_install_states` from `.provision` (verified no circular import:
  `provision.py` imports nothing from `suite.py`) — a read of an existing,
  already-public function, never a new write path.
- **No new pixi task, no `_SUPPORTED_MODULES` change, no CLI flag change.**
  The Surface line names only `suite.py`, `tests/unit/test_suite*.py`, and
  `install-matrix.md`.

## I/O Matrix

| Input | Behavior |
|---|---|
| `_bmad/_config/manifest.yaml` present, `installation.version` agrees with conda-meta | `installed` stage value = the agreed version; no new drift |
| `_bmad/_config/manifest.yaml` present, `installation.version` DISAGREES with conda-meta (the 2026-09-05 shape, replayed via fixture) | `installed` stage value = the APPLIED (manifest) version; `detail` names both; `drifts` gains `core_applied_env_drift` |
| `_bmad/_config/manifest.yaml` absent | falls back to the conda-meta read unchanged (today's pre-fix behavior, for a non-`bmad-method` checkout state) |
| `probe_wired` for `bmad-labs-skills`, all four consented dirs present | `wired` (was: `documented`, even with all four present) |
| `probe_wired` for `bmad-labs-skills`, zero/partial consented dirs, playbook cites the plugin path | `documented` (unchanged) |
| `probe_wired` for `bmad-builder`, all five real dirs present | `wired` (unchanged result, now via the correct five-name census rather than an incomplete 3-of-5 prefix match) |
| `probe_wired` for `bmad-builder`, only 3 of 5 present (a hypothetical partial-provision state the OLD prefix check would have missed) | `unwired`/`missing` (a genuine behavior IMPROVEMENT — the old check would have falsely reported wired here) |
| `probe_wired` for `bmad-method-test-architecture-enterprise` / `bmad-creative-intelligence-suite` / `bmad-utility-skills`, roster entry present | `wired` (unchanged result today, now via `module_install_states`) |
| `probe_wired` for `bmad-manticore`, studio root absent or empty (today's real, live state) | `unwired` |
| `probe_wired` for `bmad-manticore`, studio root has `_bmad/` + `.claude/skills/mc-*` (hypothetical, once 46.6 unblocks) | `wired` |
| `steward suite pipeline-truth --json`, live run | Row 10 (`bmad-labs-skills`) live `wired` value = `wired`; every other row's live value matches its current register cell (or a finding is recorded if not) |
| `adoption-register.md` § 1 | Row 10's Wired cell: `documented` → `wired`; every other row confirmed unchanged or corrected with a named reason |
| `install-matrix.md` | installed-stage caveat text removed |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py`
  - `import os` (new) — for `os.environ.get(_PYFORGE_STUDIO_ROOT_ENV)`.
  - `from .provision import module_install_states` (new) — for the AD-9
    roster read.
  - New constants: `_BMAD_CORE_MANIFEST_RELATIVE_PATH = Path("_bmad/_config/manifest.yaml")`,
    `_PYFORGE_STUDIO_ROOT_ENV = "PYFORGE_STUDIO_ROOT"`,
    `_PYFORGE_STUDIO_ROOT_DEFAULT = "~/pyforge-studio"`,
    `INSTALL_CLASS_STUDIO_MODULE = "studio-module"` (new install-class
    constant, alongside the existing `INSTALL_CLASS_*` group).
  - New function `read_applied_core_version(repo: Path) -> str | None` —
    fail-open read of `_bmad/_config/manifest.yaml`'s
    `installation.version` (mirrors `read_recipe_version`'s own
    try/except/isinstance shape for consistency).
  - New function `_installer_tree_installed_stage(repo: Path, name: str, *, hooks: ProbeHooks) -> StageProbe`
    — applied-first, env-fallback, drift-detail-on-disagreement (exact
    logic in Design Notes).
  - `build_package_truth` — the `installed_stage` computation branches on
    `pkg.install_class == INSTALL_CLASS_INSTALLER_TREE`, calling the new
    helper; every other class's computation is byte-for-byte unchanged
    (`_stage_from_value(hooks.installed(repo, pkg.name))`).
  - `name_drifts` — new drift tag `core_applied_env_drift`, detected via a
    documented, stable `StageProbe.detail` prefix check (`"applied "` ...
    `" / env "`) rather than a new dataclass field (Design Notes explains
    why).
  - `SuitePackageDef` — two new opt-in fields: `wire_skill_names_all:
    tuple[str, ...] = ()` (ALL must be present, vs. the existing
    `wire_skill_names`'s ANY semantics) and `module_code: str | None = None`
    (the `provision.py` `_SUPPORTED_MODULES` key, for the AD-9-roster
    check).
  - `_module_census_hit` — gains one new check ahead of its existing
    dir/config-key/skill-name/prefix checks: if `pkg.wire_skill_names_all`
    is set, ALL of them must be present in the skills census (returns the
    hit detail only when the full set matches; otherwise this function's
    EXISTING fallback checks still run, so a package that sets BOTH
    `wire_skill_names_all` and something else is not silently short-
    circuited — though in practice only `bmad-builder` sets the new field
    among the current five, and it drops its now-superseded
    `wire_skill_prefixes` entirely, so there is no overlap to reason about
    today).
  - `probe_wired` — three changes: (1) the `INSTALL_CLASS_PLUGIN_PATH`
    branch (labs) checks `wire_skill_names_all` FIRST (via
    `_module_census_hit`) before falling back to
    `_plugin_path_documented`; (2) a new `INSTALL_CLASS_STUDIO_MODULE`
    branch (manticore) implementing the studio-root + `_bmad/` +
    `mc-*`-census check described above; (3) the bottom generic fallback
    branch, when `pkg.module_code` is set, calls
    `module_install_states(cwd=repo).get(pkg.module_code) == "installed"`
    instead of `_module_census_hit` — `bmb` (which sets
    `wire_skill_names_all` but NOT `module_code`) still falls through to
    the (now five-name-aware) `_module_census_hit` path unchanged.
  - `SUITE_PACKAGES` — per-entry changes:
    - `bmad-builder`: drop `wire_skill_prefixes`; add
      `wire_skill_names_all=("bmad-bmb-setup", "bmad-agent-builder",
      "bmad-workflow-builder", "bmad-module-builder", "bmad-eval-runner")`;
      keep `wire_bmad_config_keys=("bmb",)` (still an accurate auxiliary
      fact, no longer the deciding signal).
    - `bmad-method-test-architecture-enterprise`: add `module_code="tea"`;
      keep existing `wire_skill_prefixes`/`wire_skill_names` as harmless
      residue UNLESS `module_code` is set takes precedence in `probe_wired`
      (it does, per the Code Map change above) — no functional overlap.
    - `bmad-creative-intelligence-suite`: add `module_code="cis"`.
    - `bmad-utility-skills`: add `module_code="utility-skills"`.
    - `bmad-labs-skills`: add `wire_skill_names_all=("mcp-builder",
      "slides-generator", "multi-repo-git-ops", "release-please")`.
    - `bmad-manticore`: `install_class=INSTALL_CLASS_STUDIO_MODULE`.
- `src/shared/packages/pyforge-steward/tests/unit/test_suite_pipeline_truth.py`
  - New tests for `read_applied_core_version` and
    `_installer_tree_installed_stage`: manifest-only, conda-meta-fallback,
    agreement (no drift), disagreement (drift named, applied value wins),
    replaying the exact 2026-09-05 shape as a named fixture.
- `src/shared/packages/pyforge-steward/tests/unit/test_suite_wired_class_predicates.py`
  - New tests: labs wired when all four consented dirs present (does NOT
    break the two existing labs tests — verified both stay green
    unmodified); bmb wired only when all five present, unwired when one of
    the five is missing (the genuine behavior-improvement case the old
    prefix check would have missed); tea/cis/utility-skills wired via
    roster presence (a fixture `_bmad/custom/config.toml` / legacy
    `_bmad/config.yaml`), unwired when the roster entry is absent even if
    stray skill dirs exist (the new, stricter, correct-per-AD-9 behavior);
    manticore unwired when the studio root is absent/empty, wired when a
    fixture studio root has `_bmad/` + a `mc-`-prefixed dir.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md`
  - Row 10 Wired cell: `documented` → `wired` (the one row the live run is
    expected to actually change). Every other row verified against the live
    run; any further discrepancy corrected with a named reason.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-channel-product/install-matrix.md`
  - The installed-stage caveat text removed (exact location found fresh).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/.memlog.md`
  - One new `(event)` line.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`
  - `46-9-...: backlog` → `done`.

## Tasks & Acceptance

1. **`read_applied_core_version` + `_installer_tree_installed_stage`.**
   - AC: a fixture repo with only `_bmad/_config/manifest.yaml`
     (`installation.version: 6.11.0`) and no conda-meta → `installed` stage
     value `6.11.0`, `ok=True`, no drift.
   - AC: a fixture repo with `_bmad/_config/manifest.yaml` = `6.11.0` AND a
     conda-meta entry = `6.12.0` (the exact 2026-09-05 replay) → `installed`
     stage value `6.11.0` (applied wins), `detail` names both, `name_drifts`
     includes `core_applied_env_drift`.
   - AC: manifest absent, conda-meta = `6.12.0` → `installed` stage value
     `6.12.0` (unchanged fallback behavior), no new drift.
   - AC: this repo's OWN real state (both present, currently agreeing) →
     `installed` stage reports the agreed version, no drift — a live,
     non-fixture confirmation that today's fix is a no-op for the currently
     healthy state.
2. **`wired` fixes for labs, bmb, tea/cis/utility-skills, manticore** exactly
   as designed in Code Map, each proven by a dedicated new unit test AND
   (where the real repo state makes it possible) a live, non-fixture
   confirmation against THIS repo's actual `.claude/skills/`/`_bmad/`
   state.
   - AC (live, this repo): `probe_wired(repo, labs_pkg).value == "wired"`;
     `probe_wired(repo, bmb_pkg).value == "wired"`;
     `probe_wired(repo, tea_pkg).value == "wired"`;
     `probe_wired(repo, cis_pkg).value == "wired"`;
     `probe_wired(repo, utility_skills_pkg).value == "wired"`;
     `probe_wired(repo, manticore_pkg).value == "unwired"` (honest, given
     46.6's own real blocked state).
   - AC: the two pre-existing labs tests
     (`test_labs_skill_census_alone_is_not_wired`,
     `test_labs_plugin_path_documented_from_playbook`) still pass
     unmodified.
3. **Regenerate `adoption-register.md`'s § 1 Wired column from a live
   `steward suite pipeline-truth --json` run.**
   - AC: the live run's per-package `wired` values are read directly (not
     re-derived by hand) and compared row-by-row against the register's
     current cells; row 10 is updated to `wired`; any other discrepancy is
     named and corrected, not silently left or silently overwritten.
   - AC: `tests/meta/test_adoption_register.py::test_wired_column_agrees_with_live_pipeline_truth_for_every_row`
     (the pre-existing meta-test, unmodified) passes.
4. **Retire `install-matrix.md`'s installed-stage caveat.**
   - AC: the caveat text (located fresh, quoted exactly before removal) no
     longer appears; nothing else in the file changes.
5. **Memlog + ledger.**
   - AC: `.memlog.md` gains one `(event)` line; the ledger's `46-9-...` key
     reads `done`.

## Spec Change Log

- 2026-09-07: initial draft, written directly (no fork) after reading
  `epics.md`'s Story 46.9 text in full, `suite.py`'s `probe_wired`,
  `_module_census_hit`, `SuitePackageDef`, `SUITE_PACKAGES` (all 13
  entries), `build_package_truth`, `name_drifts`, `ProbeHooks`,
  `read_installed_version`; `pyforge-doctor`'s `bmad_method.py::_gather`
  (confirming the non-duplication boundary); `_bmad/_config/manifest.yaml`'s
  real content in this worktree; live verification of `_bmad/custom/
  config.toml`'s `[modules.tea]`/`[modules.utility-skills]` and
  `_bmad/config.yaml`'s legacy `cis:` entry; live verification of all five
  `bmad-builder` skill dirs present and zero `mc-*` dirs present; the
  existing `test_suite_wired_class_predicates.py`/
  `test_suite_pipeline_truth.py` test files (confirming no existing test's
  assumptions are broken by this fix); confirmed no circular import risk
  between `suite.py` and `.provision`.

## Review Triage Log

Four independent, context-free reviewer subagents ran in parallel against the
full diff (no vendored content this story). 4 distinct findings (Blind Hunter
and Edge Case Hunter independently found the SAME headline bug, empirically
reproduced by both, and are merged as one finding below) plus one additional
lint issue caught during my own pre-review verification pass, before the
reviewers ran. 1 high / 1 medium / 1 low / 1 not-a-story-finding (lint), 0
false.

1. **[Patched — HIGH] `_module_census_hit`'s `wire_skill_names_all` check
   was "checked first," not exclusive — a miss fell through to `bmad-
   builder`'s own auxiliary `wire_bmad_config_keys=("bmb",)` check, which
   independently reports a hit from the `bmb:` key alone, regardless of
   whether all five skill dirs actually landed.** (Blind Hunter finding #1
   and Edge Case Hunter finding #1, both empirically reproduced
   independently against a fixture mirroring this repo's own real
   `_bmad/config.yaml`, which genuinely carries the `bmb:` key today —
   live-relevant, not hypothetical.) A hypothetical partial-provision state
   (3 of 5 bmb skill dirs present) would have reported `wired` via the
   config-key fallback, directly contradicting this story's own AC ("a
   genuine behavior IMPROVEMENT" — the old prefix census would have missed
   this too, but the fix was supposed to close that gap, not leave a
   different door open to the same outcome). **Fix:** `wire_skill_names_all`,
   when declared on a `SuitePackageDef`, is now the SOLE, EXCLUSIVE signal
   — it returns immediately whether it hits or misses, never falling
   through to `wire_bmad_dirs`/`wire_bmad_config_keys`/`wire_skill_names`/
   `wire_skill_prefixes`. No other package declares `wire_skill_names_all`
   alongside a second `wire_*` field today, so this has no effect on any
   other row. Proved with a new regression test,
   `test_bmb_partial_dirs_stays_unwired_even_with_the_config_key_present`,
   reproducing the exact live shape (3 of 5 dirs + a real-shaped
   `_bmad/config.yaml` with the `bmb:` key) and asserting `unwired`. The
   pre-existing `test_bmb_unwired_when_only_three_of_five_present` was also
   tightened from `!= "wired"` to `== "unwired"` (Blind Hunter's own note
   that the original assertion was weaker than the AC's literal claim).
2. **[Patched — Medium] `PYFORGE_STUDIO_ROOT=""` (set but empty) silently
   resolved to the process's cwd instead of the documented default,
   reintroducing exactly the in-repo signal AD-3 retired.** (Edge Case
   Hunter finding #2, empirically reproduced.) `os.environ.get(key,
   default)` only falls back to `default` when the key is ABSENT, not
   when it is present-but-empty — a classic gotcha. **Fix:**
   `os.environ.get(key) or default` treats an empty string the same as
   unset. Proved with a new regression test,
   `test_manticore_studio_root_env_set_but_empty_falls_back_to_default_not_cwd`,
   made hermetic against the real machine's actual home directory by
   monkeypatching `HOME` to a fresh, controlled, empty `tmp_path`
   subdirectory (rather than depending on the ambient, currently-empty-but-
   not-a-test-concern real `~/pyforge-studio`), and asserting the probe
   does not read the cwd's own planted `_bmad/`/`mc-*` content.
3. **[Deferred — Low] `_skills_census()` now runs unconditionally at the
   top of `_module_census_hit`, a wasted `iterdir()` for
   `bmad-module-skill-forge` (which could previously short-circuit via
   `wire_bmad_dirs` alone before ever touching `.claude/skills`).** (Edge
   Case Hunter finding #3.) Negligible cost (one local directory listing);
   deferred as a pure micro-optimization with no behavioral effect, not
   worth the churn of restructuring the function's check order further in
   the same pass that just fixed a real correctness bug there.
4. **[Patched, found during my own pre-review verification, not by a
   reviewer] `UP037` ruff finding: quoted forward-reference type annotation
   (`hooks: "ProbeHooks"`) on the new `_installer_tree_installed_stage`
   function is unnecessary** — `suite.py` already has `from __future__
   import annotations` at the top, making every annotation lazy
   regardless of definition order or quoting. Ruff baseline-comparison
   (same file set, before vs. after this story's changes) showed 3
   pre-existing findings (1 `SIM102`, 2 `I001`, all unrelated to this
   story and left untouched) plus this 1 net-new finding from the story's
   own new code. Fixed by removing the quotes; ruff count returns to the
   pre-existing baseline of 3.

Intent Alignment and Verification Gap reviewers both reported no findings —
Verification Gap independently re-ran every task's AC live (including a
fresh `steward suite pipeline-truth --json` run and a manual re-derivation
of `read_applied_core_version`/`read_installed_version` agreement) and
Intent Alignment independently re-verified the doctor-non-duplication,
bmb-vs-module-class separation, the labs "no-other" scope boundary, the
manticore-unverified caveat, the "only row 10 changes" claim (tracing
cis/tea/utility-skills/bmb's live state to confirm neither old nor new
mechanism disagreed for any of them), and the necessity of the
`fresh_clone.py` deviation — all confirmed sound.

Post-patch verification: `pixi run -e pyforge-steward pyforge-steward-test`
→ **1180 passed** (1178 + 2 new regression tests for findings 1/2). Ruff
net-new-finding check (baseline vs. patched, same file set) returns to the
pre-existing baseline count of 3 after fixing finding 4.

## Design Notes

- **Exact `_installer_tree_installed_stage` logic**, spelled out because it
  is the load-bearing fix:
  ```python
  def _installer_tree_installed_stage(
      repo: Path, name: str, *, hooks: "ProbeHooks"
  ) -> StageProbe:
      applied = read_applied_core_version(repo)
      env = hooks.installed(repo, name)
      if applied is None:
          return _stage_from_value(env)
      if env is not None and applied != env:
          return StageProbe(
              value=applied, ok=True,
              detail=f"applied {applied} / env {env} -- core-applied-env-drift",
          )
      return StageProbe(value=applied, ok=True)
  ```
  `name_drifts` detects the drift via `pkg.installed.detail and
  "core-applied-env-drift" in pkg.installed.detail` — a documented, stable
  sentinel substring in an existing free-text field, chosen over adding a
  new `StageProbe` field because every other stage's `detail` is already
  free-text prose no other consumer parses structurally; adding a typed
  field for exactly one drift class would be the heavier, less consistent
  change.
- **Why `bmb` keeps `wire_bmad_config_keys=("bmb",)` after losing its
  deciding-signal status:** it remains a true, cheap-to-check auxiliary
  fact (the `merge-config.py` step DID write that key) that still
  contributes to `_module_census_hit`'s detail string when the five-name
  check also hits, at zero cost — removing it would lose diagnostic detail
  for no behavioral gain.
- **Why `tea`/`cis`/`utility-skills` keep their existing
  `wire_skill_prefixes`/`wire_skill_names` fields even though `probe_wired`
  no longer reads them (once `module_code` is set):** deleting dead fields
  from three `SuitePackageDef` entries is a larger, purely-cosmetic diff
  than this fix needs; `module_code`'s presence is what actually changes
  behavior, and leaving the old fields in place costs nothing at runtime
  (they are simply unread once the roster branch wins). A follow-up cleanup
  story can remove them later if their presence proves confusing in
  practice; this story does not manufacture that cleanup as a task.
- **Why manticore's probe is written against best-available evidence
  despite 46.6 being blocked:** the alternative — deferring 46.9 entirely
  until 46.6 unblocks — would leave the OLD, definitively-wrong
  in-repo-`.claude/skills/mc-*` census in place for however long that takes,
  which is strictly worse than a best-effort, explicitly-caveated new probe
  that reports the same honest `"unwired"` answer today's broken probe
  ALSO happens to report (since this repo genuinely has zero `mc-*` dirs
  either way) — the fix is directionally correct and behaviorally
  identical today, differing only in what it will correctly detect once
  46.6 actually lands a studio.

## Implementation Notes

- **A necessary deviation from the stated Surface line** (`suite.py`,
  `tests/unit/test_suite*.py`, `install-matrix.md`):
  `src/shared/packages/pyforge-steward/src/pyforge/steward/fresh_clone.py`'s
  own `_EXPECTED_WIRED["bmad-labs-skills"]` constant, and the corresponding
  assertion in `tests/unit/test_fresh_clone_class_path.py::
  test_live_checkout_proves_six_class_outcomes`, both independently
  hardcoded the exact same stale `"documented"` expectation this story's
  `probe_wired` fix corrects. Running the full `pyforge-steward-test` suite
  after the `suite.py` changes (this implementation's own boundary #9:
  "all tests must pass") turned these two up as genuinely red --
  `fresh_clone.py`'s `prove()` calls `probe_wired` directly against this
  repo's own live state, so once labs correctly reports `wired` (all four
  Story 46.5-consented skills are genuinely present), the hardcoded
  `"documented"` expectation there is exactly as stale as the one this
  story exists to fix in `adoption-register.md`. Left unfixed, this would
  either leave the suite red or require silently under-scoping "all tests
  must pass." Both were updated (`_EXPECTED_WIRED["bmad-labs-skills"] =
  "wired"`; the test assertion to match), one line each, with a comment
  citing this story. No other line in `fresh_clone.py` changed.
- **A second pre-existing test outside the three explicitly protected
  ones** also needed a one-line update for the same reason:
  `tests/unit/test_suite_wired_class_predicates.py::
  test_live_repo_names_six_and_template_is_n_a` asserted `probe.value !=
  "wired"` for all six non-module install classes against this repo's live
  state; `bmad-labs-skills` is now the one correct exception (Task 2's own
  AC). Carved out with an `elif` branch and a comment, rather than removing
  labs from the loop or weakening the assertion for the other five.
- **`adoption-register.md` row 1's Hazards cell** (`bmad-method`) still
  reads "installed-stage caveat: pipeline-truth reads conda-meta, not
  `_bmad/_config/manifest.yaml`" -- the Code Map names only
  `install-matrix.md`'s caveat for retirement, not this cell, so it was
  left untouched per the Surface-line boundary. This is now a stale
  cross-reference (the bug it names is fixed), noted here rather than
  silently edited outside the stated scope; a follow-up doc pass can
  retire it explicitly.
- **Live confirmation (Task 3, boundary #10):** a real, non-baseline
  `pixi run -e pyforge-steward pyforge steward suite pipeline-truth --json`
  run against this repo's own state (network-backed, not a fixture) was
  executed and read directly. Per-package `wired` values: `bmad-method`
  present, `bmad-loop` provisionable, `bmad-method-test-architecture-
  enterprise` wired, `bmad-builder` wired, `bmad-creative-intelligence-
  suite` wired, `bmad-module-skill-forge` present, `bmad-eval-quality`
  runnable, `bmad-utility-skills` wired, `bmad-labs-skills` wired,
  `bmad-module-template` n/a, `bmad-manticore` unwired, `bmad-dashboard`
  runnable, `mybmad-dashboard` runnable. Only `bmad-labs-skills` changed
  category versus the register's pre-story cells (`documented` -> `wired`);
  every other row already agreed -- confirming the Boundaries &
  Constraints' own row-by-row prediction exactly, with no undisclosed
  discrepancy. `bmad-method`'s `installed` stage reported `6.12.0` with no
  `core_applied_env_drift` (manifest and conda-meta currently agree),
  confirming Task 1's AC that the fix is a live no-op for today's healthy
  state.

## Auto Run Result

Status: done
Blocking condition: none

Implementation subagent delivered all 5 tasks; independent 4-reviewer pass
found 4 findings (1 high, 1 medium, 1 low, plus 1 lint-only issue caught in
my own pre-review pass), 3 patched with regression tests, 1 deferred (low
severity, plus the pre-existing manticore-unverified caveat re-recorded in
frontmatter `deferred`), 0 false. Final state:

- `installed` stage for `bmad-method` reads `_bmad/_config/manifest.yaml`'s
  applied core version first, falling back to conda-meta only when the
  manifest is absent, naming `core_applied_env_drift` on disagreement.
- `wired` probe corrected for labs (all four consented dirs), bmb (all
  five dirs, now genuinely exclusive after the HIGH-severity fix), tea/
  cis/utility-skills (AD-9 roster read), and manticore (a new dedicated
  `INSTALL_CLASS_STUDIO_MODULE`, honestly reporting `unwired` against the
  real, empty studio).
- `adoption-register.md` row 10 flipped `documented` -> `wired`; every
  other row confirmed unchanged by a live `pipeline-truth --json` run.
- `install-matrix.md`'s installed-stage caveat removed.
- `fresh_clone.py` + its test corrected for the same reason (a necessary,
  disclosed out-of-scope deviation — labs now genuinely reports `wired`).
- Final suite: `pixi run -e pyforge-steward pyforge-steward-test` →
  **1180 passed**. Ruff net-new-finding count: 0 (returned to the
  pre-existing baseline of 3 after fixing the one lint issue this story's
  own new code introduced).
