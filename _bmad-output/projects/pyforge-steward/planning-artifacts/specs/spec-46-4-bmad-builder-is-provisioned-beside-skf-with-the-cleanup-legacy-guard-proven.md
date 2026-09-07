---
title: 'Story 46.4: bmad-builder is provisioned beside skf, with the cleanup-legacy guard proven'
type: 'feature'
created: '2026-09-07'
baseline_revision: '09b7d0214c2688f7952b12b7ef41f269a85c6ab0'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
deferred:
  - summary: >-
      The `if not skill_names: raise RuntimeError(...)` branch (empty
      skills_source_dir) is currently unreachable given bmb's own
      registration (skill_dir is guaranteed to be a child of
      skills_source_dir, and skill_dir's own existence is already checked
      earlier) -- defensive code for a future misregistration, with no
      test.
    evidence: |-
      Real defensive code, but exercising it requires deliberately
      misconfiguring a future SetupSkillBackend registration; not worth a
      test for currently-dead-but-harmless code.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_provision_setup_skill
    severity: low
  - summary: >-
      `_copy_setup_skill_dirs` does rmtree-then-copytree per skill with no
      staging/temp-and-rename step; a process kill or disk error between
      those two calls could leave a skill directory missing or
      half-populated.
    evidence: |-
      Matches the same pattern already used by `_flatten_nested_skill_dirs`
      (Story 46.3) and every other module's own idempotent-overwrite
      convention in this file; not a new risk class this story introduces.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_copy_setup_skill_dirs
    severity: low
  - summary: >-
      The "collision check passes against the live 16 skf-* dirs" claim is
      only verified by a one-time manual run recorded in .memlog.md; no
      test fixture populates skf-*-shaped directories.
    evidence: |-
      The registry-level `test_supported_installer_modules_have_disjoint_skill_names`
      and `test_live_share_skill_names_are_disjoint_across_installer_modules`
      tests already cover the structural cross-module-collision invariant
      generically; a bmb-specific skf-* fixture would be redundant
      coverage of the same mechanism.
    location: >-
      src/shared/packages/pyforge-steward/tests/conformance/test_provision_module.py
    severity: low
  - summary: >-
      Once bmb is recorded installed, a later-introduced foreign directory
      at one of the five skill-name paths would be silently overwritten on
      the next re-provision rather than refusing.
    evidence: |-
      Matches the exact same idempotent-overwrite architecture every other
      module in this file already uses (the collision check is
      intentionally skipped once `already_installed` is true); not a new
      risk this story introduces, a pre-existing, fleet-wide design choice.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_provision_setup_skill
    severity: low
  - summary: >-
      "bmad-builder is provisioned beside skf" is tested only against
      synthetic fixtures (four fabricated sibling skill dirs), never the
      real installed skf-* tree or a real bmad-builder share tree, in any
      automated test.
    evidence: |-
      Matches this project's own established pattern (Stories 46.2/46.3)
      of pairing synthetic-fixture unit tests with a documented, dated
      live-verification run recorded in .memlog.md for the real-tree half
      of a claim.
    location: >-
      src/shared/packages/pyforge-steward/tests/conformance/test_provision_module.py
    severity: low
  - summary: >-
      "The cleanup-legacy guard proven" relies on the pre-existing Story
      6.1 argv-assertion test rather than a new, story-owned assertion
      specific to the new copy code path.
    evidence: |-
      The existing test re-runs against the CURRENT, updated
      `_provision_setup_skill` (including the new copy step) on every
      suite run -- confirmed still green after this story's changes --
      so it is current, live coverage, not stale inherited evidence, even
      though its own assertion text was not modified by this diff.
    location: >-
      src/shared/packages/pyforge-steward/tests/conformance/test_provision_module.py
    severity: low
  - summary: >-
      "Provisioned"/"wired" status asserts a stronger claim (functional
      reachability by a station persona) than what this diff's own
      functional surface delivers (files land + config record).
    evidence: |-
      Matches Stories 46.2/46.3's own precedent for what "wired" means in
      this register -- "installed and bookkept," not "proven invocable by
      a live persona session." Reasonable, consistent interpretation.
    location: >-
      _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md
    severity: low
  - summary: >-
      No test in this diff touches Mason (the register's row 7 also names
      Mason as a wielder of module/agent authoring alongside Steward).
    evidence: |-
      Explicitly out of this story's own scope per its Never clause and
      Code Map (Mason's own routing is a separate story, not this one).
    location: >-
      _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md
    severity: low
---

<intent-contract>

## Intent

**Problem:** `bmad-builder` 2.2.2 is installed and `_SUPPORTED_MODULES["bmb"]` is registered as a `SetupSkillBackend`, but that backend only drives `bmad-bmb-setup`'s config-merge scripts (writing `_bmad/config.yaml` and `_bmad/module-help.csv`) -- it never copies any skill directory into `.claude/skills/` (confirmed live: `.claude/skills/` has zero `bmb`-related entries today, and the share tree has all five: `bmad-bmb-setup`, `bmad-agent-builder`, `bmad-workflow-builder`, `bmad-module-builder`, `bmad-eval-runner` under `share/bmad-builder/skills/`). This is a known, named gap ("adversarial review F-5").

**Approach:** Extend `SetupSkillBackend` with an opt-in skills-copy step (a new `skills_source_dir` field, set only for `bmb`) that copies each of the five skill directories into `.claude/skills/`, gated by the same skill-name-collision check the `CondaInstallBackend` path already uses (reused, not reimplemented) -- checked against the live 16 `skf-*` dirs. Add a unit test proving the extension never introduces a `cleanup-legacy.py`/`--legacy-dir` call (the existing Story 6.1 test already asserts this for the current subprocess calls; confirm it stays valid and sufficient once the new copy step -- a plain file operation, no new subprocess call -- lands). Add the `bmad-agent-steward` routing lines for both pipelines (builder skills for persona/workflow authoring, `skf-*` for domain-skill compilation).

## Boundaries & Constraints

**Always:**
- `skills_source_dir` on `SetupSkillBackend` is opt-in (`Path | None = None`, unset for any future `SetupSkillBackend` module) -- set only for `bmb`, to `Path("skills")` relative to `backend.skill_dir`'s own parent (i.e. `share/bmad-builder/skills`, confirmed live as the real path containing all five skill dirs plus `module.yaml`/`module-help.csv`, which the copy step must skip -- discover only directories, mirroring `_installer_skill_names`'s own directory-only `iterdir()` filter).
- The skill-copy step runs the skill-name-collision check first (reusing `_check_skill_name_collisions`, never a second, divergent implementation), then copies each of the five discovered directories into `.claude/skills/<name>` (fresh install: create; re-provision of an already-installed `bmb`: overwrite in place, matching every other backend's own idempotent-overwrite convention).
- The five landed skill names are exactly: `bmad-bmb-setup`, `bmad-agent-builder`, `bmad-workflow-builder`, `bmad-module-builder`, `bmad-eval-runner` (confirmed live via the share tree's own `skills/` listing).
- `_bmad/config.yaml` still gains the `bmb` section via the existing, untouched `merge-config.py` call (Story 6.1's own mechanism -- `SetupSkillBackend` is explicitly NOT part of the Story 46.2 AD-9 migration to `_bmad/custom/config.toml`, since that migration only touched `CondaInstallBackend`'s `_record_module_manifest` path).
- The existing unit test at `tests/conformance/test_provision_module.py` asserting no call's argv ever contains `cleanup-legacy.py`/`--legacy-dir` must still pass unmodified after this story's extension -- the new copy step is a plain `shutil.copytree`-class operation, never a subprocess call, so it cannot introduce either forbidden invocation by construction. If this claim turns out false once implemented (i.e. the copy step somehow needs a subprocess), that is a HALT-worthy contradiction of this story's own Never clause below, not something to route around.
- `bmad-agent-steward`'s persona skill gains routing text (one addition, matching the AD-2 pointer-line convention already established in Stories 46.1/46.2/46.3): persona/workflow authoring routes to the builder skills (`bmad-agent-builder`, `bmad-workflow-builder`, `bmad-module-builder`, `bmad-eval-runner`, `bmad-bmb-setup`), domain-skill compilation routes to `skf-*` -- two named pipelines, not a single blended line.
- The register's own row 7 (`bmad-builder`) already carries this story's key (`46.4`) and its wielder (`steward (module/agent authoring), mason`) -- verify, do not restate or re-decide; only `steward`'s own persona-skill routing text is new work here (`mason`'s side, if any, is that station's own story, not this one).

**Never:**
- Never pass `--legacy-dir` to `merge-config.py`/`merge-help-csv.py`, and never invoke `cleanup-legacy.py` at all -- it would `shutil.rmtree` this repo's own governance-owned `_bmad/core/config.yaml` as an unconditional side effect of its hardcoded `[module_code, "core"]` removal list (Story 6.1's own documented hazard, re-affirmed by this story's own epic text).
- Never touch the `CondaInstallBackend`/`_provision_conda_install` path (tea/cis/utility-skills/manticore) -- this story's changes are scoped to `SetupSkillBackend`/`_provision_setup_skill` only.
- Never migrate `bmb`'s roster entry to `_bmad/custom/config.toml` -- that AD-9 migration was explicitly scoped to `CondaInstallBackend` modules only (Story 46.2's own Boundaries); `bmb` keeps writing `_bmad/config.yaml` via `merge-config.py`, unchanged.
- Never add a skill-name-collision allowlist bypass for `bmb` -- the same collision check every other module goes through applies here too, checked against the real, live `skf-*` tree (16 dirs today).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh bmb provision | No `.claude/skills/bmad-*builder*`/`bmad-bmb-setup`/`bmad-eval-runner` yet | `steward provision --module bmb --json` copies all 5 skill dirs, `_bmad/config.yaml` gains `bmb`, no collision with the 16 `skf-*` dirs | -- |
| Re-provision | The 5 dirs already exist from a prior run | Overwritten in place (idempotent), no duplication, no error | -- |
| Foreign collision | A `.claude/skills/bmad-agent-builder` dir already exists, NOT recorded as `bmb`-installed | `RuntimeError` naming the collision, nothing copied, nothing written to `_bmad/config.yaml` | -- |
| `cleanup-legacy.py` guard | Any invocation of `steward provision --module bmb` | The existing unit test's argv assertion still passes -- no call ever contains `cleanup-legacy.py` or `--legacy-dir` | -- |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py:344-349` (`SetupSkillBackend`) -- add `skills_source_dir: Path | None = None` (relative to repo root).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` `_SUPPORTED_MODULES["bmb"]` -- add `skills_source_dir=Path(".pixi/envs/local-recipes/share/bmad-builder/skills")` (confirmed live: this exact path holds `module.yaml`, `module-help.csv`, and the five skill directories).
- `.pixi/envs/local-recipes/share/bmad-builder/skills/` -- confirmed live contents: `module.yaml`, `module-help.csv` (both files, must be excluded from the copy), and five directories (`bmad-bmb-setup`, `bmad-agent-builder`, `bmad-workflow-builder`, `bmad-module-builder`, `bmad-eval-runner`).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py:568-590` (`_check_skill_name_collisions`) -- reuse verbatim for the new copy step; same signature already used by `_provision_conda_install`.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py:469-479` (`_installer_skill_names`) -- the existing directory-only `iterdir()` discovery pattern to mirror for the new bmb skill-name prediction (a small sibling helper or an inline equivalent -- match this file's existing style, don't invent a third discovery convention).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py:809-887` (`_provision_setup_skill`) -- insert the collision-check + copy step. Ordering: collision-check before the subprocess calls (matching `_provision_conda_install`'s own ordering of collision-check-before-install-side-effects); copy the skills either before or after `merge-config.py` runs (no interdependency between the two -- confirm no ordering constraint exists in `bmad-bmb-setup`'s own scripts before assuming either order is safe).
- `src/shared/packages/pyforge-steward/tests/conformance/test_provision_module.py:200-224` -- the existing `cleanup-legacy.py`/`--legacy-dir` guard test; re-run after implementation to confirm it stays green with no changes needed. If a change IS needed, that itself is a finding to record, not a silent edit.
- `.claude/skills/bmad-agent-steward/SKILL.md` -- add the two-pipeline routing text (builder skills vs. `skf-*`), matching the "## Utility skill routing (AD-2)"-style heading convention Story 46.2 already established on the other five persona skills.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` -- row 7 (`bmad-builder`): confirm the `Wired` cell needs updating from `unwired` to `wired` once actually provisioned (mirroring Stories 46.2/46.3's own precedent of updating the row the moment the member is genuinely wired) -- verify live via `steward suite pipeline-truth` after provisioning, don't assume.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` -- add `SetupSkillBackend.skills_source_dir`; register it for `bmb`; add the discovery+collision-check+copy step to `_provision_setup_skill`.
- `src/shared/packages/pyforge-steward/tests/unit/test_provision*.py` or `tests/conformance/test_provision_module.py` (match this package's existing per-concern file organization -- verify which file already covers `bmb` before adding a new one) -- tests for: fresh copy of all 5 skills, idempotent re-provision, a foreign-collision refusal, and re-confirmation that the `cleanup-legacy.py`/`--legacy-dir` guard test still passes with zero modification.
- `.claude/skills/bmad-agent-steward/SKILL.md` -- the two-pipeline routing addition.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` -- row 7 `Wired` cell update if the live pipeline-truth check confirms it's now `wired`.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/.memlog.md` -- a dated `(event)` line for the bmb skill-copy landing.
- Re-derive (never assume a stale count from a prior story) the blanket-glob `pixi.toml`-governing spec set IF this story's changes touch `pixi.toml` at all -- if they do not (this story adds no pixi task), skip this step entirely and say so in the Auto Run Result, rather than reconciling specs with nothing to reconcile.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml` -- flip `46-4-bmad-builder-is-provisioned-beside-skf-with-the-cleanup-legacy-guard-proven` to `done` via the project's sprint-ledger-sync mechanism once verified.

**Acceptance Criteria:**
- Given `bmad-builder` 2.2.2 in the pixi env, when `steward provision --module bmb --json` runs, then `bmad-bmb-setup`, `bmad-agent-builder`, `bmad-workflow-builder`, `bmad-module-builder`, `bmad-eval-runner` all land under `.claude/skills/`, the wire-time collision check passes against the live 16 `skf-*` dirs, and `_bmad/config.yaml` gains the `bmb` section (unchanged mechanism).
- Given a foreign, unrecorded dir already at one of the five predicted skill paths, when `steward provision --module bmb` runs, then it refuses with a named collision error and writes nothing.
- Given a re-provision of an already-installed `bmb`, when it runs again, then the five skills are overwritten in place (idempotent), no error, no duplication.
- Given the existing `cleanup-legacy.py`/`--legacy-dir` guard test, when the full `pyforge-steward-test` suite runs after this story's changes, then that test still passes with zero modification to its own assertions.
- Given `bmad-agent-steward`'s persona skill, when inspected, then it names both pipelines (builder skills for persona/workflow authoring; `skf-*` for domain-skill compilation) as two distinct routing statements.

## Spec Change Log

## Review Triage Log

### 2026-09-07 — Review pass
- verdicts: 16 findings — high 2, medium 2, low 10, false 2, maybe-false 0
- findings:
  - `[low]` `[defer]` Blind Hunter: the "no skills discovered" empty-`skills_source_dir` branch has zero test coverage -- recorded in frontmatter `deferred:`; currently unreachable given bmb's own registration, defensive code for a future misconfiguration.
  - `[high]` `[patch]` Blind Hunter (same root as Verification Gap's own pre-verified gap finding below): the skill-copy step ran BEFORE the `merge-config.py`/`merge-help-csv.py` subprocess calls, so a failed subprocess call left the freshly-copied skill dirs behind with `_bmad/config.yaml` never gaining the `bmb` key -- a retry then saw its own leftover directories as a foreign collision and permanently refused. Applied: the actual copy now runs only after both subprocess calls succeed (the collision check itself stays early, before any side effect, preserving the "foreign collision refuses with nothing written" guarantee); proved with a new test that fails the first attempt, confirms nothing was copied, then succeeds on retry.
  - `[low]` `[defer]` Blind Hunter: `_copy_setup_skill_dirs`'s rmtree-then-copytree per skill has no staging/temp-and-rename step -- recorded in frontmatter `deferred:`; matches the same pattern Story 46.3's `_flatten_nested_skill_dirs` and every other module already use.
  - `[false]` `[reject]` Blind Hunter: the memlog's "1126 passed" baseline vs. "1135 passed" final count doesn't reconcile with only 4 new test functions -- refuted: the actual baseline (this story's own `baseline_revision`, the end of Story 46.3) was 1131, not 1126 (confirmed via this reviewing session's own final Story 46.3 verification); 1131 + 4 new tests = 1135 reconciles exactly. The memlog simply cited the wrong "before" number; the code and test delta are both correct.
  - `[medium]` `[patch]` Blind Hunter: no disambiguation between `bmad-eval-runner` (bmad-builder, runs a skill's own evals during authoring) and the similarly-named, unrelated `bmad-eval-quality` CLI (register row 5, scores a code reviewer's output) -- applied: added a one-sentence disambiguation to `bmad-agent-steward/SKILL.md`'s routing line.
  - `[low]` `[defer]` Blind Hunter: the "collision check passes against the live 16 skf-* dirs" claim is only verified by a one-time manual run, not a test populating skf-*-shaped fixture dirs -- recorded in frontmatter `deferred:`; the registry-level disjoint-skill-names tests already cover the structural invariant generically.
  - `[false]` `[reject]` Blind Hunter: an out-of-scope stylistic reformat (a blank line removed near the `pytest` import) is bundled into an otherwise-surgical diff -- refuted: this was this review pass's own necessary `ruff --fix` correction for an import-sort violation introduced by the new test additions, not an erroneous change from the original implementation; confirmed it restores ruff's finding count to the established baseline.
  - `[medium]` `[patch]` Edge Case Hunter: a foreign plain file (not a directory) at a predicted skill path would raise an unclear `shutil.copytree` `FileExistsError` instead of a named error. Applied: `_copy_setup_skill_dirs` now raises a clear `RuntimeError` naming the offending path; new test proves it (using an already-installed `bmb` so the scenario reaches this guard rather than the earlier, broader collision check).
  - `[low]` `[defer]` Edge Case Hunter: `_copy_setup_skill_dirs`'s loop could fail partway through (permission/disk error) leaving a mix of copied and un-copied skills -- recorded in frontmatter `deferred:`; duplicate root cause of the Blind Hunter staging/temp-rename finding above.
  - `[low]` `[defer]` Edge Case Hunter (claim): once bmb is recorded installed, a later-introduced foreign directory at a skill-name path would be silently overwritten on the next re-provision -- recorded in frontmatter `deferred:`; matches the identical idempotent-overwrite architecture every other module in this file already uses, not a new risk.
  - `[high]` `[patch]` Verification Gap (pre-verified gap finding, trusted per protocol, live-demonstrated): duplicate of the Blind Hunter retry-self-collision finding above -- same fix, already applied and proved.
  - `[low]` `[defer]` Verification Gap (other finding): the "no skills discovered" branch is dead code under the current registration -- duplicate of the Blind Hunter finding above; same route.
  - `[low]` `[defer]` Intent Alignment: "beside skf" is tested only against synthetic fixtures, never the real skf-*/bmad-builder trees, in any automated test -- recorded in frontmatter `deferred:`; matches this project's own established pattern (46.2/46.3) of synthetic-fixture tests plus a dated live-verification memlog line for the real-tree half of a claim.
  - `[low]` `[defer]` Intent Alignment: "the cleanup-legacy guard proven" relies on the pre-existing Story 6.1 test rather than a new, story-owned assertion -- recorded in frontmatter `deferred:`; the existing test re-runs against the CURRENT, updated code on every suite run (confirmed still green after every patch this pass), so it is live, current coverage, not stale inherited evidence, even though its own text wasn't modified.
  - `[low]` `[defer]` Intent Alignment: "provisioned"/"wired" asserts a stronger functional-reachability claim than what this diff's own surface (files land + config record) delivers -- recorded in frontmatter `deferred:`; matches Stories 46.2/46.3's own established meaning of "wired" in this register.
  - `[low]` `[defer]` Intent Alignment: no test touches Mason, named in the register row alongside Steward -- recorded in frontmatter `deferred:`; explicitly out of this story's own scope per its Never clause.

## Design Notes

**Why reuse `_check_skill_name_collisions` rather than writing a bmb-specific check:** the function is already generic over `name`/`skill_names`/`cwd`/`already_installed` and carries no `CondaInstallBackend`-specific assumptions in its own body (confirmed by reading it) -- a second, parallel implementation would be exactly the kind of "never a second, divergent check" pattern this file's own docstrings elsewhere warn against.

**Why the copy step doesn't need its own new error-context helper:** `_provision_setup_skill`'s existing `FileNotFoundError`/`RuntimeError` messages already name the module and the offending path pattern consistently; the new copy step's own failure modes (missing `skills_source_dir`, a predicted skill not actually present as a directory) should follow that exact same message shape, not invent a new one.

## Verification

**Commands:**
- `PATH="$PWD/.pixi/envs/local-recipes/bin:$PATH" pixi run -e pyforge-steward steward provision --module bmb --json` -- expected: exit 0, five skills listed, idempotent on a second run.
- `ls .claude/skills/ | grep -E "^bmad-bmb-setup$|^bmad-agent-builder$|^bmad-workflow-builder$|^bmad-module-builder$|^bmad-eval-runner$"` -- expected: 5 matches.
- `grep -c "bmb" _bmad/config.yaml` -- expected: non-zero (the merge-config.py mechanism is unchanged).
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: all pass, including the pre-existing `cleanup-legacy.py`/`--legacy-dir` guard test, unmodified.

## Auto Run Result

Status: done

**Summary:** Extended `SetupSkillBackend` with an opt-in `skills_source_dir` field (set only for `bmb`) so `_provision_setup_skill` now actually copies bmad-builder's five skill directories into `.claude/skills/` -- closing the long-standing gap where the backend only ever drove `merge-config.py`/`merge-help-csv.py` and never copied any skills. Gated by the same `_check_skill_name_collisions` every `CondaInstallBackend` module already uses. Added the two-pipeline routing text to `bmad-agent-steward/SKILL.md`. The pre-existing `cleanup-legacy.py`/`--legacy-dir` argv guard test needed no changes and stays green.

**Files changed:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` -- `SetupSkillBackend.skills_source_dir`; `_setup_skill_names`; `_copy_setup_skill_dirs` (fixed this pass: now guards against a foreign plain-file target); `_provision_setup_skill` (fixed this pass: the copy is deferred until after both subprocess calls succeed, closing a real retry-self-collision bug; the collision check itself stays early).
- `src/shared/packages/pyforge-steward/tests/conformance/test_provision_module.py` -- 4 original tests (fresh copy, idempotent re-provision, foreign-collision refusal, CLI reporting) plus 2 added this pass (retry-after-failure success, target-exists-as-file guard).
- `.claude/skills/bmad-agent-steward/SKILL.md` -- two-pipeline routing text, plus (this pass) an `eval-runner`/`eval-quality` disambiguation sentence.
- `.claude/skills/bmad-{bmb-setup,agent-builder,workflow-builder,module-builder,eval-runner}/` -- vendored upstream skill content, provisioned live during planning; untouched by this story's authored work.
- `_bmad/config.yaml` -- gained the `bmb:` section via the unchanged `merge-config.py` mechanism; `_bmad/module-help.csv` created via the unchanged `merge-help-csv.py` mechanism.
- `adoption-register.md` row 7 (`bmad-builder`) `unwired` -> `wired`; sprint ledger flip; dated memlog `(event)` entry.
- No `pixi.toml` change in this story -- the pixi.toml-governing spec-surface re-derivation step was correctly skipped, per the story's own Tasks instruction, and noted as skipped rather than silently omitted.

**Review findings breakdown** (this pass, 16 findings from 4 independent context-free reviewers -- Blind Hunter, Edge Case Hunter, Verification Gap, Intent Alignment):
- Patched (2 high, 2 medium): a real, live-demonstrated retry-self-collision bug (copying skills before the subprocess calls meant a failed retry permanently locked on its own leftover directories -- independently found and demonstrated by both Blind Hunter and Verification Gap); a foreign-plain-file-at-target guard with a clear error message; an `eval-runner`/`eval-quality` naming disambiguation.
- Deferred (8, recorded in frontmatter `deferred:`): several real-in-principle-but-low-risk fragility items matching pre-existing patterns elsewhere in this file (no staging/temp-rename during copy, post-install foreign-dir overwrite on re-provision -- both shared by every other module's own idempotent-overwrite convention); test-coverage gaps for currently-unreachable defensive code and for real-tree/skf-*/Mason claims that this project's own established pattern already covers via live-verification memlogs rather than synthetic fixtures.
- Rejected (2 false): a claimed test-count-discrepancy in the memlog, refuted by identifying the correct baseline (1131, not the memlog's mistaken 1126) which reconciles the delta exactly; a claimed out-of-scope stylistic reformat, refuted as this review pass's own necessary `ruff --fix` correction, not an erroneous change from the original implementation.

**Follow-up review recommendation: true.** Two high-verdict findings (both halves of the same retry-self-collision bug, independently found by two reviewers) were patched this pass, along with two medium findings. Specific unverified risk to re-check: the reordering fix (copy after subprocess success) was proven against a fixture simulating a `merge-config.py` failure and retry, but not against a real, live `bmad-builder` provisioning failure (no such failure has actually occurred against the real package in this session).

**Verification performed:** `pixi run -e pyforge-steward pytest .../test_provision_module.py -v -k bmb` (8/8 passed both before and after this pass's patches, plus 2 new); `pixi run -e pyforge-steward pyforge-steward-test` (1135 -> 1137 passed across this review pass's additions); `ruff check` on both touched files (20 pre-existing findings confirmed via `git stash`-based before/after comparison, zero net new after removing one incidental `noqa` this pass introduced); live re-verification: `steward provision --module bmb --json` re-run, idempotent, 5 skills present, `_bmad/config.yaml` has `bmb:`; directly reproduced the retry-self-collision bug against the pre-fix code and confirmed the fix resolves it.

**Residual risks:** the eight deferred items above, all real-in-principle-but-low-risk or matching pre-existing, accepted patterns elsewhere in this file. No promoted per-story spec exists yet for this story (matches its two immediate predecessors in this batch) -- to be addressed at merge time per this repo's own stated convention.
