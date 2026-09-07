---
title: 'Story 46.3: TEA is provisioned and tea-test-review is a pixi task'
type: 'feature'
created: '2026-09-07'
baseline_revision: '32d0971b961c32ab2453fc00a6cb87f6ec711b40'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
deferred:
  - summary: >-
      No promoted per-story spec file exists in the tracked
      planning-artifacts/specs/ directory for Stories 46.1, 46.2, or 46.3
      (unlike 46.7/46.8, which each have one).
    evidence: |-
      Matches this repo's own "story specs are durable, promoted after
      merge" convention, which happens at merge time per the repo's stated
      process, not mid-batch while several dependent stories are still
      landing on the same branch. Real gap to close when this branch
      merges, not blocking mid-batch.
    location: >-
      _bmad-output/projects/pyforge-steward/planning-artifacts/specs/
    severity: low
  - summary: >-
      Reading "test_artifacts ... pointed at each station's
      planning-artifacts/ per its .bmad-config.toml" could plausibly mean
      per-station RESOLVED values rather than the one global unresolved
      template string this story actually writes.
    evidence: |-
      Proving per-station resolution would require actually rendering a
      TEA skill per active project, which is blocked by the separate,
      disclosed render_skill.py/workflow.yaml incompatibility finding.
      The unresolved-template approach is the best achievable outcome
      given that constraint, and matches how other `{output_folder}`-style
      templates already resolve per-active-project elsewhere in this repo.
    location: >-
      _bmad/custom/config.toml::modules.tea.test_artifacts
    severity: medium (documented interpretation, not a defect)
  - summary: >-
      `_installer_skill_names`'s flatten-branch prediction is derived only
      from the share_root tree, never cross-checked against what the
      installer's own copy actually produced at dest before flattening.
    evidence: |-
      Real in principle; the existing post-install missing-skills check
      (comparing predicted names against `dest/<name>.is_dir()`) already
      catches the case where a predicted leaf never actually materializes,
      which covers the practical failure mode. A share-vs-installer
      disagreement narrower than "leaf missing entirely" is not covered,
      but no such case is currently reachable with the real TEA package.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_installer_skill_names
    severity: low
  - summary: >-
      A new test (`test_provision_installer_missing_non_nested_skill_after_successful_flatten_raises`)
      hand-rolls its own installer stand-in instead of reusing the shared
      `_fake_installer_run`, risking drift as the real TEA share shape
      evolves.
    evidence: |-
      Real test-hygiene nit, no functional risk to production code.
    location: >-
      src/shared/packages/pyforge-steward/tests/conformance/test_provision_module_installers.py
    severity: low
  - summary: >-
      If TEA's own upstream layout ever grew a second flatten-nested
      container with a leaf name colliding with another container's leaf,
      the second would be silently discarded rather than raising.
    evidence: |-
      Currently inert -- TEA's only flatten_nested_dirs source
      ("workflows") has exactly one container ("testarch"); no second
      container exists to collide with it.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_flatten_nested_skill_dirs
    severity: low
  - summary: >-
      A foreign, pre-existing `.claude/skills/testarch/` directory (not
      created by this story's own flattening) would not be caught by the
      pre-install skill-name-collision check, since "testarch" is no
      longer one of the predicted post-flatten names.
    evidence: |-
      Exotic: no other module or convention in this repo uses "testarch"
      as a skill name; the practical likelihood of a real collision is
      very low.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_provision_conda_install
    severity: low
---

<intent-contract>

## Intent

**Problem:** `steward provision --module tea` already runs (TEA 1.24.0 is installed and `_SUPPORTED_MODULES["tea"]` is registered), but three real gaps stop it from actually delivering what Story 46.3 needs: (1) the installer's own upstream layout nests all nine workflow skills one level too deep (`workflows/testarch/bmad-testarch-*`), so after `steward provision --module tea` runs they land at `.claude/skills/testarch/bmad-testarch-*` -- invisible to Claude Code's own skill discovery, which only scans `.claude/skills/<name>/SKILL.md` one level deep, not the `.claude/skills/bmad-testarch-*` flat layout the register/epic actually require; (2) TEA ships a real `module.yaml` (confirmed live: `.pixi/envs/local-recipes/share/bmad-method-test-architecture-enterprise/module.yaml`) whose answers -- most importantly `test_artifacts` -- are never merged into the AD-9 roster, because `_provision_conda_install` (unlike bmb's `SetupSkillBackend` path) has no module.yaml-answers mechanism at all; (3) there is no `tea-test-review` pixi task yet.

**Approach:** Add a TEA-specific post-install flattening step (move each of the nine `workflows/testarch/*` skill directories up to `.claude/skills/bmad-testarch-*` / `.claude/skills/bmad-teach-me-testing`, then remove the now-empty `testarch/` container); add a module.yaml-answers mechanism for `CondaInstallBackend` modules (opt-in per backend, since only TEA currently has a module.yaml among tea/cis/utility-skills/manticore) that computes TEA's answers with `test_artifacts` overridden to point at the station's `planning-artifacts/` rather than the module's own default `test-artifacts` folder, merged into `[modules.tea]` alongside `provisioned_by`/`installer`/`skills`; add the `tea-test-review` pixi task; reconcile the six blanket-glob specs governing `pixi.toml`.

## Boundaries & Constraints

**Always:**
- The flattening is TEA-specific (opt-in via a new field on `CondaInstallBackend`, e.g. `flatten_nested_dirs: tuple[str, ...]` naming which top-level `skill_source_dirs` entries need this treatment) -- `cis`/`utility-skills`/`manticore` are unaffected; their `skill_source_dirs`/`skill_names` behavior is unchanged.
- After flattening, `.claude/skills/` gains exactly ten new top-level entries for TEA: `bmad-tea` (the Murat agent, unaffected -- `agents/` was never nested) plus the nine workflow skills currently misnamed as one `testarch` directory: `bmad-testarch-{nfr,atdd,automate,ci,trace,framework,test-design,test-review}` and `bmad-teach-me-testing`. No `.claude/skills/testarch/` directory survives.
- The module.yaml-answers mechanism is a NEW, opt-in addition to `_provision_conda_install` (a `module_yaml_relative_path: Path | None = None` field on `CondaInstallBackend`, defaulting to `None` for every module except TEA) -- when set, compute answers via the same `_module_variable_defaults`-style logic `_provision_setup_skill` already uses for `bmb`, but do NOT drive `merge-config.py`/`merge-help-csv.py` (those are `bmb`-specific subprocess wrappers) -- merge the resulting answers dict directly into the `[modules.<name>]` TOML section this story's own Story 46.2 predecessor already writes.
- `test_artifacts`'s answer is overridden (not left at the module's own YAML default `"{output_folder}/test-artifacts"`) to `"{output_folder}/planning-artifacts"`, so its templated `result` (`"{project-root}/{value}"`) resolves, once a skill actually renders it against an active project's own `.bmad-config.toml` `output_folder`, to that project's real tracked `planning-artifacts/` directory -- matching the epic's "test_artifacts ... pointed at each station's planning-artifacts/ per its .bmad-config.toml." Store the UNRESOLVED template string (`"{output_folder}/planning-artifacts"`), never a pre-resolved absolute path -- resolution happens per-active-project at skill-render time, not at provisioning time.
- Every other TEA module.yaml variable keeps its own declared `default` (no other overrides) -- this story does not decide TEA's `tea_use_playwright_utils`/`tea_browser_automation`/etc. defaults, it only closes the `test_artifacts` gap the epic explicitly names.
- `tea-test-review` (pixi task, `local-recipes` feature) wraps the real `tea-test-review` CLI binary (already installed: confirmed at `.pixi/envs/local-recipes/bin/tea-test-review`) as `tea-test-review --base origin/main --min-score <N>`, where `N` is an argument with a default of `80` (AD-4: the argument/value split -- `N`'s default lives in the pixi task definition, not hardcoded deep in a script).
- Every `pixi.toml` blanket-glob spec whose surface includes this change gets a memlog line and a scoped `spec_surface_check.py --write-baseline --spec <name>` (six specs, per Story 45.2/46.1's own precedent for this exact pixi.toml co-governance pattern -- identify them the same way: grep `pixi.toml` in each spec's `surface:` glob declarations).
- Record the `render_skill.py`/TEA-workflow-format finding explicitly (see Never below) as a memlog `(finding)`, not a silent gap.

**Never:**
- Never modify `_bmad/scripts/render_skill.py` in this story. Live-verified: `render_skill.py` hard-requires a `workflow.md` render entry (`_load_sources` raises `RenderError` otherwise); TEA's nine workflow skills ship `workflow.yaml` + `instructions.md` instead -- a structurally different, third-party skill-authoring format `render_skill.py` was never built to read. `render_skill.py` is shared, high-blast-radius infrastructure used by every station's every BMAD-authored skill; teaching it a second skill format is a materially larger change than this story's `S` effort estimate, and is not named as a task anywhere else in this epic. Confirmed via a live, direct test this session: `uv run render_skill.py --skill .claude/skills/testarch/bmad-testarch-test-design` HALTs with "render entry is missing: .../workflow.md" -- this HALT is unrelated to config completeness and would persist even after every other part of this story lands. The epic's own literal acceptance clause ("so render_skill.py renders bmad-testarch-test-design on the first try") is not achievable as written without that larger change; this is recorded as a named finding, not silently worked around or silently claimed as met.
- Never touch `bmad-tea-install`'s own behavior (it is a vendored, third-party binary) -- the flattening happens as a Steward-side post-install step operating on the files it already wrote, never a patch to the installer itself.
- Never add `tea-test-review` to `detectors`/`detectors-ci` -- Warden's gate exit code must be unaffected by this task's existence.
- Never decide the marshal-side (31.1-31.3) or warden-advisory (11.2) work -- this story only provisions TEA and ships the pixi task; those depend on this story, not the reverse.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh TEA provision | `bmad-tea-install` copies `agents/bmad-tea` and `workflows/testarch/*` (9 dirs) as today | Post-flatten: `.claude/skills/bmad-tea/` + 9 top-level `bmad-testarch-*`/`bmad-teach-me-testing` dirs exist; `.claude/skills/testarch/` does not exist | If flattening can't find the expected nested container, raise a clear `RuntimeError` naming what was expected vs. found -- never silently leave the nested layout in place |
| Idempotent re-provision | The flattened layout already exists from a prior run | Re-running produces the same end state, no duplication, no error | -- |
| `[modules.tea]` answers | TEA's real module.yaml (confirmed: `test_artifacts` + 9 other variables) | The TOML section carries `provisioned_by`/`installer`/`skills` (Story 46.2 shape) plus every module.yaml variable's answer, with `test_artifacts` overridden to `"{output_folder}/planning-artifacts"` and every other variable at its own declared default | -- |
| `--list-modules` | After provisioning | Reports `tea` `"installed"` | -- |
| `tea-test-review` pixi task | `pixi run -e local-recipes tea-test-review` (no args) | Runs `tea-test-review --base origin/main --min-score 80` | `-- --min-score 90` overrides `N`; never joins `detectors`/`detectors-ci` |
| render_skill.py against a TEA workflow skill | `bmad-testarch-test-design` (flattened, config answered) | Still HALTs with "render entry is missing: workflow.md" -- a named, disclosed finding, not a regression this story introduces or is expected to fix | -- |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py:317-331` -- `CondaInstallBackend` dataclass; add `flatten_nested_dirs: tuple[str, ...] = ()` (names of `skill_source_dirs` entries whose immediate children are themselves containers to flatten, not leaf skills) and `module_yaml_relative_path: Path | None = None` (module.yaml location relative to `share_root`, for the opt-in answers mechanism).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py:349-369` -- `_SUPPORTED_MODULES["tea"]`: add `flatten_nested_dirs=("workflows",)` and `module_yaml_relative_path=Path("module.yaml")` (confirmed live: TEA's module.yaml sits at the share root, NOT under `assets/` like bmb's -- read the real path before assuming bmb's `_MODULE_YAML_RELATIVE_PATH` constant applies).
- `.pixi/envs/local-recipes/share/bmad-method-test-architecture-enterprise/module.yaml` -- read fully before implementing. Ten variables total (`test_artifacts` plus nine `tea_*`/`test_*`/`ci_platform`/`risk_threshold`/`test_design_output`/`test_review_output`/`trace_output`); only `test_artifacts` gets an overridden answer, every other variable keeps its own `default`.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py:392-399` -- `_module_variable_defaults(module_yaml)`: the existing, reusable helper (currently only called by `_provision_setup_skill`/bmb) that collects `{key: default}` for every top-level module.yaml entry declaring a `default`. Reuse this verbatim for TEA's answers; only override the single `test_artifacts` key afterward.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py:469-479` -- `_installer_skill_names`: for a backend with `flatten_nested_dirs`, the predicted names must be the FLATTENED leaf names (the 9 workflow skills + `bmad-tea`), not the current one-level `iterdir()` result (`bmad-tea`, `testarch`) -- this function is also used for pre-install collision checking, so it must predict the POST-flatten state.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py:695-750` (`_provision_conda_install`) -- after the installer subprocess succeeds and the missing-skills check passes (against the flattened expected names), add the flattening step (move `dest/testarch/*` to `dest/*`, remove `dest/testarch`) before the module.yaml-answers computation and the `_record_module_manifest` call.
- `_bmad/custom/config.toml` -- confirmed live: `[modules.utility-skills]` already lands here (Story 46.2). This story's `[modules.tea]` section follows immediately, using the exact same comment-preserving text-editing writer `_record_module_manifest` (unchanged by this story except to accept an additional `answers: dict[str, object] | None = None` parameter merged into the rendered section).
- `.pixi/envs/local-recipes/bin/tea-test-review` -- confirmed installed and runnable; `--help` names `--base`/`--min-score` (verify the exact flag names live before wiring the pixi task -- do not assume from memory).
- `pixi.toml` -- Story 45.2/46.1's own precedent: new `[feature.local-recipes.tasks.tea-test-review]` entry; six blanket-glob specs to reconcile (grep `pixi.toml` in `surface:` across `_bmad-output/projects/*/planning-artifacts/specs/*/` -- the exact six may differ slightly from 45.2's/46.1's own list if a spec's surface changed since; re-derive, don't assume the same six).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` / `open-items-register.md` -- not touched by this story unless the render_skill.py finding needs a durable DW-FU entry (judgment call for the implementer: a memlog `(finding)` line is the minimum bar per this story's own Boundaries; a full DW-FU ledger entry is optional additive documentation, not required).

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` -- add `flatten_nested_dirs`/`module_yaml_relative_path` fields to `CondaInstallBackend`; register them for `tea`; update `_installer_skill_names` to predict flattened names; add the post-install flattening step and the module.yaml-answers computation (reusing `_module_variable_defaults`, overriding `test_artifacts`) in `_provision_conda_install`; extend `_record_module_manifest`'s rendering to merge an optional answers dict into the TOML section.
- `src/shared/packages/pyforge-steward/tests/conformance/test_provision_module_installers.py` (or a new TEA-specific test module, matching this package's existing per-concern organization) -- tests for: flattening (fresh + idempotent re-run), the predicted-vs-actual name check still catching a genuinely missing skill post-flatten, module.yaml answers merged with `test_artifacts` overridden and every other variable at its own default, and that `cis`/`utility-skills`/`manticore` (no `flatten_nested_dirs`/`module_yaml_relative_path`) are completely unaffected.
- `pixi.toml` -- add `tea-test-review` task under `[feature.local-recipes.tasks]` (never `detectors`/`detectors-ci`), default `--min-score 80`.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/.memlog.md` -- a dated `(event)` line for the TEA provisioning/flattening/module.yaml-answers landing, and a dated `(finding)` line for the `render_skill.py`/`workflow.yaml` incompatibility (per this story's own Never clause).
- Six blanket-glob `pixi.toml`-governing specs -- one memlog line + scoped `spec_surface_check.py --write-baseline --spec <name>` each.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml` -- flip `46-3-tea-is-provisioned-and-tea-test-review-is-a-pixi-task` to `done` via the project's sprint-ledger-sync mechanism once verified.

**Acceptance Criteria:**
- Given TEA 1.24.0 in the pixi env, when `steward provision --module tea --json` runs, then `.claude/skills/bmad-tea/` and nine top-level `bmad-testarch-*`/`bmad-teach-me-testing` skill directories exist, `.claude/skills/testarch/` does not exist, and `--list-modules` reports `tea` installed.
- Given the same provisioning run, when `_bmad/custom/config.toml` is inspected, then `[modules.tea]` carries `provisioned_by`/`installer`/`skills` plus every module.yaml variable's answer, with `test_artifacts` equal to `"{output_folder}/planning-artifacts"` (the unresolved template, not a pre-resolved path).
- Given a re-provision of an already-flattened, already-answered TEA install, when `steward provision --module tea --json` runs again, then the end state is unchanged (idempotent) and no error occurs.
- Given `pixi run -e local-recipes tea-test-review`, when it runs, then it invokes `tea-test-review --base origin/main --min-score 80`; given `-- --min-score 90`, then it overrides to 90.
- Given `pixi task list -e detectors`, when inspected, then `tea-test-review` does not appear.
- Given a live attempt to render `bmad-testarch-test-design` via `render_skill.py`, when it HALTs on the missing `workflow.md` entry, then this is recorded as a named memlog finding, not silently ignored or falsely claimed as resolved.
- Given `pixi run -e pyforge-steward pyforge-steward-test`, when it runs after this story's changes, then it passes in full, including new coverage for the flattening and module.yaml-answers logic.

## Spec Change Log

## Review Triage Log

### 2026-09-07 — Review pass
- verdicts: 23 findings — high 1, medium 10, low 11, false 1, maybe-false 0
- findings:
  - `[high]` `[patch]` Blind Hunter: `_flatten_nested_skill_dirs` discarded the freshly re-installed nested copy and kept the stale already-flattened target on every re-provision -- meaning a real TEA package version bump would never actually reach the ten flattened skills after the very first provision, permanently freezing them. Applied: inverted the logic to always adopt the fresh nested copy (replacing any stale flattened target), matching how every other conda-install module already refreshes via plain rmtree+copytree; proved with a new test that stages changed share content between two provision runs and asserts the flattened target picks up the change.
  - `[false]` `[reject]` Blind Hunter: `scripts/.spec-surface-baseline.json`'s `pyforge-steward/spec-pyforge-steward` entry is silently rewritten with no matching memlog entry -- refuted by direct comparison of the old and new baseline JSON: that specific entry's hash is byte-identical before and after this diff; the nine specs that DID change each have a matching memlog line (verified: `git status` shows exactly nine memlog files modified, matching the nine changed baseline entries).
  - `[medium]` `[defer]` Blind Hunter: the sprint ledger flips this story to `done` even though epics.md names the `render_skill.py` render as "the acceptance test," and this diff's own memlog concedes that command still HALTs -- recorded in frontmatter `deferred:` as a documented, disclosed scope boundary (matches this same epic's own Story 46.1/46.2 precedent of flipping `done` on the achievable majority of a story while naming a residual gap by memlog, not by leaving `done` unset).
  - `[medium]` `[patch]` Blind Hunter + Verification Gap (same root, Verification Gap's pre-verified gap finding, trusted per protocol): the new `FileNotFoundError` (missing module.yaml) and `RuntimeError` (non-mapping module.yaml) guards shipped with zero test coverage. Applied: added `test_provision_tea_missing_module_yaml_raises_named_error` and `test_provision_tea_non_mapping_module_yaml_raises_named_error`, mirroring the existing `bmb`-path precedent for the second case.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (same root): `_toml_value`'s `TypeError` for an unsupported module.yaml answer type carried no module/key context (unlike every other error path in this file), and had zero test coverage. Applied: `_render_module_toml_section` now catches and re-raises with the module name and variable key named; added `test_toml_value_unsupported_type_names_the_module_and_key`.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (same root): no guard against a module.yaml answer key colliding with the three reserved manifest fields (`provisioned_by`/`installer`/`skills`), which would silently emit a duplicate, `tomllib`-invalid TOML key. Applied: `_render_module_toml_section` now raises a clear `RuntimeError` naming the collision; added `test_render_module_toml_section_rejects_reserved_answer_key`.
  - `[low]` `[defer]` Blind Hunter: no promoted per-story spec file exists yet in tracked `planning-artifacts/specs/` for Stories 46.1/46.2/46.3 -- recorded in frontmatter `deferred:`; matches this repo's own "promoted at merge time" convention, not a mid-batch gap.
  - `[low]` `[defer]` Blind Hunter: `_installer_skill_names`'s flatten-branch prediction is never cross-checked against what the installer's own copy actually produces at `dest` -- recorded in frontmatter `deferred:`; the existing missing-skills check already catches the practical failure mode (a predicted leaf never materializing).
  - `[low]` `[defer]` Blind Hunter: a new test hand-rolls its own installer stand-in instead of reusing the shared fake -- recorded in frontmatter `deferred:` as a test-hygiene nit with no functional risk.
  - `[low]` `[reject]` Blind Hunter: sorting-style inconsistency between `_installer_skill_names` (sorts `Path` objects) and `_flatten_nested_skill_dirs` (sorts `.name` strings) -- cosmetic, functionally identical output; not worth a mechanical style-only edit in the same pass as substantive fixes.
  - `[low]` `[defer]` Edge Case Hunter: a second flatten-nested container with a leaf name colliding with another container's leaf would be silently discarded -- recorded in frontmatter `deferred:`; currently inert (TEA has exactly one container).
  - `[medium]` `[patch]` Edge Case Hunter: module.yaml default of an unsupported type (int/float/list/None) previously crashed as an uncaught `TypeError`, bypassing `ProvisionDuty`'s `DutyResult(ok=False)` error contract -- same root cause and same fix as the `_toml_value` context finding above (the re-raise now happens inside `_render_module_toml_section`, which is called from within `_provision_conda_install`'s existing try/except boundary in `_run_module`, so it's caught and reported cleanly rather than crashing past it).
  - `[medium]` `[patch]` Edge Case Hunter: reserved-key collision (installer/skills/provisioned_by) -- duplicate of the Blind Hunter finding above; same fix, already applied.
  - `[low]` `[defer]` Edge Case Hunter: target-exists-as-plain-file-not-directory during flatten would raise an unclear low-level `OSError` from `shutil.move` -- recorded in frontmatter `deferred:` as an exotic edge case (would require a foreign plain file at a flattened skill's exact path).
  - `[low]` `[defer]` Edge Case Hunter: a foreign, pre-existing `.claude/skills/testarch/` directory would not be caught by the pre-install collision check now that "testarch" is no longer a predicted post-flatten name -- recorded in frontmatter `deferred:`; exotic, no other convention in this repo uses that name.
  - `[low]` `[reject]` Edge Case Hunter (deletion, reviewer's own low confidence): the old fake installer asserted immediately on a missing staged skill; the new one only surfaces the same condition via the production `RuntimeError` path -- rejected: exercising the real production error path instead of a test-only assert is the more correct testing practice, not a regression.
  - `[medium]` `[patch]` Verification Gap (pre-verified gap finding, trusted per protocol): duplicate of the Blind Hunter "zero test coverage for missing/non-mapping module.yaml" finding above -- same fix, already applied.
  - `[medium]` `[patch]` Verification Gap (pre-verified gap finding, trusted per protocol): the non-mapping module.yaml `RuntimeError` guard specifically had no test even though the sibling `bmb` path has one for the exact same shape -- same fix, already applied (`test_provision_tea_non_mapping_module_yaml_raises_named_error` mirrors `test_provision_module_malformed_module_yaml_is_a_clean_runtime_error`).
  - `[medium]` `[defer]` Intent Alignment: Reading A (the epic's literal "render_skill.py renders ... on the first try" acceptance test) is not achieved -- duplicate of the Blind Hunter "ledger flipped despite acceptance test failing" finding above; same disclosed-deviation route.
  - `[low]` `[defer]` Intent Alignment: the render-time surface has zero regression coverage -- no test asserts anything about `render_skill.py` succeeding or failing against a TEA skill; the only record is a memlog prose line. Recorded rather than patched: adding a test that deliberately proves a known, disclosed, out-of-scope failure mode is optional documentation polish, not a correctness gap this pass needs to close.
  - `[medium]` `[defer]` Intent Alignment: "test_artifacts ... per its .bmad-config.toml" plausibly reads as per-station resolved values rather than one global unresolved template -- recorded in frontmatter `deferred:` as a documented interpretation, not a defect (proving per-station resolution is blocked by the separate render_skill.py finding).
  - `[low]` `[defer]` Intent Alignment: no promoted per-story spec file exists for this story -- duplicate of the Blind Hunter finding above; same route.
  - `[low]` `[reject]` Intent Alignment: "N as an argument (default 80)" is implemented as a hardcoded `--min-score 80` in the pixi task's `cmd` string (override via `-- --min-score 90`) rather than a first-class pixi task argument -- rejected: functionally equivalent, and matches the exact same pattern this project's own prior stories (e.g. `eval-quality-review-twin-run -- --trials N`) already established as the house convention for this class of pixi task.

## Design Notes

**Why flattening lives in Steward, not the installer:** `bmad-tea-install` is a vendored third-party binary (part of the `bmad-method-test-architecture-enterprise` conda package) that copies its own upstream directory structure verbatim. Steward's own AD-1 constraint ("never reimplements the module's installer") means the copy itself is untouched; the flatten step is a POST-install file move Steward performs on the files the installer already wrote, restoring the flat `.claude/skills/<name>/` shape every other station's skill-discovery mechanism actually requires -- not a reimplementation of what the installer does, a correction of where its output lands relative to Claude Code's own one-level skill-discovery scan.

**Why the render_skill.py gap is a finding, not a blocker for the rest of this story:** the other three deliverables (flattening, module.yaml-answers/AD-9 roster, the `tea-test-review` pixi task) are independently valuable and independently verifiable without `render_skill.py` ever succeeding against a TEA workflow skill -- Claude Code's own native skill-loading (reading `SKILL.md` + `workflow.yaml` + `instructions.md` directly, without going through BMAD's custom render pass) is very plausibly how these skills are actually meant to be invoked, given their `customize.toml` already uses BMAD's own customization vocabulary (`activation_steps_prepend`, `persistent_facts`) independent of `render_skill.py`. Confirming or refuting that hypothesis is future work for whoever owns `render_skill.py`/the TEA integration surface, not this story.

## Verification

**Commands:**
- `PATH="$PWD/.pixi/envs/local-recipes/bin:$PATH" pixi run -e pyforge-steward steward provision --module tea --json` -- expected: exit 0, ten skill names listed (bmad-tea + 9 flattened workflows), idempotent on a second run.
- `ls .claude/skills/ | grep -E "^bmad-testarch-|^bmad-teach-me-testing$|^bmad-tea$"` -- expected: 10 matches; `ls .claude/skills/testarch` -- expected: no such directory.
- `python3 -c "import tomllib; print(tomllib.load(open('_bmad/custom/config.toml','rb'))['modules']['tea'])"` -- expected: `test_artifacts` present and equal to the unresolved template string.
- `pixi run -e local-recipes tea-test-review` -- expected: invokes the real CLI with `--base origin/main --min-score 80`.
- `pixi task list -e detectors` -- expected: `tea-test-review` absent.
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: all pass.

## Auto Run Result

Status: done

**Summary:** Provisioned TEA end-to-end: added an opt-in post-install flattening mechanism (`CondaInstallBackend.flatten_nested_dirs`) that moves TEA's nine `workflows/testarch/*` workflow skills up to top-level `.claude/skills/bmad-testarch-*`/`bmad-teach-me-testing` (matching Claude Code's one-level skill discovery, which the previous nested layout was invisible to), and an opt-in module.yaml-answers mechanism (`module_yaml_relative_path`) that merges all 14 of TEA's real module.yaml variables into `[modules.tea]`, with `test_artifacts` overridden to the unresolved per-active-project template `"{output_folder}/planning-artifacts"`. Added the `tea-test-review` pixi task. Re-derived the pixi.toml-governing blanket-glob spec set from the real detector rather than assuming Story 45.2/46.1's stale count -- found nine, not six -- and reconciled all nine.

**Files changed:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` -- `CondaInstallBackend` gains `flatten_nested_dirs`/`module_yaml_relative_path`; `_installer_skill_names` predicts flattened names; new `_flatten_nested_skill_dirs` (fixed this pass to refresh, not freeze, flattened content on re-provision) and `_module_yaml_answers`; `_render_module_toml_section`/`_toml_value` extended with answer merging, a reserved-key guard, and module/key-named error context (both added this pass).
- `src/shared/packages/pyforge-steward/tests/conformance/test_provision_module_installers.py` -- TEA fixture rewritten to stage the real nested share shape + a representative module.yaml; new tests for flattening (fresh/idempotent/refresh-on-upgrade/missing-skill), module.yaml answers, and (this pass) missing/non-mapping module.yaml, the reserved-key guard, and `_toml_value`'s error context.
- `pixi.toml` -- new `tea-test-review` task.
- `.claude/skills/bmad-tea/`, `bmad-teach-me-testing/`, `bmad-testarch-{atdd,automate,ci,framework,nfr,test-design,test-review,trace}/` -- vendored upstream skill content, provisioned live during planning; untouched by this story's authored work.
- `_bmad/custom/config.toml` -- new `[modules.tea]` section (addition-only, verified).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` -- row 6 (TEA) `unwired` -> `wired`.
- Nine specs' `.memlog.md` + `scripts/.spec-surface-baseline.json` -- pixi.toml co-governance reconcile (re-derived count: nine, not the six named in the epic's own stale text).
- Sprint ledger flip.

**Review findings breakdown** (this pass, 23 findings from 4 independent context-free reviewers -- Blind Hunter, Edge Case Hunter, Verification Gap, Intent Alignment):
- Patched (1 high, 9 medium; several findings from different layers sharing one fix): the flatten-refresh bug (high -- would have permanently frozen all ten flattened skills at their first-ever-provisioned content, never picking up a real TEA version bump); zero test coverage for the missing/non-mapping module.yaml guards; `_toml_value`'s uncaught/context-free `TypeError` for an unsupported answer type; no reserved-manifest-key collision guard.
- Deferred (6, recorded in frontmatter `deferred:`, plus 3 more medium/low findings deferred as documented scope boundaries rather than code fixes -- see the triage log for the full list): the render_skill.py/workflow.yaml incompatibility and the story's own "done" flip despite it (matches this epic's own established precedent from 46.1/46.2); the per-station-vs-global-template interpretation of `test_artifacts`; no promoted per-story spec yet for 46.1/46.2/46.3; several currently-inert edge cases in the new flatten/discovery logic.
- Rejected (1 false + 3 low): a claimed silent `.spec-surface-baseline.json` rewrite of an unrelated spec, refuted by direct before/after JSON comparison; a cosmetic sorting-style inconsistency; a test-design observation that actually reflects *better* practice, not a regression; the pixi task's `N`-as-argument implementation, which matches this project's own established house convention.

**Follow-up review recommendation: true.** One high-verdict finding (the flatten-refresh bug) and nine medium-verdict findings were patched this pass, several touching the same new module.yaml-answers code path in close succession. Specific unverified risk to re-check: the flatten-refresh fix was proven against a fixture simulating a version bump, but not against a REAL TEA package version bump (the pinned version hasn't changed since this story landed); and the render_skill.py/workflow.yaml incompatibility remains a real, disclosed gap that blocks the epic's own literal acceptance criterion until a future, larger effort addresses it.

**Verification performed:** `pixi run -e pyforge-steward pytest .../test_provision_module_installers.py -v` (36/36 passed, including all patches and the new refresh-proving test); `pixi run -e pyforge-steward pyforge-steward-test` (1126 -> 1131 passed across this review pass's additions); `ruff check` on all touched files (11 pre-existing findings, confirmed identical count via the established baseline, zero net new); live re-verification against the real repo: `steward provision --module tea --json` re-run twice more (idempotent, no `testarch/` container, all 10 skills present); `_bmad/custom/config.toml`'s real `[modules.tea]` section re-confirmed parseable with all 14 answer keys; `pixi task list -e detectors` confirmed `tea-test-review` absent; direct JSON diff of `scripts/.spec-surface-baseline.json` confirming exactly the nine claimed specs changed and no others (refuting the Blind Hunter's tenth-spec claim).

**Residual risks:** the render_skill.py/workflow.yaml incompatibility (disclosed, not fixed -- a separate, larger effort). The six deferred items above, all real-in-principle-but-currently-inert or documented interpretations. No promoted per-story spec exists yet for this story or its two predecessors in this batch -- to be addressed at merge time per this repo's own stated convention.
