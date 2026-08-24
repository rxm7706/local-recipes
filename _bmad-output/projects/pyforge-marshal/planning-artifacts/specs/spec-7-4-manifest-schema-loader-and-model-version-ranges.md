---
title: 'Story 7.4: Manifest schema, loader, and model-version ranges'
type: 'feature'
created: '2026-08-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
baseline_revision: 'f2f4b7692e64c31371597e5c563845cb59df33c7'
final_revision: 'f7b2acbd3a82680bc67832b7d366bd0697b4e85d'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md'
  - '{project-root}/_bmad-output/planning-artifacts/specs/spec-pyforge-marshal/extraction-manifest.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** The seed installer's operating model must be declared as data, never as engine
code branches (AD-55, A-02, NFR-M1), but no code yet parses, validates, or version-scopes
`templates/manifest.yaml` — every later story (7.5's real manifest, 7.3's write guard, later
detect/plan/migrate work) needs a trustworthy loader and a real model-semver comparator to key
`since`/`until` bounds and future migrations against.

**Approach:** Add `seed/model/manifest.py` (dataclasses + `load_manifest()` enforcing every
AC-listed schema rule, raising `ManifestError` at load time) and `seed/model/version.py` (a
self-contained SemVer 2.0.0 parser/comparator with full pre-release-ordering precedence),
mirroring `core/model.py`'s existing `@dataclass(frozen=True)` + `__post_init__` idiom.

## Boundaries & Constraints

**Always:**
- `manifest.py` defines `ArtifactClass` (StrEnum, 6 members: `referenced`, `copied-managed`,
  `copied-seeded`, `generated-derived`, `hybrid-managed-region`, `unclassified-deferred`),
  `AppliesTo` (StrEnum: `init`/`adopt`/`both`), `Region` (frozen dataclass: `name: str`,
  `anchor: tuple[str, ...]`, non-empty), `ManifestEntry` (frozen dataclass with the AC's
  fields), and `Manifest` (frozen dataclass: `model_version`, `never_write`, `entries`) —
  `@dataclass(frozen=True)` + `__post_init__` validation raising `ValueError`, same idiom as
  `core/model.py`'s `Finding`/`Envelope`. No pydantic, no runtime `jsonschema` (no precedent
  for that pattern in this package; `schemas/*.json` is for cross-process contracts, not
  internal loading).
- `load_manifest(path: Path) -> Manifest` reads one YAML document (top-level keys:
  `model_version`, `never_write`, `artifacts` — a list, each entry an explicit `id:` field).
  Raises `ManifestError` (new, local `class ManifestError(Exception)`) naming the offending
  id/field for: duplicate ids, an unrecognized `class`, a `hybrid-managed-region` entry with
  zero `regions`, any missing required field (`id`/`class`/`path`/`applies_to`/`rationale`
  always; `pin` for `referenced`; `format` + non-empty `regions` for
  `hybrid-managed-region`), an unparseable `since`/`until`/`model_version` string, and an
  `until <= since` inversion.
- After validation, filter `entries` to those applicable at the manifest's own
  `model_version`: keep an entry iff (`since is None or since <= model_version`) and
  (`until is None or model_version < until`) — half-open, so an entry is retired starting
  exactly at `until`.
- `version.py` defines `ModelVersion` (frozen dataclass: major/minor/patch/prerelease
  tuple/build tuple), `ModelVersion.parse(text)` implementing the full SemVer 2.0.0 grammar,
  ordering via `functools.total_ordering` implementing SemVer 2.0.0 precedence exactly
  (numeric-vs-alphanumeric pre-release identifier rules; a pre-release orders below its
  release; build metadata never affects ordering), `InvalidVersionError(ValueError)` on a
  malformed string, and `in_range(version, since, until)` implementing the half-open check.
- `pin` (referenced) and `format` (hybrid) are validated only as non-empty strings — not
  parsed as `ModelVersion`. Real pins (e.g. tmux `>=3.7b`) aren't valid SemVer, and
  `format`'s marker vocabulary belongs to the not-yet-built `regions/markers.py`.
- `path` is validated only as a non-empty string — this story does not render its Jinja
  templating (that needs a concrete repo slug, unavailable at manifest-load time; the lean
  `pyforge-marshal` env has no `jinja2` dependency and this story adds none).
- `legacy_of`, when present, is validated only as a non-empty string — no referential check
  against other entries' ids (not named in the AC).

**Block If:** none — schema, error conditions, and SemVer grammar all resolve from
architecture (AD-55/AD-56/AD-59/AD-61, A-02/A-05) plus the epics AC without human input.

**Never:**
- No production `templates/manifest.yaml` content — Story 7.5 authors it; tests here use
  inline/fixture YAML only, and `seed/templates/` stays untouched.
