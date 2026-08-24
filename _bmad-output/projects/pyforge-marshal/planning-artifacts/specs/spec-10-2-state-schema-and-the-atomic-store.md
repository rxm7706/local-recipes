---
title: 'State schema and the atomic store'
type: 'feature'
created: '2026-08-14'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
difficulty: 'heavy'
baseline_revision: '64e717d13554938e03ceac5a6a98c2aae407b957'
final_revision: 'd640b48aa0d738166eca369d398f72eab3275535'
---

<intent-contract>

## Intent

**Problem:** Genesis has no state. `seed/state/` is an empty package, so `detect/hashes.py`'s
`check_managed_file(..., recorded_sha)` takes a value nobody can supply, `detect/inventory.py` and
`plan/build.py` both document "no read of `.marshal/seed-state.yml`", and `StateInvalid` (exit 5)
has no raise site. Without a tool-owned, schema-validated state file, the repo and Genesis's
belief about it can silently disagree — the `bmad-switch` marker failure this architecture is
written against (P-08, AR-6).

**Approach:** Build `seed/state/schema.json` (Draft 2020-12, closed) and `seed/state/store.py`
exposing a frozen `SeedState` plus `read_state()` (schema-validated on every read; every
malformation becomes `StateInvalid`, never a traceback) and `write_state()` (validate → serialize
→ exactly one atomic replace, routed through `seed/fs.py`). Consumers — the apply runner, the
verbs, migrations — are Stories 10.3–10.7 and Epic 11.

## Boundaries & Constraints

**Always:**
- The document has exactly eleven top-level keys — `model_version`, `seed_model_version`,
  `adopted_at`, `last_update`, `mode`, `agents[]`, `managed[]`, `skips[]`, `legacy[]`,
  `migrations_applied[]`, `opted_out[]` (FR-102 plus `opted_out[]`, which the epics AC adds).
  `schema.json` `require`s all eleven and sets `"additionalProperties": false`.
- Every read validates against the packaged `state/schema.json` with
  `jsonschema.Draft202012Validator` before any field is consumed. On the **read** path every
  failure mode — unreadable file, non-UTF-8, invalid YAML, duplicate mapping keys, non-mapping
  root, schema violation — is converted to `StateInvalid(message, remedy=...)` (exit 5), so no
  `jsonschema`, `yaml`, `OSError`, or `UnicodeDecodeError` type escapes `read_state` (FR-104:
  "never a traceback"). The **write** path converts only its own schema failure; an `OSError` or
  `NeverWriteViolation` from `fs.write` propagates unchanged, because a failed write means the
  environment refused, not that state is invalid.
- An **absent** state file is not invalid: `read_state` returns `None`. Story 10.5 must run
  `check` against a never-adopted repo, and 10.1's `check` AC says absent artifacts are reported,
  not raised.
- `write_state` validates the serialized document against the same schema **before** writing, then
  writes through `pyforge.marshal.seed.fs.write` — the never-write guard, which delegates to
  `pyforge.core.atomic_write.atomic_write_bytes`. `store.py` implements no temp-file or rename
  mechanics of its own (P-01; P-08's "one atomic replace"; the CAP-7 sole-ownership meta test in
  `pyforge-core/tests/meta/test_atomic_write_sole_ownership.py` fails the build otherwise).
- `store.py` imports only stdlib, `yaml`, `jsonschema`, `seed.errors`, `seed.fs`, and
  `seed.model.version`. It never imports `seed.detect`, `seed.plan`, `seed.apply`, `seed.verbs`, or
  `seed.engine` — the architecture's no-upward-imports rule. Converting a `StateInvalid` into a
  `FindingType.STATE_INVALID` finding is `detect`'s job, not this module's.
- Genesis never reads, parses, or hand-edits `.marshal/.copier-answers.yml` (FR-105, AD-52):
  `store.py` contains no reference to that path. State is the single source of truth for Copier
  answers, re-supplied via `data=` — `copier_data(state)` is the projection that does it.
- `managed[]` entries record `id`, `path`, `class`, `body_sha`, and `inserted_region_span` — enough
  for a future `eject` to withdraw the tool's claim without touching content (AD-58). `body_sha`
  carries `detect/hashes.py::hash_content`'s shipped shape (8 lowercase hex), enforced by a schema
  `pattern`; `class` is constrained to `ArtifactClass`'s six wire values.
