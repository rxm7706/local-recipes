---
title: 'The render-HALT class has a detector'
type: 'feature'
created: '2026-09-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      pyforge-marshal/spec-pyforge-core's own declared surface glob
      (pyforge-{atlas,doctor,herald,marshal,mason,scribe,steward,warden}/src/**)
      never matches any real path, so changes under seven of the eight
      stations' src/** silently evade that spec's drift detection.
    evidence: |-
      chain.py::_glob_to_re treats brace characters as literal regex-escaped
      text (verified directly against the glob-compiling code, no {a,b,c}
      expansion support exists), so the literal substring
      "pyforge-{atlas,doctor,herald,marshal,mason,scribe,steward,warden}"
      can never appear in any real file path. Discovered incidentally while
      reconciling this story's own pixi.toml touch against
      pyforge-marshal/spec-pyforge-core (a foreign spec); the fix (a real glob
      per station, or a spec-owned decision to only watch specific stations)
      is marshal's own spec-authoring call, not this story's to make.
    location: >-
      _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
      (surface: list)
    severity: medium
baseline_revision: 'ec4dc5dfd471370f541a9d6e3157c253d6592de3'
---

<intent-contract>

## Intent

**Problem:** `_bmad/scripts/render_skill.py` HALTs every rendering skill (`bmad-build`,
`bmad-build-auto`, ...) with `RenderError: ambiguous config value` whenever the same
bare key name occurs at two different dotted paths in the merged central config
(`load_central_config()`'s merge of `_bmad/config.toml` + `_bmad/config.user.toml` +
`_bmad/custom/config.toml` + `_bmad/custom/config.user.toml`) -- this happened live
on 2026-09-06 (`[core] user_skill_level` colliding with a regenerated
`[modules.bmm] user_skill_level`, fixed by commit `99e595cc6a`) and nothing catches
this class proactively; an operator only learns about it when a skill invocation
HALTs mid-session.

**Approach:** A new Doctor source, `sources/bmad_config.py`, independently reproduces
`load_central_config()`'s exact 4-layer structural merge (never imports
`_bmad/scripts/config_utils.py` -- Boundaries) and reproduces `_find_config_values`'s
own unqualified-leaf-key scan, EXCLUDING the `agents` top-level namespace (Design
Notes: BMAD's persona registry, not a settings namespace -- excluding it is what
makes "ok on today's tree" true; see the empirical proof below). One WARN Finding per
ambiguous key naming it and every colliding path; one OK Finding naming the checked
count when none are ambiguous. Wired into `scripts/detectors.py`'s
`_DOCTOR_SOURCE_TASKS` (offline, deterministic, no budget concerns -- same bar
`platform-policy-suite` already cleared) plus its own standalone pixi task.

## Boundaries & Constraints

**Always:**
- Read-only: only the four already-tracked/gitignored `_bmad/config*.toml` /
  `_bmad/custom/config*.toml` files. No subprocess, no git history, no writes.
- Every layer read is fail-open: a missing file, an unreadable file, or malformed
  TOML all fold to `{}` for that one layer and merging continues with the rest --
  including `_bmad/config.toml` itself, which `render_skill.py`'s own
  `load_central_config()` treats as `required=True` (Design Notes: this detector's
  job is signalling risk in whatever central config exists, not re-enforcing the
  renderer's own installation-completeness contract).
- The merge and the leaf-key scan are REPRODUCED locally in this module, never
  imported from `_bmad/scripts/config_utils.py` or `render_skill.py` -- this
  detector must keep working (and catch the SAME ambiguity class) even if the
  renderer's own merge/scan code is what is broken (mirrors every other source in
  this package's "structurally independent of the mechanism it inspects" rule).
- The `agents` top-level key is excluded from the scan entirely (neither counted as
  a leaf nor recursed into) -- verified empirically against the real tracked
  `_bmad/config.toml` + `_bmad/custom/config.toml`: without this exclusion, today's
  tree reports 6 false-positive "ambiguous" keys (`module`/`team`/`name`/`title`/
  `icon`/`description`, each repeated once per `[agents.bmad-agent-*]` entry, an
  expected structural repetition never resolved via the `{{.key}}` short-token
  mechanism the real HALT class targets) instead of the AC's required `ok`.
- Never gates: status is `ok` or `warn` only, mirroring `BMAD_METHOD_VERSION_DRIFT`'s
  own always-informs discipline.

**Never:**
- Never resolve, expand, or write `{project-root}`-style path placeholders (that is
  `render_skill.py::_resolve_config_value`'s own job, irrelevant to detecting
  ambiguity itself).
- Never treat a TOML array-of-tables as a scannable collection of leaves (mirrors
  `_find_config_values`'s own behavior: a list is a dead end, never recursed into).
- Never add a second exclusion beyond `agents` speculatively -- only this one,
  empirically-justified exclusion; a future false positive under a different
  namespace is a new story's problem, not something to pre-guess here.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Today's real tree | The actual tracked `_bmad/config.toml` + `_bmad/custom/config.toml` (no user-layer files on this machine) | Exactly one OK Finding naming the checked-key count (11) | No error expected |
| Planted collision | A fixture layer set with `[core] user_skill_level` AND `[modules.bmm] user_skill_level` (the exact 2026-09-06 incident shape) | One WARN Finding naming `user_skill_level` and both paths (`core.user_skill_level`, `modules.bmm.user_skill_level`) | No error expected |
| Missing layer file | `_bmad/config.user.toml` and `_bmad/custom/config.user.toml` both absent (the real, common case -- gitignored per-user files) | Treated as empty layers; merge and scan proceed over the remaining layers | Fail-open, no exception |
| Malformed TOML in one layer | One layer file contains unparseable TOML | That one layer folds to `{}`; the other layers still merge and are scanned | Fail-open, no exception |
| `agents` registry present | The real `[agents.bmad-agent-*]` blocks (each repeating `module`/`team`/`name`/`title`/`icon`/`description`) | None of those six keys appear in the scan at all -- no Finding, no effect on the checked-key count | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- `Source` enum (~L46-243, last member `PLATFORM_POLICY_SUITE` at L243): add `BMAD_RENDER_CONFIG_AMBIGUITY = "bmad-render-config-ambiguity"` with a Story 20.2 docstring comment following the file's own per-member convention (see `PLATFORM_POLICY_SUITE`'s comment block immediately above it for the exact prose shape to mirror).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- `REGISTRY` tuple (~L149 onward): add one `SourceRegistration(source=Source.BMAD_RENDER_CONFIG_AMBIGUITY, scope="repo", subject_station="steward", owning_station="doctor")` entry, mirroring `PLATFORM_POLICY_SUITE`'s own entry (~L407-419) -- `subject_station="steward"` because `_bmad/custom/config*.toml` customizations are steward's territory (`spec-bmad-method-core-upgrade`'s own `customization-inventory.md` C2 row: "steward | Sanctioned custom layer").
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py` -- `DISPATCH` dict (~L68-95): import `bmad_config` alongside the existing `from . import (...)` block (~L46-56); add `Source.BMAD_RENDER_CONFIG_AMBIGUITY.value: bmad_config.gather,`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py` -- read-only reference for this package's established conventions (module docstring shape, `degrade_on_exception` usage, per-Finding evidence style); NOT modified by this story.
- `_bmad/scripts/config_utils.py` -- read-only reference: `structural_merge`/`merge_layers`/`load_toml` (~L79-107) are the algorithms to REPRODUCE (never import) in the new module.
- `_bmad/scripts/render_skill.py` -- read-only reference: `_find_config_values` (~L128-137) and `_resolve_short_config` (~L140-150) are the scan algorithm to reproduce (minus path-resolution, minus the `agents` namespace).
- `_bmad/custom/config.toml` -- read-only reference: its own comment block (L9-24) documents the real 2026-09-06 incident and today's fixed pin locations -- the exact fixture shape for the planted-collision test.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py` -- `_EXPECTED_DISPATCH` dict (~L41-57) and its `bmad_method, board, chain, ...` import list (~L27-37): add `bmad_config` to the import list and `"bmad-render-config-ambiguity": bmad_config.gather,` to the dict. `test_dispatch_covers_exactly_the_registered_sources` and the parametrized tests both derive from this dict automatically -- no other edit needed in this file.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_registry.py` -- NOT edited: `test_every_source_member_has_exactly_one_registry_entry` iterates `Source` members dynamically, so it picks up the new member/registration pair automatically once both land.
- `scripts/detectors.py` -- `_DOCTOR_SOURCE_TASKS` tuple (~L204-222): add `("bmad-render-config-ambiguity", "bmad-render-config-ambiguity-check"),` following the `platform-policy-suite` precedent (offline, deterministic, no budget concerns -- unlike the opt-in-only `bmad-method-version-drift`/`sibling-dreams-drift`/`due-for-verification` rows explicitly named as excluded in the comment just above this tuple).
- `tests/scripts/test_detectors_doctor_sources.py` -- NOT edited: every assertion derives `len(detectors._DOCTOR_SOURCE_TASKS)` dynamically rather than hardcoding a count.
- `pixi.toml` -- new task block, placed alongside `[feature.local-recipes.tasks.platform-policy-suite-check]` (~L930-932): `[feature.local-recipes.tasks.bmad-render-config-ambiguity-check]` with a one-line `description` and `cmd = "python -m pyforge.doctor.sources bmad-render-config-ambiguity"`.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_config.py` (new file) -- implement `_load_layer(path) -> dict` (fail-open TOML read), `_structural_merge(base, override)` (mirrors `config_utils.structural_merge`, dict-recursive, override wins; arrays are NOT keyed-merged here since no layer in this scan needs that -- a plain `structural_merge`-shaped dict/scalar merge is sufficient and simpler), `_merge_layers(target) -> dict` (folds the four `_LAYER_RELATIVE_PATHS` in `load_central_config()`'s own order), `_find_leaf_paths(data, prefix="") -> dict[str, list[str]]` (mirrors `_find_config_values`, keyed by bare leaf name, skipping the top-level `agents` key entirely), `_gather(target) -> tuple[Finding, ...]` (merge, scan, one OK or N WARN Findings), and `gather(target) -> tuple[Finding, ...]` (wraps `_gather` in `degrade_on_exception(Source.BMAD_RENDER_CONFIG_AMBIGUITY, "bmad-render-config-ambiguity", ...)`, mirroring `bmad_method.gather`'s own outer-wrapper shape) -- closes the "nothing catches this proactively" gap.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py`, `sources/__init__.py`, `sources/__main__.py` -- wire the new `Source` member, its `REGISTRY` entry, and its `DISPATCH` entry, per Code Map.
- `scripts/detectors.py`, `pixi.toml` -- wire the new source into the default detector sweep and give it a standalone pixi task, per Code Map.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_config.py` (new file) -- unit-test `_load_layer` (hit, missing file, malformed TOML, non-table TOML), `_structural_merge` (override wins on scalar conflict, recursive dict merge, override's own scalar replaces a base dict wholesale and vice versa -- matches `structural_merge`'s own fall-through `return override` for any non-dict/non-dict pairing), `_find_leaf_paths` (single leaf, colliding leaf at two paths, `agents`-shaped repetition produces zero matches, a list value is a dead end); and `gather()`-level tests covering every I/O Matrix row, including one that builds the REAL tracked `_bmad/config.toml` + `_bmad/custom/config.toml` content as its fixture (copied verbatim, not read live from disk -- this file's isolation convention) to prove the empirical "11 checked, 0 ambiguous" claim this spec's Boundaries rely on.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py` -- add the one import and one dict entry per Code Map.

**Acceptance Criteria:**
- Given the real tracked `_bmad/config.toml` + `_bmad/custom/config.toml` content (no user-layer files), when `gather()` runs, then it returns exactly one OK Finding whose evidence names the checked-key count, and the `agents.*` per-entry field repetition produces no Finding at all.
- Given a fixture with `[core] user_skill_level` planted beside `[modules.bmm] user_skill_level` (the exact 2026-09-06 incident shape), when `gather()` runs, then it returns a WARN Finding naming `user_skill_level` and both dotted paths in its message and evidence.
- Given any one of the four layer files is missing or contains malformed TOML, when `gather()` runs, then that layer contributes nothing to the merge and no exception propagates past `gather()`.
- Given `python -m pyforge.doctor.sources bmad-render-config-ambiguity` is run from the repo root, when it executes against this repo's own real config, then it exits 0 and prints the OK finding (proving the new pixi task and CLI wiring both resolve end-to-end).

## Spec Change Log

## Review Triage Log

### 2026-09-07 — Review pass
- verdicts: 16 findings — high 0, medium 1, low 4, false 11, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind Hunter: the `spec-pyforge-doctor` memlog's Story 20.1 entry (RECONCILES `bmad_method.py`/its test) and the matching baseline-hash bump appear in this patch with no corresponding code hunk for either file — flagged as "incomplete or mislabeled" — refutation: this is a deliberate catch-up reconciliation for drift Story 20.1's own review left un-reconciled (that code already landed in Story 20.1's own commit, before this patch's `baseline_revision`); the exact same pattern — a later pass naming and closing an earlier pass's un-reconciled baseline lag with no code hunk of its own — is already established fleet-wide precedent, verbatim in this same spec's own memlog history (e.g. its "Baseline reconciliation, 2026-09-02... this spec's memlog HAD moved for the same pass, but did not NAME the 2 governed path(s)... closes that" entry).
  - `[low]` `[patch]` Blind Hunter + Verification Gap (same root cause): `models.py`'s new `BMAD_RENDER_CONFIG_AMBIGUITY` comment says the detector "Judges Marshal-governed factory apparatus" while `sources/__init__.py`'s `SourceRegistration` sets `subject_station="steward"` — the two disagree, and neither comment acknowledges that the scanned config spans an installer-managed base layer (arguably marshal's tooling-installation surface, per `BMAD_METHOD_VERSION_DRIFT`'s own precedent) and a steward-owned custom layer (the real 2026-09-06 incident's fixture deliberately spans both). Verified: this is a real copy-paste residue in the `models.py` comment (`BMAD_METHOD_VERSION_DRIFT`'s neighboring comment also says "Judges Marshal-governed factory apparatus", copied without updating). `subject_station="steward"` itself is the right, defensible choice on reflection (steward's own custom-layer pin placement is the only lever a human can actually pull to resolve any collision — the installer-managed layer is regenerated wholesale, never hand-edited — per `customization-inventory.md` C2's own remediation record), so the field stays as-is; only the misleading comment needs fixing.
  - `[false]` `[reject]` Blind Hunter: `pixi.toml` gained a new task with no `environment.yaml` regeneration, flagged against the repo's always-on rule — refutation: verified directly by running `pixi project export conda-environment -e build` and diffing byte-for-byte against the tracked `environment.yaml` — output is identical. A new pixi *task* (not a dependency) does not change the exported conda-environment spec; the rule's own trigger condition (a dependency change) does not apply here.
  - `[low]` `[patch]` Blind Hunter: `_find_leaf_paths`'s tests cover a list of scalars as the "dead end" case but never a list-of-tables (list of dicts) — the shape the docstring explicitly calls out as the motivating case — evidence: confirmed the code itself is already correct either way (`_find_leaf_paths`'s own `if not isinstance(data, dict): return result` guard makes ANY list, scalar or dict contents, a dead end identically), so this is a coverage-completeness gap, not a behavior bug. Action: add one more test asserting a list-of-dicts value is also a dead end.
  - `[false]` `[reject]` Blind Hunter: a same-named key that is a list at one path and a scalar at another (e.g. `core.tags` list vs `modules.bmm.tags` string) is never flagged ambiguous, since list-valued keys are skipped entirely — refutation: verified against the real `render_skill.py::_find_config_values`, which applies the identical exclusion (`not isinstance(value, (dict, list))`) on its own matching side — a list-valued occurrence of a key is excluded from consideration by the REAL renderer too, so this detector's behavior exactly mirrors the mechanism it inspects; there is no daylight between the two for this scenario.
  - `[low]` `[patch]` Blind Hunter: when `_bmad/config.toml` itself (the layer `render_skill.py` treats as `required=True`) is entirely missing, `gather()` still returns a plain `OK` ("no ambiguous config keys ... (0 checked)"), which reads as "verified clean" rather than "nothing was there to check" — evidence: this is a deliberate, already-documented scope decision (this spec's own Design Notes: "a missing `config.toml` here just means there is nothing to be ambiguous about yet... not a misconfiguration this detector should raise on") and stays fail-open exactly as specified; only the message wording is worth sharpening so an operator doesn't misread "0 checked" as "verified current config is clean" when it could mean "no central config exists at all." Action: message wording only, no behavior/scope change.
  - `[false]` `[reject]` Blind Hunter: `_find_leaf_paths`'s recursive call runs unconditionally for every entry (including scalar leaves), relying on the callee's own early-return guard to make it a no-op for non-dict data, rather than an explicit `elif isinstance(value, dict):` split — refutation: no actual harm is identified (not a behavior bug, not a measurable performance concern at this config tree's size — ~11 keys); this is a standard, common Python idiom (delegate the type check to the callee's own guard) with zero named consequence, not a defect.
  - `[false]` `[reject]` Blind Hunter: the `spec-pyforge-doctor` memlog gained a blank line after its frontmatter's closing `---`, unexplained by either new entry — refutation: this is `_bmad/scripts/memlog.py`'s own established append/normalization behavior (the sanctioned CLI tool used for every append in this patch), not a manual edit this story introduced or needs to explain.
  - `[false]` `[reject]` Blind Hunter: five near-identical "Cross-station surface touch... pixi.toml gained one new task..." memlog paragraphs across five foreign specs add ongoing upkeep cost versus one entry with a cross-reference — refutation: this exact one-entry-per-spec pattern (no consolidation, no cross-references) is the already-established, repeatedly-precedented fleet convention for foreign-spec-surface reconciliation, verbatim in this same `spec-pyforge-doctor` memlog's own prior entries (two separate marshal-authored "Cross-station surface touch... Reconciled + baseline re-stamped... per the foreign-spec-surface procedure" paragraphs, one per touch, 2026-09-06); each spec's memlog is also its own independent, flat, self-contained chronological record by `memlog.py`'s own documented design — consolidating across specs would violate that.
  - `[medium]` `[defer]` Blind Hunter: `pyforge-marshal/spec-pyforge-core`'s own declared surface glob (`pyforge-{atlas,doctor,herald,marshal,mason,scribe,steward,warden}/src/**`) never matches any real path (documented in that spec's memlog during this story's foreign-spec reconciliation, not remediated) — verified true and real (see `chain.py::_glob_to_re`, no brace-expansion support — confirmed directly against the glob-compiling code), meaning changes under seven of the eight stations' `src/**` silently evade that spec's drift detection today. This is marshal's own spec-authoring defect, not something this story's surface reaches or should fix cross-station. Recorded in this spec's `deferred` frontmatter for visibility; the actual remedy (a real per-station glob, or a scoped decision to watch fewer stations) is marshal's own call.
  - `[false]` `[reject]` Blind Hunter: `bmad_config.py`'s docstring cites `config_utils.py`'s `structural_merge`/`merge_layers`/`load_toml` function names as what it reproduces, and the reviewer could not verify these names exist "from the diff alone" — refutation: verified directly against the live `_bmad/scripts/config_utils.py` (not just the diff) — all three names exist verbatim as written; the docstring's traceability claim is accurate.
  - `[low]` `[patch]` Edge Case Hunter: `_load_layer`'s fail-open exception tuple (`OSError`, `tomllib.TOMLDecodeError`) omits `UnicodeDecodeError`, which `tomllib.load` genuinely raises for a non-UTF-8-encoded layer file (`UnicodeDecodeError` is a `ValueError` subclass, not an `OSError`/`TOMLDecodeError`) — verified by direct reproduction (`tomllib.load` on invalid-UTF-8 bytes raises `UnicodeDecodeError`, confirmed independently, not just taking the reviewer's word). One undecodable layer currently escapes this module's own per-layer fail-open and is instead caught only by the outer `degrade_on_exception` wrapper, degrading the whole gather to one generic WARN instead of precise per-key findings for the other three layers. Action: add `UnicodeDecodeError` to `_load_layer`'s except tuple.
  - `[false]` `[reject]` Intent Alignment: the diff's whole-tree key-name-collision scan is one level more abstract than the story's own real-world anchor (an actual skill invocation HALTing on a specific `{{.key}}` lookup) — refutation: the AC's own Then-clause literally reads "scans for a key present at two different paths," with no qualification on actual short-token usage; this spec's own Boundaries/Design Notes explicitly chose and justified this exact (broader, proactive) reading during planning, not as an implementation-time liberty.
  - `[false]` `[reject]` Intent Alignment: the `agents` top-level exclusion is "invented mid-implementation, not present in the AC," justified only by "a fact about the current fixture/tree" rather than the renderer's own real semantics, and proven only against a frozen, hand-copied test snapshot rather than the live files — refutation: the exclusion and its full reasoning (agent personas are never resolved via the generic `{{.key}}` short-token mechanism, addressed by id elsewhere instead) were authored in this spec's own Design Notes during planning, not invented ad hoc during implementation; the frozen-snapshot test convention is this test file's own pre-existing, explicitly-documented, deliberate isolation policy (its own comment: "copied VERBATIM... If the tracked files change, this fixture must be updated deliberately, not silently re-synced"), not a new risk this story introduces.
  - `[false]` `[reject]` Intent Alignment: reimplementing the renderer's merge/scan logic instead of cross-checking against the real `render_skill.py`/`config_utils.py` functions means a future change to the real renderer's merge/scan rules would go uncaught — refutation: structural independence from the mechanism under inspection is this entire doctor-sources package's established, fleet-wide, `tests/meta/test_source_independence.py`-enforced architecture (every sibling source works this way); a cross-check importing the renderer's own code would defeat the stated purpose ("this detector must keep working... even if the renderer's own merge/scan code is what is broken") rather than strengthen it.

## Design Notes

**Why `agents` is the one exclusion, empirically justified rather than assumed.**
Running the real merge+scan against today's tracked `_bmad/config.toml` +
`_bmad/custom/config.toml` (verified directly, not asserted) surfaces exactly 6
colliding leaf names (`module`, `team`, `name`, `title`, `icon`, `description`),
every single one confined to the `[agents.bmad-agent-*]` blocks -- five sibling
persona entries that structurally repeat the same field set by design. `core` and
`modules.*` together contribute zero collisions. `render_skill.py`'s own
`_find_config_values` would technically flag all 6 too if ever asked to resolve
`{{.name}}` -- but nothing ever does, because agent personas are addressed by their
own id elsewhere, never through the generic short-token mechanism. Excluding
`agents` is therefore not a guess at what "feels" like noise; it is the one
exclusion that makes the AC's own literal "ok on today's tree" true, confirmed by
running the algorithm against the real files before writing this spec.

**Why not scope the scan to `core`+`modules` by inclusion instead of excluding `agents`.**
An include-list would need updating every time a new top-level settings namespace
appears; excluding the one namespace known today to be a structurally-repeating
registry (not a settings surface) degrades gracefully if a future settings
namespace is added, and only needs revisiting if a future namespace repeats
`agents`' own "named collection of homogeneous entries" shape.

**Why config.toml's own absence is fail-open here despite `render_skill.py` requiring it.**
`load_central_config()` treats `_bmad/config.toml` as `required=True` because the
renderer cannot function at all without it. This detector's job is different: report
ambiguity risk in whatever central config actually exists right now. A missing
`config.toml` here just means there is nothing to be ambiguous about yet (a
degenerate, harmless case), not a misconfiguration this detector should error on --
that installation-completeness signal belongs to whichever check actually verifies
the BMAD installation, not this one.

## Verification

**Commands:**
- `pixi run -e pyforge-doctor pyforge-doctor-test` -- expected: full suite green, no regressions.
- `pixi run -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_config.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_registry.py -v` -- expected: every new and updated test passes.
- `pixi run -e local-recipes bmad-render-config-ambiguity-check` (once the pixi task lands) -- expected: exits 0, prints one OK line naming the checked-key count.
- `pixi run -e local-recipes detectors` -- expected: the new source appears in the sweep and reports `pass` (or `FINDINGS`/`unknown` only if something is genuinely wrong), never crashes the run.

## Auto Run Result

**Summary of implemented change:** a new Doctor source, `bmad-render-config-ambiguity`, independently reproduces `_bmad/scripts/render_skill.py`'s `load_central_config()` four-layer structural merge and its `_find_config_values` unqualified-leaf-key scan (never imports either), excluding the `agents` top-level namespace (BMAD's persona registry, empirically verified as the one exclusion needed to make "ok on today's tree" true). Emits one WARN Finding per ambiguous key naming it and every colliding dotted path, or one OK Finding naming the checked-key count. Wired into `scripts/detectors.py`'s default `detectors`/`detectors-ci` sweep and its own standalone pixi task, mirroring `platform-policy-suite`'s prior landing shape.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_config.py` (new) — the detector.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_config.py` (new) — unit tests for every helper plus gather()-level tests for every I/O Matrix row, including a frozen copy of the real tracked `_bmad/config.toml` + `_bmad/custom/config.toml` proving "11 checked, 0 ambiguous."
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` — new `Source.BMAD_RENDER_CONFIG_AMBIGUITY` member.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` — new `SourceRegistration` (`subject_station="steward"`).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py` — new `DISPATCH` entry.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json`, `tests/unit/test_models.py`, `tests/meta/test_source_independence.py`, `tests/unit/test_sources_dispatch.py` — closed-taxonomy/coherence/independence/dispatch test updates required to keep the full suite green (not named in the spec's own Code Map, but load-bearing exhaustiveness gates).
- `scripts/detectors.py` — new `_DOCTOR_SOURCE_TASKS` entry (offline, deterministic, no budget concerns, matching `platform-policy-suite`'s own precedent).
- `pixi.toml` — new `bmad-render-config-ambiguity-check` task.
- Spec-surface reconciliation (process compliance, not story scope creep — the story's own Surface line named this explicitly: "six blanket-glob specs → memlog + scoped stamps"): memlog entries + scoped `--write-baseline` stamps for `pyforge-doctor/spec-pyforge-doctor` and `pyforge-doctor/spec-pixi-candidate-currency` (own project, also covering Story 20.1's own previously-un-reconciled `bmad_method.py` drift, found during this pass) plus the 5 foreign specs whose blanket `pixi.toml` surface glob this story's one new pixi task incidentally touched (`pyforge-atlas/spec-atlas-kedro-catalog-expansion`, `pyforge-marshal/spec-pyforge-core`, `pyforge-steward/spec-mcp-era-isolation`, `spec-platform-image-one-pixi-env`, `spec-python-agent-platform`) — each verified via the three-check foreign-spec-surface procedure (zero overlap beyond the shared `pixi.toml`; `git stash` proved `pixi.toml` carried zero drift against each spec's baseline immediately before this story's edit, so this story's edit is the sole, fully-accounted-for cause) before reconciling.

**Review findings breakdown** (16 total across 4 layers):
- Patched (4, all applied and re-verified): `models.py`'s `BMAD_RENDER_CONFIG_AMBIGUITY` comment copy-paste residue ("Judges Marshal-governed factory apparatus") conflicting with the real `subject_station="steward"` (low); `_load_layer`'s fail-open exception tuple missing `UnicodeDecodeError`, verified by direct reproduction that `tomllib.load` raises it for non-UTF-8 layers (low); the `checked == 0` OK message reading as "verified clean" rather than "nothing to check" (low); no test for a list-of-tables "dead end" shape, the exact case the docstring names (low).
- Deferred (1, medium): `pyforge-marshal/spec-pyforge-core`'s own declared surface glob (brace-expansion syntax `pyforge-{atlas,doctor,...}/src/**`) never matches any real path — verified directly against `chain.py::_glob_to_re`, which has no brace-expansion support — a genuine, pre-existing foreign-spec authoring defect discovered incidentally during this story's own reconciliation, not this story's surface to fix. Recorded in frontmatter `deferred`.
- Rejected as false (11): a mislabeling claim about Story 20.1's own memlog/baseline catch-up (matches established fleet precedent verbatim); a missing `environment.yaml` regeneration claim (empirically disproven — byte-identical export before/after, since only a pixi *task*, not a dependency, changed); an asymmetric list-vs-scalar collision claim (verified to exactly mirror the real renderer's own exclusion of list values); an unconditional-recursion style nit with no named harm; an unexplained memlog blank line (is `memlog.py`'s own established write behavior); five near-identical foreign-spec memlog entries called redundant (matches this repo's own established, repeated foreign-spec-reconciliation convention verbatim); a docstring-citation-unverifiable claim (verified directly against the real `config_utils.py` — the cited names exist); three intent-alignment divergence points (scope of "ambiguous," the `agents` exclusion's justification, and the lack of a renderer cross-check test) — all three are deliberate, already-documented architectural/design decisions from this spec's own planning, not implementation-time liberties, and a renderer cross-check would defeat this package's own fleet-wide structural-independence architecture.

**Follow-up review recommendation:** `false` — all 4 patched entries were `low`; the one `medium` finding was routed to `defer`, not `patch`. The rule (`true` only if a patched entry was `high`, or 2+ `medium` entries were patched) is not met.

**Verification performed:**
- `pixi run -e pyforge-doctor pyforge-doctor-test` → 1400 passed / 1 skipped (post-implementation, pre-patch), 1402 passed / 1 skipped (post-patch; delta matches the 2 new tests).
- `pixi run -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_config.py -q` → all pass, including the 2 new review-driven tests.
- `pixi run -e local-recipes bmad-render-config-ambiguity-check` → exits 0, prints the OK finding naming the checked-key count against this repo's own real config.
- `pixi run -e local-recipes spec-surface-check` → `ok`, zero drift, after the full memlog+scoped-stamp reconciliation across all 7 touched specs (2 own, 5 foreign).
- `pixi project export conda-environment -e build` diffed byte-for-byte against the tracked `environment.yaml` → identical (confirms the Blind Hunter's `environment.yaml`-regeneration claim was false).
- `ruff check` on every new/changed doctor-package file → clean at every stage (pre- and post-patch).

**Residual risks:** none rated `high`/`medium` remain unaddressed in-scope. The one deferred item (`spec-pyforge-core`'s unmatchable surface glob) is a foreign, pre-existing spec-authoring defect outside this story's own surface — recorded for marshal's own attention, does not affect this detector's own correctness or this story's own governed files.