- No `seed/model/artifact.py` (Story 7.5's surface) — `ArtifactClass` here is only the
  minimal StrEnum this story's own validation needs, not a richer `Artifact` object.
- No adoption of Story 7.2's not-yet-built exit-code taxonomy — `ManifestError` is a local,
  minimal exception; wiring it onto the shared taxonomy is later-story work.
- No `never_write` enforcement (path matching, symlink resolution) — that's Story 7.3's `fs`
  guard; this story only parses and exposes the raw path-pattern list.
- No new dependency — SemVer parsing is hand-rolled; no `packaging`, no `jinja2`, no runtime
  `jsonschema` validation path.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid manifest, all six classes | One valid entry per class incl. `unclassified-deferred` | `Manifest` returned, every entry typed and populated | No error expected |
| Duplicate id | Two entries share `id: foo` | -- | `ManifestError` naming `foo` |
| Unknown class | `class: bogus-class` | -- | `ManifestError` naming id + value |
| Hybrid missing regions | `class: hybrid-managed-region`, no/empty `regions` | -- | `ManifestError` naming id |
| Referenced missing pin | `class: referenced`, no `pin` | -- | `ManifestError` naming id |
| Entry retired by `until` | entry `until: "1.0.0"`, manifest `model_version: "1.0.0"` | entry excluded from `Manifest.entries` | No error expected |
| Entry kept by `since` | entry `since: "0.9.0"`, no `until`, `model_version: "1.0.0"` | entry included | No error expected |
| Malformed version string | `model_version: "not-a-version"` | -- | `ManifestError` wrapping `InvalidVersionError` |
| SemVer pre-release ordering | `1.0.0-alpha` vs `1.0.0-alpha.1` vs `1.0.0-beta` vs `1.0.0` | strictly increasing per SemVer 2.0.0 precedence | No error expected |
| Build metadata ignored | `1.0.0+build1` vs `1.0.0+build2` | equal | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/model/version.py` -- NEW:
  `ModelVersion` (frozen dataclass, `@total_ordering`), `InvalidVersionError`, `in_range()`.
  No new dependency -- hand-rolled SemVer 2.0.0 grammar + precedence. `__post_init__`
  validates identifiers against the grammar (not just as `str`), so the ordering relation
  stays total for every constructible value; `__str__` round-trips back to a parseable string.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/model/manifest.py` -- NEW:
  `ArtifactClass`, `AppliesTo`, `Region`, `ManifestEntry`, `Manifest`, `ManifestError`,
  `load_manifest()`. Two-layer validation: the dataclasses' own `__post_init__` (raising
  `ValueError`) does the real shape checking, same idiom as `core/model.py`; `load_manifest`
  extracts raw YAML fields and re-raises any `ValueError` as `ManifestError`, prefixed with
  the offending id (or `"artifacts[N]"` / `"manifest"` for a pre-id or top-level failure).
  Parsing goes through `_StrictLoader` (a `SafeLoader` subclass rejecting repeated AUTHORED
  mapping keys -- ONE YAML merge key's inherited pairs are exempt, since an explicit override
  is the idiom's whole purpose, but a REPEATED `<<:` is itself an authored duplicate) and a
  closed key vocabulary at all three levels -- nothing in the document is silently dropped or
  silently ignored. Every identity-bearing string field routes through `_require_text`, a
  `.strip()`-based non-blank check that also STORES the stripped value, so surrounding
  whitespace is never part of an identity. `_build_entry` resolves the entry's class before
  building its regions, so a field the class does not take is always reported as such rather
  than as a shape complaint about its value.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_model_version.py` -- NEW: 75
  collected tests (parse valid/invalid grammar, the SemVer spec's own pre-release-ordering
  chain, build-metadata-ignored, `in_range` boundaries, non-ASCII-digit rejection, the
  follow-up pass's field-level grammar validation, comparator trichotomy, `str()` round-trip,
  and unusable-numeric-component coverage, the second follow-up pass's unbounded-length
  numeric-pre-release ordering -- correct, not merely non-raising -- through both the
  comparator and `in_range`, plus the third pass's renderability invariant: every
  constructible `ModelVersion` can be formatted into a message).
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_model_manifest.py` -- NEW: 92
  collected tests (one entry per class, every `ManifestError` scenario in the I/O matrix,
  since/until range filtering, defaults, `Region`/`ManifestEntry` direct-construction
  validation, the first review pass's falsy-masking / TypeError-vs-ValueError / file-I/O /
  error-locator coverage, the follow-up pass's duplicate-key, closed-key,
  class-appropriate-field, duplicate-region-name, non-UTF-8 and frozen/hashable coverage, the
  second follow-up pass's YAML-merge-key acceptance (and authored-duplicate rejection
  inside a merged entry), whitespace-only field rejection, region-level error locator,
  in-memory duplicate-id rejection, and the two top-level `model_version` authoring mistakes,
  plus the third pass's whitespace-normalization, blank-anchor, class-before-shape ordering,
  repeated-merge-key, deep-nesting, `never_write` locator, and the five previously-uncovered
  dataclass type guards).
  Every error assertion is anchored on the locator AND the reason: the parametrized
  missing-required-field test that asserted a bare `pytest.raises(ManifestError)`, and four
  substring-only matches, were tightened in the second follow-up pass; the third pass
  tightened the remaining eight locator-only / reason-only matches and replaced a vacuous
  set-literal truthiness assertion with an explicit per-object `hash()`.

## Tasks & Acceptance

**Execution:**
- [x] `seed/model/version.py` -- implement `ModelVersion` parse/compare (full SemVer 2.0.0
  precedence incl. pre-release ordering, build metadata ignored) + `InvalidVersionError` +
  `in_range()` -- gives `manifest.py` a trustworthy, dependency-free comparator
- [x] `seed/model/manifest.py` -- implement the schema types + `ManifestError` +
  `load_manifest()` per Boundaries above -- the schema + loader the AC requires
- [x] `tests/unit/test_seed_model_version.py` -- parse/compare/pre-release-ordering/build-
  metadata/invalid-string coverage -- proves version.py's AC clause
- [x] `tests/unit/test_seed_model_manifest.py` -- the I/O matrix above -- proves manifest.py's
  AC clauses

**Acceptance Criteria:**
- Given a YAML manifest with one valid entry per class, when `load_manifest` parses it, then a
  `Manifest` is returned with every entry's fields typed and populated
- Given a manifest with two entries sharing an `id`, when `load_manifest` parses it, then it
  raises `ManifestError` naming the duplicate id
- Given a manifest entry with an unrecognized `class`, when `load_manifest` parses it, then it
  raises `ManifestError`
- Given a `hybrid-managed-region` entry with no `regions`, when `load_manifest` parses it,
  then it raises `ManifestError`
- Given entries with `since`/`until` bounds on either side of the manifest's own
  `model_version`, when `load_manifest` parses it, then only entries applicable at that
  version appear in `Manifest.entries`
- Given two `ModelVersion` strings differing only in pre-release identifiers, when compared,
  then ordering matches SemVer 2.0.0 precedence
- Given the existing `pyforge-marshal` test/lint/import-linter suite, when this story's files
  are added, then all stay green with no meta-test changes required

## Spec Change Log

## Review Triage Log

