---
title: 'Story 8.1: Marker grammar and the per-format registry'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '90cd67b4e9f1b17a9f106dace30f8bbbe978266c'
final_revision: '7f51bc983846d6cdccd315ccf689496d4745c3b7'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Every managed-region file format needs one canonical marker grammar, but no
comment-style registry, marker renderer/parser, or format validation exists yet — and Story
7.4's already-shipped manifest loader explicitly left the `format`/region-`name` validation
unenforced, forward-referencing this story to close it (evidenced in the S-7.4 spec's Review
Triage Log and two open entries in `deferred-work.md`).

**Approach:** Add `seed/regions/markers.py`: a `RegionFormat` registry (html/hash/slashstar),
begin/end marker render + parse functions, a body-only sha helper, and the region-name token
charset. Wire the two forward-referenced checks back into `seed/model/manifest.py`.

## Boundaries & Constraints

**Always:**
- Grammar (AD-53), byte-exact: `<open> marshal-seed:begin region=<name> model-version=<semver>
  sha=<8-hex> <close>` and `<open> marshal-seed:end region=<name> <close>`.
- Registry v1: `html` → `<!-- … -->` (for `.md`); `hash` → `# …` with **no** close token (for
  `.gitignore`/`.toml`/`.yml`/`.yaml`/shell); `slashstar` is a registered enum member but both
  render and parse raise `NotImplementedError` if selected.
- Format is selected only from the artifact's declared `format` — never sniffed from content
  or extension.
- `sha` is computed from the region **body only**; expose this as a small reusable function so
  the marker line is provably not self-referential.
- Region name is restricted to a marker-safe token charset (no raw space or `=`) —
  `[a-z0-9][a-z0-9-]*`, matching every name already in `templates/manifest.yaml`.
