---
title: 'Story 20.2: Face parity is part of done (CAP-5)'
type: 'feature'
created: '2026-08-27'
status: 'done'
updated: '2026-08-27'
baseline_revision: '8519bd3a835fad95a455b4b9e7eb198910693bb0'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-34-1-read-only-live-attach.md
warnings: []
deferred:
  - summary: >-
      epics.md still shows Story 20.2 (and 20.1) as "Status: backlog" even though the
      spec/ledger have progressed past that.
    evidence: |-
      Confirmed by grep: epics.md:1801 reads "Status: backlog" for Story 20.2, and 20.1's
      entry (epics.md:1791) shows the same staleness despite 20.1 being fully done
      (sprint-status-ledger.yaml + its spec file both say done). This story's own commits
      don't touch epics.md's Status field either -- that field is evidently synced on a
      separate, coarser cadence than per-story implementation work.
    location: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md:1791,1801
    severity: low
  - summary: >-
      The parity fixture only exercises INTEGER/VARCHAR/DOUBLE columns, not the data
      types most prone to silently diverging across the HTTP face's JSON wire format
      (NULL, DATE/TIMESTAMP, DECIMAL, BLOB).
    evidence: |-
      FIXTURE_TABLE in tests/query_plane/test_face_parity.py is
      `(id INTEGER, label VARCHAR, amount DOUBLE)` with three non-null rows. The story's
      own Problem statement is specifically about the HTTP face silently diverging from
      the library face without anyone noticing -- NULL/date/decimal round-tripping through
      JSON is a classic source of exactly that kind of silent divergence, and the current
      fixture can't exercise it. The gate's core mechanism (seeded-divergence detection) is
      still proven correct via the DOUBLE column, so this is a thoroughness gap, not a
      correctness defect.
    location: src/shared/packages/pyforge-atlas/tests/query_plane/test_face_parity.py:49-67
    severity: medium
  - summary: >-
      A TOCTOU race exists between `_port_is_free(DEFAULT_PORT)` and
      `boot_query_plane`'s actual bind of that same hard-coded port.
    evidence: |-
      If something else grabs port 3000 in the window between the pre-check and the real
      duckdb-server launch, the failure surfaces as an opaque
      `pytest.fail("duckdb-server exited at startup...")` rather than a clear
      "port was stolen" diagnostic. This mirrors the same pre-existing pattern already
      accepted in tests/test_query_plane_boot.py (Story 20.1) -- not introduced uniquely by
      this diff, and low-probability given tests run against ephemeral tmp_path DBs.
    location: src/shared/packages/pyforge-atlas/tests/query_plane/test_face_parity.py:228-229
    severity: low
---

<intent-contract>

## Intent

**Problem:** Story 20.1 raises both the in-process library face and the Mosaic
`duckdb-server` HTTP/Arrow face from one boot script, but nothing proves the two faces answer
identically. CAP-19's own success wording says filesystem-less consumers (DB-GPT/Langflow
estate reads, live console queries) "bind to the HTTP face" — if that face can silently diverge
from the library face nobody would notice until a consumer got wrong data.