### 2026-08-10 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 4, low 3)
- defer: 0
- reject: 3: (high 0, medium 0, low 3)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): `raw_document.get("never_write")/("artifacts") or []` and the per-entry `raw_entry.get("regions") or []` silently coerced a present-but-falsy wrong-typed value (`false`, `0`, `""`) into an empty default instead of raising `ManifestError`. Replaced all three with an explicit `is None` check before the type validation.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): `ManifestEntry.regions`, `Manifest.never_write`, `Manifest.entries` called `tuple(self.<field>)` unconditionally before validating, so a non-iterable value (e.g. `regions=5`) raised a raw `TypeError` instead of the class's documented `ValueError` contract. Applied the same guarded-conversion pattern `Region.anchor` already used (`tuple(x) if isinstance(x, list) else x`, then an explicit `isinstance(..., tuple)` check) to all three.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): `_SEMVER_PATTERN`'s `\d` matched non-ASCII Unicode decimal digits (e.g. Arabic-Indic), letting a non-conformant string like `"1٠3.0.0"` parse silently as `major=103` instead of raising `InvalidVersionError`. Added `re.ASCII` to the compiled pattern.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): `load_manifest` never wrapped the file-open/YAML-parse call, so a missing file or malformed YAML raised a raw `FileNotFoundError`/`yaml.YAMLError` instead of the documented `ManifestError`-only contract. Wrapped in `try/except (OSError, yaml.YAMLError)`.
  - `[low]` `[patch]` Blind Hunter: five real validation branches (non-list `artifacts`, non-mapping entry, non-list `never_write`, non-mapping region, non-list `regions`) had zero test coverage. Added tests for all five, plus the falsy-masking and I/O-wrapping fixes above.
  - `[low]` `[patch]` Blind Hunter: the module docstring claimed `load_manifest` does "no field-by-field re-validation of its own," which is inaccurate for the two top-level collection fields (`never_write`, `artifacts`) that do get a loader-side pre-check (needed because `Manifest(...)`'s own construction isn't wrapped in a `ValueError`→`ManifestError` translation). Reworded to state the actual, narrower rule; also added the previously-omitted `never_write` case to `load_manifest`'s own raise-scenario docstring enumeration.
  - `[low]` `[patch]` Blind Hunter: entries with a missing/invalid `id` all collapsed to the same generic `"manifest: ..."` message, giving no way to tell which of several malformed entries in a large manifest was broken. Added the array index (`artifacts[N]`) to the fallback label.
  - `[reject]` Blind Hunter: 5 `ruff` `TRY004` ("prefer `TypeError`") findings on the `isinstance`-guarded `ValueError` raises. Verified this is an established, pre-existing repo convention, not a regression: `core/model.py` alone (unrelated to this story) trips the identical 5 findings in the identical pattern. This diff's own guard fixes above added 2 more instances of the same accepted convention (7 total).
  - `[reject]` Blind Hunter: `pyright` `reportArgumentType` findings in the new test files from deliberately passing wrong-typed literals (e.g. `regions=5`, `applies_to="sometimes"`) to exercise runtime `ValueError` paths. Verified this matches the established, accepted convention in `test_model.py` (10 pre-existing instances of the identical pattern, never fixed) — not a defect.
  - `[reject]` Blind Hunter: duplicate-`id` detection runs before `since`/`until` filtering, forbidding the same `id` from being reused across two non-overlapping time windows (e.g. a reclassification). The epics AC states plainly that "duplicate ids... are load-time errors" with no time-window carve-out, and no upstream document or Story 7.5's actual V1 content names a concrete need for id reuse across ranges — treated as out-of-scope speculative generalization, not a gap in this story's AC compliance.

