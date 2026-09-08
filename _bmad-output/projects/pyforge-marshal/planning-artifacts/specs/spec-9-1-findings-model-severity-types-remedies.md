---
title: 'Story 9.1: Findings model -- severity, types, remedies'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
final_revision: '0cd6906ee4'
baseline_revision: 'dd9f9cc90d0bb4021a1472d83102defb550197b0'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Epic 9 ("Detect & Plan") has no shared vocabulary yet for a conformance problem --
every future `detect`/`plan`/`check` story needs one typed, closed shape to report a finding in,
with a remedy a human or CI can act on without reading Genesis's own source.

**Approach:** Add `seed/detect/findings.py`: a `Severity` ladder (`HARD`/`DRIFT`/`INFO`, the
design AD-54 borrows from `bmad_drift_check.py` without importing or vendoring it), a closed
`FindingType` enum (the 12 members the epics AC names), a `REMEDIES` mapping giving every member
a documented remedy string (NFR-M3, P-10), and a frozen `Finding` dataclass tying one instance of
each together plus stable `--json` serialization.

## Boundaries & Constraints

**Always:**
- `Finding` is `@dataclass(frozen=True)` with exactly the fields `severity`, `type`, `path`,
  `message`, `remedy` (the epics AC's literal shape), following this package's own
  `__post_init__`-validates-at-construction idiom (`ManifestEntry`, `Artifact`, doctor's own
  `Finding`).
- `Severity` and `FindingType` are `StrEnum` with kebab-case/uppercase wire values matching this
  package's existing `ArtifactClass` convention (kebab-case) and the borrowed ladder's own
  uppercase spelling (`HARD`/`DRIFT`/`INFO`, matching `pyforge.doctor.sources.factory`'s own port
  of the identical ladder).
- `FindingType` covers at minimum, and this story covers exactly, the 12 members the epics AC
  names: `artifact-missing`, `managed-file-modified`, `managed-region-modified`,
  `managed-region-missing`, `derived-stale`, `model-behind`, `state-invalid`,
  `never-write-violation`, `referenced-dep-missing`, `uncovered`, `legacy-present`, `opted-out`.
- `REMEDIES: Mapping[FindingType, str]` is an inline-literal `MappingProxyType` (mirrors
  `artifact.py`'s `CLASS_BEHAVIOR` -- never a rebindable module dict), one non-empty remedy per
  member.
- `Finding.__post_init__` coerces `severity`/`type` via their enum constructors (fail loud on an
  invalid value), rejects a blank `path`/`message`, and requires `remedy == REMEDIES[type]`
  exactly -- a `Finding` can never carry a hand-typed or mismatched remedy, and a `FindingType`
  member added without a `REMEDIES` entry raises immediately from every construction site, not
  only from the completeness test.
- A `Finding.new(severity, type, path, message)` classmethod is the sanctioned constructor for
  future call sites: it resolves `remedy` from `REMEDIES` so no caller hand-copies remedy text.
  Direct `Finding(...)` construction stays legal (tests, the completeness check).
- `Finding.to_json_dict()` returns `{severity, type, path, message, remedy}` with plain `str`
  values in that fixed key order -- the `--json` stability the epics AC requires.
- A unit test iterates every `FindingType` member and asserts `REMEDIES` has a non-empty `str`
  entry for it.

**Block If:** None -- the epics AC, AD-54, P-10, and this package's existing `artifact.py`/
`manifest.py` precedent fully specify the shape; no decision here requires human input.

**Never:**
- No import, vendor, or extraction of `bmad_drift_check.py` or any of its `local-recipes`-specific
  content (AD-54) -- this module borrows only the `Finding` shape and the severity ladder.
- No severity-per-type mapping or enforcement -- `severity` stays a free, caller-supplied field
  validated only against the closed `Severity` enum; which severity a given type actually carries
  at a real call site is a later detect/plan story's decision, not this model's.
- No `detect/inventory.py`, `detect/hashes.py`, or any real finding-emission call site -- this
  story ships the model only, exactly as Story 7.4 shipped `ManifestError` and Story 7.2 shipped
  `SeedError` without wiring either to a real raise site yet.
- No import from `pyforge.marshal.seed.errors` or any other `seed/*` module -- `findings.py` is a
  leaf under `detect/`, needing nothing beyond the stdlib.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid construction | `Finding.new(Severity.HARD, FindingType.ARTIFACT_MISSING, "AGENTS.md", "missing")` | instance with `.remedy == REMEDIES[FindingType.ARTIFACT_MISSING]` | No error |
| Direct construction, correct remedy | `Finding(Severity.INFO, FindingType.LEGACY_PRESENT, "docs/specs/x.md", "legacy", REMEDIES[FindingType.LEGACY_PRESENT])` | equal instance | No error |
| Direct construction, mismatched remedy | `Finding(Severity.HARD, FindingType.UNCOVERED, "x", "m", "wrong text")` | -- | `ValueError` |
| Blank path/message | `Finding.new(Severity.HARD, FindingType.UNCOVERED, "", "m")` | -- | `ValueError` |
| String coercion | `Finding.new("HARD", "uncovered", "x", "m")` | coerces to `Severity.HARD`/`FindingType.UNCOVERED` | No error |
| Invalid severity/type string | `Finding.new("CRITICAL", "uncovered", "x", "m")` | -- | `ValueError` |
| Enum completeness | iterate `FindingType` | every member has a non-empty `str` in `REMEDIES` | Test failure if any missing/empty |
| JSON stability | `finding.to_json_dict()` | `{"severity": "HARD", "type": "uncovered", "path": ..., "message": ..., "remedy": ...}`, fixed key order | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/findings.py` -- NEW, this
  story's Surface: `Severity`, `FindingType`, `REMEDIES`, `Finding`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_findings.py` -- NEW, covers the
  I/O Matrix plus the enum-completeness and JSON-serialization assertions.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/model/artifact.py` -- reference
  only: the `CLASS_BEHAVIOR`/`describe()` pairing-validation idiom this story mirrors.

## Tasks & Acceptance

**Execution:**
- [x] `seed/detect/findings.py` -- add `Severity(StrEnum)` (`HARD`, `DRIFT`, `INFO`) and
  `FindingType(StrEnum)` (the 12 kebab-case members) -- the closed vocabulary every later
  detect/plan story emits against
- [x] same file -- add `REMEDIES: Mapping[FindingType, str]` as an inline `MappingProxyType`
  literal, one non-empty remedy per `FindingType` member
- [x] same file -- add `Finding` (`@dataclass(frozen=True)`: `severity`, `type`, `path`,
  `message`, `remedy`) with `__post_init__` enum coercion, blank-field rejection, and
  remedy-matches-`REMEDIES` validation; add `Finding.new(...)` and `Finding.to_json_dict()`
- [x] `tests/unit/test_seed_detect_findings.py` -- cover every I/O Matrix row, including the
  `REMEDIES` completeness iteration and the `to_json_dict()` key-order/value assertion

**Acceptance Criteria:**
- Given `detect/findings.py`, when any future check produces a finding, then it is expressible as
  a `Finding(severity, type, path, message, remedy)` with `severity` drawn from `Severity`.
- Given `FindingType`, when a test iterates its members, then every member has a non-empty `str`
  entry in `REMEDIES`.
- Given a `FindingType` member added without a matching `REMEDIES` entry, when any code
  constructs a `Finding` of that type, then it raises immediately (`KeyError`-derived `ValueError`
  from `__post_init__`), and the completeness test also fails.
- Given a `Finding` instance, when `.to_json_dict()` is called, then the result is stable,
  JSON-serializable, and uses plain `str` values for `severity`/`type`.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 1, low 2)
- defer: 0
- reject: 11
- addressed_findings:
  - `[medium]` `[patch]` Edge Case Hunter + Blind Hunter (independently): `Finding.new(...)` looked
    up `REMEDIES[resolved_type]` via a raw subscript, so a `FindingType` member missing from
    `REMEDIES` would raise a bare `KeyError` from the sanctioned constructor, while direct
    `Finding(...)` construction raised the documented, friendly `ValueError` via
    `__post_init__`'s own `try/except`. Currently latent (all 12 members have entries) but reachable
    the moment a future member is added without one -- and `.new()` is the primary call path.
    Extracted `_remedy_for(finding_type)`, routed both `__post_init__` and `Finding.new` through it,
    and added a monkeypatch-based test exercising the previously-dead missing-entry path through
    both construction routes, asserting identical `ValueError` messages.
  - `[low]` `[patch]` Blind Hunter: `path`/`message` validation checked `.strip()` truthiness but
    stored the unstripped value verbatim (`"  x  "` passed and leaked into `to_json_dict()`
    padded). Now stripped and stored via `object.__setattr__` in `__post_init__`, with a new test.
  - `[low]` `[patch]` Blind Hunter: `test_finding_type_has_exactly_12_members` asserted only a
    count, so a typo'd/renamed member would still pass. Replaced with an exact set-equality
    assertion against the epics AC's 12 literal kebab-case values.
  - `[reject]` Blind Hunter: double coercion in `Finding.new()` (`Severity(severity)` re-coerced by
    `__post_init__`) is "pointless work." Deliberate: `type` must be pre-resolved to key the
    `REMEDIES` lookup regardless, and resolving `severity` the same way keeps `new()`'s own
    signature precisely typed rather than widened to `Any` -- not a bug, a stated design choice.
  - `[reject]` Blind Hunter: `type` shadows the builtin (field name and `new()` parameter). This
    codebase's ruff config carries no `[tool.ruff]` section at all (verified: default rule set,
    no flake8-builtins/A00x selected), and the name matches the epics AC's own literal
    `Finding(severity, type, path, message, remedy)` constructor shape verbatim.
  - `[reject]` Blind Hunter: `REMEDIES`'s "read-only" docstring claim (`MappingProxyType`) is
    asserted but not tested (no test asserts mutation raises `TypeError`). Matches this package's
    own established precedent -- `artifact.py`'s identical `CLASS_BEHAVIOR` carries the same
    design and the same absence of a dedicated immutability test.
  - `[reject]` Blind Hunter: only 3 of 12 `REMEDIES` entries are pinned by content-specific
    assertions elsewhere; the rest are checked only for non-blankness. The new exact-set-equality
    test (above) now pins every member's wire value; pinning all 12 remedy STRINGS verbatim would
    test prose content with zero behavior at stake -- disproportionate, matching this package's
    own `test_seed_errors.py` precedent for rejecting string-content-trivia coverage.
  - `[reject]` Blind Hunter: architecture/PRD citations (AD-54, P-10, NFR-M3, the `detect`
    dependency-rule ordering, parity with `pyforge.doctor.sources.factory`) are prose, unenforced
    by any test/lint/import-linter rule. True of essentially every docstring citation in this
    codebase; no code or spec change follows, and the "leaf, zero `pyforge.marshal.*` imports"
    invariant this module actually needs IS enforced structurally (import-linter's AD-3 contract
    covers `pyforge.marshal.seed` as a whole; nothing in this file imports a sibling module).
  - `[reject]` Blind Hunter: `path` has no shape validation beyond non-blank (absolute paths,
    `../` traversal). Explicitly out of this story's Never boundary -- no `detect/inventory.py`
    exists yet to populate real paths; that validation belongs to the story that actually walks a
    repo, not this pure model.
  - `[reject]` Blind Hunter: the 12 `REMEDIES` strings mix imperative/declarative/advisory tone.
    Cosmetic prose-style preference with zero behavior or contract impact.
  - `[reject]` Blind Hunter: no `dataclass(frozen=True, slots=True)`. Speculative micro-optimization
    not requested by any AC, and not this package's own convention -- neither `artifact.py`'s
    `Artifact`/`ClassBehavior` nor `manifest.py`'s `ManifestEntry`/`Region` use `slots=True` either.
  - `[reject]` Blind Hunter: "uneven rigor" between `Finding.new` and direct construction for
    `path`/`message`. Mischaracterized -- `__post_init__` validates ALL fields identically
    regardless of entry point; that is the entire point of `__post_init__`-based validation over
    constructor-only checks.
  - `[reject]` Blind Hunter: no `__all__`. Not this package's convention -- `artifact.py`,
    `manifest.py`, and `version.py` (the three modules this story explicitly mirrors) declare none
    either; adding one here would be a new, unprecedented pattern, not a fix.
  - `[reject]` Edge Case Hunter: an unhashable `severity`/`type` (e.g. a `list`) raises `TypeError`
    from the `StrEnum` constructor, not the docstring's stated `ValueError`. Real but disproportionate
    -- matches this package's own `spec-7-2`/`test_seed_errors.py` precedent for rejecting
    adversarial-input hardening when every real call site in this codebase only ever passes an
    enum member or a matching plain string, never an arbitrary unhashable object.

### 2026-08-13 — Review pass (deterministic-verification repair)
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 0, low 2)
- defer: 1
- reject: 6
- addressed_findings:
  - `[low]` `[patch]` Blind Hunter: the reconciliation memlog entry (added by this repair pass,
    not the story's own code) said `Finding`'s `.new()` constructor "validates its remedy against
    `REMEDIES`" -- the validation actually lives in `__post_init__`, which fires on every
    construction path; `.new()` only pre-resolves a correct remedy so that check never has
    anything to catch. Reworded to attribute the check correctly.
  - `[low]` `[patch]` Blind Hunter: the same memlog entry's re-verification note stated ruff was
    "clean on both new files" but only said pyright reported "zero errors attributable to
    `findings.py` itself," leaving `test_seed_detect_findings.py`'s own pyright status unstated.
    Reworded to say both files explicitly: `findings.py` zero errors, the test file carrying only
    the same systemic unresolved-import pattern every sibling test file already carries.
  - `[reject]` Blind Hunter: the memlog's `updated:` frontmatter timestamp was not bumped by this
    entry. Checked live via `git log -p` on the file: not "an unbroken per-commit pattern" as
    claimed -- roughly half of recent append commits (including the immediately-prior 14-4 entry)
    do not bump it either. This entry's behavior matches live, current precedent.
  - `[reject]` Blind Hunter: the memlog's pyright claim (582 errors, `reportMissingImports`,
    `test_findings.py` in the same class) "does not reproduce" -- Blind Hunter's own counter-run
    used a different pixi environment (`-e pyforge-marshal`) than the story's own declared
    Verification command (`-e local-recipes`). Re-ran the exact declared command directly: 582
    errors, `reportMissingImports`, `test_findings.py` and `test_seed_detect_findings.py` both
    show the identical unresolved-`pyforge.marshal`-import pattern, `findings.py` itself clean --
    the entry's claim holds exactly under the command it cites.
  - `[reject]` Blind Hunter: point-in-time tool counts baked into the memlog with no "as of"
    qualifier. True of every entry in this file's multi-week history, not a defect introduced by
    this one; reformatting the convention is out of scope for a reconciliation-only pass.
  - `[reject]` Blind Hunter: "no narrower sibling spec claims either path" is near-tautological
    given this Spec's one broad `src/shared/packages/pyforge-marshal/**` glob. Accurate but
    cosmetic phrasing matching this file's own established convention; zero behavior/contract
    impact.
  - `[reject]` Blind Hunter: the entry doesn't state whether this was the only outstanding drift
    repo-wide. Directly checked: `python scripts/spec_surface_reconcile.py` (unscoped, whole repo)
    returned `OK: every tracked file governed or allowlisted; no drift.` after this pass -- the
    underlying concern does not hold, and no prior entry in this file states this either.
  - `[reject]` Blind Hunter: `REMEDIES[NEVER_WRITE_VIOLATION]`'s remedy text ("file an issue
    against Genesis") is not independently actionable. Out of scope for this diff -- `findings.py`'s
    `REMEDIES` content is from the ORIGINAL story diff, already reviewed; the prior 2026-08-13
    pass already rejected the identical class of remedy-content-quality objection ("pinning all 12
    remedy strings verbatim would test prose content with zero behavior at stake").
  - `[defer]` Blind Hunter (self-certifying stamp, no independent reviewer named before
    `--write-baseline`) + Blind Hunter (unlocked concurrent read-modify-write of
    `scripts/.spec-surface-baseline.json`) + Edge Case Hunter (`--write-baseline --spec` merges
    EVERY file the named spec governs, not just the paths a reconciliation entry names --
    CONFIRMED verdict): all three describe facets of one pre-existing design gap in
    `scripts/spec_surface_check.py`, entirely outside this story's own Surface. Deduplicated into
    one ledger entry, `DW-FU-9-1`.

## Design Notes

**Why `remedy` is validated against `REMEDIES`, not left free-text.** NFR-M3 and P-10 both frame
remedy as a property of the *type*, documented once ("every finding type is documented with a
remedy" / "one enum member with a documented remedy string"), not a per-instance convenience a
caller could word differently each time. Validating `remedy == REMEDIES[type]` in
`__post_init__` makes that invariant structural rather than a convention callers might drift from
-- the same reasoning `Artifact.__post_init__` already applies to its own entry/behavior pairing
in this exact package. `Finding.new(...)` exists so no real call site has to hand-copy the
`REMEDIES` text (and risk a typo raising `ValueError`) to get a valid instance.

**Why no severity-per-type table.** Individual epics ACs pin specific type/severity pairings for
their own call sites (9.3: hash-mismatch types are always `HARD`; 9.4: `legacy-present` is always
`INFO`; 9.5: `uncovered` is always `HARD`), but nothing in this story's own AC asks for that as a
structural constraint, and at least one type (`referenced-dep-missing`) has no severity pinned
anywhere yet. Baking a severity table in now would assert an invariant this story cannot verify
for every member and that a later story might contradict.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expect all tests pass, including
  the new test file.
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` -- expect no new
  finding categories.
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-marshal` -- expect no growth
  beyond the existing accepted baseline.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- expect all contracts pass (this module imports nothing from `pyforge.marshal.*`).

## Auto Run Result

**Summary.** This story's code (`findings.py`, `test_seed_detect_findings.py`) was already
implemented and reviewed by a prior session (commit `dd9f9cc90d`), but the run's own deterministic
verify step -- `python scripts/spec_surface_reconcile.py` -- failed: both new files sit under
`pyforge-marshal/spec-pyforge-marshal`'s governed surface, and that Spec's `.memlog.md` had not
named them. This pass repaired that governance drift only; the intent-contract and story code are
byte-identical to the prior session.

**Files changed (this pass, outside the intent-contract):**
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`
  -- new `## Surface reconcile 2026-08-13 — story 9-1 landing` entry naming both governed paths,
  the landing commit, CAP-13, and real re-verification results.
- `scripts/.spec-surface-baseline.json` -- re-stamped, scoped to `pyforge-marshal/spec-pyforge-marshal`
  only, via `python scripts/spec_surface_check.py --write-baseline --spec pyforge-marshal/spec-pyforge-marshal`.

**Review findings breakdown (this pass):** 2 patch (both low, wording-precision fixes to the new
memlog entry: a `.new()`/`__post_init__` validation misattribution, and an asymmetric
ruff-vs-pyright coverage statement), 1 defer (`DW-FU-9-1` -- a pre-existing `scripts/
spec_surface_check.py --write-baseline --spec` design gap: spec-scoped rather than path-scoped,
and unlocked against concurrent writers; entirely outside this story's own Surface), 6 reject (one
factually disproven -- the `updated:` frontmatter claim; one reproduced against the wrong pixi
environment -- the pyright claim, re-verified accurate under the story's own declared command; the
rest cosmetic/out-of-scope). Follow-up review not recommended: low-consequence, localized fixes
only.

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` -- exit 0, `OK: every tracked file governed or
  allowlisted; no drift.` (was failing with 2 gating findings at session start).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 3575 passed, 9 slow deselected.
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` -- 186 pre-existing
  findings, none in either new file (targeted `ruff check` on both: `All checks passed!`).
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-marshal` -- 582 pre-existing
  `reportMissingImports` findings (the accepted baseline this story's own Verification section
  anticipates); zero attributable to `findings.py`, `test_seed_detect_findings.py` carries only the
  same systemic pattern every sibling test file already carries.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- clean, 3 contracts kept, 0 broken.

**Residual risks.** `DW-FU-9-1` (deferred, see above) is a real but pre-existing tooling-safety
gap in `spec_surface_check.py`, unrelated to this story's own code; confirmed non-live in this
instance (no unrelated file drifted at stamp time).