**Approach:** per the `query-plane-face` ruling ("parity between them is part of the face's
definition of done"), add an offline-safe parity gate that runs an IDENTICAL fixture query set
against (a) the library face (a `connect_reader`/`connect_writer` handle) and (b) the HTTP/Arrow
`duckdb-server` face, and asserts row-for-row agreement. Prove the gate is not vacuous with a
seeded-divergence negative test (mutate one face's fixture row; the gate must fail and name the
divergence). This is a NEW, narrowly-scoped test suite — it must not be confused with, or added
into, the pre-existing `tests/parity/` package, which covers a different kind of parity
(legacy-`cf_atlas.db`-vs-migrated-pipeline-output, Story B1/B4/AD-19) entirely unrelated to the
CAP-19 query plane's two faces.

## Acceptance Criteria

Lifted verbatim from `epics.md` (Story 20.2):

> **Given** both faces up on fixture data **When** the parity gate runs an identical query set
> against the library face and the HTTP/Arrow face **Then** results agree row-for-row **And** a
> seeded divergence fails the gate (proven in-test) **And** filesystem-less consumers bind to
> the HTTP face per CAP-19's success wording ("the plane DSN or HTTP face") — parity is part of
> the face's definition of done per the `query-plane-face` ruling (2026-08-26); the gate is
> offline-safe.

## Boundaries & Constraints

**Always:** `BMAD_ACTIVE_PROJECT=pyforge-atlas`; ledger key `20-2-face-parity-is-part-of-done`;
depends on Story 20.1's boot script (S-20.1) — this story cannot be implemented before 20.1
lands the two faces it compares; run the SAME fixture data through both faces (never two
independently-seeded stores, or a "match" would be meaningless); the gate is offline-safe —
fixture-driven, `--frozen`, no live external network.

**Block If:** Story 20.1's boot script does not yet expose a stable, addressable way to reach
the HTTP/Arrow face in a test process (e.g. no fixed local port/socket the gate can connect to)
— report and stop; this story cannot construct a parity harness against a moving target.

**Never:** implement or modify the boot script itself (that is Story 20.1's scope only); build a
general cross-engine comparison framework beyond this one gate; add this gate's tests under
`tests/parity/` — that directory's "parity" means legacy-vs-migrated pipeline output (Story
B1/B4), a different concept the reviewer must not conflate with face parity; implement Story
20.3's pipeline work or Story 20.4/20.5's dashboard work here.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | fixture query set, both faces up | row-for-row match across every query | none |
| SEEDED_DIVERGENCE | one face's fixture row intentionally mutated in-test | gate fails, naming the divergent query/row | proves the gate is not vacuous |
| FACE_DOWN | HTTP face not raised (Story 20.1's stack-down degrade path) | gate explicitly skips/marks the HTTP-side comparison not-applicable with a named reason | never silently reports a pass for an unattempted comparison |
| EMPTY_RESULT | a fixture query returns 0 rows on both faces | parity holds (0 rows == 0 rows) | none |

</intent-contract>

## Code Map

- Depends on Story 20.1's new boot-script module — no such module exists in the repo yet
  (confirmed by grep), so this story's harness necessarily imports whatever connection-factory
  functions 20.1 lands (a library-face handle + an HTTP/Arrow-face client/endpoint).
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/duckdb_writer.py::connect_reader` — the
  library-face side of the comparison; reuse verbatim, do not re-open `atlas.duckdb` a second
  way.
- `src/shared/packages/pyforge-atlas/tests/singularity/test_duckdb_sole_engine.py` — the
  offline, `--frozen`, named-invariant-gate STYLE this new parity gate should structurally
  mirror (a single focused test module proving one named property, not a general framework).
- `src/shared/packages/pyforge-atlas/tests/parity/` (`harness.py`, `parity_runner.py`,
  `PARITY_NOTES.md`, `fixtures/`) — EXISTING but a DIFFERENT kind of "parity"
  (legacy-`cf_atlas.db`-vs-migrated-pipeline-output, Story B1/B4/AD-19). Cited here ONLY as a
  naming-collision warning: this story's face-parity gate must NOT live in, or be confused
  with, this directory. A new test home is needed — no existing `tests/query_plane/` or similar
  directory exists yet (confirmed by directory listing); create one, e.g.
  `tests/query_plane/test_face_parity.py`.
- `pixi.toml` `[feature.pyforge-atlas.tasks.duckdb-singularity]` (~line 2006) and
  `[feature.pyforge-atlas.tasks.parity-diff]` (~line 1994) — existing Wave F / Wave B gate task
  shapes to mirror for a new `[feature.pyforge-atlas.tasks.<face-parity-name>]` task; pick a name
  that does NOT collide with `parity-diff` (already taken by the unrelated B1/B4 gate).

## Review Triage Log

### 2026-08-27 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 0, low 2)
- defer: 3: (high 0, medium 1, low 2)
- reject: 16: (high 0, medium 0, low 16)
- addressed_findings:
  - `[low]` `[patch]` `_shutdown_boot`'s kill/wait fallback could raise on an already-exited
    process (stale `returncode` after a mid-test crash), masking an in-flight test failure and
    skipping `boot.library.close()`. Fixed: whole HTTP-teardown wrapped in `try/finally` so the
    library close always runs, and the kill/wait fallback calls are each wrapped in
    `contextlib.suppress(Exception)`.
  - `[low]` `[patch]` The seeded-divergence test's `writer.execute(UPDATE...)` wasn't wrapped in
    try/finally (unlike `_seed_fixture`'s identical pattern), so a failed `execute` would leak
    the writer connection and mask the real error behind a `SecondWriterRefused` on the next
    `boot_query_plane` call. Fixed: wrapped in `try/finally: writer.close()` to match.

Reject rationale (representative, not exhaustive): duplicated protocol-helper code vs.
`test_query_plane_boot.py` is a deliberate, spec-endorsed self-contained-file choice (Never:
no shared comparison framework); the `tests/query_plane/` subdirectory is spec-mandated (Code
Map explicitly calls for it), not a convention fragmentation; the AC's "filesystem-less
consumers bind to the HTTP face" clause is CAP-19 background rationale restated in the AC
prose, not an operationalized matrix row for this story to test; the sprint-status-ledger
key not being updated in this diff matches the established pattern (Story 20.1's ledger entry
was updated in a separate follow-up docs commit, not its implementation commit); the
sequential-vs-concurrent comparison approach is the only physically possible one given
DuckDB's single-writer-per-file constraint (documented in the module docstring), not a spec
deviation; the two `@requires_duckdb_server`-gated tests skipping when the binary is absent
mirrors the exact same accepted pattern in Story 20.1's own `test_query_plane_boot.py`.

## Auto Run Result

**Summary:** Added the offline-safe face-parity gate required by the `query-plane-face`
ruling: a new, narrowly-scoped test module runs an identical fixture query set against the
library face (`duckdb_writer.connect_reader`) and the real HTTP/Arrow `duckdb-server` face
raised by Story 20.1's `boot_query_plane`, asserting row-for-row agreement, with a
seeded-divergence negative test proving the gate is not vacuous and an explicit
not-applicable path for the stack-down degrade case. Kept entirely separate from the
pre-existing, unrelated `tests/parity/` package per the story's Never clause.

**Files changed:**
- `src/shared/packages/pyforge-atlas/tests/query_plane/__init__.py` — new (empty), new test
  package home for query-plane-face tests, distinct from `tests/parity/`.
- `src/shared/packages/pyforge-atlas/tests/query_plane/test_face_parity.py` — new; the
  parity gate itself: 3 tests covering all 4 I/O matrix rows (HAPPY_PATH, SEEDED_DIVERGENCE,
  FACE_DOWN, EMPTY_RESULT).
- `pixi.toml` — added `[feature.pyforge-atlas.tasks.query-plane-parity]` running the new
  test module; name deliberately distinct from the unrelated `parity-diff` task.

**Review findings breakdown:** 2 patches applied (both low severity — a test-teardown
exception-masking risk in `_shutdown_boot`, and a writer-connection leak-on-failure in the
seeded-divergence test); 3 items deferred (1 medium — fixture lacks NULL/DATE/DECIMAL
coverage for the exact divergence class this gate exists to catch; 2 low — stale
`epics.md` status field, a pre-existing TOCTOU port-check race mirrored from Story 20.1's own
tests); 16 items rejected as non-issues (spec-endorsed design choices, CAP-19 background
rationale misread as a testable AC, physically-necessitated sequential-comparison approach,
and patterns established/accepted by sibling Story 20.1).

**Follow-up review recommendation:** `false`. Patched-finding score: 2 low, 0 medium, 0
high → `3×0 + 1×2 = 2` (< 5), and no high-severity patch.

**Verification performed:**
- `pixi run -e pyforge-atlas query-plane-parity` → 3 passed (duckdb-server provisioned in
  this env; no tests skipped), both before and after the patch pass.
- Matrix Test Audit: all 4 I/O rows (HAPPY_PATH, SEEDED_DIVERGENCE, FACE_DOWN, EMPTY_RESULT)
  independently confirmed covered by an executed, passing assertion (read the test source
  directly, not just the implementer's report).
- Non-vacuousness independently reconfirmed: inspected `_assert_parity` and the
  seeded-divergence test's own in-test proof (`pytest.raises(AssertionError)` naming both
  affected queries).
- Confirmed `query_plane_boot.py` (Story 20.1's boot script) was not modified.
- Confirmed `pixi.toml`'s new task is additive only — `pixi project export
  conda-environment -e build` produces a byte-identical `environment.yaml`, so no
  regeneration/commit needed for that repo-wide gate.
- Full 4-layer parallel review (blind hunter, edge-case hunter, verification-gap,
  intent-alignment) run against the diff since baseline `8519bd3a83`; verification-gap
  reviewer found no gaps (confirmed by actually running the gate, not just reading it).

**Residual risks:** The fixture's narrow type coverage (deferred item 2, medium severity) is
the main one worth future attention — it's the closest thing to a real gap in the gate's
ability to catch the exact failure mode the story exists to prevent, though the gate's
core mechanism is proven sound. The two `@requires_duckdb_server`-gated tests only prove
parity for real when the binary is provisioned (true in this env and the documented
pyforge-atlas linux-64 pixi env); elsewhere they skip cleanly rather than failing, matching
Story 20.1's own established pattern for this dependency.