### 2026-08-10 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 12: (high 0, medium 4, low 8)
- defer: 3: (high 0, medium 2, low 1)
- reject: 7: (high 0, medium 0, low 7)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): `_is_numeric_identifier` used bare `.isdigit()`, which is `True` for characters `int()` refuses — VERIFIED live: `ModelVersion(1,0,0,prerelease=("²",)) < ModelVersion(1,0,0,prerelease=("1",))` raised a raw `ValueError: invalid literal for int()` straight out of the comparator. `parse` was protected by the prior pass's `re.ASCII`, but `__post_init__` is a second, unguarded entry point (tests, `dataclasses.replace`, a future state deserializer). This is a hazard the repo already documents as real — `adapters/harness_bmadloop.py:549` rejects `.isdigit()` in a comment for exactly this reason. Fixed at both layers: `__post_init__` now validates every `prerelease`/`build` identifier against the SemVer grammar, and the comparator uses `isascii() and isdecimal()`.
  - `[medium]` `[patch]` Edge Case Hunter: the same unguarded `__post_init__` also let ordering itself break — VERIFIED: for `("01",)` vs `("1",)`, `a < b`, `b < a` and `a == b` were ALL `False` (equal numerically, unequal by the dataclass `__eq__`), so the pair satisfied none of `<`/`>`/`==` and `sorted`/`bisect` silently misbehaved. Closed by the same grammar validation; a new trichotomy test asserts exactly one of the three holds for every pair in a representative set.
  - `[medium]` `[patch]` Edge Case Hunter: `load_manifest` documents a `ManifestError`-only contract, but `UnicodeDecodeError` is a `ValueError`, NOT an `OSError` — VERIFIED: a manifest with any non-UTF-8 byte raised raw `UnicodeDecodeError` past the prior pass's `(OSError, yaml.YAMLError)` handler. Added an explicit handler.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): the module justifies its list-shaped `artifacts:` wire format by "PyYAML's default loader silently overwrites duplicate mapping keys" — then applied that reasoning at exactly one level. VERIFIED: a document with two `model_version:` keys silently took the second (`9.9.9`), changing which entries survive the filter for the whole model; an entry with two `path:` keys silently took the second. The file a human reviews in the diff was not the file the engine loads. Added `_StrictLoader`, a `SafeLoader` subclass rejecting any repeated key (its `ConstructorError` is a `YAMLError`, so the existing handler reports it).
  - `[medium]` `[patch]` Blind Hunter: unknown keys were silently ignored — VERIFIED: an entry carrying `untl: "2.0.0"` (a one-character typo meaning the entry never retires) and a document with `artefacts:` (meaning zero artifacts are installed and the run still exits 0) both loaded clean. For a hand-authored contract file whose only reviewer is a git diff, a closed key vocabulary is the cheapest available guard. Added `_DOCUMENT_KEYS`/`_ENTRY_KEYS`/`_REGION_KEYS` with a locator-prefixed error at each level.
  - `[low]` `[patch]` Edge Case Hunter: `pin`/`format`/`regions` were required on their own class but ignored everywhere else — VERIFIED: a `copied-managed` entry declaring `regions:` loaded clean and the regions were silently never applied, so an author believes a region is managed and nothing ever says otherwise. Now rejected in both directions.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): duplicate region names within one entry — VERIFIED accepted. The region name is its identity in the `marshal-seed:*` marker wire format (AD-64), so two same-named regions hand the writer two conflicting spans for one marker pair and the idempotency check cannot tell which span it owns. Added a per-entry uniqueness check, plus a test pinning that the same name across DIFFERENT entries (`AGENTS.md` and `CLAUDE.md` both carrying `tiers`) stays legal.
  - `[low]` `[patch]` Edge Case Hunter: `never_write: [""]` was accepted, unlike every other string field in the module — an empty pattern reaching S-7.3's guard could match every path. Now required non-empty.
  - `[low]` `[patch]` Blind Hunter: `ModelVersion` had no `__str__`, so this story's own AC-mandated error message printed a dataclass repr — VERIFIED: `until (ModelVersion(major=1, minor=0, patch=0, prerelease=(), build=())) must be strictly greater than since (...)`. Added `__str__`; the message now reads `until (1.0.0) must be strictly greater than since (2.0.0)`, and a test pins the `parse(str(v)) == v` round-trip the later state-writing story needs.
  - `[low]` `[patch]` Blind Hunter: with both bounds present, an entry-level `since`/`until` parse failure did not say which one was bad (`foo: 'bad' is not a valid SemVer...`), leaving the operator to guess which line to edit — and the top-level path already named its field (`manifest: model_version: ...`), so the loader was inconsistent with itself. `_parse_bound` now takes the field name.
  - `[low]` `[patch]` Edge Case Hunter: a grammatically valid but absurd numeric component escaped as a raw `ValueError` — VERIFIED: CPython refuses `int()` past 4300 digits, and `load_manifest` caught only `InvalidVersionError`. `parse` now converts it to `InvalidVersionError`, and the loader's top-level catch was widened to its superclass.
  - `[low]` `[patch]` Blind Hunter: `ManifestError`'s class docstring documented two message prefixes while the code emits three (`artifacts[N]:`, as the module docstring already correctly stated), so a consumer routing on the documented prefix would misclassify entry errors as top-level ones. Reconciled the class docstring; `load_manifest`'s raise-scenario enumeration was also brought up to date with every guard added this pass.
  - `[low]` `[patch]` Blind Hunter: test assertions matched only the entry id (`pytest.raises(ManifestError, match="foo")`), which passes for ANY failure of entry `foo` — a regression that changes WHICH rule fires stayed green; `match="manifest"` matched nearly every message the module can emit. Tightened every assertion to anchor on the locator AND the reason, broadened `test_wrong_type_required_field` from 2 fields to all 5 with a per-field expected message, and added the missing frozen/hashable assertion P-11's immutability leans on.
  - `[reject]` Blind Hunter: `ManifestError` is minted outside Story 7.2's exit-code taxonomy. Directly restates this story's own Never bullet ("No adoption of Story 7.2's not-yet-built exit-code taxonomy — wiring it onto the shared taxonomy is later-story work"); 7.2 is itself still `blocked`.
  - `[reject]` Blind Hunter + Edge Case Hunter: duplicate `id` across disjoint `since`/`until` windows is forbidden. The prior pass rejected this on a stated premise, so the premise was re-verified against the source rather than inherited: `epics.md:1557` requires `id` "(stable, unique)" and `epics.md:1571` states "duplicate ids... are load-time errors" with no time-window carve-out. Premise confirmed true; rejection stands on scope.
  - `[reject]` Blind Hunter: `pin` is not parsed as a version range. Explicitly scoped out by Boundaries, with the reason given there (real pins like tmux `>=3.7b` are not valid SemVer).
  - `[reject]` Edge Case Hunter: `format` should be a closed `RegionFormat` StrEnum. Explicitly scoped out by Boundaries — the marker vocabulary belongs to the not-yet-built `regions/markers.py`.
  - `[reject]` Edge Case Hunter: a pre-release `model_version` (`2.0.0-rc.1`) excludes entries gated `since: 2.0.0`. That is exactly SemVer 2.0.0 precedence, which Boundaries requires this module implement "exactly"; the proposed fix (strip pre-release before comparing) would deviate from the spec, not comply with it.
  - `[reject]` Blind Hunter: `version.py` duplicates `adapters/harness_bmadloop.py`'s `harness_version_tuple`. Different domains — tool version pins (`>=0.9.0,<0.10`, `0.9.0rc1`) versus the model-version clock — and the Never bullet targets external dependencies, not internal specialization.
  - `[reject]` Blind Hunter: a structurally empty manifest is indistinguishable from a healthy one. The reachable half (a MISSPELLED `artifacts:` key) is now a hard error via the closed-key patch above; the remainder asks for a minimum-content assertion no requirement names, and `test_artifacts_defaults_to_empty_tuple` blesses the absent-key default deliberately.

