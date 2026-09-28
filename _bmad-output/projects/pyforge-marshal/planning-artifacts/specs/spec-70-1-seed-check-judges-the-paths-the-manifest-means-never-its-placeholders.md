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

**Approach:**
- Move the substitution into `seed/model/manifest.py` as the one renderer (for example `render_slug_paths(manifest, slug) -> Manifest`, `dataclasses.replace` per entry, a no-op where the placeholder is absent). `_manifest_for_init` calls it; `init`'s behaviour is byte-identical.
- `run_check` gains a keyword-only `slug: str | None = None`. With a non-empty slug, the manifest is rendered before `classify`/`build_plan`, so every templated entry is classified, planned and reported at its rendered path.
- With no slug, each entry whose path still carries `{{ slug }}` is left out of classification and planning and yields one INFO `slug-unresolved` finding (new `FindingType`), path = the templated path, message naming the entry, remedy naming `--project`. INFO never affects `failing`.
- An `unclassified-deferred` entry never yields `ARTIFACT_MISSING` (its `ABSENT` classification is skipped in the finding loop, the way `REFERENCED` already is).
- `cli/seed.py::run_check` passes the slug `_resolve_project_slug` returns (an empty string is "no slug").
- `init.py`'s docstring paragraph on the check gap is replaced by a pointer to this story; the PRD-J1 test in `test_seed_verbs_init.py` checks the full manifest with the init slug instead of a manifest that excludes templated entries.

Checking this repository still applies: the model was extracted from it and SC-02 / Story 12.2 hold it to the model, so it is never exempted by name. After this story its remaining findings are true — never adopted (`model-behind`, DRIFT) and no `.bmad-loop/policy.toml` at the primary root (HARD; the harness policy is rendered per loop home) — and belong to Story 12.2's K-02.

Ledger key: `70-1-seed-check-judges-the-paths-the-manifest-means-never-its-placeholders`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-279 (FR-225).
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

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 70.1. One renderer, in `seed/model/manifest.py`, called by `init` and `check` (P-03: no module re-derives a sibling's rule). The slug comes from the command's existing resolution, never from state. `check` stays read-only (no `seed.fs` import, no writes). A truly absent rendered path stays HARD.

**Never:**
- Do not add a `slug` key (or any key) to the seed state schema.
- Do not exempt this repository, or any repository, by name or path.
- Do not change `init`'s or `adopt`'s plans, `build_plan`, or the packaged `manifest.yaml`.
- Do not change the `.bmad-loop/policy.toml` finding on this repository; it is K-02's (Story 12.2).
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
| this repository's primary checkout | marker names a station | no `{{` path, no glob finding; `model-behind` and `.bmad-loop/policy.toml` remain | true findings (K-02) |
| `init --slug demo` | fresh directory | unchanged plan and files | as today |

</intent-contract>

## Source

Contract authored from the operator's 2026-09-28 direction, `docs/dreams/pyforge-marshal.md`'s 2026-09-28 entry (*`marshal seed check` judges the paths the manifest means*) and `spec-pyforge-marshal` CAP-279 with its 2026-09-28 direction entry in the Spec's `.memlog.md` (the reproduction and the file:line evidence), decomposed the same session as Epic 70's mint.

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-279 (FR-225).
Ledger key: `70-1-seed-check-judges-the-paths-the-manifest-means-never-its-placeholders`.
Ledger status at mint: `backlog`.
Policy: no `[epic_surfaces]` entry; the Surface is inside marshal's default surface.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks:**
- On the primary checkout, `pixi run --frozen -e pyforge-guild marshal seed check --json` carries no finding whose path contains `{{` and no `.claude/skills/**` finding.
