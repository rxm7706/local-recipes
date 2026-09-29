---
title: '70.1: Seed check judges the paths the manifest means, never its placeholders'
type: 'fix'
created: '2026-09-28'
status: 'backlog'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/manifest.yaml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/context.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `pixi run --frozen -e pyforge-guild marshal seed check --json` exits 1 on this repository with `result.failing: true`. Its HARD `artifact-missing` findings include five literal placeholders — `docs/dreams/{{ slug }}.md` (`starter-dream`), `_bmad-output/projects/{{ slug }}/.bmad-config.toml` (`project-config`), `_bmad-output/projects/{{ slug }}/planning-artifacts/specs/README.md` (`specs-readme`), `presentations/{{ slug }}/` (`deck-scaffolding`), `_bmad-output/projects/{{ slug }}/` (`project-subtree`) — and the literal glob `.claude/skills/**` (`claude-skills`, class `unclassified-deferred`). All eight projects here carry every rendered path. The cause:
- `seed/verbs/check.py::run_check` hands the packaged manifest to `detect.inventory.classify` and `plan.build.build_plan` unrendered, and its `ARTIFACT_MISSING` branch reports every `ABSENT` entry with a pending action.
- Only `seed/verbs/init.py::_manifest_for_init` substitutes `{{ slug }}` (`entry.path.replace("{{ slug }}", slug)`, `:387`); `init.py`'s own docstring records that `check` cannot verify a templated entry and leaves it for a later story (Story 10.7). AD-55 declares a manifest path templated on the slug.
- `cli/seed.py` already resolves a project for `check` (`_resolve_project_slug`: `--project`, then `BMAD_ACTIVE_PROJECT`, then the target's `_bmad/custom/.active-project` marker) and uses it only for the `[context]` read.
- An `unclassified-deferred` entry has no class contract (`model/artifact.py` excludes it from `CLASS_BEHAVIOR`); Story 12.2's oracle already excludes it explicitly.
- *(Amended 2026-09-28, operator ruling.)* `.bmad-loop/policy.toml` (`bmad-loop-policy`, generated-derived, `templates/manifest.yaml:236-245`) is HARD `artifact-missing` on the primary checkout, yet every writer renders it into a loop home only — `adapters/harness_bmadloop.py::write_policy_toml(effective, <loop_home>)` (`:797`), from `cli/config.py:732` (`--write-harness-policy`), `cli/refresh.py:135`, `cli/adapters.py:1490` and `cli/spin.py:744`, on the homes `marshal init` provisions (`~/.bmad-loops/<slug>`, branch `loop/<slug>`). The manifest has no word for where an entry is required: `_ENTRY_KEYS` (`model/manifest.py`) has no scope key and `AppliesTo` names seed verbs only. The operator ruled that the file is required in loop homes only — this repository is the seed's home, not a loop home — and that the model entry carries that scope.

**Approach:**
- Move the substitution into `seed/model/manifest.py` as the one renderer (for example `render_slug_paths(manifest, slug) -> Manifest`, `dataclasses.replace` per entry, a no-op where the placeholder is absent). `_manifest_for_init` calls it; `init`'s behaviour is byte-identical.
- `run_check` gains a keyword-only `slug: str | None = None`. With a non-empty slug, the manifest is rendered before `classify`/`build_plan`, so every templated entry is classified, planned and reported at its rendered path.
- With no slug, each entry whose path still carries `{{ slug }}` is left out of classification and planning and yields one INFO `slug-unresolved` finding (new `FindingType`), path = the templated path, message naming the entry, remedy naming `--project`. INFO never affects `failing`.
- An `unclassified-deferred` entry never yields `ARTIFACT_MISSING` (its `ABSENT` classification is skipped in the finding loop, the way `REFERENCED` already is).
- `cli/seed.py::run_check` passes the slug `_resolve_project_slug` returns (an empty string is "no slug").
- `init.py`'s docstring paragraph on the check gap is replaced by a pointer to this story; the PRD-J1 test in `test_seed_verbs_init.py` checks the full manifest with the init slug instead of a manifest that excludes templated entries.
- **The loop-home scope (amended 2026-09-28, operator ruling).** `model/manifest.py` gains one closed optional entry key, `required_in`, added to `_ENTRY_KEYS` and validated the way `applies_to` is (a `RequiredIn` enum whose one member is `loop-home`; an unknown value is a `ManifestError` prefixed with the entry id; absent means required in every checked repository). `templates/manifest.yaml`'s `bmad-loop-policy` gains `required_in: loop-home`, and its rationale says why (rendered per loop home; a primary checkout never holds one). No other entry changes; `model_version` stays `1.0.0` and the manifest keeps 43 entries.
- `cli/seed.py::run_check` resolves whether the target is a loop home: the `VcsPort.list_worktrees` entry whose path is the target carries a branch `core/context.slug_from_loop_branch` accepts (`loop/<slug>`). It passes `run_check` a keyword-only `in_loop_home: bool | None` — `None` when the listing fails or no entry matches. A keyword-only `vcs` seam defaults to the real adapter, the way `manifest=` does.
- In `run_check`'s `ARTIFACT_MISSING` branch, an absent entry with `required_in: loop-home` yields no finding when `in_loop_home is False`, beside the existing `applies_to` skip (`check.py:389-400`). `True` or `None` judges it as today: an unreadable target never passes on the scope.

Checking this repository still applies: the model was extracted from it and SC-02 / Story 12.2 hold it to the model, so it is never exempted by name. After this story its remaining findings are true and none is HARD — never adopted (`model-behind`, DRIFT), plus the DRIFT and INFO findings for managed regions, referenced dependencies and the kit — so it reads `failing: false` and exits 0 without `--strict`. `.bmad-loop/policy.toml` is not owed on it: the scope is the manifest entry's and holds for every primary checkout, not an exemption of this repository. Whether `adopt` should also skip a `loop-home` entry off a loop home is Story 12.2's (K-02) question, not this story's.

Ledger key: `70-1-seed-check-judges-the-paths-the-manifest-means-never-its-placeholders`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-279 (FR-225; amended 2026-09-28, operator ruling: `.bmad-loop/policy.toml` is required in loop homes only, a scope the manifest entry carries); AD-55 (amended in place 2026-09-28: the entry's optional `required_in`).
- Kinship: Story 10.7 (the gap named in `init.py`), Story 12.2 (the local-recipes oracle, K-02); `spec-pyforge-steward:CAP-162` (steward Story 73.1: `steward session check` reads this command's envelope whatever its exit code — the parse half, a separate steward CAP, not this story).

## Acceptance Criteria

- Given a fixture repository carrying `docs/dreams/demo.md`, `_bmad-output/projects/demo/.bmad-config.toml`, `_bmad-output/projects/demo/planning-artifacts/specs/README.md`, `presentations/demo/` and `_bmad-output/projects/demo/` When `marshal seed check --project demo --json` runs Then no finding's path contains `{{` and none of the five templated entries is `artifact-missing`
- Given the same fixture without `docs/dreams/demo.md` When the check runs with `--project demo` Then a HARD `artifact-missing` finding names `docs/dreams/demo.md` and `failing` is true
- Given no `--project`, no `BMAD_ACTIVE_PROJECT` and no marker When the check runs Then the five templated entries yield five INFO `slug-unresolved` findings naming `--project`, none is classified at a literal placeholder path, and `failing` is unaffected by them
- Given `BMAD_ACTIVE_PROJECT=demo`, or the target's marker reading `demo`, When the check runs without `--project` Then the entries are judged at the `demo` paths
- Given a manifest `unclassified-deferred` entry whose path is a glob with no literal match When the check runs Then it yields no `artifact-missing`
- Given `seed init` into a fresh directory with `--slug demo` When `run_check` runs on it with `slug="demo"` against the full packaged manifest Then the templated entries are conformant (the PRD-J1 test's exclusion is retired)
- Given the renderer called by both `init` and `check` When a manifest path carries no placeholder Then it is returned unchanged
- Given the rendering removed from `run_check` When the fixture case runs Then `docs/dreams/{{ slug }}.md` is reported missing and the test fails (mutation)
- Given a fixture repository without `.bmad-loop/policy.toml`, checked out on `main` When `marshal seed check --project demo --json` runs Then no finding names `.bmad-loop/policy.toml` (amended 2026-09-28)
- Given the same fixture checked out on `loop/demo` (a loop home) When the check runs Then a HARD `artifact-missing` finding names `.bmad-loop/policy.toml` and `failing` is true
- Given a target whose worktree listing fails (`in_loop_home` is `None`) When the check runs Then the absent `.bmad-loop/policy.toml` is HARD `artifact-missing`, as today
- Given the packaged manifest When it loads Then it holds 43 entries at `model_version` 1.0.0 and `bmad-loop-policy` carries `required_in: loop-home`; given an entry declaring `required_in: nowhere` Then `load_manifest` raises `ManifestError` prefixed with that entry's id
- Given the scope check removed from `run_check` When the `main` fixture runs Then `.bmad-loop/policy.toml` is reported missing and the test fails (mutation)

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 70.1. One renderer, in `seed/model/manifest.py`, called by `init` and `check` (P-03: no module re-derives a sibling's rule). The slug comes from the command's existing resolution, never from state. `check` stays read-only (no `seed.fs` import, no writes). A truly absent rendered path stays HARD. The loop-home scope lives on the manifest entry (`required_in`) and is resolved at the CLI boundary from the target's own branch; it is never a test of a path or a repository name.

**Never:**
- Do not add a `slug` key (or any key) to the seed state schema.
- Do not exempt this repository, or any repository, by name or path.
- Do not change `init`'s or `adopt`'s plans or `build_plan`. The packaged `manifest.yaml` changes only by `bmad-loop-policy`'s `required_in` and its rationale: no entry, class, path or `model_version` moves (amended 2026-09-28; the prior rule left the manifest untouched).
- Do not let the scope pass a loop home, or a target whose branch cannot be read: there `.bmad-loop/policy.toml` stays HARD when absent (amended 2026-09-28; the prior rule left this finding to Story 12.2's K-02).
- Do not touch steward's session check (`src/shared/packages/pyforge-steward/src/pyforge/steward/session.py`); its parse of this JSON is `spec-pyforge-steward:CAP-162`.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`; do not run `scripts/bmad-switch`.

Co-governing Specs: `spec-pyforge-marshal` (owner of `src/shared/packages/pyforge-marshal/**`) and `spec-pyforge-core` (co-governs every station's `src/`) — reconcile each one the spec-surface detector names.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| slug resolved, paths present | `--project demo`, rendered paths exist | no templated finding | none |
| slug resolved, a path absent | `docs/dreams/demo.md` missing | HARD `artifact-missing` naming it | `failing` true |
| no slug | no flag, env or marker | five INFO `slug-unresolved`; nothing classified at a placeholder | `failing` unaffected |
| env or marker only | `BMAD_ACTIVE_PROJECT` / marker `demo` | judged at `demo` paths | none |
| unclassified-deferred glob | `.claude/skills/**` | no `artifact-missing` | none |
| this repository's primary checkout | marker names a station | no `{{` path, no glob finding, no `.bmad-loop/policy.toml` finding; `model-behind` and the other DRIFT / INFO findings remain | `failing` false, exit 0 without `--strict` |
| not a loop home | branch `main`, `.bmad-loop/policy.toml` absent | no finding for `bmad-loop-policy` | none |
| loop home | branch `loop/demo`, `.bmad-loop/policy.toml` absent | HARD `artifact-missing` naming it | `failing` true |
| branch unreadable | worktree listing fails | judged as today (HARD when absent) | never passes on the scope |
| unknown scope value | an entry with `required_in: nowhere` | `ManifestError` prefixed with the entry id | manifest load fails, as for any schema error |
| `init --slug demo` | fresh directory | unchanged plan and files | as today |

</intent-contract>

## Source

Contract authored from the operator's 2026-09-28 direction, `docs/dreams/pyforge-marshal.md`'s 2026-09-28 entry (*`marshal seed check` judges the paths the manifest means*) and `spec-pyforge-marshal` CAP-279 with its 2026-09-28 direction entry in the Spec's `.memlog.md` (the reproduction and the file:line evidence), decomposed the same session as Epic 70's mint. Amended the same day from the operator's ruling that `.bmad-loop/policy.toml` is required in loop homes only (the Spec's `.memlog.md` decision entry of 2026-09-28 and CAP-279's amended text).

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-279 (FR-225).
Ledger key: `70-1-seed-check-judges-the-paths-the-manifest-means-never-its-placeholders`.
Ledger status at mint: `backlog`.
Amended 2026-09-28 (operator ruling): the loop-home scope for `.bmad-loop/policy.toml`; key and status kept.
Policy: no `[epic_surfaces]` entry; the Surface, including `seed/templates/manifest.yaml`, is inside marshal's default surface.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks:**
- On the primary checkout, `pixi run --frozen -e pyforge-guild marshal seed check --json` carries no finding whose path contains `{{`, no `.claude/skills/**` finding and no `.bmad-loop/policy.toml` finding, reads `result.failing: false` and exits 0.