### 2026-08-10 — Review pass (second follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 0, medium 3, low 5)
- defer: 2: (high 0, medium 1, low 1)
- reject: 11: (high 0, medium 3, low 8)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): the prior pass's
    4300-digit fix stopped one function short. `_PRERELEASE_IDENTIFIER` accepts a numeric
    pre-release identifier of unbounded length while `_compare_prerelease_identifier` called
    bare `int()` — VERIFIED: `parse("1.0.0-" + "1"*5000) < parse("1.0.0-" + "2"*5000)` raised
    `ValueError: Exceeds the limit (4300 digits)`, and VERIFIED again through `load_manifest`,
    whose post-validation `in_range` filter sits outside every `try/except`, so the raw
    `ValueError` escaped the documented `ManifestError`-only contract entirely. It also
    falsified `_is_numeric_identifier`'s own comment ("keeping the comparator total for any
    input that reaches it"). Fixed by removing `int()` from the comparator: with leading zeros
    stripped, the longer decimal string is the larger number and equal-length strings compare
    numerically in lexicographic order — total at every length, and correct even for a
    leading-zero identifier the grammar should have rejected.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): `_StrictLoader`
    (the prior pass's own addition) rejected legal YAML. `SafeConstructor.construct_mapping`
    runs `flatten_mapping`, splicing a merge key's inherited pairs into `node.value` BEFORE
    the duplicate scan walked it — VERIFIED: an entry `- <<: *base` / `id: bar` failed with
    `found duplicate key 'id'` naming a line the author never duplicated. Merge-key override is
    standard YAML whose whole purpose is that the explicit key wins, and it is the idiom a
    human reaches for in a file of near-identical entries (S-7.5's). Fixed by snapshotting the
    authored key nodes before delegating and skipping merge-tagged keys; a new test pins that a
    key the author genuinely wrote twice inside a merged entry is still rejected.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): every non-empty
    check was a bare truthiness test, so whitespace-only values passed — VERIFIED: an entry
    with `id`, `path` and `rationale` all `"   "` loaded clean. A blank `rationale` satisfies
    AD-55's reviewability requirement without being reviewable; a blank `path` reaches S-7.3's
    guard indistinguishable from a real target; a blank `id` cannot be addressed by
    `explain <id>`. The module already rejected an EMPTY `never_write` pattern on exactly this
    reasoning, so it was inconsistent with itself one space away. Added `_require_text`
    (`.strip()`-based) across `id`/`path`/`rationale`/`pin`/`format`/`legacy_of`/region `name`
    and both `never_write` checks. Fixing it exposed a second-order defect found in
    verification, fixed in the same patch: the loader's `entry_label` used the same bare
    truthiness test, so a blank id labelled its own error with an invisible locator
    (`   : id must be ...`) instead of falling back to `artifacts[N]`.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): `Manifest(...)`
    accepted duplicate ids when constructed directly — VERIFIED. Id uniqueness lived only in
    `load_manifest`, yet the module docstring advertises these dataclasses as constructible on
    their own ("tests, a future in-memory manifest builder") and states `__post_init__` does
    "the real checking" — so the one invariant every downstream consumer keys on (`by_id`,
    `explain <id>`, state addressing) was absent from the layer documented as owning it. Added
    the check to `Manifest.__post_init__`; the loader keeps its own (that is where the AC's
    "`ManifestError` naming the duplicate id" contract lives).
  - `[low]` `[patch]` Blind Hunter: region-level errors carried no region locator — VERIFIED:
    an entry with three regions whose second has `anchor: []` reported only
    `foo: anchor must be a non-empty tuple, got ()`. This is the identical defect both prior
    passes fixed one level up (`artifacts[N]`) and one field over (`since:`/`until:`), left
    unfixed at the third level of the structure the module itself calls out as having "a closed
    vocabulary at all three levels." Errors now read `foo: regions[1] (two): ...`, falling back
    to the bare index when the name is unreadable.
  - `[low]` `[patch]` Blind Hunter: the Code Map's claim that "every error assertion [is]
    anchored on the reason, not merely the entry id" was false for five tests — VERIFIED:
    `test_missing_required_field_raises_manifest_error`, parametrized over all five required
    fields, asserted a bare `pytest.raises(ManifestError)` with NO `match` at all (green for
    any load failure whatsoever), and four others matched only `"foo"` / `"never_write"` /
    `"artifacts"`, substrings that appear in nearly every message the module emits. All five
    tightened to a per-case locator-and-reason regex.
  - `[low]` `[patch]` Blind Hunter: the two likeliest top-level authoring mistakes had no
    coverage and one had a misleading message — VERIFIED: a MISSING `model_version` key fell
    through to `parse(None)` and reported `version must be a str, got None`, a type error that
    reads as a bug report rather than an instruction to add the line; an unquoted
    `model_version: 1.0` (a YAML float) was rejected but untested. Added an explicit
    required-key check with its own message, plus tests for both.
  - `[low]` `[patch]` Blind Hunter: two docstring inaccuracies. The module's `ArtifactClass`
    sentence did not parse ("the six-member classification vocabulary the extraction-manifest's
    own five product classes plus `unclassified-deferred` resolve to") — reworded, along with
    the class docstring repeating it. And the module docstring called `never_write`/`artifacts`
    "the one deliberate exception" to routing validation through the dataclasses, when the
    loader also checks the document shape, the top-level key vocabulary and `model_version` —
    reworded to name the actual rule (the whole top level is loader-checked, because
    `Manifest(...)` is not wrapped in the `ValueError`→`ManifestError` translation).
  - `[reject]` Edge Case Hunter: `format` should be a closed `RegionFormat` StrEnum, citing
    S-8.1's AC as assigning the check here. The premise was verified rather than inherited —
    `epics.md:1663` does read "an artifact declaring a format not in the registry is a manifest
    load error (S-7.4)". But S-8.1's own Surface is `seed/regions/markers.py` and its Deps are
    S-7.4: the registry does not exist yet, so this loader cannot validate against it. S-8.1
    builds the registry and wires it in — which is exactly what this story's Boundaries say
    ("`format`'s marker vocabulary belongs to the not-yet-built `regions/markers.py`"). The
    forward reference is recorded here so the next pass does not re-litigate it and S-8.1 is on
    notice to close it.
  - `[reject]` Blind Hunter + Edge Case Hunter: `path` accepts absolute (`/etc/passwd`) and
    traversal (`../../../.ssh/authorized_keys`) values. Real and reproduced — but already
    recorded verbatim as an open entry in the deferred-work ledger by the previous pass. Not
    re-appended: a duplicate ledger entry is noise, and the orchestrator owns existing entries.
  - `[reject]` Blind Hunter: the version filter discards retired/future-staged entries with no
    record, so `explain <retired-id>` cannot distinguish "retired" from "unknown". Also already
    an open ledger entry from the previous pass, with the additive fix (`at_version=` /
    `all_entries`) already described there. Filtering by the bundled model version is precisely
    what the AC asks for; the exposure question belongs to the story that first needs it.
  - `[reject]` Edge Case Hunter: `legacy_of` should be checked referentially against other
    entries' ids. Directly restates this story's own Boundaries bullet ("`legacy_of`, when
    present, is validated only as a non-empty string — no referential check against other
    entries' ids (not named in the AC)").
  - `[reject]` Edge Case Hunter: `pin` should be parsed as a version range. Third pass in a row
    for this one; explicitly scoped out by Boundaries with the reason stated there (real pins
    like tmux `>=3.7b` are not valid SemVer).
  - `[reject]` Edge Case Hunter: `path` should be jinja-syntax-validated at load. Boundaries
    scope out jinja rendering, and the proposed guard imports `jinja2` — a dependency this
    story's Never bullet forbids and the lean `pyforge-marshal` env does not carry.
  - `[reject]` Edge Case Hunter: the loader should reject an entry whose `path` matches the
    manifest's own `never_write`. Scoped out (S-7.3's guard owns never-write matching), and
    unsound here regardless: `path` is jinja-templated, so it cannot be matched against a glob
    before rendering. The adjacent, real half of this (7.5's manifest needs exemptions the flat
    `never_write` list cannot express) is already an open ledger entry from the prior pass.
  - `[reject]` Blind Hunter: `never_write` accepts duplicate/unnormalized patterns. A duplicate
    deny-pattern denies the same thing twice; no consequence for the consumer.
  - `[reject]` Blind Hunter: a structurally empty manifest is indistinguishable from a healthy
    one via the version filter. The finding correctly notes the prior pass's rejection premise
    was incomplete (the closed-key patch closes the misspelled-`artifacts:` route, not the
    filter route) — so the premise is restated correctly here rather than reused. It is still
    not a defect: an all-filtered-out manifest is the documented, correct behavior of the
    half-open filter, no requirement names a minimum-content assertion, and this story ships no
    diagnostic channel to warn on one.
  - `[reject]` Blind Hunter: the commentary-to-code ratio is extreme and each rationale is
    restated in five places. The one concrete, checkable sub-claim (a divergence between the
    module docstring and `load_manifest`'s own enumeration) was real and is patched above. The
    remedy for the rest — cut the comments — conflicts with the established house style in this
    package (`core/model.py`) and would delete rationale two prior passes deliberately added.
  - `[reject]` Blind Hunter: `path` is mandatory even for `referenced` entries, which the
    extraction-manifest describes as "not materialized", so the fixture writes `path: "n/a"`.
    The AC lists `path` among the always-required fields with no per-class carve-out; changing
    that is a schema decision for S-7.5's author, not a loader defect.

### 2026-08-10 — Review pass (third follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 12: (high 0, medium 2, low 10)
- defer: 0
- reject: 4: (high 0, medium 0, low 4)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): `_require_text`
    decided validity with `.strip()` but STORED the padded value, so surrounding whitespace was
    significant to identity and to nothing else — VERIFIED: a manifest with `id: "foo"` and
    `id: " foo "` loaded clean as two distinct entries that render identically, defeating the
    AC's "duplicate ids are a load-time error" contract outright and leaving neither reachable
    by `explain foo`; `path: "  AGENTS.md  "` likewise reached S-7.3's guard matching no
    pattern and no file, and (Edge Case Hunter, same root cause) a padded `never_write` pattern
    silently protected nothing while reading as present in the diff. `_require_text` now
    returns the stripped value and every caller stores it; `never_write` is stripped on store
    too. The padded id now collides with its bare twin and reports `foo: duplicate id`, which
    is the AC's own error rather than a new one.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): `Region.anchor`
    items were the one string field the prior pass's non-blank sweep missed, still on bare
    truthiness — VERIFIED: `anchor: ["   "]` loaded clean. An anchor is AD-56's literal
    line-prefix matcher, so a whitespace-only one matches the first indented line in the target
    file and splices the managed region at an arbitrary position — the same "matches
    everything" hazard that already disqualifies an empty `never_write` pattern, and the module
    was inconsistent with itself one field over. Now rejected. The value is deliberately NOT
    stripped (unlike an id or a path, an anchor's own leading whitespace is significant), and a
    test pins that an intentionally indented anchor still round-trips.
  - `[low]` `[patch]` Blind Hunter: `ManifestError`'s three-mutually-exclusive-locator contract
    was violated by one raise — VERIFIED: a non-mapping entry emitted
    `manifest: artifacts[0] must be a mapping`, both prefixes at once, so a consumer routing on
    `startswith("manifest: ")` misclassified an entry failure as a top-level one. This is the
    defect the second pass patched at the docstring and then re-shipped in the code. Now
    `artifacts[0]: entry must be a mapping`. The finding's second half (an entry-level
    duplicate-key error labelled `manifest:`) was verified and judged correct-by-construction —
    PyYAML fails while composing the document, before any entry structure exists to address —
    so the class docstring now states that rule explicitly rather than leaving it implied.
  - `[low]` `[patch]` Blind Hunter: the prior pass's merge-key exemption was unconditional, so
    a genuinely duplicated `<<:` evaded the strict loader — VERIFIED: `<<: *a` / `<<: *b` on
    consecutive lines loaded clean taking `path` from `b` (last wins), while the semantically
    identical `<<: [*a, *b]` takes it from `a` (first wins, per the YAML merge spec). Two
    spellings of "inherit from a and b" producing opposite artifacts is exactly what
    `_StrictLoader` exists to prevent, and the exemption was written for ONE merge key
    overriding an inherited value. Only the first `<<:` is now exempt; a repeat is reported as
    an authored duplicate naming the sanctioned sequence spelling. Both directions are pinned
    by tests.
  - `[low]` `[patch]` Blind Hunter: `RecursionError` escaped the `ManifestError`-only contract
    — VERIFIED: `artifacts:` followed by 500 nested `[` raised a raw `RecursionError` (at depth
    200 it correctly reported `ManifestError`). PyYAML's composer recurses per nesting level,
    so this is the same escape class as the prior pass's `UnicodeDecodeError`, on the very
    input (malformed YAML) the contract's own docstring enumerates. Added a handler.
  - `[low]` `[patch]` Blind Hunter: `never_write` was the one error in the module naming
    neither a locator nor the offending value — VERIFIED: `["a", 42, "b"]` reported only
    `manifest: never_write must be a list of non-blank str`. The module fixed this exact defect
    at three other levels across two prior passes (`artifacts[N]`, `regions[N] (name)`,
    `since:`/`until:`); on S-7.5's real deny-list an unlocated failure is a manual bisect. Now
    `manifest: never_write[1] must be a non-empty, non-blank str, got 42`.
  - `[low]` `[patch]` Blind Hunter: class-appropriateness was checked last, so a field the class
    does not take at all was reported as a shape complaint about its value — VERIFIED: a
    `copied-seeded` entry carrying `regions: [{name: tiers, anchor: []}]` reported
    `anchor must be a non-empty tuple`, telling the author to repair a region the class forbids
    outright, and `pin: 5` on a `copied-managed` entry reported `pin must be a non-empty,
    non-blank str`, sending them to fix the type of a field they must delete. Both now report
    the class rule. The fix required `_build_entry` to resolve the class BEFORE building
    regions; a test written for the fix caught the first attempt shadowing the
    unrecognized-class error itself, which the final shape preserves.
  - `[low]` `[patch]` Blind Hunter: the likeliest region-authoring slip got a message naming a
    Python type the wire format cannot express — VERIFIED: `anchor: "## Tiers"` (a scalar
    instead of a list) reported `anchor must be a non-empty tuple, got '## Tiers'`, while every
    neighbouring message in the module speaks YAML. Reworded to "non-empty list of str".
  - `[low]` `[patch]` Blind Hunter: the 4300-digit hardening stopped one function short again
    — VERIFIED: `ModelVersion.__post_init__` accepted any non-negative `int`, but CPython
    refuses to RENDER one past 4300 digits, so
    `ManifestEntry(..., since=ModelVersion(major=10**5000, ...), until=ModelVersion(1,0,0))`
    raised a raw `ValueError` from inside `__str__` *while formatting* this story's own
    AC-mandated `until (...) must be strictly greater than since (...)` message — the error was
    destroyed by its own interpolation, and `parse` (which converts this correctly) disagreed
    with the second entry point the prior pass itself identified as unguarded. `__post_init__`
    now proves every numeric component is renderable, with a test pinning the invariant: if a
    `ModelVersion` exists, any message interpolating it can be formatted.
  - `[low]` `[patch]` Blind Hunter: five dataclass validation branches had zero test coverage
    (`anchor` non-str items, `regions` non-`Region` items, `since`/`until` non-`ModelVersion`,
    `model_version` non-`ModelVersion`, `entries` non-`ManifestEntry`) — confirmed by grep and
    by the reviewer's line tracer. The first pass closed five different uncovered branches and
    these five shipped in their place; three of them carry the `TRY004` ruff finding this story
    records as an accepted convention, so a regression flipping any to `TypeError` would have
    shipped green. All five now covered.
  - `[low]` `[patch]` Blind Hunter: eight error assertions were locator-only or reason-only,
    falsifying the Code Map's claim that "every error assertion is anchored on the locator AND
    the reason" — VERIFIED by reading: `match=r"artifacts\[0\]"`, `"could not read"`,
    `"invalid YAML"`, `r"artifacts\[1\]"`, `"duplicate key"` (x2), `"is not valid UTF-8"`,
    `"^manifest: model_version:"`. Two of them (the unanchored `artifacts[0]` and
    `duplicate key` matches) are exactly the assertions that stayed green against the doubled
    prefix defect patched above. All eight tightened to a locator-and-reason regex.
  - `[low]` `[patch]` Blind Hunter: `assert {region, entry, manifest}  # hashable` is a vacuous
    assertion — a non-empty set literal is always truthy, so the assert itself can never fail
    and a `__hash__ = None` regression would surface as an unnamed `TypeError` inside a test
    named `..._frozen_and_hashable`. Replaced with an explicit per-object `hash()`.
  - `[reject]` Blind Hunter: the closed top-level key vocabulary forecloses a
    `_defaults: &base {...}` anchor block, so the merge-key idiom can only anchor a real
    artifact entry. Reproduced and real as stated, but adding a top-level affordance to the
    wire format is a schema decision owned by S-7.5 (the story that authors the manifest and
    would be its only consumer); no AC or upstream document names one, and nothing is broken
    without it — merge keys off a real entry work, which is what the exemption's own tests pin.
  - `[reject]` Blind Hunter: `load_manifest("/path/as/a/str")` raises `AttributeError`, not
    `ManifestError`. Reproduced, but the `ManifestError` contract is about manifest CONTENT;
    passing a `str` where the signature says `Path` is caller misuse that pyright catches
    statically, and funnelling it into `ManifestError` would disguise a caller bug as a
    manifest problem.
  - `[reject]` Edge Case Hunter: a region `name` should be restricted to a marker-safe charset.
    Real — and already recorded verbatim as an open deferred-work entry by the second pass
    (AD-53's space-delimited marker grammar, assigned to S-8.1). Not re-appended: the
    orchestrator owns existing entries and a duplicate is noise.
  - `[reject]` Edge Case Hunter: two entries sharing one `path` may each declare a same-named
    region, producing two identical markers in one file. Its premise — that two entries may
    share a `path` — is itself the second pass's open ledger entry on cross-entry path
    uniqueness (verified still present), so this is a refinement of an already-deferred finding
    rather than a new one. Unsound to check here regardless: `path` is jinja-templated, so
    pre-render path equality is not decidable at load time.

## Design Notes

- **Why filtering uses the manifest's own top-level `model_version`, not an externally
  supplied "current" version:** architecture names `model_version` as installed *state*
  (`state.model_version`, a separate later-story concern) — the manifest's own top-level
  `model_version` is "the bundled model version" the AC's loader filters by, confirmed by
  Story 7.5's own AC ("initial `model_version` is `1.0.0`" is itself manifest-authored). This
  makes the manifest an append-only historical ledger: future-staged and retired entries stay
  in the reviewable diff without deletion, matching AD-55's "manifest is the product's actual
  contract."
- **`since`/`until` are half-open (`[since, until)`)** — undocumented upstream; this story's
  own decision, matching the common `>=since,<until` versioning convention.
- **Top-level entry list is `artifacts:` (a list with explicit `id:` fields), not an
  `{id: {...}}` mapping** — AD-55's "entries keyed by stable artifact id" describes the
  addressing scheme used downstream (state, `explain <id>`), not the YAML shape; PyYAML's
  default loader silently overwrites duplicate mapping keys, which would defeat the
  "duplicate ids are a load-time error" AC.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expect all tests pass
  including the two new files
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` -- expect this
  story's four files to contribute exactly 8 `TRY004` findings, all the accepted repo
  convention recorded in the first review pass, and NO others. (7 through the second follow-up
  pass; the third pass split one compound `isinstance`-guarded raise in `version.py` into two
  so an over-long numeric component could be reported separately, which ruff counts as one
  more instance of the same accepted pattern.) The package-wide total (~190) is pre-existing
  and unrelated: it reproduces identically on the untouched baseline revision, so the gate is
  baseline-vs-head parity on this story's own files, not a zero-finding run.
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-marshal` -- same parity
  gate. This story's files contribute 3 `reportMissingImports` (an environment artifact --
  the `local-recipes` env has no `pyforge-marshal` install, which is also why the package
  total is 587 on the untouched baseline) plus the 1 `reportArgumentType` recorded as an
  accepted test convention in the first review pass.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- expect all contracts pass

**Outcomes (third follow-up review pass, 2026-08-10):**
- tests: `3436 passed, 9 deselected` (3414 before this pass; +22 new tests). Per-file
  collection: `test_seed_model_version.py` 75, `test_seed_model_manifest.py` 92.
- ruff: story files contribute exactly 8 findings, all `TRY004`, all the accepted repo
  convention (7 in `manifest.py`, unchanged; +1 in `version.py` from splitting one compound
  guarded raise). No other rule fires on this story's files.
- pyright: 587 package-wide, unchanged from the recorded baseline; this story's files
  contribute the same 4 findings (3 `reportMissingImports` env artifacts + 1
  `reportArgumentType` accepted test convention) -- the new negative-path tests carry explicit
  `# pyright: ignore[reportArgumentType]` comments, so the count did not grow.
- lint-imports: `Contracts: 3 kept, 0 broken` (AD-4, AD-3, AD-9).
- Every patched finding was reproduced live against the shipped code BEFORE the fix and re-run
  after; no finding was accepted on inference alone. Both rejections that rest on a claim about
  another document (the region-`name` marker grammar and cross-entry `path` uniqueness) were
  checked against the actual deferred-work ledger rather than inherited from the prior pass's
  summary -- both entries are present and open, so neither was re-appended.
- The class-before-shape fix was itself caught mid-pass by a test written for it (the first
  shape shadowed the unrecognized-class error); the final shape reports the class error first
  and pins that ordering.

**Residual risks:**
- Text fields are now stored STRIPPED, not merely validated with `.strip()`. This is a
  deliberate normalization: it is what makes a padded id collide with its bare twin and report
  the AC's own `duplicate id` error. `Region.anchor` items are the documented exception (an
  anchor's own leading whitespace is significant to AD-56's line-prefix match), pinned by a
  test in both directions. Three existing assertions moved with the `never_write` locator
  change (message text only, not which rule fires).
