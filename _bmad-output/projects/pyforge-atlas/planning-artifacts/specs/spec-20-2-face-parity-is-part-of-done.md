---
title: 'Story 20.2: Face parity is part of done (CAP-5)'
type: 'feature'
created: '2026-08-27'
status: 'ready'
updated: '2026-08-27'
baseline_revision: 'cc8b3b2b1c09d6e56a5aebf752e25f507c846571'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-34-1-read-only-live-attach.md
warnings: []
deferred: []
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