- Every written file opens with a prominent do-not-hand-edit comment header (FR-103), re-emitted on
  every write and ignored on read.
- `.marshal/seed-state.yml` stays git-tracked (FR-107): `templates/files/model-ignores.gitignore.j2`
  already ignores only `.marshal/plan.json` and comments why — it ships correct and is not touched.

**Block If:** `pyforge.core.atomic_write` is missing from the environment (DW-FU-14-2 records that
Story 14.2's commit was never merged into `loop/pyforge-marshal`, though `seed/fs.py` imports it at
this worktree's HEAD) — HALT rather than hand-rolling a second atomic write.

**Never:**
- Never add a `manifest.yaml` entry for `.marshal/seed-state.yml`. That roster is pinned by Story
  7.5, the coverage gap is an open separately-scoped deferred-work item, and
  `engine/copier.py::_GENESIS_OWNED_PATHS` already allow-lists the path.
- Never build the apply runner, any verb, CLI wiring, migrations, or `eject` (10.3–10.7, Epic 11;
  AD-58: "No eject verb ships in V1").
- Never invent state fields beyond the eleven — no `slug`, no free-form `answers` map. A twelfth
  field needs a PRD/architecture amendment first.
- Never modify `detect/hashes.py`, `detect/inventory.py`, or `plan/build.py` to consume state;
  those seams belong to their own stories.
- Never add a seventh `SeedError` leaf — `tests/unit/test_seed_errors.py` asserts exactly six.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Round-trip | valid `SeedState`, writable repo | `write_state` then `read_state` returns an equal `SeedState`; file carries the header | No error expected |
| Never adopted | repo with no `.marshal/seed-state.yml` | `read_state` returns `None` | No error expected |
| Schema violation | file missing `mode`, or with an unknown key, or `body_sha: "ZZ"` | nothing returned | `StateInvalid` naming the offending field path and reason (exit 5) |
| Malformed input | invalid YAML, duplicate mapping keys, non-UTF-8 bytes, or a non-mapping root | nothing returned | `StateInvalid`; no `yaml.YAMLError` / `UnicodeDecodeError` / `OSError` escapes |
| Invalid state written | `SeedState` whose document fails the schema (e.g. malformed timestamp) | nothing written; any existing file byte-identical | `StateInvalid` raised before the first write |
| Mid-apply failure | 4 artifact writes queued, the 2nd raises; state write never reached | pre-existing state file byte-identical, no `.tmp` residue in `.marshal/` | the artifact write's own error propagates unchanged |
| Guarded path | state path matched by a `never_write` pattern | nothing written | `NeverWriteViolation` (exit 4) from `fs`, propagated unwrapped |

</intent-contract>

## Code Map

Paths under `src/shared/packages/pyforge-marshal/` unless noted; module prefix
`src/pyforge/marshal/`.

- `.../seed/state/schema.json` -- NEW. Draft 2020-12, `$id: urn:local-recipes:pyforge-marshal:seed-state.v1`,
  closed, mirroring `src/pyforge/marshal/schemas/journal.json`'s house style.
- `.../seed/state/store.py` -- NEW. `SeedState`, `ManagedArtifact`, `LegacyArtifact`,
  `RegionSpanRecord`, `state_path`, `read_state`, `write_state`, `copier_data`,
  `seed_model_version`, `utc_timestamp`.
- `.../seed/state/__init__.py` -- currently 0 bytes; re-export the public symbols with `__all__`.
- `.../seed/fs.py` -- consumed unmodified: `write(path, data, *, repo_root, never_write)` and
  `NeverWrite(patterns=...)`. It is the only write path (P-01) and already delegates atomically.
- `.../seed/errors.py` -- consumed unmodified: `StateInvalid` (exit 5, first real raise site here)
  and `InternalError` (exit 10). Both require a non-blank `remedy=` kwarg.
- `.../seed/detect/hashes.py` -- `hash_content` defines the `body_sha` shape (8 lowercase hex);
  not modified.
- `.../seed/regions/parse.py` -- `RegionSpan(name, ..., body_span: tuple[int, int])` is the
  precedent `inserted_region_span` mirrors (UTF-8 byte offsets, body only, markers excluded).
- `.../seed/model/manifest.py` -- reference only: `_StrictLoader`'s duplicate-key rejection and
  `load_manifest`'s four-`except` error funnel are the shapes to mirror; `ArtifactClass` supplies
  the six `class` wire values.
- `.../seed/model/version.py` -- `ModelVersion.parse` / `__str__` round-trips `model_version`.
- `.../seed/engine/copier.py` -- `_GENESIS_OWNED_PATHS` already allow-lists the state path;
  `MaterializeRequest.data` is `copier_data`'s eventual consumer.
- `src/shared/packages/pyforge-core/src/pyforge/core/atomic_write.py` -- the sole atomic primitive,
  reached only via `fs.write`.
- `.../tests/unit/test_seed_state_store.py` -- NEW.
- `pyproject.toml` / `pixi.toml` -- **no change**: `jsonschema>=4.25` and `PyYAML>=6.0` are already
  declared in both, and `test_manifest_sync.py` enforces that they stay in sync.

## Tasks & Acceptance

**Execution:**
- [x] `seed/state/schema.json` -- author the closed Draft 2020-12 schema: eleven required
  properties; `model_version`/`seed_model_version` as SemVer-ish strings; `adopted_at`/`last_update`
  as `pattern`-checked RFC-3339 UTC timestamps (`format` alone is not enforced by jsonschema);
  `mode` as `enum: ["init", "adopt"]`; `agents` as a unique array of `^[a-z][a-z0-9-]*$`; `managed`
  as objects of `{id, path, class, body_sha, inserted_region_span}` with `class` enumerating
  `ArtifactClass`'s wire values, `body_sha` `^[0-9a-f]{8}$`, and `inserted_region_span` either
  `null` or `{name, start, end}` with non-negative integers; `skips` an array of glob strings;
  `legacy` objects of `{id, path, legacy_of}` mirroring `LegacyRecord`; `migrations_applied` a
  unique array of version strings; `opted_out` a unique array of `^[a-z0-9][a-z0-9-]*#[a-z0-9][a-z0-9-]*$`
  (`<artifact-id>#<region>`, Story 8.5's shape). -- the wire contract every read is checked against.
- [x] `seed/state/store.py` -- define frozen dataclasses `RegionSpanRecord(name, start, end)`,
  `ManagedArtifact(id, path, artifact_class, body_sha, inserted_region_span)`, `LegacyArtifact(id,
  path, legacy_of)`, and `SeedState` (the eleven fields, tuples not lists), each with
  `to_json_dict()` / `from_json_dict()` mirroring `plan/types.py`'s house convention. -- the typed
  in-memory form callers use instead of raw dicts.
- [x] `seed/state/store.py` -- implement `state_path(repo_root) -> Path` (mirrors
  `plan/build.py::default_plan_path`), `_load_schema()` via
  `importlib.resources.files("pyforge.marshal.seed.state") / "schema.json"` (cached), and a
  `_StrictLoader(yaml.SafeLoader)` rejecting duplicate and merge keys. -- the read primitives.
- [x] `seed/state/store.py` -- implement `read_state(repo_root) -> SeedState | None`: absent →
  `None`; read bytes → decode UTF-8 → `yaml.load(_StrictLoader)` → require a mapping root →
  `Draft202012Validator(...).validate(...)` → `from_json_dict`. Every failure funnels to
  `StateInvalid(message, remedy=...)` with `raise ... from exc`. -- FR-104's "finding, not a crash".
- [x] `seed/state/store.py` -- implement `write_state(state, *, repo_root, never_write) -> None`:
  `to_json_dict` → validate against the schema (raise `StateInvalid` on failure, before any I/O) →
  `yaml.safe_dump(sort_keys=False, allow_unicode=True, default_flow_style=False)` → prepend the
  do-not-hand-edit header → single `fs.write(...)` call. -- P-08's one atomic replace, P-01's write
  boundary, FR-103's header.
- [x] `seed/state/store.py` -- implement `seed_model_version() -> str` via
  `importlib.metadata.version("pyforge-marshal")` (`PackageNotFoundError` → `InternalError`),
  `utc_timestamp(moment=None) -> str` emitting the schema's exact timestamp shape, and
  `copier_data(state) -> dict[str, Any]` projecting `model_version`, `seed_model_version`, `mode`,
  and `agents` for `MaterializeRequest.data`. -- A-05's two clocks, one format owner, and FR-105's
  "answers re-supplied from state".
- [x] `seed/state/__init__.py` -- re-export the public symbols with an explicit `__all__`, matching
  `seed/engine/__init__.py`. -- the package's front door.
- [x] `tests/unit/test_seed_state_store.py` -- cover every I/O-matrix row plus: schema
  self-validity (`Draft202012Validator.check_schema`) and `$schema`/`$id`/`additionalProperties`
  assertions; the schema's `class` enum equals `{c.value for c in ArtifactClass}` (drift guard);
  eject reconstruction from `state.managed` alone (AD-58); header presence and round-trip through
  it; the fault-injection sequence (monkeypatch `seed.fs.atomic_write_bytes` to raise on the 2nd
  call, assert the pre-existing state file is byte-identical and `.marshal/` holds no `.tmp`
  residue); `never_write` rejection surfacing `NeverWriteViolation`; and an assertion that
  `store.py`'s source contains neither `.copier-answers.yml` nor `os.replace`/`mkstemp`. -- proves
  the matrix, AD-58, P-01, P-08, FR-103, FR-105.

**Acceptance Criteria:**
- Given a written state file, when it is opened by a human, then the first line is a comment and
  the header block says in plain words that the file is tool-owned and must not be hand-edited
  (FR-103).
- Given `read_state` is handed any malformed input, when it fails, then the raised exception is
  exactly `StateInvalid` (`exit_code == 5`) carrying a non-blank remedy, and `SeedError` still has
  exactly six subclasses.
- Given `state.managed` alone, when a test reconstructs the removal set, then every managed
  artifact yields its path, class, recorded hash, and — for a `hybrid-managed-region` entry — the
  region name and body span needed to strip the region without touching surrounding content
  (AD-58).
- Given `store.py`, when its imports are inspected, then it imports no module from `seed.detect`,
  `seed.plan`, `seed.apply`, `seed.verbs`, or `seed.engine`, and no second atomic-write
  implementation exists (`pyforge-core`'s CAP-7 meta test stays green).
- Given `templates/files/model-ignores.gitignore.j2`, when the story lands, then it is byte-
  identical to its pre-story content — `.marshal/plan.json` ignored, `.marshal/seed-state.yml`
  tracked (FR-107).

## Spec Change Log

## Review Triage Log

### 2026-08-14 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 19: (high 0, medium 9, low 10)
- defer: 1: (medium 1)
- reject: 2: (medium 1, low 1)
- addressed_findings:
  - `[medium]` `[patch]` `_StrictLoader` never saw duplicates authored inside a merge-anchored
    node — PyYAML's `flatten_mapping` splices the anchor's pairs in without calling
    `construct_mapping` on it, so `<<: &s / mode: init / mode: adopt` loaded as `mode: adopt`,
    the exact last-wins outcome the class exists to prevent. Merge keys are now refused outright
    (state is tool-written and never contains anchors), matching the spec task's literal wording.
  - `[medium]` `[patch]` Every anchored `schema.json` pattern admitted a trailing newline
    (jsonschema compiles `pattern` with Python `re`, whose `$` matches before a final `\n`), so
    `body_sha: "0123abcd\n"` validated — falsifying the schema's own DW-FU-9-3 closure claim.
    All patterns now terminate with `(?![\s\S])`, portable across ECMA-262 and Python.
  - `[medium]` `[patch]` `frozen=True` was a half-promise: list-valued fields passed straight
    through, so `read_state` returned a non-equal object and `state.agents.append(...)` mutated
    the "frozen" instance. All six sequence fields now coerce to tuples and reject wrong-typed
    items, mirroring `fs.NeverWrite.__post_init__`.
  - `[medium]` `[patch]` The same defect on the one field a JSON Schema can never police —
    `model_version` is typed `ModelVersion` but a plain `str` serialized identically and came
    back as a `ModelVersion`, a silently non-equal round-trip. Found during post-patch
    verification, not by either reviewer; now rejected at construction.
  - `[medium]` `[patch]` Duplicate `managed[]` claims validated (same `id`/`path`, different
    `body_sha`), making the recorded-hash lookup order-dependent; duplicate `managed[].id` /
    `managed[].path` / `legacy[].id` are now rejected, the invariant `model/manifest.py` already
    enforces for manifest entries.
  - `[medium]` `[patch]` Inverted region spans validated (`start=100, end=5`), so AD-58's eject
    splice would duplicate bytes instead of stripping a region; `RegionSpanRecord` now enforces
    `0 <= start <= end`, as `fs.replace_span` already does.
  - `[medium]` `[patch]` `class` and `inserted_region_span` were uncoupled — a
    `hybrid-managed-region` entry with a null span and a `referenced` entry with a populated span
    both validated, contradicting the schema's own description. Now an iff, enforced in both
    `ManagedArtifact.__post_init__` and an `if`/`then`/`else` in the schema.
  - `[medium]` `[patch]` The fault-injection test replaced `fs.atomic_write_bytes` wholesale, so
    no temp file was ever created and "no `.tmp` residue" was true by construction. The fault now
    lands inside the real atomic write, after the temp file exists.
  - `[medium]` `[patch]` No test covered a state with empty collections — the normal fresh-`init`
    shape, which `yaml.safe_dump` renders in flow style (`skips: []`) regardless of
    `default_flow_style=False`, making the one YAML-shape assertion vacuous. Added a full
    round-trip for that shape and scoped the assertion honestly.
  - `[low]` `[patch]` A `!!map`-tagged scalar raised a bare `ValueError` out of the pre-scan,
    escaping the read path's `StateInvalid`-only contract; node type is now checked first.
  - `[low]` `[patch]` A missing or corrupt packaged `schema.json` propagated raw out of
    `read_state` (the `try` caught only `ValidationError`); now `InternalError` (exit 10) — a
    broken install is not invalid state.
  - `[low]` `[patch]` `migrations_applied` uniqueness was string-wise, but `ModelVersion` ignores
    build metadata, so `["1.2.0", "1.2.0+build"]` named one version twice and could re-run a
    migration; now deduped by parsed version.
  - `[low]` `[patch]` `opted_out`'s artifact half required lowercase-kebab while `managed[].id`
    accepted any non-blank string, making a legal entry's opt-out unrepresentable; the artifact
    half now accepts any non-blank token without `#` or whitespace.
  - `[low]` `[patch]` A dangling symlink at the state path read as "never adopted", so `init`
    could re-establish over an existing installation; a broken link is now `StateInvalid`.
  - `[low]` `[patch]` The "no second atomic-write implementation" guard was a substring grep over
    the whole file including prose, with a deny-list missing `os.rename`, `Path.rename`,
    `shutil.move`, `mkdtemp`, and write-mode `open`; it is now AST-based and widened.
  - `[low]` `[patch]` The header promised a hand edit is "overwritten without warning or reported
    as invalid state" — untrue of a schema-valid edit, which is silently believed until the next
    write. Reworded to say so.
  - `[low]` `[patch]` `write_state`'s docstring omitted the bare `ValueError` `fs._guard` raises
    for a non-directory `repo_root` — outside the `SeedError` taxonomy, so a caller catching
    `(SeedError, OSError)` gets a traceback. Documented, not converted (that would fight `fs.py`).
  - `[low]` `[patch]` Rejected values were interpolated whole into operator-facing messages,
    turning a large malformed document into a multi-kilobyte single-line error; now truncated.
  - `[low]` `[patch]` `_load_schema()` was `lru_cache`d and handed out the shared mutable dict, so
    any caller mutating it silently poisoned every later validation; only the text is cached now.

**Deferred (1).** `DW-FU-10-2` — `pixi run --frozen -e pyforge-ci pyforge-deps-test` fails
`test_conda_run_deps_add_nothing_undeclared[pyforge-mason]`. Pre-existing and provably unrelated:
every input that assertion reads is byte-identical to baseline `64e717d`, and the remedy edits
`pyforge-mason`'s manifests or `pyforge-ci`'s allow-list — both inside this spec's Never list.

**Rejected (2).** (1, medium) *No `adopted_at <= last_update` constraint* — enforcing clock
monotonicity would make a legitimate write fail under ordinary NTP skew, a worse failure than the
inverted pair it prevents. (2, low) *`utc_timestamp()` should consume `ports/clock.py::ClockPort`
per AD-20* — the function already accepts an explicit `moment` for determinism, and importing
`marshal.ports` would breach the import surface this spec's Boundaries pin.

## Design Notes

**Runtime `jsonschema` in `src/` is deliberate and new here.** Every other marshal schema
(`schemas/*.json`) is validated in tests only, and `model/manifest.py` says so explicitly. Story
10.2's AC ("validates against `state/schema.json` on every read") overrides that precedent for this
one file, because state is the artifact whose corruption must degrade to a finding rather than a
crash (FR-104). The schema is co-located under `seed/state/`, not in `marshal/schemas/`, per the
epics Surface line.

**Four points where the contract is silent; the reading chosen, and why.** (1) `mode` — only
`mode: init` is ever named (FR-77). `init` and `adopt` are the only two verbs that materialize a
repo (`check` is read-only, `update` moves `model_version` without re-establishing origin), so the
enum is `["init", "adopt"]`. (2) Timestamp format — nothing specifies one, so RFC-3339 UTC is
pinned by a schema `pattern` (jsonschema does not enforce `format` by default) and produced by the
single owner `utc_timestamp()`. (3) `inserted_region_span` — recorded as `{name, start, end}`,
mirroring `RegionSpan.name` + `body_span`'s UTF-8 byte offsets rather than serializing the whole
`RegionSpan`; AD-58 needs only enough to strip the claim. (4) `agents[]` — no adapter-id constant
exists anywhere in `seed/`, so the schema constrains shape (lowercase kebab, unique) rather than
enumerating FR-115's four adapters, whose canonical spellings are Story 10.6's surface.

**DW-FU-9-3 is resolved by construction.** That entry asks whether a shape-invalid `recorded_sha`
should be distinguishable from a genuine hand-edit before it reaches
`check_managed_file`/`check_managed_region`. The schema's `body_sha` `^[0-9a-f]{8}$` pattern makes
a malformed hash a `StateInvalid` at read time, so no malformed value can ever reach those two
functions — the deferred question becomes moot without editing `detect/hashes.py`.

**Two small, deliberate duplications.** `_StrictLoader` is re-declared locally rather than imported
from `model/manifest.py`, which exposes it only as a private symbol; the alternative — no strict
loading — would let a hand-edited duplicate key be silently last-wins in the one file whose entire
premise is that it is not hand-edited. And `schema.json` hardcodes `ArtifactClass`'s wire values
because a schema is a wire contract, not a mirror of a Python enum; a test asserts the two agree so
the duplication cannot drift.

**`copier_data` carries only what state actually knows.** Per-invocation inputs a template also
needs (notably `slug`) are supplied by the verbs on top of this projection; state deliberately has
no `slug` field, and inventing one would breach the eleven-key contract.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: full suite green,
  including the new `test_seed_state_store.py`; no regression in `test_seed_errors.py`'s six-leaf
  assertion or `test_manifest_sync.py`.
- `pytest src/shared/packages/pyforge-core/tests/meta/test_atomic_write_sole_ownership.py -q` --
  expected: green, proving `store.py` added no second atomic-write implementation.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: green; import-linter contracts
  unaffected by the new `seed.state` edges.
- `git diff --stat -- src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/` --
  expected: empty (the gitignore region and manifest are untouched).

## Auto Run Result

Status: `done` — committed as `d640b48` on
`bmad-loop/20260814-202331-bc8d/10-2-state-schema-and-the-atomic-store` (not pushed).

**Implemented change.** Genesis gains its tool-owned state document. `read_state` validates
`.marshal/seed-state.yml` against a packaged closed Draft 2020-12 schema on every read and turns
every malformation — unreadable, non-UTF-8, invalid YAML, duplicate-keyed, non-mapping root,
schema-failing — into `StateInvalid` (exit 5) rather than a traceback (FR-104), while an absent
file returns `None` so Story 10.5 can `check` a never-adopted repo. `write_state` validates
before touching disk, then performs exactly one atomic replace routed through `seed/fs.py`, so
P-01's write boundary and P-08's "state written last" both hold and `pyforge-core` keeps sole
ownership of atomic write (CAP-7). Copier's answers file stays opaque (FR-105/AD-52): the module
never names it, and `copier_data` re-supplies answers from state. `managed[]` records `id`,
`path`, `class`, `body_sha`, and `inserted_region_span`, which a test proves is enough to
reconstruct an eject removal set from state alone (AD-58).

**Files changed** (4 files, +2567):
- `.../seed/state/schema.json` (NEW, 184) — the wire contract: eleven required keys,
  `additionalProperties: false` at every object level, `class` enumerating `ArtifactClass`'s six
  wire values, `body_sha` pinned to `hash_content`'s shape, `if`/`then` coupling
  `inserted_region_span` to the hybrid class.
- `.../seed/state/store.py` (NEW, 1023) — `SeedState`/`ManagedArtifact`/`LegacyArtifact`/
  `RegionSpanRecord`, `state_path`, `read_state`, `write_state`, `copier_data`,
  `seed_model_version`, `utc_timestamp`.
- `.../seed/state/__init__.py` (0 bytes → 39) — explicit `__all__` re-export.
- `.../tests/unit/test_seed_state_store.py` (NEW, 1321) — 83 tests.

**Review findings.** 19 patches applied (9 medium, 10 low), 1 deferred, 2 rejected, 0 intent gaps,
0 spec defects. Full breakdown in the Review Triage Log. Every reported defect was reproduced
against the worktree before being accepted, and every fix re-probed after. The medium patches
closed real holes rather than polish: duplicates authored inside a YAML merge anchor bypassed the
strict loader entirely; every anchored schema pattern admitted a trailing newline; list-valued
fields made `frozen=True` a half-promise; and duplicate managed claims, inverted region spans, and
class/span mismatches all validated. One medium finding — a plain `str` accepted for the
`ModelVersion`-typed `model_version`, round-tripping silently non-equal — was found by my own
post-patch verification, not by either reviewer.

**Verification.**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → **4321 passed, 9 deselected**
  (4260 before this story).
- `pytest src/shared/packages/pyforge-core/tests/meta/test_atomic_write_sole_ownership.py` →
  **304 passed** — no second atomic-write implementation.
- `git diff --stat -- .../seed/templates/` → **empty**; the `.gitignore` region still ignores only
  `.marshal/plan.json`, leaving state git-tracked (FR-107).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` → **1 failed, 73 passed**. The failure is
  `test_conda_run_deps_add_nothing_undeclared[pyforge-mason]` and is **pre-existing**: every input
  that assertion reads (root `pixi.toml`, every package `pyproject.toml`, the whole
  `pyforge-mason` tree) is byte-identical to baseline `64e717d`. Recorded as `DW-FU-10-2`.

**Follow-up review recommended: true.** 19 patches is high volume, and several changed behavior
rather than wording — inputs that previously validated are now rejected at construction
(non-tuple sequences, wrong-typed `model_version`, duplicate claims, inverted spans, class/span
mismatches, version-equal migrations), and the schema's patterns were re-anchored across the
board. That breadth of post-review behavioral change benefits from an independent look.

**Residual risks.**
- `DW-FU-10-2` will red `pyforge-deps-test` for every story in this loop until Mason's packaging
  gate is fixed. It is unrelated to this story and unfixable from within its surface.
- Four contract silences were resolved by judgment, not by citation, and are documented in Design
  Notes: `mode`'s value set (`init`/`adopt`), the timestamp format, `inserted_region_span`'s
  shape, and `agents[]`'s grammar. A later story with better information may narrow any of them;
  the schema is the single place each is pinned.
- `seed_model_version` reads `importlib.metadata.version("pyforge-marshal")`, so it reports
  whatever the installed distribution says — correct in the pixi env and in CI, but a source-path
  invocation without an install raises `InternalError` (exit 10) rather than guessing.