- `_StrictLoader` exempts the FIRST YAML merge key only. A document that merges an anchor and
  repeats a key *inside* the anchor is still caught, and a repeated `<<:` is now rejected --
  but the single-merge exemption remains a deliberate widening of what the loader accepts,
  pinned by tests in both directions.
- `_build_entry` now resolves `ArtifactClass(raw_class)` before `ManifestEntry.__post_init__`
  does, so the class error precedes the id error for an entry whose id and class are both
  malformed. `__post_init__` remains the type boundary (it re-runs the conversion); the
  ordering change is confined to which of two errors an author sees first.
- Two findings the second pass judged real remain deferred rather than fixed because the
  correct rule is a schema decision owned downstream: cross-entry `path` uniqueness (S-7.5) and
  the region `name` marker-grammar token (S-8.1). Both are open in the deferred-work ledger
  with the evidence; this pass re-verified both entries are present and added none.



## Auto Run Result

Status: done — third follow-up review pass (no intent gap, no spec repair, no loopback).

**Change under review:** Story 7.4's four new files, unchanged in scope since the original
implementation — the manifest schema + loader and the hand-rolled SemVer 2.0.0
parser/comparator, plus their unit tests. This pass reviewed the accumulated diff since
`f2f4b7692e` and applied 12 patches; no production behavior outside `seed/model/` was touched.