- Wire both checks back into the already-shipped `seed/model/manifest.py`: `ManifestEntry`
  validates `format` against the `RegionFormat` registry for `hybrid-managed-region` entries
  (raising `ValueError`, which the existing loader already wraps as `ManifestError`); `Region`
  validates `name` against the token charset. Both are pre-agreed, evidenced forward
  references, not scope creep — see the S-7.4 spec's Review Triage Log (`[reject] ... S-8.1 is
  on notice to close it`) and `deferred-work.md`'s two open entries naming this story.
- New exception type in `markers.py` roots on `pyforge.core.errors.PyforgeError` (Story 14.3
  convention: `class MarkerError(PyforgeError, ValueError): ...`).
- Reuse `seed/model/version.py`'s `ModelVersion`/`InvalidVersionError` for the `model-version`
  field — no second SemVer parser.
- A round-trip test proves render → parse → render is byte-identical for every operational
  registered format (html, hash).

**Block If:** None — the grammar, registry values, and name/sha token shapes are fully
specified by AD-53 plus the deferred-work ledger's own forward references; no decision here
requires human input.

**Never:**
- Scan a whole file for spans, reject nesting/overlap, or skip fenced code blocks — S-8.2.
- Resolve anchors, insert regions, or define the `<top>` anchor sentinel — S-8.4's AC already
  owns `<top>`'s semantics; do not resolve it here even though one ledger entry loosely
  mentions "S-8.1's grammar".
- Perform span substitution or touch `fs.replace_span()` — S-8.3 (and `seed/fs.py` does not
  exist yet; S-7.2/7.3 are `blocked`).
- Implement marker deletion / opt-out state — S-8.5.
- Normalize CRLF vs LF — that's S-8.2's document-level concern, not this line-level grammar.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Render html begin | `RegionFormat.HTML, "tiers", ModelVersion(1,0,0), "a1b2c3d4"` | `<!-- marshal-seed:begin region=tiers model-version=1.0.0 sha=a1b2c3d4 -->` | No error |
| Render hash end | `RegionFormat.HASH, "tiers"` | `# marshal-seed:end region=tiers` | No error |
| Round trip | render(fmt, ...) → parse → render | byte-identical output, for html and hash | No error |
| Slashstar selected | `render_begin(RegionFormat.SLASHSTAR, ...)` or `parse_marker_line(RegionFormat.SLASHSTAR, ...)` | n/a | raises `NotImplementedError` |
| Bad region name | name `"my region"` or `"My_Region"` | n/a | `MarkerError` (markers.py) / `ValueError` (manifest.py `Region`) |
| Bad sha | sha not exactly 8 lowercase hex chars | n/a | `MarkerError` |
| Body-only sha | same body, marker lines differ (region name changes) | `region_sha(body)` unchanged | No error |
| Unregistered manifest format | manifest entry `format: xml` | n/a | `ManifestError` naming the entry id + `xml` |
| Non-marker line | ordinary text line | n/a | `parse_marker_line` returns `None` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/regions/markers.py` -- NEW,
  this story's Surface: `RegionFormat`, per-format delimiter registry, `MarkerError`,
  `BeginMarker`/`EndMarker` frozen dataclasses, `region_sha`, `render_begin`/`render_end`,
  `parse_marker_line`, `REGION_NAME_PATTERN` (public, so `manifest.py` can reuse it).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/model/manifest.py` -- MODIFY:
  `ManifestEntry.__post_init__` (hybrid-class branch, ~line 319) converts/validates `format`
  via `RegionFormat`; `Region.__post_init__` (~line 243) validates `name` via
  `REGION_NAME_PATTERN`. Existing fixtures already only use `html`/`hash` and
  `[a-z0-9-]`-safe names (verified), so no other test in this file should regress.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/model/version.py` -- REFERENCE
  ONLY: reuse `ModelVersion`/`InvalidVersionError`, no changes.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_regions_markers.py` -- NEW.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_model_manifest.py` -- MODIFY: add
  the two closing cases (unregistered `format`, marker-unsafe region `name`).

## Tasks & Acceptance

**Execution:**
- [x] `seed/regions/markers.py` -- add `RegionFormat` StrEnum (`html`/`hash`/`slashstar`) + the
  delimiter registry + `MarkerError(PyforgeError, ValueError)` -- the per-format registry AC
- [x] same file -- add `BeginMarker`/`EndMarker` frozen dataclasses with `__post_init__`
  validating the name charset (+ 8-hex sha and `ModelVersion` type on `BeginMarker`) -- grammar
  structural validation
- [x] same file -- add `region_sha(body: str) -> str` (`hashlib.sha256(body.encode()).hexdigest()[:8]`,
  matching the repo's existing truncated-hash idiom) -- the body-only, non-self-referential AC
- [x] same file -- add `render_begin`/`render_end` (slashstar raises `NotImplementedError`) --
  rendering
- [x] same file -- add `parse_marker_line(fmt, line) -> BeginMarker | EndMarker | None`
  (slashstar raises `NotImplementedError`; non-marker lines return `None`; malformed marker
  lines raise `MarkerError`) -- parsing, needed for the round-trip proof
- [x] `seed/model/manifest.py` -- wire the `RegionFormat` registry check into
  `ManifestEntry.__post_init__`'s hybrid branch -- closes S-7.4's forward-referenced AC
- [x] same file -- wire `REGION_NAME_PATTERN` into `Region.__post_init__` -- closes the open
  deferred-work ledger entry on region-name tokens
- [x] `tests/unit/test_seed_regions_markers.py` -- cover every I/O Matrix row: per-format
  rendering, the html+hash round trip, slashstar `NotImplementedError` on both render and
  parse, name/sha validation errors, and the body-only sha proof
- [x] `tests/unit/test_seed_model_manifest.py` -- add an unregistered-`format` case and a
  marker-unsafe region-`name` case, each asserting `ManifestError` with a locator-and-reason
  `match=` regex (repo convention)

**Acceptance Criteria:**
- Given an artifact's declared format, when a region is rendered, then the comment style comes
  from the registry and is never inferred from the file's content or extension.
- Given `slashstar` is selected for render or parse, then `NotImplementedError` is raised and
  no marker text is produced.
- Given a region body, when its marker's sha is computed, then changing the region name or
  model-version alone (body unchanged) never changes the sha.
- Given a manifest entry with `format: xml`, when the manifest loads, then it raises
  `ManifestError` naming the entry id and the invalid format.
- Given a region named with a space or `=`, when the manifest loads, then it raises
  `ManifestError` naming the entry id and the offending name.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3 (medium 1, low 2)
- defer: 0
- reject: 9
- addressed_findings:
  - `[medium]` `[patch]` Edge Case Hunter: `render_begin`/`render_end`/`parse_marker_line` checked
    `fmt is RegionFormat.SLASHSTAR` by identity only. A caller passing the bare string
    `"slashstar"` (not the enum member) would skip that guard, and `StrEnum`'s value-based dict
    hashing means `_DELIMITERS["slashstar"]` still resolves — the unimplemented format would
    silently render/parse instead of raising. Same root cause let any other unregistered `fmt`
    value reach `_DELIMITERS[fmt]` as a bare, undocumented `KeyError`. Fixed with a
    `_coerce_format` helper (`RegionFormat(fmt)`, wrapped as `MarkerError` on failure) called at
    the top of all three public functions — a no-op for an already-valid member, and now raises
    `NotImplementedError`/`MarkerError` correctly either way. Added
    `test_bare_string_slashstar_still_raises_not_implemented` and
    `test_unregistered_fmt_raises_marker_error_not_key_error`.
  - `[low]` `[patch]` Blind Hunter: `_MARKER_TAG` was interpolated into `_BEGIN_BODY_PATTERN`/
    `_END_BODY_PATTERN` unescaped. Currently harmless (`"marshal-seed"` has no regex
    metacharacters) but a latent fragility on a future edit. Wrapped in `re.escape()`.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (duplicate root cause): `_strip_delimiters`
    requires an exact single space around delimiters, so a marker line with irregular
    whitespace (or a CRLF ending, deferred to S-8.2 by design) is not reliably recognized as a
    marker — verified by execution that this is not even uniform: extra whitespace after the
    open delimiter returns `None` (never reaches tag detection), while extra whitespace before
    the close delimiter reaches tag detection and then raises `MarkerError` (the leftover space
    fails the field grammar). The module's docstring previously overclaimed a single uniform
    outcome. Corrected both the module docstring and `parse_marker_line`'s own docstring to
    state plainly that only the exact canonical grammar is guaranteed recognized and that
    off-grammar variants are unspecified between the two outcomes — no parsing-logic change,
    since expanding tolerance is S-8.2's job, not this module's. Added
    `test_extra_whitespace_after_open_delimiter_returns_none_not_an_error` and
    `test_extra_whitespace_before_close_delimiter_raises_marker_error`, pinning both verified
    outcomes so the asymmetry can't silently drift.
  - `[reject]` Blind Hunter: claimed removing `"format"` from the trailing `(pin, format,
    legacy_of)` validation loop leaves non-hybrid entries' `format` unvalidated. False positive,
    confirmed by re-reading the full (unchanged) file: the pre-existing `else: if self.format is
    not None: raise ValueError("format is only valid on hybrid-managed-region entries...")`
    branch already forces `format` to `None` on every non-hybrid entry before that loop is ever
    reached — Edge Case Hunter independently found and discarded the same claim.
  - `[reject]` Blind Hunter: "no explicit format-only-valid-on-hybrid guard" — the guard named
    above already exists, unchanged by this diff.
  - `[reject]` Blind Hunter: "no test for the above gap" — moot, the gap does not exist.
  - `[reject]` Blind Hunter: `REGION_NAME_PATTERN` permits a trailing/doubled hyphen
    (`"tiers-"`, `"a--b"`). Real, but it is the exact `[a-z0-9][a-z0-9-]*` pattern this story's
    own spec Boundaries mandated verbatim (sourced from the S-7.4 deferred-work ledger entry
    this story closes) — no marker-grammar ambiguity results, since the region name is captured
    by `\S+` up to the next space regardless of hyphen placement. A spec-level decision, not an
    implementation defect.
  - `[reject]` Blind Hunter: region-name validation is duplicated between `markers.py`'s
    `_require_region_name` and `manifest.py`'s `Region.__post_init__` instead of the latter
    calling the former. Real duplication, but de-duplicating would change the exact error
    message a pre-existing, passing S-7.4 test
    (`test_whitespace_only_region_name_raises_manifest_error`) asserts via `match=` regex,
    which the spec's own Code Map explicitly required not to regress. The two checks also serve
    complementary purposes (the shared non-blank/type convention every string field in this
    schema uses, then the marker-specific charset) — kept as intentional layered validation
    rather than risk that test's contract for a style-only gain.
  - `[reject]` Blind Hunter: `region_sha` truncates to 8 hex characters (32 bits), no documented
    collision ceiling. Real, but the 8-hex-character sha is AD-53's own ratified grammar, not a
    choice this story's implementation made — not this story's decision to relitigate.
  - `[reject]` Blind Hunter: the `suffix=" or None"` message on the hybrid-branch `format` call
    is misleading, since `self.format` is already proven truthy by the preceding guard. Real but
    negligible (no test asserts this message text; a developer hitting it still understands the
    problem) — not worth the risk of touching a heavily-reviewed file for a one-word message
    accuracy nit.
  - `[reject]` Blind Hunter: the new `model → regions → model` cross-package import direction
    (`manifest.py` importing `regions/markers.py`, which imports `model/version.py`) blurs the
    `model`/`regions` directory split. Deliberate and evidenced — this story's own spec
    Boundaries cite the exact S-7.4 Review Triage Log entry authorizing this forward wiring, and
    `lint-imports` confirms no contract restricts it (re-verified this pass: 3 kept, 0 broken).
  - `[reject]` Blind Hunter: a blank region name and a charset-violating region name now produce
    two different `ValueError` messages in `Region.__post_init__`. A direct consequence of the
    layered-validation design kept above (not de-duplicated) — not a new defect on its own.



- **Why `manifest.py` changes belong in this story, not a follow-up:** S-7.4's Surface never
  included format/name-token validation — its own spec explicitly rejected adding it, on the
  documented grounds that "the registry does not exist yet" and "S-8.1 builds the registry and
  wires it in." Splitting this into a separate story would re-open a file that already carries
  3 review passes for a two-line addition with no new design surface.
- **Golden round-trip shape:**
  ```
  begin = render_begin(RegionFormat.HTML, "tiers", ModelVersion.parse("1.0.0"), region_sha(body))
  parsed = parse_marker_line(RegionFormat.HTML, begin)
  assert render_begin(RegionFormat.HTML, parsed.region, parsed.model_version, parsed.sha) == begin
  ```
- `ManifestEntry.format`'s declared type becomes `RegionFormat | None` (matching the existing
  `artifact_class: ArtifactClass` precedent, where the loader passes a raw string that
  `__post_init__` converts) rather than staying `str | None`.

### 2026-08-13 — Repair pass (deterministic verification failure)
- intent_gap: 0
- bad_spec: 0
- patch: 1 (low)
- defer: 1 (low)
- reject: 4
- addressed_findings:
  - `[low]` `[patch]` Blind Hunter: the story-8.1 `.memlog.md` reconciliation entry (written to
    close the `spec_surface_reconcile.py` gating failure below) overstated the intent contract's
    own "two open entries in deferred-work.md" framing as "both named this story to close them."
    Verified: only one of the two entries mentioning S-8.1 (region-name charset) is actually
    closed by this story; the second (`<top>` anchor sentinel) is explicitly out of scope per this
    story's own Never-section. Reworded the memlog entry's opening sentence to name only the
    entry actually closed, without touching the frozen `<intent-contract>` itself.
  - `[low]` `[defer]` Edge Case Hunter: the region-name `deferred-work.md` entry this story closes
    still reads `status: open` — no mechanism in this repo flips a deferred-work entry's status
    when the story that closes it lands. Recorded as `DW-FU-8-1` rather than hand-edited inline
    (repo convention: never modify an existing deferred-work entry in place).
  - `[reject]` Edge Case Hunter: baseline stamped from working-tree contents rather than pinned to
    commit `90cd67b4e9`. Verified false — `git status` was clean at that commit before this repair
    pass began; none of the 4 governed files were touched by the repair, only the memlog and the
    baseline JSON.
  - `[reject]` Edge Case Hunter: sibling specs sharing the same 4 paths were not re-evaluated.
    Verified false — `_collect_surfaces` shows `spec-pyforge-marshal` is the sole spec whose
    surface glob matches any of the 4 files.
  - `[reject]` Edge Case Hunter: repair-pass test/ruff/pyright/lint-imports counts are asserted as
    prose with no linked artifact. Matches this memlog file's own universal, pre-existing
    convention across every prior entry — not something this pass introduced.
  - `[reject]` Edge Case Hunter: the memlog's stamped sha1 might not reflect the final on-disk
    prose. Verified false — `sha1sum .memlog.md` matches the baseline's stamped `memlog` hash
    exactly, and `--write-baseline` was re-run after the last content edit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expect all tests pass,
  including the new `test_seed_regions_markers.py` and the two added manifest cases.
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` -- expect no new
  finding categories beyond this package's existing accepted `TRY004` convention.
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-marshal` -- expect no growth
  beyond the existing accepted baseline (env-artifact `reportMissingImports` +
  `reportArgumentType` on negative-path tests).
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- expect all contracts pass (no contract restricts `seed.model` importing `seed.regions`).

## Auto Run Result

Status: done

Summary: this session was a repair pass, not a re-implementation. The story's actual code
(`markers.py`, the `manifest.py` wiring, both test files) was already implemented, reviewed, and
committed in a prior session (`90cd67b4e9`); this pass touched no production code. The prior
session's own `python scripts/spec_surface_reconcile.py` verify step failed because
`spec-pyforge-marshal`'s `.memlog.md` was never updated to name the 4 changed/added files, so the
gate saw governed drift with no reconciling memlog movement.

Files changed this pass:
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`
  -- new "Surface reconcile" entry naming all 4 files story 8.1 touched, summarizing the change and
  the prior review pass, and recording this repair pass's own re-verification.
