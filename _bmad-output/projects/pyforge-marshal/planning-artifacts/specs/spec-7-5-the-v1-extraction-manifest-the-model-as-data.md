---
title: 'Story 7.5: The V1 extraction manifest (the model, as data)'
type: 'feature'
created: '2026-08-11'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '4cf8ae53138727263af60c6b94c9c3a359668021'
final_revision: 'bb1d7319b6'
context:
  - '{project-root}/_bmad-output/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md'
  - '{project-root}/_bmad-output/planning-artifacts/specs/spec-pyforge-marshal/extraction-manifest.md'
  - '{project-root}/AGENTS.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `seed/model/manifest.py` (Story 7.4) can load and validate a manifest, but no
`templates/manifest.yaml` content exists yet — Genesis has a schema with nothing to say. FR-66,
FR-71 and FR-118 require the operating model declared as real V1 data, not engine branches.

**Approach:** Author `seed/templates/manifest.yaml` (every artifact named in the PRD's *The V1
manifest*, classified per its own rule) plus the shared region body files it references under
`seed/templates/files/`, and `seed/model/artifact.py` (a small `ClassBehavior`/`Artifact` data
layer backing the future `marshal seed explain`, FR-127).

## Boundaries & Constraints

**Always:**
- One `templates/manifest.yaml`, `model_version: "1.0.0"`, validated by `load_manifest`
  (Story 7.4) with zero `ManifestError`s. `never_write` is exactly 7 patterns: `docs/dreams/*.md`,
  `**/planning-artifacts/**`, `**/implementation-artifacts/**`, `docs/specs/*.md`, `_bmad/bmm/**`,
  `_bmad/core/**`, `_bmad/skf/**` (Skill Forge is installer-owned like bmm/core — PRD's re-audit).
- REFERENCED: 16 entries — the PRD's 6 (`bmad-method`, `bmad-loop`, `copier`, `tmux`,
  `bmad-installed-skills` for `_bmad/bmm/**`+`_bmad/core/**`, `pixi`) plus the 10 the PRD's own
  extraction-manifest companion audited in but the PRD prose never absorbed (`bmad-builder`,
  `bmad-test-architecture-enterprise`, `bmad-creative-intelligence-suite`, `bmad-skill-forge`,
  `bmad-dashboard`, and 5 triage-open: `bmad-manticore`, `bmad-labs-skills`,
  `bmad-utility-skills`, `bmad-method-wds-expansion`, `bmad-module-template`) — omitting them
  is a known, already-recorded coverage gap, not a stale-doc quirk. `pin` values come from the
  live `pixi.toml` where it and the PRD disagree (`pixi` is `>=0.76.1` live, not the PRD's stale
  `>=0.72.2`); `path: "n/a"` for all (matches Story 7.4's own fixture convention).
- COPIED-MANAGED: 5 entries — `bmad-switch` (`scripts/bmad-switch`), `bmad-loop-worktree`
  (`scripts/bmad-loop-worktree`), a detector-registry entry pointing at `scripts/detectors.py`
  (NOT a single hand-named detector file — the companion doc's own audit found and fixed this
  exact "hardcoded list omits the newest thing" defect once already), `docs/dreams/README.md`,
  and the CI workflow (`.github/workflows/detectors.yml`).
- COPIED-SEEDED: 6 entries — starter Dream (`docs/dreams/{{ slug }}.md`, `applies_to: init`),
  `_bmad-output/projects/{{ slug }}/.bmad-config.toml`, `_bmad/custom/config.toml`,
  `.bmad-loop/policy.toml`, the specs README (`.../planning-artifacts/specs/README.md`,
  `applies_to: init`), deck scaffolding (`presentations/{{ slug }}/`).
- GENERATED-DERIVED: 9 entries — 3 whole-file adapters (`.cursor/rules/specs.mdc`, `GEMINI.md`,
  `.github/copilot-instructions.md` — NOT `CLAUDE.md`, see dedup below), `_bmad-output/PROJECTS.md`,
  the two `_bmad-output/{planning,implementation}-artifacts` symlinks as separate entries, and 3
  directory skeletons (`docs/dreams/`, `docs/specs/`, `_bmad-output/projects/{{ slug }}/`).
- HYBRID-MANAGED-REGION: exactly 4 file entries. `AGENTS.md` (format `html`; regions `tiers`
  anchor `["## The tiers"]`, `portability-contract` anchor `["## Portability contract"]`,
  `dream-first-workflow` anchor `["## Dream-first workflow"]`). `CLAUDE.md` (format `html`;
  regions `tiers` anchor `["### Spec-driven, framework-neutral layout"]`, `bmad-multiproject`
  anchor `["### Multi-Project Pattern"]`). `.gitignore` (format `hash`; region `model-ignores`
  anchor `["<top>"]`). `README.md` (format `html`; region `model-badge` anchor `["<top>"]`,
  rationale notes it is opt-in/off-by-default — no schema field for that exists yet, so this is
  descriptive only, not enforced here).
- **Region-body convention (new, this story):** one file per **region name** (shared across
  entries that declare it — `tiers` appears on both `AGENTS.md` and `CLAUDE.md`, backing exactly
  one source per AD-63) at `seed/templates/files/<region-name>.md.j2` (`.gitignore.j2` for
  `model-ignores`). 6 files total: `tiers`, `portability-contract`, `dream-first-workflow`,
  `bmad-multiproject`, `model-ignores`, `model-badge`. Bodies for the three AGENTS.md regions
  are faithful, install-target-neutral transcriptions of AGENTS.md's own "The tiers",
  "Portability contract" and "Dream-first workflow" sections (per the epics AC).
- unclassified-deferred: 3 entries — `.claude/skills/**`, `pixi.toml` (task blocks),
  `docs/reference/library-llms-full.md` — each with a real, non-generic `rationale` (required on
  every class; S-9.5's future coverage check treats a bare deferral as uncovered).
- `seed/model/artifact.py`: `ClassBehavior` (frozen dataclass: `definition`, `update_behavior`,
  `hand_edit_behavior`), a `CLASS_BEHAVIOR` mapping keyed by the 5 product `ArtifactClass`
  members (not `unclassified-deferred`) transcribed from the PRD's classification-rule table,
  and `Artifact` (frozen dataclass pairing a `ManifestEntry` with its `ClassBehavior`) plus a
  `describe(entry) -> Artifact` factory — the data FR-127's future `explain` verb renders.

**Block If:** none — every entry classifies from the PRD/architecture without human input.

**Never:**
- No `.gitignore` entry under `copied-managed` — the PRD lists it there AND under HYBRID, but
  its own COPIED-MANAGED description says "delivered as a managed region," so it is ONE HYBRID
  entry, not two. Same dedup for `CLAUDE.md`: the PRD's GENERATED-DERIVED table names it, but
  the very next paragraph says "all **three** inspected" (excluding it) and its own HYBRID row
  gives it two named regions — one HYBRID entry, not a second whole-file DERIVED one.
- No `never_write` negation/exemption syntax. The AC's two carve-outs (the init-seeded Dream and
  specs README each sit inside a broader `never_write` glob) are NOT encoded here — Story 7.4's
  schema has no per-entry exemption field and adding one is outside this story's Surface
  (`manifest.yaml` + `artifact.py`, not `manifest.py`). This is the exact gap Story 7.4's review
  already recorded as belonging to "whoever authors 7.5's real manifest" — recording, not
  silently fixing, is the correct move here; the fs-guard/orchestrator story that constructs
  `NeverWrite` from a loaded `Manifest` must exclude each `copied-seeded`+`applies_to: init`
  entry's own resolved path before matching.
- No `legacy_of` usage — no entry in this V1 manifest needs it yet (AD-59's mechanism stays
  unexercised, matching Story 7.4's own precedent).
- No jinja2 dependency and no rendering — `{{ slug }}` in `path` values and the region files
  stays literal, unparsed text (Story 7.4's own Never bullet, still true here).
- No changes to `seed/model/manifest.py` or `seed/model/version.py`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Load the real manifest | `templates/manifest.yaml` via `load_manifest` | `Manifest` with `model_version == 1.0.0`, all entries present, zero errors | No error expected |
| Class coverage | every entry | exactly one of the 6 `ArtifactClass` values | No error expected |
| No duplicate paths | all 43 entries | no two entries share a rendered `path` (proves the two dedups above) | No error expected |
| Region-body coverage | every `hybrid-managed-region` region name | a matching `templates/files/<name>.md.j2` exists and is non-empty | Test failure names the missing file |
| unclassified-deferred rationale | the 3 deferred entries | each `rationale` is non-generic prose, not a placeholder | Test failure names the entry |
| `Artifact` pairing | `describe(entry)` for one entry per product class | returns the matching `ClassBehavior` | No error expected |

</intent-contract>

## Code Map

- `src/pyforge/marshal/seed/templates/manifest.yaml` -- NEW: the V1 manifest content (~43
  entries across 6 classes + the 7-pattern `never_write` list), the deliverable FR-66/FR-71
  describe.
- `src/pyforge/marshal/seed/templates/files/{tiers,portability-contract,dream-first-workflow,
  bmad-multiproject,model-badge}.md.j2`, `.../model-ignores.gitignore.j2` -- NEW: the region
  body files, transcribed faithfully from `AGENTS.md`/`CLAUDE.md`/`.gitignore`.
- `src/pyforge/marshal/seed/model/artifact.py` -- NEW: `ClassBehavior`, `CLASS_BEHAVIOR`,
  `Artifact`, `describe()` -- data backing the future `marshal seed explain` (FR-127), same
  `@dataclass(frozen=True)` idiom as `manifest.py`/`core/model.py`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_templates_manifest.py` -- NEW:
  loads the packaged manifest via `importlib.resources` + `load_manifest`, asserts the I/O
  matrix above plus per-class counts and the `never_write` list contents.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_model_artifact.py` -- NEW:
  `CLASS_BEHAVIOR` covers exactly the 5 product classes, `describe()` pairing, frozen/hashable.

## Tasks & Acceptance

**Execution:**
- [x] `seed/templates/manifest.yaml` -- author all 43 entries + `never_write` (7 patterns) +
  `model_version: "1.0.0"` per Boundaries -- the manifest FR-66/FR-67/FR-68/FR-70/FR-71 require
- [x] `seed/templates/files/*.md.j2` (+ `model-ignores.gitignore.j2`) -- author the 6 region
  bodies, faithful to `AGENTS.md`/`CLAUDE.md`/`.gitignore`'s current content -- realizes the
  epics AC's "template bodies render ... faithfully to AGENTS.md"
- [x] `seed/model/artifact.py` -- implement `ClassBehavior`/`CLASS_BEHAVIOR`/`Artifact`/
  `describe()` per Boundaries -- the data FR-127 needs
- [x] `tests/unit/test_seed_templates_manifest.py` -- the I/O matrix's manifest-loading rows
- [x] `tests/unit/test_seed_model_artifact.py` -- the I/O matrix's `Artifact`-pairing row

**Acceptance Criteria:**
- Given `templates/manifest.yaml`, when `load_manifest` parses it, then it returns a `Manifest`
  with `model_version == ModelVersion.parse("1.0.0")` and zero `ManifestError`s
- Given the loaded manifest, when entries are grouped by class, then counts are 16 referenced,
  5 copied-managed, 5 copied-seeded, 10 generated-derived (review moved `.bmad-loop/policy.toml`
  here -- see Review Triage Log), 4 hybrid-managed-region (with the region names listed in
  Boundaries), 3 unclassified-deferred
- Given the loaded manifest's `never_write`, when compared to the 7-pattern list in Boundaries,
  then it matches exactly
- Given the two hybrid entries that could have collapsed into two manifest rows each
  (`.gitignore`, `CLAUDE.md`), when the manifest is inspected, then each appears exactly once
- Given every declared region name across all hybrid entries, when checked against
  `seed/templates/files/`, then a matching, non-empty body file exists
- Given the existing `pyforge-marshal` test/lint/import-linter suite, when this story's files
  are added, then all stay green with no meta-test changes required

## Spec Change Log

- **Judgment calls not pinned by Boundaries, recorded for traceability (no contract change):**
  - `pin` values for the 5 triage-open REFERENCED entries (`bmad-manticore`,
    `bmad-labs-skills`, `bmad-utility-skills`, `bmad-method-wds-expansion`,
    `bmad-module-template`) use each package's live `pixi.toml` version constraint, because
    `ManifestEntry.__post_init__` requires a non-empty `pin` on every `referenced` entry even
    though the companion doc calls their floors "unset" -- the `rationale` field carries the
    "installed but barely exercised, triage open" caveat instead.
  - `bmad-installed-skills` and `bmad-skill-forge` (delivered "via `bmad-method install`", not
    a standalone conda package) use `bmad-method`'s own floor (`>=6.10.0`) as their `pin`, for
    the same non-empty-pin reason.
  - `tmux`'s pin is `>=3.7b_`, the exact live `pixi.toml` string (vs. the PRD/companion doc's
    `>=3.7b`) -- same "pin comes from live pixi.toml where it disagrees" rule the Boundaries
    applied to `pixi`. `bmad-dashboard`'s pin (`>=1.2.2.dev0`) follows the identical rule
    against the companion doc's `>=1.2.2` -- omitted from this list in the first pass (review
    finding, see Review Triage Log), listed here now for the same completeness reason `pixi`
    and `tmux` are.
  - `applies_to` on entries the Boundaries left unstated (most `copied-managed`,
    `generated-derived`, and all `hybrid-managed-region` entries) is `both`; the two
    `copied-seeded` init-only carve-outs and `docs/specs/` (adopt-only legacy skeleton) are
    exactly as named in the Boundaries/Never sections.
  - The I/O matrix's "no two entries share a rendered path" check
    (`test_no_two_materialized_entries_share_a_rendered_path`) excludes the 16 `referenced`
    entries' shared `"n/a"` sentinel path -- they are explicitly *not materialized*, so "a
    rendered path" does not apply to them; the check targets the two named dedups
    (`.gitignore`, `CLAUDE.md`), which it also asserts directly by id.

## Review Triage Log

### 2026-08-11 — Review pass (second follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 3, low 2)
- defer: 7: (high 0, medium 7, low 0)
- reject: 13: (high 0, medium 3, low 10)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): the prior pass's
    `MappingProxyType` fix did not close the hole its own comment claims to close. A
    `MappingProxyType` is a read-only *view*, not a copy, and the table stayed bound to a
    module-level `_CLASS_BEHAVIOR`, so `_CLASS_BEHAVIOR[cls] = other` remained fully visible
    through `CLASS_BEHAVIOR` — the exact "rebound entry corrupts `describe()` and still passes
    its own guard, undetectably from inside" the comment describes. VERIFIED by execution, and
    by grep: nothing else in the package referenced the private name. The existing test proved
    only that the proxy rejects `CLASS_BEHAVIOR[...] = ...`. Fixed by building the literal
    inline into `MappingProxyType({...})` so no mutable alias exists, plus
    `test_no_mutable_module_level_alias_backs_the_read_only_table`, which asserts the module
    exposes no `ArtifactClass`-keyed dict under any name.
  - `[medium]` `[patch]` Blind Hunter: the manifest header comment justified BOTH dedups with
    one citation — "their own PRD rows say so once read past the summary table" — and that
    citation supports only one of them. VERIFIED against `prd.md`: true for `.gitignore`, whose
    COPIED-MANAGED row says outright "delivered as a managed region in a repo-owned
    `.gitignore`"; FALSE for `CLAUDE.md`, whose GENERATED-DERIVED row carries no hybrid pointer
    and whose summary sentence reads in full "The **four** agent-adapter files are the clearest
    case for DERIVED: all three inspected (…)" — i.e. it *counts* CLAUDE.md among the four
    rather than excluding it, the opposite of what this story's Design Note and
    `test_claude_md_is_hybrid_not_also_generated_derived`'s docstring both assert. The
    classification is nevertheless correct, and the dispositive source went uncited: AD-63 —
    "`CLAUDE.md` and `AGENTS.md` receive it as a managed region (FR-117); Cursor, Gemini, and
    Copilot files are whole-file generated-derived" — names exactly the three whole-file
    adapters the manifest ships. Corrected the header comment, the test docstring, and the
    Design Note to rest the CLAUDE.md dedup on AD-63 and to state plainly that the PRD points
    both ways. Data unchanged.
  - `[medium]` `[patch]` Edge Case Hunter: no test asserted any `pin` VALUE — the one field
    that is the entire payload of a REFERENCED entry — while every other number in the file is
    pinned exactly (class counts, `never_write`, anchors, `applies_to` sets). The only guard was
    `assert entry.pin`. VERIFIED consequential: the immediately prior pass corrected
    `bmad-loop` from `>=0.8.1` to `>=0.9.0` as a HIGH-severity defect (the manifest had
    certified an environment in which `pyforge-marshal` itself cannot install), and the whole
    suite was green before that fix and would be green again after a silent revert. Added
    `test_referenced_pins_match_the_live_environment_exactly`, pinning all 16 id→pin pairs.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup):
    `test_class_behavior_transcribes_the_prd_classification_table_verbatim`'s docstring claims
    it guards "transcription drift", but `_PRD_TABLE` is a hand-copy authored in the same commit
    as `_CLASS_BEHAVIOR` and nothing reads `prd.md` — a PRD edit changes nothing and no test
    fails. VERIFIED the transcription itself is currently correct (all 15 cells match
    `prd.md`'s table after bold-stripping), so this is a claim-accuracy defect, not a data one.
    The test cannot be made to read the PRD: it is a planning artifact outside the wheel, so
    parsing it would fail every installed-package run. Rewrote the docstring to state the real
    scope — it pins `CLASS_BEHAVIOR` against isolated edits, in one direction only, and both
    literals must be hand-updated if the PRD's table is ever amended.
  - `[low]` `[patch]` Blind Hunter: `Artifact.__post_init__`'s mismatch message spoke Python
    member names (`HYBRID_MANAGED_REGION`) while the `expected is None` branch three lines above
    spoke the wire format (`'unclassified-deferred'`), addressing the same operator in two
    vocabularies. VERIFIED against the package's own stated convention, documented in
    `manifest.py`'s `Region.__post_init__`: "every neighbouring message in this module speaks
    the wire format the author actually writes." Switched both spellings to `.value` and updated
    the one test that matched on the message.
  - `[medium]` `[defer]` Edge Case Hunter: `**/planning-artifacts/**` and its
    implementation-artifacts twin never match the directory NODE itself — including
    `_bmad-output/planning-artifacts`, the exact path AD-61 names as its worked example.
    VERIFIED by execution in both matcher dialects. The 7 patterns are pinned verbatim by the
    Boundaries; the resolution is AD-61 matcher semantics. Appended to the ledger.
  - `[medium]` `[defer]` Blind Hunter + Edge Case Hunter (independent dup):
    `bmad-installed-skills` and `bmad-skill-forge` name no package anywhere (VERIFIED absent
    from `pixi.toml` and `recipes/`; the real package is `bmad-module-skill-forge`), so FR-95's
    id-keyed presence probe reports two permanent false missings. Unfixable in Surface — there
    is no package name to rename them to, and distinguishing installer-delivered entries needs a
    schema field. Appended to the ledger for S-11.5.
  - `[medium]` `[defer]` Edge Case Hunter + Blind Hunter (independent dup): `<top>` is the sole
    anchor for `model-ignores` and `model-badge` but matches zero lines in `.gitignore` and
    `README.md` (VERIFIED by execution), and AD-56 defines no sentinel semantics for it — so
    both regions take the EOF-append fallback and the README badge lands last. Anchors are
    contract-pinned. Appended to the ledger.
  - `[medium]` `[defer]` Blind Hunter (two findings merged): two further planning-artifact
    divergences beyond the already-recorded `CLAUDE.md` one — `.bmad-loop/policy.toml` ships
    `generated-derived` against four sources still saying COPIED-SEEDED, and `_bmad/skf/**`
    ships as a 7th never-write pattern the PRD's 5-row table and the epics' 6-pattern list do
    not carry (`epics.md:2243`'s stale `pixi >=0.76.2` is the same family). Needs a
    correct-course over PRD + epics. Appended to the ledger.
  - `[medium]` `[defer]` Edge Case Hunter: `specs-dir-legacy` is `applies_to: adopt` — every
    adopt — while the PRD scopes it to "`docs/specs/` **only when legacy**" and the entry's own
    rationale asserts that condition. `AppliesTo` has no conditional-existence member, so
    adopting a clean repo materialises the deprecated Tier-1 directory. Schema change, out of
    Surface. Appended to the ledger.
  - `[medium]` `[defer]` Edge Case Hunter: four model-written artifacts have no manifest entry
    (`.marshal/seed-state.yml`, `.marshal/.copier-answers.yml`, `.marshal/plan.json`,
    `_bmad-output/projects/*/.bmad-config.user.toml`) — two of them named by this story's own
    `model-ignores.gitignore.j2`. VERIFIED the PRD never mentions `.marshal/` at all, so the
    omission is inherited, and the entry roster + counts are contract-pinned. Appended to the
    ledger for S-9.5's coverage check.
  - `[medium]` `[defer]` Blind Hunter + Edge Case Hunter (independent dup): on a greenfield
    `init` into an empty directory none of the four hybrid host files exists and every region
    has a single anchor, so all 7 regions take AD-56's EOF-append path into files that are
    naked, heading-less bodies. AD-56 is scoped to "pre-existing files" and has no
    create-with-scaffold branch. Belongs to S-8.4. Appended to the ledger.
  - `[medium]` `[reject]` Blind Hunter + Edge Case Hunter: `dreams-readme` sits inside the
    `docs/dreams/*.md` never-write glob. Real and correctly reasoned, but this is verbatim the
    finding the FIRST follow-up pass deferred; it is already an open ledger entry. Re-deferring
    would duplicate it, and the orchestrator owns its status.
  - `[medium]` `[reject]` Blind Hunter: the AC's two never-write carve-outs are absent from the
    data. Already recorded three times over — the spec's own Never section, its "The never-write
    exemption gap is intentionally left open" Design Note, and Story 7.4's review, which
    assigned it to the fs-guard story. Not new information.
  - `[medium]` `[reject]` Edge Case Hunter: five `generated-derived` directory entries nest
    never-write globs and contradictory class contracts. Verbatim the finding the first
    follow-up pass deferred; already an open ledger entry.
  - `[low]` `[reject]` Blind Hunter + Edge Case Hunter: `AGENTS.md` and `CLAUDE.md` share one
    `tiers.md.j2` body, so CLAUDE.md-only content would be lost. Two errors. The sharing is
    contract-pinned ("backing exactly one source per AD-63") and is precisely AD-63's rule —
    "Adapter fan-out renders from **one contract document**… Prevents: four drifting copies of
    the tier table." And the stated failure is wrong: a managed region is a marker-delimited
    INSERTION, so pre-existing unmarked content is duplicated, not deleted — which is the
    already-deferred adopt-into-the-source-repo finding, not a new one.
  - `[low]` `[reject]` Blind Hunter + Edge Case Hunter: `readme-badge`'s "opt-in, off by
    default" is prose-only. Prior-pass rejection premise re-verified and still true and
    scope-based: `prd.md` says "opt-in; off by default", Story 7.4's schema has no opt-in
    concept, and the entry's own `rationale` states the limitation explicitly.
  - `[low]` `[reject]` Blind Hunter: `describe()` raises for the 3 `unclassified-deferred`
    entries, so FR-127 cannot use it for them. Prior-pass rejection premise re-verified: the
    Boundaries pin `CLASS_BEHAVIOR` as "keyed by the 5 product `ArtifactClass` members (not
    `unclassified-deferred`)", and FR-127's other outputs read straight off `ManifestEntry`.
  - `[low]` `[reject]` Blind Hunter: FR-118 packaging is asserted but the tests read the source
    tree. The reporter itself verified the built wheel does include `manifest.yaml` and all six
    `.j2` files, and `importlib.resources` is the correct idiom — the finding is a hypothetical
    about a future `exclude` rule.
  - `[low]` `[reject]` Blind Hunter: `pin` mixes conda match-spec and PEP 440 grammars, so "at
    least one of the 16 fails to parse." Refuted by the other reviewer's execution: all 16 parse
    under `packaging.specifiers.SpecifierSet`, including `>=3.7b_` (normalised to `3.7b0`) and
    the three `.dev0` floors.
  - `[low]` `[reject]` Blind Hunter + Edge Case Hunter: the `"n/a"` sentinel is a valid relative
    path and collapses 16 entries onto one key for FR-127's path lookup. The convention is
    contract-pinned ("`path: 'n/a'` for all (matches Story 7.4's own fixture convention)"), the
    prior pass already re-keyed the test's exclusion on class, and a path→entry index would
    reasonably skip non-materialised entries.
  - `[low]` `[reject]` Blind Hunter: `pixi-toml-tasks` defers the whole file though its
    rationale scopes to task blocks. The Boundaries write it exactly this way ("`pixi.toml`
    (task blocks)"), and the schema has no sub-file scoping to express it with.
  - `[low]` `[reject]` Edge Case Hunter: classifying `docs/specs/` `generated-derived`
    contradicts AD-59, whose own example names it. Overstated. AD-59 governs the legacy
    CONTENT ("never written to"), which `never_write`'s `docs/specs/*.md` pattern already
    protects; the entry is the directory skeleton, which the PRD's own derived table lists as
    such. The real residual — unconditional adopt — is deferred separately above.
  - `[low]` `[reject]` Edge Case Hunter: `Artifact`'s mismatch guard uses value equality, so it
    would degrade to a no-op if two `ClassBehavior`s were ever identical. Hypothetical: all five
    are distinct today (verified), and a duplicated behavior would itself be a transcription bug
    the verbatim test catches first.
  - `[low]` `[reject]` Edge Case Hunter: a region name containing a dot, or a non-`.j2` file
    under `templates/files/`, would confuse the orphan-body check's `split(".", 1)[0]`. No such
    region or file exists, and the naming convention is this story's own.
  - `[low]` `[reject]` Edge Case Hunter: the two symlink entries carry no trailing slash while
    the three directory skeletons do. They are symlinks, not directories; the distinction is
    correct, not an inconsistency.

### 2026-08-11 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 2, medium 5, low 4)
- defer: 3: (high 0, medium 3, low 0)
- reject: 4: (high 0, medium 0, low 4)
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter: the `bmad-loop` REFERENCED pin was `>=0.8.1`, and its
    rationale asserted as fact that no load-bearing feature justified a bump. VERIFIED false
    against two live sources: `pixi.toml:1046` is `bmad-loop = ">=0.9.0"`, and
    `pyforge-marshal/pyproject.toml:33` declares `"bmad-loop>=0.9.0,<0.10"` as a HARD runtime
    dependency — so the manifest certified an environment in which `pyforge-marshal`, the tool
    performing FR-95's floor check, cannot install at all. This also violated the Boundaries'
    own rule ("`pin` values come from the live `pixi.toml` where it and the PRD disagree"), the
    same rule already applied to `pixi`, `tmux` and `bmad-dashboard`. Corrected to `>=0.9.0`
    (the live pixi.toml value; the `<0.10` cap is pyproject's, not the model's) and the
    rationale rewritten to name the real load-bearing requirement.
  - `[high]` `[patch]` Blind Hunter: the REFERENCED entry id `bmad-test-architecture-enterprise`
    is not the package's name. VERIFIED against `pixi.toml:1047` —
    `bmad-method-test-architecture-enterprise = ">=1.19.1"` — and against the companion doc,
    which spells it in full. Since Story 7.4's schema has no `package` field, `id` is the ONLY
    handle FR-95's presence/floor check has on a referenced entry, so the abbreviation makes
    FR-95 emit a missing-dependency finding for a package that is installed and at floor. Every
    other package-backed id in the manifest matches its pixi.toml key exactly (including the
    structurally identical `bmad-method-wds-expansion`), confirming a transcription slip rather
    than a naming convention. Renamed. The Boundaries' prose shorthand for this entry is
    unchanged in meaning and the REFERENCED count stays 16.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): the manifest's own
    header comment still read "6 copied-seeded, 9 generated-derived" — the one site the prior
    pass's `bmad-loop-policy` reclassification missed, having corrected the section headers, the
    AC bullet and both test files. VERIFIED by loading: `Counter` reports copied-seeded 5,
    generated-derived 10. No test reads YAML comments, so it could not rot loudly; AD-55's
    stated value is that the manifest is reviewable as a diff, and its only summary was wrong.
    Corrected.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): the `Artifact`
    pairing guard the PRIOR pass added had a null hole and no type checks.
    `CLASS_BEHAVIOR.get(UNCLASSIFIED_DEFERRED)` returns `None`, and the next line
    `if self.behavior == expected: return` short-circuits on `None == None` — so
    `Artifact(entry=<unclassified-deferred>, behavior=None)` constructed cleanly, producing
    exactly the mismatched pairing the guard exists to prevent and deferring the failure to an
    `AttributeError` in a future `explain`. Separately, neither field was isinstance-checked, so
    a non-`ManifestEntry` raised `AttributeError` from the class lookup rather than the
    `ValueError` this module's own docstring promises — while `Manifest.__post_init__`, which
    that docstring cites as the precedent, does isinstance-check its members. Added both type
    guards and an explicit `expected is None` branch, all raising `ValueError` naming the id,
    plus 3 tests.
  - `[medium]` `[patch]` Blind Hunter: the `.gitignore` model region omitted `.marshal/plan.json`.
    VERIFIED against binding architecture, not this repo's live file: AD-57 states verbatim
    "Plans are written to `.marshal/plan.json` and gitignored by the model's own `.gitignore`
    region," and `epics.md:1905` restates it as an AC. `adopt` is dry-run by default (FR-79) and
    writes the plan on its first invocation, so every adopting repo got an untracked file on the
    tool's own happy path. Added — naming the file, not `.marshal/`, because AD-52 makes
    `.marshal/seed-state.yml` git-tracked. (This re-tests the prior pass's `[reject]` on this
    same file, which held FR-76 to be the binding enumeration: FR-76 is necessary but not
    sufficient, since AD-57 adds a requirement FR-76 does not list. The prior reject's own
    subject, `_bmad/config.user.toml`, remains correctly rejected — it is not a model artifact.)
  - `[medium]` `[patch]` Blind Hunter: the same region omitted `.bmad-loop/policy.toml`, which
    THIS story's prior pass reclassified `generated-derived` ("rendered whole ... on every
    `marshal config --write-harness-policy` run"). VERIFIED against `.gitignore:772-777`, whose
    own comment documents the path as derived, never hand-edited, never tracked. Shipping a
    region that materializes the file without ignoring it leaves every adopting repo permanently
    dirty — the exact failure this template's own lines 6-11 were written to prevent for the
    implementation-artifacts symlink, and one that stops `bmad-loop run` from starting. Added;
    unfinished follow-through from the prior pass's own reclassification.
  - `[medium]` `[patch]` Edge Case Hunter: no test asserted region **anchors**, only region
    names. VERIFIED this is silently non-fatal by design: AD-56 says "insertion goes after the
    first match; if none matches, the region is **appended at end of file**", and
    `Region.__post_init__` validates only non-blankness — so a typo'd or stale anchor relocates
    a managed span to EOF with nothing failing, even though the Boundaries name each anchor
    exactly. Added `test_every_hybrid_region_declares_its_exact_anchor`, pinning all 7
    (entry id, region name, anchor) triples.
  - `[low]` `[patch]` Edge Case Hunter: no test referenced `applies_to` at all, though this
    story's own Design Notes make `applies_to: init` the sole discriminator a future fs-guard
    story uses to exempt `starter-dream`/`specs-readme` from the never-write globs their paths
    sit inside. Flipping either to `both` passed the whole suite. Added
    `test_applies_to_scoping_matches_the_spec`, pinning the init-only and adopt-only id sets.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): the body-file check ran
    one direction only (region → file), so a renamed or removed region would leave an orphaned
    `.j2` shipping in the wheel with a green suite — and the convention has no schema field
    behind it (Design Notes), making the tests its only specification. Added
    `test_every_body_file_is_claimed_by_a_declared_region` asserting set equality both ways.
  - `[low]` `[patch]` Edge Case Hunter: `test_no_two_materialized_entries_share_a_rendered_path`
    excluded the sentinel by the STRING `"n/a"` rather than by class, so a materialized entry
    authored with `path: "n/a"` would be dropped from the duplicate-path check, never reach the
    referenced-only assertion (which iterates REFERENCED entries), pass `_require_text`, and
    arrive at the future write guard as a literal relative path named `n/a`. Re-keyed the
    exclusion on `artifact_class is not REFERENCED` and added the converse test.
  - `[low]` `[patch]` Blind Hunter: `CLASS_BEHAVIOR` was a plain mutable module-level dict in a
    module whose every other value is `@dataclass(frozen=True)` and whose docstring justifies
    that as "immutable value objects". VERIFIED by execution that a rebound entry corrupts
    `describe()` process-wide AND still passes `Artifact.__post_init__`, because the guard
    validates against the same table — the corruption is undetectable from inside the module.
    Wrapped in `MappingProxyType` (public name and all existing reads unchanged), plus a test.
  - `[medium]` `[defer]` Edge Case Hunter (findings 1+2, merged — one gap from two sides): five
    `generated-derived` DIRECTORY entries are ancestors of never-write globs and of other
    entries with contradictory class contracts (`dreams-dir` ⊃ `docs/dreams/*.md` +
    `dreams-readme`/`starter-dream`; `project-subtree` ⊃ both artifact globs +
    `project-config`/`specs-readme`; `specs-dir-legacy` ⊃ `docs/specs/*.md`; both symlink
    entries at the root of the same globs). VERIFIED by computing ancestry over the loaded
    manifest. The schema has no node-kind field distinguishing "mkdir if missing" from
    "recompute this subtree", so GENERATED_DERIVED's "recomputed every run / overwritten on next
    run" reads as an instruction to rewrite a Tier-0/Tier-2 subtree the model forbids writing.
    Same family as the already-recorded `dreams-readme` collision and the same reason for
    deferring: it needs a schema/orchestrator decision outside this story's Surface. Appended to
    `implementation-artifacts/deferred-work.md`.
  - `[medium]` `[defer]` Blind Hunter: the PRD's GENERATED-DERIVED table and `epics.md:1596`
    ("the four adapter files") still count `CLAUDE.md` as a whole-file derived artifact, while
    the manifest ships three plus one HYBRID `claude-md`. VERIFIED both sources. The dedup is
    correct on the merits and is test-pinned here, but AD-55 makes the manifest the product's
    contract while the PRD/epics remain the input every later story reads, and nothing checks
    epics↔manifest agreement — so a later story or correct-course pass re-derives four. Amending
    two planning artifacts is outside this story's Surface. Appended to the ledger.
  - `[medium]` `[defer]` Blind Hunter: adopting the model into the repo it was extracted from
    duplicates content. VERIFIED byte-identity (`diff` against `AGENTS.md` lines 65-78 / 31-47 /
    51-61 → IDENTICAL) and anchor prefix-matching; S-8.4's idempotence check keys on markers,
    which the live file lacks, so `adopt` on `local-recipes` plans a second marker-wrapped copy
    of each region — and a second tier table into `CLAUDE.md`'s existing tier section. The
    byte-identity is REQUIRED by this story's AC, so the template is not the defect; the gap is
    that AD-56/S-8.4 define no detection for pre-existing unmarked content (FR-80's
    `present-legacy` is its natural home). SC-10 is the test that hits it. Appended to the
    ledger so S-8.4 does not inherit it as a surprise.
  - `[low]` `[reject]` Blind Hunter: the 5 triage-open REFERENCED entries (plus
    `bmad-installed-skills`/`bmad-skill-forge`) ship floors the companion doc calls "unset".
    VERIFIED this is schema-forced, not invented: `ManifestEntry.__post_init__` requires a
    non-empty `pin` on every `referenced` entry, the values are the live `pixi.toml` constraints,
    each entry's `rationale` carries the triage-open caveat, and the Spec Change Log already
    records the deviation. Both alternatives the finding proposes (reclassify as
    `unclassified-deferred`, or drop the entries) would break the Boundaries' pinned
    "REFERENCED: 16 entries" and re-open the coverage gap the 2026-07-31 re-audit closed.
  - `[low]` `[reject]` Blind Hunter: `describe()` has no data path for the 3
    `unclassified-deferred` entries, so FR-127's `explain` cannot use this layer for them.
    VERIFIED contract-pinned: the Boundaries specify `CLASS_BEHAVIOR` is "keyed by the 5 product
    `ArtifactClass` members (not `unclassified-deferred`)", the module docstring states the
    reasoning, and FR-127's other two outputs (`class`, `rationale`) read straight off
    `ManifestEntry` without `describe()`. Changing it would contradict the intent contract.
  - `[low]` `[reject]` Blind Hunter: `model-ignores.gitignore.j2` groups
    `_bmad-output/projects/*/.bmad-config.user.toml` under a symlink-related comment header that
    does not describe it. VERIFIED as a faithful transcription of the live `.gitignore:747-751`,
    which this story's Code Map mandates; FR-76 lists the rule and assigns it no grouping.
    A comment's grouping carries no behavior — gitignore rules for distinct paths are
    order-independent. Cosmetic.
  - `[low]` `[reject]` Blind Hunter: `test_no_two_materialized_entries_share_a_rendered_path`
    says "rendered" but compares un-rendered strings, so `{{ slug }}` vs `{{slug}}` aliases would
    read as distinct. VERIFIED the non-rendering is an explicit Never bullet and the `n/a`
    exclusion is documented in the Spec Change Log; no such alias exists in the manifest, and the
    real hole the finding gestures at (a non-referenced entry escaping the check) is closed by
    the class-keyed exclusion patched above. The residual cross-entry path-containment question
    is the deferred item, not a defect in this test.