**Files changed this pass:**
- `src/pyforge/marshal/seed/model/manifest.py` — `_require_text` now stores the stripped value
  (whitespace is no longer part of an identity); `Region.anchor` items must be non-blank;
  `_build_entry` resolves the artifact class before building regions so a field the class does
  not take is reported as such; `_StrictLoader` exempts only the first YAML merge key;
  `RecursionError` joins the `ManifestError` handler; the `never_write` error names its index
  and value; the non-mapping-entry error uses the `artifacts[N]:` locator alone; `ManifestError`'s
  docstring now states the YAML-parse-failure rule explicitly.
- `src/pyforge/marshal/seed/model/version.py` — `__post_init__` proves every numeric component
  is renderable, so a directly-constructed `ModelVersion` can never destroy the error message
  that interpolates it.
- `tests/unit/test_seed_model_manifest.py` — 92 collected (was 74): +8 tightened assertions,
  the vacuous hashability assert replaced, and new coverage for whitespace normalization,
  blank anchors, class-before-shape ordering, repeated merge keys, deep nesting, the
  `never_write` locator, and the five previously-uncovered dataclass type guards.
- `tests/unit/test_seed_model_version.py` — 75 collected (was 71): unrenderable numeric
  component rejected at construction, plus the renderability invariant.

**Review findings:** 12 patched (2 medium, 10 low), 0 deferred, 4 rejected, 0 intent gaps, 0
bad-spec loopbacks. Both rejections resting on a claim about the deferred-work ledger were
checked against the ledger itself — both entries are present and open, so none was re-appended.

**Verification:** `3436 passed, 9 deselected`; ruff on this story's files = 8 findings, all the
accepted `TRY004` convention; pyright 587 package-wide (unchanged baseline), 4 from this
story's files; `lint-imports` 3 kept, 0 broken. Every patched finding was reproduced live
against the shipped code before the fix and re-run after.

**Follow-up review recommended:** yes — this pass changed what the schema accepts (stripped
storage across every text field, blank anchors rejected, repeated merge keys rejected) and
moved class resolution earlier in the load path. The volume is 12 and the breadth spans the
loader's error contract, its YAML strictness and its validation ordering, so an independent
pass over the new semantics is worth one more look.