- `scripts/.spec-surface-baseline.json` -- re-stamped via `spec_surface_check.py --write-baseline
  --spec pyforge-marshal/spec-pyforge-marshal` (scoped to this one spec only).
- `_bmad-output/projects/pyforge-marshal/implementation-artifacts/deferred-work.md` -- new
  `DW-FU-8-1` entry (a review-pass finding, not required by the verify gate): the region-name
  `deferred-work.md` entry this story closes still reads `status: open`.

Review findings breakdown (this pass's own diff -- memlog + baseline stamp only): 1 patch (low,
a wording overclaim in the new memlog entry, fixed), 1 defer (low, `DW-FU-8-1` above), 4 reject
(all independently verified false or matching pre-existing convention). See Review Triage Log
above for detail.

Verification performed:
- `python scripts/spec_surface_reconcile.py` -- was rc=1 with 4 gating `drift` findings, now
  `OK: every tracked file governed or allowlisted; no drift.` (rc=0).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 3615 passed, 9 deselected.
- `ruff check` scoped to the 4 story-owned files -- 7 findings, all pre-existing accepted `TRY004`.
- `pyright` scoped to the 4 story-owned files -- only the accepted baseline (env-artifact
  `reportMissingImports` + `reportArgumentType` on one negative-path test).
- `lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- 3
  contracts kept, 0 broken.
- Confirmed via direct `pyforge.doctor.sources.chain.gather_spec_surface` invocation that
  `spec-pyforge-marshal` has zero FAIL and zero WARN findings after this repair (not just the
  reconcile script's own FAIL-only filter).

Residual risk: none identified for this story. `DW-FU-8-1` is a pre-existing ledger-hygiene gap
(no mechanism in this repo flips a deferred-work entry's `status:` when its closing story lands),
out of this story's own Surface, recorded for whoever next reconciles that ledger.

