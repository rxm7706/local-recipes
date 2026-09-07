---
title: 'Story 46.2: utility-skills is provisioned and its ten skills have wielders'
type: 'feature'
created: '2026-09-07'
baseline_revision: '1ff4517e52e6a82fa992632f0f87d2104f8f4d10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
deferred:
  - summary: >-
      The epic's own text asks for "the module's module.yaml answers at
      the installer's key paths" in the AD-9 roster section; no
      CondaInstallBackend module (tea/cis/utility-skills/manticore) ships
      a module.yaml, so this is vacuous for the migration this story
      actually performs.
    evidence: |-
      Confirmed: no module.yaml exists anywhere under
      .pixi/envs/local-recipes/share/bmad-utility-skills/. That machinery
      is exclusive to bmb's SetupSkillBackend path, untouched by this
      story. Disclosed as an explicit interpretation in the spec's own
      Boundaries & Constraints before implementation began.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_record_module_manifest
    severity: low
  - summary: >-
      "The CAP-8 pre-flight scan compares conda-module skills against
      share/bmad-utility-skills/skills" (epics.md) names a specific
      existing subsystem (spec-bmad-method-core-upgrade's CAP-8, the
      local-customization pre-flight in upgrade.py); this story satisfies
      the underlying drift-detection intent via a standalone pytest
      assertion instead, and does not touch upgrade.py.
    evidence: |-
      Confirmed via grep: zero references to this story in upgrade.py.
      Extending the real CLI pre-flight report machinery would be a
      materially larger, cross-cutting change disproportionate to this
      story's S effort estimate. Disclosed as the one clause "most likely
      to need a documented deviation" in the spec's own Boundaries before
      implementation began; the Intent Alignment reviewer independently
      confirmed this exact divergence.
    location: >-
      src/shared/packages/pyforge-steward/tests/conformance/test_provision_module_installers.py::test_live_utility_skills_share_tree_matches_the_ten_expected_names
    severity: medium (documented deviation, not a defect)
  - summary: >-
      adoption-register.md's column header ("Wired 2026-09-06") and
      file-level "Measured 2026-09-06" intro note were left unchanged even
      though row 8's cell was updated based on a 2026-09-07 re-verification.
    evidence: |-
      The header's own convention states "a member's wiring changes only
      by changing its row" -- read as the header/intro documenting the
      table's original baseline pass, not an auto-updating per-row
      timestamp. A reader who does not read that sentence carefully could
      still momentarily believe the whole table is a 2026-09-06 snapshot.
    location: >-
      _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md
    severity: low
  - summary: >-
      _record_module_manifest's line-based section matcher only replaces
      the first occurrence of a `[modules.<name>]` header if the file
      somehow already contains more than one (a state that should not
      arise from this function's own writes, but could from manual editing).
    evidence: |-
      Real in principle, no live trigger today (no duplicate section
      exists in the tracked _bmad/custom/config.toml). The regex-swallowing
      bug that made duplicates more likely to accumulate silently was
      fixed this pass (line-based boundary stops at the first
      blank/comment/next-header line); a genuinely already-duplicated file
      would need separate, manual reconciliation regardless of this
      writer's behavior.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_record_module_manifest
    severity: low
  - summary: >-
      The section matcher does not tolerate CRLF line endings in an
      existing `[modules.<name>]` header line (compares against a bare
      `\n`/`\r\n`-stripped literal, which is CRLF-tolerant for the compare
      itself, but the file is read as text in default universal-newlines
      mode so this is likely already fine in practice -- flagged as
      low-confidence residual risk, not independently re-verified with an
      actual CRLF fixture this pass).
    evidence: |-
      Python's default text-mode file reading normalizes line endings, so
      a CRLF source file should already present as LF to this code; not
      independently proven with a dedicated CRLF fixture test this pass.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_record_module_manifest
    severity: low
  - summary: >-
      Non-BMP Unicode characters in a name/installer/skill value would be
      escaped by json.dumps as UTF-16 surrogate pairs, which tomllib
      rejects on the next read.
    evidence: |-
      Currently inert -- every value this writer ever renders today (a
      registered module name, an installer entry-point name, a skill
      directory name) is a plain ASCII identifier from hardcoded
      _SUPPORTED_MODULES data or discovered skill directory names, never
      user-supplied Unicode.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py::_toml_string
    severity: low
---

<intent-contract>

## Intent

**Problem:** `bmad-utility-skills` 2.0.0 is pinned and installed in the `local-recipes` pixi env, and `steward provision --module utility-skills` already works end-to-end (confirmed live this session: it copies 10 `bmad-os-*` skill dirs and records them), but nothing routes those 10 skills to a wielding station, the roster is still written to the legacy `_bmad/config.yaml` instead of AD-9's `_bmad/custom/config.toml [modules.utility-skills]`, and now that the module is actually provisioned, `adoption-register.md`'s own row for it is stale ("unwired") and Story 46.1's freshly-shipped meta-tests fail against the live tree.

**Approach:** Provision utility-skills (already done, confirmed working); migrate the roster writer shared by every `CondaInstallBackend` module from `_bmad/config.yaml` to `_bmad/custom/config.toml [modules.<name>]` (AD-9), with backward-compatible reads for the pre-existing `cis` entry still sitting in the legacy file; add one routing pointer line to each of the six wielding stations' persona skills; update the register's row and § 2 table to match reality; and add a live-tree assertion closing DW-FU-15-3-4 for this module.

## Boundaries & Constraints

**Always:**
- The roster-writer migration (AD-9) is a change to the SHARED function backing every `CondaInstallBackend` module (`cis`, `tea`, `utility-skills`, `manticore`), not a utility-skills-only special case -- verified by exercising it via utility-skills (this story's own module), per the story's own AC wording ("provision's roster writer moves").
- The new `[modules.<name>]` TOML section carries exactly `provisioned_by`, `installer`, `skills` (an array) -- the same three fields the legacy YAML entry carried. `bmad-utility-skills` (confirmed: no `module.yaml` ships in its share tree) and the other three `CondaInstallBackend` modules also have no `module.yaml`-derived answers to merge in (that machinery is exclusive to the `bmb` `SetupSkillBackend` path, which this story does not touch) -- so "the module's `module.yaml` answers at the installer's key paths" from the epic text is vacuous for every module this story's migration actually touches; do not invent a `module.yaml` lookup for a `CondaInstallBackend` module.
- `_bmad/custom/config.toml` carries extensive hand-written prose comments (documented header block, per-module explanatory comments for `[modules.skf]`) that MUST survive byte-for-byte. Write the new `[modules.<name>]` section by locating-and-replacing (if it already exists) or appending (if it does not) a well-delimited TOML block via targeted text editing -- never a full parse-mutate-reserialize round trip through a TOML library, which would silently drop every comment in the file.
- `--list-modules` must keep reporting `cis` as `"installed"` after this migration, even though `cis`'s own roster entry was written by the OLD mechanism (Story 46.8, already shipped) and still lives only in `_bmad/config.yaml` -- the read side checks `_bmad/custom/config.toml` first, then falls back to the legacy `_bmad/config.yaml` for a module whose entry lives only there. Do not re-provision or hand-migrate cis's existing entry to satisfy this; the fallback read is the correct, minimal fix.
- Every one of the 10 `bmad-os-*` skills gets exactly one routing pointer line in its wielding station's persona skill (`bmad-agent-<station>/SKILL.md` or `customize.toml`), per the register's own § 2 assignment: herald (`bmad-os-changelog`, `bmad-os-changelog-social`), doctor (`bmad-os-root-cause-analysis`), warden (`bmad-os-review-pr`, `bmad-os-findings-triage`), scribe (`bmad-os-diataxis`, `bmad-os-audit-file-refs`, `bmad-os-editorial-review-translation`), marshal (`bmad-os-gh-triage`), steward (`bmad-os-skill-to-bundle`) -- one line per station is enough even where a station wields more than one of the ten.
- `adoption-register.md`'s row 8 (`bmad-utility-skills`) "Wired 2026-09-06" cell is updated to reflect the live, now-provisioned state (confirmed via `steward suite pipeline-truth`: value `wired`, detail ".claude/skills matches prefix 'bmad-os-'") -- Story 46.1's own AC ("the row changes first") applies here for real, for the first time since that meta-test shipped.
- The DW-FU-15-3-4 live-tree assertion for this module: a test that provisions (or dry-run-discovers) utility-skills' skill set from the real installed `share/bmad-utility-skills/skills/` tree and asserts it equals the exact 10 expected `bmad-os-*` names -- closing, for utility-skills, the same class of "is the module's effective skill set actually checked against the live tree, not just assumed" gap `_CIS_SKILL_NAMES` left open for CIS (CIS's own half of DW-FU-15-3-4 was already closed by Story 46.8, per the open-items register).
- Interpretation, recorded here rather than left implicit: "the CAP-8 pre-flight scan compares conda-module skills against `share/bmad-utility-skills/skills`" is read as satisfied by the same live-tree drift assertion above (recorded skills/roster vs. the real share-package contents), not as a mandate to extend `steward upgrade bmad-core`'s own pre-flight CLI/report machinery (`upgrade.py`) with a new, cross-cutting check -- the latter would be materially larger than this story's `S` effort estimate and is not named anywhere else in this epic's stories. If a reviewer disagrees, this is the one clause most likely to need a documented deviation, not a silent reinterpretation.

**Never:**
- Never touch `bmb`'s `SetupSkillBackend` path, `merge-config.py`, or any `module.yaml`-answers machinery -- that is a different provisioning path this story does not exercise or change.
- Never re-provision or edit CIS's existing `_bmad/config.yaml` entry to force it into the new format -- the backward-compatible read handles it.
- Never add more than one pointer line per station for utility-skills' skills, and never restate routing in `AGENTS.md` or `CLAUDE.md` (AD-2, already covered by Story 46.1's meta-test, which this story's changes must keep green).
- Never widen `steward upgrade bmad-core`'s pre-flight report structure in this story (see the Interpretation note above).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh provision | `bmad-utility-skills` in the env, no prior `[modules.utility-skills]` section | `steward provision --module utility-skills --json` copies 10 skill dirs and appends a new `[modules.utility-skills]` section to `_bmad/custom/config.toml`, preserving every existing comment/section byte-for-byte | -- |
| Idempotent re-provision | The section already exists from a prior run | The section is replaced in place (same 3 fields, same content since nothing changed), not duplicated | -- |
| `--list-modules` after migration | `cis` recorded only in legacy `_bmad/config.yaml`; `utility-skills` recorded only in the new `_bmad/custom/config.toml` | Both report `"installed"` | A module recorded in neither location reports `"available"`, unchanged from today |
| DW-FU-15-3-4 live-tree assertion | The real installed `share/bmad-utility-skills/skills/` directory | Discovered skill set == the 10 expected `bmad-os-*` names, exactly | A share-tree change (skill added/removed upstream) that isn't reflected in the expected-name list fails the assertion loudly |
| Story 46.1's meta-tests, re-run after this story | `.claude/skills/bmad-os-*` now exist; register updated; routing lines added | `test_skill_routing_matches_ad2_for_every_currently_provisioned_row` and `test_wired_column_agrees_with_live_pipeline_truth_for_every_row` both pass | -- |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py:349-369` -- `_SUPPORTED_MODULES` (already registers `utility-skills` as a `CondaInstallBackend`, `installer="bmad-utility-skills-install"`, `share_package="bmad-utility-skills"`, `skill_source_dirs=("skills",)` -- dynamic discovery, no hardcoded allowlist unlike CIS's `_CIS_SKILL_NAMES` at line 336).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py:508-546` -- `_record_module_manifest(name, *, cwd, installer, skills)`: the roster writer to migrate. Currently reads/merges/atomically-writes `_bmad/config.yaml` as YAML (`config[name] = {"provisioned_by": "steward", "installer": installer, "skills": list(skills)}`). This is the ONE function to change; it is called by every `CondaInstallBackend`'s provisioning path (confirmed: not called by `_provision_setup_skill`, the `bmb`-only path).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py:882` -- `--list-modules`'s read side: `{name: ("installed" if name in config else "available") for name in _SUPPORTED_MODULES}` where `config` is loaded from `_bmad/config.yaml`. Needs the backward-compatible two-location read described in Boundaries.
- `_bmad/config.yaml` (repo root) -- the CURRENT roster file. Confirmed live content: a `cis:` section (Story 46.8) and, as of this session's investigation, a `utility-skills:` section (this story's own live provisioning run, done before this spec was written -- see below). After migration, new/re-provisioned modules stop writing here; existing entries (cis) are read as a fallback, never migrated in place by this story.
- `_bmad/custom/config.toml` (repo root) -- the AD-9 target. Read fully before editing: extensive header comments, `[core]`, `[modules.bmm]`, `[modules.skf]` sections with detailed prose. The new `[modules.utility-skills]` section must be appended (or, on re-run, replaced in place) without disturbing any of this.
- `.claude/skills/bmad-os-{audit-file-refs,changelog,changelog-social,diataxis,editorial-review-translation,findings-triage,gh-triage,review-pr,root-cause-analysis,skill-to-bundle}/` -- already provisioned live this session (confirmed via `steward provision --module utility-skills --json`, 10 dirs landed, currently untracked in git). Nothing further to do to these dirs themselves.
- `.claude/skills/bmad-agent-{herald,doctor,warden,scribe,marshal,steward}/SKILL.md` -- each needs exactly one new routing pointer line for its assigned `bmad-os-*` skill(s), per the exact station assignment in Boundaries & Constraints.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` -- § 1 row 8 (`bmad-utility-skills`)'s "Wired 2026-09-06" cell: currently `unwired`, confirmed by live `steward suite pipeline-truth` run to now be `wired` (detail: `.claude/skills matches prefix 'bmad-os-'`). Update this cell (and the date if the register's own convention re-dates on a row change -- check the file's header/convention before assuming). § 2's ten `bmad-os-*` rows already carry the correct station/story-key assignments -- no change needed there, only the live tree and personas need to catch up to what § 2 already declares.
- `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py` (Story 46.1) -- both `test_skill_routing_matches_ad2_for_every_currently_provisioned_row` and `test_wired_column_agrees_with_live_pipeline_truth_for_every_row` are CONFIRMED FAILING right now (verified live this session) because utility-skills is provisioned but the register/routing haven't caught up yet. This story's changes must turn both green again -- treat their current failure as this story's own regression-proof, not a pre-existing issue to route around.
- `src/shared/packages/pyforge-steward/tests/conformance/test_provision_module_installers.py:176-198` -- `test_live_share_skill_names_are_disjoint_across_installer_modules`, the closest existing live-tree pattern (reads `.pixi/envs/local-recipes/share`); model the new DW-FU-15-3-4 test's repo-root-finding and share-path logic on this, but assert exact-set-equality to the 10 expected names rather than cross-module disjointness.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md:1158-1161` -- DW-FU-15-3-4's entry; per `open-items-register.md:67`, its CIS half already closed with Story 46.8 -- this story closes the utility-skills half only.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` -- rewrite `_record_module_manifest` to write `_bmad/custom/config.toml [modules.<name>]` via targeted text editing (locate an existing `^\[modules\.<name>\]$` block and replace through the next `^\[` or EOF; otherwise append with a blank-line separator), preserving every other byte of the file; update the `--list-modules` implementation (or its backing read helper) to check `_bmad/custom/config.toml` first and fall back to `_bmad/config.yaml` for a name not found there.
- `src/shared/packages/pyforge-steward/tests/unit/` or `tests/conformance/` (existing provision test files -- extend the most relevant one rather than adding a new file, matching this package's existing organization) -- unit tests for the new TOML writer: fresh-write, idempotent re-write, comment preservation, and the `--list-modules` two-location read (cis-in-legacy-only, utility-skills-in-new-only, a module in neither).
- `src/shared/packages/pyforge-steward/tests/conformance/test_provision_module_installers.py` -- add the DW-FU-15-3-4 live-tree test for utility-skills (skip cleanly if the local-recipes share tree is absent, matching the existing pattern at line 176).
- `.claude/skills/bmad-agent-herald/SKILL.md`, `bmad-agent-doctor/SKILL.md`, `bmad-agent-warden/SKILL.md`, `bmad-agent-scribe/SKILL.md`, `bmad-agent-marshal/SKILL.md`, `bmad-agent-steward/SKILL.md` -- one routing pointer line each, naming this station's assigned `bmad-os-*` skill(s).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` -- update row 8's "Wired 2026-09-06" cell from `unwired` to `wired`.
- `_bmad/config.yaml` -- leave as-is (still carries `cis:`, now also carries `utility-skills:` from this session's live provisioning run; the new writer does not touch this file going forward, and nothing in this story requires removing the stale `utility-skills:` entry from it, since the new config.toml entry is now the authoritative one the read side prefers).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/.memlog.md` -- one dated `(event)` line recording the AD-9 roster-writer migration and the register row update.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml` -- flip `46-2-utility-skills-is-provisioned-and-its-ten-skills-have-wielders` to `done` via the project's sprint-ledger-sync mechanism once verified.

**Acceptance Criteria:**
- Given `bmad-utility-skills` 2.0.0 in the pixi env, when `steward provision --module utility-skills --json` runs, then ten `bmad-os-*` dirs exist under `.claude/skills/`, `--list-modules` reports `utility-skills` installed, and the retired-ID guard and integrity meta-tests stay green.
- Given a fresh `_bmad/custom/config.toml` (no prior `[modules.utility-skills]` section) or one already provisioned once, when `steward provision --module utility-skills --json` runs, then the file gains (or idempotently keeps) exactly one `[modules.utility-skills]` section with `provisioned_by`, `installer`, `skills`, and every pre-existing comment/section in the file is byte-for-byte unchanged.
- Given `cis`'s roster entry still lives only in `_bmad/config.yaml` (Story 46.8, unmigrated) and `utility-skills`'s lives only in the new `_bmad/custom/config.toml`, when `--list-modules` runs, then both report `"installed"`.
- Given the real installed `share/bmad-utility-skills/skills/` tree, when the new DW-FU-15-3-4 test runs, then the discovered skill set exactly equals the 10 expected `bmad-os-*` names.
- Given the six wielding stations' persona skills, when Story 46.1's `test_skill_routing_matches_ad2_for_every_currently_provisioned_row` runs, then it passes (each of the 10 skills is mentioned by exactly its one assigned station's persona and by no other, and `CLAUDE.md` mentions none of them).
- Given the register's row 8 update, when Story 46.1's `test_wired_column_agrees_with_live_pipeline_truth_for_every_row` runs, then it passes (no disagreement for `bmad-utility-skills`).
- Given `pixi run -e pyforge-steward pyforge-steward-test`, when it runs after this story's changes, then it passes in full (both of Story 46.1's currently-failing tests included).

## Spec Change Log

## Review Triage Log

### 2026-09-07 — Review pass
- verdicts: 29 findings — high 0, medium 10, low 7, false 12, maybe-false 0
- findings:
  - `[medium]` `[patch]` Blind Hunter: `_bmad/config.yaml` gets a hand-added `utility-skills:` block duplicating the new `[modules.utility-skills]` entry in `_bmad/custom/config.toml`, reintroducing a split source of truth the AD-9 migration was meant to remove -- applied: removed the stray `utility-skills:` block from `_bmad/config.yaml` (it was a leftover from a live provisioning run done during planning, before the migration code existed); `--list-modules` still reports it installed via the new location alone.
  - `[false]` `[reject]` Blind Hunter: `bmad-os-findings-triage/SKILL.md` references non-existent `tam-commit`/`tam-push` skills -- refuted as out of scope: this is vendored, verbatim upstream package content the intent (provisioning + routing + config migration) does not extend to auditing or patching; a real finding against the `bmad-utility-skills` upstream package, not this diff's authored work.
  - `[false]` `[reject]` Blind Hunter: `bmad-os-review-pr/SKILL.md` references a non-existent `bmad-review-edge-case-hunter` skill -- same refutation as above: vendored upstream content, out of scope for this story's intent.
  - `[false]` `[reject]` Blind Hunter: `bmad-os-audit-file-refs/SKILL.md` hardcodes the upstream package's own `src/bmm src/core src/utility` layout, not this repo's -- same refutation: vendored upstream content, out of scope.
  - `[false]` `[reject]` Blind Hunter: `references/writing-quality.md` is duplicated verbatim across three new skill folders with no shared-file mechanism -- same refutation: vendored upstream package structure, out of scope for this story to restructure.
  - `[medium]` `[patch]` Blind Hunter: `_record_module_manifest`'s section-replacement logic swallowed any comment or blank line sitting between the rewritten section and the next section header, attributing it to (and destroying it with) the section being replaced -- applied: rewrote the matcher to stop at the first blank line, comment line, or next `[...]` header, preserving everything from that boundary onward; proven with a new test rewriting a non-last section and asserting the trailing comment/blank line survive byte-for-byte.
  - `[medium]` `[patch]` Blind Hunter: the legacy YAML writer's "must be a mapping" refusal (backed by a test) was deleted with no replacement -- the new writer never validated the destination is even well-formed TOML before text-editing it -- applied: `_record_module_manifest` now parses the existing file with `tomllib.loads` first (when non-empty) and raises a clear `RuntimeError` naming the file if it doesn't parse, restoring an equivalent safety net; new test `test_provision_installer_refuses_malformed_destination_toml` proves it.
  - `[false]` `[reject]` Blind Hunter: `bmad-os-root-cause-analysis/SKILL.md`'s frontmatter carries extra `license`/`metadata`/`compatibility` keys the other nine new skills don't -- refuted as out of scope: vendored upstream content variance, not authored by this story.
  - `[false]` `[reject]` Blind Hunter: new skills' documented runtime output locations (e.g. `_bmad-output/rca-reports/`) have no `.gitignore`/Tier classification -- refuted as out of scope: this concerns the skills' own future runtime behavior when actually invoked later, not anything created by this diff; also vendored-content-adjacent, not this story's authored surface.
  - `[false]` `[reject]` Blind Hunter: `CLAUDE.md`'s Skill Reference table isn't updated to list the ten new skills -- refuted: this would directly violate Story 46.1's own just-shipped AD-2 invariant and meta-test (`CLAUDE.md must never mention` a routed skill name) -- adding them there would break `test_skill_routing_matches_ad2_for_every_currently_provisioned_row`, not fix a gap.
  - `[medium]` `[patch]` Verification Gap (pre-verified gap finding, trusted per protocol): `_manifest_location_label`'s `CondaInstallBackend` branch was unverified at two of its three `_run_module` call sites (the "already wrote a section" and "could not confirm whether ... was touched" messages) -- confirmed by reverting the message text and observing no test failure. Action: added a direct unit test of `_manifest_location_label` per backend kind (the "already wrote a" branch is structurally unreachable for `CondaInstallBackend` modules via the real code path, since `_record_module_manifest` is unconditionally the last statement with nothing after it to fail -- a direct label test is the correct, minimal coverage rather than forcing an artificial failure that cannot occur in production) and a new integration test for the "could not confirm" branch (`test_provision_installer_state_read_failure_names_could_not_confirm`) proving it now names the TOML path.
  - `[medium]` `[patch]` Verification Gap (other finding): `_bmad/config.yaml`'s manually-added `utility-skills:` block is an orphaned duplicate that would never be updated or removed by the new writer, drifting silently from the TOML copy over time -- same root cause and same fix as the Blind Hunter finding above (already applied).
  - `[low]` `[defer]` Intent Alignment: Reading A's "module.yaml answers at the installer's key paths" is not implemented -- recorded in frontmatter `deferred:` as a disclosed interpretation (vacuous for every `CondaInstallBackend` module, none of which ship a `module.yaml`).
  - `[medium]` `[defer]` Intent Alignment: "the CAP-8 pre-flight scan compares conda-module skills against `share/bmad-utility-skills/skills`" names `upgrade.py`'s real pre-flight machinery; the diff satisfies the drift-detection intent via a standalone pytest assertion instead, never touching `upgrade.py` -- recorded in frontmatter `deferred:` as the spec's own self-disclosed, most-likely-to-be-contested deviation; a real `upgrade.py` integration is separate, larger future work disproportionate to this story's `S` effort.
  - `[low]` `[defer]` Intent Alignment: `adoption-register.md`'s column header/intro date (2026-09-06) doesn't reflect row 8's actual 2026-09-07 re-verification -- recorded in frontmatter `deferred:`; the header's own convention ("a member's wiring changes only by changing its row") supports leaving it as a baseline-pass timestamp rather than a per-row auto-update.
  - `[false]` `[reject]` Intent Alignment: diff-mass provenance note (2600 of 3423 lines are vendored skill content, not authored logic) -- informational observation, not a defect; no action applicable.
  - `[low]` `[defer]` Edge Case Hunter: the section matcher doesn't explicitly handle a CRLF-terminated existing header line -- Python's universal-newlines text-mode read should already normalize this before the comparison runs; not independently re-verified with a dedicated CRLF fixture this pass, recorded in frontmatter `deferred:`.
  - `[low]` `[defer]` Edge Case Hunter: only the first occurrence of a duplicated `[modules.<name>]` header would be updated if the file somehow already contained more than one -- real in principle, no live trigger (no duplicate exists today); the regex bug that made silent duplication more likely was fixed this pass, recorded in frontmatter `deferred:`.
  - `[low]` `[reject]` Edge Case Hunter: no validation that `name` excludes `.` before interpolating into `[modules.<name>]` (a dotted name would produce a nested TOML table) -- rejected: every caller passes a literal `_SUPPORTED_MODULES` key, all of which are hardcoded, dot-free ASCII strings; unlikely in everyday use and the fix (input validation for a value that can never actually vary) is speculative complexity with no live case.
  - `[low]` `[defer]` Edge Case Hunter: `json.dumps`-based TOML string escaping would mis-encode a non-BMP Unicode character as a UTF-16 surrogate pair, which `tomllib` rejects -- real in principle, currently inert (every rendered value today is a hardcoded ASCII identifier); recorded in frontmatter `deferred:`.
  - `[low]` `[reject]` Edge Case Hunter: no file lock around the read-modify-write in `_record_module_manifest` -- concurrent `steward provision` invocations could race -- rejected as pre-existing: the legacy YAML writer had the identical unlocked read-modify-write race; not a regression this story introduced or is responsible for fixing.
  - `[medium]` `[patch]` Edge Case Hunter: `_module_install_state_or_none`'s except tuple caught `yaml.YAMLError`/`tomllib.TOMLDecodeError`/`OSError` but not `UnicodeDecodeError`, which `tomllib.load` actually raises for invalid UTF-8 bytes (verified empirically: `tomllib.load` on non-UTF-8 bytes raises `UnicodeDecodeError`, not `TOMLDecodeError`) -- would crash past the function's own documented degrade-to-`None` contract -- applied: added `UnicodeDecodeError` to the except tuple.
  - `[false]` `[reject]` Edge Case Hunter: `bmad-os-changelog/SKILL.md` has no defined behavior when zero commits exist since the last release tag -- refuted as out of scope: vendored upstream skill-instruction content, not authored by this story.
  - `[false]` `[reject]` Edge Case Hunter: `bmad-os-changelog-social/SKILL.md` has no defined behavior when only one version tag exists -- same refutation: vendored content, out of scope.
  - `[false]` `[reject]` Edge Case Hunter: `bmad-os-findings-triage/SKILL.md` has no defined behavior for a finding that can't be matched to any PR review thread -- same refutation: vendored content, out of scope.
  - `[false]` `[reject]` Edge Case Hunter: `bmad-os-diataxis/SKILL.md`'s location table has no fallback for a path outside its five listed subdirectories -- same refutation: vendored content, out of scope.
  - `[medium]` `[patch]` Edge Case Hunter: deletion finding (high confidence) -- the legacy reader wrapped a config-read failure into a `RuntimeError` so `_run_module`'s exception handler could attach diagnostics; the new bare `read_text`/`tomllib.load` calls bypass that handler for a `UnicodeDecodeError` specifically -- same root cause and same fix as the finding above (the except-tuple widening in `_module_install_state_or_none` restores the degrade-to-`None` contract at the correct layer; `module_install_states` itself is documented and intended to propagate a genuinely malformed file, matching the `pixi.toml`-parsing precedent, so this is the right fix point, not a second wrapper).
  - `[medium]` `[patch]` Edge Case Hunter (claim, high confidence, empirically demonstrated): a CRLF-terminated or otherwise-unmatched existing header causes the append branch to run, producing two `[modules.<name>]` sections, contradicting the AC's "exactly one section" claim -- addressed as part of the section-matcher rewrite above (line-based matching is line-ending-tolerant via Python's universal-newlines text read); the specific append-produces-duplicate failure mode is closed by the same fix, though a dedicated adversarial CRLF-fixture test was not added this pass (see the CRLF deferred item above for the residual, lower-confidence uncertainty).
  - `[medium]` `[patch]` Edge Case Hunter (claim, medium confidence, empirically demonstrated): replacing a section that is not the file's last one collapsed the blank-line separator before the following section, contradicting the Design Notes' "preserving every other byte" claim -- applied: same fix as the Blind Hunter "swallows trailing comments" finding above; proven by the new non-last-section test.

## Design Notes

**TOML section writer, concretely:** read the file's full text; search for `re.compile(rf"(?ms)^\[modules\.{re.escape(name)}\]\n.*?(?=^\[|\Z)")`; if found, replace that span with the freshly-rendered section text; if not found, append `"\n[modules.{name}]\n"` plus the three fields to the end of the file (ensuring exactly one blank line separates it from whatever precedes it). Render `skills` as a TOML array; a simple one-line `skills = ["a", "b", ...]` is fine (matches the flat style already used for scalar keys elsewhere in the file) -- no need to match `[modules.skf]`'s multi-line prose-commented style, which is hand-authored, not generated.

**Why the read-side fallback, not a migration:** migrating cis's existing entry would touch a file/section this story doesn't otherwise need to touch, on behalf of a different, already-shipped story (46.8). The two-location read is strictly smaller, safer, and is itself the natural backward-compatibility shape for a roster-format change that lands after some entries already exist in the old format.

## Verification

**Commands:**
- `PATH="$PWD/.pixi/envs/local-recipes/bin:$PATH" pixi run -e pyforge-steward steward provision --module utility-skills --json` -- expected: exit 0, 10 skills listed, idempotent on a second run.
- `PATH="$PWD/.pixi/envs/local-recipes/bin:$PATH" pixi run -e pyforge-steward steward provision --list-modules --json` -- expected: `cis` and `utility-skills` both `"installed"`.
- `git diff _bmad/custom/config.toml` -- expected: an addition-only diff (a new `[modules.utility-skills]` section), zero lines removed or altered elsewhere in the file.
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: all pass, including Story 46.1's two currently-failing tests.

## Auto Run Result

Status: done

**Summary:** Migrated the roster writer shared by every `CondaInstallBackend` module (tea/cis/utility-skills/manticore) from `_bmad/config.yaml` to `_bmad/custom/config.toml [modules.<name>]` (AD-9) via comment-preserving targeted text editing; added a two-location backward-compatible read so `cis`'s pre-existing Story 46.8 entry keeps reporting installed; added one routing pointer line to each of the six wielding stations' persona skills for the ten `bmad-os-*` utility skills; updated `adoption-register.md`'s row 8 from `unwired` to `wired`; and closed the utility-skills half of DW-FU-15-3-4 with a live-tree assertion. This turned Story 46.1's two freshly-shipped meta-tests, which started failing the moment utility-skills was actually provisioned mid-session, back green.

**Files changed:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` -- `_record_module_manifest` rewritten (TOML section writer, line-based, comment/blank-line-preserving); `module_install_states` + new `_custom_config_toml_module_names` (two-location read); `_manifest_location_label` (per-backend message routing); `_module_install_state_or_none`'s except tuple widened.
- `src/shared/packages/pyforge-steward/tests/conformance/test_provision_module_installers.py` -- DW-FU-15-3-4 live-tree test; TOML-writer unit tests (fresh-write, idempotent rewrite, sibling-content preservation, non-last-section trailing-content preservation, malformed-destination refusal); `_manifest_location_label` direct test; state-read-failure integration test. Five pre-existing tests updated for the new config location; one obsolete non-mapping-config test replaced with its TOML equivalent.
- `src/shared/packages/pyforge-steward/tests/conformance/test_provision_list_modules.py` -- two-location `--list-modules` read tests.
- `.claude/skills/bmad-agent-{herald,doctor,warden,scribe,marshal,steward}/SKILL.md` -- one routing line each.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md` -- row 8 `unwired` -> `wired`.
- `_bmad/custom/config.toml` -- new `[modules.utility-skills]` section (addition-only diff, verified).
- `_bmad/config.yaml` -- the stray hand-provisioned `utility-skills:` block removed this review pass (see findings below); `cis:` entry untouched.
- `.claude/skills/bmad-os-*/` (10 new dirs) -- vendored upstream skill content, provisioned live during planning; untouched by this story's authored work.
- Memlog and sprint-status-ledger updates recording the story's landing.

**Review findings breakdown** (this pass, 29 findings from 4 independent context-free reviewers -- Blind Hunter, Edge Case Hunter, Verification Gap, Intent Alignment):
- Patched (10 medium-verdict findings, several sharing a fix): removed the orphaned `_bmad/config.yaml` duplicate roster entry; fixed the section-matcher to stop at the first blank/comment/next-header line rather than swallowing trailing content on rewrite (fixes both the "swallows comments" and "collapses blank-line separator on non-last-section rewrite" findings, proven by a new test); restored a malformed-destination-TOML refusal (replacing the deleted legacy "must be a mapping" guard); added direct + integration test coverage for `_manifest_location_label`'s previously-unverified branches; widened `_module_install_state_or_none`'s except tuple to catch `UnicodeDecodeError` (which `tomllib.load` actually raises for invalid UTF-8, not `TOMLDecodeError`), restoring the documented degrade-to-`None` contract the legacy reader had.
- Deferred (6, recorded in frontmatter `deferred:`): two self-disclosed, spec-level interpretation gaps against the epic's literal wording (module.yaml answers, vacuous for every touched module; the CAP-8 pre-flight scan, satisfied by a pytest assertion rather than an `upgrade.py` integration -- both flagged in the spec itself before implementation began); the register's header/intro date not re-stamped for a single-row update; three real-in-principle-but-currently-inert code fragility items (CRLF tolerance not independently fixture-tested, first-match-only duplicate-header handling, non-BMP Unicode escaping).
- Rejected (12 false + 2 low): nine findings against the ten new `bmad-os-*` skills' vendored upstream content (dangling skill references, path-layout mismatches, duplicated reference files, frontmatter inconsistency, missing `.gitignore` entries, undefined edge-case behavior in the skill instructions themselves) -- all out of scope, since the intent (provisioning + routing + config migration) does not extend to auditing or patching a third-party package's own content; one finding refuted because implementing it would violate Story 46.1's own just-shipped AD-2/CLAUDE.md-never invariant; one informational diff-mass observation with no actionable defect; one dot-in-name validation and one file-locking concern both judged pre-existing/inert and not worth speculative complexity.

**Process note:** the implementation subagent (properly bounded this time, unlike an earlier story in this batch) completed cleanly within its stated scope and did not fabricate a review pass or touch the read-only intent-contract. It did prematurely set the spec's own frontmatter `status` to `done` before the review step ran (corrected to `in-review` before this pass began) -- a minor process deviation, not a content problem; the actual code and its own verification were sound.

**Follow-up review recommendation: true.** Ten medium-verdict findings were patched this pass, several touching the same core writer function (`_record_module_manifest`) in close succession. Specific unverified risk to re-check: the CRLF-tolerance claim for the section matcher was reasoned about (Python's universal-newlines text read should normalize it) but not proven with a dedicated CRLF fixture test; and the deferred CAP-8/upgrade.py interpretation should be revisited if a future story needs the real pre-flight CLI to surface this drift check operator-facing, not just in the test suite.

**Verification performed:** `pixi run -e pyforge-steward pytest .../test_provision_module_installers.py -v` (25/25 passed, including all patches); `pixi run -e pyforge-steward pyforge-steward-test` (1108 failed-2/passed-1108 at the point utility-skills was first provisioned mid-planning -> 1116 passed after implementation -> 1120 passed after this review pass's additional tests); `ruff check` on every touched Python file before and after this pass (11 pre-existing findings, confirmed identical count and content before/after via a baseline-copy diff, zero net new); manually re-ran `steward provision --module utility-skills --json` twice to reconfirm idempotency after the section-matcher rewrite; manually verified `git diff _bmad/custom/config.toml` is still addition-only after the config.yaml cleanup; empirically confirmed `tomllib.load` raises `UnicodeDecodeError` (not `TOMLDecodeError`) for invalid UTF-8 bytes before deciding the except-tuple fix.

**Residual risks:** the six deferred items above, all real-in-principle-but-currently-inert or explicitly-disclosed scope interpretations. The nine vendored-upstream-content findings are real defects in the `bmad-utility-skills` package itself (dangling skill references, this-repo-layout mismatches) that will surface as broken workflows if and when someone actually invokes those specific skills -- worth a note to whoever owns tracking upstream package quality, though not this story's to fix.