### 2026-08-11 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 2, medium 3, low 2)
- defer: 1: (high 0, medium 1, low 0)
- reject: 6: (high 0, medium 0, low 6)
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter: `.bmad-loop/policy.toml` (id `bmad-loop-policy`) was
    classified `copied-seeded` ("materialized once, then repo-owned forever... expected and fine
    to hand-edit"). VERIFIED against this repo's own shipped code: `.gitignore:777`'s own comment
    and `adapters/harness_bmadloop.py` (Story 1.10, AD-12/AD-35) both document this exact path as
    rendered whole from `EffectivePolicy` on every `marshal config --write-harness-policy` run,
    never hand-edited, never tracked -- the opposite contract. Reclassified `generated-derived`;
    counts corrected copied-seeded 6->5, generated-derived 9->10 in the manifest, the outside-
    intent-contract AC bullet, and both test files' `EXPECTED_CLASS_COUNTS`.
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): the 4 shared region
    body files (`tiers`, `portability-contract`, `dream-first-workflow`, `bmad-multiproject`)
    each duplicated their own anchor's heading line. VERIFIED: AD-56 inserts a region's body
    AFTER the anchor line, and the anchor IS the host file's pre-existing heading -- so
    `tiers.md.j2`'s leading `## The tiers (do not cross them)` line, spliced into CLAUDE.md right
    after CLAUDE.md's own (different-level, different-wording) `### Spec-driven,
    framework-neutral layout` anchor, produces a broken heading hierarchy; the same body spliced
    into AGENTS.md (whose anchor IS that exact heading text) produces a literal duplicate. Fixed
    by stripping the leading heading (+ its blank line) from all 4 files; `model-badge` is
    unaffected (anchor is `<top>`, not a heading match). Recorded as a new Design Note.
  - `[medium]` `[patch]` Blind Hunter: `test_class_behavior_transcribes_the_prd_classification_
    table_verbatim` spot-checked only 2 of 5 classes' fields (4 of 15), and missed a real
    transcription error in the 3rd (see next finding). Expanded to a parametrized, table-driven
    check of all 5 classes x 3 columns.
  - `[low]` `[patch]` Blind Hunter: `ClassBehavior[COPIED_MANAGED].hand_edit_behavior` dropped
    the backticks around `` `--force` `` present in the PRD/architecture source text ("`check`
    reports; `update` refuses without --force" vs. the source's "...without `` `--force` ``").
    VERIFIED by diff against the PRD's own table row. Restored the backticks; now caught by the
    expanded verbatim test above.
  - `[medium]` `[patch]` Edge Case Hunter: `Artifact` (a plain frozen dataclass) could be
    constructed directly with a `behavior` that does not match `entry.artifact_class`, silently
    producing a mismatched pairing `describe()` itself would never produce. Matches the exact
    hazard Story 7.4's own review hardened `Manifest`/`ManifestEntry` against (validate in
    `__post_init__`, not only in a bypassable factory). Added a `__post_init__` check raising
    `ValueError` naming both the entry id and the mismatched class, plus a test.
  - `[medium]` `[patch]` Edge Case Hunter: the placeholder-rationale check
    (`test_unclassified_deferred_entries_have_real_non_generic_rationale`) covered only the 3
    `unclassified-deferred` entries, not all 43 -- a placeholder `rationale` on any other class
    would pass undetected even though `rationale` is required on every entry. Added
    `test_no_entry_anywhere_has_a_placeholder_rationale` covering all 43.
  - `[low]` `[patch]` Blind Hunter: the Spec Change Log's "judgment calls" list named `pixi` and
    `tmux` as cases where a live-`pixi.toml` pin was used over the stale companion-doc value, but
    `bmad-dashboard` (`>=1.2.2.dev0` live vs. the companion doc's `>=1.2.2`) got the identical
    treatment without being listed. Added it to the Spec Change Log for completeness.
  - `[medium]` `[defer]` Edge Case Hunter: `dreams-readme` (`docs/dreams/README.md`,
    `copied-managed`, `applies_to: both`) is a third, previously undocumented artifact whose path
    collides with the `docs/dreams/*.md` never-write pattern -- beyond the two carve-outs
    (`starter-dream`, `specs-readme`) already named in Boundaries/Never. VERIFIED against the
    PRD's own never-write table, which names only "the one seed at init" as the exception, not
    `README.md`; this is a pre-existing PRD/architecture-level gap, not introduced by this
    story's implementation, and unlike the two init-only carve-outs it also affects `update`
    (not just `init`), since the entry is `applies_to: both`. Appended to
    `implementation-artifacts/deferred-work.md` (not fixed here: same "needs the fs-guard/
    orchestrator story's exemption mechanism" reasoning as the two already-recorded carve-outs).
  - `[low]` `[reject]` Blind Hunter: `model-ignores.gitignore.j2` omits `_bmad/config.user.toml`
    (present in this repo's live, accumulated `.gitignore`). VERIFIED against the actual binding
    source: FR-76 enumerates the `.gitignore` model region's contents precisely
    (`implementation-artifacts/`, the two symlinks, `_bmad/custom/.active-project`,
    `.bmad-loop/runs/`+`cache/`, `_bmad-output/projects/*/.bmad-config.user.toml`) and does NOT
    include `_bmad/config.user.toml` -- the template matches FR-76 exactly; the finding compared
    against the wrong ground truth (this repo's full, independently-accumulated `.gitignore`
    rather than the model region FR-76 actually defines).
  - `[low]` `[reject]` Blind Hunter: the `copier` REFERENCED entry states a pin as settled fact
    when AD-64 calls Copier's adoption conditional ("if S-7.6's spike adopts it"). VERIFIED: AD-64
    is about WHEN the `pixi.toml` dependency line is added (a packaging-story sequencing detail,
    S-12.1), not whether the operating MODEL commits to Copier -- FR-120/AD-52 and the PRD's own
    unconditional REFERENCED table entry all already treat Copier as the settled template engine.
    Matches upstream design; not a defect this story introduced.
  - `[low]` `[reject]` Blind Hunter: `readme-badge`'s `applies_to: both` "contradicts" its own
    "opt-in, off by default" rationale, since no schema field encodes opt-in status. VERIFIED the
    entry's own `rationale` text already states this limitation explicitly ("no schema field for
    that exists yet, so this is descriptive only, not enforced here") -- an honest, self-
    documented limitation is not a silent contradiction, and Story 7.4's schema genuinely has no
    opt-in concept to add without exceeding this story's Surface.
  - `[low]` `[reject]` Blind Hunter: REFERENCED conflates "not materialized" with "materialized
    but installer-owned" (`bmad-installed-skills`, `bmad-skill-forge`, `path: "n/a"` for
    directories that exist on disk). VERIFIED this is the PRD/companion doc's OWN classification,
    reproduced faithfully (both explicitly REFERENCED "installed BMAD skills... installer-owned;
    regenerated by `bmad-method install`"); not an error this story introduced.
  - `[low]` `[reject]` Blind Hunter: individual detector scripts (not just the dispatcher) have no
    manifest entry, reproducing "a hardcoded list omits the newest thing." VERIFIED this restates
    the exact problem the `detector-registry` entry's discovery-based rationale (pointing at
    `scripts/detectors.py` rather than enumerating files) already exists to solve -- adding
    per-script entries would reintroduce the defect the design deliberately avoids.
  - `[low]` `[reject]` Blind Hunter: no data-level cross-reference ties `bmad-installed-skills`'s
    rationale (naming `_bmad/bmm/**`+`_bmad/core/**`) to the matching `never_write` patterns.
    VERIFIED this asks for a schema capability (rationale-to-pattern linking) that Story 7.4's
    schema does not have and no FR/AD names -- out of this story's Surface, not a defect.

## Design Notes

- **Region body files carry no heading of their own.** AD-56: insertion goes AFTER the anchor
  line, and the anchor IS the host file's own pre-existing heading (`## The tiers` in AGENTS.md,
  `### Spec-driven, framework-neutral layout` in CLAUDE.md — deliberately different wording and
  level). The first-pass bodies each duplicated their own heading line, which review verified
  produces two defects: a literal duplicate heading in AGENTS.md (same text as its anchor,
  immediately following it) and a broken outline in CLAUDE.md (the shared `tiers` body's H2
  spliced in right after CLAUDE.md's H3 anchor). All four shared bodies
  (`tiers`/`portability-contract`/`dream-first-workflow`/`bmad-multiproject`) now start directly
  with content; the heading is supplied by whichever host file's own anchor line it attaches
  after. `model-badge` is unaffected — its anchor is `<top>`, not a heading match.
- **`bmad-multiproject.md.j2` deliberately excludes two live-incident narrative paragraphs.**
  CLAUDE.md's "Multi-Project Pattern" section carries two dated incident anecdotes (the
  2026-07-14 marker/symlink near-miss, the 2026-07-25 11-Spec fan-out drift) that are
  local-recipes' own history, not model-generic rule content an adopting repo would want
  narrated back to it. The mechanism/rule content those paragraphs illustrate (never call
  `bmad-switch` from a parallel agent; verify placement after writing) is fully preserved in the
  surrounding bullets. The "(HARD, since 2026-07-25)" qualifier on the PARALLEL AGENTS rule
  IS restored (review finding) — it is a severity marker, not an anecdote.
- **Two PRD table duplications, resolved as one entry each.** The PRD's classification tables
  are additive prose written before the COPIED-MANAGED/HYBRID split was fully drawn: `.gitignore`
  appears in both because its COPIED-MANAGED row literally says "delivered as a managed region,"
  and `CLAUDE.md` appears in both because the GENERATED-DERIVED section's summary sentence names
  only three files. **Corrected by the second follow-up review:** that sentence does not settle
  it. Quoted in full it reads "The **four** agent-adapter files are the clearest case for
  DERIVED: all three inspected (`GEMINI.md`, `.cursor/rules/specs.mdc`,
  `.github/copilot-instructions.md`) restate the same tier table" — it *counts* CLAUDE.md among
  the four while naming three, so the PRD points both ways and cannot be the citation. The
  dispositive source is **AD-63**: "`CLAUDE.md` and `AGENTS.md` receive it as a managed region
  (FR-117); Cursor, Gemini, and Copilot files are whole-file generated-derived" — exactly the
  three whole-file adapters this manifest ships. The `.gitignore` half stands on the PRD as
  originally written. This is the exact ambiguity Story 7.4's review flagged as genuinely open
  and assigned to whoever authors this manifest — resolved here, not deferred further, on
  AD-63's authority.
- **Why the REFERENCED list pulls from the audited companion doc, not just the PRD's own inline
  section.** The epics AC cites "PRD § *The V1 manifest*," but that inline section was never
  updated with the companion `extraction-manifest.md`'s 2026-07-31 re-audit (10 additional
  REFERENCED rows, verified against live `pixi.toml` — `bmad-builder`, TEA, CIS, Skill Forge,
  `bmad-dashboard`, and 5 triage-open packages all resolve in the live environment today).
  Shipping only the PRD's original 6 would recreate the coverage gap the audit already found
  and fixed once. Terminology is normalized to the 2026-08-10 rename throughout (`marshal seed
  explain`/`check`/`update`, `marshal-seed:*` markers) — the companion doc still says `genesis`.
- **The never-write exemption gap is intentionally left open.** Encoding it would mean adding a
  field to `ManifestEntry` or `Manifest` in `manifest.py`, which this story's Surface does not
  touch (`manifest.yaml` + `artifact.py` only). The two affected entries (`starter-dream`,
  `specs-readme`) are both `applies_to: init`, which is exactly the signal a future
  orchestrator/fs-wiring story needs to compute an effective `NeverWrite` set that excludes
  them — recorded here so that story does not have to rediscover it.
- **`templates/files/<region-name>.md.j2` is a new convention, not a schema field.**
  `Region` (Story 7.4) carries only `name`/`anchor` — no body reference — so the mapping from a
  region name to its body file is by naming convention, established here because no prior story
  defined one and the epics AC requires real bodies to exist now.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expect all tests pass including
  the two new files, with no regressions in the existing `test_seed_model_manifest.py` suite
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` -- expect **194**
  findings total: the pre-existing **192**-finding baseline plus exactly 2 new `TRY004`
  (`type-check-without-type-error`) from the follow-up review's `Artifact.__post_init__` type
  guards. (The second follow-up review corrected these numbers: this section previously named
  194 as the *pre-existing* baseline, which read as an expected total of 196. Measured both
  ways -- the full package reports 194, and re-running with this story's three new `.py` files
  excluded reports 192.) Deliberate and unsuppressed: `TRY004` is an accepted, never-`noqa`'d baseline pattern
  in this package (34 occurrences, 7 of them in `seed/model/manifest.py` itself), because the
  package's documented convention is a `ValueError` naming the offending id rather than the
  `TypeError` the rule prefers. The follow-up review supersedes this section's original
  "adds no `isinstance`-guarded raises" note, which described the pre-review state.
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-marshal` -- expect no new
  findings beyond the pre-existing baseline
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- expect all contracts pass (this story adds no new imports across `pyforge.marshal.seed`'s
  boundaries)

**Manual checks (if no CLI):**
- Diff `seed/templates/files/tiers.md.j2`, `portability-contract.md.j2`,
  `dream-first-workflow.md.j2` against `AGENTS.md`'s live "The tiers", "Portability contract",
  and "Dream-first workflow" sections to confirm faithful, install-target-neutral transcription
  (per the epics AC's explicit wording).



## Auto Run Result

Status: done (second follow-up review pass, no loopback — 0 intent_gap, 0 bad_spec)

**Implemented change (this pass).** Review-only pass over the story's full diff since
`4cf8ae53`. The shipped model DATA is unchanged: all 43 manifest entries, the 7-pattern
`never_write` list, and all six region body files are byte-identical to the reviewed state.
Five patches landed — two harden real holes (an immutability guard that did not guard, and the
one manifest field no test asserted), three correct claims the code makes about its own sources.

**Files changed**
- `seed/model/artifact.py` — the class-behavior table is now built inline into
  `MappingProxyType({...})` with no mutable module-level alias behind it (the prior pass's proxy
  was a read-only *view* over a still-reachable `_CLASS_BEHAVIOR`, so the corruption its own
  comment described stayed reachable); `Artifact.__post_init__`'s mismatch message switched from
  Python member names to the wire format its neighbouring branch already used.
- `seed/templates/manifest.yaml` — header comment only: the two dedups now cite their real,
  separate sources (`.gitignore` on its PRD COPIED-MANAGED row; `CLAUDE.md` on AD-63, because
  the PRD sentence previously cited counts CLAUDE.md among "the four" rather than excluding it).
- `tests/unit/test_seed_templates_manifest.py` — new
  `test_referenced_pins_match_the_live_environment_exactly` pinning all 16 id→pin pairs;
  corrected `test_claude_md_is_hybrid_not_also_generated_derived`'s docstring.
- `tests/unit/test_seed_model_artifact.py` — new
  `test_no_mutable_module_level_alias_backs_the_read_only_table`; the transcription test's
  docstring now states its real (one-directional) scope instead of claiming PRD-drift detection;
  updated the message-match regex for the wire-format change.
- `implementation-artifacts/deferred-work.md` — 7 new entries appended (new only; no existing
  entry read back, modified, or re-opened).

**Review findings breakdown.** 25 findings after dedup across two independent reviewers.
Patches applied 5 (medium 3, low 2). Deferred 7 (all medium): the `**/planning-artifacts/**`
directory-node matching gap vs AD-61; two REFERENCED ids that name no package (FR-95 probe);
`<top>` as an unimplemented anchor sentinel; two further PRD/epics-vs-manifest divergences
(`.bmad-loop/policy.toml` class, the 7th never-write pattern); `specs-dir-legacy`'s
unconditional adopt vs the PRD's "only when legacy"; four unclassified `.marshal/*` +
`.bmad-config.user.toml` artifacts vs S-9.5's coverage check; and greenfield `init` having no
host file for any of the 7 regions. Rejected 13 (medium 3, low 10) — the 3 medium rejects are
real findings already recorded as open ledger entries by the previous pass (re-deferring would
duplicate them); the rest are contract-pinned decisions with re-verified premises, one claim
refuted by the other reviewer's execution (all 16 pins parse under `SpecifierSet`), and one
whose stated failure mode was wrong (a managed region duplicates unmarked content, it does not
delete it).

**Verification performed** (all four spec commands, in the worktree)
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — **3487 passed, 9 deselected**,
  including the 2 new tests. No regressions.
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` — **194** findings,
  matching the corrected expectation (192 pre-existing + the 2 documented `TRY004`). Measured
  the baseline directly by re-running with this story's three new `.py` files excluded → 192.
  This pass added no new findings.
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-marshal` — 590 errors, all of
  the pre-existing `reportMissingImports` class (pyright runs in `local-recipes`, where
  `pyforge-marshal` is not installed). `seed/model/artifact.py` contributes **zero**; the only
  lines naming this story's files are 3 unresolved-import errors in the two test modules, same
  as every other test module in the package.
- `pixi run --frozen -e pyforge-marshal lint-imports …` — **3 contracts kept, 0 broken.**

**Residual risks.** All material risk now sits in the 7 deferred items, each of which is a
consumer-side contract the shipped data cannot express under Story 7.4's schema. Two are
load-bearing for stories already in flight: `<top>`'s undefined semantics and the missing
greenfield host-file branch both land on S-8.4's insertion work, and the `.marshal/*` coverage
gap lands on S-9.5. The `**/planning-artifacts/**` directory-node gap is the one with a safety
consequence — AD-61's guard, built as specified from these patterns, would not stop a
directory-level operation on the Tier-2 tree. Within this story's own Surface no residual risk
is known: the data is unchanged and every named number in it (counts, `never_write`, anchors,
`applies_to` sets, and now pins) is test-pinned exactly.
